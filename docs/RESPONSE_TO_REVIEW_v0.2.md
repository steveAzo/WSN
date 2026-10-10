# Response to the editorial review: draft v0.1 → v0.2 (2026-10-10)

**Files:**
- `papers/paper1/draft/Paper1_draft_v0.2.pdf` (14 pp.), `Paper1_draft_v0.2_supplement.pdf` (Tables S1–S7, Figs. S1–S2), and `Paper1_draft_v0.2.docx` (for comments).
- The v0.1 sources are kept in `papers/paper1/draft/v0.1_sources/`.

**Analyses:** scripts are `src/analysis/revision_*.py`, `src/sim/run_ablation.py` and `src/sim/run_loss_ack.py`; outputs are in `results/revision/`.

**Venue:** the target is IEEE IoT-J (user decision), not IJDSN. The review's comments are addressed regardless of venue.

## Major comments

| # | Comment | Response | Where |
|---|---|---|---|
| 1 | Contribution sprawl | Reframed around one thesis: suppression judged under per-report LPWAN costs, with prediction used only where the signal supports it. New lead result: the decomposition of the saving into accounting structure vs prediction. Contributions cut from 5 groups to 3; RQs reordered. | Intro; §VI-A; Fig. 1 |
| 2 | External validity; "predicts" | "Predicts" → "is strongly associated with" throughout. New *Boundary conditions* subsection: Weija promoted from Limitations (comment 18); deployment-time analysis showing diel share from the first 1–13 weeks ranks sites at only ρ = 0.34–0.60 vs 0.84 for a full year. New *External validity* subsection separating structural (accounting) from conditional (prediction) evidence. | §VI-C; §VII-B |
| 3 | Unit of analysis | 14 datasets / 55 simulated site–parameter series / 56 Phase-1 series, stated once and used consistently. | §IV-A; Table S1 |
| 4 | Effect sizes and CIs | Every headline effect is now reported with a 95% site-bootstrap CI and exact Wilcoxon or permutation p. | §V-E Statistics; all of §VI; Table S5 |
| 5 | Pseudo-replication | The 52-observation correlation now has a site-clustered CI [0.22, 0.84], per-parameter values, and site means (ρ = 0.72). The naive p = 1e-7 is no longer quoted. | §VI-B; Table S3 |
| 6 | Tolerances; why L2 | Levels related to the USGS record-accuracy classes (Wagner et al. 2006, Table 18, verified from the PDF): L2 is the loosest level within "excellent" for all four parameters. **We state honestly that this correspondence was noted after the sweep was designed**; no record shows L2 was pre-declared. All levels are reported. | §V-E Tolerances; §VII-C |
| 7 | RLS-D specification | Algorithm 1 (state, update order, repair, gaps, resync, trace bound ρw); operation and memory counts. **New finding:** RLS-D needs about 10 KB for 4 parameters, more than the Waspmote's 8 KB SRAM (verified: Libelium guide, Atmel datasheet). RIDGE-D is the 8-bit variant. | §V-B; Alg. 1 |
| 8 | Tuning leakage; provenance | Provenance table for every parameter. φ re-selected at the final ρ: still 0.97. ρ = 0.01 and the sensitive detector are declared as **not rule-chosen**. RLS-D results now also shown on tuning sites (L4: +12.5%). Ablation added. | Table S2; §V-B; Table V; Table S6 |
| 9 | Events | Claim narrowed to abrupt changes; gradual drift stated as unresolved. Operating curves for steps and ramps separately; detection delays; **false-alarm rate of the sensitive detector (11.7/param/30 d) now stated**. | §VI-F; Fig. 4; Table VI; Table S7 |
| 10 | Reference-event validation | No adjudicator available (user decision), so reference events are presented as secondary to injected ground truth. Counts reported (1,612 events). | §IV-B; §VII-C |
| 11 | Formal loss guarantee | Proposition 1 with assumptions A1–A4 and a proof sketch; certified/flagged/provisional states; certification delay bound. **New finding:** the v0.1 confirmed protocol fails silently under ACK loss (5% loss: unflagged violations in every RLS-D run, 1,230 steps). Fixed by flagged resynchronisation (0 unflagged in all 504 runs). 23 new unit tests (106 pass). Duplicates and stale reports handled by A3. Bursty loss and reordering not simulated (stated). | §III-D; §V-D; §VI-G |
| 12 | Energy realism | All lifetimes labelled "modelled". One-at-a-time sensitivity: gain > 1 under every input. Battery voltage and idealisations stated (lifetimes optimistic). Payload realism (15–23 B: ±0.03 in gain). Duty cycle checked. No hardware validation (user decision): stated as a limitation. | §V-F; §VI-H; Table S4 |
| 13 | ADAPTIVEML fairness | Exact rate matching by interpolating the bounded front. ADAPTIVEML is worse in 100/100 cases; 10.6× [8.6, 15.1] at α = 1. Unmatchable runs excluded and counted. σ(t) information question answered (node-side for both). | §V-A; §VI-D; Fig. 3 |
| 14 | Prediction vs structure | New decomposition figure (every cycle → separate → bundled → report-level → RLS-D) with CIs per level. | §VI-A; Fig. 1 |
| 15 | Multiplicity | Holm correction within families. Confirmatory set declared, **at revision time** (stated as such). The L0 result ("persistence wins") becomes non-significant after Holm (p = 0.096) and is now worded as a tendency. | §V-E; Table IV |
| 16 | Archive with DOI | Data and code availability section added (versions, seeds). **The Zenodo DOI needs the user's account** (TODO in main.tex). | Back matter |
| 17 | Literature currency | Kreković → IEEE AIoT 2025 proceedings (DOI). Lu → accepted at the Irish Signals and Systems Conference 2026. Kangethe still arXiv only. Papers 26–30 read and Related Work corrected. "No work" → "we found no prior study that combines …"; search cutoff October 2026. **The search method itself must be described by the user** (TODO). | §II |
| 18 | Weija as a boundary condition | Promoted to Results. Smoothness statistic **pre-registered**; P1 failed as written (InWaterSense's noise profile is rougher); P2 exploratory (ρ 0.85). Presented as a hypothesis. | §VI-C |
| 19 | Equal-accuracy pairing | Paired per site: 7.8× [5.2, 13.6] smaller error, and RLS-D also lives 6% longer [2, 14]. Site-level figure in the supplement. | §VI-H; Fig. S2 |
| 20 | Length and narrative | Rewritten for economy: 14 → 11 pages (≈ 8,500 → 6,100 words) without removing any result. Bullets → prose; duplicated explanations removed; method costs at L2, unconfirmed-protocol costs, detect-vs-tighten and gain-vs-sensing moved to the supplement (Tables S8–S10, Fig. S3) with their key numbers kept in the text. IoT-J charges mandatory fees beyond 8 pages and there is no funding, so see D7. | whole paper |

## Section comments

| Section | Response |
|---|---|
| Abstract | Says "modelled"; gives the site count; says RLS-D is held out; no universal wording; 248 words. |
| Introduction | "without any guarantee" → names the reconstruction-error bound and timeliness; the systems question comes first. |
| Related Work | Conservative novelty wording; cutoff date; preprints updated. |
| System Model | Tolerance types (absolute; EC converted per site); synchronous sampling and the shared step index stated. |
| Data | Flow counts (Table S1); InWaterSense cleaning counts in the text; training length per site. |
| Predictability | Estimator vs data length analysed (§VI-C). |
| Methods | RLS-D pseudocode; loss protocols defined precisely; training, warm-up, tuning and test distinguished; unequal training lengths stated. |
| Results | CIs and site-level distributions; consistent units (% of every cycle). |
| Discussion | "Decide per report" made conditional on the cost model, payload, duty cycle and tariff. |
| Conclusion | "Cost nothing" bounded to the evaluated traces and the matched comparison. |

## Figures and tables

| Item | Response |
|---|---|
| Figures | All figures redrawn: validated colour-blind-safe palette, distinct markers and line styles (grayscale-safe), no embedded titles, n stated, CIs. Old Fig. 1 (diel vs skill) moved to the supplement (S1); Fig. 2 marks the InWaterSense and Weija boundary cases; the energy assumptions are in the captions. |
| Tables | n and CIs added, and labels made explicit. Lower-priority tables moved to the supplement (S1–S7). |

## Minor comments

All addressed in the text:
- one term ("report suppression"); "send-on-delta (SOD)" spelled one way;
- "optimal" removed; "near-optimal" replaced;
- Spearman p by permutation; event counts; rounding effect (median 1.2%);
- CSO defined; DO-saturation uncertainty (~0.4%);
- trace-bound value; assertion tolerance 1e-9; software versions; seeds;
- mAh → J at 3.7 V; idealisations; LoRaWAN duty cycle; payload; ACK capacity (qualitative);
- "rivers and streams"; "one country/year";
- "DRAFT" header kept until submission (D6).

## Errors in v0.1 found during the revision (corrected)

1. "Report-level decisions save … irrespective of the predictor": false for LMS and RLS γ = 0.98 (up to 5.5× more reports). Now explained as a design rule.
2. Methods/Integrity claimed tests of "report-level ≤ bundled ≤ separate". Only bundled ≤ separate is guaranteed and tested.
3. The confirmed-uplink protocol was not bounded-or-flagged under ACK loss (see comment 11).
4. Paper 29 (Jarwan) was called a review; paper 30 (Liazid) was cited for adaptive thresholds (it is about model maintenance).

## Still open (needs the user or the Prof)

| # | Item |
|---|---|
| D2 | ~~Title~~: decided 2026-10-10 (the review's recommended title). |
| D4 | Zenodo DOI for the code release. |
| D6 | Conflict-of-interest / funding statements; remove the DRAFT header at submission. |
| D7 | **Venue vs length (no funding):** IoT-J charges mandatory fees beyond 8 pages, and there is no funding. Either cut to 8 pages or choose a venue with no author charges. |
| — | Describe the literature search method actually used in Phase 0 (TODO in sec_related.tex). |

## Validation round (2026-10-10, evening)

Every number in the text was re-derived from the result files.

**Errors found and corrected:**
1. "Saves 29–45% of reports **at every site**" (abstract, introduction, results, discussion, conclusion). 29–45% is the range of the *median* per-site saving across levels; individual sites save as little as 10%. Now: "a median 29–45%, and saves reports at every site".
2. "Within 0.4% at L1–L3" contradicted the −0.5% at L2 in the same sentence. Now "within 0.5%".
3. "Frozen weights (RIDGE-D) cost up to 13% on InWaterSense, mixed elsewhere (−9 to +4%)" (from v0.1). The 13% was the gap to the per-site best, not the cost relative to RLS-D, and −9 to +4% does not reproduce. Recomputed: median difference ≤ 2% at L1–L3 (per site −7 to +11%), up to +10% on InWaterSense.
4. **Double rounding** (a value rounded, stored, then rounded again):
   - unconfirmed-protocol overhead: SOD +2.1% → **+2.0%**; RLS-T +79.3% → **+79.2%** (both inherited from v0.1);
   - RLS-D L2 gap CI upper bound 3.1 → **3.0**;
   - ablation CHG at L4 6.2 → **6.3**; RLS-D on tuning sites at L4 12.4 → **12.5**;
   - confirmed-uplink overhead at 0.5% loss "+0.6%" → "+0.5–0.6%".
   
   All revision scripts now store full precision (6 significant figures) and were re-run; every other number reproduced.
5. "Event capture 0.93–0.98 for every bounded predictor" excluded LMS (1.00). Now names the four predictors.
6. "The event detector costs about 1%" was computed for the *sensitive* detector. Wording corrected.
7. Supplement items S5–S7 and Fig. S1 were not cited in the main text. Citations added.

**Also done:**
- Figures 1(b) and 2 cleaned: legend above the panel; no free text in Fig. 2, with the statistics moved to the caption.
- AI acknowledgement removed (the user will add it if needed).
- Weija is publishable (user, 2026-10-10).
- `.gitignore` added.
