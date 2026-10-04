"""Phase 2 analysis: every table and figure in the Phase 2 report, from results/phase2/results.csv.

Tables (results/phase2/tables/):
  t1_level2_pct_periodic.csv  reports as % of periodic (every cycle), report mode, level L2
  t2_rlst_vs_sod.csv          RLS-T vs SOD report savings per tolerance level (Wilcoxon, USGS)
  t3_rq2_decomposition.csv    separate -> bundled -> report-level savings (RQ2)
  t4_adaptiveml_matched.csv   ADAPTIVEML vs bounded RLS-T at the closest report rate (RQ3)
  t5_fixed_matched.csv        periodic / batching vs bounded RLS-T at the closest report rate
  t6_events.csv               event capture and delay per method and level
  t7_predictability_link.csv  Phase 1 predictability vs Phase 2 gain (Spearman)
Figures (results/phase2/figures/):
  fig4_pareto.png             reports vs normalised max error (USGS medians)
  fig5_link.png               diel share vs RLS-T saving over SOD (L2)
  fig6_events.png             event capture vs tolerance level

Usage: python src/analysis/phase2_analysis.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr, wilcoxon

RES = Path("results/phase2")
TAB, FIG = RES / "tables", RES / "figures"
TAB.mkdir(parents=True, exist_ok=True); FIG.mkdir(parents=True, exist_ok=True)
P = ["T", "EC", "DO", "pH"]
INWS = "InWaterSense n1"
BOUNDED = ["SOD", "DBP", "RIDGE", "RLS-T"]          # main bounded comparison set (LMS, RLS(0.98) in t1)

r = pd.read_csv(RES / "results.csv")
per = r[(r.kind == "PERIODIC") & r.setting.isna()].set_index("dataset").reports_per_day
r["pct"] = 100 * r.reports_per_day / r.dataset.map(per)
usgs = ~r.dataset.str.startswith("InWater")


def save(df, name):
    df.to_csv(TAB / name, index=False)
    print(f"\n== {name}\n{df.to_string(index=False)}")


def closest(B, pct):
    """row of B with report rate closest (in log ratio) to pct"""
    return B.iloc[(np.log(B.pct) - np.log(pct)).abs().argmin()]


def maxratios(a, b):
    return {f"{p}_maxratio": a[f"{p}_max"] / b[f"{p}_max"]
            for p in P if pd.notna(a.get(f"{p}_max")) and b[f"{p}_max"] > 0}


# ---- integrity
fx = r[r.kind.isin(["SOD", "LMS", "DBP", "RIDGE", "RLS", "RLS-T"])]
viol = fx[[f"{p}_viol" for p in P]].max().max()
assert viol == 0, f"bound violated: {viol}"
assert not r.duplicated(["dataset", "kind", "setting", "mode"]).any()
print(f"{len(r)} runs, {r.dataset.nunique()} datasets, max bound violation = {viol}")

# ---- t1: level-2 report cost
x = r[(r["mode"] == "report") & (r.level == 2)]
t1 = x.pivot_table(index="dataset", columns="kind", values="pct").round(1)
t1["best"] = t1.idxmin(axis=1)
t1 = t1.reset_index()
save(t1, "t1_level2_pct_periodic.csv")

# ---- t2: RLS-T vs SOD per level
rows = []
for lvl in range(5):
    g = r[(r["mode"] == "report") & (r.level == lvl) & usgs].pivot_table(
        index="dataset", columns="kind", values="reports_per_day")
    gain = 100 * (1 - g["RLS-T"] / g["SOD"])
    inws = r[(r["mode"] == "report") & (r.level == lvl) & (r.dataset == INWS)].set_index("kind").reports_per_day
    rows.append({"level": lvl, "median_saving_pct": round(gain.median(), 1),
                 "wins": f"{(gain > 0).sum()}/{len(gain)}",
                 "wilcoxon_p": wilcoxon(g["RLS-T"], g["SOD"]).pvalue,
                 "inws_saving_pct": round(100 * (1 - inws["RLS-T"] / inws["SOD"]), 1)})
save(pd.DataFrame(rows), "t2_rlst_vs_sod.csv")

# ---- t3: RQ2 decomposition
g = r[r.kind.isin(BOUNDED)].pivot_table(index=["dataset", "kind", "level"], columns="mode",
                                         values="reports_per_day").reset_index()
g["bundling"] = 100 * (1 - g.bundled / g.separate)
g["free_riding"] = 100 * (1 - g.report / g.bundled)
g["total"] = 100 * (1 - g.report / g.separate)
g["group"] = np.where(g.dataset == INWS, "InWaterSense", "USGS")
t3 = g.groupby(["group", "level"])[["bundling", "free_riding", "total"]].median().round(1).reset_index()
u = g[g.group == "USGS"]
t3.attrs = {}
save(t3, "t3_rq2_decomposition.csv")
print(f"free-riding positive in {(u.free_riding > 0).sum()}/{len(u)} USGS cases, "
      f"Wilcoxon p = {wilcoxon(u.report, u.bundled).pvalue:.1e}")

# ---- t4: ADAPTIVEML vs RLS-T, matched report rate (report mode)
rows = []
for kind in ["ADAPTIVEML", "ADAPTIVEML-RLS-T"]:
    for _, a in r[(r.kind == kind) & (r["mode"] == "report")].iterrows():
        b = closest(r[(r.kind == "RLS-T") & (r["mode"] == "report") & (r.dataset == a.dataset)], a.pct)
        row = {"kind": kind, "alpha": a.alpha, "dataset": a.dataset, "pct_A": a.pct, "pct_B": b.pct,
               "capA": a.event_capture, "capB": b.event_capture}
        row.update(maxratios(a, b))
        row["rmse_ratio"] = np.nanmean([a[f"{p}_rmse"] / b[f"{p}_rmse"] for p in P
                                        if pd.notna(a.get(f"{p}_rmse")) and b[f"{p}_rmse"] > 0])
        rows.append(row)
d = pd.DataFrame(rows)
d["max_ratio_gmean"] = np.exp(np.log(d.filter(like="_maxratio")).mean(axis=1))
d.to_csv(TAB / "t4_adaptiveml_matched_all.csv", index=False)
du = d[~d.dataset.str.startswith("InWater")]
t4 = du.groupby(["kind", "alpha"]).agg(
    reports_A=("pct_A", "median"), reports_B=("pct_B", "median"),
    T=("T_maxratio", "median"), EC=("EC_maxratio", "median"), DO=("DO_maxratio", "median"),
    pH=("pH_maxratio", "median"), max_gmean=("max_ratio_gmean", "median"),
    share_worse=("max_ratio_gmean", lambda s: (s > 1).mean()),
    rmse=("rmse_ratio", "median"), captureA=("capA", "median"), captureB=("capB", "median")
).round(2).reset_index()
save(t4, "t4_adaptiveml_matched.csv")

# ---- t5: periodic / batching vs RLS-T, matched
rows = []
for kind in ["PERIODIC", "BATCH"]:
    for _, a in r[(r.kind == kind) & r.setting.notna()].iterrows():
        b = closest(r[(r.kind == "RLS-T") & (r["mode"] == "report") & (r.dataset == a.dataset)], a.pct)
        row = {"kind": kind, "every_min": a.setting, "dataset": a.dataset, "pct_A": a.pct, "pct_B": b.pct,
               "capA": a.event_capture, "capB": b.event_capture, "delA": a.event_delay_med_min,
               "delB": b.event_delay_med_min, "data_delay": a.mean_delay_min}
        row.update(maxratios(a, b))
        rows.append(row)
d = pd.DataFrame(rows)
du = d[~d.dataset.str.startswith("InWater")]
t5 = du.groupby(["kind", "every_min"]).agg(
    reports_A=("pct_A", "median"), reports_B=("pct_B", "median"),
    T=("T_maxratio", "median"), EC=("EC_maxratio", "median"), DO=("DO_maxratio", "median"),
    pH=("pH_maxratio", "median"), captureA=("capA", "median"), captureB=("capB", "median"),
    event_delayA=("delA", "median"), event_delayB=("delB", "median"), batch_data_delay=("data_delay", "median")
).round(2).reset_index()
save(t5, "t5_fixed_matched.csv")
print("(BATCH max-error ratio is 0 by construction: exact data, delivered late)")

# ---- t6: events
k = r[r.kind.isin(BOUNDED + ["LMS"]) & (r["mode"] == "report") & usgs]
t6 = k.groupby(["kind", "level"]).agg(capture=("event_capture", "median"),
                                      delay_med=("event_delay_med_min", "median"),
                                      delay_p90=("event_delay_p90_min", "median"),
                                      pct=("pct", "median")).round(3).reset_index()
save(t6, "t6_events.csv")

# ---- t7: Phase 1 predictability vs Phase 2 gain
a = pd.read_csv("results/phase1/check_a_summary.csv", dtype={"site": str})
a["site"] = a.site.where(a.site.str.startswith("InWater"), "USGS " + a.site.str[:8])
s = a.groupby("site").agg(diel=("diel_share", "mean"), skill=("skill_AR", "mean"))
rows, link = [], {}
for lvl in range(5):
    g = r[(r["mode"] == "report") & (r.level == lvl)].pivot_table(index="dataset", columns="kind",
                                                                    values="reports_per_day")
    dd = s.join((100 * (1 - g["RLS-T"] / g["SOD"])).rename("gain")).dropna()
    link[lvl] = dd
    for scope, e in [("all", dd), ("USGS", dd.drop(INWS))]:
        for m in ["diel", "skill"]:
            rho, p = spearmanr(e[m], e.gain)
            loo = min(spearmanr(e.drop(i)[m], e.drop(i).gain)[0] for i in e.index)
            rows.append({"level": lvl, "sites": scope, "n": len(e), "predictor": m,
                         "rho": round(rho, 2), "p": round(p, 4), "loo_min_rho": round(loo, 2)})
save(pd.DataFrame(rows), "t7_predictability_link.csv")

# ---- fig4: Pareto (USGS medians): % of periodic vs max error / L2 delta (mean over parameters)
LEVELS2 = {"T": 0.2, "DO": 2, "pH": 0.1}


def norm_err(row):
    """max error in units of the L2 tolerance, averaged over parameters (EC uses its own L2 delta)"""
    v = []
    for p in P:
        if pd.isna(row.get(f"{p}_max")):
            continue
        ref = LEVELS2.get(p)
        if p == "EC":
            dEC = r[(r.dataset == row.dataset) & (r.kind == "SOD") & (r.level == 2)].EC_delta.iloc[0]
            ref = dEC
        v.append(row[f"{p}_max"] / ref)
    return np.mean(v)


cur = {"SOD (bounded)": (r.kind == "SOD") & (r["mode"] == "report"),
       "RLS-T (bounded)": (r.kind == "RLS-T") & (r["mode"] == "report"),
       "ADAPTIVEML": (r.kind == "ADAPTIVEML") & (r["mode"] == "report"),
       "Periodic": (r.kind == "PERIODIC") & r.setting.notna()}
key = {"SOD (bounded)": "level", "RLS-T (bounded)": "level", "ADAPTIVEML": "alpha", "Periodic": "setting"}
fig, ax = plt.subplots(figsize=(6.2, 4.4))
for lab, m in cur.items():
    e = r[m & usgs].copy()
    e["err"] = e.apply(norm_err, axis=1)
    pts = e.groupby(key[lab])[["pct", "err"]].median().sort_values("pct")
    ax.plot(pts.pct, pts.err, "o-", label=lab)
ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlabel("reports, % of reporting every cycle"); ax.set_ylabel("max error / L2 tolerance (mean over parameters)")
ax.set_title("Fewer reports AND a guaranteed error bound\n(medians over 13 USGS rivers)", fontsize=10)
ax.legend(frameon=False); fig.tight_layout(); fig.savefig(FIG / "fig4_pareto.png", dpi=160)

# ---- fig5: link
dd = link[2]
fig, ax = plt.subplots(figsize=(6, 4.2))
ax.scatter(dd.drop(INWS).diel, dd.drop(INWS).gain, s=40, c="#1b9e77", label="USGS rivers")
ax.scatter(dd.loc[INWS, "diel"], dd.loc[INWS, "gain"], marker="X", s=100, c="#d95f02", edgecolor="k",
           label="InWaterSense")
ax.axhline(0, c="grey", lw=.8)
rho = spearmanr(dd.diel, dd.gain)[0]
ax.set_xlabel("diel variance share (Phase 1, mean over parameters)")
ax.set_ylabel("RLS-T report saving over send-on-delta, %")
ax.set_title(f"Prediction pays where the day-night cycle dominates\n(L2 tolerances, Spearman {rho:.2f})",
             fontsize=10)
ax.legend(frameon=False); fig.tight_layout(); fig.savefig(FIG / "fig5_link.png", dpi=160)

# ---- fig6: events
fig, ax = plt.subplots(figsize=(6, 4))
for kind, e in t6.groupby("kind"):
    ax.plot(e.level, e.capture, "o-", label=kind)
ax.set_xticks(range(5)); ax.set_xticklabels([f"L{i}" for i in range(5)])
ax.set_xlabel("tolerance level"); ax.set_ylabel("events reported while ongoing (median share)")
ax.set_title("Loose tolerances miss events, whatever the predictor\n(13 USGS rivers)", fontsize=10)
ax.legend(frameon=False); fig.tight_layout(); fig.savefig(FIG / "fig6_events.png", dpi=160)
print("\nfigures saved to", FIG)
