"""Phase 1, Check A — is there short-term cross-parameter structure a DPS can exploit?

Two distinct questions (they are often confused; see PAPER1_PLAN.md):
 (a) Do the parameters' *surprises* co-occur?  -> contemporaneous correlation of
     innovations (first differences and univariate-AR residuals). If positive, threshold
     exceedances cluster, so one report-level decision costs less than per-parameter
     decisions (RQ1).
 (b) Do *past* values of the other parameters improve prediction out of sample?
     In a suppressed report the server knows only past (reconstructed) values, so only
     lagged cross-parameter information is usable (VAR vs univariate AR) (RQ2).
Level correlations are reported only to reproduce paper 20 (they are mostly seasonal).

All models are fitted on the chronologically first half and evaluated on the second
half, within contiguous segments only (no lag ever crosses a gap).
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

P_LAGS = 3                    # AR / VAR order (on differences)
HORIZONS = [1, 6, 36]         # steps ahead: 10 min, 1 h, 6 h for 10-min data


def lagged_design(df, vars_, target, h, own_only):
    """Direct h-step model on differences: x[t+h]-x[t] ~ lags of dx (own or all vars)."""
    rows = []
    for _, s in df.groupby("segment"):
        if len(s) < P_LAGS + h + 2:
            continue
        dx = s[vars_].diff()
        y = s[target].shift(-h) - s[target]
        cols = [target] if own_only else vars_
        X = pd.concat({f"{c}_l{j}": dx[c].shift(j) for c in cols for j in range(P_LAGS)}, axis=1)
        X["t"] = s["t"].values
        X["y"] = y.values
        rows.append(X.dropna())
    return pd.concat(rows) if rows else pd.DataFrame()


def fit_predict(D, split_t):
    tr, te = D[D.t < split_t], D[D.t >= split_t]
    feats = [c for c in D.columns if c not in ("t", "y")]
    A = np.c_[np.ones(len(tr)), tr[feats].values]
    beta, *_ = np.linalg.lstsq(A, tr.y.values, rcond=None)
    pred = np.c_[np.ones(len(te)), te[feats].values] @ beta
    return te.y.values, pred


def block_bootstrap_ratio(e_a, e_b, days, n=500, seed=0):
    """95% CI of MSE(b)/MSE(a) resampling whole days (keeps autocorrelation)."""
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({"a": e_a ** 2, "b": e_b ** 2, "d": days})
    g = df.groupby("d")[["a", "b"]].sum()
    vals = g.values
    rs = [vals[rng.integers(0, len(vals), len(vals))].sum(0) for _ in range(n)]
    r = np.array([b / a for a, b in rs])
    return float(np.percentile(r, 2.5)), float(np.percentile(r, 97.5))


def check_a(df, vars_, name, horizons=HORIZONS):
    out = {"dataset": name, "vars": vars_, "n": int(len(df))}
    # (0) level correlation, to reproduce paper 20
    out["corr_levels"] = df[vars_].corr().round(3).to_dict()
    # (a) contemporaneous correlation of innovations
    d1 = df.groupby("segment")[vars_].diff()
    out["corr_first_diff"] = d1.corr().round(3).to_dict()
    res = {}
    for v in vars_:
        D = lagged_design(df, vars_, v, 1, own_only=True)
        split = D.t.quantile(0.5)
        y, p = fit_predict(D, split)
        res[v] = pd.Series(y - p, index=D[D.t >= split].t.values)
    R = pd.DataFrame(res).dropna()
    out["corr_ar_residuals"] = R.corr().round(3).to_dict()
    # (b) out-of-sample skill: persistence vs AR (own lags) vs VAR (all lags)
    skill = {}
    for h in horizons:
        for v in vars_:
            Da = lagged_design(df, vars_, v, h, own_only=True)
            Dv = lagged_design(df, vars_, v, h, own_only=False)
            split = Da.t.quantile(0.5)
            Dv = Dv[Dv.t.isin(Da.t)]; Da = Da[Da.t.isin(Dv.t)]
            ya, pa = fit_predict(Da, split)
            yv, pv = fit_predict(Dv, split)
            days = pd.to_datetime(Da[Da.t >= split].t).dt.floor("D").values
            mse_pers, mse_ar, mse_var = np.mean(ya ** 2), np.mean((ya - pa) ** 2), np.mean((yv - pv) ** 2)
            lo, hi = block_bootstrap_ratio(ya - pa, yv - pv, days)
            skill[f"h{h}_{v}"] = {
                "mse_persistence": mse_pers, "skill_AR_vs_pers": 1 - mse_ar / mse_pers,
                "skill_VAR_vs_pers": 1 - mse_var / mse_pers,
                "VAR_over_AR_mse_ratio": mse_var / mse_ar, "ratio_95ci": [lo, hi], "n_test": int(len(ya))}
    out["oos_skill"] = skill
    return out


def load_inws(node=1, vars_=("T", "EC", "DO"), min_seg=144):
    c = pd.read_csv("data/clean/inws_cycles.csv", parse_dates=["t"])
    c = c[(c.node == node)].dropna(subset=list(vars_))
    seglen = c.groupby("segment").t.transform("size")
    return c[seglen >= min_seg].sort_values("t")


def summarize(r):
    print(f"\n=== {r['dataset']} (n={r['n']}) ===")
    for k in ("corr_levels", "corr_first_diff", "corr_ar_residuals"):
        print(k); print(pd.DataFrame(r[k]).to_string())
    print("out-of-sample: skill vs persistence (AR, VAR); VAR/AR MSE ratio [95% CI]")
    for k, s in r["oos_skill"].items():
        print(f"  {k:10s} AR {s['skill_AR_vs_pers']:+.3f}  VAR {s['skill_VAR_vs_pers']:+.3f}  "
              f"VAR/AR {s['VAR_over_AR_mse_ratio']:.3f} [{s['ratio_95ci'][0]:.3f}, {s['ratio_95ci'][1]:.3f}]  n={s['n_test']}")


def load_usgs(site, vars_=("T", "EC", "DO", "pH"), min_seg_hours=24):
    c = pd.read_csv(f"data/clean/usgs/{site}.csv", parse_dates=["t"]).dropna(subset=list(vars_))
    step = c.t.diff().dt.total_seconds().median() / 60
    seglen = c.groupby("segment").t.transform("size")
    return c[seglen * step >= min_seg_hours * 60].sort_values("t"), step


if __name__ == "__main__":
    Path("results/phase1").mkdir(parents=True, exist_ok=True)
    if len(sys.argv) > 1 and sys.argv[1] == "usgs":
        for site in sys.argv[2:]:
            df, step = load_usgs(site)
            hz = [1, int(60 / step), int(360 / step)]          # one step, 1 h, 6 h
            r = check_a(df, ["T", "EC", "DO", "pH"], f"USGS {site} (step {step:.0f} min)", hz)
            summarize(r)
            Path(f"results/phase1/check_a_usgs_{site}.json").write_text(json.dumps(r, indent=2, default=float))
    else:
        results = []
        for vars_ in (["T", "EC", "DO"], ["T", "EC", "DO", "pH"]):
            r = check_a(load_inws(vars_=tuple(vars_)), vars_, f"InWaterSense node 1 {'+'.join(vars_)}")
            summarize(r); results.append(r)
        Path("results/phase1/check_a_inws.json").write_text(json.dumps(results, indent=2, default=float))
