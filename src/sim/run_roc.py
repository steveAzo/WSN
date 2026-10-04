"""Phase 3a: detector ROC on all datasets (injected events, known onsets).

PRE-REGISTERED (written 2026-10-03 before any all-site result was seen):
  tuning sites  : every second USGS site in ID order (positions 0, 2, 4, ...)
  test sites    : the other USGS sites + InWaterSense (never used for choosing)
  rule          : among configs whose MEDIAN false-alarm rate over tuning sites is
                  <= 2 alarms / parameter / 30 days, choose the highest mean detection of
                  amp = 5 events (Check B threshold) over shapes and durations; ties -> lower FA
Usage: python src/sim/run_roc.py [--jobs 2]     -> results/phase3/roc.csv (resumable)
"""
import argparse
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import pandas as pd

sys.path.insert(0, "src")
from sim.run_phase2 import dataset_names, get  # noqa: E402
from sim.roc_detector import roc  # noqa: E402

GRID = [dict(mode="lag", lag_min=m, k=k, H=H, c=k + 3) for m in (60, 120, 240) for k in (2, 3) for H in (4, 8)]
# ROUND 2 (added 2026-10-03 after round 1 showed slow ramps are missed by lag detectors; tuned on
# the SAME tuning sites only, same rule; the overall winner is then run once on the test sites)
SLOW = [dict(mode="median", k=k, H=H, c=k + 3) for k in (3, 4) for H in (8, 16)]
FAST = [dict(mode="lag", lag_min=60, k=3, H=4, c=6), dict(mode="lag", lag_min=60, k=2, H=8, c=5),
        dict(mode="lag", lag_min=120, k=3, H=4, c=6)]
GRID += SLOW + [{"bank": [f, s]} for f in FAST for s in SLOW]          # cfg 12.. 27
ROUND1 = range(12)
OUT = Path("results/phase3/roc.csv")


def split():
    usgs = sorted(n for n in dataset_names() if n.startswith("USGS"))
    return usgs[0::2], usgs[1::2] + ["InWaterSense n1"]


def job(spec):
    name, i = spec
    t0 = time.time()
    r = roc(get(name), [GRID[i]], shapes=("step", "ramp"), amps=(3, 5, 8), durs=(60, 180, 360))
    r["cfg"] = i; r["secs"] = round(time.time() - t0, 1)
    return r


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--round", type=int, default=1)
    ap.add_argument("--test-cfg", type=int, default=None, help="run ONE chosen config on the test sites")
    a = ap.parse_args()
    tune, test = split()
    if a.test_cfg is not None:
        S = [(n, a.test_cfg) for n in test]
    elif a.round == 1:
        S = [(n, i) for n in tune + test for i in ROUND1]
    else:
        S = [(n, i) for n in tune for i in range(len(ROUND1), len(GRID))]
    parts = []
    if OUT.exists():
        old = pd.read_csv(OUT); parts.append(old)
        done = set(zip(old.dataset, old.cfg)); S = [s for s in S if s not in done]
    print(f"{len(S)} jobs; tuning={tune}", flush=True)
    t0 = time.time()
    with Pool(a.jobs) as pool:
        for k, r in enumerate(pool.imap_unordered(job, S), 1):
            parts.append(r); pd.concat(parts).to_csv(OUT, index=False)
            el = time.time() - t0
            print(f"  {k}/{len(S)} {r.dataset.iloc[0]} cfg{r.cfg.iloc[0]} {el/60:.1f} min, ~{el/k*(len(S)-k)/60:.0f} min left", flush=True)
    print("saved", OUT)
