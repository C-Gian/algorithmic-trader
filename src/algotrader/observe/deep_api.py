"""Deep validation views, reports and routes (diagnostic jobs linked to a streaming run)."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from .. import ops
from . import deep

DEEP_PHASES = ("QUEUED", "PREPARING_SOURCE", "VALIDATING", "GENERATING_REPORT")


def deep_view(row: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    status = row["status"]
    terminal = status in deep.TERMINAL
    lease_expired = bool(status == "running" and row["lease_expires_at"] and row["lease_expires_at"] < now)
    health, detail = ops.derive_health(
        status=status, phase=row["phase"], lease_expired=lease_expired, last_progress_at=row["last_progress_at"],
        heartbeat_at=row["heartbeat_at"], progress=row["progress"], supervisor=row["supervisor"],
        generation=row["lease_generation"], now=now, paused=row["paused"])
    p = row["progress"] or {}
    running = status == "running" and not lease_expired
    tl = ops.timeline(list(row["phase_history"] or []), None if terminal else row["phase"], row["phase_started_at"],
                      running, now, DEEP_PHASES, current_measure=p)
    eta = ops.phase_eta(p.get("done"), p.get("total"), p.get("rate_base_done"), p.get("rate_window_seconds"),
                        "events") if running else (None, "no ETA while " + status)
    plan = row["plan"]
    result = row["result"]
    return {
        "validation_id": row["validation_id"], "replay_id": row["replay_id"], "kind": "deep_validation",
        "validator": plan["validator"], "validator_version": plan["validator_version"], "scope": plan["scope"],
        "mode": plan["mode"], "status": status, "phase": row["phase"],
        "phase_label": ops.PHASE_LABEL.get(row["phase"] or "", "—"),
        "health": health.value, "health_label": ops.HEALTH_LABEL[health.value], "health_detail": detail,
        "generation": row["lease_generation"], "attempt": row["attempt"],
        "progress": {"done": p.get("done"), "total": plan["committed_cursor"], "unit": "events",
                     "fraction": (p.get("done") / plan["committed_cursor"]) if p.get("done") is not None else None,
                     "saved_cursor": row["resume_cursor"], "stage": p.get("stage"),
                     "last_progress_at": ops.iso(row["last_progress_at"])},
        "eta": {"seconds": eta[0], "basis": eta[1], "scope": "current phase only"},
        "timeline": tl, "created_at": ops.iso(row["created_at"]), "started_at": ops.iso(row["started_at"]),
        "finished_at": ops.iso(row["finished_at"]),
        "controls": {"cancel": {"enabled": not terminal and not row["cancel_requested"]},
                     "pause": {"enabled": status in ("queued", "running") and not row["paused"]
                               and not row["cancel_requested"]},
                     "resume": {"enabled": bool(row["paused"]) and not terminal}},
        "cancel_requested": row["cancel_requested"], "paused": row["paused"],
        "plan": plan, "comparisons": {"compared": (row["comparisons"] or {}).get("compared", 0),
                                      "mismatches": len((row["comparisons"] or {}).get("mismatches", []))},
        "result": result, "error": row["error"], "recovery_log": row["recovery_log"],
        "diagnostic_log": row["diagnostic_log"],
    }


_RUNTIME_LABEL = {
    "passed": "Runtime integrity verified, engine reference-tested",
    "failed": "Runtime integrity FAILED",
    "incomplete": "Runtime assurance INCOMPLETE",
    "not_checked": "Runtime assurance NOT CHECKED",
}


def _coverage(res: dict[str, Any]) -> str:
    covered, target, total = res.get("covered_events"), res.get("target_events"), res.get("run_total_events")
    text = f"{covered if covered is not None else '—'}/{target if target is not None else '—'} committed events"
    if total is not None and target is not None and target != total:
        text += f" (run total {total}: the uncommitted remainder was not examined)"
    return text


def assurance_summary(c, replay_id: str, op_assurance: dict[str, Any] | None,
                      status: str | None = None) -> dict[str, Any]:
    """Current assurance of a run: its own runtime/terminal validation and the linked Deep validation results,
    always reported side by side. A Deep (reference) MATCH never promotes a failed, incomplete or unchecked
    runtime result, and never hides runtime warnings or limited diagnostic coverage.

    ``status`` is the run's operational status. While the run is not finished, an unchecked or in-progress
    runtime result is the normal state ("pending"), not a warning; a FAILED result is always a warning."""
    rows = c.execute("SELECT validation_id, status, result, finished_at FROM observation_deep_validations "
                     "WHERE replay_id = %s ORDER BY created_at DESC", (replay_id,)).fetchall()
    latest = rows[0] if rows else None
    run_state = (op_assurance or {}).get("state")
    pending = status is not None and status not in deep.TERMINAL and run_state in (None, "not_checked", "incomplete")
    runtime_label = ("Runtime checks pending - they run when the replay finishes" if pending else
                     _RUNTIME_LABEL.get(str(run_state), f"Runtime assurance {str(run_state or 'pending').upper()}"))
    warnings: list[str] = []
    limitations: list[str] = []
    if run_state is not None and run_state != "passed" and not pending:
        detail = (op_assurance or {}).get("detail")
        warnings.append(f"{runtime_label}" + (f": {detail}" if detail else "")
                        + " - a Deep validation result does not change this runtime outcome")
    mismatch_found = False
    for r in rows:
        res = r["result"] or {}
        if res.get("mismatches"):
            mismatch_found = True
            done = r["status"] == "completed"
            warnings.append(f"Deep validation {r['validation_id']} found {len(res['mismatches'])} mismatch(es) between "
                            "the independent reference execution and the run's committed records"
                            + ("" if done else f" before it stopped ({r['status']}, {_coverage(res)})"))
    deep_state = "not_run"
    if latest is not None:
        deep_state = ((latest["result"] or {}).get("outcome") if latest["status"] in deep.TERMINAL
                      else latest["status"])
    earlier_match = next((r for r in rows[1:] if r["status"] == "completed"
                          and (r["result"] or {}).get("outcome") == "match"), None)
    if latest is None:
        reference_label = "no Deep validation of this run"
    elif deep_state == "match":
        reference_label = (f"Deep validation reference re-execution matched ({_coverage(latest['result'])}; "
                           "canonical-cache scope)")
        if (latest["result"] or {}).get("target_events") != (latest["result"] or {}).get("run_total_events"):
            limitations.append(f"Deep validation {latest['validation_id']} examined only the committed prefix: "
                               f"{_coverage(latest['result'])}")
    elif deep_state == "mismatch":
        reference_label = "Deep validation reference re-execution MISMATCH"
    elif latest["status"] in deep.TERMINAL:
        reference_label = (f"latest Deep validation {latest['status'].upper()} - INCOMPLETE, no reference conclusion "
                           f"({_coverage(latest['result'] or {})})")
        if earlier_match is not None:
            reference_label += f"; earlier Deep validation {earlier_match['validation_id']} matched"
    else:
        reference_label = f"Deep validation {latest['status']}"
    headline = f"{runtime_label}; {reference_label}"
    if mismatch_found:
        headline = f"ASSURANCE WARNING - Deep validation mismatch; {runtime_label}"
    elif warnings:
        headline = f"ASSURANCE WARNING - {headline}"
    return {"headline": headline, "run_validation": run_state,
            "runtime": {"state": run_state, "label": runtime_label, "pending": pending},
            "deep_validation": deep_state, "reference": {"state": deep_state, "label": reference_label,
                                                         "earlier_match": earlier_match["validation_id"]
                                                         if earlier_match else None},
            "latest_deep_validation": latest["validation_id"] if latest else None,
            "deep_validations": len(rows), "warnings": warnings, "limitations": limitations}


def deep_report(row: dict[str, Any], now: datetime) -> dict[str, Any]:
    v = deep_view(row, now)
    terminal = v["status"] in deep.TERMINAL
    return {"report_kind": "DEEP_VALIDATION", "report_format": "algotrader.deep-validation-report.v1",
            "snapshot": not terminal, "captured_at": None if terminal else now.isoformat(),
            **{k: v[k] for k in ("validation_id", "replay_id", "validator", "validator_version", "scope", "mode",
                                 "status", "phase", "generation", "attempt", "plan", "comparisons", "result",
                                 "error", "recovery_log", "created_at", "started_at", "finished_at")},
            "health": None if terminal else {"state": v["health"], "detail": v["health_detail"]},
            "progress": v["progress"],
            "timing": {"active_seconds_total": v["timeline"]["active_seconds_total"],
                       "unmeasured_spans": v["timeline"]["unmeasured_spans"],
                       "phases": [p for p in v["timeline"]["phases"] if p["spans"] or p["state"] == "current"]},
            "counters": row.get("metrics") or {},
            "note": ("Diagnostic only: this result never changes the originating run's records, artifacts or "
                     "terminal report.")}


def render_markdown(r: dict[str, Any]) -> str:
    res = r["result"] or {}
    head = "Deep validation report" + ("" if not r["snapshot"] else " — snapshot (incomplete)")
    lines = [f"# {head}", "",
             f"**{r['report_kind']}** · validation `{r['validation_id']}` · run `{r['replay_id']}`"
             + (f" · captured {r['captured_at']}" if r["captured_at"] else ""),
             f"**Status:** {r['status'].upper()} · outcome **{str(res.get('outcome', 'pending')).upper()}** · "
             f"validator {r['validator']} v{r['validator_version']} · mode {r['mode']}", "",
             f"> {r['scope']}", "",
             f"- Covered events: {res.get('covered_events', r['progress'].get('done'))}/"
             f"{r['plan']['committed_cursor']} (run total {r['plan']['total_events']})",
             f"- Comparisons: {r['comparisons']['compared']} at {res.get('comparison_cursors', '—')} cursors · "
             f"mismatches {r['comparisons']['mismatches']}",
             f"- Input examined: {res.get('input_examined', 'canonical feed cache only')}",
             f"- Cache `{r['plan']['cache_id']}` · manifest {r['plan']['cache_manifest_sha256'][:16]}",
             f"- Active time {r['timing']['active_seconds_total']:.1f} s"
             + (f" · {r['timing']['unmeasured_spans']} unmeasured span(s)" if r["timing"]["unmeasured_spans"] else ""),
             f"- Attempts {r['attempt']} · generation {r['generation']}"]
    for m in (res.get("mismatches") or [])[:10]:
        lines.append(f"  - MISMATCH at cursor {m['cursor']} ({m['at']}, {m['kind']}): expected {m['expected'][:16]} "
                     f"reference {m['reference'][:16]}")
    if r["error"]:
        lines.append(f"- Detail: {r['error']}")
    lines += ["", f"_{r['note']}_", ""]
    return "\n".join(lines)


def build_router(conn: Callable) -> APIRouter:
    r = APIRouter(prefix="/api/observations")

    def get(c, vid: str) -> dict[str, Any]:
        row = c.execute("SELECT * FROM observation_deep_validations WHERE validation_id = %s", (vid,)).fetchone()
        if row is None:
            raise HTTPException(404, f"deep validation {vid} not found")
        return row

    @r.post("/{replay_id}/deep-validations", status_code=201)
    def launch(replay_id: str) -> dict[str, Any]:
        with conn() as c:
            try:
                vid = deep.create_deep_validation(c, replay_id)
            except LookupError:
                raise HTTPException(404, f"observation replay {replay_id} not found") from None
            except deep.DeepRejected as exc:
                raise HTTPException(409, str(exc)) from None
            return deep_view(get(c, vid))

    @r.get("/{replay_id}/deep-validations")
    def list_deep(replay_id: str) -> list[dict[str, Any]]:
        with conn() as c:
            rows = c.execute("SELECT * FROM observation_deep_validations WHERE replay_id = %s ORDER BY created_at DESC",
                             (replay_id,)).fetchall()
        return [deep_view(x) for x in rows]

    @r.get("/{replay_id}/assurance")
    def assurance(replay_id: str) -> dict[str, Any]:
        with conn() as c:
            row = c.execute("SELECT assurance, status FROM observation_replays WHERE replay_id = %s",
                            (replay_id,)).fetchone()
            if row is None:
                raise HTTPException(404, f"observation replay {replay_id} not found")
            return assurance_summary(c, replay_id, row["assurance"], row["status"])

    @r.get("/deep-validations/{vid}")
    def detail(vid: str) -> dict[str, Any]:
        with conn() as c:
            return deep_view(get(c, vid))

    def command(vid: str, cmd: str) -> dict[str, Any]:
        with conn() as c:
            try:
                deep.control(c, vid, cmd)
            except LookupError:
                raise HTTPException(404, f"deep validation {vid} not found") from None
            except deep.DeepRejected as exc:
                raise HTTPException(409, str(exc)) from None
            return deep_view(get(c, vid))

    @r.post("/deep-validations/{vid}/cancel")
    def cancel(vid: str) -> dict[str, Any]:
        return command(vid, "cancel")

    @r.post("/deep-validations/{vid}/pause")
    def pause(vid: str) -> dict[str, Any]:
        return command(vid, "pause")

    @r.post("/deep-validations/{vid}/resume")
    def resume(vid: str) -> dict[str, Any]:
        return command(vid, "resume")

    def report(vid: str) -> dict[str, Any]:
        with conn() as c:
            return deep_report(get(c, vid), datetime.now(UTC))

    @r.get("/deep-validations/{vid}/report.json")
    def report_json(vid: str, download: bool = False) -> PlainTextResponse:
        headers = {"Content-Disposition": f'attachment; filename="{vid}.json"'} if download else {}
        return PlainTextResponse(json.dumps(report(vid), indent=2, sort_keys=True, default=str) + "\n",
                                 media_type="application/json", headers=headers)

    @r.get("/deep-validations/{vid}/report.md")
    def report_md(vid: str, download: bool = False) -> PlainTextResponse:
        headers = {"Content-Disposition": f'attachment; filename="{vid}.md"'} if download else {}
        return PlainTextResponse(render_markdown(report(vid)), media_type="text/markdown; charset=utf-8",
                                 headers=headers)

    return r
