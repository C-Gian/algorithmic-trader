"""API: commands, snapshots, SSE and artifact inspection."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from algotrader import db
from algotrader.api import create_app
from algotrader.contracts import SCHEMA_VERSION, Run
from algotrader.worker import Worker

pytestmark = pytest.mark.db


@pytest.fixture
def client(database_url, artifact_root, tmp_path):
    return TestClient(create_app(database_url, artifact_root, web_dist=tmp_path / "no-ui"))


def test_start_run_is_queued_not_executed_by_request(client):
    r = client.post("/api/runs", json={"speed": 0})
    assert r.status_code == 201
    run = r.json()
    assert run["status"] == "queued" and run["progress"]["steps_done"] == 0
    assert client.get("/api/runs").json()[0]["run_id"] == run["run_id"]


def test_invalid_start_is_rejected(client):
    assert client.post("/api/runs", json={"fault": "explode"}).status_code == 422
    assert client.post("/api/runs", json={"speed": -1}).status_code == 422
    assert client.get("/api/runs/nope").status_code == 404


def test_full_cycle_snapshot_and_artifacts(client, database_url, artifact_root, reference_trace):
    run_id = client.post("/api/runs", json={"speed": 0}).json()["run_id"]
    assert client.get(f"/api/runs/{run_id}/manifest").status_code == 404
    Worker(url=database_url, worker_id="w", artifact_root=artifact_root).run_once()

    snap = client.get(f"/api/runs/{run_id}/snapshot").json()
    assert snap["run"]["status"] == "completed"
    assert snap["run"]["progress"]["steps_done"] == 120
    assert snap["run"]["progress"]["sim_time"] == "2026-01-01T02:00:00Z"
    assert {"observation", "market_view", "decision", "account"} <= set(snap["latest"])
    assert snap["latest"]["market_view"]["demo"] is True

    assert len(client.get(f"/api/runs/{run_id}/prices").json()) == 120
    decisions = client.get(f"/api/runs/{run_id}/events", params={"kind": "decision", "limit": 5000}).json()
    assert len(decisions) == 120

    manifest = client.get(f"/api/runs/{run_id}/manifest").json()
    assert manifest["semantic_trace_hash"] == reference_trace[0]
    arts = client.get(f"/api/runs/{run_id}/artifacts").json()["artifacts"]
    assert {"decisions.parquet", "report.md", "validation.json"} <= {a["name"] for a in arts}
    view = client.get(f"/api/runs/{run_id}/artifacts/fills.parquet", params={"format": "json"}).json()
    assert view["rows"] == 8 and view["records"][0]["fill_id"].startswith("F-O")
    report = client.get(f"/api/runs/{run_id}/artifacts/report.md")
    assert report.status_code == 200 and "DEMO / SYNTHETIC" in report.text
    assert client.get(f"/api/runs/{run_id}/artifacts/../../secret").status_code == 404


def test_cancel_endpoint(client, database_url, artifact_root):
    run_id = client.post("/api/runs", json={"speed": 0}).json()["run_id"]
    assert client.post(f"/api/runs/{run_id}/cancel").json()["cancel_requested"] is True
    Worker(url=database_url, worker_id="w", artifact_root=artifact_root).run_once()
    assert client.get(f"/api/runs/{run_id}").json()["status"] == "cancelled"
    assert client.post(f"/api/runs/{run_id}/cancel").status_code == 409
    assert client.get(f"/api/runs/{run_id}/manifest").json()["status"] == "cancelled"


def test_sse_stream_starts_with_snapshot_and_ends_on_terminal(client, database_url, artifact_root):
    run_id = client.post("/api/runs", json={"speed": 0}).json()["run_id"]
    Worker(url=database_url, worker_id="w", artifact_root=artifact_root).run_once()
    with client.stream("GET", f"/api/runs/{run_id}/stream") as resp:
        body = "".join(resp.iter_text())
    blocks = [b for b in body.split("\n\n") if b.strip()]
    assert blocks[0].startswith("event: snapshot")
    first = json.loads(blocks[0].split("data: ", 1)[1])
    assert first["run"]["status"] == "completed"
    assert blocks[-1].startswith("event: end")


def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_manifest_identifies_semantic_schema_version(client, database_url, artifact_root):
    run_id = client.post("/api/runs", json={"speed": 0}).json()["run_id"]
    Worker(url=database_url, worker_id="w", artifact_root=artifact_root).run_once()
    manifest = client.get(f"/api/runs/{run_id}/manifest").json()
    assert manifest["schema_version"] == SCHEMA_VERSION == "algotrader.semantic.v1"
    assert manifest["replay_control"] == {"paused": False, "step_budget": 0, "speed": 0.0}
    assert client.get("/api/health").json()["schema_version"] == SCHEMA_VERSION


def test_run_view_conforms_to_run_contract(client):
    run = client.post("/api/runs", json={"speed": 3}).json()
    Run.model_validate(run)
    assert run["control"] == {"paused": False, "step_budget": 0, "speed": 3.0}
    assert "speed" not in run["config"]
    assert run["runtime_state"] == "queued"
    assert run["progress"]["eta_seconds"] is None and run["progress"]["eta_basis"].startswith("unavailable")


def test_pause_step_resume_speed_and_runtime_states(client, database_url, artifact_root):
    run_id = client.post("/api/runs", json={"speed": 0, "paused": True}).json()["run_id"]
    view = client.get(f"/api/runs/{run_id}").json()
    assert view["runtime_state"] == "paused" and view["control"]["paused"] is True
    w = Worker(url=database_url, worker_id="w", artifact_root=artifact_root)
    assert w.run_once() is False  # nothing happens while paused

    assert client.post(f"/api/runs/{run_id}/resume").status_code == 200
    assert client.post(f"/api/runs/{run_id}/resume").status_code == 409  # not paused
    assert client.post(f"/api/runs/{run_id}/step").status_code == 409  # only while paused
    assert client.post(f"/api/runs/{run_id}/pause").json()["runtime_state"] == "paused"

    stepped = client.post(f"/api/runs/{run_id}/step").json()
    assert stepped["runtime_state"] == "stepping" and stepped["control"]["step_budget"] == 1
    w.run_once()
    view = client.get(f"/api/runs/{run_id}").json()
    assert (view["runtime_state"], view["status"], view["progress"]["steps_done"]) == ("paused", "paused", 1)
    assert view["progress"]["eta_seconds"] is None and "paused" in view["progress"]["eta_basis"]

    assert client.post(f"/api/runs/{run_id}/speed", json={"speed": 2000}).status_code == 422
    assert client.post(f"/api/runs/{run_id}/speed", json={"speed": 7}).json()["control"]["speed"] == 7.0
    assert client.post("/api/runs/nope/pause").status_code == 404

    cancelled = client.post(f"/api/runs/{run_id}/cancel").json()  # cancel while paused
    assert cancelled["runtime_state"] == "cancel_requested"
    w.run_once()
    view = client.get(f"/api/runs/{run_id}").json()
    assert view["runtime_state"] == "cancelled" and view["progress"]["steps_done"] == 1
    assert [e["command"] for e in view["control_log"]] == [
        "start", "resume", "pause", "step", "parked", "speed", "cancel"
    ]
    for action in ("pause", "resume", "step"):
        assert client.post(f"/api/runs/{run_id}/{action}").status_code == 409


def test_runtime_state_reports_recovering_when_lease_expired(client, database_url, artifact_root):
    run_id = client.post("/api/runs", json={"speed": 0}).json()["run_id"]
    Worker(url=database_url, worker_id="dead", artifact_root=artifact_root).claim()
    assert client.get(f"/api/runs/{run_id}").json()["runtime_state"] == "running"
    with db.connection(database_url) as c, c.transaction():
        c.execute("UPDATE runs SET lease_expires_at = now() - interval '1 second'")
    view = client.get(f"/api/runs/{run_id}").json()
    assert view["runtime_state"] == "recovering" and view["lease_expired"] is True
    client.post(f"/api/runs/{run_id}/pause")
    assert client.get(f"/api/runs/{run_id}").json()["runtime_state"] == "recovering"


def test_eta_only_from_observed_throughput(client, database_url, artifact_root):
    run_id = client.post("/api/runs", json={"speed": 0}).json()["run_id"]
    w = Worker(url=database_url, worker_id="w", artifact_root=artifact_root)
    w.claim()
    assert client.get(f"/api/runs/{run_id}").json()["progress"]["eta_seconds"] is None
    with db.connection(database_url) as c, c.transaction():  # 30 bars observed in 10 s
        c.execute("INSERT INTO run_checkpoints (run_id, next_step, next_seq, state) VALUES (%s, 30, 0, '{}')", (run_id,))
        c.execute("UPDATE runs SET throughput_since = now() - interval '10 seconds', throughput_base_step = 0")
    progress = client.get(f"/api/runs/{run_id}").json()["progress"]
    assert progress["eta_seconds"] == pytest.approx(30, rel=0.05)  # 90 bars left at ~3 bars/s
    assert progress["eta_basis"].startswith("observed")


def test_health_reports_worker_liveness(client, database_url, artifact_root):
    assert client.get("/api/health").json()["workers"]["alive"] == 0
    Worker(url=database_url, worker_id="w-health", artifact_root=artifact_root).beat(None, force=True)
    workers = client.get("/api/health").json()["workers"]
    assert workers["alive"] == 1 and workers["recent"][0]["worker_id"] == "w-health"
    with db.connection(database_url) as c, c.transaction():
        c.execute("UPDATE workers SET heartbeat_at = now() - interval '1 minute'")
    workers = client.get("/api/health").json()["workers"]
    assert workers["alive"] == 0 and workers["recent"][0]["alive"] is False
