"""Phase 1 — sensor-resolution (quantization) hypothesis.

Hypothesis: where 1-step changes are comparable to the recording resolution, the series is a
staircase and prediction skill is low even if a diel cycle exists (large, slow rivers).
Measures per site x parameter (all from the data, no assumptions):
  resolution   = most common non-zero |1-step change| (the recording quantum)
  zero_share   = share of 1-step changes that are exactly 0
  dh_over_res  = median |1-hour change| / resolution
Then: Spearman correlation of these with the 1-hour VAR skill from Check A.
"""
import numpy as np
import pandas as pd

V = ["T", "EC", "DO", "pH"]


def measures(df, v, steps_per_hour):
    rows = []
    d1, dh = [], []
    for _, s in df.groupby("segment"):
        x = s[v].dropna().round(6)
        d1.append(x.diff().dropna()); dh.append(x.diff(steps_per_hour).dropna())
    d1, dh = pd.concat(d1).abs(), pd.concat(dh).abs()
    nz = d1[d1 > 0]
    res = float(nz.round(6).mode().iloc[0]) if len(nz) else np.nan
    return {"resolution": res, "zero_share": float((d1 == 0).mean()),
            "dh_over_res": float(dh.median() / res) if res else np.nan}


if __name__ == "__main__":
    skill = pd.read_csv("results/phase1/check_a_summary.csv")
    out = []
    c = pd.read_csv("data/clean/inws_cycles.csv", parse_dates=["t"]); c = c[c.node == 1]
    for v in V:
        out.append({"site": "InWaterSense n1", "param": v, **measures(c, v, 6)})
    for site in skill.site.unique():
        if site.startswith("InWater"):
            continue
        code = site.split()[0]
        df = pd.read_csv(f"data/clean/usgs/{code}.csv", parse_dates=["t"])
        step = df.t.diff().dt.total_seconds().median() / 60
        for v in V:
            out.append({"site": site, "param": v, **measures(df, v, int(round(60 / step)))})
    q = pd.DataFrame(out).merge(skill[["site", "param", "skill_VAR", "diel_share"]], on=["site", "param"])
    q.to_csv("results/phase1/quantization.csv", index=False)
    pd.set_option("display.width", 220)
    print(q.round(3).to_string(index=False))
    u = q[~q.site.str.startswith("InWater")]
    print("\nSpearman with 1-h VAR skill (USGS):")
    for m in ["zero_share", "dh_over_res", "diel_share"]:
        print(f"  {m:12s} {u[m].corr(u.skill_VAR, method='spearman'):+.2f}")
    # does adding resolution information explain residual misses of diel share?
    u = u.assign(r_diel=u.diel_share.rank(), r_skill=u.skill_VAR.rank(), r_dh=u.dh_over_res.rank())
    X = np.c_[np.ones(len(u)), u.r_diel, u.r_dh]
    for cols, name in [((0, 1), "diel only"), ((0, 1, 2), "diel + dh/res")]:
        b, *_ = np.linalg.lstsq(X[:, cols], u.r_skill, rcond=None)
        pred = X[:, cols] @ b
        print(f"  rank-regression R^2 ({name}): {1 - np.var(u.r_skill - pred) / np.var(u.r_skill):.2f}")
