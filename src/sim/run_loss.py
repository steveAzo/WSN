"""Phase 3d: packet loss and resynchronisation (report-level, bounded, level L2).

Loss rates: 0.5 % and 1 % (measured NB-IoT range, Michelinakis 2021, paper 11) and 5 % (stress).
Protocols: "ack" (confirmed uplink, 2 retries) and "seq" (unconfirmed + sequence numbers +
heartbeat resync every 6 h or 24 h). Predictors: SOD, RLS-T, RLS-D (proposed), RIDGE-D (frozen variant). 3 loss seeds each.
Metrics (test period): transmissions/day (incl. retries, heartbeats), share of steps where some
parameter violates delta, share flagged, UNFLAGGED violations (must be 0 under "seq").
Usage: python src/sim/run_loss.py [--jobs 2]   -> results/phase3/loss.csv
"""
import argparse
import warnings
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
from sim.engine import run_dps_lossy  # noqa: E402
from sim.run_phase2 import dataset_names, deltas, get  # noqa: E402
from sim.run_phase3 import factory, offline_choice  # noqa: E402

OUT = Path("results/phase3/loss.csv")
LOSS = [0.0, 0.005, 0.01, 0.05]
PROTO = [("ack", None), ("seq", 6 * 60), ("seq", 24 * 60)]
KINDS = ["SOD", "RLS-T", "RLS-D", "RIDGE-D"]
SEEDS = [0, 1, 2]


def job(spec):
    name, kind, p, (proto, hb_min), seed = spec
    ds = get(name); t0 = time.time()
    delta = deltas(ds, 2)
    choice = offline_choice(ds, delta) if kind == "SWITCH" else np.zeros(len(ds.params), int)
    hb = int(round(hb_min / ds.step_min)) if hb_min else None
    o = run_dps_lossy(ds.X, ds.seg_start, factory(ds, kind, delta, choice), delta, p, proto,
                      retries=2, hb_steps=hb, seed=seed)
    te = ds.test
    days = (ds.t[te].iloc[-1] - ds.t[te].iloc[0]).total_seconds() / 86400
    err = np.abs(ds.X - o["R"]); err[np.isnan(err)] = np.inf
    bad = (err > delta + 1e-9).any(1)
    return {"dataset": name, "kind": kind, "loss": p, "proto": proto, "hb_min": hb_min, "seed": seed,
            "tx_per_day": o["tx"][te].sum() / days, "viol_share": bad[te].mean(),
            "flag_share": o["flagged"][te].mean(), "unflagged_viol": int((bad & ~o["flagged"])[te].sum()),
            "max_err_over_delta": float(np.nanmax(np.where(np.isfinite(err[te]), err[te], np.nan) / delta)),
            "secs": round(time.time() - t0, 1)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--jobs", type=int, default=1); a = ap.parse_args()
    S = [(n, k, p, pr, s) for n in dataset_names() for k in KINDS for p in LOSS for pr in PROTO
         for s in (SEEDS if p > 0 else [0])]
    rows = []
    if OUT.exists():
        old = pd.read_csv(OUT); rows = old.to_dict("records")
        done = {(r["dataset"], r["kind"], r["loss"], r["proto"], None if pd.isna(r["hb_min"]) else int(r["hb_min"]), r["seed"])
                for r in rows}
        S = [s for s in S if (s[0], s[1], s[2], s[3][0], s[3][1], s[4]) not in done]
    print(f"{len(S)} runs", flush=True); t0 = time.time()
    with Pool(a.jobs) as pool:
        for i, r in enumerate(pool.imap_unordered(job, S), 1):
            rows.append(r)
            if i % 10 == 0 or i == len(S):
                pd.DataFrame(rows).to_csv(OUT, index=False)
                el = time.time() - t0
                print(f"  {i}/{len(S)} {el/60:.1f} min, ~{el/i*(len(S)-i)/60:.0f} min left", flush=True)
    pd.DataFrame(rows).to_csv(OUT, index=False); print("saved", OUT)
