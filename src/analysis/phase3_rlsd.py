"""Choose RLS-D damping phi on TUNING sites (rule in src/sim/run_rlsd.py); report held-out sites.
Reference = per-site best of SOD / RLS-T from Phase 2 (same code path, report mode).
-> results/phase3/rlsd_choice.json, results/phase3/t_rlsd.csv"""
import json
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "src")
from sim.run_roc import split  # noqa: E402

tune, test = split()
r = pd.read_csv("results/phase3/rlsd.csv")
p2 = pd.read_csv("results/phase2/results.csv")
p2 = p2[(p2["mode"] == "report") & p2.kind.isin(["SOD", "RLS-T"]) & p2.level.between(1, 4)]
ref = p2.pivot_table(index=["dataset", "level"], columns="kind", values="reports_per_day")
ref["oracle"] = ref.min(axis=1)
d = r.join(ref, on=["dataset", "level"])
d["gap"] = 100 * (d.reports_per_day / d.oracle - 1)
d["gap_rlst"] = 100 * (d["RLS-T"] / d.oracle - 1)
d["gap_sod"] = 100 * (d.SOD / d.oracle - 1)
d["set"] = np.where(d.dataset.isin(tune), "tune", "test")
assert (d[[c for c in d if c.endswith("_viol")]].fillna(0) == 0).all().all(), "bound violated"

s = d.groupby(["set", "phi"]).gap.agg(["median", "mean", "max"]).round(1)
print("gap to per-site best fixed predictor (%), by phi:\n", s.to_string())
phi = float(d[d.set == "tune"].groupby("phi").gap.median().idxmin())
print("\nCHOSEN phi =", phi)
json.dump({"phi": phi, "rule": "min median gap to min(SOD, RLS-T) over tuning sites x L1-L4",
           "tuning_sites": tune}, open("results/phase3/rlsd_choice.json", "w"), indent=1)

c = d[d.phi == phi]
t = c.groupby(["set", "level"]).agg(rlsd=("gap", "median"), rlsd_max=("gap", "max"),
                                    rlst=("gap_rlst", "median"), rlst_max=("gap_rlst", "max"),
                                    sod=("gap_sod", "median"), sod_max=("gap_sod", "max"),
                                    beats_oracle=("gap", lambda g: f"{(g < 0).sum()}/{len(g)}")).round(1)
print("\nchosen phi, gap to oracle (%) by level:\n", t.to_string())
t.reset_index().to_csv("results/phase3/t_rlsd.csv", index=False)
print("\nper site (chosen phi):\n", c.pivot_table(index="dataset", columns="level", values="gap").round(1).to_string())
