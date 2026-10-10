"""Phase 2 - run every baseline on every dataset (trace-driven), in parallel.

Grid (fixed in advance, identical for every dataset):
  tolerance levels L0..L4 (fixed-delta methods):
      T  0.05 0.1 0.2 0.5 1.0 degC      DO 0.5 1 2 5 10 %sat
      pH 0.02 0.05 0.1 0.2 0.5          EC 0.5 1 2 5 10 % of the training-period median
  fixed-delta methods : SOD, LMS (Santini), DBP (Raza), RIDGE (ADAPTIVEML predictor), RLS
  ADAPTIVEML / -RLS   : alpha in 0.5 1 1.5 2 3 (paper default alpha = 1)
  modes               : separate, bundled, report   (for every DPS method)
  periodic            : every cycle, 30 min, 1 h, 2 h, 4 h (zero-order hold at the server)
  batch (Ghosh-style) : 30 min, 1 h, 2 h, 4 h (exact data, delivered late)
Method settings follow the papers: LMS N=4, mu=1/(100*Ex); DBP window 1 h, l=min(3, m//2);
Ridge/RLS w=24, lambda=1, gamma=0.98, rho=10. RLS updates only on reported values (sync-correct;
updating every step was worse, tested 2026-10-03) with covariance bounding.
RLS-T = RLS with gamma = 0.999: the paper default 0.98 (memory ~50 samples for 24 weights) was
unstable on 15-min data (81.5 vs 11.1 reports/day at Frenchtown L2), so we report BOTH the paper
default and this tuned variant, to avoid a straw-man comparison.

Usage: python src/sim/run_phase2.py [--datasets "USGS 01458500,InWaterSense n1"] [--jobs 8]
Output: results/phase2/results.csv  (one row per run)
"""
import argparse
import functools
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "src")
from sim import data as D  # noqa: E402
from sim.engine import run_batch, run_dps, run_periodic  # noqa: E402
from sim.metrics import compute  # noqa: E402
from sim.predictors import DBP, LMS, LastValue, Ridge, RLS  # noqa: E402

LEVELS = {"T": [0.05, 0.1, 0.2, 0.5, 1.0], "DO": [0.5, 1, 2, 5, 10],
          "pH": [0.02, 0.05, 0.1, 0.2, 0.5], "EC": [0.005, 0.01, 0.02, 0.05, 0.10]}
ALPHAS = [0.5, 1.0, 1.5, 2.0, 3.0]
MODES = ["separate", "bundled", "report"]
PERIODS_MIN = [None, 30, 60, 120, 240]
BATCH_MIN = [30, 60, 120, 240]


@functools.lru_cache(maxsize=2)
def get(name):
    """load ONLY the requested dataset (loading all of them in every worker exhausted memory)"""
    if name == "Weija":
        return D.load_weija()                   # held-out case study, only via --datasets Weija
    return D.load_inws() if name.startswith("InWaterSense") else D.load_usgs(name.split()[1])


def dataset_names():
    sites = pd.read_csv("data/raw/usgs/candidate_sites.csv", dtype={"site": str}).site
    return ["InWaterSense n1"] + [f"USGS {s}" for s in sites if Path(f"data/clean/usgs/{s}.csv").exists()]


def deltas(ds, lvl):
    ec_med = float(np.median(ds.X[~ds.test, ds.params.index("EC")]))
    return np.array([LEVELS[p][lvl] * (ec_med if p == "EC" else 1.0) for p in ds.params])


def make_factory(ds, pred, delta):
    m = max(4, int(round(60 / ds.step_min)))
    train = [ds.train_segments(j) for j in range(len(ds.params))]
    Ex = [float(np.mean(np.concatenate(s) ** 2)) for s in train]

    def make():
        out = []
        for j in range(len(ds.params)):
            if pred == "SOD": out.append(LastValue())
            elif pred == "LMS": out.append(LMS(N=4, Ex=Ex[j], emax=delta[j]))
            elif pred == "DBP": out.append(DBP(m=m, l=3))
            elif pred == "RIDGE": out.append(Ridge(w=24, train=train[j]))
            elif pred == "RLS": out.append(RLS(w=24, train=train[j]))
            elif pred == "RLS-T": out.append(RLS(w=24, train=train[j], gamma=0.999))
        return out
    return make


def job(spec):
    name, kind, a, b, mode = spec
    ds = get(name)
    t0 = time.time()
    row = {"dataset": name, "kind": kind, "setting": a, "mode": mode}
    if kind in ("SOD", "LMS", "DBP", "RIDGE", "RLS", "RLS-T"):
        delta = deltas(ds, a)
        res = run_dps(ds.X, ds.seg_start, make_factory(ds, kind, delta), mode=mode, delta=delta)
        row.update(compute(ds, res, delta)); row["level"] = a
        row.update({f"{p}_delta": float(d) for p, d in zip(ds.params, delta)})
    elif kind in ("ADAPTIVEML", "ADAPTIVEML-RLS", "ADAPTIVEML-RLS-T"):
        pred = {"ADAPTIVEML": "RIDGE", "ADAPTIVEML-RLS": "RLS", "ADAPTIVEML-RLS-T": "RLS-T"}[kind]
        res = run_dps(ds.X, ds.seg_start, make_factory(ds, pred, [None] * len(ds.params)), mode=mode, alpha=a)
        row.update(compute(ds, res)); row["alpha"] = a
    elif kind == "PERIODIC":
        k = 1 if a is None else max(1, int(round(a / ds.step_min)))
        row.update(compute(ds, run_periodic(ds.X, ds.seg_start, k))); row["period_min"] = a or ds.step_min
    elif kind == "BATCH":
        k = max(1, int(round(a / ds.step_min)))
        res, delay = run_batch(ds.X, ds.seg_start, k)
        row.update(compute(ds, res, extra_delay_steps=delay)); row["period_min"] = a
    row["secs"] = round(time.time() - t0, 1)
    return row


def specs(names):
    out = []
    for n in names:
        for kind in ("SOD", "LMS", "DBP", "RIDGE", "RLS", "RLS-T"):
            out += [(n, kind, l, None, m) for l in range(5) for m in MODES]
        for kind in ("ADAPTIVEML", "ADAPTIVEML-RLS", "ADAPTIVEML-RLS-T"):
            out += [(n, kind, a, None, m) for a in ALPHAS for m in MODES]
        out += [(n, "PERIODIC", p, None, "report") for p in PERIODS_MIN]
        out += [(n, "BATCH", p, None, "report") for p in BATCH_MIN]
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", default=None)
    ap.add_argument("--jobs", type=int, default=2)   # laptop has 3.9 GB RAM: 6 workers ran out of memory
    ap.add_argument("--out", default="results/phase2/results.csv")
    a = ap.parse_args()
    names = a.datasets.split(",") if a.datasets else dataset_names()
    S = specs(names)
    prev = []
    if Path(a.out).exists():                     # resume: skip runs already saved
        old = pd.read_csv(a.out)
        prev = old.to_dict("records")
        done = {(r["dataset"], r["kind"], "" if pd.isna(r["setting"]) else float(r["setting"]), r["mode"]) for r in prev}
        S = [s for s in S if (s[0], s[1], "" if s[2] is None else float(s[2]), s[4]) not in done]
        print(f"resuming: {len(prev)} runs already saved, {len(S)} to go", flush=True)
    print(f"{len(S)} runs on {len(names)} datasets with {a.jobs} workers", flush=True)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    rows, t0 = list(prev), time.time()
    with Pool(a.jobs) as pool:
        for i, r in enumerate(pool.imap_unordered(job, S), 1):
            rows.append(r)
            if i % 10 == 0 or i == len(S):
                el = time.time() - t0
                print(f"  {i}/{len(S)} done, {el/60:.1f} min elapsed, ~{el/i*(len(S)-i)/60:.0f} min to go", flush=True)
                pd.DataFrame(rows).to_csv(a.out, index=False)       # checkpoint
    pd.DataFrame(rows).to_csv(a.out, index=False)
    print("saved", a.out)
