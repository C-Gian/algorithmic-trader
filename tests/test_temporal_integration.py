"""WP-008-R2 evidence (database): the temporal substrate inside the accepted streaming job - fenced checkpoint
persistence, cadence/STEP/pause invariance, crash and corrupted-restore recovery, reconciliation v3 scope, Deep
validation v2 (shadow fold + separate reference aggregator), legacy observe.stream.v1 compatibility, inspection
and copy reports. Bounded synthetic fixtures only; no historical month/year run.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg
import psycopg.rows
import pytest
from okx_fake import FIXTURE_END, FIXTURE_START, FakeOkx, client
from okx_synth import synthetic_fake

from algotrader import db
from algotrader.feed.adapter import build_feed
from algotrader.marketdata import dataset as md
from algotrader.observe import control, deep, diagnostics
from algotrader.observe import job as observe_job
from algotrader.observe.api import REPLAY_SELECT, replay_view
from algotrader.observe.contracts import ReplayStatus, SourceKind
from algotrader.observe.feedcache import open_cache
from algotrader.observe.job import SimulatedCrash
from algotrader.observe.kernel import new_temporal, temporal_config
from algotrader.observe.reconcile import reconcile
from algotrader.observe.worker import ObservationWorker
from algotrader.temporal import engine as te


@pytest.fixture
def conn(database_url):
    with psycopg.connect(database_url, autocommit=True, row_factory=psycopg.rows.dict_row) as c:
        yield c


def synthetic_dataset(root: Path, days: int = 1) -> str:
    s = datetime(2026, 8, 31, 20, tzinfo=UTC)  # Monday 20:00: crosses a day and a month boundary
    return md.acquire(client(synthetic_fake(s, s + timedelta(days=days))), root, s, s + timedelta(days=days)
                      ).manifest.dataset_id


def fixture_dataset(root: Path) -> str:
    return md.acquire(client(FakeOkx()), root, FIXTURE_START, FIXTURE_END).manifest.dataset_id


def worker(database_url, root, art, **kw) -> ObservationWorker:
    kw.setdefault("worker_id", "observe:temporal")
    kw.setdefault("isolate", False)
    kw.setdefault("checkpoint_events", 500)
    kw.setdefault("sleep", lambda s: None)
    return ObservationWorker(database_url, root, art, lease_seconds=5, poll_interval=0.01, **kw)


def drain(w: ObservationWorker) -> None:
    while w.run_once():
        pass


def row_of(conn, rid):
    return conn.execute(REPLAY_SELECT + " WHERE r.replay_id = %s", (rid,)).fetchone()


def ranges(conn, rid):
    return conn.execute("SELECT * FROM observation_ranges WHERE replay_id = %s ORDER BY from_cursor", (rid,)).fetchall()


def expire(conn, rid):
    conn.execute("UPDATE observation_replays SET lease_expires_at = now() - interval '1 second' WHERE replay_id = %s",
                 (rid,))


def crash_after(rid, at):
    def hook(replay_id, cursor):
        if replay_id == rid and cursor == at:
            raise SimulatedCrash()
    return hook


class Reference:
    """Pure temporal fold of the same canonical feed under the run's pinned configuration."""

    def __init__(self, root: Path, ds: str, cursors=()):
        feed = build_feed(md.dataset_path(root, ds))
        self.cfg = temporal_config(feed.manifest)
        eng = new_temporal(feed.manifest, {"temporal": self.cfg})
        want = set(cursors)
        self.at: dict[int, tuple[str, str, str, int]] = {}
        for i, e in enumerate(feed.events):
            eng.on_event(e, i)
            if i + 1 in want:
                self.at[i + 1] = (te.pack(eng)[1], eng.commitment(), eng.aggregate_chain, eng.dispatch_seq)
        self.total = len(feed.events)
        eng.finish(datetime.fromisoformat(self.cfg["clock_end"]))
        self.final = eng.summary(recent=10)


def terminal_temporal(art: Path, row) -> dict:
    m = row["manifest"]
    d = art / "observations" / row["replay_id"] / m["artifact_dir"] / "temporal.json"
    return json.loads(d.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Cadence, STEP/pause, crash: semantic records never depend on operational boundaries
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_checkpoint_cadence_never_changes_temporal_records(database_url, conn, tmp_path):
    root, art = tmp_path / "data", tmp_path / "art"
    ds = synthetic_dataset(root)
    runs = {}
    for ckpt in (7, 333, 5000):
        rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
        drain(worker(database_url, root, art, checkpoint_events=ckpt))
        runs[ckpt] = (rid, row_of(conn, rid), ranges(conn, rid))
    cursors = {r["to_cursor"] for _, _, rs in runs.values() for r in rs}
    ref = Reference(root, ds, cursors)
    for ckpt, (rid, row, rs) in runs.items():
        assert row["status"] == "completed", (ckpt, row["error"])
        assert row["engine_format"] == "observe.stream.v2" and row["lifecycle_version"] == 4
        for r in rs:  # every committed range equals the pure fold at that cursor (state, outputs, dispatch seq)
            assert (r["temporal_sha256"], r["temporal_commitment"], r["aggregate_chain"], r["dispatch_seq"]) == \
                ref.at[r["to_cursor"]], (ckpt, r["to_cursor"])
        t = terminal_temporal(art, row)
        assert t["aggregate_chain"] == ref.final["aggregate_chain"]
        assert t["dispatch_commitment"] == ref.final["dispatch_commitment"]
        assert t["finished_at_clock_end"] and t["clock_time"] == ref.cfg["clock_end"]
        checks = {c["name"]: c for c in row["manifest"]["validation"]["checks"]}
        assert row["manifest"]["validation"]["validator_version"] == "3" and row["manifest"]["validation"]["passed"]
        assert checks["temporal_state_verified"]["passed"] and checks["temporal_clock_end_finish"]["passed"]
    # sanity: the fixture really exercises closures of several horizons and an incomplete (gap) interval
    by = {x["track"].rsplit("/", 1)[-1]: x for x in ref.final["tracks"] if "trade_bar_1m" in x["track"]}
    assert by["15m"]["sealed_by_status"].get("COMPLETE") and by["15m"]["sealed_by_status"].get("INCOMPLETE")
    assert by["1w"]["sealed_by_status"] == {"OUTSIDE_COVERAGE": 1} and by["1mo"]["sealed_by_status"] == {
        "OUTSIDE_COVERAGE": 2}


@pytest.mark.db
def test_step_pause_and_paced_execution_equal_the_uninterrupted_records(database_url, conn, tmp_path):
    root, art = tmp_path / "data", tmp_path / "art"
    ds = fixture_dataset(root)
    ref = Reference(root, ds)
    rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0, paused=True)
    drain(worker(database_url, root, art))
    assert row_of(conn, rid)["status"] == "paused"
    for _ in range(14):  # STEP exactly one feed event at a time across the first 15m tie boundary
        control.step(conn, rid)
        drain(worker(database_url, root, art))
    row = row_of(conn, rid)
    assert row["applied"] == 14 and row["temporal_view"]["admitted_cursor"] == 14
    control.set_speed(conn, rid, 500)  # paced (sleep is a no-op in tests): pacing never changes records
    control.resume(conn, rid)
    drain(worker(database_url, root, art, checkpoint_events=3))
    row = row_of(conn, rid)
    assert row["status"] == "completed"
    t = terminal_temporal(art, row)
    assert (t["aggregate_chain"], t["dispatch_commitment"], t["dispatch_seq"]) == (
        ref.final["aggregate_chain"], ref.final["dispatch_commitment"], ref.final["dispatch_seq"])


@pytest.mark.db
@pytest.mark.parametrize("at", [1, 15, 42])
def test_crash_after_commit_restores_temporal_state_without_duplicate_dispatches(database_url, conn, tmp_path, at):
    root, art = tmp_path / "data", tmp_path / "art"
    ds = fixture_dataset(root)
    ref = Reference(root, ds)
    rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    with pytest.raises(SimulatedCrash):
        worker(database_url, root, art, worker_id="observe:a", checkpoint_events=1,
               after_commit=crash_after(rid, at)).run_once()
    expire(conn, rid)
    drain(worker(database_url, root, art, worker_id="observe:b"))
    row = row_of(conn, rid)
    assert row["status"] == "completed"
    t = terminal_temporal(art, row)
    assert (t["aggregate_chain"], t["dispatch_commitment"], t["dispatch_seq"]) == (
        ref.final["aggregate_chain"], ref.final["dispatch_commitment"], ref.final["dispatch_seq"])
    seqs = [r["dispatch_seq"] for r in ranges(conn, rid)]
    assert seqs == sorted(seqs)  # never decreasing: no dispatch re-emitted or lost across the crash
    g2 = row["metrics"]["2"]
    assert g2["prefix_restore_events"] == 0 and g2["events_applied"] == ref.total - at


@pytest.mark.db
def test_corrupt_temporal_restore_state_falls_back_and_reproduces_the_committed_temporal_state(
        database_url, conn, tmp_path):
    root, art = tmp_path / "data", tmp_path / "art"
    ds = fixture_dataset(root)
    ref = Reference(root, ds)
    rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    with pytest.raises(SimulatedCrash):
        worker(database_url, root, art, worker_id="observe:a", checkpoint_events=5,
               after_commit=crash_after(rid, 30)).run_once()
    conn.execute("UPDATE observation_restore_points SET temporal_blob = 'garbage'::bytea WHERE replay_id = %s "
                 "AND cursor = 30", (rid,))
    expire(conn, rid)
    drain(worker(database_url, root, art, worker_id="observe:b"))
    row = row_of(conn, rid)
    assert row["status"] == "completed"
    g2 = row["metrics"]["2"]
    assert g2["restore_fallbacks"] == 1 and g2["restore_suffix_events"] == 5 and g2["prefix_restore_events"] == 0
    rejected = [e for e in row["diagnostic_log"] if e["event"] == "restore_point_rejected"]
    assert rejected and "temporal state" in rejected[0]["detail"]
    assert terminal_temporal(art, row)["aggregate_chain"] == ref.final["aggregate_chain"]


# ---------------------------------------------------------------------------
# Reconciliation v3 scope and tamper; Deep validation v2
# ---------------------------------------------------------------------------


def _reconcile_inputs(conn, root, rid):
    row = conn.execute("SELECT * FROM observation_replays WHERE replay_id = %s", (rid,)).fetchone()
    eng = row["engine"]
    ck = conn.execute("SELECT * FROM observation_checkpoints WHERE replay_id = %s", (rid,)).fetchone()
    terminal = conn.execute("SELECT * FROM observation_restore_points WHERE replay_id = %s AND cursor = %s",
                            (rid, ck["cursor"])).fetchone()
    receipt = conn.execute("SELECT * FROM observation_feed_caches WHERE cache_id = %s", (eng["cache_id"],)).fetchone()
    cache = open_cache(root, eng["cache_id"], expected_manifest_sha256=eng["cache_manifest_sha256"])
    from algotrader.observe.contracts import ObservationReplayConfig

    cfg = ObservationReplayConfig.model_validate(row["config"])
    return dict(status=ReplayStatus.COMPLETED, cache=cache, ranges=ranges(conn, rid), cursor=ck["cursor"],
                terminal=dict(terminal), committed_snapshot_digest=ck["snapshot_digest"], engine=eng,
                freshness=cfg.freshness_policy, hook=lambda *a: None, receipt=receipt)


@pytest.mark.db
def test_reconciliation_v3_detects_temporal_tampering_and_states_its_scope(database_url, conn, tmp_path):
    root, art = tmp_path / "data", tmp_path / "art"
    ds = fixture_dataset(root)
    rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    drain(worker(database_url, root, art, checkpoint_events=9))
    kw = _reconcile_inputs(conn, root, rid)
    out: dict = {}
    v, _ = reconcile(**kw, temporal_out=out)
    assert v.passed and v.validator_version == "3" and out["finished_at_clock_end"]
    assert "No independent temporal re-execution was performed in this run" in v.scope
    bad = dict(kw)
    bad["terminal"] = {**kw["terminal"], "temporal_sha256": "0" * 64}
    v2, _ = reconcile(**bad)
    failed = {c.name for c in v2.checks if not c.passed}
    assert not v2.passed and "temporal_state_verified" in failed
    rs = [dict(r) for r in kw["ranges"]]
    rs[0]["dispatch_seq"] = 10_000  # a decreasing dispatch sequence across ranges
    v3, _ = reconcile(**{**kw, "ranges": rs})
    assert "temporal_ranges_recorded" in {c.name for c in v3.checks if not c.passed}


@pytest.mark.db
def test_deep_validation_v2_matches_and_detects_a_tampered_aggregate_chain(database_url, conn, tmp_path):
    root, art = tmp_path / "data", tmp_path / "art"
    ds = synthetic_dataset(root)
    rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    drain(worker(database_url, root, art, checkpoint_events=700))
    vid = deep.create_deep_validation(conn, rid)
    drain(worker(database_url, root, art))
    d = conn.execute("SELECT * FROM observation_deep_validations WHERE validation_id = %s", (vid,)).fetchone()
    res = d["result"]
    assert d["status"] == "completed" and res["outcome"] == "match", res
    assert res["validator_version"] == "3" and "separate naive reference aggregator" in res["scope"]
    term = res["temporal"]["terminal"]
    assert term["compared"] and term["comparisons"] == 11 and term["clock_end"]
    assert term["reference_sealed_records_final"] == term["shadow_sealed_records_final"] > 100
    assert res["temporal"]["reference_sealed_records"] == res["temporal"]["shadow_sealed_records"] > 100
    assert res["compared"] >= 6 * len(ranges(conn, rid)) + 11
    # tamper one recorded aggregate chain: the separate reference aggregator reports the mismatch
    target = ranges(conn, rid)[2]
    conn.execute("UPDATE observation_ranges SET aggregate_chain = %s WHERE replay_id = %s AND range_seq = %s",
                 ("f" * 64, rid, target["range_seq"]))
    vid2 = deep.create_deep_validation(conn, rid)
    drain(worker(database_url, root, art))
    res2 = conn.execute("SELECT result FROM observation_deep_validations WHERE validation_id = %s",
                        (vid2,)).fetchone()["result"]
    assert res2["outcome"] == "mismatch"
    assert {(m["kind"], m["cursor"]) for m in res2["mismatches"]} == {("aggregate_chain", target["to_cursor"])}
    assert res2["temporal"]["terminal"]["compared"]  # boundary tamper does not disturb the terminal comparison
    # the originating run is never modified by Deep validation
    assert row_of(conn, rid)["status"] == "completed"


@pytest.mark.db
def test_paused_and_resumed_deep_v2_refolds_the_temporal_prefix(database_url, conn, tmp_path, monkeypatch):
    root, art = tmp_path / "data", tmp_path / "art"
    ds = synthetic_dataset(root)
    rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    drain(worker(database_url, root, art, checkpoint_events=700))
    monkeypatch.setattr(deep, "SAVE_EVENTS", 500)
    vid = deep.create_deep_validation(conn, rid)
    deep.control(conn, vid, "pause")  # parks at its first save point (500 events)
    worker(database_url, root, art).run_once()
    d = conn.execute("SELECT status, resume_cursor FROM observation_deep_validations WHERE validation_id = %s",
                     (vid,)).fetchone()
    assert d["status"] == "paused" and d["resume_cursor"] == 500
    deep.control(conn, vid, "resume")
    drain(worker(database_url, root, art))
    d = conn.execute("SELECT status, result FROM observation_deep_validations WHERE validation_id = %s",
                     (vid,)).fetchone()
    assert d["status"] == "completed" and d["result"]["outcome"] == "match", d["result"]
    assert d["result"]["temporal"]["temporal_refold_events"] == 500  # disclosed re-fold of the covered prefix
    assert d["result"]["temporal"]["terminal"]["compared"]


def _deep(conn, database_url, root, art, rid):
    vid = deep.create_deep_validation(conn, rid)
    drain(worker(database_url, root, art))
    return conn.execute("SELECT * FROM observation_deep_validations WHERE validation_id = %s", (vid,)).fetchone()


def _published(art, row):
    m = row["manifest"]
    return art / "observations" / row["replay_id"] / m["artifact_dir"] / "temporal.json"


@pytest.mark.db
def test_deep_v3_pending_final_tie_run_compares_the_clock_end_finish(database_url, conn, tmp_path):
    """The fixture feed ends exactly on its last barrier: the final closures exist only in the published finish."""
    root, art = tmp_path / "data", tmp_path / "art"
    ds = fixture_dataset(root)
    rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    drain(worker(database_url, root, art, checkpoint_events=1000))
    row = row_of(conn, rid)
    last = ranges(conn, rid)[-1]
    published = json.loads(_published(art, row).read_text(encoding="utf-8"))
    assert published["aggregate_chain"] != last["aggregate_chain"]  # the finish sealed records after the last range
    d = _deep(conn, database_url, root, art, rid)
    res = d["result"]
    assert d["status"] == "completed" and res["outcome"] == "match", res
    assert res["temporal"]["terminal"]["compared"] and res["temporal"]["terminal"]["comparisons"] == 11


@pytest.mark.db
def test_deep_v3_detects_tampering_of_only_the_finished_temporal_output(database_url, conn, tmp_path):
    root, art = tmp_path / "data", tmp_path / "art"
    ds = fixture_dataset(root)
    rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    drain(worker(database_url, root, art))
    row = row_of(conn, rid)
    path = _published(art, row)
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["aggregate_chain"] = "e" * 64  # a consistent but wrong finished output; pre-finish records untouched
    data = json.dumps(doc, indent=2, sort_keys=True).encode()
    path.write_bytes(data)
    import hashlib

    m = row["manifest"]
    m["artifacts"] = [dict(a, sha256=hashlib.sha256(data).hexdigest(), bytes=len(data)) if a["name"] == "temporal.json"
                      else a for a in m["artifacts"]]
    m["temporal"]["aggregate_chain"] = "e" * 64
    conn.execute("UPDATE observation_replays SET manifest = %s WHERE replay_id = %s",
                 (psycopg.types.json.Jsonb(m), rid))
    before = [dict(r) for r in ranges(conn, rid)]
    d = _deep(conn, database_url, root, art, rid)
    res = d["result"]
    assert res["outcome"] == "mismatch", res
    assert {x["kind"] for x in res["mismatches"]} == {"terminal_aggregate_chain", "terminal_shadow_aggregate_chain"}
    assert [dict(r) for r in ranges(conn, rid)] == before  # the original run's records are never modified


@pytest.mark.db
@pytest.mark.parametrize("damage", ["absent", "corrupt", "unlisted"])
def test_deep_v3_without_usable_terminal_evidence_never_matches(database_url, conn, tmp_path, damage):
    root, art = tmp_path / "data", tmp_path / "art"
    ds = fixture_dataset(root)
    rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    drain(worker(database_url, root, art))
    row = row_of(conn, rid)
    path = _published(art, row)
    if damage == "absent":
        path.unlink()
    elif damage == "corrupt":
        path.write_bytes(path.read_bytes().replace(b"aggregate_chain", b"aggregate_chaim"))
    else:
        m = row["manifest"]
        m["artifacts"] = [a for a in m["artifacts"] if a["name"] != "temporal.json"]
        conn.execute("UPDATE observation_replays SET manifest = %s WHERE replay_id = %s",
                     (psycopg.types.json.Jsonb(m), rid))
    d = _deep(conn, database_url, root, art, rid)
    assert d["status"] == "failed" and d["result"]["outcome"] == "error", d["result"]
    assert "terminal temporal evidence" in d["error"]


@pytest.mark.db
def test_deep_v3_keeps_prefix_only_scope_for_cancelled_and_paused_targets(database_url, conn, tmp_path):
    root, art = tmp_path / "data", tmp_path / "art"
    ds = fixture_dataset(root)
    rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0, paused=True)
    drain(worker(database_url, root, art))
    for _ in range(20):
        control.step(conn, rid)
        drain(worker(database_url, root, art))
    assert row_of(conn, rid)["status"] == "paused"
    d = _deep(conn, database_url, root, art, rid)
    res = d["result"]
    assert res["outcome"] == "match" and res["covered_events"] == 20 and res["target_events"] == 20
    assert res["temporal"]["terminal"]["compared"] is False and "no finish" in res["temporal"]["terminal"]["scope"]
    assert d["plan"]["terminal"] is None
    control.cancel(conn, rid)
    drain(worker(database_url, root, art))
    assert row_of(conn, rid)["status"] == "cancelled"
    d2 = _deep(conn, database_url, root, art, rid)
    assert d2["result"]["outcome"] == "match" and d2["result"]["temporal"]["terminal"]["compared"] is False


# ---------------------------------------------------------------------------
# Legacy compatibility, migration suspension, inspection and copy reports
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_legacy_stream_v1_runs_keep_their_formats_validator_and_deep_claims(database_url, conn, tmp_path,
                                                                             monkeypatch):
    root, art = tmp_path / "data", tmp_path / "art"
    ds = fixture_dataset(root)
    monkeypatch.setattr(observe_job, "ENGINE_FORMAT", "observe.stream.v1")
    monkeypatch.setattr(observe_job, "temporal_config", lambda manifest: None)
    rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    drain(worker(database_url, root, art, checkpoint_events=11))
    row = row_of(conn, rid)
    assert row["status"] == "completed" and row["engine_format"] == "observe.stream.v1"
    v = row["manifest"]["validation"]
    assert v["validator_version"] == "2" and v["passed"]
    assert not [c for c in v["checks"] if c["name"].startswith("temporal")]
    assert row["manifest"]["temporal"] is None and row["temporal_view"] is None
    assert all(r["temporal_sha256"] is None for r in ranges(conn, rid))
    assert replay_view(row)["temporal"] is None
    vid = deep.create_deep_validation(conn, rid)
    drain(worker(database_url, root, art))
    res = conn.execute("SELECT result FROM observation_deep_validations WHERE validation_id = %s",
                       (vid,)).fetchone()["result"]
    assert res["outcome"] == "match" and res["validator_version"] == "1" and "temporal" not in res


@pytest.mark.db
def test_migration_10_suspends_pre_r2_nonterminal_runs_read_only(database_url, conn, tmp_path):
    root = tmp_path / "data"
    ds = fixture_dataset(root)
    rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    conn.execute("UPDATE observation_replays SET lifecycle_version = 3 WHERE replay_id = %s", (rid,))
    conn.execute(db.SCHEMA_V10)  # idempotent additive migration body
    row = row_of(conn, rid)
    assert row["suspended_at"] is not None and row["suspension"]["migration"] == 10
    assert row["suspension"]["historical_status"] == "queued" and row["status"] == "queued"
    with pytest.raises(control.ControlRejected):
        control.resume(conn, rid)
    assert not worker(database_url, root, tmp_path / "art").run_once()  # never claimed or replayed


@pytest.mark.db
def test_inspection_view_and_copy_report_expose_the_temporal_substrate(database_url, conn, tmp_path):
    root, art = tmp_path / "data", tmp_path / "art"
    ds = synthetic_dataset(root)
    rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    drain(worker(database_url, root, art))
    row = row_of(conn, rid)
    view = replay_view(row)["temporal"]
    assert view["note"] == "temporal substrate only; no adviser"
    assert view["clock_policy"] == "temporal.clock.modeled-complete-prefix.v1"
    c = view["committed"]
    assert c["admitted_cursor"] == row["applied"] and len(c["tracks"]) == 18 and c["readiness"]
    md_text = diagnostics.render_markdown(diagnostics.diagnostic_report(row, art, datetime.now(UTC)))
    assert "## Temporal substrate (temporal substrate only; no adviser)" in md_text
    assert "seal-no-revision" in md_text and "temporal.clock.modeled-complete-prefix.v1" in md_text
    assert "engineering demonstration dependencies only" in md_text
    for word in ("LONG", "SHORT", "buy", "sell", "profit"):
        assert word not in md_text.split("## Temporal substrate")[1].split("## ")[0]
