# Continuous v0.4 diagnosis — confirmation → WAIT → issue → entry → outcome

READY FOR DIRECTOR REVIEW — CONTINUOUS V0.4 DIAGNOSIS CORRECTION ONLY (Astra F1–F4 on `e07bbe0`). This is descriptive development evidence. It does not propose or authorize any change to rules, parameters, thresholds or infrastructure.

**Director acceptance recorded:** “Prova continua accettata come evidenza descrittiva di sviluppo; risultato negativo; causa non identificata; nessuna modifica metodologica autorizzata.”

| Item | Value |
|---|---|
| Evaluation / replay | `eval-20261007T182934-3f41ad` / `obs-20261007T182934-f8c3d4` |
| Build | `97a2a8c` (every journal record carries `97a2a8ceb81a…+image`) |
| Method | v0.4 `mp003.rules.v0.4`; rules `316629a4…`, register `5873cb10…`, identity `01d2cc94…`; evaluator v3, PRIMARY delay 60 s |
| Pack / cache | `pack-1ae7d36c…` (manifest `1bec1f15…`), cache `fc-80221b24…` (manifest `95478a50…`, 679,335 events). The evaluation pins this cache, and its manifest equals the pack's pin. |
| Windows | initialization 2025-07-28 → 09-01 (not evaluated); evaluation 2025-09-01 → 2026-01-01; tail to 01-01 06:05 |
| Integrity | Journal 34,682 rows and evaluation records 2,980 rows: digests and chains recomputed, matching the finish commitment (heads `926bf6f9…` / `4e1a6ac5…`). Assurance PASSED 21/21. |

## Access, labels and how the procedure evolved

**Access.**
- The app's own report export (read-only GET) was read first.
- Then the single authorized extraction: one `REPEATABLE READ READ ONLY` transaction ([export.sql](export.sql)), limited to this run, at snapshot `841063:841063:`.
- This correction reuses those local exports only: there was no new extraction.
- No feed cache was copied, and there was no write, replay, Deep validation or counterfactual.

**Labels.**
- **STORED:** journal and evaluation fields.
- **DERIVED:** exact Decimal arithmetic on them.
- **UNAVAILABLE:** intrabar order, historical quotes, news/calendar, and any structure or value change the method does not publish.

**Procedure — not entirely ex ante.** Details are in [DEFINITIONS.md](DEFINITIONS.md).
1. The **initial definitions** (S1–S6, windows, classes) were written from the record schema and existing fields, without thresholds, **before the outcomes were joined**.
2. The **window cutoff was corrected afterwards**, after a first output already joined to the outcomes. Context and phase are computed before the decision but published after it, so the observations of the decision's dispatch are now included. The MarketView published after selection stays excluded.
3. Only the 4 context-withdrawn WAITs change. Both variants are kept: `classification` and `classification_strict_seq`.
4. This correction aligned `classify()` with the definition (missing observations → INDETERMINATE) and made the limits, levels, prices and times explicit. **No class was redefined after the outcomes, and every classification is unchanged.**

## Reconciliation with the report (all match)

| Quantity | Director | Extracted / report builder | App export |
|---|---:|---:|---|
| A confirmations | 89 | 89 | funnel identical |
| WAITs opened | 57 | 57 (`WAIT_OPEN` in window) | identical |
| Calls | 13 | 13 | identical |
| RETURN calls / entered PRIMARY | 12 / 11 | 12 / 11 | — |
| Terminal path records | 52 | 52 (13 × 4; periods COMPLETE; 0 extraneous; 0 duplicates) | periods identical |
| RETURN outcomes | — | 12 = 10 guidance INVALIDATED + 2 TARGET_REACHED; 10 INVALIDATED = 9 PRIMARY entries stopped + 1 NO_ENTRY | — |

Exact sums of the STORED normalized one-unit price-net values (not an account return; funding not covered). They are unchanged by this correction and identical to the app report's `periods.total`:

| Variant | Population | Sum (exact) |
|---|---|---|
| PRIMARY | 12 CLOSED of 13 (9 STOP, 2 TARGET, 1 TIME_EXPIRED; 1 NO_ENTRY) | −0.0172669915495620322520588143828262568475328858467215 |
| ENTRY_DELAY_0 | 13 CLOSED | −0.0189589082307479951689262847541956376482915259832091 |
| ENTRY_DELAY_120 | 11 CLOSED (2 NO_ENTRY) | −0.0161862340579918341860714785673331875991564897959369 |
| HORIZON_ONLY | 12 CLOSED (1 NO_ENTRY) | −0.02674259455689570963913479282769230277377470143260080 |

## The 13 calls (chronological)

**Levels.**
- **V structural:** the confirmed scenario's frozen V, unrounded.
- **V_op:** the operational guidance V, derived from it and tick-rounded away from the entry.

**Distances.**
- Every distance to V uses **V_op**, signed toward the call direction, in bps of the reference price: the stored confirmation close, the stored issue close, or the stored **modeled PRIMARY entry open** (not a close).
- "Return vs conf. close" is `d·(issue close − confirmation close)/S15_confirmation`; a negative value means the price came back against the direction.

**Terminal times.**
- **Contact bar:** the certified 1m bar named in the terminal reason.
- **Published:** the journal publication of the terminal.
- The instant inside the bar is UNAVAILABLE.

Full linked sequences: [call_timeline.csv](call_timeline.csv); every field: [calls.csv](calls.csv) and `dossier.json`.

| # | Call (issue UTC) | Dir/mode | Confirm → issue (min) | V structural / V_op | Close→V_op / →T at confirm (bps) | Close→V_op / →T at issue (bps) | Return vs conf. close (S15) | Pre-issue class | PRIMARY entry open: +min (rejected opens); open→V_op bps | Guidance terminal: contact bar → published | Scenario terminal | PRIMARY exit | Price-net |
|---:|---|---|---:|---|---|---|---:|---|---|---|---|---|---:|
| 1 | 09-03 16:26 | LONG RETURN | 49 | 111826.055 / 111826.0 | -30.93 / +23.57 | -8.12 / +46.51 | -0.89 | NONE_RECORDED_H2_CONSISTENT | +2 (1); -9.07 | INVALIDATED 16:43–16:44 bar → 16:44 | INVALIDATED | STOP fill 16:43, held 15 min | -0.231% |
| 2 | 09-13 18:16 | SHORT RETURN | 13 | 115573.9 / 115573.9 | -9.99 / +31.60 | -4.67 / +36.89 | -0.34 | NONE_RECORDED_H2_CONSISTENT | +8 (7); -4.79 | INVALIDATED 18:27–18:28 bar → 18:28 | INVALIDATED | STOP fill 18:27, held 3 min | -0.188% |
| 3 | 09-26 00:52 | SHORT RETURN | 20 | 109382.96 / 109383.0 | -19.69 / +41.41 | -5.31 / +55.70 | -0.59 | NONE_RECORDED_H2_CONSISTENT | NO_ENTRY (CALL_TERMINAL_BEFORE_QUALIFYING_OPEN; first boundary 00:53) | INVALIDATED 00:52–00:53 bar → 00:53 | INVALIDATED | — | — |
| 4 | 10-06 18:26 | LONG RETURN | 10 | 124966.465 / 124966.4 | -26.06 / +37.52 | -13.60 / +50.06 | -0.38 | NONE_RECORDED_H2_CONSISTENT | +1 (0); -11.85 | TARGET_REACHED 18:50–18:51 bar → 18:51 | DESTINATION_REACHED | TARGET fill 18:50, held 23 min | +0.378% |
| 5 | 10-19 20:13 | LONG RETURN | 5 | 108723.155 / 108723.1 | -18.80 / +39.37 | -11.83 / +46.38 | -0.34 | NONE_RECORDED_H2_CONSISTENT | +1 (0); -9.83 | INVALIDATED 21:12–21:13 bar → 21:13 | INVALIDATED | STOP fill 21:12, held 58 min | -0.238% |
| 6 | 10-26 23:34 | LONG IMMEDIATE | 0 | 114309.58 / 114309.5 | -25.34 / +99.42 | -25.34 / +99.42 | 0.00 | NOT_APPLICABLE_IMMEDIATE | +1 (0); -27.39 | TIME_EXPIRED → 03:34 | TIME_EXPIRED | GUIDANCE_TIME_EXPIRED fill 03:35, held 240 min | +0.101% |
| 7 | 10-31 03:32 | LONG RETURN | 24 | 108464.61 / 108464.6 | -50.49 / +85.57 | -37.59 / +98.64 | -0.38 | NONE_RECORDED_H2_CONSISTENT | +1 (0); -37.87 | TARGET_REACHED 04:40–04:41 bar → 04:41 | DESTINATION_REACHED | TARGET fill 04:40, held 67 min | +0.843% |
| 8 | 11-17 21:44 | SHORT RETURN | 26 | 92278.475 / 92278.5 | -47.36 / +58.08 | -26.89 / +78.33 | -0.36 | NONE_RECORDED_H2_CONSISTENT | +24 (23); -32.85 | INVALIDATED 22:42–22:43 bar → 22:43 | INVALIDATED | STOP fill 22:42, held 34 min | -0.469% |
| 9 | 11-23 06:18 | LONG RETURN | 23 | 85912.005 / 85912.0 | -37.43 / +64.37 | -32.02 / +69.84 | -0.15 | NONE_RECORDED_H2_CONSISTENT | +1 (0); -27.87 | INVALIDATED 06:51–06:52 bar → 06:52 | INVALIDATED | STOP fill 06:51, held 32 min | -0.418% |
| 10 | 12-01 17:08 | SHORT RETURN | 13 | 85463.99 / 85464.0 | -114.23 / +79.74 | -61.94 / +131.03 | -0.84 | NONE_RECORDED_H2_CONSISTENT | +1 (0); -64.39 | INVALIDATED 18:14–18:15 bar → 18:15 | INVALIDATED | STOP fill 18:14, held 65 min | -0.784% |
| 11 | 12-05 11:07 | SHORT RETURN | 7 | 91468.96 / 91469.0 | -25.68 / +25.75 | -8.07 / +43.26 | -0.76 | NONE_RECORDED_H2_CONSISTENT | +1 (0); -4.30 | INVALIDATED 11:08–11:09 bar → 11:09 | INVALIDATED | STOP fill 11:08, held 0 min | -0.183% |
| 12 | 12-19 19:16 | SHORT RETURN | 36 | 87492.255 / 87492.3 | -54.04 / +15.57 | -17.08 / +52.28 | -0.60 | NONE_RECORDED_H2_CONSISTENT | +2 (1); -17.05 | INVALIDATED 19:19–19:20 bar → 19:20 | INVALIDATED | STOP fill 19:19, held 1 min | -0.311% |
| 13 | 12-25 16:38 | LONG RETURN | 11 | 88113.96 / 88113.9 | -34.17 / +16.77 | -6.31 / +44.74 | -2.06 | OBSTACLE_ONLY | +1 (0); -8.64 | INVALIDATED 16:50–16:51 bar → 16:51 | INVALIDATED | STOP fill 16:50, held 11 min | -0.226% |

### Facts from these rows (STORED / DERIVED)

**Lineage.**
- Every call is an A call, with one structural scenario/owner, one entry attempt and one call.
- 12 of 13 scenarios lost and replaced their local anchor before confirmation, at anchor epochs 2–4; #13 is at epoch 1.
- By rule (MP-002 §3), R/K/V never change after confirmation.

**Targets and B.** Every call target is a LANDMARK (LANDMARK_CAP for #13), strictly nearer than the scenario destination B.

**V and terminals.**
- The operational V is the structural V tick-rounded away from the entry.
- In all 10 invalidated RETURN calls, the guidance (on V_op) and the scenario (on its structural V) are ended by the **same certified contact bar** and published in the same dispatch.
- In the 2 target calls, the scenario also reached destination B.
- #6 (IMMEDIATE) ran to the hard deadline, for both the guidance and the scenario.

**Confirmation → issue.**
- WAITs lasted 5–49 min (median 16.5), with 2–16 blocker updates. The blockers were mostly `REWARD_RISK_BELOW_MINIMUM`, `CLOSE_OUTSIDE_RETURN_CORRIDOR` and `NO_ROOM_AFTER_COSTS`.
- Residual time to the hard deadline at issue was 191–235 min.
- Every RETURN issue followed a `RETURN_USABLE` close.

**Context and phase at issue are published categories.**
- The context category at issue equals the one at confirmation for all 13 calls (UP for LONG, DOWN for SHORT).
- The last context publication is often hours before the issue (e.g. #1: published 14:00, issue 16:26). Its category persists; its attached values are as of 14:00, not a certainly current snapshot.
- The phase is never an opposite expansion.

**Geometry at issue.**
- By construction of RETURN, the issue close lies in the fixed R–K corridor, nearer V_op than the confirmation close.
- Return depth against the direction: 0.15–2.06 S15 (median 0.48).
- Issue close → V_op: 4.67–61.94 bps (median 12.7).
- Issue close → T: 36.9–131.0 bps (median 51.2).
- These equal the stored `risk_bps`/`gain_bps` at the 0.01 bps presentation.

**Entry.**
- The first PRIMARY candidate boundary is `ceil(issue + 60 s)`, which is issue + 1 min here.
- 9 entered at +1–2 min; #2 at +8 (7 rejected opens); #8 at +24 (23 rejected opens).
- In 10 of 12 RETURN calls, the first entry-status revision closed *new* entry 1–9 min after issue while the thesis was ongoing; some reopened. In #3 and #11 the first revision was the V terminal. This status does not change the PRIMARY path, which enters on the first admissible open.

**#3 (no PRIMARY entry).**
- Issued 00:52.
- The certified V contact is in the bar **00:52–00:53**; the guidance and scenario terminals were **published 00:53**.
- The PRIMARY first candidate boundary, 00:53, therefore met a terminal call: `CALL_TERMINAL_BEFORE_QUALIFYING_OPEN`.
- The zero-delay path records its entry and its stop in that bar starting 00:52.
- The 120 s path and the horizon-only baseline have no entry.

**Outcome.**
- 9 STOP (modeled stop fills held 0–65 min), 2 TARGET (23 and 67 min) and 1 TIME_EXPIRED (IMMEDIATE, +0.101%).
- The 9 stopped PRIMARY entries opened 4.30–64.39 bps from V_op (STORED modeled open; DERIVED distance).

## H1 and H2 (same criteria for every case)

**Observation limits.**
- S1–S6 count **published occurrences**, not every possible change of state.
- S1 is a landmark break, S2 an opposite-direction scenario transition and S3 counterevidence of the aggregate MarketView; none is automatically specific to the call.
- The absence of S5/S6 in issued calls is **expected from the gates** (A withdrawal on forbidden context or opposite expansion). It is not an independent verification of the quality of the selection.

| Pre-issue class | Calls | Guidance terminals |
|---|---|---|
| NONE_RECORDED_H2_CONSISTENT | #1–5, #7–12 (11) | 9 INVALIDATED, 2 TARGET_REACHED |
| OBSTACLE_ONLY (S4) | #13 | INVALIDATED |
| NOT_APPLICABLE_IMMEDIATE | #6 | TIME_EXPIRED |
| H1_RECORDED / INDETERMINATE | none (context and phase categories known at every issue) | — |

**Summary statement.** All 12 RETURN calls reach the economic region with no recorded occurrence of the directional H1 criteria. Eleven satisfy the H2 class; #13 instead has S4 and is classified OBSTACLE_ONLY. For #13 the cap moved 88564.3 → 88564.0 (a new 15m pivot zone). That is a constraint on the target, not evidence of directional deterioration, nor a cause of the stop.

**No occurrences found.** Non sono state trovate occorrenze S1/S2/S3/S5/S6 nelle finestre esaminate. Questo non certifica l’assenza di ogni cambiamento avverso né la coerenza complessiva della tesi.

- **Pre-entry window:** no occurrence.
- **Hold window (descriptive only):** one opposite-expansion publication for #5. No other S1–S6 occurrence before the guidance terminals.

**Same criteria on the 57 WAITs** (window up to the entry end):

| WAIT class | Count | Window classes |
|---|---:|---|
| ISSUED | 12 | 11 NONE_RECORDED_H2_CONSISTENT, 1 OBSTACLE_ONLY |
| Ended without a usable return | 45 | 35 NONE_RECORDED, 6 OBSTACLE_ONLY, 4 H1_RECORDED (S6: context published BALANCED → `CONTEXT_FORBIDDEN_PREISSUE`) |

Endings of the 45 WAITs:
- 17 `SCENARIO_TERMINAL`, each in the same dispatch as the scenario terminal;
- 16 `PRE_ENTRY_TARGET_CONTACT`;
- 8 `ORIGINAL_SETUP_DEADLINE`;
- 4 `CONTEXT_FORBIDDEN_PREISSUE`.

Their scenarios ended: 34 DESTINATION_REACHED, 5 INVALIDATED, 3 STALLED and 3 TIME_EXPIRED. These WAITs never entered and have no path, so they are **not** controls for the entered calls.

### What the records support
- **The economic region was reached without directional H1 occurrences.** All 12 RETURN calls reached it without a recorded occurrence of the directional H1 criteria; 11 are in the H2 class and #13 is OBSTACLE_ONLY.
- **The negative result concentrates on the frozen V.** In the 10 invalidated RETURN calls, guidance and scenario end on the same certified contact bar. 9 had entered PRIMARY and were stopped; #3 had no entry.
- **The issue close is near V_op by construction of the RETURN container.** The corridor lies between K and R, with V just beyond R. The adverse return that creates the economic region is the price movement that brings the price near V.

### What the records contradict
- **H1 as published evidence.** No S1/S2/S3/S5/S6 occurrence precedes any issue, within the limits above.
- **Issuing against a published veto.** No call was issued against a published forbidden context or opposite expansion. The 4 context-withdrawn WAITs show the gate operating; as stated, this is not an independent check of selection quality.

### What the records cannot decide
- **Whether the adverse return was itself real deterioration.** Unpublished value changes, lower-timeframe structure, intrabar sequence, quotes and news are UNAVAILABLE.
- **Generalizable differences or causes.** Il campione è ridotto e selezionato; questa analisi descrittiva non stima affidabilmente differenze generalizzabili per classe, distanza o timing e non identifica effetti causali. Non conclude equivalenza al caso.
- **Whether another entry container, stop placement or timing would have changed outcomes.** That is counterfactual and excluded.
- **Whether the WAITs without return describe the same population.** They are not comparable.

## Verification

**Executor checks (this correction; product suites, E2E and Compose not run).**
- **Probe:** the synthetic probe (`--selfcheck`) checks that missing phase, no observations, or an UNAVAILABLE context give INDETERMINATE, and that a full case gives H2. The reviewed `e07bbe0` script returned H2 for the missing cases (fail-before); the corrected script passes.
- **Invariance:** call classes are unchanged (#13 OBSTACLE_ONLY, #6 IMMEDIATE, 11 H2), and so are the WAIT classes, all counts and the exact sums.
- **Reconciliation:** 12 = 10 + 2 and 10 = 9 + 1 are checked in `dossier.json`.
- **Renamed field:** the PRIMARY entry distance values are unchanged; the field is renamed `primary_entry_open_to_V_operational_bps`.
- **Reproducibility:** two regenerations from the same local exports are byte-identical.

**Not independently verified.** These are executor checks; Astra's independent verification is separate and not claimed here.

## Files

| File | Content |
|---|---|
| [DEFINITIONS.md](DEFINITIONS.md) | evidence types, observation limits, windows, classes, levels/times, procedure provenance, erratum |
| [dossier.json](dossier.json) | provenance, pins, chains, reconciliation (incl. RETURN outcome identities), totals, tabulations, `levels_and_times`, `observation_limits`, every call/WAIT row, per-call evidence |
| [calls.csv](calls.csv) | 13 calls: lineage; V structural/operational; confirmation/issue geometry and timing; published categories with timestamps; evidence counts; entry (modeled open); terminal contact bar and publication; all variants |
| [waits.csv](waits.csv) | 57 WAITs: geometry, blockers, cap revisions, returns, ending, concurrent scenario terminal, evidence counts, observation availability |
| [call_timeline.csv](call_timeline.csv) | linked chronological records for every call |
| [export.sql](export.sql) · [extract_continuous_diagnosis.py](extract_continuous_diagnosis.py) | the single read-only extraction and the offline script (`uv run python extract_continuous_diagnosis.py <export_dir> <out_dir>`; `--selfcheck` for the probe) |

**Limits.**
- Descriptive development evidence on exposed data (Sep–Dec 2025); January–August 2026 is untouched except the authorized tail.
- No proposal of rules or parameters.
- Remote CI: PENDING / NOT CHECKED, Owner-operated.
