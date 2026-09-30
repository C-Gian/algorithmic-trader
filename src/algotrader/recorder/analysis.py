"""Measured-availability analysis of a recording session (pure; reads the raw journal).

Everything here is derived from retained raw evidence; nothing is corrected
in place. Delays are reported on the raw local clock and, separately, as an
estimate adjusted by the median observed offset to the OKX server clock.
A single session is evidence, not a universal latency constant.
"""

from __future__ import annotations

import json
import statistics
from collections.abc import Iterable, Iterator
from datetime import timedelta
from pathlib import Path
from typing import Any

from .contracts import (
    RECEIPT_POINT,
    RECORDER_SCHEMA_VERSION,
    BarChannelReport,
    ChannelFamily,
    ChannelReceipt,
    ChannelSpec,
    ClockReport,
    Connection,
    DelaySummary,
    FundingReport,
    Interval,
    JournalRecord,
    LifecycleEvent,
    ParseStatus,
    SessionConfig,
    SessionReport,
    SessionStatus,
)

BAR_NS = 60 * 1_000_000_000
BAR_FAMILIES = (ChannelFamily.TRADE_BAR_1M, ChannelFamily.MARK_BAR_1M, ChannelFamily.INDEX_BAR_1M)


def channel_map(config: SessionConfig) -> dict[tuple[str, str], ChannelSpec]:
    return {(c.channel, c.inst_id): c for c in config.channels}


def data_rows(rec: JournalRecord) -> list[Any]:
    if rec.parse_status != ParseStatus.DATA:
        return []
    try:
        doc = json.loads(rec.raw)
    except ValueError:
        return []
    data = doc.get("data")
    return data if isinstance(data, list) else []


def spec_for(rec: JournalRecord, cmap: dict[tuple[str, str], ChannelSpec]) -> ChannelSpec | None:
    if rec.channel is None or rec.inst_id is None:
        return None
    return cmap.get((rec.channel, rec.inst_id))


def iter_bar_rows(records: Iterable[JournalRecord], config: SessionConfig) -> Iterator[tuple[ChannelSpec, JournalRecord, list]]:
    cmap = channel_map(config)
    for rec in records:
        spec = spec_for(rec, cmap)
        if spec is None or spec.family not in BAR_FAMILIES or rec.kind != "ws_message":
            continue
        for row in data_rows(rec):
            if isinstance(row, list) and row and str(row[0]).isdigit():
                yield spec, rec, row


def build_bar_index(records: Iterable[JournalRecord], config: SessionConfig) -> Iterator[dict]:
    """First completed (confirm=1) receipt per (channel, bar), in receipt order."""
    seen: set[tuple[str, int]] = set()
    for spec, rec, row in iter_bar_rows(records, config):
        if str(row[-1]) != "1":
            continue
        key = (spec.key, int(row[0]))
        if key in seen:
            continue
        seen.add(key)
        yield {"channel_key": spec.key, "family": spec.family.value, "bar_open_ms": int(row[0]),
               "first_completed_seq": rec.seq, "first_completed_recv_utc_ns": rec.recv_utc_ns,
               "generation": rec.generation, "row": row}


def _summary(values_s: list[float], negative: int) -> DelaySummary:
    if not values_s:
        return DelaySummary(count=0, min_s=None, p50_s=None, p90_s=None, max_s=None, mean_s=None,
                            negative_count=negative)
    v = sorted(values_s)

    def pct(p: float) -> float:
        return v[min(len(v) - 1, max(0, round(p * (len(v) - 1))))]

    return DelaySummary(count=len(v), min_s=round(v[0], 6), p50_s=round(pct(0.5), 6), p90_s=round(pct(0.9), 6),
                        max_s=round(v[-1], 6), mean_s=round(statistics.fmean(v), 6), negative_count=negative)


def _dt(ns: int):
    from .journal import ns_to_dt

    return ns_to_dt(ns)


def build_report(path: Path, config: SessionConfig, lifecycle: list[LifecycleEvent], recovered: bool,
                 start_ns: int, stop_ns: int) -> tuple[SessionReport, dict]:
    from .journal import iter_clock, iter_records

    cmap = channel_map(config)
    per_channel: dict[str, dict] = {c.key: {"records": 0, "first": None, "last": None} for c in config.channels}
    bars: dict[str, dict] = {c.key: {"updates": 0, "forming": 0, "first": {}, "dup": 0, "changed": 0, "ooo": 0,
                                     "max_bar": None, "delays": []}
                             for c in config.channels if c.family in BAR_FAMILIES}
    funding = {"ws": 0, "poll": 0, "times": [], "transitions": [], "fields": set(), "last_time": None}
    errors: list[str] = []
    data_records = 0
    total = 0
    for rec in iter_records(path):
        total += 1
        spec = spec_for(rec, cmap)
        if rec.parse_status == ParseStatus.ERROR:
            errors.append(f"seq {rec.seq} {rec.connection}: {rec.raw[:240]}")
        if spec is not None:
            pc = per_channel[spec.key]
            pc["records"] += 1
            pc["first"] = pc["first"] if pc["first"] is not None else rec.recv_utc_ns
            pc["last"] = rec.recv_utc_ns
        if spec is None or rec.parse_status != ParseStatus.DATA:
            continue
        data_records += 1
        if spec.family in BAR_FAMILIES and rec.kind == "ws_message":
            b = bars[spec.key]
            for row in data_rows(rec):
                bar_ms, confirm = int(row[0]), str(row[-1])
                b["updates"] += 1
                if b["max_bar"] is not None and bar_ms < b["max_bar"]:
                    b["ooo"] += 1
                b["max_bar"] = max(b["max_bar"] or bar_ms, bar_ms)
                if bar_ms in b["first"]:
                    if confirm == "1" and row == b["first"][bar_ms]:
                        b["dup"] += 1
                    else:
                        b["changed"] += 1  # anything after completion that differs (kept raw)
                    continue
                if confirm == "1":
                    b["first"][bar_ms] = row
                    b["delays"].append((rec.recv_utc_ns - (bar_ms * 1_000_000 + BAR_NS)) / 1e9)
                else:
                    b["forming"] += 1
        elif spec.family == ChannelFamily.FUNDING_LIVE:
            funding["ws" if rec.kind == "ws_message" else "poll"] += 1
            for row in data_rows(rec):
                if not isinstance(row, dict):
                    continue
                funding["fields"].update(row)
                ft = row.get("fundingTime")
                if ft and ft not in funding["times"]:
                    funding["times"].append(ft)
                if funding["last_time"] is not None and ft != funding["last_time"]:
                    funding["transitions"].append(
                        f"{_dt(rec.recv_utc_ns).isoformat()} seq {rec.seq}: fundingTime {funding['last_time']} -> {ft} "
                        f"(settState={row.get('settState')}, settFundingRate={row.get('settFundingRate')})")
                funding["last_time"] = ft

    # lifecycle: subscriptions, connections, outages, healthy windows
    subscribed: set[str] = set()
    connections = 0
    connected_kinds: set[str] = set()
    outages: list[Interval] = []
    open_outage: dict[str, int] = {}
    healthy: dict[str, list[list[int | None]]] = {c.key: [] for c in config.channels}
    kind_of = {c.key: c.connection.value for c in config.channels}
    for ev in lifecycle:
        conn = ev.connection.value if ev.connection else None
        if ev.event == "connected":
            connections += 1
            connected_kinds.add(conn)
        elif ev.event == "subscribed" and ev.channel:
            subscribed.add(ev.channel)
            healthy.setdefault(ev.channel, []).append([ev.at_utc_ns, None])
            if conn in open_outage:
                outages.append(Interval(start=_dt(open_outage.pop(conn)), end=_dt(ev.at_utc_ns),
                                        connection=ev.connection, detail="disconnected until resubscribed"))
        elif ev.event in ("disconnected", "connect_failed", "closed") and conn:
            for key, windows in healthy.items():
                if kind_of.get(key) == conn and windows and windows[-1][1] is None:
                    windows[-1][1] = ev.at_utc_ns
            if ev.event != "closed":  # a requested stop is not a coverage outage
                open_outage.setdefault(conn, ev.at_utc_ns)
        if ev.event in ("connect_failed", "subscribe_error", "receive_error"):
            errors.append(f"lifecycle {ev.event} {conn or ''} {ev.channel or ''}: {ev.detail[:200]}")
    for conn, t in open_outage.items():
        outages.append(Interval(start=_dt(t), end=None, connection=Connection(conn),
                                detail="disconnected; not resubscribed before session end"))
    for windows in healthy.values():
        if windows and windows[-1][1] is None:
            windows[-1][1] = stop_ns
    reconnects = max(0, connections - len(connected_kinds))

    # clock
    clocks = list(iter_clock(path))
    ok = [c for c in clocks if c.status == "ok" and c.offset_estimate_ns is not None]
    offsets = sorted(c.offset_estimate_ns / 1e6 for c in ok)
    median_offset_ms = statistics.median(offsets) if offsets else None
    clock = ClockReport(
        observations=len(clocks), ok_observations=len(ok),
        offset_estimate_ms_min=offsets[0] if offsets else None,
        offset_estimate_ms_median=median_offset_ms,
        offset_estimate_ms_max=offsets[-1] if offsets else None,
        rtt_ms_median=statistics.median(c.rtt_ns / 1e6 for c in ok) if ok else None,
        clock_quality="observed" if ok else "unknown",
    )

    grace_ns = int(config.completion_grace.total_seconds() * 1e9)
    bar_reports = []
    for spec in config.channels:
        if spec.family not in BAR_FAMILIES:
            continue
        b = bars[spec.key]
        raw = b["delays"]
        missing = []
        for w0, w1 in healthy.get(spec.key, []):
            # bars whose end + grace fits inside the healthy window
            first_end = -(-w0 // BAR_NS) * BAR_NS
            end = first_end
            while end + grace_ns <= w1:
                bar_ms = (end - BAR_NS) // 1_000_000
                if bar_ms not in b["first"]:
                    missing.append(_dt(end - BAR_NS))
                end += BAR_NS
        adjusted = None
        if median_offset_ms is not None:
            adj = [d + median_offset_ms / 1000 for d in raw]
            adjusted = _summary(adj, sum(1 for d in adj if d < 0))
        bar_reports.append(BarChannelReport(
            channel_key=spec.key, family=spec.family, updates=b["updates"], forming_updates=b["forming"],
            completed_bars=len(b["first"]), duplicate_completed=b["dup"], post_completion_changes=b["changed"],
            out_of_order_updates=b["ooo"], delay_raw=_summary(raw, sum(1 for d in raw if d < 0)),
            delay_offset_adjusted=adjusted, missing_completions_while_healthy=tuple(sorted(set(missing))),
        ))

    unusable = list(outages)
    if clock.clock_quality == "unknown":
        unusable.append(Interval(start=_dt(start_ns), end=_dt(stop_ns), connection=None,
                                 detail="clock offset unknown (no successful server-time observation)"))
    requested = {c.key for c in config.channels}
    if data_records == 0:
        status = SessionStatus.FAILED
    elif recovered or reconnects or errors or outages or subscribed != requested:
        status = SessionStatus.PARTIAL
    else:
        status = SessionStatus.CLEAN
    report = SessionReport(
        schema_version=RECORDER_SCHEMA_VERSION,
        session_id=config.session_id,
        status=status,
        duration_s=round((stop_ns - start_ns) / 1e9, 3),
        receipt_point=RECEIPT_POINT,
        note=("Measured client receipt timing for this session only; not an exchange publication time and not a "
              "universal latency constant. Outages are recorder coverage loss, not market gaps. Missing "
              f"completions use a {config.completion_grace.total_seconds()} s grace on the local clock."),
        channels=tuple(
            ChannelReceipt(channel_key=c.key, family=c.family, subscribed=c.key in subscribed,
                           records=per_channel[c.key]["records"],
                           first_recv_utc=_dt(per_channel[c.key]["first"]) if per_channel[c.key]["first"] else None,
                           last_recv_utc=_dt(per_channel[c.key]["last"]) if per_channel[c.key]["last"] else None)
            for c in config.channels
        ),
        bars=tuple(bar_reports),
        funding=FundingReport(
            snapshots_ws=funding["ws"], snapshots_poll=funding["poll"],
            distinct_funding_times=tuple(_dt(int(t) * 1_000_000) for t in funding["times"]),
            funding_time_transitions=tuple(funding["transitions"]),
            fields_seen=tuple(sorted(funding["fields"])),
        ),
        clock=clock,
        outages=tuple(outages),
        unusable_timing_periods=tuple(unusable),
        errors=tuple(errors),
    )
    return report, {"subscribed": tuple(sorted(subscribed)), "connections": connections, "reconnects": reconnects,
                    "records": total}


def delay_of(bar_open_ms: int, recv_utc_ns: int) -> timedelta:
    return timedelta(microseconds=(recv_utc_ns - (bar_open_ms * 1_000_000 + BAR_NS)) // 1000)
