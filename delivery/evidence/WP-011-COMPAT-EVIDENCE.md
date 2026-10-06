# WP-011 compatibility follow-up (F3) — executor engineering evidence

Date: 2026-10-06. Base `32233ec` (Director review of `9b05a3e`: [review](../WP-011-CORRECTION-DIRECTOR-REVIEW.md)). Scope: F3 only. **READY FOR DIRECTOR REVIEW — WP-011 COMPATIBILITY FOLLOW-UP ONLY**; not accepted. No method, numerical, public-contract, v0.2, stored-output or Owner-data change; no economic run or download. Machine-readable: [JSON](WP-011-COMPAT-EVIDENCE.json).

## Fix (`src/algotrader/adviser/core3.py`)

`AdviserCoreV3` keeps a private `_deps_known` flag: True for new cores and after every genuine dispatch (which recomputes the snapshot), False only when a decoded v3 state had **no** `core.v3.deps` key. Encoding writes `deps` only when known, so a legacy state re-encodes to its exact verified bytes. A present empty snapshot (`"deps": []`) stays distinct from an absent one. `engine.unpack_runtime` is unchanged: decompression, SHA-256, decode and the exact canonical round-trip guard still apply to every state; unknown keys, wrong types, non-canonical values, wrong SHA, corrupt bytes and incompatible states still fail. Nothing is normalized, replayed, rewritten or invented. New states and checkpoints keep the snapshot (the 9b05a3e direct-restore repair is retained).

## Legacy fixture produced by the reviewed codec

`tests/fixtures/mp002_legacy_v3_states.json.gz` (16.6 KB): canonical v0.3 runtime states encoded by the reviewed codec itself (`src/` identical at f1a8023 and ed64d05; run from a temporary `git worktree` of ed64d05, imports verified from the worktree) for the synthetic `a3_stall_after_return` fold at three cuts: `before_0400` (event 5037), `inside_0400` (5038, between the first 04:00 event and the 04:00 sealed-ingestion landmarks) and `before_0500` (5217). Generator: [WP-011-COMPAT-LEGACY-FIXTURE-GEN.py](WP-011-COMPAT-LEGACY-FIXTURE-GEN.py). A test proves each equals the current codec's state at the same cut minus `deps`.

## Fail-before (9b05a3e codec, `core3.py` stashed) / fixed-after

| Check | 9b05a3e | Fixed |
|---|---|---|
| Director production-codec probe: legacy / new | rejected (`does not round-trip exactly`) / exact | exact / exact ([output](WP-011-COMPAT-PROBE.json)) |
| `tests/test_mp002_state_compat.py` (20) | 7 failed, 13 passed | 20 passed |
| DB `test_legacy_restore_point_is_restored_and_verified_without_fallback` mid-run 05:00 / final commit | both runs FAILED: legacy point rejected, fallback suffix `_UnsafeRecovery … does not reproduce the committed adviser state` | both completed, assurance passed, no rejection/fallback |

Failing before: absent-snapshot exact round trip (3 cuts), present-empty vs absent distinction, legacy continuation (2 exact cuts + inside_0400). Passing before and after (controls): fixture provenance equality (3), every integrity failure case (wrong SHA, corrupt bytes, unknown v3 key, `deps` null, malformed entry, non-canonical time, v0.2 state under v0.3), production pack/unpack restore of new snapshots around 04:00/05:00/06:00 (digests equal to the uninterrupted fold).

## What a legacy state does after restore (precise claim)

- Restores through production `unpack_runtime` with exact bytes/hash; re-encoded unchanged while no dispatch has run.
- After its first genuine dispatch it writes the recomputed snapshot, byte-identical to the uninterrupted fold's state at that point (`before_0400`, `before_0500`: all journal and evaluator digests identical).
- **Limitation (unknowable metadata, not invented):** records emitted in that first dispatch's sealed ingestion, before the recomputation (here the 04:00 1h landmarks after `inside_0400`), carry empty `env.dependencies`; all other fields, the professional content, every evaluator record and later snapshots are identical. The DB test bounds any such difference to one dispatch time with empty dependencies only.
- Direct DB restore (mid-run) and a reclaim after the final commit both restore the legacy point; terminal reconciliation (`adviser_terminal_state_verified`, `adviser_finish_rederived`) passes. The DB legacy blob is the stored point with `deps` removed, i.e. exactly the reviewed codec's shape (equality proven on the fixtures above).
- Live restore (`LiveDriver.decode`) verifies the SHA without a round-trip guard; a legacy live state now also keeps its shape until the first dispatch (same metadata limitation).

## Not covered — for Director decision

Code reading, not executed: Deep validation v7 re-executes the whole prefix with the current codec and compares each range's stored `adviser_sha256`. For a run whose ranges were written by the pre-9b05a3e codec, those state hashes include no `deps` while the shadow fold's do, so Deep would report `adviser_state` mismatches on such runs (commitments/records unaffected). This is a consequence of the snapshot that 9b05a3e introduced, outside this bounded F3 codec fix; no change made. Pre-correction v0.3 runs exist only as unaccepted engineering runs (Owner comparison never activated).

## Checks actually run (local; disposable PostgreSQL 18.3, port 55439, scratchpad; stopped afterwards; Owner stack untouched)

- Pure: `test_mp002_state_compat/correction/paths/rules/versions/live` → 100 passed, 1 DB skip, then `test_mp002_live.py` with DB 4 passed.
- DB (`ALGOTRADER_REQUIRE_DB=1`): `test_mp002_db.py` (9 incl. 2 new), `test_adviser_correction_live_db.py`, `test_adviser_live_db.py` → 13 passed.
- `algotrader schema`: all baselines match.
- Not run (isolated state-codec change, per review): full ~26-minute suite, E2E, benchmark, compose-smoke. Remote CI: PENDING / NOT CHECKED (Owner-operated).
