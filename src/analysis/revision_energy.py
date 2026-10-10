"""Revision A7 (review M12; analyses "Energy sensitivity" and "Payload realism"; minor comments on units,
battery voltage, idealisations, LoRaWAN duty cycle and ACK traffic).

1. One-at-a-time (tornado) sensitivity, NB-IoT N211 RAI and LoRaWAN SF12, median USGS rates at L2:
   outputs = battery life of RLS-D, and its gain over reporting every cycle. Each input is moved
   between a low and a high value with everything else at the default.
   -> results/revision/a7_tornado.csv
2. Payload realism: bytes of a bundled report (all parameters, sequence number, timestamp, flags),
   and LoRaWAN report energy / airtime vs payload size.  -> results/revision/a7_payload.csv
3. LoRaWAN duty cycle (ETSI 1 % per sub-band, EU868): airtime per day of each scheme, including
   retries of confirmed uplinks, against the 864 s/day limit.  -> results/revision/a7_dutycycle.csv
Usage: python src/analysis/revision_energy.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "src")
from energy import model as M  # noqa: E402
from energy import params as P  # noqa: E402

OUT = Path("results/revision"); OUT.mkdir(parents=True, exist_ok=True)
L = pd.read_csv("results/phase4/lifetime.csv")
u = L[L.dataset.str.startswith("USGS") & (L.radio == "NB-IoT N211 RAI") & (L.t_sense == "typical")
      & L.confirmed & L.battery.str.startswith("6600")]
SPD = u[u.method == "PERIODIC every cycle"].groupby("dataset").samples_per_day.first().median()
RPD = {lvl: u[(u.method == "RLS-D") & (u.level == lvl)].groupby("dataset").reports_per_day.first().median()
       for lvl in (1, 2, 3, 4)}
BAT = P.BATTERIES["6600 mAh Li-ion (Weija node, paper 22)"]


def life(rpd, rad, t_sense=5.0, loss=0.01, bat=BAT, host_awake=True, sleep_x=1.0, on_x=1.0, erep_x=1.0,
         usable=1.0):
    prof = dict(M.radio(rad))
    prof["e_report_ack"] *= erep_x; prof["e_report"] *= erep_x
    if not host_awake:
        prof["t_conn"] = 0.0
    keep_sleep, keep_on = P.P_HOST_SLEEP, P.P_HOST_ON
    P.P_HOST_SLEEP, P.P_HOST_ON = keep_sleep * sleep_x, keep_on * on_x
    try:
        tx = rpd * (1 + loss + loss ** 2)                 # confirmed uplink, up to two retries
        e = M.daily_energy(SPD, tx, prof, t_sense=t_sense, confirmed=True)["total"]
    finally:
        P.P_HOST_SLEEP, P.P_HOST_ON = keep_sleep, keep_on
    return M.lifetime_years(e, bat * usable)


# 1. tornado
FACTORS = [  # name, low kwargs, high kwargs, description
    ("sensing time per sample", {"t_sense": 1.0}, {"t_sense": 30.0}, "1 s / 30 s (default 5 s)"),
    ("report energy", {"erep_x": 0.5}, {"erep_x": 2.0}, "x0.5 / x2 of the measured median"),
    ("host sleep power", {"sleep_x": 7 / 33}, {"sleep_x": 3.0}, "hibernate 7 uA / 3 x deep sleep (default 33 uA)"),
    ("host active power", {"on_x": 0.7}, {"on_x": 1.3}, "-30 % / +30 %"),
    ("packet loss", {"loss": 0.005}, {"loss": 0.05}, "0.5 % / 5 % (default 1 %)"),
    ("host during modem activity", {"host_awake": False}, {"host_awake": True}, "asleep / awake (default awake)"),
    ("usable battery capacity", {"usable": 0.7}, {"usable": 1.0}, "70 % (self-discharge, cold, regulator) / ideal"),
    ("battery size", {"bat": P.BATTERIES["5 Wh (3GPP reference, papers 10/11)"]}, {"bat": BAT}, "5 Wh / 6600 mAh at 3.7 V"),
]
rows = []
for rad in ["NB-IoT N211 RAI", "NB-IoT N211 default", "LoRaWAN SF12", "LoRaWAN SF7"]:
    base_l = life(RPD[2], rad); base_g = base_l / life(SPD, rad)
    for name, lo, hi, desc in FACTORS:
        vals = {}
        for tag, kw in [("low", lo), ("high", hi)]:
            lr = life(RPD[2], rad, **kw); le = life(SPD, rad, **kw)
            vals[f"life_{tag}"], vals[f"gain_{tag}"] = lr, lr / le
        rows.append({"radio": rad, "factor": name, "setting": desc, "life_base": base_l, "gain_base": base_g, **vals})
t = pd.DataFrame(rows)
t["life_swing"] = (t.life_high - t.life_low).abs()
t = t.sort_values(["radio", "life_swing"], ascending=[True, False])
t.to_csv(OUT / "a7_tornado.csv", index=False, float_format="%.6g")
pd.set_option("display.width", 220)
print(f"median USGS rates: {SPD:.0f} samples/day; RLS-D reports/day L1-L4 = "
      + ", ".join(f"{v:.1f}" for v in RPD.values()))
print(t.drop(columns=["life_swing"]).round(2).to_string(index=False))

# 2. payload
# bundled report: 4 parameters as int16 scaled values (8 B) or float32 (16 B); sequence number 2 B;
# timestamp 4 B; flag byte 1 B (event alarm, heartbeat, resync). Link-layer headers/MIC are added by the
# radio stack and are already in the LoRaWAN frame model (13 B) and in the NB-IoT measurements.
pay = []
for lab, b in [("int16 values (4 params) + seq + time + flags", 8 + 2 + 4 + 1),
               ("float32 values (4 params) + seq + time + flags", 16 + 2 + 4 + 1),
               ("draft assumption", 20), ("LoRaWAN SF12 maximum (EU868, DR0)", 51)]:
    for sf in (7, 12):
        pay.append({"payload": lab, "bytes": b, "sf": sf, "airtime_ms": M.lora_frame_ms(sf, b),
                    "E_report_J": M.lora_report_energy(sf, b), "E_report_ack_J": M.lora_report_energy(sf, b, confirmed=True)})
pay = pd.DataFrame(pay)
for sf in (7, 12):
    ref = pay[(pay.sf == sf) & (pay.bytes == 20)].E_report_ack_J.item()
    pay.loc[pay.sf == sf, "E_ack_vs_20B"] = pay[pay.sf == sf].E_report_ack_J / ref
pay.to_csv(OUT / "a7_payload.csv", index=False, float_format="%.6g")
print("\n", pay.round(3).to_string(index=False))
# effect on the lifetime gain (SF12, confirmed) of the realistic payload range
for b in (15, 23):
    for sf in (12,):
        scale = M.lora_report_energy(sf, b, confirmed=True) / M.lora_report_energy(sf, 20, confirmed=True)
        g = life(RPD[2], f"LoRaWAN SF{sf}", erep_x=scale) / life(SPD, f"LoRaWAN SF{sf}", erep_x=scale)
        print(f"SF{sf}, {b}-byte payload: RLS-D L2 gain {g:.2f}x (20-byte: "
              f"{life(RPD[2], f'LoRaWAN SF{sf}') / life(SPD, f'LoRaWAN SF{sf}'):.2f}x)")

# 3. LoRaWAN duty cycle (EU868: 1 % per sub-band = 864 s/day of uplink airtime)
dc = []
for sf in (7, 12):
    air = M.lora_frame_ms(sf, 20) / 1e3
    for lab, rpd in [("every cycle", SPD)] + [(f"RLS-D L{k}", v) for k, v in RPD.items()]:
        for loss in (0.01, 0.05):
            tx = rpd * (1 + loss + loss ** 2)
            dc.append({"sf": sf, "scheme": lab, "loss": loss, "uplinks_per_day": tx, "airtime_s_per_day": tx * air,
                       "share_of_1pct_limit": tx * air / 864, "min_spacing_needed_s": air / 0.01,
                       "mean_spacing_s": 86400 / tx})
dc = pd.DataFrame(dc)
dc.to_csv(OUT / "a7_dutycycle.csv", index=False, float_format="%.6g")
print("\n", dc.round(3).to_string(index=False))
