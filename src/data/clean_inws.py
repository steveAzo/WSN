"""Phase 1 — clean the InWaterSense raw data into 10-minute multi-parameter "cycles".

Why cycles: each sampling cycle's four parameters arrive as separate messages a few
seconds apart (paper 16, Table 8). Raw timing is bimodal: within-cycle gaps 0–60 s,
between-cycle gaps ~610 s, only 0.1–0.4 % of gaps in 120–540 s (checked 2026-10-03).
So readings of the same node < 120 s apart belong to one cycle.

Quality tiers (values are never silently dropped — every decision is a flag):
  RANGE  hard physical / sensor-fault range  -> value set to NaN
         T [0, 40] degC: -0.33/-0.35 recur as fault codes; 81–115 degC impossible.
         EC [50, 3000] uS/cm: grab samples at Plemetin 262–831 (Shala 2014; Kelmendi
             2023); < 50 is a dry/disconnected probe; node 2 shows -5021 fault code.
         pH [0, 14]; DO [0, 200] %sat (DO is % saturation, docs/DO_UNITS_EVIDENCE.md).
  PLAUS  site plausibility -> value set to NaN
         pH [5, 10]: Sitnica grab samples 6.6–8.3 (Shala 2014; Kelmendi 2023); week-long
         node-1 episodes at pH 2–4 are probe faults, not river chemistry.
  SPIKE  Hampel outlier (window 7 cycles ~70 min, 4 scaled MAD) -> value KEPT, flagged.
         Could be a genuine short event or a glitch; Check B decides.
Segments: a new segment starts after a gap > 60 min (never interpolate across it).

Outputs: data/clean/inws_cycles.csv, results/phase1/inws_quality.json
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path("INWS/INWSStaticDataParameterWise.csv")
OUT = Path("data/clean"); REP = Path("results/phase1")
PARAMS = {"Temperature": "T", "Conductivity": "EC", "pH": "pH", "DissolvedOxygen": "DO"}
RANGE = {"T": (0.0, 40.0), "EC": (50.0, 3000.0), "pH": (0.0, 14.0), "DO": (0.0, 200.0)}
PLAUS = {"pH": (5.0, 10.0)}
CYCLE_GAP_S, SEGMENT_GAP_MIN = 120, 60
HAMPEL_W, HAMPEL_K = 7, 4.0


def load_raw():
    p = pd.read_csv(RAW, dtype={"Timestamp": str})
    # the published CSV ends with 199 all-empty rows = the 199 duplicates paper 16 says were removed
    p = p.dropna(how="all")
    p["t"] = pd.to_datetime(p["Timestamp"].str[:14], format="%Y%m%d%H%M%S")
    p["node"] = p["Node Id"].astype(int)
    p["var"] = p["Parameter"].map(PARAMS)
    n0 = len(p)
    p = p.drop_duplicates(["node", "t", "var", "Value"])
    return p.sort_values(["node", "t"]), n0 - len(p)


def to_cycles(p):
    p = p.copy()
    gap = p.groupby("node")["t"].diff().dt.total_seconds()
    p["cycle"] = (gap.isna() | (gap > CYCLE_GAP_S)).cumsum()
    # a parameter seen twice in one cycle: keep the median, count it as a conflict
    agg = p.groupby(["node", "cycle", "var"])["Value"].agg(["median", "size"]).reset_index()
    wide = agg.pivot_table(index=["node", "cycle"], columns="var", values="median").reset_index()
    times = p.groupby(["node", "cycle"])["t"].agg(t="min", span=lambda s: (s.max() - s.min()).total_seconds())
    wide = wide.merge(times.reset_index(), on=["node", "cycle"])
    wide["n_dup_param"] = agg.groupby(["node", "cycle"])["size"].apply(lambda s: int((s > 1).sum())).values
    return wide


def hampel_flags(x, w=HAMPEL_W, k=HAMPEL_K):
    med = x.rolling(w, center=True, min_periods=3).median()
    mad = (x - med).abs().rolling(w, center=True, min_periods=3).median() * 1.4826
    return ((x - med).abs() > k * mad) & (mad > 0)


def main():
    OUT.mkdir(parents=True, exist_ok=True); REP.mkdir(parents=True, exist_ok=True)
    p, n_dup = load_raw()
    c = to_cycles(p)
    report = {"raw_rows": int(len(p) + n_dup), "exact_duplicates_removed": int(n_dup), "nodes": {}}
    frames = []
    for node, d in c.groupby("node"):
        d = d.sort_values("t").reset_index(drop=True)
        r = {"cycles": int(len(d)), "start": str(d.t.min()), "end": str(d.t.max())}
        for v in PARAMS.values():
            raw = d[v].copy()
            lo, hi = RANGE[v]
            d[f"{v}_range"] = raw.notna() & ~raw.between(lo, hi)
            d.loc[d[f"{v}_range"], v] = np.nan
            if v in PLAUS:
                lo, hi = PLAUS[v]
                d[f"{v}_plaus"] = d[v].notna() & ~d[v].between(lo, hi)
                d.loc[d[f"{v}_plaus"], v] = np.nan
            else:
                d[f"{v}_plaus"] = False
            r[v] = {"missing_in_cycle": int(raw.isna().sum()), "range_fail": int(d[f"{v}_range"].sum()),
                    "plaus_fail": int(d[f"{v}_plaus"].sum())}
        gap_min = d.t.diff().dt.total_seconds() / 60
        d["segment"] = (gap_min.isna() | (gap_min > SEGMENT_GAP_MIN)).cumsum()
        for v in PARAMS.values():
            d[f"{v}_spike"] = d.groupby("segment")[v].transform(lambda s: hampel_flags(s)).fillna(False).astype(bool)
            r[v]["spike_flag"] = int(d[f"{v}_spike"].sum())
        d["complete"] = d[list(PARAMS.values())].notna().all(axis=1)
        seg = d.groupby("segment").agg(n=("t", "size"), start=("t", "min"), end=("t", "max"))
        r.update(complete_cycles=int(d.complete.sum()), segments=int(len(seg)),
                 segments_ge_1day=int((seg.n >= 144).sum()),
                 cycles_in_segments_ge_1day=int(seg.n[seg.n >= 144].sum()),
                 median_cycle_interval_s=float(d.t.diff().dt.total_seconds().median()),
                 cycles_with_duplicate_param=int((d.n_dup_param > 0).sum()))
        report["nodes"][int(node)] = r
        frames.append(d)
    out = pd.concat(frames).drop(columns=["cycle"])
    out.to_csv(OUT / "inws_cycles.csv", index=False)
    (REP / "inws_quality.json").write_text(json.dumps(report, indent=2, default=str))
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
