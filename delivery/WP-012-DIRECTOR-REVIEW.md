# WP-012 — Director engineering review
Date: 2026-10-07 Europe/Rome. Reviewed product: e434d4311a947f65f2fccf035d61e79d9108add2.
Decision: CORRECTION REQUIRED — one reproduced blocking finding. No Owner economic comparison activated.
Exact-SHA CI: PENDING / NOT CHECKED by Director; Owner-operated.

## Scope and evidence actually examined
Read executor evidence, the changed-file inventory, new core4 and v0.3 hook extraction, method/codec/report/comparison/reconciliation and selected integration wiring against the closed MP-003 domains. The frozen v0.2 core/evaluator/runtime are absent from the changes; v0.3 hook changes were examined, not presumed neutral from the executor summary alone.

Director independently ran MP-003 paths and versions: 100 passed plus one packaging-test failure caused by missing Director documents in the temporary review snapshot. After fetching the missing authoritative documents from the exact reviewed commit, only that test was rerun: 1 passed. Thus all 101 selected tests pass on the completed snapshot. This is not a fresh full-suite, DB, browser, live or Compose verification. Executor's local/DB/browser results remain executor evidence, and final CI is not asserted.

The additional [probe](evidence/WP-012-DIRECTOR-PROBE.py) runs a complete synthetic temporal/runtime/adviser tape in both LONG and positive-price mirrored SHORT. [Observed output](evidence/WP-012-DIRECTOR-PROBES.json) records the unexpected confirmations. No Owner DB/data/stack, network market input, historical economic replay or Deep was used.

## F1 — Old-anchor-only contact in an interval straddling supersession is ignored
Blocking causal/semantic defect in core4._local_contact.

The branch for m.end > current anchor publication tests only the CURRENT V and returns None immediately when the extremum does not reach that V. It does not examine the prior active epoch whose domain overlaps the first part of the minute. Consequently a possible contact with the old V before supersession is erased by the lower new V. The wholly-before-publication late-epoch branch handles that case only when the interval ends before publication; it misses the straddling counterpart.

Reachable LONG probe:
- first ARM at 03:45:30, R=100000, V1=99800;
- complete [03:45,04:00) clean reaction supersedes it at actual publication 04:00:30: R2=99850, V2=99650;
- newly admitted complete [04:00,04:01) minute has low=99750: below V1, above V2; it spans publication and no finer order is known;
- no ANCHOR_LOST is recorded; epoch 2 later CONFIRMS at 04:14.
SHORT mirror reproduces: V1=100200, V2=100350, high=100250; same missing ambiguity and epoch-2 confirmation.

The possible old contact occurred in a minute whose end is AFTER the new reaction source bar's end. If it happened while the old anchor was still active, that older source bar cannot rescue it under the contact-cutoff rule. Since intraminute ordering is unavailable, the current anchor cannot be certified clean. Required result: journal anchor UNASSESSABLE, same structural owner WATCH (unless a separate structural terminal applies), contact interval end retained for any later genuine replacement, no confirmation using epoch 2. A later eligible new anchor is not forbidden.

This follows MP-003 §3 time-domain monitoring/publication ambiguity and WP-012 §2; it is consistent with the executor's conservative late-earlier-epoch interpretation. It does NOT restore the v0.3 whole-scenario V terminal or invent a new method. The original v0.3 interval helper already distinguishes level revisions inside an interval; the new branch must preserve that causal distinction for local anchors.

## Required bounded correction
1. Evaluate eligible epoch domains overlapping an interval, including the prior active epoch at a supersession inside that interval. Do not test arbitrary dead epochs outside their active domain or infer intrabar order. Do not bypass detection merely because the new V was not touched. Preserve no-retroactive confirmation/source-publication and contact-before-revision semantics.
2. Add fail-before/fixed-after LONG/SHORT full-tape regressions for this probe. Controls: neither active-domain V touched; new V reached in a straddling interval; wholly earlier late contact; wholly AFTER supersession touching only old V (must not resurrect the inactive level); first-arm origin, destination/contact collision and ordinary replacement unchanged.
3. Exercise production pack/unpack immediately before and after supersession and contact, plus one isolated durable restore/cadence case proving the same outcome. Keep canon/hash guards and old-version bytes intact.
4. Run relevant MP-003 pure/version/DB restore suites and existing v0.2/v0.3 parity/compatibility guards. Full local 42-minute suite and full browser rerun are not required for this kernel-only correction absent other changed paths; exact final CI full checks/compose-smoke remain required and Owner-operated. No economic replay, new benchmark or acquisition.
5. Update evidence with exact commands/results, fail-before/after and identity/compatibility effects. No expected fixture update that merely accepts the erroneous confirmation. Commit/push; READY FOR DIRECTOR REVIEW — WP-012 CORRECTION ONLY.

## Interpretations and retained boundaries
Freshness/coverage in ever-armed WATCH is consistent with required monitoring. Same completing reaction bar may source replacement; strict replacement versus inclusive clean supersession and actual live dispatch publication are explicit closed rules. Late earlier-epoch contact making current anchor unassessable is conservative and consistent, provided all overlapping domains (F1) are handled and unrelated inactive levels do not create contacts.

The existing after-confirmation policy, numerical predicates, inheritance identity and frozen old releases are not reopened. Reusing evaluator v3 and leaving its unchanged contract revision is appropriate. observe revision 7 for its added value domain is documented. No profitability/frequency conclusion follows from engineering tests.

Owner Oct/Nov/Dec v0.3/v0.4 plan remains INACTIVE until independent correction review and exact-SHA green CI. Old October results and partial v0.3 series remain preserved. Only the bounded correction above is active.
