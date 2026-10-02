"""Pure bridge: recorded session -> ``algotrader.feed.v1`` RECORDED events.

Semantics:

* only the **first completed** (confirm=1) push of a bar becomes a feed event;
  its ``available_time`` is that message's local receipt time
  (``availability_basis=RECORDED``); forming pushes never become observations
  and later completed pushes never replace the first one (they stay raw
  evidence and are counted in the session report);
* identity/dedup is the explicit (channel, bar open time) first-completion
  rule applied while scanning the journal - it does not rely on the observable
  state's bounded history;
* validity uses the same parser/rules as WP-003 (invalid OHLC or volumes ->
  SLOT_QUALITY INVALID_ROW, no values in valid state);
* a completion whose local receipt precedes the bar end (clock inconsistency)
  is excluded and reported rather than clamped;
* recorder outages produce no events (no fabricated gaps or fills);
* live pre-settlement funding snapshots are *not* settlements and are not
  forced into ``funding_settlement``: they remain recorder-only in WP-005.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ..feed.adapter import Feed, assemble_feed, make_event
from ..feed.contracts import (
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
from ..feed.ordering import FeedError
from ..marketdata.contracts import Family as MdFamily
from ..marketdata.okx import MalformedResponse, RawResponse, parse_candle, parse_instrument
from .analysis import iter_bar_rows
from .contracts import ChannelFamily
from .journal import iter_lifecycle, iter_records, load_config, ns_to_dt

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


class RecordedStream:
    """Streaming form of the bridge (WP-008-R1B): journal records are read twice, never materialized.

    Iterate ``events()`` once; afterwards ``excluded``, ``coverage``, ``instrument``, ``inst_id`` and
    ``index_id`` describe the session exactly as ``build_recorded_feed`` would. The first-completion dedup
    keeps one key per (channel, bar) - inherent to the accepted rule and bounded by the session's bar count.
    """

    def __init__(self, session: Path, until_utc_ns: int | None = None) -> None:
        self.session, self.until = session, until_utc_ns
        self.config = load_config(session)
        self.excluded: list[str] = []
        self.coverage: tuple[ChannelCoverage, ...] = ()
        self.instrument: dict = {}
        self.inst = None
        self._channels: dict[str, ChannelRef] = {}

    def _instrument(self):
        config = self.config
        inst_rec = next((r for r in iter_records(self.session, self.until)
                         if r.purpose == "instrument" and r.parse_status.value == "data"), None)
        if inst_rec is None:
            raise FeedError(f"session {config.session_id} has no recorded instrument snapshot")
        resp = RawResponse(base_url=config.endpoints.rest_base_url, path="/api/v5/public/instruments", params={},
                           url=inst_rec.endpoint, http_status=200, body=inst_rec.raw.encode("utf-8"),
                           retrieved_at=ns_to_dt(inst_rec.recv_utc_ns), code="0",
                           data=json.loads(inst_rec.raw)["data"])
        return parse_instrument(resp, config.inst_id, f"{config.session_id}#seq{inst_rec.seq}")

    def events(self):
        config = self.config
        inst = self.inst = self._instrument()
        channels = self._channels
        seen: set[tuple[str, int]] = set()
        max_recv = 0

        def records():
            nonlocal max_recv
            for r in iter_records(self.session, self.until):
                max_recv = max(max_recv, r.recv_utc_ns)
                yield r

        for spec, rec, row in iter_bar_rows(records(), config):
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
                            raw_page_ref=None, retrieved_at=recv,
                            source_availability_policy=RECORDED_POLICY.base_policy_id)
            try:
                parsed = parse_candle(md_fam, row, inst, recv, f"{config.session_id}#seq{rec.seq}")
            except MalformedResponse as exc:
                self.excluded.append(f"{spec.key} bar {row[0]} seq {rec.seq}: malformed ({exc})")
                continue
            r = parsed.record
            if recv < r.close_time:
                self.excluded.append(f"{spec.key} bar {r.open_time.isoformat()} seq {rec.seq}: local receipt "
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
            yield make_event(ch, kind, r.open_time, r.close_time, recv, RECORDED_POLICY, src, payload)

        lifecycle = list(iter_lifecycle(self.session))
        start = ns_to_dt(lifecycle[0].at_utc_ns) if lifecycle else datetime.now(UTC)
        end_ns = self.until if self.until is not None else max(
            [e.at_utc_ns for e in lifecycle] + [max_recv] + [lifecycle[0].at_utc_ns if lifecycle else 0])
        # evidence can speak until the exact cutoff/stop instant (not floored: flooring would claim
        # "beyond coverage" inside a minute that was still being recorded)
        covered_from, covered_until = _floor_minute(start), ns_to_dt(end_ns)
        for spec in config.channels:
            if spec.family in FAMILY:
                channels.setdefault(spec.key, ChannelRef(source="okx", family=FAMILY[spec.family][0],
                                                         series_id=spec.inst_id))
        self.coverage = tuple(
            ChannelCoverage(channel=ch, covered_from=covered_from, covered_until=max(covered_until, covered_from),
                            expected_cadence=BAR)
            for ch in channels.values()
        )
        self.instrument = {"inst_id": inst.inst_id, "index_id": inst.index_id, "ct_val": str(inst.ct_val),
                           "ct_val_ccy": inst.ct_val_ccy, "ct_mult": str(inst.ct_mult), "base_ccy": inst.base_ccy,
                           "quote_ccy": inst.quote_ccy, "settle_ccy": inst.settle_ccy}


def build_recorded_feed(session: Path, until_utc_ns: int | None = None) -> BridgeResult:
    """Feed from the journal records received at or before ``until_utc_ns`` (default: all)."""
    stream = RecordedStream(session, until_utc_ns)
    events = list(stream.events())
    feed = assemble_feed(events, stream.coverage, RECORDED_POLICY, (stream.config.session_id,), stream.inst.inst_id,
                         stream.inst.index_id, stream.instrument)
    return BridgeResult(feed=feed, excluded=tuple(stream.excluded), funding_note=FUNDING_NOTE)
