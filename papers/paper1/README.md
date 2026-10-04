# Paper 1 reading list

Per-paper summaries, weaknesses and the gap analysis are in **[LITERATURE_NOTES.md](LITERATURE_NOTES.md)**. Extracted text for every PDF is in `txt/`, so you can search it.

## Must read in full (in this order)

| # | Paper | What to look for |
|---|---|---|
| 01 | Adu-Manu et al. 2017, ACM TOSN (Prof's survey) | §5.2–5.4 and §7. The open problems we answer (§7.1, 7.2, 7.4) |
| 16 | Ahmedi & Ahmedi 2022, Data in Brief (the dataset paper) | Node placement, how the data was sent, missing values |
| 04 | Dias, Bellalta, Oechsner 2016, ACM Computing Surveys | DPS taxonomy (§3–4); open issues (§6–7) |
| 05 | Raza et al. 2015, IEEE TKDE (DBP) | The DBP algorithm (§3); why 99% suppression gave only 3–7× lifetime (§5) |
| **17** | **Kangethe et al. 2026, arXiv (ADAPTIVEML)** | **Our main competitor.** Eq. 5, Table IV, and its future-work list |
| 06 | Carvalho et al. 2011, Sensors | How their "multivariate" differs from ours (batch coefficients, no error bound) |
| 12 | Rao et al. 2019, Sensors | Adaptive tolerance (§3.2), critical zones (§3.3), sync overhead (§4.2) |
| 20 | Ahmedi & Makolli 2023, JWLD | Correlations on our dataset (Table 1). Are they seasonal or short-term? |
| 22 | Adu-Manu et al. 2020, WCMC (the Prof's Weija deployment) | Same Libelium hardware; fixed 30/60-min reporting to save energy; data-quality problems |
| 24 | Santini & Römer 2006, INSS | The original LMS DPS; sync rules; §V open issues (loss, heartbeat, *block/joint* prediction) |
| 23 | Ghosh et al. 2022, IEEE TGCN | Multi-parameter hub; wake-up energy E_w ≫ E_t; batching vs fixed 'bad' limits |

## Skim (methods and results)

| # | Paper | Why |
|---|---|---|
| 21 | Macêdo et al. 2025, Earth | Another prior use of our dataset; which DO data they discarded and why |
| 14 | Shu et al. 2017, Sensors | Water-quality adaptive sampling; missed DO peaks (Fig. 5) |
| 15 | Lu et al. 2026, arXiv | GLR/MAD event detector; injected-event evaluation; EDR/ODD metrics |
| 07 | Morales et al. 2021, Sensors | Deep learning in DPS; thresholds too loose for us |
| 13 | Płaczek 2023, Sensors | Interval prediction; pointer to Almalki 2021 (critical limits) |
| 08 | Maurya et al. 2025, Sci. Reports | Correlation-based predictor selection; pointer to Ghosh et al. 2022 |
| 18 | Kreković et al. 2025, arXiv | Recent univariate DPS; confirms multivariate is still open |
| 19 | Dias et al. 2017, Computer Communications | Theory of DPS gains |

## Reference material (use the tables when building the energy model)

| # | Paper | Use |
|---|---|---|
| 10 | Sørensen et al. 2021 (NB-IoT/LTE-M model) | Table X power values; eqs. 30–32 |
| 11 | Michelinakis et al. 2021, IEEE IoT J (NB-IoT measurements) | Table VIII per-report energy; Table X lifetimes; packet loss |
| 09 | Casals et al. 2017, Sensors (LoRaWAN) | Table 5 state currents; lifetime results (§5.2) |

## Get these yourself (requested via the Prof; 22, 23, 24 obtained 2026-10-03)

**Via UG library (IEEE Xplore / SpringerLink), or email the authors:**
- **Liazid, Lehsaini, Liazid (2019)**, *An improved adaptive dual prediction scheme…*, Wireless Networks 25:3545. https://doi.org/10.1007/s11276-019-01950-7
- **Shu, Chen, Bhargava, de Silva (2019)**, *An energy-efficient dual prediction scheme using LMS filter and LSTM in WSNs for environment monitoring*, IEEE IoT J 6(4):6736. https://doi.org/10.1109/JIOT.2019.2911295 *(authors verified via OpenAlex; an earlier version of this list wrongly said "Wu et al.")*
- Wu, Chen, Chen, Fan, Liu (2020), *An adaptive dual prediction scheme based on edge intelligence*, IEEE IoT J 7(10):9481. https://doi.org/10.1109/JIOT.2020.2997795
- Jarwan, Sabbah, Ibnkahla (2019), *Data transmission reduction schemes in WSNs for efficient IoT systems*, IEEE JSAC 37(6):1307.
- Almalki et al. (2021), *EERP-DPM: energy efficient routing protocol using dual prediction model for healthcare using IoT*, J. Healthcare Eng.
- Ahmedi et al. (2018), *InWaterSense: An intelligent WSN for monitoring surface water quality to a river in Kosovo*, IJAEIS 9(1). The system paper.

## Notes

- The two background papers named in the original proposal document ("Energy-Efficient Data Gathering in WSNs Using Edge-Based Prediction Approaches" and "Adaptive Sampling and Data Compression Strategies for Long-Term Environmental Monitoring") could not be found. Do not cite them.
- Always cite from the actual PDF. Paper 17 mis-attributes paper 07's authors, and this list itself once had a wrong author name (fixed above).
