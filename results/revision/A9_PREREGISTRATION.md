# A9 pre-registration: a diel-smoothness statistic (written 2026-10-10, BEFORE computing it)

**Context.** Review comment M18 suggests a two-dimensional deployment diagnostic: diel strength plus smoothness. It asks us to test a smoothness statistic "if it can be done without post-hoc overfitting; otherwise present it as a hypothesis". Weija is the only dataset with a high diel share where prediction failed. Any test therefore has a single positive case and is **exploratory by construction**. This file fixes the statistic and the predictions before any value is computed.

## Statistic (fixed now)

For a series x, in local standard time:
1. Compute the within-day anomaly: a_t = x_t − (mean of x_t on that calendar day). This is the same anomaly as for diel share.
2. Compute the hour-of-day profile p[h], h = 0..23, as the mean of a_t in each clock hour.
3. Compute the **roughness** R = mean_h (p[h+1] − p[h])² / Var(p), with h taken cyclically (23 → 0).
4. Normalise: R_norm = R / R_sine, where R_sine = 2(1 − cos(2π/24)) ≈ 0.0681 is the value for a pure 24-h sinusoid. A smooth sinusoidal cycle gives R_norm ≈ 1. Sharp, spike-shaped cycles give R_norm ≫ 1.

R_norm is computed for temperature (T), the parameter that carries the Weija diel signal. It is computed on the whole series, with the same data as diel share. For Weija the T+EC cleaned series is used, as in Phase 1 of the Weija report.

## Predictions (fixed now)

- **P1.** Weija's T roughness R_norm is the largest of the 15 datasets (13 USGS, InWaterSense, Weija).
- **P2 (exploratory, no inference).** The combined score S = diel share / R_norm (site mean of diel share; T roughness) ranks the RLS-T saving at L2 across the 15 datasets at least as well as diel share alone (Spearman ρ). With one failing case this cannot be a confirmatory test, and it will be reported as an exploratory description only.
- **If P1 fails,** the spike hypothesis is weakened, and the paper says so.

## How it will be reported

As a boundary-condition hypothesis with a one-case test, never as a validated diagnostic. A new deployment-time test (a further held-out site) is future work.
