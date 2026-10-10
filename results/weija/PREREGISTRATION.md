# Weija held-out test: prediction written BEFORE any simulation (2026-10-04)

**Why this file exists.** Weija (Prof Adu-Manu's 2018-19 Densu/Weija deployment, Ghana) was
never used for any tuning. All frozen choices (detector, RLS-D phi, RLS-T gamma) came from the
7 USGS tuning sites. So Weija is an independent test of the paper's central claim (C1): *the
diel variance share of a site predicts how much prediction-based suppression saves over
send-on-delta*. We write the prediction down first, so that it cannot be adjusted afterwards.

## Inputs fixed before the run

- Data: `data/clean/weija_cycles.csv` from `src/data/clean_weija.py` (imputed rows dropped,
  unflagged interpolation ramps removed). Simulated parameters are **T (Sensor Two) and EC**.
  pH is not simulated, because its values are unverified (see the cleaner docstring).
  The window is 31 Oct 2018 to 4 Jan 2019: 2,742 complete cycles at a 32.5-min step.
- Phase 1 numbers for Weija (Check A, 1-h = 2 steps):
  - diel share: T 0.706, EC 0.075, so the **site mean is 0.39**;
  - 1-h AR skill: T +0.20, EC +0.08.
- The Phase 2 relation over the 14 existing datasets at L2 is
  `gain = 1.2 + 74.0 * diel` (R^2 = 0.78), where gain = 100 * (1 - RLS-T / SOD) in report-level reports.

## Prediction

- **Primary:** RLS-T saves **30 %** of reports versus SOD at L2. The 90 % prediction interval is
  **[18 %, 43 %]**.
  - Hit: the measured gain lies inside the interval.
  - Miss: it lies outside. A miss is reported, not explained away.
- **Directional expectation (weaker; stated in advance):** Weija lies *below* the fitted line.
  The 1-h skill of T (0.20) is well below that of USGS sites with similar diel share
  (0.46-0.68), because Sensor Two is noisy (spikes up to 37.8 degC).
- **Per parameter:** most of the saving comes from T; EC gains little (diel share 0.075).

## What would change the paper

| Outcome | Consequence for the paper |
|---|---|
| Hit | Weija becomes an out-of-sample, cross-continent confirmation of C1. |
| Miss, below the line | Supports adding sensor-noise share as a second predictor (RQ1 already names it). |
| Miss, above the line | The diel-share relation is conservative; we report it as such. |

---

## Addendum (same day, after the runs; the prediction above is unchanged)

- **Outcome: MISS, below the line.** Measured L2 gain is **−16 %**, against a predicted 30 % [18, 43].
  - Run 1 gave −16.4 %. A cleaning bug was then found from a figure, not from the result (see below). Run 2 gave −15.9 %.
  - The directional expectation (below the line) held. The size of the miss was not anticipated.
- **Cleaning fix between the runs.** The ramp rule detected only constant slope *per minute*. Interpolation in the received files is constant *per row*, and the interpolated values carry 4–16 decimals where genuine readings have ≤ 3.
  - The cleaner now drops both kinds (`clean_weija.py`, COMPUTED tier). Run 1 is archived in `run1_ramp_bug/`.
  - The corrected diel share is 0.43 rather than 0.39. Read off the same fitted line, that predicts about 33 %, so the miss is if anything larger.
- Full analysis: `WEIJA_REPORT.md`.
