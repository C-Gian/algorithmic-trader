# WP-011 — Director engineering review
Date: 2026-10-05. Reviewed product: `f1a8023763e820e41cbd6085be14b4ebabbcb0d3`.
Disposition: **CORRECTION REQUIRED — WP-011 ONLY. No Owner economic run authorized.**
Remote CI: PENDING / NOT CHECKED by Director; Owner operates the CI handoff. This review is not conditional permission to run October.

## Evidence and scope
Read the implementation delta, core3/evaluator3, method dispatch, runtime/state, reconciliation/Deep integration, report/comparison and test evidence. Executed bounded offline synthetic probes only: [script](evidence/WP-011-DIRECTOR-PROBES.py), [results](evidence/WP-011-DIRECTOR-PROBES.json). No Owner DB/container/data access, no replay/Deep job or real economic run.
Pure WP-011 suites: 54 passed plus one packaging test initially affected by a Director download trailing-newline artifact; that artifact was corrected and the packaging test passed separately (55 passing tests in aggregate). One DB-dependent live test skipped because no DB was configured; no claim of independent full-suite/DB/E2E verification. Executor's local full run is 657 passed / 2 outdated revision-pin failures, then observe tests 21/21; do not reword it as one full all-green run. Exact final CI remains required.

## F1 — blocking: box retirement misses simultaneous protective contact / opposite-edge close
`core3.dispatch` calls `_scen_intervals` before `_box_close_flags`; the latter scans the already-mutated scenario dictionary rather than the pre-dispatch structural B episodes its docstring promises.
Reachable full fold: box [100000,101800], z=60; B LONG confirmed at 04:46, alive at 04:59. Keep prices 101860 until the last minute [04:59,05:00), then close 99930 < L-z=99940, also contacting V. At 05:00 the protective contact terminates B and deletes it; the same newly admitted 15m opposite-edge close no longer sees B. The old box remains and births B SHORT from the old box in that very dispatch.
Expected: preserve protective call/scenario contact precedence, but derive the structural box-retirement predicate from the B episode present at the beginning of this dispatch. Retire the old box once on that simultaneous opposite-edge close; no new episode may be born from it. Do not resurrect episodes already structurally dead before this dispatch, and do not retire on a mere earlier wick or a returned-inside close above the far edge.
MP-002 §3 B1 preserves the structural MP-001 opposite-edge rule, independent of child economics. The direct-call white-box test bypasses the failing orchestration. This is an implementation ordering defect, not permission to alter the closed method.
Required regressions: reachable LONG and SHORT full-dispatch paths, with issued and economic-rejected child variants, same-dispatch collision; nonretiring wick/inside-return and episode-dead-before-dispatch controls; direct restore around the boundary must preserve resulting box token and lineage.

## F2 — blocking: already confirmed antecedents are reported as unactivated
`EvaluatorV3.on_journal` credits CONFIRM only to samples already in memory; inherited `Evaluator._sample` creates every later sample with activated_at=null, including a principal already CONFIRMED at that sample cutoff.
Reachable A fixture: CONFIRM 04:01; same scenario is principal at 05:00 and 06:00. Both later rows falsely report antecedent_activated_1h=false and antecedent_activated_4h=false; the 04:00 pre-confirmation sample correctly gets true after CONFIRM.
Expected: a sample knows the already-published confirmation of its own principal at the sample cutoff, while an ARMED sample may be updated only by its causally later confirmation. Preserve the timestamp/reference in the v0.3 evaluator's durable state or obtain it from the cutoff's core state, without replaying history or borrowing another scenario's activation. Do not change frozen v0.2 semantics/records.
Required regressions: pre-confirmation -> confirmation; already-confirmed LONG/SHORT samples; never-confirmed/terminal/wrong-scenario controls; pause/restore before and after the hourly sample; pure and durable outputs agree, and 1h/4h endpoint availability remains separate from activation.

## Decisions on executor interpretations
- A K >= frozen B: literal after-arm destination-contact precedence is correct. No confirmation/call after the narrative destination is already contacted. Keep an explicit diagnostic count/example; do not relax K or destination rules to create calls. MP-002 before-arm spent/reaction precedence remains unchanged.
- The v0.2 dislocation baseline defect is acknowledged; keep the frozen baseline unchanged. v0.3's once-per-slot correction implements the retained method rule. Explicitly disclose this extra version difference in comparison JSON/Markdown and practical handoff, not only STATE: integrated comparison cannot attribute improvement to RETURN alone. No fresh September extraction or baseline rerun authorized.
- Warmup entry clearing with structural context retained, latest fresh return minute, frozen call landmark references, live pre-activation exclusion and odd-microsecond midpoint rounding are consistent with the closed design within the reviewed scope.
- Interpretation 12 cannot justify F1: a B episode present at dispatch entry still owns the opposite-edge predicate for that simultaneous close even when protective contact terminates it earlier in the same dispatch.
No method revision/parameter search/new research package is activated.

## Bounded correction and verification
Implement only F1/F2 and the explicit comparison limitation/diagnostic wording above. Keep the v0.2 baseline and closed numeric/method rules unchanged; preserve all previously saved results. Add fail-before/fixed-after assertions on the reviewed commit and current correction, including reachable orchestration rather than only helper calls.
Run relevant MP-002 pure/routing/path/packaging suites; DB-required restore/evaluator/Deep tests covering the changed paths; relevant browser/report tests if their surfaces change. Full suite and compose-smoke must pass on exact final SHA in CI, operated by Owner. Avoid another local 26-minute full run solely to repeat unaffected checks; run it if a wider change/failure justifies it, and report exact local coverage without guessing.
Update engineering evidence and STATE with expected/actual results and remaining limits. No new performance benchmark, acquisition, real replay, economic evaluation, protected window, automatic task activation or Owner handoff.
Completion: **READY FOR DIRECTOR REVIEW — WP-011 CORRECTION ONLY**. CI wait stays with Owner.
