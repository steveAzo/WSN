"""Revision A12 (review M11): confirmed uplink under ACK loss, v0.1 protocol "ack" vs revised "ack_rs".
Same settings as run_loss.py (L2, report-level, 2 retries, SOD / RLS-T / RLS-D / RIDGE-D, 3 seeds) with
uplink loss p in {0.5 %, 1 %, 5 %} and an independent ACK loss equal to p.
(With ACK loss = 0, "ack_rs" is identical to "ack" step for step - tests/test_sim.py - so the v0.1
loss.csv rows stand for that case.)  -> results/revision/loss_ack.csv
Usage: python src/sim/run_loss_ack.py [jobs]
"""
import sys
import time
import warnings
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, "src")
warnings.filterwarnings("ignore", category=RuntimeWarning)
from sim.engine import run_dps_lossy  # noqa: E402
from sim.run_phase2 import dataset_names, deltas, get  # noqa: E402
from sim.run_phase3 import factory  # noqa: E402

OUT = "results/revision/loss_ack.csv"


def job(spec):
    name, kind, p, proto, seed = spec
    ds = get(name); t0 = time.time(); delta = deltas(ds, 2)
    o = run_dps_lossy(ds.X, ds.seg_start, factory(ds, kind, delta, np.zeros(len(ds.params), int)), delta, p,
                      proto, retries=2, seed=seed, ack_loss=p)
    te = ds.test
    days = (ds.t[te].iloc[-1] - ds.t[te].iloc[0]).total_seconds() / 86400
    err = np.abs(ds.X - o["R"]); err[np.isnan(err)] = np.inf
    bad = (err > delta + 1e-9).any(1)
    return {"dataset": name, "kind": kind, "loss": p, "ack_loss": p, "proto": proto, "seed": seed,
            "tx_per_day": o["tx"][te].sum() / days, "viol_share": bad[te].mean(),
            "flag_share": o["flagged"][te].mean(), "unflagged_viol": int((bad & ~o["flagged"])[te].sum()),
            "viol_steps": int(bad[te].sum()), "secs": round(time.time() - t0, 1)}


if __name__ == "__main__":
    S = [(n, k, p, pr, s) for n in dataset_names() for k in ["SOD", "RLS-T", "RLS-D", "RIDGE-D"]
         for p in (0.005, 0.01, 0.05) for pr in ("ack", "ack_rs") for s in (0, 1, 2)]
    rows = []
    with Pool(int(sys.argv[1]) if len(sys.argv) > 1 else 1) as pool:
        for i, r in enumerate(pool.imap_unordered(job, S), 1):
            rows.append(r)
            if i % 48 == 0:
                print(f"{i}/{len(S)}", flush=True); pd.DataFrame(rows).to_csv(OUT, index=False)
    pd.DataFrame(rows).to_csv(OUT, index=False); print("saved", OUT)
