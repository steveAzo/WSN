"""Phase 1 figures for the predictability report.
fig1: diel share vs 1-hour VAR skill (every dataset x parameter)
fig2: monthly report cost vs out-of-sample skill (USGS site-months)
fig3: InWaterSense DO, 1-7 Sep 2015 (suspected fouling artefact) with T and EC
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

OUT = Path("results/phase1/figures"); OUT.mkdir(parents=True, exist_ok=True)
COL = {"T": "#d95f02", "EC": "#7570b3", "DO": "#1b9e77", "pH": "#e7298a"}

s = pd.read_csv("results/phase1/check_a_summary.csv")
fig, ax = plt.subplots(figsize=(6, 4.2))
for v, g in s.groupby("param"):
    u, i = g[~g.site.str.startswith("InWater")], g[g.site.str.startswith("InWater")]
    ax.scatter(u.diel_share, u.skill_VAR, c=COL[v], label=v, s=36, alpha=.85)
    ax.scatter(i.diel_share, i.skill_VAR, c=COL[v], marker="X", s=90, edgecolor="k")
ax.axhline(0, c="grey", lw=.8)
ax.set_xlabel("share of within-day variance explained by time of day")
ax.set_ylabel("1-h prediction skill vs 'last value'")
ax.set_title("Predictability follows the day-night cycle\n(circles: 13 USGS rivers; X: InWaterSense)", fontsize=10)
ax.legend(frameon=False); fig.tight_layout(); fig.savefig(OUT / "fig1_diel_vs_skill.png", dpi=160)

m = pd.read_csv("results/phase1/seasonal.csv")
m = m[m.dataset != "InWaterSense n1"]
fig, axs = plt.subplots(1, 4, figsize=(12, 3.2), sharey=True)
for ax, v in zip(axs, ["T", "DO", "pH", "EC"]):
    g = m[m.param == v]
    ax.scatter(g.cost, g.skill, s=14, c=COL[v], alpha=.7)
    ax.set_title(f"{v}  (Spearman {g.cost.corr(g.skill, method='spearman'):+.2f})", fontsize=10)
    ax.set_xlabel("reports per sample (send-on-delta)"); ax.axhline(0, c="grey", lw=.8)
axs[0].set_ylabel("out-of-sample 1-h skill")
fig.suptitle("Costly months are predictable months (113 USGS site-months)", fontsize=11)
fig.tight_layout(); fig.savefig(OUT / "fig2_cost_vs_skill.png", dpi=160)

c = pd.read_csv("data/clean/inws_cycles.csv", parse_dates=["t"])
c = c[(c.node == 1) & (c.t >= "2015-09-01") & (c.t < "2015-09-08")].set_index("t")
c = c[["DO", "T", "EC"]].resample("10min").median().reset_index()   # gaps become NaN, so lines break
fig, ax = plt.subplots(3, 1, figsize=(9, 5.5), sharex=True)
for a, v, lab in zip(ax, ["DO", "T", "EC"], ["DO (% sat)", "T (°C)", "EC (µS/cm)"]):
    a.plot(c.t, c[v], lw=.8, c=COL[v]); a.set_ylabel(lab)
ax[0].set_title("InWaterSense node 1, 1-7 Sep 2015: daily morning DO jumps with no T/EC response\n(suspected biofouling/sunlight artefact)", fontsize=10)
fig.tight_layout(); fig.savefig(OUT / "fig3_inws_do_artefact.png", dpi=160)
print("saved", sorted(p.name for p in OUT.glob("*.png")))
