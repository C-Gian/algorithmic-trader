"""Synthetic comprehension episode: updates of ONE call in the live cockpit (evidence generator; no product change).

One real in-memory v0.6 live session (``LiveSession``, mocked services) over the existing MP-005 L1-L3 LONG tape of
``tests/test_mp005_live.py`` (``tape("L", REF, neutral, eq, VALID, ...)``, wide quote at 04:05). Minimal fixture adaptation:
  * three later minutes appended to the tape (price leaves the structural area upward, then touches the call's target);
  * between minute closes the same price is re-quoted every 4 s, so the 5 s quote-freshness rule does not interleave
    QUOTE_STALE revisions (the existing feed sends one quote per minute). No rule, parameter or engine code changes.

Three successive views of the SAME session, run and call, as the engine produced them:
  1. 04:07:01.5 - the call issued on the valid recovery, entry AVAILABLE, thesis ONGOING;
  2. 04:08:01.5 - entry CLOSED (price outside the structural area), thesis ONGOING;
  3. 04:10:01.5 - thesis TARGET_REACHED (certified target contact); the call's recorded history opened through the
     cockpit's existing "history" button in "What changed".

Each view passes through the real ``algotrader.adviser.api.live_status`` boundary (alerts = the session's own alertable
material changes). The session's committed journal is inserted, as produced, into the disposable database of the E2E
stack (the live store's own INSERT), so the history card is served by the real ``GET /api/adviser/runs/{run}/calls/{id}``.
The only addition to the page is the CSS label "Dimostrazione sintetica". Synthetic engineering inputs only.

Usage (disposable PostgreSQL, built UI):
    ALGOTRADER_TEST_DATABASE_URL=postgresql://... uv run python delivery/evidence/LIVE-CALL-UPDATES-EPISODE/generate_episode.py
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / "tests"), str(ROOT / "tests" / "e2e")]

import adviser6_fixtures as fx  # noqa: E402
import psycopg  # noqa: E402
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from psycopg import sql  # noqa: E402
from psycopg.types.json import Jsonb  # noqa: E402
from test_mp005_live import WIDE, feed6, session, tape  # noqa: E402
from test_ui_smoke import Stack  # noqa: E402

from algotrader import db  # noqa: E402
from algotrader.adviser import api as adv_api  # noqa: E402
from algotrader.adviser import live as lv  # noqa: E402
from algotrader.adviser.core import Quote  # noqa: E402

SESSION_ID = "demo-synthetic-session"
LABEL_CSS = """.live-cockpit::before { content: "Dimostrazione sintetica"; align-self: flex-start; padding: 4px 12px;
  border-radius: 999px; border: 1px solid currentColor; font-size: 13px; font-weight: 600; letter-spacing: .02em;
  opacity: .85; }"""
EQ = fx.minute(99995, 100005, 99990, 100000)
POST = [fx.minute(100010, 100120, 100005, 100100),  # [04:07,04:08) closes above the structural area top 100049.9
        fx.minute(100100, 100320, 100090, 100300),  # [04:08,04:09)
        fx.minute(100300, 100720, 100290, 100710)]  # [04:09,04:10) high beyond the target 100700.0
QUOTES = {fx.T(4, 5): WIDE}


def keep_fresh(sess, clock, until: datetime, price: Decimal) -> None:
    """Re-quote the last close every 4 s until ``until`` (synthetic feed density only; same price)."""
    t = clock.t + timedelta(seconds=4)
    while t < until:
        clock.t = t
        sess.on_quote(Quote(price, price, t, t, "BTC-USDT-SWAP", "q" * 64), t)
        sess.tick(t)
        t += timedelta(seconds=4)


def episode() -> tuple[list[dict], list[dict]]:
    mins = tape("L", fx.REF, fx.neutral(1)[0], EQ, fx.VALID, *POST)
    sess, clock = session(mins, fx.T(4, 7), quotes=QUOTES)  # through [04:06,04:07): issue at 04:07:01
    journal: list[dict] = []
    views: list[dict] = []

    def capture():
        j, _, _ = sess.driver.take()
        journal.extend(j)
        views.append({"clock_now": clock.t, "status": sess.status,
                      "view": json.loads(json.dumps(sess.view(), default=str)), "journal_upto": len(journal)})

    def minute(k: int) -> None:  # the minute [04:0k, 04:0k+1), preceded by fresh re-quotes of the previous close
        prev = mins[int((fx.T(4, k) - (fx.DAY2 - timedelta(days=1))) / timedelta(minutes=1)) - 1].c
        keep_fresh(sess, clock, fx.T(4, k + 1), prev)
        feed6(sess, clock, mins, fx.T(4, k), fx.T(4, k + 1), QUOTES)

    capture()     # 1. 04:07:01.5
    minute(7)
    capture()     # 2. 04:08:01.5
    minute(8)
    minute(9)
    capture()     # 3. 04:10:01.5
    return views, journal


def check(views: list[dict], journal: list[dict]) -> dict:
    v1, v2, v3 = (m["view"] for m in views)
    assert {m["status"] for m in views} == {"LIVE"} and len({v["run_id"] for v in (v1, v2, v3)}) == 1
    c1, c2 = v1["call"], v2["call"]
    cid = c1["call_id"]
    assert c2["call_id"] == cid and v3["call"] is None
    assert (c1["revision"], c1["entry_status"], c1["thesis_status"]) == (0, "AVAILABLE", "ONGOING")
    assert c2["entry_status"] == "CLOSED" and c2["thesis_status"] == "ONGOING"  # closed, not merely UNVERIFIED
    assert "QUOTE_STALE" not in c2["entry_reasons"]
    [r3] = [r for r in v3["recent_calls"] if r["call_id"] == cid]
    assert r3["terminal"] == "TARGET_REACHED"
    calls = [e for e in journal if e["kind"] == "call"]
    revs = [e["record"] for e in journal if e["kind"] == "call_revision" and e["record"]["call_id"] == cid]
    mcs = [e["record"] for e in journal if e["kind"] == "material_change" and e["record"]["subject_id"] == cid]
    assert [e["record"]["call_id"] for e in calls] == [cid]
    assert not any("QUOTE_STALE" in r["entry_reasons"] for r in revs)  # no interleaved stale-quote revision
    issue = calls[0]["record"]
    return {
        "method": "v0.6 (btc.context-action.v0.6 / adviser.core.v6), live profile, mocked services",
        "run_id": v1["run_id"], "session_id_displayed": SESSION_ID, "scenario_id": issue["scenario_id"],
        "call_id": cid, "issued_at": issue["issued_at"], "entry_mode": issue.get("entry_mode"),
        "structural_area": issue["structural_area"], "target": issue["target"], "stop": issue["invalidation"],
        "hard_deadline": issue["hard_deadline"],
        "tape": ("tests/test_mp005_live.py L1-L3 LONG (REF, neutral, eq, VALID; WIDE quote 04:05) + 3 appended minutes "
                 "(c 100100, 100300, high 100720); re-quotes every 4 s at the last close"),
        "revisions": [{"revision": r["revision"], "published_at": r["env"]["published_at"],
                       "entry_status": r["entry_status"], "entry_reasons": r["entry_reasons"],
                       "thesis_status": r["thesis_status"], "terminal_reason": r["terminal_reason"],
                       "admissible": r["current_admissible_bounds"], "guidance": r["guidance"]} for r in revs],
        "material_changes": [{"type": m["change_type"], "published_at": m["env"]["published_at"],
                              "alertable": m["alertable"], "summary": m["summary"]} for m in mcs],
        "moments": [{"n": i + 1, "clock": str(m["clock_now"]),
                     "call": ({k: m["view"]["call"][k] for k in ("revision", "entry_status", "entry_reasons",
                                                                 "thesis_status", "admissible_bounds", "guidance")}
                              if m["view"]["call"] else None),
                     "recent_call": next(({k: r[k] for k in ("terminal", "reason", "terminal_at")}
                                          for r in m["view"].get("recent_calls", []) if r["call_id"] == cid), None)}
                    for i, m in enumerate(views)],
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


def persist_journal(url: str, run_id: str, journal: list[dict]) -> None:
    """The session's committed journal, as produced, through the live store's own INSERT."""
    with psycopg.connect(url, autocommit=True) as c, c.cursor() as cur:
        cur.executemany(
            """INSERT INTO adviser_journal (run_id, seq, kind, record_id, clock_time, professional_seq,
                   factual_cursor, origin, subject, digest, chain, record, generation)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            [(run_id, e["seq"], e["kind"], e["record_id"], e["clock_time"], e["professional_seq"], e["factual_cursor"],
              e["origin"], e["subject"], e["digest"], e["chain"], Jsonb(e["record"]), 1) for e in journal])


def screenshots(bodies: list[str], run_id: str, journal: list[dict], cid: str) -> dict:
    admin = os.environ["ALGOTRADER_TEST_DATABASE_URL"]
    name = f"algotrader_demo_{uuid.uuid4().hex[:10]}"
    with psycopg.connect(admin, autocommit=True) as c:
        c.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    info = psycopg.conninfo.conninfo_to_dict(admin)
    info["dbname"] = name
    url = psycopg.conninfo.make_conninfo(**info)
    db.migrate(url)
    persist_journal(url, run_id, journal)
    tmp = Path(tempfile.mkdtemp(prefix="demo-episode-"))
    stack = Stack(url, tmp / "artifacts", tmp)
    current = {"body": bodies[0]}
    seen: dict = {}
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            page = b.new_context(viewport={"width": 1280, "height": 1000}).new_page()
            page.route("**/api/adviser/live", lambda r: r.fulfill(status=200, body=current["body"],
                                                                  headers={"content-type": "application/json"}))
            page.goto(f"{stack.base}/#market")
            page.add_style_tag(content=LABEL_CSS)
            panel = page.get_by_test_id("live-call")

            def shot(fname: str) -> None:
                page.wait_for_timeout(600)
                page.evaluate("() => window.scrollTo(0, 0)")  # the sticky shell bar must not cover the content
                page.wait_for_timeout(200)
                loc = page.get_by_test_id("live-cockpit")
                box = loc.bounding_box()
                y = page.evaluate("() => window.scrollY")
                page.screenshot(path=str(OUT / fname), full_page=True,
                                clip={"x": box["x"], "y": box["y"] + y, "width": box["width"], "height": box["height"]})

            def texts(n: int) -> None:
                det = page.get_by_test_id("live-proposal-details")
                seen[n] = {"panel_state": panel.get_attribute("data-state"),
                           "panel_visible": panel.inner_text(),
                           "details_only": det.locator(".more-body").text_content() if det.count() else None,
                           "alerts_banner": (page.get_by_test_id("live-alerts").inner_text()
                                             if page.get_by_test_id("live-alerts").count() else None)}

            for n, (body, state, fname) in enumerate(zip(bodies[:2], ("AVAILABLE", "CLOSED"),
                                                         ("1-ingresso-disponibile.png", "2-ingresso-chiuso-tesi-aperta.png")),
                                                     start=1):
                current["body"] = body
                expect(panel).to_have_attribute("data-state", state, timeout=15_000)
                texts(n)
                shot(fname)
            current["body"] = bodies[2]
            expect(page.get_by_test_id("live-last-terminal")).to_be_visible(timeout=15_000)
            texts(3)
            page.get_by_test_id("timeline-call-history-open").first.click()  # the cockpit's existing path
            card = page.get_by_test_id("live-call-history")
            expect(card.get_by_test_id("history-revisions")).to_be_visible(timeout=15_000)
            seen[3]["history_card"] = card.inner_text()
            shot("3-conclusione-storico-della-call.png")
            b.close()
    finally:
        stack.stop()
        with psycopg.connect(admin, autocommit=True) as c:
            c.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name)))
    return seen


def main() -> None:
    views, journal = episode()
    facts = check(views, journal)
    bodies = [status_json(m, journal) for m in views]
    facts["rendered"] = screenshots(bodies, facts["run_id"], journal, facts["call_id"])
    (OUT / "episode.json").write_text(json.dumps(facts, indent=1, default=str, ensure_ascii=False) + "\n",
                                      encoding="utf-8")
    print(json.dumps({k: facts[k] for k in ("run_id", "call_id")}, indent=1))


if __name__ == "__main__":
    main()
