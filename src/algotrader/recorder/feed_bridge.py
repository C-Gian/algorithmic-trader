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

    Iterate ``events()`` once; afterwards ``excluded`` (or ``iter_excluded()``), ``coverage``, ``instrument``
    and ``inst`` describe the session exactly as the in-memory bridge would. Working memory is bounded:
    the first-completion dedup keys and the exclusion list live in an on-disk sqlite index / spill file in a
    private work directory, lifecycle events are scanned for their first/max times only, and ``hook`` is
    called every ``HOOK_EVERY`` journal records (including long stretches of duplicates yielding nothing).
    """

    HOOK_EVERY = 1000

    def __init__(self, session: Path, until_utc_ns: int | None = None, *, workdir: Path | None = None,
                 hook=None) -> None:
        import tempfile

        self.session, self.until = session, until_utc_ns
        self.config = load_config(session)
        self._own_work = workdir is None
        self.work = Path(tempfile.mkdtemp(prefix="bridge-")) if workdir is None else workdir
        self.hook = hook or (lambda *_: None)
        self.coverage: tuple[ChannelCoverage, ...] = ()
        self.instrument: dict = {}
        self.inst = None
        self.excluded_count = 0
        self.dedup_max_rows = 0
        self._channels: dict[str, ChannelRef] = {}
        self._excl_path = self.work / "exclusions.jsonl"

    @property
    def excluded(self) -> list[str]:
        return list(self.iter_excluded())

    def iter_excluded(self):
        if not self._excl_path.is_file():
            return
        with self._excl_path.open(encoding="utf-8") as f:
            for line in f:
                yield json.loads(line)

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

    def close(self) -> None:
        if self._own_work:
            import shutil

            shutil.rmtree(self.work, ignore_errors=True)

    def events(self):
        import sqlite3

        config = self.config
        inst = self.inst = self._instrument()
        channels = self._channels
        self.work.mkdir(parents=True, exist_ok=True)
        dbp = self.work / "first-completion.sqlite"
        if dbp.exists():
            dbp.unlink()
        db = sqlite3.connect(dbp)
        db.execute("PRAGMA cache_size = -4096")
        db.execute("PRAGMA journal_mode = OFF")
        db.execute("PRAGMA synchronous = OFF")
        db.execute("CREATE TABLE seen (channel TEXT NOT NULL, bar INTEGER NOT NULL, PRIMARY KEY (channel, bar))")
        excl = self._excl_path.open("w", encoding="utf-8", newline="\n")
        max_recv = 0
        n_records = 0

        def records():
            nonlocal max_recv, n_records
            for r in iter_records(self.session, self.until):
                max_recv = max(max_recv, r.recv_utc_ns)
                n_records += 1
                if n_records % self.HOOK_EVERY == 0:
                    self.hook("bridge journal records (first-completion dedup)", n_records, None, "records")
                yield r

        def exclude(text: str) -> None:
            excl.write(json.dumps(text) + "\n")
            self.excluded_count += 1

        try:
            for spec, rec, row in iter_bar_rows(records(), config):
                if str(row[-1]) != "1":
                    continue  # forming updates never become observations
                cur = db.execute("INSERT OR IGNORE INTO seen (channel, bar) VALUES (?, ?)", (spec.key, int(row[0])))
                if cur.rowcount == 0:
                    continue  # first completed receipt wins; later completions stay raw evidence only
                self.dedup_max_rows += 1
                fam, md_fam = FAMILY[spec.family]
                ch = channels.setdefault(spec.key, ChannelRef(source="okx", family=fam, series_id=spec.inst_id))
                recv = ns_to_dt(rec.recv_utc_ns)
                src = SourceRef(dataset_id=config.session_id, artifact=f"journal seq {rec.seq}", row_index=rec.seq,
                                raw_page_ref=None, retrieved_at=recv,
                                source_availability_policy=RECORDED_POLICY.base_policy_id)
                try:
                    parsed = parse_candle(md_fam, row, inst, recv, f"{config.session_id}#seq{rec.seq}")
                except MalformedResponse as exc:
                    exclude(f"{spec.key} bar {row[0]} seq {rec.seq}: malformed ({exc})")
                    continue
                r = parsed.record
                if recv < r.close_time:
                    exclude(f"{spec.key} bar {r.open_time.isoformat()} seq {rec.seq}: local receipt "
                            f"{recv.isoformat()} precedes bar end (clock inconsistency); not bridged")
                    continue
                if r.quality_flags:
                    payload = SlotQualityPayload(reason=QualityReason.INVALID_ROW, detail="recorded completed bar "
                                                 "failed validity checks; values withheld", flags=r.quality_flags)
                    kind = EventKind.SLOT_QUALITY
                else:
                    kind = EventKind.BAR_OBSERVATION
                    ohlc = dict(open=r.open, high=r.high, low=r.low, close=r.close)
                    if fam == Family.TRADE_BAR_1M:
                        payload = TradeBarPayload(**ohlc, volume_contracts=r.volume_contracts,
                                                  volume_base=r.volume_base, volume_base_ccy=r.volume_base_ccy,
                                                  volume_quote=r.volume_quote, volume_quote_ccy=r.volume_quote_ccy)
                    elif fam == Family.MARK_BAR_1M:
                        payload = MarkBarPayload(**ohlc)
                    else:
                        payload = IndexBarPayload(index_id=r.index_id, **ohlc)
                yield make_event(ch, kind, r.open_time, r.close_time, recv, RECORDED_POLICY, src, payload)
        finally:
            excl.close()
            db.close()
            try:
                dbp.unlink()
            except OSError:
                pass

        first_ns, max_ns = None, 0
        for e in iter_lifecycle(self.session):  # streamed: only the first and the maximum time are kept
            first_ns = e.at_utc_ns if first_ns is None else first_ns
            max_ns = max(max_ns, e.at_utc_ns)
        start = ns_to_dt(first_ns) if first_ns is not None else datetime.now(UTC)
        end_ns = self.until if self.until is not None else max(
            [max_ns, max_recv] + [first_ns if first_ns is not None else 0])
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
    try:
        events = list(stream.events())
        excluded = tuple(stream.excluded)
    finally:
        stream.close()
    feed = assemble_feed(events, stream.coverage, RECORDED_POLICY, (stream.config.session_id,), stream.inst.inst_id,
                         stream.inst.index_id, stream.instrument)
    return BridgeResult(feed=feed, excluded=excluded, funding_note=FUNDING_NOTE)
