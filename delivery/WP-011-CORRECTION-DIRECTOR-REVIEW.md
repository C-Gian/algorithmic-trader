# WP-011 correction — Director review
Date: 2026-10-06. Product reviewed: `9b05a3e4bd3767ea627fa821ceaea3a32da34460` (base ed64d05).
Disposition: **F1/F2 CLOSED; ONE BOUNDED COMPATIBILITY FOLLOW-UP REQUIRED.**
No Owner development comparison/economic run activated. CI remains PENDING / NOT CHECKED by Director (Owner-operated).

## F1/F2 closure
Read the correction delta and tests. Independently ran tests/test_mp002_correction.py: 25 passed, and reran both original full-path Director probes: F1 true, F2 true.
F1 retains the dispatch-entry B ownership for the same-dispatch far-edge retirement while V/protective contact keeps precedence; the old box retires once and births nothing. Earlier-dead episodes/wicks/inside-return remain controls.
F2 initializes a sample's activation from its own principal's confirmation known at the cutoff; the later-confirmation handler still credits ARMED samples causally. No baseline v0.2 mutation.
The comparison dislocation limitation and A destination-before-confirmation diagnosis satisfy the requested additions.
Independent review used no DB, browser, full suite or economic run. Executor DB/E2E evidence is read, not represented as independently rerun; final exact-SHA full CI/compose success is still required.

## Additional dependency snapshot — authorized purpose, incomplete compatibility
Keeping the prior dispatch dependency snapshot in v0.3 state is within the required direct-restore determinism scope. Accept that purpose; keep v0.2 frozen and its limitation disclosed. It preserves uninterrupted professional semantics and repairs new-state restore metadata.
However, the claimed backward compatibility is not true through the production codec.

## F3 — blocking: absent optional deps breaks exact old-state round trip
The new `core3.decode` accepts absent `v3.deps`, but `core3.encode` always adds `deps: []`. `engine.unpack_runtime` compares canonical re-encoding with the original verified bytes and therefore rejects the old v3 blob as `adviser state does not round-trip exactly`.
The added test calls AdviserRuntimeV3.decode directly, bypassing this production guard. A syntactically valid legacy v3 state with the same pinned method, config and correct SHA fails; the new shape passes. This can reject every legacy v3 restore point, affecting restore/fallback and diagnostics on pre-correction engineering runs; it is not damaged storage.
Evidence: [production-codec probe](evidence/WP-011-CORRECTION-DIRECTOR-PROBE.py), [results](evidence/WP-011-CORRECTION-DIRECTOR-PROBE.json). Complete synthetic engine configuration, no monkeypatch, DB or Owner data access.

### Required bounded fix
Preserve the exact verified legacy shape when decoding/re-encoding a state that lacks deps, through unpack_runtime before any dispatch mutation. Distinguish absent from a present empty snapshot. New states/checkpoints keep the snapshot; after a genuine subsequent dispatch, a legacy state can emit the new optional field with the actual recomputed snapshot.
Do not disable the exact round-trip guard, normalize arbitrary stored bytes, ignore the blob SHA, broadly tolerate unknown/incompatible shapes, rewrite old restore points/artifacts/results, or replay the prefix to recover missing metadata. The snapshot missing in a legacy checkpoint cannot be invented: retain/disclose that legacy first-dispatch metadata limitation where needed, while new snapshots restore exactly.
The original v0.3 format may remain with an optional compatible field; no method/numerical/public-contract revision is needed for this compatibility correction.

### Verification and completion
Use an actual old-shape fixture produced by the reviewed f1a8023/ed64d05 codec, plus a new snapshot-present fixture. Check production pack/unpack exact byte/hash round trip for absent, present-empty and present-nonempty states; continuation creates an honest new snapshot; wrong SHA/corrupt bytes/incompatible state still fail. Include a bounded DB restore/diagnostic integration path with an old restore blob; do not only call decode. Test direct restore equality for new snapshots around the relevant hourly boundaries and preserve F1/F2 guards.
Run the new targeted codec/restore tests and affected MP-002 pure/DB-required tests. No routine repeat of the 26-minute local full suite, E2E or benchmark for an isolated state-codec correction; widen only if a new failure or wider change requires it. Full exact-SHA CI and compose-smoke remain Owner-operated prerequisites.
Update evidence/STATE/README with precise compatibility claims. Completion: **READY FOR DIRECTOR REVIEW — WP-011 COMPATIBILITY FOLLOW-UP ONLY**.
No new feature, source, method change, acquisition, economic evaluation or Owner handoff.
