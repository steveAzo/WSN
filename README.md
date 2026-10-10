# When Does Prediction Pay in LPWAN Water-Quality Monitoring? Code and results

Code, configuration and result files for the paper *"When Does Prediction Pay in LPWAN Water-Quality Monitoring? Multi-Site Error-Bounded Report Suppression"* by K. S. Adu-Manu and S. K. Azongo, University of Ghana.

The repository contains:
- a trace-driven simulator of error-bounded dual-prediction schemes (DPS) for multi-parameter water-quality nodes;
- all baselines, including send-on-delta, LMS, DBP, the ADAPTIVEML predictors, periodic reporting and batching;
- the proposed RLS-D predictor, the node-side CUSUM event detector, and the two loss-recovery protocols;
- the NB-IoT/LoRaWAN energy model;
- the scripts that regenerate every number, table and figure.

## Layout

| Path | Contents |
|---|---|
| `src/data/` | Download (USGS) and cleaning scripts for every dataset |
| `src/sim/` | Simulator: `engine.py` (accounting modes, loss protocols), `predictors.py`, `detector.py`, `inject.py`, and the experiment runners `run_*.py` |
| `src/energy/` | Energy model; every parameter with its source in `params.py` |
| `src/analysis/` | Statistics, tables and figures (`phase*_analysis.py`, `revision_*.py`) |
| `tests/` | Unit tests of the simulator's correctness properties (106 tests) |
| `data/` | Downloaded and cleaned USGS data (2023) and cleaned InWaterSense cycles |
| `INWS/` | The published InWaterSense dataset (Ahmedi, Mendeley Data, doi:10.17632/krzv3g6d5f.1, CC BY 4.0) |
| `results/` | Result files of every run (`phase1`–`phase4`, `weija`, `revision`) |

**Weija data.** The Weija deployment data belong to the deployment team and are not included. The results derived from them are included, in `results/weija/`.

## Environment

The code was run with Python 3.13 on Windows; it uses only the standard library plus the packages below.

```
pip install -r requirements.txt
python -m pytest tests -q        # 106 tests
```

On a machine with little memory, run the experiments with one worker (`--jobs 1`, or a final argument of `1`).

## Reproducing the results

Run from the repository root, in this order. Approximate run times are for a laptop with one worker.

1. **Data.**
   - Download the USGS data: `bash src/data/fetch_all_usgs.sh`.
   - Clean it: `python src/data/clean_usgs.py`.
   - Clean InWaterSense: `python src/data/clean_inws.py` (reads `INWS/`).
   - USGS may revise approved data over time. The exact files used in the paper are in `data/`.
2. **Predictability (Phase 1).**
   - Scripts: `src/analysis/check_a.py`, `check_b.py`, `summarize_check_a.py`, `seasonal.py`.
   - Their arguments are documented at the top of each script.
3. **Baselines (Phase 2, about 1 h).**
   - `python src/sim/run_phase2.py --jobs 1`
   - `python src/analysis/phase2_analysis.py`
4. **Proposed scheme (Phase 3, a few hours in total).**
   - `python src/sim/run_rlsd.py 1`
   - `python src/sim/run_roc.py --jobs 1`
   - `python src/sim/run_phase3.py --jobs 1`
   - `python src/sim/run_loss.py --jobs 1`
   - `python src/analysis/phase3_analysis.py`
5. **Energy (Phase 4).**
   - `python src/energy/run_phase4.py`
   - `python src/analysis/phase4_analysis.py`
6. **Revision analyses.**
   - Runs: `python src/sim/run_ablation.py 1` (about 1 h) and `python src/sim/run_loss_ack.py 1` (about 1 h).
   - Then, in this order:
     - `src/analysis/revision_stats.py`
     - `revision_frontiers.py`
     - `revision_events.py`
     - `revision_energy.py`
     - `revision_diel.py`
     - `revision_smoothness.py`
     - `revision_ablation.py`
     - `revision_dataflow.py`
     - `revision_supplement.py`
     - `revision_figures.py`
   - Finally: `python src/analysis/paper_numbers.py`.

Every runner is resumable and writes its results to `results/`. Random seeds are fixed in the scripts: loss seeds 0–2; bootstrap and permutation seed 20261010.

## Citing

See `CITATION.cff`. Please cite the archived release DOI shown on the Zenodo record.

## Data sources

- **USGS National Water Information System,** instantaneous values, 2023 (public domain).
- **InWaterSense:** Ahmedi, L., Mendeley Data V1, doi:10.17632/krzv3g6d5f.1. Dataset description: Ahmedi & Ahmedi, *Data in Brief* 44 (2022).
