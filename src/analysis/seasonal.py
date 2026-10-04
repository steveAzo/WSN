"""Phase 1 — are the costliest months the most predictable? (out of sample)

For every dataset and calendar month m (>= 14 days of data, >= 30 days of earlier data):
  cost(m)  = send-on-delta report rate in month m (persistence DPS, per parameter), with
             tolerances delta: T 0.2 degC, DO 2 %sat, pH 0.1, EC 2 % of the site median.
  skill(m) = 1 - MSE(VAR)/MSE(last value) for 1-hour-ahead prediction in month m, with the
             model trained ONLY on data before month m (expanding window).
Then: Spearman correlation between cost and skill, pooled over site-months and within site.
"""
import sys
import warnings

import numpy as np
import pandas as pd

sys.path.insert(0, "src/analysis")
from check_a import lagged_design, load_inws, load_usgs  # noqa: E402
from theory_check import sod_rate  # noqa: E402

warnings.filterwarnings("ignore")
V = ["T", "EC", "DO", "pH"]


def deltas(df):
    return {"T": 0.2, "DO": 2.0, "pH": 0.1, "EC": 0.02 * float(df.EC.median())}


def monthly(df, name, h):
    df = df.copy(); df["m"] = df.t.dt.tz_localize(None).dt.to_period("M") if df.t.dt.tz else df.t.dt.to_period("M")
    dl, rows = deltas(df), []
    for v in V:
        D = lagged_design(df, V, v, h, own_only=False)
        D["m"] = pd.to_datetime(D.t).dt.tz_localize(None).dt.to_period("M") if pd.to_datetime(D.t).dt.tz else pd.to_datetime(D.t).dt.to_period("M")
        feats = [c for c in D.columns if c not in ("t", "y", "m")]
        for m, g in df.groupby("m"):
            span = (g.t.max() - g.t.min()).days
            tr, te = D[D.m < m], D[D.m == m]
            if len(tr) == 0:
                continue
            train_days = (pd.to_datetime(tr.t).max() - pd.to_datetime(tr.t).min()).days
            if span < 14 or len(te) < 200 or train_days < 30:
                continue
            A = np.c_[np.ones(len(tr)), tr[feats].values]
            b, *_ = np.linalg.lstsq(A, tr.y.values, rcond=None)
            e = te.y.values - np.c_[np.ones(len(te)), te[feats].values] @ b
            rows.append({"dataset": name, "param": v, "month": str(m), "cost": sod_rate(g, v, dl[v]),
                         "skill": 1 - np.mean(e ** 2) / np.mean(te.y.values ** 2)})
    return rows


if __name__ == "__main__":
    sites = pd.read_csv("data/raw/usgs/candidate_sites.csv", dtype={"site": str}).site.tolist()
    rows = monthly(load_inws(vars_=tuple(V)), "InWaterSense n1", 6)
    for s in sites:
        try:
            df, step = load_usgs(s)
        except FileNotFoundError:
            continue
        rows += monthly(df, s, int(round(60 / step)))
        print("done", s, flush=True)
    r = pd.DataFrame(rows)
    r.to_csv("results/phase1/seasonal.csv", index=False)
    u = r[r.dataset != "InWaterSense n1"]
    print(f"\nsite-months: USGS {u.groupby(['dataset','month']).ngroups}, InWaterSense {r[r.dataset=='InWaterSense n1'].month.nunique()}")
    print("param | pooled Spearman(cost, skill) | median within-site Spearman | n site-months | skill in costliest vs cheapest third")
    for v in V:
        g = u[u.param == v]
        within = g.groupby("dataset").apply(lambda x: x.cost.corr(x.skill, method="spearman") if len(x) >= 5 else np.nan)
        q = g.cost.quantile([1 / 3, 2 / 3])
        hi, lo = g[g.cost >= q.iloc[1]].skill.median(), g[g.cost <= q.iloc[0]].skill.median()
        print(f"{v:5s} | {g.cost.corr(g.skill, method='spearman'):+.2f} | {within.median():+.2f} | {len(g)} | {hi:+.2f} vs {lo:+.2f}")
    w = r[r.dataset == "InWaterSense n1"].pivot(index="month", columns="param", values=["cost", "skill"])
    print("\nInWaterSense monthly (out of sample):\n", w.round(3).to_string())
