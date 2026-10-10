"""Revision A2: RLS-D ablation and provenance checks (review M7, M8; analysis "Ablation of RLS-D").

Variants (all: change model on the last w = 24 changes, ridge warm start, RLS gamma = 0.999, report mode):
  CHG              phi = 1,    no repair, rho = 0.01
  CHG+DAMP         phi = 0.97, no repair, rho = 0.01
  CHG+REPAIR       phi = 1,    repair,    rho = 0.01
  RLS-D            phi = 0.97, repair,    rho = 0.01   (the proposed predictor; must equal phase3.csv)
  RLS-D(rho=10)    phi = 0.97, repair,    rho = 10     (the covariance scale used when phi was tuned)
  RLS-D(phi=0.9)   phi = 0.9,  repair,    rho = 0.01   } with RLS-D and CHG+REPAIR: the phi-selection rule
  RLS-D(phi=0.8)   phi = 0.8,  repair,    rho = 0.01   } re-applied at the final rho (tuning sites only)
The level-based baseline RLS-T comes from results/phase3/phase3.csv (same simulator, same deltas).
All 14 datasets x L1-L4.  -> results/revision/ablation.csv
Usage: python src/sim/run_ablation.py [jobs]
"""
import sys
import time
from multiprocessing import Pool

import pandas as pd

sys.path.insert(0, "src")
from sim.engine import run_dps  # noqa: E402
from sim.metrics import compute  # noqa: E402
from sim.predictors import RLSDelta  # noqa: E402
from sim.run_phase2 import dataset_names, deltas, get  # noqa: E402

VARIANTS = {"CHG": (1.0, False, 0.01), "CHG+DAMP": (0.97, False, 0.01), "CHG+REPAIR": (1.0, True, 0.01),
            "RLS-D": (0.97, True, 0.01), "RLS-D(rho=10)": (0.97, True, 10.0),
            "RLS-D(phi=0.9)": (0.9, True, 0.01), "RLS-D(phi=0.8)": (0.8, True, 0.01)}
OUT = "results/revision/ablation.csv"


def job(spec):
    name, L, var = spec
    phi, repair, rho = VARIANTS[var]
    ds = get(name); t0 = time.time(); d = deltas(ds, L)
    tr = [ds.train_segments(j) for j in range(len(ds.params))]
    r = run_dps(ds.X, ds.seg_start, lambda: [RLSDelta(w=24, train=tr[j], phi=phi, repair=repair, rho=rho)
                                             for j in range(len(ds.params))], mode="report", delta=d)
    out = {"dataset": name, "level": L, "variant": var, "phi": phi, "repair": repair, "rho": rho}
    out.update(compute(ds, r, d)); out["secs"] = round(time.time() - t0, 1)
    return out


if __name__ == "__main__":
    S = [(n, L, v) for n in dataset_names() for L in (1, 2, 3, 4) for v in VARIANTS]
    rows = []
    with Pool(int(sys.argv[1]) if len(sys.argv) > 1 else 1) as pool:
        for i, r in enumerate(pool.imap_unordered(job, S), 1):
            rows.append(r)
            if i % 28 == 0:
                print(f"{i}/{len(S)}", flush=True)
                pd.DataFrame(rows).to_csv(OUT, index=False)
    pd.DataFrame(rows).to_csv(OUT, index=False); print("saved", OUT)
