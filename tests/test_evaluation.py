"""WP-008 observation-only evaluation facade and terminal reports (offline fixtures).

An evaluation launches the accepted durable observation replay on a prepared corpus
chunk; its report must be honest about incomplete coverage and must never present
trading metrics as numbers while no adviser exists.
"""

from __future__ import annotations

import json
import shutil

import psycopg
import psycopg.rows
import pytest
from fastapi.testclient import TestClient
from okx_fake import FakeOkx
from test_corpus import TEST_PLAN, corpus_worker, plan_file  # noqa: F401 - fixture reuse

from algotrader.api import create_app
from algotrader.corpus import job as cj
from algotrader.corpus.plan import load_plan
from algotrader.evaluation import report as rp
from algotrader.marketdata import dataset as md
from algotrader.observe.worker import ObservationWorker

pytestmark = pytest.mark.db


@pytest.fixture
def conn(database_url):
    with psycopg.connect(database_url, autocommit=True, row_factory=psycopg.rows.dict_row) as c:
        yield c


@pytest.fixture
def env(database_url, conn, tmp_path, plan_file):  # noqa: F811
    root, art = tmp_path / "data", tmp_path / "art"
    cj.create_job(conn, load_plan(), "test-chunk")
    corpus_worker(database_url, root, FakeOkx()).run_once()
    api = TestClient(create_app(database_url, art, web_dist=tmp_path / "no-ui", data_root=root))
    return api, root, art


def observer(database_url, root, art) -> ObservationWorker:
    return ObservationWorker(database_url, root, art, worker_id="observe:test", lease_seconds=5, poll_interval=0.01, isolate=False,
                             sleep=lambda s: None)


def drain(w: ObservationWorker) -> None:
    while w.run_once():
        pass


def assert_no_trading_numbers(doc: dict) -> None:
    caps = doc["capabilities"]
    assert caps["professional_adviser"]["status"] == "NOT_IMPLEMENTED"
    for key, _label in rp.UNAVAILABLE_METRICS:
        assert caps[key]["status"] == "UNAVAILABLE" and caps[key]["value"] is None
        assert caps[key]["reason"] == "no professional adviser connected yet"
    text = json.dumps(doc).lower()
    for word in ("pnl", "profit", "win_rate", "long", "short", "market_view_id"):
        assert f'"{word}"' not in text


def test_completed_evaluation_produces_deterministic_markdown_and_json(database_url, env):
    api, root, art = env
    res = api.post("/api/evaluations", json={"chunk_id": "test-chunk", "speed": 0})
    assert res.status_code == 201
    ev = res.json()
    eid = ev["evaluation_id"]
    assert ev["run_type"] == "observation_only" and "not connected yet" in ev["notice"]
    assert ev["replay"]["source"]["kind"] == "dataset" and ev["corpus"]["chunk_id"] == "test-chunk"
    # before any worker ran: a diagnostic snapshot (not a result) is already copyable
    snap = api.get(f"/api/evaluations/{eid}/report.json").json()
    assert snap["snapshot"] is True and snap["captured_at"] and snap["completion"] == "INCOMPLETE"
    assert snap["conclusion"]["verdict"] == "IN_PROGRESS_SNAPSHOT" and snap["feed"]["content_identity"] == "PENDING"
    assert_no_trading_numbers(snap)
    assert "DIAGNOSTIC SNAPSHOT" in api.get(f"/api/evaluations/{eid}/report.md").text

    drain(observer(database_url, root, art))
    detail = api.get(f"/api/evaluations/{eid}").json()
    assert detail["replay"]["status"] == "completed" and detail["report_available"]

    doc = api.get(f"/api/evaluations/{eid}/report.json").json()
    assert doc["report_kind"] == "OBSERVATION_ONLY_EVALUATION" and doc["completion"] == "COMPLETE"
    assert doc["status"] == "completed" and doc["validation"] == {**doc["validation"], "ran": True, "passed": True}
    assert doc["conclusion"]["verdict"] == "WORKFLOW_VALID" and doc["stopped_at"] is None
    assert doc["corpus"]["dataset_id"] == doc["source"]["dataset_id"]
    assert doc["corpus"]["storage"]["total_bytes"] > 0 and doc["corpus"]["acquisition"]["outcome"] == "acquired"
    assert doc["coverage"]["requested"] == {"start": "2026-09-30T07:50:00+00:00", "end": "2026-09-30T08:10:00+00:00"}
    assert doc["coverage"]["applied_events"] == doc["coverage"]["total_events"] == doc["feed"]["event_count"]
    assert doc["availability"]["basis"] == "MODELED" and doc["availability"]["measured"] is False
    assert doc["quality_status"] == "degraded" and any("DEGRADED" in w for w in doc["warnings"])
    assert doc["next_diagnostic"].startswith("Adviser evaluation pending")
    assert_no_trading_numbers(doc)

    md_text = api.get(f"/api/evaluations/{eid}/report.md").text
    assert "OBSERVATION_ONLY_EVALUATION" in md_text and rp.NOT_CONNECTED in md_text
    assert "| Call count | UNAVAILABLE |" in md_text and "| Professional adviser | NOT_IMPLEMENTED |" in md_text
    assert "WORKFLOW_VALID" in md_text and "validation **PASS**" in md_text
    total = doc["coverage"]["total_events"]
    assert f"PASS `completed_consumed_entire_feed`: cursor {total}/{total}" in md_text  # Owner coverage comparison
    assert "PASS `cache_receipt_and_pin`" in md_text and "trusted receipt" in md_text
    # deterministic: the same terminal state yields the same bytes
    assert api.get(f"/api/evaluations/{eid}/report.md").text == md_text
    assert api.get(f"/api/evaluations/{eid}/report.json").text == api.get(f"/api/evaluations/{eid}/report.json").text
    dl = api.get(f"/api/evaluations/{eid}/report.md?download=true")
    assert dl.headers["content-disposition"] == f'attachment; filename="{eid}-report.md"'
    assert api.get("/api/evaluations").json()[0]["evaluation_id"] == eid


def test_cancelled_evaluation_reports_incomplete_coverage(database_url, env):
    api, root, art = env
    eid = api.post("/api/evaluations", json={"chunk_id": "test-chunk", "speed": 0, "paused": True}).json()[
        "evaluation_id"]
    rid = api.get(f"/api/evaluations/{eid}").json()["replay"]["replay_id"]
    w = observer(database_url, root, art)
    drain(w)  # prepares and parks at cursor 0
    assert api.post(f"/api/observations/{rid}/step").status_code == 200
    drain(w)
    api.post(f"/api/observations/{rid}/cancel")
    drain(w)
    doc = api.get(f"/api/evaluations/{eid}/report.json").json()
    assert doc["status"] == "cancelled" and doc["completion"] == "INCOMPLETE"
    assert doc["conclusion"]["verdict"] == "INCOMPLETE_CANCELLED"
    assert doc["stopped_at"]["applied_events"] == 1 < doc["stopped_at"]["total_events"]
    assert doc["validation"]["ran"] is True
    assert_no_trading_numbers(doc)
    text = api.get(f"/api/evaluations/{eid}/report.md").text
    assert "INCOMPLETE" in text and "not a successful evaluation" in text and "Stopped at: 1/" in text


def test_failed_evaluation_reports_the_operational_failure(database_url, env):
    api, root, art = env
    ev = api.post("/api/evaluations", json={"chunk_id": "test-chunk", "speed": 0}).json()
    shutil.rmtree(md.dataset_path(root, ev["corpus"]["dataset_id"]))  # evidence vanishes before the worker runs
    drain(observer(database_url, root, art))
    doc = api.get(f"/api/evaluations/{ev['evaluation_id']}/report.json").json()
    assert doc["status"] == "failed" and doc["completion"] == "INCOMPLETE"
    assert doc["conclusion"]["verdict"] == "OPERATIONAL_FAILURE"
    # never prepared: no manifest; validation did not run and is not reported as PASS or FAIL
    assert doc["validation"]["ran"] is False and doc["validation"]["passed"] is None
    assert doc["operation"]["assurance"]["state"] == "not_checked" and doc["snapshot"] is True
    assert "not replayable" in doc["stopped_at"]["reason"]
    assert_no_trading_numbers(doc)


def test_evaluation_requires_a_prepared_chunk(database_url, conn, tmp_path, plan_file):  # noqa: F811
    api = TestClient(create_app(database_url, tmp_path / "art", web_dist=tmp_path / "no-ui", data_root=tmp_path))
    assert api.post("/api/evaluations", json={"chunk_id": "test-chunk"}).status_code == 409
    assert api.post("/api/evaluations", json={"chunk_id": "nope"}).status_code == 404
    assert api.get("/api/evaluations/nope").status_code == 404
    assert TEST_PLAN["chunks"][0]["chunk_id"] == "test-chunk"
