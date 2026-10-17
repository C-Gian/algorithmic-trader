"""Esecuzioni (job) del servizio: macchina a stati, un solo worker, chiave d'avvio idempotente.

Stati attivi: STARTING (prenotato e registrato su disco prima di calcolare), RUNNING,
CANCEL_REQUESTED. Esiti terminali, uno solo per job e mai modificati dopo: COMPLETED (risultato
completo pubblicato), INCOMPLETE (pubblicato ma con finestra interrotta/operazioni irrisolte),
CANCELLED, INTERRUPTED (servizio arrestato o riavviato), FAILED (dati mancanti/non certificabili o
errore). Il job conserva profilo, versioni, provenienza, cronologia degli stati e ultimo progresso;
il bundle del risultato non contiene nulla di tutto questo.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import threading
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

from obs001.acquire import AcquisitionError
from obs001.minutes import SchemaError
from trading_primitives.file_lock import FileLock

from cand001 import ENGINE_VERSION
from cand001.config import Candidate
from cand001.pipeline import Cancelled, Events, execute
from cand001.profiles import Profile

JOB_SCHEMA = "app001.job/1"
ACTIVE = ("STARTING", "RUNNING", "CANCEL_REQUESTED")
TERMINAL = ("COMPLETED", "INCOMPLETE", "CANCELLED", "INTERRUPTED", "FAILED")
TRANSITIONS = {
    "STARTING": {"RUNNING", "CANCEL_REQUESTED", "FAILED", "INTERRUPTED"},
    "RUNNING": {"CANCEL_REQUESTED", "COMPLETED", "INCOMPLETE", "FAILED", "INTERRUPTED"},
    "CANCEL_REQUESTED": {"CANCELLED", "COMPLETED", "INCOMPLETE", "FAILED", "INTERRUPTED"},
}
STAGES = ("check", "init", "simulate", "save")
JOB_ID = re.compile(r"^job-\d{8}T\d{6}Z-[0-9a-f]{6}$")
REQUEST_KEY = re.compile(r"^[A-Za-z0-9_-]{8,80}$")
WRITE_EVERY_S = 0.5
INTERRUPTED_CAUSE = "servizio arrestato o riavviato prima della conclusione; il calcolo non riprende da solo"


def now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def write_json_atomic(path: Path, data: dict) -> None:
    tmp = path.with_name(f".{path.name}.{secrets.token_hex(3)}.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    for attempt in range(20):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:  # Windows: un lettore esterno può tenere il file per un attimo
            if attempt == 19:
                tmp.unlink(missing_ok=True)
                raise
            time.sleep(0.05)


class StartRefused(Exception):
    def __init__(self, code: str, message: str, job: dict | None = None):
        super().__init__(message)
        self.code, self.message, self.job = code, message, job


def _empty_progress(profile: Profile, files_expected: int | None = None) -> dict:
    """Contatori non ancora calcolati = None, non zero."""
    return {
        "stage": None,
        "stages": {
            "check": {"status": "PENDING", "startedAt": None, "finishedAt": None, "filesExpected": files_expected, "filesDone": None,
                      "byKind": None, "current": None},
            "init": {"status": "PENDING", "startedAt": None, "finishedAt": None, "minutes": None, "prefixMinutes": None, "windowMinutes": None,
                     "steps": None, "current": None},
            "simulate": {"status": "PENDING", "startedAt": None, "finishedAt": None, "closesTotal": None, "closes": None, "t": None,
                         "episodes": None, "calls": None, "requests": None, "fills": None, "tradesClosed": None, "positionOpen": None,
                         "pendingEntry": None, "haltedAt": None},
            "save": {"status": "PENDING", "startedAt": None, "finishedAt": None, "step": None, "publishing": False},
        },
        "window": {"start": profile.window[0], "end": profile.window[1]},
    }


class JobEvents(Events):
    """Riceve gli eventi del percorso comune e aggiorna il progresso del job; solleva Cancelled
    al primo punto di controllo dopo una richiesta d'annullamento o d'arresto del servizio."""

    def __init__(self, manager: "JobManager", job: dict):
        self.m, self.job = manager, job
        self.last_write = 0.0

    def _check(self) -> None:
        if self.m._cancel_event.is_set():
            raise Cancelled()

    def _touch(self, force: bool = False) -> None:
        self.job["updatedAt"] = now_iso()
        now = time.monotonic()
        if force or now - self.last_write >= WRITE_EVERY_S:
            self.m._persist(self.job)
            self.last_write = now

    def stage(self, name: str, **info) -> None:
        self._check()
        with self.m._lock:
            prog = self.job["progress"]
            at = now_iso()
            for s in STAGES:
                st = prog["stages"][s]
                if s == name:
                    st["status"], st["startedAt"] = "RUNNING", at
                elif st["status"] == "RUNNING":
                    st["status"], st["finishedAt"] = "DONE", at
            prog["stage"] = name
            st = prog["stages"][name]
            if name == "check":
                st.update(filesExpected=info["filesExpected"], filesDone=0, current=None,
                          byKind={k: {"expected": sum(1 for f in info["files"] if f["kind"] == k), "done": 0} for k in ("trade", "funding", "mark")},
                          reuseObs=len(info.get("reuseObs", [])))
            elif name == "init":
                st.update(minutes=info["minutes"], minutesValid=info["minutesValid"], prefixMinutes=info["prefixMinutes"],
                          windowMinutes=info["windowMinutes"], steps={})
            elif name == "simulate":
                st.update(closesTotal=info["closesTotal"], bars45=info["bars45"], bars1D=info["bars1D"])
            self._touch(force=True)

    def tick(self, name: str, **info) -> None:
        self._check()
        with self.m._lock:
            st = self.job["progress"]["stages"][name]
            if name == "check":
                event = info["event"]
                if event == "file":
                    st["current"] = {"kind": info["kind"], "month": info["month"], "rows": 0}
                elif event == "rows" and st["current"]:
                    st["current"]["rows"] = info["rows"]
                elif event == "done":
                    st["filesDone"] += 1
                    st["byKind"][info["kind"]]["done"] += 1
                    st["current"] = None
            elif name == "init":
                st["steps"][info["step"]] = {"done": info["done"], "total": info["total"]}
                st["current"] = info["step"]
            elif name == "simulate":
                for k in ("t", "closes", "closesTotal", "episodes", "calls", "requests", "fills", "tradesClosed", "positionOpen", "pendingEntry", "haltedAt"):
                    st[k] = info[k]
            elif name == "save":
                st["step"] = info["step"]
            self._touch()

    def publishing(self) -> None:
        """Ultimo punto in cui l'annullamento vale; dopo, il risultato viene pubblicato."""
        with self.m._lock:
            if self.m._cancel_event.is_set():
                raise Cancelled()
            self.job["progress"]["stages"]["save"]["publishing"] = True
            self._touch(force=True)

    def log(self, message: str) -> None:
        self.m.log(f"[{self.job['jobId']}] {message.strip()}")


class JobManager:
    def __init__(self, cand: Candidate, profiles: dict[str, Profile], data_dir: Path,
                 runner: Callable[..., dict] = execute, log: Callable[[str], None] | None = None,
                 worker_lock: FileLock | None = None):
        self.cand, self.profiles, self.data_dir = cand, profiles, data_dir
        self.root = data_dir / "jobs"
        self.root.mkdir(parents=True, exist_ok=True)
        self.runner = runner
        self.log = log or (lambda msg: None)
        self.worker_lock = worker_lock or FileLock(self.root / "worker.lock")
        self._lock = threading.RLock()
        self._cancel_event = threading.Event()
        self._shutdown = False
        self._jobs: dict[str, dict] = {}
        self._by_key: dict[str, str] = {}
        self._active: str | None = None
        self._thread: threading.Thread | None = None
        self._recover()

    # ------------------------------------------------------------- persistenza

    def _path(self, job_id: str) -> Path:
        return self.root / job_id / "job.json"

    def _persist(self, job: dict) -> None:
        folder = self.root / job["jobId"]
        folder.mkdir(parents=True, exist_ok=True)
        write_json_atomic(folder / "job.json", job)

    def _recover(self) -> None:
        """All'avvio: i job non conclusi di un servizio precedente diventano INTERRUPTED, mai completi."""
        for folder in sorted(p for p in self.root.iterdir() if p.is_dir() and JOB_ID.match(p.name)):
            try:
                job = json.loads((folder / "job.json").read_text(encoding="utf-8"))
            except (OSError, ValueError):
                self.log(f"job {folder.name}: stato illeggibile, ignorato (cartella conservata)")
                continue
            if job.get("jobId") != folder.name:
                continue
            if job["state"] in ACTIVE:
                self._transition(job, "INTERRUPTED", INTERRUPTED_CAUSE)
                job["error"] = {"kind": "INTERRUPTED", "message": INTERRUPTED_CAUSE}
                self._persist(job)
                shutil.rmtree(folder / "staging", ignore_errors=True)
            self._jobs[job["jobId"]] = job
            if job.get("requestKey"):
                self._by_key[job["requestKey"]] = job["jobId"]

    # ------------------------------------------------------------- stato

    @staticmethod
    def _transition(job: dict, state: str, note: str | None = None) -> None:
        current = job["state"]
        if state not in TRANSITIONS.get(current, set()):
            raise RuntimeError(f"transizione non ammessa {current} -> {state}")
        job["state"] = state
        at = now_iso()
        job["stateHistory"].append({"state": state, "at": at, **({"note": note} if note else {})})
        job["updatedAt"] = at
        if state in TERMINAL:
            job["finishedAt"] = at

    def get(self, job_id: str) -> dict | None:
        if not JOB_ID.match(job_id or ""):
            return None
        with self._lock:
            job = self._jobs.get(job_id)
            return json.loads(json.dumps(job)) if job else None

    def get_by_key(self, request_key) -> dict | None:
        with self._lock:
            job_id = self._by_key.get(request_key) if isinstance(request_key, str) else None
            return self.get(job_id) if job_id else None

    def list(self) -> list[dict]:
        with self._lock:
            jobs = [json.loads(json.dumps(j)) for j in self._jobs.values()]
        jobs.sort(key=lambda j: j["createdAt"], reverse=True)
        return jobs

    def active(self) -> dict | None:
        with self._lock:
            return self.get(self._active) if self._active else None

    # ------------------------------------------------------------- avvio

    def start(self, profile_id: str, request_key: str) -> tuple[dict, bool]:
        """Ritorna (job, creato). Stessa chiave: stesso job anche se concluso. Altro job attivo: rifiuto."""
        if not isinstance(request_key, str) or not REQUEST_KEY.match(request_key):
            raise StartRefused("INVALID_REQUEST", "chiave d'avvio mancante o non valida")
        if profile_id not in self.profiles:
            raise StartRefused("PROFILE_NOT_ALLOWED", "profilo non previsto: sono ammessi solo i profili fissi dell'app")
        with self._lock:
            if self._shutdown:
                raise StartRefused("SERVICE_STOPPING", "il servizio si sta arrestando")
            known = self._by_key.get(request_key)
            if known:
                job = self.get(known)
                if job["profileId"] != profile_id:
                    raise StartRefused("REQUEST_KEY_CONFLICT", "chiave d'avvio già usata per un altro profilo", job)
                return job, False
            if self._active:
                raise StartRefused("ACTIVE_JOB_EXISTS", "C'è già un backtest in corso", self.get(self._active))
            if not self.worker_lock.acquire():
                raise StartRefused("WORKER_BUSY", "Un altro calcolo usa la stessa cartella dati (per esempio un comando diretto da terminale)")
            try:
                profile = self.profiles[profile_id]
                at = now_iso()
                job_id = f"job-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{secrets.token_hex(3)}"
                job = {
                    "kind": "APP001_JOB", "schema": JOB_SCHEMA, "jobId": job_id, "requestKey": request_key, "profileId": profile_id,
                    "profile": profile.ref(), "state": "STARTING", "stateHistory": [{"state": "STARTING", "at": at}],
                    "createdAt": at, "startedAt": at, "updatedAt": at, "finishedAt": None,
                    "candidate": {"id": self.cand.raw["id"], "version": self.cand.raw["candidateVersion"], "configHash": self.cand.hash},
                    "engineVersion": ENGINE_VERSION, "dataDir": str(self.data_dir), "progress": _empty_progress(profile),
                    "result": None, "error": None, "cancel": None, "service": {"pid": os.getpid()},
                }
                self._persist(job)  # prenotato e registrato prima di calcolare
            except Exception:
                self.worker_lock.release()
                raise
            self._jobs[job_id] = job
            self._by_key[request_key] = job_id
            self._active = job_id
            self._cancel_event.clear()
            self._thread = threading.Thread(target=self._run, args=(job,), name=f"worker-{job_id}", daemon=True)
            self._thread.start()
            return self.get(job_id), True

    def _finish(self, job: dict, state: str, note: str | None = None, **fields) -> None:
        with self._lock:
            if job["state"] in TERMINAL:  # esito già scritto (es. arresto del servizio): resta l'unico
                return
            job.update(fields)
            prog = job["progress"]
            at = now_iso()
            for st in prog["stages"].values():
                if st["status"] == "RUNNING":
                    st["status"], st["finishedAt"] = ("DONE" if state in ("COMPLETED", "INCOMPLETE") else "STOPPED"), at
            self._transition(job, state, note)
            self._persist(job)

    def _run(self, job: dict) -> None:
        profile = self.profiles[job["profileId"]]
        events = JobEvents(self, job)
        try:
            with self._lock:
                if job["state"] == "STARTING":
                    self._transition(job, "RUNNING")
                    self._persist(job)
            out = self.runner(self.cand, self.data_dir, profile, events, command=f"APP-001 servizio locale, job {job['jobId']}",
                              execution={"via": "APP-001", "jobId": job["jobId"]}, staging=self.root / job["jobId"] / "staging")
            if out["status"] == "BLOCKED_FUNDING":
                self._finish(job, "FAILED", "dati non certificabili: nessun risultato economico",
                             error={"kind": "DATA_NOT_CERTIFIED", "message": out["message"], "qualityReport": out["qualityReport"]})
                return
            result = {"resultId": out["runId"], "bundleSha256": out["bundleSha256"], "bundleBytes": out["bundleBytes"],
                      "complete": out["complete"], "reusedIdenticalBundle": out["reusedIdenticalBundle"], "inputHash": out["inputHash"],
                      "configHash": out["configHash"], "engineVersion": out["engineVersion"], "counts": out["counts"],
                      "halted": out["halted"], "timings": out["timings"]}
            self._finish(job, "COMPLETED" if out["complete"] else "INCOMPLETE",
                         None if out["complete"] else "risultato pubblicato ma incompleto (finestra interrotta o operazioni irrisolte)",
                         result=result)
        except Cancelled:
            with self._lock:
                if job["state"] == "CANCEL_REQUESTED":
                    job["cancel"]["outcome"] = "CANCELLED"
                    self._finish(job, "CANCELLED", "annullato su richiesta; nessun risultato pubblicato")
                else:
                    self._finish(job, "INTERRUPTED", INTERRUPTED_CAUSE, error={"kind": "INTERRUPTED", "message": INTERRUPTED_CAUSE})
        except (AcquisitionError, SchemaError, FileNotFoundError) as e:
            self._finish(job, "FAILED", "dati mancanti o non interpretabili", error={"kind": "DATA_MISSING_OR_INVALID", "message": str(e)})
        except Exception as e:  # noqa: BLE001 - errore registrato nel job, nessun falso successo
            try:
                (self.root / job["jobId"] / "error.txt").write_text(traceback.format_exc(), encoding="utf-8")
            except OSError:
                pass
            self._finish(job, "FAILED", "errore del programma", error={"kind": "INTERNAL", "message": f"{type(e).__name__}: {e}"})
        finally:
            with self._lock:
                if self._active == job["jobId"]:
                    self._active = None
                self.worker_lock.release()
            self.log(f"[{job['jobId']}] esito {job['state']}")

    # ------------------------------------------------------------- annullamento e arresto

    def cancel(self, job_id: str) -> tuple[dict, str]:
        """Ritorna (job, esito): REQUESTED, ALREADY_REQUESTED, ALREADY_FINISHED, TOO_LATE."""
        with self._lock:
            job = self._jobs.get(job_id) if JOB_ID.match(job_id or "") else None
            if job is None:
                raise KeyError(job_id)
            if job["state"] in TERMINAL:
                return self.get(job_id), "ALREADY_FINISHED"
            if job["progress"]["stages"]["save"]["publishing"]:
                job["cancel"] = {"requestedAt": now_iso(), "outcome": "TOO_LATE"}
                self._persist(job)
                return self.get(job_id), "TOO_LATE"
            if job["state"] == "CANCEL_REQUESTED":
                return self.get(job_id), "ALREADY_REQUESTED"
            job["cancel"] = {"requestedAt": now_iso(), "outcome": None}
            self._transition(job, "CANCEL_REQUESTED")
            self._persist(job)
            self._cancel_event.set()
            return self.get(job_id), "REQUESTED"

    def shutdown(self, timeout_s: float = 8.0) -> None:
        """Arresto ordinato: il job attivo si ferma al punto di controllo successivo e diventa INTERRUPTED
        (o CANCELLED se l'annullamento era già stato chiesto). Nessuna attesa indefinita."""
        with self._lock:
            self._shutdown = True
            self._cancel_event.set()
            thread = self._thread
        if thread is not None:
            thread.join(timeout_s)
        with self._lock:
            if self._active:
                job = self._jobs[self._active]
                if job["state"] in ACTIVE:
                    self._finish(job, "INTERRUPTED", INTERRUPTED_CAUSE + " (worker non fermato in tempo)",
                                 error={"kind": "INTERRUPTED", "message": INTERRUPTED_CAUSE})
