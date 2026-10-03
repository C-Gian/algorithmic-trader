# WP-008-R2 — Causal temporal substrate
Status: DIRECTOR-APPROVED BOUNDED IMPLEMENTATION SPECIFICATION
Date: 2026-10-03 (Europe/Rome)
Authority: FOUNDATION.md v3.1; SR-003 disposition; integrated plan §9.
Prerequisites: R1A/B/C accepted; Owner September incident closed; WP-010 accepted at f7ad4bc.
This is factual time/dispatch infrastructure, not the adviser method, a strategy, or economic validation.

## 1. Scope and actual baseline
The production kernel in observe/kernel.py incrementally applies feed.state.apply; its explicit restore JSON holds bounded channel history (inspection default 240). It does not yet hold higher-horizon accumulators, temporal deadlines or reasoning dispatches. Rebuilding those from public snapshots would lose prerequisites and invite prefix replay.
Add a centrally owned temporal reducer beside the accepted factual reducer, driven by each admitted feed event and explicit clock commands. Preserve source ordering, source/cache identity and existing observation snapshots. Live input ownership is not built here: use a recorded/admitted command fixture interface, not new connections, collectors or an always-on platform.
Do not create a competing replay kernel, bar database transaction per minute, general strategy DSL or economic rules.

## 2. Required factual horizons
Default versioned profile temporal.utc-horizons.v1:
- base 1m evidence retained as accepted;
- 15m setup, 1h tactical, 4h broad, daily broad, weekly/monthly context.
Roles are labels/design conventions, not confirmation votes, supported win rates or mandatory readiness gates.
UTC intervals are half-open [start,end). Minute/hour/day anchors are UTC midnight; weeks start Monday 00:00 UTC; months start calendar day 1 and end next calendar month. No local-time/DST anchors, fixed 30-day month, rolling substitution or OHLC copied from native bars.
Aggregate each trade/mark/index series separately. Funding is sparse factual settlement context, not a candle or summed into price/volume.
Each 1m slot belongs to exactly one interval at each configured horizon. Exclude any slot crossing an invalid base boundary rather than invent alignment.

## 3. Aggregate records and numeric semantics
New namespaced contract algotrader.temporal.v1, revision 1, PROVISIONAL; do not overload frozen semantic.v1 or marketdata.v1. A record contains:
- source/channel/instrument/family; horizon/profile version; interval start/end;
- status FORMING, COMPLETE, INCOMPLETE or OUTSIDE_COVERAGE;
- expected/valid/missing/rejected constituent counts and reason summary;
- OHLC and typed volumes only when COMPLETE; incomplete values may be exposed solely in an explicitly partial diagnostic field, never as a complete bar;
- known_at, admission cursor, closure dispatch ID, availability basis/policy, source/feed provenance and content digest.
OHLC: first open, max high, min low, last close in market-slot order. Trade sums exact Decimal contracts/base/quote volumes independently, preserving currencies/units. Mark/index have no fabricated volume.
Completion requires every expected minute valid, admitted no later than the closure barrier, with end <= clock time; expected constituents depend on actual calendar interval length.
known_at of COMPLETE is max(interval end, prerequisite available times). Dispatch publication time is separate and cannot precede known_at. Missing, rejected and outside coverage never become zero-price/forward-filled constituents.
A coverage cut through an interval cannot produce a complete truncated higher bar; partial first/last intervals are OUTSIDE_COVERAGE with the reason visible.
Counts reconcile exactly; absent minutes at closure are classified locally as missing prerequisites without creating synthetic feed events or changing the canonical input commitment.

## 4. Conservative late-data policy
Freeze each interval at its scheduled closure barrier. If all prerequisites were not admitted, seal it INCOMPLETE/OUTSIDE_COVERAGE. Do not reopen or repair a sealed interval in R2.
An older minute admitted before its still-open interval's barrier contributes in market-slot order; an event for a sealed interval is counted as late-excluded in temporal diagnostics and remains accepted factual evidence in the existing feed reducer. It cannot regress the latest complete aggregate or rewrite any earlier dispatch.
Explicit quality events are never replaced by late values; duplicate-slot rejection remains the accepted admission rule. No second chance source merge.
Expose the policy ID temporal.seal-no-revision.v1 and its consequence: late data can make a horizon unavailable despite subsequent receipt. Future revision policy requires an explicit version/change decision.
To avoid an unbounded minute map, maintain only current open accumulators with a bounded constituent bitmap/slot table for each calendar interval. Close and discard constituent tables at barriers; retain bounded sealed aggregate records, not all minute history. Bound worst-case calendar month by 31 days and declare the configured per-channel/profile maximum. Reject input outside supported coverage/order assumptions visibly.

## 5. Clock and dispatch contract
Separate market time, feed availability time, clock time, admission cursor, and actual dispatch receipt. Wall-clock pacing/checkpoint/UI cadence are never reasoning time.
Define typed input commands Admit(event,cursor), AdvanceTo(time,barrier), RegisterDeadline(id,due,priority), CancelDeadline(id). R2 uses engineering subscribers/reasons only; no actual candidate or call is created.
A dispatch records stable sequence/ID, clock time, admitted cursor/last order, policy/profile/config identity, reasons, prerequisite aggregate IDs and readiness. Persist enough concise audit material to replay the admission/clock barriers exactly; no full snapshot per dispatch is required.
No dispatch can read past its admitted prefix. Monotone clocks and cursors, deterministic serialization/order, and no duplicate dispatch IDs are required.

### Modeled historical execution
At each deadline t: admit every canonical event with available_time <= t, including the entire tie group; update forming aggregates; then close due intervals and assess readiness. No event available after t contributes.
Order at t: factual admissions; aggregate closure/readiness changes; due expiry-type callbacks; scheduled reasoning callbacks; potential publication callbacks. R2 only tests this order with fake subscribers.
Coalesce scheduled reasons sharing (t, admitted cursor) into one dispatch, with sorted unique reasons. Never erase a material transition or a separately logged recorded receipt barrier.
Jump directly to the next input/deadline; do not loop on empty minute ticks. Stream tied input rather than buffering the whole group. Checkpoint only consistent boundaries or persist pending-boundary state exactly.

### Recorded/live-style execution
Recorded receipt time is not exchange publication. At a clock barrier admit only the explicitly logged prefix, even if other events share a timestamp; never wait for a supposedly complete historical tie group.
A dispatch receipt/command sequence disambiguates equal timestamp operations. A subsequent receipt at the same time can cause a later dispatch with a different admitted cursor. A late receipt affects only later outputs.
Replay of the same admission/clock command tape must equal live-style fixture execution. Recorded source events without a dispatch tape use a named recorded-replay synthetic-barrier policy, explicitly not a claim to reproduce decisions of an unrecorded live adviser.
Do not reorder receipts into modeled perfect boundary batches while claiming live equivalence. Live wall-clock recovery/catch-up and connections remain WP-009 dependencies, not new R2 services.

### Deadlines without events
Timers can run with no new evidence and must not fake bars. Stable priority then stable ID orders equal-time deadlines. Due expiry hooks precede new-publication hooks.
Finite replay stops at its declared clock_end (default coverage end); do not advance indefinitely or force future outcomes. Timer input/config and pending due state are in restore data.
STEP retains its accepted exactly-one-feed-event meaning. At a tied boundary a modeled scheduled dispatch may remain pending until the tie group has been admitted; the UI must distinguish applied event, forming aggregate and published closure. Pause freezes simulated time; resume adds no paused wall time to the reasoning clock.

## 6. Readiness, freshness and bounded state
Each observation dependency declares required family/horizon, number of consecutive complete records and freshness allowance. R2 demonstrates configured dependency queries; MP-001 chooses production lookbacks and authority.
Return explicit READY, WARMING_UP, GAP, STALE, OUTSIDE_COVERAGE or UNAVAILABLE with missing requirements/counts; define precedence deterministically and expose all blockers, not just a Boolean.
One unavailable optional horizon cannot invalidate all others. Do not inherit feed.freshness's two-minute inspection threshold as an adviser policy.
Expose both age since interval end and age since known_at. Freshness compares clock time to the declared allowance and detects due expected closures lacking complete data. Sparse funding has no fabricated scheduled completeness.
Finite capacities are profile/config inputs with hard operational maximums; enough state for the configured queries or explicit configuration rejection. No arbitrary method lookback chosen for performance acceptance.
Restore includes current accumulators, bounded sealed records, quality/late counters, logical clock, processed barrier, pending tie/deadline commands, dispatch sequence and configuration fingerprint. Restore is direct, not full-prefix reconstruction. Monthly source continuation must preserve temporal state; source/instrument discontinuity resets only affected dependencies and records why.

## 7. Integration and compatibility
Introduce temporal state/engine format identifiers and compatibility fingerprints; do not silently decode new restore state as observe-state.v1. Existing runs/cache receipts/source identities and readers remain unchanged.
If observe public documents gain fields, explicitly bump OBSERVE schema revision/changelog and preserve old readers; Director authorizes additive optional temporal references/summary fields only. Leave feed.v1 unchanged unless a concrete unavoidable contract conflict is reported before altering it.
Store the temporal restore payload in the same generation-fenced checkpoint transaction as the factual cursor/state and dispatch commitment. Extend normal reconciliation truthfully to check temporal restore/dispatch integrity; do not relabel existing validation artifacts or claim independent temporal re-execution. Version validator if its checks/scope change; declare exact scope.
Extend optional reference validation for new temporal-enabled runs only using a separate small/reference path over the same declared clock-command tape. Existing Deep v1 runs keep their claim. If exposing a new validator, give it its own version; do not silently add semantic meaning to old IDs.
Historical pre-R2 unfinished runs follow additive suspended-read-only compatibility; no auto-replay/salvage. Any migration must be additive and legacy fixtures covered.
Reuse the existing supervisor, lease, controls, reports and receipt-pinned streaming source. No public semantic.v2, adviser calls, P&L, new database/service platform or new source acquisition.

## 8. Minimal Owner-visible surface
Within existing expandable technical details show horizon/profile, newest sealed interval and status, known_at/clock time/admitted cursor, readiness reasons and late-excluded counts. Label 'temporal substrate only; no adviser'. Copy reports expose coverage/warmup/clock policy and named invariants, not performance or market advice.
Do not redesign Home/Data/Recorder/mobile. Preserve the successful Workbench primary result path and available details. No new real-month Owner run is required to accept this engineering slice.

## 9. Acceptance evidence
Use tiny hand-authored and differential fixtures; no full historical profitability jobs or timeframe/parameter tournament.
A. UTC anchors: 15m/1h/4h/day; Monday week; month transitions incl February leap and non-leap; partial coverage; DST irrelevant.
B. Exact OHLC/Decimal typed volume for each family; funding sparse and distinct.
C. Missing/rejected constituent cannot COMPLETE; late before barrier contributes; late after seal does not revise; newest interval never regresses.
D. Cutoff perturbation: change/append events after a dispatch's admitted cutoff and prove its record/state digest unchanged.
E. Modeled ties: dispatch sees whole <=t prefix regardless of family order, pacing, STEP cadence and render rate; pending tied boundary restores correctly.
F. Recorded fixtures: interleaved equal-time receipts/clock barriers, delayed close, no perfect tie assumption, deterministic replay of the tape; separate policy label without tape.
G. Equal-time expiry-before-publication; no-event timers; pause/resume; finite clock_end; ordered IDs; no duplicate dispatch after crash.
H. Restore at open interval, closure tie and deadline; compare restored vs uninterrupted outputs; checkpoint cadence cannot change semantic records.
I. Readiness family/horizon-specific, stale/no-new-event, optional unknown not universal veto; declared retention overflow rejected; bounded heap/state measured on synthetic short vs longer inputs with same profile.
J. Legacy readers/schema baseline discipline, generation/CAS faults, corrupted restore fallback, normal/Deep claim scope and deterministic report checks.
K. Required repository checks and isolated compose smoke. Report local runtime limits and CI evidence separately.
Review economic-neutral output. Normal observation state/reference digests on legacy fixtures remain identical; temporal digest comparisons use the same tape/profile and do not equate modeled with recorded execution.

## 10. Explicit MP-001 decisions left open
Exact professional observations; lookbacks and dependency authority; horizon revisions with reasons; scenario/candidate coverage; lifecycle deadlines; cost/response assumptions; timing/cycle/news dispositions; source needs, warmup/evaluation/tail windows.
R2 is not a gate requiring every horizon to be READY before any future call. R3 acquires only approved method-dependent context, after MP-001.

## 11. Executor handoff
Implement this bounded slice using AGENTS.md. Report base/final, contracts/formats/migrations actually changed, clock policies, semantic/reference fixtures, bounded-state evidence and limitations. Do not launch September, acquire a year, activate MP-001 or tune for calls. Director review precedes the next task.
