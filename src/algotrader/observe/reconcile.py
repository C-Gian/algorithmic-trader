"""Bounded terminal reconciliation for streaming runs (validator ``observe.stream-reconciliation`` v2).

Assurance layers (WP-008-R1C):

* **Admission** (preparation): private verified source snapshot, trusted cache receipt, SHA-256-pinned
  partitions verified before any of their events is applied.
* **Runtime** (every admitted event, in the kernel): cache position == cursor (total-order continuity), the
  accepted reducer's strict order / unique-slot / channel checks, rolling input commitment; at every checkpoint
  the causal-cutoff snapshot and a fenced cursor compare-and-set.
* **Terminal** (this module, bounded - no history replay, no per-event records, no state rebuild):

  1. committed ranges: positive counts, contiguous [0, cursor), first/last order keys ordered within and
     strictly increasing across ranges;
  2. exact consumed input: every committed line is re-hashed from the verified cache partitions and the
     rolling input commitment is recomputed; it must equal each range's recorded commitment and the terminal
     checkpoint commitment (proves which bytes were consumed, in which order, exactly once);
  3. range boundary order keys equal the canonical cache keys at those positions;
  4. terminal restorable state (format, compatibility fingerprint, SHA-256, exact round-trip, cursor) and a
     snapshot materialized from it equal the committed state/snapshot digests (and the last range's);
  5. cache manifest SHA-256 == run pin == trusted receipt; every partition matches its pinned SHA-256. The
     trusted receipt is REQUIRED: an absent receipt, or one whose manifest/event count differs, fails the check
     and can never yield PASS (R1C correction of v2; reports stored before it keep their recorded check
     details, where an absent receipt is named "not supplied");
  6. completed runs: cursor == feed event count and final commitment == the cache's full-stream commitment.

  Separate commitments are reported: input (rolling prefix commitment), state (state SHA-256 / snapshot
  digest) and output (SHA-256 of the committed range records).

* **Temporal** (version 3, ``observe.stream.v2`` runs only; R1B/R1C runs keep version 2 and its claims):

  7. every committed range records the temporal state SHA-256, the combined temporal output commitment, the
     aggregate chain and the dispatch sequence; dispatch sequences never decrease;
  8. the terminal temporal restore state (format, profile/context fingerprint pinned at preparation, SHA-256, exact
     round-trip, cursor == committed cursor) equals the last range's recorded temporal SHA-256 / commitment;
  9. completed runs: the finite clock-end finish (declared ``clock_end``) is derived deterministically from that
     verified terminal state, without reading any event beyond the committed cursor.

  This verifies the integrity of the committed temporal state and its recorded commitments. It is NOT an
  independent temporal re-execution; that is the optional Deep validation (v2 for temporal runs).

* **Reference** (outside normal runs): protected differential and hand-expected fixtures in the test suite,
  and the optional, explicitly launched Deep validation job. A normal run never performs an independent
  reference replay; its wording says so.
"""

from __future__ import annotations

import gzip
import hashlib
from collections.abc import Callable
from typing import Any

from ..feed.ordering import canonical
from .contracts import ReplayStatus, ReplayValidation, ValidationCheck, ValidationOutcome
from .feedcache import FeedCache, decode, extend_commitment, initial_commitment, order_sort_key
from .kernel import StateError, fingerprint, restore_temporal, unpack_state

VALIDATOR_ID = "observe.stream-reconciliation"
VALIDATOR_VERSION = "2"
VALIDATOR_SCOPE = (
    "Runtime integrity verified, engine reference-tested: bounded terminal reconciliation of a streaming run - "
    "committed range continuity and order bounds, exact re-hash of every consumed input line against the "
    "receipt-pinned feed cache with the rolling input commitment recomputed at every range boundary, verified "
    "terminal restorable state and snapshot digest, cache/receipt/partition integrity and (completed runs) "
    "exactly-once consumption of the whole canonical stream. No independent reference replay was performed in "
    "this run: kernel/reference equivalence is covered by protected differential fixtures and by the optional "
    "Deep validation job.")

VALIDATOR_VERSION_TEMPORAL = "3"
VALIDATOR_SCOPE_TEMPORAL = VALIDATOR_SCOPE + (
    " Version 3 (temporal-enabled observe.stream.v2 runs) additionally verifies the committed temporal substrate: "
    "temporal state SHA-256, output/aggregate commitments and dispatch sequence recorded at every committed range; "
    "the terminal temporal restore state (pinned profile fingerprint, exact round-trip, cursor) equal to the last "
    "range's records; and, for completed runs, the clock-end finish derived from that verified state. No independent "
    "temporal re-execution was performed in this run (optional Deep validation v2).")

VALIDATOR_VERSION_PACK = "4"
VALIDATOR_SCOPE_PACK = VALIDATOR_SCOPE_TEMPORAL + (
    " Version 4 (evaluation-pack runs, source kind pack) additionally verifies the pack pins: the pack manifest file "
    "SHA-256 equals the run pin and the trusted publication receipt, its body re-hashes to the pack id, and its "
    "feed cache id/manifest SHA-256 equal the run's pinned cache. Consuming the whole canonical feed is reported "
    "separately from per-minute source coverage: a completed pack run can contain explicit source gaps.")

Hook = Callable[[str, int, int | None, str], None]


def _key(display: str) -> bytes:
    return display.replace("|", "\x00").encode()


def output_commitment(ranges: list[dict[str, Any]]) -> str:
    h = hashlib.sha256(b"algotrader.observe.output-ranges.v1\x00")
    for r in ranges:
        h.update(canonical({k: r.get(k) for k in ("range_seq", "from_cursor", "to_cursor", "event_count",
                                                  "first_order", "last_order", "commitment_before",
                                                  "commitment_after", "snapshot_digest", "state_sha256")}) + b"\n")
    return h.hexdigest()


def reconcile(*, status: ReplayStatus, cache: FeedCache, ranges: list[dict[str, Any]], cursor: int,
              terminal: dict[str, Any] | None, committed_snapshot_digest: str, engine: dict[str, Any],
              freshness, hook: Hook, receipt: dict[str, Any] | None = None,
              temporal_out: dict[str, Any] | None = None,
              pack: dict[str, Any] | None = None) -> tuple[ReplayValidation, Any]:
    """Returns (validation, terminal snapshot or None). ``hook`` may raise OperationCancelled. For temporal runs the
    verified (and, when completed, clock-end finished) temporal summary is written to ``temporal_out``."""
    from ..ops import OperationCancelled

    checks: list[ValidationCheck] = []
    commitments: dict[str, Any] = {}

    def check(name: str, ok: bool, detail: str) -> None:
        checks.append(ValidationCheck(name=name, passed=ok, detail=detail))

    temporal_cfg = engine.get("temporal")
    version, scope = ((VALIDATOR_VERSION_PACK, VALIDATOR_SCOPE_PACK) if engine.get("pack") else
                      (VALIDATOR_VERSION_TEMPORAL, VALIDATOR_SCOPE_TEMPORAL) if temporal_cfg
                      else (VALIDATOR_VERSION, VALIDATOR_SCOPE))

    def result(outcome: ValidationOutcome) -> ReplayValidation:
        return ReplayValidation(passed=outcome == ValidationOutcome.PASSED, checks=tuple(checks), outcome=outcome,
                                validator=VALIDATOR_ID, validator_version=version, scope=scope)

    # 1. range continuity, positive counts and order bounds
    expect, problems, prev_last = 0, [], None
    for r in ranges:
        if r["from_cursor"] != expect:
            problems.append(f"range {r['range_seq']} starts at {r['from_cursor']}, expected {expect}")
        if r["event_count"] <= 0 or r["event_count"] != r["to_cursor"] - r["from_cursor"]:
            problems.append(f"range {r['range_seq']} count {r['event_count']} is not positive/consistent")
        first, last = _key(r["first_order"]), _key(r["last_order"])
        if first > last:
            problems.append(f"range {r['range_seq']} first order key is after its last")
        if prev_last is not None and first <= prev_last:
            problems.append(f"range {r['range_seq']} does not start strictly after the previous range")
        prev_last = last
        expect = r["to_cursor"]
    if expect != cursor:
        problems.append(f"ranges end at {expect}, committed cursor is {cursor}")
    check("committed_ranges_contiguous", not problems,
          "; ".join(problems[:5]) or f"{len(ranges)} positive committed ranges cover [0, {cursor}) exactly once, "
                                      "order bounds strictly increasing")
    # 2. recorded commitment chain
    h = initial_commitment(cache.cache_id).hex()
    chain_bad = None
    for r in ranges:
        if r["commitment_before"] != h:
            chain_bad = f"range {r['range_seq']} commitment_before does not continue the chain"
            break
        h = r["commitment_after"]
    terminal_commit = terminal["commitment"] if terminal else None
    check("input_commitment_chain", chain_bad is None and h == terminal_commit,
          chain_bad or f"recorded input commitments chain through all ranges to {str(h)[:16]} (terminal checkpoint)")
    # 3. cache identity: manifest == run pin == trusted receipt
    pin = engine.get("cache_manifest_sha256")
    if receipt is None:
        check("cache_receipt_and_pin", False,
              f"no trusted receipt exists for cache {cache.cache_id} (run pin {str(pin)[:16]}): the cache cannot be "
              "tied to its verified preparation; assurance cannot pass")
    else:
        rec, rec_count = receipt.get("cache_manifest_sha256"), receipt.get("event_count")
        count_ok = rec_count is None or rec_count == cache.event_count
        check("cache_receipt_and_pin", cache.manifest_sha256 == pin == rec and count_ok,
              f"cache manifest {cache.manifest_sha256[:16]}, run pin {str(pin)[:16]}, trusted receipt {str(rec)[:16]}"
              + ("" if count_ok else f"; receipt event count {rec_count} != cache {cache.event_count}"))
    # 4. exact consumed input: re-hash every committed line from verified partitions; boundary keys
    bad_parts: list[str] = []
    mismatch = None
    boundaries = {r["to_cursor"]: r for r in ranges}
    starts = {r["from_cursor"]: r for r in ranges}
    ends = {r["to_cursor"] - 1: r for r in ranges}
    try:
        commit = initial_commitment(cache.cache_id)
        parts = cache.partitions
        for i, p in enumerate(parts):
            hook("re-hash consumed input from verified partitions", i, len(parts), "partitions")
            if p["first_seq"] >= cursor:
                # beyond the committed prefix: integrity of the pinned bytes only
                data = (cache.path / p["file"]).read_bytes()
                if hashlib.sha256(data).hexdigest() != p["sha256"]:
                    bad_parts.append(p["file"])
                continue
            data = (cache.path / p["file"]).read_bytes()
            if hashlib.sha256(data).hexdigest() != p["sha256"]:
                bad_parts.append(p["file"])
                continue
            if commit.hex() != p["commitment_before"] and mismatch is None:
                mismatch = f"partition {p['file']} commitment_before differs from the recomputed chain"
            lines = gzip.decompress(data).split(b"\n")[:-1]
            for j, line in enumerate(lines):
                seq = p["first_seq"] + j
                if seq >= cursor:
                    break
                commit = extend_commitment(commit, line)
                if seq in starts and mismatch is None and \
                        order_sort_key(decode(line)) != _key(starts[seq]["first_order"]):
                    mismatch = f"range {starts[seq]['range_seq']} first order key differs from cache position {seq}"
                if seq in ends and mismatch is None and \
                        order_sort_key(decode(line)) != _key(ends[seq]["last_order"]):
                    mismatch = f"range {ends[seq]['range_seq']} last order key differs from cache position {seq}"
                b = boundaries.get(seq + 1)
                if b is not None and commit.hex() != b["commitment_after"] and mismatch is None:
                    mismatch = (f"recomputed input commitment at cursor {seq + 1} differs from range "
                                f"{b['range_seq']}'s recorded commitment")
        hook("re-hash consumed input from verified partitions", len(parts), len(parts), "partitions")
    except OperationCancelled:
        check("validation_completed", False, "cancelled while re-hashing consumed input; assurance INCOMPLETE")
        return result(ValidationOutcome.INCOMPLETE), None
    except OSError as exc:
        bad_parts.append(f"unreadable: {exc}")
    commitments["input"] = commit.hex() if not bad_parts else None
    check("feed_cache_integrity", not bad_parts, f"{len(cache.partitions)} partitions match their pinned SHA-256"
          if not bad_parts else f"mismatch: {', '.join(bad_parts[:5])}")
    check("consumed_input_exact", not bad_parts and mismatch is None and commitments["input"] == terminal_commit,
          mismatch or (f"{cursor} consumed lines re-hashed; recomputed input commitment {str(commitments['input'])[:16]}"
                       " equals every range boundary and the terminal checkpoint"
                       if commitments["input"] == terminal_commit else
                       "recomputed input commitment differs from the terminal checkpoint"))
    # 5. terminal state
    snap = None
    if terminal is None:
        check("terminal_state_verified", False, "no terminal restorable checkpoint exists")
    else:
        try:
            if terminal["state_format"] != engine["state_format"] or terminal["fingerprint"] != fingerprint(
                    cache.cache_id, freshness, engine.get("format") or "observe.stream.v1"):
                raise StateError("format/compatibility fingerprint mismatch")
            state = unpack_state(bytes(terminal["state_blob"]), terminal["state_sha256"])
            if state.cursor.applied_events != cursor or terminal["cursor"] != cursor:
                raise StateError(f"terminal state cursor {state.cursor.applied_events} != committed {cursor}")
            from .kernel import Kernel

            snap = Kernel(cache.feed_meta, freshness, state, b"").snapshot()
            if snap.content_digest != committed_snapshot_digest or snap.content_digest != terminal["snapshot_digest"]:
                raise StateError("snapshot materialized from the terminal state differs from the committed digest")
            last = ranges[-1] if ranges else None
            if last is not None and last.get("snapshot_digest") is not None and (
                    last["snapshot_digest"] != snap.content_digest or last["state_sha256"] != terminal["state_sha256"]):
                raise StateError("terminal state/snapshot differ from the last committed range's recorded digests")
            commitments["state"] = {"state_sha256": terminal["state_sha256"], "snapshot_digest": snap.content_digest}
            check("terminal_state_verified", True, f"terminal state (cursor {cursor}) verified; snapshot digest "
                                                   f"{snap.content_digest[:16]} equals the committed digest")
        except StateError as exc:
            snap = None
            check("terminal_state_verified", False, str(exc))
    # 6. completed: exactly-once consumption of the whole canonical stream
    if status == ReplayStatus.COMPLETED:
        ok = cursor == cache.event_count and terminal_commit == cache.manifest["final_commitment"]
        check("completed_consumed_entire_feed", ok,
              f"cursor {cursor}/{cache.event_count}; final commitment "
              f"{'equals' if terminal_commit == cache.manifest['final_commitment'] else 'differs from'} the "
              "cache's full-stream commitment")
    if temporal_cfg:
        _temporal_checks(check, status, ranges, terminal, cursor, engine, commitments, temporal_out)
    if engine.get("pack"):
        _pack_checks(check, engine, pack or {}, cache, status, cursor)
    commitments["output"] = output_commitment(ranges)
    check("observation_only", snap is None or set(snap.labels) >= {"OBSERVATION_ONLY", "NO_INTERPRETATION"},
          "observation-only snapshot labels; no MarketView/decision/order/account records")
    check("commitments_reported", True,
          f"input {str(commitments.get('input'))[:16]} · state "
          f"{str((commitments.get('state') or {}).get('state_sha256'))[:16]} · output {commitments['output'][:16]} "
          "(three distinct commitments; none substitutes for another)")
    outcome = ValidationOutcome.PASSED if all(c.passed for c in checks) else ValidationOutcome.FAILED
    return result(outcome), snap


def _temporal_checks(check, status: ReplayStatus, ranges: list[dict[str, Any]], terminal: dict[str, Any] | None,
                     cursor: int, engine: dict[str, Any], commitments: dict[str, Any],
                     out: dict[str, Any] | None) -> None:
    from datetime import datetime

    from ..temporal.engine import TemporalError

    problems, prev = [], 0
    for r in ranges:
        if not (r.get("temporal_sha256") and r.get("temporal_commitment") and r.get("aggregate_chain")) \
                or r.get("dispatch_seq") is None:
            problems.append(f"range {r['range_seq']} has no recorded temporal state/commitments")
            continue
        if r["dispatch_seq"] < prev:
            problems.append(f"range {r['range_seq']} dispatch sequence {r['dispatch_seq']} decreases from {prev}")
        prev = r["dispatch_seq"]
    check("temporal_ranges_recorded", not problems,
          "; ".join(problems[:5]) or f"{len(ranges)} ranges record temporal state SHA-256, output/aggregate "
                                     f"commitments and a non-decreasing dispatch sequence (last {prev})")
    if terminal is None:
        check("temporal_state_verified", False, "no terminal restorable checkpoint exists")
        return
    try:
        eng = restore_temporal(terminal, engine)
        if eng.cursor != cursor:
            raise StateError(f"terminal temporal cursor {eng.cursor} != committed {cursor}")
        last = ranges[-1] if ranges else None
        if last is not None and (last["temporal_sha256"] != terminal["temporal_sha256"]
                                 or last["temporal_commitment"] != eng.commitment()
                                 or last["aggregate_chain"] != eng.aggregate_chain
                                 or last["dispatch_seq"] != eng.dispatch_seq):
            raise StateError("terminal temporal state differs from the last committed range's recorded commitments")
        commitments["temporal"] = {"state_sha256": terminal["temporal_sha256"], "output": eng.commitment(),
                                   "aggregate_chain": eng.aggregate_chain, "dispatch_seq": eng.dispatch_seq}
        check("temporal_state_verified", True,
              f"terminal temporal state (cursor {cursor}, profile {engine['temporal']['profile']['profile_id']}, "
              f"{eng.profile.clock_policy.value}) verified; {eng.counters['sealed']} sealed records, "
              f"{eng.dispatch_seq} dispatches, late-excluded {eng.counters['late_excluded']}")
    except (StateError, TemporalError) as exc:
        check("temporal_state_verified", False, str(exc))
        return
    if status == ReplayStatus.COMPLETED:
        try:
            clock_end = datetime.fromisoformat(engine["temporal"]["clock_end"])
            before = eng.dispatch_seq
            eng.finish(clock_end)
            forming = sum(len(t.open) + (0 if t.done() else 1) for t in eng.tracks.values())
            check("temporal_clock_end_finish", eng.clock == clock_end,
                  f"finite clock end {clock_end.isoformat()} derived from the verified terminal state without "
                  f"further input: {eng.dispatch_seq - before} final dispatch(es); {forming} interval(s) still "
                  "unsealed at clock end")
        except TemporalError as exc:
            check("temporal_clock_end_finish", False, str(exc))
    if out is not None:
        out.update(eng.summary(recent=10))
        out["finished_at_clock_end"] = status == ReplayStatus.COMPLETED


def _pack_checks(check, engine: dict[str, Any], pack: dict[str, Any], cache: FeedCache, status: ReplayStatus,
                 cursor: int) -> None:
    from ..corpus.pack import pack_id_for

    pin = engine["pack"]
    rec, doc, file_sha = pack.get("receipt"), pack.get("manifest"), pack.get("file_sha256")
    problems = []
    if rec is None:
        problems.append("no trusted publication receipt for the pack")
    if file_sha is None or doc is None:
        problems.append("pack manifest file missing or unreadable")
    if file_sha is not None and file_sha != pin["pack_manifest_sha256"]:
        problems.append("pack manifest file differs from the run pin")
    if rec is not None and rec["manifest_sha256"] != pin["pack_manifest_sha256"]:
        problems.append("publication receipt differs from the run pin")
    if doc is not None:
        if doc.get("pack_id") != pin["pack_id"] or pack_id_for(doc) != pin["pack_id"]:
            problems.append("pack manifest body does not hash to its identity")
        feed = doc.get("feed") or {}
        if feed.get("cache_id") != cache.cache_id or feed.get("cache_manifest_sha256") != cache.manifest_sha256 \
                or feed.get("cache_manifest_sha256") != engine.get("cache_manifest_sha256"):
            problems.append("pack feed cache identity differs from the run's pinned cache")
    check("pack_receipt_and_pins", not problems,
          "; ".join(problems) or f"pack {pin['pack_id']} manifest {pin['pack_manifest_sha256'][:16]} == run pin == "
                                  f"publication receipt; feed cache {cache.cache_id} pinned")
    if doc is not None:
        bars = [c for c in doc.get("coverage", []) if c.get("expected_slots")]
        expected = sum(c["expected_slots"] for c in bars)
        gaps = sum(c["missing"] + c["rejected"] for c in bars)
        trade = [c for c in bars if c["family"] == "trade_bar_1m"]
        tg = sum(c["missing"] + c["rejected"] for c in trade)
        consumed = status == ReplayStatus.COMPLETED and cursor == cache.event_count
        check("pack_coverage_reported", True,
              f"feed consumed {'entirely' if consumed else f'to cursor {cursor}/{cache.event_count}'}; source "
              f"coverage (separate fact): {gaps} missing/rejected of {expected} expected bar slots, trade "
              f"{tg} missing/rejected of {sum(c['expected_slots'] for c in trade)} (pack status {doc.get('status')})")

