"""Durable recorder job + API (PostgreSQL-backed; offline fake OKX transports)."""

from __future__ import annotations

import threading
import time

import pytest
from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb
from recorder_fake import BUSINESS, ENDPOINTS, PUBLIC, FakeClock, FakeNetwork, captured_script

from algotrader import db
from algotrader.api import create_app
from algotrader.recorder import job
from algotrader.recorder.contracts import Connection, ParseStatus
from algotrader.recorder.journal import SessionWriter, is_finalized, iter_records, load_manifest, recordings_dir
from algotrader.recorder.okx_live import make_config

pytestmark = pytest.mark.db


def fake_worker(database_url, data_root):
    scripts = {PUBLIC: [captured_script("public")], BUSINESS: [captured_script("business")]}
    clock = FakeClock(min(i[1] for s in scripts.values() for i in s[0]) - 1_000_000)
    net = FakeNetwork(clock, scripts)
    worker = job.RecorderWorker(database_url, data_root, worker_id="recorder:test", lease_seconds=10,
                                recorder_kwargs={"clock": clock, "ws_connect": net.connect, "rest_get": net.rest_get,
                                                 "control_interval": 0.01})
    return worker, net


@pytest.fixture
def api(database_url, tmp_path):
    app = create_app(database_url, tmp_path / "artifacts", web_dist=tmp_path / "no-ui", data_root=tmp_path / "data")
    return TestClient(app)


def test_api_start_worker_record_stop_and_inspect(api, database_url, tmp_path):
    created = api.post("/api/recorder/sessions", json={"max_duration_minutes": 30,
                                                        "ws_public_url": PUBLIC, "ws_business_url": BUSINESS,
                                                        "rest_base_url": ENDPOINTS.rest_base_url})
    assert created.status_code == 201
    s = created.json()
    assert s["status"] == "queued" and s["labels"] == ["PUBLIC_MARKET_RECORDING", "NO_TRADING"]
    assert s["endpoints"]["ws_business_url"] == BUSINESS and s["max_duration_seconds"] == 1800
    assert set(s["channels"]) == {"candle1m:BTC-USDT-SWAP", "mark-price-candle1m:BTC-USDT-SWAP",
                                  "index-candle1m:BTC-USDT", "funding-rate:BTC-USDT-SWAP"}
    worker, net = fake_worker(database_url, tmp_path / "data")
    t = threading.Thread(target=worker.run_once)
    t.start()
    deadline = time.monotonic() + 30
    while not net.done and time.monotonic() < deadline:
        time.sleep(0.02)
    running = api.get(f"/api/recorder/sessions/{s['session_id']}").json()
    assert running["status"] == "running" and running["stats"]["records"] > 0  # live heartbeat stats
    assert api.post(f"/api/recorder/sessions/{s['session_id']}/stop").status_code == 200
    t.join(30)
    done = api.get(f"/api/recorder/sessions/{s['session_id']}").json()
    assert done["status"] == "clean" and done["manifest"]["status"] == "clean"
    assert done["report"]["bars"][0]["completed_bars"] == 2 and "stop requested" in done["manifest"]["stop_reason"]
    assert api.get(f"/api/recorder/sessions/{s['session_id']}/verify").json()["ok"] is True
    files = [f["name"] for f in done["manifest"]["files"]]
    for name in ("manifest.json", "report.json", "lifecycle.jsonl", files[0]):
        assert api.get(f"/api/recorder/sessions/{s['session_id']}/files/{name}").status_code == 200
    assert api.get(f"/api/recorder/sessions/{s['session_id']}/files/../../x").status_code == 404
    assert api.post(f"/api/recorder/sessions/{s['session_id']}/stop").status_code == 409
    health = api.get("/api/health").json()
    assert health["recorder_workers"]["recent"][0]["worker_id"] == "recorder:test"
    assert all(not w["worker_id"].startswith("recorder:") for w in health["workers"]["recent"])
    assert api.get("/api/recorder/sessions").json()["sessions"][0]["session_id"] == s["session_id"]


def test_api_rejects_private_endpoints_and_stop_of_queued_cancels(api):
    assert api.post("/api/recorder/sessions", json={"ws_public_url": "wss://ws.okx.com:8443/ws/v5/private"}
                    ).status_code == 422
    assert api.post("/api/recorder/sessions", json={"max_duration_minutes": 0}).status_code == 422
    sid = api.post("/api/recorder/sessions", json={}).json()["session_id"]
    assert api.post(f"/api/recorder/sessions/{sid}/stop").json()["status"] == "cancelled"
    assert api.get("/api/recorder/sessions/nope").status_code == 404


def test_worker_recovers_an_abandoned_session_as_partial(database_url, tmp_path):
    data_root = tmp_path / "data"
    config = make_config("rec-abandoned", endpoints=ENDPOINTS)
    clock = FakeClock(1790768690_000_000_000)
    w = SessionWriter(data_root, config, clock)  # a recorder process that will "die"
    w.lifecycle("session_start")
    for _, ts, raw in captured_script("business")[:6]:
        clock.advance_to(ts)
        w.record(kind="ws_message", connection=Connection.BUSINESS, generation=1, endpoint=BUSINESS,
                 recv_utc_ns=ts, recv_mono_ns=clock.monotonic_ns(), raw=raw, parse_status=ParseStatus.DATA,
                 channel="candle1m", inst_id="BTC-USDT-SWAP")
    w.sync()
    with db.connection(database_url) as c, c.transaction():
        c.execute(
            "INSERT INTO recorder_sessions (session_id, status, config, lease_owner, lease_expires_at, started_at) "
            "VALUES (%s, 'running', %s, 'recorder:dead', now() - interval '1 minute', now())",
            ("rec-abandoned", Jsonb(config.model_dump(mode="json"))))
    worker = job.RecorderWorker(database_url, data_root, worker_id="recorder:rescuer")
    assert worker.run_once()
    with db.connection(database_url) as c:
        row = c.execute("SELECT * FROM recorder_sessions WHERE session_id = 'rec-abandoned'").fetchone()
    assert row["status"] == "partial" and "not resumed" in row["error"]
    path = recordings_dir(data_root) / "rec-abandoned"
    assert is_finalized(path) and load_manifest(path).recovered_after_crash
    assert [r.seq for r in iter_records(path)] == list(range(1, 7))  # no duplicated receipts
    assert worker.run_once() is False  # nothing left to claim
