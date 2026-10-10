"""Revision A2: analyse results/revision/ablation.csv (RLS-D ablation, rho and phi provenance).
Gap of each variant to the per-site best fixed predictor min(SOD, RLS-T) (phase3.csv), per level,
held-out test sites (6 USGS) and tuning sites separately; phi rule re-applied at rho = 0.01.
-> results/revision/a2_ablation_summary.csv, a2_phi_rule.csv
Usage: python src/analysis/revision_ablation.py
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "src")
from sim.run_roc import split  # noqa: E402

tune, test = split()
rng = np.random.default_rng(20261010)
a = pd.read_csv("results/revision/ablation.csv")
p3 = pd.read_csv("results/phase3/phase3.csv"); p3 = p3[(p3.det == 0) & (p3.tight == 0)]
b = p3.pivot_table(index=["dataset", "level"], columns="kind", values="reports_per_day")
oracle = b[["SOD", "RLS-T"]].min(axis=1)
# integrity: RLS-D in the ablation must equal phase3.csv exactly
m = a[a.variant == "RLS-D"].set_index(["dataset", "level"]).reports_per_day
assert np.allclose(m.sort_index(), b["RLS-D"].reindex(m.sort_index().index)), "RLS-D does not reproduce"
v = a.pivot_table(index=["dataset", "level"], columns="variant", values="reports_per_day")
v["RLS-T"] = b["RLS-T"]; v["SOD"] = b["SOD"]
gap = 100 * (v.div(oracle.reindex(v.index), axis=0) - 1)
gap = gap.reset_index()
gap["set"] = np.where(gap.dataset.isin(tune), "tune",
                      np.where(gap.dataset.str.startswith("InWater"), "InWaterSense", "test"))
ORDER = ["SOD", "RLS-T", "CHG", "CHG+DAMP", "CHG+REPAIR", "RLS-D", "RLS-D(rho=10)", "RLS-D(phi=0.9)", "RLS-D(phi=0.8)"]
rows = []
for (st, lvl), e in gap.groupby(["set", "level"]):
    for c in ORDER:
        x = e[c].values
        i = rng.integers(0, len(x), (20000, len(x)))
        lo, hi = np.percentile(np.median(x[i], axis=1), [2.5, 97.5]) if len(x) > 1 else (np.nan, np.nan)
        rows.append({"set": st, "level": lvl, "variant": c, "n": len(x), "median_gap_pct": np.median(x),
                     "ci_lo": lo, "ci_hi": hi, "max_gap_pct": x.max()})
s = pd.DataFrame(rows)
s.to_csv("results/revision/a2_ablation_summary.csv", index=False, float_format="%.6g")
w = s.pivot_table(index=["set", "level"], columns="variant", values="median_gap_pct")[ORDER]
pd.set_option("display.width", 250)
print("median gap to the per-site best fixed predictor (%), report mode\n", w.round(1))
# phi selection rule (fixed in Phase 3): minimise the median over tuning site x L1-L4 of the gap
cand = {"1.0": "CHG+REPAIR", "0.97": "RLS-D", "0.9": "RLS-D(phi=0.9)", "0.8": "RLS-D(phi=0.8)"}
t = gap[gap.set == "tune"]
rule = pd.DataFrame([{"phi": k, "rho": 0.01, "median_gap_tuning_L1-L4": t[c].median()} for k, c in cand.items()])
old = pd.read_csv("results/phase3/rlsd.csv")
old = old.merge(oracle.rename("oracle").reset_index(), on=["dataset", "level"])
old["gap"] = 100 * (old.reports_per_day / old.oracle - 1)
old = old[old.dataset.isin(tune)].groupby("phi").gap.median().rename("median_gap_tuning_L1-L4").reset_index()
old["rho"] = 10.0; old["phi"] = old.phi.astype(str)
rule = pd.concat([old, rule])
rule.to_csv("results/revision/a2_phi_rule.csv", index=False, float_format="%.6g")
print("\nphi rule on tuning sites (choose the minimum):\n", rule.to_string(index=False))
