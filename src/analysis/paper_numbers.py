"""Every number quoted in the Paper 1 draft, regenerated from the result files.

The draft (papers/paper1/draft/) must only quote values printed by this script, so a reviewer
(or us) can re-check each one. Run after all phases: python src/analysis/paper_numbers.py
Output: papers/paper1/draft/numbers/*.csv and a printed summary.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "src")
OUT = Path("papers/paper1/draft/numbers"); OUT.mkdir(parents=True, exist_ok=True)
pd.set_option("display.width", 220); pd.set_option("display.max_columns", 30)


def datasets():
    from sim.run_phase2 import dataset_names, get
    meta = pd.read_csv("data/raw/usgs/candidate_sites.csv", dtype={"site": str}).set_index("site")
    tune = set(pd.read_json("results/phase3/rlsd_choice.json").tuning_sites)
    rows = []
    for n in dataset_names():
        ds = get(n); get.cache_clear()
        s = n.split()[1] if n.startswith("USGS") else None
        rows.append(dict(
            dataset=n, name=meta.loc[s, "name"] if s else "InWaterSense node 1 (Sitnica, Kosovo)",
            state=meta.loc[s, "state"] if s else "XK", stratum=meta.loc[s, "stratum"] if s else "real deployment",
            role="tuning" if n in tune else "test", params="+".join(ds.params), step_min=round(ds.step_min, 1),
            cycles=len(ds.X), start=str(ds.t.iloc[0].date()), end=str(ds.t.iloc[-1].date()),
            test_days=round((ds.t[ds.test].iloc[-1] - ds.t[ds.test].iloc[0]).total_seconds() / 86400),
            segments=int(ds.seg_start.sum()), test_events=0 if ds.events is None else len(ds.events)))
    d = pd.DataFrame(rows)
    d.to_csv(OUT / "datasets.csv", index=False)
    print(d.drop(columns=["name"]).to_string(index=False))
    return d


def phase1():
    """Check A (1-h, out of sample), diel link, seasonal link, Check B events"""
    from scipy.stats import spearmanr
    a = pd.read_csv("results/phase1/check_a_summary.csv", dtype={"site": str})
    u, i = a[~a.site.str.startswith("InWater")], a[a.site.str.startswith("InWater")]
    t = u.groupby("param").agg(n=("site", "size"), ar_gt10=("skill_AR", lambda s: int((s > 0.10).sum())),
                               var_gt10=("skill_VAR", lambda s: int((s > 0.10).sum())),
                               cross_helps=("cross_helps", "sum"), med_var_over_ar=("VAR/AR", "median"),
                               min_var_over_ar=("VAR/AR", "min"))
    print(t.to_string()); print("InWaterSense skill_VAR:", i.set_index("param").skill_VAR.to_dict(),
                                "cross_helps:", int(i.cross_helps.sum()))
    rho = spearmanr(u.diel_share, u.skill_VAR)
    print(f"USGS site-params: Spearman(diel, skill_VAR) = {rho[0]:.2f} (p={rho[1]:.1e}), n={len(u)}")
    for v in ("T", "EC", "DO", "pH"):
        g = u[u.param == v]; print(f"   {v}: rho={spearmanr(g.diel_share, g.skill_VAR)[0]:.2f}, diel range {g.diel_share.min():.2f}-{g.diel_share.max():.2f}")
    print("InWaterSense diel:", i.set_index("param").diel_share.to_dict())
    s = pd.read_csv("results/phase1/seasonal.csv"); s = s[s.dataset != "InWaterSense n1"]
    print("seasonal: site-months", s.groupby(["dataset", "month"]).ngroups)
    for v in ("T", "EC", "DO", "pH"):
        g = s[s.param == v]; q = g.cost.quantile([1 / 3, 2 / 3])
        print(f"   {v}: rho(cost,skill)={spearmanr(g.cost, g.skill)[0]:+.2f}  skill costliest third {g[g.cost >= q.iloc[1]].skill.median():.2f} cheapest {g[g.cost <= q.iloc[0]].skill.median():.2f}  min skill {g.skill.min():.2f}")
    b = pd.read_csv("results/phase1/check_b_runs.csv"); bu = b[~b.dataset.str.startswith("InWater")]
    print("Check B USGS: events", int((bu.kind == "event").sum()), "glitches", int((bu.kind == "glitch").sum()),
          "| InWaterSense events", int(((b.kind == "event") & b.dataset.str.startswith("InWater")).sum()),
          "glitches", int(((b.kind == "glitch") & b.dataset.str.startswith("InWater")).sum()))
    sm = pd.read_csv("results/phase1/check_b_summary.csv"); sm = sm[~sm.dataset.str.startswith("InWater")]
    print(sm.groupby("param")[["events_per_30d", "coherent_share"]].median().to_string())


def alarm_coincidence(win_h=2.0):
    """How many 'false' alarms of the chosen detector (clean test data) fall within win_h of a Check B
    reference event on the same parameter, vs the number expected by chance (share of test time
    covered by the +-win_h-widened event windows x alarms). Re-derivation 2026-10-04: the Phase 3
    report's '523 of 996, 87 expected' was not saved by any script."""
    import json
    from sim.roc_detector import run_detector, train_hours
    from sim.inject import resolution
    from sim.run_phase2 import dataset_names, get
    cfg = json.load(open("results/phase3/detector_choice.json"))["config"]
    rows = []
    for n in dataset_names():
        ds = get(n); get.cache_clear()
        al = run_detector(ds, ds.X, cfg, resolution(ds), train_hours(ds))
        t = ds.t.to_numpy(); te = ds.test
        w = np.timedelta64(int(win_h * 60), "m")
        for j, p in enumerate(ds.params):
            near = np.zeros(len(t), bool)
            ev = ds.events[ds.events.param == p] if ds.events is not None else []
            for _, e in (ev.iterrows() if len(ev) else []):
                near |= (t >= np.datetime64(e.start) - w) & (t <= np.datetime64(e.end) + w)
            a = al[:, j] & te
            rows.append({"dataset": n, "param": p, "alarms": int(a.sum()), "near": int((a & near).sum()),
                         "expected": float(a.sum() * near[te].mean())})
    d = pd.DataFrame(rows); d.to_csv(OUT / "alarm_coincidence.csv", index=False)
    tot = d[["alarms", "near", "expected"]].sum()
    print(d.groupby("dataset")[["alarms", "near", "expected"]].sum().round(1).to_string())
    print(f"TOTAL alarms {tot.alarms}, within {win_h} h of a reference event {tot.near}, expected by chance {tot.expected:.0f}"
          f" -> enrichment {tot.near / tot.expected:.1f}x")


def energy_rlsd_over_sod():
    """per-site lifetime gain of RLS-D over SOD (median and max over USGS sites), by radio, sensing
    time and level. NOTE p4_gain_by_level.csv pools all sensing times; the paper quotes 5 s ('typical')."""
    d = pd.read_csv("results/phase4/lifetime.csv")
    u = d[d.confirmed & d.battery.str.startswith("6600") & d.dataset.str.startswith("USGS")]
    k = u[u.method.isin(["SOD", "RLS-D"]) & u.level.between(1, 4)]
    p = k.pivot_table(index=["radio", "t_sense", "dataset", "level"], columns="method", values="lifetime_y")
    p["gain_pct"] = 100 * (p["RLS-D"] / p["SOD"] - 1)
    t = p.groupby(["radio", "t_sense", "level"]).gain_pct.agg(["median", "max"]).round(1).unstack("level")
    t.to_csv(OUT / "energy_rlsd_over_sod.csv")
    print(t.xs("typical", level="t_sense").to_string())


if __name__ == "__main__":
    which = sys.argv[1:] or ["datasets"]
    for w in which:
        print(f"\n===== {w}"); globals()[w]()
