# Active Task — WP-008-R1B: Streaming replay and restorable checkpoints

Status: **READY — ONLY ACTIVE IMPLEMENTATION PACKAGE**
Date: 2026-10-02
Accepted prerequisite: R1A at `0919001fb689909080e139801641eb4c7105702f`.

Implement the R1B scope below under AGENTS.md and `strategic_reviews/SR-003-DIRECTOR-DISPOSITION.md`. Consult the Astra review sections 6–8 and 15 through that disposition. Preserve the accepted causal semantics and R1A operational behavior while removing the four structural costs: eager feed, full snapshot per event, per-event SQL/delivery persistence, and full-prefix restore.

## 1. One causal kernel and bounded immutable input

Use one sequential event-application kernel in max-speed, paced and STEP modes. Retain the existing pure core/reducer as a protected small-fixture reference. No vectorized alternate state path, skipped events, altered ordering, decimal precision, quality admission, channel roles or MODELED/RECORDED availability.

Stream normalized evidence in bounded blocks, with deterministic merge and indexed source positions. Support historical datasets and finalized recorded sessions with their existing exclusions/authority. Do not materialize the complete source into an event tuple, Python/Pydantic list, JSON tree or full-query result. Bounded histories retain the accepted freshness/history semantics; optimize representation only with differential evidence.

Prepare an immutable reusable normalized feed cache keyed by actual verified source contents plus adapter/order/availability versions. Cold preparation verifies once and passes the verified result through construction; no nested duplicate verification. Define the trust boundary explicitly: path/mtime alone is insufficient; prevent source/cache mutation from being silently consumed. Pin and verify cache manifests/partitions and invalidate mismatched or corrupt cache content. Publish atomically with observable progress/cancellation. A cold streaming build may scan all input; a restored run must not normalize/build or replay its full prefix again.

Preserve canonical event/feed/config identities, including exact current ordered-event hash semantics. A rolling consumed-prefix commitment is separately named/versioned and cannot replace the canonical hash or state digest. Full coverage/count/quality metadata remains administrative, never causal state knowledge. Cache/index size can scale with source bytes on disk; working memory must remain bounded.

## 2. Cheap application and sparse persistence

Apply every admitted evidence event sequentially without constructing/hashing a full public snapshot, delta or DeliveryRecord per event in the normal hot path. Materialize public snapshots at checkpoints, explicit inspections and terminal boundaries. Preserve exact reference snapshots/digests at the same selected cursors.

New streaming runs do not write an observation_deliveries row or SQL transaction per event. Persist compact committed input-range records with contiguous cursors/counts/order bounds/prefix integrity and restorable checkpoints. Keep computed vs committed progress distinct; UI/report authoritative coverage is the committed cursor. Every commit compares the expected prior cursor and current owner/generation.

Poll controls about every 250 ms of wall time, independently of chunk/checkpoint size. Initial checkpoint cadence: either 2 active-compute seconds or 5,000 events, whichever occurs first, plus pause, STEP and terminal boundaries. Pause commits the accepted boundary and parks; STEP applies and durably commits exactly one source event. Cancel preserves the accepted committed prefix and bounded INCOMPLETE diagnostics without full trace export/re-derivation. Keep R1A responsiveness targets and explicitly report overruns/noninterruptible units.

## 3. Versioned restore and crash consistency

Store validated explicit restorable state in PostgreSQL initially: engine/state format and compatibility fingerprint; source/cache identities and partition/offset/next cursor; last total-order key; consumed input integrity/counters; exact observable reducer state including bounded channel history/quality/freshness; committed output boundary. Do not use opaque pickle as the only format. Do not invent future horizons/timers/adviser state in R1B.

Retain at least two verified restore checkpoints and terminal state, with atomic retention/references. Verify payload integrity, format, compatibility and source position before use. Resume restores state directly, then reprocesses only the bounded uncommitted suffix. Corrupt latest checkpoint falls back explicitly to a verified predecessor with diagnostic evidence; no valid state means visible failure or an explicitly requested observable rebuild, never silent replay from zero. Do not discard evidence needed by inspections or diagnostics.

Keep monotonic generations across claims and fence every durable write/publication. Preserve generation-scoped immutable files; if referenced files are introduced, durably close/publish them before a fenced DB reference, verify references on restore, and test orphan/crash behavior. Rename alone is not file/DB atomicity or proof of power-loss durability. PostgreSQL-owned small state is preferred.

Pin the execution/storage format on each run. Existing legacy and R1A runs, delivery rows, checkpoints, configs/manifests and readers remain intact; do not automatically convert, reclaim under the new engine, salvage or relabel them. New runs get an explicit format/version; any necessary additive observe contract revision requires compatibility/changelog. Cache/state formats may be separate internal versioned contracts. Frozen semantic.v1, marketdata.v1, feed.v1 and recorder.v1 schema bytes and evidence semantics remain unchanged.

## 4. Committed-prefix inspection and functional terminal path

Replace delivery-row-dependent chart/API queries for new runs with bounded indexed evidence queries filtered by committed admission position, not market time alone. Late records, equal-time ordering and source boundaries must not expose uncommitted future evidence. Enforce bounded page/window sizes. Retain current reports and meaningful chart/latest-state controls; do not remove inspection to claim speed. If reconstructing an older detailed state needs computation, use a nearby verified inspection checkpoint or a separately observable bounded diagnostic operation, never a hidden full-prefix HTTP replay.

The new storage path must finish honestly without requiring its absent per-event delivery rows. Provide the minimum bounded terminal reconciliation needed for valid new-run manifests/reports: committed range continuity, checkpoint/state/input commitments and referenced artifact checks. Precisely label validator/version/scope and distinguish these checks from full reference equivalence. Do not fake the old validator PASS, synthesize all delivery records at finalization or replay full history routinely. Reference differential validation remains in short tests; R1C owns final layered-assurance closure, optional Deep-validation UI/job and full release performance gates. Old terminal readers/assurance remain unchanged.

## 5. Required evidence for Director review

- Differential and hand-expected fixtures: selected prefixes/final state across fast, paced, STEP, batch/checkpoint settings and restore; ties, late arrivals, gaps/rejections, duplicates, end-of-source and partition boundaries; future-suffix perturbations leave earlier state/inspection unchanged.
- Cache fixtures: cold vs warm identical identities/state; source/cache tampering, interrupted build and incompatible versions; no duplicated verification inside a valid preparation trust boundary.
- Fault fixtures: before/after checkpoint transaction; immutable publication before failed DB commit if used; stale generation including reused worker ID; checkpoint corruption/fallback/no valid checkpoint; DB outage; pause/resume, cancellation and terminal publication. No missing committed references, duplicate committed ranges or stale overwrite.
- Structural counters on short/medium synthetic offline engineering fixtures: source records read/decoded, peak RSS when supported, events applied, snapshot/hash counts, delivery rows, transactions/checkpoints, restore suffix events and bytes. Demonstrate memory scales with block/history limits rather than source length, transactions with checkpoints rather than events, and direct restore at a meaningful prefix. Show cancellation latency under compute load and across serialization/hashing units, including cancellation consumed during validation. These are bounded engineering checks, not real historical month/year evaluations.
- Preserve R1A lifecycle/API/report/E2E checks and required CI. Report actual measurements, environment, skipped checks and any failing structural gate. Do not claim month/year budgets or Owner improvement from unmatched synthetic data.

## Exit and exclusions

No R2 aggregation/dispatch, method closure, adviser/semantic.v2, acquisition/context expansion, strategy/P&L evaluation, September retry or old-run salvage. R1C is planned, not activated. The application remains observation-only.

Finish with **READY FOR DIRECTOR REVIEW — R1B ONLY** and **NOT READY FOR OWNER MARKET REPLAY**.
