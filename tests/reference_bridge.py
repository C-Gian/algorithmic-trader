"""Independent in-memory reference of the recorded-session bridge (verbatim from accepted commit 17b5720).

Test-only: the production bridge streams with disk-backed dedup; this copy materializes everything exactly
like the accepted WP-005/WP-007 implementation so differential tests compare against code it does not share.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from algotrader.feed.adapter import Feed, assemble_feed, make_event
from algotrader.feed.contracts import (
    AvailabilityBasis,
    AvailabilityPolicy,
    ChannelCoverage,
    ChannelRef,
    EventKind,
    Family,
    IndexBarPayload,
    MarkBarPayload,
    QualityReason,
    SlotQualityPayload,
    SourceRef,
    TradeBarPayload,
)
from algotrader.feed.ordering import FeedError
from algotrader.marketdata.contracts import Family as MdFamily
from algotrader.marketdata.okx import MalformedResponse, RawResponse, parse_candle, parse_instrument
from algotrader.recorder.analysis import iter_bar_rows
from algotrader.recorder.contracts import ChannelFamily
from algotrader.recorder.journal import iter_lifecycle, iter_records, load_config, ns_to_dt

RECORDED_POLICY = AvailabilityPolicy(
    policy_id="feed.recorded.v1(first-completed-local-receipt)",
    basis=AvailabilityBasis.RECORDED,
    base_policy_id="recorder.v1 local receipt (client-observed, not exchange publication)",
    bar_delay=timedelta(0),
    funding_delay=timedelta(0),
    measured=True,
    note=("RECORDED availability: local client receipt time of the first completed (confirm=1) push, as recorded. "
          "Measured on the recording host's uncorrected wall clock; not the exchange publication time."),
)
FAMILY = {
    ChannelFamily.TRADE_BAR_1M: (Family.TRADE_BAR_1M, MdFamily.TRADE_CANDLES),
    ChannelFamily.MARK_BAR_1M: (Family.MARK_BAR_1M, MdFamily.MARK_CANDLES),
    ChannelFamily.INDEX_BAR_1M: (Family.INDEX_BAR_1M, MdFamily.INDEX_CANDLES),
}
BAR = timedelta(minutes=1)
FUNDING_NOTE = ("Live funding snapshots are pre-settlement/indicative information, not settlements; they are "
                "retained raw in the recording and deliberately not bridged into feed.v1 funding_settlement.")


@dataclass(frozen=True)
class BridgeResult:
    feed: Feed
    excluded: tuple[str, ...]
    funding_note: str


def _floor_minute(t: datetime) -> datetime:
    return t.replace(second=0, microsecond=0)


def build_recorded_feed(session: Path, until_utc_ns: int | None = None) -> BridgeResult:
    """Feed from the journal records received at or before ``until_utc_ns`` (default: all)."""
    config = load_config(session)
    records = list(iter_records(session, until_utc_ns))
    inst_rec = next((r for r in records if r.purpose == "instrument" and r.parse_status.value == "data"), None)
    if inst_rec is None:
        raise FeedError(f"session {config.session_id} has no recorded instrument snapshot")
    resp = RawResponse(base_url=config.endpoints.rest_base_url, path="/api/v5/public/instruments", params={},
                       url=inst_rec.endpoint, http_status=200, body=inst_rec.raw.encode("utf-8"),
                       retrieved_at=ns_to_dt(inst_rec.recv_utc_ns), code="0",
                       data=json.loads(inst_rec.raw)["data"])
    inst = parse_instrument(resp, config.inst_id, f"{config.session_id}#seq{inst_rec.seq}")
    channels: dict[str, ChannelRef] = {}
    events, excluded = [], []
    seen: set[tuple[str, int]] = set()
    for spec, rec, row in iter_bar_rows(records, config):
        if str(row[-1]) != "1":
            continue  # forming updates never become observations
        key = (spec.key, int(row[0]))
        if key in seen:
            continue  # first completed receipt wins; later completions stay raw evidence only
        seen.add(key)
        fam, md_fam = FAMILY[spec.family]
        ch = channels.setdefault(spec.key, ChannelRef(source="okx", family=fam, series_id=spec.inst_id))
        recv = ns_to_dt(rec.recv_utc_ns)
        src = SourceRef(dataset_id=config.session_id, artifact=f"journal seq {rec.seq}", row_index=rec.seq,
                        raw_page_ref=None, retrieved_at=recv, source_availability_policy=RECORDED_POLICY.base_policy_id)
        try:
            parsed = parse_candle(md_fam, row, inst, recv, f"{config.session_id}#seq{rec.seq}")
        except MalformedResponse as exc:
            excluded.append(f"{spec.key} bar {row[0]} seq {rec.seq}: malformed ({exc})")
            continue
        r = parsed.record
        if recv < r.close_time:
            excluded.append(f"{spec.key} bar {r.open_time.isoformat()} seq {rec.seq}: local receipt "
                            f"{recv.isoformat()} precedes bar end (clock inconsistency); not bridged")
            continue
        if r.quality_flags:
            payload = SlotQualityPayload(reason=QualityReason.INVALID_ROW, detail="recorded completed bar failed "
                                         "validity checks; values withheld", flags=r.quality_flags)
            kind = EventKind.SLOT_QUALITY
        else:
            kind = EventKind.BAR_OBSERVATION
            ohlc = dict(open=r.open, high=r.high, low=r.low, close=r.close)
            if fam == Family.TRADE_BAR_1M:
                payload = TradeBarPayload(**ohlc, volume_contracts=r.volume_contracts, volume_base=r.volume_base,
                                          volume_base_ccy=r.volume_base_ccy, volume_quote=r.volume_quote,
                                          volume_quote_ccy=r.volume_quote_ccy)
            elif fam == Family.MARK_BAR_1M:
                payload = MarkBarPayload(**ohlc)
            else:
                payload = IndexBarPayload(index_id=r.index_id, **ohlc)
        events.append(make_event(ch, kind, r.open_time, r.close_time, recv, RECORDED_POLICY, src, payload))

    lifecycle = list(iter_lifecycle(session))
    start = ns_to_dt(lifecycle[0].at_utc_ns) if lifecycle else datetime.now(UTC)
    end_ns = until_utc_ns if until_utc_ns is not None else max(
        [e.at_utc_ns for e in lifecycle] + [r.recv_utc_ns for r in records] + [lifecycle[0].at_utc_ns if lifecycle else 0])
    # evidence can speak until the exact cutoff/stop instant (not floored: flooring would claim
    # "beyond coverage" inside a minute that was still being recorded)
    covered_from, covered_until = _floor_minute(start), ns_to_dt(end_ns)
    for spec in config.channels:
        if spec.family in FAMILY:
            channels.setdefault(spec.key, ChannelRef(source="okx", family=FAMILY[spec.family][0], series_id=spec.inst_id))
    coverage = tuple(
        ChannelCoverage(channel=ch, covered_from=covered_from, covered_until=max(covered_until, covered_from),
                        expected_cadence=BAR)
        for ch in channels.values()
    )
    instrument = {"inst_id": inst.inst_id, "index_id": inst.index_id, "ct_val": str(inst.ct_val),
                  "ct_val_ccy": inst.ct_val_ccy, "ct_mult": str(inst.ct_mult), "base_ccy": inst.base_ccy,
                  "quote_ccy": inst.quote_ccy, "settle_ccy": inst.settle_ccy}
    feed = assemble_feed(events, coverage, RECORDED_POLICY, (config.session_id,), inst.inst_id, inst.index_id,
                         instrument)
    return BridgeResult(feed=feed, excluded=tuple(excluded), funding_note=FUNDING_NOTE)
