"""Revision A1: uncertainty, exact tests and multiplicity for every headline effect (review M4, M5, M15, M19).

Principle: the unit of replication is the SITE. Every effect is first reduced to one number per site,
the published median is re-derived from those numbers (asserted against the existing tables), and only
then is a site-level bootstrap CI added.

Outputs (results/revision/):
  a1_effects.csv        one row per headline effect: n sites, estimate, 95% CI, test, p (exact), Holm p
  a1_corr52.csv         diel share vs 1-h VAR skill: naive 52-obs p vs site-clustered bootstrap, by parameter
  a1_equal_accuracy.csv paired per-site equal-accuracy comparison (RLS-D L2 vs hourly periodic)

Bootstrap: percentile CI, B = 20000 resamples of sites with replacement, seed 20261010.
Wilcoxon p: exact (scipy method="exact"; no zero differences occur, asserted).
Spearman p: Monte-Carlo permutation p, (hits + 1) / (200000 + 1) and the asymptotic t-approximation that the draft quoted.
Holm: within pre-declared families (one family = one question asked at several tolerance levels).
Usage: python src/analysis/revision_stats.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr, wilcoxon

sys.path.insert(0, "src")
from sim.run_roc import split  # noqa: E402

OUT = Path("results/revision"); OUT.mkdir(parents=True, exist_ok=True)
B, SEED = 20000, 20261010
rng = np.random.default_rng(SEED)
P = ["T", "EC", "DO", "pH"]
INWS = "InWaterSense n1"
rows = []


def boot_ci(x, stat=np.median):
    x = np.asarray(x, float)
    idx = rng.integers(0, len(x), size=(B, len(x)))
    s = np.apply_along_axis(stat, 1, x[idx]) if stat is not np.median else np.median(x[idx], axis=1)
    return np.percentile(s, [2.5, 97.5])


def wilcox_exact(d):
    d = np.asarray(d, float)
    assert (d != 0).all(), "zero differences: exact Wilcoxon not applicable"
    return wilcoxon(d, method="exact").pvalue


def _rowcorr(X, Y):
    """Spearman rho per row of two (k, n) arrays (average ranks for ties); nan for constant rows"""
    RX, RY = rankdata(X, axis=1), rankdata(Y, axis=1)
    RX -= RX.mean(1, keepdims=True); RY -= RY.mean(1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        return (RX * RY).sum(1) / np.sqrt((RX ** 2).sum(1) * (RY ** 2).sum(1))


def spearman_perm(x, y, n=200000):
    """two-sided permutation p for Spearman rho, (count + 1) / (n + 1)"""
    x, y = np.asarray(x, float), np.asarray(y, float)
    obs = abs(spearmanr(x, y)[0]); hits = 0
    for _ in range(n // 20000):
        X = rng.permuted(np.tile(x, (20000, 1)), axis=1)
        hits += (np.abs(_rowcorr(X, np.tile(y, (20000, 1)))) >= obs - 1e-12).sum()
    return (hits + 1) / (n + 1)


def boot_rho(x, y, n=20000):
    x, y = np.asarray(x, float), np.asarray(y, float)
    idx = rng.integers(0, len(x), size=(n, len(x)))
    return np.nanpercentile(_rowcorr(x[idx], y[idx]), [2.5, 97.5])


def add(effect, family, level, values, estimate=None, ci=None, test="", p=np.nan, note=""):
    v = np.asarray(values, float)
    est = np.median(v) if estimate is None else estimate
    lo, hi = boot_ci(v) if ci is None else ci
    rows.append({"effect": effect, "family": family, "level": level, "n_sites": len(v),
                 "estimate": est, "ci_lo": lo, "ci_hi": hi, "site_min": v.min(), "site_max": v.max(),
                 "test": test, "p": p, "note": note})


def holm(ps):
    ps = np.asarray(ps, float); order = np.argsort(ps); m = len(ps); adj = np.empty(m); run = 0.0
    for rank, i in enumerate(order):
        run = max(run, (m - rank) * ps[i]); adj[i] = min(1.0, run)
    return adj


r = pd.read_csv("results/phase2/results.csv")
usgs = r.dataset.str.startswith("USGS")

# ---------------------------------------------------------------- E1: RLS-T vs SOD saving per level
t2 = pd.read_csv("results/phase2/tables/t2_rlst_vs_sod.csv")
for lvl in range(5):
    g = r[(r["mode"] == "report") & (r.level == lvl) & usgs].pivot_table(index="dataset", columns="kind",
                                                                          values="reports_per_day")
    gain = 100 * (1 - g["RLS-T"] / g["SOD"])
    assert abs(gain.median() - t2.loc[t2.level == lvl, "median_saving_pct"].item()) < 0.06
    add("RLS-T saving over SOD (%)", "E1 RLS-T vs SOD", lvl, gain,
        test="Wilcoxon signed-rank, exact, two-sided", p=wilcox_exact(g["RLS-T"] - g["SOD"]),
        note=f"wins {(gain > 0).sum()}/{len(gain)}")

# ---------------------------------------------------------------- E2: diel share vs saving (site level)
a = pd.read_csv("results/phase1/check_a_summary.csv", dtype={"site": str})
a["site"] = a.site.where(a.site.str.startswith("InWater"), "USGS " + a.site.str[:8])
diel = a.groupby("site").diel_share.mean()
wj = json.load(open("results/weija/phase1.json", encoding="utf-8"))["T+EC"]["diel_share"]
w2 = pd.read_csv("results/weija/phase2.csv")
t7 = pd.read_csv("results/phase2/tables/t7_predictability_link.csv")
link_p = []
for lvl in range(5):
    g = r[(r["mode"] == "report") & (r.level == lvl)].pivot_table(index="dataset", columns="kind",
                                                                    values="reports_per_day")
    gain = 100 * (1 - g["RLS-T"] / g["SOD"])
    d = pd.DataFrame({"diel": diel, "gain": gain}).dropna()
    gw = w2[(w2["mode"] == "report") & (w2.level == lvl)].set_index("kind").reports_per_day
    dw = pd.concat([d, pd.DataFrame({"diel": [np.mean(list(wj.values()))],
                                     "gain": [100 * (1 - gw["RLS-T"] / gw["SOD"])]}, index=["Weija"])])
    for scope, e in [("14 datasets", d), ("13 USGS", d.drop(INWS)), ("15 incl. Weija (held out)", dw)]:
        rho = spearmanr(e.diel, e.gain)[0]
        if scope != "15 incl. Weija (held out)":
            ref = t7[(t7.level == lvl) & (t7.sites == ("all" if scope == "14 datasets" else "USGS"))
                     & (t7.predictor == "diel")].rho.item()
            assert abs(rho - ref) < 0.006, (lvl, scope, rho, ref)
        lo, hi = boot_rho(e.diel.values, e.gain.values)
        p_perm = spearman_perm(e.diel.values, e.gain.values)
        rows.append({"effect": f"Spearman rho, diel share vs RLS-T saving [{scope}]", "family": "E2 diel link",
                     "level": lvl, "n_sites": len(e), "estimate": rho,
                     "ci_lo": lo, "ci_hi": hi,
                     "site_min": np.nan, "site_max": np.nan, "test": "permutation (200k)", "p": p_perm,
                     "note": f"asymptotic p = {spearmanr(e.diel, e.gain)[1]:.2g}"})

# ---------------------------------------------------------------- E3: report-level saving (per site)
t3 = pd.read_csv("results/phase2/tables/t3_rq2_decomposition.csv")
g = r[r.kind.isin(["SOD", "DBP", "RIDGE", "RLS-T"])].pivot_table(index=["dataset", "kind", "level"],
                                                                   columns="mode", values="reports_per_day").reset_index()
g["total"] = 100 * (1 - g.report / g.separate)
for lvl in range(5):
    u = g[(g.level == lvl) & g.dataset.str.startswith("USGS")]
    pooled = u.total.median()                                          # what the draft reports (site x method)
    assert abs(pooled - t3[(t3.group == "USGS") & (t3.level == lvl)].total.item()) < 0.06
    persite = u.groupby("dataset").total.median()                      # one number per site
    add("report-level saving over separate DPS (%)", "E3 report-level", lvl, persite,
        test="Wilcoxon signed-rank, exact (report vs separate, per-site medians)",
        p=wilcox_exact(-persite), note=f"draft value (median over 52 site x method) = {pooled:.1f}; "
                                        f"min over all 260 site x method x level cases computed separately")
print("min report-level saving over every USGS site x method x level:",
      round(g[g.dataset.str.startswith("USGS")].total.min(), 1))

# ---------------------------------------------------------------- E4: RLS-D gap to the per-site best (test sites)
tune, test = split()
p3 = pd.read_csv("results/phase3/phase3.csv")
b = p3[p3.det == 0].pivot_table(index=["dataset", "level"], columns="kind", values="reports_per_day")
b["oracle"] = b[["SOD", "RLS-T"]].min(axis=1)
gap = (100 * (b["RLS-D"] / b.oracle - 1)).reset_index(name="gap")
sodgap = (100 * (b["SOD"] / b.oracle - 1)).reset_index(name="gap")
for lvl in range(1, 5):
    v = gap[(gap.level == lvl) & gap.dataset.isin(test) & gap.dataset.str.startswith("USGS")].gap
    add("RLS-D gap to per-site best fixed predictor (%)", "E4 RLS-D gap", lvl, v,
        note="6 held-out USGS sites; small n, CI is wide by necessity")
    s = sodgap[(sodgap.level == lvl) & sodgap.dataset.isin(test) & sodgap.dataset.str.startswith("USGS")].gap
    add("SOD gap to per-site best fixed predictor (%)", "E4 RLS-D gap", lvl, s)

# ---------------------------------------------------------------- E5: ADAPTIVEML max-error ratio (per site)
t4 = pd.read_csv("results/phase2/tables/t4_adaptiveml_matched_all.csv")
t4u = t4[t4.dataset.str.startswith("USGS") & (t4.kind == "ADAPTIVEML")]
for alpha, e in t4u.groupby("alpha"):
    add("ADAPTIVEML / RLS-T max-error ratio (gmean over params)", "E5 ADAPTIVEML", f"alpha={alpha}",
        e.max_ratio_gmean, test="Wilcoxon exact on log ratio", p=wilcox_exact(np.log(e.max_ratio_gmean)),
        note=f"median |log rate mismatch| = {np.median(np.abs(np.log(e.pct_A / e.pct_B))):.3f}; "
             f"max = {np.max(np.abs(np.log(e.pct_A / e.pct_B))):.3f}")
    dcap = e.capA - e.capB
    add("event capture, ADAPTIVEML minus RLS-T", "E5b ADAPTIVEML capture", f"alpha={alpha}", dcap,
        test="Wilcoxon exact" if (dcap != 0).all() else "Wilcoxon (zeros present: zsplit)",
        p=wilcox_exact(dcap) if (dcap != 0).all() else wilcoxon(dcap, zero_method="zsplit").pvalue)

# ---------------------------------------------------------------- E6: lifetime gains (per site), 5 s sensing
L = pd.read_csv("results/phase4/lifetime.csv")
L = L[L.confirmed & L.battery.str.startswith("6600") & L.dataset.str.startswith("USGS") & (L.t_sense == "typical")]
for rad, e in L.groupby("radio"):
    ev = e[e.method == "PERIODIC every cycle"].set_index("dataset").lifetime_y
    rl = e[(e.method == "RLS-D") & (e.level == 2)].set_index("dataset").lifetime_y
    so = e[(e.method == "SOD") & (e.level == 2)].set_index("dataset").lifetime_y
    add("battery-life gain RLS-D L2 over every cycle (x)", "E6 lifetime", rad, rl / ev, note="modelled")
    add("battery-life gain RLS-D over SOD at L2 (%)", "E6 lifetime", rad, 100 * (rl / so - 1),
        test="Wilcoxon exact" if ((rl - so) != 0).all() else "", note="modelled",
        p=wilcox_exact(rl - so) if ((rl - so) != 0).all() else np.nan)

# ---------------------------------------------------------------- E7: equal accuracy, PAIRED per site (M19)
# Rule (stated in advance of looking at the per-site values): same site, same radio (N211 RAI, 5 s sensing);
# RLS-D at L2 vs PERIODIC 60 min; compare the per-site error ratio and the per-site lifetime ratio.
p2 = r
dL2 = p2[(p2.kind == "SOD") & (p2.level == 2) & (p2["mode"] == "report")].set_index("dataset")
ref = {"T": 0.2, "DO": 2.0, "pH": 0.1}


def nerr(row):
    return np.mean([row[f"{q}_max"] / (dL2.loc[row.dataset, "EC_delta"] if q == "EC" else ref[q])
                    for q in P if pd.notna(row.get(f"{q}_max"))])


life = L[L.radio == "NB-IoT N211 RAI"]
eq = []
for ds in sorted(p2[usgs].dataset.unique()):
    per = p2[(p2.dataset == ds) & (p2.kind == "PERIODIC") & (p2.setting == 60)].iloc[0]
    rd = p3[(p3.dataset == ds) & (p3.kind == "RLS-D") & (p3.det == 0) & (p3.level == 2)].iloc[0]
    eq.append({"dataset": ds, "err_periodic60": nerr(per), "err_rlsd_L2": nerr(rd),
               "life_periodic60": life[(life.dataset == ds) & (life.method == "PERIODIC 60 min")].lifetime_y.item(),
               "life_rlsd_L2": life[(life.dataset == ds) & (life.method == "RLS-D") & (life.level == 2)].lifetime_y.item()})
eq = pd.DataFrame(eq)
eq["err_ratio"] = eq.err_periodic60 / eq.err_rlsd_L2
eq["life_ratio"] = eq.life_rlsd_L2 / eq.life_periodic60
eq.round(3).to_csv(OUT / "a1_equal_accuracy.csv", index=False)
add("equal accuracy: periodic-60min / RLS-D-L2 worst-case error (paired per site)", "E7 equal accuracy", 2,
    eq.err_ratio, test="Wilcoxon exact on log ratio", p=wilcox_exact(np.log(eq.err_ratio)))
add("equal accuracy: RLS-D-L2 / periodic-60min lifetime (paired per site)", "E7 equal accuracy", 2,
    eq.life_ratio, note="modelled")
print("draft (ratio of medians): err 7.8x, life 4.62 vs 4.32 y;  paired per site: "
      f"median err ratio {eq.err_ratio.median():.1f}x, median life ratio {eq.life_ratio.median():.2f}")

# ---------------------------------------------------------------- Holm within families of tests
d = pd.DataFrame(rows)
d["p_holm"] = np.nan
for fam, e in d[d.p.notna()].groupby("family"):
    sub = e if fam != "E2 diel link" else e[e.effect.str.contains("14 datasets")]
    d.loc[sub.index, "p_holm"] = holm(sub.p.values)
d.to_csv(OUT / "a1_effects.csv", index=False, float_format="%.6g")

# ---------------------------------------------------------------- A1b: the 52-observation correlation (M5)
u = a[a.site.str.startswith("USGS")]
assert len(u) == 52
rho52, p52 = spearmanr(u.diel_share, u.skill_VAR)
sites = u.site.unique()
xs = np.stack([u[u.site == s].sort_values("param").diel_share.values for s in sites])   # (13, 4)
ys = np.stack([u[u.site == s].sort_values("param").skill_VAR.values for s in sites])
idx = rng.integers(0, len(sites), size=(B, len(sites)))
bs = _rowcorr(xs[idx].reshape(B, -1), ys[idx].reshape(B, -1))
c = [{"analysis": "pooled 52 site-parameters (draft)", "rho": rho52, "ci_lo": np.nan, "ci_hi": np.nan,
      "p": p52, "note": "naive: treats 52 observations as independent"},
     {"analysis": "pooled 52, site-clustered bootstrap", "rho": rho52, "ci_lo": np.percentile(bs, 2.5),
      "ci_hi": np.percentile(bs, 97.5), "p": np.nan, "note": f"{B} resamples of the 13 sites"}]
for q in ["T", "DO", "pH", "EC"]:
    e = u[u.param == q]
    lo, hi = boot_rho(e.diel_share.values, e.skill_VAR.values)
    c.append({"analysis": f"stratified: {q} only (13 sites)", "rho": spearmanr(e.diel_share, e.skill_VAR)[0],
              "ci_lo": lo, "ci_hi": hi,
              "p": spearman_perm(e.diel_share.values, e.skill_VAR.values), "note": "permutation p"})
m = u.groupby("site")[["diel_share", "skill_VAR"]].mean()
c.append({"analysis": "site means (13 sites, one obs per site)", "rho": spearmanr(m.diel_share, m.skill_VAR)[0],
          "ci_lo": np.nan, "ci_hi": np.nan, "p": spearman_perm(m.diel_share.values, m.skill_VAR.values),
          "note": "permutation p"})
pd.DataFrame(c).to_csv(OUT / "a1_corr52.csv", index=False, float_format="%.6g")

pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 70)
print(d.drop(columns=["note"]).to_string(index=False, float_format=lambda x: f"{x:.3g}"))
print(pd.DataFrame(c).to_string(index=False, float_format=lambda x: f"{x:.3g}"))
