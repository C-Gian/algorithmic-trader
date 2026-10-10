"""Cockpit clarity — synthetic state screenshots (evidence generator; not a product or test change).

Real in-memory ``LiveSession`` states over EXISTING synthetic fixtures, without changing any rule:
* v0.6 MP-005 L1-L3 tape (``LIVE-COMPREHENSION-EPISODE/generate_episode.py``): waiting without a call (04:06:01.5),
  call AVAILABLE (04:07:01.5), same call UNVERIFIED / QUOTE_STALE (04:07:06);
* v0.2 WP-009 live fixture (``tests/test_adviser_live.py``): call CLOSED / PRICE_OUTSIDE_STRUCTURAL_AREA (05:23:01.5)
  and the call terminated TARGET_REACHED (08:27:01.5, now only in recent_calls);
* not current: the v0.6 AVAILABLE view served with a STOPPED session row through the real presentation boundary.

Every view goes through ``algotrader.adviser.api.live_status`` and the built cockpit on the E2E stack (disposable
database, route-mocked ``/api/adviser/live``), browser time zone Europe/Rome. Only a CSS label "Dimostrazione
sintetica" is added to the screenshots.

    ALGOTRADER_TEST_DATABASE_URL=postgresql://... uv run python delivery/evidence/LIVE-PROPOSAL-CLARITY/generate_states.py
"""

from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "generate_episode", OUT.parent / "LIVE-COMPREHENSION-EPISODE" / "generate_episode.py")
ep = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ep)  # also puts tests/ and tests/e2e on sys.path

import psycopg  # noqa: E402
from adviser_fixtures import DAY2  # noqa: E402
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from psycopg import sql  # noqa: E402
from test_adviser_live import COMPAT, Clock, feed_live, fetcher  # noqa: E402
from test_ui_smoke import Stack  # noqa: E402

from algotrader import db  # noqa: E402
from algotrader.adviser import api as adv_api  # noqa: E402
from algotrader.adviser import live as lv  # noqa: E402

LABEL_CSS = """.live-side::before { content: "Dimostrazione sintetica"; align-self: flex-start; padding: 4px 12px;
  border-radius: 999px; border: 1px solid currentColor; font-size: 13px; font-weight: 600; opacity: .85; }"""


def v02_states() -> tuple[dict, dict, list[dict]]:
    clock = Clock(DAY2 + timedelta(hours=4, seconds=30))
    sess = lv.LiveSession(compat=COMPAT, build="test", clock=clock)
    sess.start(None, fetcher())
    sess.on_connection("CONNECTED", clock.t)
    journal: list[dict] = []

    def until(t):
        feed_live(sess, clock, clock.t.replace(second=0, microsecond=0), t)
        journal.extend(sess.driver.take()[0])
        return {"clock_now": clock.t, "status": sess.status, "journal_upto": len(journal),
                "view": json.loads(json.dumps(sess.view(), default=str))}

    closed = until(DAY2 + timedelta(hours=5, minutes=23))
    terminal = until(DAY2 + timedelta(hours=8, minutes=27))
    c = closed["view"]["call"]
    assert closed["status"] == "LIVE" and c["entry_status"] == "CLOSED" and c["thesis_status"] == "ONGOING"
    assert c["entry_reasons"] == ["PRICE_OUTSIDE_STRUCTURAL_AREA"]
    tv = terminal["view"]
    assert tv["call"] is None and [(r["call_id"], r["terminal"]) for r in tv["recent_calls"]] == [
        (c["call_id"], "TARGET_REACHED")]
    return closed, terminal, journal


def stopped_json(moment: dict, journal: list[dict]) -> str:
    body = json.loads(ep.status_json(moment, journal))
    now = datetime.now(UTC)
    row = {"session_id": ep.SESSION_ID, "status": "stopped", "phase": "STOPPED", "created_at": now, "started_at": now,
           "stopped_at": now, "stop_requested": False, "error": None, "identity": None, "config": {"method": "v0.6"},
           "heartbeat_at": now, "lease_expires_at": None, "progress": {}, "connection": {}, "diagnostic_log": [],
           "view": moment["view"]}
    st = adv_api.live_status(ep._Conn(row, []))
    assert st["view"]["call"]["entry_status"] == "UNVERIFIED" and st["view"]["call"]["presentation"] == "NOT_CURRENT"
    st["alerts"] = body["alerts"]
    return json.dumps(st, default=str)


def main() -> None:
    views, journal6 = ep.episode()
    facts = ep.check(views, journal6)
    closed, terminal, journal2 = v02_states()
    shots = [  # (file, body, expected data-state, open details)
        ("1-in-attesa.png", ep.status_json(views[0], journal6), "WAITING", False),
        ("2-ingresso-disponibile.png", ep.status_json(views[1], journal6), "AVAILABLE", False),
        ("3-ingresso-non-piu-disponibile.png", ep.status_json(closed, journal2), "CLOSED", False),
        ("4-disponibilita-non-confermabile.png", ep.status_json(views[2], journal6), "UNVERIFIED", False),
        ("5-call-conclusa.png", ep.status_json(terminal, journal2), "WAITING", False),
        ("6-sessione-non-corrente.png", stopped_json(views[1], journal6), "UNVERIFIED", False),
        ("7-approfondimenti-chiusa.png", ep.status_json(closed, journal2), "CLOSED", True),
    ]
    admin = os.environ["ALGOTRADER_TEST_DATABASE_URL"]
    name = f"algotrader_demo_{uuid.uuid4().hex[:10]}"
    with psycopg.connect(admin, autocommit=True) as c:
        c.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    info = psycopg.conninfo.conninfo_to_dict(admin)
    info["dbname"] = name
    url = psycopg.conninfo.make_conninfo(**info)
    db.migrate(url)
    tmp = Path(tempfile.mkdtemp(prefix="demo-states-"))
    stack = Stack(url, tmp / "artifacts", tmp)
    cur = {"body": shots[0][1]}
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            for width, height, suffix, subset in ((1280, 1000, "", shots), (390, 844, "-telefono", shots[1:2])):
                page = b.new_context(viewport={"width": width, "height": height}, timezone_id="Europe/Rome").new_page()
                page.route("**/api/adviser/live", lambda r: r.fulfill(status=200, body=cur["body"],
                                                                      headers={"content-type": "application/json"}))
                page.goto(f"{stack.base}/#market")
                page.add_style_tag(content=LABEL_CSS)
                for fname, body, state, details in subset:
                    cur["body"] = body
                    panel = page.get_by_test_id("live-call")
                    expect(panel).to_have_attribute("data-state", state, timeout=15_000)
                    det = page.get_by_test_id("live-proposal-details")
                    if det.evaluate("e => e.open") != details:
                        det.locator("summary").click()
                    page.evaluate("() => window.scrollTo(0, 0)")  # sticky bars stay at the page top in the render
                    page.wait_for_timeout(500)
                    side = page.locator(".live-side")
                    box = side.bounding_box()
                    y = page.evaluate("() => window.scrollY")
                    page.screenshot(path=str(OUT / fname.replace(".png", f"{suffix}.png")), full_page=True,
                                    clip={"x": box["x"], "y": box["y"] + y, "width": box["width"], "height": box["height"]})
                page.context.close()
            b.close()
    finally:
        stack.stop()
        with psycopg.connect(admin, autocommit=True) as c:
            c.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name)))
    c2 = closed["view"]["call"]
    states = {
        "v0.6 episode": facts,
        "v0.2 CLOSED": {"run_id": closed["view"]["run_id"], "call_id": c2["call_id"], "clock": str(closed["clock_now"]),
                        "entry_status": c2["entry_status"], "entry_reasons": c2["entry_reasons"], "revision": c2["revision"]},
        "v0.2 terminal": {"clock": str(terminal["clock_now"]), "recent_calls": terminal["view"]["recent_calls"]},
        "not current": "v0.6 AVAILABLE view (moment 2) served with a STOPPED session row: API presents UNVERIFIED, NOT_CURRENT",
    }
    (OUT / "states.json").write_text(json.dumps(states, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps(states, indent=1, default=str))


if __name__ == "__main__":
    main()
