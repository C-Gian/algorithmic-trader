"""WP-008-R1B evidence: streaming kernel, immutable feed cache, sparse persistence and direct restore.

Bounded offline engineering fixtures only (captured 20-minute OKX fixture, crafted edge-case feeds and
deterministic synthetic multi-day datasets served through the accepted acquisition path). These are
structural/differential checks, not historical month/year evaluations or performance claims.
"""

from __future__ import annotations

import json
import random
import shutil
import threading
import time
import tracemalloc
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import psycopg
import psycopg.rows
import pytest
from fastapi.testclient import TestClient
from okx_fake import FIXTURE_END, FIXTURE_START, FakeOkx, client
from okx_synth import synthetic_fake

from algotrader.api import create_app
from algotrader.feed.adapter import assemble_feed, build_feed, make_event
from algotrader.feed.contracts import (
    ChannelCoverage,
    ChannelRef,
    EventKind,
    Family,
    MarkBarPayload,
    QualityReason,
    SlotQualityPayload,
    SourceRef,
    TradeBarPayload,
)
from algotrader.feed.ordering import FeedError, default_freshness, modeled_availability
from algotrader.marketdata import dataset as md
from algotrader.observe import control
from algotrader.observe import feedcache as fc
from algotrader.observe.contracts import SourceKind
from algotrader.observe.core import ReplayCore
from algotrader.observe.job import SimulatedCrash
from algotrader.observe.kernel import Kernel, pack_state, unpack_state
from algotrader.observe.worker import ObservationWorker

FRESH = default_freshness()
MIN = timedelta(minutes=1)


@pytest.fixture
def conn(database_url):
    with psycopg.connect(database_url, autocommit=True, row_factory=psycopg.rows.dict_row) as c:
        yield c


def fixture_dataset(root: Path) -> str:
    return md.acquire(client(FakeOkx()), root, FIXTURE_START, FIXTURE_END).manifest.dataset_id


def synthetic_dataset(root: Path, days: int) -> str:
    s = datetime(2026, 9, 1, tzinfo=UTC)
    return md.acquire(client(synthetic_fake(s, s + timedelta(days=days))), root, s, s + timedelta(days=days)
                      ).manifest.dataset_id


def worker(database_url, root, art, **kw) -> ObservationWorker:
    kw.setdefault("worker_id", "observe:stream")
    kw.setdefault("isolate", False)
    kw.setdefault("checkpoint_events", 5)
    kw.setdefault("sleep", lambda s: None)
    return ObservationWorker(database_url, root, art, lease_seconds=5, poll_interval=0.01, **kw)


def drain(w: ObservationWorker) -> None:
    while w.run_once():
        pass


def row_of(conn, rid):
    return conn.execute("SELECT r.*, k.cursor, k.snapshot_digest FROM observation_replays r LEFT JOIN "
                        "observation_checkpoints k USING (replay_id) WHERE replay_id = %s", (rid,)).fetchone()


def ranges(conn, rid):
    return conn.execute("SELECT * FROM observation_ranges WHERE replay_id = %s ORDER BY from_cursor", (rid,)).fetchall()


def expire(conn, rid):
    conn.execute("UPDATE observation_replays SET lease_expires_at = now() - interval '1 second' WHERE replay_id = %s",
                 (rid,))


def gen_counters(row, gen=None):
    return row["metrics"][str(gen or row["lease_generation"])]


def reference(root: Path, ds: str) -> ReplayCore:
    return ReplayCore(build_feed(md.dataset_path(root, ds)), FRESH)


# ---------------------------------------------------------------------------
# 1. Differential: committed checkpoints equal the pure reference at every committed cursor
# ---------------------------------------------------------------------------


@pytest.mark.db
@pytest.mark.parametrize("ckpt,speed", [(1, 0), (3, 0), (7, 0), (5000, 0), (4, 200)],
                         ids=["every-event", "batch3", "batch7", "default-cadence", "paced"])
def test_checkpoint_digests_equal_the_reference_at_every_committed_cursor(database_url, conn, tmp_path, ckpt, speed):
    root, art = tmp_path / "data", tmp_path / "art"
    ds = fixture_dataset(root)
    core = reference(root, ds)
    expected = {0: core.at(0).snapshot.content_digest}
    pos = core.at(0)
    while pos.cursor < core.total:
        pos, _ = core.step(pos)
        expected[pos.cursor] = pos.snapshot.content_digest
    rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=speed)
    seen = []

    def record(replay_id, cursor):
        seen.append((cursor, row_of(conn, replay_id)["snapshot_digest"]))

    drain(worker(database_url, root, art, checkpoint_events=ckpt, after_commit=record))
    row = row_of(conn, rid)
    assert row["status"] == "completed" and row["snapshot_digest"] == expected[core.total]
    assert seen and all(d == expected[c] for c, d in seen), [(c, d[:8], expected[c][:8]) for c, d in seen]
    rs = ranges(conn, rid)
    assert [r["to_cursor"] for r in rs] == [c for c, _ in seen]
    if speed == 0:
        assert all(r["event_count"] == ckpt for r in rs[:-1]) and rs[-1]["event_count"] <= ckpt


@pytest.mark.db
def test_direct_restore_at_many_cursors_reproduces_the_reference(database_url, conn, tmp_path):
    root, art = tmp_path / "data", tmp_path / "art"
    ds = fixture_dataset(root)
    final = reference(root, ds)
    final_digest = final.at(final.total).snapshot.content_digest
    for k in (1, 13, 30, 60):
        rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)

        def crash(replay_id, cursor, k=k, rid=rid):
            if replay_id == rid and cursor == k:
                raise SimulatedCrash()

        with pytest.raises(SimulatedCrash):
            worker(database_url, root, art, worker_id="observe:a", checkpoint_events=1, after_commit=crash).run_once()
        expire(conn, rid)
        drain(worker(database_url, root, art, worker_id="observe:b"))
        row = row_of(conn, rid)
        assert row["status"] == "completed" and row["snapshot_digest"] == final_digest, k
        g2 = gen_counters(row, 2)
        assert g2["events_applied"] == final.total - k and g2["prefix_restore_events"] == 0, (k, g2)
        assert g2["restore_suffix_events"] == 0 and g2["source_verifications"] == 0


# ---------------------------------------------------------------------------
# 2. Crafted edge cases: ties, late arrival, gap, rejection, partition boundaries, end of source, duplicate
# ---------------------------------------------------------------------------

T0 = datetime(2026, 9, 1, 0, 0, tzinfo=UTC)
TRADE = ChannelRef(source="okx", family=Family.TRADE_BAR_1M, series_id="BTC-USDT-SWAP")
MARK = ChannelRef(source="okx", family=Family.MARK_BAR_1M, series_id="BTC-USDT-SWAP")
INDEX = ChannelRef(source="okx", family=Family.INDEX_BAR_1M, series_id="BTC-USDT")
POLICY = modeled_availability()
INSTRUMENT = {"inst_id": "BTC-USDT-SWAP", "index_id": "BTC-USDT"}


def _src(i: int) -> SourceRef:
    return SourceRef(dataset_id="synthetic-edge", artifact="crafted", row_index=i, raw_page_ref=None,
                     retrieved_at=None, source_availability_policy="crafted")


def _trade(t, avail, i, close=100):
    p = Decimal(close)
    return make_event(TRADE, EventKind.BAR_OBSERVATION, t, t + MIN, avail, POLICY, _src(i),
                      TradeBarPayload(open=p, high=p + 1, low=p - 1, close=p, volume_contracts=Decimal(1),
                                      volume_base=Decimal("0.01"), volume_base_ccy="BTC", volume_quote=p,
                                      volume_quote_ccy="USDT"))


def _mark(t, avail, i, close=100):
    p = Decimal(close)
    return make_event(MARK, EventKind.BAR_OBSERVATION, t, t + MIN, avail, POLICY, _src(i),
                      MarkBarPayload(open=p, high=p, low=p, close=p))


def _quality(ch, t, reason, i):
    return make_event(ch, EventKind.SLOT_QUALITY, t, t + MIN, t + MIN, POLICY, _src(i),
                      SlotQualityPayload(reason=reason, detail="crafted"))


def edge_events(suffix_variant: int = 0) -> list:
    t = [T0 + k * MIN for k in range(8)]
    ev = [
        _trade(t[0], t[1], 0), _mark(t[0], t[1], 1),  # tie: same availability -> family rank order
        _quality(INDEX, t[0], QualityReason.MISSING, 2),
        _trade(t[1], t[1] + 5 * MIN, 3, close=101),  # LATE: bar t1 known only at t6
        _trade(t[2], t[3], 4, close=102),  # newer bar known earlier
        _quality(MARK, t[1], QualityReason.INVALID_ROW, 5),  # rejection
        _quality(TRADE, t[3], QualityReason.MISSING, 6),  # gap
        _trade(t[4], t[5], 7, close=104), _mark(t[2], t[3], 8),
    ]
    if suffix_variant:  # future suffix (available strictly after t[6]) differs
        ev += [_trade(t[6], t[7] + suffix_variant * MIN, 9, close=200 + suffix_variant),
               _mark(t[5], t[7] + suffix_variant * MIN, 10, close=300 + suffix_variant)]
    else:
        ev += [_trade(t[6], t[7], 9, close=106)]
    return ev


def coverage():
    return tuple(ChannelCoverage(channel=c, covered_from=T0, covered_until=T0 + 8 * MIN, expected_cadence=MIN)
                 for c in (TRADE, MARK, INDEX))


def build(root: Path, events: list, name: str) -> fc.FeedCache:
    key = {"crafted": name, "format": fc.CACHE_FORMAT}
    shuffled = list(events)
    random.Random(7).shuffle(shuffled)  # any input order: the cache establishes the canonical order
    return fc.build_cache(root, key, iter(shuffled), coverage, POLICY, ("synthetic-edge",),
                          lambda: ("BTC-USDT-SWAP", "BTC-USDT", INSTRUMENT),
                          lambda: {"quality": "crafted", "exclusions": [], "notes": []})


def test_edge_cases_match_reference_and_hand_expected_order(tmp_path, monkeypatch):
    monkeypatch.setattr(fc, "PARTITION_EVENTS", 2)  # many partition boundaries
    monkeypatch.setattr(fc, "SORT_BLOCK", 3)  # several external-sort spill runs
    events = edge_events()
    ref = assemble_feed(events, coverage(), POLICY, ("synthetic-edge",), "BTC-USDT-SWAP", "BTC-USDT", INSTRUMENT)
    cache = build(tmp_path, events, "edge")
    assert cache.feed_manifest == ref.manifest  # identical canonical identities and counts
    assert len(cache.partitions) == 5
    order = [fc.decode(line).event_id for _s, line in fc.CacheReader(cache).iter_from(0)]
    hand = [  # hand-expected canonical order (availability, family rank, series, market time, kind)
        "okx/BTC-USDT-SWAP/trade_bar_1m#obs@2026-09-01T00:00:00Z",
        "okx/BTC-USDT-SWAP/mark_bar_1m#obs@2026-09-01T00:00:00Z",
        "okx/BTC-USDT/index_bar_1m#quality@2026-09-01T00:00:00Z",
        "okx/BTC-USDT-SWAP/mark_bar_1m#quality@2026-09-01T00:01:00Z",
        "okx/BTC-USDT-SWAP/trade_bar_1m#obs@2026-09-01T00:02:00Z",
        "okx/BTC-USDT-SWAP/mark_bar_1m#obs@2026-09-01T00:02:00Z",
        "okx/BTC-USDT-SWAP/trade_bar_1m#quality@2026-09-01T00:03:00Z",
        "okx/BTC-USDT-SWAP/trade_bar_1m#obs@2026-09-01T00:04:00Z",
        "okx/BTC-USDT-SWAP/trade_bar_1m#obs@2026-09-01T00:01:00Z",  # the late arrival comes after newer bars
        "okx/BTC-USDT-SWAP/trade_bar_1m#obs@2026-09-01T00:06:00Z",  # end of source
    ]
    assert order == hand == [e.event_id for e in ref.events]
    core = ReplayCore(ref, FRESH)
    pos = core.at(0)
    k = Kernel(cache.feed_meta, FRESH, None, fc.initial_commitment(cache.cache_id))
    for seq, line in fc.CacheReader(cache).iter_from(0):
        k.apply_line(line)
        pos, _ = core.step(pos)
        assert k.snapshot().content_digest == pos.snapshot.content_digest, seq
        if seq == 4:  # explicit restore across a partition boundary
            blob, sha = pack_state(k.state)
            k = Kernel(cache.feed_meta, FRESH, unpack_state(blob, sha), k.commitment)
    trade = k.state.channel(TRADE.channel_id)
    assert trade.latest_valid.event_time == T0 + 6 * MIN  # late older bar never replaced the latest
    assert [h.event_time for h in trade.history] == [T0, T0 + MIN, T0 + 2 * MIN, T0 + 4 * MIN, T0 + 6 * MIN]
    assert k.commitment.hex() == cache.manifest["final_commitment"]


def test_duplicate_slot_is_rejected_exactly_like_the_reference(tmp_path):
    events = edge_events() + [_trade(T0, T0 + 2 * MIN, 99, close=999)]  # second event for slot (trade, t0)
    with pytest.raises(FeedError, match="ambiguous slot"):
        assemble_feed(events, coverage(), POLICY, ("synthetic-edge",), "BTC-USDT-SWAP", "BTC-USDT", INSTRUMENT)
    with pytest.raises(FeedError, match="ambiguous slot"):
        build(tmp_path, events, "dup")
    assert not [p for p in fc.cache_root(tmp_path).iterdir()]  # nothing published, no temporary leftovers


def test_future_suffix_perturbation_leaves_earlier_states_unchanged(tmp_path):
    a, b = build(tmp_path, edge_events(1), "a"), build(tmp_path, edge_events(3), "b")
    ka = Kernel(a.feed_meta, FRESH, None, fc.initial_commitment(a.cache_id))
    kb = Kernel(b.feed_meta, FRESH, None, fc.initial_commitment(b.cache_id))
    la, lb = list(fc.CacheReader(a).iter_from(0)), list(fc.CacheReader(b).iter_from(0))
    cutoff = T0 + 6 * MIN  # everything available up to here is identical in both
    compared = 0
    for (_, x), (_, y) in zip(la, lb):
        ea, eb = fc.decode(x), fc.decode(y)
        if ea.available_time > cutoff or eb.available_time > cutoff:
            break
        assert x == y  # identical admitted evidence
        ka.apply_line(x)
        kb.apply_line(y)
        assert ka.snapshot().content_digest == kb.snapshot().content_digest
        compared += 1
    assert compared == 9 and a.feed_manifest.ordered_event_hash != b.feed_manifest.ordered_event_hash


# ---------------------------------------------------------------------------
# 3. Feed cache trust boundary
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_cold_then_warm_cache_identical_identities_without_reverification(database_url, conn, tmp_path):
    root, art = tmp_path / "data", tmp_path / "art"
    ds = fixture_dataset(root)
    r1 = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    drain(worker(database_url, root, art))
    r2 = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    drain(worker(database_url, root, art))
    a, b = row_of(conn, r1), row_of(conn, r2)
    assert a["config"]["feed"] == b["config"]["feed"] and a["snapshot_digest"] == b["snapshot_digest"]
    assert a["engine"]["cache_id"] == b["engine"]["cache_id"]
    ca, cb = gen_counters(a), gen_counters(b)
    assert (ca["cache_reused"], ca["source_verifications"], ca["feed_builds"]) == (False, 1, 1)
    assert (cb["cache_reused"], cb["source_verifications"], cb["feed_builds"]) == (True, 0, 0)
    assert "reused feed cache" in b["config"]["verification"]["method"]
    assert len([p for p in fc.cache_root(root).iterdir() if not p.name.startswith(".")]) == 1


@pytest.mark.db
def test_source_and_cache_tampering_are_never_silently_consumed(database_url, conn, tmp_path):
    root, art = tmp_path / "data", tmp_path / "art"
    ds = fixture_dataset(root)
    final = reference(root, ds)
    good = final.at(final.total).snapshot.content_digest
    rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    drain(worker(database_url, root, art))
    cid = row_of(conn, rid)["engine"]["cache_id"]
    cdir = fc.cache_root(root) / cid
    # (a) a corrupted cache partition: detected before any of its events is applied; cache quarantined
    part = cdir / "part-00000.jsonl.gz"
    raw = bytearray(part.read_bytes())
    raw[-12] ^= 0xFF
    part.write_bytes(bytes(raw))
    bad = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    drain(worker(database_url, root, art))
    r = row_of(conn, bad)
    assert r["status"] == "failed" and "pinned SHA-256" in r["error"] and "quarantined" in r["error"]
    assert not cdir.exists() and list(fc.cache_root(root).glob(f".invalid-{cid}-*"))
    # the next launch rebuilds the cache from the verified source and is reference-identical
    ok = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    drain(worker(database_url, root, art))
    r = row_of(conn, ok)
    assert r["status"] == "completed" and r["snapshot_digest"] == good and gen_counters(r)["cache_reused"] is False
    # (b) an incompatible/altered cache manifest: quarantined at preparation, rebuilt
    mf = cdir / "manifest.json"
    doc = json.loads(mf.read_bytes())
    doc["format"] = "algotrader.observe-feedcache.v0"
    mf.write_text(json.dumps(doc), encoding="utf-8")
    again = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    drain(worker(database_url, root, art))
    r = row_of(conn, again)
    assert r["status"] == "completed" and r["snapshot_digest"] == good and gen_counters(r)["cache_reused"] is False
    # (c) a tampered SOURCE package: its manifest identity changes -> different cache key -> cold verify fails
    p = md.dataset_path(root, ds) / "trade_candles_1m.parquet"
    data = bytearray(p.read_bytes())
    data[len(data) // 3] ^= 0xFF  # silent in-place corruption (same size, footer intact)
    p.write_bytes(bytes(data))
    m = md.dataset_path(root, ds) / "manifest.json"
    m.write_bytes(m.read_bytes() + b" ")
    tam = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    drain(worker(database_url, root, art))
    r = row_of(conn, tam)
    assert r["status"] == "failed" and "failed verification" in r["error"] and r["config"] is None


@pytest.mark.db
def test_interrupted_cache_build_publishes_nothing_and_is_rebuilt(database_url, conn, tmp_path):
    root, art = tmp_path / "data", tmp_path / "art"
    ds = synthetic_dataset(root, 1)
    rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    w = worker(database_url, root, art, progress_interval=0.02, faults={"BUILDING_FEED_cpu_per_unit": 0.01})
    t = threading.Thread(target=w.run_once, daemon=True)
    t.start()
    end = time.monotonic() + 60
    while time.monotonic() < end and (row_of(conn, rid)["progress"] or {}).get("stage") != "write ordered partitions":
        time.sleep(0.01)
    t0 = time.perf_counter()
    control.cancel(conn, rid)
    t.join(60)
    took = time.perf_counter() - t0
    r = row_of(conn, rid)
    assert r["status"] == "cancelled" and "during source preparation" in r["error"]
    assert not [p for p in fc.cache_root(root).iterdir()]  # no published cache and no temporary leftovers
    assert took < 2.0, took
    print(f"cancel while writing/hashing cache partitions applied in {took:.2f} s")
    rid2 = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    drain(worker(database_url, root, art))
    assert row_of(conn, rid2)["status"] == "completed"


# ---------------------------------------------------------------------------
# 4. Restore-point corruption, fallback and no valid checkpoint; DB outage at commit
# ---------------------------------------------------------------------------


def _crash_after(rid, at):
    def hook(replay_id, cursor):
        if replay_id == rid and cursor == at:
            raise SimulatedCrash()
    return hook


@pytest.mark.db
def test_corrupt_latest_restore_point_falls_back_to_a_verified_predecessor(database_url, conn, tmp_path):
    root, art = tmp_path / "data", tmp_path / "art"
    ds = fixture_dataset(root)
    final = reference(root, ds)
    rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    with pytest.raises(SimulatedCrash):
        worker(database_url, root, art, worker_id="observe:a", after_commit=_crash_after(rid, 30)).run_once()
    pts = conn.execute("SELECT cursor FROM observation_restore_points WHERE replay_id = %s ORDER BY cursor",
                       (rid,)).fetchall()
    assert [p["cursor"] for p in pts] == [25, 30]  # retention: the latest two verified restore points
    conn.execute("UPDATE observation_restore_points SET state_blob = 'garbage'::bytea WHERE replay_id = %s "
                 "AND cursor = 30", (rid,))
    expire(conn, rid)
    drain(worker(database_url, root, art, worker_id="observe:b"))
    r = row_of(conn, rid)
    assert r["status"] == "completed" and r["snapshot_digest"] == final.at(final.total).snapshot.content_digest
    g2 = gen_counters(r, 2)
    assert g2["restore_fallbacks"] == 1 and g2["restore_suffix_events"] == 5 and g2["prefix_restore_events"] == 0
    events = [e["event"] for e in r["diagnostic_log"]]
    assert "restore_point_rejected" in events and "restore_fallback" in events


@pytest.mark.db
def test_no_valid_restore_point_is_a_visible_failure_not_a_silent_replay(database_url, conn, tmp_path):
    root, art = tmp_path / "data", tmp_path / "art"
    ds = fixture_dataset(root)
    rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    with pytest.raises(SimulatedCrash):
        worker(database_url, root, art, worker_id="observe:a", after_commit=_crash_after(rid, 30)).run_once()
    conn.execute("UPDATE observation_restore_points SET fingerprint = 'incompatible' WHERE replay_id = %s", (rid,))
    expire(conn, rid)
    drain(worker(database_url, root, art, worker_id="observe:b"))
    r = row_of(conn, rid)
    assert r["status"] == "failed" and "no valid restore checkpoint" in r["error"]
    assert "nothing was replayed from zero" in r["error"] and r["cursor"] == 30
    assert gen_counters(r, 2)["events_applied"] == 0
    assert len(ranges(conn, rid)) == 6  # committed evidence preserved


@pytest.mark.db
def test_database_failure_inside_the_checkpoint_transaction_commits_nothing(database_url, conn, tmp_path):
    root, art = tmp_path / "data", tmp_path / "art"
    ds = fixture_dataset(root)
    rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)

    def outage(replay_id, cursor):
        if cursor == 20:
            raise psycopg.OperationalError("simulated connection loss inside the checkpoint transaction")

    with pytest.raises(psycopg.OperationalError):
        worker(database_url, root, art, worker_id="observe:a", before_commit=outage).run_once()
    assert row_of(conn, rid)["cursor"] == 15 and ranges(conn, rid)[-1]["to_cursor"] == 15
    expire(conn, rid)
    drain(worker(database_url, root, art, worker_id="observe:b"))
    r = row_of(conn, rid)
    rs = ranges(conn, rid)
    assert r["status"] == "completed" and [x["from_cursor"] for x in rs] == list(range(0, r["total_events"], 5))


# ---------------------------------------------------------------------------
# 5. Structural counters on short/medium synthetic fixtures (bounded engineering checks)
# ---------------------------------------------------------------------------


def _measure(database_url, conn, root, art, ds, ckpt):
    rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    tracemalloc.start()
    t0 = time.perf_counter()
    drain(worker(database_url, root, art, checkpoint_events=ckpt))
    wall = time.perf_counter() - t0
    _cur, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    r = row_of(conn, rid)
    return r, peak, wall


@pytest.mark.db
def test_structure_scales_with_blocks_and_checkpoints_not_source_length(database_url, conn, tmp_path, monkeypatch):
    monkeypatch.setattr(fc, "SORT_BLOCK", 1500)
    monkeypatch.setattr(fc, "PARTITION_EVENTS", 1000)
    root, art = tmp_path / "data", tmp_path / "art"
    rows = []
    for days in (1, 4):
        ds = synthetic_dataset(root, days)
        cold, cold_peak, cold_wall = _measure(database_url, conn, root, art, ds, 500)
        warm, warm_peak, warm_wall = _measure(database_url, conn, root, art, ds, 500)
        n = cold["total_events"]
        for r in (cold, warm):
            c = gen_counters(r)
            ck = c["checkpoints_committed"]
            assert r["status"] == "completed" and r["manifest"]["validation"]["passed"]
            assert c["delivery_rows_written"] == 0 and c["prefix_restore_events"] == 0
            assert ck == -(-n // 500) and c["transactions_committed"] == ck + 1  # transactions follow checkpoints
            assert c["snapshots_built"] == ck + 1 and c["events_applied"] == n  # snapshots only at checkpoints
            assert len(ranges(conn, r["replay_id"])) == ck
            assert c["source_records_read"] == n
        cc, wc = gen_counters(cold), gen_counters(warm)
        assert cc["sort_spill_runs"] >= 2 * (n // 1500) and wc["cache_reused"] is True
        rows.append({"days": days, "events": n, "cold_peak_mb": round(cold_peak / 2**20, 1),
                     "warm_peak_mb": round(warm_peak / 2**20, 1), "cold_s": round(cold_wall, 2),
                     "warm_s": round(warm_wall, 2), "checkpoints": wc["checkpoints_committed"],
                     "transactions": wc["transactions_committed"], "delivery_rows": wc["delivery_rows_written"],
                     "cache_bytes": cc.get("cache_bytes_read"), "spill_runs": cc["sort_spill_runs"],
                     "state_bytes": wc["checkpoint_state_bytes"], "max_rss_mb": round(
                         (wc.get("max_rss_bytes") or 0) / 2**20, 1)})
    small, large = rows
    assert large["events"] > 3.5 * small["events"]
    # Python-heap peak follows the sort block / partition / history bounds, not the source length
    assert large["cold_peak_mb"] < 1.5 * small["cold_peak_mb"] + 2, rows
    assert large["warm_peak_mb"] < 1.5 * small["warm_peak_mb"] + 2, rows
    print("STRUCTURE", json.dumps(rows))
    # direct restore at a meaningful prefix of the larger fixture
    big = conn.execute("SELECT source_id FROM observation_replays ORDER BY created_at DESC LIMIT 1").fetchone()
    rid = control.create_replay(conn, root, SourceKind.DATASET, big["source_id"], speed=0)
    with pytest.raises(SimulatedCrash):
        worker(database_url, root, art, worker_id="observe:a", checkpoint_events=500,
               after_commit=_crash_after(rid, 8000)).run_once()
    expire(conn, rid)
    t0 = time.perf_counter()
    drain(worker(database_url, root, art, worker_id="observe:b", checkpoint_events=500))
    resume_wall = time.perf_counter() - t0
    r = row_of(conn, rid)
    g2 = gen_counters(r, 2)
    assert r["status"] == "completed" and g2["events_applied"] == r["total_events"] - 8000
    assert g2["prefix_restore_events"] == 0 and g2["restore_suffix_events"] == 0 and g2["source_verifications"] == 0
    assert g2["max_control_gap_seconds"] < 1.0
    print(f"RESTORE at 8000/{r['total_events']}: resumed and finished in {resume_wall:.2f}s, "
          f"applied {g2['events_applied']} events, 0 prefix events")


@pytest.mark.db
def test_inspection_reads_only_the_committed_prefix_from_the_cache(database_url, conn, tmp_path):
    root, art = tmp_path / "data", tmp_path / "art"
    ds = fixture_dataset(root)
    api = TestClient(create_app(database_url, art, web_dist=tmp_path / "no-ui", data_root=root))
    rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0, paused=True)
    w = worker(database_url, root, art)
    drain(w)
    for _ in range(7):
        control.step(conn, rid)
        drain(w)
    committed = row_of(conn, rid)["cursor"]
    assert committed == 7
    dl = api.get(f"/api/observations/{rid}/deliveries", params={"latest": 1000}).json()
    assert [d["seq"] for d in dl] == list(range(7))
    feed = build_feed(md.dataset_path(root, ds))
    assert [d["event_id"] for d in dl] == [e.event_id for e in feed.events[:7]]
    bars = api.get(f"/api/observations/{rid}/traded-bars", params={"tail": 5000}).json()
    expected = [i for i, e in enumerate(feed.events[:7]) if e.channel.family == Family.TRADE_BAR_1M]
    assert [b["seq"] for b in bars["bars"]] == expected and bars["committed_cursor"] == 7
    assert api.get(f"/api/observations/{rid}/deliveries", params={"after_seq": 6, "limit": 5000}).json() == []
    rep = api.get(f"/api/observations/{rid}/report.json").json()
    assert rep["storage"]["delivery_rows"] == 0 and rep["storage"]["ranges"] == 7
    shutil.rmtree(fc.cache_root(root))
    assert api.get(f"/api/observations/{rid}/deliveries", params={"latest": 5}).status_code == 410
