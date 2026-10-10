# A2: design provenance table (review M8) and ablation findings

Every parameter is listed with its value, its source, the data used to choose it, and whether it was frozen before held-out results were seen.
- **"Test" sites:** the 6 USGS sites that are not tuning sites, plus InWaterSense (`sim.run_roc.split`).
- **Tuning sites:** every second USGS site in identifier order (7 sites).

| Parameter | Value | Source | Data used to choose it | Frozen before test results? |
|---|---|---|---|---|
| Train/test split | first 20% *by time* | design | none | yes (design). Training spans 46–73 days on USGS, 14 days at Wissahickon, 12.4 days at InWaterSense (A10) |
| Tuning/test site split | every 2nd USGS site in ID order | design rule | none | yes, written before any all-site result |
| Tolerances L0–L4 | T 0.05–1 °C, DO 0.5–10 %sat, pH 0.02–0.5, EC 0.5–10% of the training median | design: sensor resolution → coarse monitoring | none | yes, fixed in code before Phase 2. **L2 as the "headline" level: no record that it was declared before the results** (see the plan, decision B3) |
| SOD | no parameters | — | — | — |
| LMS | N = 4, μ = 1/(100 E_x) | Santini & Römer 2006 | none (paper default) | yes |
| DBP | m = max(4, 60 min/Δt), l = 3 | Raza et al. 2015, adapted to a 60-min learning window | none | yes |
| Ridge (ADAPTIVEML) | w = 24, λ = 1, frozen | Kangethe et al. 2026 | none | yes |
| RLS (ADAPTIVEML-RLS) | γ = 0.98, P₀ = 10·I | Kangethe et al. 2026 | none | yes |
| RLS-T | γ = 0.999 | ours | **one tuning site (Frenchtown, 01458500)**: 81.5 vs 11.1 reports/day at L2 | yes; the other 12 USGS sites are out of sample for it |
| Covariance trace bound (RLS, RLS-T, RLS-D) | tr P ≤ ρ·w (initial trace): 240 for ρ = 10; 0.24 for ρ = 0.01 | covariance bounding / anti-windup (Åström & Wittenmark 1995); the cap value is ours | none | yes |
| RLS-D: change model, w = 24, λ = 1, γ = 0.999 | inherited from Ridge / RLS-T | Phase-2 diagnosis (failure modes seen on all 14 datasets) | design motivated by Phase-2 diagnostics on **all** datasets | the *mechanism* was designed after seeing Phase-2 results on all sites. Its parameters below were tuned on tuning sites only |
| RLS-D: φ | 0.97 | written rule: minimise the median gap to min(SOD, RLS-T) over tuning sites × L1–L4 | 7 tuning sites, run with ρ = 10 | yes. **Re-applied at the final ρ = 0.01 (A2 rerun): the rule still picks 0.97** (−1.43% vs −1.20% for 0.9, −0.42% for 1.0, −0.01% for 0.8) |
| RLS-D: ρ (initial covariance) | 0.01 | development fix: ρ = 10 caused large-gain transients after heartbeat resyncs (it doubled reports at zero loss) | smoke tests of the loss protocol; datasets not recorded | **not chosen by a written rule.** Its effect on lossless report rates is negligible (A2: ρ = 10 vs 0.01 differ by ≤ 0.3 points at L1–L3 on test sites) |
| RLS-D: history repair | on | Phase-2 diagnosis | all datasets (diagnosis) | design |
| RIDGE-D | RLS-D with frozen weights | design (for unconfirmed uplinks) | none | yes |
| Detector (chosen) | lag 120 min, k = 3, H = 8, c = 6 | written rule: median FA ≤ 2/param/30 d on tuning sites, then maximum mean detection of 5σ injected events | 7 tuning sites (round 1 + round 2 grid) | yes; run once on the test sites |
| Detector (sensitive) | lag 120 min, k = 2, H = 4, c = 5 | a fixed point of the round-1 grid (cfg 4), picked as the high-sensitivity alternative after round 1 | round-1 ROC sweep | **not chosen by the written rule**; a sensitivity analysis. Its false-alarm rate (11.7/param/30 d on test sites, A5) must be reported wherever it is used |
| Heartbeat period | 6 h, 24 h | design | none | yes |
| Retries (confirmed) | 2 | design | none | yes |
| ADAPTIVEML α | {0.5, 1, 1.5, 2, 3} | sweep around the paper default 1 | none | yes |
| Energy parameters | see `src/energy/params.py` | Michelinakis 2021, Sørensen 2022, Casals 2017, Libelium datasheet | none | yes; t_sense swept |
| Injected events | 3/5/8σ, 1/3/6 h, steps and ramps | design (Check B's own threshold = 5σ) | none | yes |

## Ablation results (`a2_ablation_summary.csv`; gap to the per-site best of SOD and RLS-T, report mode, median)

| Variant | Test L1 | L2 | L3 | L4 | Tune L4 | InWaterSense L2/L3/L4 |
|---|---|---|---|---|---|---|
| SOD | +21.6 | +35.6 | +34.7 | +21.2 | 0.0 | 0 / 0 / 0 |
| RLS-T (level model) | 0 | 0 | 0 | 0 | +12.4 | +3.2 / +11.0 / +19.1 |
| CHG (change model only) | +0.5 | +1.8 | +0.7 | +6.3 | +21.3 | +2.1 / +7.8 / +15.9 |
| CHG + damping | +0.4 | +1.0 | +1.2 | +6.2 | +16.1 | +1.6 / +8.1 / +15.6 |
| CHG + repair | −0.1 | −0.3 | +1.8 | +3.5 | +16.2 | +2.8 / +8.1 / +15.7 |
| **RLS-D** (both) | −0.2 | −0.5 | +0.4 | +2.4 | +12.5 | +3.0 / +7.6 / +13.4 |
| RLS-D, ρ = 10 | −0.3 | −0.4 | +0.1 | +2.2 | +9.8 | +2.6 / +8.9 / +15.9 |

**Honest reading:**
1. **Most of RLS-D's gain over SOD comes from the shrunk change model itself** (CHG is within 0.5–6% of the per-site best on test sites, while SOD is 21–36% behind).
2. **Damping and repair matter mainly at L4.** On test sites they reduce the gap from 6.3% to 2.4%; on tuning sites, from 21.3% to 12.5%. At L1–L3 their effects are within the site-to-site uncertainty (n = 6; CIs overlap).
3. **The draft shows the RLS-D gap only for test sites.** On tuning sites at L4, RLS-D is 12.5% behind the per-site best (SOD), exactly as RLS-T is. At the loosest tolerance, "degrades gracefully to SOD" is only partly true. Report it.
4. **On InWaterSense,** RLS-D reduces RLS-T's penalty (19.1% → 13.4% at L4) but does not remove it.

## Complexity and memory (M7). These are counts, not measurements; no hardware is available (decision D3).

Per parameter, with w = 24:

| | Prediction (every step) | RLS update (reported steps only) | State |
|---|---|---|---|
| **RLS-D** | form the 24 changes (24 subtractions), β·z (24 MAC), φ^k scaling: **~50 flops** | Pz (576 MAC), gain (~50), β (24), P update (576), trace bound (24): **~1,250 flops** | P (576 floats) + β (24) + history (25) + scalars ≈ **626 floats ≈ 2.5 KB (float32)** |
| RIDGE-D / RLS-D with frozen weights | same | none | β + history ≈ **49 floats ≈ 200 B** |
| SOD | none | none | 1 value |

**Platform check (verify the SRAM figure in the datasheet before writing):** the Libelium Waspmote is built on an ATmega1281, which has **8 KB SRAM**.
- RLS-D for 4 parameters needs about **10 KB** (P matrices about 9.2 KB). It does **not fit** on the platform our field data comes from.
- RIDGE-D (about 0.8 KB for 4 parameters) fits.
- RLS-D fits on Cortex-M-class LPWAN hosts with 20–256 KB RAM (e.g. STM32L0, nRF9160). Name these only if a datasheet is checked.

**Time, rough estimate:** software floating point on an 8-bit AVR costs about 100–150 cycles per flop. 1,250 flops is about 0.2 M cycles, i.e. about 13 ms at 14.7 MHz per parameter per reported step. That is about 1 mJ at 69 mW, negligible next to a 0.1–1.3 J report. Label it as an estimate.

**Paper wording:**
- RLS-D needs about 2.5 KB per parameter (float32), or about 10 KB for four parameters, beyond the 8 KB SRAM of the Waspmote's ATmega1281.
- Frozen-weight RIDGE-D needs about 0.2 KB per parameter.
- So RIDGE-D is the variant for 8-bit hosts, and RLS-D targets 32-bit LPWAN hosts.
- The ablation and RIDGE-D results quantify what is lost (RIDGE-D vs RLS-D: up to +13% on InWaterSense, −9 to +4% elsewhere; v0.1 results).
