# HANDOVER: Paper 1 state as of 2026-10-04 (read this first in a new session)

**Project.** NSS research with Prof Kofi Sarpong Adu-Manu (University of Ghana). Paper 1 is working-titled *"When Does Prediction Pay? Predictability-Aware, Error-Bounded Report Suppression for LPWAN Water-Quality Monitoring"*. Target venue: IEEE Internet of Things Journal (to confirm with the Prof). The user is a new researcher: explain reasoning, hand-hold, give reading/thinking tasks. **Only multi-hour runs go to the user** (with a progress display); everything shorter, Claude runs itself.

**Read in this order:**
1. `docs/TUTORIAL_PAPER1.md`: ground-up explanation of everything, plus meeting prep.
2. `PAPER1_PLAN.md`: plan v3. §2 is the evidence summary for all phases; §11 is the work plan.
3. Phase reports, in order:
   - `results/phase1/PREDICTABILITY_REPORT.md`
   - `results/phase2/PHASE2_REPORT.md`
   - `results/phase3/PHASE3_REPORT.md`
   - `results/phase4/PHASE4_REPORT.md`
4. `papers/paper1/LITERATURE_NOTES.md` (paper cards, gap table) and `papers/paper1/README.md` (reading list).

## Status

| Phase | State | Key output |
|---|---|---|
| 0 Literature | done | 25 papers, notes, gap analysis |
| 1 Data and predictability | done | InWaterSense unpredictable; 13 USGS rivers; diel share explains skill (ρ = 0.66) |
| 2 Baselines (2,016 runs) | done | diel share predicts DPS gain (ρ = 0.84); report-level saves 30–45%; ADAPTIVEML max error 8–17× worse |
| 3 Proposed scheme | done | RLS-D predictor, CUSUM detector, loss protocols; negative results documented |
| 4 Energy | done | battery life 1.1–3.5×; equal-accuracy view; solar nodes not energy-bound → RQ4 reframing pending |
| 5 Hardware | optional | lab server down; not needed |
| 6 Writing | **next** | after the Prof meeting |

## Open decisions (for the Prof)

1. **RQ4 framing.** Energy does not bind solar nodes (≥ 33× margin with a 2 W panel). Should RQ4 cover battery-only nodes, hardware size, and per-message / duty-cycle cost?
2. **Tolerances δ.** Ours are L0–L4 (L2: T 0.2 °C, DO 2 %sat, pH 0.1, EC 2% of median). Are there regulatory or EPA references?
3. **Venue.** IEEE IoT-J? Conference version first?
4. **Weija data (arrived 2026-10-04):** whether and how to use it as a third case study; what probes and settling times; what radio.
5. **InWaterSense hardware facts:** awake time per sample (the largest energy uncertainty, swept 1–30 s); node 1 location.

## Weija data (NEW, not yet analysed)

**Location:** `cleaned/cleaned/` (also a `__MACOSX` folder, which can be ignored). The Prof says part of the data was lost.
- Files are `<param>_cleaned_records.csv` (Datetime, Value, Parameter, Label, Unit, Probe Name, Was_Imputed) and `*_daily_series.csv`.
- Parameters: calcium, conductivity, dissolved oxygen, fluoride, ORP, pH, temperature.
- **Range:** 30 Oct 2018 to 11 Mar 2019, about 119 days with data (dry season).
- **Sampling:**
  - pH, conductivity, calcium and fluoride: about every 32.5 min.
  - Temperature: about every 18 min, **24% imputed**.
  - DO and ORP: about every 5 h, too coarse for this simulation.
- **Suspicious values:** pH 0.00–13.13; DO max 46 mg/L; minimum floors at 2.00 (calcium, DO). These need a Phase-1-style clean (range limits, Hampel filter, **drop imputed rows**).
- **Usable core:** T, pH and EC are co-sampled (pH has a T reading within 2 min 100% of the time; EC 94%).
- **Plan:**
  - run Check A (predictability), Check B (events) and the Phase 2/3 pipeline on T/pH/EC at about 30-min steps;
  - add a `load_weija()` to `src/sim/data.py`;
  - note that the Phase 3 detector and RLS-D were tuned on 15-min data, so their time constants may need care at 30 min.
- **Do not use the daily series** (they are aggregated and imputed).

## Code map (Python, Windows; see memory note on UTF-8)

- `src/data/`
  - `clean_inws.py`, `clean_usgs.py`, `fetch_usgs.py`: data preparation.
  - Clean data lives in `data/clean/` (`inws_cycles.csv`, `usgs/<site>.csv`).
- `src/analysis/`
  - Phase 1: `check_a.py`, `check_b.py`, `seasonal.py`, `quantization.py`, `theory_check.py`.
  - Later phases: `phase2_analysis.py`, `phase3_detector.py`, `phase3_rlsd.py`, `phase3_analysis.py`, `phase4_analysis.py`.
- `src/sim/`
  - `engine.py`: `run_dps` (modes separate / bundled / report; optional detector and tighten); `run_periodic`; `run_batch`; `run_dps_lossy` (protocols "ack" and "seq", heartbeat, priming).
  - `predictors.py`: LastValue (SOD), LMS, DBP, Ridge, RLS, **RLSDelta** (proposed: change model, damping φ, history repair, `adapt`, ρ), Switch (negative result).
  - `detector.py`: CusumDetector (modes median / lag), DetectorBank, `make_detector`.
  - `inject.py`: injected-event benchmark.
  - `data.py`: Dataset loaders; train fraction 0.2; segments split at gaps > 60 min.
  - Runners:
    - `run_phase2.py`: results in `results/phase2/results.csv`.
    - `run_roc.py`: detector ROC, results in `results/phase3/roc.csv`.
    - `run_rlsd.py`: φ tuning.
    - `run_phase3.py`: results in `results/phase3/phase3.csv`.
    - `run_loss.py`: results in `results/phase3/loss.csv`.
  - All runners are resumable, with a `--jobs` option.
- `src/energy/`
  - `params.py`: every parameter with its source.
  - `model.py`: NB-IoT and LoRaWAN per-report energy, daily energy, lifetime.
  - `run_phase4.py`: results in `results/phase4/lifetime.csv`.
- `tests/`: `test_sim.py` and `test_energy.py`, 78 tests, all passing (`python -m pytest tests -q`).

## Frozen design choices (and why)

- **Data split:** first 20% of each series for training, remaining 80% for test.
- **Pre-registered tuning:** tuning sites are every 2nd USGS site in ID order (7 sites). Test sites are the other 6 plus InWaterSense.
- **Detector:** lag 120 min, k = 3, H = 8 (rule: median false alarms ≤ 2 per parameter per 30 days on tuning sites, then maximum detection of 5σ events). Sensitive variant: k = 2, H = 4. Config in `results/phase3/detector_choice.json`.
- **RLS-D:** φ = 0.97 (`results/phase3/rlsd_choice.json`), ρ = 0.01, w = 24, repair on. RIDGE-D = the same with frozen weights, for unconfirmed links.
- **RLS-T** = RLS with γ = 0.999. The paper default γ = 0.98 is unstable on 15-min data; both are reported.
- **Energy:** host awake during reports by default (sensitivity: asleep); confirmed uplink with 1% loss; 6,600 mAh battery.

## Machine constraints and lessons

- **Memory:** the laptop has 3.6 GB RAM, often < 0.1 GB free. Use `--jobs 1` and close the browser. An out-of-memory error shows as `ParserError ... out of memory` or `_ArrayMemoryError`.
- **Ctrl+C in PowerShell can leave pool workers running in the background.** Check with `Get-Process python`; stop with `Stop-Process -Name python`.
- **Expected warnings:** "Mean of empty slice" is now silenced in the runners. Remove `2>&1` from commands in PowerShell 5.1.
- **Citations still to verify:** Gardner & McKenzie 1985 (damped trend), Åström & Wittenmark (covariance bounding), Page 1954 (CUSUM). A measured GPRS per-report energy source is needed before any GPRS claim.

## Next steps (suggested order)

1. Run the Prof meeting and record its decisions in `PAPER1_PLAN.md` §12.
2. Profile and clean Weija, and decide whether it becomes the third case study.
3. Verify the remaining citations from the actual texts.
4. Write Phase 6, starting with Methods and Results, then the Introduction and Related Work.
