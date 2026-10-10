"""Weija held-out test: diagnostics behind results/weija/WEIJA_REPORT.md (run after
run_phase2.py / run_phase3.py with --datasets Weija).

  1. link     : Phase 2 diel-share -> RLS-T gain link, 14 datasets vs 15 with Weija (Spearman)
  2. where    : per-parameter and time-of-day reports at L2 (separate mode)
  3. history  : report rate on test steps with a full 24-step history only
  4. probes   : sensitivity to the T probe (Sensor One) and to single parameters
  5. thinning : CONTROL - USGS sites thinned 15 -> 30 min, all params and T+EC only
  6. post hoc : forecastable diel share (prior-7-day profile) and diel-anomaly skewness
                (hypotheses for WHY, chosen after seeing the miss -> labelled post hoc)
Output: results/weija/diagnostics.json.   Usage: python src/analysis/weija_diagnostics.py
"""
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, "src"); sys.path.insert(0, "src/analysis")
from sim import data as D  # noqa: E402
from sim.engine import run_dps  # noqa: E402
from sim.metrics import compute  # noqa: E402
from sim.run_phase2 import deltas, get, make_factory  # noqa: E402
from summarize_check_a import diel_share  # noqa: E402

warnings.filterwarnings("ignore")
OUT = Path("results/weija/diagnostics.json")
THIN_SITES = ["01475530", "01400500", "01458500", "01473500"]   # 3 high-gain + 1 low-gain USGS
SIMULATED = {"Weija": ["T", "EC"], "InWaterSense n1": ["T", "EC", "DO"]}


def tz_of(state):
    return -8 if state == "OR" else (-6 if state == "IL" else -5)


def gains(level):
    r = pd.concat([pd.read_csv("results/phase2/results.csv"), pd.read_csv("results/weija/phase2.csv")])
    g = r[(r["mode"] == "report") & (r.level == level)].pivot_table(index="dataset", columns="kind",
                                                                    values="reports_per_day")
    return 100 * (1 - g["RLS-T"] / g["SOD"])


def link():
    a = pd.read_csv("results/phase1/check_a_summary.csv", dtype={"site": str})
    a["site"] = a.site.where(a.site.str.startswith("InWater"), "USGS " + a.site.str[:8])
    s = a.groupby("site").agg(diel=("diel_share", "mean"), skill=("skill_AR", "mean"))
    w = json.load(open("results/weija/phase1.json"))["T+EC"]
    s.loc["Weija"] = [np.mean(list(w["diel_share"].values())),
                      np.mean([w["oos_skill"]["h2_T"]["skill_AR_vs_pers"], w["oos_skill"]["h2_EC"]["skill_AR_vs_pers"]])]
    out = {}
    for lvl in range(5):
        d = s.join(gains(lvl).rename("gain")).dropna(); o = d.drop("Weija")
        out[f"L{lvl}"] = {"weija_gain": round(float(d.gain["Weija"]), 1),
                          "weija_rank_of_15": int(d.gain.rank()["Weija"]),
                          **{f"rho_{m}_{k}": round(float(spearmanr(e[m], e.gain)[0]), 2)
                             for m in ("diel", "skill") for k, e in (("14", o), ("15", d))},
                          "p_diel_15": round(float(spearmanr(d.diel, d.gain)[1]), 4)}
    return out


def where():
    ds = get("Weija"); te = ds.test; dl = deltas(ds, 2)
    days = (ds.t[te].iloc[-1] - ds.t[te].iloc[0]).total_seconds() / 86400
    hr = ds.t.dt.hour.to_numpy()
    out = {}
    for k in ("SOD", "DBP", "RLS-T"):
        s = run_dps(ds.X, ds.seg_start, make_factory(ds, k, dl), mode="separate", delta=dl).sent[te]
        out[k] = {"T_per_day": round(s[:, 0].sum() / days, 2), "EC_per_day": round(s[:, 1].sum() / days, 2),
                  "T_share_10_16h": round(s[(hr[te] >= 10) & (hr[te] < 16), 0].sum() / s[:, 0].sum(), 2),
                  "T_per_day_00_06h": round(s[hr[te] < 6, 0].sum() / days, 2)}
    return out


def history():
    ds = get("Weija"); te = ds.test; dl = deltas(ds, 2)
    seg = np.cumsum(ds.seg_start)
    pos = pd.Series(1, index=range(len(seg))).groupby(seg).cumcount().to_numpy()
    full = te & (pos >= 24)
    out = {"test_share_short_history": round(float((te & (pos < 24)).sum() / te.sum()), 3)}
    for k in ("SOD", "DBP", "RLS-T"):
        r = run_dps(ds.X, ds.seg_start, make_factory(ds, k, dl), mode="report", delta=dl)
        out[k] = {"per_step_full_history": round(float(r.n_reports[full].mean()), 3),
                  "per_step_all_test": round(float(r.n_reports[te].mean()), 3)}
    return out


def probes():
    c = pd.read_csv("data/clean/weija_cycles.csv", parse_dates=["t"])
    out = {}
    for nm, cols, src in [("T1+EC", ["T", "EC"], "T1"), ("T only", ["T"], "T"),
                          ("T1 only", ["T"], "T1"), ("EC only", ["EC"], None)]:
        d = c.copy()
        if src:
            d["T"] = d[src]
        ds = D._finish("Weija " + nm, d, cols, None)
        dl = deltas(ds, 2) if "EC" in cols else np.array([0.2])
        rp = {m: compute(ds, run_dps(ds.X, ds.seg_start, make_factory(ds, m, dl), mode="report", delta=dl),
                         dl)["reports_per_day"] for m in ("SOD", "DBP", "RLS-T")}
        out[nm] = {**{m: round(v, 2) for m, v in rp.items()}, "gain_RLST": round(100 * (1 - rp["RLS-T"] / rp["SOD"]), 1)}
    return out


def thinning():
    out = []
    for site in THIN_SITES:
        for params in (["T", "EC", "DO", "pH"], ["T", "EC"]):
            for k in (1, 2):
                d = pd.read_csv(f"data/clean/usgs/{site}.csv", parse_dates=["t"]).dropna(subset=params).iloc[::k]
                ds = D._finish(f"USGS {site} /{k}", d, params, None); dl = deltas(ds, 2)
                rp = {m: compute(ds, run_dps(ds.X, ds.seg_start, make_factory(ds, m, dl), mode="report", delta=dl),
                                 dl)["reports_per_day"] for m in ("SOD", "RLS-T")}
                out.append({"site": site, "params": "+".join(params), "step_min": round(ds.step_min),
                            "gain_RLST": round(100 * (1 - rp["RLS-T"] / rp["SOD"]), 1)})
                print(out[-1], flush=True)
    return out


def fdiel(df, v, tz=0):
    """1 - SSE(today's hourly anomaly profile vs mean profile of the previous 7 days) / SS(today)"""
    s = df.set_index("t")[v].dropna()
    s.index = (s.index.tz_localize(None) if s.index.tz is not None else s.index) + pd.Timedelta(hours=tz)
    H = s.groupby([s.index.floor("D"), s.index.hour]).mean().unstack()
    A = H[H.notna().sum(1) >= 20]
    A = A.sub(A.mean(1), axis=0)
    num = den = 0.0
    for d in A.index:
        prev = A[(A.index < d) & (A.index >= d - pd.Timedelta(days=7))]
        if len(prev) < 3:
            continue
        p, x = prev.mean(), A.loc[d]; m = x.notna() & p.notna()
        num += ((x[m] - p[m]) ** 2).sum(); den += (x[m] ** 2).sum()
    return 1 - num / den


def skew(df, v):
    s = df.set_index("t")[v].dropna()
    a = s - s.groupby(s.index.floor("D")).transform("mean")
    return float(a.skew())


def post_hoc():
    meta = pd.read_csv("data/raw/usgs/candidate_sites.csv", dtype={"site": str}).set_index("site")
    rows = []
    w = pd.read_csv("data/clean/weija_cycles.csv", parse_dates=["t"])
    for v in ("T", "EC"):
        rows.append(("Weija", v, diel_share(w.dropna(subset=[v]), v), fdiel(w, v), skew(w, v)))
    c = pd.read_csv("data/clean/inws_cycles.csv", parse_dates=["t"]); c = c[c.node == 1]
    for v in ("T", "EC", "DO", "pH"):
        rows.append(("InWaterSense n1", v, diel_share(c.dropna(subset=[v]), v), fdiel(c, v), skew(c, v)))
    for s in meta.index:
        f = Path(f"data/clean/usgs/{s}.csv")
        if not f.exists():
            continue
        d = pd.read_csv(f, parse_dates=["t"])
        for v in ("T", "EC", "DO", "pH"):
            rows.append((f"USGS {s}", v, diel_share(d.dropna(subset=[v]), v), fdiel(d, v, tz_of(meta.loc[s, "state"])), skew(d, v)))
    R = pd.DataFrame(rows, columns=["site", "param", "diel", "fdiel", "skew"])
    keep = R.apply(lambda x: x.param in SIMULATED.get(x.site, ["T", "EC", "DO", "pH"]), axis=1)
    S = R[keep].groupby("site")[["diel", "fdiel"]].mean().join(gains(2).rename("gain")).dropna()
    return {"per_param_T": R[R.param == "T"].round(3).to_dict("records"),
            "rho_fdiel_15": round(float(spearmanr(S.fdiel, S.gain)[0]), 2),
            "rho_fdiel_14": round(float(spearmanr(S.drop("Weija").fdiel, S.drop("Weija").gain)[0]), 2)}


def main():
    # resumable: each stage is saved as soon as it finishes (the laptop runs out of memory at times)
    res = json.loads(OUT.read_text()) if OUT.exists() else {}
    for name, f in (("link", link), ("where_L2", where), ("history_L2", history), ("probes_L2", probes),
                    ("thinning_L2", thinning), ("post_hoc", post_hoc)):
        if name in res:
            continue
        res[name] = f(); print(name, "done", flush=True)
        OUT.write_text(json.dumps(res, indent=2, default=float))
    print(json.dumps({k: v for k, v in res.items() if k not in ("post_hoc", "thinning_L2")}, indent=1))


if __name__ == "__main__":
    main()
