"""Revision A3 + A4.

A3 (review M13, Fig. 3): rate-matched comparison of ADAPTIVEML with the bounded RLS-T front.
    Per site, the bounded front is RLS-T at L0-L4 (report mode): points (report rate, max error).
    For each ADAPTIVEML run we INTERPOLATE the bounded max error at exactly the ADAPTIVEML report
    rate (linear in log-log between neighbouring levels), per parameter. Runs whose rate lies
    outside the bounded front's range are flagged and excluded, not extrapolated.
    -> results/revision/a3_rate_matched.csv (per run), a3_rate_matched_summary.csv
A4 (review M14): decomposition of the report count, per site and level:
    every cycle -> separate SOD -> bundled SOD -> report-level SOD -> report-level RLS-T -> RLS-D,
    as % of reporting every cycle.   -> results/revision/a4_decomposition.csv (+ summary)
Usage: python src/analysis/revision_frontiers.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path("results/revision"); OUT.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(20261010)
P = ["T", "EC", "DO", "pH"]
r = pd.read_csv("results/phase2/results.csv")
per = r[(r.kind == "PERIODIC") & r.setting.isna()].set_index("dataset").reports_per_day
r["pct"] = 100 * r.reports_per_day / r.dataset.map(per)
usgs = r.dataset.str.startswith("USGS")


def boot(x, B=20000):
    x = np.asarray(x, float); i = rng.integers(0, len(x), (B, len(x)))
    return np.percentile(np.median(x[i], axis=1), [2.5, 97.5])


# ------------------------------------------------------------------ A3
rows = []
for ds in sorted(r[usgs].dataset.unique()):
    front = r[(r.dataset == ds) & (r.kind == "RLS-T") & (r["mode"] == "report")].sort_values("pct")
    lo, hi = front.pct.min(), front.pct.max()
    for kind in ["ADAPTIVEML", "ADAPTIVEML-RLS-T"]:
        for _, a in r[(r.dataset == ds) & (r.kind == kind) & (r["mode"] == "report")].iterrows():
            row = {"dataset": ds, "kind": kind, "alpha": a.alpha, "pct": a.pct, "inside": lo <= a.pct <= hi}
            ratios, rr = [], []
            for p in P:
                if pd.isna(a.get(f"{p}_max")):
                    continue
                f = front.dropna(subset=[f"{p}_max"])
                # bounded max error interpolated at the ADAPTIVEML rate (log-log, monotone in rate)
                bm = np.exp(np.interp(np.log(a.pct), np.log(f.pct), np.log(f[f"{p}_max"])))
                brm = np.exp(np.interp(np.log(a.pct), np.log(f.pct), np.log(f[f"{p}_rmse"])))
                row[f"{p}_ratio"] = a[f"{p}_max"] / bm
                ratios.append(a[f"{p}_max"] / bm); rr.append(a[f"{p}_rmse"] / brm)
            row["max_ratio_gmean"] = float(np.exp(np.mean(np.log(ratios))))
            row["rmse_ratio_mean"] = float(np.mean(rr))
            rows.append(row)
d = pd.DataFrame(rows)
d.to_csv(OUT / "a3_rate_matched.csv", index=False, float_format="%.6g")
din = d[d.inside]
s = []
for (kind, alpha), e in din.groupby(["kind", "alpha"]):
    persite = e.max_ratio_gmean.values
    lo, hi = boot(persite)
    s.append({"kind": kind, "alpha": alpha, "n_sites_inside": len(e), "n_sites_outside":
              int((~d[(d.kind == kind) & (d.alpha == alpha)].inside).sum()),
              "max_ratio_median": np.median(persite), "ci_lo": lo, "ci_hi": hi,
              "site_min": persite.min(), "site_max": persite.max(), "share_worse": (persite > 1).mean(),
              "rmse_ratio_median": np.median(e.rmse_ratio_mean)})
s = pd.DataFrame(s)
s.to_csv(OUT / "a3_rate_matched_summary.csv", index=False, float_format="%.6g")
print("A3: ADAPTIVEML vs bounded RLS-T front interpolated at the same report rate (USGS)")
print(s.to_string(index=False, float_format=lambda x: f"{x:.3g}"))
print(f"max-ratio over all inside runs: min {din.max_ratio_gmean.min():.2f}, "
      f"runs worse than bounded: {(din.max_ratio_gmean > 1).sum()}/{len(din)}")

# ------------------------------------------------------------------ A4
p3 = pd.read_csv("results/phase3/phase3.csv")
p3 = p3[(p3.det == 0) & (p3.tight == 0)]
rows = []
for ds in sorted(r[usgs].dataset.unique()) + ["InWaterSense n1"]:
    for lvl in range(1, 5):
        q = r[(r.dataset == ds) & (r.level == lvl)]
        g = lambda k, m: q[(q.kind == k) & (q["mode"] == m)].pct.item()
        rd = p3[(p3.dataset == ds) & (p3.level == lvl) & (p3.kind == "RLS-D")].reports_per_day.item()
        rows.append({"dataset": ds, "level": lvl, "every_cycle": 100.0,
                     "separate_SOD": g("SOD", "separate"), "bundled_SOD": g("SOD", "bundled"),
                     "report_SOD": g("SOD", "report"), "report_RLS-T": g("RLS-T", "report"),
                     "report_RLS-D": 100 * rd / per[ds]})
dd = pd.DataFrame(rows)
dd.to_csv(OUT / "a4_decomposition.csv", index=False, float_format="%.6g")
cols = ["separate_SOD", "bundled_SOD", "report_SOD", "report_RLS-T", "report_RLS-D"]
summ = []
for lvl, e in dd[dd.dataset.str.startswith("USGS")].groupby("level"):
    for c in cols:
        lo, hi = boot(e[c]); summ.append({"level": lvl, "stage": c, "median_pct": e[c].median(),
                                          "ci_lo": lo, "ci_hi": hi})
    # stage-to-stage savings, per site
    for a_, b_, lab in [("separate_SOD", "bundled_SOD", "bundling"), ("bundled_SOD", "report_SOD", "free-riding"),
                        ("report_SOD", "report_RLS-D", "prediction (RLS-D over SOD)")]:
        sv = 100 * (1 - e[b_] / e[a_]); lo, hi = boot(sv)
        summ.append({"level": lvl, "stage": f"saving: {lab}", "median_pct": sv.median(), "ci_lo": lo, "ci_hi": hi})
summ = pd.DataFrame(summ)
summ.to_csv(OUT / "a4_decomposition_summary.csv", index=False, float_format="%.6g")
print("\nA4: reports as % of every cycle (USGS medians, 95% site-bootstrap CI)")
print(summ.to_string(index=False, float_format=lambda x: f"{x:.1f}"))
