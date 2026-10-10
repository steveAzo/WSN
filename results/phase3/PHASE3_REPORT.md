# Phase 3 report: the proposed scheme, its stress tests, and what did not work

*2026-10-04. Code: `src/sim/` (detector.py, inject.py, predictors.py: RLSDelta and Switch, engine.py: run_dps_lossy). Runs: `run_roc.py`, `run_rlsd.py`, `run_phase3.py`, `run_loss.py`. Analysis: `src/analysis/phase3_detector.py`, `phase3_rlsd.py`, `phase3_analysis.py`. Tables: `results/phase3/tables/`. Figures: `results/phase3/figures/`. Tests: 50 pass (`python -m pytest tests -q`).*

## 1. Protocol for avoiding self-deception

- **Tuning and test sites were fixed before any all-site result was seen.** The 7 tuning sites are every second USGS site in ID order. The test sites are the other 6 USGS sites plus InWaterSense.
- **Every design choice was made on tuning sites by a written rule:** the detector setting and the damping φ.
- **Ground truth for events.** Injected events with known onsets are added to the real test-period data. Each is a step or ramp of 3, 5 or 8 × the series' robust noise scale *in that month* (the same scale Check B uses), lasting 1–6 h. The offline Check B events are used only as a secondary check: the online detector is built differently from the labeller, to avoid circularity.
- **Every bounded run is asserted to never exceed δ.** No run in Phase 3 did.
- **Synchronisation is verified by tests.** A server-replay test reconstructs the server's view from the reports alone, for every new predictor and for the switch.

## 2. Final design

| Component | What it is | Why |
|---|---|---|
| Report decision | Report-level (any parameter exceeds δ → send all), bounded | Phase 2: saves 30–45% of reports |
| Predictor **RLS-D** | Linear model on the last 24 *changes*; ridge warm start; slow RLS adaptation (ρ = 0.01); **damped trend** (predicted change × φᵏ, φ = 0.97, k = steps since last report); **history repair** (blind stretch replaced by a straight line from previous to new reported value) | §3 |
| Event detector | Node-side two-sided CUSUM on a diel-aware 2-h-ahead residual (lag 120 min, k = 3, H = 8); an alarm forces a report and flags the event | §4 |
| Loss handling | Confirmed uplink (recommended); or unconfirmed uplink with sequence numbers and heartbeat resync, guaranteeing "**bounded or flagged**" | §5 |

## 3. Predictor: what failed, what worked

Gap to the per-site best fixed predictor, min(send-on-delta, RLS-T), in % of reports (median, [max]):

| Sites | Level | SOD | RLS-T | **RLS-D** | RIDGE-D (frozen) | SWITCH |
|---|---|---|---|---|---|---|
| Test (6) | L1 | +21.6 [+55] | 0.0 [0.0] | **−0.2 [+3.0]** | +0.7 [+2.8] | −0.8 [+1.1] |
| | L2 | +35.6 [+74] | 0.0 [0.0] | **−0.5 [+5.3]** | +0.2 [+3.1] | +1.7 [+6.9] |
| | L3 | +34.7 [+53] | 0.0 [0.0] | **+0.4 [+5.0]** | +1.1 [+9.3] | +4.7 [+12] |
| | L4 | +21.2 [+45] | 0.0 [+1.9] | **+2.4 [+16]** | +4.3 [+18] | +11.7 [+17] |
| Tune (7) | L2 | +26.8 | 0.0 | **−3.4** | +0.5 | +5.9 |
| | L4 | 0.0 [+85] | +12.4 [+60] | +12.5 [+23] | +1.2 [+18] | +20.5 [+29] |
| InWaterSense | L2 / L3 / L4 | 0 / 0 / 0 | +3 / +11 / +19 | +3 / +8 / +13 | +13 / +11 / +8 | 0 / 0 / 0 |

### Negative results (kept; each has a diagnosis)

1. **Selecting the predictor at deployment from early data fails.** Both diel share and replay on the training period were tried. The training period is mostly winter, when send-on-delta suffices; RLS-T wins in the busy summer. Training-replay picked the wrong predictor at 29–50% of site-levels, costing up to +85%. Training diel share puts InWaterSense (0.112) level with the Mississippi (0.115) and Illinois (0.117), where RLS-T wins. This is the Phase 1 seasonality finding again: diel share explains gains *across sites over a year* (Phase 2, ρ = 0.84), but not from a few winter weeks. (`selection_replay.csv`)
2. **Online switching between send-on-delta and RLS-T does not pay.**
   - Version 1 thrashed (70–130 switches): its shadow predictor was evaluated on the active one's reconstruction, so the "last value" shadow tracked the RLS prediction.
   - Version 2 uses exact node-side virtual pipelines and is stable (≤ 16 switches at L1–L3, 21 at L4; corrected 2026-10-04, previously "≤ 16"). It still loses: per-parameter virtual counts mis-rank predictors under report-level free-riding, and each switch has a transient cost.
   - It correctly stays on send-on-delta at InWaterSense.
3. **Online adaptation of the change model matters little.** Frozen weights (RIDGE-D) cost up to +13% on InWaterSense and are mixed elsewhere. The paper-default covariance (ρ = 10) causes large post-reset transients, so ρ = 0.01 is used.

### What worked, and why (mechanism)

At loose tolerances the predictor runs *blind* between reports, for hours. A one-step model fed its own predictions drifts, while "last value" cannot drift. When a report finally arrives, the correction jump (> δ by construction) enters the history as a fake fast change.
- **Damping** fades the extrapolation to "hold" during long blind stretches.
- **History repair** removes the fake jump.

Together they make one predictor near-optimal at L1–L3 with no selection step. This mechanism also explains Phase 2's tolerance sweet spot.

**Honest limits:**
- RLS-D still loses to send-on-delta on the noise-dominated InWaterSense (3–13%) and at L4 on some rivers.
- At L4, absolute report rates are 1–6 per day, so Phase 4 must show whether the difference matters for battery life.

## 4. Event detector

**Design path.**
- The first detector (CUSUM on the residual from a 24-h median) raised about one false alarm per parameter per day: water-quality residuals are smooth and autocorrelated.
- A diel-aware lag forecast fixed that.
- Round 2 tested banks of fast + slow detectors. They lie on the same trade-off curve as single detectors, so slow 5σ ramps remain hard in real time.

**Held-out results** (rule: median false alarms ≤ 2 per parameter per 30 days on tuning sites, then best detection of 5σ events):
- 5σ steps lasting 3–6 h: detected 70%. 8σ steps: 85%. 5σ ramps: 5–24%.
- Tuning and test detection agree (0.34 vs 0.34 mean), so there's no overfitting. False alarms are higher on test sites (2.5 vs 1.8).
- **About half of the "false alarms" fall within 2 h of a real Check B event on the same parameter:** 523 of 996, against 87 expected by chance, a 6× enrichment. The true false-alarm rate is about 1 per parameter per month.

**Cost and benefit in the full scheme** (USGS medians; "informed" = a report carrying the parameter while the event lasts):

| Configuration | Reports/day | 5σ steps | 5σ ramps | Check B events |
|---|---|---|---|---|
| RLS-D, L3 (tighter tolerance) | 7.81 | 0.87 | 0.88 | 0.81 |
| RLS-D, L4 | 2.40 | 0.62 | 0.53 | 0.62 |
| RLS-D + chosen detector, L4 | 2.71 | 0.88 | 0.61 | 0.62 |
| RLS-D + sensitive detector, L4 | 3.13 | **0.97** | **0.87** | 0.72 |

**Reading the table.**
- A loose tolerance plus the sensitive detector catches more injected events than tightening to L3, at **40% of the reports**.
- At L1–L2 injected events are 5–10 × δ and are always reported anyway; there the detector adds the *event flag* only (72–88% of steps flagged, median delay 15–45 min).
- **Limitation:** real Check B events improve less (0.62 → 0.72; L3 reaches 0.81). Real events are slower and more gradual than injected steps, and slow drifts are the detector's weak point.
- **Negative ablation:** halving δ during events costs +2–15% reports over RLS-D alone (L1–L4; corrected 2026-10-04 from "+4–15%") for at most +0.04 capture. It is dropped.

## 5. Packet loss and resynchronisation

All 14 datasets, L2; loss of 0.5%, 1% and 5%; 3 seeds (seed-to-seed variation ≈ 16%, so medians are stable); 1,680 runs.

| Protocol | Extra transmissions | Violations of δ | Time flagged as unverified (1% loss) |
|---|---|---|---|
| Confirmed, 2 retries | ≈ loss rate (+0.6% at 0.5%, +5% at 5%) | ≈ 0 (only at 5% loss: 18–23 steps *in total* over the 42 runs per predictor, 14 datasets × 3 seeds; the node knows of them. Corrected 2026-10-04: this cell previously said "≈20 per site per test year") | — |
| Unconfirmed, 24-h heartbeat | SOD +2%, RIDGE-D +4%, RLS-D +15%, RLS-T +79% | **0 unflagged** in all 1,120 runs | SOD 1.6%, RIDGE-D 10.5%, RLS-D 10.5% |
| Unconfirmed, 6-h heartbeat | SOD +8%, RIDGE-D +18%, RLS-D +30%, RLS-T +71% | **0 unflagged** | SOD 1.7%, RIDGE-D 4.1%, RLS-D 3.8% |

**Implications.**
- Over confirmed uplinks (NB-IoT/LTE-M), RLS-D keeps its savings at the cost of retries.
- Over unconfirmed links, send-on-delta is **self-synchronising**: any received report repairs it. That makes it the robust choice; frozen RIDGE-D with daily heartbeats is the model-based compromise.
- Phase 4 must price ACK reception and retries to finish this comparison.
- Two resync bugs were caught in smoke tests before the long runs and are now covered by regression tests: an empty history after each heartbeat silently turned RLS into send-on-delta, and ρ = 10 transients after resets.

## 6. Consequences for the paper

- **C2** becomes a predictor that is near-optimal without selection (RLS-D), plus documented negative results on selection and switching. This is narrower than planned, but every claim is evidenced.
- **C3** holds:
  - bounded error without loss;
  - "bounded or flagged" under loss (0 counterexamples);
  - better event capture per report at loose tolerances, with the slow-drift limitation stated.
- **Phase 4 (energy)** must answer three questions:
  - whether the L4 differences matter for lifetime;
  - the ACK cost of confirmed uplinks;
  - heartbeat costs under PSM/eDRX.

## 7. Citations to verify before writing

Gardner & McKenzie 1985 (damped trend); Åström & Wittenmark (covariance bounding); Page 1954 (CUSUM). All are marked TODO-CITE in the code.
