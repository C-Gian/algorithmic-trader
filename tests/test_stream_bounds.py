"""WP-008-R1B correction evidence: bounded cold preparation, verified-byte boundary and trusted cache receipts.

Deterministic offline engineering fixtures (captured OKX/recorder fixtures and synthetic datasets served
through the accepted acquisition path). Not historical evaluations; no month/year claims.
"""

from __future__ import annotations

import json
import multiprocessing
import shutil
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg
import psycopg.rows
import pytest
from okx_fake import FIXTURE_END, FIXTURE_START, FakeOkx, client
from okx_synth import measure_cold_build, shuffle_parquet, synthetic_fake
from recorder_fake import BUSINESS, PUBLIC, captured_script, record_session
from reference_bridge import build_recorded_feed as reference_recorded_feed

from algotrader.feed.adapter import build_feed
from algotrader.marketdata import dataset as md
from algotrader.observe import control
from algotrader.observe import feedcache as fc
from algotrader.observe.contracts import SourceKind
from algotrader.observe.core import ReplayCore
from algotrader.observe.job import ReplayJob, SimulatedCrash
from algotrader.observe.sources import prepare_stream_source
from algotrader.observe.worker import ObservationWorker
from algotrader.ops import OperationCancelled
from algotrader.feed.ordering import default_freshness
from algotrader.recorder.journal import finalize, recordings_dir

FRESH = default_freshness()
DAY = timedelta(days=1)
S0 = datetime(2026, 8, 1, tzinfo=UTC)


class MemReceipts:
    """In-memory receipt store for DB-free preparation fixtures."""

    def __init__(self) -> None:
        self.rows: dict[str, dict] = {}

    def get(self, cid):
        return self.rows.get(cid)

    def put(self, cache, key, kind, sid, sha, durability, verification, created_by):
        self.rows.setdefault(cache.cache_id, {"cache_manifest_sha256": cache.manifest_sha256,
                                              "created_at": datetime.now(UTC), "durability": durability})
        return self.rows[cache.cache_id]


def synth(root: Path, days: int, gap_days: float = 0.0, gap_every: int | None = 97) -> str:
    end = S0 + days * DAY
    gaps = ((S0 + DAY / 2, S0 + DAY / 2 + gap_days * DAY),) if gap_days else ()
    return md.acquire(client(synthetic_fake(S0, end, gap_every=gap_every, gaps=gaps)), root, S0, end
                      ).manifest.dataset_id


def all_events(cache) -> list:
    return [fc.decode(line) for _s, line in fc.CacheReader(cache).iter_from(0)]


def heavy_recording(root: Path, repeats: int, session_id: str) -> str:
    """Captured session + ``repeats`` late repeated completions of every business push (dedup-heavy, no-yield),
    plus one completion received before its bar end (a bridge exclusion)."""
    business = captured_script("business")
    confirm = 1790768700590111500  # first completed trade push of the first bar
    i = next(k for k, item in enumerate(business) if item[1] == confirm)
    business[i] = ("msg", 1790768699_900_000_000, business[i][2])
    business.sort(key=lambda item: item[1])
    heavy = []
    for kind, ns, raw in business:  # each push immediately followed by ``repeats`` late identical re-deliveries
        heavy.append((kind, ns, raw))
        if kind == "msg" and raw.startswith('{"arg"') and '"data"' in raw:  # candle pushes only (not acks)
            heavy.extend((kind, ns + r, raw) for r in range(1, repeats + 1))
    scripts = {PUBLIC: [captured_script("public")], BUSINESS: [heavy]}
    path, *_ = record_session(root, scripts, session_id=session_id)
    finalize(path, "test", False, "test-host", 1, None)
    return session_id


@pytest.fixture
def limits(monkeypatch):
    monkeypatch.setattr(fc, "SORT_BLOCK", 400)
    monkeypatch.setattr(fc, "FAN_IN", 3)
    monkeypatch.setattr(fc, "PARTITION_EVENTS", 700)


# ---------------------------------------------------------------------------
# 1. Exactness on long gaps, unsorted Parquet, multi-pass merge; recorded duplicates/exclusions
# ---------------------------------------------------------------------------


def test_long_gap_unsorted_parquet_multipass_merge_is_reference_exact(tmp_path, limits):
    root = tmp_path / "data"
    ds = synth(root, 6, gap_days=4)  # a 4-day hole inside 6 days (thousands of absent slots per family)
    path = md.dataset_path(root, ds)
    shuffle_parquet(path)  # unsorted normalized rows (still a verifying package)
    assert md.verify(path) == []
    ref = build_feed(path)  # the in-memory reference adapter
    counters: dict = {}
    p = prepare_stream_source(root, SourceKind.DATASET, ds, receipts=MemReceipts(), counters=counters)
    assert p.cache.feed_manifest == ref.manifest  # identical content identity, ordered hash, counts
    assert all_events(p.cache) == list(ref.events)  # identical ids, order, admission, provenance, gap classes
    absent = sum(1 for e in ref.events if e.source.artifact.endswith("(absent slot)"))
    assert absent > 3 * 4 * 1440  # the gap really produced absent-slot evidence
    sort = counters["sort"]
    assert sort["order"]["merge_passes"] >= 2 and sort["order"]["runs_created"] > 3 * 3
    assert sort["order"]["max_open_runs"] <= 3 and sort["content"]["max_open_runs"] <= 3  # bounded fan-in
    assert sort["order"]["max_buffer_records"] <= 400
    assert not list(fc.cache_root(root).glob(".snap-*")) and not list(fc.cache_root(root).glob(".tmp-*"))


def test_recorded_duplicates_and_exclusions_are_reference_exact(tmp_path, limits):
    root = tmp_path / "data"
    sid = heavy_recording(root, 30, "rec-dup")
    ref = reference_recorded_feed(recordings_dir(root) / sid)  # independent in-memory accepted bridge
    counters: dict = {}
    p = prepare_stream_source(root, SourceKind.RECORDING, sid, receipts=MemReceipts(), counters=counters)
    assert p.cache.feed_manifest == ref.feed.manifest
    assert all_events(p.cache) == list(ref.feed.events)  # first completed receipt still wins
    assert list(p.loaded.summary.exclusions) == list(ref.excluded) and len(ref.excluded) == 1
    assert counters["bridge_first_completions"] == ref.feed.manifest.event_count + 1  # incl. the excluded one


# ---------------------------------------------------------------------------
# 2. Memory: peak RSS (where supported) and Python heap, measured in fresh processes
# ---------------------------------------------------------------------------


def _measure(args: dict) -> dict:
    ctx = multiprocessing.get_context("spawn")
    with ctx.Pool(1) as pool:
        return pool.apply(measure_cold_build, (args,))


def test_cold_preparation_memory_does_not_grow_with_gap_or_duplicate_length(tmp_path):
    limits = {"SORT_BLOCK": 1000, "FAN_IN": 4, "PARTITION_EVENTS": 1000}
    rows = []
    for days, gap in ((2, 1), (10, 9)):  # gap length x9 (absent-slot evidence grows with it)
        root = tmp_path / f"gap{days}"
        ds = synth(root, days, gap_days=gap)
        rows.append({"fixture": f"{days}d/{gap}d-gap", **_measure({"root": str(root), "kind": "dataset",
                                                                    "source_id": ds, "limits": limits})})
    for reps in (5, 60):  # repeated recorded completions x12 (dedup work grows; events do not)
        root = tmp_path / f"rec{reps}"
        sid = heavy_recording(root, reps, f"rec-{reps}")
        rows.append({"fixture": f"recording x{reps}", **_measure({"root": str(root), "kind": "recording",
                                                                   "source_id": sid, "limits": limits})})
    print("MEMORY", json.dumps([{k: r[k] for k in ("fixture", "events", "heap_peak", "rss_peak", "rss_source",
                                                   "partitions", "exclusions", "bridge_first_completions")}
                                | {"max_open_runs": max(r["sort"]["order"]["max_open_runs"],
                                                        r["sort"]["content"]["max_open_runs"]),
                                   "merge_passes": r["sort"]["order"]["merge_passes"]} for r in rows]))
    small, large, rsmall, rlarge = rows
    assert large["events"] > 4 * small["events"]
    mb = 2 ** 20
    # Python heap: bounded by sort block / batch / partition limits (partition metadata is the only growth)
    assert large["heap_peak"] < 1.5 * small["heap_peak"] + 2 * mb, rows
    assert rlarge["heap_peak"] < 1.5 * rsmall["heap_peak"] + 2 * mb, rows
    if small["rss_peak"] and large["rss_peak"]:  # native (Arrow/sqlite/gzip) allocations included
        assert large["rss_peak"] < 1.3 * small["rss_peak"] + 40 * mb, rows
        assert rlarge["rss_peak"] < 1.3 * rsmall["rss_peak"] + 40 * mb, rows
    for r in rows:
        assert max(r["sort"]["order"]["max_open_runs"], r["sort"]["content"]["max_open_runs"]) <= 4


# ---------------------------------------------------------------------------
# 3. Cancellation inside long no-yield work
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("stage", ["bridge journal records", "classify absent slots", "merge order sort runs",
                                   "index raw-page slot evidence", "snapshot source package"])
def test_cancellation_during_no_yield_preparation_work(tmp_path, monkeypatch, stage):
    monkeypatch.setattr(fc, "SORT_BLOCK", 300)
    monkeypatch.setattr(fc, "FAN_IN", 2)
    root = tmp_path / "data"
    if stage == "bridge journal records":
        sid, kind = heavy_recording(root, 60, "rec-cancel"), SourceKind.RECORDING
    else:
        sid, kind = synth(root, 2, gap_every=None), SourceKind.DATASET  # dense: the absent-slot walk yields nothing
    calls = {"n": 0, "t": None}

    def hook(st, done, total, unit):
        if st.startswith(stage):
            calls["n"] += 1
            if calls["t"] is None:
                calls["t"] = time.perf_counter()  # cancellation requested at the first unit of this stage
            raise OperationCancelled(st)

    t0 = time.perf_counter()
    with pytest.raises(OperationCancelled):
        prepare_stream_source(root, kind, sid, receipts=MemReceipts(), verify_hook=hook, build_hook=hook)
    assert calls["n"] == 1 and time.perf_counter() - t0 < 30
    leftovers = [p.name for p in fc.cache_root(root).iterdir()] if fc.cache_root(root).exists() else []
    assert leftovers == [], leftovers  # nothing published, no snapshot/temporary directories left


# ---------------------------------------------------------------------------
# 4. Verified-byte boundary (DB, full job)
# ---------------------------------------------------------------------------


@pytest.fixture
def conn(database_url):
    with psycopg.connect(database_url, autocommit=True, row_factory=psycopg.rows.dict_row) as c:
        yield c


def worker(database_url, root, art, **kw) -> ObservationWorker:
    kw.setdefault("worker_id", "observe:bounds")
    return ObservationWorker(database_url, root, art, lease_seconds=5, poll_interval=0.01, isolate=False,
                             checkpoint_events=10, sleep=lambda s: None, **kw)


def drain(w) -> None:
    while w.run_once():
        pass


def row_of(conn, rid):
    return conn.execute("SELECT r.*, k.cursor, k.snapshot_digest FROM observation_replays r LEFT JOIN "
                        "observation_checkpoints k USING (replay_id) WHERE replay_id = %s", (rid,)).fetchone()


def receipt(conn, cid):
    return conn.execute("SELECT * FROM observation_feed_caches WHERE cache_id = %s", (cid,)).fetchone()


def flip_middle(p: Path) -> None:
    data = bytearray(p.read_bytes())
    data[len(data) // 3] ^= 0xFF  # same size; manifest untouched
    p.write_bytes(bytes(data))


@pytest.mark.db
def test_source_mutation_after_verification_never_becomes_cache_evidence(database_url, conn, tmp_path, monkeypatch):
    root, art = tmp_path / "data", tmp_path / "art"
    ds = md.acquire(client(FakeOkx()), root, FIXTURE_START, FIXTURE_END).manifest.dataset_id
    original = build_feed(md.dataset_path(root, ds))
    good = ReplayCore(original, FRESH).at(original.manifest.event_count).snapshot.content_digest
    target = md.dataset_path(root, ds) / "trade_candles_1m.parquet"

    def mutate_after_verification(self, stage):
        if stage == "after_verification":
            flip_middle(target)  # the ORIGINAL changes right after the snapshot verified; manifest unchanged

    monkeypatch.setattr(ReplayJob, "_prep_fault", mutate_after_verification)
    rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    drain(worker(database_url, root, art))
    monkeypatch.undo()
    r = row_of(conn, rid)
    assert r["status"] == "completed" and r["snapshot_digest"] == good  # built only from the verified snapshot
    assert r["config"]["feed"]["ordered_event_hash"] == original.manifest.ordered_event_hash
    assert md.verify(md.dataset_path(root, ds)) != []  # the original is now corrupt ...
    rc = receipt(conn, r["engine"]["cache_id"])
    assert rc["cache_manifest_sha256"] == r["engine"]["cache_manifest_sha256"]  # ... yet the receipt pins good bytes
    # a cold rebuild from the corrupted original (no cache, no receipt) is rejected: nothing falsely verified
    shutil.rmtree(fc.cache_root(root))
    conn.execute("DELETE FROM observation_feed_caches")
    rid2 = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    drain(worker(database_url, root, art))
    r2 = row_of(conn, rid2)
    assert r2["status"] == "failed" and "failed verification" in r2["error"] and r2["config"] is None
    assert receipt(conn, r["engine"]["cache_id"]) is None
    assert [p.name for p in fc.cache_root(root).iterdir()] == []


@pytest.mark.db
def test_mutation_before_snapshot_and_manifest_mutation_during_preparation_are_rejected(database_url, conn, tmp_path,
                                                                                        monkeypatch):
    from algotrader.observe import sources

    root, art = tmp_path / "data", tmp_path / "art"
    ds = md.acquire(client(FakeOkx()), root, FIXTURE_START, FIXTURE_END).manifest.dataset_id
    path = md.dataset_path(root, ds)
    orig_snapshot = sources.snapshot_source
    saved = {p.name: p.read_bytes() for p in path.iterdir() if p.is_file()}

    def mutate_data_then_copy(src, dest, hook):  # data file changes between locate and snapshot
        flip_middle(src / "mark_candles_1m.parquet")
        return orig_snapshot(src, dest, hook)

    monkeypatch.setattr(sources, "snapshot_source", mutate_data_then_copy)
    rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    drain(worker(database_url, root, art))
    r = row_of(conn, rid)
    assert r["status"] == "failed" and "failed verification" in r["error"]
    for name, data in saved.items():
        (path / name).write_bytes(data)

    def mutate_manifest_then_copy(src, dest, hook):  # manifest/quality inputs change during preparation
        (src / "manifest.json").write_bytes((src / "manifest.json").read_bytes() + b" ")
        return orig_snapshot(src, dest, hook)

    monkeypatch.setattr(sources, "snapshot_source", mutate_manifest_then_copy)
    rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    drain(worker(database_url, root, art))
    r = row_of(conn, rid)
    assert r["status"] == "failed" and "changed while it was being prepared" in r["error"]
    assert conn.execute("SELECT count(*) AS n FROM observation_feed_caches").fetchone()["n"] == 0
    assert not [p for p in fc.cache_root(root).iterdir() if not p.name.startswith(".invalid-")]


@pytest.mark.db
def test_recording_report_and_config_mutation_after_snapshot_do_not_change_facts(database_url, conn, tmp_path,
                                                                                 monkeypatch):
    from test_observe import fixture_scripts

    from algotrader.observe.sources import load_recording

    root, art = tmp_path / "data", tmp_path / "art"
    path, *_ = record_session(root, fixture_scripts(), session_id="rec-facts")
    finalize(path, "test", False, "test-host", 1, None)
    expected = load_recording(root, "rec-facts").summary

    def mutate_after_snapshot(self, stage):
        if stage == "after_snapshot":
            rep = json.loads((path / "report.json").read_text(encoding="utf-8"))
            rep["outages"] = [{"connection": None, "start": "2026-09-30T08:00:00+00:00", "end": None}]
            (path / "report.json").write_text(json.dumps(rep), encoding="utf-8")

    monkeypatch.setattr(ReplayJob, "_prep_fault", mutate_after_snapshot)
    rid = control.create_replay(conn, root, SourceKind.RECORDING, "rec-facts", speed=0)
    drain(worker(database_url, root, art))
    r = row_of(conn, rid)
    assert r["status"] == "completed"
    assert r["config"]["source"]["warnings"] == list(expected.warnings)  # facts come from the verified snapshot
    assert r["config"]["source"]["exclusions"] == list(expected.exclusions)


# ---------------------------------------------------------------------------
# 5. Trusted receipts: compatible manifest alteration on a NEW warm run; publication crash boundaries
# ---------------------------------------------------------------------------


def _alter(doc: dict, how: str) -> None:
    if how == "source_facts":
        doc["source_facts"]["quality"] = "clean"
    elif how == "feed_metadata":
        k = next(iter(doc["feed_manifest"]["event_counts"]))
        doc["feed_manifest"]["event_counts"][k] += 1
    elif how == "partition_hash":
        doc["partitions"][0]["sha256"] = "0" * 64
    elif how == "final_commitment":
        doc["final_commitment"] = "f" * 64


@pytest.mark.db
@pytest.mark.parametrize("how", ["source_facts", "feed_metadata", "partition_hash", "final_commitment"])
def test_compatible_cache_manifest_alteration_is_rejected_on_a_new_warm_run(database_url, conn, tmp_path, how):
    root, art = tmp_path / "data", tmp_path / "art"
    ds = md.acquire(client(FakeOkx()), root, FIXTURE_START, FIXTURE_END).manifest.dataset_id
    r1 = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    drain(worker(database_url, root, art))
    a = row_of(conn, r1)
    cid = a["engine"]["cache_id"]
    mf = fc.cache_root(root) / cid / "manifest.json"
    doc = json.loads(mf.read_bytes())
    _alter(doc, how)  # compatible: format, key and cache id unchanged
    mf.write_bytes(fc.canonical(doc))
    fc.open_cache(root, cid, doc["key"])  # the mutable manifest alone would still "open"
    r2 = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    drain(worker(database_url, root, art))
    b = row_of(conn, r2)
    prep = b["metrics"][str(b["lease_generation"])]["preparation"]
    assert prep["cache_quarantined"]["reason"].startswith("feed cache") and "changed" in prep["cache_quarantined"][
        "reason"]
    assert b["status"] == "completed" and b["snapshot_digest"] == a["snapshot_digest"]
    assert b["config"]["source"]["source_status"] == "degraded"  # the true fact, not the altered one
    assert b["config"]["feed"] == a["config"]["feed"]
    # the rebuilt cache reproduces the trusted receipt exactly; the run pins the receipt, not the altered bytes
    assert b["engine"]["cache_manifest_sha256"] == receipt(conn, cid)["cache_manifest_sha256"] == a["engine"][
        "cache_manifest_sha256"]
    assert list(fc.cache_root(root).glob(f".invalid-{cid}-*"))


@pytest.mark.db
@pytest.mark.parametrize("stage", ["before_publish_rename", "after_publish_rename", "before_receipt"])
def test_crash_around_publication_and_receipt_commit(database_url, conn, tmp_path, stage):
    root, art = tmp_path / "data", tmp_path / "art"
    ds = md.acquire(client(FakeOkx()), root, FIXTURE_START, FIXTURE_END).manifest.dataset_id
    rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    with pytest.raises(SimulatedCrash):
        worker(database_url, root, art, worker_id="observe:a", faults={f"prep_{stage}": "crash"}).run_once()
    published = [p for p in fc.cache_root(root).iterdir() if p.name.startswith("fc-")]
    assert conn.execute("SELECT count(*) AS n FROM observation_feed_caches").fetchone()["n"] == 0  # no receipt
    assert bool(published) == (stage != "before_publish_rename")
    conn.execute("UPDATE observation_replays SET lease_expires_at = now() - interval '1 second' WHERE replay_id = %s",
                 (rid,))
    drain(worker(database_url, root, art, worker_id="observe:b"))
    r = row_of(conn, rid)
    assert r["status"] == "completed"
    rc = receipt(conn, r["engine"]["cache_id"])
    assert rc is not None and rc["cache_manifest_sha256"] == r["engine"]["cache_manifest_sha256"]
    assert rc["durability"].startswith("partition/manifest files fsynced")
    if stage != "before_publish_rename":  # a published cache without a receipt is never trusted: rebuilt
        prep = r["metrics"]["2"]["preparation"]
        assert prep["cache_quarantined"]["reason"] == "no trusted receipt"
    # a receipt whose cache directory vanished: the deterministic rebuild must reproduce it
    shutil.rmtree(fc.cache_root(root) / r["engine"]["cache_id"])
    rid2 = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    drain(worker(database_url, root, art))
    r2 = row_of(conn, rid2)
    assert r2["status"] == "completed" and r2["engine"]["cache_manifest_sha256"] == rc["cache_manifest_sha256"]
