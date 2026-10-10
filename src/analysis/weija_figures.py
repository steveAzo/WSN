"""Figures for results/weija/WEIJA_REPORT.md.

  figW1_week.png : one week of the cleaned Weija cycles (T, T1, EC, pH), midday shaded
  figW2_test.png : pre-registered test - Phase 2 diel share vs RLS-T saving at L2, fitted line
                   (14 datasets), 90 % prediction interval at Weija's diel share, Weija's result
Usage: python src/analysis/weija_figures.py
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

FIG = Path("results/weija/figures"); FIG.mkdir(parents=True, exist_ok=True)
BLUE, ORANGE, INK, MUTED, GRID = "#2a78d6", "#eb6834", "#222222", "#6b6a63", "#e4e3dc"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False,
                     "axes.spines.right": False})


def week():
    c = pd.read_csv("data/clean/weija_cycles.csv", parse_dates=["t"])
    w = c[(c.t >= "2018-11-08") & (c.t < "2018-11-16")].set_index("t")[["T", "T1", "EC", "pH"]]
    gap = w.index.to_series().diff() > pd.Timedelta("60min")       # break lines at data gaps
    br = w[gap].copy(); br[:] = np.nan; br.index = br.index - pd.Timedelta("1min")
    w = pd.concat([w, br]).sort_index().reset_index()
    panels = [("T", "T, Sensor Two (°C)  - simulated"), ("T1", "T, Sensor One (°C)"),
              ("EC", "EC (µS/cm)  - simulated"), ("pH", "pH  - NOT simulated (unverified)")]
    fig, ax = plt.subplots(len(panels), 1, figsize=(7.2, 7.0), sharex=True)
    for a, (v, lab) in zip(ax, panels):
        for d in pd.date_range("2018-11-08", "2018-11-15"):
            a.axvspan(d + pd.Timedelta("11h"), d + pd.Timedelta("15h"), color=GRID, lw=0)
        a.plot(w.t, w[v], color=BLUE if v != "pH" else MUTED, lw=1.2)
        a.set_title(lab, loc="left", fontsize=9, color=INK)
        a.grid(axis="y", color=GRID, lw=0.6)
    ax[-1].xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%d %b"))
    ax[-1].set_xlabel("November 2018 (shaded: 11:00-15:00 local time; gaps are left open)")
    fig.suptitle("Weija: sharp midday excursions in every probe", x=0.01, ha="left", fontsize=10.5)
    fig.tight_layout(); fig.savefig(FIG / "figW1_week.png", dpi=160); plt.close(fig)


def test():
    r = pd.read_csv("results/phase2/results.csv")
    a = pd.read_csv("results/phase1/check_a_summary.csv", dtype={"site": str})
    a["site"] = a.site.where(a.site.str.startswith("InWater"), "USGS " + a.site.str[:8])
    s = a.groupby("site").agg(diel=("diel_share", "mean"))
    g = r[(r["mode"] == "report") & (r.level == 2)].pivot_table(index="dataset", columns="kind", values="reports_per_day")
    d = s.join((100 * (1 - g["RLS-T"] / g["SOD"])).rename("gain")).dropna()
    x, y = d.diel.values, d.gain.values
    b = np.polyfit(x, y, 1); n = len(x); se = np.sqrt(((y - np.polyval(b, x)) ** 2).sum() / (n - 2))
    # the PRE-REGISTERED prediction used run 1's Phase 1 numbers (before the cleaning fix), so the
    # interval is drawn there; the measured point sits at the corrected diel share
    wj0 = json.load(open("results/weija/run1_ramp_bug/phase1.json"))["T+EC"]["diel_share"]
    x0 = float(np.mean(list(wj0.values())))
    wj = json.load(open("results/weija/phase1.json"))["T+EC"]["diel_share"]
    x1 = float(np.mean(list(wj.values())))
    pi = stats.t.ppf(.95, n - 2) * se * np.sqrt(1 + 1 / n + (x0 - x.mean()) ** 2 / ((x - x.mean()) ** 2).sum())
    w = pd.read_csv("results/weija/phase2.csv"); w = w[(w["mode"] == "report") & (w.level == 2)].set_index("kind")
    y0 = 100 * (1 - w.reports_per_day["RLS-T"] / w.reports_per_day["SOD"])
    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    xx = np.linspace(0, 0.6, 50)
    ax.plot(xx, np.polyval(b, xx), color=MUTED, lw=1.2, ls="--", zorder=1)
    ax.axhline(0, color=MUTED, lw=0.8)
    ax.errorbar([x0], [np.polyval(b, x0)], yerr=[[pi], [pi]], fmt="o", ms=8, mfc="white", mec=ORANGE,
                ecolor=ORANGE, capsize=4, lw=1.5, zorder=3)
    ax.scatter(x, y, s=46, color=BLUE, edgecolor="white", lw=1.5, zorder=2, label="14 datasets of Phases 1-2")
    ax.scatter([x1], [y0], s=70, color=ORANGE, edgecolor="white", lw=1.5, zorder=4, label="Weija (held out)")
    ax.annotate(f"pre-registered {np.polyval(b, x0):.0f}%\n90% PI [{np.polyval(b, x0) - pi:.0f}, {np.polyval(b, x0) + pi:.0f}]",
                (x0, np.polyval(b, x0) + pi), xytext=(8, 0), textcoords="offset points", fontsize=8, color=INK, va="center")
    ax.annotate(f"measured {y0:.0f}%", (x1, y0), xytext=(9, -2), textcoords="offset points", fontsize=8, color=INK)
    ax.annotate("InWaterSense", (d.diel["InWaterSense n1"], d.gain["InWaterSense n1"]), xytext=(6, -10),
                textcoords="offset points", fontsize=8, color=MUTED)
    ax.set_xlabel("diel variance share (site mean over simulated parameters)")
    ax.set_ylabel("reports saved by RLS-T vs send-on-delta, L2 (%)")
    ax.set_title("Pre-registered test: Weija falls far below the prediction", loc="left", fontsize=10.5)
    ax.grid(color=GRID, lw=0.6); ax.legend(frameon=False, loc="upper left")
    fig.tight_layout(); fig.savefig(FIG / "figW2_test.png", dpi=160); plt.close(fig)


if __name__ == "__main__":
    week(); test(); print("saved", FIG)
