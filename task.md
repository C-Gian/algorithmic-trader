# Active Task — WP-008-R1: Fast Durable Observation Replay and Finalization

Status: READY  
Owner: Project & Research Director  
Executor: Claude Code  
Type: performance/correctness hardening — **NO PROFESSIONAL TRADER YET**

## Trigger

The first real Owner month run exposed a product-blocking performance problem:

- Sep-2025 corpus prepared successfully;
- observation replay reached `129600 / 129600` applied feed events;
- the replay itself required roughly one hour on the Owner machine;
- terminal finalization/validation then consumed ~99% of one CPU core for at least another ~20 minutes;
- the UI falsely showed `RECOVERING / stalled / System Degraded` during that CPU-bound validation because the observer stopped heartbeating while finalizing.

This is not acceptable for the Owner-operated historical workflow.

Do not ask the Owner to repeat the month run before R1 is complete.

## Goal

Make the accepted observation replay substantially faster **without weakening causal correctness, ordering, restart safety or integrity guarantees**.

The intended strategy is:

**process many causal events in memory → atomically commit a bounded batch/checkpoint → continue**

rather than:

**one PostgreSQL transaction per event**

and:

**validate ordering/integrity + pure final/checkpoint state efficiently**

rather than:

**rebuild and hash a full snapshot after every delivery a second time during terminal validation**.

## Non-negotiable invariants

Preserve:

- exact `feed.v1` event order;
- no future evidence;
- deterministic final observable state;
- traded/mark/index/funding separation;
- event-level delivery identities;
- duplicate prevention;
- crash-before-commit safety;
- crash-after-commit idempotency;
- pause/resume/step semantics;
- restart recovery;
- immutable source verification;
- deterministic terminal report;
- frozen public/domain schema baselines unless a generic defect truly blocks the work.

Performance may change. Semantics may not.

## 1. Batched max-speed processing

At max/unpaced speed, process a bounded batch of sequential feed events in memory before writing the durable checkpoint.

Use a documented batch size suitable for local work, e.g. hundreds to low thousands of events.

Exact size is an implementation choice, but it must be:
- explicit;
- tested;
- not derived by P&L/performance tuning against market outcomes.

Within a batch:

1. start from the last committed durable cursor/state;
2. apply events strictly in accepted causal order;
3. produce the event-level delivery records needed for audit/history;
4. compute the resulting checkpoint state/digest;
5. commit the whole batch atomically.

The transaction must atomically include:
- checkpoint cursor advance from batch start → batch end;
- checkpoint snapshot/digest/view for batch end;
- all delivery rows for the batch;
- any batch validation/checkpoint metadata introduced operationally.

A crash before commit:
- persists none of the batch;
- the whole batch is replayed.

A crash after commit:
- the whole batch is already durable;
- recovery resumes at the next event;
- no committed delivery is duplicated.

## 2. Step / paced modes

Preserve exact one-event STEP behavior.

When paused and the Owner requests STEP:
- exactly one feed delivery is applied and durably committed.

For non-max user pacing:
- batching may be reduced or disabled as needed to preserve intuitive pacing and control responsiveness.

Do not make max-speed batching alter the final result.

## 3. Control responsiveness

At max speed:
- pause/cancel requests may take effect at a batch boundary;
- the maximum unresponsive interval must remain small enough for an Owner-operated UI.

Document the actual behavior in the UI/runtime detail.

Do not check the database once per event merely to preserve near-zero-latency pause.

## 4. Recovery

Recovery must remain trustworthy.

Do not require replaying every committed event with a full per-event snapshot merely to trust the checkpoint.

A recovered worker may:
- reconstruct from immutable evidence to the last committed checkpoint; or
- use a new operational checkpoint-state mechanism if independently validated.

Prefer the simpler design that preserves accepted correctness.

If introducing stored full observable state for recovery:
- treat it as operational checkpoint data, not a new market/trader semantic contract;
- protect it with a deterministic digest;
- verify it against source/feed identity;
- test corruption detection.

## 5. Terminal validation redesign

Replace the current expensive validation path.

Current problem:
- `validate()` replays each delivery;
- each replay step builds/hashes a snapshot;
- `_no_future()` repeatedly scans snapshot contents;
- this duplicates large amounts of work after the run already reached its terminal cursor.

The new terminal validation must still prove at least:

1. source/feed identity unchanged;
2. committed delivery count equals cursor;
3. delivery sequence is contiguous;
4. event ids are unique;
5. committed event ids/availability times match the exact accepted feed prefix/order;
6. no event beyond the committed cursor is treated as applied;
7. final observable state/digest equals a pure derivation from the immutable source at the terminal cursor;
8. completed replay cursor equals total feed events;
9. observation-only boundary remains intact.

Do **not** recompute a full ObservableSnapshot + digest for every event merely to prove these.

A valid efficient design is, for example:
- verify delivery identity/order directly;
- re-apply the pure reducer over the feed prefix in memory;
- compute/compare snapshot only at bounded checkpoint boundaries and/or final cursor;
- use rolling/batch integrity metadata where useful.

The exact proof mechanism is your implementation choice.

Explain why the new proof is logically sufficient.

## 6. Finalization heartbeat and phase

Finalization/validation is real work and must remain visible.

While finalizing:
- keep the observer heartbeat alive;
- do not allow health to report the replay worker as dead/stalled merely because CPU-bound validation is running.

Expose an operational phase such as:
- PROCESSING
- FINALIZING
- VALIDATING

and validation progress if defensibly measurable.

The UI must show:
**Validating final result**
rather than:
**RECOVERING / stalled**

when the worker is alive and validating.

If adding operational DB fields/migration is useful, keep them separate from `observe.v1` domain semantics.

## 7. Existing stuck run compatibility

The Owner currently has a replay that has already committed all `129600 / 129600` events under the old implementation but did not reach terminal manifest/report before R1.

R1 should, where practical, allow this existing replay to be reclaimed/finalized by the new implementation **without re-applying all 129600 durable deliveries into PostgreSQL**.

It is acceptable to:
- rebuild/verify pure state from immutable source;
- use the already committed deliveries;
- produce the terminal manifest/report.

Do not require deleting the dataset or re-downloading Sep-2025.

Do not silently mutate historical committed delivery identities.

## 8. Report timing

The final evaluation report must distinguish:

- replay processing time;
- finalization/validation time;
- total elapsed time;
- recovery count.

This gives the Director evidence about where future cost lives.

## 9. Performance evidence

Do not run the Owner's real Sep-2025 network acquisition.

Use deterministic/offline data.

Add a representative large offline benchmark/test harness sufficient to demonstrate the structural improvement.

At minimum prove:

### Database transaction reduction
For max-speed replay of N events:
- durable batch commits are O(N / batch_size), not O(N).

Do not enforce an absolute wall-clock threshold in CI if environment variance makes it flaky.

But report:
- old theoretical commit count: N;
- new measured commit/batch count;
- offline events/s for the representative fixture;
- final validation duration for that fixture.

A generated/captured ~100k-event fixture is acceptable if test runtime remains practical.

### Finalization complexity
Prove through tests/instrumentation that terminal validation no longer performs one full snapshot/digest derivation per committed delivery.

## 10. Correctness tests

Add/adjust deterministic tests for:

- batch and event-at-a-time final snapshot equality;
- batch sizes 1 / small / default yield identical final digest;
- strict order preserved;
- no future leakage;
- duplicate event prevention;
- crash before batch commit;
- crash after batch commit;
- restart at a committed batch boundary;
- pause at/between batches;
- STEP exactly one event;
- cancel at a batch boundary;
- speed change does not alter final digest;
- corrupted checkpoint/integrity metadata is detected;
- terminal validation catches missing/reordered/tampered delivery identities;
- completed source validates PASS;
- existing old-style event-by-event replay can still be finalized.

## 11. UI / health tests

E2E/offline tests must show:

- max replay runs with batched processing;
- live progress still advances;
- pause/resume works;
- STEP still advances exactly one event;
- validation phase is visible;
- health remains available for Market replay during validation;
- no false `RECOVERING / stalled` while observer heartbeat is current;
- terminal report appears;
- Copy report still works.

Do not redesign the application.

## 12. Contracts

Do not modify:
- `semantic.v1`;
- `marketdata.v1`;
- `feed.v1`;
- `recorder.v1`;
- `observe.v1`;

unless a truly generic contract defect blocks the optimization.

Operational database migrations/internal metadata are allowed.

Do not create `semantic.v2`.

## 13. No trader changes

Do not implement:
- MarketView;
- timeframe hierarchy;
- higher-timeframe adviser logic;
- LONG/SHORT;
- indicators;
- cycles/news;
- targets/stops;
- P&L evaluation.

The Owner's timeframe question is recorded for later Astra/adviser review. This task is only replay performance/correctness.

## 14. Git workflow

Before editing:

`git pull --ff-only origin main`

Implement only WP-008-R1.

Run all relevant tests/E2E/build/compose smoke.

Commit and push normally to `main`.

Do not run the real month evaluation yourself.

## 15. Completion report

Report:

- base/final SHA;
- exact batching/checkpoint design;
- chosen default batch size and why;
- max-speed vs paced/STEP behavior;
- crash/recovery semantics;
- terminal validation proof and why it remains sufficient;
- heartbeat/finalization phase behavior;
- existing full-cursor run compatibility;
- DB migration/internal metadata changes;
- old vs new transaction count on representative N;
- offline benchmark events/s;
- offline validation duration;
- test/E2E results;
- schema baseline hashes;
- GitHub Actions result;
- limitations.

Then stop with:

**READY FOR OWNER REPLAY RETRY**

Do not ask the Owner to redownload September.

Acceptance belongs to the Project & Research Director.
