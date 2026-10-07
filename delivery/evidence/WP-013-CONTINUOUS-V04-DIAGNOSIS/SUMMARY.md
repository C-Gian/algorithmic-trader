# Continuous v0.4 diagnosis — confirmation → WAIT → issue → entry → outcome

READY FOR DIRECTOR REVIEW — CONTINUOUS V0.4 DIAGNOSIS ONLY. This is descriptive development evidence. It does not propose or authorize any change to rules, parameters, thresholds or infrastructure.

**Director acceptance recorded:** “Prova continua accettata come evidenza descrittiva di sviluppo; risultato negativo; causa non identificata; nessuna modifica metodologica autorizzata.”

| Item | Value |
|---|---|
| Evaluation / replay | `eval-20261007T182934-3f41ad` / `obs-20261007T182934-f8c3d4` |
| Build | `97a2a8c` (every journal record carries `97a2a8ceb81a…+image`) |
| Method | v0.4 `mp003.rules.v0.4`; rules `316629a4…`, register `5873cb10…`, identity `01d2cc94…`; evaluator v3, PRIMARY delay 60 s |
| Pack / cache | `pack-1ae7d36c…` (manifest `1bec1f15…`), cache `fc-80221b24…` (manifest `95478a50…`, 679,335 events). The evaluation pins this cache, and its manifest equals the pack's pin. |
| Windows | initialization 2025-07-28 → 09-01 (not evaluated); evaluation 2025-09-01 → 2026-01-01; tail to 01-01 06:05 |
| Integrity | Journal 34,682 rows and evaluation records 2,980 rows: digests and chains recomputed, matching the finish commitment (heads `926bf6f9…` / `4e1a6ac5…`). Assurance PASSED 21/21. |

## Access and labels

**Evidence used.**
1. The app's own report export (read-only GET), first.
2. Because the report has no per-record linkage, the **single authorized extraction**: one `REPEATABLE READ READ ONLY` psql transaction ([export.sql](export.sql)), limited to this run's rows, at snapshot `841063:841063:`.

**Not used.** No feed cache was copied: every distance uses closes stored in the journal, and outcomes use the stored paths. There was no write to the Owner DB, no stack change, no replay, no Deep validation and no counterfactual.

**Labels.**
- **STORED:** journal and evaluation fields.
- **DERIVED:** exact Decimal arithmetic on them.
- **UNAVAILABLE:** intrabar order, historical quotes, news/calendar, and any structure the method does not journal.

**Reproducibility.** Two runs of [extract_continuous_diagnosis.py](extract_continuous_diagnosis.py) on the same export produce byte-identical `dossier.json` and CSVs. The input `snapshot.jsonl` is not committed; its SHA-256 is in the dossier.

**Evidence definitions.** These were registered in [DEFINITIONS.md](DEFINITIONS.md) before the outcome analysis, from existing fields only and without thresholds. They apply identically to all 13 calls (target calls and the IMMEDIATE call included) and to all 57 WAITs.
- **One erratum.** The journal writes context/phase observations *after* the decision records of the same dispatch, although the method computes them first, so the window now includes them.
- **Both variants are reported.** Calls: identical under both. WAITs: only the 4 context-withdrawn WAITs change.

## Reconciliation with the report (all match)

| Quantity | Director | Extracted / report builder | App export |
|---|---:|---:|---|
| A confirmations | 89 | 89 | funnel identical |
| WAITs opened | 57 | 57 (`WAIT_OPEN` in window) | identical |
| Calls | 13 | 13 | identical |
| RETURN calls / entered PRIMARY | 12 / 11 | 12 / 11 | — |
| Terminal path records | 52 | 52 (13 × 4; periods COMPLETE; 0 extraneous; 0 duplicates) | periods identical |

Exact sums of the STORED normalized one-unit price-net values (not an account return; funding not covered):

| Variant | Population | Sum (exact) |
|---|---|---|
| PRIMARY | 12 CLOSED of 13 (9 STOP, 2 TARGET, 1 TIME_EXPIRED; 1 NO_ENTRY) | −0.0172669915495620322520588143828262568475328858467215 |
| ENTRY_DELAY_0 | 13 CLOSED | −0.0189589082307479951689262847541956376482915259832091 |
| ENTRY_DELAY_120 | 11 CLOSED (2 NO_ENTRY) | −0.0161862340579918341860714785673331875991564897959369 |
| HORIZON_ONLY | 12 CLOSED (1 NO_ENTRY) | −0.02674259455689570963913479282769230277377470143260080 |

These are identical to the app report's `periods.total`.

## The 13 calls (chronological)

Distances are signed toward the call direction, in bps of the reference close (DERIVED). "Return vs conf. close" is `d·(issue close − confirmation close)/S15_confirmation`; a negative value means the price came back against the call direction. The full linked sequence for every call (scenario, anchors, confirmation, WAIT records, call, revisions, evidence, paths) is in [call_timeline.csv](call_timeline.csv); every field is in [calls.csv](calls.csv) and `dossier.json`.

| # | Call (issue UTC) | Dir/mode | Confirm → issue (min) | Close→V / →T at confirm (bps) | Close→V / →T at issue (bps) | Return vs conf. close (S15) | Pre-issue class | PRIMARY entry (+min; rejected opens) | Guidance / scenario terminal | PRIMARY exit | Price-net |
|---:|---|---|---:|---|---|---:|---|---|---|---|---:|
| 1 | 09-03 16:26 | LONG RETURN | 49 | -30.93 / +23.57 | -8.12 / +46.51 | -0.89 | NONE_RECORDED_H2_CONSISTENT | +2 (1) | INVALIDATED 16:44 / INVALIDATED | STOP held 15 min | -0.231% |
| 2 | 09-13 18:16 | SHORT RETURN | 13 | -9.99 / +31.60 | -4.67 / +36.89 | -0.34 | NONE_RECORDED_H2_CONSISTENT | +8 (7) | INVALIDATED 18:28 / INVALIDATED | STOP held 3 min | -0.188% |
| 3 | 09-26 00:52 | SHORT RETURN | 20 | -19.69 / +41.41 | -5.31 / +55.70 | -0.59 | NONE_RECORDED_H2_CONSISTENT | NO_ENTRY (CALL_TERMINAL_BEFORE_QUALIFYING_OPEN) | INVALIDATED 00:53 / INVALIDATED | — | — |
| 4 | 10-06 18:26 | LONG RETURN | 10 | -26.06 / +37.52 | -13.60 / +50.06 | -0.38 | NONE_RECORDED_H2_CONSISTENT | +1 (0) | TARGET_REACHED 18:51 / DESTINATION_REACHED | TARGET held 23 min | +0.378% |
| 5 | 10-19 20:13 | LONG RETURN | 5 | -18.80 / +39.37 | -11.83 / +46.38 | -0.34 | NONE_RECORDED_H2_CONSISTENT | +1 (0) | INVALIDATED 21:13 / INVALIDATED | STOP held 58 min | -0.238% |
| 6 | 10-26 23:34 | LONG IMMEDIATE | 0 | -25.34 / +99.42 | -25.34 / +99.42 | 0.00 | NOT_APPLICABLE_IMMEDIATE | +1 (0) | TIME_EXPIRED 03:34 / TIME_EXPIRED | GUIDANCE_TIME_EXPIRED held 240 min | +0.101% |
| 7 | 10-31 03:32 | LONG RETURN | 24 | -50.49 / +85.57 | -37.59 / +98.64 | -0.38 | NONE_RECORDED_H2_CONSISTENT | +1 (0) | TARGET_REACHED 04:41 / DESTINATION_REACHED | TARGET held 67 min | +0.843% |
| 8 | 11-17 21:44 | SHORT RETURN | 26 | -47.36 / +58.08 | -26.89 / +78.33 | -0.36 | NONE_RECORDED_H2_CONSISTENT | +24 (23) | INVALIDATED 22:43 / INVALIDATED | STOP held 34 min | -0.469% |
| 9 | 11-23 06:18 | LONG RETURN | 23 | -37.43 / +64.37 | -32.02 / +69.84 | -0.15 | NONE_RECORDED_H2_CONSISTENT | +1 (0) | INVALIDATED 06:52 / INVALIDATED | STOP held 32 min | -0.418% |
| 10 | 12-01 17:08 | SHORT RETURN | 13 | -114.23 / +79.74 | -61.94 / +131.03 | -0.84 | NONE_RECORDED_H2_CONSISTENT | +1 (0) | INVALIDATED 18:15 / INVALIDATED | STOP held 65 min | -0.784% |
| 11 | 12-05 11:07 | SHORT RETURN | 7 | -25.68 / +25.75 | -8.07 / +43.26 | -0.76 | NONE_RECORDED_H2_CONSISTENT | +1 (0) | INVALIDATED 11:09 / INVALIDATED | STOP held 0 min | -0.183% |
| 12 | 12-19 19:16 | SHORT RETURN | 36 | -54.04 / +15.57 | -17.08 / +52.28 | -0.60 | NONE_RECORDED_H2_CONSISTENT | +2 (1) | INVALIDATED 19:20 / INVALIDATED | STOP held 1 min | -0.311% |
| 13 | 12-25 16:38 | LONG RETURN | 11 | -34.17 / +16.77 | -6.31 / +44.74 | -2.06 | OBSTACLE_ONLY (1 cap revision) | +1 (0) | INVALIDATED 16:51 / INVALIDATED | STOP held 11 min | -0.226% |

### Facts from these rows (STORED / DERIVED)

**Lineage.** Every call is an A call: one structural scenario/owner, one entry attempt and one call.
- Before confirmation, 12 of 13 scenarios had lost and replaced their local anchor at least once. They were confirmed on anchor epoch 2–4; the exception is #13, epoch 1.
- By rule (MP-002 §3), R/K/V never change after confirmation.

**Destination B, target and V are distinct.**
- Every call target is a LANDMARK (LANDMARK_CAP for #13), strictly nearer than the scenario destination B (both are in `calls.csv`).
- The call's V is the scenario's frozen V. For all 10 RETURN calls invalidated, the guidance and the scenario were invalidated by the **same certified V contact, in the same dispatch**. For the 2 target calls, the scenario also reached destination B.
- #6 (IMMEDIATE) ran to the hard deadline, for both the guidance and the scenario.

**Confirmation → issue.**
- WAITs lasted 5–49 min (median 16.5). Residual time to the hard deadline at issue was 191–235 min.
- Every RETURN issue came on a `RETURN_USABLE` close, after 2–16 blocker updates. Blockers were mostly `REWARD_RISK_BELOW_MINIMUM`, `CLOSE_OUTSIDE_RETURN_CORRIDOR` and `NO_ROOM_AFTER_COSTS`.
- Each call has a single cap. The exception is #13, where a new 15m pivot lowered the cap once (S4).

**Geometry at issue.**
- By construction of RETURN, the issue close lies in the fixed R–K corridor, nearer V than the confirmation close. This is the economic region reached by an adverse return.
- Return depth against the direction: 0.15–2.06 S15 (median 0.48).
- Distance to V at issue: 4.67–61.94 bps (median 12.7). It equals the stored `risk_bps` at the 0.01 bps presentation.
- Distance to the target at issue: 36.9–131.0 bps (median 51.2), equal to the stored `gain_bps` at the same presentation.
- At confirmation the medians were −32.6 bps to V and +38.4 bps to T.

**Entry.**
- The first PRIMARY candidate boundary was `ceil(issue + 60 s)`, which is issue + 1 minute for these minute-aligned issues.
- 9 entered at +1–2 min.
- #2 entered at +8 (7 rejected opens) and #8 at +24 (23 rejected opens). Their entry status alternated between AVAILABLE and CLOSED in the stored revisions.
- #3 has no entry: V was contacted in the minute after issue (00:53), before the first qualifying open (`CALL_TERMINAL_BEFORE_QUALIFYING_OPEN`). The 0 s sensitivity entered; the 120 s sensitivity and the horizon-only baseline had no entry.
- In 10 of 12 issued RETURN calls the first stored entry-status revision closed new entry while the thesis was ongoing, 1–9 min after issue, for `REWARD_RISK_BELOW_MINIMUM` or `PRICE_OUTSIDE_STRUCTURAL_AREA`; some reopened. In the other two (#3, #11) the first revision was the V terminal. This status concerns new entries; it does not alter the PRIMARY path, which enters on the first admissible open.

**Outcome.**
- 9 STOP. Held 0–65 min: three within 3 min (#2, #11, #12) and the others 11–65 min.
- 2 TARGET (23 and 67 min) and 1 TIME_EXPIRED (IMMEDIATE, +0.101%).

## H1 and H2 (same criteria for every case)

**Pre-issue window** (after CONFIRM up to and including the decision dispatch's factual updates; DEFINITIONS.md):

| Pre-issue class | Calls | Guidance terminals |
|---|---|---|
| NONE_RECORDED_H2_CONSISTENT | #1–5, #7–12 (11) | 9 INVALIDATED, 2 TARGET_REACHED |
| OBSTACLE_ONLY (S4) | #13 | INVALIDATED |
| NOT_APPLICABLE_IMMEDIATE | #6 | TIME_EXPIRED |
| H1_RECORDED / INDETERMINATE | none | — |

- In every call's pre-issue window there are no recorded adverse landmark breaks (S1), opposing scenario activations (S2), view counterevidence (S3), opposite expansion (S5) or non-aligned context (S6).
- The context at issue equals the context at confirmation (UP for LONG, DOWN for SHORT) for all 13.
- The phase at issue is never an opposite expansion.
- The same holds in the pre-entry windows. After entry (descriptive only), one opposite-expansion record appears for #5 during the hold. No other S1–S6 record appears up to the guidance terminals.

**Same criteria on the 57 WAITs** (W_wait = up to the entry terminal):

| WAIT class | Count | Window classes |
|---|---:|---|
| ISSUED | 12 | 11 NONE_RECORDED, 1 OBSTACLE_ONLY |
| Ended without a usable return | 45 | 35 NONE_RECORDED, 6 OBSTACLE_ONLY, 4 H1_RECORDED (S6: context became BALANCED → `CONTEXT_FORBIDDEN_PREISSUE`) |

Endings of the 45 WAITs:
- 17 `SCENARIO_TERMINAL`, every one in the same dispatch as the scenario terminal;
- 16 `PRE_ENTRY_TARGET_CONTACT`;
- 8 `ORIGINAL_SETUP_DEADLINE`;
- 4 `CONTEXT_FORBIDDEN_PREISSUE`.

Their scenarios ended: 34 DESTINATION_REACHED, 5 INVALIDATED, 3 STALLED and 3 TIME_EXPIRED. Over the 12 issued WAITs the scenarios ended 10 INVALIDATED and 2 DESTINATION_REACHED. These WAITs never entered, have different windows and have no path. They are **not** controls for the entered calls, and the contrast is not an estimate of any effect.

### What the records support
- **The H2 description fits all 12 RETURN calls.** The economic region was reached by a usable return after confirmation, with no recorded structural deterioration in the pre-issue window (11 calls). The only recorded item for #13 is one new obstacle (cap revision).
- **The negative result is concentrated in RETURN calls ending at the frozen V.** In 10 of 12 the guidance and the scenario end together on the same V contact. The 9 of them that entered sat 4.30–64.39 bps from V at the PRIMARY entry (STORED entry price; DERIVED distance); #3 never entered.
- **The issue price is structurally close to V by construction.** The corridor lies between K and R, with V just beyond R. The adverse return that creates the economic region is the same price movement that brings the price near V.

### What the records contradict
- **H1, as recorded evidence, is contradicted for these 13 calls.** None of the predefined adverse structural records (S1, S2, S3, S5, S6) precedes any issue.
- **The method did not issue against recorded forbidden context or opposite expansion.** By rule, those signals withdraw a WAIT before issue. The 4 WAITs withdrawn by context confirm the rule operated; no issued call carries such a record.

### What the records cannot decide
- **Whether the adverse return was itself real deterioration.** The return depth (0.15–2.06 S15) and the proximity to V are price facts the method does not journal as structural evidence. Lower-timeframe structure, order flow, intrabar sequence, quotes and news are UNAVAILABLE. **The absence of a recorded change does not prove the absence of deterioration.**
- **Causality.** Neither H1 nor H2 is shown to cause the outcomes. The same NONE_RECORDED class contains the 2 targets and 9 invalidations. With 12 RETURN calls, no difference by class, distance or timing can be distinguished from chance, and none is claimed.
- **Whether a different entry container, stop placement or timing would have changed outcomes.** That is counterfactual and excluded.
- **Whether the WAITs without return describe the same population.** They are not comparable, as stated above.

## Files

| File | Content |
|---|---|
| [DEFINITIONS.md](DEFINITIONS.md) | evidence types, windows, classification (registered before the outcomes), erratum |
| [dossier.json](dossier.json) | provenance, pins, chains, reconciliation, totals, tabulations, every call/WAIT row, per-call evidence records, UNAVAILABLE list |
| [calls.csv](calls.csv) | 13 calls: lineage, confirmation/issue geometry and timing, evidence counts, entry, outcomes, all variants |
| [waits.csv](waits.csv) | 57 WAITs: opening geometry, blockers, cap revisions, returns, ending, concurrent scenario terminal, evidence counts |
| [call_timeline.csv](call_timeline.csv) | linked chronological records for every call |
| [export.sql](export.sql) · [extract_continuous_diagnosis.py](extract_continuous_diagnosis.py) | the single read-only extraction and the offline script (`uv run python extract_continuous_diagnosis.py <export_dir> <out_dir>`) |

**Limits.**
- Descriptive development evidence only, on exposed development data (Sep–Dec 2025); January–August 2026 is untouched except the authorized tail.
- No proposal or implementation of rules, parameters, thresholds or infrastructure.
- Remote CI: PENDING / NOT CHECKED, Owner-operated.
