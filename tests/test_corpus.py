"""WP-008 corpus plan, local corpus state and durable corpus acquisition jobs.

Offline only: acquisitions use the captured OKX fixtures through the real
``OkxPublicClient`` (tests/okx_fake.py). Tests that need a chunk matching the
20-minute fixture use a tiny test plan via ``ALGOTRADER_CORPUS_PLAN``; the
checked-in plan itself is asserted exactly.
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path

import psycopg
import psycopg.rows
import pytest
from fastapi.testclient import TestClient
from okx_fake import CONFIRMED_END, FIXTURE_END, FIXTURE_START, FakeOkx, client

from algotrader.api import create_app
from algotrader.corpus import job as cj
from algotrader.corpus import state
from algotrader.corpus.plan import PLAN_FILE, CorpusPlan, load_plan
from algotrader.marketdata import dataset as md

TEST_PLAN = {
    "plan_id": "test-corpus",
    "plan_version": 1,
    "description": "tiny deterministic test plan matching the captured OKX fixture window",
    "source": "okx",
    "inst_id": "BTC-USDT-SWAP",
    "bar": "1m",
    "families": ["instrument", "trade_candles_1m", "mark_candles_1m", "index_candles_1m", "funding_rates"],
    "target": {"start": "2026-09-30T07:50:00Z", "end": "2026-09-30T08:30:00Z"},
    "chunk_rule": "test",
    "chunks": [
        {"chunk_id": "test-chunk", "label": "Fixture window", "start": "2026-09-30T07:50:00Z",
         "end": "2026-09-30T08:10:00Z", "preparable": True, "note": "test"},
        {"chunk_id": "test-locked", "label": "Locked", "start": "2026-09-30T08:10:00Z",
         "end": "2026-09-30T08:30:00Z", "preparable": False, "note": "planned"},
    ],
}


@pytest.fixture
def plan_file(tmp_path: Path, monkeypatch) -> Path:
    p = tmp_path / "plan.json"
    p.write_text(json.dumps(TEST_PLAN), encoding="utf-8")
    monkeypatch.setenv("ALGOTRADER_CORPUS_PLAN", str(p))
    return p


@pytest.fixture
def conn(database_url):
    with psycopg.connect(database_url, autocommit=True, row_factory=psycopg.rows.dict_row) as c:
        yield c


class NoNetwork:
    """Transport that fails the test if any request is made."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, url, headers, timeout):
        self.calls += 1
        raise AssertionError(f"unexpected network request {url}")


def corpus_worker(database_url, root, transport, **kw) -> cj.CorpusWorker:
    return cj.CorpusWorker(database_url, root, worker_id=kw.pop("worker_id", "corpus:test"), lease_seconds=5,
                           poll_interval=0.01, heartbeat_interval=0.05, sleep=lambda s: None,
                           client_factory=lambda base: client(transport, base_url=base), **kw)


def job_row(c, job_id):
    return c.execute("SELECT * FROM corpus_jobs WHERE job_id = %s", (job_id,)).fetchone()


def tmp_dirs(root: Path) -> list[Path]:
    base = md.datasets_dir(root)
    return [p for p in base.iterdir() if p.name.startswith(".tmp-")] if base.is_dir() else []


# ---------------------------------------------------------------------------
# Plan
# ---------------------------------------------------------------------------


def test_checked_in_plan_target_and_initial_chunk_are_exact(monkeypatch):
    monkeypatch.delenv("ALGOTRADER_CORPUS_PLAN", raising=False)
    plan = load_plan()
    assert plan == load_plan(PLAN_FILE)
    assert plan.source == "okx" and plan.inst_id == "BTC-USDT-SWAP" and plan.bar == "1m"
    assert plan.target.start == datetime(2025, 9, 1, tzinfo=UTC)
    assert plan.target.end == datetime(2026, 9, 1, tzinfo=UTC)
    first = plan.chunks[0]
    assert (first.chunk_id, first.start, first.end) == (
        "btc-okx-2025-09", datetime(2025, 9, 1, tzinfo=UTC), datetime(2025, 10, 1, tzinfo=UTC))
    assert [c.chunk_id for c in plan.chunks if c.preparable] == ["btc-okx-2025-09"]
    # twelve contiguous calendar months covering exactly the target; later chunks PLANNED/locked
    assert len(plan.chunks) == 12
    assert plan.chunks[-1].chunk_id == "btc-okx-2026-08" and plan.chunks[-1].end == plan.target.end
    assert all(a.end == b.start for a, b in zip(plan.chunks, plan.chunks[1:]))


def test_plan_rejects_oversized_overlapping_or_non_okx_chunks():
    bad = json.loads(json.dumps(TEST_PLAN))
    bad["source"] = "binance"
    with pytest.raises(ValueError):
        CorpusPlan.model_validate(bad)
    bad = json.loads(json.dumps(TEST_PLAN))
    bad["chunks"][1]["start"] = "2026-09-30T08:00:00Z"
    with pytest.raises(ValueError):
        CorpusPlan.model_validate(bad)
    bad = json.loads(json.dumps(TEST_PLAN))
    bad["target"]["end"] = "2026-12-30T00:00:00Z"
    bad["chunks"][1]["end"] = "2026-12-30T00:00:00Z"
    with pytest.raises(ValueError):
        CorpusPlan.model_validate(bad)


# ---------------------------------------------------------------------------
# marketdata.acquire progress hook: optional, default behavior unchanged
# ---------------------------------------------------------------------------


def test_progress_hook_does_not_change_the_dataset(tmp_path):
    plain = md.acquire(client(FakeOkx()), tmp_path / "a", FIXTURE_START, FIXTURE_END)
    seen: list[md.AcquireProgress] = []
    hooked = md.acquire(client(FakeOkx()), tmp_path / "b", FIXTURE_START, FIXTURE_END, progress=seen.append)
    assert hooked.manifest.dataset_id == plain.manifest.dataset_id
    files_a = {f.name: f.sha256 for f in plain.manifest.files if f.name != "manifest.json"}
    files_b = {f.name: f.sha256 for f in hooked.manifest.files if f.name != "manifest.json"}
    raw = {k: v for k, v in files_a.items() if k.startswith("raw/") or k.endswith(".parquet")}
    assert raw == {k: v for k, v in files_b.items() if k in raw}
    assert seen[-1].phase == "finalizing" and seen[-1].windows_done == seen[-1].windows_total == 4
    assert seen[-1].pages == hooked.manifest.raw_page_count
    assert [p.windows_done for p in seen] == sorted(p.windows_done for p in seen)
    assert all(p.work_dir.startswith(".tmp-") for p in seen) and not tmp_dirs(tmp_path / "b")


def test_progress_hook_can_abort_at_a_page_boundary_without_publishing(tmp_path):
    class Stop(Exception):
        pass

    def hook(p: md.AcquireProgress) -> None:
        if p.pages >= 3:
            raise Stop()

    with pytest.raises(Stop):
        md.acquire(client(FakeOkx()), tmp_path, FIXTURE_START, FIXTURE_END, progress=hook)
    assert md.list_manifests(tmp_path) == [] and not tmp_dirs(tmp_path)


# ---------------------------------------------------------------------------
# Durable jobs
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_api_prepare_only_queues_and_only_the_initial_chunk_is_preparable(database_url, tmp_path, monkeypatch):
    monkeypatch.delenv("ALGOTRADER_CORPUS_PLAN", raising=False)
    root = tmp_path / "data"
    api = TestClient(create_app(database_url, tmp_path / "art", web_dist=tmp_path / "no-ui", data_root=root))
    doc = api.get("/api/corpus").json()
    assert doc["plan"]["target"] == {"start": "2025-09-01T00:00:00+00:00", "end": "2026-09-01T00:00:00+00:00"}
    status = {c["chunk_id"]: c["status"] for c in doc["chunks"]}
    assert status["btc-okx-2025-09"] == "not_prepared"
    assert {v for k, v in status.items() if k != "btc-okx-2025-09"} == {"planned"}
    assert api.post("/api/corpus/chunks/btc-okx-2025-10/prepare").status_code == 422
    assert api.post("/api/corpus/chunks/nope/prepare").status_code == 404
    res = api.post("/api/corpus/chunks/btc-okx-2025-09/prepare")
    assert res.status_code == 201
    job = res.json()
    # the request only recorded a queued job: no worker ran, nothing was fetched or written
    assert job["status"] == "queued" and job["runtime_state"] == "queued"
    assert not (root / "datasets").exists()
    assert api.post("/api/corpus/chunks/btc-okx-2025-09/prepare").status_code == 409  # one active job per chunk
    chunk = next(c for c in api.get("/api/corpus").json()["chunks"] if c["chunk_id"] == "btc-okx-2025-09")
    assert chunk["status"] == "preparing" and chunk["latest_job"]["job_id"] == job["job_id"]
    assert "from scratch" in job["recovery_behavior"]
    # cancelling a queued job never starts it
    assert api.post(f"/api/corpus/jobs/{job['job_id']}/cancel").json()["status"] == "cancelled"
    assert api.post(f"/api/corpus/jobs/{job['job_id']}/cancel").status_code == 409


@pytest.mark.db
def test_non_okx_source_is_impossible(database_url, conn, tmp_path, monkeypatch, plan_file):
    plan = load_plan()
    with pytest.raises(cj.CorpusJobRejected):
        cj.create_job(conn, plan, "test-chunk", base_url="https://api.example.com")
    monkeypatch.setenv("ALGOTRADER_OKX_BASE_URL", "https://okx.com.evil.example")
    api = TestClient(create_app(database_url, tmp_path / "art", web_dist=tmp_path / "no-ui", data_root=tmp_path))
    res = api.post("/api/corpus/chunks/test-chunk/prepare")
    assert res.status_code == 422 and "not an official OKX host" in res.json()["detail"]
    assert conn.execute("SELECT count(*) AS n FROM corpus_jobs").fetchone()["n"] == 0


@pytest.mark.db
def test_worker_acquires_verifies_and_binds_then_reuses_without_network(database_url, conn, tmp_path, plan_file):
    root = tmp_path / "data"
    plan = load_plan()
    job_id = cj.create_job(conn, plan, "test-chunk")
    fake = FakeOkx()
    w = corpus_worker(database_url, root, fake)
    assert w.run_once() and not w.run_once()
    row = job_row(conn, job_id)
    assert row["status"] == "completed" and row["outcome"] == "acquired" and row["attempt"] == 1
    assert row["progress"]["windows_done"] == row["progress"]["windows_total"] and row["progress"]["pages"] > 0
    binding = conn.execute("SELECT * FROM corpus_chunks WHERE chunk_id = 'test-chunk'").fetchone()
    ds = binding["dataset_id"]
    assert row["dataset_id"] == ds and binding["verification_ok"]
    path = md.dataset_path(root, ds)
    assert md.verify(path) == [] and binding["manifest_sha256"] == state.manifest_sha256(path)
    storage = binding["storage"]
    assert storage["total_bytes"] == binding["bytes_on_disk"] > storage["raw_bytes"] > 0
    assert storage["parquet_bytes"] > 0 and storage["raw_page_count"] == md.load_manifest(path).raw_page_count
    assert {f["family"] for f in storage["families"]} == {"trade_candles_1m", "mark_candles_1m", "index_candles_1m",
                                                          "funding_rates"}
    calls = len(fake.calls)

    # Prepare again: the verified binding is reused, no network request at all
    job2 = cj.create_job(conn, plan, "test-chunk")
    offline = NoNetwork()
    corpus_worker(database_url, root, offline).run_once()
    row2 = job_row(conn, job2)
    assert row2["status"] == "completed" and row2["outcome"] == "reused_binding" and offline.calls == 0
    assert len(fake.calls) == calls
    assert len(md.list_manifests(root)) == 1  # nothing duplicated

    api = TestClient(create_app(database_url, tmp_path / "art", web_dist=tmp_path / "no-ui", data_root=root))
    chunk = next(c for c in api.get("/api/corpus").json()["chunks"] if c["chunk_id"] == "test-chunk")
    assert chunk["status"] == "prepared" and chunk["local"]["dataset_id"] == ds and chunk["local"]["usable"]
    assert chunk["local"]["bytes_on_disk"] == storage["total_bytes"]
    assert "work_dir" not in chunk["latest_job"]["progress"]  # no private paths in the Owner view
    locked = next(c for c in api.get("/api/corpus").json()["chunks"] if c["chunk_id"] == "test-locked")
    assert locked["status"] == "planned" and not locked["preparable"]


@pytest.mark.db
def test_exact_local_dataset_is_adopted_without_network(database_url, conn, tmp_path, plan_file):
    root = tmp_path / "data"
    md.acquire(client(FakeOkx()), root, FIXTURE_START, CONFIRMED_END)  # different interval: never adopted
    ds = md.acquire(client(FakeOkx()), root, FIXTURE_START, FIXTURE_END).manifest.dataset_id
    job_id = cj.create_job(conn, load_plan(), "test-chunk")
    offline = NoNetwork()
    corpus_worker(database_url, root, offline).run_once()
    row = job_row(conn, job_id)
    assert row["status"] == "completed" and row["outcome"] == "adopted_local_dataset" and row["dataset_id"] == ds
    assert offline.calls == 0


@pytest.mark.db
def test_logical_interval_mismatch_is_rejected(database_url, conn, tmp_path, plan_file):
    root = tmp_path / "data"
    other = md.acquire(client(FakeOkx()), root, FIXTURE_START, CONFIRMED_END)
    plan = load_plan()
    chunk = plan.chunk("test-chunk")
    assert state.find_local_match(root, plan, chunk) == []
    with pytest.raises(state.CorpusMismatch, match="not the chunk interval"):
        with conn.transaction():
            state.bind(conn, plan, chunk, other.path, None, "manual", datetime.now(UTC))
    assert conn.execute("SELECT count(*) AS n FROM corpus_chunks").fetchone()["n"] == 0


@pytest.mark.db
def test_missing_or_altered_binding_is_not_reported_prepared(database_url, conn, tmp_path, plan_file):
    root = tmp_path / "data"
    cj.create_job(conn, load_plan(), "test-chunk")
    corpus_worker(database_url, root, FakeOkx()).run_once()
    api = TestClient(create_app(database_url, tmp_path / "art", web_dist=tmp_path / "no-ui", data_root=root))

    def status():
        return next(c for c in api.get("/api/corpus").json()["chunks"] if c["chunk_id"] == "test-chunk")

    assert status()["status"] == "prepared"
    ds = status()["local"]["dataset_id"]
    manifest = md.dataset_path(root, ds) / "manifest.json"
    original = manifest.read_bytes()
    manifest.write_bytes(original + b" ")
    assert status()["status"] == "invalid" and "changed" in status()["local"]["problem"]
    # the launch itself never hashes (<=1 s durable launch); the worker-owned preparation re-checks the
    # manifest hash recorded at binding and fails the run visibly instead of replaying altered evidence
    ev = api.post("/api/evaluations", json={"chunk_id": "test-chunk", "speed": 0})
    assert ev.status_code == 201
    from algotrader.observe.worker import ObservationWorker

    ObservationWorker(database_url, root, tmp_path / "art", worker_id="observe:t", isolate=False).run_once()
    rv = api.get(f"/api/evaluations/{ev.json()['evaluation_id']}").json()["replay"]
    assert rv["status"] == "failed" and "manifest changed since it was bound" in rv["error"]
    assert rv["configured"] is False
    manifest.write_bytes(original)
    assert status()["status"] == "prepared"
    moved = manifest.parent.with_name("moved-away")
    manifest.parent.rename(moved)
    assert status()["status"] == "invalid" and not status()["local"]["usable"]
    # preparing again re-acquires (the bound dataset is gone) and rebinds
    job_id = cj.create_job(conn, load_plan(), "test-chunk")
    corpus_worker(database_url, root, FakeOkx()).run_once()
    assert job_row(conn, job_id)["outcome"] == "acquired" and status()["status"] == "prepared"


@pytest.mark.db
def test_cancellation_stops_at_a_page_boundary_and_binds_nothing(database_url, conn, tmp_path, plan_file):
    root = tmp_path / "data"
    keep = md.acquire(client(FakeOkx()), root, FIXTURE_START, CONFIRMED_END)  # existing immutable dataset
    job_id = cj.create_job(conn, load_plan(), "test-chunk")
    fake = FakeOkx()

    def hook(family, page):
        if family.value == "mark_candles_1m":
            cj.cancel_job(conn, job_id)
            time.sleep(0.6)  # let the heartbeat (0.05 s) observe the durable cancel flag
        return page

    fake.page_hook = hook
    corpus_worker(database_url, root, fake).run_once()
    row = job_row(conn, job_id)
    assert row["status"] == "cancelled" and "no chunk bound" in row["error"]
    assert conn.execute("SELECT count(*) AS n FROM corpus_chunks").fetchone()["n"] == 0
    assert not tmp_dirs(root)
    assert [m.dataset_id for m in md.list_manifests(root)] == [keep.manifest.dataset_id]
    assert md.verify(keep.path) == []  # finalized datasets are never deleted by cancellation


@pytest.mark.db
def test_acquired_dataset_is_verified_before_binding(database_url, conn, tmp_path, plan_file, monkeypatch):
    root = tmp_path / "data"
    job_id = cj.create_job(conn, load_plan(), "test-chunk")
    monkeypatch.setattr(md, "verify", lambda path, progress=None: ["simulated hash mismatch"])
    corpus_worker(database_url, root, FakeOkx()).run_once()
    row = job_row(conn, job_id)
    assert row["status"] == "failed" and "failed verification" in row["error"]
    assert conn.execute("SELECT count(*) AS n FROM corpus_chunks").fetchone()["n"] == 0


class Crash(BaseException):
    """Stand-in for a hard worker death inside the acquisition."""


@pytest.mark.db
def test_worker_restart_reclaims_and_restarts_the_chunk_from_scratch(database_url, conn, tmp_path, plan_file):
    root = tmp_path / "data"
    job_id = cj.create_job(conn, load_plan(), "test-chunk")
    fake = FakeOkx()

    def die(family, page):
        if family.value == "index_candles_1m":
            raise Crash()
        return page

    fake.page_hook = die
    with pytest.raises(Crash):
        corpus_worker(database_url, root, fake, worker_id="corpus:dead").run_once()
    row = job_row(conn, job_id)
    assert row["status"] == "running" and row["lease_owner"] == "corpus:dead"
    # a hard death can leave the attempt's temporary directory behind; simulate it
    orphan = md.datasets_dir(root) / ".tmp-deadbeef"
    orphan.mkdir(parents=True)
    conn.execute("UPDATE corpus_jobs SET progress = progress || '{\"work_dir\": \".tmp-deadbeef\"}'::jsonb, "
                 "lease_expires_at = now() - interval '1 second' WHERE job_id = %s", (job_id,))
    api = TestClient(create_app(database_url, tmp_path / "art", web_dist=tmp_path / "no-ui", data_root=root))
    view = api.get(f"/api/corpus/jobs/{job_id}").json()
    # lease expired alone is "unresponsive / awaiting recovery", never "recovering"
    assert view["runtime_state"] == "unresponsive" and view["operation"]["health"] == "unresponsive"
    assert "CORPUS_PREPARATION_DIAGNOSTIC" in api.get(f"/api/corpus/jobs/{job_id}/report.md").text

    corpus_worker(database_url, root, FakeOkx(), worker_id="corpus:new").run_once()
    row = job_row(conn, job_id)
    assert row["status"] == "completed" and row["attempt"] == 2 and row["outcome"] == "acquired"
    assert [e["event"] for e in row["recovery_log"]] == ["lease_expired_reclaimed"]
    assert "from scratch" in row["recovery_log"][0]["detail"] and "removed" in row["recovery_log"][0]["detail"]
    assert not orphan.exists() and not tmp_dirs(root)
    assert conn.execute("SELECT dataset_id FROM corpus_chunks").fetchone()["dataset_id"] == row["dataset_id"]


@pytest.mark.db
def test_repeated_interruptions_fail_explicitly_without_binding(database_url, conn, tmp_path, plan_file):
    root = tmp_path / "data"
    job_id = cj.create_job(conn, load_plan(), "test-chunk")
    conn.execute("UPDATE corpus_jobs SET status = 'running', lease_owner = 'corpus:gone', attempt = 2, "
                 "interruptions = 2, lease_expires_at = now() - interval '1 second' WHERE job_id = %s", (job_id,))
    offline = NoNetwork()
    corpus_worker(database_url, root, offline).run_once()
    row = job_row(conn, job_id)
    assert row["status"] == "failed" and "consecutive attempts" in row["error"] and offline.calls == 0
    assert conn.execute("SELECT count(*) AS n FROM corpus_chunks").fetchone()["n"] == 0


@pytest.mark.db
def test_health_reports_the_corpus_capability(database_url, conn, tmp_path, plan_file):
    api = TestClient(create_app(database_url, tmp_path / "art", web_dist=tmp_path / "no-ui", data_root=tmp_path))
    caps = api.get("/api/health").json()["capabilities"]
    assert caps["corpus"]["status"] == "unavailable" and caps["core"]["status"] == "available"
    cj.create_job(conn, load_plan(), "test-chunk")
    assert api.get("/api/health").json()["capabilities"]["corpus"]["status"] == "stalled"
    w = corpus_worker(database_url, tmp_path, NoNetwork(), worker_id="corpus:idle")
    with w._conn() as c:
        w.beat(c, None)
    h = api.get("/api/health").json()
    assert h["capabilities"]["corpus"]["status"] == "available" and h["corpus_workers"]["alive"] == 1
    assert h["workers"]["alive"] == 0  # a corpus worker is not a synthetic run worker
    assert h["capabilities"]["recorder"]["status"] == "unavailable"  # optional recorder stays distinct
