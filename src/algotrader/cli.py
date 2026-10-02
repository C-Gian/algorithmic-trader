"""Command-line entry points.

    algotrader migrate            create/upgrade the PostgreSQL schema
    algotrader api                run the FastAPI app (serves the built web UI)
    algotrader worker             run a durable run worker (synthetic DEMO replay)
    algotrader observe-worker     run a durable real-market observation-replay worker
    algotrader corpus-worker      run a durable corpus-preparation worker (public OKX, read-only)
    algotrader serve              migrate + supervised worker + api (local, no Docker)
    algotrader replay             run the engine in-process and print the trace hash
    algotrader schema [--write]   check / write the semantic contract JSON Schema baseline
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

from . import db


def _worker(args: argparse.Namespace) -> None:
    from .worker import Worker

    Worker(lease_seconds=args.lease_seconds, poll_interval=args.poll_interval).run_forever()


def _api(args: argparse.Namespace) -> None:
    import uvicorn

    uvicorn.run("algotrader.api:app_from_env", factory=True, host=args.host, port=args.port, log_level="info")


def _serve(args: argparse.Namespace) -> None:
    """Local stack without Docker: API in-process; run worker and recorder worker as supervised children.

    A dead child (e.g. a controlled fault) is restarted, mirroring the ``restart: unless-stopped``
    policy in docker-compose.yml.
    """
    db.migrate()
    stop = threading.Event()
    cmds = [
        [sys.executable, "-m", "algotrader.cli", "worker", "--lease-seconds", str(args.lease_seconds)],
        [sys.executable, "-m", "algotrader.cli", "recorder-worker"],
        [sys.executable, "-m", "algotrader.cli", "observe-worker"],
        [sys.executable, "-m", "algotrader.cli", "corpus-worker"],
    ]

    def supervise(cmd: list[str]) -> None:
        while not stop.is_set():
            proc = subprocess.Popen(cmd, env=os.environ.copy())
            while proc.poll() is None:
                if stop.is_set():
                    proc.terminate()
                    proc.wait(10)
                    return
                time.sleep(0.2)
            logging.warning("%s exited with code %s; restarting in 1s", cmd[3], proc.returncode)
            time.sleep(1)

    threads = [threading.Thread(target=supervise, args=(c,), daemon=True) for c in cmds]
    for t in threads:
        t.start()
    try:
        _api(args)
    finally:
        stop.set()
        for t in threads:
            t.join(15)


def _observe_worker(args: argparse.Namespace) -> None:
    from .observe.worker import ObservationWorker

    ObservationWorker(data_root=args.root, lease_seconds=args.lease_seconds, poll_interval=args.poll_interval,
                      heartbeat_interval=args.heartbeat_seconds, isolate=not args.inline_compute).run_forever()


def _corpus_worker(args: argparse.Namespace) -> None:
    from .corpus.job import CorpusWorker

    CorpusWorker(data_root=args.root, lease_seconds=args.lease_seconds,
                 poll_interval=args.poll_interval).run_forever()


def _recorder_worker(args: argparse.Namespace) -> None:
    from .recorder.job import RecorderWorker

    RecorderWorker(data_root=args.root, lease_seconds=args.lease_seconds).run_forever()


def _recorder_endpoints(args: argparse.Namespace):
    from .recorder.job import configured_endpoints

    ep = configured_endpoints()
    return ep.model_copy(update={k: v for k, v in (("ws_public_url", args.ws_public_url),
                                                    ("ws_business_url", args.ws_business_url),
                                                    ("rest_base_url", args.rest_base_url)) if v})


def _recorder_run(args: argparse.Namespace) -> None:
    """Foreground bounded public recording (for integration checks); no database needed."""
    import asyncio
    import socket
    from datetime import timedelta

    from .recorder.job import _code_version, new_session_id
    from .recorder.journal import SessionWriter, finalize, verify
    from .recorder.okx_live import Recorder, SystemClock, make_config

    config = make_config(new_session_id(), endpoints=_recorder_endpoints(args),
                         max_duration=timedelta(minutes=args.minutes),
                         clock_probe_interval=timedelta(seconds=args.clock_probe_seconds))
    clock = SystemClock()
    writer = SessionWriter(args.root, config, clock)
    started = clock.time_ns()
    print(f"recording {config.session_id} for up to {args.minutes} min -> {writer.dir}", flush=True)
    rec = Recorder(config, writer, clock)
    try:
        reason = asyncio.run(rec.run())
    except KeyboardInterrupt:
        reason = "interrupted"
    finally:
        writer.close()
    finalize(writer.dir, reason, False, socket.gethostname(), os.getpid(), _code_version(),
             started_ns=started, stopped_ns=clock.time_ns())
    problems = verify(writer.dir)
    print("verify: " + ("OK" if not problems else "; ".join(problems)))
    _print_recording(writer.dir)
    if problems:
        sys.exit(1)


def _recorder_inspect(args: argparse.Namespace) -> None:
    from .recorder.journal import session_path, verify

    path = session_path(args.root, args.session_id)
    if path is None:
        sys.exit(f"no recording {args.session_id} under {args.root}")
    problems = verify(path)
    print("verify: " + ("OK" if not problems else "; ".join(problems)))
    _print_recording(path)


def _print_recording(path) -> None:
    from .feed.ordering import FeedError
    from .recorder.feed_bridge import build_recorded_feed
    from .recorder.journal import is_finalized, load_manifest, load_report

    if not is_finalized(path):
        print(f"{path.name}: not finalized")
        return
    m, r = load_manifest(path), load_report(path)
    print(f"session {m.session_id}: {m.status.value} ({m.stop_reason}); {r.duration_s} s; "
          f"schema {m.schema_version} ({m.contract_status})")
    print(f"  endpoints   ws public {m.endpoints.ws_public_url} | ws business {m.endpoints.ws_business_url} | "
          f"rest {m.endpoints.rest_base_url}")
    print(f"  subscribed  {', '.join(m.channels_subscribed) or '-'} (requested {', '.join(m.channels_requested)})")
    print(f"  records {m.record_count}; connections {m.connections}; reconnects {m.reconnects}; errors {m.errors}; "
          f"clock {r.clock.clock_quality} (offset median {r.clock.offset_estimate_ms_median} ms, "
          f"rtt median {r.clock.rtt_ms_median} ms)")
    for b in r.bars:
        d = b.delay_raw
        print(f"  {b.channel_key:34} updates {b.updates:5} completed {b.completed_bars:4} dup {b.duplicate_completed} "
              f"changed {b.post_completion_changes} ooo {b.out_of_order_updates} "
              f"delay_s[min {d.min_s} p50 {d.p50_s} p90 {d.p90_s} max {d.max_s} neg {d.negative_count}] "
              f"missing_healthy {len(b.missing_completions_while_healthy)}")
    f = r.funding
    print(f"  funding     ws snapshots {f.snapshots_ws}; poll snapshots {f.snapshots_poll}; "
          f"fundingTimes {[t.isoformat() for t in f.distinct_funding_times]}; transitions {len(f.funding_time_transitions)}")
    print(f"  outages {len(r.outages)}; unusable timing periods {len(r.unusable_timing_periods)}; errors {len(r.errors)}")
    try:
        bridge = build_recorded_feed(path)
        fm = bridge.feed.manifest
        print(f"  recorded feed: {fm.event_count} events {fm.event_counts}; policy {fm.availability_policy.policy_id}; "
              f"content {fm.content_identity}; excluded {len(bridge.excluded)}")
    except FeedError as exc:
        print(f"  recorded feed: not built ({exc})")


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


def _feed_inspect(args: argparse.Namespace) -> None:
    """Developer/Director inspection of the causal feed and observable state (not Owner UI)."""
    from datetime import timedelta

    from .feed.adapter import build_feed
    from .feed.ordering import default_freshness, modeled_availability
    from .feed.state import snapshot_at
    from .marketdata.dataset import dataset_path, parse_utc

    path = dataset_path(args.root, args.dataset_id)
    if path is None:
        sys.exit(f"no dataset {args.dataset_id} under {args.root}")
    policy = modeled_availability(timedelta(seconds=args.bar_delay_seconds),
                                  timedelta(seconds=args.funding_delay_seconds))
    feed = build_feed(path, policy)
    m = feed.manifest
    cutoff = parse_utc(args.cutoff)
    snap = snapshot_at(feed, cutoff, default_freshness(history_limit=args.history))
    if args.json:
        print(json.dumps({"feed": json.loads(m.model_dump_json()), "snapshot": json.loads(snap.model_dump_json())},
                         indent=2))
        return
    print(f"feed {m.schema_version} ({m.contract_status}, revision {m.schema_revision})")
    print(f"  dataset (evidence package)  {', '.join(m.dataset_ids)}")
    print(f"  content identity            {m.content_identity}")
    print(f"  ordering policy             {m.ordering_policy_id}")
    print(f"  availability policy         {m.availability_policy.policy_id} (measured={m.availability_policy.measured})")
    print(f"  events                      {m.event_count}  ordered-event sha256 {m.ordered_event_hash}")
    for k, v in m.event_counts.items():
        print(f"    {k:40} {v}")
    print(f"snapshot {snap.snapshot_id} as_of {snap.as_of.isoformat()} (cursor {snap.cursor.applied_events} events)")
    print(f"  content digest {snap.content_digest}; freshness policy {snap.freshness_policy_id}")
    for c in snap.channels:
        lv = c.latest_valid
        latest = "-"
        if lv is not None:
            p = lv.payload
            value = f"close {p.close}" if hasattr(p, "close") else f"rate {p.funding_rate}"
            latest = f"{lv.event_time.isoformat()} {value} (available {lv.available_time.isoformat()}, age {c.age_since_available})"
        print(f"  {c.channel_id:40} {c.condition.value:12} {c.freshness.value:14} latest {latest}")
        print(f"  {'':40} counts {c.counts.model_dump()} history {len(c.history)} beyond_coverage {c.beyond_coverage}")
    print("labels: " + ", ".join(snap.labels) + " (no interpretation, prediction or recommendation)")


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
    rw = sub.add_parser("recorder-worker", help="durable public market recorder worker (no trading)")
    rw.add_argument("--lease-seconds", type=float, default=30.0)
    rw.add_argument("--root", type=Path, default=None, help="data root (ALGOTRADER_DATA_ROOT)")
    rw.set_defaults(fn=_recorder_worker)
    ow = sub.add_parser("observe-worker", help="durable real-market observation-replay worker (no interpretation)")
    ow.add_argument("--lease-seconds", type=float,
                    default=float(os.environ.get("ALGOTRADER_OBSERVE_LEASE_SECONDS", 30)))
    ow.add_argument("--heartbeat-seconds", type=float, default=2.0)
    ow.add_argument("--poll-interval", type=float, default=0.5)
    ow.add_argument("--inline-compute", action="store_true",
                    help="diagnostics only: run compute in the supervisor process (heartbeat shares the GIL)")
    ow.add_argument("--root", type=Path, default=None, help="data root (ALGOTRADER_DATA_ROOT)")
    ow.set_defaults(fn=_observe_worker)
    cw = sub.add_parser("corpus-worker", help="durable corpus-preparation worker (public read-only OKX acquisition)")
    cw.add_argument("--lease-seconds", type=float, default=60.0)
    cw.add_argument("--poll-interval", type=float, default=1.0)
    cw.add_argument("--root", type=Path, default=None, help="data root (ALGOTRADER_DATA_ROOT)")
    cw.set_defaults(fn=_corpus_worker)
    rec = sub.add_parser("recorder", help="public market recorder tools (no trading)")
    rsub = rec.add_subparsers(dest="recorder_cmd", required=True)
    rr = rsub.add_parser("run", help="foreground bounded public recording session (integration check)")
    rr.add_argument("--minutes", type=float, required=True)
    rr.add_argument("--clock-probe-seconds", type=float, default=60.0)
    for opt in ("--ws-public-url", "--ws-business-url", "--rest-base-url"):
        rr.add_argument(opt, default=None)
    ri = rsub.add_parser("inspect", help="verify and summarize a recording session")
    ri.add_argument("session_id")
    for p_ in (rr, ri):
        p_.add_argument("--root", type=Path, default=None, help="data root (ALGOTRADER_DATA_ROOT)")
    rr.set_defaults(fn=_recorder_run)
    ri.set_defaults(fn=_recorder_inspect)
    sc = sub.add_parser("schema", help="check (default) or --write the semantic contract JSON Schema baseline")
    sc.add_argument("--write", action="store_true")
    sc.set_defaults(fn=_schema)


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

    fd = sub.add_parser("feed", help="causal feed / observable state inspection (developer tooling)")
    fsub = fd.add_subparsers(dest="feed_cmd", required=True)
    fi = fsub.add_parser("inspect", help="build a dataset's causal feed and print the snapshot at a cutoff")
    fi.add_argument("dataset_id")
    fi.add_argument("--cutoff", required=True, help="UTC knowledge cutoff, e.g. 2026-09-30T08:05Z")
    fi.add_argument("--bar-delay-seconds", type=float, default=0.0,
                    help="modeled extra availability delay for bars (assumption, not measured)")
    fi.add_argument("--funding-delay-seconds", type=float, default=0.0)
    fi.add_argument("--history", type=int, default=240, help="valid observations retained per channel")
    fi.add_argument("--json", action="store_true")
    common(fi)
    fi.set_defaults(fn=_feed_inspect)
    args = p.parse_args(argv)
    if hasattr(args, "root") and args.root is None:
        from .marketdata.dataset import default_data_root

        args.root = default_data_root()
    from .marketdata.dataset import DatasetError
    from .feed.ordering import FeedError
    from .marketdata.okx import SourceError

    try:
        args.fn(args)
    except (DatasetError, SourceError, FeedError) as exc:  # explicit, non-traceback failure for data/feed commands
        sys.exit(f"ERROR: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
