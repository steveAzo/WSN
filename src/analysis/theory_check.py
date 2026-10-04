"""Feasibility test for the theoretical angle (not a final result).

Hypothesis: for a "local level" signal x_t = L_t + e_t (L random walk with step variance q,
e white sensor noise with variance r), the report rate of send-on-delta (persistence DPS,
report when |x_t - x_last_sent| > delta) is predictable from (q, r) alone.
(q, r) are fitted on a short TRAINING window from the variogram V(k) = k*q + 2r,
then the predicted report rate (Monte Carlo of the fitted model) is compared with the
actual send-on-delta report rate on the TEST window.
"""
import sys
import numpy as np
import pandas as pd


def variogram_fit(df, v, kmax=6):
    ks, vs = [], []
    for k in range(1, kmax + 1):
        d = df.groupby("segment")[v].diff(k).dropna()
        ks.append(k); vs.append(np.mean(d ** 2))
    q, two_r = np.polyfit(ks, vs, 1)
    return max(q, 1e-12), max(two_r / 2, 0.0)


def sod_rate(df, v, delta):
    """actual reports per sample of send-on-delta (persistence) within segments"""
    reports, n = 0, 0
    for _, s in df.groupby("segment"):
        x = s[v].values
        last = x[0]; reports += 1; n += len(x)
        for xi in x[1:]:
            if abs(xi - last) > delta:
                reports += 1; last = xi
    return reports / n


def model_rate(q, r, delta, n=200_000, seed=0):
    rng = np.random.default_rng(seed)
    L = np.cumsum(rng.normal(0, np.sqrt(q), n)); x = L + rng.normal(0, np.sqrt(r), n)
    last, rep = x[0], 1
    for xi in x[1:]:
        if abs(xi - last) > delta:
            rep += 1; last = xi
    return rep / n


def run(df, v, deltas, label):
    t_split = df.t.quantile(0.3)                      # train on first 30 % only
    tr, te = df[df.t < t_split], df[df.t >= t_split]
    q, r = variogram_fit(tr, v)
    print(f"\n{label} {v}: fitted q={q:.4g}, r={r:.4g}  (sensor-noise share at lag1 = {2*r/(q+2*r):.2f})")
    for d in deltas:
        a, m = sod_rate(te, v, d), model_rate(q, r, d)
        print(f"  delta={d:<6} actual reports/sample={a:.4f}  predicted={m:.4f}  ratio={m/a:.2f}")


if __name__ == "__main__":
    c = pd.read_csv("data/clean/inws_cycles.csv", parse_dates=["t"])
    c = c[(c.node == 1)].dropna(subset=["T", "EC", "DO"])
    c = c[c.groupby("segment").t.transform("size") >= 144]
    run(c, "T", [0.1, 0.2, 0.5, 1.0], "InWaterSense n1")
    run(c, "EC", [2, 5, 10, 20], "InWaterSense n1")
    run(c, "DO", [1, 2, 5, 10], "InWaterSense n1")
    u = pd.read_csv("data/clean/usgs/01458500.csv", parse_dates=["t"]).dropna(subset=["T", "EC", "DO"])
    u = u[u.groupby("segment").t.transform("size") >= 96]
    run(u, "T", [0.1, 0.2, 0.5, 1.0], "USGS 01458500")
    run(u, "EC", [2, 5, 10, 20], "USGS 01458500")
    run(u, "DO", [1, 2, 5, 10], "USGS 01458500")
