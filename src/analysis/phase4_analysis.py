"""Phase 4 analysis: tables and figures from results/phase4/lifetime.csv.

Tables (results/phase4/tables/): p4_main, p4_gain_by_level, p4_shares, p4_host_sensitivity, p4_solar
Figures (results/phase4/figures/):
  fig10_gain_vs_sensing.png   lifetime gain of RLS-D (L2) over every-cycle reporting vs sensing time
  fig11_equal_accuracy.png    lifetime vs worst-case error: periodic schedules vs bounded schemes
Usage: python src/analysis/phase4_analysis.py
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, "src")
from energy import params as P  # noqa: E402
from energy.model import daily_energy, lifetime_years, radio  # noqa: E402

RES = Path("results/phase4"); TAB, FIG = RES / "tables", RES / "figures"
TAB.mkdir(parents=True, exist_ok=True); FIG.mkdir(parents=True, exist_ok=True)
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]        # validated categorical slots 1-4
MARK = ["o", "s", "^", "D"]
INK, INK2 = "#0b0b0b", "#52514e"
BAT = P.BATTERIES["6600 mAh Li-ion (Weija node, paper 22)"]
plt.rcParams.update({"axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
                     "font.size": 9})


def save(df, name):
    df.to_csv(TAB / name, index=False); print(f"\n== {name}\n{df.to_string(index=False)}")


d = pd.read_csv(RES / "lifetime.csv")
u = d[d.confirmed & d.battery.str.startswith("6600") & d.dataset.str.startswith("USGS")].copy()
per = u[u.method == "PERIODIC every cycle"].set_index(["dataset", "radio", "t_sense"]).lifetime_y
u["gain_vs_every_cycle"] = u.lifetime_y.values / per.reindex(
    pd.MultiIndex.from_frame(u[["dataset", "radio", "t_sense"]])).values

# ---- main table: L2
sel = u[(u.method.isin(["PERIODIC every cycle", "SOD", "RLS-D", "RLS-D+DET2"])) & ((u.level == 2) | u.level.isna())]
t = sel.pivot_table(index=["radio", "t_sense"], columns="method", values="lifetime_y", aggfunc="median")
g = sel.pivot_table(index=["radio", "t_sense"], columns="method", values="gain_vs_every_cycle", aggfunc="median")
main = t[["PERIODIC every cycle", "SOD", "RLS-D", "RLS-D+DET2"]].join(g[["SOD", "RLS-D"]], rsuffix=" gain")
save(main.round(2).reset_index(), "p4_main.csv")

# ---- RLS-D over SOD by level
k = u[(u.method.isin(["SOD", "RLS-D"])) & u.level.between(1, 4)]
p = k.pivot_table(index=["radio", "t_sense", "dataset", "level"], columns="method", values="lifetime_y")
p["gain_pct"] = 100 * (p["RLS-D"] / p["SOD"] - 1)
save(p.groupby(["radio", "level"]).gain_pct.median().unstack().round(1).reset_index(), "p4_gain_by_level.csv")

# ---- energy shares (RLS-D, L2)
s = u[(u.method == "RLS-D") & (u.level == 2)].copy()
for c in ["E_sleep", "E_sense", "E_report"]:
    s[c + "_pct"] = 100 * s[c] / s.E_day
save(s.groupby(["radio", "t_sense"])[["E_sleep_pct", "E_sense_pct", "E_report_pct", "P_avg_mW"]]
     .median().round(1).reset_index(), "p4_shares.csv")

# ---- host awake during the report (default) vs asleep
rows = []
for rad in ["NB-IoT N211 RAI", "NB-IoT BC95 RAI", "LoRaWAN SF7", "LoRaWAN SF12", "NB-IoT N211 default"]:
    for awake in (True, False):
        prof = dict(radio(rad)); prof["t_conn"] = prof["t_conn"] if awake else 0.0
        gains = []
        for ds, grp in u[(u.radio == rad) & (u.t_sense == "typical")].groupby("dataset"):
            a = grp[grp.method == "PERIODIC every cycle"].iloc[0]; b = grp[(grp.method == "RLS-D") & (grp.level == 2)].iloc[0]
            life = lambda r: lifetime_years(daily_energy(r.samples_per_day, r.reports_per_day * 1.0104, prof,
                                                         t_sense=5.0, confirmed=True)["total"], BAT)
            gains.append(life(b) / life(a))
        rows.append({"radio": rad, "host_awake_during_report": awake, "gain_RLS-D_L2": np.median(gains)})
save(pd.DataFrame(rows).round(2), "p4_host_sensitivity.csv")

# ---- solar margin: Weija 2 W panel, worst month ~3.5 peak-sun hours, 0.6 derating (assumptions)
harvest = 2.0 * 3.5 * 3600 * 0.6
need = u[(u.method == "PERIODIC every cycle") & (u.t_sense == "very slow")].E_day.max()
save(pd.DataFrame([{"panel_W": 2.0, "peak_sun_h": 3.5, "derate": 0.6, "harvest_J_per_day": harvest,
                    "worst_case_need_J_per_day": need, "margin_x": harvest / need,
                    "panel_W_for_need": need / (3.5 * 3600 * 0.6)}]).round(3), "p4_solar.csv")

# ---- fig10: gain vs sensing time (median USGS rates), host awake during report
med = u[u.radio == "NB-IoT N211 RAI"].groupby(["dataset", "method", "level"], dropna=False)[
    ["samples_per_day", "reports_per_day"]].first().reset_index()
spd = med[med.method == "PERIODIC every cycle"].samples_per_day.median()
rrl = med[(med.method == "RLS-D") & (med.level == 2)].reports_per_day.median()
ts = np.logspace(np.log10(0.5), np.log10(60), 60)
fig, ax = plt.subplots(figsize=(6.4, 4.0))
for i, rad in enumerate(["NB-IoT N211 RAI", "NB-IoT BC95 RAI", "LoRaWAN SF12", "LoRaWAN SF7"]):
    prof = radio(rad)
    gain = [daily_energy(spd, spd * 1.0104, prof, t_sense=t, confirmed=True)["total"] /
            daily_energy(spd, rrl * 1.0104, prof, t_sense=t, confirmed=True)["total"] for t in ts]
    ax.plot(ts, gain, color=SERIES[i], lw=2, marker=MARK[i], markevery=12, ms=6, label=rad,
            markeredgecolor="#fcfcfb", markeredgewidth=1)
    ax.annotate(rad.replace(" RAI", ""), (ts[0], gain[0]), xytext=(-6, 0), textcoords="offset points",
                color=INK2, va="center", ha="right", fontsize=8)
for t in P.T_SENSE.values():
    ax.axvline(t, color="#e4e3df", lw=0.8, zorder=0)
ax.set_xscale("log"); ax.set_xlim(0.12, 60)
ax.set_xlabel("time awake per sample for sensing (s, log scale)")
ax.set_ylabel("battery-life gain over reporting every cycle (x)")
ax.set_title("Report suppression pays when the radio, not the sensing, dominates\n"
             f"RLS-D at L2; median USGS rates ({rrl:.0f} of {spd:.0f} cycles/day reported)", fontsize=9.5, color=INK)
ax.grid(axis="y", color="#e4e3df", lw=0.6); ax.legend(frameon=False, fontsize=8, loc="lower left", bbox_to_anchor=(0.0, 0.0))
fig.tight_layout(); fig.savefig(FIG / "fig10_gain_vs_sensing.png", dpi=170)

# ---- fig11: equal-accuracy view (N211 RAI, 5 s sensing)
p2 = pd.read_csv("results/phase2/results.csv"); p3 = pd.read_csv("results/phase3/phase3.csv")
dL2 = p2[(p2.kind == "SOD") & (p2.level == 2) & (p2["mode"] == "report")].set_index("dataset")
ref = {"T": 0.2, "DO": 2.0, "pH": 0.1}


def nerr(row, ds):
    v = [row[f"{q}_max"] / (dL2.loc[ds, "EC_delta"] if q == "EC" else ref[q])
         for q in ["T", "EC", "DO", "pH"] if pd.notna(row.get(f"{q}_max"))]
    return np.mean(v)


life = u[(u.radio == "NB-IoT N211 RAI") & (u.t_sense == "typical")]
pts = []
for _, r in p2[(p2.kind == "PERIODIC") & p2.setting.notna() & p2.dataset.str.startswith("USGS")].iterrows():
    lab = f"PERIODIC {int(r.setting)} min"
    pts.append({"family": "Periodic (30-240 min)", "lab": f"{int(r.setting)} min", "dataset": r.dataset,
                "err": nerr(r, r.dataset), "life": life[(life.dataset == r.dataset) & (life.method == lab)].lifetime_y.iloc[0]})
for kind, fam in [("SOD", "Send-on-delta (L1-L4)"), ("RLS-D", "RLS-D (L1-L4)")]:
    for _, r in p3[(p3.kind == kind) & (p3.det == 0) & p3.dataset.str.startswith("USGS")].iterrows():
        pts.append({"family": fam, "lab": f"L{int(r.level)}", "dataset": r.dataset, "err": nerr(r, r.dataset),
                    "life": life[(life.dataset == r.dataset) & (life.method == kind) & (life.level == r.level)].lifetime_y.iloc[0]})
q = pd.DataFrame(pts).groupby(["family", "lab"])[["err", "life"]].median().reset_index()
save(q.round(3), "p4_equal_accuracy.csv")
fig, ax = plt.subplots(figsize=(6.4, 4.0))
for i, fam in enumerate(["Periodic (30-240 min)", "Send-on-delta (L1-L4)", "RLS-D (L1-L4)"]):
    e = q[q.family == fam].sort_values("life")
    ax.plot(e.err, e.life, color=SERIES[[1, 2, 0][i]], lw=2, marker=MARK[i], ms=7, label=fam,
            markeredgecolor="#fcfcfb", markeredgewidth=1)
    off = {"Periodic (30-240 min)": (6, -3), "Send-on-delta (L1-L4)": (6, -11), "RLS-D (L1-L4)": (-14, 5)}[fam]
    for _, row in e.iterrows():
        ax.annotate(row.lab, (row.err, row.life), xytext=off, textcoords="offset points", fontsize=7, color=INK2)
ax.set_xscale("log")
ax.set_xlabel("worst-case reconstruction error / L2 tolerance (median over parameters, log)")
ax.set_ylabel("battery life (years, 6600 mAh)")
ax.set_title("Same battery life, an order of magnitude smaller worst-case error\n"
             "NB-IoT (u-blox N211, release after send), 5 s sensing; medians over 13 USGS rivers",
             fontsize=9.5, color=INK)
ax.grid(color="#e4e3df", lw=0.6); ax.legend(frameon=False, fontsize=8, loc="upper left")
fig.tight_layout(); fig.savefig(FIG / "fig11_equal_accuracy.png", dpi=170)
print("\nfigures saved")
