"""Phase 1, Check B — event content: how many genuine events vs glitches does each series hold?

OFFLINE reference labelling (uses past AND future data; it creates ground-truth-like labels for
evaluating the event-preservation guarantee — it is NOT the online detector the node runs).
Per series (dataset x parameter), within contiguous segments:
  1. baseline  = centred 24-h rolling median; anomaly a = x - baseline
  2. remove the typical diel shape: per calendar month, subtract the hour-of-day median of a
  3. robust scale s = 1.4826 * MAD of the residual, per month, FLOORED at the sensor's
     recording resolution (from quantization.csv). Without the floor, coarsely recorded
     series (pH in 0.1 steps) on calm days get s ~ 0 and every single step looks like an
     "event" (observed in the first run, 2026-10-03).
  4. exceedance = |residual| > K*s (K = 5); runs separated by <= 1 h are merged
  5. classify a run:  glitch = duration < 30 min AND the series returns to its pre-run level;
                      event  = duration >= 60 min;  otherwise "short"
  6. an event is "coherent" if another parameter at the same dataset has an event overlapping
     within +-1 h (e.g. storm: EC drops while T/DO/pH shift together)
Outputs: results/phase1/check_b_runs.csv (every run), results/phase1/check_b_summary.csv
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "src/analysis")
from check_a import load_usgs  # noqa: E402

V = ["T", "EC", "DO", "pH"]
K, MERGE_MIN, GLITCH_MAX_MIN, EVENT_MIN_MIN = 5.0, 60, 30, 60


def residual(df, v, step_min, tz_shift_h=0, res=0.0):
    out = []
    w = max(3, int(round(24 * 60 / step_min)))
    for _, s in df.groupby("segment"):
        s = s[["t", v]].dropna().set_index("t")[v]
        if len(s) < w // 2:
            continue
        base = s.rolling(w, center=True, min_periods=w // 4).median()
        out.append((s - base).rename("a"))
    a = pd.concat(out).to_frame()
    loc = a.index.tz_localize(None) if a.index.tz is not None else a.index
    a["m"] = loc.to_period("M"); a["h"] = (loc + pd.Timedelta(hours=tz_shift_h)).hour
    a["r"] = a.a - a.groupby(["m", "h"]).a.transform("median")
    a["s"] = a.groupby("m").r.transform(lambda r: 1.4826 * (r - r.median()).abs().median()).clip(lower=res)
    return a


def runs(a, x, step_min):
    exc = (a.r.abs() > K * a.s) & (a.s > 0)
    t = a.index[exc]
    if len(t) == 0:
        return []
    out, start, prev = [], t[0], t[0]
    for ti in t[1:]:
        if (ti - prev).total_seconds() / 60 > MERGE_MIN:
            out.append((start, prev)); start = ti
        prev = ti
    out.append((start, prev))
    res = []
    for s0, s1 in out:
        dur = (s1 - s0).total_seconds() / 60 + step_min
        before = x[:s0].iloc[-4:-1].median() if len(x[:s0]) > 3 else np.nan
        after = x[s1:].iloc[1:4].median() if len(x[s1:]) > 3 else np.nan
        scale = a.s.loc[s0]
        reverts = abs(after - before) < 2 * scale if np.isfinite(before) and np.isfinite(after) else False
        peak = float(a.r.loc[s0:s1].abs().max() / scale) if scale > 0 else np.nan
        kind = "glitch" if (dur < GLITCH_MAX_MIN and reverts) else ("event" if dur >= EVENT_MIN_MIN else "short")
        res.append({"start": s0, "end": s1, "dur_min": dur, "peak_sigma": peak, "reverts": bool(reverts), "kind": kind})
    return res


def analyse(df, name, step_min, tz, resolution):
    days = (df.t.max() - df.t.min()).total_seconds() / 86400
    allruns = []
    for v in V:
        a = residual(df, v, step_min, tz, resolution.get(v, 0.0))
        x = df.dropna(subset=[v]).set_index("t")[v]
        for r in runs(a, x, step_min):
            allruns.append({"dataset": name, "param": v, **r})
    R = pd.DataFrame(allruns)
    if R.empty:
        return R, days
    ev = R[R.kind == "event"]
    R["coherent"] = False
    for i, e in ev.iterrows():
        o = ev[(ev.param != e.param) & (ev.start <= e.end + pd.Timedelta(hours=1)) & (ev.end >= e.start - pd.Timedelta(hours=1))]
        R.loc[i, "coherent"] = len(o) > 0
    return R, days


if __name__ == "__main__":
    meta = pd.read_csv("data/raw/usgs/candidate_sites.csv", dtype={"site": str}).set_index("site")
    c = pd.read_csv("data/clean/inws_cycles.csv", parse_dates=["t"]); c = c[c.node == 1]
    jobs = [(c, "InWaterSense n1", 10.2, 0)]
    for s in meta.index:
        try:
            df, step = load_usgs(s, min_seg_hours=24)
        except (FileNotFoundError, KeyError):
            continue
        tz = -8 if meta.loc[s, "state"] == "OR" else (-6 if meta.loc[s, "state"] == "IL" else -5)
        jobs.append((df, f"{s} {meta.loc[s, 'name'][:24]}", step, tz))
    q = pd.read_csv("results/phase1/quantization.csv")
    q["code"] = q.site.str.split().str[0]
    allR, summ = [], []
    for df, name, step, tz in jobs:
        code = name.split()[0]
        resolution = q[q.code == code].set_index("param").resolution.to_dict()
        R, days = analyse(df, name, step, tz, resolution)
        allR.append(R)
        for v in V:
            g = R[R.param == v] if not R.empty else R
            e = g[g.kind == "event"] if not g.empty else g
            summ.append({"dataset": name, "param": v, "days": round(days),
                         "events_per_30d": round(len(e) / days * 30, 2),
                         "glitches_per_30d": round((g.kind == "glitch").sum() / days * 30, 2) if not g.empty else 0,
                         "event_median_dur_h": round(e.dur_min.median() / 60, 1) if len(e) else np.nan,
                         "coherent_share": round(e.coherent.mean(), 2) if len(e) else np.nan})
        print("done", name, flush=True)
    R = pd.concat(allR); S = pd.DataFrame(summ)
    R.to_csv("results/phase1/check_b_runs.csv", index=False); S.to_csv("results/phase1/check_b_summary.csv", index=False)
    pd.set_option("display.width", 200)
    print(S.pivot(index="dataset", columns="param", values="events_per_30d").to_string())
    print("\ncoherent share of events:\n", S.pivot(index="dataset", columns="param", values="coherent_share").to_string())
    print("\nglitches per 30 days:\n", S.pivot(index="dataset", columns="param", values="glitches_per_30d").to_string())
    iw = R[(R.dataset == "InWaterSense n1") & (R.kind == "event")].sort_values("peak_sigma", ascending=False)
    print("\nInWaterSense: 12 strongest events\n", iw.head(12)[["param", "start", "dur_min", "peak_sigma", "coherent"]].to_string(index=False))
