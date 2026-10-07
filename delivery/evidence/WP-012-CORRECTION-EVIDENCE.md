# WP-012 correction F1 — evidence

Base `85ee150`; reviewed product `e434d43`. Scope: [Director review](../WP-012-DIRECTOR-REVIEW.md) F1 only. MP-003 is unchanged. This is executor evidence, **not acceptance**. No economic run, Owner data or protected access. The Owner handoff stays INACTIVE.

Structured data:
- [JSON](WP-012-CORRECTION-EVIDENCE.json): probe before/after, fail-before/fixed-after, identity effects.
- [Director probe](WP-012-DIRECTOR-PROBE.py).

## Defect and fix

`core4._local_contact` tested only the current V for an interval ending after the current anchor's publication. If an interval straddled a supersession and reached only the superseded V (active in the interval's earlier part), the contact was ignored, and the new anchor could later confirm.

The fix (`src/algotrader/adviser/core4.py`) evaluates every anchor domain that actually overlaps the interval:
- **Superseded domains** are tested only where they overlap: [publication, successor publication).
- **Domains that ended by a loss** belong to dead anchors and are never re-tested.
- **Classification of a touch:**
  - interval wholly in the current domain → certified contact (unchanged);
  - straddling the current publication, touching the current V → `ANCHOR_CONTACT_TIME_AMBIGUOUS` (unchanged);
  - straddling, touching only a superseded V → **new** `SUPERSEDED_ANCHOR_CONTACT_TIME_AMBIGUOUS_EPOCH_n`;
  - interval ending at or before the current publication → `LATE_CONTACT_WITH_EARLIER_ANCHOR_EPOCH_n` (unchanged).

Each ambiguous case makes the current anchor UNASSESSABLE. The same owner returns to WATCH (unless a structural terminal applies) and the contact-interval end is kept as the replacement cutoff. No intrabar order is inferred.

To distinguish the two kinds of ended domain, a closed domain entry now records how it ended (`SUPERSEDED` / `LOST`) as a fifth element. Confirmation, WAIT/call/evaluator, deadlines, prospective replacement and every other rule are unchanged.

## Results

**Director probe** (`PYTHONPATH=tests uv run python delivery/evidence/WP-012-DIRECTOR-PROBE.py`):

| | LONG | SHORT |
|---|---|---|
| before (e434d43) | REVISE 04:00:30 e2 → **CONFIRM 04:14 e2** | same (mirrored) |
| after | REVISE 04:00:30 e2 → **ANCHOR_LOST 04:01 e2 UNASSESSABLE** (SUPERSEDED_…_EPOCH_1) → REARM 04:15:30 e3 (bar ending after the cutoff) → CONFIRM 04:17 e3 | same |

Epoch 2 never confirms. The later genuine replacement is allowed, as the review states.

**Regressions** (`tests/test_mp003_correction.py`, LONG and SHORT):
- **F1 full tape:** records, `previous_anchor` (epoch 2, V2, interval [04:00,04:01), cutoff 04:01), owner OCCUPIED, unchanged original deadline, prospective REARM source/publication.
- **Controls:**
  - neither active-domain V touched (epoch 2 confirms at 04:14);
  - new V reached in the straddling interval (existing ambiguity);
  - a minute wholly after the supersession that touches only the old V (no contact: the inactive level is not resurrected);
  - a dead lost domain is never re-tested (a single loss).
- **Production pack/unpack** (`engine.pack_runtime` / `engine.unpack_runtime` with exact canonical round trip and hash guards): cuts at 04:00:15 (before the supersession), 04:00:45 (after it, before the contact), 04:01:15 (after the contact) and 04:15:45 (after the replacement). Outputs are byte-identical to the uninterrupted fold.
- **Live path** (recorded receipts: the supersession publishes at 04:00:01.5, so the next minute always straddles it):
  - restarts from the persisted LiveDriver state before the supersession, between the supersession and the contact, and after the contact all reproduce the uninterrupted structural lineage;
  - **durable** case: production `LiveStore.save` every minute into a disposable database, restart from `LiveStore.load_state()` between the supersession and the contact, stored journal equals the uninterrupted lineage.

Historical pack runs publish only on minute boundaries (modeled availability), so a straddling supersession is unreachable there. Their existing durable restore/cadence suite (`tests/test_mp003_db.py`) still passes.

**Fail-before / fixed-after.** The same module (12 pure cases) was run in a worktree of `e434d43`; the worktree's own source was verified to be imported.
- Before: 6 failed (F1 L/S, single-loss control L/S, pack/unpack L/S, all of which require the loss) and 6 controls passed.
- After: 12 passed.

No expected fixture was changed to accept the erroneous confirmation.

**Relevant suites after the fix** (disposable PostgreSQL 18.6, port 55439, `ALGOTRADER_REQUIRE_DB=1`; Owner stack untouched):
- **Command:** `uv run pytest tests/test_mp003_correction.py tests/test_mp003_paths.py tests/test_mp003_versions.py tests/test_mp003_live.py tests/test_mp003_db.py tests/test_mp002_state_compat.py tests/test_mp002_versions.py tests/test_mp002_paths.py tests/test_mp002_rules.py`.
- **Result:** **208 passed**. This includes the 38 v0.2/v0.3 fixed-fixture byte pins, the v0.3 legacy-state compatibility, v0.4 durable crash/reclaim/STEP/Deep, and the existing late-epoch, straddle, first-arm-origin, destination-collision and ordinary-replacement fixtures, all unchanged.

Not rerun (only `core4.py` and tests changed): the full 42-minute suite, the browser suite, the benchmark and Compose. Exact-SHA CI is Owner-operated: **PENDING / NOT CHECKED**.

## Identity and compatibility effects

- **Unchanged:** method, rules manifest, register, model/rules version, implementation id `adviser.core.v4`, state/runtime formats, contracts (semantic.v2 r3, observe.v1 r7, adviser-evaluation.v1 r3).
- **v0.4 behaviour change:** a v0.4 run on a tape containing such a straddling interval now loses the anchor. v0.4 has never been activated for Owner runs, so no stored Owner result is affected.
- **Pre-correction states:** v0.4 states written by `e434d43` decode unchanged (four-element domain entries). An old closed entry without its end kind is treated as superseded, the conservative choice.
- **v0.2/v0.3:** code and outputs are untouched.

READY FOR DIRECTOR REVIEW — WP-012 CORRECTION ONLY
