"""Revision figures for draft v0.2 (review: Figs 1-7 comments, M14, M13, M9; grayscale-safe).

Palette: validated categorical slots (dataviz skill reference palette, light mode):
  blue #2a78d6, orange #eb6834, aqua #1baf7a (+ yellow #eda100 for 4-series line charts).
  validate_palette.js: all hard checks pass (3 slots --pairs all; 4 slots adjacent); aqua/yellow < 3:1
  contrast -> every series also has its own marker / line style and a direct label (print, CVD).
Outputs (vector PDF) -> papers/paper1/draft/figures/v2_*.pdf
Usage: python src/analysis/revision_figures.py [name ...]
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr, theilslopes

OUT = Path("papers/paper1/draft/figures"); OUT.mkdir(parents=True, exist_ok=True)
REV = Path("results/revision")
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#8a8984", "#e4e3df"
plt.rcParams.update({"font.size": 8, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.linewidth": 0.8, "lines.linewidth": 2.0, "lines.markersize": 6,
                     "legend.frameon": False, "legend.fontsize": 7.5, "pdf.fonttype": 42,
                     "savefig.bbox": "tight", "savefig.pad_inches": 0.02})
W1 = 3.45                                                  # IEEE single column (in)
rng = np.random.default_rng(20261010)


def boot(x, B=20000):
    x = np.asarray(x, float); i = rng.integers(0, len(x), (B, len(x)))
    return np.percentile(np.median(x[i], axis=1), [2.5, 97.5])


def save(fig, name):
    fig.savefig(OUT / f"{name}.pdf"); fig.savefig(OUT / f"{name}.png", dpi=200); plt.close(fig)
    print("saved", name)


# ---------------------------------------------------------------- decomposition (M14)
def decomposition():
    d = pd.read_csv(REV / "a4_decomposition.csv")
    u = d[d.dataset.str.startswith("USGS")]
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.16, 2.5), gridspec_kw={"width_ratios": [1.25, 1]})
    # (a) L2 path for every site (thin, muted) and the median (bold), log scale
    stages = ["every_cycle", "separate_SOD", "bundled_SOD", "report_SOD", "report_RLS-D"]
    labels = ["every\ncycle", "separate\n(SOD)", "bundled\n(SOD)", "report-level\n(SOD)", "report-level\n(RLS-D)"]
    e = u[u.level == 2]
    x = np.arange(len(stages))
    for _, row in e.iterrows():
        a.plot(x, row[stages].values, color=GRID, lw=1, zorder=1)
    med = e[stages].median()
    lo = [boot(e[s])[0] for s in stages]; hi = [boot(e[s])[1] for s in stages]
    a.plot(x[:4], med.values[:4], color=BLUE, marker="o", zorder=3, label="accounting structure")
    a.plot(x[3:], med.values[3:], color=ORANGE, marker="s", ls="--", zorder=3, label="prediction")
    a.vlines(x, lo, hi, color=INK2, lw=1, zorder=2)
    for xi, m in zip(x, med.values):
        a.annotate(f"{m:.0f}%", (xi, m), xytext=(5, 4), textcoords="offset points", fontsize=7, color=INK)
    a.set_yscale("log"); a.set_yticks([10, 20, 50, 100]); a.set_yticklabels(["10", "20", "50", "100"])
    a.set_xticks(x); a.set_xticklabels(labels, fontsize=6.8)
    a.set_ylabel("reports, % of every cycle (L2)")
    a.legend(loc="lower left"); a.grid(axis="y", color=GRID, lw=0.6)
    a.set_title("(a) one site per grey line; median and 95% CI", fontsize=8, loc="left", color=INK, pad=16)
    # (b) stage savings by level (median, 95% CI), three series
    s = pd.read_csv(REV / "a4_decomposition_summary.csv")
    s = s[s.stage.str.startswith("saving")]
    ser = [("saving: bundling", "bundling", BLUE, "o", "-"), ("saving: free-riding", "free riding", AQUA, "^", ":"),
           ("saving: prediction (RLS-D over SOD)", "prediction", ORANGE, "s", "--")]
    for k, (st, lab, col, mk, ls) in enumerate(ser):
        q = s[s.stage == st].sort_values("level")
        xx = q.level.values + (k - 1) * 0.12
        b.errorbar(xx, q.median_pct, yerr=[q.median_pct - q.ci_lo, q.ci_hi - q.median_pct], color=col, marker=mk,
                   ls=ls, capsize=0, elinewidth=1, label=lab)
    b.axhline(0, color=INK2, lw=0.8)
    b.set_xticks([1, 2, 3, 4]); b.set_xticklabels(["L1", "L2", "L3", "L4"])
    b.set_ylabel("reports saved by the stage (%)"); b.grid(axis="y", color=GRID, lw=0.6)
    b.set_ylim(-9, 40)
    b.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3, fontsize=7, handlelength=2.2,
             columnspacing=1.0, borderaxespad=0.2)
    b.set_title("(b) savings per stage, by tolerance", fontsize=8, loc="left", color=INK, pad=16)
    fig.tight_layout(w_pad=1.5)
    save(fig, "v2_decomposition")


# ---------------------------------------------------------------- diel link with boundary cases (Fig. 2)
def link():
    """one point per dataset; identities in a single legend, statistics in the caption (no free text)"""
    o = pd.read_csv(REV / "a9_smoothness.csv")
    fig, ax = plt.subplots(figsize=(W1, 2.5))
    us = o[o.dataset.str.startswith("USGS")]
    core = o[~o.dataset.eq("Weija")]
    sl, ic, _, _ = theilslopes(core.saving_L2, core.diel_share_mean)
    xs = np.linspace(0, 0.6, 50)
    ax.axhline(0, color=INK2, lw=0.7, zorder=1)
    ax.plot(xs, ic + sl * xs, color=MUTED, lw=1.2, ls="--", zorder=1, label="Theil-Sen fit (14 datasets)")
    ax.scatter(us.diel_share_mean, us.saving_L2, color=BLUE, marker="o", s=30, edgecolor="white", lw=0.8,
               zorder=3, label="USGS rivers and streams (13)")
    i = o[o.dataset.str.startswith("InWater")]; w = o[o.dataset == "Weija"]
    ax.scatter(i.diel_share_mean, i.saving_L2, color=ORANGE, marker="s", s=34, edgecolor="white", lw=0.8, zorder=3,
               label="InWaterSense (Kosovo)")
    ax.scatter(w.diel_share_mean, w.saving_L2, color=AQUA, marker="^", s=44, edgecolor=INK2, lw=0.8, zorder=3,
               label="Weija (Ghana, held out)")
    ax.set_xlabel("diel variance share (site mean over parameters)")
    ax.set_ylabel("RLS-T saving over SOD at L2 (%)")
    ax.set_xlim(-0.01, 0.6); ax.set_ylim(-20, 64); ax.set_yticks([-20, -10, 0, 10, 20, 30, 40, 50]); ax.grid(color=GRID, lw=0.6)
    ax.legend(loc="upper left", fontsize=6.5, handletextpad=0.4, borderaxespad=0.3)
    fig.tight_layout(); save(fig, "v2_link")


# ---------------------------------------------------------------- rate-matched ADAPTIVEML (Fig. 3, M13)
def ratematched():
    r = pd.read_csv("results/phase2/results.csv")
    per = r[(r.kind == "PERIODIC") & r.setting.isna()].set_index("dataset").reports_per_day
    r["pct"] = 100 * r.reports_per_day / r.dataset.map(per)
    u = r[r.dataset.str.startswith("USGS")].copy()
    dL2 = u[(u.kind == "SOD") & (u.level == 2) & (u["mode"] == "report")].set_index("dataset").EC_delta
    ref = {"T": 0.2, "DO": 2.0, "pH": 0.1}

    def nerr(row):
        return np.mean([row[f"{q}_max"] / (dL2[row.dataset] if q == "EC" else ref[q])
                        for q in ["T", "EC", "DO", "pH"] if pd.notna(row.get(f"{q}_max"))])
    u["err"] = u.apply(nerr, axis=1)
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.16, 2.5), gridspec_kw={"width_ratios": [1.2, 1]})
    cur = [("RLS-T (bounded)", (u.kind == "RLS-T") & (u["mode"] == "report"), "level", BLUE, "o", "-"),
           ("SOD (bounded)", (u.kind == "SOD") & (u["mode"] == "report"), "level", AQUA, "^", ":"),
           ("ADAPTIVEML", (u.kind == "ADAPTIVEML") & (u["mode"] == "report"), "alpha", ORANGE, "s", "--"),
           ("periodic", (u.kind == "PERIODIC") & u.setting.notna(), "setting", YELLOW, "D", "-.")]
    for lab, m, key, col, mk, ls in cur:
        pts = u[m].groupby(key)[["pct", "err"]].median().sort_values("pct")
        a.plot(pts.pct, pts.err, color=col, marker=mk, ls=ls, label=lab)
    a.set_xscale("log"); a.set_yscale("log")
    a.set_xlabel("reports, % of every cycle"); a.set_ylabel("worst-case error / L2 tolerance")
    a.grid(color=GRID, lw=0.6); a.legend(loc="lower left", fontsize=6.8)
    a.set_title("(a) median fronts, 13 USGS sites", fontsize=8, loc="left", color=INK)
    d = pd.read_csv(REV / "a3_rate_matched.csv")
    d = d[d.inside & (d.kind == "ADAPTIVEML")]
    alphas = sorted(d.alpha.unique())
    for k, al in enumerate(alphas):
        v = d[d.alpha == al].max_ratio_gmean.values
        jit = rng.uniform(-0.12, 0.12, len(v))
        b.scatter(np.full(len(v), k) + jit, v, color=ORANGE, marker="s", s=14, alpha=0.8, edgecolor="white", lw=0.5)
        b.hlines(np.median(v), k - 0.25, k + 0.25, color=INK, lw=2)
        b.annotate(f"n={len(v)}", (k, 2.4), ha="center", fontsize=6.5, color=INK2)
    b.axhline(1, color=INK2, lw=0.8, ls="--"); b.text(len(alphas) - 0.6, 1.08, "equal error", fontsize=6.5, color=INK2, ha="right")
    b.set_yscale("log"); b.set_ylim(0.8, 60); b.set_xticks(range(len(alphas)))
    b.set_xticklabels([f"$\\alpha$={a:g}" for a in alphas])
    b.set_ylabel("worst-case error ratio")
    b.grid(axis="y", color=GRID, lw=0.6)
    b.set_title("(b) ADAPTIVEML / bounded, same report rate", fontsize=8, loc="left", color=INK)
    fig.tight_layout(w_pad=1.5); save(fig, "v2_ratematched")


# ---------------------------------------------------------------- event operating curves (Fig. 4, M9)
def events():
    c = pd.read_csv(REV / "a5_operating_curves.csv")
    fig, ax = plt.subplots(figsize=(W1, 2.6))
    for shape, col, mk, ls, lab in [("step", BLUE, "o", "-", "5$\\sigma$ steps"), ("ramp", ORANGE, "s", "--", "5$\\sigma$ ramps")]:
        e = c[c["shape"] == shape].sort_values("fa_per30d_median")
        ax.scatter(e.fa_per30d_median, e.detect_5sigma, color=col, marker=mk, s=12, alpha=0.35, edgecolor="none")
        f = e[e.detect_5sigma == e.detect_5sigma.cummax()]
        ax.plot(f.fa_per30d_median, f.detect_5sigma, color=col, marker=mk, ls=ls, label=f"{lab} (front)")
    for (lag, k, H, cc), lab in [((120, 3, 8, 6), "chosen"), ((120, 2, 4, 5), "sensitive")]:
        q = c[(c.lag_min == lag) & (c.k == k) & (c.H == H) & (c.c == cc)]
        x = q.fa_per30d_median.iloc[0]
        ax.axvline(x, color=MUTED, lw=0.8, ls=":")
        ax.text(x, 1.02, lab, rotation=0, ha="center", fontsize=6.5, color=INK2)
    ax.set_xscale("log"); ax.set_ylim(0, 1.08)
    ax.set_xticks([2, 3, 5, 10]); ax.set_xticklabels(["2", "3", "5", "10"]); ax.minorticks_off()
    ax.set_xlabel("false alarms per parameter per 30 days")
    ax.set_ylabel("share of injected events detected")
    ax.grid(color=GRID, lw=0.6); ax.legend(loc="lower right", fontsize=7)
    fig.tight_layout(); save(fig, "v2_events")


# ---------------------------------------------------------------- energy: gain vs sensing time (Fig. 6)
def sensing():
    sys.path.insert(0, "src")
    from energy import params as EP  # noqa: E402
    from energy.model import daily_energy, radio  # noqa: E402
    L = pd.read_csv("results/phase4/lifetime.csv")
    u = L[L.dataset.str.startswith("USGS") & (L.radio == "NB-IoT N211 RAI") & L.confirmed]
    spd = u[u.method == "PERIODIC every cycle"].groupby("dataset").samples_per_day.first().median()
    rrl = u[(u.method == "RLS-D") & (u.level == 2)].groupby("dataset").reports_per_day.first().median()
    ts = np.logspace(np.log10(0.5), np.log10(60), 60)
    fig, ax = plt.subplots(figsize=(W1, 2.5))
    sty = [("NB-IoT N211 default", "NB-IoT, default timers", ORANGE, "s", "--"),
           ("LoRaWAN SF12", "LoRaWAN SF12", AQUA, "^", ":"),
           ("NB-IoT N211 RAI", "NB-IoT, RAI", BLUE, "o", "-"),
           ("LoRaWAN SF7", "LoRaWAN SF7", YELLOW, "D", "-.")]
    for rad, lab, col, mk, ls in sty:
        prof = radio(rad)
        g = [daily_energy(spd, spd * 1.0101, prof, t_sense=t, confirmed=True)["total"] /
             daily_energy(spd, rrl * 1.0101, prof, t_sense=t, confirmed=True)["total"] for t in ts]
        ax.plot(ts, g, color=col, marker=mk, markevery=12, ls=ls, label=lab)
    ax.axvline(EP.T_SENSE["typical"], color=MUTED, lw=0.8, ls=":")
    ax.text(EP.T_SENSE["typical"] * 1.08, 1.04, "default 5 s", fontsize=6.5, color=INK2)
    ax.set_xscale("log"); ax.set_xticks([0.5, 1, 5, 10, 30, 60]); ax.set_xticklabels(["0.5", "1", "5", "10", "30", "60"])
    ax.minorticks_off()
    ax.set_xlabel("time awake per sample for sensing (s)"); ax.set_ylabel("modelled battery-life gain (x)")
    ax.set_ylim(1, 4.5); ax.grid(color=GRID, lw=0.6); ax.legend(loc="upper right", fontsize=6.8)
    fig.tight_layout(); save(fig, "v2_sensing")


# ---------------------------------------------------------------- equal accuracy, per site (Fig. S2, M19)
def equal():
    e = pd.read_csv(REV / "a1_equal_accuracy.csv")
    fig, ax = plt.subplots(figsize=(W1 * 1.3, 2.6))
    for _, r in e.iterrows():
        ax.plot([r.err_periodic60, r.err_rlsd_L2], [r.life_periodic60, r.life_rlsd_L2], color=GRID, lw=1, zorder=1)
    ax.scatter(e.err_periodic60, e.life_periodic60, color=ORANGE, marker="s", s=22, edgecolor="white", lw=0.6,
               zorder=3, label="hourly periodic")
    ax.scatter(e.err_rlsd_L2, e.life_rlsd_L2, color=BLUE, marker="o", s=22, edgecolor="white", lw=0.6, zorder=3,
               label="RLS-D, L2")
    ax.set_xscale("log"); ax.set_xlabel("worst-case error / L2 tolerance (mean over parameters)")
    ax.set_ylabel("modelled battery life (years)"); ax.grid(color=GRID, lw=0.6); ax.legend(loc="upper right")
    fig.tight_layout(); save(fig, "v2_equal_accuracy")


if __name__ == "__main__":
    todo = sys.argv[1:] or ["decomposition", "link", "ratematched", "events", "sensing", "equal"]
    for t in todo:
        globals()[t]()
