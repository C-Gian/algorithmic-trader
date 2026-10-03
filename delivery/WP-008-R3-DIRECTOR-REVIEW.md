# WP-008-R3 — Director review
Date: 2026-10-03
Reviewed: `33c2b8345245ddc3646fd215964411786c095c20`, base `1dac5bad1af93906f02142bc8e9dbb6a455c89cb`.
Decision: **CORRECTION REQUIRED — R3 ONLY**. No Owner preparation handoff or WP-009 activation yet.

## Scope and evidence
Reviewed the source diff, pack contracts/presets/planner/composition/source preparation/publication, pack job/API, replay reconciliation and tests. Independently inspected CI run37149503468 jobs: checks (web build/typecheck, non-E2E, E2E) and compose-smoke completed SUCCESS. Executor reports458 non-E2E and11 E2E, isolated migration11 smoke and two-size measurements; those complete suites were not rerun by the Director.

Three small standard-library probes executed exact extracted function/statement AST from reviewed code with dependency stubs and temporary directories, without altering product code, running a DB/Owner stack, acquiring market data or performing a replay. The probes isolate the offending code paths; they are not full integration tests. Executor regressions must reproduce them through real pack preparation/publication.

## 1. Verified source bytes do not own all contributor facts — blocking trust defect
Location: `corpus/pack.py::prepare_contributors`, then `check_contributors`, `build_pack_cache`, `manifest_body`.

After `prepare_stream_source` establishes the private-snapshot/receipt-pinned trust boundary, `prepare_contributors` calls `md.load_manifest` on the original mutable source path again. Request bounds, instrument snapshot and byte counts come from this second read, while the Contributor carries the earlier verified manifest SHA/cache pin. These fields drive compatibility, definition hash/cache key and the published metadata assumption. The second read has no comparison against the verified bytes.

Counterexample: mutate the original manifest's tick or instrument fields after source preparation returns, before the second manifest read. The exact-function probe returned the changed unverified tick while both supplied verified source/cache pins matched. A single contributor avoids cross-contributor disagreement detection. The same gap exists during cold preparation and warm reuse/rebuild. R1B's snapshot guarantee must extend to the new pack facts, not just the event bytes.

Required correction: derive all contributor facts from the same verified snapshot or receipt-pinned evidence, or recheck and bind the exact manifest bytes being interpreted so a race is rejected. Never combine new original facts with old verified identities. Preserve warm-cache trust and no routine event-source reload. Add cold/warm/post-verification manifest mutation regressions (definition/tick/request/source facts), rebuild pins and unchanged-source success. Result must use original verified facts or fail visibly, never publish tampered facts as verified.

## 2. Publication trusts intended artifact bytes and misses staging-directory durability — blocking publication defect
Location: `pack.py::stage_pack`, `publish_staged`; `pack_job.py::_prepare` publication transaction.

`stage_pack` fsyncs the manifest/provenance files; publication computes receipt SHA from `render_manifest(doc)` in memory. `publish_staged` does not rehash actual staged/published manifest/provenance against that expected identity before the receipt/COMPLETED commit. The exact-function probe altered the staged manifest and publication still returned `published`; actual file SHA differed from the receipt's intended SHA. Later `open_pack` rejects it, but preparation may already have declared COMPLETED. This is a concrete gap against the specification's rehash-before-reference rule.

Also, the staging directory itself is never fsynced on POSIX after its entries are created; fsyncing the packs parent after rename does not substitute for persisting entries inside the renamed directory. The probe recorded file and parent-directory fsync calls only. Windows's declared unsupported directory fsync remains a limitation, not a demand to invent support.

Required correction: verify actual manifest/provenance bytes against their expected pins under the publication boundary before durable references/COMPLETED; persist required staging/final directory entries on supported platforms before the receipt. Cover altered staged/published manifest and provenance, converged destinations, cancel/fence and crash boundaries. Bad bytes must not receive a successful trusted publication. Use real artifact operations plus fsync-order spies; preserve immutable existing good artifacts and explicit Windows durability scope.

## 3. Startup cleanup deletes other active attempts' staging — blocking concurrency defect
Location: `pack_job.py::_prepare`, unconditional `packs_root(...).glob('.tmp-*')` cleanup; `pack.py::stage_pack` staging names.

Every pack attempt deletes every `.tmp-*` directory at startup without checking owner/job/generation or liveness. Different presets can have concurrent jobs and workers. If worker A has staged its pack and worker B starts another preparation, B deletes A's pending output. The exact cleanup statement probe removed a temporary directory representing another active worker's staging. Calling these all interrupted attempts is unjustified; fencing on job rows does not protect unrelated filesystem cleanup.

Required correction: scope staging ownership and cleanup to the current safely abandoned attempt, or positively establish abandonment before cleanup. A new/current/stale generation must not remove another live owner's staged files. Add two-job/two-worker interleaving and reclaim tests around staging/publish/cleanup; cancellation should remove only its own unpublished artifacts. No universal directory sweep or age-only claim of abandonment.

## Accepted design choices and residual limits
- Excluding download-vs-local history from content identity is correct; retain it in operational job records.
- READY_WITH_LIMITATIONS for optional reference gaps is acceptable with explicit scope; it does not assert trade-core failure. Keep the visible acknowledgement and separately reported usable trade coverage.
- Same-ID differing directories may be quarantined and reproducibly rebuilt, subject to the corrected trust/durability/ownership boundaries. Never rewrite existing receipt identity to accept different content.
- NOT_PROBED is truthful and allowed. Real boundary-source availability and size remain Owner preparation evidence after acceptance.
- Data page pack listing is a nonblocking disclosed omission: Workbench is the assigned usable entry point.
- Unknown funding completeness, historical metadata validity, calendar/incidents/quotes, annual performance and Windows directory fsync remain open. No profitability or first-adviser readiness claim.

## Handoff
Correct findings1–3 only, retaining existing behavior and tests. Full relevant checks and isolated CI; no new substantial acquisition/benchmark/Owner replay. Update STATE with executor evidence and leave Director acceptance pending. Completion: **READY FOR DIRECTOR REVIEW — R3 CORRECTION ONLY**.
