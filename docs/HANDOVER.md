# HANDOVER: Paper 1 state as of 2026-10-04, evening (read this first in a new session)

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
| 4b Weija held-out test | done | pre-registered prediction failed (−16 % vs +30 %); C1 qualified (ρ 0.84 → 0.62) |
| 6 Writing | **draft v0.1 done 2026-10-04** | `papers/paper1/draft/` (PDF + DOCX + COVER_NOTE.md); taken to the Prof meeting 2026-10-05 |

## Open decisions (for the Prof)

1. **RQ4 framing.** Energy does not bind solar nodes (≥ 33× margin with a 2 W panel). Should RQ4 cover battery-only nodes, hardware size, and per-message / duty-cycle cost?
2. **Tolerances δ.** Ours are L0–L4 (L2: T 0.2 °C, DO 2 %sat, pH 0.1, EC 2% of median). Are there regulatory or EPA references?
3. **Venue.** IEEE IoT-J? Conference version first?
4. **Weija (analysed 2026-10-04):** permission to publish it as a held-out case; probe placement; which T probe; pH compensation; raw files? (`results/weija/WEIJA_REPORT.md` §7)
5. **InWaterSense hardware facts:** awake time per sample (the largest energy uncertainty, swept 1–30 s); node 1 location.

## Weija held-out test (DONE 2026-10-04; read `results/weija/WEIJA_REPORT.md`)

**Data.** The received files are in `cleaned/cleaned/` (ignore `__MACOSX` and the daily series). They had been pre-processed by someone else, and our profile found:
- Temperature Sensor Two is 100 % imputed in Feb–Mar 2019.
- **Unflagged interpolation**: values with > 3 decimals, and constant per-row ramps.
- Ca and F are white noise from December.
- pH swings 8.5–12.8 daily, tracking T (not simulated).
- DO and ORP are 5-hourly.
- **Usable:** T + EC every 32.5 min, 31 Oct 2018 – 4 Jan 2019 (2,478 cycles).
- Note: the earlier claim "pH has a T reading within 2 min 100 % of the time" counted imputed T. It was wrong.

**Result.**
- The pre-registered prediction (`results/weija/PREREGISTRATION.md`, RLS-T saving 30 % [18, 43] at L2) **failed**: the measured saving is −16 %.
- RLS-D sends +10 % reports versus SOD; SWITCH stays on SOD; the bound holds.
- Including Weija, the C1 link is ρ = 0.62 (was 0.84), and skill is level with diel share.
- Ruled out: sampling step, parameter set, history, probe, diel irregularity.
- Supported (post hoc): spike-shaped midday excursions (sun-heated small volume?).
- **A cleaning bug was found and fixed mid-way:** run 1 is archived in `results/weija/run1_ramp_bug/`, with the same conclusion.

**For the Prof:** see the questions in the report §7 (probe placement, which T probe, pH compensation, raw files, permission).

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
  - `data.py`: Dataset loaders; train fraction 0.2; segments split at gaps > 60 min. `load_weija()` is reachable only via `--datasets Weija` (not in `dataset_names()`, so the frozen 14-dataset runs are untouched); outputs go to `results/weija/` via `--out`.
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
- Weija: `src/data/clean_weija.py`, `src/analysis/weija_phase1.py`, `weija_diagnostics.py` (resumable), `weija_figures.py`; results in `results/weija/`.
- `tests/`: `test_sim.py`, `test_energy.py` and `test_weija.py`, 83 tests, all passing (`python -m pytest tests -q`).

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

## Paper draft (Phase 6)

- **Location:** `papers/paper1/draft/`.
  - Sources: `main.tex` plus `sec_*.tex`.
  - Bibliography: `refs.bib`. Every entry is verified (OpenAlex, arXiv or PDF); the three methods citations (Gardner & McKenzie, Page, Åström & Wittenmark) are verified too.
  - Outputs: `Paper1_draft_v0.1.pdf` and `.docx`.
  - `COVER_NOTE.md` lists the default choices and the open points.
- **Validation round 2026-10-10 evening:**
- The paper is 11 pp. and the supplement Tables S1–S10 + Figs. S1–S3.
- Errors found and fixed are listed in `docs/RESPONSE_TO_REVIEW_v0.2.md` ("Validation round").
- **Lesson:** never re-round a stored rounded value. All revision CSVs are now full precision (`%.6g`).
- `.gitignore` added. Literature PDFs, their txt copies, `cleaned/` (Weija raw), the drafts and the review docx are excluded. Files already committed in `5ff22fc` still need `git rm --cached` (the user commits).

**Build:** `pdflatex main; bibtex main; pdflatex main; pdflatex main`. Word copy: `pandoc main.tex -o Paper1_draft_v0.1.docx --citeproc --bibliography=refs.bib --csl=ieee.csl --resource-path=.:figures`.
- **Numbers.**
  - `src/analysis/paper_numbers.py` regenerates the dataset table, the Phase-1 statistics, the alarm coincidence (996 alarms / 523 near events / 87 expected) and the RLS-D-over-SOD energy gains. Its outputs go to `papers/paper1/draft/numbers/`.
  - Each number in the LaTeX has a `% source:` comment.
- **Corrections found while drafting** (all fixed in the reports):
  - Phase 2: the diel-band savings had picked the extremes.
  - Phase 3: violations at 5% loss are a total over 42 runs, not per site; the maximum number of switches is 21, not 16; halving δ costs +2–15%, not +4–15%.
  - Phase 4: RLS-D's energy gain over SOD is radio-dependent: +5.5% for RAI, +16.9% with default timers, not "0–7%".
- **Weija** is in Limitations only (one paragraph, flagged for the Prof).

## Revision v0.1 → v0.2 (started 2026-10-10). READ `docs/REVISION_PLAN_v0.2.md` FIRST

**Input:** an editorial review (`papers/paper1/Editorial_Review_When_Does_Prediction_Pay.docx`). Verdict: major revision before submission.

**User decisions:**
- Venue: **IEEE IoT-J** (IJDSN is the fallback).
- No hardware validation.
- No expert to label events: reference events become secondary to the injected events.

**Analyses A1–A11 are done.** Scripts are `src/analysis/revision_*.py` and `src/sim/run_ablation.py`; outputs are in `results/revision/`. Findings: `results/revision/A1_FINDINGS.md` and `A2_PROVENANCE.md`.

**Simulator change:**
- `run_dps_lossy` gained `ack_loss` and a protocol `ack_rs` (confirmed uplink with flagged resync).
- With ack_loss = 0, results are identical to v0.1.
- 106 tests pass.
- The real-data rerun writes `results/revision/loss_ack.csv` (`src/sim/run_loss_ack.py`).

**Done (2026-10-10 evening):**
- **Draft v0.2:** `papers/paper1/draft/Paper1_draft_v0.2.pdf` (14 pp.), `Paper1_draft_v0.2_supplement.pdf`, `Paper1_draft_v0.2.docx`.
- **Sources:** `main.tex` + `sec_*.tex`. The supplement is `supplement.tex`; its tables are generated by `src/analysis/revision_supplement.py`.
- **Figures:** `src/analysis/revision_figures.py` writes the `figures/v2_*.pdf` files.
- **v0.1 sources** are in `draft/v0.1_sources/`.
- **The point-by-point response** is `docs/RESPONSE_TO_REVIEW_v0.2.md`. Its open items (title, DOI, page budget, search method, AI disclosure, Weija permission) are for the user and the Prof.

**Build:**
- Paper: pdflatex main; bibtex main; pdflatex ×2.
- Supplement: pdflatex supplement ×2.
- Word: copy the sources and figures/v2_*.png into a temporary folder, change .pdf to .png in the includegraphics lines, and run pandoc there. On Windows, --resource-path with drive letters fails.

## Next steps (suggested order)

1. Run the Prof meeting with draft v0.1; record the decisions (`COVER_NOTE.md` open points) in `PAPER1_PLAN.md` §12, then revise the draft.
1b. Restyle the figures for the journal (no embedded titles; fitted line on the link figure; consistent palette).
2. ~~Profile and clean Weija~~ (done). After the meeting: record the Prof's answers. If raw Weija files arrive, re-run the chain (report §8).
3. ~~Verify the remaining citations~~ (done 2026-10-04).
3b. ~~Read the late papers 26–30 (Wu 2020, Almalki 2021, Shu 2019, Jarwan 2019, Liazid 2019)~~ (done 2026-10-10). Related Work was corrected (see the LITERATURE_NOTES cards and §E); results are unchanged. GD-LMS/OSSLMS = unit-step NLMS (verified numerically); adding it as a baseline is optional.
4. ~~Write Phase 6~~ (draft v0.1 done). Next: revise it after the Prof's comments, release the code (repository URL), choose the venue.


## Repository release (2026-10-10)
- **Files added:** `README.md` (reproduction steps), `requirements.txt`, `CITATION.cff`, `.zenodo.json`.
- **Zenodo DOI:** step-by-step guide in `docs/ZENODO_STEPS.md`; the user does it. When the user sends the version and concept DOIs, add the version DOI to the paper's Data and Code Availability section (bib entry) and the concept DOI to CITATION.cff and README.
- **Before pushing:** commit `5ff22fc` (unpushed) contains publisher PDFs and the Weija raw files. To remove it:
  ```
  git update-ref -d HEAD
  git rm -r --cached . -q
  git add .
  ```
  Check that `git ls-files | grep -E "\.pdf$|^cleaned/"` prints nothing, then commit.
- **No funding:** IoT-J charges mandatory fees beyond 8 pages, so either the paper fits 8 pages or the venue changes. Decision pending (user + Prof).
