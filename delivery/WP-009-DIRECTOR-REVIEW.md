# WP-009 — Director review
Date: 2026-10-05
Reviewed: `5d1f2e169f2894b548015552c187c0eade1dc5a2`, base `a840131`.
Decision: **CHANGES REQUIRED — WP-009 ONLY. NOT READY FOR OWNER BACKTEST A.**

## Evidence and scope

The integrated implementation is real: packaged method identities, three families and reflected SHORT paths, separate evaluator, durable professional state/journal, live input tape and Home/Workbench surfaces. Preserve that architecture. This review is not an economic evaluation, parameter search or a general infrastructure redesign.

Independent Director checks:
- Read the Foundation, active specification, method sections relevant to the findings and the implementation paths below; isolated archive of the reviewed commit, Owner checkout/stack untouched.
- Ran the six pure adviser suites (`method`, `rules`, `evaluator`, `paths`, `causality`, `live`): **69 passed in 37.24 s**. Director runtime Python3.12.14/Pydantic2.13.5; this is an offline pure check, not the project's full Python3.14 DB/browser verification.
- Added short synthetic counterexamples against the actual imported core/evaluator/live code. API-window and Deep-comparison probes extract the actual functions using AST and substitute boundary fixtures; these are not database integration tests. Results and reproducible probe sources: [evidence](evidence/WP-009-DIRECTOR-PROBES.json).
- Retrieved [CI37275582552](https://github.com/C-Gian/algorithmic-trader/actions/runs/37275582552), exact reviewed SHA: **FAILURE**. `checks` job111651760472: web checks success, **544 non-E2E passed**, E2E **12 passed / 1 failed**. `compose-smoke` job111651760765 success. The executor's local539 aggregate and13 E2E are local reported evidence, not this CI result.

The supplied report's “all checks pass” is therefore not the current CI conclusion. No real September replay/economic run was performed by the Director.

## Findings requiring correction

### 1. HIGH — ordinary protective stop gaps get a favorable fictitious fill
`adviser/evaluator.py::_path_minute` handles an adverse opening gap only when `m.start == pending_exit_at`. An otherwise ordinary protected minute opening beyond V is filled at V with `STOP_TOUCH`.

Counterexample: LONG entry100000, V99950, T100400, no pending exit. Next complete minute opens99900, high99940, low99880. Actual exit99950 over the whole minute; required exit99900 at the model opening boundary. This understates loss and gives the wrong funding-ownership interval. MP-001§11 explicitly requires adverse-open pricing on protective stop gaps.

Fix for LONG/SHORT and all guidance variants. Preserve the both-level ambiguity rule when intrabar ordering is actually unknown; do not impose target-first chronology. HORIZON_ONLY retains its declared no-protection scope. Test ordinary and pending-exit gap/contact collisions, inclusive boundaries and funding ownership. Product calls remain unchanged by evaluator corrections.

### 2. HIGH — no-input timers do not implement both-age freshness and residual closure
`adviser/core.py::next_deadline` uses **max(end,known_at)+allowance** for trade freshness although `_fresh` requires both ages. First failure is **min(end,known_at)+allowance+EPS**. A recently received old bar must not get an extended life.

Counterexample: minute ends12:00, received/known12:01, allowance120s. Actual next timer12:03:00.000001; required12:02:00.000001. Advance to12:02:01 without another input: `_fresh` is false but professional clock remains12:01 and thesis ONGOING.

The residual timer is scheduled at `hard_deadline-minimum`, where equality still permits entry, then removed as already processed. Counterexample: A deadline12:30, clock12:00, healthy data/geometry. At12:00:00.000001 residual is below30m, but entry remains AVAILABLE until another input/timer.

Schedule the actual first failing boundaries; drain due expiry/adequacy commands deterministically without fabricated data or duplicate dispatches. Cover delayed receipt, freshness equality, no-new-input residual closure, restored timers and pre-open evaluator eligibility. Preserve equality semantics (age<=allowance; residual>=minimum).

### 3. HIGH — C withdrawal is tied to market-end/dispatch equality
`adviser/core.py::_context_withdrawals` examines C's close below L-z only when `m15[-1].end == dispatch_time`. Recorded/live complete bars normally dispatch after their market end.

Counterexample: valid BALANCED context, TRANSITION phase, armed C_LONG, L100005/z3. A new complete15m closes100001 at12:00 and is dispatched12:00:01. The attempt survives although the close is below100002. It must withdraw before any coincident/later trigger. The current probe avoids adverse EXPANSION and context loss, so neither accidentally masks the defect.

Use newly admitted sealed-close identity/frontier, not equality of two different time meanings. Assert modeled and delayed-receipt LONG/SHORT, restored state and coincident trigger; old closes must not be applied repeatedly.

### 4. HIGH — disconnected/stopped/stale sessions can retain usable-entry presentation
`LiveSession.disconnected` changes only session connectivity. Connectivity is not a core/tape adequacy input. A fresh ticker can keep an otherwise viable call AVAILABLE while the candle session says DISCONNECTED. Counterexample: ongoing synthetic live call, disconnect candle socket, supply a fresh admissible quote and tick: entry AVAILABLE, reasons empty.

`adviser/api.py::live_status` and `web/src/views/LiveCockpit.tsx` also preserve call AVAILABLE / “Live call” / admissible-now presentation after Stop or when the lease is unresponsive. A warning elsewhere is insufficient current-entry semantics.

Persist/tape connection loss and recovery as explicit adequacy inputs, replay deterministically, and prevent new/current actionable entry while required connection or current worker evidence is unavailable. Keep a still-assessable thesis separate from entry; a monitoring gap/staleness follows the registered terminal rules. Reconnection alone is not proof of fresh usable input. Suppress current-ready presentation at API/UI/Copy-analysis boundaries for stopped, failed, unresponsive and disconnected sessions without rewriting the saved call history.

Director operational decision: AVAILABLE->UNVERIFIED is a material withdrawal of usable entry and should produce one committed withdrawal/unverified alert; recovery produces one reopening when actually adequate. No per-tick alerts, old-alert replay or reconstructed alerts. This corrects executor interpretation8; it does not create a trading rule. Test disconnect with fresh quotes, silent stale socket, reconnect, Stop/restart, worker loss, browser/API/MD consistency and alert dedup.

### 5. HIGH — Stop during startup fold is ignored; task ownership needs guaranteed cleanup
`LiveSession.reconstruct` polls cancellation before family fetches, but not during the replay loop. A10-minute fixture sets cancel after the last family acquisition, before folding: all10 minutes/30 events still apply. At96h this cannot be presented as bounded cooperative Stop.

`LiveAdviserWorker._session` starts its socket task and startup thread before the `try/finally` that cleans socket/quote tasks. Startup failure or fence loss can leave network/compute work alive until loop shutdown; cancellation of `to_thread` alone does not stop its underlying thread. Initial metadata acquisition also precedes the startup heartbeat loop.

Make startup ownership cover metadata acquisition, catch-up and live operation. Check cancellation/fence between bounded fetch/replay units, signal/join cooperative startup work and close owned subscriptions/tasks on every exit. Keep lease/progress truthful during expensive work. Do not enter LIVE or publish alerts after an already observed Stop. Use offline blocked-fetch/replay/fence/failure tests; no generic supervisor rewrite or Owner stack changes.

### 6. HIGH — call-detail price window exposes the uncommitted suffix
`adviser/api.py::window` selects only `engine`, then reads cache to `cursor+after` with no committed-cursor limit. Probe: committed cursor1, request cursor1/before0/after3 returns slots1,2,3; none has been committed.

Clamp to the run's actual committed frontier and validate cursor/bounds; any optional suffix preview must be explicitly separate and authorized rather than represented as committed historical inspection. Call/revision/outcome inspection must support a requested cutoff consistently; no later records under an earlier cutoff. Preserve completed-run retrospective diagnosis within its committed frontier. Test paused/running/failed/completed runs, requested future cursor, exact end boundaries, source tamper and cutoff-safe call/journal detail.

### 7. HIGH — Deep v4 trusts stored digests instead of the stored semantic/evaluation bytes
`observe/deep.py` loads `SELECT seq,digest` for adviser journal/evaluation rows; `_adv_compare` compares replayed digests against that map. Altering only stored `record` bytes leaves the map unchanged and can produce a matching comparison. The existing tamper test changes `digest`, not `record`.

The Director's extracted actual comparison returns no mismatch for a byte-only alteration retaining seq/digest. This demonstrates the comparison hole; it is not a full DB Deep run. The separate runtime reconciliation re-hashes records, but a previous saved runtime PASS does not certify later mutable bytes or substitute for Deep's own advertised comparison.

Re-hash actual stored bytes and verify sequences/chains/frontier against pinned range/finish expectations before declaring reference agreement. Test record-only alteration with unchanged digest, changed digest/chain, missing/extra rows, journal and evaluation tables, launch/resume boundaries and completed finish. Fail/error or mismatch, never MATCH on unverified output bytes. Original runs/artifacts and saved diagnostic reports remain immutable; bump the new Deep claim/version where necessary.

### 8. MEDIUM, release-blocking verification — repeated copy can acknowledge an earlier copy
CI's failing legacy Workbench journey obtains the completed MD, then clicks Copy; clipboard still contains the earlier RUNNING snapshot3/61. `useCopyFeedback` leaves state `copied` from the previous click while the next fetch/write awaits, so the E2E's `to_contain_text('Copied')` can pass before the new operation completes. This is a supported race diagnosis, not proof that the terminal report endpoint generated wrong bytes.

Give each copy operation a fresh pending/completion state (prevent overlap or track operation identity); confirm only after that write succeeds. Test two rapid/successive copies across the terminal transition with delayed fetch/clipboard, failure and out-of-order completions. Assert the actual second clipboard contents; do not weaken the content-equality check or merely rerun CI until green. Retrieve a final green exact-SHA CI with all E2E journeys.

### 9. MEDIUM, scope completion — required diagnosis is partly omitted
`adviser/report.py` supplies rejection counts and MarketView row minutes, but not the specified **overlapping named blocker durations**, SLOT_OCCUPIED/PRIORITY duration or staged room erosion from impulse/reaction through trigger/open. It reports trigger-to-open erosion only for issued calls. MP-001§11 and WP-009§4 require these for diagnosing coverage/zero calls, not just headline P&L. These are not the explicitly optional exit-delay export.

Complete bounded, durable diagnostic accumulators/journal reconstruction with defined denominators and overlapping-blocker semantics. Preserve all rejected/suppressed candidates and separate attempt counts from elapsed time. Make data available in Copy/MD/JSON and labelled details; stages inapplicable to B/C stay explicitly not applicable. Tiny overlapping-blocker/zero-call/interrupted/restore fixtures must prove values, no parameter search or real-market run. Do not add a second analytics infrastructure.

## Executor interpretation disposition

1. **Accepted:** B/C low<=V does not satisfy their trigger predicate and may remain pending; A's explicit trigger-contact rejection differs. The straddling-arm withdrawal still applies to every family. No new method prose needed.
2. **Accepted:** current usable S15 at trigger is frozen for issued geometry; owned setup zones/scales stay frozen separately.
3. **Accepted with existing boundary:** deferred pivots/periods become known at actual zoned creation, never backdated; preserve expiry/contiguity and immediately previous-period scope.
4. **Accepted:** EXPANSION/COMPRESSION do not require1h to be observed; remaining context-dependent phase branches unavailable if context missing. MarketView/setup dependencies remain explicit.
5. **Accepted:** required15m loss resets affected windows/unfinished objects and affected issued thesis; optional loss is not a global reset.
6. **Accepted:** non-price pre-open eligibility plus own-open geometry, price CLOSED versus quote-only UNVERIFIED; correction4 adds connection/session readiness truthfully.
7. **Accepted principle, defective scheduling:** <=freshness equality and EPS first failure; finding2.
8. **Partly accepted:** reconstruction/restart suppress old new-call alerts. Usable-entry withdrawal to UNVERIFIED must alert once; finding4.
9. **Accepted:** admission clock may be max(receipt,processed clock), but retain measured receipt and original market time; finding3 illustrates why they must remain distinct.
10. **Accepted:** evaluation-start reset clears candidate/call state and excludes warmup scoring, preserving observation/landmark state and reported boundary effect.

## Correction and acceptance boundary

Only correct these findings and directly required regression/compatibility evidence. Preserve MP-001 rules/register, development/protected split, thresholds, Owner pack/data and old saved reports. Version behavioural implementation and evaluator identities explicitly so changed semantics cannot resume under the old identity; old reports remain readable and incompatible unfinished work is surfaced honestly. Public provisional schema changes, if needed, require revision/changelog; frozen baselines unchanged.

Run the full final non-E2E suite with DB required, E2E, web/schema checks and isolated CI Compose smoke. Distinguish exact final full runs from partial reruns. Include failing-before/fixed-after evidence for the counterexamples and verify cancellation/restore/Deep/version discipline. No annual benchmark or new general hardening package.

Owner Backtest A remains inactive. After corrected Director acceptance, use the already prepared September development pack in the app; no reacquisition, new method or economic handoff is authorized by this review.
