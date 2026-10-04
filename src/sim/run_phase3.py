"""Phase 3b/c: the proposed scheme and its ablations, on every dataset and tolerance level.

Methods (all report-level, all error-bounded by delta):
  SOD, RLS-T        : the Phase 2 baselines (re-run so every number comes from one code path)
  RLS-D             : proposed predictor: ridge model on CHANGES, slow RLS adaptation (rho = 0.01),
                      damped trend (phi from results/phase3/rlsd_choice.json, tuned on tuning sites
                      only), history repair
  RIDGE-D           : same with frozen weights (the variant for unconfirmed uplinks)
  SWITCH            : documented NEGATIVE result: online synchronised switching between SOD and
                      RLS-T (predictors.Switch), starting from the training-replay choice
  (OFFLINE / training-replay selection: negative result, results/phase3/selection_replay.csv)
  +DET              : node-side CUSUM event detector (config from results/phase3/detector_choice.json,
                      chosen on tuning sites only); an alarm forces a report
  +DET+TIGHT        : additionally delta/2 while the detector is in its event state
  det = 2           : sensitivity analysis with a high-sensitivity detector config
Runs per (dataset, level, method): clean data (Check B events, report cost) and two injected-event
copies (amp 5 step / ramp, 3 h; known onsets) for informed / alarm capture.
Usage: python src/sim/run_phase3.py [--jobs 2]   -> results/phase3/phase3.csv (resumable)
"""
import argparse
import warnings
import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "src")
# expected: median alarm delay of methods WITHOUT a detector is over an empty set -> NaN
warnings.filterwarnings("ignore", message="Mean of empty slice")
warnings.filterwarnings("ignore", category=RuntimeWarning, module="numpy")
from sim.detector import make_detector  # noqa: E402
from sim.engine import run_dps  # noqa: E402
from sim.inject import eval_events, hours, inject, noise_scale, resolution  # noqa: E402
from sim.metrics import compute  # noqa: E402
from sim.predictors import LastValue, RLS, RLSDelta, Switch  # noqa: E402
from sim.roc_detector import train_hours  # noqa: E402
from sim.run_phase2 import dataset_names, deltas, get  # noqa: E402

OUT = Path("results/phase3/phase3.csv")
METHODS = [("SOD", 0, 0), ("RLS-T", 0, 0), ("RLS-D", 0, 0), ("RIDGE-D", 0, 0), ("SWITCH", 0, 0),
           ("SOD", 1, 0), ("RLS-D", 1, 0), ("RLS-D", 1, 1),
           ("SOD", 2, 0), ("RLS-D", 2, 0)]   # det 1 = chosen config; det 2 = sensitive (sensitivity analysis)


def rlsd_phi():
    return json.loads(Path("results/phase3/rlsd_choice.json").read_text())["phi"]
LEVELS_RUN = [1, 2, 3, 4]                     # L0: every method already captures all events (Phase 2)
INJ = [("step", 5, 180), ("ramp", 5, 180)]


def det_cfg(det=1):
    """1: config chosen by the pre-registered rule on tuning sites; 2: high-sensitivity config
    (round-1 cfg 4: lag 120 min, k=2, H=4; ~0.73 detection at ~8 false alarms/param/30 d)"""
    if det == 2:
        from sim.run_roc import GRID
        return GRID[4]
    return json.loads(Path("results/phase3/detector_choice.json").read_text())["config"]


def offline_choice(ds, delta):
    """per parameter: 1 (RLS-T) if it had fewer exceedances than SOD on the training period"""
    n = int((~ds.test).sum())
    X, seg = ds.X[:n], ds.seg_start[:n]
    tr = [ds.train_segments(j) for j in range(len(ds.params))]
    cnt = []
    for kind in ("SOD", "RLS-T"):
        mk = lambda: [LastValue() if kind == "SOD" else RLS(w=24, train=tr[j], gamma=0.999)
                      for j in range(len(ds.params))]
        cnt.append(run_dps(X, seg, mk, mode="separate", delta=delta).sent.sum(0))
    return (cnt[1] < cnt[0]).astype(int)


def factory(ds, kind, delta, choice):
    tr = [ds.train_segments(j) for j in range(len(ds.params))]
    phi = rlsd_phi() if kind in ("RLS-D", "RIDGE-D") else None

    def make():
        out = []
        for j in range(len(ds.params)):
            rls = lambda j=j: RLS(w=24, train=tr[j], gamma=0.999)
            if kind == "SOD": out.append(LastValue())
            elif kind == "RLS-T": out.append(rls())
            elif kind == "RLS-D": out.append(RLSDelta(w=24, train=tr[j], phi=phi, repair=True, rho=0.01))
            elif kind == "RIDGE-D": out.append(RLSDelta(w=24, train=tr[j], phi=phi, repair=True, adapt=False))
            elif kind == "SWITCH":
                out.append(Switch(LastValue, rls, delta[j], ds.step_min, start=int(choice[j])))
        return out
    return make


def det_factory(ds, res, trh, cfg):
    return lambda: [make_detector(ds.step_min, ds.train_segments(j), res[j], trh, cfg)
                    for j in range(len(ds.params))]


def job(spec):
    name, lvl, mi = spec
    ds = get(name); kind, det, tight = METHODS[mi]
    t0 = time.time()
    res, delta, h = resolution(ds), deltas(ds, lvl), hours(ds)
    choice = offline_choice(ds, delta) if kind == "SWITCH" else np.zeros(len(ds.params), int)
    kw = dict(mode="report", delta=delta)
    if det:
        kw.update(make_detectors=det_factory(ds, res, train_hours(ds), det_cfg(det)), hour=h)
    if tight:
        kw["tighten"] = delta / 2
    keep = {}

    def mk():
        keep["p"] = factory(ds, kind, delta, choice)(); return keep["p"]
    r = run_dps(ds.X, ds.seg_start, mk, **kw)
    row = {"dataset": name, "level": lvl, "kind": kind, "det": det, "tight": tight,
           "choice_rls": ",".join(map(str, choice))}
    row.update(compute(ds, r, delta))
    if kind == "SWITCH":
        row["n_switch"] = sum(p.n_switch for p in keep["p"])
    if det:
        days = (ds.t[ds.test].iloc[-1] - ds.t[ds.test].iloc[0]).total_seconds() / 86400
        row["alarms_per_day"] = float(r.alarm[ds.test].sum() / days)
    sc = noise_scale(ds, res)
    for shape, amp, dur in INJ:
        X, ev = inject(ds, shape, amp, dur, seed=0, scale=sc, res=res)
        ri = run_dps(X, ds.seg_start, factory(ds, kind, delta, choice), **kw)
        e = eval_events(ev, ri, ds.step_min)
        row[f"{shape}_n"] = len(e)
        row[f"{shape}_informed"] = e.informed.mean()
        row[f"{shape}_inf_delay"] = e.inf_delay.median()
        row[f"{shape}_alarmed"] = e.alarmed.mean()
        row[f"{shape}_al_delay"] = e.al_delay.median()
        row[f"{shape}_a_over_delta"] = float(np.median(ev.a / delta[ev.j.astype(int)]))
    row["secs"] = round(time.time() - t0, 1)
    return row


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--datasets", default=None); a = ap.parse_args()
    names = a.datasets.split(",") if a.datasets else dataset_names()
    S = [(n, l, m) for n in names for l in LEVELS_RUN for m in range(len(METHODS))]
    rows = []
    if OUT.exists():
        old = pd.read_csv(OUT); rows = old.to_dict("records")
        km = {(k, d, t): i for i, (k, d, t) in enumerate(METHODS)}
        done = {(r["dataset"], r["level"], km[(r["kind"], r["det"], r["tight"])]) for r in rows}
        S = [s for s in S if s not in done]
    print(f"{len(S)} runs", flush=True)
    t0 = time.time()
    with Pool(a.jobs) as pool:
        for i, r in enumerate(pool.imap_unordered(job, S), 1):
            rows.append(r)
            if i % 5 == 0 or i == len(S):
                pd.DataFrame(rows).to_csv(OUT, index=False)
                el = time.time() - t0
                print(f"  {i}/{len(S)} {el/60:.1f} min, ~{el/i*(len(S)-i)/60:.0f} min left", flush=True)
    pd.DataFrame(rows).to_csv(OUT, index=False); print("saved", OUT)
