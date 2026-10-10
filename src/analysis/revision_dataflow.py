"""Revision A10/A11: data-quality flow per dataset and the exact number of evaluated series.
raw -> approved (USGS) / plausible (InWaterSense) -> complete cycles -> simulated cycles and segments
(split at gaps > 60 min) -> training (first 20 %) / test. -> results/revision/a10_dataflow.csv
Usage: python src/analysis/revision_dataflow.py
"""
import json
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "src")
from sim.run_phase2 import dataset_names, get  # noqa: E402

uq = {q["file"][:8]: q for q in json.load(open("results/phase1/usgs_quality.json"))}
iq = json.load(open("results/phase1/inws_quality.json"))
rows = []
for name in dataset_names():
    ds = get(name)
    seg = int(ds.seg_start.sum()); n = len(ds.X)
    test_days = float((ds.t[ds.test].max() - ds.t[ds.test].min()).total_seconds() / 86400)
    step_d = float(np.median(np.diff(ds.t.values).astype("timedelta64[s]").astype(float))) / 86400
    train_data_days = (~ds.test).sum() * step_d
    row = {"dataset": name, "params_simulated": ",".join(ds.params), "n_params": len(ds.params),
           "sim_cycles": n, "sim_segments": seg, "train_cycles": int((~ds.test).sum()),
           "test_cycles": int(ds.test.sum()), "test_span_days": round(test_days),
           "train_share_of_cycles": round((~ds.test).mean(), 3), "train_data_days": round(train_data_days, 1)}
    if name.startswith("USGS"):
        q = uq[name.split()[1]]
        row.update({"raw_values": q["raw_values"], "approved_values": q["approved_values"],
                    "timestamps": q["timestamps"], "complete_cycles": q["complete_T_EC_DO_pH"],
                    "excluded_params": "-"})
    else:
        n1 = iq["nodes"]["1"]
        row.update({"raw_values": iq["raw_rows"], "approved_values": np.nan, "timestamps": n1["cycles"],
                    "complete_cycles": n1["complete_cycles"],
                    "excluded_params": f"pH (plausibility failures {n1['pH']['plaus_fail']} of {n1['cycles']} cycles)",
                    "range_fail_T_EC_DO": f"{n1['T']['range_fail']}/{n1['EC']['range_fail']}/{n1['DO']['range_fail']}",
                    "spike_flagged_kept_T_EC_DO": f"{n1['T']['spike_flag']}/{n1['EC']['spike_flag']}/{n1['DO']['spike_flag']}"})
    rows.append(row)
d = pd.DataFrame(rows)
d.to_csv("results/revision/a10_dataflow.csv", index=False)
pd.set_option("display.width", 250)
print(d.to_string(index=False))
print(f"\nsimulated site-parameter series: {d.n_params.sum()} ({len(d)} datasets); "
      f"Phase-1 predictability series: 56 (InWaterSense pH included there, excluded from simulation)")
