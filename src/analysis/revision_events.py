"""Revision A5 (review M9, M10, Fig. 4, minor comments on event counts and rounding).

1. Operating points of the chosen and the sensitive detector, steps and ramps SEPARATELY, per amplitude
   and duration, on tuning vs held-out sites: detection rate (mean and site range), false alarms per
   parameter per 30 days, and the distribution over sites of the median detection delay.
   -> results/revision/a5_operating_points.csv
2. Operating curves: every single (non-bank) lag-mode configuration of the ROC sweep, held-out sites:
   median false alarms vs mean detection of 5-sigma steps and of 5-sigma ramps (all durations).
   -> results/revision/a5_operating_curves.csv
3. Event counts: injected events per site/shape (benchmark), reference events per site/parameter
   (Check B over the whole series and in the test period).   -> results/revision/a5_event_counts.csv
4. Rounding: effective injected amplitude after rounding to the logger resolution vs nominal.
   -> results/revision/a5_rounding.csv
Usage: python src/analysis/revision_events.py
"""
import ast
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "src")
from sim.inject import noise_scale, resolution  # noqa: E402
from sim.run_phase2 import dataset_names, get  # noqa: E402
from sim.run_roc import split  # noqa: E402

OUT = Path("results/revision"); OUT.mkdir(parents=True, exist_ok=True)
tune, test = split()
roc = pd.read_csv("results/phase3/roc.csv")
roc = roc[roc.bank.isna()].copy()
roc["set"] = np.where(roc.dataset.isin(tune), "tune", np.where(roc.dataset.str.startswith("InWater"), "InWaterSense", "test"))
chosen = json.load(open("results/phase3/detector_choice.json"))["config"]
CFG = {"chosen (k=3, H=8, c=6)": chosen, "sensitive (k=2, H=4, c=5)": dict(chosen, k=2, H=4, c=5)}


def pick(c):
    m = (roc["mode"] == c["mode"]) & (roc.k == c["k"]) & (roc.H == c["H"]) & (roc.c == c["c"])
    if c["mode"] == "lag":
        m &= roc.lag_min == c["lag_min"]
    return roc[m]


# 1. operating points
rows = []
for lab, c in CFG.items():
    e = pick(c)
    assert len(e), lab
    for (st, shape, amp, dur), g in e.groupby(["set", "shape", "amp", "dur"]):
        rows.append({"config": lab, "set": st, "shape": shape, "amp_sigma": amp, "dur_min": dur,
                     "n_sites": g.dataset.nunique(), "n_events": int(g.n.sum()),
                     "detect_mean": g.detect.mean(), "detect_min": g.detect.min(), "detect_max": g.detect.max(),
                     "detect_pooled": (g.detect * g.n).sum() / g.n.sum(),
                     "fa_per30d_median": g.fa_per30d_param.median(),
                     "delay_med_min_sites_median": g.delay_med.median(),
                     "delay_med_min_sites_min": g.delay_med.min(), "delay_med_min_sites_max": g.delay_med.max()})
op = pd.DataFrame(rows)
op.to_csv(OUT / "a5_operating_points.csv", index=False, float_format="%.6g")
v = op[(op.amp_sigma == 5)].groupby(["config", "set", "shape"]).agg(
    detect=("detect_mean", "mean"), fa=("fa_per30d_median", "first"),
    delay_med=("delay_med_min_sites_median", "median")).round(3)
print("5-sigma events, mean over durations:\n", v)

# 2. operating curves (held-out USGS sites, single lag-mode configurations)
cur = []
for key, g in roc[(roc.set == "test") & (roc["mode"] == "lag")].groupby(["lag_min", "k", "H", "c"]):
    fa = g.drop_duplicates("dataset").fa_per30d_param.median()
    for shape in ["step", "ramp"]:
        q = g[(g["shape"] == shape) & (g.amp == 5)]
        cur.append({"lag_min": key[0], "k": key[1], "H": key[2], "c": key[3], "shape": shape,
                    "fa_per30d_median": fa, "detect_5sigma": q.detect.mean(),
                    "delay_med_min": q.delay_med.median()})
cur = pd.DataFrame(cur)
cur.to_csv(OUT / "a5_operating_curves.csv", index=False, float_format="%.6g")
best = cur.sort_values("fa_per30d_median")
for shape in ["step", "ramp"]:
    s = best[best["shape"] == shape]
    s = s[s.detect_5sigma == s.detect_5sigma.cummax()]
    print(f"\n{shape}: Pareto front (held-out sites)\n", s.round(2).to_string(index=False))

# 3. counts
cb = pd.read_csv("results/phase1/check_b_summary.csv")
inj = pick(chosen).groupby(["dataset", "shape"]).n.max().unstack()   # events per (amp, dur) cell
cnt = cb[["dataset", "param", "days", "events_per_30d"]].copy()
cnt["events_total"] = (cnt.events_per_30d * cnt.days / 30).round().astype(int)
cnt = cnt.merge(inj.rename(columns={"step": "injected_per_cell_step", "ramp": "injected_per_cell_ramp"}),
                left_on="dataset", right_index=True, how="left")
cnt.to_csv(OUT / "a5_event_counts.csv", index=False)
print("\nreference events: total", int(cnt.events_total.sum()), "over", cnt.dataset.nunique(), "datasets;",
      "per site-parameter median", cnt.events_total.median(), "range", cnt.events_total.min(), "-", cnt.events_total.max())

# 4. rounding of injected amplitudes
rr = []
for name in dataset_names():
    ds = get(name); res = resolution(ds); sc = noise_scale(ds, res)
    for j, p in enumerate(ds.params):
        for amp in (3, 5, 8):
            a = amp * sc[:, j]
            eff = np.round(a / res[j]) * res[j]
            rel = np.abs(eff - a) / a
            rr.append({"dataset": name, "param": p, "amp_sigma": amp, "resolution": res[j],
                       "scale_over_res_median": float(np.median(sc[:, j] / res[j])),
                       "rel_change_median": float(np.median(rel)), "rel_change_max": float(rel.max())})
rr = pd.DataFrame(rr)
rr.to_csv(OUT / "a5_rounding.csv", index=False, float_format="%.6g")
print("\nrounding: relative amplitude change, median over all", f"{rr.rel_change_median.median():.3%},",
      f"worst case {rr.rel_change_max.max():.1%} (bound 0.5/3 = 16.7% when the scale is at the floor)")
print(rr.groupby("amp_sigma")[["rel_change_median", "rel_change_max"]].max().round(4))
