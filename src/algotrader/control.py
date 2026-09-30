"""Durable replay-control commands: create, pause, resume, step, speed, cancel.

Commands only change persisted control state in PostgreSQL; the worker that
owns (or next claims) the run acts on it. Nothing here touches the semantic
journal, so control can never change trader decisions. Each accepted command
is appended to the run's operational ``control_log``.

Semantics:
  PAUSE   the worker finishes the step in progress, then parks the run at the
          committed checkpoint (status ``paused``, lease released).
  RESUME  clears the pause; the run is queued for a worker again.
  STEP    while paused, grants exactly one more input step; the worker commits
          it normally and parks again.
  SPEED   changes pacing (bars/s, 0 = max) of any non-terminal run.
  CANCEL  as before; also valid while paused.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from .contracts import TERMINAL_STATUSES, RunConfig
from .synthetic import build_fixture

TERMINAL = {s.value for s in TERMINAL_STATUSES}


class RunNotFound(LookupError):
    pass


class ControlRejected(Exception):
    """The command is not valid in the run's current state."""


def _entry(command: str, **detail: Any) -> Jsonb:
    return Jsonb([{"at": datetime.now(UTC).isoformat(), "command": command, **detail}])


def new_run_id() -> str:
    return f"run-{datetime.now(UTC):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:6]}"


def create_run(
    conn: psycopg.Connection,
    config: RunConfig,
    speed: float = 4.0,
    paused: bool = False,
    run_id: str | None = None,
) -> str:
    run_id = run_id or new_run_id()
    total = build_fixture(config.fixture_id, config.seed).total_steps
    with conn.transaction():
        conn.execute(
            """
            INSERT INTO runs (run_id, status, config, total_steps, speed, paused, control_log)
            VALUES (%s, 'queued', %s, %s, %s, %s, %s)
            """,
            (run_id, Jsonb(config.model_dump(mode="json")), total, speed, paused,
             _entry("start", speed=speed, paused=paused)),
        )
    return run_id


def _lock(conn: psycopg.Connection, run_id: str) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT r.status, r.paused, r.step_budget, r.cancel_requested, r.total_steps,
               coalesce(c.next_step, 0) AS steps_done
        FROM runs r LEFT JOIN run_checkpoints c USING (run_id)
        WHERE r.run_id = %s FOR UPDATE OF r
        """,
        (run_id,),
    ).fetchone()
    if row is None:
        raise RunNotFound(run_id)
    if row["status"] in TERMINAL:
        raise ControlRejected(f"run already {row['status']}")
    return row


def pause(conn: psycopg.Connection, run_id: str) -> None:
    with conn.transaction():
        row = _lock(conn, run_id)
        if row["cancel_requested"]:
            raise ControlRejected("cancellation already requested")
        if row["paused"]:
            return  # idempotent
        conn.execute(
            "UPDATE runs SET paused = true, step_budget = 0, control_log = control_log || %s WHERE run_id = %s",
            (_entry("pause", at_step=row["steps_done"]), run_id),
        )


def resume(conn: psycopg.Connection, run_id: str) -> None:
    with conn.transaction():
        row = _lock(conn, run_id)
        if not row["paused"]:
            raise ControlRejected("run is not paused")
        conn.execute(
            """
            UPDATE runs SET paused = false, step_budget = 0,
                status = CASE WHEN status = 'paused' THEN 'queued' ELSE status END,
                control_log = control_log || %s
            WHERE run_id = %s
            """,
            (_entry("resume", at_step=row["steps_done"]), run_id),
        )


def step(conn: psycopg.Connection, run_id: str) -> None:
    with conn.transaction():
        row = _lock(conn, run_id)
        if row["cancel_requested"]:
            raise ControlRejected("cancellation already requested")
        if not row["paused"]:
            raise ControlRejected("STEP is only valid while paused")
        if row["steps_done"] + row["step_budget"] >= row["total_steps"]:
            raise ControlRejected("no input bars left to step")
        conn.execute(
            "UPDATE runs SET step_budget = step_budget + 1, control_log = control_log || %s WHERE run_id = %s",
            (_entry("step", at_step=row["steps_done"]), run_id),
        )


def set_speed(conn: psycopg.Connection, run_id: str, speed: float) -> None:
    if not 0 <= speed <= 1000:
        raise ControlRejected("speed must be between 0 (max) and 1000 bars/s")
    with conn.transaction():
        row = _lock(conn, run_id)
        # A speed change starts a new observed-throughput window for the ETA.
        conn.execute(
            """
            UPDATE runs SET speed = %s, throughput_since = now(), throughput_base_step = %s,
                control_log = control_log || %s
            WHERE run_id = %s
            """,
            (speed, row["steps_done"], _entry("speed", speed=speed, at_step=row["steps_done"]), run_id),
        )


def cancel(conn: psycopg.Connection, run_id: str) -> None:
    with conn.transaction():
        row = _lock(conn, run_id)
        if row["cancel_requested"]:
            return
        conn.execute(
            "UPDATE runs SET cancel_requested = true, control_log = control_log || %s WHERE run_id = %s",
            (_entry("cancel", at_step=row["steps_done"]), run_id),
        )
