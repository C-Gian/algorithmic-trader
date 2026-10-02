"""Bounded terminal reconciliation for streaming runs (validator ``observe.stream-reconciliation`` v1).

What it checks (no history replay, no per-event records):

1. committed input ranges are contiguous from cursor 0 to the committed cursor, without gaps, overlaps or
   duplicates, and their counts sum to the cursor;
2. the rolling input commitment chains across ranges and ends at the terminal checkpoint's commitment;
3. the terminal restorable state verifies (format, compatibility fingerprint, SHA-256, exact round-trip),
   its cursor equals the committed cursor, and a snapshot materialized from it has the committed digest;
4. every feed-cache partition still matches its pinned SHA-256 (file hashing only; no decoding/applying);
5. for COMPLETED runs: the cursor equals the feed event count and the final commitment equals the cache's
   full-stream commitment, i.e. every canonical event was consumed exactly once in canonical order.

It does NOT re-execute the reducer against an independent reference. Equivalence of the incremental kernel
with the pure reference reducer is established by differential tests; full Deep validation is R1C scope.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from typing import Any

from .contracts import ReplayStatus, ReplayValidation, ValidationCheck, ValidationOutcome
from .feedcache import FeedCache, initial_commitment
from .kernel import StateError, fingerprint, unpack_state

VALIDATOR_ID = "observe.stream-reconciliation"
VALIDATOR_VERSION = "1"
VALIDATOR_SCOPE = (
    "Bounded terminal reconciliation of a streaming run: committed range continuity, rolling input commitment "
    "chain against the immutable feed cache, verified terminal restorable state and committed snapshot digest, "
    "feed-cache partition integrity and (completed runs) exactly-once consumption of the whole canonical stream. "
    "Not a full reference re-execution: kernel/reference equivalence is covered by differential tests; Deep "
    "validation is planned (R1C).")

Hook = Callable[[str, int, int | None, str], None]


class ReconcileCancelled(Exception):
    pass


def reconcile(*, status: ReplayStatus, cache: FeedCache, ranges: list[dict[str, Any]], cursor: int,
              terminal: dict[str, Any] | None, committed_snapshot_digest: str, engine: dict[str, Any],
              freshness, hook: Hook) -> tuple[ReplayValidation, Any]:
    """Returns (validation, terminal snapshot or None). ``hook`` may raise OperationCancelled."""
    from ..ops import OperationCancelled

    checks: list[ValidationCheck] = []

    def check(name: str, ok: bool, detail: str) -> None:
        checks.append(ValidationCheck(name=name, passed=ok, detail=detail))

    def result(outcome: ValidationOutcome) -> ReplayValidation:
        return ReplayValidation(passed=outcome == ValidationOutcome.PASSED, checks=tuple(checks), outcome=outcome,
                                validator=VALIDATOR_ID, validator_version=VALIDATOR_VERSION, scope=VALIDATOR_SCOPE)

    # 1. range continuity
    expect, problems = 0, []
    for r in ranges:
        if r["from_cursor"] != expect:
            problems.append(f"range {r['range_seq']} starts at {r['from_cursor']}, expected {expect}")
        if r["event_count"] != r["to_cursor"] - r["from_cursor"]:
            problems.append(f"range {r['range_seq']} count mismatch")
        expect = r["to_cursor"]
    if expect != cursor:
        problems.append(f"ranges end at {expect}, committed cursor is {cursor}")
    check("committed_ranges_contiguous", not problems,
          "; ".join(problems) or f"{len(ranges)} committed ranges cover [0, {cursor}) exactly once")
    # 2. commitment chain
    h = initial_commitment(cache.cache_id).hex()
    chain_bad = None
    for r in ranges:
        if r["commitment_before"] != h:
            chain_bad = f"range {r['range_seq']} commitment_before does not continue the chain"
            break
        h = r["commitment_after"]
    terminal_commit = terminal["commitment"] if terminal else None
    check("input_commitment_chain", chain_bad is None and h == terminal_commit,
          chain_bad or f"rolling input commitment chains through all ranges to {str(h)[:16]} (terminal checkpoint)")
    # 3. terminal state
    snap = None
    if terminal is None:
        check("terminal_state_verified", False, "no terminal restorable checkpoint exists")
    else:
        try:
            if terminal["state_format"] != engine["state_format"] or terminal["fingerprint"] != fingerprint(
                    cache.cache_id, freshness):
                raise StateError("format/compatibility fingerprint mismatch")
            state = unpack_state(bytes(terminal["state_blob"]), terminal["state_sha256"])
            if state.cursor.applied_events != cursor or terminal["cursor"] != cursor:
                raise StateError(f"terminal state cursor {state.cursor.applied_events} != committed {cursor}")
            from .kernel import Kernel

            snap = Kernel(cache.feed_meta, freshness, state, b"").snapshot()
            if snap.content_digest != committed_snapshot_digest or snap.content_digest != terminal["snapshot_digest"]:
                raise StateError("snapshot materialized from the terminal state differs from the committed digest")
            check("terminal_state_verified", True, f"terminal state (cursor {cursor}) verified; snapshot digest "
                                                   f"{snap.content_digest[:16]} equals the committed digest")
        except StateError as exc:
            snap = None
            check("terminal_state_verified", False, str(exc))
    # 4. cache integrity (file hashing only)
    bad = []
    try:
        parts = cache.partitions
        for i, p in enumerate(parts):
            hook("verify feed-cache partitions", i, len(parts), "partitions")
            data = (cache.path / p["file"]).read_bytes()
            if hashlib.sha256(data).hexdigest() != p["sha256"]:
                bad.append(p["file"])
        hook("verify feed-cache partitions", len(parts), len(parts), "partitions")
    except OperationCancelled:
        check("validation_completed", False, "cancelled while verifying feed-cache partitions; assurance INCOMPLETE")
        return result(ValidationOutcome.INCOMPLETE), None
    except OSError as exc:
        bad.append(f"unreadable: {exc}")
    check("feed_cache_integrity", not bad, f"{len(cache.partitions)} partitions match their pinned SHA-256"
          if not bad else f"mismatch: {', '.join(bad)}")
    # 5. completed: exactly-once consumption of the whole canonical stream
    if status == ReplayStatus.COMPLETED:
        ok = cursor == cache.event_count and terminal_commit == cache.manifest["final_commitment"]
        check("completed_consumed_entire_feed", ok,
              f"cursor {cursor}/{cache.event_count}; final commitment "
              f"{'equals' if terminal_commit == cache.manifest['final_commitment'] else 'differs from'} the "
              "cache's full-stream commitment")
    check("observation_only", snap is None or set(snap.labels) >= {"OBSERVATION_ONLY", "NO_INTERPRETATION"},
          "observation-only snapshot labels; no MarketView/decision/order/account records")
    outcome = ValidationOutcome.PASSED if all(c.passed for c in checks) else ValidationOutcome.FAILED
    return result(outcome), snap
