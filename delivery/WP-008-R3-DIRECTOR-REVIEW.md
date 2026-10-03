# WP-008-R3 — Director review

**Current status: ACCEPTED at `09e23fdb06ad496c8c29d42d0d8785c6e5c84282` — R3 only. READY FOR OWNER SEPTEMBER PACK PREPARATION.** WP-009 executor implementation is not active.
Date: 2026-10-03
Reviewed: `33c2b8345245ddc3646fd215964411786c095c20`, base `1dac5bad1af93906f02142bc8e9dbb6a455c89cb`.
Initial decision (historical): **CORRECTION REQUIRED — R3 ONLY** at33c2b83. Superseded by correction acceptance below.

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

## Correction acceptance — 2026-10-03

ACCEPTED at `09e23fdb06ad496c8c29d42d0d8785c6e5c84282` (base6aa982e). Findings1–3 closed:
- Contributor facts are parsed from one byte buffer whose SHA equals the verified manifest/source receipt pin. Cold/warm/rebuild mutation cannot combine new facts with an old pin.
- Actual manifest/provenance bytes checked at staging/publication/after rename before receipts; files, staged directory, published directory and packs parent are fsynced on supported platforms. Bad staged bytes fail; bad published bytes quarantined. Good existing content is verified before convergence.
- Attempt-owned staging and abandonment checks replace the global cleanup. Own older generations and terminal-job leftovers can be removed; another live job's staging is preserved.

Independently read the focused diff and eleven regression cases in `tests/test_pack_correction.py` (including parameterized cold mutations), earlier retained pack tests and publication-lock flow. Independently inspected CI37152698917: checks with web/non-E2E/E2E and compose-smoke SUCCESS. Executor reports469 non-E2E, zero skips and11 E2E locally; complete suites were not rerun by the Director.

Director exact-function AST probes with standard-library dependency stubs and temporary directories now pass: matching metadata accepted/changed buffer rejected; altered staged and post-rename bytes rejected; correct publication/convergence; staging-directory fsync invoked; own older generation removed while another live generation remains. These isolate code paths, not a DB integration rerun or a power-loss experiment. No real market bytes, acquisition, Owner stack or replay was used. Frozen contracts unchanged in the correction.

Residual limits retained: Windows directory fsync unavailable/unproven; R1B feedcache cleanup outside this correction; real boundary availability/bytes unmeasured; funding completeness, historical metadata and calendar/incident/quote coverage limited; annual application gates unmeasured. No economic acceptance or trading method implementation.

### Owner preparation handoff — September only
Upgrade following README (stop app services, update checkout, rebuild/start; preserve all volumes). In Historical Workbench, **1 · Prepare data**, retain **September 2025 — development**. Check windows: warmup28Aug→1Sep2025; evaluation1Sep→1Oct; tail1Oct00:00→06:05. Click **Prepare data** once. It reuses September and acquires only missing ranges; actual source availability and byte size are measured here, so no download-time promise.

When the job is terminal (COMPLETED, FAILED or CANCELLED), click **Copy preparation report for chat** and send it to the Director. Ready/Ready with limitations is a preparation result; full feed and economic outcomes are not tested. Do not start the data/engine check, Deep validation, other months or a backtest for this handoff. On failure, copy the report as-is rather than retrying blindly. This preparation is authorized after acceptance; it is not a prerequisite for drafting WP-009.

Next Director task: specify the integrated WP-009 implementation/semantic.v2/UI/evaluation acceptance against MP-001 and the accepted substrate. No executor work or economic run assigned yet.
