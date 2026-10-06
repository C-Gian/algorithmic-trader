# WP-011 correction — executor engineering evidence

Date: 2026-10-06. Base `ed64d05` (Director review of product `f1a8023`). Scope: [Director review](../WP-011-DIRECTOR-REVIEW.md) F1, F2, the comparison dislocation limitation and the A destination-before-confirmation diagnostic. **READY FOR DIRECTOR REVIEW — WP-011 CORRECTION ONLY**; not accepted. No economic run, acquisition, protected window, replay of real data or Owner handoff. Machine-readable: [JSON](WP-011-CORRECTION-EVIDENCE.json).

## Changes

| Item | Change | Files |
|---|---|---|
| F1 | `dispatch` snapshots the B episodes alive at dispatch entry (sid, direction, owner); `_box_close_flags` derives the opposite far-edge retirement from that snapshot. Protective call contact and scenario V contact keep precedence (they still run first and end the episode); the episode's own cancellation is moot once it is dead; the box retires once and births nothing. Episodes dead before the dispatch are not in the snapshot (no resurrection). Called without a snapshot (white-box), the helper snapshots the current map as before. | `src/algotrader/adviser/core3.py` |
| F2 | `EvaluatorV3._sample` records the principal's confirmation when the principal scenario in the core state at the sample cutoff is CONFIRMED with `conf_at <= h` (equals the CONFIRM `published_at`). An ARMED principal is still credited only by its own later CONFIRM (`on_journal`). No other scenario is consulted, nothing is replayed; the activation is kept in the pending sample (already durable evaluator state). v0.2 `evaluator.py` untouched. | `src/algotrader/adviser/evaluator3.py` |
| Restore found while running the review's restore checks | Records emitted during a dispatch's sealed ingestion (e.g. a 1h landmark) carry the previous dispatch's dependency snapshot, which was not in the restorable state: a direct restore just before 04:00/06:00 gave those landmark envelopes empty `dependencies` (digest mismatch; present at `f1a8023`, reproduced). v0.3 state now carries the snapshot (`core.v3.deps`, optional on decode: earlier v3 states decode as before). Uninterrupted outputs unchanged. **v0.2 has the same metadata-only defect and is left frozen** (disclosed in README). | `core3.py` |
| Comparison limitation | `adviser.comparison.v1` adds `limitations` (`V02_DISLOCATION_BASELINE_DEFECT_CORRECTED_IN_V03` for a v0.2/v0.3 pair), a *Comparison limitations* Markdown section, scope wording and a Workbench notice (`compare-limitations`); the v0.3 registered summary includes the destination-first count. Additive JSON field; comparisons are computed on read, nothing stored changes. The inactive Owner handoff text in [WP-011 evidence](WP-011-ENGINEERING-EVIDENCE.md) states the same. | `compare.py`, `web/src/api.ts`, `web/src/views/Backtest.tsx` |
| A destination before confirmation | `adviser.report.v3` funnel `a_destination_before_confirmation` (count, by direction, ≤3 examples with K/destination/time/reason, note), a diagnosis line when non-zero and a Markdown line (tolerant of reports built before it). Derived from journal records only; K/destination rules unchanged. Additive. | `report3.py` |

No numerical value, method rule, source, v0.2 file or saved output changed.

## Fail-before / fixed-after

Fail-before = new tests with `src/` and `web/` reverted to the reviewed code (`git stash`), fixed-after = this working tree.

| Check | Reviewed code | Corrected |
|---|---|---|
| Director probe script F1 / F2 `expected_property` | false / false | true / true ([output](WP-011-CORRECTION-PROBES.json)) |
| `tests/test_mp002_correction.py` (25 pure tests) | 13 failed, 12 passed | 25 passed |
| `test_mp002_db.py` new durable F1/F2 + paired comparison | 3 failed | 7/7 passed (whole file) |

Failing before (as designed): simultaneous collision LONG/SHORT × child issued/economically rejected (retirement 0 at 05:00, B SHORT/LONG born from the old box, retired only at 05:15); white-box snapshot retirement; already-confirmed A LONG/SHORT samples (1h/4h false); pause/restore around 04:00, 05:00, 06:00 (activation false; at 04:00/06:00 also the landmark dependency digest); comparison limitation; destination-first diagnostic; v3 state snapshot compatibility. Durable: retirement observed 05:15 instead of 05:00, activation false, no limitation.

Passing before and after (controls): returned-inside close above the far edge (V contact ends B, box kept); earlier wick only (B ends 04:51, box kept); episode dead before the dispatch (no retirement at 05:00, the unchanged rules treat the close as a fresh opposite B break); direct restore around 05:00 for all four F1 variants (digests equal, BOX_RETIRED lineage `[box id]`, resulting box token); never-confirmed ARMED principal (false/false); white-box wrong scenario (another scenario's CONFIRM never credited; own later CONFIRM 06:10 → 1h false, 4h true; a later-than-cutoff confirmation never counts).

Resulting box token after the corrected retirement: retirement sets `NEED_FALSE`; the unchanged box-birth rule then sees the same close's non-compression phase → `READY` (no replacement box in that dispatch).

## Checks actually run (local, Windows, Python venv, disposable PostgreSQL 18.3 on port 55439 in the session scratchpad; Owner stack untouched)

- Pure: `test_mp002_correction/paths/rules/versions/live` + all `test_adviser_*` → 189 passed, 22 skipped (DB not configured in that run; the DB files were then run separately with `ALGOTRADER_REQUIRE_DB=1`).
- DB (`ALGOTRADER_REQUIRE_DB=1`): `test_mp002_db.py` 7 passed (v0.3 pure≡durable, cadence/crash/reclaim/step/corrupt restore, method pinning, Deep v7 match/tamper, paired comparison, 2 new correction tests with crash/reclaim at the 05:00 boundary); `test_adviser_correction_db`, `test_adviser_integration`, `test_adviser_live_db`, `test_adviser_correction_live_db`, `test_adviser_correction_versions`, `test_evaluation`, `test_observe`, `test_ux_wording` → 49 passed.
- Browser: full E2E `tests/e2e` 19 passed (MP-002 journey now asserts the visible limitation and the copied Markdown section).
- Web typecheck + build; `algotrader schema` baselines match (no contract change).
- **Not run locally:** the full ~26-minute suite and compose-smoke (unaffected areas; CI on the exact SHA is required and Owner-operated). Remote CI: PENDING / NOT CHECKED.

## Remaining limits

- v0.2 restore envelope-dependency defect (above) stays in the frozen baseline.
- The F2 activation is a sample-time fact; samples with no anchor (emitted immediately) cannot later be credited by a CONFIRM after the cutoff — unchanged MP-001 behavior.
- Report/comparison additions are additive without a version bump; readers tolerate their absence.
- Owner October/November/December comparison remains INACTIVE until Director engineering acceptance.

> Erratum (2026-10-06, compatibility follow-up): the claim above that earlier v3 states "decode as before" held only for direct `decode`; the production `unpack_runtime` round-trip guard rejected them (Director F3). Corrected and evidenced in [WP-011-COMPAT-EVIDENCE.md](WP-011-COMPAT-EVIDENCE.md).
