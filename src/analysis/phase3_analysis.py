"""Phase 3 analysis: tables and figures from results/phase3/phase3.csv and loss.csv.

Tables (results/phase3/tables/): p3_predictors, p3_detector, p3_detect_vs_tighten, p3_loss
Figures (results/phase3/figures/): fig8_detector_tradeoff.png, fig9_loss.png
Usage: python src/analysis/phase3_analysis.py
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, "src")
from sim.run_roc import split  # noqa: E402

RES = Path("results/phase3"); TAB, FIG = RES / "tables", RES / "figures"
TAB.mkdir(parents=True, exist_ok=True); FIG.mkdir(parents=True, exist_ok=True)
tune, test = split()


def grp(d):
    return np.where(d.isin(tune), "tune", np.where(d.str.startswith("InWater"), "InWaterSense", "test"))


def save(df, name):
    df.to_csv(TAB / name, index=False); print(f"\n== {name}\n{df.to_string(index=False)}")


r = pd.read_csv(RES / "phase3.csv")
assert r[[c for c in r if c.endswith("_viol")]].fillna(0).max().max() == 0, "bound violated"
assert not r.duplicated(["dataset", "level", "kind", "det", "tight"]).any()
r["m"] = r.kind + np.where(r.det > 0, "+DET" + r.det.astype(str), "") + np.where(r.tight > 0, "+TIGHT", "")
r["set"] = grp(r.dataset)

# ---- predictors vs per-site best fixed predictor (oracle)
b = r[r.det == 0].pivot_table(index=["dataset", "level"], columns="kind", values="reports_per_day")
b["oracle"] = b[["SOD", "RLS-T"]].min(axis=1)
g = pd.DataFrame({k: 100 * (b[k] / b.oracle - 1) for k in ["SOD", "RLS-T", "RLS-D", "RIDGE-D", "SWITCH"]}).reset_index()
g["set"] = grp(g.dataset)
t = g.groupby(["set", "level"])[["SOD", "RLS-T", "RLS-D", "RIDGE-D", "SWITCH"]].agg(
    lambda s: f"{s.median():+.1f} [{s.max():+.1f}]").reset_index()
save(t, "p3_predictors.csv")

# ---- detector: cost and capture (USGS medians)
u = r[r.dataset.str.startswith("USGS")].copy()
base = u[u.m == "RLS-D"].set_index(["dataset", "level"]).reports_per_day
u["overhead_pct"] = 100 * (u.reports_per_day.values / base.reindex(pd.MultiIndex.from_frame(u[["dataset", "level"]])).values - 1)
M = ["RLS-D", "RLS-D+DET1", "RLS-D+DET1+TIGHT", "RLS-D+DET2", "SOD", "SOD+DET1", "SOD+DET2"]
t = u[u.m.isin(M)].groupby(["level", "m"]).agg(
    reports=("reports_per_day", "median"), overhead_pct=("overhead_pct", "median"),
    checkB_capture=("event_capture", "median"), step_informed=("step_informed", "median"),
    step_alarmed=("step_alarmed", "median"), step_alarm_delay_min=("step_al_delay", "median"),
    ramp_informed=("ramp_informed", "median"), ramp_alarmed=("ramp_alarmed", "median"),
    event_over_delta=("step_a_over_delta", "median")).round(2).reset_index()
save(t, "p3_detector.csv")

# ---- detector at L4 vs tightening to L3 (per USGS site, then medians)
p = u.set_index(["dataset", "level", "m"])
rows = []
for ds in u.dataset.unique():
    for lab, (lvl, m) in {"RLS-D L3 (tighten)": (3, "RLS-D"), "RLS-D L4": (4, "RLS-D"),
                          "RLS-D+DET1 L4": (4, "RLS-D+DET1"), "RLS-D+DET2 L4": (4, "RLS-D+DET2")}.items():
        x = p.loc[(ds, lvl, m)]
        rows.append({"dataset": ds, "config": lab, "reports": x.reports_per_day, "step": x.step_informed,
                     "ramp": x.ramp_informed, "checkB": x.event_capture})
d = pd.DataFrame(rows)
save(d.groupby("config")[["reports", "step", "ramp", "checkB"]].median().round(2).reset_index(), "p3_detect_vs_tighten.csv")

# ---- loss
l = pd.read_csv(RES / "loss.csv")
l["protocol"] = np.where(l.proto == "ack", "confirmed (2 retries)", "unconfirmed, heartbeat " + (l.hb_min / 60).fillna(0).astype(int).astype(str) + " h")
base = l[(l.loss == 0) & (l.proto == "ack")].set_index(["dataset", "kind"]).tx_per_day
l["tx_overhead_pct"] = 100 * (l.tx_per_day.values / base.reindex(pd.MultiIndex.from_frame(l[["dataset", "kind"]])).values - 1)
seq = l[l.proto == "seq"]
print(f"\nunconfirmed protocol: {int(seq.unflagged_viol.sum())} unflagged violations in {len(seq)} runs "
      f"({seq.dataset.nunique()} datasets)")
t = l.groupby(["kind", "protocol", "loss"]).agg(
    tx_overhead_pct=("tx_overhead_pct", "median"), violation_pct=("viol_share", lambda s: 100 * s.median()),
    flagged_pct=("flag_share", lambda s: 100 * s.median()), unflagged_viol=("unflagged_viol", "sum")).round(2).reset_index()
save(t, "p3_loss.csv")

# ---- fig8: reports vs injected-step capture at L1-L4 (USGS medians)
fig, axs = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
for ax, col, title in [(axs[0], "step_informed", "5-sigma steps (3 h)"), (axs[1], "ramp_informed", "5-sigma ramps (3 h)")]:
    for m, mk in [("RLS-D", "o-"), ("RLS-D+DET1", "s-"), ("RLS-D+DET2", "^-"), ("SOD", "x--")]:
        e = u[u.m == m].groupby("level")[["reports_per_day", col]].median()
        ax.plot(e.reports_per_day, e[col], mk, label=m)
        for lvl, row in e.iterrows():
            ax.annotate(f"L{int(lvl)}", (row.reports_per_day, row[col]), fontsize=7, xytext=(3, -8), textcoords="offset points")
    ax.set_xscale("log"); ax.set_xlabel("reports per day (median, 13 USGS rivers)"); ax.set_title(title, fontsize=10)
axs[0].set_ylabel("events reported while ongoing (median share)")
axs[0].legend(frameon=False, fontsize=8)
fig.suptitle("A loose tolerance plus an event detector vs a tighter tolerance", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "fig8_detector_tradeoff.png", dpi=160)

# ---- fig9: loss, unconfirmed protocol: flagged time vs transmission overhead at 1 % loss
fig, ax = plt.subplots(figsize=(6.2, 4.2))
e = l[(l.loss == 0.01)].groupby(["kind", "protocol"])[["tx_overhead_pct", "flag_share"]].median().reset_index()
for kind, mk in [("SOD", "o"), ("RIDGE-D", "s"), ("RLS-D", "^"), ("RLS-T", "x")]:
    q = e[e.kind == kind]
    ax.scatter(q.tx_overhead_pct, 100 * q.flag_share, marker=mk, s=60, label=kind)
    for _, row in q.iterrows():
        ax.annotate(row.protocol.replace("unconfirmed, heartbeat ", "hb ").replace("confirmed (2 retries)", "ack"),
                    (row.tx_overhead_pct, 100 * row.flag_share), fontsize=7, xytext=(4, 2), textcoords="offset points")
ax.set_xlabel("extra transmissions vs lossless, % (median)"); ax.set_ylabel("time flagged as unverified, % (median)")
ax.set_title("1 % packet loss: confirmed uplink vs heartbeat resynchronisation", fontsize=10)
ax.legend(frameon=False); fig.tight_layout(); fig.savefig(FIG / "fig9_loss.png", dpi=160)
print("\nfigures saved")
