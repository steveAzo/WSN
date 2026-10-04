"""Metrics computed on the TEST period only.

reports_per_day      : transmitted reports per day (separate mode counts one per parameter)
report_ratio         : reports / test steps  (1.0 = one report every cycle)
per parameter        : MAE, RMSE, max abs error, and (fixed-tolerance runs) the share of steps
                       with |error| > delta (must be 0 for bounded schemes)
events (offline reference labels, Check B): for each event of parameter p,
    delay_min   = time from event start to the first report that includes p (at/after start)
    captured    = delay_min <= event duration (the server learnt of it while it was ongoing)
    max_err_sig = max |error| inside the event window / that series' delta (or raw if none)
"""
import numpy as np
import pandas as pd


def compute(ds, res, delta=None, extra_delay_steps=None):
    te = ds.test
    days = (ds.t[te].iloc[-1] - ds.t[te].iloc[0]).total_seconds() / 86400
    E = np.abs(ds.X - res.R)
    if extra_delay_steps is not None:            # batching: exact values, delivered late
        E = np.zeros_like(E)
    out = {"reports_per_day": float(res.n_reports[te].sum() / days),
           "report_ratio": float(res.n_reports[te].sum() / te.sum())}
    for j, p in enumerate(ds.params):
        e = E[te, j]
        out[f"{p}_mae"] = float(e.mean()); out[f"{p}_rmse"] = float(np.sqrt((e ** 2).mean()))
        out[f"{p}_max"] = float(e.max())
        if delta is not None:
            out[f"{p}_viol"] = float((e > delta[j] + 1e-9).mean())
    if extra_delay_steps is not None:
        out["mean_delay_min"] = float(extra_delay_steps[te].mean() * ds.step_min)
    out.update(event_metrics(ds, res, E))
    return out


def event_metrics(ds, res, E):
    if ds.events is None or ds.events.empty:
        return {"n_events": 0}
    t = ds.t.to_numpy()
    rows = []
    for _, ev in ds.events.iterrows():
        j = ds.params.index(ev.param)
        s = np.searchsorted(t, np.datetime64(ev.start))
        e = np.searchsorted(t, np.datetime64(ev.end), side="right")
        if s >= len(t) or e <= s:
            continue
        nxt = np.flatnonzero(res.sent[s:, j])
        delay = (t[s + nxt[0]] - t[s]) / np.timedelta64(1, "m") if len(nxt) else np.inf
        dur = (t[e - 1] - t[s]) / np.timedelta64(1, "m") + ds.step_min
        rows.append({"param": ev.param, "delay": delay, "captured": delay <= dur,
                     "maxerr": float(E[s:e, j].max())})
    if not rows:
        return {"n_events": 0}
    r = pd.DataFrame(rows)
    return {"n_events": int(len(r)), "event_capture": float(r.captured.mean()),
            "event_delay_med_min": float(np.median(r.delay[np.isfinite(r.delay)])) if np.isfinite(r.delay).any() else np.nan,
            "event_delay_p90_min": float(np.percentile(r.delay[np.isfinite(r.delay)], 90)) if np.isfinite(r.delay).any() else np.nan}
