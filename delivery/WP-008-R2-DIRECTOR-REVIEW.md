# WP-008-R2 — Director review
Date: 2026-10-03
Reviewed implementation: `44ce68a62ff315d476c712aedd76bef5fd3f8d89` (base `9169096`).
Current decision: **ACCEPTED after correction at `ddc1831`** (see closure below). The initial finding and evidence below are historical. No new Owner replay is requested.

## Scope and evidence
Source review of the temporal engine/reference, streaming kernel, reconciliation and Deep validation, against WP-008-R2-CAUSAL-TEMPORAL-SPEC.md, especially §§5, 7 and evidence J.
The executor reports 431 non-E2E / 10 E2E, schema/web checks and isolated smoke. Independently checked CI run 37135564664: compose-smoke SUCCESS; web and non-E2E steps SUCCESS; checks job still running at review publication, with E2E not yet concluded. This is not a claim of a fully green final CI.
Director reproduced the finding with the actual pure temporal modules and hand-authored event constructors from tests/test_temporal.py, on Python 3.12 / Pydantic 2.13.5. Unused pytest decoration and pyarrow imports were stubbed solely to load those constructors; no database or Arrow operation was invoked. No full test-suite rerun or Owner data/stack access was performed.

## Finding 1 — Deep v2 omits the terminal clock barrier and published temporal output
Priority: blocking acceptance of the reference-validation extension, not evidence that the replay aggregates themselves are wrong.

Reconciliation `_temporal_checks` restores the last committed temporal state and calls `eng.finish(clock_end)` to construct the temporal summary published as temporal.json. This can close aggregates and fire final dispatches after the last event/checkpoint. In contrast, `DeepJob._validate` compares only the pre-finish range/restore-point state and reference aggregate chain; it never calls the reference's `finish` or compares the published finished temporal result.

Reproduction: one trade channel, coverage 2025-09-01 00:00–00:15 UTC, fifteen valid modeled one-minute bars, zero delay, default horizons. After all admissions, both engine and reference have zero sealed records and equal chains, with the 00:15 barrier pending. This is the state on which the current Deep path can report MATCH. Terminal `engine.finish()` then produces six records, including the COMPLETE 15m aggregate; the reference still has zero records and a different chain. Calling `reference.finish(clock_end)` produces the same six records and restores equality. The missing reference barrier is therefore observable without altering product code.

At a calendar-month boundary, this omission can exclude precisely the final higher-horizon records from the optional reference comparison. The stated boundary-only limitation does not fulfil the specification's same declared clock-command tape: the terminal clock command is part of the completed output.

### Required bounded correction
- For a genuinely completed run with a published temporal finish, extend Deep v2 to consume the pinned terminal clock command in both shadow and separate reference paths and compare the finished aggregate chain/output with the immutable published temporal result, in addition to existing committed-boundary comparisons.
- Pin/read the appropriate published generation and validate the artifact/reference identity. Missing, corrupt or inconsistent required finished evidence must not yield MATCH. Do not modify the original run, artifacts or saved historical diagnostic results.
- Paused, cancelled, failed and partial-prefix targets must retain their exact committed-prefix scope; do not invent a finish or imply whole-feed coverage for them.
- Preserve generation/Cancel terminal serialization, bounded progress/control hooks, truthful comparison counts and deterministic reports. Decide and document any necessary validator revision under existing contract discipline; do not rewrite historical claims.
- Add a regression for the exact 15-minute pending-final-tie case, plus a month-end fixture or equivalent multiple-horizon boundary. Prove that tampering only with the finished temporal output (leaving pre-finish range/restore commitments intact) prevents MATCH; cover absent/corrupt evidence and partial/cancelled targets.
- Run required repository checks and isolated CI/smoke. No new real-month benchmark, acquisition or broader infrastructure change is requested.

## Non-blocking dispositions
The reference aggregator is separate for aggregate math; readiness/deadline/dispatch checks use a shadow fold of the same temporal engine. The disclosed distinction is acceptable for this bounded slice; it is not independent verification of those components. Real tape input, multi-chunk application runs, annual application gates and Windows directory fsync remain explicit limits, not new tasks here.
The recorded 120-second closure allowance is an engineering convention, not an adviser threshold. Default finite end currently includes the allowance; retain and clearly document that departure from the specification's coverage-end shorthand. MP-001 must choose actual method timing/dependencies.
The measured monthly synthetic overhead does not justify optimization work while the monthly gate passes. MP-001/R3/WP-009 remain inactive until the correction is reviewed.

## Correction review and acceptance — 2026-10-03
Implementation: `ddc1831b5015692e0b34969bc23390c2dff82a46`; correction base `35d73fc`.
**ACCEPTED — WP-008-R2 factual temporal slice. Finding 1 is closed.**

Independent source review confirms launch-time pins of the completed run's clock_end, artifact directory/generation, manifest artifact hash/size and temporal reference. Deep v3 applies finish to both shadow and separate reference and performs eleven comparisons against the published evidence. Missing/unlisted/corrupt required evidence fails; internally consistent but incorrect finished aggregate commitments mismatch. Paused/cancelled/failed targets remain prefix-only. Existing stored v2 plans without terminal pins retain the boundary-only path and saved scope; legacy streaming runs retain Deep v1. No schemas, migrations or original-run writes were added by this correction.

Independent bounded probe used the actual `_terminal_compare` function extracted by AST, real temporal engine/reference and the original fifteen-minute fixture: valid finished output gives eleven comparisons, six reference records and no mismatch; changing only the finished aggregate chain in both output and manifest reference produces terminal_aggregate_chain and terminal_shadow_aggregate_chain mismatches while pre-finish input/state is untouched. Artifact loading/database regression coverage was inspected in tests, not independently rerun locally. The same import stubs/runtime limitations as the initial probe apply; no production behavior was stubbed in the comparison.

CI run **37138450907** independently checked: checks SUCCESS (web typecheck/build, non-E2E and E2E steps), compose-smoke SUCCESS. Executor reports local 439 non-E2E, zero skipped, 10 E2E and six schema baselines matching; Director does not claim a second full local suite. Regression source covers final pending ties, month-end higher horizons, finished-output-only tampering, absent/corrupt/unlisted artifacts, paused/cancelled prefix scope and resumed Deep execution.

Accepted scope remains factual UTC aggregation/clock/readiness and bounded checkpoint restore, not an adviser or profitability evidence. Normal temporal runs use reconciliation v3; new Deep temporal launches use v3, with distinct shared-engine vs separate aggregate reference scope. Default finite clock end is coverage end plus the pinned engineering closure allowance. Annual application gates, Windows directory fsync, real live tapes and application-level multi-chunk execution remain open as previously declared. No new benchmark or Owner run is needed for this closure.

Next is **Director MP-001 integrated method specification**, not more general infrastructure hardening. R3 acquisition and WP-009 implementation require their own later activation.
