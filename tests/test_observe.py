"""Real-market observation replay (algotrader.observe.v1): causal correctness, durability and separation.

Historical evidence comes from captured OKX public responses served offline
(tests/fixtures/okx); recorded evidence from captured OKX public WebSocket
messages replayed through the recorder with a fake clock (tests/fixtures/okx_ws).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import psycopg
import psycopg.rows
import pytest
from fastapi.testclient import TestClient
from okx_fake import CONFIRMED_END, FIXTURE_END, FIXTURE_START, FakeOkx, client
from recorder_fake import BUSINESS, PUBLIC, captured_script, record_session

from algotrader.api import create_app
from algotrader.feed.contracts import (
    AvailabilityBasis,
    ChannelCondition,
    EventKind,
    Family,
    QualityReason,
)
from algotrader.feed.ordering import default_freshness, sort_key
from algotrader.feed.state import apply_all, initial_state, snapshot, snapshot_at
from algotrader.marketdata.dataset import acquire
from algotrader.observe import control
from algotrader.observe.contracts import ReplayStatus, SourceKind
from algotrader.observe.core import ReplayCore, as_of
from algotrader.observe.sources import SourceRejected, load_dataset, load_recording
from algotrader.observe.job import LeaseLost
from algotrader.observe.worker import ObservationWorker, SimulatedCrash
from algotrader.recorder.feed_bridge import build_recorded_feed
from algotrader.recorder.journal import finalize, iter_records, ns_to_dt, recordings_dir

FRESH = default_freshness()
PAYLOAD_TYPE = {Family.TRADE_BAR_1M: "trade_bar_1m", Family.MARK_BAR_1M: "mark_bar_1m",
                Family.INDEX_BAR_1M: "index_bar_1m", Family.FUNDING_SETTLEMENT: "funding_settlement"}


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------


def dataset(root: Path, clean: bool = False) -> str:
    return acquire(client(FakeOkx()), root, FIXTURE_START, CONFIRMED_END if clean else FIXTURE_END).manifest.dataset_id


def fixture_scripts() -> dict:
    return {PUBLIC: [captured_script("public")], BUSINESS: [captured_script("business")]}


def recording(root: Path, scripts: dict | None = None, session_id: str = "rec-obs") -> str:
    path, *_ = record_session(root, scripts or fixture_scripts(), session_id=session_id)
    finalize(path, "test", False, "test-host", 1, None)
    return session_id


def evidence_times_ok(snap) -> bool:
    return all(e.available_time <= snap.as_of
               for c in snap.channels for e in (c.latest_valid, c.last_quality, *c.history) if e is not None)


def full_replay(core: ReplayCore):
    pos, recs = core.at(0), []
    while pos.cursor < core.total:
        pos, rec = core.step(pos)
        recs.append(rec)
    return pos, recs


# ---------------------------------------------------------------------------
# Contract
# ---------------------------------------------------------------------------


def test_observe_contract_is_separate_provisional_and_baselined():
    from algotrader import schema
    from algotrader.observe import contracts as oc

    assert oc.OBSERVE_SCHEMA_VERSION == "algotrader.observe.v1" and oc.OBSERVE_CONTRACT_STATUS == "PROVISIONAL"
    assert oc.OBSERVE_CHANGELOG[-1][0] == oc.OBSERVE_SCHEMA_REVISION == 2  # R1A Director-approved revision
    assert [r for r, _, _ in oc.OBSERVE_CHANGELOG] == [1, 2]
    stored = json.loads(schema.baseline_path(oc.OBSERVE_SCHEMA_VERSION).read_text(encoding="utf-8"))
    assert stored == schema.observe_baseline(), "observe contract drift: bump OBSERVE_SCHEMA_REVISION + changelog"
    assert (stored["status"], stored["revision"]) == ("PROVISIONAL", 2)
    # revision-2 additions are optional: revision-1 manifests/validations stay readable unchanged
    for name in ("lease_generation", "artifact_dir", "phase_timings", "operational_metrics"):
        assert name not in stored["$defs"]["ObservationReplayManifest"]["required"]
    for name in ("outcome", "validator", "validator_version", "scope"):
        assert name not in stored["$defs"]["ReplayValidation"].get("required", [])
    assert "ObservationLaunch" in stored["public_contracts"]
    own = {n: stored["$defs"][n] for n in stored["public_contracts"]}
    fields = {p for d in own.values() for p in d.get("properties", {})}
    for banned in ("bias", "confidence", "recommendation", "decision", "target", "invalidation", "position",
                   "equity", "leverage", "pnl", "order", "fill"):
        assert banned not in fields, banned
    # frozen/provisional baselines this package depends on are untouched
    import hashlib

    for version, sha in (("algotrader.semantic.v1", "7e212b948ef0d756628b9db2da4b923aace3d8d25532dc48d58b8b10ce4e0c09"),
                         ("algotrader.marketdata.v1", "646b014a66248343f1df8e1bd9fd8a64e3b170517f65dd5670841d457e689bc1"),
                         ("algotrader.feed.v1", "bffcbae1f589fb8031547d58e95813e7f194804d25d57b354c1c5c2084afe346"),
                         ("algotrader.recorder.v1", "51362b13040c7bb20e5d6f1cc20d92683f63eadd567325c2c35d3bc4083e1956")):
        text = schema.baseline_path(version).read_text(encoding="utf-8")
        assert hashlib.sha256(text.encode()).hexdigest() == sha, version


# ---------------------------------------------------------------------------
# Historical dataset: causal correctness (pure)
# ---------------------------------------------------------------------------


def test_dataset_replay_applies_accepted_order_and_matches_pure_prefix_at_every_cursor(tmp_path):
    src = load_dataset(tmp_path, dataset(tmp_path))
    feed = src.feed
    assert feed.manifest.availability_policy.basis == AvailabilityBasis.MODELED
    assert "not measured publication timing" in src.availability_label
    core = ReplayCore(feed, FRESH)
    pos = core.at(0)
    assert all(c.latest_valid is None and c.condition == ChannelCondition.NEVER_SEEN for c in pos.snapshot.channels)
    events = feed.events
    for i in range(core.total):
        pos, rec = core.step(pos)
        assert rec.seq == i and rec.event_id == events[i].event_id  # one step == one feed delivery
        assert pos.snapshot.as_of == events[i].available_time == rec.available_time
        pure = snapshot(apply_all(initial_state(feed, FRESH), events[: i + 1]), events[i].available_time, feed)
        assert pos.snapshot.content_digest == pure.content_digest == rec.snapshot_digest
        assert evidence_times_ok(pos.snapshot)
        if i == 0:  # the first state holds exactly the first delivery and nothing later
            seen = [c for c in pos.snapshot.channels if c.latest_slot_time is not None]
            assert len(seen) == 1 and pos.snapshot.cursor.applied_events == 1
        if i + 1 == core.total or events[i + 1].available_time > events[i].available_time:
            # at an availability boundary the cursor state IS the pure knowledge-cutoff state
            assert pos.snapshot.content_digest == snapshot_at(feed, events[i].available_time, FRESH).content_digest
    assert [sort_key(e.order) for e in events] == sorted(sort_key(e.order) for e in events)


def test_quality_events_update_condition_without_leaking_invalid_values(tmp_path):
    src = load_dataset(tmp_path, dataset(tmp_path))
    core = ReplayCore(src.feed, FRESH)
    pos = core.at(0)
    seen_quality = 0
    while pos.cursor < core.total:
        event = src.feed.events[pos.cursor]
        before = {c.channel_id: c for c in pos.snapshot.channels}
        pos, rec = core.step(pos)
        after = {c.channel_id: c for c in pos.snapshot.channels}[rec.channel_id]
        if event.kind == EventKind.SLOT_QUALITY:
            seen_quality += 1
            prev = before[rec.channel_id]
            assert rec.quality_reason is not None
            assert after.latest_valid == prev.latest_valid  # no value enters valid state
            assert after.last_quality.event_id == event.event_id
            assert after.condition in (ChannelCondition.GAP, ChannelCondition.REJECTED, ChannelCondition.INVALID_ONLY)
            assert all(h.kind != EventKind.SLOT_QUALITY for h in after.history)
    assert seen_quality >= 1  # the degraded fixture has missing/rejected slots


def test_traded_mark_index_and_funding_remain_separate_channels(tmp_path):
    src = load_dataset(tmp_path, dataset(tmp_path))
    pos, _ = full_replay(ReplayCore(src.feed, FRESH))
    fams = {c.channel.family for c in pos.snapshot.channels}
    assert fams == {Family.TRADE_BAR_1M, Family.MARK_BAR_1M, Family.INDEX_BAR_1M, Family.FUNDING_SETTLEMENT}
    for c in pos.snapshot.channels:
        for e in (c.latest_valid, *c.history):
            if e is not None:
                assert e.channel.channel_id == c.channel_id and e.payload.payload_type == PAYLOAD_TYPE[c.channel.family]


# ---------------------------------------------------------------------------
# Recorded session: causal correctness (pure)
# ---------------------------------------------------------------------------


def test_recorded_replay_uses_first_completed_receipt_and_never_forming_pushes(tmp_path):
    sid = recording(tmp_path)
    src = load_recording(tmp_path, sid)
    assert src.feed.manifest.availability_policy.basis == AvailabilityBasis.RECORDED
    assert "client-observed receipt" in src.availability_label
    path = recordings_dir(tmp_path) / sid
    first_completed: dict[tuple[str, int], int] = {}
    for rec in iter_records(path):
        if rec.channel in ("candle1m", "mark-price-candle1m", "index-candle1m") and rec.raw.startswith('{"arg"'):
            for row in json.loads(rec.raw)["data"]:
                if row[-1] == "1":
                    first_completed.setdefault((rec.channel, int(row[0])), rec.recv_utc_ns)
    bars = [e for e in src.feed.events if e.channel.family != Family.FUNDING_SETTLEMENT]
    assert len(bars) == len(first_completed)  # forming (confirm=0) pushes never become deliveries
    channel_name = {Family.TRADE_BAR_1M: "candle1m", Family.MARK_BAR_1M: "mark-price-candle1m",
                    Family.INDEX_BAR_1M: "index-candle1m"}
    for e in bars:
        key = (channel_name[e.channel.family], int(e.event_time.timestamp() * 1000))
        assert e.available_time == ns_to_dt(first_completed[key])  # first completed local receipt
        assert e.available_time >= e.event_end_time  # never known before the bar ended

    core = ReplayCore(src.feed, FRESH)
    pos = core.at(0)
    while pos.cursor < core.total:
        pos, rec = core.step(pos)
        assert evidence_times_ok(pos.snapshot)  # no future completion leaks before its receipt
        pure = snapshot(apply_all(initial_state(src.feed, FRESH), src.feed.events[: pos.cursor]), rec.available_time,
                        src.feed)
        assert pos.snapshot.content_digest == pure.content_digest


def test_recorded_incremental_replay_equals_the_feed_rebuilt_from_the_journal_prefix(tmp_path):
    """Live parity: at each receipt boundary, the replay state equals the state built only from what had been
    received by then (journal truncated at that receipt)."""
    sid = recording(tmp_path)
    path = recordings_dir(tmp_path) / sid
    src = load_recording(tmp_path, sid)
    events = src.feed.events
    core = ReplayCore(src.feed, FRESH)
    pos = core.at(0)
    checked = 0
    while pos.cursor < core.total:
        pos, rec = core.step(pos)
        i = pos.cursor - 1
        if i + 1 == len(events) or events[i + 1].available_time > events[i].available_time:
            # available_time is the receipt ns truncated to microseconds: the cutoff covers that whole microsecond
            prefix = build_recorded_feed(path, until_utc_ns=_ns(rec.available_time) + 999).feed
            assert [e.event_id for e in prefix.events] == [e.event_id for e in events[: i + 1]]
            assert snapshot_at(prefix, rec.available_time, FRESH).content_digest == pos.snapshot.content_digest
            checked += 1
    assert checked >= 3


def _ns(t) -> int:
    from datetime import UTC, datetime

    delta = t - datetime(1970, 1, 1, tzinfo=UTC)
    return (delta.days * 86400 + delta.seconds) * 1_000_000_000 + delta.microseconds * 1000


def test_partial_session_outage_is_not_converted_into_market_gaps(tmp_path):
    business = captured_script("business")
    cut = next(i for i, item in enumerate(business) if item[1] > 1790768702_000_000_000)
    first, second = business[:cut], business[cut:]
    resub = [("msg", second[0][1] - 10_000_000 + k, raw) for k, (_, _, raw) in enumerate(business[:3])]
    scripts = {PUBLIC: [captured_script("public")],
               BUSINESS: [first + [("close", 1790768705_000_000_000)], "refuse", resub + second]}
    sid = recording(tmp_path, scripts)
    src = load_recording(tmp_path, sid)
    assert src.summary.source_status == "partial"
    assert any("PARTIAL" in w for w in src.summary.warnings)
    assert any("recorder outage" in w and "not a market gap" in w for w in src.summary.warnings)
    pos, recs = full_replay(ReplayCore(src.feed, FRESH))
    assert all(r.kind != EventKind.SLOT_QUALITY for r in recs)  # no fabricated gap events
    assert all(c.counts.missing == 0 for c in pos.snapshot.channels)


def test_bridge_exclusions_stay_visible_in_the_replay_config(tmp_path):
    scripts = fixture_scripts()
    b = scripts[BUSINESS][0]
    confirm = 1790768700590111500  # first completed trade push of the first bar
    i = next(k for k, item in enumerate(b) if item[1] == confirm)
    b[i] = ("msg", 1790768699_900_000_000, b[i][2])  # derived: receipt before bar end (clock inconsistency)
    b.sort(key=lambda item: item[1])
    sid = recording(tmp_path, scripts)
    src = load_recording(tmp_path, sid)
    assert len(src.summary.exclusions) == 1 and "precedes bar end" in src.summary.exclusions[0]
    config = control.build_config("obs-x", src)
    assert config.source.exclusions == src.summary.exclusions
    assert any("not settlements" in n for n in config.source.notes)  # live funding is not a settlement


def test_unusable_or_unfinalized_recordings_cannot_launch(tmp_path):
    sid = recording(tmp_path, {PUBLIC: ["refuse"], BUSINESS: ["refuse"]}, session_id="rec-dead")
    with pytest.raises(SourceRejected):
        load_recording(tmp_path, sid)
    path, *_ = record_session(tmp_path, fixture_scripts(), session_id="rec-open")  # not finalized
    with pytest.raises(SourceRejected, match="not finalized"):
        load_recording(tmp_path, path.name)
    with pytest.raises(SourceRejected, match="not found"):
        load_dataset(tmp_path, "no-such-dataset")


# ---------------------------------------------------------------------------
# Separation from the synthetic semantic.v1 path
# ---------------------------------------------------------------------------


def test_real_replay_domain_path_imports_no_synthetic_trader_modules():
    code = ("import sys, algotrader.observe.worker, algotrader.observe.api, algotrader.observe.control, "
            "algotrader.observe.core, algotrader.observe.sources, algotrader.observe.artifacts; "
            "print('\\n'.join(sorted(m for m in sys.modules if m.startswith('algotrader'))))")
    loaded = set(subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout.split())
    forbidden = {"algotrader.trader", "algotrader.risk", "algotrader.account", "algotrader.engine",
                 "algotrader.synthetic", "algotrader.contracts", "algotrader.worker", "algotrader.control",
                 "algotrader.artifacts", "algotrader.validation"}
    assert not loaded & forbidden, loaded & forbidden


# ---------------------------------------------------------------------------
# Durable execution (PostgreSQL)
# ---------------------------------------------------------------------------


def worker(database_url, root, art, **kw) -> ObservationWorker:
    kw.setdefault("worker_id", "observe:test")
    kw.setdefault("isolate", False)
    kw.setdefault("checkpoint_events", 5)  # small cadence so short fixtures cross several checkpoints
    return ObservationWorker(database_url, root, art, lease_seconds=5, poll_interval=0.01, sleep=lambda s: None, **kw)


def drain(w: ObservationWorker) -> None:
    while w.run_once():
        pass


def replay_row(c, rid):
    return c.execute("SELECT r.*, k.cursor, k.snapshot_digest FROM observation_replays r "
                     "LEFT JOIN observation_checkpoints k USING (replay_id) WHERE replay_id = %s", (rid,)).fetchone()


def deliveries(c, rid):
    """Legacy per-event delivery rows (streaming runs never write them)."""
    return c.execute("SELECT seq, event_id FROM observation_deliveries WHERE replay_id = %s ORDER BY seq",
                     (rid,)).fetchall()


def ranges(c, rid):
    return c.execute("SELECT * FROM observation_ranges WHERE replay_id = %s ORDER BY from_cursor", (rid,)).fetchall()


def expire_lease(c, rid):
    c.execute("UPDATE observation_replays SET lease_expires_at = now() - interval '1 second' WHERE replay_id = %s",
              (rid,))


def assert_contiguous(rs, cursor):
    expect = 0
    for r in rs:
        assert r["from_cursor"] == expect and r["event_count"] == r["to_cursor"] - r["from_cursor"]
        expect = r["to_cursor"]
    assert expect == cursor
    for a, b in zip(rs, rs[1:]):
        assert a["commitment_after"] == b["commitment_before"]


@pytest.fixture
def conn(database_url):
    with psycopg.connect(database_url, autocommit=True, row_factory=psycopg.rows.dict_row) as c:
        yield c


@pytest.mark.db
def test_dataset_replay_completes_durably_with_valid_artifacts_and_no_synthetic_rows(database_url, conn, tmp_path):
    root, art = tmp_path / "data", tmp_path / "art"
    ds = dataset(root)
    rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    drain(worker(database_url, root, art))
    row = replay_row(conn, rid)
    src = load_dataset(root, ds)
    total = src.feed.manifest.event_count
    assert row["status"] == "completed" and row["cursor"] == total == row["total_events"]
    pure = snapshot_at(src.feed, as_of(src.feed, total), FRESH)
    assert row["snapshot_digest"] == pure.content_digest  # final state == pure reference cutoff snapshot
    m = row["manifest"]
    assert m["validation"]["passed"], m["validation"]
    assert m["validation"]["validator"] == "observe.stream-reconciliation"  # never labelled as the old validator
    assert {c["name"] for c in m["validation"]["checks"]} >= {
        "committed_ranges_contiguous", "input_commitment_chain", "terminal_state_verified", "feed_cache_integrity",
        "completed_consumed_entire_feed", "consumed_input_exact", "cache_receipt_and_pin", "commitments_reported"}
    assert m["validation"]["validator_version"] == "2"
    assert "No independent reference replay was performed in this run" in m["validation"]["scope"]
    assert "Runtime integrity verified, engine reference-tested" in m["validation"]["scope"]
    assert m["config"]["availability_policy"]["basis"] == "MODELED" and not m["config"]["availability_policy"]["measured"]
    assert m["config"]["freshness_policy"]["note"].startswith("Inspection default")
    assert m["config"]["source"]["source_id"] == ds and m["source_reference"] == f"datasets/{ds}"
    # canonical identities preserved exactly
    assert m["config"]["feed"]["content_identity"] == src.feed.manifest.content_identity
    assert m["config"]["feed"]["ordered_event_hash"] == src.feed.manifest.ordered_event_hash
    out = art / "observations" / rid / m["artifact_dir"]
    assert m["artifact_dir"] == f"g{m['lease_generation']}" and m["schema_revision"] == 2
    names = {a["name"] for a in m["artifacts"]}
    assert names == {"config.json", "engine.json", "ranges.jsonl", "final_snapshot.json", "validation.json"}
    assert json.loads((out / "final_snapshot.json").read_text())["content_digest"] == pure.content_digest
    assert row["engine_format"] == "observe.stream.v1" and row["engine"]["state_format"] == "algotrader.observe-state.v1"
    # sparse persistence: no per-event delivery rows; compact contiguous committed ranges
    assert not deliveries(conn, rid)
    rs = ranges(conn, rid)
    assert_contiguous(rs, total) and len(rs) == -(-total // 5)
    c = row["metrics"][str(row["lease_generation"])]
    assert c["delivery_rows_written"] == 0 and c["transactions_committed"] == len(rs) + 1  # + initial checkpoint
    assert c["events_applied"] == total and c["snapshots_built"] == len(rs) + 1  # checkpoints + initial only
    assert c["source_verifications"] == 1 and c["feed_builds"] == 1  # verified once; no nested re-verification
    # separation: no synthetic run / semantic journal rows, no interpretation records
    assert conn.execute("SELECT count(*) AS n FROM runs").fetchone()["n"] == 0
    assert conn.execute("SELECT count(*) AS n FROM run_events").fetchone()["n"] == 0

    def keys(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                yield k
                yield from keys(v)
        elif isinstance(obj, list):
            for v in obj:
                yield from keys(v)

    final = json.loads((out / "final_snapshot.json").read_text())
    found = set(keys(m)) | set(keys(final))
    assert not found & {"market_view", "scenarios", "bias", "decision", "permitted_action", "proposed_action",
                        "target", "invalidation", "fill_id", "position", "equity", "exposure_fraction"}


@pytest.mark.db
def test_recording_replay_completes_with_recorded_availability(database_url, conn, tmp_path):
    root, art = tmp_path / "data", tmp_path / "art"
    sid = recording(root)
    rid = control.create_replay(conn, root, SourceKind.RECORDING, sid, speed=0)
    drain(worker(database_url, root, art))
    row = replay_row(conn, rid)
    assert row["status"] == "completed" and row["manifest"]["validation"]["passed"]
    assert row["manifest"]["config"]["availability_policy"]["basis"] == "RECORDED"
    assert row["manifest"]["source_reference"] == f"recordings/{sid}"
    src = load_recording(root, sid)
    assert row["manifest"]["config"]["feed"]["ordered_event_hash"] == src.feed.manifest.ordered_event_hash
    assert row["manifest"]["config"]["source"]["exclusions"] == list(src.summary.exclusions)
    assert row["snapshot_digest"] == snapshot_at(src.feed, as_of(src.feed, src.feed.manifest.event_count),
                                                 FRESH).content_digest


@pytest.mark.db
def test_pause_step_resume_speed_are_durable_and_do_not_change_digests(database_url, conn, tmp_path):
    root, art = tmp_path / "data", tmp_path / "art"
    ds = dataset(root)
    ref = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    drain(worker(database_url, root, art))
    reference = replay_row(conn, ref)
    src = load_dataset(root, ds)
    core = ReplayCore(src.feed, FRESH)

    rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=5, paused=True)
    with pytest.raises(control.ControlRejected, match="PENDING"):
        control.step(conn, rid)  # STEP needs a prepared feed: the total is still PENDING
    w = worker(database_url, root, art)
    assert w.run_once()  # paused launch: the worker prepares the source, then parks at cursor 0
    row = replay_row(conn, rid)
    assert row["status"] == "paused" and row["cursor"] == 0
    assert row["total_events"] == reference["total_events"] and row["config"] is not None
    assert not w.run_once()  # parked: nothing to claim
    for n in (1, 2):
        control.step(conn, rid)
        drain(w)
        row = replay_row(conn, rid)
        # STEP: exactly one source event, durably committed (its own range), reference-identical state
        assert row["status"] == "paused" and row["cursor"] == n and len(ranges(conn, rid)) == n
        assert ranges(conn, rid)[-1]["event_count"] == 1
        assert row["snapshot_digest"] == core.at(n).snapshot.content_digest
        assert row["step_budget"] == 0 and row["lease_owner"] is None  # parked at a committed cursor
    control.set_speed(conn, rid, 250)  # pacing change while paused
    control.resume(conn, rid)
    drain(w)
    row = replay_row(conn, rid)
    assert row["status"] == "completed"
    assert row["snapshot_digest"] == reference["snapshot_digest"]
    assert_contiguous(ranges(conn, rid), row["total_events"])
    assert not deliveries(conn, rid)
    commands = [e["command"] for e in row["control_log"]]
    assert commands[:1] == ["start"] and commands.count("step") == 2 and "parked" in commands
    assert "speed" in commands and "resume" in commands
    with pytest.raises(control.ControlRejected):
        control.pause(conn, rid)  # terminal


@pytest.mark.db
@pytest.mark.parametrize("when", ["before_commit", "after_commit"])
def test_worker_crash_and_reclaim_restore_directly_without_duplicate_ranges(database_url, conn, tmp_path, when):
    root, art = tmp_path / "data", tmp_path / "art"
    ds = dataset(root)
    ref = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    drain(worker(database_url, root, art))
    reference = replay_row(conn, ref)

    rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)

    def crash(replay_id, cursor):
        if replay_id == rid and cursor == 35:
            raise SimulatedCrash()

    a = worker(database_url, root, art, worker_id="observe:a", **{when: crash})
    with pytest.raises(SimulatedCrash):
        a.run_once()
    a.close()
    row = replay_row(conn, rid)
    committed = 30 if when == "before_commit" else 35  # checkpoint transaction rolled back vs. committed-then-died
    assert row["status"] == "running" and row["cursor"] == committed
    assert_contiguous(ranges(conn, rid), committed)
    expire_lease(conn, rid)
    drain(worker(database_url, root, art, worker_id="observe:b"))
    row = replay_row(conn, rid)
    rs = ranges(conn, rid)
    assert row["status"] == "completed"
    assert_contiguous(rs, row["total_events"])  # no gap, no overlap, no duplicate committed range
    assert row["snapshot_digest"] == reference["snapshot_digest"]  # digest-identical after restart
    assert {r["generation"] for r in rs} == {1, 2}
    assert row["recovery_log"][0]["event"] == "lease_expired_reclaimed"
    assert f"committed feed cursor {committed}" in row["recovery_log"][0]["detail"]
    assert row["attempt"] == 2 and row["manifest"]["validation"]["passed"]
    g2 = row["metrics"]["2"]
    # direct restore: the second attempt neither rebuilt the cache nor replayed the committed prefix
    assert g2["prefix_restore_events"] == 0 and g2["restore_suffix_events"] == 0
    assert g2["events_applied"] == row["total_events"] - committed
    assert g2["source_verifications"] == 0 and g2["feed_builds"] == 0 and g2["cache_reused"] is True


@pytest.mark.db
def test_stale_generation_cannot_commit_and_cursor_cas_refuses_a_retried_range(database_url, conn, tmp_path):
    root, art = tmp_path / "data", tmp_path / "art"
    rid = control.create_replay(conn, root, SourceKind.DATASET, dataset(root), speed=0, paused=True)
    w = worker(database_url, root, art)
    drain(w)  # prepare + park at 0
    control.step(conn, rid)
    drain(w)
    row = replay_row(conn, rid)
    assert row["cursor"] == 1
    from algotrader.observe import feedcache as fc
    from algotrader.observe.job import JobSpec, ReplayJob, _UnsafeRecovery
    from algotrader.observe.kernel import Kernel

    cache = fc.open_cache(root, row["engine"]["cache_id"])
    reader = fc.CacheReader(cache)
    k = Kernel(cache.feed_meta, FRESH, None, fc.initial_commitment(cache.cache_id))
    line = reader.lines(0, 1)[0][1]
    before = k.commitment
    k.apply_line(line)
    gen = row["lease_generation"]
    conn.execute("UPDATE observation_replays SET status = 'running', lease_owner = %s WHERE replay_id = %s",
                 (w.worker_id, rid))
    job = ReplayJob(JobSpec(database_url, rid, w.worker_id, gen, str(root), str(art)))
    # a retried commit of the already committed first event: the cursor CAS (expected prior 0) refuses it
    with pytest.raises(_UnsafeRecovery):
        job.commit_checkpoint(k, 0, before, "a", "b", row["engine"])
    stale = ReplayJob(JobSpec(database_url, rid, w.worker_id, gen - 1, str(root), str(art)))
    with pytest.raises(LeaseLost):  # an older generation (same worker id) cannot commit at all
        stale.commit_checkpoint(k, 1, before, "a", "b", row["engine"])
    assert len(ranges(conn, rid)) == 1 and replay_row(conn, rid)["cursor"] == 1
    job.close()
    stale.close()


@pytest.mark.db
def test_repeated_interruptions_fail_explicitly(database_url, conn, tmp_path):
    root, art = tmp_path / "data", tmp_path / "art"
    rid = control.create_replay(conn, root, SourceKind.DATASET, dataset(root), speed=0)

    def crash(replay_id, seq):
        raise SimulatedCrash()

    for attempt in range(3):
        w = worker(database_url, root, art, worker_id=f"observe:{attempt}", before_commit=crash)
        try:
            w.run_once()
        except SimulatedCrash:
            pass
        w.close()
        expire_lease(conn, rid)
    drain(worker(database_url, root, art, worker_id="observe:last"))
    row = replay_row(conn, rid)
    assert row["status"] == "failed" and "consecutive attempts" in row["error"]
    assert row["cursor"] == 0 and not deliveries(conn, rid)


@pytest.mark.db
def test_unsafe_recovery_and_vanished_source_fail_explicitly(database_url, conn, tmp_path):
    root, art = tmp_path / "data", tmp_path / "art"
    ds = dataset(root)
    rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0, paused=True)
    drain(worker(database_url, root, art))
    control.step(conn, rid)
    drain(worker(database_url, root, art))
    conn.execute("UPDATE observation_checkpoints SET snapshot_digest = 'tampered' WHERE replay_id = %s", (rid,))
    control.resume(conn, rid)
    drain(worker(database_url, root, art))
    row = replay_row(conn, rid)
    assert row["status"] == "failed" and "recovery is not safe" in row["error"]

    rid2 = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0, paused=True)
    import shutil

    shutil.rmtree(root / "datasets" / ds)  # evidence vanishes after the durable launch, before preparation
    drain(worker(database_url, root, art))
    row = replay_row(conn, rid2)
    assert row["status"] == "failed" and "source not replayable" in row["error"]
    # never prepared: no verified config, no manifest, and assurance is explicitly NOT CHECKED (not FAIL/PASS)
    assert row["config"] is None and row["total_events"] is None and row["manifest"] is None
    assert row["assurance"]["state"] == "not_checked"


@pytest.mark.db
def test_cancel_is_durable(database_url, conn, tmp_path):
    root, art = tmp_path / "data", tmp_path / "art"
    rid = control.create_replay(conn, root, SourceKind.DATASET, dataset(root), speed=0, paused=True)
    drain(worker(database_url, root, art))
    control.step(conn, rid)
    drain(worker(database_url, root, art))
    control.cancel(conn, rid)
    drain(worker(database_url, root, art))
    row = replay_row(conn, rid)
    assert row["status"] == ReplayStatus.CANCELLED and row["cursor"] == 1
    # bounded cancellation: no prefix load / source reload / reference re-derivation; assurance INCOMPLETE and
    # the committed input range stays preserved in the database
    m = row["manifest"]
    assert m["status"] == "cancelled" and m["validation"]["outcome"] == "incomplete" and not m["validation"]["passed"]
    assert {a["name"] for a in m["artifacts"]} == {"config.json", "validation.json"}
    assert len(ranges(conn, rid)) == 1 and not deliveries(conn, rid)
    with pytest.raises(control.ControlRejected):
        control.resume(conn, rid)


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_observation_api_sources_preflight_launch_state_and_artifacts(database_url, tmp_path):
    root, art = tmp_path / "data", tmp_path / "art"
    ds = dataset(root, clean=True)
    sid = recording(root)
    recording(root, {PUBLIC: ["refuse"], BUSINESS: ["refuse"]}, session_id="rec-dead")
    api = TestClient(create_app(database_url, art, web_dist=tmp_path / "no-ui", data_root=root))

    sources = api.get("/api/observations/sources").json()
    assert [d["source_id"] for d in sources["datasets"]] == [ds]
    recs = {r["source_id"]: r for r in sources["recordings"]}
    assert recs[sid]["replayable"] and recs[sid]["availability_basis"] == "RECORDED"
    assert not recs["rec-dead"]["replayable"]
    pre = api.get(f"/api/observations/sources/dataset/{ds}").json()
    # cheap preview: no hashing/feed build here; verification is a durable preparation phase after launch
    assert pre["availability"]["basis"] == "MODELED" and pre["verification"] is None and pre["feed"] is None
    assert "not verified here" in pre["verification_note"].lower()
    assert api.get("/api/observations/sources/dataset/nope").status_code == 422
    assert api.post("/api/observations", json={"source_kind": "dataset", "source_id": "nope"}).status_code == 422
    # a finalized but FAILED recording is launchable cheaply; preparation turns it into a visible failed job
    dead = api.post("/api/observations", json={"source_kind": "recording", "source_id": "rec-dead"}).json()
    assert dead["status"] == "queued" and dead["configured"] is False and dead["feed"] is None
    assert dead["source"]["source_status"] == "PENDING" and dead["progress"]["total_events"] is None
    drain(worker(database_url, root, art))
    dead = api.get(f"/api/observations/{dead['replay_id']}").json()
    assert dead["status"] == "failed" and "FAILED" in dead["error"]
    assert dead["operation"]["assurance"]["state"] == "not_checked"
    dmd = api.get(f"/api/observations/{dead['replay_id']}/report.md").text
    assert "FAILED" in dmd and "no terminal manifest" in dmd

    created = api.post("/api/observations", json={"source_kind": "dataset", "source_id": ds, "speed": 0,
                                                  "paused": True})
    assert created.status_code == 201
    view = created.json()
    rid = view["replay_id"]
    assert view["kind"] == "market_observation_replay" and view["control"]["unit"] == "events/s"
    assert view["availability"] is None and view["operation"]["phase"] is None and "REAL_MARKET_EVIDENCE" in view["labels"]
    assert view["operation"]["controls"]["step"]["enabled"] is False  # total PENDING
    assert api.post(f"/api/observations/{rid}/step").status_code == 409
    w = worker(database_url, root, art)
    drain(w)  # prepares, then parks at cursor 0
    view = api.get(f"/api/observations/{rid}").json()
    assert view["availability"]["basis"] == "MODELED" and view["runtime_state"] == "paused"
    assert view["operation"]["controls"]["step"]["enabled"] is True
    assert api.post(f"/api/observations/{rid}/step").status_code == 200
    drain(w)
    st = api.get(f"/api/observations/{rid}/state").json()
    assert st["replay"]["runtime_state"] == "paused" and st["replay"]["progress"]["applied_events"] == 1
    assert st["state"]["cursor"]["applied_events"] == 1 and "history" not in st["state"]["channels"][0]
    # committed-prefix inspection: only admission positions < committed cursor (1) are ever exposed
    early = api.get(f"/api/observations/{rid}/deliveries", params={"latest": 50}).json()
    assert [d["seq"] for d in early] == [0] and early[0]["snapshot_digest"] is None
    assert api.get(f"/api/observations/{rid}/deliveries", params={"after_seq": 0}).json() == []
    assert all(b["seq"] < 1 for b in api.get(f"/api/observations/{rid}/traded-bars").json()["bars"])
    assert api.post(f"/api/observations/{rid}/resume").status_code == 200
    drain(w)
    done = api.get(f"/api/observations/{rid}").json()
    assert done["status"] == "completed" and done["validation_passed"] is True
    dl = api.get(f"/api/observations/{rid}/deliveries", params={"latest": 5}).json()
    assert len(dl) == 5 and dl[-1]["seq"] == done["progress"]["applied_events"] - 1
    bars = api.get(f"/api/observations/{rid}/traded-bars").json()["bars"]
    assert bars and all("close" in b for b in bars if b["kind"] == "bar_observation")
    feed = load_dataset(root, ds).feed
    assert len(bars) == sum(1 for e in feed.events if e.channel.family == Family.TRADE_BAR_1M)  # never mark/index
    m = api.get(f"/api/observations/{rid}/manifest").json()
    for a in m["artifacts"]:
        assert api.get(f"/api/observations/{rid}/files/{a['name']}").status_code == 200
    assert api.get(f"/api/observations/{rid}/files/..%2Fsecret").status_code == 404
    assert api.post(f"/api/observations/{rid}/pause").status_code == 409  # terminal
    # synthetic runs are untouched and remain a separate listing
    assert api.get("/api/runs").json() == []


@pytest.mark.db
def test_health_is_capability_aware(database_url, tmp_path):
    root, art = tmp_path / "data", tmp_path / "art"
    api = TestClient(create_app(database_url, art, web_dist=tmp_path / "no-ui", data_root=root))
    caps = api.get("/api/health").json()["capabilities"]
    assert caps["core"]["status"] == "available"
    assert {caps[k]["status"] for k in ("market_replay", "recorder", "synthetic_replay")} == {"unavailable"}
    w = worker(database_url, root, art)
    w.beat(None, force=True)
    h = api.get("/api/health").json()
    assert h["capabilities"]["market_replay"]["status"] == "available" and h["observation_workers"]["alive"] == 1
    assert h["workers"]["alive"] == 0  # an observation worker is not a synthetic run worker
    api.post("/api/runs", json={"speed": 0})
    assert api.get("/api/health").json()["capabilities"]["synthetic_replay"]["status"] == "stalled"
