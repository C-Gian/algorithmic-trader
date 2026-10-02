"""Shared operational job/progress contract (``algotrader.ops.v1``; operational, not a domain contract).

One small vocabulary for every long Owner-visible operation (observation replay /
evaluation and corpus preparation), even though each keeps its own table and worker.
Four things are kept separate and never folded into one string:

* **status**    - lifecycle: queued / running / paused / completed / failed / cancelled;
* **phase**     - what work is (or was last) being done;
* **health**    - is the operation observably progressing, knowingly waiting, alive without
                  observed progress, unresponsive (awaiting recovery), actually restoring, ...;
* **assurance** - not checked / incomplete / passed / failed, with validator, version and scope.

Heartbeat (supervisor liveness) is not progress (compute milestones). Health is derived
at read time from persisted facts only; it never infers progress from CPU usage.
"""

from __future__ import annotations

import os
import platform
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

OPS_CONTRACT = "algotrader.ops.v1"

# Operation lifecycle version of an observation replay row.
LIFECYCLE_LEGACY = 1  # WP-007/WP-008: verified config + total fixed inside the launch request
LIFECYCLE_R1A = 2  # R1A: durable launch envelope first; worker-owned preparation persists the config


class Status(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


TERMINAL = frozenset({Status.COMPLETED, Status.FAILED, Status.CANCELLED})


class Phase(StrEnum):
    QUEUED = "QUEUED"
    PREPARING_SOURCE = "PREPARING_SOURCE"
    DOWNLOADING = "DOWNLOADING"  # corpus only
    VERIFYING_SOURCE = "VERIFYING_SOURCE"
    BUILDING_FEED = "BUILDING_FEED"
    INITIALIZING = "INITIALIZING"
    REPLAYING = "REPLAYING"
    FINALIZING = "FINALIZING"
    VALIDATING = "VALIDATING"
    GENERATING_REPORT = "GENERATING_REPORT"
    BINDING = "BINDING"  # corpus only: fenced binding of the verified dataset


PHASE_LABEL: dict[str, str] = {
    "QUEUED": "Queued",
    "PREPARING_SOURCE": "Preparing source",
    "DOWNLOADING": "Downloading",
    "VERIFYING_SOURCE": "Verifying source",
    "BUILDING_FEED": "Building feed",
    "INITIALIZING": "Initializing",
    "REPLAYING": "Replaying",
    "FINALIZING": "Finalizing",
    "VALIDATING": "Validating",
    "GENERATING_REPORT": "Generating report",
    "BINDING": "Binding dataset",
}

OBSERVATION_PHASES = ("QUEUED", "PREPARING_SOURCE", "VERIFYING_SOURCE", "BUILDING_FEED", "INITIALIZING",
                      "REPLAYING", "FINALIZING", "VALIDATING", "GENERATING_REPORT")
CORPUS_PHASES = ("QUEUED", "PREPARING_SOURCE", "VERIFYING_SOURCE", "DOWNLOADING", "BINDING")


class Health(StrEnum):
    PROGRESSING = "progressing"
    WAITING = "waiting"  # known waiting: queued, paused, pacing, rate limit ...
    ALIVE_NO_PROGRESS = "alive_no_progress"  # supervisor alive, no compute milestone within the phase limit
    COMPUTE_LOST = "compute_lost"  # supervisor saw the compute process end; awaiting recovery
    UNRESPONSIVE = "unresponsive"  # no supervisor heartbeat: lease expired, awaiting recovery
    RECOVERING = "recovering"  # a new fenced attempt is actually restoring committed state
    SUSPENDED = "suspended"  # operational suspension (legacy pre-upgrade run); read-only
    FINISHED = "finished"  # terminal
    DISCONNECTED = "disconnected"  # the database cannot be reached (API level)


HEALTH_LABEL: dict[str, str] = {
    "progressing": "Progressing",
    "waiting": "Waiting",
    "alive_no_progress": "Alive · no progress observed",
    "compute_lost": "Compute process lost · awaiting recovery",
    "unresponsive": "Unresponsive · awaiting recovery",
    "recovering": "Recovering",
    "suspended": "Suspended",
    "finished": "Finished",
    "disconnected": "Disconnected",
}


class Assurance(StrEnum):
    NOT_CHECKED = "not_checked"
    INCOMPLETE = "incomplete"
    PASSED = "passed"
    FAILED = "failed"


# Default inactivity limits (seconds without a compute milestone) before a running phase with a live
# supervisor is shown as "alive, no progress observed". Engineering defaults, measured later (R1C).
DEFAULT_STALL_LIMIT = 30.0
STALL_LIMITS: dict[str, float] = {
    "PREPARING_SOURCE": 30.0, "VERIFYING_SOURCE": 30.0, "BUILDING_FEED": 60.0, "INITIALIZING": 60.0,
    "REPLAYING": 30.0, "FINALIZING": 60.0, "VALIDATING": 30.0, "GENERATING_REPORT": 60.0,
    "DOWNLOADING": 120.0, "BINDING": 30.0,
}


def utcnow() -> datetime:
    return datetime.now(UTC)


def iso(v: datetime | None) -> str | None:
    return v.isoformat() if v is not None else None


def parse_iso(v: Any) -> datetime | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v
    return datetime.fromisoformat(str(v))


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


def derive_health(*, status: str, phase: str | None, lease_expired: bool, last_progress_at: datetime | None,
                  heartbeat_at: datetime | None, progress: dict[str, Any] | None, supervisor: dict[str, Any] | None,
                  generation: int, now: datetime, suspended: bool = False,
                  paused: bool = False) -> tuple[Health, str]:
    """Truthful operation health from persisted facts (see module docstring)."""
    progress = progress or {}
    supervisor = supervisor or {}
    if suspended:
        return Health.SUSPENDED, "operationally suspended (pre-upgrade run preserved read-only); no worker claims it"
    if status in TERMINAL:
        return Health.FINISHED, f"operation {status}"
    if status == Status.QUEUED:
        return Health.WAITING, "queued: waiting for a worker to claim it"
    if status == Status.PAUSED:
        return Health.WAITING, "paused at a committed boundary; no compute is running"
    # running
    exit_info = supervisor.get("compute_exit")
    if lease_expired:
        if exit_info and exit_info.get("generation") == generation:
            return Health.COMPUTE_LOST, (f"compute process ended unexpectedly (exit {exit_info.get('exitcode')}) "
                                         f"at {exit_info.get('at')}; awaiting a new fenced attempt")
        hb = f"last supervisor heartbeat {iso(heartbeat_at)}" if heartbeat_at else "no supervisor heartbeat"
        return Health.UNRESPONSIVE, f"worker unresponsive ({hb}); lease expired, awaiting recovery"
    if progress.get("restoring"):
        return Health.RECOVERING, (f"attempt {progress.get('restoring_attempt', '?')} restoring committed state "
                                   f"under fencing generation {generation}")
    if progress.get("waiting"):
        return Health.WAITING, str(progress["waiting"])
    limit = float(progress.get("stall_limit") or STALL_LIMITS.get(phase or "", DEFAULT_STALL_LIMIT))
    if last_progress_at is None:
        return Health.ALIVE_NO_PROGRESS, "supervisor alive; no compute milestone recorded yet"
    age = (now - last_progress_at).total_seconds()
    if age > limit:
        return Health.ALIVE_NO_PROGRESS, (f"supervisor alive, but no compute milestone for {age:.0f}s "
                                          f"(phase limit {limit:.0f}s)")
    return Health.PROGRESSING, f"last compute milestone {age:.1f}s ago"


# ---------------------------------------------------------------------------
# Phase timeline
# ---------------------------------------------------------------------------


TIMING_DEFINITIONS = {
    "wall_seconds": "wall-clock length of the span (start to end, database clock)",
    "waiting_seconds": ("declared intentional waits inside the span: queue wait, configured replay pacing sleeps; "
                        "paused time is not inside any span"),
    "active_seconds": ("compute-process monotonic time of the span minus its declared waits; null when the span was "
                       "interrupted and could not be measured (never reported as zero)"),
}


def closed_entry(phase: str, generation: int, attempt: int, started_at: datetime | None, ended_at: datetime,
                 active_seconds: float | None, *, waiting: bool = False, interrupted: bool = False,
                 note: str | None = None, waiting_seconds: float | None = None) -> dict[str, Any]:
    """One closed phase span. ``active_seconds`` None means unmeasured (e.g. interrupted), not zero."""
    wall = (ended_at - started_at).total_seconds() if started_at else None
    if waiting:  # a declared waiting span (queue): no compute by definition
        active_seconds, waiting_seconds = 0.0, wall
    measured = active_seconds is not None
    return {"phase": phase, "generation": generation, "attempt": attempt, "started_at": iso(started_at),
            "ended_at": iso(ended_at), "wall_seconds": wall,
            "active_seconds": active_seconds,
            "waiting_seconds": waiting_seconds if measured else None,
            "measured": measured, "waiting": waiting, "interrupted": interrupted, "note": note}


def _measured(e: dict[str, Any]) -> bool:
    # revision of R1A spans before this correction: interrupted spans carried active None; waiting spans 0.0
    return e.get("measured", e.get("active_seconds") is not None)


def timeline(history: list[dict[str, Any]], current_phase: str | None, current_started: datetime | None,
             running: bool, now: datetime, order: tuple[str, ...],
             current_measure: dict[str, Any] | None = None) -> dict[str, Any]:
    """Per-phase totals with explicit wall / waiting / active meanings (see ``TIMING_DEFINITIONS``).

    Unmeasured spans are counted, never summed as zero; the open span's active/waiting time comes only from
    the compute process's last milestone (``current_measure``) and is otherwise unknown.
    """
    totals: dict[str, dict[str, Any]] = {}
    for e in history:
        t = totals.setdefault(e["phase"], {"active_seconds": 0.0, "waiting_seconds": 0.0, "wall_seconds": 0.0,
                                           "spans": 0, "interrupted_spans": 0, "unmeasured_spans": 0})
        t["spans"] += 1
        t["wall_seconds"] += float(e.get("wall_seconds") or 0.0)
        if e.get("interrupted"):
            t["interrupted_spans"] += 1
        if _measured(e):
            t["active_seconds"] += float(e.get("active_seconds") or 0.0)
            t["waiting_seconds"] += float(e.get("waiting_seconds") or 0.0)
        else:
            t["unmeasured_spans"] += 1
    current = None
    open_wall = 0.0
    open_active: float | None = None
    open_waiting: float | None = None
    if current_phase:
        if running and current_started is not None:
            open_wall = max((now - current_started).total_seconds(), 0.0)
        m = current_measure or {}
        if running and m.get("phase") == current_phase and m.get("phase_active_seconds") is not None:
            open_active = float(m["phase_active_seconds"])
            open_waiting = float(m.get("phase_waiting_seconds") or 0.0)
        current = {"phase": current_phase, "label": PHASE_LABEL.get(current_phase, current_phase),
                   "started_at": iso(current_started), "wall_seconds": open_wall if running else None,
                   "active_seconds": open_active, "waiting_seconds": open_waiting,
                   "active_basis": ("as of the last compute milestone" if open_active is not None
                                    else "not measured yet in this span")}
    phases = []
    seen = set(totals) | ({current_phase} if current_phase else set())
    for p in [*order, *sorted(seen - set(order))]:
        t = totals.get(p) or {"active_seconds": 0.0, "waiting_seconds": 0.0, "wall_seconds": 0.0, "spans": 0,
                              "interrupted_spans": 0, "unmeasured_spans": 0}
        is_current = p == current_phase
        state = "current" if is_current else ("done" if t["spans"] else "pending")
        unmeasured = t["unmeasured_spans"] + (1 if is_current and running and open_active is None else 0)
        phases.append({"phase": p, "label": PHASE_LABEL.get(p, p), "state": state,
                       "active_seconds": t["active_seconds"] + (open_active or 0.0 if is_current else 0.0),
                       "waiting_seconds": t["waiting_seconds"] + (open_waiting or 0.0 if is_current else 0.0),
                       "wall_seconds": t["wall_seconds"] + (open_wall if is_current else 0.0),
                       "spans": t["spans"], "interrupted_spans": t["interrupted_spans"],
                       "unmeasured_spans": unmeasured, "active_complete": unmeasured == 0})
    measured = [e for e in history if _measured(e)]
    unmeasured_total = len(history) - len(measured) + (1 if current and running and open_active is None else 0)
    return {
        "current": current, "phases": phases,
        "active_seconds_total": sum(float(e.get("active_seconds") or 0.0) for e in measured) + (open_active or 0.0),
        "waiting_seconds_total": sum(float(e.get("waiting_seconds") or 0.0) for e in measured) + (open_waiting or 0.0),
        "unmeasured_spans": unmeasured_total,
        "active_complete": unmeasured_total == 0,
        "definitions": TIMING_DEFINITIONS,
    }


# ---------------------------------------------------------------------------
# Current-phase ETA (never a whole-job ETA)
# ---------------------------------------------------------------------------

ETA_MIN_UNITS = 5
ETA_MIN_SECONDS = 1.0


def phase_eta(done: int | None, total: int | None, base_done: int | None, window_seconds: float | None,
              unit: str, *, basis: str = "active work in the current phase/substage") -> tuple[float | None, str]:
    """ETA for the remaining units of the CURRENT comparable window only (never a whole-job estimate).

    The caller must start the window (``base_done`` at ``window_seconds`` = 0) at the beginning of a comparable
    span - the current phase/substage/unit/total, generation and pacing - so that preparation, pauses or other
    units can never be counted as this window's throughput. Too little observation -> unknown.
    """
    if total is None or done is None:
        return None, "unknown: the current phase has no known total"
    if base_done is None or window_seconds is None:
        return None, "unknown: no throughput observed yet in this window"
    moved = done - base_done
    if moved < ETA_MIN_UNITS or window_seconds < ETA_MIN_SECONDS:
        return None, "unknown: not enough comparable progress observed yet"
    rate = moved / window_seconds
    return (total - done) / rate, (f"current window only: {moved} {unit} in {window_seconds:.1f}s of {basis} "
                                   f"({rate:.1f} {unit}/s); later phases are not included")


# ---------------------------------------------------------------------------
# Cooperative progress reporting
# ---------------------------------------------------------------------------


class OperationCancelled(Exception):
    """Raised from a progress hook at a safe boundary when cancellation was requested."""


ProgressHook = Callable[[str, int, int | None, str], None]


def no_progress(stage: str, done: int, total: int | None, unit: str) -> None:  # noqa: ARG001
    return None


# ---------------------------------------------------------------------------
# Environment / process facts (cheap; unsupported values are explicit)
# ---------------------------------------------------------------------------


def environment() -> dict[str, Any]:
    return {
        "python": sys.version.split()[0],
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "logical_cpus": os.cpu_count(),
        "code_version": os.environ.get("ALGOTRADER_CODE_VERSION") or None,
    }


def process_metrics() -> dict[str, Any]:
    out: dict[str, Any] = {"cpu_seconds": round(time.process_time(), 3)}
    try:
        import resource  # POSIX only

        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        out["max_rss_bytes"] = int(rss) * (1 if sys.platform == "darwin" else 1024)
    except (ImportError, OSError):
        out["max_rss_bytes"] = None
        out["max_rss_unknown_reason"] = "resource.getrusage unavailable on this platform"
    return out
