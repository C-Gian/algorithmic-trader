"""Live call history (cockpit): the existing read-only call-detail route serves ONE live call's committed journal —
only that continuity run and call, revisions in recorded (seq) order, no hypothetical evaluator path — and reading it
changes no adviser table. Synthetic journal rows plus one real live-worker journal (offline OKX fake); engineering
checks only, no market evidence or economic evaluation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from pack_fixtures import connect
from psycopg.types.json import Jsonb
from test_adviser_live_db import DAY2, FakeClock, _run_worker, _wait, ws_messages

from algotrader.adviser import live as lv
from algotrader.api import create_app

pytestmark = pytest.mark.db

TABLES = ("adviser_journal", "adviser_evaluation_records", "adviser_finish", "adviser_live_sessions",
          "adviser_live_state", "adviser_input_tape", "adviser_alerts")
T0 = datetime(2026, 10, 10, 9, 0, tzinfo=UTC)


def _snapshot(database_url) -> dict[str, tuple[int, str]]:
    with connect(database_url) as c:
        return {t: tuple(c.execute(f"SELECT count(*) AS n, md5(coalesce(string_agg(x::text, '|' ORDER BY x::text), "
                                   f"'')) AS h FROM {t} x").fetchone().values()) for t in TABLES}


def _api(database_url, tmp_path) -> TestClient:
    return TestClient(create_app(database_url, tmp_path / "art", web_dist=tmp_path / "no-ui", data_root=tmp_path / "d"))


def _insert(c, run_id: str, seq: int, kind: str, rid: str, subject: str | None, record: dict, minute: int) -> None:
    t = T0 + timedelta(minutes=minute)
    record = {**record, "env": {"record_id": rid, "published_at": t.isoformat(), "origin": "LIVE",
                                "factual_cursor": seq}}
    c.execute("""INSERT INTO adviser_journal (run_id, seq, kind, record_id, clock_time, professional_seq,
                     factual_cursor, origin, subject, digest, chain, record, generation)
                 VALUES (%s, %s, %s, %s, %s, %s, %s, 'LIVE', %s, 'd', 'c', %s, 1)""",
              (run_id, seq, kind, rid, t, seq, seq, subject, Jsonb(record)))


def _call(cid: str, target: str) -> dict:
    return {"call_id": cid, "attempt_id": f"att-{cid}", "family": "A", "direction": "LONG", "issued_at": T0.isoformat(),
            "issue_reference": "100", "invalidation": "90", "target": target, "target_type": "LEVEL",
            "structural_area": ["95", "99"], "hard_deadline": (T0 + timedelta(hours=3)).isoformat(),
            "entry_status": "AVAILABLE", "thesis_status": "ONGOING", "actionability": {"admissible_bounds": ["96", "99"]}}


def _rev(cid: str, n: int, entry: str, thesis: str = "ONGOING", terminal: str | None = None) -> dict:
    return {"call_id": cid, "revision": n, "entry_status": entry, "entry_reasons": [f"R{n}"], "thesis_status": thesis,
            "terminal_reason": terminal, "current_admissible_bounds": None, "remaining_minutes": str(100 - n),
            "duration_window_minutes": None, "guidance": f"g{n}", "changed": ["entry"]}


def test_history_reads_only_the_selected_run_and_call_in_recorded_order_without_writes(database_url, tmp_path):
    with connect(database_url) as c:
        # run A: two calls interleaved; run B reuses call id c1 with different values (never mixed in)
        _insert(c, "live-A", 1, "call", "c1", "att-c1", _call("c1", "120"), 0)
        _insert(c, "live-A", 2, "call_revision", "c1#r1", "c1", _rev("c1", 1, "CLOSED"), 1)
        _insert(c, "live-A", 3, "call", "c2", "att-c2", _call("c2", "130"), 2)
        _insert(c, "live-A", 4, "call_revision", "c2#r1", "c2", _rev("c2", 1, "CLOSED"), 3)
        _insert(c, "live-A", 5, "material_change", "c1#mc2-entry_reopened", "c1",
                {"change_id": "c1#entry_reopened#2", "subject_id": "c1", "change_type": "ENTRY_REOPENED",
                 "summary": "s", "alertable": True}, 4)
        _insert(c, "live-A", 6, "call_revision", "c1#r2", "c1", _rev("c1", 2, "AVAILABLE"), 4)
        _insert(c, "live-A", 7, "call_revision", "c1#r3", "c1", _rev("c1", 3, "CLOSED", "INVALIDATED", "STOP_CONTACT"), 5)
        _insert(c, "live-B", 1, "call", "c1", "att-c1", _call("c1", "999"), 0)
        _insert(c, "live-B", 2, "call_revision", "c1#r1", "c1", _rev("c1", 1, "UNVERIFIED"), 9)
        _insert(c, "live-A", 8, "call", "c3", "att-c3", _call("c3", "140"), 6)  # issued, no revision yet
        c.commit()
    before = _snapshot(database_url)
    api = _api(database_url, tmp_path)
    d = api.get("/api/adviser/runs/live-A/calls/c1").json()
    assert d["call"]["call_id"] == "c1" and d["call"]["target"] == "120"
    assert [(r["call_id"], r["revision"], r["entry_status"]) for r in d["revisions"]] == [
        ("c1", 1, "CLOSED"), ("c1", 2, "AVAILABLE"), ("c1", 3, "CLOSED")]
    assert d["revisions"][-1]["thesis_status"] == "INVALIDATED" and d["revisions"][-1]["terminal_reason"] == "STOP_CONTACT"
    assert [r["guidance"] for r in d["revisions"]] == ["g1", "g2", "g3"]  # stored values, unchanged
    assert d["hypothetical_paths"] == []  # live: no evaluator path exists or is required
    b = api.get("/api/adviser/runs/live-B/calls/c1").json()
    assert b["call"]["target"] == "999" and [r["entry_status"] for r in b["revisions"]] == ["UNVERIFIED"]
    two = api.get("/api/adviser/runs/live-A/calls/c2").json()
    assert [r["call_id"] for r in two["revisions"]] == ["c2"]
    issued_only = api.get("/api/adviser/runs/live-A/calls/c3").json()
    assert issued_only["call"]["call_id"] == "c3" and issued_only["revisions"] == []
    assert api.get("/api/adviser/runs/live-A/calls/nope").status_code == 404
    assert api.get("/api/adviser/runs/live-C/calls/c1").status_code == 404
    assert _snapshot(database_url) == before  # reading the history writes nothing


def test_history_of_a_real_live_call_across_a_restart_is_its_own_journal(database_url, tmp_path):
    """The live worker's own committed records: the call keeps one continuity run across two sessions and its history
    (including the restart-gap terminal written by the second session) is exactly its journal rows in seq order."""
    clock = FakeClock(DAY2 + timedelta(hours=4, seconds=30))
    with connect(database_url) as c:
        sid = lv.start_session(c)
    th, ws = _run_worker(database_url, clock, ws_messages(DAY2 + timedelta(hours=4), DAY2 + timedelta(hours=5, minutes=30)))
    _wait(database_url, "SELECT 1 FROM adviser_live_sessions WHERE session_id = %s AND view->>'status' = 'WARMING_UP'",
          (sid,))
    ws.gate.set()
    call = _wait(database_url, "SELECT * FROM adviser_journal WHERE kind = 'call'", ())
    with connect(database_url) as c:
        lv.stop_session(c, sid)
    th.join(60)
    clock.set(DAY2 + timedelta(hours=6))
    with connect(database_url) as c:
        sid2 = lv.start_session(c)
    th2, ws2 = _run_worker(database_url, clock, [])
    ws2.gate.set()
    _wait(database_url, "SELECT * FROM adviser_journal WHERE kind = 'call_revision' AND "
                        "record->>'terminal_reason' = 'RESTART_GAP_OVERLAPS_THESIS'", ())
    with connect(database_url) as c:
        lv.stop_session(c, sid2)
    th2.join(60)
    run_id, cid = call["run_id"], call["record_id"]
    with connect(database_url) as c:
        rows = c.execute("SELECT record FROM adviser_journal WHERE run_id = %s AND kind = 'call_revision' AND "
                         "subject = %s ORDER BY seq", (run_id, cid)).fetchall()
        view = c.execute("SELECT view FROM adviser_live_sessions WHERE session_id = %s", (sid,)).fetchone()["view"]
    assert view["run_id"] == run_id  # the cockpit's run identity is the journal's run identity
    before = _snapshot(database_url)
    d = _api(database_url, tmp_path).get(f"/api/adviser/runs/{run_id}/calls/{cid}").json()
    assert _snapshot(database_url) == before
    assert d["call"]["call_id"] == cid and d["call"]["env"]["origin"] == "LIVE"
    assert d["revisions"] == [r["record"] for r in rows] and len(rows) >= 1
    assert [r["revision"] for r in d["revisions"]] == list(range(1, len(rows) + 1))
    assert all(r["call_id"] == cid for r in d["revisions"])
    assert d["revisions"][-1]["terminal_reason"] == "RESTART_GAP_OVERLAPS_THESIS"
    assert d["revisions"][-1]["thesis_status"] != "ONGOING"
    assert d["hypothetical_paths"] == []
