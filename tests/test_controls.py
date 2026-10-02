"""WP-008-R1C control and durability closure (bounded engineering fixtures, declared local load).

Declared load: test-only CPU busy work per cooperative unit (``<PHASE>_cpu_per_unit`` faults) stands in for a
slow disk / busy CPU, so every long unit really takes time. Targets: acknowledgement <=1 s; control applied
normally <=2 s, and <=5 s at a bounded safe unit. Measured latencies are printed (CONTROL_MATRIX).
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg
import psycopg.rows
import pytest
from fastapi.testclient import TestClient
from okx_fake import FIXTURE_END, FIXTURE_START, FakeOkx, client
from okx_synth import synthetic_fake

from algotrader.api import create_app
from algotrader.feed.adapter import build_feed
from algotrader.feed.ordering import default_freshness
from algotrader.marketdata import dataset as md
from algotrader.observe import control
from algotrader.observe import feedcache as fc
from algotrader.observe.contracts import SourceKind
from algotrader.observe.core import ReplayCore
from algotrader.observe.job import SimulatedCrash
from algotrader.observe.worker import ObservationWorker

pytestmark = pytest.mark.db
FRESH = default_freshness()
MATRIX: list[dict] = []


@pytest.fixture
def conn(database_url):
    with psycopg.connect(database_url, autocommit=True, row_factory=psycopg.rows.dict_row) as c:
        yield c


def add_large_file(dataset_dir: Path, mib: int) -> None:
    """Add one large hash-listed file to a package (a single long copy/hash unit), updating its manifest."""
    big = dataset_dir / "large_attachment.bin"
    with big.open("wb") as f:
        for i in range(mib):
            f.write(hashlib.sha256(str(i).encode()).digest() * 32768)
    m = json.loads((dataset_dir / "manifest.json").read_text(encoding="utf-8"))
    m["files"].append({"name": big.name, "sha256": md.sha256_file(big), "bytes": big.stat().st_size, "rows": None,
                       "media_type": "application/octet-stream"})
    (dataset_dir / "manifest.json").write_text(json.dumps(m, indent=2), encoding="utf-8")


def worker(database_url, root, art, **kw) -> ObservationWorker:
    kw.setdefault("worker_id", "observe:ctl")
    kw.setdefault("isolate", False)
    kw.setdefault("progress_interval", 0.1)
    return ObservationWorker(database_url, root, art, lease_seconds=5, poll_interval=0.01, **kw)


def wait_stage(conn, rid, pred, timeout=120.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        r = conn.execute("SELECT phase, progress, last_progress_at, status FROM observation_replays "
                         "WHERE replay_id = %s", (rid,)).fetchone()
        if pred(r):
            return r
        if r["status"] in ("completed", "failed", "cancelled"):
            raise AssertionError(f"finished before the stage was reached: {r['status']} {r['phase']}")
        time.sleep(0.01)
    raise AssertionError("stage not reached")


def cancel_case(database_url, conn, api, root, art, ds, label, pred, faults, **wkw):
    rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    w = worker(database_url, root, art, faults=faults, **wkw)
    t = threading.Thread(target=w.run_once, daemon=True)
    t.start()
    seen = wait_stage(conn, rid, pred)
    refresh_age = (datetime.now(UTC) - seen["last_progress_at"]).total_seconds()
    t0 = time.perf_counter()
    assert api.post(f"/api/observations/{rid}/cancel").status_code == 200
    ack = time.perf_counter() - t0
    t.join(60)
    applied = time.perf_counter() - t0
    r = conn.execute("SELECT status, error, phase FROM observation_replays WHERE replay_id = %s", (rid,)).fetchone()
    MATRIX.append({"unit": label, "phase": seen["phase"], "stage": (seen["progress"] or {}).get("stage"),
                   "ack_s": round(ack, 3), "applied_s": round(applied, 3), "progress_age_s": round(refresh_age, 3),
                   "status": r["status"]})
    assert r["status"] == "cancelled", r
    assert ack < 1.0 and applied < 2.0 and refresh_age < 2.0, MATRIX[-1]
    return rid


def test_control_latency_matrix_under_declared_load(database_url, conn, tmp_path, monkeypatch):
    root, art = tmp_path / "data", tmp_path / "art"
    api = TestClient(create_app(database_url, art, web_dist=tmp_path / "no-ui", data_root=root))
    s0 = datetime(2026, 8, 1, tzinfo=UTC)
    ds = md.acquire(client(synthetic_fake(s0, s0 + 3 * timedelta(days=1), gaps=((s0 + timedelta(hours=6),
                                                                                    s0 + timedelta(days=2)),))),
                    root, s0, s0 + timedelta(days=3)).manifest.dataset_id
    add_large_file(md.dataset_path(root, ds), 48)  # a single 48 MiB copy/hash unit
    stage = lambda prefix: (lambda r: str((r["progress"] or {}).get("stage") or "").startswith(prefix))  # noqa: E731
    cancel_case(database_url, conn, api, root, art, ds, "snapshot copy (single 48 MiB file)",
                stage("snapshot large_attachment.bin"), {"VERIFYING_SOURCE_cpu_per_unit": 0.05})
    cancel_case(database_url, conn, api, root, art, ds, "source hashing (single 48 MiB file)",
                stage("hash large_attachment.bin"), {"VERIFYING_SOURCE_cpu_per_unit": 0.05})
    cancel_case(database_url, conn, api, root, art, ds, "long-gap absent-slot walk (no yields)",
                stage("classify absent slots"), {"BUILDING_FEED_cpu_per_unit": 0.2})
    monkeypatch.setattr(fc, "SORT_BLOCK", 200)
    monkeypatch.setattr(fc, "FAN_IN", 2)
    cancel_case(database_url, conn, api, root, art, ds, "external multi-pass merge",
                stage("merge order sort runs"), {"BUILDING_FEED_cpu_per_unit": 0.2})
    monkeypatch.undo()
    # warm cache from here on (built once without faults)
    warm = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    while worker(database_url, root, art, sleep=lambda s: None).run_once():
        pass
    assert conn.execute("SELECT status FROM observation_replays WHERE replay_id = %s", (warm,)).fetchone()[
        "status"] == "completed"
    cancel_case(database_url, conn, api, root, art, ds, "replay (applying events)",
                lambda r: r["phase"] == "REPLAYING", {"REPLAYING_cpu_per_unit": 0.002})
    cancel_case(database_url, conn, api, root, art, ds, "terminal reconciliation (re-hash consumed input)",
                lambda r: r["phase"] == "VALIDATING", {"VALIDATING_cpu_per_unit": 0.3})
    cancel_case(database_url, conn, api, root, art, ds, "report serialization / artifact hashing",
                lambda r: r["phase"] == "GENERATING_REPORT", {"GENERATING_REPORT_cpu_per_unit": 0.3})
    # pause and STEP during replay
    rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    w = worker(database_url, root, art, faults={"REPLAYING_cpu_per_unit": 0.002})
    t = threading.Thread(target=w.run_once, daemon=True)
    t.start()
    wait_stage(conn, rid, lambda r: r["phase"] == "REPLAYING")
    t0 = time.perf_counter()
    api.post(f"/api/observations/{rid}/pause")
    t.join(30)
    paused = time.perf_counter() - t0
    r = conn.execute("SELECT r.status, k.cursor FROM observation_replays r JOIN observation_checkpoints k "
                     "USING (replay_id) WHERE replay_id = %s", (rid,)).fetchone()
    assert r["status"] == "paused" and paused < 2.0
    MATRIX.append({"unit": "pause during replay", "applied_s": round(paused, 3), "status": "paused"})
    t0 = time.perf_counter()
    api.post(f"/api/observations/{rid}/step")
    worker(database_url, root, art, sleep=lambda s: None).run_once()
    stepped = time.perf_counter() - t0
    r2 = conn.execute("SELECT cursor FROM observation_checkpoints WHERE replay_id = %s", (rid,)).fetchone()
    assert r2["cursor"] == r["cursor"] + 1 and stepped < 2.0
    MATRIX.append({"unit": "STEP one event (claim + restore + commit)", "applied_s": round(stepped, 3),
                   "status": "paused"})
    MATRIX.append({"unit": "terminal publication (rename + DB commit)", "applied_s": None,
                   "status": "atomic save boundary under the replay row lock (cancel is serialized before/after)"})
    print("CONTROL_MATRIX", json.dumps(MATRIX))


# ---------------------------------------------------------------------------
# Durability / referenced-file faults
# ---------------------------------------------------------------------------


def _crash_at(rid, at):
    def hook(replay_id, cursor):
        if replay_id == rid and cursor == at:
            raise SimulatedCrash()
    return hook


def test_lost_cache_during_a_resumable_run_is_rebuilt_to_its_receipt(database_url, conn, tmp_path):
    root, art = tmp_path / "data", tmp_path / "art"
    ds = md.acquire(client(FakeOkx()), root, FIXTURE_START, FIXTURE_END).manifest.dataset_id
    ref = build_feed(md.dataset_path(root, ds))
    good = ReplayCore(ref, FRESH).at(ref.manifest.event_count).snapshot.content_digest
    rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    with pytest.raises(SimulatedCrash):
        worker(database_url, root, art, worker_id="observe:a", checkpoint_events=10,
               after_commit=_crash_at(rid, 30)).run_once()
    eng = conn.execute("SELECT engine FROM observation_replays WHERE replay_id = %s", (rid,)).fetchone()["engine"]
    shutil.rmtree(fc.cache_root(root) / eng["cache_id"])  # referenced cache lost while the run is resumable
    conn.execute("UPDATE observation_replays SET lease_expires_at = now() - interval '1 second' WHERE replay_id = %s",
                 (rid,))
    while worker(database_url, root, art, worker_id="observe:b", checkpoint_events=10).run_once():
        pass
    r = conn.execute("SELECT r.*, k.snapshot_digest FROM observation_replays r JOIN observation_checkpoints k "
                     "USING (replay_id) WHERE replay_id = %s", (rid,)).fetchone()
    assert r["status"] == "completed" and r["snapshot_digest"] == good
    assert r["engine"] == eng  # pins never rewritten
    g2 = r["metrics"]["2"]
    assert g2["feed_builds"] == 1 and g2["prefix_restore_events"] == 0  # rebuilt from source, restored directly


def test_lost_cache_with_changed_source_fails_safely_with_an_actionable_report(database_url, conn, tmp_path):
    root, art = tmp_path / "data", tmp_path / "art"
    ds = md.acquire(client(FakeOkx()), root, FIXTURE_START, FIXTURE_END).manifest.dataset_id
    api = TestClient(create_app(database_url, art, web_dist=tmp_path / "no-ui", data_root=root))
    rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    with pytest.raises(SimulatedCrash):
        worker(database_url, root, art, worker_id="observe:a", checkpoint_events=10,
               after_commit=_crash_at(rid, 30)).run_once()
    eng = conn.execute("SELECT engine FROM observation_replays WHERE replay_id = %s", (rid,)).fetchone()["engine"]
    shutil.rmtree(fc.cache_root(root) / eng["cache_id"])
    p = md.dataset_path(root, ds) / "index_candles_1m.parquet"
    data = bytearray(p.read_bytes())
    data[len(data) // 3] ^= 0xFF
    p.write_bytes(bytes(data))  # the source no longer verifies (manifest unchanged)
    conn.execute("UPDATE observation_replays SET lease_expires_at = now() - interval '1 second' WHERE replay_id = %s",
                 (rid,))
    while worker(database_url, root, art, worker_id="observe:b").run_once():
        pass
    r = conn.execute("SELECT r.*, k.cursor FROM observation_replays r JOIN observation_checkpoints k "
                     "USING (replay_id) WHERE replay_id = %s", (rid,)).fetchone()
    assert r["status"] == "failed" and "failed verification" in r["error"]  # no resume on unverified input
    assert r["engine"] == eng and r["cursor"] == 30  # pins kept; committed evidence preserved
    rep = api.get(f"/api/observations/{rid}/report.md").text
    assert "failed verification" in rep and "Next diagnostic" in rep


def test_lost_or_corrupted_artifacts_are_reported_not_silently_trusted(database_url, conn, tmp_path):
    root, art = tmp_path / "data", tmp_path / "art"
    ds = md.acquire(client(FakeOkx()), root, FIXTURE_START, FIXTURE_END).manifest.dataset_id
    api = TestClient(create_app(database_url, art, web_dist=tmp_path / "no-ui", data_root=root))
    rid = control.create_replay(conn, root, SourceKind.DATASET, ds, speed=0)
    while worker(database_url, root, art).run_once():
        pass
    m = api.get(f"/api/observations/{rid}/manifest").json()
    gdir = art / "observations" / rid / m["artifact_dir"]
    (gdir / "ranges.jsonl").write_text("tampered\n", encoding="utf-8")
    raw = bytearray((gdir / "validation.json").read_bytes())
    raw[10] ^= 1  # same size, different content
    (gdir / "validation.json").write_bytes(bytes(raw))
    os.remove(gdir / "engine.json")
    rep = api.get(f"/api/observations/{rid}/report.json").json()["manifest"]
    state = {a["name"]: a for a in rep["artifacts"]}
    assert state["engine.json"]["present"] is False
    assert state["ranges.jsonl"]["size_matches"] is False
    assert state["validation.json"]["size_matches"] is True and state["validation.json"]["sha256_matches"] is False
    assert api.get(f"/api/observations/{rid}/files/engine.json").status_code == 410
    assert "engine.json" in api.get(f"/api/observations/{rid}/report.md").text
