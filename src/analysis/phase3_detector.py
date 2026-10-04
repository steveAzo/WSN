"""Phase 3a analysis: apply the PRE-REGISTERED detector selection rule (see src/sim/run_roc.py)
and report held-out performance.  -> results/phase3/detector_choice.json, tables, fig7_roc.png"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, "src")
from sim.run_roc import GRID, split  # noqa: E402

FA_BUDGET = 2.0
OUT = Path("results/phase3"); (OUT / "figures").mkdir(parents=True, exist_ok=True)
r = pd.read_csv(OUT / "roc.csv")
tune, test = split()
r["set"] = r.dataset.map(lambda d: "tune" if d in tune else "test")

per = r.groupby(["set", "dataset", "cfg"]).agg(fa=("fa_per30d_param", "first")).reset_index()
det5 = r[r.amp == 5].groupby(["set", "dataset", "cfg"]).detect.mean().rename("det5")
per = per.join(det5, on=["set", "dataset", "cfg"])
cfg = per[per.set == "tune"].groupby("cfg").agg(fa_med=("fa", "median"), det5=("det5", "mean")).reset_index()
cfg["config"] = cfg.cfg.map(lambda i: GRID[i])
ok = cfg[cfg.fa_med <= FA_BUDGET].sort_values(["det5", "fa_med"], ascending=[False, True])
assert len(ok), "no config meets the false-alarm budget"
best = int(ok.iloc[0].cfg)
print("tuning-site summary per config:\n", cfg.round(3).to_string(index=False))
print(f"\nCHOSEN cfg {best}: {GRID[best]}")
json.dump({"cfg": best, "config": GRID[best], "rule": f"median FA <= {FA_BUDGET}/param/30d on tuning sites; "
           "max mean detection of amp-5 events", "tuning_sites": tune},
          open(OUT / "detector_choice.json", "w"), indent=1)

ch = r[r.cfg == best]
tab = ch.pivot_table(index=["set", "amp"], columns=["shape", "dur"], values="detect", aggfunc="median").round(2)
print("\nchosen config, median detection over sites (held-out = test):\n", tab.to_string())
site = ch.groupby(["set", "dataset"]).agg(fa=("fa_per30d_param", "first"),
                                          det5=("detect", lambda s: s[ch.loc[s.index, "amp"] == 5].mean()),
                                          delay5_step=("delay_med", lambda s: s[(ch.loc[s.index, "amp"] == 5) &
                                                                                (ch.loc[s.index, "shape"] == "step")].median()))
print("\nper site:\n", site.round(2).to_string())
tab.reset_index().to_csv(OUT / "t_detector_chosen.csv", index=False)
site.reset_index().to_csv(OUT / "t_detector_sites.csv", index=False)

fig, ax = plt.subplots(figsize=(6, 4.2))
for s, mk in [("tune", "o"), ("test", "s")]:
    g = per[per.set == s].groupby("cfg").agg(fa=("fa", "median"), d=("det5", "mean"))
    ax.scatter(g.fa, g.d, marker=mk, label=f"{s} sites", alpha=.8)
    if best in g.index:
        ax.scatter(g.loc[best, "fa"], g.loc[best, "d"], marker=mk, s=160, facecolor="none", edgecolor="k")
ax.axvline(FA_BUDGET, c="grey", ls="--", lw=.8)
ax.set_xlabel("false alarms per parameter per 30 days (median over sites)")
ax.set_ylabel("detection of injected 5-sigma events (mean)")
ax.set_title("Event detector operating points (circled: chosen on tuning sites)", fontsize=10)
ax.legend(frameon=False); fig.tight_layout(); fig.savefig(OUT / "figures" / "fig7_roc.png", dpi=160)
