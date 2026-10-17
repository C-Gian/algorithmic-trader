"""API HTTP locale del servizio APP-001 (libreria standard, 127.0.0.1).

Confini: solo /api; nessun comando, argomento o percorso dal browser, solo ID registrati di profili,
job e risultati. Host ammessi: il servizio e il frontend Vite locali (contro DNS rebinding). Le
richieste che modificano (POST) richiedono Origin del frontend locale e corpo JSON; nessuna intestazione
CORS. Errori con codice: SERVICE/NOT_FOUND/INVALID_REQUEST/PROFILE_NOT_ALLOWED/DATA_MISSING/
ACTIVE_JOB_EXISTS/... così l'app distingue servizio assente, risorsa mancante, dati e conflitti.
"""

from __future__ import annotations

import json
import re
import socket
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from cand001 import ENGINE_VERSION
from cand001.profiles import describe

from . import FRONTEND_ORIGINS, SERVICE_VERSION
from .catalog import Catalog
from .jobs import JobManager, StartRefused, now_iso

MAX_BODY = 4096
JOB_ROUTE = re.compile(r"^/api/jobs/([^/]+)$")
CANCEL_ROUTE = re.compile(r"^/api/jobs/([^/]+)/cancel$")
RESULT_ROUTE = re.compile(r"^/api/results/([^/]+)$")
BUNDLE_ROUTE = re.compile(r"^/api/results/([^/]+)/bundle$")
STATUS = {"PROFILE_NOT_ALLOWED": 400, "INVALID_REQUEST": 400, "REQUEST_KEY_CONFLICT": 409, "ACTIVE_JOB_EXISTS": 409, "WORKER_BUSY": 409,
          "SERVICE_STOPPING": 503, "DATA_MISSING": 422}


class App:
    """Stato condiviso del servizio: candidato, profili, job e catalogo."""

    def __init__(self, cand, profiles, data_dir, manager: JobManager, port: int, started_at: str):
        self.cand, self.profiles, self.data_dir, self.manager, self.port = cand, profiles, data_dir, manager, port
        self.catalog = Catalog(cand, profiles, data_dir)
        self.started_at = started_at
        self.set_port(port)

    def set_port(self, port: int) -> None:
        self.port = port
        self.allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"} | {urlsplit(o).netloc for o in FRONTEND_ORIGINS}

    def profiles_view(self) -> list[dict]:
        out = []
        for p in self.profiles.values():
            out.append({**describe(p), "inputStart": self.cand.input_start, "candidate": {"id": self.cand.raw["id"], "version": self.cand.raw["candidateVersion"],
                        "configHash": self.cand.hash}, "engineVersion": ENGINE_VERSION, "notionalUSDT": self.cand.econ["notionalUSDT"],
                        "costs": {"baseline": self.cand.econ["baseline"], "stress": {k: self.cand.econ["stress"][k] for k in ("fee", "slippage")},
                                  "funding": "storico Binance Vision, prezzo mark 1m"},
                        "availability": self.catalog.availability(p)})
        return out


def job_summary(job: dict) -> dict:
    keys = ("jobId", "profileId", "profile", "state", "createdAt", "startedAt", "finishedAt", "updatedAt", "result", "error", "cancel", "engineVersion")
    return {k: job.get(k) for k in keys}


class Handler(BaseHTTPRequestHandler):
    server_version = "APP001"
    sys_version = ""
    app: App  # impostato dalla classe derivata in make_server

    def log_message(self, format, *args):  # noqa: A002 - firma della libreria
        pass

    # ------------------------------------------------------------- risposte

    def _send(self, status: int, body: bytes, content_type: str = "application/json; charset=utf-8") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-App001-Service", SERVICE_VERSION)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, status: int, data: dict) -> None:
        self._send(status, json.dumps({**data, "serverTime": now_iso()}, ensure_ascii=False).encode("utf-8"))

    def _error(self, status: int, code: str, message: str, **extra) -> None:
        self._json(status, {"error": {"code": code, "message": message, **extra}})

    # ------------------------------------------------------------- confini

    def _host_ok(self) -> bool:
        return (self.headers.get("Host") or "") in self.app.allowed_hosts

    def _origin_ok(self) -> bool:
        return self.headers.get("Origin") in FRONTEND_ORIGINS

    def _read_raw(self) -> bytes | None:
        """Legge sempre il corpo dichiarato (entro MAX_BODY) prima di rispondere, anche a un rifiuto:
        su Windows chiudere un socket con dati non letti interrompe la risposta al client."""
        try:
            n = int(self.headers.get("Content-Length") or "0")
        except ValueError:
            n = -1
        if n < 0 or n > MAX_BODY:
            self.close_connection = True
            return None
        return self.rfile.read(n) if n else b""

    def _body(self, raw: bytes | None) -> dict | None:
        ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if raw is None or ctype != "application/json":
            return None
        try:
            data = json.loads(raw or b"{}")
        except ValueError:
            return None
        return data if isinstance(data, dict) else None

    # ------------------------------------------------------------- metodi

    def do_OPTIONS(self):  # noqa: N802 - nessun CORS: il browser non riceve permessi cross-origin
        self._error(405, "METHOD_NOT_ALLOWED", "metodo non ammesso")

    def do_PUT(self):  # noqa: N802
        self._error(405, "METHOD_NOT_ALLOWED", "metodo non ammesso")

    do_DELETE = do_PATCH = do_PUT

    def do_GET(self):  # noqa: N802
        if not self._host_ok():
            return self._error(403, "FORBIDDEN_HOST", "host non ammesso: il servizio risponde solo al frontend locale")
        path = urlsplit(self.path).path
        app = self.app
        if path == "/api/health":
            return self._json(200, {"service": "APP-001", "version": SERVICE_VERSION, "engineVersion": ENGINE_VERSION,
                                    "candidate": {"id": app.cand.raw["id"], "version": app.cand.raw["candidateVersion"], "configHash": app.cand.hash},
                                    "dataDir": str(app.data_dir), "startedAt": app.started_at})
        if path == "/api/profiles":
            return self._json(200, {"profiles": app.profiles_view(), "activeJob": app.manager.active()})
        if path == "/api/jobs":
            active = app.manager.active()
            return self._json(200, {"jobs": [job_summary(j) for j in app.manager.list()], "activeJobId": active["jobId"] if active else None})
        if path == "/api/results":
            return self._json(200, {"results": app.catalog.list()})
        m = JOB_ROUTE.match(path)
        if m:
            job = app.manager.get(m.group(1))
            return self._json(200, {"job": job}) if job else self._error(404, "NOT_FOUND", "esecuzione non trovata")
        m = BUNDLE_ROUTE.match(path)
        if m:
            entry, body, reason = app.catalog.bundle(m.group(1))
            if entry is None:
                return self._error(404, "NOT_FOUND", "risultato non trovato")
            if body is None:
                return self._error(409, "RESULT_NOT_OPENABLE", reason, result=entry)
            return self._send(200, body)
        m = RESULT_ROUTE.match(path)
        if m:
            entry = app.catalog.get(m.group(1))
            if entry is None:
                return self._error(404, "NOT_FOUND", "risultato non trovato")
            jobs = [job_summary(j) for j in app.manager.list() if (j.get("result") or {}).get("resultId") == entry["resultId"]]
            return self._json(200, {"result": entry, "manifest": app.catalog.manifest(entry["resultId"]), "jobs": jobs})
        return self._error(404, "NOT_FOUND", "risorsa non trovata")

    do_HEAD = do_GET

    def do_POST(self):  # noqa: N802
        raw = self._read_raw()
        if not self._host_ok():
            return self._error(403, "FORBIDDEN_HOST", "host non ammesso")
        if not self._origin_ok():
            return self._error(403, "FORBIDDEN_ORIGIN", "le modifiche sono accettate solo dal frontend locale dell'app")
        body = self._body(raw)
        if body is None:
            return self._error(400, "INVALID_REQUEST", "corpo JSON richiesto")
        path = urlsplit(self.path).path
        app = self.app
        if path == "/api/jobs":
            extra = set(body) - {"profileId", "requestKey"}
            if extra:
                return self._error(400, "INVALID_REQUEST", f"campi non ammessi: {', '.join(sorted(extra))}. Periodo, strategia e costi sono fissati dal profilo")
            pid = body.get("profileId")
            profile = app.profiles.get(pid) if isinstance(pid, str) else None
            if profile is None:
                return self._error(400, "PROFILE_NOT_ALLOWED", "profilo non previsto: sono ammessi solo i profili fissi dell'app")
            known = app.manager.get_by_key(body.get("requestKey"))
            if known is None:
                avail = app.catalog.availability(profile)
                if not avail["available"]:
                    return self._error(422, "DATA_MISSING", "dati richiesti mancanti: nessun backtest avviato e nessun download tentato",
                                       missing=avail["missing"])
            try:
                job, created = app.manager.start(pid, body.get("requestKey"))
            except StartRefused as e:
                return self._error(STATUS.get(e.code, 409), e.code, e.message, **({"job": e.job} if e.job else {}))
            return self._json(201 if created else 200, {"job": job, "created": created})
        m = CANCEL_ROUTE.match(path)
        if m:
            if body:
                return self._error(400, "INVALID_REQUEST", "l'annullamento non accetta parametri")
            try:
                job, outcome = app.manager.cancel(m.group(1))
            except KeyError:
                return self._error(404, "NOT_FOUND", "esecuzione non trovata")
            if outcome == "TOO_LATE":
                return self._error(409, "TOO_LATE", "Il risultato è già in pubblicazione: l'annullamento non è più possibile", job=job)
            return self._json(202 if outcome in ("REQUESTED", "ALREADY_REQUESTED") else 200, {"job": job, "outcome": outcome})
        return self._error(404, "NOT_FOUND", "risorsa non trovata")


class LocalServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False  # su Windows SO_REUSEADDR permetterebbe di condividere una porta occupata

    def server_bind(self):
        if sys.platform == "win32" and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def make_server(app: App, host: str = "127.0.0.1") -> LocalServer:
    handler = type("BoundHandler", (Handler,), {"app": app})
    server = LocalServer((host, app.port), handler)
    app.set_port(server.server_address[1])  # porta 0 nei test: quella assegnata dal sistema
    return server
