"""Revision A9: diel-smoothness statistic, exactly as pre-registered in
results/revision/A9_PREREGISTRATION.md (written before this script was run).

R_norm = [mean_h (p[h+1]-p[h])^2 / Var(p)] / [2(1 - cos(2 pi / 24))], p = hour-of-day profile (local
standard time) of the within-day anomaly, cyclic in h; computed for T. Exploratory (one failing case).
-> results/revision/a9_smoothness.csv
Usage: python src/analysis/revision_smoothness.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, "src/analysis")
from summarize_check_a import diel_share  # noqa: E402
from weija_phase1 import load as load_weija_phase1  # noqa: E402

R_SINE = 2 * (1 - np.cos(2 * np.pi / 24))
meta = pd.read_csv("data/raw/usgs/candidate_sites.csv", dtype={"site": str}).set_index("site")


def roughness(df, v, tz):
    s = df.set_index("t")[v].dropna()
    anom = s - s.groupby(s.index.floor("D")).transform("mean")
    p = anom.groupby((s.index + pd.Timedelta(hours=tz)).hour).mean().reindex(range(24))
    d = np.diff(np.r_[p.values, p.values[0]])
    return float(np.mean(d ** 2) / np.var(p.values) / R_SINE)


rows = []
c = pd.read_csv("data/clean/inws_cycles.csv", parse_dates=["t"]); c = c[c.node == 1]
rows.append(("InWaterSense n1", c, 0, ["T", "EC", "DO", "pH"]))
for site in meta.index:
    f = Path(f"data/clean/usgs/{site}.csv")
    if f.exists():
        tz = -8 if meta.loc[site, "state"] == "OR" else (-6 if meta.loc[site, "state"] == "IL" else -5)
        rows.append((f"USGS {site}", pd.read_csv(f, parse_dates=["t"]), tz, ["T", "EC", "DO", "pH"]))
rows.append(("Weija", load_weija_phase1(["T", "EC"]), 0, ["T", "EC"]))

r = pd.read_csv("results/phase2/results.csv")
g = r[(r["mode"] == "report") & (r.level == 2)].pivot_table(index="dataset", columns="kind", values="reports_per_day")
gain = (100 * (1 - g["RLS-T"] / g["SOD"])).to_dict()
w = pd.read_csv("results/weija/phase2.csv"); w = w[(w["mode"] == "report") & (w.level == 2)].set_index("kind").reports_per_day
gain["Weija"] = 100 * (1 - w["RLS-T"] / w["SOD"])

out = []
for name, df, tz, ps in rows:
    out.append({"dataset": name, "diel_share_mean": np.mean([diel_share(df, p, tz) for p in ps if p in df]),
                "diel_share_T": diel_share(df, "T", tz), "R_norm_T": roughness(df, "T", tz), "saving_L2": gain[name]})
o = pd.DataFrame(out)
o["S"] = o.diel_share_mean / o.R_norm_T
o["rank_R_norm_T"] = o.R_norm_T.rank(ascending=False).astype(int)
o.sort_values("R_norm_T", ascending=False).to_csv("results/revision/a9_smoothness.csv", index=False, float_format="%.6g")
print(o.sort_values("R_norm_T", ascending=False).round(3).to_string(index=False))
print("\nP1 (Weija has the largest T roughness):", o.loc[o.dataset == "Weija", "rank_R_norm_T"].item() == 1)
print("P2 (exploratory): rho(diel, saving) =", round(spearmanr(o.diel_share_mean, o.saving_L2)[0], 3),
      "; rho(S, saving) =", round(spearmanr(o.S, o.saving_L2)[0], 3), "(15 datasets)")
