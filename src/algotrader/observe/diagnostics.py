"""Operational view and diagnostic export for observation replays (any status, any lifecycle version).

Built only from bounded persisted facts: the replay row (status, phase history, progress,
generation, supervisor facts, counters, logs), its checkpoint cursor and - when one is
claimed - the terminal manifest, whose existence/size on disk is checked. Nothing here
re-executes the source or reads all delivery rows, so a diagnostic report is available
while queued, preparing, running, paused, validating, interrupted, failed or cancelled,
and also when the final manifest is missing or final report generation failed.

A diagnostic export is not terminal assurance: it never infers validation from a full cursor.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .. import ops
from .artifacts import files_dir
from .contracts import ReplayRuntimeState

DIAGNOSTIC_FORMAT = "algotrader.observe-diagnostic.v1"  # operational export format (not a domain contract)
TERMINAL = {"completed", "cancelled", "failed"}
PREP = {"QUEUED", "PREPARING_SOURCE", "VERIFYING_SOURCE", "BUILDING_FEED", "INITIALIZING"}
POST = {"FINALIZING", "VALIDATING", "GENERATING_REPORT"}

STREAM_NOTE = (
    "Streaming engine (observe.stream.v1): every event is applied by one incremental kernel; snapshots are "
    "materialized only at checkpoints; committed input is persisted as compact ranges plus restorable "
    "checkpoints (no per-event delivery rows/transactions); restore is direct from a verified checkpoint.")
REMAINING_COSTS = (
    "R1A keeps the WP-007 engine costs on purpose (removed in R1B/R1C): eager full feed construction in memory, "
    "duplicate source verification inside feed construction, one PostgreSQL transaction + one delivery row + one "
    "full observable snapshot per feed event, full prefix rebuild on every restore/resume, and a full pure "
    "re-derivation of every committed delivery during terminal validation."
)


def _lease_expired(row: dict[str, Any], now: datetime) -> bool:
    return bool(row["status"] == "running" and row["lease_expires_at"] and row["lease_expires_at"] < now)


def runtime_state(row: dict[str, Any], lease_expired: bool) -> tuple[ReplayRuntimeState, str]:
    status = row["status"]
    progress = row.get("progress") or {}
    phase = row.get("phase")
    if row.get("suspended_at") is not None:
        return ReplayRuntimeState.SUSPENDED, (row.get("suspension") or {}).get("reason", "suspended")
    applied, total = row.get("applied") or 0, row["total_events"]
    cov = f"{applied:,}/{total:,}" if total is not None else f"{applied:,}/PENDING"
    if status in TERMINAL:
        a_state = (row.get("assurance") or {}).get("state") or (
            ("passed" if row["manifest"]["validation"]["passed"] else "failed") if row.get("manifest") else "not_checked")
        return ReplayRuntimeState(status), {
            "completed": f"replay cursor {cov} and terminal artifacts published (operational completion); "
                         f"assurance {a_state.replace('_', ' ')} is reported separately",
            "cancelled": f"cancelled by user at cursor {cov}; assurance {a_state.replace('_', ' ')}",
            "failed": f"failed at cursor {cov}; see error; assurance {a_state.replace('_', ' ')}",
        }[status]
    if row["cancel_requested"]:
        return ReplayRuntimeState.CANCEL_REQUESTED, "cancellation requested; applied at the next safe boundary"
    if status == "running" and lease_expired:
        return ReplayRuntimeState.UNRESPONSIVE, "lease expired; awaiting recovery by a new fenced attempt"
    if status == "running" and progress.get("restoring"):
        return ReplayRuntimeState.RECOVERING, "a new fenced attempt is restoring the committed state"
    if row["paused"]:
        if row["step_budget"] > 0:
            return ReplayRuntimeState.STEPPING, f"paused; {row['step_budget']} single feed delivery(ies) pending"
        if status == "running" and phase not in PREP:
            return ReplayRuntimeState.PAUSING, "pause requested; worker finishes the current delivery"
        if status == "running":
            return ReplayRuntimeState.PREPARING, "preparing the source; it will park at cursor 0 (pause requested)"
        if status == "queued":
            return ReplayRuntimeState.QUEUED, "waiting for an observation worker to prepare the source (start paused)"
        return ReplayRuntimeState.PAUSED, "paused at a committed feed cursor; no worker holds the replay"
    if status == "running" and phase in PREP:
        return ReplayRuntimeState.PREPARING, f"{ops.PHASE_LABEL.get(phase, phase)}"
    if status == "running" and phase in POST:
        target = progress.get("finalizing_as") or "completed"
        what = ops.PHASE_LABEL.get(phase, phase).lower()
        if total is not None and applied == total:
            head = f"replay cursor complete ({cov}); {what}"
        else:
            head = f"{what} a partial run at cursor {cov}"
        return ReplayRuntimeState.FINISHING, (f"{head} as {target}; not finished until artifacts and the terminal "
                                              "status are committed; completion is separate from assurance")
    if status == "running":
        return ReplayRuntimeState.RUNNING, f"worker {row['lease_owner']} is applying feed deliveries"
    return ReplayRuntimeState.QUEUED, "waiting for an observation worker"


def _controls(row: dict[str, Any], applied: int) -> dict[str, dict[str, Any]]:
    status, phase = row["status"], row.get("phase")
    total = row["total_events"]

    def ctl(ok: bool, why: str | None) -> dict[str, Any]:
        return {"enabled": ok, "reason": None if ok else why}

    if row.get("suspended_at") is not None:
        why = "pre-upgrade run suspended read-only; use the diagnostic export"
        return {k: ctl(False, why) for k in ("pause", "resume", "step", "speed", "cancel")}
    if status in TERMINAL:
        why = f"operation {status}"
        return {k: ctl(False, why) for k in ("pause", "resume", "step", "speed", "cancel")}
    cancel_req = row["cancel_requested"]
    post = status == "running" and phase in POST
    return {
        "pause": ctl(not cancel_req and not row["paused"] and not post,
                     "cancellation requested" if cancel_req else "already paused" if row["paused"]
                     else f"not applicable during {phase}"),
        "resume": ctl(bool(row["paused"]) and not cancel_req,
                      "cancellation requested" if cancel_req else "not paused"),
        "step": ctl(bool(row["paused"]) and not cancel_req and total is not None and not post
                    and applied + row["step_budget"] < total,
                    "cancellation requested" if cancel_req else "only while paused" if not row["paused"]
                    else "available once preparation has fixed the feed" if total is None
                    else f"not applicable during {phase}" if post else "no feed deliveries left"),
        "speed": ctl(not cancel_req and not post, "cancellation requested" if cancel_req
                     else f"not applicable during {phase}"),
        "cancel": ctl(not cancel_req, "cancellation already requested"),
    }


def operation(row: dict[str, Any], now: datetime) -> dict[str, Any]:
    """The shared status / phase / health / assurance view of one observation replay."""
    status = row["status"]
    terminal = status in TERMINAL
    legacy = (row.get("lifecycle_version") or ops.LIFECYCLE_LEGACY) < ops.LIFECYCLE_R1A
    applied = row.get("applied") or 0
    lease_expired = _lease_expired(row, now)
    progress = dict(row.get("progress") or {})
    suspended = row.get("suspended_at") is not None
    generation = row.get("lease_generation") or 0
    health, health_detail = ops.derive_health(
        status=status, phase=row.get("phase"), lease_expired=lease_expired,
        last_progress_at=row.get("last_progress_at"), heartbeat_at=row["heartbeat_at"], progress=progress,
        supervisor=row.get("supervisor"), generation=generation, now=now, suspended=suspended,
        paused=bool(row["paused"]))
    if legacy and not terminal and not suspended:
        health, health_detail = ops.Health.SUSPENDED, "pre-upgrade run without lifecycle tracking"
    running = status == "running" and not lease_expired
    phase = row.get("phase")
    tl = ops.timeline(list(row.get("phase_history") or []), None if terminal else phase,
                      row.get("phase_started_at"), running, now, ops.OBSERVATION_PHASES, current_measure=progress)
    # current-phase progress
    if phase == "REPLAYING" or (legacy and not terminal):
        done, total, unit = applied, row["total_events"], "events"
    else:
        done, total, unit = progress.get("done"), progress.get("total"), progress.get("unit")
    eta, basis = None, "unknown"
    if running:
        if phase == "REPLAYING":
            # window = this REPLAYING span since its start / the last pacing change (never claim or preparation)
            since, base = row["throughput_since"], row["throughput_base"]
            speed = row["speed"]
            waits = progress.get("phase_waiting_seconds") or 0.0
            eta, basis = ops.phase_eta(
                applied, row["total_events"], base, (now - since).total_seconds() if since else None, "events",
                basis=("wall-clock replay time in the current REPLAYING window at pacing "
                       f"{'max' if speed == 0 else f'{speed:g} events/s'}; this span contains {waits:.1f}s of declared "
                       "pacing waits (not active compute throughput)"))
        else:
            eta, basis = ops.phase_eta(done, total, progress.get("rate_base_done"),
                                       progress.get("rate_window_seconds"), unit or "units")
    else:
        basis = f"no ETA while {status}" if not terminal else "finished"
    assurance = row.get("assurance")
    if assurance is None:
        m = row.get("manifest")
        if m is not None:
            v = m["validation"]
            assurance = {"state": "passed" if v["passed"] else "failed", "validator": v.get("validator") or
                         "observe.terminal-revalidation (revision 1)", "validator_version": v.get("validator_version"),
                         "scope": v.get("scope") or "revision-1 terminal re-derivation", "legacy": legacy}
        else:
            assurance = {"state": ops.Assurance.NOT_CHECKED.value,
                         "detail": "no terminal validation has run" + ("" if terminal else " yet")}
    sup = dict(row.get("supervisor") or {})
    sup.pop("environment", None)
    return {
        "contract": ops.OPS_CONTRACT,
        "lifecycle_version": row.get("lifecycle_version") or ops.LIFECYCLE_LEGACY,
        "status": status,
        "phase": phase,
        "phase_label": ops.PHASE_LABEL.get(phase or "", "Not tracked (pre-upgrade run)" if legacy else "—"),
        "phase_started_at": ops.iso(row.get("phase_started_at")),
        "health": health.value,
        "health_label": ops.HEALTH_LABEL[health.value],
        "health_detail": health_detail,
        "assurance": assurance,
        "generation": generation,
        "attempt": row["attempt"],
        "progress": {
            "stage": progress.get("stage"), "done": done, "total": total, "unit": unit,
            "fraction": (done / total) if (done is not None and total) else None,
            "detail": progress.get("detail"), "waiting": progress.get("waiting"),
            "progress_seq": row.get("progress_seq") or 0,
            "last_progress_at": ops.iso(row.get("last_progress_at")),
            "last_progress_age_seconds": ((now - row["last_progress_at"]).total_seconds()
                                          if (row.get("last_progress_at") and not terminal) else None),
            "stall_limit_seconds": progress.get("stall_limit"),
            "noninterruptible_units": progress.get("noninterruptible_units"),
        },
        "eta": {"seconds": eta, "basis": basis, "scope": "current phase only (never a whole-job estimate)"},
        "timeline": tl,
        "wall_seconds": (((row["finished_at"] or now) - row["created_at"]).total_seconds()),
        "controls": _controls(row, applied),
        "supervisor": sup,
        "suspension": ({"at": ops.iso(row["suspended_at"]), **(row.get("suspension") or {})} if suspended else None),
        "diagnostic_log": list(row.get("diagnostic_log") or []),
        "metrics": row.get("metrics") or {},
    }


# ---------------------------------------------------------------------------
# Diagnostic export
# ---------------------------------------------------------------------------


HASH_LIMIT = 64 * 2**20


def _host_line(env: Any) -> str:
    if not isinstance(env, dict):
        return str(env)
    ram = env.get("ram_bytes")
    return (f"{env.get('platform')} · Python {env.get('python')} · CPU {env.get('cpu_model') or 'unknown'} · "
            f"{env.get('logical_cpus')} logical · RAM {f'{ram / 2**30:.1f} GiB' if ram else 'unknown'} · "
            f"cgroup cpu.max {env.get('cgroup_cpu_max') or 'n/a'} · memory.max {env.get('cgroup_memory_max') or 'n/a'}")


def _sha_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest_check(art_root: Path, row: dict[str, Any]) -> dict[str, Any]:
    m = row.get("manifest")
    if m is None:
        return {"claimed": False, "detail": "no terminal manifest is recorded for this replay"}
    d = files_dir(art_root, row["replay_id"], m)
    mf = d / "manifest.json"
    out: dict[str, Any] = {"claimed": True, "artifact_dir": m.get("artifact_dir") or "(revision-1 replay directory)",
                           "manifest_file_present": mf.is_file()}
    if mf.is_file():
        data = mf.read_bytes()
        out["manifest_file_sha256"] = hashlib.sha256(data).hexdigest()
        try:
            out["manifest_file_matches_database"] = json.loads(data) == m
        except ValueError:
            out["manifest_file_matches_database"] = False
    files = []
    for a in m.get("artifacts", []):
        p = d / a["name"]
        files.append({"name": a["name"], "present": p.is_file(),
                      "size_matches": p.is_file() and p.stat().st_size == a["bytes"],
                      "sha256_matches": (_sha_file(p) == a["sha256"]) if p.is_file() and a["bytes"] <= HASH_LIMIT
                      else None})
    out["artifacts"] = files
    out["note"] = (f"file presence and sizes checked; artifacts up to {HASH_LIMIT // 2**20} MiB re-hashed against the "
                   "manifest (larger legacy traces: size only)")
    return out


def next_diagnostic(row: dict[str, Any], op: dict[str, Any]) -> str:
    h, status, phase = op["health"], row["status"], row.get("phase")
    if op["suspension"]:
        return ("Pre-upgrade run preserved read-only. Keep it as incomplete diagnostic evidence; the replacement "
                "September run is a new run on the same local dataset once R1C is accepted (no redownload).")
    if h in ("unresponsive", "compute_lost"):
        return "Check that the observer service is running; a new fenced attempt resumes from the committed cursor."
    if h == "alive_no_progress":
        return (f"The supervisor is alive but {phase} reported no milestone within its limit: copy this report to "
                "the Director (possible stuck work; do not restart blindly).")
    if status == "failed":
        return "Copy this report to the Director: the error and phase identify where the operation failed."
    if status == "cancelled":
        return "Cancelled: coverage/assurance are incomplete as reported; relaunch only when needed."
    if status == "completed":
        return "Terminal: compare phase timings and counters with the next run (R1B/R1C performance work)."
    return "In progress: this is a snapshot, not a result. Re-copy later or wait for the terminal report."


STREAM_REMAINING = (
    "Remaining for R1C: layered assurance closure and the optional observable Deep validation (reference "
    "re-execution), full release performance gates on representative data, and the Owner's September run.")


def diagnostic_report(row: dict[str, Any], art_root: Path, now: datetime,
                      evaluation: dict[str, Any] | None = None, storage: dict[str, Any] | None = None) -> dict[str, Any]:
    op = operation(row, now)
    terminal = row["status"] in TERMINAL
    cfg = row.get("config")
    launch = row.get("launch") or {}
    applied = row.get("applied") or 0
    total = row["total_events"]
    pending = "PENDING"
    src = (cfg or {}).get("source") or {}
    env = (row.get("supervisor") or {}).get("environment") or {}
    return {
        "report_kind": "OBSERVATION_REPLAY_DIAGNOSTIC",
        "report_format": DIAGNOSTIC_FORMAT,
        "run_type": "Market replay — data and engine check (observation only; no adviser)",
        "snapshot": not terminal,
        "captured_at": None if terminal else now.isoformat(),
        "replay_id": row["replay_id"],
        "evaluation_id": (evaluation or {}).get("evaluation_id") or launch.get("evaluation_id"),
        "lifecycle_version": op["lifecycle_version"],
        "identity": {
            "source_kind": row["source_kind"], "source_id": row["source_id"],
            "source_status": src.get("source_status", pending),
            "verified": (cfg or {}).get("verification", {}).get("verified") if cfg else pending,
            "feed_content_identity": (cfg or {}).get("feed", {}).get("content_identity", pending) if cfg else pending,
            "ordered_event_hash": (cfg or {}).get("feed", {}).get("ordered_event_hash", pending) if cfg else pending,
            "availability_basis": (cfg or {}).get("availability_policy", {}).get("basis", pending) if cfg else pending,
            "total_events": total if total is not None else pending,
        },
        "engine": {"code_version": (cfg or {}).get("code_version") or launch.get("code_version"),
                   "environment": env or "unknown (not recorded by this run's worker)"},
        "status": row["status"],
        "phase": op["phase"],
        "health": {"state": op["health"], "detail": op["health_detail"]} if not terminal else
                  {"state": op["health"], "detail": "terminal"},
        "assurance": op["assurance"],
        "coverage": {
            "committed_cursor": applied, "total_events": total if total is not None else pending,
            "fraction": (applied / total) if total else None,
            "information_time": ops.iso(row.get("info_time")), "last_event_id": row.get("last_event_id"),
            "note": "replay cursor coverage only; a full cursor is not completed validation",
        },
        "timing": {
            "created_at": ops.iso(row["created_at"]), "started_at": ops.iso(row["started_at"]),
            "finished_at": ops.iso(row["finished_at"]),
            "wall_seconds_since_launch": op["wall_seconds"],
            "active_seconds_total": op["timeline"]["active_seconds_total"],
            "waiting_seconds_total": op["timeline"]["waiting_seconds_total"],
            "unmeasured_spans": op["timeline"]["unmeasured_spans"],
            "active_complete": op["timeline"]["active_complete"],
            "definitions": op["timeline"]["definitions"],
            "phases": [p for p in op["timeline"]["phases"] if p["spans"] or p["state"] == "current"],
            "phase_spans": list(row.get("phase_history") or []),
        },
        "attempts": {"attempt": row["attempt"], "max_attempts": row["max_attempts"], "generation": op["generation"],
                     "recovery_log": list(row["recovery_log"] or []),
                     "diagnostic_log": op["diagnostic_log"]},
        "progress": op["progress"] if not terminal else {k: op["progress"][k] for k in
                                                          ("stage", "done", "total", "unit", "progress_seq")},
        "controls": {"paused": row["paused"], "step_budget": row["step_budget"], "speed": row["speed"],
                     "cancel_requested": row["cancel_requested"],
                     "commands": [c.get("command") for c in (row["control_log"] or [])]},
        "counters": row.get("metrics") or {},
        "counters_note": ("cheap per-attempt counters keyed by fencing generation; unknown values are null with a "
                          "reason; pre-upgrade runs recorded none"),
        "manifest": manifest_check(art_root, row),
        "suspension": op["suspension"],
        "error": row["error"],
        "stream_engine": row.get("engine"),
        "storage": storage,
        "limitations": [*((STREAM_NOTE, STREAM_REMAINING) if row.get("engine_format") else (REMAINING_COSTS,)),
                        "Diagnostic export from persisted operational facts only; it does not re-verify the source "
                        "or re-derive deliveries and is not terminal assurance."],
        "next_diagnostic": next_diagnostic(row, op),
    }


def render_markdown(r: dict[str, Any]) -> str:
    ident, cov, tm, a = r["identity"], r["coverage"], r["timing"], r["assurance"]
    title = "Diagnostic snapshot (incomplete)" if r["snapshot"] else "Terminal diagnostic"
    lines = [
        f"# Market replay diagnostic — {title}",
        "",
        f"**{r['report_kind']}** · replay `{r['replay_id']}`"
        + (f" · evaluation `{r['evaluation_id']}`" if r.get("evaluation_id") else "")
        + (f" · captured {r['captured_at']}" if r["captured_at"] else ""),
        f"**Status:** {r['status'].upper()} · phase **{r['phase'] or '—'}** · health **{r['health']['state']}** · "
        f"assurance **{str(a.get('state')).upper()}**",
        "",
        f"> {r['run_type']}. A diagnostic export is not terminal assurance.",
        "",
        "## Identity",
        f"- Source: {ident['source_kind']} `{ident['source_id']}` · status {ident['source_status']} · "
        f"verified {ident['verified']}",
        f"- Feed: {ident['feed_content_identity']} · total events {ident['total_events']} · availability "
        f"{ident['availability_basis']}",
        f"- Engine: code {r['engine']['code_version'] or 'unknown'} · lifecycle v{r['lifecycle_version']}",
        f"- Worker host: {_host_line(r['engine']['environment'])}",
        "",
        "## Progress",
        f"- Committed cursor: {cov['committed_cursor']:,}/{cov['total_events'] if isinstance(cov['total_events'], str) else format(cov['total_events'], ',')}"
        f" · information time {cov['information_time'] or '—'}",
        f"- Health: {r['health']['detail']}",
        f"- Assurance: {a.get('state')} — {a.get('detail') or a.get('scope') or ''}",
        f"- Wall since launch: {tm['wall_seconds_since_launch']:.1f} s · active (measured) "
        f"{tm['active_seconds_total']:.1f} s · declared waits {tm['waiting_seconds_total']:.1f} s"
        + ("" if tm["active_complete"] else
           f" · INCOMPLETE: {tm['unmeasured_spans']} unmeasured span(s), active time unknown for them"),
        "- Timing: wall = start-to-end clock time; waiting = declared waits (queue, pacing); active = compute "
        "time minus declared waits; paused time lies in no span",
    ]
    for p in tm["phases"]:
        lines.append(f"  - {p['label']}: active {p['active_seconds']:.1f} s · waiting {p['waiting_seconds']:.1f} s · "
                     f"wall {p['wall_seconds']:.1f} s · {p['spans']} span(s)"
                     f"{' · ' + str(p['interrupted_spans']) + ' interrupted' if p['interrupted_spans'] else ''}"
                     f"{' · ' + str(p['unmeasured_spans']) + ' unmeasured' if p['unmeasured_spans'] else ''}"
                     f"{' · CURRENT' if p['state'] == 'current' else ''}")
    pr = r["progress"]
    if pr.get("stage") or pr.get("done") is not None:
        lines.append(f"- Last milestone: {pr.get('stage') or '—'} {pr.get('done')}/{pr.get('total')} {pr.get('unit') or ''}"
                     + (f" at {pr['last_progress_at']}" if pr.get("last_progress_at") else ""))
    att = r["attempts"]
    lines.append(f"- Attempts {att['attempt']}/{att['max_attempts']} · fencing generation {att['generation']}")
    for x in att["recovery_log"]:
        lines.append(f"  - recovery: attempt {x.get('attempt')} · {x.get('event')} — {x.get('detail')}")
    for x in att["diagnostic_log"]:
        lines.append(f"  - {x.get('event')}: {x.get('detail')}")
    c = r["controls"]
    lines.append(f"- Controls: paused={c['paused']} step_budget={c['step_budget']} speed={c['speed']} "
                 f"cancel_requested={c['cancel_requested']}")
    m = r["manifest"]
    lines += ["", "## Terminal manifest"]
    if not m["claimed"]:
        lines.append(f"- {m['detail']}")
    else:
        lines.append(f"- Directory {m['artifact_dir']} · manifest file present {m['manifest_file_present']}"
                     + (f" · matches database {m.get('manifest_file_matches_database')}" if m["manifest_file_present"]
                        else ""))
        missing = [x["name"] for x in m["artifacts"]
                   if not (x["present"] and x["size_matches"] and x.get("sha256_matches") is not False)]
        lines.append(f"- Artifacts: {len(m['artifacts'])} listed · missing/size/hash mismatch: {', '.join(missing) or 'none'}")
    if r["counters"]:
        lines += ["", "## Counters (per fencing generation)"]
        for gen, cnt in sorted(r["counters"].items()):
            keys = ("events_applied", "snapshots_built", "transactions_committed", "delivery_rows_written",
                    "prefix_restore_events", "validation_deliveries_rederived", "source_verifications",
                    "output_bytes", "cpu_seconds", "max_rss_bytes")
            lines.append(f"- g{gen}: " + " · ".join(f"{k} {cnt.get(k)}" for k in keys if k in cnt))
    if r["suspension"]:
        lines += ["", "## Suspension", f"- {r['suspension'].get('reason')}",
                  f"- Historical status at upgrade: {r['suspension'].get('historical_status')}"]
    if r["error"]:
        lines += ["", "## Error", f"- {r['error']}"]
    eng, st = r.get("stream_engine"), r.get("storage")
    if eng:
        lines += ["", "## Engine", f"- {eng.get('format')} · state {eng.get('state_format')} · cache "
                  f"`{eng.get('cache_id')}` ({'reused' if eng.get('cache_reused_at_preparation') else 'built'} at "
                  f"preparation) · checkpoint policy {eng.get('checkpoint_policy')}"]
    if st:
        lines.append(f"- Storage: {st.get('ranges')} committed range(s) to cursor {st.get('ranges_to_cursor')} · "
                     f"restore points {st.get('restore_points')} · per-event delivery rows {st.get('delivery_rows')}")
    ca = r.get("current_assurance")
    if ca:
        lines += ["", "## Current assurance (linked)", f"- {ca['headline']}",
                  f"- Run validation: {ca['run_validation']} · Deep validation: {ca['deep_validation']}"
                  + (f" (latest `{ca['latest_deep_validation']}`)" if ca.get("latest_deep_validation") else "")]
        lines += [f"- WARNING: {w}" for w in ca["warnings"]]
    lines += ["", "## Limitations"] + [f"- {x}" for x in r["limitations"]]
    lines += ["", f"Next diagnostic: {r['next_diagnostic']}", "", f"_Format {r['report_format']}_", ""]
    return "\n".join(lines)
