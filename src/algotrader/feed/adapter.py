"""Pure adapter: accepted ``algotrader.marketdata.v1`` dataset -> causal feed events.

Reads a verified dataset's manifest, normalized Parquet artifacts and (only to
classify *why* a slot is absent) its retained raw source pages. Never touches
the network or a database and never writes to the dataset.

Admission rules:

* a confirmed, OK-quality bar becomes a BAR_OBSERVATION;
* an INVALID row becomes a SLOT_QUALITY event (reason INVALID_ROW) carrying no
  numeric values into valid state;
* a bar slot inside the coverage window without a normalized row becomes a
  SLOT_QUALITY event, classified from the raw pages as CONFLICTING_DUPLICATE,
  INCOMPLETE_REJECTED (only confirm=0 seen) or MISSING;
* each settled funding row becomes a FUNDING_OBSERVATION;
* nothing is forward-filled and channels are never substituted for each other.

Availability = marketdata.v1 modeled availability + the feed policy's delay.
Event (economic) time is never changed by the availability transformation.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pyarrow.parquet as pq

from ..marketdata.contracts import DatasetManifest, Family as MdFamily, RawPageRef
from ..marketdata.dataset import load_manifest, verify
from .contracts import (
    BAR_FAMILIES,
    FEED_CONTRACT_STATUS,
    FEED_SCHEMA_REVISION,
    FEED_SCHEMA_VERSION,
    ORDERING_POLICY_ID,
    AvailabilityPolicy,
    ChannelCoverage,
    ChannelRef,
    EventKind,
    Family,
    FeedEvent,
    FeedManifest,
    FundingPayload,
    IndexBarPayload,
    MarkBarPayload,
    QualityReason,
    SlotQualityPayload,
    SourceRef,
    TradeBarPayload,
)
from .ordering import FeedError, digest, modeled_availability, order_events, order_key, ordered_event_hash

# Optional cooperative progress hook ``(stage, done, total, unit)``: called between bounded build units.
# It may raise to cancel and never changes the feed that is built.
BuildProgress = Callable[[str, int, int | None, str], None]


def _no_hook(stage: str, done: int, total: int | None, unit: str) -> None:  # noqa: ARG001
    return None

BAR = timedelta(minutes=1)
SOURCE = "okx"
CONTENT_IDENTITY_PREFIX = "feedcontent.v1:"

MD_FAMILY = {
    Family.TRADE_BAR_1M: MdFamily.TRADE_CANDLES,
    Family.MARK_BAR_1M: MdFamily.MARK_CANDLES,
    Family.INDEX_BAR_1M: MdFamily.INDEX_CANDLES,
    Family.FUNDING_SETTLEMENT: MdFamily.FUNDING,
}
KIND_TAG = {EventKind.BAR_OBSERVATION: "obs", EventKind.FUNDING_OBSERVATION: "obs", EventKind.SLOT_QUALITY: "quality"}


@dataclass(frozen=True)
class Feed:
    manifest: FeedManifest
    events: tuple[FeedEvent, ...]  # in deterministic causal order


def iso(t: datetime) -> str:
    return t.isoformat().replace("+00:00", "Z")


def event_id(channel: ChannelRef, kind: EventKind, event_time: datetime) -> str:
    return f"{channel.channel_id}#{KIND_TAG[kind]}@{iso(event_time)}"


def make_event(
    channel: ChannelRef,
    kind: EventKind,
    event_time: datetime,
    event_end_time: datetime | None,
    base_available: datetime,
    policy: AvailabilityPolicy,
    source: SourceRef,
    payload,
) -> FeedEvent:
    delay = policy.funding_delay if channel.family == Family.FUNDING_SETTLEMENT else policy.bar_delay
    available = base_available + delay
    if available < (event_end_time or event_time):
        raise FeedError(f"{channel.channel_id}: availability {available} precedes market time")
    eid = event_id(channel, kind, event_time)
    return FeedEvent(
        event_id=eid,
        channel=channel,
        kind=kind,
        event_time=event_time,
        event_end_time=event_end_time,
        available_time=available,
        availability_basis=policy.basis,
        availability_policy_id=policy.policy_id,
        source=source,
        order=order_key(eid, channel.family, channel.series_id, event_time, kind, available),
        payload=payload,
    )


# ---------------------------------------------------------------------------
# Content identity
# ---------------------------------------------------------------------------


def content_record(event: FeedEvent) -> dict:
    """Availability- and provenance-independent content of one event."""
    return {
        "channel": event.channel.channel_id,
        "kind": event.kind.value,
        "event_time": iso(event.event_time),
        "event_end_time": iso(event.event_end_time) if event.event_end_time else None,
        "payload": event.payload.model_dump(mode="json"),
    }


def content_identity(events: Iterable[FeedEvent], coverage: Iterable[ChannelCoverage], instrument: dict) -> str:
    """Identity of the normalized feed content, independent of acquisition packaging.

    Covers: schema version, instrument fields that define units/series, per-channel
    coverage windows and every event's channel/kind/market time/payload. Excludes
    dataset ids, base URL, pagination, retrieval times, raw page refs and the
    availability policy (which is recorded separately).
    """
    body = {
        "schema": FEED_SCHEMA_VERSION,
        "instrument": instrument,
        "coverage": sorted(
            (c.channel.channel_id, iso(c.covered_from), iso(c.covered_until),
             c.expected_cadence.total_seconds() if c.expected_cadence else None)
            for c in coverage
        ),
        "events": sorted(
            (content_record(e) for e in events), key=lambda r: (r["channel"], r["event_time"], r["kind"])
        ),
    }
    return CONTENT_IDENTITY_PREFIX + digest(body)


def assemble_feed(
    events: Iterable[FeedEvent],
    coverage: tuple[ChannelCoverage, ...],
    policy: AvailabilityPolicy,
    dataset_ids: tuple[str, ...],
    inst_id: str,
    index_id: str,
    instrument: dict,
    progress: BuildProgress | None = None,
) -> Feed:
    hook = progress or _no_hook
    hook("order events (single unit)", 0, 1, "stages")
    ordered = order_events(events)
    hook("order events (single unit)", 1, 1, "stages")
    counts: dict[str, int] = {}
    for e in ordered:
        key = f"{e.channel.family.value}/{e.kind.value}"
        counts[key] = counts.get(key, 0) + 1
    covered = {c.channel.channel_id for c in coverage}
    for e in ordered:
        if e.channel.channel_id not in covered:
            raise FeedError(f"event {e.event_id} has no declared channel coverage")
    hook("feed identity hashes (single unit)", 0, 1, "stages")
    manifest = FeedManifest(
        schema_version=FEED_SCHEMA_VERSION,
        contract_status=FEED_CONTRACT_STATUS,
        schema_revision=FEED_SCHEMA_REVISION,
        dataset_ids=dataset_ids,
        content_identity=content_identity(ordered, coverage, instrument),
        inst_id=inst_id,
        index_id=index_id,
        ordering_policy_id=ORDERING_POLICY_ID,
        availability_policy=policy,
        coverage=coverage,
        event_count=len(ordered),
        event_counts=dict(sorted(counts.items())),
        ordered_event_hash=ordered_event_hash(ordered),
    )
    hook("feed identity hashes (single unit)", 1, 1, "stages")
    return Feed(manifest, ordered)


# ---------------------------------------------------------------------------
# Dataset adapter
# ---------------------------------------------------------------------------


def _raw_slot_evidence(path: Path, pages: list[RawPageRef], md_family: MdFamily, lo: datetime, hi: datetime):
    """For bar families: raw confirmed rows per key and keys seen only unconfirmed."""
    confirmed: dict[int, set[str]] = {}
    unconfirmed: set[int] = set()
    lo_ms, hi_ms = int(lo.timestamp() * 1000), int(hi.timestamp() * 1000)
    for page in pages:
        if page.family != md_family:
            continue
        doc = json.loads((path / page.file).read_bytes())
        for row in doc.get("data", []):
            if not isinstance(row, list) or not row or not str(row[0]).isdigit():
                continue
            key = int(str(row[0]))
            if not lo_ms <= key < hi_ms:
                continue
            if str(row[-1]) == "1":
                confirmed.setdefault(key, set()).add(json.dumps(row))
            else:
                unconfirmed.add(key)
    return confirmed, unconfirmed


def _bar_payload(family: Family, row: dict):
    ohlc = {k: Decimal(row[k]) for k in ("open", "high", "low", "close")}
    if family == Family.TRADE_BAR_1M:
        return TradeBarPayload(
            **ohlc,
            volume_contracts=Decimal(row["volume_contracts"]),
            volume_base=Decimal(row["volume_base"]),
            volume_base_ccy=row["volume_base_ccy"],
            volume_quote=Decimal(row["volume_quote"]),
            volume_quote_ccy=row["volume_quote_ccy"],
        )
    if family == Family.MARK_BAR_1M:
        return MarkBarPayload(**ohlc)
    return IndexBarPayload(index_id=row["index_id"], **ohlc)


def build_feed(dataset_path: Path, policy: AvailabilityPolicy | None = None,
               progress: BuildProgress | None = None) -> Feed:
    """Transform one verified marketdata.v1 dataset into an ordered causal feed."""
    policy = policy or modeled_availability()
    hook = progress or _no_hook
    problems = verify(dataset_path, progress=lambda st, d, t, u: hook(f"re-verify inside feed build: {st}", d, t, u))
    if problems:
        raise FeedError(f"dataset {dataset_path.name} failed verification: {problems}")
    m: DatasetManifest = load_manifest(dataset_path)
    inst = m.instrument
    pages = [RawPageRef.model_validate_json(line)
             for line in (dataset_path / "request_log.jsonl").read_text(encoding="utf-8").splitlines()]
    start, end = m.request.start, m.request.end
    channels = {
        Family.TRADE_BAR_1M: ChannelRef(source=SOURCE, family=Family.TRADE_BAR_1M, series_id=inst.inst_id),
        Family.MARK_BAR_1M: ChannelRef(source=SOURCE, family=Family.MARK_BAR_1M, series_id=inst.inst_id),
        Family.INDEX_BAR_1M: ChannelRef(source=SOURCE, family=Family.INDEX_BAR_1M, series_id=inst.index_id),
        Family.FUNDING_SETTLEMENT: ChannelRef(source=SOURCE, family=Family.FUNDING_SETTLEMENT, series_id=inst.inst_id),
    }
    coverage = tuple(
        ChannelCoverage(channel=ch, covered_from=start, covered_until=end,
                        expected_cadence=BAR if fam in BAR_FAMILIES else None)
        for fam, ch in channels.items()
    )
    events: list[FeedEvent] = []
    for k, (fam, ch) in enumerate(channels.items()):
        hook("normalize families", k, len(channels), "families")
        artifact = f"{MD_FAMILY[fam].value}.parquet"
        rows = pq.read_table(dataset_path / artifact).to_pylist()

        def src(row_index: int | None, row: dict | None) -> SourceRef:
            return SourceRef(
                dataset_id=m.dataset_id,
                artifact=artifact,
                row_index=row_index,
                raw_page_ref=row["raw_page_ref"] if row else None,
                retrieved_at=row["retrieved_at"] if row else None,
                source_availability_policy=m.availability_policy,
            )

        if fam == Family.FUNDING_SETTLEMENT:
            for i, row in enumerate(rows):
                t = row["funding_time"]
                events.append(make_event(
                    ch, EventKind.FUNDING_OBSERVATION, t, None, row["available_time"], policy, src(i, row),
                    FundingPayload(
                        funding_rate=Decimal(row["funding_rate"]),
                        realized_rate=Decimal(row["realized_rate"]) if row["realized_rate"] is not None else None,
                        method=row["method"], formula_type=row["formula_type"],
                    ),
                ))
            continue

        present: set[datetime] = set()
        for i, row in enumerate(rows):
            t, close_t = row["open_time"], row["close_time"]
            present.add(t)
            if row["quality"] == "OK":
                events.append(make_event(ch, EventKind.BAR_OBSERVATION, t, close_t, row["available_time"], policy,
                                         src(i, row), _bar_payload(fam, row)))
            else:
                events.append(make_event(
                    ch, EventKind.SLOT_QUALITY, t, close_t, row["available_time"], policy, src(i, row),
                    SlotQualityPayload(reason=QualityReason.INVALID_ROW,
                                       detail="row failed source validity checks; values withheld from valid state",
                                       flags=tuple(row["quality_flags"] or ())),
                ))
        confirmed, unconfirmed = _raw_slot_evidence(dataset_path, pages, MD_FAMILY[fam], start, end)
        t = start
        while t < end:
            if t not in present:
                key = int(t.timestamp() * 1000)
                if len(confirmed.get(key, ())) > 1:
                    reason, detail = QualityReason.CONFLICTING_DUPLICATE, "source returned conflicting values; none admitted"
                elif key in unconfirmed and key not in confirmed:
                    reason, detail = QualityReason.INCOMPLETE_REJECTED, "only an unconfirmed (confirm=0) bar was returned"
                elif key in confirmed:
                    reason, detail = QualityReason.EXCLUDED_UNCLASSIFIED, "raw record present but not normalized"
                else:
                    reason, detail = QualityReason.MISSING, "no source record for this slot; not filled"
                # knowledge that the slot is absent is modeled at the slot's would-be availability
                events.append(make_event(
                    ch, EventKind.SLOT_QUALITY, t, t + BAR, t + BAR, policy,
                    SourceRef(dataset_id=m.dataset_id, artifact=f"{artifact} (absent slot)", row_index=None,
                              raw_page_ref=None, retrieved_at=None, source_availability_policy=m.availability_policy),
                    SlotQualityPayload(reason=reason, detail=detail),
                ))
            t += BAR

    instrument = {
        "inst_id": inst.inst_id, "index_id": inst.index_id, "ct_val": str(inst.ct_val),
        "ct_val_ccy": inst.ct_val_ccy, "ct_mult": str(inst.ct_mult), "base_ccy": inst.base_ccy,
        "quote_ccy": inst.quote_ccy, "settle_ccy": inst.settle_ccy,
    }
    hook("normalize families", len(channels), len(channels), "families")
    return assemble_feed(events, coverage, policy, (m.dataset_id,), inst.inst_id, inst.index_id, instrument,
                         progress=hook)


# ---------------------------------------------------------------------------
# Streaming dataset adapter (WP-008-R1B)
# ---------------------------------------------------------------------------
#
# Produces exactly the events of ``build_feed`` (same ids, payloads, sources, availability and quality
# classification) without materializing a family table, the event list or the raw-page key maps:
# parquet rows are read in bounded record batches and absent slots are classified against the raw pages
# only for the absent keys. The caller owns verification: this function is used inside a preparation
# trust boundary that has just verified the dataset once, so it does not verify again.
# Events are yielded per channel in source row order; the caller establishes the total order.


@dataclass(frozen=True)
class DatasetFeedMeta:
    dataset_id: str
    inst_id: str
    index_id: str
    coverage: tuple[ChannelCoverage, ...]
    instrument: dict
    channels: tuple[tuple[Family, ChannelRef], ...]


def dataset_feed_meta(dataset_path: Path) -> DatasetFeedMeta:
    m: DatasetManifest = load_manifest(dataset_path)
    inst = m.instrument
    channels = (
        (Family.TRADE_BAR_1M, ChannelRef(source=SOURCE, family=Family.TRADE_BAR_1M, series_id=inst.inst_id)),
        (Family.MARK_BAR_1M, ChannelRef(source=SOURCE, family=Family.MARK_BAR_1M, series_id=inst.inst_id)),
        (Family.INDEX_BAR_1M, ChannelRef(source=SOURCE, family=Family.INDEX_BAR_1M, series_id=inst.index_id)),
        (Family.FUNDING_SETTLEMENT, ChannelRef(source=SOURCE, family=Family.FUNDING_SETTLEMENT,
                                               series_id=inst.inst_id)),
    )
    start, end = m.request.start, m.request.end
    coverage = tuple(
        ChannelCoverage(channel=ch, covered_from=start, covered_until=end,
                        expected_cadence=BAR if fam in BAR_FAMILIES else None)
        for fam, ch in channels
    )
    instrument = {
        "inst_id": inst.inst_id, "index_id": inst.index_id, "ct_val": str(inst.ct_val),
        "ct_val_ccy": inst.ct_val_ccy, "ct_mult": str(inst.ct_mult), "base_ccy": inst.base_ccy,
        "quote_ccy": inst.quote_ccy, "settle_ccy": inst.settle_ccy,
    }
    return DatasetFeedMeta(m.dataset_id, inst.inst_id, inst.index_id, coverage, instrument, channels)


def _iter_rows(path: Path, batch_rows: int):
    pf = pq.ParquetFile(path)
    i = 0
    for batch in pf.iter_batches(batch_size=batch_rows):
        for row in batch.to_pylist():
            yield i, row
            i += 1


def _absent_slots(path: Path, start: datetime, end: datetime, batch_rows: int) -> set[int]:
    """Absent 1m slots in [start, end) from the open_time column, read in bounded batches."""
    absent: set[int] = set()
    expected = start
    for batch in pq.ParquetFile(path).iter_batches(batch_size=batch_rows, columns=["open_time"]):
        for t in batch.column(0).to_pylist():
            if t < expected - BAR:  # not in market-time order: exact fallback (bounded by the row count)
                return _absent_slots_unordered(path, start, end, batch_rows)
            while expected < t and expected < end:
                absent.add(int(expected.timestamp() * 1000))
                expected += BAR
            if t >= expected:
                expected = t + BAR
    while expected < end:
        absent.add(int(expected.timestamp() * 1000))
        expected += BAR
    return absent


def _absent_slots_unordered(path: Path, start: datetime, end: datetime, batch_rows: int) -> set[int]:
    present: set[datetime] = set()
    for batch in pq.ParquetFile(path).iter_batches(batch_size=batch_rows, columns=["open_time"]):
        present.update(batch.column(0).to_pylist())
    absent, t = set(), start
    while t < end:
        if t not in present:
            absent.add(int(t.timestamp() * 1000))
        t += BAR
    return absent


def _absent_slot_classes(path: Path, md_family: MdFamily, absent: set[int]):
    """Raw-page evidence restricted to the absent keys (bounded by the number of missing slots)."""
    confirmed: dict[int, set[str]] = {}
    unconfirmed: set[int] = set()
    if not absent:
        return confirmed, unconfirmed
    with (path / "request_log.jsonl").open(encoding="utf-8") as f:
        for line in f:
            page = RawPageRef.model_validate_json(line)
            if page.family != md_family:
                continue
            doc = json.loads((path / page.file).read_bytes())
            for row in doc.get("data", []):
                if not isinstance(row, list) or not row or not str(row[0]).isdigit():
                    continue
                key = int(str(row[0]))
                if key not in absent:
                    continue
                if str(row[-1]) == "1":
                    confirmed.setdefault(key, set()).add(json.dumps(row))
                else:
                    unconfirmed.add(key)
    return confirmed, unconfirmed


def iter_dataset_events(dataset_path: Path, policy: AvailabilityPolicy | None = None,
                        progress: BuildProgress | None = None, batch_rows: int = 4096):
    """Yield the events of ``build_feed(dataset_path, policy)`` (unordered across channels), streaming."""
    policy = policy or modeled_availability()
    hook = progress or _no_hook
    m: DatasetManifest = load_manifest(dataset_path)
    meta = dataset_feed_meta(dataset_path)
    start, end = m.request.start, m.request.end
    for k, (fam, ch) in enumerate(meta.channels):
        hook("stream normalized families", k, len(meta.channels), "families")
        artifact = f"{MD_FAMILY[fam].value}.parquet"
        apath = dataset_path / artifact

        def src(row_index: int | None, row: dict | None, artifact: str = artifact) -> SourceRef:
            return SourceRef(
                dataset_id=m.dataset_id, artifact=artifact, row_index=row_index,
                raw_page_ref=row["raw_page_ref"] if row else None,
                retrieved_at=row["retrieved_at"] if row else None,
                source_availability_policy=m.availability_policy,
            )

        if fam == Family.FUNDING_SETTLEMENT:
            for i, row in _iter_rows(apath, batch_rows):
                yield make_event(
                    ch, EventKind.FUNDING_OBSERVATION, row["funding_time"], None, row["available_time"], policy,
                    src(i, row),
                    FundingPayload(
                        funding_rate=Decimal(row["funding_rate"]),
                        realized_rate=Decimal(row["realized_rate"]) if row["realized_rate"] is not None else None,
                        method=row["method"], formula_type=row["formula_type"],
                    ))
            continue
        absent = _absent_slots(apath, start, end, batch_rows)
        for i, row in _iter_rows(apath, batch_rows):
            t, close_t = row["open_time"], row["close_time"]
            if row["quality"] == "OK":
                yield make_event(ch, EventKind.BAR_OBSERVATION, t, close_t, row["available_time"], policy,
                                 src(i, row), _bar_payload(fam, row))
            else:
                yield make_event(
                    ch, EventKind.SLOT_QUALITY, t, close_t, row["available_time"], policy, src(i, row),
                    SlotQualityPayload(reason=QualityReason.INVALID_ROW,
                                       detail="row failed source validity checks; values withheld from valid state",
                                       flags=tuple(row["quality_flags"] or ())),
                )
        confirmed, unconfirmed = _absent_slot_classes(dataset_path, MD_FAMILY[fam], absent)
        for key in sorted(absent):
            t = datetime.fromtimestamp(key / 1000, tz=start.tzinfo)
            if len(confirmed.get(key, ())) > 1:
                reason, detail = QualityReason.CONFLICTING_DUPLICATE, "source returned conflicting values; none admitted"
            elif key in unconfirmed and key not in confirmed:
                reason, detail = QualityReason.INCOMPLETE_REJECTED, "only an unconfirmed (confirm=0) bar was returned"
            elif key in confirmed:
                reason, detail = QualityReason.EXCLUDED_UNCLASSIFIED, "raw record present but not normalized"
            else:
                reason, detail = QualityReason.MISSING, "no source record for this slot; not filled"
            yield make_event(
                ch, EventKind.SLOT_QUALITY, t, t + BAR, t + BAR, policy,
                SourceRef(dataset_id=m.dataset_id, artifact=f"{artifact} (absent slot)", row_index=None,
                          raw_page_ref=None, retrieved_at=None, source_availability_policy=m.availability_policy),
                SlotQualityPayload(reason=reason, detail=detail),
            )
    hook("stream normalized families", len(meta.channels), len(meta.channels), "families")
