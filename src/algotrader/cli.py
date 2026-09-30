"""Command-line entry points.

    algotrader migrate            create/upgrade the PostgreSQL schema
    algotrader api                run the FastAPI app (serves the built web UI)
    algotrader worker             run a durable run worker
    algotrader serve              migrate + supervised worker + api (local, no Docker)
    algotrader replay             run the engine in-process and print the trace hash
    algotrader schema [--write]   check / write the semantic contract JSON Schema baseline
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


def _schema(args: argparse.Namespace) -> None:
    from .schema import baseline_path, baselines, render, write_baseline

    for version, build in baselines().items():
        if args.write:
            print(f"wrote {write_baseline(version=version)}")
            continue
        path = baseline_path(version)
        if not path.is_file() or path.read_text(encoding="utf-8") != render(build()):
            sys.exit(f"contracts differ from the checked-in baseline {path}")
        print(f"{path.name}: contracts match the checked-in baseline")


def _data_fetch(args: argparse.Namespace) -> None:
    from .marketdata.dataset import acquire, parse_utc
    from .marketdata.okx import OkxPublicClient

    client = OkxPublicClient(base_url=args.base_url, timeout=args.timeout)
    result = acquire(client, args.root, parse_utc(args.start), parse_utc(args.end), page_limit=args.page_limit)
    _print_dataset(result.path, "already present (identical source content)" if result.reused else "created")


def _data_verify(args: argparse.Namespace) -> None:
    from .marketdata.dataset import dataset_path, verify

    path = dataset_path(args.root, args.dataset_id)
    if path is None:
        sys.exit(f"no dataset {args.dataset_id} under {args.root}")
    problems = verify(path)
    if problems:
        sys.exit("VERIFY FAILED:\n  " + "\n  ".join(problems))
    _print_dataset(path, "verified")


def _data_list(args: argparse.Namespace) -> None:
    from .marketdata.dataset import list_manifests

    for m in list_manifests(args.root):
        print(f"{m.dataset_id}  {m.request.start:%Y-%m-%d %H:%M}..{m.request.end:%Y-%m-%d %H:%M} UTC  "
              f"quality={m.quality_status}")


def _data_live_check(args: argparse.Namespace) -> None:
    """Manual live integration check (never run in CI): probe, fetch, write, verify."""
    from datetime import UTC, datetime, timedelta

    from .marketdata.dataset import acquire, verify
    from .marketdata.okx import OkxPublicClient

    client = OkxPublicClient(base_url=args.base_url, timeout=args.timeout)
    now = datetime.now(UTC).replace(second=0, microsecond=0)
    end = now - timedelta(minutes=2)  # well past the last completed bar
    start = end - timedelta(minutes=args.minutes)
    print(f"LIVE CHECK against {client.base_url} for [{start:%Y-%m-%dT%H:%MZ}, {end:%Y-%m-%dT%H:%MZ})")
    inst = client.instrument("BTC-USDT-SWAP")
    print(f"instrument probe: HTTP {inst.http_status}, code {inst.code}, sha256 {inst.sha256[:16]}...")
    result = acquire(client, args.root, start, end)
    problems = verify(result.path)
    _print_dataset(result.path, "verified" if not problems else "VERIFY FAILED")
    if problems:
        sys.exit("\n".join(problems))
    print("LIVE CHECK OK (integration evidence only; not a trading result)")


def _print_dataset(path, verdict: str) -> None:
    from .marketdata.dataset import load_manifest, load_quality

    m, q = load_manifest(path), load_quality(path)
    print(f"dataset {m.dataset_id}: {verdict}")
    print(f"  path      {path}")
    print(f"  source    {m.request.base_url} {m.instrument.inst_id} ({m.instrument.inst_type} {m.instrument.ct_type}, "
          f"{m.instrument.ct_val} {m.instrument.ct_val_ccy}/contract, settle {m.instrument.settle_ccy})")
    print(f"  requested [{m.request.start.isoformat()}, {m.request.end.isoformat()})")
    print(f"  retrieved {m.retrieval_started_at.isoformat()} .. {m.retrieval_finished_at.isoformat()}; "
          f"{m.raw_page_count} raw pages; schema {m.schema_version}")
    for f, fq in zip(m.families, q.families):
        gaps = f", gaps {len(fq.gaps)} ({fq.missing_rows} bars)" if fq.missing_rows else ""
        print(f"  {f.family.value:18} rows {f.rows:6}  pages {f.pages:3}  "
              f"{f.first_time.isoformat() if f.first_time else '-'} .. {f.last_time.isoformat() if f.last_time else '-'}  "
              f"status {fq.status}{gaps}")
    print(f"  quality   {q.status}")


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
    sc = sub.add_parser("schema", help="check (default) or --write the semantic contract JSON Schema baseline")
    sc.add_argument("--write", action="store_true")
    sc.set_defaults(fn=_schema)

    from pathlib import Path

    from .marketdata.dataset import default_data_root
    from .marketdata.okx import DEFAULT_BASE_URL

    data = sub.add_parser("data", help="bounded public market-data datasets (read-only sources)")
    dsub = data.add_subparsers(dest="data_cmd", required=True)

    def common(p: argparse.ArgumentParser, source: bool = False) -> None:
        p.add_argument("--root", type=Path, default=default_data_root(), help="data/catalog root (ALGOTRADER_DATA_ROOT)")
        if source:
            p.add_argument("--base-url", default=os.environ.get("ALGOTRADER_OKX_BASE_URL", DEFAULT_BASE_URL),
                           help="OKX public REST base URL (regional domains differ)")
            p.add_argument("--timeout", type=float, default=10.0)

    f = dsub.add_parser("fetch-okx", help="acquire a bounded OKX BTC-USDT-SWAP 1m dataset")
    f.add_argument("--start", required=True, help="inclusive UTC start, minute-aligned (e.g. 2026-09-29T08:00Z)")
    f.add_argument("--end", required=True, help="exclusive UTC end, minute-aligned")
    f.add_argument("--page-limit", type=int, default=100)
    common(f, source=True)
    f.set_defaults(fn=_data_fetch)
    v = dsub.add_parser("verify", help="re-check a dataset's hashes, row counts and identity")
    v.add_argument("dataset_id")
    common(v)
    v.set_defaults(fn=_data_verify)
    ls = dsub.add_parser("list")
    common(ls)
    ls.set_defaults(fn=_data_list)
    lc = dsub.add_parser("live-check", help="manual live OKX integration check (not run in CI)")
    lc.add_argument("--minutes", type=int, default=30)
    common(lc, source=True)
    lc.set_defaults(fn=_data_live_check)
    args = p.parse_args(argv)
    from .marketdata.dataset import DatasetError
    from .marketdata.okx import SourceError

    try:
        args.fn(args)
    except (DatasetError, SourceError) as exc:  # explicit, non-traceback failure for data commands
        sys.exit(f"ERROR: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
