"""Command-line entry points.

    algotrader migrate            create/upgrade the PostgreSQL schema
    algotrader api                run the FastAPI app (serves the built web UI)
    algotrader worker             run a durable run worker
    algotrader serve              migrate + supervised worker + api (local, no Docker)
    algotrader replay             run the engine in-process and print the trace hash
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
import threading
import time

from . import db


def _worker(args: argparse.Namespace) -> None:
    from .worker import Worker

    Worker(lease_seconds=args.lease_seconds, poll_interval=args.poll_interval).run_forever()


def _api(args: argparse.Namespace) -> None:
    import uvicorn

    uvicorn.run("algotrader.api:app_from_env", factory=True, host=args.host, port=args.port, log_level="info")


def _serve(args: argparse.Namespace) -> None:
    """Local stack without Docker: API in-process, worker as a supervised child.

    If the worker dies (e.g. a controlled fault), it is restarted, mirroring
    the ``restart: unless-stopped`` policy in docker-compose.yml.
    """
    db.migrate()
    stop = threading.Event()
    cmd = [sys.executable, "-m", "algotrader.cli", "worker", "--lease-seconds", str(args.lease_seconds)]

    def supervise() -> None:
        while not stop.is_set():
            proc = subprocess.Popen(cmd, env=os.environ.copy())
            while proc.poll() is None:
                if stop.is_set():
                    proc.terminate()
                    proc.wait(10)
                    return
                time.sleep(0.2)
            logging.warning("worker exited with code %s; restarting in 1s", proc.returncode)
            time.sleep(1)

    t = threading.Thread(target=supervise, daemon=True)
    t.start()
    try:
        _api(args)
    finally:
        stop.set()
        t.join(15)


def _replay(args: argparse.Namespace) -> None:
    from .engine import Engine, trace_hash
    from .synthetic import build_fixture

    engine = Engine(build_fixture(seed=args.seed))
    _, events = engine.run_all()
    print(f"events={len(events)} trace_sha256={trace_hash([e.semantic() for e in events])}")


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    p = argparse.ArgumentParser(prog="algotrader")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("migrate").set_defaults(fn=lambda a: db.migrate())
    w = sub.add_parser("worker")
    w.add_argument("--lease-seconds", type=float, default=float(os.environ.get("ALGOTRADER_LEASE_SECONDS", 10)))
    w.add_argument("--poll-interval", type=float, default=0.5)
    w.set_defaults(fn=_worker)
    for name, fn in (("api", _api), ("serve", _serve)):
        s = sub.add_parser(name)
        s.add_argument("--host", default=os.environ.get("ALGOTRADER_HOST", "127.0.0.1"))
        s.add_argument("--port", type=int, default=int(os.environ.get("ALGOTRADER_PORT", 8000)))
        s.add_argument("--lease-seconds", type=float, default=float(os.environ.get("ALGOTRADER_LEASE_SECONDS", 10)))
        s.set_defaults(fn=fn)
    r = sub.add_parser("replay")
    r.add_argument("--seed", type=int, default=20260929)
    r.set_defaults(fn=_replay)
    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
