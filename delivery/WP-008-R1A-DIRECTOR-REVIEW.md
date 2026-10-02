# WP-008-R1A Director review

Date: 2026-10-02
Reviewed implementation: `66a2dce90619848776e891e7f50f0f8440d95eb4` (base `fb19de247350f205ad8c9da2cb18adeb7ea885b6`).
Decision: **CHANGES REQUIRED — R1A ONLY**. No R1B activation or Owner September retry.

## Evidence and retained work

GitHub Actions run `37038947330`: independently inspected jobs `checks` and `compose-smoke`, both SUCCESS. The executor reports 320 non-E2E and 10 E2E tests; the Director did not rerun those suites locally. Source inspection supports retaining durable pending launch, independent compute supervision, monotonic generation fencing, generation-scoped publication, legacy suspension, and incomplete diagnostic export. This is not a blanket acceptance of every implementation claim.

## Required corrections

1. **Cancellation can trigger unbounded work.** `observe/job.py:ReplayJob.finalize` explicitly sets `_cancellable = status == COMPLETED`; an already cancelled partial run loads every committed delivery and calls full reference validation with cancellation disabled. `_load_quietly` also disables cancellation during reload. This violates the R1A control budget and bounded incomplete diagnostics. Once cancellation is observed, terminate at a bounded safe boundary with truthful CANCELLED/INCOMPLETE diagnostics; do not re-load/re-derive the whole prefix as a prerequisite. Cancellation newly requested during terminal phases must be checked before terminal publication/commit, with any unavoidable atomic boundary documented. Preserve committed evidence and generation fences. This does not require a new validator or streaming engine.

2. **ETA mixes phases and substage units.** `observe/worker.py` starts `throughput_since` at claim, before preparation; `observe/diagnostics.py:operation` uses it for replay ETA. Example: 100 s preparation + 10 s replay, 50 of 100 events: existing `ops.phase_eta` gives 110 s instead of 10 s. This numerical result was reproduced directly from the stdlib-only ops module, not as a full integration benchmark. `ReplayJob.milestone` also retains a rate base across stage/unit/total changes within a phase. Reset rate windows at meaningful phase/substage/attempt/control boundaries and keep estimates unknown until sufficient comparable progress exists. Never label claim elapsed time as replay active work.

3. **Timing must distinguish measured work from waiting or unknown spans.** `_closed` measures all monotonic phase elapsed time while `_pace` separately counts intentional sleep; current open timeline adds wall time as active time. Interrupted unknown active spans are summed as zero without exposing incompleteness. Define and expose consistent active/wall/waiting accounting, exclude declared waits from active throughput, and preserve unknown measurements as unknown or explicitly incomplete. Do not imply a complete active measurement through a numeric zero. Also check terminal-phase text against the actual cursor: `runtime_state` must not imply the cursor is complete for partial failure/finalization or imply validation passed solely from operational completion.

## Correction acceptance evidence

Use short deterministic fixtures covering partial replay cancellation after a nontrivial committed prefix, configured paused/resumed cancellation and terminal-phase cancellation; none may require a full reference pass to acknowledge cancellation. Retain full-cursor validation cancellation tests and stale-generation publication tests. Add meaningful regressions for long preparation followed by replay, substage unit resets, intentional pacing/waiting and interrupted timing. Report actual control latency and reference-work counters, plus required CI checks. Retain schema compatibility and legacy preservation. No Owner database, dataset or live containers are needed.

## Correction review and closure — 2026-10-02

Correction: `0919001fb689909080e139801641eb4c7105702f`, base `adcf127b366dfc6a22aa6b670cbc6a4f1b6fe89d`.
Final decision: **ACCEPTED — R1A operational slice only**. The earlier CHANGES REQUIRED decision above remains the historical review of `66a2dce`.

The Director inspected correction code in job/artifacts/worker/diagnostics/ops and the new regression fixtures. Already observed partial cancellation uses config/checkpoint-only artifacts; pause/resume cancellation claims only to finalize; terminal publication locks the same row as Cancel and checks the cancellation boundary. Replay rate starts at REPLAYING; substage/unit/total rate bases reset; timing exposes measured active/waiting and unknown interrupted spans. Existing supervision, generation and legacy preservation architecture remains.

Independently verified CI run `37044401955`: checks SUCCESS, compose-smoke SUCCESS. The executor reports 331 non-E2E + 10 E2E tests and the measured short cancellation fixtures; these timings/counts were not independently rerun by the Director. Independently executed stdlib checks passed for interrupted unknown spans, measured active/waiting totals and comparable ETA; seven tracked schema-related files were byte-identical to the correction base. No local full suite, Owner dataset, database or live stack was accessed.

This closes the three requested regressions at the bounded fixture scope. It does not demonstrate month/year performance or universal five-second control latency: full-trace serialization/hashing and other existing eager units still require the structural work and representative control tests in R1B/C. In particular, cancellation consumed inside validation can retain/hash the already serialized trace; release review must measure that path rather than infer large-run responsiveness from 61 events.

The executor acknowledged a no-op pull despite AGENTS.md. This was a workflow violation; no tree change resulted, and it does not invalidate the implementation evidence. AGENTS now explicitly prohibits no-op/startup pull habits. R1B is activated by the new task; R1C and Owner September retry remain inactive.
