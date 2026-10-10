# Paper 1: Literature notes

*Compiled 2026-09-30 after a full read of papers 01, 04–08, 12–18, 20, 21 and the relevant sections of 09–11, 19. Extracted text for every PDF is in `txt/` so you can search it.*

**How to use this file:** each card says what the paper did, on what data, what it found, what it did *not* do, and why it matters to us. The gap analysis at the bottom is the basis of our related-work section and our novelty claim.

---

## A. Our context

### 01: Adu-Manu, Tapparello, Heinzelman, Katsriku, Abdulai (2017). *Water Quality Monitoring Using WSNs: Current Trends and Future Research Directions.* ACM TOSN 13(1).
- **What:** survey of WSN-based water-quality monitoring: sensors, architectures (sensor → local station via ZigBee → remote via GPRS/3G), energy management, data processing, open issues.
- **Key facts:** GPRS/ZigBee is the dominant architecture (Table VI/VIII); DO safe range quoted as **5–6 mg/L** (Table I).
- **Open issues it names that we answer:**
  - §7.2: "when gathering correlated data, as is the case for WSN-based WQM systems, a **joint data acquisition, compression and transmission scheme** can greatly improve the performance" [Pattem et al. 2008].
  - §7.4: "a **complete energy evaluation model** is required".
  - §7.1: prediction tools plus "detection algorithms of **contamination events**" that trigger alarms in real time.
  - §7.6: sensor drift must be considered in data processing.
- **Use:** motivation and framing. This is the Prof's own call for exactly this kind of work.

### 16: Ahmedi & Ahmedi (2022). *Dataset on water quality monitoring from a WSN in a river in Kosovo.* Data in Brief 44.
- **Deployment:** Libelium Waspmote Plug & Sense.
  - **Node 1:** "on the discharge point source to which the discharge tube is extended… from within the housing".
  - **Node 2:** ~100 m downstream, in a manhole.
  - **Links:** ZigBee *and cables* to one gateway (in the manhole) → GPRS → MS SQL server.
- **Data:** 105,652 raw records (199 duplicates removed). Node 1 has 78,378 (74%), node 2 has 27,075. The grouped file has 29,842 rows.
- **Missing values:** 4,642 rows (18.4%) have nulls, **only for node 1, mostly in winter**. Cause: the 4 parameters of one sample arrive with **different timestamps, seconds apart** (Table 8). Rounding to the minute re-joins them. So each parameter was effectively sent as its own message.
- **Outliers:** Table 5, e.g. pH −28 to 94.58.
- **Units:** DO units are **not stated**.
- **Use:** ground truth for our dataset description. The "separate message per parameter" detail supports our report-level argument (§D).

### 20: Ahmedi & Makolli (2023). *The correlation of WQ parameters over wireless sensors generated dataset in the Sitnica River.* J. Water & Land Dev. 59.
- **What:** linear regression between parameter pairs in WEKA, on **node 1 only** (23,073 samples per parameter; 18,500 after removing out-of-range and missing values).
- **Results:**

  | Pair | r |
  |---|---|
  | DO–T | **−0.80** (DO = −5.09·T + 105.5) |
  | EC–T | **+0.72** |
  | EC–DO | −0.49 |
  | DO–pH | 0.31 |
  | pH–T | ≈ 0 |

  DO is labelled mg·dm⁻³.
- **Caveats (important for us):**
  1. These are correlations of **levels across 8 months**, which are largely driven by the seasons (summer → winter). DPS needs **short-term co-movement** (correlation of *changes*), and that may be much weaker. **We must test this first.**
  2. The fitted line gives DO ≈ 105 at 0 °C. A slope of −5 per °C is ~25× the physical rate for mg/L (≈ −0.2 mg/L per °C), so the DO values are unlikely to be mg/L. Question for the Prof.
- **Use:** evidence that a cross-parameter premise is *plausible* on this exact dataset. Cite as prior use of the dataset.

### 21: Macêdo et al. (2025). *Evolutionary-Assisted Data-Driven Approach for DO Modeling: A Case Study in Kosovo.* Earth 6(3):81.
- **What:** predicts DO from T, EC and pH with Elastic Net, SVR and LightGBM, tuned by a genetic algorithm. LightGBM reaches R² = 0.944.
- **Data handling:** kept only the **first 18,360 samples**. The later DO series was discarded as "sensor drift or interference". Reports DO range 3.7–149.2 "mg/L" (physically implausible as mg/L; the paper does not question it).
- **Limitations:** random 70/30 split on a time series leaks information (optimistic R²). No communication aspect.
- **Use:**
  - A second prior use of the dataset.
  - Supports the idea that DO is predictable from the other parameters.
  - Warns us that **late-2015 DO is unreliable**. Our evaluation window must handle this.

---

## B. Prediction-based data reduction: the core literature

### 04: Dias, Bellalta, Oechsner (2016). *A Survey about Prediction-Based Data Reduction in WSNs.* ACM Computing Surveys 49(3).
- **Taxonomy:** Single Prediction Schemes vs **Dual Prediction Schemes (DPS)**. In a DPS the model can be generated at the cluster head, generated independently after an initialisation phase (Santini & Römer 2006), or generated at the node.
- **Predictors covered:** constant, AR, MA, ES, ARIMA, linear/kernel regression, PCA, GP, ANN, with their complexity (Tables I–II).
- **Key observations:**
  - **Most works reuse the same dataset, Intel Berkeley Lab (Madden 2004).**
  - Model choice is often ad hoc.
  - The cost of computing and re-transmitting models is rarely counted.
  - Under channel errors, "absence of updates… is usually treated as a signal of predictions' high accuracy", so **beacons or heartbeats are needed**.
  - Aderohunmu 2013 found the *constant* predictor gave the best accuracy–energy trade-off.
  - Goel & Imielinski: prediction only pays off below about 15,000 instructions per prediction.
- **Open issues:** a statistically grounded way to evaluate prediction efficiency (communication, computation, where to predict), heterogeneous devices, and long-term prediction.
- **Use:** related-work backbone. We use its terminology (DPS, independent model generation).

### 05: Raza, Camerra, Murphy, Palpanas, Picco (2015). *Practical Data Prediction for Real-World WSNs* (DBP). IEEE TKDE 27(8).
- **Method: Derivative-Based Prediction.** The slope between averages of the *l* edge points of a learning window of *m* samples. Very cheap: 50 lines of TinyOS, 108 B RAM, no floating point.
- **Tolerances:** value tolerance εV = max(ε_rel·|V|, ε_abs) and **time tolerance εT** (the number of consecutive out-of-bound readings allowed before a new model is sent).
- **Data:** 7 datasets. Includes SOIL at 10-min sampling (m = 6) and WATER (chlorine, *simulated* EPANET).
- **Results:** suppression 90–99.7%. DBP is best or second-best everywhere.
- **Crucial system result:** 99% suppression gave only **3–5× lifetime** in a real testbed, 7× after MAC/routing tuning, because **network control overhead dominates** once data traffic is small. Also, **losing a single model message causes large errors**, so reliability mechanisms are needed.
- **Use:**
  - **The baseline to beat.**
  - Our tolerance definitions (εV, εT) come from here.
  - Its lesson becomes our argument: *count the fixed per-report and per-connection overhead*. For cellular IoT that means attach/sync, RRC and TAU, not MAC beacons.

### 06: Carvalho, Gomes, Agoulmine, de Souza (2011). *Improving Prediction Accuracy for WSN Data Reduction by Applying Multivariate Spatio-Temporal Correlation.* Sensors 11.
- **Method:** each node fits **multiple linear regression** (predict humidity and light from temperature and time) over a window of 6–10 samples. It sends the regression coefficients plus the raw temperature samples to the sink. Neighbours with near-identical coefficients (Euclidean distance) send a short "correlated" packet instead.
- **Data and setup:** Intel Lab (T, H, light); TOSSIM simulation.
- **Results:** multivariate regression gives the best SSerr/R². It costs about 2× the energy of the time-only regression, but still saves ~86% vs sending raw data.
- **Not done:**
  - **Not a DPS.** It is batch/window model reporting with **no per-sample error bound**.
  - Only indoor lab data.
  - Energy model is per byte (µJ/byte).
  - Coefficient computation cost is not counted (noted by Dias).
- **Use:** closest *multivariate* prior work. Our distinction: bounded-error, sample-by-sample dual prediction with cross-parameter predictors.

### 07: Morales, Rangel de Sousa, Brusamarello, Fernandes (2021). *Evaluation of Deep Learning Methods in a DPS to Reduce Transmission Data in a WSN.* Sensors 21:7375.
- **Method:** LSTM, GRU, CNN, DNN, Seq2Seq and Seq2Seq+Attention, trained on 3 series from one node at a hydroelectric plant (80 days, 5-min sampling). Multi-output forecasting, 12 steps ahead.
- **Results:** Attention model is best. At a threshold of **1.5 °C → ~60–65% fewer transmissions; 3 °C → ~80%**. The threshold is applied to temperature only.
- **Not done:** no comparison with simple baselines (naive, DBP); no hardware; no energy model. The thresholds are very loose for water quality.
- **Use:** shows deep learning is not obviously worth it, and that multivariate *outputs* alone do not give a multi-parameter guarantee. (Note: paper 17 cites this paper with the **wrong authors**, a reminder to verify every citation.)

### 12: Rao, Zhao, Wang, Zhang, Jiang, Wang (2019). *Adaptive Data Acquisition with Energy Efficiency and Critical-Sensing Guarantee.* Sensors 19:2654.
- **Method:**
  - **Switching:** compressed sensing (sparse sampling) when data is in the *non-critical* zone; DPS when data is in the *critical* zone. Zones are defined by **fixed application thresholds**, e.g. air humidity 60–80%.
  - **Adaptive deviation tolerance:** computed **once per day** from the previous day's 24 segments using a Student-t prediction interval. It **grows with variability**.
- **Data:** greenhouse air humidity and soil moisture, 5-min, 14 days.
- **Key results:**
  - **Model-synchronisation overhead cut DBP's compression ratio by 54% (air) and 17% (soil)**, and made SVR's net compression negative.
  - DBP is preferable because it has low sync overhead.
- **Not done:** energy only via compression ratio; univariate; events are fixed-threshold only.
- **Use:**
  - Count the synchronisation overhead.
  - The "critical-sensing guarantee" concept exists, but only with **fixed limits**.
  - Their tolerance loosens in noisy periods.

### 13: Płaczek (2023). *A Multi-Agent Prediction Method for Data Sampling and Transmission Reduction in IoT Sensor Networks.* Sensors 23:8478.
- **Method:** the gateway predicts **intervals** of future readings (multi-agent search over history) and schedules the next sample for when the value *could* first cross an application level. This is single-prediction, gateway-side.
- **Data and result:** smartphone RSSI data; 95% transmission reduction.
- **Not done:** univariate (multivariate is future work); RSSI, not environmental data.
- **Use:** its related work points to **Almalki et al. 2021 (healthcare DPS that always reports values outside fixed critical limits)**. So "always send out-of-limit values" is **not new**.

### 14: Shu, Xia, Chen, de Silva (2017). *An Energy Efficient Adaptive Sampling Algorithm in a Sensor Network for Automated Water Quality Monitoring.* Sensors 17:2551.
- **Method:** DDASA changes the *sampling* frequency using a sigmoid of the relative change.
- **Data:** NOAA buoy, hourly DO and turbidity, 3 months.
- **Results:** ~31% battery energy saved vs fixed-rate sampling; 5% more saved than a classic adaptive sampling algorithm.
- **Not done:** no transmission-suppression DPS; normalized mean error only (no hard bound). **At larger thresholds it misses important DO peaks** (their Fig. 5).
- **Use:** the closest water-quality energy paper. Its missed peaks motivate our event-preserving requirement.

### 15: Lu, Sun, Jiang, Butler (2026). *Adaptive Sampling for Spatiotemporal Anomaly Monitoring in WSNs.* arXiv 2607.15235.
- **Method:**
  - **Normal periods:** Kalman-filter uncertainty-driven sparse sampling.
  - **Anomalies:** "sentinel" nodes run a two-sided **GLR detector on normalized innovations** with **median/MAD node-relative thresholds**, and wake neighbours.
- **Data:** Intel Lab with *injected* anomalies.
- **Metrics:** event detection rate (EDR), onset detection delay (ODD), anomaly-window sampling ratio.
- **Use:**
  - The robust GLR/MAD detector is a good tool for telling **events from noise**.
  - The *injected-event* evaluation method and EDR/ODD metrics are worth adopting.
  - Sampling-oriented, not DPS.

### 17: Kangethe, Uddin, Wang (2026). *Learning to Transmit: Volatility-Aware Predictive Communication for Energy-Efficient IoT Networks* (ADAPTIVEML). arXiv 2607.19590. ⚠️ **Most important competitor.**
- **Method:**
  - Ridge regression on the last 24 values (ADAPTIVEML-RLS adds online RLS with forgetting).
  - **Transmit iff |x − x̂| > α·σ(t)**, where σ(t) is the *rolling standard deviation of the signal* over 24 samples.
  - Dual-prediction reconstruction at the sink.
- **Data:** Chicago beach weather (hourly air temperature), Intel Lab, UCI Air Quality (CO).
- **Baselines:** periodic, static threshold, ARIMA, Kalman, EMA, LMS.
- **Results:** 94.7% fewer transmissions, MAE 0.35 °C. RLS improves MAE by 12–18% under drift.
- **Energy:** a flat **59 µJ per packet** (nRF52840).
- **Weaknesses / what they did not do:**
  1. **No hard error bound.** The threshold *grows* when the signal is volatile, so reconstruction error is largest exactly during events. They report MAE, not maximum error or event capture. For water-quality alarms this is the wrong direction.
  2. **Univariate.** "Multi-channel Ridge for correlated sensor arrays" is listed as **their future work**.
  3. **Energy model ignores per-connection overhead.** µJ per packet is fine for BLE but not for NB-IoT/LoRaWAN, where each report costs ~0.1–4 J. "Hardware energy measurement" is future work.
  4. **No resynchronisation under packet loss.** Listed as future work. They claim loss *increases* suppression, which hides model divergence.
  5. No water data; unreviewed preprint with citation errors (e.g., mis-cites paper 07's authors).
- **Use:** we **must cite and beat or differentiate from it**. It removes "volatility-adaptive threshold" as a novelty claim. Its future-work list overlaps ours, so we should **move steadily**.

### 18: Kreković, Kušek, Podnar Žarko, Le-Phuoc (2025). *Edge-Based Predictive Data Reduction for Smart Agriculture.* arXiv 2511.19103.
- **Method:** univariate LSTM, one step ahead, **fixed** threshold (0.5 or 1.0 °C).
- **Data:** air temperature at Croatian stations (10-min), plus satellite pre-training for cross-site transfer.
- **Results:** 77–88% reduction at 0.5 °C; 94–98% at 1.0 °C.
- **Not done:** univariate and fixed threshold (both are future work); no energy model.
- **Use:** confirms the direction is active (2025–26), and that multivariate plus adaptive is still open.

### 19: Dias, Bellalta, Oechsner (2017). *The Impact of DPS on the Reduction of the Number of Transmissions in Sensor Networks.* Computer Communications 112. (arXiv 1509.08778)
- **What:** analytical model of DPS plus aggregation gains in multi-hop WSNs. Up to ~98% fewer transmissions at the busiest nodes. Prediction accuracy and inter-sensor correlation drive the gains.
- **Use:** theory citation for DPS gains; it is for multi-hop mesh networks, not cellular.

### 08: Maurya, Kumar, Raj, Gupta (2025). *Energy consumption minimisation at edge node using CcBPS…* Scientific Reports 15:37422.
- **Different paradigm: sensor selection.** Some sensors sleep, and the edge node predicts them with Gaussian-process regression from the correlated active sensors. CcBPS picks the predictor subset by cross-correlation (≥ 0.9 or ≥ the mean correlation).
- **Data and result:** Indian air-quality datasets; 6.5–34% less *edge* computation energy.
- **Not done:** no error bound; the energy model is an assumed 1 mJ per time unit; no radio energy.
- **Use:** supports cross-parameter prediction and correlation-based predictor selection. Its references point to **Ghosh, De, Chatterjee, Portmann (IEEE TGCN 2022), "Edge intelligence framework for data-driven dynamic priority sensing and transmission"** (LSTM + RL for a *multi-parameter sensor hub*). **Get this from the library**; it is the nearest multi-parameter energy paper.

### 24: Santini & Römer (2006). *An Adaptive Strategy for Quality-Based Data Reduction in WSNs.* INSS. (Added 2026-10-03)
- **What:** the original LMS-based DPS with **independent model generation**: identical filters at node and sink, w[0] = 0, no prior model.
  - **Modes:** initialisation → normal → stand-alone.
  - **Sync rule:** in stand-alone mode the node feeds its *prediction* (not the reading) back into its history, so node and sink stay identical.
- **Data and results:** Intel Lab temperature; ~90% fewer transmissions at e_max = 0.5 °C with N = 4–10 taps (≈ 17 operations per step).
- **Open issues it already names:**
  1. **Message loss** desynchronises the filters. Sequence numbers plus forced re-initialisation are proposed but "not satisfactory"; an equivalent tighter budget e_eq = f(p, e_max) is suggested.
  2. **Node failure.** Force a report "at least once every K instants" (a heartbeat).
  3. **Joint/block prediction.** A multiple-error (block) LMS over a block of readings, reporting "only if the joint prediction error will exceed the given threshold". Proposed for *neighbouring nodes* at a cluster head; not implemented.
- **Use:** baseline (LMS DPS) and origin of our sync rules. **Its block idea is the earliest form of a joint (report-level) decision. We must cite it.** Our difference: per-parameter hard bounds inside a multi-parameter report, cross-parameter predictors, and the per-report energy argument for LPWAN.

### 23: Ghosh, De, Chatterjee, Portmann (2022). *Edge Intelligence Framework for Data-Driven Dynamic Priority Sensing and Transmission.* IEEE TGCN 6(1). (Added 2026-10-03)
- **What:** a multi-parameter sensor hub (6 air-pollution gases). The edge node chooses an **active sensor subset**, sampling instants and **measurement-cycle length**:
  - discounted-UCB reinforcement learning;
  - GPR temporal models (shared by node and edge) and GPR cross-parameter models (edge only).
- **Two-state operation:**
  - **"Good" state:** samples are **buffered and sent at the end of the cycle**.
  - **"Bad" state:** any parameter exceeds a **fixed** threshold, and data is sent immediately.
- **Key idea relevant to us:** communication energy E_c = E_w (wake-up, fixed, ≫) + E_t per sample, so fewer radio activations save energy.
- **Results:** up to 41% sensing energy and 32% bandwidth saved vs prior multi-sensing; 98% "bad-state" detection; reconstruction nMSE ~7×10⁻⁴.
- **Not done:**
  - Batching adds **latency up to the cycle length** (21 s–1 h) in the good state.
  - "Bad" is defined by fixed limits; there is no per-sample error bound.
  - Sensing energy dominates in their setup (264 J sensing vs 0.0055 J communication), with no cellular/LPWAN radio model.
  - Air-quality data only.
- **Use:** the nearest *multi-parameter, wake-up-aware* prior work. Cite it for the "fixed wake-up cost" argument. Our difference: real-time bounded-error suppression with no batching delay, an event detector instead of fixed limits, and LPWAN per-report energy where communication dominates.

### 26: Wu, Chen, Chen, Fan, Liu (2020). *An Adaptive Dual Prediction Scheme Based on Edge Intelligence* (ARUCP). IEEE IoT J 7(10):9481–9493. (Added 2026-10-10, full read)
- **Setting:** IoT *search*. The cloud predicts each sensor's current output so that search queries need not poll the sensors. Not a monitoring/telemetry paper.
- **Method:**
  - **Cycle-level transfer decision at the node.** The node buffers the m samples of a reporting cycle and compares them with the predicted sequence using a compressed LCSS similarity (CLCSS, eqs. 1–3). It reports the **whole cycle** only if the dissimilarity Val_T exceeds a threshold θ. **θ is left unspecified** ("beyond the scope").
  - **Cloud side:** an ELM predictor updated online (AOUM-OSELM, where the update weight grows with Val_T) and a DBSCAN pattern monitor (AWPC) that rebuilds the model on a new pattern. The new weights are sent back down to the node.
- **Data:** UCI hydraulic test rig (Helwig 2015). TS1–TS4 and PS1–PS6, 60-s cycles, 2,205 cycles; trained on the first 400, tested on 1,500.
- **Results:**
  - 332 reports in 1,500 cycles (−77.9%) at about 4 points lower R² than reporting every cycle.
  - 76.56% communication energy saved at 95.47% "accuracy" (mean windowed R²).
  - Energy uses the first-order radio model (Heinzelman 2002), per bit.
- **Not done:**
  - **No per-sample error bound.** The decision is a sequence similarity, and LCSS deliberately ignores outlying points, so short excursions can be absorbed as "noise".
  - Single-parameter models (one per sensor).
  - Batching delay of one reporting cycle.
  - No packet loss; no water data; no comparison with a constant/SOD predictor.
- **Use:**
  - A **third ancestor of the "joint/block decision"**, alongside Santini 2006 and Ghosh 2022. It is a *temporal* block (one sensor, many samples), not a cross-parameter one.
  - Cite in "Multi-parameter and joint decisions". Strengthens "the report-level decision is not new in itself; our difference is per-parameter hard bounds and immediate reporting".

### 27: Almalki, Ben Othman, Almalki, Sakli (2021). *EERP-DPM: Energy Efficient Routing Protocol Using Dual Prediction Model for Healthcare Using IoT.* J. Healthcare Eng. 2021:9988038. (Added 2026-10-10, full read)
- **What:** a WBAN routing protocol.
  - The DPS part is the Santini/Jarwan scheme: a buffer of N values; report if |P_n − NDV_n| > e_max, otherwise feed the prediction back. **The predictor itself is never specified.**
  - Readings beyond fixed upper/lower limits (example: BP > 180/120 mmHg) are "emergency data": high priority, sent **directly** to the aggregator. Normal data goes via relay nodes.
  - The aggregator packs all sensors' forwarded data of a round into one message.
- **Evaluation:** MATLAB (first-order radio model, 0.5 J nodes, 15,000 rounds) plus the MySignals HW V2 platform. Compared with E-HARP and PCRP on lifetime, residual energy, throughput, path loss and delay.
  - **No transmission-reduction rate and no reconstruction error are reported.**
- **⚠ Important for our citation.** The paper is internally inconsistent about critical values:
  - Its prose (§3.2.2) says data is sent "if it is different from the data predicted, **or** data is considered critical".
  - Its **Algorithm 1** checks criticality **only inside the e_max-violation branch**. There, the limit changes the *routing*, not whether a report is sent.
  - Płaczek 2023 (paper 13) repeats the prose version.
  - So cite it as *"flag readings beyond fixed upper/lower limits as emergency data and route them directly with priority"*, **not** as "always report values outside the limits".
- **Use:** the primary source for the "fixed critical limits in DPS" sentence (replace the secondary citation via Płaczek).

### 28: Shu, Chen, Bhargava, de Silva (2019). *An Energy-Efficient DPS Using LMS Filter and LSTM in WSNs for Environment Monitoring.* IEEE IoT J 6(4):6736–6747. (Added 2026-10-10, full read)
- **Method:**
  - **GD-LMS:** the step size is chosen per step using the Moore–Penrose pseudo-inverse (eqs. 9–15).
  - **Hybrid:** when GD-LMS misses e_threshold, the node checks an offline-trained LSTM (2 layers, 50/15 units, window 50). If the LSTM is within the threshold, the node sends a short **beacon** ("use the LSTM value") instead of the reading. Otherwise it sends the reading.
  - Tolerance rule (eq. 24): e = min(|max−avg|, |min−avg|)·λ%. λ = 5% gives 0.2 °C.
- **Data:** Intel Lab temperature, node 13: 25,000 samples, 31-s sampling, abnormal values interpolated. The LSTM uses 21,332 training samples and is tested on **2,545**. The comparison with Santini's LMS uses nodes 1, 11, 13 and 49 (6–9 March).
- **Results:**
  - At 0.2 °C, fewer than one third of the 2,545 samples are sent, plus beacons.
  - **"At least 62.3% of transmission energy"** saved, assuming a beacon costs ≤ ½ a data packet (ZigBee).
  - MAE 0.0688; "accuracy ≈ 93%".
  - Table IV reports the maximum absolute error.
- **Not done (in their own words):**
  - "The algorithm proposed in this paper **assumes that there is no network failure**"; loss is future work.
  - Univariate.
  - One indoor dataset.
  - Energy counted as a packet count.
  - No comparison with constant/SOD.
  - The LSTM is trained offline on 85% of the series (the test is only the last ~10%).
- **⚠ Our derivation (verified numerically 2026-10-10, max difference 5e-15):** GD-LMS (eqs. 12–15) is exactly **normalised LMS with unit step**: W ← W + X·e/‖X‖². The same holds for OSSLMS in Jarwan 2019 (paper 29, eq. 5). Because the unit step projects the weights onto the latest sample, the filter tends towards persistence. This is consistent with Jarwan's report that its weights converge to [1, 0, …, 0].
- **Use:**
  - In-domain (environmental) IoT-J DPS: the closest "learned predictor in a DPS" paper to cite.
  - Its explicit no-loss assumption supports our loss contribution.
  - The beacon idea is a cousin of our heartbeat/flag messages.

### 29: Jarwan, Sabbah, Ibnkahla (2019). *Data Transmission Reduction Schemes in WSNs for Efficient IoT Systems.* IEEE JSAC 37(6):1307–1324. (Added 2026-10-10, full read)
- **Not a review.** It is a research paper with a comparative study:
  - **Tier 1:** a bounded DPS between cluster member and cluster head (Santini-style feedback, e_max). OSSLMS vs online NN vs online LSTM.
  - **Tier 2:** lossy block compression at the cluster head (PCA, NMF, T-SVD, truncated DWT, and a new R-DWT-PCA). This tier has **no hard bound** and adds a delay of m slots.
- **Data:** Intel Lab temperature, **resampled to 5-hour intervals** with gaps filled, first 600 slots, six clusters.
- **Results (DP):**
  - At e_max = 0.5 °C, N = 10: mean transmission reduction over all nodes is **LSTM 51.2%, NN 51.1%, OSSLMS 48.3%**. Learned models gain only ~3 points.
  - "The latest N−1 weights in W converge to zero … the first weight approaches one". In other words, **OSSLMS degenerates to the last value (persistence)**.
- **Open issues it names that we answer (§VI):**
  - **Loss ambiguity:** "a suppressed transmission … looks the same as a failed reception … some techniques must be developed".
  - **Cross-parameter prediction:** "using data from all onboard sensors to predict … each individual sensor is beneficial", plus time-of-day features.
  - Critical data may bypass DP.
  - Evaluation is application-layer only; lifetime and hardware are future work.
- **Use:**
  - Correct the draft's "Jarwan et al. review …" to describe a *comparison*.
  - Its ~3-point gain of LSTM over (persistence-like) OSSLMS is independent prior evidence for our C1: learned prediction pays little unless the signal has predictable structure.
  - Cite its loss-ambiguity statement in the loss subsection.

### 30: Liazid, Lehsaini, Liazid (2019). *An Improved Adaptive Dual Prediction Scheme for Reducing Data Transmission in WSNs.* Wireless Networks 25(6):3545–3555. (Added 2026-10-10, full read)
- **Not about adaptive thresholds.** The draft v0.1 said it was; corrected 2026-10-10.
- **What it does:**
  - The sink builds AR models (cloud-assisted) and disseminates them by unicast; the model is not independently generated at the node.
  - When a model drifts beyond e_max, the usual adaptive DPS (Aderohunmu 2013) re-collects a history table of readings to refit.
  - Liazid instead **estimates the new model's parameters from the stored collection of previously used models**, which saves the history-table transmissions.
- **Evaluation:**
  - Data: Tlemcen airport weather (T, pressure, RH), 30-min sampling, January 2017. AR orders 3/3/4, chosen by a validation criterion.
  - **The transmission tables come from the Dias 2017 ring-network model with *assumed* accuracies a_min and b_min (0–0.9).** They are not measured suppression on the data.
  - Results: 1–5 points better than ordinary adaptive DPS, "up to 99%" when accuracies are high; energy is TelosB per-bit.
- **Not done:**
  - "Synchronization problem … not considered"; "the number of lost packets will not be taken into consideration".
  - Event detection is "not under the scope".
- **Use:** an example of model-maintenance refinements and of the no-loss assumption. Cited in Related Work ("Later work" and the loss sentence).

### 22: Adu-Manu, Katsriku, Abdulai, Engmann (2020). *Smart River Monitoring Using WSNs.* Wireless Commun. Mobile Comput. (Added 2026-10-03)
- **What:** a Libelium Smart Water + Smart Water Ions deployment at the **Weija intake (Ghana)**, Sept 2018 – Feb 2019.
  - Star topology; ZigBee to a base station ~1.5 km away; 4G/GPRS to the cloud with a web portal and SMS alerts; solar harvesting.
  - **Reporting every 30 min (pH, EC, T, Ca, F) and hourly (DO, ORP) "to overcome communication delays and energy consumption".**
  - Each parameter is sent in its own frame (Table 2).
- **Issues observed:** biofouling, cable damage (pH −1.99), out-of-range values, duplicate retransmissions, internet-data outages, and **DO mean 17.36 / SD 30.44 and "negative DO"** (same Libelium DO sensor; see `docs/DO_UNITS_EVIDENCE.md`).
- **Use:**
  - Motivation and continuity with the Prof's work: Ghana, the same hardware family, transmissions reduced by hand-chosen fixed intervals. Our scheme makes that choice data-driven and error-bounded.
  - The Weija data is a candidate **second dataset**; ask the Prof.

### Dataset context (not part of the reading list; for the data section)
- **Shala et al. (2014), Geoadria.** Grab-sample DO in the Sitnica; Plemetin station as low as 0.53 mg/L (spring). Plemetin is affected by industrial wastewater discharge.
- **Kelmendi & Aliu (2023), IJESD 14(2).** Plemetin (S1) grab samples: T ≈ 19 °C, EC 689–737 µS/cm, DO 5.15–7.19 mg/L, pH 7.7–7.8. Described as close to the Kosovo A/B power plants.
- Local copies: `papers/dataset_context/`.

---

## C. Radio energy models (for our energy/lifetime evaluation)

### 10: Sørensen et al. (2021). *Modelling and Experimental Validation for Battery Lifetime Estimation in NB-IoT and LTE-M.* arXiv 2106.13286.
- **Model:** a state/procedure energy model (sync, service request, TX/RX, cDRX, release, PSM, TAU), validated within 5% on u-blox N211 (NB-IoT) and R410M (LTE-M).
- **Measured values (Table X, N211):**

  | Quantity | Value |
  |---|---|
  | P_TX at 23 dBm | 743 mW |
  | P_RX | 222 mW |
  | cDRX sleep | 21 mW |
  | **PSM sleep** | **9.5 µW** |
  | **Sync after wake-up** | **160 mJ** (R410M: 362 mJ NB-IoT, 1095 mJ LTE-M) |

- **Formulas:** E_cycle = E_sync + E_SR + E_cDRX + E_release + E_PSM (eq. 30). Lifetime = C·SF / (E_hour + E_device) (eq. 32).
- **Findings:** TAU dominates when reports are rarer than T3412. ~10-year life only at ≥ 24-hour reporting.
- **Use:** our NB-IoT/LTE-M energy model and its parameters.

### 11: Michelinakis et al. (2021). *Dissecting Energy Consumption of NB-IoT Devices Empirically.* IEEE IoT Journal. (arXiv 2004.07127)
- **What:** field measurements with 2 modules × 2 operators.
- **Findings:**
  - Energy per uplink packet (connected state): default timers **~0.8–4.2 J**; with the RAI flag **~0.12–1.3 J**.
  - **Packet size barely matters** unless RAI is used.
  - PSM ≈ 10 µW.
  - **Packet loss 0.5–1%** on commercial networks.
- **Lifetime (Table X, 5 Wh, 20-byte packets):**

  | Reporting interval | Default timers | With RAI |
  |---|---|---|
  | 1 h | **0.5–2.4 years** | ~6 years |
  | 24 h | up to ~13 years | ~45 years |

- **Use:**
  1. On cellular IoT the cost is **per report, not per byte**.
  2. 10-minute reporting with default settings would last **months, not years**. This is the practical motivation.
  3. The 0.5–1% loss rate means DPS resynchronisation matters.

### 09: Casals, Mir, Vidal, Gomez (2017). *Modeling the Energy Performance of LoRaWAN.* Sensors 17:2364.
- **Model:** an 11-state current profile per uplink (wake-up, TX, two receive windows, etc.) measured on a MultiConnect mDot.
- **Lifetime with a 2400 mAh battery:**

  | Reporting interval | Lifetime |
  |---|---|
  | 5 min | **0.26–0.83 years** |
  | 60 min | 2.1–3.8 years |
  | Never (sleep only) | 6.2 years |

- **Other findings:** payload size matters only at short intervals; BER and collisions can cut lifetime by up to 10×.
- **Use:** our LoRaWAN energy model.

---

## D. Gap analysis: where Paper 1 can contribute

| Capability | 05 DBP | 06 Carvalho | 07 Morales | 12 Rao | 17 AdaptiveML | 14 Shu | **Paper 1 (target)** |
|---|---|---|---|---|---|---|---|
| Dual prediction, sample-by-sample | ✓ | – (batch) | ✓ | ✓ | ✓ | – (sampling) | ✓ |
| **Hard per-parameter error bound** (max error ≤ δ) | ✓ | – | – | ✓ | **– (grows with σ)** | – | ✓ |
| Cross-parameter (multivariate) predictor | – | ✓ | ◦ (outputs only) | – | – (future work) | – | ✓ |
| **Report-level decision** (one wake-up sends all parameters) | – | – | – | – | – | – | ✓ |
| Adaptive threshold | – | – | – | ◦ (daily) | ✓ (volatility) | ◦ | ✓ (noise-aware, capped) |
| **Event-preserving** (events never smoothed away; detection delay measured) | – | – | – | ◦ (fixed limits) | – | – (misses peaks) | ✓ |
| Sync overhead and packet-loss resync | ◦ | – | – | ✓ (overhead) | – (future work) | – | ✓ |
| **Cellular/LPWAN energy model** (per-report J, PSM, TAU, RAI) | – (MAC/CTP) | – (µJ/byte) | – | – | – (59 µJ/pkt) | ◦ (sensing) | ✓ |
| Real river water-quality data | – (simulated chlorine) | – | – | – | – | ✓ (buoy, hourly) | ✓ |

✓ = done, ◦ = partial, – = not done.

**Update 2026-10-03 (papers 23, 24).** The report-level idea has two ancestors, and we must cite both:
- **Santini & Römer 2006** proposed (but never built) a block/joint prediction where a cluster head reports only if the joint error exceeds a threshold.
- **Ghosh et al. 2022** built wake-up-aware *batching* for a multi-parameter hub, using fixed "bad" limits.

Neither gives per-parameter hard bounds with immediate (no batching delay) reporting, cross-parameter predictors in a DPS, event detection beyond fixed limits, or an LPWAN per-report energy evaluation. So the claim must be phrased as **"the first evaluation and design of report-level, bounded, event-preserving DPS for LPWAN water-quality monitoring"**, not "the first joint decision".

**Conclusion.** Single ingredients exist: DPS, multivariate prediction, adaptive thresholds, critical limits. What no paper we found does is **combine them under the cost structure of cellular/LPWAN water-quality monitoring**:

1. Suppression decided per **multi-parameter report**. This matters because on NB-IoT/LoRaWAN the energy is paid per wake-up, not per byte (papers 10, 11). The report is sent if *any* parameter fails, so good cross-parameter prediction pays off *more* here than in per-packet models.
2. A **hard per-parameter error bound** with a **noise-aware** threshold that never exceeds the application tolerance, plus **event preservation**. This is the opposite of ADAPTIVEML, which loosens during volatility.
3. Evaluation with **real per-report energy** (NB-IoT with and without RAI, LoRaWAN, legacy GPRS), including sync, heartbeat and TAU overheads and 0.5–1% loss.
4. On **real river data** (InWaterSense), plus a second dataset for generality.

## E. Still to obtain via the UG library (for completeness)

*Obtained 2026-10-03: Ghosh et al. 2022 (23), Santini & Römer 2006 (24), Adu-Manu et al. 2020 (22).*
*Obtained 2026-10-05 and read in full 2026-10-10: Wu 2020 (26), Almalki 2021 (27), Shu 2019 (28), Jarwan 2019 (29); see the cards in §B. Liazid 2019 (30) was added and read the same day. Every paper cited in the draft has now been read in full. Still missing: Ahmedi 2018 (the InWaterSense system paper, not cited).*

*Draft edits made 2026-10-10 from papers 26–30 (Related Work only; no results changed):*
- *Jarwan is described as a comparison, not a review.*
- *Liazid is described as model maintenance, not adaptive thresholds.*
- *Wu is added to the joint decisions.*
- *The critical-limits sentence now cites Almalki directly (Płaczek dropped from the references).*
- *A loss-ambiguity sentence was added.*
- *A footnote states GD-LMS/OSSLMS = unit-step NLMS.*

- Liazid, Lehsaini, Liazid (2019), *Wireless Networks* 25:3545. Adaptive DPS, threshold from a moving average of errors.
- Shu, Chen, Bhargava, de Silva (2019), *An energy-efficient DPS using LMS filter and LSTM…*, IEEE IoT J 6(4):6736. (Authors verified via OpenAlex.)
- Wu, Chen, Chen, Fan, Liu (2020), *An adaptive DPS based on edge intelligence*, IEEE IoT J 7(10):9481.
- Jarwan, Sabbah, Ibnkahla (2019), IEEE JSAC 37(6):1307.
- Almalki et al. (2021), *EERP-DPM…*, J. Healthcare Eng. (DPS plus always-report critical limits.)
- Santini & Römer (2006), INSS. The original LMS-based DPS.
- Ahmedi et al. (2018), the InWaterSense system paper (IJAEIS 9(1)).
