# WP-013 — Continuous v0.4 reference September–December 2025: registered protocol

Date: 2026-10-07. Status: **REGISTERED BEFORE LAUNCH — Owner launch INACTIVE** until the Director's technical review and green exact-SHA CI.

Authority:
- the Owner's assignment of 7 October 2026, applying the Astra protocol;
- Q4 dossier closure at `2d6fe9e`: accepted as descriptive evidence; RETURN–terminal association observed; causality not identified; no method change authorized.

This document registers the windows, pins and reading criteria **before** any result exists. It authorizes no method change.

## 1. Fixed protocol (UTC, half-open intervals)

| Window | Interval | Role |
|---|---|---|
| Initialization | 2025-07-28 00:00 → 2025-09-01 00:00 (35 days, 840 h) | context only, **not evaluated** |
| Evaluation | 2025-09-01 00:00 → 2026-01-01 00:00 (122 days) | the only scored portion |
| Tail | 2026-01-01 00:00 → 2026-01-01 06:05 (365 min) | outcome tail only, not scored |

**Registered preset.**
- Id: `btc-2025-09-to-2025-12-continuous-init35d-v1`, labelled "September–December 2025 — continuous reference (35-day initialization)".
- File: [`delivery/WP-013-PRESETS.json`](WP-013-PRESETS.json), byte-identical to `src/algotrader/corpus/presets.json`.
- `initialization = REGISTERED_EXPLICIT_INITIALIZATION`.
- Identity sha256: `fabd1c55535a1f13e0fe7cdd30e217886e229063987015e4a7fbf64a0c952dbc`.

**Earlier presets.** The file-level fine warmup stays 96 h. The two WP-008-R3 presets and every month-builder preset keep byte-identical documents and identities, so nothing about the earlier runs changes.

**Why 28 July.** It is a Monday. The initialization therefore contains, before 1 September:
- the complete previous month (August);
- the previous week (25–31 August);
- the previous day (31 August);
- the full 168 h memory window of the 1 h pivots.

**Run.** This is **one continuous v0.4 run**:
- one WARMUP→EVALUATION transition at 1 September;
- no reset or finish at the 1 October, 1 November or 1 December boundaries;
- the existing v0.4 tail semantics.

**What the run does not isolate.** It is **new development evidence**. It does **not** isolate the warmup effect: the initial context and the continuity across months change together relative to the single-month Q4 runs.

## 2. Pins identifiable in the report

The report's **Launch pins** section names:
- method v0.4 (`btc.context-action.v0.4` / `mp003.rules.v0.4`), with rules, register, implementation and identity hashes;
- build;
- capability profile and its hash;
- clock policy;
- evaluator format and hash;
- per-variant costs: fee 5 bps/leg, allowance 2 bps/leg, entry/exit delays;
- pack and feed identity.

**PRIMARY stays the 60-second entry delay.** No parameter, rule or numerical value of the method changes, and no new cyclical reading is added: the initialization only feeds the current method's existing dependencies.

## 3. Reading criteria, registered before launch

1. **Technical problems block conclusions.** Technical, causal or coverage problems prevent economic conclusions. Examples: assurance not passed, failed total/monthly reconciliation, initialization coverage gaps, or a context attestation showing insufficient data. The run is then diagnosed, not interpreted.
   - *Director decision, 7 October 2026 (WP-013 F2-R1, recorded verbatim):* “REPORT INCOMPLETE blocca la lettura economica della prova, anche con run COMPLETED e assurance PASSED. È una valutazione della completezza del report e non modifica retroattivamente lo stato o l’assurance salvati. Una riconciliazione fallita resta un blocco distinto.”
   - In English: REPORT INCOMPLETE blocks the economic reading of the run, even when the run is COMPLETED and its assurance PASSED. It assesses the completeness of the report and does not retroactively change the saved status or assurance. A failed reconciliation, including extraneous or repeated path records, remains a separate block.
2. **No changes mid-window.** A negative result does not lead to any change midway through the window. The frozen v0.4 candidate is read over the whole registered window.
3. **Small samples stay insufficient.** There is no call quota to reach, and more calls are not an improvement by themselves.
4. **Later revisions need a falsifiable diagnosis.** A diagnosis alone does not justify a revision, nor does the price-net balance alone.
5. **Report the sensitivities with their denominators.**
   - PRIMARY is the reference; sensitivities are reported, never selected for being favourable.
   - Sums are normalized one-unit price-net sums. They are not account returns, and funding is not covered.
6. **January–August 2026 stays protected**, except the already-documented 1 January 00:00–06:05 tail, which this run consumes again as an outcome tail only.

## 4. Report produced by the run

The report comes from committed records only. It is available through **Copy report for chat** and the Markdown/JSON exports.

**Context at the evaluation start.**
- Coverage of the initialization.
- Readiness of the 1m/15m/1h scales.
- State of the previous day/week/month levels and of the 15m/1h pivots.

It keeps three cases apart:
- insufficient data;
- never-built landmarks;
- levels that were built and then legitimately broken, expired or retired.

Pivot memory completeness is **never certified**.

**Total and monthly sections of the same run.** One section each for September, October, November and December, plus the total. Each section reports coverage/assessability, MarketView rows and samples, scenario transitions and A confirmations, routing and D/N, WAITs, calls and guidance, and the hypothetical paths.

Attribution rules:
- Calls are attributed to their month of issue and followed to their outcome even after that month ends, never counted twice.
- Confirmations and WAITs use their own publication/opening times.
- Coverage uses minutes and view samples use their sample time, each with its own denominator.

Censoring and the uncovered funding stay explicit. The report also carries an exact reconciliation of the total against the monthly sections.

## 5. Owner instructions (INACTIVE until technical review and green CI)

When the Director activates this run:

1. Start the app as usual and open **Historical Workbench**.
2. In step **1 · Prepare data**, open **Other selections** and find **"September–December 2025 — continuous reference (35-day initialization)"**.
   - The panel shows the evaluation period and the initialization separately, and says the initialization is not evaluated.
   - It lists what is already on this computer and what needs download (expected at least 28–31 July and August 2025), with a size estimate.
3. Press **Prepare data** and wait for **Ready**.
   - Only missing data are downloaded; completed downloads are reused if you retry.
   - If it ends **Ready with limitations**, copy the preparation report and stop: do not launch.
4. In step **2 · Check data and engine**, select this pack.
   - Choose **Adviser evaluation** and **MP-003 v0.4**.
   - Leave speed at maximum and press **Start**. Do not change anything else.
5. Expected time:
   - The September–December evaluation is roughly 4–5 times the earlier single-month runs, which took about 2 minutes each: about 10–15 minutes.
   - Preparation adds the download and verification time of the missing days, typically several minutes.
   - The app shows the measured ETA.
6. In step **3**, when the run is **COMPLETED**, press **Copy report for chat**, paste it here, and also download the JSON export.
   - If the run fails or is interrupted, copy the diagnostic report anyway.
