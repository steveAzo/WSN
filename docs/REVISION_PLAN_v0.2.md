# Revision plan: draft v0.1 → v0.2 (from the editorial review, 2026-10-10)

The source is `papers/paper1/Editorial_Review_When_Does_Prediction_Pay.docx`, read in full.
- Every number the review quotes was checked against the draft. All match, so the review describes the draft accurately.
- **Verdict:** major revision before submission; "scientific potential: high".

**Who does what:**
- **C** = Claude can do it alone.
- **C-run** = Claude can do it, but it needs new simulation runs. All are short (minutes to ~1 h on this laptop).
- **U** = needs the user or the Prof.

**Status:** `todo` / `doing` / `done` / `decided-not` (each with a reason).

## Facts checked before planning (2026-10-10)

**Venue: IJDSN.**
- It is published by **Wiley until January 2027**, then by **Sage** (Wiley's journal page).
- It is indexed in SCIE, Q3, with an impact factor of about 2.
- The Sage–EIFL agreement waives the APC for Ghana-based corresponding authors in gold OA journals. It covers articles that **enter production between 1 Jan 2026 and 31 Dec 2028**.
- So the waiver applies only if the article is accepted and goes into production after the move to Sage. Confirm with Sage that IJDSN is on the EIFL list.

**The 2026 preprints (review comment 17):**
- Kangethe 2026 (ADAPTIVEML): arXiv only.
- Lu 2026: accepted at IEEE ISSC 2026; proceedings pending.
- Kreković 2025: accepted at IEEE AIoT 2025. Cite the proceedings.

## A. Analyses (do these first; the text depends on them)

| # | Review item | Action | Who | Status |
|---|---|---|---|---|
| A1 | M4, M5, M15, M19; Results; Tables | **Site-clustered bootstrap CIs** for the headline effects: L2 saving, report-level saving, RLS-D gap, max-error ratio vs ADAPTIVEML, event-capture differences, lifetime gains. Exact p-values (state whether exact or asymptotic). Clustered bootstrap for the 52-observation correlation. Holm correction within families. Declare which analyses are confirmatory and which exploratory. | C | done (results/revision/A1_FINDINGS.md) |
| A2 | M7, M8; §9 ablation | **RLS-D ablation:** RLS-T → change model → +damping → +repair → both, on L1–L4, reported per site. **Design provenance table**: parameter, value, source, data used to choose it, frozen before test? Pseudocode. Operation and memory counts per step (no MCU measurement is available; say so). | C-run | done: A2_PROVENANCE.md (ablation, provenance, complexity) |
| A3 | M13; Fig. 3 | **Rate-matched frontiers.** Interpolate report-rate vs max-error/RMSE curves and compare at common rates, reporting the remaining mismatch. Check in the code whether ADAPTIVEML's σ(t) uses node-side readings, and state it. | C | done: A1_FINDINGS.md §A3 |
| A4 | M14 | **Decomposition figure:** periodic → separate SOD → bundled → report-level → learned predictor. | C | done: a4_decomposition*.csv (figure still to draw) |
| A5 | M9, M10; Fig. 4; minor | **Events.** Operating curves for steps and ramps separately, detection-delay distributions, event counts per site and parameter, denominators on Fig. 4. Check whether rounding to sensor resolution changes amplitude materially. | C | done: A1_FINDINGS.md §A5 |
| A6 | M10 | **Blinded adjudication sheet.** A stratified random sample of reference events and "false" alarms, plotted without detector output, for a domain expert to label. | C prepares, **U** labels | decided-not (D5: no adjudicator) |
| A7 | M12; §9 energy; minor (units, voltage, self-discharge, LoRaWAN duty cycle, payload, ACK energy) | **Energy sensitivity (tornado).** Payload realism using the real bundled payload size. LoRaWAN duty-cycle feasibility. State the battery voltage and the mAh→J conversion. List what is omitted (self-discharge, temperature, regulator, ageing) and say absolute lifetimes are optimistic. | C | done: A1_FINDINGS.md §A7 |
| A8 | Predictability section | Sensitivity of diel share to the number of weeks used to estimate it; uncertainty of the estimator. | C | done: A1_FINDINGS.md §A8 |
| A9 | M18; §9 deployment diagnostic | A **smoothness/forecastability statistic** alongside diel share. Weija would be its only "failure" case, so this can only be **exploratory**. Pre-register the statistic before computing it. | C | done (pre-registered; P1 failed as written, P2 exploratory) |
| A10 | Data section | Data-quality flow counts per dataset: raw → removed → segments → retained → excluded parameters. | C | done: a10_dataflow.csv |
| A11 | M3 | One unit throughout: "14 sites/datasets comprising N site–parameter series". Count N exactly. | C | done: 14 datasets / 55 simulated series / 56 Phase-1 series |
| A12 | M11; Methods | **Loss proposition** ("bounded or flagged"): its assumptions, when the flag starts and ends, multiple losses, heartbeat loss, duplicates, reordering, delayed ACKs, failure of all retries. Check against the simulator, and add tests where the simulator does not cover a case. | C | done: Proposition 1, ack_rs protocol, 23 tests, real-data rerun (a12_loss_ack_summary.csv) |

## B. Text and claims (after A)

| # | Review item | Action | Status |
|---|---|---|---|
| B1 | M1, M20; §10 | Reframe the paper around one systems thesis. Fewer contribution bullets. Convert bullet-heavy results to prose. Move lower-priority tables to supplementary material. | done in v0.2 (see RESPONSE_TO_REVIEW_v0.2.md) |
| B2 | M2 | "predicts" → "is strongly associated with". Add an external-validity subsection: ranking evidence vs deployment-time prediction. | done in v0.2 (see RESPONSE_TO_REVIEW_v0.2.md) |
| B3 | M6 | Rationale for the tolerances. Tolerances normalised by robust variability or measurement uncertainty. Justify L2 a priori. **Honesty check:** L2 was named the headline level before the Phase-2 results (see PAPER1_PLAN). Verify this before writing it. | done in v0.2 (see RESPONSE_TO_REVIEW_v0.2.md) |
| B4 | M18 | Move Weija from Limitations to a boundary-condition result. | done in v0.2 (see RESPONSE_TO_REVIEW_v0.2.md) |
| B5 | M17; Related Work | "We found no prior study that combines …" plus the literature-search cutoff date. Update the preprint statuses. Add 2024–26 coverage (search needed). | done in v0.2 (see RESPONSE_TO_REVIEW_v0.2.md) |
| B6 | Minor wording | "optimal" → "best among evaluated methods". "near-optimal" → "near the best evaluated fixed predictor". Spell send-on-delta (SOD) one way throughout. One term for the technique ("report suppression"). Define CSO. "rivers and streams". "one country/year". Narrow "without any guarantee". Make "cost nothing in reports" conditional. Make "always decide per report" conditional on the cost model, payload, duty cycle and tariff. | done in v0.2 (see RESPONSE_TO_REVIEW_v0.2.md) |
| B7 | System model | Tolerance types (absolute vs relative for EC). Synchronous sampling; effect of clock drift or asynchronous sensing. | done in v0.2 (see RESPONSE_TO_REVIEW_v0.2.md) |
| B8 | Minor | DO-saturation uncertainty. Trace-bound value and source. Numerical tolerance used by the assertions. Language and version; seeds. | done in v0.2 (see RESPONSE_TO_REVIEW_v0.2.md) |
| B9 | Abstract | Say the results are modelled; give the number of USGS sites; say the RLS-D evaluation is held out. | done in v0.2 (see RESPONSE_TO_REVIEW_v0.2.md) |
| B10 | Title | See decision D2. | done in v0.2 (see RESPONSE_TO_REVIEW_v0.2.md) |
| B11 | Figures | Restyle all figures (grayscale-safe, n stated, uncertainty bands, assumptions in captions). | done in v0.2 (see RESPONSE_TO_REVIEW_v0.2.md) |

## Decisions (user, 2026-10-10)
- **D1 venue: IEEE IoT-J.** Keep IEEEtran. IJDSN is the fallback.
- **D3 hardware: none.** State it as a limitation; energy is a *modelled* result, backed by the A7 sensitivity analysis.
- **D5 adjudication: nobody available.** Present reference events strictly as secondary to the injected-event ground truth. Drop A6.
- **B3 honesty finding:** no record shows L2 was named the headline level before the Phase-2 results (git history starts 2026-10-04; no earlier plan names it). Do **not** claim an a-priori choice. Report all levels with equal weight and add an external anchor for the tolerances (USGS record-accuracy classes, Wagner et al. 2006; verify from the source first).

## C. Needs the user or the Prof

| # | Item | Notes |
|---|---|---|
| D1 | **Venue** | IJDSN (Q3, IF ≈ 2, APC waived via EIFL from 2027) vs the original aim of a top journal (IEEE IoT-J, Q1). This changes the template and the page budget. |
| D2 | **Title** | The review offers two options; the current title also stays possible. |
| D3 | Hardware validation (M12) | Possible on one NB-IoT/LoRaWAN board? If not, state it as a limitation. |
| D4 | Archive (M16) | A Zenodo DOI needs the user's account. Claude prepares the release (README, hashes, configuration, seeds). |
| D5 | Expert adjudication (M10) | The Prof or a hydrologist labels the A6 sheet blind. |
| D7 | **Page budget (IoT-J)** | No hard cap, but $175 per page beyond 8 (IoT-J author guidelines, 2025). v0.1 is 12 pages (≈ $700). Decide with the Prof; detail goes to supplementary material either way. |
| D6 | Statements | Conflict of interest, data availability, code availability. Remove the "DRAFT" header at submission. |


## Findings log (details in results/revision/A1_FINDINGS.md and A2_PROVENANCE.md)

1. **Free-riding is not predictor-independent.** It backfires (up to 5×) for LMS and RLS γ = 0.98. Draft statements to fix: "irrespective of the predictor"; Integrity: "report-level ≤ bundled ≤ separate" (only bundled ≤ separate is tested). New design rule: state changes driven by own exceedances.
2. **L0 "persistence wins" is not significant after Holm correction** (p = 0.096).
3. **The 52-observation correlation p = 1e-7 is pseudo-replicated.** Site-clustered CI [0.22, 0.84].
4. **The confirmed-uplink protocol is unsafe under ACK loss.** Silent divergence: 427 unflagged violations in the synthetic test. Fixed by "ack_rs" (flagged resync), with 23 new tests. The real-data rerun is in progress.
5. **The sensitive detector has 11.7 FA/param/30 d.** Not stated in the draft.
6. **RLS-D needs about 10 KB RAM for 4 parameters; the Waspmote has 8 KB SRAM.** RIDGE-D is the 8-bit option.
7. **On tuning sites at L4, RLS-D is 12.4% behind the per-site best.** Only test sites were shown.
8. **ρ = 0.01 was not chosen by a written rule.** The φ rule re-applied at ρ = 0.01 still gives 0.97.
9. **Diel share ranks sites only with a long record.** First weeks give ρ 0.34–0.60 vs 0.84 for a full year: ranking evidence, not a deployment-time predictor.
10. **Smoothness pre-registration:** P1 failed as written; P2 (ρ 0.85) is exploratory only.
11. **Claims that got stronger:** the ADAPTIVEML comparison survives exact rate matching (100/100 runs). The equal-accuracy claim survives pairing (7.8× [5.2, 13.6]; RLS-D also lives 6% longer). The lifetime gain is > 1 under every sensitivity setting.


## Status 2026-10-10 evening
Draft v0.2 written: `papers/paper1/draft/Paper1_draft_v0.2.pdf` + supplement + docx; point-by-point response in `docs/RESPONSE_TO_REVIEW_v0.2.md`. Open: D2, D4, D6, D7, the literature-search description, the AI-disclosure wording, the Weija permission.
