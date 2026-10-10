# A1 findings: uncertainty, exact tests, multiplicity (2026-10-10)

The script is `src/analysis/revision_stats.py`; its outputs are `a1_effects.csv`, `a1_corr52.csv` and `a1_equal_accuracy.csv`.

**Method:**
- Every effect is reduced to **one number per site**.
- The published median is re-derived from those per-site numbers and asserted equal to the existing tables. All assertions pass.
- 95% CIs are percentile intervals from a bootstrap over sites (20,000 resamples, seed 20261010).
- Wilcoxon p-values are exact.
- Spearman p-values come from a Monte-Carlo permutation test (200,000 permutations); the draft quoted asymptotic ones.
- Holm correction is applied within families.

## Headline effects with CIs

| Claim in the draft | Value with 95% CI (site bootstrap) | Change needed |
|---|---|---|
| RLS-T saving over SOD at L2: 26.1% | 26.1% [13.0, 30.5]; 13/13 wins; exact p = 0.00024; Holm 0.0012 | add the CI |
| L1 / L3 / L4 | 18.9% [14.5, 20.9]; 7.1% [1.7, 27.8]; 1.0% [−12.4, 23.0] (Holm p 0.002 / 0.024 / 0.50) | add the CIs |
| **L0: "persistence wins"** (p = 0.048) | −6.0% [−10.6, −1.4]; exact p = 0.048; **Holm p = 0.096** | **soften:** "tends to lose (not significant after Holm correction)" |
| ρ(diel, saving) = 0.84 at L2, 14 datasets | 0.84 [0.46, 0.99]; permutation p = 0.0003 | add the CI; "associated with", not "predicts" |
| 13 USGS only: 0.80 | 0.80 [0.36, 0.98]; p = 0.0016 | add the CI |
| Including Weija (15): 0.62 | 0.63 [0.07, 0.97]; p = 0.015 | promote into the main text |
| L0 link: 0.52, p = 0.06 | 0.52 [−0.13, 0.97]; permutation p = 0.062 | as before |
| **52 site–parameters: ρ = 0.66, p = 1e-7** | ρ = 0.66, **site-clustered CI [0.22, 0.84]**. Per parameter: T 0.60 [0.04, 0.92], DO 0.68 [0.16, 0.90], pH 0.59 [−0.02, 0.83], EC −0.26 [−0.80, 0.49]. Site means (n = 13): ρ = 0.72, p = 0.007 | **replace the naive p** with the clustered CI and the per-parameter values (M5) |
| Report-level saving "31–44%" (median over site × method) | per-site medians: L0 44.6 [37.8, 48.4]; L1 37.0 [31.4, 41.9]; L2 35.8 [32.8, 40.8]; L3 37.3 [31.0, 42.4]; L4 29.4 [24.0, 35.3]. **The range becomes 29–45%** | use the per-site numbers |
| RLS-D gap to the per-site best, test sites (n = 6) | L1 −0.2 [−0.7, 2.1]; L2 −0.5 [−2.1, 3.0]; L3 +0.4 [−4.7, 4.6]; L4 +2.4 [−2.4, 11.3] | add the CIs; say n = 6 |
| ADAPTIVEML max-error ratio 8.4–17.4× (median per α) | α = 1: 11.8× [8.4, 15.9]; per site 5.8–32.9×; **> 1 in every site × α case (min 2.8×)** | add the CIs and the per-site range |
| Lifetime gain 1.4–2.9× at 5 s (modelled) | N211 RAI 1.72 [1.65, 1.81]; default 2.88 [2.60, 3.26]; SF12 2.05 [1.93, 2.21]; SF7 1.41 [1.35, 1.45]; BC95 1.49 [1.44, 1.54] | add the CIs; say "modelled" |
| RLS-D over SOD lifetime +5.5% (RAI) / +16.9% (default) | +5.5% [3.4, 10.6]; +16.9% [9.5, 23.9]; exact p = 0.00024 | add the CIs |
| **Equal accuracy:** 7.8× smaller error at "about the same" life (ratio of medians) | **paired per site:** error ratio 7.8× [5.2, 13.6] (per site 4.1–19.2×) and life ratio 1.06 [1.02, 1.14]. RLS-D also lives 6% longer, paired | M19 answered: the claim holds when paired |

## Correction found: free-riding is not predictor-independent

`min(total saving)` over every USGS site × method × level was **−13.7%**, which led to the following.
- **The four main methods:** report-level beats separate in 257 of 260 cases. The exceptions are RIDGE at 01467087 L4 (−13.7%) and DBP at L4 at two sites (−1.3%, −1.9%).
- **The paper-default LMS and RLS (γ = 0.98):** report-level costs *more* than separate in many cases, up to 5.5× (free-riding up to −505%).
- **Mechanism (verified in the code):**
  - Our Santini LMS treats any reported value in stand-alone mode as an exceedance and returns to normal mode, which forces a report every step for N steps. So every free-ride triggers a burst of forced reports.
  - RLS updates its weights on every reported step, so free-rides add many updates to an already unstable γ = 0.98 filter. This one is plausible but not isolated by an experiment.
- **Draft statements that are wrong:**
  1. "worth adopting irrespective of the predictor" (Results).
  2. "with any predictor" (Discussion, guidance 1).
  3. "the counts satisfy report-level ≤ bundled ≤ separate" (Methods, Integrity). The test asserts **bundled ≤ separate** only (`tests/test_sim.py:78`). Report-level ≤ bundled holds only for the same decisions; free-riding changes later decisions.
- **Design rule for the paper:** report-level decisions pay off when the predictor's state transitions are driven by its own exceedances, not by every received value. In other words, free riders should refresh the reconstruction without triggering mode switches or extra learning. This holds for SOD, DBP, RLS-T and RLS-D.

# A3: rate-matched ADAPTIVEML comparison (`src/analysis/revision_frontiers.py`)

**Method:**
- Per site, take the bounded RLS-T front at L0–L4.
- Interpolate its max error and RMSE (log-log) at **exactly** each ADAPTIVEML run's report rate.
- Runs whose rate falls outside the front are excluded, not extrapolated:
  - α = 0.5: 8 of 13 sites excluded, because they report more often than L0;
  - α ≥ 1: 1–2 sites excluded.

**Result:**
- ADAPTIVEML has the larger worst-case error in **100 of 100** matchable runs, minimum 3.9×.
- At α = 1 (its paper default) the ratio is **10.6× [8.6, 15.1]** (per site 5.3–27.9×). Over all α the medians are 8.0–17.0×, and 9.0–18.7× with RLS-T inside.
- The RMSE ratio is 2.4–4.6×.
- So the claim survives exact rate matching. Replace "nearest neighbour" with "interpolated at the same rate", and replace "8–17×" with "8–19×".

**Fairness question (M13):**
- σ(t) is computed from the node's own last 24 true readings, as in the ADAPTIVEML paper.
- The decision is made on the node, and the server never needs σ.
- The bounded schemes also decide on the node using the true reading.
- So there is no information asymmetry. State this in Methods.

# A4: decomposition (`a4_decomposition*.csv`)

Medians over the 13 USGS rivers at L2, as % of reporting every cycle:

| Stage | Reports (%) | Saving (95% CI) |
|---|---|---|
| separate SOD | 37.9 | |
| bundled SOD | 32.9 | bundling −20.9% [12.7, 24.1] |
| report-level SOD | 28.3 | free-riding −18.2% [14.6, 22.8] |
| report-level RLS-D | 21.0 | prediction −26.9% [16.0, 32.8] |

Other levels:
- **L1:** bundling 30.8%, free-riding 3.9%, prediction 19.6%.
- **L3:** bundling 11.0%, free-riding 26.5%, prediction 12.6% [4.2, 28.9].
- **L4:** bundling 7.0%, free-riding 20.3%, prediction 3.4% [−7.0, 19.8], which is not distinguishable from 0.

Accounting (bundling + free-riding) delivers more than prediction at every level except L2, where they are comparable. This is the visual message M14 asks for.

# A5: events (`src/analysis/revision_events.py`)

**5σ events, held-out USGS sites, mean over 1/3/6-h durations:**
- **Chosen detector (k = 3, H = 8, c = 6):**
  - steps 0.61, median delay 30 min;
  - ramps 0.13, median delay 135 min;
  - 2.6 false alarms per parameter per 30 days.
- **Sensitive detector (k = 2, H = 4, c = 5):**
  - steps 0.85 (delay 15 min);
  - ramps 0.60 (delay 90 min);
  - **11.7 false alarms per parameter per 30 days.** The draft never states this. Add it to the detect-vs-tighten table.
- **Operating curves** (`a5_operating_curves.csv`):
  - The step-detection front rises from 0.40 at 2.4 FA/30 d to 0.88 at 10.9.
  - The ramp front stays ≤ 0.34 below 5 FA/30 d.
  - So slow ramps are unresolved at low false-alarm rates. Narrow the claim to abrupt changes (M9).

**"0.34 vs 0.34" reproduces** when "test" = 6 USGS + InWaterSense, the protocol's definition. Held-out USGS alone gives 0.37. State the set explicitly.

**Reference events (Check B, whole series):**
- 1,612 events over 14 datasets.
- Per site-parameter: median 10.5, range 0–187.
- Use these as the denominators on Fig. 4.

**Rounding of injected events:**
- The effective amplitude differs from the nominal by a median of 1.2%.
- Worst case: 13.4% at 3σ, 8.5% at 5σ, 5.5% at 8σ.
- The bound is 0.5/3 = 16.7% when the noise scale sits at the resolution floor.
- Immaterial; state it in one sentence.

# A7: energy sensitivity, payload, duty cycle (`src/analysis/revision_energy.py`)

**Setup:**
- Rates are the median USGS ones: 92 samples/day; RLS-D reports/day 35.0 / 17.6 / 7.8 / 2.4 at L1–L4.
- Lifetimes here are evaluated at the median rates, so N211 RAI shows 4.57 y vs 4.62 y in the draft table, which takes the median of per-site lifetimes. **Use the tornado for swings only.**

**Battery-life gain of RLS-D at L2 over reporting every cycle, under one-at-a-time changes:**

| Radio | Gain (base) | Range under the changes | Driver of the range |
|---|---|---|---|
| NB-IoT N211 RAI | 1.78× | 1.20–2.50× | sensing time |
| NB-IoT default timers | 3.16× | 1.77–4.03× | |
| LoRaWAN SF12 | 2.16× | 1.38–2.74× | |
| LoRaWAN SF7 | 1.44× | 1.12–1.74× | |

- **The gain is > 1 under every change.** Ranked by influence: sensing time > report energy ≈ host sleep power ≈ host-during-modem > host active power > packet loss (negligible).
- **Absolute lifetimes swing a lot:**
  - N211 RAI: 1.1–8.8 y over 1–30 s of sensing.
  - Battery size: 5 Wh gives 0.94 y vs 4.57 y.
  - 70% usable capacity gives 3.20 y.
  - So lifetimes must be called **modelled**, with a "usable capacity" caveat.

**Units:**
- 6,600 mAh × 3.7 V nominal (Li-ion) = 87.9 kJ; ideal battery.
- Omitted: self-discharge, temperature, regulator efficiency (LoRa at 3.3 V), ageing. So absolute lifetimes are **optimistic**. A 70% usable-capacity case is shown.

**Payload:**
- A bundled report is 15 B (int16 × 4 + seq 2 + timestamp 4 + flags 1) or 23 B (float32).
- The LoRaWAN frame model adds 13 B of MAC header and MIC.
- SF12 confirmed report energy changes −5% / +5% vs the 20-B assumption, and the RLS-D gain changes 2.13× / 2.19× vs 2.16×.
- NB-IoT per-report energy is insensitive to small payloads (Michelinakis).
- **Conclusion insensitive.**

**LoRaWAN duty cycle (EU868, 1% per sub-band = 864 s/day):**
- SF12 reporting every cycle with 5% loss uses 175 s/day (20% of the limit); mean spacing 894 s vs the 181 s minimum after each frame.
- RLS-D L2 uses 33 s/day (4%).
- **Not binding** at our rates; retries must respect the off-time.
- Suppression also cuts gateway downlink (ACK) load about 5× at L2. Mention it only qualitatively.

# A8: diel-share estimator vs data length (`src/analysis/revision_diel.py`)

**Agreement of a k-week estimate with the full-year value** (site mean over parameters):

| Window | Median abs. deviation | p90 |
|---|---|---|
| 1 week | 0.23 | 0.46 |
| 4 weeks | 0.12 | 0.29 |
| 13 weeks | 0.07 | 0.16 |

Seasonality makes short windows unreliable.

**Ranking power (14 datasets; Spearman ρ with the RLS-T saving at L2):**
- Full year: 0.84.
- One random window per site: 0.40 (1 week), 0.46 (2 weeks), 0.52 (4 weeks), 0.65 (8 weeks), 0.56 (13 weeks; 12 sites).
- **First valid k weeks (the deployment case): 0.34–0.60.**

So diel share is **ranking evidence across sites over a year, not a deployment-time predictor** (M2). This is consistent with the draft's negative result that predictor selection at deployment fails. Write a short "external validity" subsection around it.

# A9: smoothness statistic (pre-registered in `A9_PREREGISTRATION.md`; script `revision_smoothness.py`)

**T roughness R_norm** (1 = a smooth sinusoid):
- Weija 2.41.
- USGS 1.07–1.64.
- InWaterSense 5.77, where the "profile" is noise (diel share of T 0.04).

**P1 FAILED as written:** Weija ranks 2nd, not 1st. The statistic is ill-conditioned when the diel amplitude is near zero, which was not anticipated. Do NOT redefine it after the fact. Report: "rougher than every USGS river; the only rougher series has no diel cycle".

**P2 (exploratory only):**
- S = diel share / R_norm ranks the saving at ρ = 0.85 over 15 datasets, vs 0.63 for diel share alone.
- With one failing case this is a **hypothesis**. A new held-out site is needed.
- Paper wording: "a hypothesis consistent with the data, not a validated diagnostic".

# A10/A11: data flow and series count (`src/analysis/revision_dataflow.py` -> `a10_dataflow.csv`)

**Unit of analysis (use these consistently):**
- **14 datasets** (13 USGS sites + InWaterSense node 1).
- **55 simulated site–parameter series** (13 × 4 + InWaterSense T, EC, DO).
- Phase 1 predictability uses **56** (InWaterSense pH included there, excluded from simulation).
- The cross-site correlations use **one value per dataset** (n = 14, or 13, or 15 with Weija).
- The 52-observation correlation uses 13 USGS sites × 4 parameters (clustered CI in A1).

**Flow:**
- **USGS:** raw values → approved-only. 0–9% of values were removed as not approved (e.g. 01400500: 217,373 → 197,230; 05420400: 147,156 → 137,762). Cycles with all 4 parameters complete were simulated: 3,445–34,802. Segments (gap > 60 min) per site: 3–46.
- **InWaterSense node 1:**
  - 105,453 raw rows, re-joined into 19,090 cycles.
  - Range failures T/EC/DO: 1 / 101 / 0.
  - pH excluded: 4,815 of 19,090 cycles failed plausibility.
  - Spikes flagged but kept: 465 / 620 / 472.
  - 18,982 simulated cycles (T, EC, DO complete) in 336 segments.

**Training length (M: "is 20% comparable across sites?"):**
- The split is the first 20% *by time*.
- USGS: 17–24% of cycles, i.e. **46–73 days**, except Wissahickon (14 days; 72-day record).
- InWaterSense: only **9.3% of cycles = 12.4 days**, because its early record is gappy.
- State this in Methods. Training length is not equal across sites.
- RLS-D adapts online, and the predictor-selection negative result already shows that early data misleads.
