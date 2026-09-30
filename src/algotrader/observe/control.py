"""Durable observation-replay commands: create, pause, resume, step, speed, cancel.

Commands only change persisted control state; the observation worker that owns
(or next claims) the replay acts on it. Semantics mirror the synthetic shell but
the unit is one **causal feed delivery** (not a bar):

  PAUSE   finish the delivery in progress, then park at the committed cursor.
  RESUME  clear the pause; the replay is queued for a worker again.
  STEP    while paused, grant exactly one more feed delivery.
  SPEED   pacing in events/s (0 = max). Operational only; never changes state.
  CANCEL  durable; also valid while paused.
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
from .contracts import (
    CLOCK_POLICY,
    LABELS,
    OBSERVE_SCHEMA_VERSION,
    TERMINAL_STATUSES,
    ObservationReplayConfig,
    SourceKind,
)
from .sources import LoadedSource, feed_identity, load_source

TERMINAL = {s.value for s in TERMINAL_STATUSES}
MAX_SPEED = 10000.0


class ReplayNotFound(LookupError):
    pass


class ControlRejected(Exception):
    """The command is not valid in the replay's current state."""


def _entry(command: str, **detail: Any) -> Jsonb:
    return Jsonb([{"at": datetime.now(UTC).isoformat(), "command": command, **detail}])


def new_replay_id() -> str:
    return f"obs-{datetime.now(UTC):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:6]}"


def code_version() -> str | None:
    import os
    import subprocess

    env = os.environ.get("ALGOTRADER_CODE_VERSION")
    if env:
        return env
    try:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5,
                             check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, timeout=5).stdout
        return sha + ("-dirty" if dirty.strip() else "")
    except (OSError, subprocess.SubprocessError):
        return None


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
                  speed: float = 20.0, paused: bool = False, replay_id: str | None = None) -> str:
    """Verify the source and build its feed *before* anything is persisted; raises SourceRejected."""
    if not 0 <= speed <= MAX_SPEED:
        raise ControlRejected(f"speed must be between 0 (max) and {MAX_SPEED:g} events/s")
    replay_id = replay_id or new_replay_id()
    source = load_source(data_root, kind, source_id)
    config = build_config(replay_id, source)
    with conn.transaction():
        conn.execute(
            """
            INSERT INTO observation_replays
                (replay_id, status, source_kind, source_id, config, total_events, speed, paused, control_log)
            VALUES (%s, 'queued', %s, %s, %s, %s, %s, %s, %s)
            """,
            (replay_id, config.source.kind.value, source_id, Jsonb(json.loads(config.model_dump_json())),
             config.feed.event_count, speed, paused, _entry("start", speed=speed, paused=paused)),
        )
    return replay_id


def _lock(conn: psycopg.Connection, replay_id: str) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT r.status, r.paused, r.step_budget, r.cancel_requested, r.total_events,
               coalesce(c.cursor, 0) AS cursor
        FROM observation_replays r LEFT JOIN observation_checkpoints c USING (replay_id)
        WHERE r.replay_id = %s FOR UPDATE OF r
        """,
        (replay_id,),
    ).fetchone()
    if row is None:
        raise ReplayNotFound(replay_id)
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
