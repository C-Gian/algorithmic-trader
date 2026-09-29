"""API: commands, snapshots, SSE and artifact inspection."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from algotrader.api import create_app
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
    assert snap["run"]["progress"]["sim_time"] == "2026-01-01T02:00:00+00:00"
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
