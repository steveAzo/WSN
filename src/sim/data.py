"""Load a dataset into the simulator's form.

Rules (identical for every method):
  * only cycles where all simulated parameters are present; new segment if gap > 60 min
  * time split: first 20 % of the time span = warm-up/training (simulated, NOT scored);
    remaining 80 % = test (scored)
  * InWaterSense uses T, EC, DO (pH has week-long probe-fault episodes, see Phase 1);
    USGS uses T, EC, DO, pH
  * reference events = Check B 'event' runs (offline labels) that start in the test period
"""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

SEG_GAP_MIN = 60
TRAIN_FRAC = 0.2


@dataclass
class Dataset:
    name: str
    params: list
    t: pd.Series
    X: np.ndarray
    seg_start: np.ndarray
    test: np.ndarray
    step_min: float
    events: pd.DataFrame = field(default=None)

    def train_segments(self, j):
        """list of 1-D arrays (one per contiguous training segment) for parameter j"""
        seg = np.cumsum(self.seg_start)
        tr = ~self.test
        return [self.X[(seg == s) & tr, j] for s in np.unique(seg[tr])]


def _naive(s):
    """timezone-aware -> naive UTC; naive stays as is (InWaterSense local time)"""
    s = pd.to_datetime(s)
    return s.dt.tz_convert("UTC").dt.tz_localize(None) if s.dt.tz is not None else s


def _finish(name, df, params, events):
    df = df.dropna(subset=params).copy()
    df["t"] = _naive(df["t"])
    df = df.sort_values("t").reset_index(drop=True)
    gap = df.t.diff().dt.total_seconds().div(60)
    seg_start = (gap.isna() | (gap > SEG_GAP_MIN)).to_numpy()
    t0, t1 = df.t.iloc[0], df.t.iloc[-1]
    test = (df.t >= t0 + TRAIN_FRAC * (t1 - t0)).to_numpy()
    step = float(gap.median())
    ev = events[(events.param.isin(params))].copy() if events is not None else None
    if ev is not None:
        ev = ev[pd.to_datetime(ev.start) >= df.t[test].iloc[0]]
    return Dataset(name, params, df.t, df[params].to_numpy(float), seg_start, test, step, ev)


def _events(prefix):
    r = pd.read_csv("results/phase1/check_b_runs.csv")
    r = r[(r.kind == "event") & r.dataset.str.startswith(prefix)].copy()
    for c in ("start", "end"):
        r[c] = _naive(pd.to_datetime(r[c], utc=(prefix != "InWaterSense")))
    return r


def load_inws():
    c = pd.read_csv("data/clean/inws_cycles.csv", parse_dates=["t"])
    c = c[c.node == 1]
    return _finish("InWaterSense n1", c, ["T", "EC", "DO"], _events("InWaterSense"))


def load_usgs(site):
    d = pd.read_csv(f"data/clean/usgs/{site}.csv", parse_dates=["t"])
    return _finish(f"USGS {site}", d, ["T", "EC", "DO", "pH"], _events(site))


def all_datasets():
    sites = pd.read_csv("data/raw/usgs/candidate_sites.csv", dtype={"site": str}).site
    out = [load_inws()]
    for s in sites:
        try:
            out.append(load_usgs(s))
        except FileNotFoundError:
            pass                                    # excluded site (no data for the year)
    return out
