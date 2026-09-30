"""Durable corpus preparation: PostgreSQL jobs owned by a ``corpus-worker`` process.

The browser/API never acquires market data. ``create_job`` only inserts a queued
job; a corpus worker claims it under a lease and, for the job's logical chunk:

1. **reuse** - if the chunk is already bound to a local dataset that passes full
   ``marketdata.v1`` verification, nothing is downloaded (outcome ``reused_binding``);
2. **adopt** - else if a local dataset with exactly the chunk's logical request exists
   and verifies, it is bound without network access (``adopted_local_dataset``);
3. **acquire** - else the accepted ``OkxPublicClient`` + ``marketdata.dataset.acquire``
   fetch the bounded month into a new immutable dataset, which is fully verified
   *before* it is bound (``acquired``; ``acquired_identical_existing`` when the source
   bytes were already present).

Cancellation is checked at every saved source page (the acquisition's safe boundary):
the temporary directory is removed and nothing is bound. A cancellation arriving after
the dataset was finalized leaves that immutable dataset untouched but unbound (a later
Prepare adopts it locally). Finalized datasets are never deleted.

Restart: a job whose worker stopped heartbeating is reclaimed after its lease expires.
There is **no byte-level resume**: the reclaiming worker removes the dead attempt's
temporary directory and restarts that one bounded chunk from scratch. After
``max_attempts`` consecutive interruptions the job fails explicitly.
"""

from __future__ import annotations

import logging
import os
import shutil
import socket
import threading
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from .. import db
from ..marketdata import dataset as md
from ..marketdata.okx import DEFAULT_BASE_URL, OkxPublicClient
from ..marketdata.okx_authority import validate_okx_rest_base_url
from . import state
from .plan import Chunk, CorpusPlan, load_plan

log = logging.getLogger("algotrader.corpus")
WORKER_PREFIX = "corpus:"
TERMINAL = ("completed", "cancelled", "failed")
RECOVERY_BEHAVIOR = (
    "If the worker stops (crash, restart, PC off) the job is reclaimed after its lease expires and this one "
    "bounded monthly chunk is acquired again from scratch; partially downloaded pages are discarded (no "
    "byte-level resume). A completed binding survives any restart."
)


class CorpusJobRejected(Exception):
    pass


class AcquisitionCancelled(Exception):
    pass


class LeaseLost(Exception):
    pass


def configured_base_url() -> str:
    url = os.environ.get("ALGOTRADER_OKX_BASE_URL", DEFAULT_BASE_URL)
    parsed = validate_okx_rest_base_url(url)  # official OKX host only; never rewritten
    return f"https://{parsed.netloc}"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def new_job_id() -> str:
    return f"corp-{datetime.now(UTC):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:6]}"


def create_job(conn: psycopg.Connection, plan: CorpusPlan, chunk_id: str, base_url: str | None = None) -> str:
    chunk = plan.chunk(chunk_id)
    if chunk is None:
        raise LookupError(chunk_id)
    if not chunk.preparable:
        raise CorpusJobRejected(f"{chunk_id} is planned but not preparable in this version")
    try:
        base = base_url or configured_base_url()
        validate_okx_rest_base_url(base)
    except ValueError as exc:
        raise CorpusJobRejected(f"market-data source rejected: {exc}") from None
    job_id = new_job_id()
    try:
        with conn.transaction():
            conn.execute("INSERT INTO corpus_jobs (job_id, chunk_id, plan_id, status, base_url) "
                         "VALUES (%s, %s, %s, 'queued', %s)", (job_id, chunk_id, plan.plan_id, base))
    except psycopg.errors.UniqueViolation:
        raise CorpusJobRejected(f"{chunk_id} already has an active preparation job") from None
    return job_id


def cancel_job(conn: psycopg.Connection, job_id: str) -> None:
    with conn.transaction():
        row = conn.execute("SELECT status, cancel_requested FROM corpus_jobs WHERE job_id = %s FOR UPDATE",
                           (job_id,)).fetchone()
        if row is None:
            raise LookupError(job_id)
        if row["status"] in TERMINAL:
            raise CorpusJobRejected(f"job already {row['status']}")
        if row["status"] == "queued":  # never started: nothing was fetched
            conn.execute("UPDATE corpus_jobs SET status = 'cancelled', cancel_requested = true, finished_at = now(), "
                         "error = 'cancelled before a worker started it' WHERE job_id = %s", (job_id,))
        else:
            conn.execute("UPDATE corpus_jobs SET cancel_requested = true WHERE job_id = %s", (job_id,))


ClientFactory = Callable[[str], OkxPublicClient]


def default_client_factory(base_url: str) -> OkxPublicClient:
    return OkxPublicClient(base_url=base_url)


class _Heartbeat(threading.Thread):
    """Extends the lease, publishes progress and reads cancellation independently of network waits."""

    def __init__(self, worker: CorpusWorker, job_id: str) -> None:
        super().__init__(daemon=True, name=f"heartbeat-{job_id}")
        self.worker, self.job_id = worker, job_id
        self.progress: dict[str, Any] = {}
        self.cancel = False
        self.lost = False
        self._halt = threading.Event()

    def publish(self, progress: dict[str, Any]) -> None:
        self.progress = progress

    def tick(self) -> None:
        with db.connect(self.worker.url, autocommit=True) as c:
            row = c.execute(
                """UPDATE corpus_jobs SET heartbeat_at = now(), progress = %s,
                       lease_expires_at = now() + make_interval(secs => %s)
                   WHERE job_id = %s AND lease_owner = %s AND status = 'running' RETURNING cancel_requested""",
                (Jsonb(self.progress), self.worker.lease_seconds, self.job_id, self.worker.worker_id),
            ).fetchone()
            self.worker.beat(c, self.job_id)
        if row is None:
            self.lost = True
        elif row["cancel_requested"]:
            self.cancel = True

    def run(self) -> None:
        while not self._halt.is_set():
            try:
                self.tick()
            except psycopg.OperationalError as exc:
                log.warning("corpus heartbeat error: %s", exc)
            self._halt.wait(self.worker.heartbeat_interval)

    def stop(self) -> None:
        self._halt.set()
        self.join(timeout=10)


class CorpusWorker:
    def __init__(self, url: str | None = None, data_root: Path | None = None, worker_id: str | None = None,
                 lease_seconds: float = 60.0, poll_interval: float = 1.0, heartbeat_interval: float = 2.0,
                 sleep: Callable[[float], None] = time.sleep, client_factory: ClientFactory | None = None,
                 plan: CorpusPlan | None = None) -> None:
        self.url = url or db.database_url()
        self.data_root = data_root or md.default_data_root()
        self.worker_id = worker_id or f"{WORKER_PREFIX}{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:6]}"
        if not self.worker_id.startswith(WORKER_PREFIX):
            raise ValueError(f"corpus worker ids must start with {WORKER_PREFIX!r}")
        self.lease_seconds = lease_seconds
        self.poll_interval = poll_interval
        self.heartbeat_interval = heartbeat_interval
        self.sleep = sleep
        self.client_factory = client_factory or default_client_factory
        self._plan = plan

    @property
    def plan(self) -> CorpusPlan:
        return self._plan or load_plan()

    def _conn(self) -> psycopg.Connection:
        return db.connect(self.url, autocommit=True)

    def beat(self, conn: psycopg.Connection, current: str | None) -> None:
        conn.execute(
            """INSERT INTO workers (worker_id, host, pid, current_run) VALUES (%s, %s, %s, %s)
               ON CONFLICT (worker_id) DO UPDATE SET heartbeat_at = now(), current_run = excluded.current_run""",
            (self.worker_id, socket.gethostname(), os.getpid(), current),
        )

    # -- lease -------------------------------------------------------------------

    def claim(self, conn: psycopg.Connection) -> tuple[dict[str, Any], str | None] | None:
        with conn.transaction():
            row = conn.execute(
                """SELECT * FROM corpus_jobs
                   WHERE status = 'queued' OR (status = 'running' AND lease_expires_at < now())
                   ORDER BY created_at LIMIT 1 FOR UPDATE SKIP LOCKED"""
            ).fetchone()
            if row is None:
                return None
            reclaimed = row["status"] == "running"
            recovery_log = list(row["recovery_log"])
            interruptions = row["interruptions"] + 1 if reclaimed else row["interruptions"]
            fail_reason = None
            if reclaimed:
                orphan = (row["progress"] or {}).get("work_dir")
                removed = self._remove_orphan(orphan)
                recovery_log.append({
                    "at": _now(), "attempt": row["attempt"] + 1, "event": "lease_expired_reclaimed",
                    "detail": (f"worker {row['lease_owner']} stopped heartbeating (last heartbeat "
                               f"{row['heartbeat_at'].isoformat() if row['heartbeat_at'] else 'never'}); "
                               f"reclaimed by {self.worker_id}. The bounded chunk restarts from scratch (no byte-level "
                               f"resume); {removed}"),
                })
                if interruptions >= row["max_attempts"]:
                    fail_reason = (f"worker interrupted on {interruptions} consecutive attempts (max "
                                   f"{row['max_attempts']}); no chunk was bound. Prepare again to retry.")
            conn.execute(
                """UPDATE corpus_jobs SET status = 'running', lease_owner = %s, heartbeat_at = now(),
                       lease_expires_at = now() + make_interval(secs => %s), attempt = attempt + 1,
                       interruptions = %s, recovery_log = %s, started_at = coalesce(started_at, now()),
                       attempt_started_at = now(), progress = '{}'::jsonb
                   WHERE job_id = %s""",
                (self.worker_id, self.lease_seconds, interruptions, Jsonb(recovery_log), row["job_id"]),
            )
            row.update(status="running", lease_owner=self.worker_id, attempt=row["attempt"] + 1,
                       recovery_log=recovery_log)
        return row, fail_reason

    def _remove_orphan(self, work_dir: Any) -> str:
        if not isinstance(work_dir, str) or not work_dir.startswith(".tmp-") or "/" in work_dir or "\\" in work_dir:
            return "no temporary directory recorded for the interrupted attempt"
        path = md.datasets_dir(self.data_root) / work_dir
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
            return f"removed the interrupted attempt's temporary directory {work_dir}"
        return f"temporary directory {work_dir} was already gone"

    def _finish(self, conn: psycopg.Connection, job_id: str, status: str, error: str | None = None,
                outcome: str | None = None, dataset_id: str | None = None, result: dict | None = None,
                progress: dict | None = None) -> None:
        conn.execute(
            """UPDATE corpus_jobs SET status = %s, error = %s, outcome = coalesce(%s, outcome),
                   dataset_id = coalesce(%s, dataset_id), result = coalesce(%s, result),
                   progress = coalesce(%s, progress), finished_at = now(), heartbeat_at = now(),
                   lease_owner = NULL, lease_expires_at = NULL
               WHERE job_id = %s AND lease_owner = %s AND status = 'running'""",
            (status, error, outcome, dataset_id, Jsonb(result) if result is not None else None,
             Jsonb(progress) if progress is not None else None, job_id, self.worker_id),
        )

    # -- main loop -----------------------------------------------------------------

    def run_forever(self, should_stop: Callable[[], bool] = lambda: False) -> None:
        log.info("corpus worker %s started (data root %s)", self.worker_id, self.data_root)
        while not should_stop():
            try:
                if not self.run_once():
                    self.sleep(self.poll_interval)
            except psycopg.OperationalError as exc:
                log.warning("corpus worker db error: %s", exc)
                self.sleep(self.poll_interval)

    def run_once(self) -> bool:
        with self._conn() as conn:
            self.beat(conn, None)
            claimed = self.claim(conn)
            if claimed is None:
                return False
            row, fail_reason = claimed
            if row["cancel_requested"]:
                self._finish(conn, row["job_id"], "cancelled", "cancelled by the Owner before completion; no chunk bound")
            elif fail_reason:
                self._finish(conn, row["job_id"], "failed", fail_reason)
            else:
                self.process(conn, row)
            return True

    def process(self, conn: psycopg.Connection, row: dict[str, Any]) -> None:
        job_id = row["job_id"]
        plan = self.plan
        chunk = plan.chunk(row["chunk_id"])
        if chunk is None or not chunk.preparable or plan.plan_id != row["plan_id"]:
            self._finish(conn, job_id, "failed", f"chunk {row['chunk_id']} is not preparable in plan {plan.plan_id}")
            return
        hb = _Heartbeat(self, job_id)
        hb.publish({"phase": "checking_local", "detail": "checking for a verified local dataset"})
        hb.start()
        try:
            self._prepare(conn, row, plan, chunk, hb)
        except AcquisitionCancelled:
            self._finish(conn, job_id, "cancelled", "cancelled by the Owner at a page boundary; temporary data "
                         "removed; no chunk bound", progress={**hb.progress, "phase": "cancelled"})
        except LeaseLost:
            log.error("%s: lease lost; another worker owns the job now", job_id)
        except Exception as exc:  # explicit failure, visible to the Owner
            log.exception("corpus job %s failed", job_id)
            self._finish(conn, job_id, "failed", f"{type(exc).__name__}: {exc}",
                         progress={**hb.progress, "phase": "failed"})
        finally:
            hb.stop()

    def _check(self, hb: _Heartbeat) -> None:
        if hb.lost:
            raise LeaseLost()
        if hb.cancel:
            raise AcquisitionCancelled()

    def _prepare(self, conn: psycopg.Connection, row: dict[str, Any], plan: CorpusPlan, chunk: Chunk,
                 hb: _Heartbeat) -> None:
        job_id = row["job_id"]
        binding = conn.execute("SELECT * FROM corpus_chunks WHERE chunk_id = %s", (chunk.chunk_id,)).fetchone()

        # 1. reuse an existing verified binding: no network
        if binding is not None:
            hb.publish({"phase": "verifying", "detail": f"verifying bound dataset {binding['dataset_id']}"})
            path, problems = state.verify_dataset(self.data_root, binding["dataset_id"])
            self._check(hb)
            if path is not None and not problems:
                self._complete(conn, job_id, plan, chunk, path, "reused_binding", hb)
                return
            state.record_verification(conn, chunk.chunk_id, False, problems)
            log.warning("%s: bound dataset unusable (%s); preparing again", chunk.chunk_id, problems)

        # 2. adopt an exactly matching local dataset: no network
        for m in state.find_local_match(self.data_root, plan, chunk):
            if binding is not None and m.dataset_id == binding["dataset_id"]:
                continue
            hb.publish({"phase": "verifying", "detail": f"verifying local dataset {m.dataset_id}"})
            path, problems = state.verify_dataset(self.data_root, m.dataset_id)
            self._check(hb)
            if path is not None and not problems:
                self._complete(conn, job_id, plan, chunk, path, "adopted_local_dataset", hb)
                return

        # 3. acquire from the accepted public OKX source
        client = self.client_factory(row["base_url"])
        if client.base_url != row["base_url"]:
            raise RuntimeError(f"client base URL {client.base_url} differs from the job's {row['base_url']}")
        started = time.monotonic()

        def on_progress(p: md.AcquireProgress) -> None:
            elapsed = time.monotonic() - started
            hb.publish({"phase": p.phase, "detail": "acquiring from OKX public REST", "windows_done": p.windows_done,
                        "windows_total": p.windows_total, "pages": p.pages, "bytes": p.bytes,
                        "work_dir": p.work_dir, "acquire_elapsed_seconds": round(elapsed, 3)})
            self._check(hb)

        result = md.acquire(client, self.data_root, chunk.start, chunk.end, inst_id=plan.inst_id,
                            progress=on_progress)
        hb.publish({**hb.progress, "phase": "verifying", "work_dir": None,
                    "detail": f"verifying new dataset {result.manifest.dataset_id} before binding"})
        problems = md.verify(result.path)
        if problems:
            raise RuntimeError(f"acquired dataset {result.manifest.dataset_id} failed verification: {problems}")
        self._complete(conn, job_id, plan, chunk, result.path,
                       "acquired_identical_existing" if result.reused else "acquired", hb)

    def _complete(self, conn: psycopg.Connection, job_id: str, plan: CorpusPlan, chunk: Chunk, path: Path,
                  outcome: str, hb: _Heartbeat) -> None:
        verified_at = datetime.now(UTC)
        progress = {**hb.progress, "phase": "completed", "work_dir": None}
        with conn.transaction():
            fence = conn.execute("SELECT cancel_requested FROM corpus_jobs WHERE job_id = %s AND lease_owner = %s "
                                 "AND status = 'running' FOR UPDATE", (job_id, self.worker_id)).fetchone()
            if fence is None:
                raise LeaseLost()
            if fence["cancel_requested"]:
                self._finish(conn, job_id, "cancelled",
                             f"cancelled by the Owner after dataset {path.name} was finalized; the immutable dataset "
                             "is kept but NOT bound (a later Prepare can adopt it locally)",
                             dataset_id=path.name, progress={**progress, "phase": "cancelled"})
                return
            storage = state.bind(conn, plan, chunk, path, job_id, outcome, verified_at)
            self._finish(conn, job_id, "completed", None, outcome, path.name,
                         {"dataset_id": path.name, "storage": storage}, progress)
        log.info("%s: chunk %s bound to %s (%s)", job_id, chunk.chunk_id, path.name, outcome)
