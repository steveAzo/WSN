"""Summarize Check A across all datasets at the 1-hour horizon (+ diel strength).

For each site and parameter:
  skill_VAR  = 1 - MSE(VAR)/MSE(last value)   (how much prediction helps at all)
  VAR/AR     = MSE ratio with 95% block-bootstrap CI ("cross" = CI entirely < 1)
  diel       = share of within-day variance explained by hour of day
Output: results/phase1/check_a_summary.csv and .md
"""
import glob
import json
from pathlib import Path

import pandas as pd

V = ["T", "EC", "DO", "pH"]


def diel_share(df, v, tz_shift_h=0):
    s = df.set_index("t")[v].dropna()
    anom = s - s.groupby(s.index.floor("D")).transform("mean")
    prof = anom.groupby((s.index + pd.Timedelta(hours=tz_shift_h)).hour).transform("mean")
    return float(prof.var() / anom.var())


def one_hour_key(r):
    hs = sorted({int(k.split("_")[0][1:]) for k in r["oos_skill"]})
    return hs[1]  # horizons are [1 step, 1 h, 6 h]


def rows_for(r, df, site, stratum, tz):
    h = one_hour_key(r)
    out = []
    for v in V:
        s = r["oos_skill"].get(f"h{h}_{v}")
        if s is None:
            continue
        lo, hi = s["ratio_95ci"]
        out.append({"site": site, "stratum": stratum, "param": v,
                    "skill_AR": round(s["skill_AR_vs_pers"], 3), "skill_VAR": round(s["skill_VAR_vs_pers"], 3),
                    "VAR/AR": round(s["VAR_over_AR_mse_ratio"], 3), "ci_lo": round(lo, 3), "ci_hi": round(hi, 3),
                    "cross_helps": hi < 1.0, "diel_share": round(diel_share(df, v, tz), 3)})
    return out


if __name__ == "__main__":
    meta = pd.read_csv("data/raw/usgs/candidate_sites.csv", dtype={"site": str}).set_index("site")
    rows = []
    # InWaterSense node 1 (4-parameter run)
    inws = json.load(open("results/phase1/check_a_inws.json"))[1]
    c = pd.read_csv("data/clean/inws_cycles.csv", parse_dates=["t"]); c = c[c.node == 1]
    rows += rows_for(inws, c, "InWaterSense n1", "real deployment (Libelium)", 0)
    for f in sorted(glob.glob("results/phase1/check_a_usgs_*.json")):
        site = Path(f).stem.split("_")[-1]
        r = json.load(open(f))
        df = pd.read_csv(f"data/clean/usgs/{site}.csv", parse_dates=["t"])
        tz = -8 if meta.loc[site, "state"] == "OR" else (-6 if meta.loc[site, "state"] == "IL" else -5)
        rows += rows_for(r, df, f"{site} {meta.loc[site, 'name'][:28]}", meta.loc[site, "stratum"], tz)
    t = pd.DataFrame(rows)
    t.to_csv("results/phase1/check_a_summary.csv", index=False)
    Path("results/phase1/check_a_summary.md").write_text(t.to_markdown(index=False))
    pd.set_option("display.width", 250)
    for v in V:
        print(f"\n=== {v} (1-hour horizon) ===")
        print(t[t.param == v][["site", "stratum", "diel_share", "skill_AR", "skill_VAR", "VAR/AR", "ci_lo", "ci_hi", "cross_helps"]].to_string(index=False))
