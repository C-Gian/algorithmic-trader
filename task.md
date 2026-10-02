# Active Task — WP-008-R1C: Assurance and performance release gates

Status: **READY — ONLY ACTIVE IMPLEMENTATION PACKAGE**
Date: 2026-10-02
Accepted prerequisites: R1A `0919001`; R1B correction `9d814ec957e17fc33c1fcfbfb96034844e416444`.

Close operational assurance and structural performance for the observation-only pipeline under AGENTS.md and `strategic_reviews/SR-003-DIRECTOR-DISPOSITION.md`. Consult Astra sections 8–10 and 15 through that disposition and the closure notes in `delivery/WP-008-R1B-DIRECTOR-REVIEW.md`. Preserve the accepted single kernel, source/cache trust boundary, sparse persistence, restore, compatibility and legacy evidence.

## 1. Layered, accurately scoped assurance

Audit and close the three layers: verified source/cache admission; incremental runtime and bounded terminal integrity; protected reference/independent-expected fixtures. Trace what is actually checked for every admitted event, including quality and auxiliary channels. Enforce total-order/cursor continuity, unique-slot policy, causal cutoff, exact consumed-input commitments, checkpoint/config/source/state compatibility and output/artifact boundaries. Distinguish input, state and output commitments.

Strengthen observe.stream-reconciliation where necessary: positive contiguous ranges/counts, first/last order bounds, terminal commitments/state/snapshot, completed exact coverage, referenced files and publication integrity. Preserve empty-prefix, cancellation, failures, DB outages and malformed/corrupt checkpoint handling. Incomplete/cancelled verification cannot become PASS; verification failure stays visible even if operational replay reaches completion. Normal terminal work cannot replay all evidence, synthesize per-event deliveries or rebuild a prefix. Expose validator/version/scope and truthful wording such as runtime integrity passed, engine reference-tested; never imply a fresh independent replay happened in every normal run.

Use the current source/cache manifest and trusted receipt consistently. Verify consumed partitions against pinned bytes; make repeated integrity work visible and justify the trust boundary, avoiding accidental nested verification or whole-state scanning per event. Preserve old readers and their original validator claims. Adviser/horizon/dependency checks remain unavailable, not fabricated.

## 2. Explicit optional Deep validation

Implement the planned Deep validation action attached to a selected new streaming observation run, through the app. Persist a linked durable diagnostic job before expensive work. It has its own progress/health/generation, bounded controls, elapsed timings, validator/version/scope and Markdown/JSON/Copy reports at every status. Refresh/restart must reattach. Reuse the operation/supervision infrastructure without building a second production replay engine.

Compare an independent reference execution of the same pinned admitted prefix with retained checkpoint/final states and committed range boundaries/commitments; disclose selected comparison cursors, coverage and whether only the canonical cache or independently normalized source was examined. Do not describe shared-input state comparison as an independent source audit. Stream bounded input and reference state; never eagerly materialize a year feed or per-event snapshots simply because this diagnostic is optional. Preserve observable pause/cancel behavior and resumable diagnostic state or explicitly reported interrupted restart cost.

Deep validation is optional, never automatically launched after ordinary completion and never required to produce a normal report. Preserve the originating run's immutable records/artifacts/results. Store diagnostic evidence separately; a genuine mismatch adds a persistent linked assurance warning that the app and copied diagnostics expose. Cancel/interruption yields INCOMPLETE, not false failure or success of the originating run. Completed diagnostic results are reproducible/idempotent; no duplicate links/publications on retries. Keep original terminal reports available, with separate linked diagnostic results and an explicit current assurance summary.

Deep checks on real substantial history remain Owner-launched in the app; executor fixtures are bounded engineering tests.

## 3. Control and durability closure

Measure status/launch acknowledgement <=1 s, progress refresh <=2 s, and pause/STEP/cancel application normally <=2 s, <=5 s at a bounded safe unit, under declared local load. Cover preparation/snapshot copy, single large-file hashing/copying, long gap/dedup scans, external merge, replay, restore, reconciliation, report serialization and terminal publication. Add byte/batch-level cooperative hooks where file-level hooks cannot meet the bound. Snapshot copy's 1 MiB buffer is not itself a cancellation checkpoint. Label unavoidable atomic save boundaries and actual overruns truthfully.

Retain heartbeat-independent compute milestones, dead-child handling, actual recovering labels and disconnected DB semantics. Fault-test referenced cache/artifact loss, corruption, partial publication and receipt/DB commit boundaries with existing generation fences. POSIX fsync claims must match actual calls; Windows directory durability remains explicitly unproven where unsupported. A lost cache must reproduce its trusted receipt from valid source or fail safely with an actionable report; never silently rewrite pins, resume on changed input or claim guaranteed power-loss recovery. No access to or modification of the Owner live stack is needed.

## 4. Reproducible structural performance evidence

Create a reproducible offline engineering benchmark/report using deterministic generated evidence and captured short edge fixtures. Measure phases separately: cold snapshot/verification/cache, warm preparation, replay, checkpoint save/restore, normal reconciliation/report and optional Deep validation. Record OS/Python/build, CPU/logical cores, storage/runtime limits, source/event/quality/partition counts, cache state, active/wall/waiting, peak RSS and Python heap where supported, snapshots/hashes/checkpoints/SQL transactions/delivery rows, restore suffix and output/cache bytes.

Start with a small pilot; only scale within a declared bounded engineering time/resource budget. A generated observation stream with representative month/year event counts may be used to test structural scaling and the reference ceilings: cached month <=120 s, year <=900 s; normal terminal/report month <=10 s, year <=30 s; cold preparation separately <=120 s/month and <=900 s/year. This is synthetic infrastructure evidence, not an actual historical month/year evaluation or Owner speedup. Avoid retaining full generated data/events in benchmark-driver RAM. Include long gaps, shuffled/duplicate recorded evidence and a many-partition case, not only clean dense bars. Capture memory plateau and metadata growth honestly.

Do not launch substantial real historical CLI replay, source acquisition, strategy evaluation or parameter sweeps. If a bounded benchmark hits its cap or a release objective fails, stop, preserve evidence and identify the phase/bottleneck/failing gate; do not label performance fixed. Optimize only the observation infrastructure needed for these gates, preserving differential behavior. Real September/hardware comparison belongs to the later Owner app handoff.

## 5. Release-ready app and review evidence

Keep Historical Workbench types explicit: Market replay available, Adviser unavailable, Deep validation now implemented only with its actual scope. Cover current-phase ETA/timeline, computed versus committed cursor, committed-prefix charts, all-status reports, unknown memory/timing and assurance warnings. Preserve route/legacy report compatibility. No cosmetic redesign.

Prepare a simple Owner procedure after controlled upgrade: preserve volumes and old September suspension; select the EXISTING verified local dataset, launch a NEW Market replay ID, copy terminal report and inspect linked old/new evidence once the replacement exists. No download, salvage, fabricated new ID or automatic retry. Show which phases and assurance establish a useful result. Make the report capture sufficient build/hardware/count/timing/controls/limits for the Director comparison; do not ask the Owner for raw logs or manual CLI benchmarks.

Required acceptance inventory: protected differential plus hand-expected ties/late/gaps/duplicates/partition/future-suffix cases; batch/pacing/STEP/checkpoint equivalence; crash/stale-generation/restore/corruption tests; receipt/cache/source boundaries; Deep match/mismatch/cancel/restart/report fixtures; representative long-unit control measurements; reproducible structural benchmark; existing DB/API/E2E/web/isolated smoke and schema compatibility. Report exactly which checks ran and any failing/unavailable gate.

## Exit and boundary

No R2 aggregation/dispatch, MP-001 method closure, R3 context acquisition, adviser/semantic.v2, trading/P&L or old-run conversion. Existing state and report scopes remain observation-only.

Finish **READY FOR DIRECTOR REVIEW — R1C ONLY**. Include a concrete proposed Owner app handoff and the benchmark/control/assurance evidence. **Owner September retry remains blocked until Director release acceptance; the executor must not announce READY FOR OWNER MARKET REPLAY on its own.**
