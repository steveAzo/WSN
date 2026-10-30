"""Supplementary tables for draft v0.2, generated from the result files (no hand transcription).
-> papers/paper1/draft/supp_tables.tex   (input by supplement.tex)
Tables are written in the order the main text first cites them (ORDER below), so S1, S2, ... follow the text.
The main text cites them with \\ref via xr; section numbers here come from main.aux (\\ref{main-...}).
Usage: python src/analysis/revision_supplement.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

REV = Path("results/revision")
OUT = Path("papers/paper1/draft/supp_tables.tex")
# order of first citation in the main text (sec_data, sec_methods, sec_results)
ORDER = ["tab:s-flow", "tab:s-prov", "tab:s-effects", "tab:s-l2", "tab:s-corr", "tab:s-ablation",
         "tab:s-detector", "tab:s-detect", "tab:s-loss", "tab:s-tornado"]
T = {}


def tex(s):
    return str(s).replace("%", r"\%").replace("&", r"\&").replace("_", r"\_").replace("#", r"\#")


def table(caption, label, cols, rows, align, note=None, size=r"\scriptsize", colsep="3pt"):
    L = T[label] = []
    L.append(r"\begin{table*}[!htbp]\centering")
    L.append(rf"\caption{{{caption}}}\label{{{label}}}{size}")
    L.append(r"\setlength{\tabcolsep}{" + colsep + r"}\begin{tabular}{@{}" + align + r"@{}}\toprule")
    L.append(" & ".join(cols) + r" \\ \midrule")
    for r in rows:
        L.append(" & ".join(r) + r" \\")
    L.append(r"\bottomrule\end{tabular}")
    if note:
        L.append(rf"\\[2pt]\parbox{{0.95\textwidth}}{{\footnotesize {note}}}")
    L.append(r"\end{table*}")


# data flow (tab:s-flow)
d = pd.read_csv(REV / "a10_dataflow.csv")
rows = []
for _, r in d.iterrows():
    rows.append([tex(r.dataset), f"{int(r.raw_values):,}", "--" if pd.isna(r.approved_values) else f"{int(r.approved_values):,}",
                 f"{int(r.timestamps):,}", f"{int(r.complete_cycles):,}", f"{int(r.sim_cycles):,}", str(int(r.sim_segments)),
                 tex(r.params_simulated), f"{r.train_data_days:.1f}", str(int(r.test_span_days))])
table("Data-quality flow per dataset. USGS: raw and approved values (all parameters), time stamps, cycles with all four "
      "parameters; InWaterSense: raw rows, re-joined cycles and complete cycles (pH excluded from simulation, 4{,}815 "
      "plausibility failures). Simulated cycles are complete for the simulated parameters; segments split at gaps over 60 min.",
      "tab:s-flow", ["Dataset", "Raw", "Approved", "Stamps/cycles", "Complete", "Simulated", "Segm.", "Parameters",
                     "Train (d)", "Test (d)"], rows, "lrrrrrrlrr", colsep="1.5pt")

# provenance (tab:s-prov) (hand-curated content lives in A2_PROVENANCE.md; reproduced here as a table)
prov = [
    ("Train/test split", "first 20\\% by time", "design", "none", "yes"),
    ("Tuning/test sites", "every 2nd USGS site by ID", "design rule", "none", "yes"),
    ("Tolerances L0--L4", "Sec.~\\ref{main-sec:protocol}", "resolution to coarse monitoring", "none",
     "yes; L2 as reference not pre-declared"),
    ("LMS", "$N=4$, $\\mu=1/(100E_x)$", "Santini \\& R\\\"omer", "none", "yes"),
    ("DBP", "$m=\\max(4,60/\\Delta t)$, $l=3$", "Raza et al.", "none", "yes"),
    ("Ridge", "$w=24$, $\\lambda=1$", "Kangethe et al.", "none", "yes"),
    ("RLS", "$\\gamma=0.98$, $\\mathbf{P}_0=10\\mathbf{I}$", "Kangethe et al.", "none", "yes"),
    ("RLS-T", "$\\gamma=0.999$", "ours", "one tuning site (01458500)", "yes"),
    ("Trace bound", "$\\mathrm{tr}\\,\\mathbf{P}\\le\\rho w$", "covariance bounding", "none", "yes"),
    ("RLS-D mechanism", "change model, damping, repair", "diagnosis of baseline runs", "all datasets (diagnosis)",
     "designed after the baseline runs"),
    ("RLS-D $\\phi$", "0.97", "written rule", "7 tuning sites ($\\rho=10$); re-checked at $\\rho=0.01$", "yes"),
    ("RLS-D $\\rho$", "0.01", "development fix (resync transients)", "development runs", "not by a rule"),
    ("Detector (chosen)", "lag 120 min, $k=3$, $H=8$, $c=6$", "written rule", "7 tuning sites", "yes"),
    ("Detector (sensitive)", "lag 120 min, $k=2$, $H=4$, $c=5$", "grid point", "first detector grid sweep", "not by a rule"),
    ("Heartbeat, retries", "6/24 h; 2", "design", "none", "yes"),
    ("ADAPTIVEML $\\alpha$", "0.5--3", "sweep around the original default of 1", "none", "yes"),
    ("Energy parameters", "Sec.~\\ref{main-sec:energy}", "measured profiles, datasheet", "none", "yes; $t_\\mathrm{sense}$ swept"),
    ("Injected events", "3/5/8$\\sigma$, 1/3/6 h", "design", "none", "yes"),
]
table("Design provenance: every parameter, its value, source, the data used to choose it, and whether it was fixed "
      "before test-site results were seen.", "tab:s-prov", ["Item", "Value", "Source", "Data used", "Fixed before test?"],
      [list(p) for p in prov], "lllp{4.2cm}p{3.6cm}")

# correlation analyses (tab:s-corr) (pseudo-replication)
c = pd.read_csv(REV / "a1_corr52.csv")
c["analysis"] = c.analysis.replace({"pooled 52 site-parameters (draft)": "pooled 52 site-parameters"})
rows = [[tex(r.analysis), f"{r.rho:.2f}", "--" if pd.isna(r.ci_lo) else f"[{r.ci_lo:.2f}, {r.ci_hi:.2f}]",
         "--" if pd.isna(r.p) else f"{r.p:.2g}"] for _, r in c.iterrows()]
table("Diel share vs.\\ out-of-sample VAR skill over persistence (1 h), USGS. The pooled $p$ treats the 52 "
      "site--parameters as independent; the site-clustered interval resamples sites.", "tab:s-corr",
      ["Analysis", "$\\rho$", "95\\% CI", "$p$"], rows, "lccc")

# energy sensitivity (tab:s-tornado)
t = pd.read_csv(REV / "a7_tornado.csv")
rows = []
for rad in ["NB-IoT N211 RAI", "LoRaWAN SF12"]:
    for _, r in t[t.radio == rad].iterrows():
        rows.append([tex(rad), tex(r.factor), tex(r.setting), f"{r.life_low:.2f} / {r.life_high:.2f}",
                     f"{r.gain_low:.2f} / {r.gain_high:.2f}"])
table("One-at-a-time energy sensitivity at median USGS rates, L2 (base: N211 RAI 4.57 y, gain 1.78; SF12 3.18 y, gain "
      "2.16). Columns give RLS-D battery life (years) and its gain over reporting every cycle at the low / high setting.",
      "tab:s-tornado", ["Radio", "Input", "Low / high setting", "Life (y)", "Gain"], rows, "lllcc")

# headline effects (tab:s-effects)
e = pd.read_csv(REV / "a1_effects.csv")
rows = []
for _, r in e.iterrows():
    rows.append([tex(r.effect), tex(r.level), str(int(r.n_sites)), f"{r.estimate:.3g}", f"[{r.ci_lo:.3g}, {r.ci_hi:.3g}]",
                 "--" if pd.isna(r.p) else f"{r.p:.2g}", "--" if pd.isna(r.p_holm) else f"{r.p_holm:.2g}"])
table("All headline effects with site-bootstrap 95\\% intervals, exact Wilcoxon or permutation $p$-values, and Holm "
      "adjustment within families.", "tab:s-effects", ["Effect", "Level", "$n$", "Est.", "95\\% CI", "$p$", "Holm"],
      rows, "p{7.2cm}lrrrrr", size=r"\tiny")

# ablation (tab:s-ablation), all variants
a = pd.read_csv(REV / "a2_ablation_summary.csv")
w = a.pivot_table(index="variant", columns=["set", "level"], values="median_gap_pct")
order = ["SOD", "RLS-T", "CHG", "CHG+DAMP", "CHG+REPAIR", "RLS-D", "RLS-D(rho=10)", "RLS-D(phi=0.9)", "RLS-D(phi=0.8)"]
cols = [(s, l) for s in ["test", "tune", "InWaterSense"] for l in (1, 2, 3, 4)]
rows = [[tex(v)] + [f"{w.loc[v, c]:+.1f}" for c in cols] for v in order]
table("RLS-D ablation: median gap to the per-site best fixed predictor (\\%), by site set and level.", "tab:s-ablation",
      ["Variant"] + [f"{'Te' if s == 'test' else 'Tu' if s == 'tune' else 'IW'} L{l}" for s, l in cols], rows, "l" + "r" * 12)

# detector operating points (tab:s-detector)
o = pd.read_csv(REV / "a5_operating_points.csv")
o = o[(o.set == "test") & (o.amp_sigma == 5)]
rows = [[tex(r.config), tex(r["shape"]), str(int(r.dur_min)), str(int(r.n_events)), f"{r.detect_mean:.2f}",
         f"{r.detect_min:.2f}--{r.detect_max:.2f}", f"{r.fa_per30d_median:.1f}",
         f"{r.delay_med_min_sites_median:.0f} ({r.delay_med_min_sites_min:.0f}--{r.delay_med_min_sites_max:.0f})"]
        for _, r in o.iterrows()]
table("Detector on held-out sites (6 USGS + InWaterSense), injected 5$\\sigma$ events: number of events, detection "
      "(mean, range over sites), false alarms per parameter per 30 days, and the median detection delay in minutes "
      "(median and range over sites).", "tab:s-detector",
      ["Configuration", "Shape", "Dur. (min)", "Events", "Detect", "Range", "FA/30 d", "Delay (min)"], rows, "llrrrrrr")

# bounded methods at L2 (tab:s-l2) (moved from the main text)
t1 = pd.read_csv("results/phase2/tables/t1_level2_pct_periodic.csv")
u1 = t1[t1.dataset.str.startswith("USGS")]; i1 = t1[t1.dataset.str.startswith("InWater")].iloc[0]
names = {"SOD": "SOD", "DBP": "DBP", "RIDGE": "Ridge", "RLS-T": "RLS-T ($\\gamma=0.999$)", "RLS": "RLS ($\\gamma=0.98$)",
         "LMS": "LMS (Santini step size)"}
rows = [[names[k], f"{u1[k].median():.1f} [{u1[k].min():.1f}, {u1[k].max():.1f}]", f"{i1[k]:.1f}"] for k in names]
table("Reports as \\% of reporting every cycle, report-level mode, L2. USGS: median [range] over 13 sites.",
      "tab:s-l2", ["Method", "USGS", "InWaterSense"], rows, "lcc")

# unconfirmed-uplink (tab:s-loss) protocol cost (moved from the main text)
l = pd.read_csv("results/phase3/tables/p3_loss.csv")
q = l[(l.loss == 0.01) & l.protocol.str.startswith("unconfirmed")]
rows = []
for kind in ["SOD", "RIDGE-D", "RLS-D", "RLS-T"]:
    r24 = q[(q.kind == kind) & q.protocol.str.endswith("24 h")].iloc[0]; r6 = q[(q.kind == kind) & q.protocol.str.endswith("6 h")].iloc[0]
    rows.append([kind, f"+{r24.tx_overhead_pct:.1f}\\%", f"{r24.flagged_pct:.1f}\\%", f"+{r6.tx_overhead_pct:.1f}\\%",
                 f"{r6.flagged_pct:.1f}\\%", str(int(q[q.kind == kind].unflagged_viol.sum()))])
table("Unconfirmed-uplink protocol at L2 and 1\\% loss: extra transmissions (including heartbeats) and share of time "
      "flagged (medians over 14 datasets and 3 seeds), and unflagged violations (total).", "tab:s-loss",
      ["Predictor", "Extra (24 h)", "Flagged (24 h)", "Extra (6 h)", "Flagged (6 h)", "Unflagged"], rows, "lccccc")

# detect vs tighten (tab:s-detect) (moved from the main text)
dv = pd.read_csv("results/phase3/tables/p3_detect_vs_tighten.csv").set_index("config")
fa = pd.read_csv(REV / "a5_operating_points.csv")
fa = fa[fa.set == "test"].groupby("config").fa_per30d_median.first()
lab = {"RLS-D L3 (tighten)": ("RLS-D, L3 (tighten)", "--"), "RLS-D L4": ("RLS-D, L4", "--"),
       "RLS-D+DET1 L4": ("RLS-D + detector, L4", f"{fa['chosen (k=3, H=8, c=6)']:.1f}"),
       "RLS-D+DET2 L4": ("RLS-D + sensitive detector, L4", f"{fa['sensitive (k=2, H=4, c=5)']:.1f}")}
rows = [[lab[k][0], f"{dv.loc[k, 'reports']:.2f}", f"{dv.loc[k, 'step']:.2f}", f"{dv.loc[k, 'ramp']:.2f}",
         f"{dv.loc[k, 'checkB']:.2f}", lab[k][1]] for k in lab]
table("Protecting events at loose tolerance: reports per day and share of injected 3-h 5$\\sigma$ steps and ramps and of "
      "reference events reported while ongoing (medians over 13 USGS sites), and false alarms per parameter per 30 days "
      "(FA, six held-out sites).", "tab:s-detect", ["Configuration", "Reports/day", "Steps", "Ramps", "Reference", "FA"],
      rows, "lccccc")

assert sorted(ORDER) == sorted(T), "ORDER must list every table exactly once"
L = []
for label in ORDER:
    if label == "tab:s-effects":  # long \tiny table: start it on a fresh page
        L.append(r"\clearpage")
    L += T[label]
OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
print("wrote", OUT, len(L), "lines")
