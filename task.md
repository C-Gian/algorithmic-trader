# Active Task — WP-008-R1A: Observable job lifecycle and diagnosis

Status: **READY — ONLY ACTIVE IMPLEMENTATION PACKAGE**
Date: 2026-10-02
Owner: Project & Research Director
Executor: Claude Code / Codex
Type: bounded operation/observability/correctness hardening; no professional trader.
Base at activation: `009c3420b588f2f0422d08fbe5d92e8ddf88b15f` plus the SR-003 disposition documentation commit. Use latest remote main, not this older SHA.

## Read and goal

Read FOUNDATION.md, STATE.md, AGENTS.md in full. Read `strategic_reviews/SR-003-DIRECTOR-DISPOSITION.md` and the supplied Astra review, especially sections 2, 7, 10–12, 14–15. The Director dispositions override conflicting review proposals. The old R1 draft and paused SR-003 task are superseded.

Make every expensive part of the existing observation workflow a durable, visible operation with trustworthy health, bounded controls and a diagnostic report even when unfinished. Deliver this slice without building the streaming engine or changing reducer/validation mathematics. A faster-looking UI is not performance acceptance.

## 1. Durable launch and preparation

Persist a lightweight launch job/envelope before dataset/session verification, feed build or recovery work. Acknowledgement target <=1s; no hashing/parsing/large queries in the HTTP launch transaction. Link the evaluation and job atomically. Validate identifiers, permissions/local existence and cheap request fields only; preparation errors become visible failed jobs with reports.

Keep one observation execution path. A job may precede a verified replay configuration: source/config/feed identity and total count are PENDING/unknown until genuinely prepared. Do not create placeholder verified identities, zero totals posing as known, or silently relax the old config reader. Persist the exact verified identity/policies before first causal application. New preparation state and old fully configured runs need explicit readers/versions.

Move launch-flow source verification/feed construction into the worker-owned operation, with phase/subphase hooks and cancellation. User-triggered full preflight/verification must also be a visible durable operation (or reuse this preparation job); no remaining hidden heavy launch preflight. R1A may retain the eager feed implementation for now, clearly instrumented and documented; streaming/cache redesign is R1B.

Handle dataset and finalized recording sources; maintain MODELED versus RECORDED labels, PARTIAL exclusions and source authority. A read-only source failure is not a reason to redownload/rebind the corpus.

## 2. Shared operational state, exact scope

Use a small versioned job/progress contract for observation/evaluation and adapt existing corpus jobs to the same status/phase/health display/report semantics. Reuse existing tables/workers or a small additive operation table; do not build a generic orchestration platform or replace acquisition/resume algorithms.

Separate:
- status: queued/running/paused/completed/failed/cancelled;
- phase: QUEUED, PREPARING_SOURCE, VERIFYING_SOURCE, BUILDING_FEED, INITIALIZING, REPLAYING, FINALIZING, VALIDATING, GENERATING_REPORT (corpus also DOWNLOADING);
- health: progressing, known waiting, alive without observed progress, unresponsive/awaiting recovery, recovery actually restoring, disconnected;
- assurance: not checked/incomplete/passed/failed, with validator/version and scope.

Persist attempt, monotonic lease generation, phase transitions/start and accumulated active durations, wall elapsed, progress sequence/last-progress time, metric completed/total/unit if known, ETA/basis if justified, controls and compact diagnostic text. Refresh/restart reattaches; pause/downtime excluded from active throughput. Operation at cursor 100% is not complete until terminal artifacts/report are published.

Progress hooks cover hashing/row verification, build stages, prefix recovery, artifact serialization, current validation loop and report publication. Report true counts or unknown totals; no fake global percentage. Current algorithm can stay slow. Source/build hooks must permit safe cancellation between bounded units; do not pretend a monolithic call is responsive. Record unavoidable noninterruptible sections with elapsed/health, and split them where needed for controls without undertaking R1B optimization.

## 3. Supervisor, fencing and controls

Separate lightweight supervision from CPU-intensive computation using an independent process and DB connection (or equivalent demonstrated GIL-independent supervision); verify compute child existence and separately track its milestones. Prefer focused reuse of current worker infrastructure; no new distributed dependency.

Initial observation defaults: heartbeat about 2s, lease about 30s. Retain corpus's longer network lease if justified; common semantics do not require identical lease durations. Bound DB calls/timeouts. A DB outage is disconnected, never a fabricated compute stall or successful save. A dead child must not have its lease renewed indefinitely. An alive child without milestones is alive/no observed progress, not proof of health from CPU usage. Phase-specific inactivity limits distinguish known waiting from suspected stuck work; controlled interruption/restore requires a new fenced generation and report evidence.

Every new ownership claim/reclaim has a monotonic generation. Fence checkpoint/cursor writes, controls consumed by execution, phase/progress writes, corpus binding, artifacts and terminal publication by current owner/generation and expected prior boundary. Stale generation must not renew or publish even with reused worker ID. Use generation/attempt-scoped staging and immutable publication so an old finalizer cannot overwrite current files before a DB fence. Preserve existing source/cursor CAS and delivery uniqueness.

Status/control acknowledgement target <=1s; progress refresh <=2s; controls applied normally <=2s and <=5s bounded safe unit under local CPU load. Cooperative progress hooks in current validator must permit cancellation at replay 100% without finishing a full reference replay; partial diagnostic assurance stays incomplete. Pause/STEP remain current replay controls: STEP exactly one source event, never a batch/candle. Preparation/terminal phases expose only applicable controls; disabled controls state why. Generation is operational and cannot alter source order/state/digests.

## 4. Diagnostic reports before completion

Provide Copy report for chat and Markdown/JSON for queued/running/paused/interrupted/failed/cancelled/completed observation/evaluation and corpus operations. Build incomplete diagnostics from bounded persisted operational facts, not full deliveries or source re-execution. Snapshot report generation must work even when the final manifest is missing or final report generation failed.

Include job/evaluation/replay and source/config IDs or explicit PENDING; report capture time; engine/build/environment identity when obtainable; status/phase/health/assurance; committed cursor and actual coverage; measured per-phase active/wall time; attempts/generation/recovery; progress and last milestone; pending controls; error/limitations; next practical diagnostic. Never infer completed validation from the full cursor. Verify manifest existence/hash where claimed; do not label diagnostic export as terminal assurance.

Instrument phase durations and available process CPU/memory, source load/verify counts, event/snapshot/delivery/transaction counts and output bytes. Unsupported metrics are unknown with a reason. Do not take per-event expensive measurements; counters must be bounded/cheap. R1B/C will use this baseline.

Keep adviser/MarketView/call/outcome metrics UNAVAILABLE/null. Existing valid terminal artifacts retain their original identities and validation scope. Corpus snapshot diagnostics do not invent network receipts or download completion.

## 5. Preserve the existing September evidence

No access to the Owner's database/dataset is assumed. Implement a backward-compatible read-only diagnostic/export path and controlled operational suspension for pre-upgrade nonterminal replay work. Preserve DB rows, checkpoints, delivery identities, manifests/files, configuration and source binding. Do not auto-claim/finalize legacy nonterminal runs through the new path.

Use an additive suspension/annotation separate from historical execution status, visible in the UI with reason and copyable diagnostics. Do not delete, mark completed/failed/cancelled merely to unblock, convert old state into new-engine state or fabricate a replacement ID. If an old terminal manifest is present, verify/report it. A legacy prefix restore/finalization is not a release gate. No need to duplicate all delivery rows for a diagnostic report.

Document the Owner upgrade's controlled shutdown/fencing step so old containers cannot keep publishing while migration occurs. Normal update must preserve volumes; never prescribe `down --volumes`. New checkpoints/generation cannot fence old binaries that ignore them: stop those processes first, then start the upgraded stack. Keep operation simple and within the existing Compose workflow.

Do not start the replacement September run in R1A. R1C will activate that app handoff and link old/new runs.

## 6. UI and contracts

Rename the destination to **Historical Workbench**, retaining `#backtest` or a compatible redirect. Explicit available type: **Market replay — data and engine check**. **Adviser backtest** is unavailable until implemented. Deep validation is planned, not an enabled fake action in this package.

Use phase timeline/current-phase bar and readable elapsed/unknown ETA. Show replay 100% / VALIDATING without a completed badge or zero whole-job ETA. RECOVERING only when a new fenced attempt is actually restoring; lease expired alone means unresponsive/awaiting recovery. Health must derive capability availability from actual worker state throughout CPU work. Distinguish current operation health from general worker service availability. No broad design makeover.

Allowed: additive operational DB migrations; operational launch/progress/report contract; `observe.v1` revision/changelog/schema update for actual operational changes with old reader/tests. This is Director approval for that limited revision, not arbitrary provisional changes. Existing revision-1 artifacts remain readable and unchanged. Freeze `semantic.v1`, `marketdata.v1`, `feed.v1`, `recorder.v1` baseline bytes. No advisory semantic.v2; no sparse-delivery/checkpoint state redesign or changed validation guarantees yet.

## 7. Required bounded verification

Use tiny deterministic/offline inputs and disposable test DBs. Add meaningful regression tests for:
- prompt durable launch while verification/build is deliberately slow; pending fields honest; preparation errors/cancel and restart discoverable;
- CPU-bound validation/preparation longer than a short test lease with progressing milestones: supervisor stays alive, no false reclaim/RECOVERING;
- alive child without progress, dead child, DB outage and actual fenced reclaim produce distinct states; stale generation cannot write state/binding/artifact/terminal status even after same-ID reacquisition;
- existing order/digest and crash idempotency unchanged; pause/resume and STEP one event work;
- cancel during validation at full cursor yields partial/incomplete report, not completed/PASS;
- incomplete/terminal/no-manifest/report-generation-failure exports; immutable legacy data remains unchanged with new operational annotation;
- progress timers survive refresh/restart; observed ETA excludes later unknown phases and pauses;
- corpus display/report/fencing retains verified local reuse and source authority; no real downloads;
- E2E launch/phase/control/copy/download and explicit run types; chart/REAL/DEMO separation and health preserved.

Run relevant unit/DB/integration/causality tests, TypeScript typecheck/build, offline E2E and Compose smoke per repository CI. Short fault tests may exceed a deliberately shortened test lease; do not launch a month/year replay. Report skipped/unavailable checks honestly. Require DB checks rather than accepting a silently skipped suite. No absolute noisy CI speed claim; demonstrate prompt/control behavior under the bounded fixture and record measured duration.

## 8. Out of scope and completion

No R1B/C, cache streaming rewrite, optimized reducer, sparse per-event persistence, new restorable checkpoint format, layered/deep validator redesign, horizon logic, news/cycles, calls, targets/stops, P&L, account sizing or order connectivity. No old-run salvage, September download/replay, substantial historical CLI evaluation or parameter sweep.

Before editing: check worktree/remotes and `git pull --ff-only origin main`; stop on divergence/unrelated local changes. Implement this task only. Commit/push normally to main after required checks; no force-push. Update README to describe actual implemented behavior and limitations; STATE records executor evidence but Director acceptance remains pending. Do not activate the next package.

Completion report: base/final SHA; files/migrations/contracts; launch/pending configuration design; supervisor/GIL/fencing/publication/control behavior; progress/timing and diagnostics; legacy preservation/upgrade steps; actual tests and schema hashes/CI results; measured short fixture timings; remaining eager feed/per-event/full-reference costs.

Finish with **READY FOR DIRECTOR REVIEW — R1A ONLY**.

**NOT READY FOR OWNER MARKET REPLAY. Do not ask Gian to retry September yet.**
