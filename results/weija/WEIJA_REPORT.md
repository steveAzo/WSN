# Weija held-out test: report (2026-10-04)

*Code: `src/data/clean_weija.py`, `src/analysis/weija_phase1.py`, `weija_diagnostics.py`, `weija_figures.py`; runners `run_phase2.py` / `run_phase3.py --datasets Weija --out results/weija/...`. Tests: `tests/test_weija.py` (83 tests pass in total). The prediction was written down before any simulation: `PREREGISTRATION.md`.*

## 1. Bottom line

1. **Usable data are small.** We can use T and EC co-sampled every 32.5 min, from 31 Oct 2018 to 4 Jan 2019 (2,478 cycles, about 65 days). Everything else is unusable for this study (§2).
2. **The pre-registered prediction failed.** Diel share predicted that RLS-T would save 30 % of reports versus send-on-delta at L2 (90 % PI [18, 43]). The measured value is **−16 %**: prediction *costs* reports. The miss holds at every tolerance level (−12 to −19 %), and Weija has the most negative gain of all 15 datasets at L1–L3.
3. **The miss is not an artefact.** Thinning USGS rivers to 30 min, restricting them to T+EC, using only steps with full predictor history, and swapping the T probe all leave the conclusion unchanged (§4).
4. **The mechanism is the waveform.** Weija temperature is flat for about 18 h and has a sharp, sun-driven midday spike (+2 to +7 °C in about 2 h). A lag-only linear predictor wins a little in the spike, but loses more at night (2.4 vs 1.0 T reports per day) and on EC, which has no diel structure.
5. **The proposed scheme is safe but gains nothing here.**
   - RLS-D costs **+10 %** reports versus SOD at L2 (InWaterSense: +3 %).
   - The bound holds (0 violations).
   - SWITCH correctly stays on SOD (0 switches).
6. **Consequence for the paper.**
   - C1 must be qualified. Including Weija, ρ(diel share, gain) at L2 falls from **0.84 to 0.62** (p = 0.013), and fitted 1-h skill (ρ = 0.66) now predicts gain about as well as diel share.
   - The two real low-cost deployments, on two continents, both favour send-on-delta.

## 2. Data quality: what we found in the received "cleaned" files

These findings come from statistics, not judgement, and each is reproduced by `clean_weija.py`. They should be raised with the Prof as questions, not as criticism: the files were processed by someone else and part of the data was lost.

| Finding | Evidence | Treatment |
|---|---|---|
| Temperature Sensor Two (the probe co-sampled with EC/pH) is imputed 87 % in Jan and **100 % in Feb–Mar 2019** | `Was_Imputed` | dropped; window ends 4 Jan |
| **Unflagged interpolated values**: genuine T/EC/pH readings have ≤ 3 decimals, imputed ones 12–15; yet 513 EC, 874 pH and 20 T rows marked *not* imputed have 4–16 decimals | e.g. EC 11–12 Nov 2018 falls by exactly 0.133219 per row for 17 h | dropped (COMPUTED tier) |
| Calcium (from about 25 Nov) and fluoride (from about 20 Dec) are **white noise** | lag-1 autocorrelation about 0 (0.87–0.95 in Nov); flat histogram between fixed bounds | not used |
| pH < 3 from about 10 Jan onward (59–85 % of Jan–Mar readings) | probe failure | range rule [3, 14] |
| pH 8.5 → 12.8 → 8.5 **every day**, tracking T (level correlation 0.82) | Fig. W1 | kept, flagged, **not simulated** |
| DO and ORP: one reading per 5 h; DO also contains a 3-week straight line | sampling interval | not used |
| T rises 5–7 °C in about 2 h at midday in *both* T probes, EC and pH spike with it | Fig. W1 | kept: this is what the node measured |

The midday excursions are too fast for the bulk water of a reservoir. They suggest that the sensors sit in a small, sun-exposed volume, such as a shallow position, a flow cell or an enclosure. For our question this is still valid data, because a deployed node would have to report exactly these values. The same stance was taken for InWaterSense fouling.

**A process note.** The first run used only a time-based ramp detector and missed the per-row interpolation. A figure revealed it, and the whole chain was re-run. Run 1 is archived in `run1_ramp_bug/`, and its conclusion was the same (L2 gain −16.4 %).

## 3. Phase 1 numbers (Check A, segments ≥ 24 h, 1 h = 2 steps)

| | diel share | 1-step AR skill | 1-h AR skill | Check B events / 30 d |
|---|---|---|---|---|
| T (Sensor Two) | 0.736 | +0.21 | +0.19 | 23.7 (USGS median 1.0) |
| EC | 0.118 | −0.19 | −0.07 | 15.8 (USGS median 6.2) |
| T1 (Sensor One, sensitivity) | 0.646 | +0.36 | +0.33 | n/a |

Most Check B "events" at Weija are the midday excursions (they start between 11:00 and 14:00). Weija's event metrics are therefore **not comparable** with the storm events at the USGS sites.

## 4. The pre-registered test (Fig. W2) and what explains the miss

**Measured RLS-T saving versus SOD, report level:** L0 −15 %, L1 −19 %, **L2 −16 %**, L3 −18 %, L4 −12 %. Every predictor in the Phase 2 grid sends more reports than SOD at every level; DBP comes closest. The bound held in every run (0 violations).

| Candidate explanation | Test | Verdict |
|---|---|---|
| 32.5-min step is too coarse | 4 USGS sites thinned from 15 to 30 min: gain changes by ≤ 3 points (Cobbs 42.5 → 40.3 %) | **ruled out** |
| Only 2 parameters | the same sites with T+EC only: 41 / 31 / 27 % | **ruled out** |
| Short segments (36 % of test steps have less than 24 steps of history) | full-history steps only: RLS-T 0.475 vs SOD 0.374 reports per step | **ruled out** |
| Noisy probe | Sensor One instead: T1+EC −6 %, T1 alone −1 % | **ruled out** (smaller loss, still no gain) |
| Diel cycle irregular from day to day | *post hoc*: share of today's profile explained by the last 7 days is 0.72 at Weija, the same as the best USGS site | **ruled out** |
| **Spike-shaped waveform** | *post hoc*: skewness of daily T anomalies is 1.6 at Weija vs −0.1 to 0.85 at USGS; RLS-T sends 2.4 vs 1.0 T reports per day at night (00–06 h) and fewer at midday (share 0.42 vs 0.50); EC alone −12 % | **supported** (post hoc; needs a new site to confirm) |

**Interpretation.** Diel share measures *how much* variance follows the clock. A predictor that sees only recent lags can use that variance only if the cycle is smooth enough for its phase to be read from the recent slope. Weija's flat-then-spike cycle gives no warning before the spike, and the dynamics learned from the spikes make the predictor drift during the flat night. *A time-of-day-aware predictor might succeed here;* that is an untested hypothesis, not a claim.

## 5. Phase 3 on Weija (proposed scheme, frozen settings)

| L2 | SOD | RLS-T | **RLS-D** | RIDGE-D | SWITCH | RLS-D+DET |
|---|---|---|---|---|---|---|
| reports/day | 15.6 | 18.0 | **17.1** | 17.7 | 15.6 | 17.2 |
| gap to SOD | 0 | +15 % | **+10 %** | +13 % | 0 | +10 % |

- RLS-D's gap to SOD at L1–L4 is +12 / +10 / +8 / +6 %. That is the same order as InWaterSense (+0 / +3 / +8 / +13 % at L1–L4).
- **SWITCH**: training-period replay chose SOD for both parameters, and it never switched. Phase 3 found that selection fails when the training period (winter) is unrepresentative. A tropical dry-season record has no such seasonal shift, and selection then works. This is consistent with Phase 3, not a contradiction.
- **Detector**: 0.19 alarms per day, about 2.9 per parameter per 30 days (the tuning rule was ≤ 2). This is expected, given the daily excursions.
- The **injected-event benchmark cannot run** at Weija: no event can be placed ≥ 1 day from segment starts and from Check B events. It is recorded as n = 0, not as a result.

## 6. What changes in the paper

- **C1 (predictability).** The headline must include Weija:
  - Wording: "ρ = 0.84 on 14 datasets; 0.62 including the held-out Weija, whose pre-registered prediction failed".
  - Diel share is a *necessary-looking* but **not sufficient** condition. The waveform (spike vs smooth) and sensor setup matter.
  - The Phase 2 statement "diel share beats fitted skill" no longer holds once Weija is included (L2: 0.62 vs 0.66).
- **Practical guidance (a strength for the IoT audience):**
  - On low-cost real deployments (InWaterSense, Weija), send-on-delta is the right default.
  - Prediction pays on clean, smooth-diel sites.
  - A short training replay can tell the two apart when the training period is representative.
- **Pre-registration is itself a contribution.** Reporting a failed out-of-sample prediction honestly is rare in this literature, and it strengthens the credibility of the rest.

## 7. Questions for Prof Adu-Manu (meeting 2026-10-05)

1. Where exactly were the probes: depth, flow-through chamber, enclosure, sun exposure? This would explain the midday spikes.
2. Which temperature probe measured the water: Sensor One, Two or Five? What were Sensors Four and Five?
3. Is the pH probe temperature-compensated? Was it calibrated during the deployment? Values of 9–12.8 are implausible for Weija.
4. Are the **raw, unprocessed** files available? The received files contain unflagged interpolation, and calcium and fluoride look like noise or filler from December on.
5. Can Weija appear in the paper as a held-out case study, with these caveats?

## 8. Reproduce

```
python src/data/clean_weija.py
python src/analysis/weija_phase1.py
python src/sim/run_phase2.py --datasets Weija --jobs 1 --out results/weija/phase2.csv
python src/sim/run_phase3.py --datasets Weija --out results/weija/phase3.csv
python src/analysis/weija_diagnostics.py
python src/analysis/weija_figures.py
```

The two runners resume from their output files, so delete those files first for a fresh run.
