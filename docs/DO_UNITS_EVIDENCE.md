# What unit is "DissolvedOxygen" in the InWaterSense dataset?

*Investigation of 2026-10-03. Conclusion: the values are almost certainly **% saturation** (relative to an air-saturated calibration), not mg/L. Absolute accuracy is questionable in some periods.*

## The problem
- Papers 20 (Ahmedi & Makolli 2023) and 21 (Macêdo et al. 2025) label DO as mg/L (mg·dm⁻³). Paper 16 (the dataset article) gives no unit.
- The recorded values range from 0 to 154.6 (median 19.3). That is impossible in mg/L: fresh water saturates at about 14.6 mg/L at 0 °C. The sensor itself is specified for 0–20 mg/L.
- The fitted relation DO = −5.09·T + 105.5 (paper 20) has a slope about 25× the physical solubility effect in mg/L (≈ −0.2 mg/L per °C).

## Evidence

**1. The manufacturer's own conversion code returns a percentage.** The deployment used Libelium Waspmote Plug & Sense Smart Water (paper 16). Libelium's open-source Waspmote API defines:

```cpp
//! Description: Converts the DO voltage into a percentage of concentration
float DOClass::DOConversion(float input)
{
    return (input - zero_calibration)/(air_calibration - zero_calibration) * 100;
}
```

- Calibration is two-point: a zero-oxygen solution (0%) and air-saturated (100%). The output is therefore % of saturation.
- The formula is **identical in API v014 (March 2015) and v019 (October 2015)**, which bracket the May 2015 – January 2016 deployment. Commits 0ffc1c5dbc and 3487535c1d, file `libraries/SensorSW/WaspSensorSW.cpp`, https://github.com/Libelium/waspmoteapi. Local copies are in `docs/datasheets/`.

**2. Converted to mg/L, the values fall in the physically and locally observed range.** We assume % saturation and convert with the Benson–Krause solubility formula, using the node's own temperature. Monthly medians at node 1 become roughly **0.5–13.7 mg/L**:
- May–June ~7 mg/L
- July–September 0.5–1.6 mg/L (summer hypoxia)
- November–December 9–14 mg/L
- *Independent grab samples at Plemetin:*
  - Shala et al. (2014, Geoadria): as low as **0.53 mg/L** in spring.
  - Kelmendi & Aliu (2023, IJESD): **5.15 and 7.19 mg/L** at ~19 °C.
- So near-zero summer DO is plausible at this heavily polluted site, described by Kelmendi & Aliu as "close to the power plants Kosovo A and B" and by Shala et al. as affected by industrial wastewater discharge. Raw values read as mg/L are not plausible.

**3. Same symptoms in another Libelium deployment.** The Prof's Weija deployment (paper 22, Adu-Manu et al. 2020) used the same Smart Water hardware with a two-point DO/ORP calibration. It reported DO mean 17.36, SD 30.44 and even negative DO, which is consistent with a percentage scale plus calibration drift.

## Caveats (important for our evaluation)
- **Abrupt level shifts in node 1 DO** (daily median), which look like sensor events (fouling, recalibration, cleaning) rather than river behaviour:

  | Date (2015) | Daily-median DO jump |
  |---|---|
  | 24 Jun | 81.6 → 34.2 |
  | 12 Oct | 17.4 → 50.1 |
  | 24 Dec | 147.2 → 5.7 |

- Paper 21 discarded the later part of the DO series as drift.
- Summer converted values (~1 mg/L) are lower than the 2023 grab samples (5–7 mg/L). They may be real (2015, discharge plume at node 1) or a calibration offset. We cannot tell without lab reference data.

## Decision for Paper 1
1. Treat DO as **% saturation**; report DO in %sat (and mg/L derived via Benson–Krause where useful).
2. **Segment the series at detected level shifts** and treat those shifts as sensor/maintenance events, not water-quality events.
3. Report results **with and without DO** (sensitivity analysis).
4. Validate methods on a second dataset with QA-approved DO in both units (e.g. USGS 01463500, which reports both mg/L and %sat).
5. Optional confirmation: the dataset authors (Ahmedi, Univ. of Prishtina) and the Prof (same Libelium sensor at Weija).

## Sources
- Libelium Waspmote API, `WaspSensorSW.cpp`. https://github.com/Libelium/waspmoteapi
- Ahmedi & Ahmedi (2022), Data in Brief 44:108486 (paper 16).
- Shala, Sallaku, Shala, Ukaj (2014), *The effects of industrial and agricultural activity on the water quality of the Sitnica River (Kosovo)*, Geoadria. https://doi.org/10.15291/geoadria.28 (local copy in `papers/dataset_context/`)
- Kelmendi & Aliu (2023), *Research of the Ecological Status in the Waters of the River Sitnica-Kosovo*, IJESD 14(2). https://doi.org/10.18178/ijesd.2023.14.2.1426 (local copy in `papers/dataset_context/`)
- Adu-Manu, Katsriku, Abdulai, Engmann (2020), *Smart River Monitoring Using WSNs*, WCMC (paper 22).
- Benson & Krause (1984), oxygen solubility in fresh water. *Equation to be cited from the USGS DO solubility tables (Office of Water Quality Technical Memo 2011.03) when writing.*
