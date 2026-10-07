# Continuous v0.4 diagnosis — evidence definitions (initial definitions before joining outcomes; cutoff amended afterwards)

Run: evaluation `eval-20261007T182934-3f41ad`, replay `obs-20261007T182934-f8c3d4`, build `97a2a8c`, pack `pack-1ae7d36c20adbde0a468a7e0f6d8750a9951aa8e`.

## How the procedure evolved (not entirely ex ante)

1. **Initial definitions, before outcomes.** The evidence types, windows and classes below were written after inspecting the record *schema* only (field names and transition vocabularies), before any call or WAIT outcome was joined. The script computes the evidence in functions that receive no path, guidance-terminal or scenario-terminal data. Outcomes are joined afterwards, for presentation.
2. **Cutoff amended afterwards.** The window end was amended after a first output that was already joined to the outcomes (see the erratum). Context and phase are computed before the decision but journaled after it, so the observations of the decision's own dispatch are now included. The MarketView of that dispatch is published after selection and stays excluded.
3. **Correction pass after the Astra review of `e07bbe0`.** This pass changed presentation and alignment only:
   - `classify()` now gives INDETERMINATE when a required observation is missing, as defined below;
   - the observation limits are stated explicitly;
   - levels, prices and times are made explicit.

   No evidence type, window or class was redefined after the outcomes, and every classification is unchanged.

No threshold is chosen. Every criterion is the presence of a record the method already writes, with its own stored semantics.

## Questions

- **H1 — structural deterioration already observable before the issue.** Between the structural confirmation and the issue, the journal records a published occurrence of a directional H1 criterion (S1, S2, S3, S5 or S6) adverse to the call direction.
- **H2 — the economic region was reached without further recorded deterioration.** The issue followed a usable return into the fixed corridor (`RETURN_USABLE` → `ISSUE`), and none of S1–S6 was recorded in the same window.

These are diagnostic labels, not causal conclusions, and not necessarily exclusive. The absence of a record does not prove the absence of real deterioration.

## Observation limits

**Occurrences, not states.** S1–S6 count **published occurrences**, not every possible change of state. A landmark, scenario, view or observation record exists only when the method publishes one.

**Categories persist; values do not stay current.**
- An observation's **category** persists until the next publication of that observation.
- The **values** attached to the last publication are as of its `published_at`.
- The publisher may not emit a new record when a value changes but the category does not.

So previously published values are never treated as a numeric snapshot certainly current at the decision. The dossier reports, for each decision, the category, its `published_at` and the values as published.

**No automatic call relevance.**
- S1 is a **landmark break**.
- S2 is an **opposite-direction scenario transition**.
- S3 is **counterevidence of the aggregate MarketView**.

None of them is automatically specific to the call: they are reported, not weighted.

**S5/S6 are not an independent check.** By construction (MP-001 §5/§6, MP-002 §6), an A attempt is withdrawn before issue by a forbidden context or an opposite expansion, so the absence of S5/S6 in issued calls is **expected from the gates**. It is not an independent verification of selection quality. S5/S6 are kept so that the same criteria apply to WAITs and a violation would be visible.

## Windows (journal order, not wall-clock guesses)

The journal is totally ordered by `seq`. Inside one dispatch (same clock time) records are journaled in this order: landmark, scenario, entry_attempt, call, market_view, material_change, observation.

| Window | Definition |
|---|---|
| W_pre (H1/H2) | `seq` strictly after the scenario's `CONFIRM` and strictly before the `ISSUE` of the same entry attempt, plus the `observation` records of the ISSUE dispatch (erratum) |
| W_wait (WAITs) | `seq` strictly after `CONFIRM` up to and including the entry-attempt end record, plus the `observation` records of that end dispatch |
| W_entry (descriptive only) | after `ISSUE` up to the PRIMARY modeled entry minute start; post-issue, never used to classify H1 |
| W_hold (descriptive only) | after the PRIMARY entry up to the guidance terminal record |

For an IMMEDIATE call, confirmation and issue occur in the same dispatch and W_pre is empty. The H1/H2 question about a wait does not apply.

## Evidence types (applied identically to every call and WAIT)

`d` is the candidate direction (LONG/SHORT); "opposite" is the other direction.

| Code | Record and field | Counts a published occurrence when, inside the window |
|---|---|---|
| S1 landmark break | `landmark` record with `status = BROKEN` | the broken level is a support for LONG (`side = LOW`) or a resistance for SHORT (`side = HIGH`); horizon reported, not weighted |
| S2 opposite scenario transition | `scenario` record of the opposite direction, any family | `transition ∈ {ARM, REARM, REVISE, CONFIRM}` |
| S3 aggregate-view counterevidence | `market_view` record | `counterevidence` non-empty, or `expected_direction` equal to the opposite direction |
| S4 new obstacle | `entry_attempt` record of this attempt | `transition = CAP_REVISION`: a newly eligible opposing zone lowers the target cap (MP-002 §6). A target constraint, not directional deterioration. |
| S5 opposite expansion | `observation` `name = phase` | `category = EXPANSION` with `values.expansion_direction` opposite to `d` |
| S6 context not aligned | `observation` `name = context` | `category` ≠ the A-aligned context (UP for LONG, DOWN for SHORT); `UNAVAILABLE` is a coverage limit, not deterioration |

## Classification (one label per call or WAIT; the same rule for all)

- **NOT_APPLICABLE_IMMEDIATE** — W_pre empty (IMMEDIATE).
- **INDETERMINATE** — a required observation is missing: an `UNAVAILABLE` context or phase publication inside the window, or no known (published, not UNAVAILABLE) context **and** phase category at the decision. This class takes precedence; a missing observation is never classified as H2.
- **H1_RECORDED** — at least one directional criterion (S1, S2, S3, S5, S6) in the window.
- **OBSTACLE_ONLY** — none of those, but at least one S4.
- **NONE_RECORDED_H2_CONSISTENT** — none of S1–S6, the required observations known, and the issue followed `RETURN_USABLE`. A WAIT without a usable return is labelled `NONE_RECORDED`.

## Levels, prices and times

- **V_structural_scenario.** The confirmed scenario's frozen V (`invalidation_level` of the scenario CONFIRM, unrounded, e.g. `109382.96`).
- **V_operational_tick.** The call/guidance V, derived from the structural V and tick-rounded away from the entry (call `invalidation`, also the WAIT geometry V, e.g. `109383.0`).
- **Distances.** Signed toward the call direction, `10000·d·(x − ref)/ref`, in bps of the reference price `ref`. Every `*_to_V*` distance uses **V_operational_tick**. The references are:
  - `conf_close_*`: the stored confirmation close;
  - `issue_close_*`: the stored issue reference close;
  - `primary_entry_open_*`: the stored modeled PRIMARY entry **open** (not a close).
- **Terminal times.**
  - `*_published_at`: the journal publication of the terminal record.
  - `*_contact_bar_start/_end`: the certified 1m contact bar named in the terminal reason.
  - The instant inside that bar is **UNAVAILABLE**.
- **Path times.** The evaluator's modeled fills (`time_start`/`time_end`).
- **Entry.** The first candidate boundary is `ceil_minute(issue + 60 s)`; the entry-status revisions and reasons, the PRIMARY entry open, attempts, rejected opens and the stored NO_ENTRY class are reported.

Later prices are used only to describe outcomes, through the stored path (entry, exit, MFE/MAE). They never define an earlier observable signal.

## Labels

- **STORED** — a committed journal or evaluation field.
- **DERIVED** — exact arithmetic on STORED fields.
- **UNAVAILABLE** — not recorded, and not reconstructible without a replay or counterfactual. Each one is named per field.

## Erratum — window end within a dispatch (recorded after the first extraction run)

**What the first run assumed.** The first full run used a strict `seq < ISSUE` window. Its output already contained the joined outcomes.

**Why that was wrong.** The journal's write order inside one dispatch puts context and phase observations *last*, although the method computes them *first* (MP-001 dispatch order: update context/phase/landmarks, then triggers, then selection/issue, then view publication). The visible symptom: 4 WAITs ended with `CONTEXT_FORBIDDEN_PREISSUE`, yet the context record that caused the withdrawal was outside the strict window.

**Amendment.** The window end includes the `observation` records of the decision's own dispatch, for calls and WAITs alike. Landmarks are already journaled before the decision. The dispatch's `market_view` is published after selection and stays excluded. The amendment follows from the journal's write order and the method's stated dispatch order, not from outcomes.

**What changed.** Both variants are reported: `classification` (amended) and `classification_strict_seq`. For the 13 calls the two are identical. Only the 4 context-withdrawn WAITs change, from NONE_RECORDED to H1_RECORDED (S6).
