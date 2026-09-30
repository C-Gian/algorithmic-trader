"""Durable recorder job: PostgreSQL-backed sessions owned by a recorder worker process.

The browser never owns a recording. The API only inserts a queued session or
sets ``stop_requested``; a ``recorder-worker`` process claims queued sessions
under a lease, records until stopped / max duration, finalizes the immutable
session directory and stores the manifest. A session whose worker died (lease
expired) is recovered by the next worker: torn tail truncated, finalized as
PARTIAL, never resumed.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import socket
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from .. import db
from .contracts import Endpoints, SessionConfig
from .journal import SessionWriter, finalize, is_finalized, load_manifest, recordings_dir, recover
from .okx_live import DEFAULT_ENDPOINTS, Recorder, SystemClock, make_config, validate_endpoints

log = logging.getLogger("algotrader.recorder")
TERMINAL = ("clean", "partial", "failed", "cancelled")


class RecorderControlError(Exception):
    pass


def configured_endpoints() -> Endpoints:
    return Endpoints(
        ws_public_url=os.environ.get("ALGOTRADER_OKX_WS_PUBLIC_URL", DEFAULT_ENDPOINTS.ws_public_url),
        ws_business_url=os.environ.get("ALGOTRADER_OKX_WS_BUSINESS_URL", DEFAULT_ENDPOINTS.ws_business_url),
        rest_base_url=os.environ.get("ALGOTRADER_OKX_BASE_URL", DEFAULT_ENDPOINTS.rest_base_url),
    )


def new_session_id() -> str:
    return f"rec-{datetime.now(UTC):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:6]}"


def create_session(conn: psycopg.Connection, max_duration: timedelta, endpoints: Endpoints | None = None,
                   session_id: str | None = None, **overrides: Any) -> str:
    endpoints = endpoints or configured_endpoints()
    validate_endpoints(endpoints)
    config = make_config(session_id or new_session_id(), endpoints=endpoints, max_duration=max_duration, **overrides)
    with conn.transaction():
        conn.execute("INSERT INTO recorder_sessions (session_id, status, config) VALUES (%s, 'queued', %s)",
                     (config.session_id, Jsonb(json.loads(config.model_dump_json()))))
    return config.session_id


def stop_session(conn: psycopg.Connection, session_id: str) -> None:
    with conn.transaction():
        row = conn.execute("SELECT status FROM recorder_sessions WHERE session_id = %s FOR UPDATE",
                           (session_id,)).fetchone()
        if row is None:
            raise LookupError(session_id)
        if row["status"] in TERMINAL:
            raise RecorderControlError(f"session already {row['status']}")
        if row["status"] == "queued":  # never started: nothing recorded
            conn.execute("UPDATE recorder_sessions SET status = 'cancelled', stop_requested = true, "
                         "finished_at = now() WHERE session_id = %s", (session_id,))
        else:
            conn.execute("UPDATE recorder_sessions SET stop_requested = true WHERE session_id = %s", (session_id,))


class RecorderWorker:
    def __init__(self, url: str | None = None, data_root: Path | None = None, worker_id: str | None = None,
                 lease_seconds: float = 30.0, poll_interval: float = 1.0, recorder_kwargs: dict | None = None,
                 sleep: Callable[[float], None] = time.sleep) -> None:
        from ..marketdata.dataset import default_data_root

        self.url = url or db.database_url()
        self.data_root = data_root or default_data_root()
        self.worker_id = worker_id or f"recorder:{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:6]}"
        self.lease_seconds = lease_seconds
        self.poll_interval = poll_interval
        self.recorder_kwargs = recorder_kwargs or {}
        self.sleep = sleep

    def _conn(self) -> psycopg.Connection:
        return db.connect(self.url, autocommit=True)

    def beat(self, conn: psycopg.Connection, current: str | None) -> None:
        conn.execute(
            """INSERT INTO workers (worker_id, host, pid, current_run) VALUES (%s, %s, %s, %s)
               ON CONFLICT (worker_id) DO UPDATE SET heartbeat_at = now(), current_run = excluded.current_run""",
            (self.worker_id, socket.gethostname(), os.getpid(), current),
        )

    def claim(self, conn: psycopg.Connection) -> tuple[dict, bool] | None:
        with conn.transaction():
            row = conn.execute(
                """SELECT * FROM recorder_sessions
                   WHERE status = 'queued' OR (status = 'running' AND lease_expires_at < now())
                   ORDER BY created_at LIMIT 1 FOR UPDATE SKIP LOCKED"""
            ).fetchone()
            if row is None:
                return None
            abandoned = row["status"] == "running"
            conn.execute(
                """UPDATE recorder_sessions SET status = 'running', lease_owner = %s, heartbeat_at = now(),
                   lease_expires_at = now() + make_interval(secs => %s), started_at = coalesce(started_at, now())
                   WHERE session_id = %s""",
                (self.worker_id, self.lease_seconds, row["session_id"]),
            )
        return row, abandoned

    def _finish(self, conn: psycopg.Connection, session_id: str, status: str, manifest: dict | None,
                error: str | None) -> None:
        conn.execute(
            """UPDATE recorder_sessions SET status = %s, manifest = %s, error = %s, finished_at = now(),
               lease_owner = NULL, lease_expires_at = NULL WHERE session_id = %s AND lease_owner = %s""",
            (status, Jsonb(manifest) if manifest else None, error, session_id, self.worker_id),
        )

    def recover_abandoned(self, conn: psycopg.Connection, row: dict) -> None:
        sid = row["session_id"]
        path = recordings_dir(self.data_root) / sid
        if not path.is_dir():
            self._finish(conn, sid, "failed", None, "worker died before the session directory was created")
            return
        if not is_finalized(path):
            recover(path, SystemClock(), f"lease of worker {row['lease_owner']} expired (recorder process died)")
            finalize(path, "recovered after recorder crash", True, socket.gethostname(), os.getpid(),
                     _code_version())
        m = load_manifest(path)
        self._finish(conn, sid, m.status.value, json.loads(m.model_dump_json()),
                     "recorder process died; session recovered and finalized as partial (not resumed)")

    def run_session(self, conn: psycopg.Connection, row: dict) -> str:
        config = SessionConfig.model_validate(row["config"])
        kwargs = dict(self.recorder_kwargs)
        clock = kwargs.pop("clock", None) or SystemClock()
        writer = SessionWriter(self.data_root, config, clock)
        started = clock.time_ns()
        lease_lost = False
        ctl_conn = self._conn()

        async def control(stats) -> bool:
            nonlocal lease_lost

            def _update() -> bool:
                nonlocal lease_lost
                res = ctl_conn.execute(
                    """UPDATE recorder_sessions SET heartbeat_at = now(), stats = %s,
                       lease_expires_at = now() + make_interval(secs => %s)
                       WHERE session_id = %s AND lease_owner = %s RETURNING stop_requested""",
                    (Jsonb(stats.as_dict()), self.lease_seconds, config.session_id, self.worker_id),
                ).fetchone()
                self.beat(ctl_conn, config.session_id)
                if res is None:
                    lease_lost = True
                    return True
                return bool(res["stop_requested"])

            return await asyncio.to_thread(_update)

        recorder = Recorder(config, writer, clock, control=control, **kwargs)
        try:
            reason = asyncio.run(recorder.run())
        finally:
            writer.close()
            ctl_conn.close()
        if lease_lost:
            log.error("%s: lease lost; leaving session for recovery", config.session_id)
            return "lease_lost"
        m = finalize(writer.dir, reason, False, socket.gethostname(), os.getpid(), _code_version(),
                     started_ns=started, stopped_ns=clock.time_ns())
        self._finish(conn, config.session_id, m.status.value, json.loads(m.model_dump_json()), None)
        return m.status.value

    def run_once(self) -> bool:
        with self._conn() as conn:
            self.beat(conn, None)
            claimed = self.claim(conn)
            if claimed is None:
                return False
            row, abandoned = claimed
            try:
                if abandoned:
                    self.recover_abandoned(conn, row)
                else:
                    self.run_session(conn, row)
            except Exception as exc:  # explicit failure, visible to the Owner
                log.exception("recorder session %s failed", row["session_id"])
                path = recordings_dir(self.data_root) / row["session_id"]
                manifest = None
                if path.is_dir() and not is_finalized(path):
                    try:
                        recover(path, SystemClock(), f"recorder error: {exc}")
                        manifest = json.loads(finalize(path, f"error: {exc}", True, socket.gethostname(),
                                                       os.getpid(), _code_version()).model_dump_json())
                    except Exception:  # noqa: BLE001 - keep the original failure explanation
                        log.exception("could not finalize %s", row["session_id"])
                self._finish(conn, row["session_id"], "failed" if manifest is None else manifest["status"],
                             manifest, f"{type(exc).__name__}: {exc}")
            return True

    def run_forever(self, should_stop: Callable[[], bool] = lambda: False) -> None:
        log.info("recorder worker %s started (data root %s)", self.worker_id, self.data_root)
        while not should_stop():
            try:
                if not self.run_once():
                    self.sleep(self.poll_interval)
            except psycopg.OperationalError as exc:
                log.warning("recorder worker db error: %s", exc)
                self.sleep(self.poll_interval)


def _code_version() -> str | None:
    from ..artifacts import code_version

    return code_version()
