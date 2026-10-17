"""Avvio del servizio locale APP-001 (normalmente dal launcher di `npm run dev`).

PowerShell, dalla radice del checkout:
    $env:PYTHONPATH = "src"; python3.12 -m app001 [--data-dir <cartella CAND-001>] [--port 8765]
La cartella dati predefinita è C:\\Projects\\algorithmic-trader-data\\CAND-001 (variabile APP001_DATA_DIR
o --data-dir per cambiarla). Il servizio non scarica nulla: ogni richiesta di rete è disattivata.
"""

from __future__ import annotations

import argparse
import os
import signal
import sys
import threading
from pathlib import Path

EXIT_PORT, EXIT_DATA, EXIT_LOCKED, EXIT_PYTHON = 3, 4, 5, 6


def say(msg: str) -> None:
    print(f"[servizio] {msg}", flush=True)


def _no_network(url: str, *args, **kwargs):
    raise RuntimeError(f"richiesta di rete non ammessa nel servizio APP-001: {url}")


def main(argv: list[str] | None = None) -> int:
    if sys.version_info < (3, 12):
        say(f"serve Python 3.12 o successivo (trovato {sys.version.split()[0]}). Indica il percorso con APP001_PYTHON.")
        return EXIT_PYTHON
    from obs001 import acquire as obs_acquire
    from trading_primitives.file_lock import FileLock

    import cand001.data as cand_data
    from cand001.cli import DEFAULT_DATA_DIR
    from cand001.config import load_candidate
    from cand001.profiles import load_profiles

    from . import DEFAULT_PORT
    from .jobs import JobManager, now_iso, write_json_atomic
    from .server import App, make_server

    parser = argparse.ArgumentParser(prog="app001", description="Servizio locale APP-001 per i backtest dall'app.")
    parser.add_argument("--data-dir", type=Path, default=Path(os.environ.get("APP001_DATA_DIR") or DEFAULT_DATA_DIR))
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--watch-stdin", action="store_true", help="arresto ordinato quando si chiude lo standard input (launcher)")
    args = parser.parse_args(argv)

    # Nessun download nel percorso dell'app, nemmeno per errore.
    obs_acquire.http_get = _no_network
    cand_data.http_get = _no_network

    data_dir = args.data_dir.resolve()
    if not (data_dir / "manifests").is_dir() or not (data_dir / "raw").is_dir():
        say(f"cartella dati non trovata o incompleta: {data_dir}")
        say("Indica la cartella CAND-001 con la variabile APP001_DATA_DIR (o --data-dir). Nessun download automatico.")
        return EXIT_DATA
    cand = load_candidate()
    profiles = load_profiles(cand)
    jobs_dir = data_dir / "jobs"
    jobs_dir.mkdir(exist_ok=True)
    service_lock = FileLock(jobs_dir / "service.lock")
    if not service_lock.acquire():
        say(f"un altro servizio APP-001 usa già la cartella {data_dir} (o si sta ancora arrestando).")
        say("Chiudi l'altra finestra del terminale con Ctrl+C e riprova; nessun processo viene terminato automaticamente.")
        return EXIT_LOCKED
    started = now_iso()
    manager = JobManager(cand, profiles, data_dir, log=say)
    app = App(cand, profiles, data_dir, manager, args.port, started)
    try:
        server = make_server(app)
    except OSError as e:
        say(f"la porta {args.port} su 127.0.0.1 non è disponibile ({e.strerror or e}).")
        say("Probabilmente un altro programma la usa: chiudilo oppure avvia con --port. Nessun processo viene terminato automaticamente.")
        service_lock.release()
        return EXIT_PORT
    write_json_atomic(jobs_dir / "service.json", {"pid": os.getpid(), "port": app.port, "startedAt": started, "dataDir": str(data_dir)})
    stop = threading.Event()

    def on_signal(*_):
        stop.set()

    for name in ("SIGTERM", "SIGBREAK"):
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), on_signal)
    if args.watch_stdin:
        def watch():
            try:
                while sys.stdin.read(1):
                    pass
            except (OSError, ValueError):
                pass
            stop.set()

        threading.Thread(target=watch, name="stdin-watch", daemon=True).start()
    worker = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.25}, name="http", daemon=True)
    worker.start()
    say(f"pronto su http://127.0.0.1:{app.port} | dati {data_dir} | candidato {cand.raw['id']} {cand.raw['candidateVersion']}")
    try:
        while not stop.wait(0.5):
            pass
    except KeyboardInterrupt:
        pass
    say("arresto: un eventuale backtest in corso viene segnato come interrotto")
    server.shutdown()
    server.server_close()
    manager.shutdown()
    service_lock.release()
    say("servizio arrestato")
    return 0


if __name__ == "__main__":
    sys.exit(main())
