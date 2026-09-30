"""RP-001 case excerpt exporter (research tooling only; not imported by the application).

Reads one accepted, verified ``algotrader.marketdata.v1`` dataset through the accepted
``feed.v1`` adapter (MODELED zero-extra-delay availability) and writes a bounded,
provenance-linked excerpt of **traded** evidence for one case:

* ``prefix``  - only feed events with ``available_time <= cutoff`` (causally known at the cutoff);
* ``outcome`` - only traded 1m events with ``cutoff < available_time <= cutoff + horizon``,
  written to a separate file and never printed (outcome masking).

Aggregation follows RP-001B B1 / DC-02: a 5m or 1h bar is emitted as COMPLETE only if every
constituent 1m slot is a VALID bar observation known at the cutoff; otherwise its status is
QUALITY_AFFECTED or PENDING and no OHLC is emitted. A descriptive true-range column (DC-03
formula) is included to support manual labeling. This tool contains no swing, zone, scale,
trigger or recommendation logic (RP-001 hard stop).

Usage:
  uv run python research/first_trader/tools/export_case_excerpt.py prefix  --root DATA --dataset-id ID --cutoff 2026-09-28T04:00Z --out FILE [--m5-hours 12] [--m1-minutes 60]
  uv run python research/first_trader/tools/export_case_excerpt.py outcome --root DATA --dataset-id ID --cutoff 2026-09-28T04:00Z --out FILE [--horizon-minutes 240]
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

from algotrader.feed.adapter import build_feed
from algotrader.feed.contracts import EventKind, Family
from algotrader.feed.ordering import modeled_availability
from algotrader.marketdata.dataset import dataset_path, load_manifest, verify

MINUTE = timedelta(minutes=1)


def iso(t: datetime) -> str:
    return t.astimezone(UTC).strftime("%Y-%m-%dT%H:%MZ")


def parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(UTC)


def floor(t: datetime, width: timedelta) -> datetime:
    epoch = datetime(1970, 1, 1, tzinfo=UTC)
    return epoch + ((t - epoch) // width) * width


def load(root: Path, dataset_id: str):
    path = dataset_path(root, dataset_id)
    if path is None:
        raise SystemExit(f"dataset {dataset_id} not found under {root}")
    problems = verify(path)
    if problems:
        raise SystemExit(f"dataset {dataset_id} failed verification: {problems}")
    feed = build_feed(path, modeled_availability())
    manifest_sha = hashlib.sha256((path / "manifest.json").read_bytes()).hexdigest()
    return path, load_manifest(path), feed, manifest_sha


def traded_minutes(feed, known_until: datetime | None = None, after: datetime | None = None):
    """{minute_open_time: (kind, payload_or_reason, known_at)} for traded 1m slots within the window."""
    out = {}
    for e in feed.events:
        if e.channel.family != Family.TRADE_BAR_1M:
            continue
        if known_until is not None and e.available_time > known_until:
            continue
        if after is not None and e.available_time <= after:
            continue
        if e.kind == EventKind.BAR_OBSERVATION:
            p = e.payload
            out[e.event_time] = ("VALID", [float(p.open), float(p.high), float(p.low), float(p.close),
                                          float(p.volume_base)], e.available_time)
        else:
            out[e.event_time] = ("QUALITY", e.payload.reason.value, e.available_time)
    return out


def aggregate(minutes: dict, width: timedelta, start: datetime, end: datetime,
              coverage: tuple[datetime, datetime] | None = None) -> list[dict]:
    """Derived bars with open_time in [start, end) whose window closes at or before ``end``.

    Slots outside the evidence coverage window are BEYOND_COVERAGE (evidence cannot speak for them),
    distinct from PENDING (not yet known) and QUALITY_AFFECTED (a slot-quality event exists)."""
    n = int(width / MINUTE)
    bars, prev_close = [], None
    t = floor(start, width)
    while t + width <= end:
        slots = [minutes.get(t + i * MINUTE) for i in range(n)]
        if all(s is not None and s[0] == "VALID" for s in slots):
            o, h = slots[0][1][0], max(s[1][1] for s in slots)
            lo, c = min(s[1][2] for s in slots), slots[-1][1][3]
            tr = (max(h, prev_close) - min(lo, prev_close)) if prev_close is not None else (h - lo)
            bars.append({"t": iso(t), "status": "COMPLETE", "ohlc": [o, h, lo, c], "tr": round(tr, 1),
                         "known_at": iso(max(s[2] for s in slots))})
            prev_close = c
        else:
            if any(s is not None and s[0] == "QUALITY" for s in slots):
                status = "QUALITY_AFFECTED"
            elif coverage and (t < coverage[0] or t + width > coverage[1]):
                status = "BEYOND_COVERAGE"
            else:
                status = "PENDING"
            bars.append({"t": iso(t), "status": status})
            prev_close = None
        t += width
    return bars


def latest_context(feed, cutoff: datetime) -> dict:
    """Latest known mark/index close and settled funding (factual context only; never used in predicates)."""
    ctx: dict = {}
    for e in feed.events:
        if e.available_time > cutoff or e.kind == EventKind.SLOT_QUALITY:
            continue
        fam = e.channel.family
        if fam in (Family.MARK_BAR_1M, Family.INDEX_BAR_1M):
            ctx[fam.value] = {"bar_open": iso(e.event_time), "close": float(e.payload.close)}
        elif fam == Family.FUNDING_SETTLEMENT:
            ctx[fam.value] = {"funding_time": iso(e.event_time), "rate": str(e.payload.funding_rate)}
    return ctx


def provenance(manifest, feed, manifest_sha: str) -> dict:
    fm = feed.manifest
    return {
        "dataset_id": manifest.dataset_id,
        "dataset_manifest_sha256": manifest_sha,
        "source": f"{manifest.request.source} {manifest.request.base_url} {manifest.instrument.inst_id}",
        "requested": [iso(manifest.request.start), iso(manifest.request.end)],
        "feed_content_identity": fm.content_identity,
        "feed_ordered_event_hash": fm.ordered_event_hash,
        "availability_policy": fm.availability_policy.policy_id,
        "availability_basis": fm.availability_policy.basis.value,
        "price_role": "traded (trade_bar_1m)",
        "tool": "research/first_trader/tools/export_case_excerpt.py",
    }


def cmd_prefix(a) -> None:
    _, m, feed, sha = load(a.root, a.dataset_id)
    cutoff = parse(a.cutoff)
    minutes = traded_minutes(feed, known_until=cutoff)
    start = m.request.start
    m1_from = cutoff - timedelta(minutes=a.m1_minutes)
    doc = {
        "kind": "RP-001 visible prefix (causally known at cutoff)",
        "visible_prefix_cutoff": iso(cutoff),
        "provenance": provenance(m, feed, sha),
        "bars_1h": aggregate(minutes, timedelta(hours=1), start, cutoff, (start, m.request.end)),
        "bars_5m": aggregate(minutes, timedelta(minutes=5), max(start, cutoff - timedelta(hours=a.m5_hours)), cutoff,
                             (start, m.request.end)),
        "bars_1m": [{"t": iso(t), "status": v[0], **({"ohlc": v[1][:4]} if v[0] == "VALID" else {"reason": v[1]})}
                    for t, v in sorted(minutes.items()) if m1_from <= t < cutoff],
        "factual_context_not_used_in_predicates": latest_context(feed, cutoff),
    }
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    print(f"prefix written: {a.out} (1h {len(doc['bars_1h'])}, 5m {len(doc['bars_5m'])}, 1m {len(doc['bars_1m'])})")


def cmd_outcome(a) -> None:
    _, m, feed, sha = load(a.root, a.dataset_id)
    cutoff = parse(a.cutoff)
    until = cutoff + timedelta(minutes=a.horizon_minutes)
    minutes = traded_minutes(feed, known_until=until, after=cutoff)
    doc = {
        "kind": "RP-001 hidden outcome suffix (known strictly after cutoff) - do not read before the prefix label is frozen",
        "visible_prefix_cutoff": iso(cutoff),
        "suffix_until": iso(until),
        "provenance": provenance(m, feed, sha),
        "bars_1m": [{"t": iso(t), "status": v[0], **({"ohlc": v[1][:4]} if v[0] == "VALID" else {"reason": v[1]})}
                    for t, v in sorted(minutes.items())],
        "bars_5m": aggregate(traded_minutes(feed, known_until=until), timedelta(minutes=5), cutoff, until,
                             (m.request.start, m.request.end)),
    }
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    print(f"outcome written: {a.out} ({len(doc['bars_1m'])} 1m slots) - contents not displayed")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("prefix", "outcome"):
        s = sub.add_parser(name)
        s.add_argument("--root", type=Path, required=True)
        s.add_argument("--dataset-id", required=True)
        s.add_argument("--cutoff", required=True)
        s.add_argument("--out", required=True)
        if name == "prefix":
            s.add_argument("--m5-hours", type=float, default=12.0)
            s.add_argument("--m1-minutes", type=int, default=60)
        else:
            s.add_argument("--horizon-minutes", type=int, default=240)
    a = p.parse_args()
    (cmd_prefix if a.cmd == "prefix" else cmd_outcome)(a)


if __name__ == "__main__":
    main()
