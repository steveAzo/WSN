"""Phase 1 checks for the Weija held-out case study (same code paths as the other datasets).

  Check A    : innovation correlation, out-of-sample AR/VAR skill (1 step, ~1 h, ~6 h)
  diel share : share of within-day variance explained by hour of day (Ghana = UTC+0, no DST)
  quantization: recording resolution, zero-change share, |1-h change| / resolution
  Check B    : offline reference events (labels for the event metrics of Phases 2-3)
Variants: T+EC (simulated), T+EC+pH (pH unverified, sensitivity only), T1+EC (other T probe).
Note: at a 32.5-min step a single exceedance lasts 32.5 min > GLITCH_MAX_MIN (30), so Check B
cannot label anything a "glitch" here; one-point runs become "short", >= 2 points "event".

Outputs: results/weija/phase1.json, results/weija/check_b_runs.csv, results/weija/check_b_summary.csv
Usage:   python src/analysis/weija_phase1.py
"""
import json
import sys
import warnings
from pathlib import Path

import pandas as pd

sys.path.insert(0, "src/analysis")
import check_b  # noqa: E402
from check_a import check_a, summarize  # noqa: E402
from quantization import measures  # noqa: E402
from summarize_check_a import diel_share  # noqa: E402

warnings.filterwarnings("ignore")
OUT = Path("results/weija")
STEP = 32.5
NAME = "Weija"


def load(vars_, min_seg_hours=24):
    c = pd.read_csv("data/clean/weija_cycles.csv", parse_dates=["t"]).dropna(subset=list(vars_))
    seglen = c.groupby("segment").t.transform("size")
    return c[seglen * STEP >= min_seg_hours * 60].sort_values("t")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    res = {}
    for vars_ in (["T", "EC"], ["T", "EC", "pH"], ["T1", "EC"]):
        d = load(vars_)
        r = check_a(d, vars_, f"{NAME} {'+'.join(vars_)}", [1, 2, 11])
        summarize(r)
        r["diel_share"] = {v: round(diel_share(d, v), 3) for v in vars_}
        r["quantization"] = {v: measures(d, v, 2) for v in vars_}
        r["days"] = round((d.t.max() - d.t.min()).total_seconds() / 86400, 1)
        print("diel share", r["diel_share"]); print("quantization", r["quantization"])
        res["+".join(vars_)] = r
    (OUT / "phase1.json").write_text(json.dumps(res, indent=2, default=float))

    # Check B on the full T+EC+pH cycles (pH events are labelled but pH is not simulated)
    check_b.V = ["T", "EC", "pH"]
    d = pd.read_csv("data/clean/weija_cycles.csv", parse_dates=["t"])
    d = d.dropna(subset=["T", "EC"])
    resolution = {v: res["T+EC+pH"]["quantization"][v]["resolution"] for v in ("T", "EC", "pH")}
    R, days = check_b.analyse(d, NAME, STEP, 0, resolution)
    R.to_csv(OUT / "check_b_runs.csv", index=False)
    S = []
    for v in check_b.V:
        g = R[R.param == v]; e = g[g.kind == "event"]
        S.append({"dataset": NAME, "param": v, "days": round(days), "runs": len(g),
                  "events_per_30d": round(len(e) / days * 30, 2),
                  "short_per_30d": round((g.kind == "short").sum() / days * 30, 2),
                  "event_median_dur_h": round(e.dur_min.median() / 60, 1) if len(e) else None,
                  "coherent_share": round(e.coherent.mean(), 2) if len(e) else None})
    S = pd.DataFrame(S); S.to_csv(OUT / "check_b_summary.csv", index=False)
    print("\nCheck B\n", S.to_string(index=False))
    print("\nstrongest events\n", R[R.kind == "event"].sort_values("peak_sigma", ascending=False)
          .head(12)[["param", "start", "dur_min", "peak_sigma", "coherent"]].to_string(index=False))


if __name__ == "__main__":
    main()
