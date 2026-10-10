"""Revision A8 (review "Predictability measures": estimator uncertainty and minimum data; M2: ranking
evidence vs deployment-time prediction).

Diel share is the site mean over parameters of Var(hour-of-day profile of the within-day anomaly) /
Var(anomaly), exactly as in Phase 1 (summarize_check_a.diel_share, local standard time).
For window lengths of 1, 2, 4, 8 and 13 weeks we compute it on every non-overlapping window with at
least 70 % of the expected samples, and ask:
  (a) how far a k-week estimate falls from the full-year value (per site: median abs. deviation, range);
  (b) whether k weeks still RANK sites by their RLS-T saving at L2: Spearman rho between the k-week site
      means and the saving, over 2000 random draws of one window per site (sites drawn independently),
      and for the FIRST k weeks of every series (the deployment case).
-> results/revision/a8_diel_windows.csv, a8_diel_rank.csv
Usage: python src/analysis/revision_diel.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, "src/analysis")
from summarize_check_a import diel_share  # noqa: E402

OUT = Path("results/revision"); OUT.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(20261010)
meta = pd.read_csv("data/raw/usgs/candidate_sites.csv", dtype={"site": str}).set_index("site")
WEEKS = [1, 2, 4, 8, 13]


def series():
    c = pd.read_csv("data/clean/inws_cycles.csv", parse_dates=["t"]); c = c[c.node == 1]
    yield "InWaterSense n1", c, 0, ["T", "EC", "DO", "pH"]
    for site in meta.index:
        f = Path(f"data/clean/usgs/{site}.csv")
        if not f.exists():
            continue
        tz = -8 if meta.loc[site, "state"] == "OR" else (-6 if meta.loc[site, "state"] == "IL" else -5)
        yield f"USGS {site}", pd.read_csv(f, parse_dates=["t"]), tz, ["T", "EC", "DO", "pH"]


def site_diel(df, tz, params):
    v = []
    for p in params:
        if p in df and df[p].notna().sum() > 48:
            try:
                v.append(diel_share(df, p, tz))
            except ZeroDivisionError:
                pass
    v = [x for x in v if np.isfinite(x)]
    return np.mean(v) if v else np.nan


rows = []
full = {}
for name, df, tz, params in series():
    df = df.sort_values("t")
    full[name] = site_diel(df, tz, params)
    step = df.t.diff().median()
    t0 = df.t.min().floor("D")
    for k in WEEKS:
        span = pd.Timedelta(weeks=k); need = 0.7 * span / step
        w = 0
        while t0 + (w + 1) * span <= df.t.max():
            sub = df[(df.t >= t0 + w * span) & (df.t < t0 + (w + 1) * span)]
            if len(sub) >= need:
                rows.append({"dataset": name, "weeks": k, "window": w, "first": w == 0,
                             "diel": site_diel(sub, tz, params)})
            w += 1
    print(name, round(full[name], 3), flush=True)
win = pd.DataFrame(rows)
win["full"] = win.dataset.map(full)
win.to_csv(OUT / "a8_diel_windows.csv", index=False, float_format="%.6g")

# check against the Phase 1 site means used in the paper
a = pd.read_csv("results/phase1/check_a_summary.csv", dtype={"site": str})
a["site"] = a.site.where(a.site.str.startswith("InWater"), "USGS " + a.site.str[:8])
ph1 = a.groupby("site").diel_share.mean()
for k, v in full.items():
    if k in ph1:
        assert abs(v - ph1[k]) < 0.002, (k, v, ph1[k])

# (a) deviation from the full-year value
dev = win.assign(absdev=(win.diel - win.full).abs()).groupby("weeks").agg(
    n_windows=("diel", "size"), median_absdev=("absdev", "median"), p90_absdev=("absdev", lambda s: s.quantile(0.9)))
print("\n(a) |k-week estimate - full-year value| (site mean over parameters)\n", dev.round(3))

# (b) ranking of the L2 saving from k weeks
r = pd.read_csv("results/phase2/results.csv")
g = r[(r["mode"] == "report") & (r.level == 2)].pivot_table(index="dataset", columns="kind", values="reports_per_day")
gain = 100 * (1 - g["RLS-T"] / g["SOD"])
out = [{"weeks": "full year", "n_sites": len(gain), "draw": "-", "rho_median": spearmanr([full[d] for d in gain.index], gain)[0],
        "rho_p05": np.nan, "rho_p95": np.nan}]
for k in WEEKS:
    e = win[win.weeks == k]
    ds_ok = [d for d in gain.index if (e.dataset == d).any()]          # sites with >= 1 valid window
    by = {d: e[e.dataset == d].diel.values for d in ds_ok}
    gk = gain.reindex(ds_ok)
    rhos = [spearmanr([rng.choice(by[d]) for d in ds_ok], gk)[0] for _ in range(2000)]
    out.append({"weeks": k, "n_sites": len(ds_ok), "draw": "random window per site", "rho_median": np.median(rhos),
                "rho_p05": np.percentile(rhos, 5), "rho_p95": np.percentile(rhos, 95)})
    first = e.sort_values("window").groupby("dataset").diel.first().reindex(ds_ok)   # first VALID window
    out.append({"weeks": k, "n_sites": len(ds_ok), "draw": "first valid k weeks (deployment)",
                "rho_median": spearmanr(first, gk)[0], "rho_p05": np.nan, "rho_p95": np.nan})
out = pd.DataFrame(out)
out.to_csv(OUT / "a8_diel_rank.csv", index=False, float_format="%.6g")
print("\n(b) Spearman rho(k-week diel share, RLS-T saving at L2), 14 datasets\n", out.round(2).to_string(index=False))
