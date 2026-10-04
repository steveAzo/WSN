"""Detector ROC: false alarms on clean data vs detection of injected events (detector only:
alarms depend on the node's true readings, not on the reporting decisions)."""
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, "src")
from sim.detector import make_detector  # noqa: E402
from sim.inject import resolution, noise_scale, hours, inject  # noqa: E402


def train_hours(ds):
    h = hours(ds); seg = np.cumsum(ds.seg_start); tr = ~ds.test
    return [h[(seg == s) & tr] for s in np.unique(seg[tr])]


def run_detector(ds, X, kw, res, trh):
    h = hours(ds); N, P = X.shape
    al = np.zeros((N, P), bool)
    for j in range(P):
        d = make_detector(ds.step_min, ds.train_segments(j), res[j], trh, kw)
        al[:, j] = d.run(X[:, j], h, ds.seg_start)
    return al


def roc(ds, grid, shapes=("step", "ramp"), amps=(3, 5, 8), durs=(60, 180, 360), seed=0):
    res = resolution(ds); sc = noise_scale(ds, res); trh = train_hours(ds)
    days = (ds.t[ds.test].iloc[-1] - ds.t[ds.test].iloc[0]).total_seconds() / 86400
    inj = {(s, a, d): inject(ds, s, a, d, seed=seed, scale=sc, res=res) for s in shapes for a in amps for d in durs}
    rows = []
    for kw in grid:
        al = run_detector(ds, ds.X, kw, res, trh)
        fa = al[ds.test].sum() / days * 30 / len(ds.params)
        for (s, a, d), (X, ev) in inj.items():
            ai = run_detector(ds, X, kw, res, trh)
            hit = [ai[e.s:e.e, int(e.j)].any() for e in ev.itertuples()]
            dl = [np.flatnonzero(ai[e.s:e.e, int(e.j)])[0] * ds.step_min for e in ev.itertuples() if ai[e.s:e.e, int(e.j)].any()]
            rows.append({"dataset": ds.name, **kw, "fa_per30d_param": fa, "shape": s, "amp": a, "dur": d,
                         "n": len(ev), "detect": np.mean(hit), "delay_med": np.median(dl) if dl else np.nan})
    return pd.DataFrame(rows)
