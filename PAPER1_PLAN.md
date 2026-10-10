# Paper 1: When Does Prediction Pay? Predictability-Aware, Error-Bounded Report Suppression for LPWAN Water-Quality Monitoring

**Status:** Phase 1 in progress (cleaning done; Check A done on 3 datasets; 11 more USGS sites downloading) · **Team:** Prof K. S. Adu-Manu (supervisor), NSS research assistant · **Last updated:** 2026-10-03 · **Target:** top-tier journal (see §10)

> **Revision history**
> - **v1** (2026-09-26): multivariate DPS with a volatility-adaptive threshold.
> - **v2** (2026-09-30, after the literature review): ADAPTIVEML (arXiv 2607.19590) already has volatility-adaptive thresholds, so v2 re-centred on report-level + bounded + event-preserving + LPWAN energy.
> - **v3** (2026-10-03, after the first experiments; this version):
>   - Check A showed that on InWaterSense **no predictor beats "last value", and cross-parameter information adds nothing**.
>   - On clean USGS rivers, **prediction cuts error vs "last value" by up to ~70% out of sample and cross-parameter VAR significantly beats single-parameter AR** (for T, DO, pH; not EC).
>   - **The months that are most expensive to report are also the most predictable.**
>   - v2's core claim ("our multivariate scheme saves X% on a river") would have been fragile; it is true on some rivers and false on others.
>   - v3 asks the deeper, more defensible question: **when does prediction pay, why, and how should a node adapt?** It answers it across many rivers, with guarantees and real energy.

---

## 1. Thesis in one paragraph

Battery-powered water-quality nodes on LPWAN links (NB-IoT, LTE-M, LoRaWAN, legacy GPRS) pay a large fixed energy cost **per report** (≈0.1–4 J). A 10–15-minute cadence therefore lasts months, not years. Dual-prediction schemes (DPS) promise large savings, but the literature evaluates them on a handful of convenient datasets (mostly Intel Lab) and assumes prediction helps.

**Our first experiments show that it depends.** Whether prediction (and cross-parameter prediction) beats simple send-on-delta reporting depends on:
- the river's **day–night (diel) dynamics**, which are biological and thermal;
- **sensor noise**;
- the **season**.

On noise-dominated, fouling-prone deployments (InWaterSense), "last value" is already optimal. On clean rivers with diel cycles, multivariate prediction captures the coupling of temperature, DO and pH and pays off most in exactly the months that are costliest.

We contribute four things:
1. A **multi-river predictability study** that explains when and why prediction pays.
2. A **predictability-aware, report-level DPS** that falls back to send-on-delta when prediction cannot help. It keeps a **hard per-parameter error bound** and **never smooths away events**.
3. A **full-year LPWAN energy and lifetime evaluation**, validated on hardware.
4. **Open code and a reproducible multi-site benchmark.**

---

## 2. Evidence so far (Phase 1; provisional until all 14 sites are processed)

| Finding | InWaterSense node 1 (10 min) | USGS 01458500 Delaware @ Frenchtown (15 min) | USGS 01438500 Delaware @ Montague (30 min) |
|---|---|---|---|
| Cycles recovered by re-joining split messages | Only 3–6 of 19,090 cycles miss a parameter (vs 4,642 null rows in the published grouped file) | n/a | n/a |
| Share of within-day variance explained by time of day (T / DO / pH) | **0.04 / 0.01 / 0.01** | 0.45 / 0.53 / 0.47 | 0.54 / 0.63 / 0.50 |
| 1-step skill of AR vs "last value" (T / DO / pH) | −0.02 / +0.01 / +0.17 (≈ none) | +0.10 / +0.06 / +0.07 | +0.52 / +0.60 / +0.23 |
| 1-h skill of VAR vs "last value" (T / DO / pH) | ≈ 0 | +0.47 / +0.33 / +0.21 | +0.72 / +0.73 / +0.55 |
| VAR/AR MSE ratio, 1 h ahead (T / DO / pH), 95% CI | ≈ 1.00 (no gain) | 0.82 / 0.95 / 0.71 (all CIs < 1) | 0.79 / 0.93 / 0.72 (all CIs < 1) |
| Same-time correlation of first differences (DO–T / DO–pH) | −0.09 / −0.08 | 0.41 / 0.21 | 0.64 / 0.58 |
| Conductivity (EC) | No predictability | No predictability (VAR/AR ≈ 1) | No predictability |

**All 13 USGS sites (Check A, 1-hour horizon; run 2026-10-03; full table in `results/phase1/check_a_summary.md`).**
- Site 14078260 had no 2023 data and is excluded (documented; not replaced, to avoid post-hoc selection).
- DO %sat is derived from approved DO mg/L + T via Benson–Krause. Validated against USGS-approved %sat at 3 sites: r ≥ 0.99, median ratio 0.999.

| Parameter | Prediction helps (VAR skill > 0.1) | Cross-parameter significantly helps (VAR/AR CI < 1) | Median VAR/AR |
|---|---|---|---|
| T | 10 / 13 | 9 / 13 | 0.94 |
| EC | 3 / 13 | 3 / 13 | 1.00 |
| DO | 8 / 13 | 7 / 13 | 0.98 |
| **pH** | **11 / 13** | **10 / 13** | **0.81** (down to 0.44) |
| InWaterSense (all four) | 0 / 4 | 0 / 4 | ≈ 1.0 |

- **Day–night strength explains predictability:** Spearman ρ(diel share, VAR skill) = 0.66 across USGS site–parameters (T 0.60, DO 0.68, pH 0.59).
- Cross-parameter value is concentrated in **pH** (photosynthesis/CO₂ coupling with T and DO). For T and DO it is real but modest. EC is mostly unpredictable everywhere.
- **Exceptions to explain in Phase 1:** large slow rivers (Mississippi Dam 13, Illinois R.) have moderate diel share but low skill. Hypothesis: 1-h changes are near the sensor resolution (quantisation). To test.

**Seasonality (Frenchtown DO).**
- The send-on-delta report rate (δ = 2 %sat) ranges from 0.004 (Jan) to 0.177 (Jun) reports per sample, about **40×**.
- The 1-h-ahead skill vs "last value" tracks it: +0.01 (Jan), +0.64 to +0.81 (Apr–Jun). **The costliest months are the most predictable.** (Confirmed out of sample across 113 USGS site-months: Spearman ρ(cost, skill) = +0.78 T, +0.68 DO, +0.59 pH; EC −0.12. See the Phase 1 report.)

**A failed idea (recorded honestly).**
- A two-parameter "local level" first-passage model (process noise q plus sensor noise r, from the variogram) mispredicts report rates by 2–6×. The cause is heavy tails (InWaterSense) and smooth diel trends (USGS).
- A 30-day pilot also fails to predict the yearly rate, because of seasonality.
- So no closed-form "predict your battery life from two numbers" claim is made unless a richer model is shown to work (RQ5, stretch).

Scripts: `src/data/clean_inws.py`, `src/data/clean_usgs.py`, `src/analysis/check_a.py`, `src/analysis/theory_check.py`. Outputs: `results/phase1/`.

**Phase 2 (baselines, 2,016 runs on 14 datasets; full report in [`results/phase2/PHASE2_REPORT.md`](results/phase2/PHASE2_REPORT.md)).**
- **Bounded learned prediction beats SOD only at moderate tolerances.** RLS-T vs SOD saves +19% / **+26%** / +7% at L1 / L2 / L3 (12, 13 and 10 of 13 USGS sites). It loses at L0 (−6%) and is n.s. at L4. InWaterSense: SOD best or tied at every level. Paper defaults (Santini LMS, RLS γ = 0.98) report 87–99% of samples.
- **Central result:** Phase 1 diel share predicts the RLS-T saving over SOD. Spearman ρ = 0.84 at L2 (14 sites, p = 0.0002); USGS only ρ = 0.80, worst leave-one-out 0.75. Diel share beats fitted skill as a predictor *on these 14*. **Qualified by the held-out Weija test (below):** with Weija, ρ = 0.62 (p = 0.013), and skill (0.66) is level with diel share.
- **RQ2:** report-level decisions save 30–45% of reports vs per-parameter DPS. Bundling dominates at tight tolerances, free-riding at loose ones. Free-riding helps in 253/260 cases.
- **RQ3:** at matched report rates, ADAPTIVEML's max error is 8–17× larger (100% of cases) and its RMSE 2–5× larger, with lower event capture at α ≥ 2.
- **Fixed schedules:** periodic max error is 4–24× larger; batching delays events 15–120 min.
- **Limitation found:** event capture drops to ≈ 0.63 at L4 for *every* bounded predictor. The bound does not protect events smaller than δ, so the Phase 3 event detector is essential, not optional.

**Phase 3 (proposed scheme; full report in [`results/phase3/PHASE3_REPORT.md`](results/phase3/PHASE3_REPORT.md)).** Tuning and test sites were fixed in advance; events were injected with known onsets.
- **Predictor RLS-D:** change model with a damped trend and history repair. Within ≈ 0–2% (median) of the per-site best fixed predictor on held-out sites at L1–L4, with no selection step. It still loses to SOD on InWaterSense (3–13%).
- **Negative results:**
  - selecting the predictor at deployment (winter training data misleads);
  - online switching;
  - halving δ during events.
- **Detector** (CUSUM, diel-aware 2-h residual):
  - Held out: 70% of 5σ steps detected, slow ramps poorly.
  - Half of its "false alarms" coincide with real events (6× chance).
  - At L4, the sensitive detector catches more injected events than tightening to L3 (steps 0.97 vs 0.87) at 40% of the reports. Real Check B events gain less (0.62 → 0.72).
- **Loss:**
  - Confirmed uplink: overhead ≈ loss rate.
  - Unconfirmed + heartbeat: 0 unflagged violations in 1,120 runs (all 14 sites), but +15–30% reports for RLS-D. SOD is self-synchronising.

**Weija held-out test (2026-10-04; full report in [`results/weija/WEIJA_REPORT.md`](results/weija/WEIJA_REPORT.md)).** The Prof's 2018–19 deployment was never used for tuning. Its prediction was written down first (`PREREGISTRATION.md`).
- **Usable data:** T + EC every 32.5 min, 31 Oct 2018 – 4 Jan 2019 (2,478 cycles).
  - Received files contain unflagged interpolation (> 3 decimals; per-row ramps).
  - Ca and F are white noise from December; pH is implausible (8.5–12.8 daily, tracking T); DO and ORP are 5-hourly.
- **Pre-registered prediction failed.**
  - Diel share 0.39 → predicted saving 30 % [18, 43] at L2. Measured **−16 %**, a loss at all levels.
  - Not explained by the step (USGS thinned to 30 min: ≤ 3-point change), the parameter set, short history, the probe, or day-to-day irregularity.
  - Supported (post hoc): spike-shaped midday excursions (skewness 1.6 vs ≤ 0.85). RLS-T loses at night and on EC.
- **RLS-D: +10 % reports vs SOD at L2** (InWaterSense +3 %). Bound held. SWITCH correctly stayed on SOD (training replay is representative in the aseasonal tropics).
- **Implication:** diel share is not sufficient. On both real low-cost deployments (Kosovo, Ghana), SOD is the right default.

**Phase 4 (energy; full report in [`results/phase4/PHASE4_REPORT.md`](results/phase4/PHASE4_REPORT.md)).** The model reproduces 20/24 of Michelinakis's lifetimes and Casals's airtime table.
- **Battery life:** suppression extends it 1.1–3.5×, depending on report energy vs sensing energy. RLS-D adds a per-site median of +5.5% over SOD at L2 for NB-IoT RAI with 5 s sensing (+16.9% with default NB-IoT timers; corrected 2026-10-04 from "0–7%"); the detector costs ≈ 1%.
- **Equal accuracy:** RLS-D at L4 lives 53% longer than 30-min periodic at the same worst-case error. RLS-D at L2 has 7.8× smaller error than hourly reporting at about the same battery life.
- **Framing:** energy does not bind solar nodes (≥ 33× margin with a 2 W panel). RQ4 should cover battery-only nodes, hardware size and per-message / duty-cycle costs.

---

## 3. Research questions

1. **RQ1: Predictability.** Across rivers, seasons and sensor quality, when are 10–15-minute water-quality series predictable enough for prediction-based suppression to beat send-on-delta? When does cross-parameter (multivariate) information add value? Which measurable signal properties explain this: diel variance share, sensor-noise share, heavy tails?
2. **RQ2: Report-level decisions.** Under per-report LPWAN costs, how much does a joint (report-level) decision save compared with independent per-parameter DPS? How does the saving depend on the co-occurrence of innovations (e.g., diel DO–T–pH coupling)?
3. **RQ3: Guarantees.** Can a predictability-aware DPS match the savings of the best adaptive schemes while guaranteeing two things?
   - **Bounded error:** max |x − x̂| ≤ δᵢ at the server, apart from declared losses.
   - **Event preservation:** capture rate and onset delay on real and injected events.
   - The baseline to beat is ADAPTIVEML, whose threshold loosens during volatility.
4. **RQ4: Energy and lifetime.** What lifetime does each scheme achieve over a **full year** on NB-IoT (default timers vs RAI), LTE-M, LoRaWAN and GPRS, once sync, heartbeat, TAU and packet-loss recovery are counted? Is the model confirmed by **hardware measurements**?
5. **RQ5 (stretch).** Can a node or operator estimate the expected report rate and lifetime online from cheap signal features, season-aware, without full trace replay?

---

## 4. Contributions (claims to support; each must survive a hostile reviewer)

- **C1: Multi-river predictability study.** The first systematic evaluation of DPS across many real water-quality sites, using a site selection rule fixed in advance (§5.2). It explains *when* prediction and cross-parameter prediction pay, through diel dynamics, noise and season. This answers the Dias et al. (04) critique of single-dataset evaluation.
- **C2: Predictability-aware, report-level DPS.**
  - Per-parameter hard bounds; one report decision per wake-up.
  - The predictor (persistence / AR / cross-parameter VAR, online RLS) is chosen by measured out-of-sample skill, cheap enough for an MCU.
  - Node and server switch predictors synchronously, so models stay identical.
  - *Prior art to cite:* Santini & Römer 2006 (block threshold, not built); Ghosh et al. 2022 (wake-up-aware batching, fixed limits); Carvalho 2011 (batch multivariate regression, no bound).
- **C3: Guarantees.**
  - A noise-aware threshold δᵢ(t) ≤ δᵢ,max (noise estimated from residuals, median/MAD).
  - A robust event detector (two-sided GLR/CUSUM on normalised innovations, following paper 15) that forces a report and tightens δ at onset.
  - Provable max-error bound under lossless operation, plus a resynchronisation protocol (sequence numbers and heartbeat; Santini §V) with quantified behaviour under 0.5–1% loss.
- **C4: Full-year LPWAN energy and lifetime evaluation, validated on hardware.**
  - Per-report energy models (Sørensen 10, Michelinakis 11, Casals 09, GPRS datasheet), including sync, TAU, heartbeat and resync overheads.
  - Hardware measurement of the per-report energy that grounds the model (§8).
  - This addresses Raza's (05) lesson that system overhead caps savings, and Nowak et al. (25), where a naive LoRaWAN prediction scheme saved only 1.1%.
- **C5: Open benchmark.** Cleaning code, site list, the selection rule, all baselines (including an ADAPTIVEML reimplementation) and evaluation scripts released.

---

## 5. Data

### 5.1 InWaterSense (Sitnica, Kosovo): primary case study
| Item | Detail |
|---|---|
| Source | Mendeley doi:10.17632/krzv3g6d5f.1 (CC BY-NC); Data in Brief doi:10.1016/j.dib.2022.108486 (paper 16) |
| Hardware | Libelium Waspmote Plug & Sense Smart Water; ZigBee and cables → one gateway → GPRS |
| Parameters | T (°C), EC (µS/cm), pH, DO (**% saturation**, see [`docs/DO_UNITS_EVIDENCE.md`](docs/DO_UNITS_EVIDENCE.md)) |
| Cadence | 611 s median (10 min 11 s); node 1 May 2015 – Jan 2016 |

**Cleaning:**
- Cycles are rebuilt from the raw parameter-wise messages. Raw timing is bimodal (within a cycle 0–60 s, between cycles ~610 s), so readings < 120 s apart form one cycle.
- Tiered quality flags (`src/data/clean_inws.py`):
  - hard range;
  - site plausibility, pH ∈ [5, 10] (grab samples 6.6–8.3; Shala 2014; Kelmendi 2023);
  - Hampel spikes kept but flagged.
- Node 1: 19,090 cycles, 14,129 complete; 29 segments ≥ 1 day hold 13,450 cycles.
- Node 2 has pervasive fault codes (EC −5021, T −0.35, DO 0) and stops in August, so it is excluded from the main evaluation.

**Known problems:**
- pH fault episodes at 2–4 lasting weeks (late Jun, late Aug–mid Sep, late Oct).
- DO level shifts (24 Jun, 12 Oct, 24 Dec), probably fouling or recalibration.
- Real events, e.g. July low flow (EC ≈ 530, DO ≈ 5%).

**Role in the paper:** the **noise-dominated, real-deployment case** (Libelium, as at Weija). It shows where prediction cannot help and why bounded, event-preserving send-on-delta matters.

### 5.2 USGS continuous water-quality sites: multi-river benchmark
- **Selection rule (fixed in advance; no cherry-picking):**
  - active river or stream sites with real-time T, specific conductance, pH and DO (mg/L **and** %sat);
  - 15-minute cadence;
  - not tidal;
  - spread across strata: large rivers, regulated rivers, mid-size rivers, urban streams (incl. combined-sewer-overflow), suburban and rangeland.
  - The scouting found 68 qualifying sites in PA/NJ/IL/OR; **14 selected**, listed in `data/raw/usgs/candidate_sites.csv`.
- **Year 2023, approved ("A") values only.** Downloaded with `src/data/fetch_usgs.py` and cleaned with `src/data/clean_usgs.py`.
- Note: some sites report at 30 min (e.g. Montague). Keep them and state the cadence; horizons are defined in physical time.
- *Extension if needed:* add 2022 for a cross-year test; add more sites from the 68 using the same rule.

### 5.3 Weija intake (Ghana, Prof's deployment, paper 22): received 2026-10-04, held-out test
- Received as pre-processed files (`cleaned/cleaned/`); part of the data was lost.
- Usable: T (Sensor Two) + EC, 32.5 min, 31 Oct 2018 – 4 Jan 2019. Cleaner: `src/data/clean_weija.py`.
- Used as a pre-registered held-out test of C1 (not for tuning). Result and caveats: `results/weija/WEIJA_REPORT.md`.

---

## 6. Method

### 6.1 Data preparation
Done for InWaterSense and USGS (§5): chronological splits only, never interpolate across gaps, keep events and flags.

### 6.2 Trace-driven simulator
Each cadence step:
1. Node and server compute identical predictions x̂ᵢ(t) from the *reconstructed* history (Santini's rule: when a report is suppressed, the prediction is fed back as the value).
2. **Per-parameter DPS (baseline):** each parameter is a separate report.
3. **Report-level DPS:** one report if any |xᵢ − x̂ᵢ| > δᵢ(t) or an event flag is raised; all parameters are then sent (free riders).
4. Heartbeat every H hours.
5. Bernoulli or bursty packet loss with sequence-number resync.

### 6.3 Baselines (strong set; a reviewer will ask for each)
| Baseline | Why |
|---|---|
| Periodic at full cadence | Upper energy bound |
| **Fixed-interval downsampling** (e.g. 30/60 min, as at Weija) | What practitioners actually do (paper 22); often surprisingly strong |
| Send-on-delta / constant predictor | Simplest DPS; Aderohunmu 2013 found it best |
| LMS DPS | Santini & Römer 2006 (paper 24) |
| DBP | Raza 2015 (paper 05) |
| Liazid adaptive threshold | Moving-average-of-errors threshold (Liazid 2019) |
| **ADAPTIVEML / -RLS** | Closest 2026 competitor (paper 17); reimplemented exactly from its eqs. 3–10 |
| Ghosh-style batching | Wake-up-aware batching with fixed "bad" limits (paper 23) |
| Our variants | Report-level ± multivariate ± predictability-aware ± event detector (ablations) |

### 6.4 Proposed scheme (to be specified precisely in Phase 3)
- **Predictor pool:** persistence, univariate AR (RLS), cross-parameter VAR (RLS). Node and server select by a shared, reconstructed-data-based skill estimate, so the selection stays synchronous.
- **Threshold:** δᵢ(t) = clip(κ·σ̂ᵢ, δᵢ,min, δᵢ,max), with σ̂ᵢ from residual median/MAD.
- **Event detector:** two-sided GLR/CUSUM on normalised innovations. It forces a report, tightens δ, and has a recovery rule.
- **Tolerances δᵢ,max:** set from sensor accuracy and regulatory relevance, e.g. T ±0.2–0.5 °C, pH ±0.1–0.2, EC ±2–5%, DO ±2–5 %sat. Confirm with the Prof (Q4).

### 6.5 Energy model
- **NB-IoT:** Sørensen state/procedure model (N211 parameters, sync 160 mJ, PSM 9.5 µW, TAU), cross-checked against Michelinakis per-report medians (default timers ~0.8–4.2 J; RAI ~0.12–1.3 J).
- **LTE-M:** Sørensen R410M parameters.
- **LoRaWAN:** Casals 11-state model (DR0–DR5, ACK/no-ACK).
- **GPRS:** datasheet (legacy deployment).
- **Batteries:** 5 Wh and 2400 mAh; sensing and MCU energy from the Waspmote datasheet.
- **Full-year simulation per site.** Lifetime reported with seasonal breakdown.

---

## 7. Evaluation protocol (rigour expected by top venues)

**Metrics:**
- Reports per day.
- Per-parameter RMSE, MAE and **maximum error**.
- **Bound-violation rate.**
- Event capture rate and onset delay: real events, plus injected step/ramp/pulse events with known onsets (paper 15 method).
- Energy per day and lifetime per radio.
- Overhead share (heartbeat, TAU, resync).
- MCU operations and memory per step.

**Statistics:**
- Chronological train/test splits.
- Block-bootstrap (by day) 95% CIs.
- Paired comparisons across sites (Wilcoxon signed-rank).
- Results per site *and* pooled by stratum.

**Robustness:**
- δ sweeps; heartbeat interval; loss rate; cadence (10/15/30 min).
- With and without DO/pH.
- Cross-year (2022 vs 2023) on a subset.

**Planned figures:**
1. Predictability map: diel variance share vs prediction gain, across sites and seasons.
2. Pareto fronts: reports per day vs max error.
3. Report-level vs per-parameter gain vs innovation correlation.
4. Event-window zoom: ours vs ADAPTIVEML.
5. Lifetime by radio and season.
6. Hardware energy trace vs model.

**Reproducibility:** public code, site list, fixed seeds, environment file.

---

## 8. Hardware validation (OPTIONAL; the project does not depend on it)

**Default (no hardware):** the energy and lifetime results come from published, *measured* per-state and per-report energy values for real radios: NB-IoT/LTE-M (papers 10 and 11, two independent measurement campaigns), LoRaWAN (paper 09) and a GPRS datasheet. A sensitivity analysis covers device-to-device variation. Many accepted IoT-journal papers use exactly this approach (e.g., papers 05, 12 and 17 evaluate energy without new hardware). We state the limitation clearly.

**If hardware becomes available later** (the lab server/equipment was down as of 2026-10-03), it would strengthen the paper but is not required. The goal would be to measure the real per-report energy and the sleep current of at least one LPWAN radio running the scheme, and show that the model's lifetime predictions match the measurement within a stated error.

| Option | What | Notes |
|---|---|---|
| A | **The Prof's Libelium Waspmote with 4G/GPRS** (the Weija hardware) + a current meter/power analyser | Same platform as both datasets. Strongest link to the data. Ask if available |
| B | NB-IoT/LTE-M dev kit (e.g., Nordic nRF9160 DK) + power profiler | Supports PSM/RAI. Check NB-IoT/LTE-M availability in Ghana (MTN/Telecel) or use a roaming IoT SIM |
| C | LoRaWAN node + a local gateway | Cheapest; no operator dependence |

Replay real traces (InWaterSense and a USGS site) through the device's scheme: device decides, radio transmits, power is measured.

---

## 9. Reading and evidence base

- PDFs and the reading order are in [`papers/paper1/README.md`](papers/paper1/README.md).
- Per-paper notes and the gap analysis are in [`papers/paper1/LITERATURE_NOTES.md`](papers/paper1/LITERATURE_NOTES.md). Papers 01–25 are read.
- Key competitors and anchors:
  - 17 ADAPTIVEML (closest);
  - 05 DBP and 24 Santini (classic DPS);
  - 06 Carvalho and 23 Ghosh (multi-parameter);
  - 12 Rao (critical sensing);
  - 25 Nowak (LoRaWAN hardware; tiny gains);
  - 09–11 energy;
  - 01 and 22 (the Prof's work).
- **Rule:** every citation is verified from the actual PDF or OpenAlex.

---

## 10. Target venues (to decide with Prof)

| Venue | Why it fits | Bar |
|---|---|---|
| **IEEE Internet of Things Journal** (primary) | DPS/IoT energy is core scope; ADAPTIVEML-type work targets it; values multi-dataset rigour and system realism | Needs C1–C4; hardware validation very helpful |
| IEEE Trans. Green Communications and Networking | Energy-efficient communication; Ghosh et al. (23) published here | Strong energy model and measurements |
| ACM Trans. Sensor Networks | The Prof's 2017 survey venue; values real deployments and systems insight | Depth of systems analysis |
| IEEE Sensors Journal / Trans. Industrial Informatics | Applied fallbacks | Lower bar |

**Option:** a short conference version (e.g. IEEE ICC/Globecom workshop, WF-IoT) to establish priority, then the full journal paper. Decide with the Prof.

---

## 11. Work plan

| Phase | Tasks | Output | Status |
|---|---|---|---|
| 0. Literature | Papers 01–25; gap analysis | Notes, plan | ✅ |
| 1. Data & predictability | Cleaning ✅; Check A ✅; Check B ✅ (events vs glitches; InWaterSense DO artefacts found); out-of-sample seasonal ✅ (ρ = +0.78 T, +0.68 DO, +0.59 pH); quantisation hypothesis ❌ rejected | [`results/phase1/PREDICTABILITY_REPORT.md`](results/phase1/PREDICTABILITY_REPORT.md) → **Prof meeting** | ✅ (pending Prof feedback) |
| 2. Simulator & baselines | Trace-driven simulator; all baselines (§6.3) incl. ADAPTIVEML; per-parameter vs report-level | Baseline Pareto fronts on all sites → [`results/phase2/PHASE2_REPORT.md`](results/phase2/PHASE2_REPORT.md) | ✅ (2,016 runs; open: injected events, tuned-LMS variant) |
| 3. Proposed scheme | RLS-D predictor (selection and switching = negative results); CUSUM detector; loss protocols; ablations | [`results/phase3/PHASE3_REPORT.md`](results/phase3/PHASE3_REPORT.md) | ✅ |
| 4. Energy | NB-IoT (2 modules, 4 configs) + LoRaWAN (SF7/SF12) models validated against papers 09/11; sensing-time sweep; equal-accuracy view; solar margin | [`results/phase4/PHASE4_REPORT.md`](results/phase4/PHASE4_REPORT.md) | ✅ (LTE-M/GPRS need a measured source; RQ4 framing to discuss) |
| 4b. Weija held-out test | Profile and re-clean; Check A/B; pre-registered prediction; Phase 2/3 grids; diagnostics | [`results/weija/WEIJA_REPORT.md`](results/weija/WEIJA_REPORT.md) | ✅ (prediction failed; C1 qualified; questions for Prof) |
| 5. Hardware (optional) | Only if equipment becomes available; otherwise skipped | Model validation | Optional (§8) |
| 6. Writing | Draft → Prof → revise → submit | Manuscript + code release | |

---

## 12. Questions for Prof Adu-Manu

1. **Weija data** (received 2026-10-04): permission to publish; probe placement (depth / flow cell / enclosure / sun) behind the midday spikes; which T probe is the water probe; pH compensation and calibration; are raw, unprocessed files available? (Details: `results/weija/WEIJA_REPORT.md` §7.)
2. **Hardware (§8, optional):** if lab equipment comes back online, is a Libelium Waspmote 4G available for energy measurements? (Not required.)
3. **DO at Weija:** how was the Libelium DO sensor converted and calibrated? (Our evidence for %sat is in `docs/DO_UNITS_EVIDENCE.md`.)
4. **Tolerances δ:** an acceptable reporting error per parameter? Any Ghana EPA / WHO / EU reference?
5. **Venue and strategy:** IEEE IoT Journal as the primary target? Conference version first, given ADAPTIVEML?
6. **Node 1 location (Sitnica):** effluent, river or a mix? This affects how events are interpreted.

---

## 13. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Scooped (ADAPTIVEML lists multivariate prediction and resync as future work) | Our scope (multi-river predictability + guarantees + full-year LPWAN energy + hardware) is broader; consider a conference version first |
| Predictability findings don't generalise beyond 2 USGS sites | 14 sites with a selection rule fixed in advance; report negatives honestly (InWaterSense is a deliberate counter-case) |
| Cross-parameter gains small even where diel cycles exist | Still a finding (C1). C2 falls back to univariate; report-level and guarantees stand on their own |
| Event ground truth lacking | Injected events with known onsets plus documented real events (e.g., Sitnica July low flow; USGS storm hydrographs) |
| Hardware unavailable (current situation) | Default plan: model-only, with two independent measured parameter sets (papers 10 and 11) and a sensitivity analysis; state the limitation |
| USGS download slowness | Background fetch with retries; cache everything locally |

---

## 14. Project layout

```
WSN/
├── PAPER1_PLAN.md                 ← this file (v3)
├── INWS/                          ← raw InWaterSense (never edit)
├── docs/                          ← DO_UNITS_EVIDENCE.md, datasheets/
├── papers/paper1/                 ← PDFs 01–25, txt/, README, LITERATURE_NOTES.md
├── papers/dataset_context/        ← Sitnica field studies
├── data/raw/usgs/                 ← USGS downloads + candidate_sites.csv
├── data/clean/                    ← inws_cycles.csv, usgs/<site>.csv
├── src/data/                      ← fetch_usgs.py, fetch_all_usgs.sh, clean_inws.py, clean_usgs.py
├── src/analysis/                  ← check_a.py, theory_check.py
└── results/phase1/                ← quality reports, Check A outputs
```
