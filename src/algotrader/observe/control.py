"""Durable observation-replay commands: launch, pause, resume, step, speed, cancel.

Commands only change persisted control state; the observation worker that owns
(or next claims) the replay acts on it. Semantics mirror the synthetic shell but
the unit is one **causal feed delivery** (not a bar):

  LAUNCH  persist a lightweight launch envelope (no hashing / parsing / feed build);
          the worker-owned preparation verifies the source and persists the config.
  PAUSE   finish the delivery in progress, then park at the committed cursor
          (requested during preparation: the replay parks at cursor 0 once prepared).
  RESUME  clear the pause; the replay is queued for a worker again.
  STEP    while paused, grant exactly one more feed delivery (needs a prepared total).
  SPEED   pacing in events/s (0 = max). Operational only; never changes state.
  CANCEL  durable; valid in every non-terminal phase (applied at the next safe boundary).

Pre-upgrade (lifecycle v1) runs that were suspended at migration are read-only here.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from ..feed.ordering import default_freshness
from ..ops import LIFECYCLE_R2
from .contracts import (
    CLOCK_POLICY,
    LABELS,
    OBSERVE_SCHEMA_VERSION,
    TERMINAL_STATUSES,
    ObservationLaunch,
    ObservationReplayConfig,
    SourceKind,
)
from .sources import LoadedSource, feed_identity, locate_source

TERMINAL = {s.value for s in TERMINAL_STATUSES}
MAX_SPEED = 10000.0
PREPARATION_PHASES = frozenset({"QUEUED", "PREPARING_SOURCE", "VERIFYING_SOURCE", "BUILDING_FEED", "INITIALIZING"})
POST_REPLAY_PHASES = frozenset({"FINALIZING", "VALIDATING", "GENERATING_REPORT"})


class ReplayNotFound(LookupError):
    pass


class ControlRejected(Exception):
    """The command is not valid in the replay's current state."""


def _entry(command: str, **detail: Any) -> Jsonb:
    return Jsonb([{"at": datetime.now(UTC).isoformat(), "command": command, **detail}])


def new_replay_id() -> str:
    return f"obs-{datetime.now(UTC):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:6]}"


def code_version() -> str | None:
    from .. import version

    return version.code_version()


def build_config(replay_id: str, source: LoadedSource) -> ObservationReplayConfig:
    return ObservationReplayConfig(
        schema_version=OBSERVE_SCHEMA_VERSION,
        replay_id=replay_id,
        source=source.summary,
        verification=source.verification,
        feed=feed_identity(source.feed),
        availability_policy=source.feed.manifest.availability_policy,
        availability_label=source.availability_label,
        # Named inspection/development policy (not a professional-trader threshold).
        freshness_policy=default_freshness(),
        clock_policy=CLOCK_POLICY,
        code_version=code_version(),
        labels=LABELS,
    )


def create_replay(conn: psycopg.Connection, data_root: Path, kind: SourceKind | str, source_id: str,
                  speed: float = 20.0, paused: bool = False, replay_id: str | None = None,
                  evaluation_id: str | None = None, expected_manifest_sha256: str | None = None,
                  run_type: str = "observation") -> str:
    """Durable launch (target <=1 s): validate cheap fields and local existence, persist the envelope.

    No verification, hashing, parsing or feed construction happens here; those are worker-owned
    phases with progress and cancellation. Source/config/feed identity and the total event count stay
    PENDING (NULL) until the worker has genuinely prepared them. Raises SourceRejected / ControlRejected.
    """
    if not 0 <= speed <= MAX_SPEED:
        raise ControlRejected(f"speed must be between 0 (max) and {MAX_SPEED:g} events/s")
    kind = SourceKind(kind)
    if run_type not in ("observation", "adviser_evaluation"):
        raise ControlRejected(f"unknown run type {run_type!r}")
    if run_type == "adviser_evaluation" and kind != SourceKind.PACK:
        raise ControlRejected("an adviser evaluation runs on a prepared evaluation pack")
    locate_source(data_root, kind, source_id)  # path existence only
    replay_id = replay_id or new_replay_id()
    launch = ObservationLaunch(
        schema_version=OBSERVE_SCHEMA_VERSION, replay_id=replay_id, source_kind=kind, source_id=source_id,
        requested_at=datetime.now(UTC), speed=speed, paused=paused, evaluation_id=evaluation_id,
        expected_manifest_sha256=expected_manifest_sha256, code_version=code_version(), run_type=run_type,
    )
    with conn.transaction():
        conn.execute(
            """
            INSERT INTO observation_replays
                (replay_id, status, source_kind, source_id, config, total_events, speed, paused, control_log,
                 lifecycle_version, launch, phase, progress)
            VALUES (%s, 'queued', %s, %s, NULL, NULL, %s, %s, %s, %s, %s, NULL, %s)
            """,
            (replay_id, kind.value, source_id, speed, paused, _entry("start", speed=speed, paused=paused),
             LIFECYCLE_R2, Jsonb(json.loads(launch.model_dump_json())),
             Jsonb({"waiting": "queued: waiting for an observation worker to prepare the source"})),
        )
    return replay_id


def _lock(conn: psycopg.Connection, replay_id: str) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT r.status, r.paused, r.step_budget, r.cancel_requested, r.total_events, r.suspended_at, r.phase,
               coalesce(c.cursor, 0) AS cursor
        FROM observation_replays r LEFT JOIN observation_checkpoints c USING (replay_id)
        WHERE r.replay_id = %s FOR UPDATE OF r
        """,
        (replay_id,),
    ).fetchone()
    if row is None:
        raise ReplayNotFound(replay_id)
    if row["suspended_at"] is not None:
        raise ControlRejected("this pre-upgrade replay is operationally suspended and preserved read-only; "
                              "export its diagnostic report instead")
    if row["status"] in TERMINAL:
        raise ControlRejected(f"replay already {row['status']}")
    return row


def pause(conn: psycopg.Connection, replay_id: str) -> None:
    with conn.transaction():
        row = _lock(conn, replay_id)
        if row["cancel_requested"]:
            raise ControlRejected("cancellation already requested")
        if row["paused"]:
            return
        if row["status"] == "running" and row["phase"] in POST_REPLAY_PHASES:
            raise ControlRejected(f"PAUSE is not applicable during {row['phase']} (the replay cursor is complete); "
                                  "CANCEL stops at the next safe boundary")
        conn.execute("UPDATE observation_replays SET paused = true, step_budget = 0, control_log = control_log || %s "
                     "WHERE replay_id = %s", (_entry("pause", at_cursor=row["cursor"]), replay_id))


def resume(conn: psycopg.Connection, replay_id: str) -> None:
    with conn.transaction():
        row = _lock(conn, replay_id)
        if not row["paused"]:
            raise ControlRejected("replay is not paused")
        conn.execute(
            """
            UPDATE observation_replays SET paused = false, step_budget = 0,
                status = CASE WHEN status = 'paused' THEN 'queued' ELSE status END,
                control_log = control_log || %s
            WHERE replay_id = %s
            """,
            (_entry("resume", at_cursor=row["cursor"]), replay_id),
        )


def step(conn: psycopg.Connection, replay_id: str) -> None:
    with conn.transaction():
        row = _lock(conn, replay_id)
        if row["cancel_requested"]:
            raise ControlRejected("cancellation already requested")
        if not row["paused"]:
            raise ControlRejected("STEP is only valid while paused")
        if row["total_events"] is None:
            raise ControlRejected("STEP is available once source preparation has fixed the feed (total PENDING)")
        if row["phase"] in POST_REPLAY_PHASES:
            raise ControlRejected(f"STEP is not applicable during {row['phase']}")
        if row["cursor"] + row["step_budget"] >= row["total_events"]:
            raise ControlRejected("no feed deliveries left to step")
        conn.execute("UPDATE observation_replays SET step_budget = step_budget + 1, control_log = control_log || %s "
                     "WHERE replay_id = %s", (_entry("step", at_cursor=row["cursor"]), replay_id))


def set_speed(conn: psycopg.Connection, replay_id: str, speed: float) -> None:
    if not 0 <= speed <= MAX_SPEED:
        raise ControlRejected(f"speed must be between 0 (max) and {MAX_SPEED:g} events/s")
    with conn.transaction():
        row = _lock(conn, replay_id)
        conn.execute(
            """
            UPDATE observation_replays SET speed = %s, throughput_since = now(), throughput_base = %s,
                control_log = control_log || %s
            WHERE replay_id = %s
            """,
            (speed, row["cursor"], _entry("speed", speed=speed, at_cursor=row["cursor"]), replay_id),
        )


def cancel(conn: psycopg.Connection, replay_id: str) -> None:
    with conn.transaction():
        row = _lock(conn, replay_id)
        if row["cancel_requested"]:
            return
        conn.execute("UPDATE observation_replays SET cancel_requested = true, control_log = control_log || %s "
                     "WHERE replay_id = %s", (_entry("cancel", at_cursor=row["cursor"]), replay_id))
