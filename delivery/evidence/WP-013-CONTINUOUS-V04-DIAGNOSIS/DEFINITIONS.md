# Continuous v0.4 diagnosis — evidence definitions (registered before the outcome analysis)

Run: evaluation `eval-20261007T182934-3f41ad`, replay `obs-20261007T182934-f8c3d4`, build `97a2a8c`, pack `pack-1ae7d36c20adbde0a468a7e0f6d8750a9951aa8e`.

This file was written after inspecting the record *schema* (field names and transition vocabularies), and before any call or WAIT outcome was joined to the evidence. The script computes the evidence table in a function that receives no path, guidance-terminal or scenario-terminal data. The outcomes are joined afterwards, only for presentation.

No threshold is chosen here. Every criterion is the presence of a record the method already writes, with its own stored semantics.

## Questions

- **H1 — structural deterioration already observable before the issue.** Between the structural confirmation and the issue, the journal records structural evidence that is adverse to the call direction.
- **H2 — the economic region was reached without further recorded deterioration.** The issue followed a usable return into the fixed corridor (`RETURN_USABLE` → `ISSUE`), and none of the H1 evidence types was recorded in the same window.

These are diagnostic labels, not causal conclusions. They are not necessarily exclusive. The absence of a record does not prove the absence of real deterioration.

## Windows (journal order, not wall-clock guesses)

The journal is totally ordered by `seq`, so a record is known before the issue if its `seq` is lower than the `seq` of the `ISSUE` entry-attempt record. This includes the records of the same dispatch that the method processes before selection (MP-002 §6, collision precedence).

| Window | Definition |
|---|---|
| W_pre (H1/H2) | `seq` strictly after the scenario's `CONFIRM` record and strictly before the `ISSUE` record of the same entry attempt |
| W_wait (WAITs without issue) | `seq` strictly after `CONFIRM` and up to and including the entry-attempt terminal record (`TERMINAL` / `REJECT`) |
| W_entry (descriptive only) | after `ISSUE` up to the PRIMARY modeled entry minute start; post-issue, never used to classify H1 |
| W_hold (descriptive only) | after the PRIMARY entry up to the guidance terminal record |

For an IMMEDIATE call, confirmation and issue occur in the same dispatch and W_pre is empty. The H1/H2 question about a wait does not apply. Its state at confirmation is reported with the same fields.

## Structural evidence types (applied identically to every call and WAIT)

`d` is the candidate direction (LONG/SHORT); "opposite" is the other direction.

| Code | Record and field | Counts when, inside the window |
|---|---|---|
| S1 ADVERSE_LANDMARK_BREAK | `landmark` record with `status = BROKEN` | the broken level is a support for LONG (`side = LOW`) or a resistance for SHORT (`side = HIGH`). The horizon (15m/1h/1d/1w/1mo) is reported, not weighted. |
| S2 OPPOSING_SCENARIO_ACTIVATION | `scenario` record of the opposite direction, any family | `transition ∈ {ARM, REARM, REVISE, CONFIRM}` |
| S3 VIEW_COUNTEREVIDENCE | `market_view` record | `counterevidence` non-empty, or `expected_direction` equal to the opposite direction |
| S4 NEW_OPPOSING_OBSTACLE | `entry_attempt` record of this attempt | `transition = CAP_REVISION` (a newly eligible opposing zone lowers the target cap, MP-002 §6). Reported separately as room/obstacle evidence, not as directional deterioration. |
| S5 OPPOSITE_EXPANSION | `observation` record `name = phase` | `category = EXPANSION` with `values.expansion_direction` opposite to `d` |
| S6 CONTEXT_NOT_ALIGNED | `observation` record `name = context` | `category` ≠ the A-aligned context (UP for LONG, DOWN for SHORT); `UNAVAILABLE` is counted as a coverage limit, not as deterioration |

Classification of the pre-issue window (one label per call, the same rule for every call):

- **H1_RECORDED** — at least one of S1, S2, S3, S5, S6 in W_pre.
- **OBSTACLE_ONLY** — none of those, but at least one S4.
- **NONE_RECORDED (H2-consistent)** — none of S1–S6 in W_pre, and the issue followed `RETURN_USABLE`.
- **NOT_APPLICABLE_IMMEDIATE** — W_pre empty (IMMEDIATE).
- **INDETERMINATE** — the window contains a context or phase `UNAVAILABLE` record, or a required record is missing.

By construction of the method (MP-001 §5/§6, MP-002 §6), an A attempt is withdrawn before issue by a forbidden context or an opposite expansion. S5 and S6 are therefore expected to be absent at issue time for issued calls. They are kept so that the same criteria apply to WAITs, and so that a violation would be visible.

## Descriptive measures (no thresholds)

All of these are STORED or DERIVED (exact Decimal) from fields known at the stated cutoff:
- **At confirmation:** confirmation close, R, K_trigger, V, T_confirm, corridor, economic region at the initial cutoff, S15, setup expiry, hard deadline.
- **At issue:** issue reference close, V, T, structural area, admissible bounds, stored gain/risk bps, cap history, and the time elapsed since confirmation and remaining to the hard deadline.
- **Distances:** signed distances from the reference close to V and to the target, in bps of that close: `10000·d·(x − close)/close`.
- **Entry:** the first candidate boundary `ceil_minute(issue + 60 s)`, the entry-status revisions with their reasons, the PRIMARY entry minute, attempts and rejected opens, and the stored NO_ENTRY class.

Later prices are used only to describe outcomes, through the stored path (entry, exit, MFE/MAE). They never define an earlier observable signal.

## Labels

- **STORED** — a committed journal or evaluation field.
- **DERIVED** — exact arithmetic on STORED fields.
- **UNAVAILABLE** — not recorded, and not reconstructible without a replay or counterfactual. Each one is named per field.

## Erratum — window end within a dispatch (recorded after the first extraction run)

**What the first run assumed.** The first full run used a strict `seq < ISSUE` window. Its output already contained the joined outcomes.

**What the journal actually does.** Inspecting the journal's write order inside one dispatch (same clock time) shows that records are written in this order: landmark, scenario, entry_attempt, call, market_view, material_change, observation. The method computes context and phase *first* (MP-001 dispatch order: update context/phase/landmarks, then triggers, then selection/issue, then view publication), but journals them *last*. The visible symptom: 4 WAITs ended with `CONTEXT_FORBIDDEN_PREISSUE`, yet the context record that caused the withdrawal was outside the strict window.

**Amendment.** The window end now also includes the `observation` records of the decision's own dispatch, for calls and WAITs alike. Two things are left unchanged:
- landmarks are already journaled before the decision;
- the dispatch's `market_view` is published after selection and stays excluded.

This amendment follows from the journal's write order and the method's stated dispatch order, not from outcomes.

**What changed.** Both variants are reported: `classification` (amended) and `classification_strict_seq`. For the 13 calls the two are identical. Only those 4 context-withdrawn WAITs change, from NONE_RECORDED to H1_RECORDED (S6).
