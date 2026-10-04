# Phase 2 report: baselines on 14 real water-quality series

*2026-10-03. Reproduce with `python src/sim/run_phase2.py` (≈1 h on 2 cores), then `python src/analysis/phase2_analysis.py` (seconds). Tables: `results/phase2/tables/`. Figures: `results/phase2/figures/`.*

## What was done

**Simulation setup.** A trace-driven simulator (`src/sim/`) replays each real series as a sensor node would see it.
- At every sampling cycle the node decides whether to transmit.
- The server reconstructs every parameter from what it receives.
- Training uses the first 20% of each series; all metrics are on the remaining 80%.
- The series are InWaterSense node 1 (T, EC, DO; 10 min) and 13 USGS rivers (T, EC, DO, pH; 15–60 min).

**Methods compared (2,016 runs in total).**

| Family | Methods |
|---|---|
| Error-bounded DPS | send-on-delta (SOD); Santini LMS; Raza DBP; Ridge (the ADAPTIVEML predictor, frozen); RLS with γ = 0.98 (paper default) and γ = 0.999 (RLS-T) |
| Adaptive threshold, not bounded | ADAPTIVEML; ADAPTIVEML-RLS, at α ∈ {0.5, 1, 1.5, 2, 3} |
| Fixed schedule | periodic reporting (every cycle, 30 min, 1 h, 2 h, 4 h); Ghosh-style batching (30 min – 4 h) |

**Settings.**
- Five tolerance levels L0–L4 per parameter. L2: T 0.2 °C, DO 2 %sat, pH 0.1, EC 2% of median.
- Three accounting modes:
  - *separate*: one report per exceeding parameter (how InWaterSense transmits);
  - *bundled*: exceeding parameters share a report;
  - *report*: any exceedance sends all parameters.

**Integrity checks.**
- No bounded run ever exceeded its tolerance (checked automatically).
- No duplicate runs.
- 25 unit tests pass: server replay is in sync, accounting is ordered correctly, and edge cases behave.

## Findings

### F1. On predictable rivers a learned predictor beats send-on-delta, but only at moderate tolerances (t1, t2)

At L2 in report mode, RLS-T is the cheapest bounded method on **13 of 14** datasets. Median cost, USGS (% of reporting every cycle):

| SOD | DBP | Ridge | **RLS-T** | RLS (γ = 0.98) | LMS |
|---|---|---|---|---|---|
| 28.3 | 24.4 | 23.3 | **21.3** | 87.0 | 99.6 |

RLS-T vs SOD across tolerance levels (13 USGS sites, paired Wilcoxon):

| Level | L0 | L1 | L2 | L3 | L4 |
|---|---|---|---|---|---|
| Median saving | −6% | +19% | **+26%** | +7% | +1% |
| Wins | 3/13 | 12/13 | **13/13** | 10/13 | 7/13 |
| p | 0.05 | 0.0005 | 0.0002 | 0.008 | 0.50 (n.s.) |

Interpretation:
- **At very tight tolerances** the predictor cannot beat sensor noise, so persistence wins.
- **At very loose tolerances** almost nothing is sent either way, so there is little left to save.
- **The benefit lies in between.** No earlier DPS paper reports this tolerance sweet spot across many sites.

**InWaterSense is the counter-case.** SOD is best or tied at every level (RLS-T −3% at L2, −19% at L4), as Phase 1's "no predictability" result predicted.

**Paper defaults fail.**
- Santini's LMS (μ = 1/(100·Eₓ)) settles into a moving average and stays in "normal" mode, reporting ≈ 99% of samples.
- ADAPTIVEML-RLS's γ = 0.98 (memory ≈ 50 samples for 24 weights) is unstable on 15-min data.

We report both the paper defaults and our tuned RLS-T, to avoid straw men.

*Caveat:* γ = 0.999 was chosen on one site (Frenchtown). The other 12 sites are therefore out of sample for this choice, but Frenchtown is not.

### F2. Prediction pays where the day–night cycle dominates (t7, fig5): the paper's central result

The Phase 1 **diel variance share** (an offline, model-free statistic) predicts the Phase 2 saving of RLS-T over SOD:

| Level | All 14 sites: ρ (p) | USGS only: ρ (p) | Worst leave-one-out ρ (USGS) |
|---|---|---|---|
| L1 | 0.71 (0.005) | 0.67 (0.01) | 0.58 |
| **L2** | **0.84 (0.0002)** | **0.80 (0.001)** | **0.75** |
| L3 | 0.78 (0.001) | 0.74 (0.004) | 0.67 |

- At L2 the saving ranges from 6–15% (diel share 0.12–0.20) to 39–43% (diel share 0.40–0.56).
- Diel share predicts the gain better than fitted 1-h forecast skill (ρ 0.80 vs 0.55 at L2, USGS).
- **Practical meaning:** an operator can decide from a few weeks of data, before deployment, whether prediction is worth implementing on a node.

### F3. Report-level decisions save 30–45% of reports versus per-parameter DPS (t3; RQ2)

Median savings over *separate* accounting (USGS, four bounded methods):

| Level | Bundling (shared report) | Free-riding (send all) | Total |
|---|---|---|---|
| L0 | 41.7% | 3.2% | 44.0% |
| L2 | 17.4% | 22.5% | 35.9% |
| L4 | 6.9% | 25.0% | 30.6% |

- At tight tolerances most of the saving comes from bundling simultaneous exceedances.
- At loose tolerances most of it comes from *free-riding*: refreshing the other parameters when one must be sent anyway, which delays their next exceedance.
- Free-riding helps in **253 of 260** USGS cases (Wilcoxon p = 7e-44).
- InWaterSense saves 33–43%, even with no predictability.

**Novelty must be stated carefully:**
- Santini & Römer 2006 proposed (but did not evaluate) a block threshold.
- Ghosh 2022 batches at wake-ups.
- Our contribution is the quantified decomposition across 14 sites.

### F4. ADAPTIVEML's adaptive threshold gives up the error guarantee, at no saving in reports (t4; RQ3)

Each ADAPTIVEML run is compared with the bounded RLS-T run whose report rate is closest (USGS, report mode):

| α | Reports (ADAPTIVEML / RLS-T) | Max-error ratio (geo. mean of parameters) | RMSE ratio | Event capture (ADAPTIVEML / RLS-T) |
|---|---|---|---|---|
| 0.5 | 74% / 66% | 8.4× | 1.9× | 1.00 / 1.00 |
| **1 (paper default)** | 56% / 49% | **11.8×** | 3.3× | 0.99 / 1.00 |
| 2 | 39% / 40% | 14.6× | 4.5× | 0.93 / 0.99 |
| 3 | 35% / 34% | 17.4× | 5.3× | 0.89 / 0.99 |

- ADAPTIVEML has the larger max error in **100% of site × α cases**, and it uses more reports at α ≤ 1.
- Per parameter at α = 1: T 11×, EC 17×, DO 12×, pH 7×.
- Using the RLS-T predictor inside ADAPTIVEML does not fix this (7.7–17×). The cause is the threshold rule α·σ(t): it widens exactly when the signal moves.

### F5. Fixed schedules: periodic loses accuracy, batching loses timeliness (t5, fig4)

At the same report count as RLS-T:

| Baseline | Accuracy | Timeliness |
|---|---|---|
| **Periodic** (zero-order hold) | max error **4–24× larger** (EC worst, pH mildest) | — |
| **Batching** | exact data | late: mean data delay 7.5–112 min, median event delay 15–120 min |

At 30–60-min-equivalent rates, RLS-T reports events with a median delay of 0 min.

### F6. Loose tolerances miss events, whatever the predictor (t6, fig6): the main limitation and Phase 3 motivation

Median share of events reported while still ongoing (USGS; events from Check B):

| Level | L0 | L1 | L2 | L3 | L4 |
|---|---|---|---|---|---|
| SOD | 1.00 | 1.00 | 0.93 | 0.83 | 0.63 |
| RLS-T | 1.00 | 1.00 | 0.95 | 0.81 | 0.63 |
| DBP | 1.00 | 1.00 | 0.98 | 0.86 | 0.70 |

- A bounded error guarantee does *not* guarantee that events are seen.
- An event smaller than δ never triggers a report.
- At low report rates (≈ 6–10% of periodic), periodic captures slightly more events than RLS-T (0.82 vs 0.75).
- LMS's capture of 1.0 is trivial, since it reports almost everything.
- These are compared at equal *tolerance*; RLS-T sends fewer reports at the same level.

→ **Phase 3** adds an innovation-based event detector (GLR/CUSUM, paper 15) that forces reports and tightens δ at onset. Its target is to raise capture at L3–L4 with a small report overhead.

## Consequences for the paper

1. **C1 is supported strongly.** Predictability (the diel share) explains when DPS pays (F1, F2), and InWaterSense is the documented negative case.
2. **C2 and the proposed scheme.**
   - Predictor choice must be per site: SOD on noise-dominated nodes, RLS-T on diel rivers.
   - Diel share is a credible selection signal.
   - The report-level decision is worth ≈ 1/3 of reports on its own (F3).
3. **C3.** The bound costs nothing in reports compared with ADAPTIVEML (F4). Events need an explicit detector (F6).
4. **Open items.**
   - Event delay under injected events with known onsets.
   - Tuned-LMS sensitivity variant.
   - Energy translation (Phase 4). Per-report LPWAN costs make the report savings above roughly proportional to energy savings, which Phase 4 must verify with sync and heartbeat overheads.

## Limitations

- The tolerance levels are ours, not regulatory. The Prof is asked for references.
- Events are labelled offline by a statistical rule (Check B), so there is no ground truth.
- Only one InWaterSense node is used, plus 13 USGS sites from one year (2023). One USGS site (05420400) has only 11 events.
- Lossless links are assumed. Loss and resync are deferred to Phase 3.
