"""SECOND desktop visual PROPOSAL of the live cockpit (chart left with candles, decision panel right) (evidence generator; renders whatever UI build is in web/dist).

The proposal screenshots were taken with the TEMPORARY local draft saved next to this file (``draft-ui.patch``) applied
and built; the product code was then restored. The states and assertions are those of the first proposal
(../COCKPIT-VISUAL-PROPOSAL/generate_proposal.py); only the label and output folder differ. Each state is a real engine state of an in-memory v0.6 live session
(mocked services) over the existing MP-005 synthetic tapes, served through the real ``live_status`` boundary:

  1. waiting without a call          LONG tape, 04:06:01.5 (A LONG confirmed, waiting for a local recovery)
  2. LONG available                  same LONG session, 04:07:01.5 (call issued, entry AVAILABLE)
  3. SHORT available                 mirrored tape (x -> 200000 - x, tests/test_mp005_live.py short=True), 04:07:01.5
  4. UNVERIFIED                      same LONG session as 1-2, 04:07:06 (no newer quote: QUOTE_STALE)
  5. CLOSED, thesis ONGOING          the LIVE-CALL-UPDATES episode (re-quoted every 4 s), 04:08:01.5
  6. call concluded, new expectation the same episode, 04:10:01.5 (TARGET_REACHED; MarketView still UP)

States come from three independent sessions and are shown as separate states, not as one sequence. The sessions'
journals are inserted as produced into the disposable database of the E2E stack so the concluded call's read-only
history (target, closing text) is served by the real call-detail route. A CSS label marks every image as a proposal.

Usage (disposable PostgreSQL, UI built WITH the draft applied):
    ALGOTRADER_TEST_DATABASE_URL=postgresql://... uv run python delivery/evidence/COCKPIT-VISUAL-PROPOSAL-2/generate_proposal.py
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import uuid
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "episode_gen", ROOT / "delivery" / "evidence" / "LIVE-CALL-UPDATES-EPISODE" / "generate_episode.py")
ep = importlib.util.module_from_spec(_spec)
sys.modules["episode_gen"] = ep
_spec.loader.exec_module(ep)  # also puts tests/ and tests/e2e on sys.path

import adviser6_fixtures as fx  # noqa: E402
import psycopg  # noqa: E402
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from psycopg import sql  # noqa: E402
from test_mp005_live import feed6, session, tape  # noqa: E402
from test_ui_smoke import Stack  # noqa: E402

from algotrader import db  # noqa: E402

VIEWPORT = {"width": 1440, "height": 1000}
LABEL_CSS = """.live-cockpit::before { content: "PROPOSTA VISIVA 2 — Dimostrazione sintetica (non implementata)";
  align-self: flex-start; padding: 4px 12px; border-radius: 999px; border: 1px solid currentColor; font-size: 13px;
  font-weight: 700; letter-spacing: .02em; opacity: .9; }"""


def take(sess, clock, journal: list[dict]) -> dict:
    j, _, _ = sess.driver.take()
    journal.extend(j)
    return {"clock_now": clock.t, "status": sess.status, "view": json.loads(json.dumps(sess.view(), default=str)),
            "journal_upto": len(journal)}


def long_session() -> tuple[list[dict], list[dict]]:
    mins = tape("L", fx.REF, fx.neutral(1)[0], ep.EQ, fx.VALID)
    sess, clock = session(mins, fx.T(4, 6), quotes=ep.QUOTES)
    journal: list[dict] = []
    out = [take(sess, clock, journal)]                                   # 1. waiting, 04:06:01.5
    feed6(sess, clock, mins, fx.T(4, 6), fx.T(4, 7), ep.QUOTES)
    out.append(take(sess, clock, journal))                               # 2. LONG available, 04:07:01.5
    clock.t = fx.T(4, 7) + timedelta(seconds=6)
    sess.tick(clock.t)
    out.append(take(sess, clock, journal))                               # 4. UNVERIFIED, 04:07:06
    return out, journal


def short_session() -> tuple[list[dict], list[dict]]:
    mins = tape("S", fx.REF, fx.neutral(1)[0], ep.EQ, fx.VALID)
    sess, clock = session(mins, fx.T(4, 7), quotes=ep.QUOTES, short=True)
    journal: list[dict] = []
    return [take(sess, clock, journal)], journal                         # 3. SHORT available, 04:07:01.5


def states() -> list[dict]:
    lv, lj = long_session()
    sv, sj = short_session()
    ev, ej = ep.episode()
    rows = [("1-attesa-senza-call", lv[0], lj, "WAITING"), ("2-long-disponibile", lv[1], lj, "AVAILABLE"),
            ("3-short-disponibile", sv[0], sj, "AVAILABLE"), ("4-non-verificabile", lv[2], lj, "UNVERIFIED"),
            ("5-ingresso-chiuso-tesi-aperta", ev[1], ej, "CLOSED"), ("6-call-conclusa-nuova-aspettativa", ev[2], ej, "WAITING")]
    out = []
    for name, m, j, state in rows:
        v = m["view"]
        c = v["call"]
        out.append({"name": name, "moment": m, "journal": j, "state": state, "run_id": v["run_id"],
                    "clock": str(m["clock_now"]),
                    "call": None if not c else {k: c[k] for k in ("call_id", "direction", "family", "revision",
                                                                 "entry_status", "entry_reasons", "thesis_status")},
                    "recent": [{k: r[k] for k in ("call_id", "terminal", "terminal_at")} for r in v.get("recent_calls", [])],
                    "expected": (v.get("market_view") or {}).get("expected_direction")})
    # the states are the engine's own
    assert out[0]["call"] is None and out[1]["call"]["entry_status"] == "AVAILABLE" and out[1]["call"]["direction"] == "LONG"
    assert out[2]["call"]["entry_status"] == "AVAILABLE" and out[2]["call"]["direction"] == "SHORT"
    assert (out[3]["call"]["entry_status"], out[3]["call"]["entry_reasons"]) == ("UNVERIFIED", ["QUOTE_STALE"])
    assert (out[4]["call"]["entry_status"], out[4]["call"]["thesis_status"]) == ("CLOSED", "ONGOING")
    assert out[5]["call"] is None and out[5]["recent"][-1]["terminal"] == "TARGET_REACHED" and out[5]["expected"] == "UP"
    return out


def main() -> None:
    rows = states()
    admin = os.environ["ALGOTRADER_TEST_DATABASE_URL"]
    name = f"algotrader_proposal2_{uuid.uuid4().hex[:10]}"
    with psycopg.connect(admin, autocommit=True) as c:
        c.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    info = psycopg.conninfo.conninfo_to_dict(admin)
    info["dbname"] = name
    url = psycopg.conninfo.make_conninfo(**info)
    db.migrate(url)
    seen = set()
    for r in rows:
        if r["run_id"] not in seen:
            ep.persist_journal(url, r["run_id"], r["journal"])
            seen.add(r["run_id"])
    tmp = Path(tempfile.mkdtemp(prefix="cockpit-proposal2-"))
    stack = Stack(url, tmp / "artifacts", tmp)
    current = {"body": ep.status_json(rows[0]["moment"], rows[0]["journal"])}  # a real state from the first load
    shots = []
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            for width, suffix, subset in ((VIEWPORT["width"], "", None), (1024, "-1024", {"5-ingresso-chiuso-tesi-aperta"}),
                                          (390, "-390", {"5-ingresso-chiuso-tesi-aperta"})):
                page = b.new_context(viewport={"width": width, "height": VIEWPORT["height"]},
                                     timezone_id="Europe/Rome").new_page()
                page.on("pageerror", lambda e: print("PAGE ERROR:", e))
                page.route("**/api/adviser/live", lambda r: r.fulfill(status=200, body=current["body"],
                                                                      headers={"content-type": "application/json"}))
                page.goto(f"{stack.base}/#market")
                page.add_style_tag(content=LABEL_CSS)
                for r in rows:
                    if subset is not None and r["name"] not in subset:
                        continue
                    current["body"] = ep.status_json(r["moment"], r["journal"])
                    expect(page.get_by_test_id("live-call")).to_have_attribute("data-state", r["state"], timeout=15_000)
                    if r["name"].startswith("6-"):
                        expect(page.get_by_test_id("live-concluded-guidance")).not_to_have_text("…", timeout=15_000)
                    page.wait_for_timeout(700)
                    page.evaluate("() => window.scrollTo(0, 0)")
                    loc = page.get_by_test_id("live-cockpit")
                    box = loc.bounding_box()
                    fname = f"{r['name']}{suffix}.png"
                    page.screenshot(path=str(OUT / fname), full_page=True,
                                    clip={"x": box["x"], "y": box["y"], "width": box["width"], "height": box["height"]})
                    shots.append(fname)
                page.context.close()
            b.close()
    finally:
        stack.stop()
        with psycopg.connect(admin, autocommit=True) as c:
            c.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name)))
    facts = {"viewport": VIEWPORT, "extra_widths": [1024, 390], "screenshots": shots,
             "states": [{k: r[k] for k in ("name", "state", "run_id", "clock", "call", "recent", "expected")} for r in rows]}
    (OUT / "proposal-states.json").write_text(json.dumps(facts, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"screenshots": shots}, indent=1))


if __name__ == "__main__":
    main()
