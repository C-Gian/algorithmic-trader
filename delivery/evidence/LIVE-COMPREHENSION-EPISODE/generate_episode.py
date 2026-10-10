"""Synthetic comprehension episode for the live cockpit (evidence generator; not a product or test change).

One real in-memory v0.6 live session (``LiveSession``, mocked services) over the existing MP-005 L1-L3 synthetic tape
(``tests/test_mp005_live.py``: ``tape("L", REF, neutral, eq, VALID)`` with the wide quote at 04:05). Three successive
views of the SAME session are captured:

1. 04:06:01.5 - expectation without a call (A LONG scenario confirmed, waiting for a local recovery);
2. 04:07:01.5 - the call issued on the valid recovery, entry AVAILABLE;
3. 04:07:06   - no newer quote for 5 s: the same call's entry becomes UNVERIFIED (QUOTE_STALE), thesis ongoing.

Each view goes through the real ``algotrader.adviser.api.live_status`` presentation boundary (alerts = the session's own
alertable material changes) and is served to the built cockpit on the LIVE CALL HISTORY E2E stack (disposable
database, route-mocked ``/api/adviser/live``). A CSS label "Dimostrazione sintetica" is injected into the screenshot
only. Synthetic engineering inputs: no market data, Owner data, live feed or order.

Usage (disposable PostgreSQL, built UI):
    ALGOTRADER_TEST_DATABASE_URL=postgresql://... uv run python delivery/evidence/LIVE-COMPREHENSION-EPISODE/generate_episode.py
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / "tests"), str(ROOT / "tests" / "e2e")]

import adviser6_fixtures as fx  # noqa: E402
import psycopg  # noqa: E402
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from psycopg import sql  # noqa: E402
from test_mp005_live import WIDE, feed6, session, tape  # noqa: E402
from test_ui_smoke import Stack  # noqa: E402

from algotrader import db  # noqa: E402
from algotrader.adviser import api as adv_api  # noqa: E402
from algotrader.adviser import live as lv  # noqa: E402

SESSION_ID = "demo-synthetic-session"
LABEL_CSS = """.live-cockpit::before { content: "Dimostrazione sintetica"; align-self: flex-start; padding: 4px 12px;
  border-radius: 999px; border: 1px solid currentColor; font-size: 13px; font-weight: 600; letter-spacing: .02em;
  opacity: .85; }"""


def episode() -> tuple[list[dict], list[dict]]:
    eq = fx.minute(99995, 100005, 99990, 100000)  # as test_live_temporary_cost_restriction_then_recovery_and_issue
    mins = tape("L", fx.REF, fx.neutral(1)[0], eq, fx.VALID)
    quotes = {fx.T(4, 5): WIDE}
    sess, clock = session(mins, fx.T(4, 6), quotes=quotes)
    journal: list[dict] = []
    views: list[dict] = []

    def capture():
        j, _, _ = sess.driver.take()
        journal.extend(j)
        views.append({"clock_now": clock.t, "status": sess.status, "view": json.loads(json.dumps(sess.view(), default=str)),
                      "journal_upto": len(journal)})

    capture()                                                   # 1. 04:06:01.5
    feed6(sess, clock, mins, fx.T(4, 6), fx.T(4, 7), quotes)  # the valid recovery minute
    capture()                                                   # 2. 04:07:01.5
    clock.t = fx.T(4, 7) + timedelta(seconds=6)                 # no newer input: quote-freshness timer only
    sess.tick(clock.t)
    capture()                                                   # 3. 04:07:06
    return views, journal


def check(views: list[dict], journal: list[dict]) -> dict:
    """The three moments are successive states of one session/run and one call, as the engine recorded them."""
    v1, v2, v3 = (m["view"] for m in views)
    assert {m["status"] for m in views} == {"LIVE"} and len({v["run_id"] for v in (v1, v2, v3)}) == 1
    assert v1["call"] is None and v1["market_view"]["expected_direction"] == "UP" and v1["market_view"]["conditional"]
    [a1] = [s for s in v1["scenarios"] if s["family"] == "A"]
    assert a1["status"] == "CONFIRMED" and a1["waiting"]["phase"] == "WAIT_RESPONSE"
    c2, c3 = v2["call"], v3["call"]
    assert c2["call_id"] == c3["call_id"] and c2["scenario_id"] == a1["scenario_id"]
    assert (c2["entry_status"], c2["revision"], c2["thesis_status"]) == ("AVAILABLE", 0, "ONGOING")
    assert (c3["entry_status"], c3["entry_reasons"], c3["revision"], c3["thesis_status"]) == (
        "UNVERIFIED", ["QUOTE_STALE"], 1, "ONGOING")
    cid = c2["call_id"]
    calls = [e for e in journal if e["kind"] == "call"]
    revs = [e["record"] for e in journal if e["kind"] == "call_revision" and e["record"]["call_id"] == cid]
    mcs = [e["record"] for e in journal if e["kind"] == "material_change" and e["record"]["subject_id"] == cid]
    assert [e["record"]["call_id"] for e in calls] == [cid] and len(revs) == 1
    assert [(m["change_type"], m["alertable"]) for m in mcs] == [("NEW_CALL", True), ("ENTRY_UNVERIFIED", True)]
    return {
        "method": "v0.6", "run_id": v1["run_id"], "session_id": SESSION_ID, "call_id": cid,
        "scenario_id": a1["scenario_id"], "tape": "tests/test_mp005_live.py L1-L3 LONG (REF, neutral, eq, VALID; WIDE quote 04:05)",
        "moments": [
            {"n": 1, "clock": str(views[0]["clock_now"]), "expected": v1["market_view"]["expected_direction"],
             "conditional": v1["market_view"]["conditional"], "table_row": v1["market_view"]["table_row"],
             "call": None, "scenario": {"family": "A", "direction": a1["direction"], "status": a1["status"],
                                        "phase": a1["waiting"]["phase"], "blockers": a1["waiting"]["blockers"]}},
            {"n": 2, "clock": str(views[1]["clock_now"]), "call_id": cid, "entry_status": "AVAILABLE", "revision": 0,
             "issued_at": c2["issued_at"], "admissible": c2["admissible_bounds"], "target": c2["target"],
             "stop": c2["stop"], "hard_deadline": c2["hard_deadline"], "material_change": "NEW_CALL"},
            {"n": 3, "clock": str(views[2]["clock_now"]), "call_id": cid, "entry_status": "UNVERIFIED",
             "entry_reasons": c3["entry_reasons"], "revision": 1, "revision_published": revs[0]["env"]["published_at"],
             "thesis": c3["thesis_status"], "guidance": revs[0]["guidance"], "material_change": "ENTRY_UNVERIFIED"}],
    }


class _Res:
    def __init__(self, rows):
        self.rows = rows

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows


class _Conn:
    """Serves one session row and its alerts to the real ``live_status`` (no database write)."""

    def __init__(self, row, alerts):
        self.row, self.alerts = row, alerts

    def execute(self, q, args=()):
        return _Res([self.row] if "adviser_live_sessions" in q else self.alerts if "adviser_alerts" in q else [])


def status_json(moment: dict, journal: list[dict]) -> str:
    now = datetime.now(UTC)
    v = moment["view"]
    row = {"session_id": SESSION_ID, "status": "running", "phase": v["status"], "created_at": now, "started_at": now,
           "stopped_at": None, "stop_requested": False, "error": None, "identity": None, "config": {"method": "v0.6"},
           "heartbeat_at": now, "lease_expires_at": now + timedelta(seconds=30), "progress": {}, "connection": {},
           "diagnostic_log": [], "view": v}
    alerts = [{**a, "acknowledged": False,
               "created_at": datetime.fromisoformat(next(e["clock_time"] for e in journal if e["seq"] == a["journal_seq"])
                                                    .replace("Z", "+00:00"))}
              for a in lv.alerts_from(journal[:moment["journal_upto"]], v["run_id"])]
    alerts.sort(key=lambda a: a["created_at"], reverse=True)
    return json.dumps(adv_api.live_status(_Conn(row, alerts)), default=str)


def screenshots(bodies: list[str], expectations: list[tuple[str, str]]) -> None:
    admin = os.environ["ALGOTRADER_TEST_DATABASE_URL"]
    name = f"algotrader_demo_{uuid.uuid4().hex[:10]}"
    with psycopg.connect(admin, autocommit=True) as c:
        c.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    info = psycopg.conninfo.conninfo_to_dict(admin)
    info["dbname"] = name
    url = psycopg.conninfo.make_conninfo(**info)
    db.migrate(url)
    tmp = Path(tempfile.mkdtemp(prefix="demo-episode-"))
    stack = Stack(url, tmp / "artifacts", tmp)
    current = {"body": bodies[0]}
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            page = b.new_context(viewport={"width": 1280, "height": 1000}).new_page()
            page.route("**/api/adviser/live", lambda r: r.fulfill(status=200, body=current["body"],
                                                                  headers={"content-type": "application/json"}))
            page.goto(f"{stack.base}/#market")
            page.add_style_tag(content=LABEL_CSS)
            names = ["1-aspettativa-senza-call.png", "2-call-disponibile.png", "3-aggiornamento-stessa-call.png"]
            for body, (testid, text), fname in zip(bodies, expectations, names):
                current["body"] = body
                expect(page.get_by_test_id(testid)).to_contain_text(text, timeout=15_000)
                page.wait_for_timeout(600)
                loc = page.get_by_test_id("live-cockpit")
                box = loc.bounding_box()
                y = page.evaluate("() => window.scrollY")
                page.screenshot(path=str(OUT / fname), full_page=True,
                                clip={"x": box["x"], "y": box["y"] + y, "width": box["width"], "height": box["height"]})
            b.close()
    finally:
        stack.stop()
        with psycopg.connect(admin, autocommit=True) as c:
            c.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name)))


def main() -> None:
    views, journal = episode()
    facts = check(views, journal)
    bodies = [status_json(m, journal) for m in views]
    (OUT / "episode.json").write_text(json.dumps(facts, indent=1, default=str) + "\n", encoding="utf-8")
    screenshots(bodies, [("live-no-trade", "No actionable trade now"), ("live-entry", "Entry valid now"),
                         ("live-entry", "Entry cannot be verified now")])
    print(json.dumps(facts, indent=1, default=str))


if __name__ == "__main__":
    main()
