"""Phase 3: tune the damping phi of RLS-D (with history repair) on the TUNING sites only.
Rule (fixed before running): choose phi minimising the median, over tuning site x level (L1-L4),
of 100*(reports / min(SOD, RLS-T) - 1) in report mode; held-out sites reported separately.
-> results/phase3/rlsd.csv"""
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, "src")
from sim.engine import run_dps  # noqa: E402
from sim.metrics import compute  # noqa: E402
from sim.predictors import RLSDelta  # noqa: E402
from sim.run_phase2 import dataset_names, deltas, get  # noqa: E402

PHIS = [1.0, 0.97, 0.9, 0.8]


def job(spec):
    name, L, phi = spec
    ds = get(name); t0 = time.time(); d = deltas(ds, L)
    tr = [ds.train_segments(j) for j in range(len(ds.params))]
    r = run_dps(ds.X, ds.seg_start, lambda: [RLSDelta(w=24, train=tr[j], phi=phi, repair=True)
                                             for j in range(len(ds.params))], mode="report", delta=d)
    out = {"dataset": name, "level": L, "phi": phi}
    out.update(compute(ds, r, d)); out["secs"] = round(time.time() - t0, 1)
    return out


if __name__ == "__main__":
    S = [(n, L, p) for n in dataset_names() for L in (1, 2, 3, 4) for p in PHIS]
    rows = []
    with Pool(int(sys.argv[1]) if len(sys.argv) > 1 else 1) as pool:
        for i, r in enumerate(pool.imap_unordered(job, S), 1):
            rows.append(r)
            if i % 20 == 0:
                print(f"{i}/{len(S)}", flush=True)
    pd.DataFrame(rows).to_csv("results/phase3/rlsd.csv", index=False); print("saved")
