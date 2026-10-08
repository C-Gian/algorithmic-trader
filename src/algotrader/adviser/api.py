"""Adviser HTTP surface: live session control/status/alerts/journal/analysis (``/api/adviser/live``) and historical
adviser inspection (``/api/adviser/runs/{replay_id}``: journal pages with a cutoff, call detail with revisions and
separately labelled hypothetical paths, a bounded price window around a cursor).

The API records commands and reads committed state only; the live worker and the observation worker own execution.
Live and historical results are never presented as simultaneous current recommendations.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse

from . import live as lv

MAX_PAGE = 2000
NOTICE = ("Advice for a human decision only: no orders, size, leverage or account. Quotes are indicative; stops are "
          "guidance, not orders or guaranteed fills.")


HEARTBEAT_CURRENT_SECONDS = 10.0  # the worker heartbeats every ~2 s; older evidence is not a current session


def present(view: dict, state: str, current: bool) -> dict:
    """Presentation boundary for the live view (API, UI and Copy analysis all use it): a session that is not current
    (stopped, failed, unresponsive, disconnected, catching up or warming up) never shows a usable entry. The saved
    call/revision history is not rewritten: the stored entry status stays available as ``entry_status_saved``."""
    if not view:
        return view
    out = {**view, "current": current, "stale_session": not current}
    call = view.get("call")
    if call and not current:
        saved = call.get("entry_status")
        out["call"] = {**call, "entry_status_saved": saved,
                       "entry_status": "UNVERIFIED" if saved == "AVAILABLE" else saved,
                       "entry_reasons": sorted(set(call.get("entry_reasons") or []) | {f"SESSION_NOT_CURRENT:{state}"}),
                       "admissible_bounds": None, "presentation": "NOT_CURRENT"}
    return out


def _row(c, sql: str, args: tuple) -> dict | None:
    return c.execute(sql, args).fetchone()


def live_status(c) -> dict[str, Any]:
    s = _row(c, "SELECT * FROM adviser_live_sessions ORDER BY created_at DESC LIMIT 1", ())
    now = datetime.now(UTC)
    if s is None:
        return {"session": None, "state": "STOPPED", "running": False,
                "message": "Live adviser is stopped: nothing is monitored and no alerts are produced.", "view": None,
                "alerts": [], "notice": NOTICE}
    lease_ok = s["status"] == "running" and s["lease_expires_at"] is not None and s["lease_expires_at"] > now
    running = s["status"] in ("queued", "running")
    view = s["view"] or {}
    state = ("STOPPED" if s["status"] == "stopped" else "FAILED" if s["status"] == "failed" else
             "STARTING" if s["status"] == "queued" else (view.get("status") or s["phase"] or "STARTING")
             if lease_ok else "UNRESPONSIVE")
    hb_age = (now - s["heartbeat_at"]).total_seconds() if s["heartbeat_at"] else None
    current = (state == "LIVE" and lease_ok and hb_age is not None and hb_age <= HEARTBEAT_CURRENT_SECONDS
               and bool(view.get("connected")))
    alerts = c.execute("SELECT * FROM adviser_alerts ORDER BY created_at DESC LIMIT 20").fetchall()
    return {
        "session": {"session_id": s["session_id"], "status": s["status"], "phase": s["phase"],
                    "created_at": s["created_at"].isoformat(), "started_at": s["started_at"].isoformat()
                    if s["started_at"] else None, "stopped_at": s["stopped_at"].isoformat() if s["stopped_at"] else None,
                    "stop_requested": s["stop_requested"], "error": s["error"], "identity": s["identity"],
                    "method": (s.get("config") or {}).get("method") or "v0.2",
                    "heartbeat_age_seconds": hb_age,
                    "progress": s["progress"], "connection": s["connection"], "notes": s["diagnostic_log"][-20:]},
        "state": state, "running": running and state not in ("STOPPED", "FAILED"),
        "message": {"STOPPED": "Live adviser is stopped: nothing is monitored and no alerts are produced.",
                    "UNRESPONSIVE": "The live adviser worker is not heartbeating: advice below may be stale.",
                    "RECONSTRUCTING": "Catching up missed history (reconstructed, not live advice).",
                    "WARMING_UP": "Warming up: waiting for current receipts/required history; no actionable entry.",
                    "DISCONNECTED": "Disconnected from the public feed: entry cannot be verified.",
                    "LIVE": "Live: current public data and quotes are being assessed." if current else
                            "Live session evidence is not current (heartbeat/connection): entry cannot be verified."
                    }.get(state, state),
        "current": current,
        "view": present(view, state, current) if view else None,
        "alerts": [{**{k: a[k] for k in ("alert_key", "change_type", "subject_id", "summary", "acknowledged")},
                    "created_at": a["created_at"].isoformat()} for a in alerts],
        "notice": NOTICE,
    }


def analysis_markdown(st: dict[str, Any]) -> str:
    v = st.get("view") or {}
    mv = v.get("market_view") or {}
    call = v.get("call")
    lines = ["# BTC adviser — current analysis", "",
             f"State **{st['state']}** · clock {v.get('clock') or '—'} · origin {v.get('origin') or '—'}",
             f"> {st['notice']}", ""]
    if not st.get("current"):
        lines += [f"> **Not current advice** (session {st['state']}): no entry is presented as usable now.", ""]
    lines += [
             "## Market view",
             f"- Observed 1h context: {mv.get('observed_context', '—')} · phase {mv.get('phase', '—')}",
             f"- Expected direction: **{mv.get('expected_direction', '—')}**"
             + (" (conditional)" if mv.get("conditional") else "") + f" · row {mv.get('table_row', '—')}"]
    for r in mv.get("reasons") or []:
        lines.append(f"  - {r}")
    for r in mv.get("counterevidence") or []:
        lines.append(f"  - counterevidence: {r}")
    lines += ["", "## Call"]
    if call:
        lines += [f"- **{call['direction']} {call['family']}** ({call['family_text']}) issued {call['issued_at']} · "
                  f"origin {call['origin']}",
                  f"- Entry now: **{call['entry_status']}**" + (f" ({', '.join(call['entry_reasons'])})"
                                                                 if call["entry_reasons"] else ""),
                  f"- Structural area {call['structural_area'][0]}–{call['structural_area'][1]} · admissible now "
                  f"{(call['admissible_bounds'] or ['—', '—'])[0]}–{(call['admissible_bounds'] or ['—', '—'])[1]}",
                  f"- Target {call['target']} ({call['target_type']}) · stop guidance {call['stop']} · hard deadline "
                  f"{call['hard_deadline']} · remaining {call['remaining_minutes']} min",
                  f"- {call['guidance']}"]
    else:
        blockers = mv.get("blockers") or []
        lines.append("- **No actionable trade now**" + (f" — top blocker: {blockers[0]}" if blockers else ""))
    lines += ["", "## Lenses"]
    for ln in v.get("lenses") or []:
        lines.append(f"- {ln['name']}: {ln['result']} — {ln['role']}")
    return "\n".join(lines) + "\n"


def build_router(conn: Callable, data_root: Path) -> APIRouter:
    r = APIRouter(prefix="/api/adviser")

    @r.get("/live")
    def live() -> dict[str, Any]:
        with conn() as c:
            return live_status(c)

    @r.get("/methods")
    def method_list() -> dict[str, Any]:
        from . import methods

        return {"default": methods.DEFAULT, "methods": methods.selectable(),
                "note": "v0.2 is the accepted baseline, v0.3 is technically accepted; v0.4 and v0.5 are shown with "
                        "their recorded release status until Director acceptance; economic usefulness is unvalidated "
                        "for every version; stored results always show their pinned method"}

    @r.post("/live/start", status_code=201)
    def live_start(method: str | None = None) -> dict[str, Any]:
        import os

        base = os.environ.get("ALGOTRADER_OKX_REST_BASE_URL", "https://www.okx.com")
        with conn() as c:
            try:
                lv.start_session(c, base, method)
            except lv.LiveControlError as exc:
                raise HTTPException(409, str(exc)) from None
            return live_status(c)

    @r.post("/live/stop")
    def live_stop() -> dict[str, Any]:
        with conn() as c:
            s = _row(c, "SELECT session_id FROM adviser_live_sessions WHERE status IN ('queued','running') "
                        "ORDER BY created_at DESC LIMIT 1", ())
            if s is None:
                raise HTTPException(409, "no live adviser session is running")
            c.commit()  # end the read transaction: the command below is its own committed transaction
            lv.stop_session(c, s["session_id"])
            return live_status(c)

    @r.post("/live/reassess")
    def live_reassess() -> dict[str, Any]:
        with conn() as c:
            s = _row(c, "SELECT session_id FROM adviser_live_sessions WHERE status = 'running' ORDER BY created_at "
                        "DESC LIMIT 1", ())
            if s is None:
                raise HTTPException(409, "manual reassessment needs a running live session")
            lv.request_reassess(c, s["session_id"])
            c.commit()
            return live_status(c)

    @r.post("/live/alerts/{alert_key}/ack")
    def ack(alert_key: str) -> dict[str, Any]:
        with conn() as c:
            c.execute("UPDATE adviser_alerts SET acknowledged = true WHERE alert_key = %s", (alert_key,))
            c.commit()
            return live_status(c)

    @r.get("/live/analysis.md")
    def analysis() -> PlainTextResponse:
        with conn() as c:
            return PlainTextResponse(analysis_markdown(live_status(c)), media_type="text/markdown; charset=utf-8")

    @r.get("/journal/{run_id}")
    def journal(run_id: str, after_seq: int = 0, limit: int = Query(200, le=MAX_PAGE), kind: str | None = None,
                cutoff: datetime | None = None) -> dict[str, Any]:
        """Committed journal page (sequence order). ``cutoff`` returns only records published at or before it."""
        with conn() as c:
            q = "SELECT seq, kind, record_id, clock_time, origin, subject, digest, record FROM adviser_journal " \
                "WHERE run_id = %s AND seq > %s"
            args: list[Any] = [run_id, after_seq]
            if kind:
                q += " AND kind = %s"
                args.append(kind)
            if cutoff is not None:
                q += " AND clock_time <= %s"
                args.append(cutoff)
            rows = c.execute(q + " ORDER BY seq LIMIT %s", (*args, limit)).fetchall()
        return {"run_id": run_id, "records": [{**x, "clock_time": x["clock_time"].isoformat()} for x in rows],
                "next_after_seq": rows[-1]["seq"] if rows else after_seq, "committed_only": True}

    def _paths(rows: list, cutoff: datetime | None) -> tuple[list, int]:
        """Hypothetical paths knowable at ``cutoff`` (resolved_at <= cutoff); revision-1 records without a
        resolution time are withheld under a cutoff, never shown as if known."""
        if cutoff is None:
            return [x["record"] for x in rows], 0
        out, withheld = [], 0
        for x in rows:
            ra = x["record"].get("resolved_at")
            if ra is not None and datetime.fromisoformat(ra.replace("Z", "+00:00")) <= cutoff:
                out.append(x["record"])
            else:
                withheld += 1
        return out, withheld

    def _cut(q: str, args: list, cutoff: datetime | None) -> tuple[str, list]:
        return (q + " AND clock_time <= %s", [*args, cutoff]) if cutoff is not None else (q, args)

    @r.get("/runs/{replay_id}/calls")
    def calls(replay_id: str, cutoff: datetime | None = None) -> dict[str, Any]:
        """Committed calls with their revisions and hypothetical paths; ``cutoff`` shows only what was published (or,
        for hypothetical paths, determined) at or before it."""
        with conn() as c:
            q, a = _cut("SELECT record FROM adviser_journal WHERE run_id = %s AND kind = 'call'", [replay_id], cutoff)
            calls = c.execute(q + " ORDER BY seq", a).fetchall()
            q, a = _cut("SELECT subject, record FROM adviser_journal WHERE run_id = %s AND kind = 'call_revision'",
                        [replay_id], cutoff)
            revs = c.execute(q + " ORDER BY seq", a).fetchall()
            paths = c.execute("SELECT record FROM adviser_evaluation_records WHERE run_id = %s AND kind = 'path' "
                              "ORDER BY seq", (replay_id,)).fetchall()
        by_call: dict[str, list] = {}
        for x in revs:
            by_call.setdefault(x["record"]["call_id"], []).append(x["record"])
        kept, withheld = _paths(paths, cutoff)
        pby: dict[str, list] = {}
        for x in kept:
            pby.setdefault(x["call_id"], []).append(x)
        return {"replay_id": replay_id, "cutoff": cutoff.isoformat() if cutoff else None,
                "calls": [{"call": x["record"], "revisions": by_call.get(x["record"]["call_id"], []),
                           "hypothetical_paths": pby.get(x["record"]["call_id"], [])} for x in calls],
                "hypothetical_paths_withheld_at_cutoff": withheld,
                "note": "hypothetical paths are normalized one-unit simulations, not fills or account results"}

    @r.get("/runs/{replay_id}/calls/{call_id}")
    def call_detail(replay_id: str, call_id: str, cutoff: datetime | None = None) -> dict[str, Any]:
        with conn() as c:
            q, a = _cut("SELECT seq, kind, record FROM adviser_journal WHERE run_id = %s AND (subject = %s OR "
                        "record_id = %s)", [replay_id, call_id, call_id], cutoff)
            rows = c.execute(q + " ORDER BY seq", a).fetchall()
            call = next((x["record"] for x in rows if x["kind"] == "call"), None)
            if call is None:
                raise HTTPException(404, f"call {call_id} not found in {replay_id}"
                                         + (f" at or before {cutoff.isoformat()}" if cutoff else ""))
            attempt = call["attempt_id"]
            q, a = _cut("SELECT record FROM adviser_journal WHERE run_id = %s AND kind = 'candidate' AND subject = %s",
                        [replay_id, attempt], cutoff)
            cand = c.execute(q + " ORDER BY seq", a).fetchall()
            q, a = _cut("SELECT record FROM adviser_journal WHERE run_id = %s AND kind = 'actionability' AND "
                        "subject IN (%s, %s)", [replay_id, attempt, call_id], cutoff)
            act = c.execute(q + " ORDER BY seq", a).fetchall()
            # v0.3: the child entry attempt (waiting/routing/caps) and its independent structural scenario
            q, a = _cut("SELECT record FROM adviser_journal WHERE run_id = %s AND kind = 'entry_attempt' AND "
                        "subject = %s", [replay_id, attempt], cutoff)
            entry = c.execute(q + " ORDER BY seq", a).fetchall()
            q, a = _cut("SELECT record FROM adviser_journal WHERE run_id = %s AND kind = 'scenario' AND subject = %s",
                        [replay_id, call.get("scenario_id") or ""], cutoff)
            scen = c.execute(q + " ORDER BY seq", a).fetchall()
            paths = c.execute("SELECT record FROM adviser_evaluation_records WHERE run_id = %s AND kind = 'path' AND "
                              "record->>'call_id' = %s ORDER BY seq", (replay_id, call_id)).fetchall()
            view = c.execute("SELECT record FROM adviser_journal WHERE run_id = %s AND kind = 'market_view' AND "
                             "clock_time <= %s ORDER BY seq DESC LIMIT 1", (replay_id, call["issued_at"])).fetchone()
        kept, withheld = _paths(paths, cutoff)
        return {"call": call, "cutoff": cutoff.isoformat() if cutoff else None,
                "candidate": [x["record"] for x in cand], "actionability": [x["record"] for x in act],
                **({"entry_attempt": [x["record"] for x in entry], "scenario": [x["record"] for x in scen]}
                   if call.get("scenario_id") else {}),
                "revisions": [x["record"] for x in rows if x["kind"] == "call_revision"],
                "material_changes": [x["record"] for x in rows if x["kind"] == "material_change"],
                "market_view_at_issue": view["record"] if view else None,
                "hypothetical_paths": kept, "hypothetical_paths_withheld_at_cutoff": withheld,
                "labels": {"hypothetical_paths": "HYPOTHETICAL normalized one-unit simulation; not a fill or account "
                                                 "result; the guidance itself is in revisions"}}

    @r.get("/runs/{replay_id}/window")
    def window(replay_id: str, cursor: int = Query(..., ge=0), before: int = Query(1500, ge=0, le=6000),
               after: int = Query(1500, ge=0, le=6000)) -> dict[str, Any]:
        """Bounded 1m trade-bar window around a factual cursor of an adviser run, from its pinned (SHA-verified) cache,
        clamped to the run's COMMITTED factual frontier: nothing beyond the committed cursor is ever returned."""
        from ..feed.contracts import EventKind, Family
        from ..observe.feedcache import CacheError, CacheReader, decode, open_cache

        with conn() as c:
            row = c.execute("SELECT r.engine, k.cursor FROM observation_replays r LEFT JOIN observation_checkpoints k "
                            "ON k.replay_id = r.replay_id WHERE r.replay_id = %s", (replay_id,)).fetchone()
        if row is None or not (row["engine"] or {}).get("adviser"):
            raise HTTPException(404, f"{replay_id} is not an adviser evaluation run")
        committed = row["cursor"] or 0
        if cursor > committed:
            raise HTTPException(409, f"cursor {cursor} is beyond the committed frontier {committed}")
        eng = row["engine"]
        lo, hi = max(0, cursor - before), min(cursor + after, committed)
        bars = []
        if hi > lo:
            try:
                cache = open_cache(data_root, eng["cache_id"], expected_manifest_sha256=eng["cache_manifest_sha256"])
                for seq, line in CacheReader(cache, {}).iter_from(lo):
                    if seq >= hi:
                        break
                    e = decode(line)
                    if e.channel.family == Family.TRADE_BAR_1M and e.kind == EventKind.BAR_OBSERVATION:
                        p = e.payload
                        bars.append({"t": e.event_time.isoformat(), "o": str(p.open), "h": str(p.high),
                                     "l": str(p.low), "c": str(p.close)})
            except CacheError as exc:
                raise HTTPException(409, f"pinned feed cache unavailable or altered: {exc}") from None
        return {"replay_id": replay_id, "bars": bars, "committed_cursor": committed, "range": [lo, hi],
                "label": "historical trade minutes (pinned pack cache) within the committed frontier"}

    _ = psycopg
    return r
