# Paper 1 from the ground up: a tutorial and meeting prep

*Written 2026-10-04 for you, before the meeting with Prof Adu-Manu. Read it in order. Part 1–2 take about an hour; Part 3 is the story of what we did; Part 5 is your meeting cheat sheet. Every number here comes from our own results files (paths at the end).*

---

## Part 1. The problem, in plain words

A **water-quality sensor node** sits in a river. Every 10–15 minutes it wakes up and measures temperature (T), conductivity (EC), dissolved oxygen (DO) and pH. Then it sends the readings to a server over a radio and goes back to sleep.

**Sending is expensive.** Waking the radio, connecting to the network and waiting for the network to let go costs far more energy than sleeping. It also costs money (cellular IoT plans charge per message or per byte) and network capacity. Yet most of the time the river barely changes: the next reading is almost what the server could have guessed.

**The idea:** let the node send only when the server would otherwise be *wrong by more than a tolerance δ* (delta). Everything else, the server fills in by itself. If done carefully, the server's picture of the river is **guaranteed** never to be off by more than δ, while the node sends far fewer messages.

**The research question of the paper** follows from that idea: *when does this pay, by how much, and with what guarantees?* "When" matters because rivers differ. Some are smooth and rhythmic; some are noisy. A trick that works on one may not work on another.

---

## Part 2. The concepts you need (with tiny examples)

### 2.1 The node, the radio, and what a "report" costs

- A **node** has a microcontroller (the "host", e.g. Libelium Waspmote), sensor probes, a battery (often with a solar panel), and a radio modem.
- **LPWAN** (Low-Power Wide-Area Network) radios are designed for this job:
  - **NB-IoT** and **LTE-M** run on the mobile networks (MTN, Vodafone, etc.).
  - **LoRaWAN** uses your own gateways on free radio bands.
- A **report** is one transmission. On NB-IoT it costs about **0.11–0.33 J** if the modem releases the connection right after sending (a flag called **RAI**, Release Assistance Indication). It costs **0.8–4 J** with default timers, because the modem waits 10–20 s for possible replies. *Source: Michelinakis 2021, which measured real commercial networks.*
- **Sleep:** between activities the modem sleeps in **PSM** (Power Saving Mode, ≈ 10 µW). The Waspmote host sleeps at 33 µA.
- **Sensing:** the host must be awake while the probes take a reading (≈ 69 mW). How long varies (1–30 s). This turned out to matter a lot (Part 3, Phase 4).

**Key fact:** the cost per report is nearly independent of its size, because 20 bytes and 200 bytes cost almost the same. So what we must cut is the *number of reports*, not the bytes. That's why our scheme works at the level of *reports*.

### 2.2 Send-on-delta (SOD): the simplest scheme

The node remembers the last value it sent. It sends again only if the new reading differs by more than δ.

*Example* (δ = 0.2 °C):

| Time | Temperature | Sent? | Server shows |
|---|---|---|---|
| 10:00 | 25.0 | **yes** (first reading) | 25.0 |
| 10:15 | 25.1 | no (changed only 0.1) | 25.0 |
| 10:30 | 25.15 | no | 25.0 |
| 10:45 | 25.3 | **yes** (0.3 > 0.2) | 25.3 |

The server's error is never more than 0.2. That's the **error bound**, and it's guaranteed by construction.

### 2.3 Dual prediction (DPS): "both sides guess the same way"

SOD's "guess" is just "same as last time". We can guess better. If the river warms every morning, the guess could follow that trend.

**Dual Prediction Scheme:** the node and the server run **the same predictor on the same information**, so they always make **the identical guess**. The node also sees the true reading:
- if |true − guess| ≤ δ, it stays silent and the server uses the guess;
- otherwise it sends the true value.

The bound still holds, and if the guesses are good, silence happens more often.

**The subtle part is synchronisation.** The predictor may only use values the server also knows: reported values, or its own guesses when nothing was reported. If the node quietly used its private true readings, the two guesses would drift apart and the guarantee would break. Santini & Römer (2006) formalised this; our code follows it, and our tests check it by replaying the server from the reports alone.

### 2.4 The tolerance δ and our levels L0–L4

δ is the *largest error the user accepts*. We tested five levels for every parameter:

| Level | T | DO | pH | EC |
|---|---|---|---|---|
| L0 (tight) | 0.05 °C | 0.5 %sat | 0.02 | 0.5% of median |
| **L2** (our main) | **0.2 °C** | **2 %sat** | **0.1** | **2%** |
| L4 (loose) | 1.0 °C | 10 %sat | 0.5 | 10% |

These are *our* choices. One question for the Prof is whether regulations or standard practice suggest values.

### 2.5 Report-level decisions: bundling and free-riding

A node measures 4 parameters, and any of them may need sending. There are three ways to account for that:
- **Separate:** each exceeding parameter is its own message. That's how InWaterSense actually transmitted.
- **Bundled:** exceeding parameters at the same moment share one message.
- **Report-level** (ours): if *any* parameter must be sent, send *all four* in one message.

Why send parameters that didn't need it? **Free-riding.** They're refreshed for free, so their next exceedance comes later.

*Example:* T must be sent at 10:45. DO hasn't exceeded yet, but it's drifting. It rides along, and the server's DO guess restarts from the true value, so DO's own exceedance (which would have come at 11:00) is postponed.

**Result (Phase 2):** report-level saves **30–45%** of reports compared with separate accounting. Bundling explains most of that at tight tolerances, free-riding at loose ones.

### 2.6 The predictors we compared

| Name | Idea in one line | Source |
|---|---|---|
| **SOD** (last value) | guess = last known value | classic baseline |
| **LMS** | small adaptive filter on the last 4 values | Santini & Römer 2006 |
| **DBP** | straight line (slope) from recent true values; slope sent inside the report | Raza et al. 2015 |
| **Ridge** | linear model on the last 24 values, fitted once | ADAPTIVEML (Kangethe 2026) |
| **RLS / RLS-T** | Ridge that keeps learning online; RLS-T = a more stable memory setting | ADAPTIVEML-RLS |
| **RLS-D** (ours) | predicts the *change*, damped when blind, with history repair | Phase 3 |

**ADAPTIVEML** is the most recent competitor (2026). Instead of a fixed δ, its threshold is α × (recent variability). When the river becomes volatile, the threshold *widens*: you send less, but the error is no longer bounded, exactly when something interesting is happening. We show this costs **8–17× larger worst-case error** for no report saving (Phase 2).

### 2.7 Predictability: why some rivers are easier

Two measures from Phase 1:
- **Diel share:** how much of a series' within-day variation is explained by time of day. Water warms in the afternoon; DO and pH rise with photosynthesis by day and fall at night. Values range from 0 (no daily rhythm) to 1 (pure rhythm).
- **Forecast skill:** how much better a model predicts than "last value" (0 = no better; 0.5 = halves the squared error).

InWaterSense had **diel share 0.01–0.04** (essentially no rhythm, noise-dominated). Most USGS rivers had 0.2–0.6.

### 2.8 Events, glitches and the CUSUM detector

- An **event** is a genuine unusual episode, such as a storm pulse or a pollution spill: ≥ 60 minutes far from normal.
- A **glitch** is a sensor spike that quickly reverts.
- **The problem:** the error bound only guarantees accuracy *within δ*. An event *smaller than δ* never triggers a report. At loose tolerances we found every predictor missed about 37% of events (Phase 2).
- **CUSUM** (cumulative sum; Page 1954) is a classic change detector.
  - Each new reading gets a score: how far it is from what normal behaviour predicts, divided by the typical noise.
  - The scores are added up, minus a slack k, and never below zero.
  - When the total exceeds a threshold H, it raises an **alarm**.
  - One spike can't trigger it (scores are capped); a sustained departure does.
- An alarm forces a report and tells the server "something unusual started".

### 2.9 Packet loss and "bounded or flagged"

Real networks lose about **0.5–1%** of messages (Michelinakis). With DPS a lost report is dangerous. The node thinks the server got the value; the server didn't, so their predictors diverge and the server's error can grow without limit. Two fixes:
- **Confirmed uplink (ack):** the server acknowledges each report, and the node retries up to twice. If all attempts fail, the node *knows*, and both sides stay in sync. Cost: about the loss rate in extra transmissions.
- **Unconfirmed + sequence numbers + heartbeat:** the server notices a gap in sequence numbers and **flags** the affected data as unverified. A periodic heartbeat report resets both predictors.
  - Guarantee: **every value the server does not flag is within δ.**
  - We tested this in 1,120 simulations: zero exceptions.

### 2.10 The energy model

Energy per day = **sleep** + **sensing** + **reports**.
- Sleep is the floor: host + modem sleeping, 24 h.
- Sensing is the same for every scheme: samples per day × awake power × awake time per sample.
- Reports are what our scheme reduces: reports per day × (radio energy + host awake during transmission).

Battery life = battery energy ÷ energy per day. We validated this against the two measurement papers: it reproduces 20 of 24 of Michelinakis's lifetimes, and Casals's LoRaWAN tables.

### 2.11 The statistics, and why we used each

- **Train/test split:** each method may learn only on the first 20% of a series and is scored on the remaining 80%, which it has never seen. Otherwise we'd be measuring memorisation.
- **Spearman ρ (rho):** rank correlation, from −1 to 1. It asks "when X is higher, is Y higher?" without assuming a straight line. Used for diel share vs gain.
- **Wilcoxon signed-rank test:** "is method A better than B across these sites, more often than chance?" It is paired and makes no normality assumption. Used for RLS-T vs SOD.
- **Leave-one-out:** recompute a result with each site removed. If ρ stays high, no single site is driving it.
- **Pre-registration and tuning/test sites:** before seeing the results, we wrote down which sites are for *choosing* settings (7 USGS sites) and which for *testing* (6 USGS + InWaterSense), and the rule for choosing. This prevents fooling ourselves by tuning on the data we report.
- **Injected events:** we added synthetic steps and ramps of known size and start time to the real data. That gives true answers for "did the detector catch it, and how fast?"

---

## Part 3. The story: what we did, why, and what we found

### Phase 0: Literature (25 papers)

We read the field: the Prof's 2017 survey, the Dias 2016 survey of prediction-based data reduction, Santini 2006, Raza 2015, energy measurement papers, and more.

**Then we found ADAPTIVEML**, a July 2026 preprint already proposing adaptive prediction thresholds. Our original idea overlapped, so we **re-centred** Paper 1 on what it lacks:
- **guarantees:** a hard error bound and event preservation;
- **report-level decisions;**
- **multi-river evidence of *when* prediction pays;**
- **real LPWAN energy.**

Santini 2006 and Ghosh 2022 partly anticipate the report-level idea, so we cite them and phrase our claim narrowly: *our contribution is the quantified decomposition across 14 sites, not the idea itself.*

### Phase 1: Data and predictability

**InWaterSense** (Sitnica river, Kosovo, May 2015 – Jan 2016, every 10 min, Libelium nodes, GPRS):
- **Cleaning:** we re-joined messages that had been split into separate rows (the published grouped file has 4,642 null rows, but only 3–6 of 19,090 cycles really miss a parameter).
- **DO units:** we proved from the Libelium code and local grab samples that DO is in **% saturation**, not mg/L (`docs/DO_UNITS_EVIDENCE.md`).
- **Artefacts:** a suspected DO fouling artefact on 2–7 Sep 2015, and level shifts on 24 Jun, 12 Oct and 24 Dec.
- **Finding: InWaterSense is not predictable.** Diel share is 0.01–0.04, nothing beats "last value", and cross-parameter information adds nothing. It's noise-dominated.

**13 USGS rivers** (2023, approved data, sites chosen by a rule written down in advance, so we couldn't cherry-pick):
- **Prediction helps (1-h skill > 0.1)** for T at 10 of 13 sites, DO 8/13, pH 11/13, EC only 3/13.
- **Cross-parameter information helps mostly for pH:** the median model error drops by 19% (VAR/AR = 0.81).
- **Diel share explains forecast skill:** ρ = 0.66.
- **The costliest months are the most predictable:** ρ = +0.78 for T, +0.68 DO, +0.59 pH. So prediction helps exactly when you'd otherwise send most.
- **A failed idea, recorded honestly:** a simple two-number theory to predict report rates was off by 2–6×. So no "predict your battery from two numbers" claim.

### Phase 2: Baselines (2,016 simulation runs)

Every method above, at every tolerance level, in all three accounting modes, on all 14 datasets:
- **F1.** On predictable rivers RLS-T beats SOD by **+26% at L2** (all 13 rivers; p = 0.0002). It doesn't at the tightest tolerance (noise wins) or the loosest (little left to save). On InWaterSense, SOD is best. **Paper defaults fail:** Santini's LMS reports about 99% of samples, and ADAPTIVEML's γ = 0.98 is unstable.
- **F2 (central result).** **Diel share predicts how much prediction saves: ρ = 0.84** (p = 0.0002). It's still 0.80 without InWaterSense, and 0.75 with the worst site removed. This answers "when does prediction pay?"
- **F3.** Report-level decisions save **30–45%** of reports versus per-parameter.
- **F4.** ADAPTIVEML has **8–17× larger worst-case error** at the same report rate (100% of cases).
- **F5.** Fixed schedules: periodic reporting has 4–24× larger error at the same report count; batching delays events by 15–120 min.
- **F6 (limitation).** At loose tolerances every predictor misses about 37% of events smaller than δ. This motivated the detector.

### Phase 3: The proposed scheme and its stress tests

We set up rules to avoid fooling ourselves: tuning and test sites, injected events, every design choice by a written rule.

**Detector.**
- The first version raised about one false alarm per day. Diagnosis: smooth water data is autocorrelated, so the residual stays high for hours.
- The fix was a residual from a diel-aware 2-hour forecast.
- **Held out, the chosen setting** (≤ 2 false alarms per parameter per month on tuning sites) detects **70% of 5σ steps and 85% of 8σ steps**, but few slow ramps. **About half its "false alarms" coincide with real events (6× chance).**
- **At L4, the sensitive detector catches 97% of injected steps at 3.1 reports/day. Plain L3 needs 7.8 reports/day to catch 87%.** Real events gain less (0.62 → 0.72).

**Predictor: three negative results first, each diagnosed.**
1. **Choosing the predictor at deployment from early data fails.** The training period is winter, when SOD suffices, but RLS-T wins in summer.
2. **Switching predictors online fails.** It is stable after a fix, but still loses.
3. **Halving δ during events costs reports for almost no gain.**

**What worked: RLS-D.** We diagnosed *why* model predictors lose at loose tolerances:
- Between reports the predictor runs "blind" for hours and drifts.
- When a report arrives, the correction jump looks like a fake fast change, and the model extrapolates it.

The two fixes:
- **Damping:** the predicted change fades the longer the node is blind (damped trend, Gardner & McKenzie 1985, still to verify).
- **History repair:** after a report, the blind stretch is replaced by a straight line from the previous to the new reported value.

**Result:** one predictor within about 0–2% (median) of the best fixed choice per site, with no selection step. The same mechanism explains Phase 2's "sweet spot".

**Loss study (1,680 runs):**
- Confirmed uplink: overhead ≈ loss rate.
- Unconfirmed + heartbeat: 0 unflagged violations, but model predictors pay +15–30% reports.
- SOD is "self-synchronising", because any received report repairs it.

### Phase 4: Energy and battery life

The model is built from published measurements and validated against them.
- **Suppression extends battery life 1.1–3.5×.** It's largest when reports are costly relative to sensing (fig 10). With 5 s sensing on NB-IoT, it's 1.5–1.7×; with 30 s sensing, ~1.2× at best.
- **RLS-D adds only 0–7% over SOD**, because after suppression reports are just 10–27% of the energy. The detector costs about 1%.
- **The strongest claim is equal accuracy** (fig 11):
  - at the same worst-case error, RLS-D lives **53% longer** than 30-min reporting;
  - at about the same battery life as hourly reporting, its worst-case error is **7.8× smaller**, and events arrive immediately.
- **Honest framing:** a solar node with a 2 W panel has **≥ 33×** more energy than needed, so for solar nodes energy isn't the argument. Fewer reports matter for battery-only nodes (manholes, pipes, submerged probes), smaller hardware, per-message costs and LoRaWAN airtime limits.

---

## Part 4. The paper in one page

**Title:** When Does Prediction Pay? Predictability-Aware, Error-Bounded Report Suppression for LPWAN Water-Quality Monitoring.

**Research questions:**
1. **RQ1:** When are water-quality series predictable enough for prediction to pay? *Answer: where the day–night cycle dominates; diel share predicts the gain (ρ = 0.84).*
2. **RQ2:** How much do report-level decisions save? *Answer: 30–45%.*
3. **RQ3:** Can we keep guarantees (bounded error, event awareness) while matching adaptive schemes? *Answer: yes. ADAPTIVEML's error is 8–17× worse at equal cost; the detector recovers events at loose tolerances; "bounded or flagged" under loss.*
4. **RQ4:** What does it buy in energy and cost? *Answer: 1.1–3.5× battery life, and 53% longer at equal accuracy; energy matters for battery-only nodes. Framing to agree with the Prof.*

**Contributions** (each backed by results):
- **C1:** multi-river predictability study (14 datasets, sites chosen by a fixed rule).
- **C2:** RLS-D, near-optimal without per-site selection, plus documented negative results.
- **C3:** guarantees: bound, detector, loss protocols.
- **C4:** validated LPWAN energy model with an equal-accuracy evaluation.
- **C5:** open benchmark code.

**What we are NOT claiming:**
- that the report-level idea is new (Santini and Ghosh anticipated it);
- that RLS-D beats SOD everywhere (it doesn't on InWaterSense);
- that energy is the binding constraint on solar nodes;
- hardware measurements of our own.

---

## Part 5. Meeting cheat sheet

### 5.1 One-minute pitch (practise saying this aloud)

> "Sensor nodes waste most of their transmissions sending readings the server could have guessed. We studied when prediction-based suppression actually pays, using InWaterSense and 13 US rivers. The answer is: where the day–night cycle dominates. A simple measure of that rhythm predicts the saving with a correlation of 0.84. Sending all parameters together whenever one must go saves another 30–45%. Unlike the newest competing method, ADAPTIVEML, our scheme guarantees the error bound; theirs is 8–17 times worse in the worst case at the same cost. We added an event detector and loss-recovery protocols, and a battery model built from published NB-IoT and LoRaWAN measurements. At the same battery life as hourly reporting, our worst-case error is about 8 times smaller."

### 5.2 Six figures to show, in this order

1. `results/phase1/figures/fig1_diel_vs_skill.png`: predictability follows the day–night cycle.
2. `results/phase2/figures/fig5_link.png`: **the central result** (ρ = 0.84).
3. `results/phase2/figures/fig4_pareto.png`: fewer reports with a guaranteed bound (vs ADAPTIVEML and periodic).
4. `results/phase3/figures/fig8_detector_tradeoff.png`: loose tolerance + detector beats tightening.
5. `results/phase4/figures/fig11_equal_accuracy.png`: same battery life, about 8× smaller worst-case error.
6. `results/phase4/figures/fig10_gain_vs_sensing.png`: when suppression pays in battery life.

### 5.3 Questions the Prof may ask, and your answers

- **"Why not just report every hour?"**
  Fig 11: hourly reporting has a 7.8× larger worst-case error for about the same battery life, and events wait up to an hour. Ours bounds the error and reports events immediately.

- **"Isn't this just send-on-delta?"**
  SOD is our baseline, and an honest one: on noisy nodes like InWaterSense it's the best predictor. Our contributions are when to use prediction (diel share), report-level decisions (30–45%), guarantees under events and loss, and RLS-D, which matches the best choice per site without having to choose.

- **"What's new compared with ADAPTIVEML?"**
  ADAPTIVEML widens its threshold when water is volatile, so its error is unbounded when it matters most: 8–17× worse worst case at the same report rate. It has no report-level decisions, no event mechanism and no loss handling. Its default RLS setting (γ = 0.98) is also unstable on 15-min river data.

- **"How do you know the detector isn't just matching your own event labels?"**
  It's built differently from the labeller: causal, using only the past. It is evaluated mainly on *injected* events with known onsets, and tuned only on tuning sites. Detection on held-out sites matched the tuning sites (0.34 vs 0.34 mean), so there's no overfitting.

- **"Why only 20% training?"**
  A real node deploys with only a few weeks of history. Scoring on the unseen 80% keeps it honest. It also exposed the seasonal problem with choosing predictors at deployment.

- **"What happens when packets are lost?"**
  With confirmed uplink, both sides always stay in sync; it costs about the loss rate in retries. Without confirmation, the server flags data after a sequence gap. Every unflagged value is within δ, with zero exceptions in 1,120 runs.

- **"Your battery numbers depend on sensing time. What did you assume?"**
  We didn't assume one value; we swept 1–30 s. The gains range from about 3× (fast sensing, costly radio) to about 1.1× (30 s sensing). Please tell us the real settling times for the Libelium/Weija probes.

- **"Our nodes are solar-powered; does energy even matter?"**
  You're right that for a 2 W panel it doesn't: there's at least 33× margin. That's why we propose framing RQ4 around battery-only nodes, smaller hardware, per-message cost and LoRaWAN airtime. Would you agree?

- **"Why are your tolerances what they are?"**
  They're a sweep (L0–L4) chosen to span sensor resolution up to coarse monitoring. We'd like your guidance or regulatory references (Ghana EPA, WHO, EU) for defensible values.

- **"What about Weija?"**
  The data arrived today. About 4 months (Oct 2018 – Mar 2019). T, pH and EC are co-sampled every ~30 min; DO is only every ~5 h. 24% of temperature values are imputed, and some values look like sensor faults (pH 0 and 13, DO 46 mg/L). It can be a third, tropical case study on T/pH/EC once cleaned. Ask the Prof which parts are trustworthy.

### 5.4 Decisions to ask the Prof for (write the answers down)

1. **RQ4 framing:** battery-only + hardware + cost, or battery only?
2. **Tolerances:** any reference values?
3. **Venue:** IEEE IoT Journal? A conference version first?
4. **Weija:**
   - which files and periods are trustworthy;
   - probe models and settling times;
   - which radio was used;
   - permission to publish results.
5. **InWaterSense:** how long the node was awake per reading; whether node 1 was in effluent or river water.
6. **Authorship and timeline** for the first draft.

### 5.5 Things NOT to overclaim in the meeting

- "We invented report-level reporting." No: Santini 2006 and Ghosh 2022 came first.
- "RLS-D always wins." No: on noisy nodes SOD is best, and RLS-D adds only 0–7% battery life over SOD.
- "The detector catches all events." No: slow ramps and gradual real events are still hard.
- "10-year battery life." The numbers depend on the module, operator and sensing time. Ratios are robust; absolute years are indicative.

---

## Part 6. Glossary

- **δ (delta):** maximum error the user accepts.
- **SOD:** send-on-delta.
- **DPS:** dual prediction scheme.
- **Report-level:** send all parameters when any must go.
- **Diel:** day–night (24-h) cycle.
- **Skill:** improvement over "last value".
- **ρ:** Spearman rank correlation.
- **Wilcoxon:** paired non-parametric test.
- **LPWAN:** low-power wide-area network.
- **NB-IoT / LTE-M:** cellular IoT.
- **LoRaWAN:** long-range unlicensed IoT.
- **SF:** LoRa spreading factor. SF7 is fast and cheap; SF12 is slow and long-range.
- **PSM:** modem deep sleep.
- **RAI:** release-after-send flag.
- **TAU:** periodic network check-in.
- **CUSUM:** cumulative-sum change detector.
- **Injected event:** synthetic event with a known start, used for testing.
- **Pre-registration:** writing the evaluation rules before seeing results.
- **RLS:** recursive least squares (online learning).
- **Damped trend:** prediction fades towards "hold" over time.
- **History repair:** straight-line fill of the blind stretch after a report.
- **Confirmed uplink:** acknowledged message.
- **"Bounded or flagged":** every unflagged value is within δ.
- **Equal-accuracy comparison:** comparing battery life at the same worst-case error.

## Part 7. Where everything is

- Plan: `PAPER1_PLAN.md`. Handover: `docs/HANDOVER.md`. Literature: `papers/paper1/LITERATURE_NOTES.md`.
- Reports:
  - `results/phase1/PREDICTABILITY_REPORT.md`
  - `results/phase2/PHASE2_REPORT.md`
  - `results/phase3/PHASE3_REPORT.md`
  - `results/phase4/PHASE4_REPORT.md`
- Figures: `results/phase*/figures/`. Tables: `results/phase*/tables/`.
- Code: `src/` (data, analysis, sim, energy). Tests: `tests/` (78 passing).
- Weija data: `cleaned/cleaned/`.

**Check yourself** (answers in Part 3):
1. Why does report-level reporting help even when only one parameter changed?
2. Why did choosing a predictor from winter training data fail?
3. Why is the equal-accuracy comparison fairer than "x times longer battery life"?
4. Why does a detector help at L4 but add little at L2?
