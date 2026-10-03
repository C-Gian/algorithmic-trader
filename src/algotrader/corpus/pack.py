"""Immutable evaluation packs: inventory, slice planning, composition, publication and replay source.

Flow (owned by the durable pack job in ``pack_job``; nothing here touches the network):

1. **Inventory/plan** - compatible local ``marketdata.v1`` packages (same public OKX source, instrument, 1m bar, all
   four historical families, official host) are found by their logical request, not by directory names. The full
   requested interval [warmup start, tail end) is covered by deterministic slices of those packages (bound corpus
   datasets first, then the longest covering package); uncovered ranges become acquisition requests split at UTC
   month boundaries and the 31-day acquisition bound.
2. **Per-source caches** - every contributing package is prepared through the accepted R1B trust boundary
   (private snapshot, verify once, receipt-pinned immutable feed cache; warm reuse on later runs).
3. **Composition** - events of each slice are read from its pinned cache, grouped by (channel, slot) with the
   bounded external sorter and resolved by ``COMPOSITION_POLICY`` (identical collapse, MISSING superseded by
   valid evidence, conflicts fail). The result streams into ONE canonical feed cache over the full requested
   interval (accepted ordering, availability and admission semantics; no eager feed, no per-month runs).
4. **Manifest/publication** - a deterministic ``algotrader.corpus-pack.v1`` manifest (identity = SHA-256 of its
   body) is staged, fsynced and published by one directory rename under ``packs/<pack_id>/``, then pinned by a
   receipt row (``corpus_packs``). The pack job commits rename + receipt + COMPLETED under its fenced row lock.

Replay (``prepare_pack_source``) accepts a pack only when its manifest file SHA-256 equals the receipt, its body
re-hashes to its id and its feed cache matches the cache receipt; a lost or corrupt cache is rebuilt from the pinned
source slices and must reproduce the receipt exactly.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from ..feed.adapter import content_record
from ..feed.contracts import (
    REJECTED_REASONS,
    ChannelCoverage,
    EventKind,
    Family,
    FeedEvent,
    QualityReason,
)
from ..feed.ordering import canonical, modeled_availability
from ..marketdata import dataset as md
from ..marketdata.contracts import HISTORICAL_FAMILIES, DatasetManifest
from ..marketdata.okx_authority import validate_okx_rest_base_url
from ..observe import feedcache as fc
from . import presets as ps
from .pack_contracts import (
    COMPOSITION_POLICY,
    DEFINITION_FIELDS,
    METADATA_POLICY,
    PACK_CONTRACT_STATUS,
    PACK_SCHEMA_REVISION,
    PACK_SCHEMA_VERSION,
    SLICE_POLICY,
    CapabilityFact,
    FeedRef,
    InstrumentPin,
    OverlapSummary,
    PackManifest,
    SourceSlice,
    WindowCounts,
)

MIN = timedelta(minutes=1)
PACK_LABELS = ("REAL_MARKET_EVIDENCE", "OBSERVATION_ONLY", "NO_ADVISER", "NO_INTERPRETATION")
BAR_FAMILIES = (Family.TRADE_BAR_1M, Family.MARK_BAR_1M, Family.INDEX_BAR_1M)
Hook = Callable[[str, int, int | None, str], None]


class PackError(Exception):
    """A pack cannot be planned, composed, published or trusted."""


class CompositionConflict(PackError):
    """Two contributors disagree about the same semantic slot (never resolved by first/last wins)."""


def _no_hook(stage: str, done: int, total: int | None, unit: str) -> None:  # noqa: ARG001
    return None


def packs_root(data_root: Path) -> Path:
    return data_root / "packs"


def _iso(t: datetime) -> str:
    return t.isoformat().replace("+00:00", "Z")


# ---------------------------------------------------------------------------
# 1. Local inventory and slice planning (no hashing, no network)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LocalSource:
    dataset_id: str
    request_start: datetime
    request_end: datetime
    bound: bool  # bound to a corpus chunk (the accepted September preparation)
    bytes: int
    manifest: DatasetManifest = field(repr=False, compare=False)


def compatible(m: DatasetManifest, inst_id: str) -> bool:
    r = m.request
    try:
        validate_okx_rest_base_url(r.base_url)
    except ValueError:
        return False
    return (r.source == "okx" and r.inst_id == inst_id and r.bar == "1m"
            and set(r.families) == set(HISTORICAL_FAMILIES))


def local_sources(data_root: Path, inst_id: str, bound_ids: set[str] = frozenset()) -> list[LocalSource]:
    out = []
    for m in md.list_manifests(data_root):
        if not compatible(m, inst_id):
            continue
        out.append(LocalSource(m.dataset_id, m.request.start, m.request.end, m.dataset_id in bound_ids,
                               sum(f.bytes for f in m.files), m))
    return sorted(out, key=lambda s: (s.request_start, s.dataset_id))


@dataclass(frozen=True)
class PlannedSlice:
    dataset_id: str
    start: datetime
    end: datetime


@dataclass(frozen=True)
class Plan:
    slices: tuple[PlannedSlice, ...]
    missing: tuple[tuple[datetime, datetime], ...]  # uncovered ranges of the requested interval
    acquisitions: tuple[tuple[datetime, datetime], ...]  # missing ranges split at months / the 31-day bound


def split_requests(lo: datetime, hi: datetime, max_days: int = 31) -> list[tuple[datetime, datetime]]:
    """Split [lo, hi) at UTC calendar-month boundaries and the bounded acquisition span."""
    out, t = [], lo
    while t < hi:
        month_end = ps.add_months(t.replace(day=1, hour=0, minute=0), 1)
        e = min(hi, month_end, t + timedelta(days=max_days))
        out.append((t, e))
        t = e
    return out


def plan_slices(sources: list[LocalSource], lo: datetime, hi: datetime, max_days: int = 31) -> Plan:
    """Deterministic cover of [lo, hi): bound datasets first, then the longest covering package, then id."""
    slices, missing, t = [], [], lo
    while t < hi:
        cands = [s for s in sources if s.request_start <= t < s.request_end]
        if cands:
            best = sorted(cands, key=lambda s: (not s.bound, -s.request_end.timestamp(), s.dataset_id))[0]
            e = min(best.request_end, hi)
            slices.append(PlannedSlice(best.dataset_id, t, e))
            t = e
        else:
            nxt = min([s.request_start for s in sources if s.request_start > t] + [hi])
            missing.append((t, nxt))
            t = nxt
    acq = [r for a, b in missing for r in split_requests(a, b, max_days)]
    return Plan(tuple(slices), tuple(missing), tuple(acq))


def estimate_bytes(sources: list[LocalSource], acquisitions: tuple[tuple[datetime, datetime], ...]) -> dict:
    """Estimated download size from the measured bytes/minute of local packages (an estimate, with its basis)."""
    minutes = sum(int((b - a) / MIN) for a, b in acquisitions)
    basis_bytes = sum(s.bytes for s in sources)
    basis_minutes = sum(int((s.request_end - s.request_start) / MIN) for s in sources)
    if not acquisitions:
        return {"estimated_bytes": 0, "minutes": 0, "basis": "nothing to download"}
    if not basis_minutes:
        return {"estimated_bytes": None, "minutes": minutes,
                "basis": "unknown: no local package to measure bytes per minute from"}
    per = basis_bytes / basis_minutes
    return {"estimated_bytes": int(per * minutes), "minutes": minutes,
            "basis": f"ESTIMATE: {per:,.0f} bytes/minute measured over {len(sources)} local package(s); actual "
                     "stored bytes are reported after preparation"}


# ---------------------------------------------------------------------------
# 2. Composition
# ---------------------------------------------------------------------------


@dataclass
class Contributor:
    dataset_id: str
    source_manifest_sha256: str
    request_start: datetime
    request_end: datetime
    start: datetime
    end: datetime
    origin: str
    cache: Any  # feedcache.FeedCache (receipt-pinned)
    instrument: Any  # marketdata InstrumentSnapshot of the package
    source_bytes: int = 0  # bytes of the immutable source package (referenced, never copied)

    def slice(self) -> SourceSlice:
        return SourceSlice(dataset_id=self.dataset_id, source_manifest_sha256=self.source_manifest_sha256,
                           request_start=self.request_start, request_end=self.request_end, start=self.start,
                           end=self.end, cache_id=self.cache.cache_id,
                           cache_manifest_sha256=self.cache.manifest_sha256)


def definition(inst) -> dict[str, str]:
    return {k: str(getattr(inst, k)) for k in DEFINITION_FIELDS}


@dataclass
class CompositionStats:
    windows: dict[str, tuple[datetime, datetime]]
    counts: dict[tuple[str, str], dict] = field(default_factory=dict)
    overlapping_slots: int = 0
    identical_collapsed: int = 0
    gap_replaced: int = 0
    composed_events: int = 0
    trade_invalid_warmup: set = field(default_factory=set)
    matched_ref_valid: dict = field(default_factory=dict)  # family -> set of valid minutes before eval start
    provenance_lines: int = 0

    def window_of(self, t: datetime) -> str | None:
        for name, (a, b) in self.windows.items():
            if a <= t < b:
                return name
        return None

    def count(self, e: FeedEvent) -> None:
        w = self.window_of(e.event_time)
        if w is None:
            return
        fam = e.channel.family.value
        c = self.counts.setdefault((fam, w), {"valid": 0, "missing": 0, "rejected": 0, "reasons": {}})
        if e.kind == EventKind.SLOT_QUALITY:
            r = e.payload.reason
            c["reasons"][r.value] = c["reasons"].get(r.value, 0) + 1
            c["missing" if r == QualityReason.MISSING else "rejected"] += 1
            if e.channel.family == Family.TRADE_BAR_1M and w == "warmup":
                self.trade_invalid_warmup.add(e.event_time)
        else:
            c["valid"] += 1
            ev_start = self.windows["evaluation"][0]
            if e.channel.family in (Family.MARK_BAR_1M, Family.INDEX_BAR_1M) and \
                    ev_start - 61 * MIN <= e.event_time < ev_start:
                self.matched_ref_valid.setdefault(e.channel.family.value, set()).add(e.event_time)


def _slot(line_key: bytes) -> bytes:
    return line_key.rsplit(b"\x00", 1)[0]


def _primary_key(c: Contributor, e: FeedEvent) -> tuple:
    return (c.source_manifest_sha256, c.dataset_id, e.source.artifact,
            e.source.row_index if e.source.row_index is not None else -1)


def compose_events(contribs: list[Contributor], lo: datetime, hi: datetime, stats: CompositionStats,
                   workdir: Path, hook: Hook = _no_hook, provenance: Path | None = None) -> Iterator[FeedEvent]:
    """Deduplicated composed events (unordered; the cache build orders them canonically)."""
    workdir.mkdir(parents=True, exist_ok=True)
    sorter = fc.ExternalSorter(workdir, "compose", hook=hook)
    prov = provenance.open("w", encoding="utf-8", newline="\n") if provenance is not None else None
    try:
        n = 0
        for ci, c in enumerate(contribs):
            reader = fc.CacheReader(c.cache)
            for _seq, line in reader.iter_from(0):
                e = fc.decode(line)
                if not (c.start <= e.event_time < c.end and lo <= e.event_time < hi):
                    continue
                key = (e.channel.channel_id + "\x00" + fc._ts(e.event_time)).encode() + b"\x00" + f"{ci:05d}".encode()
                sorter.add(key, line)
                n += 1
                if n % 5000 == 0:
                    hook("read source slices", n, None, "events")
        hook("read source slices", n, n, "events")
        group: list[tuple[int, FeedEvent]] = []
        prev = None
        done = 0
        for key, line in sorter.merged():
            slot = _slot(key)
            if prev is not None and slot != prev:
                yield _resolve(group, contribs, stats, prov)
                group = []
            prev = slot
            group.append((int(key.rsplit(b"\x00", 1)[1]), fc.decode(line)))
            done += 1
            if done % 5000 == 0:
                hook("compose slots", done, n, "events")
        if group:
            yield _resolve(group, contribs, stats, prov)
        hook("compose slots", done, n, "events")
    finally:
        sorter.close()
        if prov is not None:
            prov.close()


def _resolve(group: list[tuple[int, FeedEvent]], contribs: list[Contributor], stats: CompositionStats,
             prov) -> FeedEvent:
    e0 = group[0][1]
    where = f"{e0.channel.channel_id} @ {_iso(e0.event_time)}"
    names = [contribs[ci].dataset_id for ci, _ in group]
    if len(group) == 1:
        chosen = e0
    else:
        stats.overlapping_slots += 1
        valid = [(ci, e) for ci, e in group if e.kind != EventKind.SLOT_QUALITY]
        quality = [(ci, e) for ci, e in group if e.kind == EventKind.SLOT_QUALITY]
        if valid:
            contents = {canonical(content_record(e)) for _, e in valid}
            if len(contents) > 1:
                raise CompositionConflict(f"conflicting evidence for {where} between {sorted(set(names))}: "
                                          "different OHLC/volume/settlement values (never first/last wins)")
            rejected = [e for _, e in quality if e.payload.reason in REJECTED_REASONS]
            if rejected:
                raise CompositionConflict(f"conflicting evidence for {where}: rejected "
                                          f"({rejected[0].payload.reason.value}) in one contributor, valid in another")
            ci, chosen = min(valid, key=lambda x: _primary_key(contribs[x[0]], x[1]))
            stats.identical_collapsed += len(valid) - 1
            stats.gap_replaced += len(quality)
        else:
            reasons = {e.payload.reason for _, e in quality}
            if len(reasons) > 1:
                raise CompositionConflict(f"conflicting quality evidence for {where}: "
                                          f"{sorted(r.value for r in reasons)}")
            ci, chosen = min(quality, key=lambda x: _primary_key(contribs[x[0]], x[1]))
            stats.identical_collapsed += len(quality) - 1
        if prov is not None:
            prov.write(json.dumps({"slot": where, "kind": chosen.kind.value, "chosen": contribs[ci].dataset_id,
                                   "contributors": names}, sort_keys=True) + "\n")
            stats.provenance_lines += 1
    stats.composed_events += 1
    stats.count(chosen)
    return chosen


def readiness_preview(stats: CompositionStats) -> dict:
    """Input readiness preview — no adviser: complete trade bars and matched reference minutes before evaluation."""
    w0, ev = stats.windows["warmup"][0], stats.windows["evaluation"][0]

    def contiguous(minutes: int) -> int:
        n, end = 0, ev
        while end - minutes * MIN >= w0:
            start = end - minutes * MIN
            if any(start <= t < end for t in stats.trade_invalid_warmup):
                break
            n += 1
            end = start
        return n

    mark = stats.matched_ref_valid.get(Family.MARK_BAR_1M.value, set())
    index = stats.matched_ref_valid.get(Family.INDEX_BAR_1M.value, set())
    matched, t = 0, ev - MIN
    while t >= ev - 61 * MIN and t in mark and t in index:
        matched += 1
        t -= MIN
    m15, h1 = contiguous(15), contiguous(60)
    return {
        "label": "input readiness preview — no adviser",
        "at": _iso(ev),
        "trade_15m_contiguous_complete": m15, "trade_15m_required_by_mp001": 25,
        "trade_1h_contiguous_complete": h1, "trade_1h_required_by_mp001": 21,
        "matched_mark_index_minutes_before_evaluation": matched, "matched_reference_desired_by_mp001": 60,
        "note": ("counts of complete input bars available before the evaluation start; no adviser predicate is "
                 "implemented or evaluated, and R2 demonstration readiness is not relabelled as the method"),
    }


def coverage_counts(stats: CompositionStats) -> tuple[WindowCounts, ...]:
    out = []
    for fam in (*BAR_FAMILIES, Family.FUNDING_SETTLEMENT):
        for w, (a, b) in stats.windows.items():
            c = stats.counts.get((fam.value, w), {"valid": 0, "missing": 0, "rejected": 0, "reasons": {}})
            out.append(WindowCounts(family=fam.value, window=w,
                                    expected_slots=int((b - a) / MIN) if fam in BAR_FAMILIES else None,
                                    valid=c["valid"], missing=c["missing"], rejected=c["rejected"],
                                    reasons=dict(sorted(c["reasons"].items()))))
    return tuple(out)


def capabilities(stats: CompositionStats, profile: dict[str, str]) -> tuple[tuple[CapabilityFact, ...], list[str]]:
    """Capability facts and visible limitations (never certifying absent evidence as neutral or complete)."""
    facts, limits = [], []

    def total(fam: Family, key: str) -> int:
        return sum(c[key] for (f, _w), c in stats.counts.items() if f == fam.value)

    def gaps(fam: Family) -> int:
        return total(fam, "missing") + total(fam, "rejected")

    tg = gaps(Family.TRADE_BAR_1M)
    facts.append(CapabilityFact(capability="trade_1m", status="OBSERVED_WITH_GAPS" if tg else "OBSERVED_COMPLETE",
                                detail=f"{total(Family.TRADE_BAR_1M, 'valid')} valid minutes; {tg} missing/rejected "
                                       "slots kept as explicit quality events (never filled)"))
    if tg:
        limits.append(f"trade 1m has {tg} missing/rejected slot(s): prepared WITH GAPS, not complete market coverage")
    for fam in (Family.MARK_BAR_1M, Family.INDEX_BAR_1M):
        g = gaps(fam)
        facts.append(CapabilityFact(capability=fam.value.replace("_bar_1m", "_1m"),
                                    status=f"{profile.get('dislocation', 'ENABLE_WHERE_SUPPORTED')}: "
                                           + ("OBSERVED_WITH_GAPS" if g else "OBSERVED_COMPLETE"),
                                    detail=f"{total(fam, 'valid')} valid minutes; {g} missing/rejected; optional "
                                           "reference context, never a veto of the price core"))
        if g:
            limits.append(f"{fam.value} has {g} missing/rejected slot(s) (optional reference context)")
    nf = total(Family.FUNDING_SETTLEMENT, "valid")
    facts.append(CapabilityFact(
        capability="funding_settlements",
        status="OBSERVED_ROWS_NOT_COMPLETENESS_PROOF" if nf else "EMPTY_UNKNOWN",
        detail=(f"{nf} settlement row(s) observed; returned rows never certify that no other settlement occurred "
                "(no eight-hour schedule is assumed); outcome funding therefore PRICE_NET_ONLY / "
                "TOTAL_NET_UNAVAILABLE until completeness is proven")))
    limits.append("funding completeness unproven: future outcome reporting is PRICE_NET_ONLY (TOTAL_NET_UNAVAILABLE)")
    facts.append(CapabilityFact(capability="event_calendar", status=profile.get("calendar", "NONE_UNKNOWN"),
                                detail="no historical as-known event schedule exists; a present-day calendar is not "
                                       "historical known-at evidence; unknown is not 'no event'"))
    facts.append(CapabilityFact(capability="incident_tape", status=profile.get("incident_tape", "NOT_COVERED"),
                                detail="no incident collector in R3"))
    facts.append(CapabilityFact(capability="quotes_oi_liquidations_depth_flow", status="NOT_COVERED",
                                detail="no obtainable historical input assigned; execution stays a declared "
                                       "bar/delay/cost model, never live quote parity"))
    facts.append(CapabilityFact(capability="instrument_metadata", status=METADATA_POLICY,
                                detail="pinned retrieval-time snapshot assumed for the window; not historical "
                                       "effective-date proof"))
    limits.append("instrument definition is a retrieval-time snapshot assumed for the whole window (approximation)")
    facts.append(CapabilityFact(capability="source_capability_probes", status="NOT_PROBED",
                                detail="no live capability probe was executed for this pack; coverage facts come "
                                       "only from the verified source packages"))
    return tuple(facts), limits


# ---------------------------------------------------------------------------
# 3. Pack cache build, manifest, publication
# ---------------------------------------------------------------------------


def pack_cache_key(contribs: list[Contributor], lo: datetime, hi: datetime, definition_sha: str) -> dict:
    return {"kind": "corpus-pack", "pack_format": PACK_SCHEMA_VERSION, "composition": COMPOSITION_POLICY,
            "requested": [_iso(lo), _iso(hi)], "definition_sha256": definition_sha,
            "availability": json.loads(modeled_availability().model_dump_json()),
            "slices": [[c.dataset_id, c.source_manifest_sha256, c.cache.manifest_sha256, _iso(c.start), _iso(c.end)]
                       for c in contribs]}


def check_contributors(contribs: list[Contributor], lo: datetime, hi: datetime) -> None:
    if not contribs:
        raise PackError("no source slice")
    t = lo
    for c in sorted(contribs, key=lambda c: (c.start, c.dataset_id)):
        if not (c.request_start <= c.start < c.end <= c.request_end):
            raise PackError(f"slice of {c.dataset_id} lies outside its source package request")
        if c.start > t:
            raise PackError(f"requested interval not covered: {_iso(t)} -> {_iso(c.start)} has no source slice")
        t = max(t, c.end)
    if t < hi:
        raise PackError(f"requested interval not covered after {_iso(t)}")
    defs = {canonical(definition(c.instrument)) for c in contribs}
    if len(defs) > 1:
        raise PackError("incompatible instrument identity/definition between contributors; composition refused")
    channels = {tuple(sorted(x.channel.channel_id for x in c.cache.feed_manifest.coverage)) for c in contribs}
    if len(channels) > 1:
        raise PackError("contributors declare different channel sets")
    pols = {c.cache.feed_manifest.availability_policy.policy_id for c in contribs}
    if pols != {modeled_availability().policy_id}:
        raise PackError(f"contributors must use the modeled zero-extra-delay availability, got {sorted(pols)}")


def primary_contributor(contribs: list[Contributor], at: datetime) -> Contributor:
    hits = [c for c in contribs if c.start <= at < c.end]
    return sorted(hits or contribs, key=lambda c: (c.start, c.dataset_id))[0]


def build_pack_cache(data_root: Path, contribs: list[Contributor], preset: ps.Preset, workdir: Path,
                     hook: Hook = _no_hook, counters: dict | None = None, fault=None,
                     provenance: Path | None = None) -> tuple[Any, CompositionStats]:
    lo, hi = preset.warmup.start, preset.tail.end
    check_contributors(contribs, lo, hi)
    windows = {"warmup": (preset.warmup.start, preset.warmup.end),
               "evaluation": (preset.evaluation.start, preset.evaluation.end),
               "tail": (preset.tail.start, preset.tail.end)}
    stats = CompositionStats(windows=windows)
    prim = primary_contributor(contribs, preset.evaluation.start)
    dsha = hashlib.sha256(canonical(definition(prim.instrument))).hexdigest()
    key = pack_cache_key(contribs, lo, hi, dsha)
    sample = prim.cache.feed_manifest
    coverage = tuple(ChannelCoverage(channel=c.channel, covered_from=lo, covered_until=hi,
                                     expected_cadence=c.expected_cadence) for c in sample.coverage)
    inst = prim.instrument
    instrument = {"inst_id": inst.inst_id, "index_id": inst.index_id, "ct_val": str(inst.ct_val),
                  "ct_val_ccy": inst.ct_val_ccy, "ct_mult": str(inst.ct_mult), "base_ccy": inst.base_ccy,
                  "quote_ccy": inst.quote_ccy, "settle_ccy": inst.settle_ccy}

    def facts() -> dict:
        tg = sum(c["missing"] + c["rejected"] for (f, _w), c in stats.counts.items()
                 if f in {x.value for x in BAR_FAMILIES})
        return {"quality": "degraded" if tg else "clean",
                "warnings": [f"{tg} missing/rejected bar slot(s) across the pack (kept, never filled)"] if tg else [],
                "notes": [f"composed by {COMPOSITION_POLICY} from {len(contribs)} source slice(s)"]}

    cache = fc.build_cache(
        data_root, key, compose_events(contribs, lo, hi, stats, workdir / "compose", hook, provenance),
        lambda: coverage, modeled_availability(), tuple(c.dataset_id for c in contribs),
        lambda: (inst.inst_id, inst.index_id, instrument), facts, hook=hook, counters=counters, fault=fault)
    return cache, stats


def manifest_body(f: ps.PresetsFile, preset: ps.Preset, contribs: list[Contributor], cache, stats: CompositionStats,
                  provenance_sha: str | None, provenance_name: str | None) -> dict:
    prim = primary_contributor(contribs, preset.evaluation.start)
    inst = prim.instrument
    d = definition(inst)
    facts, limits = capabilities(stats, f.capability_profile)
    cov = coverage_counts(stats)
    bar_gaps = sum(c.missing + c.rejected for c in cov if c.family in {x.value for x in BAR_FAMILIES})
    fm = cache.feed_manifest
    allowance = modeled_availability().bar_delay
    m = {
        "schema_version": PACK_SCHEMA_VERSION, "contract_status": PACK_CONTRACT_STATUS,
        "schema_revision": PACK_SCHEMA_REVISION, "pack_id": "",
        "preset": ps.preset_doc(preset), "preset_sha256": ps.preset_sha256(f, preset),
        "presets_schema": f.schema_version, "presets_version": f.version, "method": f.method,
        "rules_version": f.rules_version, "register_sha256": ps.MP001_REGISTER_SHA256,
        "capability_profile": dict(f.capability_profile),
        "capability_profile_sha256": ps.capability_profile_sha256(f),
        "windows": ps.windows_doc(preset), "boundaries": dict(f.boundaries),
        "evidence_classes": ps.classify(f, preset),
        "requested_start": preset.warmup.start, "requested_end": preset.tail.end, "tail_end": preset.tail.end,
        "clock_end": preset.tail.end + allowance,
        "instrument": InstrumentPin(policy=METADATA_POLICY, definition=d,
                                    definition_sha256=hashlib.sha256(canonical(d)).hexdigest(),
                                    snapshot_dataset_id=prim.dataset_id, snapshot_retrieved_at=inst.retrieved_at,
                                    snapshot_raw_sha256=inst.raw_sha256,
                                    note="retrieval-time snapshot assumed for the window; not historical "
                                         "effective-date proof; all contributors share this definition"),
        "sources": tuple(c.slice() for c in contribs), "slice_policy": SLICE_POLICY,
        "composition_policy": COMPOSITION_POLICY,
        "feed": FeedRef(cache_id=cache.cache_id, cache_manifest_sha256=cache.manifest_sha256,
                        content_identity=fm.content_identity, ordered_event_hash=fm.ordered_event_hash,
                        ordering_policy_id=fm.ordering_policy_id, availability_policy_id=fm.availability_policy.policy_id,
                        event_count=fm.event_count, event_counts=dict(fm.event_counts)),
        "coverage": cov,
        "overlap": OverlapSummary(overlapping_slots=stats.overlapping_slots,
                                  identical_collapsed=stats.identical_collapsed,
                                  gap_replaced_by_valid=stats.gap_replaced, conflicts=0,
                                  provenance_file=provenance_name, provenance_sha256=provenance_sha),
        "capabilities": facts, "input_readiness_preview": readiness_preview(stats),
        "status": "READY_WITH_LIMITATIONS" if bar_gaps else "READY", "limitations": tuple(limits),
        "storage": {"source_package_bytes": sum(c.source_bytes for c in contribs),
                    "pack_cache_bytes": sum(p["bytes"] for p in cache.partitions),
                    "pack_cache_partitions": len(cache.partitions),
                    "note": "the pack adds its own composed feed cache; source packages are referenced, never copied"},
        "labels": PACK_LABELS,
    }
    doc = json.loads(PackManifest.model_validate(m).model_dump_json())
    doc["pack_id"] = pack_id_for(doc)
    return doc


def pack_id_for(doc: dict) -> str:
    body = {k: v for k, v in doc.items() if k != "pack_id"}
    return "pack-" + hashlib.sha256(canonical(body)).hexdigest()[:40]


def render_manifest(doc: dict) -> bytes:
    return (json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode()


def stage_pack(data_root: Path, doc: dict, provenance: Path | None) -> Path:
    root = packs_root(data_root)
    root.mkdir(parents=True, exist_ok=True)
    tmp = root / f".tmp-{doc['pack_id']}-{uuid.uuid4().hex[:8]}"
    tmp.mkdir()
    if provenance is not None and provenance.exists():
        shutil.copyfile(provenance, tmp / "provenance.jsonl")
        fc._fsync_file(tmp / "provenance.jsonl")
    (tmp / "manifest.json").write_bytes(render_manifest(doc))
    fc._fsync_file(tmp / "manifest.json")
    return tmp


def publish_staged(data_root: Path, pack_id: str, staged: Path) -> str:
    """One directory rename. Identical existing content converges. A directory with the same content-derived id but
    different bytes cannot be a legitimate pack (the id hashes the body): it is moved aside to ``.invalid-*`` (never
    deleted or overwritten in place) and the verified staging is published."""
    final = packs_root(data_root) / pack_id
    if final.exists():
        same = all((final / n).is_file() and (final / n).read_bytes() == (staged / n).read_bytes()
                   for n in [p.name for p in staged.iterdir()])
        if same:
            shutil.rmtree(staged, ignore_errors=True)
            return "converged"
        aside = packs_root(data_root) / f".invalid-{pack_id}-{uuid.uuid4().hex[:8]}"
        final.rename(aside)
        staged.rename(final)
        fc._fsync_dir(packs_root(data_root))
        return "published_after_quarantine"
    staged.rename(final)
    fc._fsync_dir(packs_root(data_root))
    return "published"


def manifest_sha256(data_root: Path, pack_id: str) -> str:
    return hashlib.sha256((packs_root(data_root) / pack_id / "manifest.json").read_bytes()).hexdigest()


def open_pack(data_root: Path, pack_id: str, receipt: dict | None) -> dict:
    """The trusted manifest of a published pack: receipt-pinned file bytes whose body re-hashes to the id."""
    if receipt is None:
        raise PackError(f"pack {pack_id} has no trusted publication receipt")
    path = packs_root(data_root) / pack_id / "manifest.json"
    try:
        raw = path.read_bytes()
    except OSError:
        raise PackError(f"pack {pack_id} manifest is not present") from None
    if hashlib.sha256(raw).hexdigest() != receipt["manifest_sha256"]:
        raise PackError(f"pack {pack_id} manifest does not match its receipt (replaced or corrupt)")
    doc = json.loads(raw)
    if doc.get("pack_id") != pack_id or pack_id_for(doc) != pack_id:
        raise PackError(f"pack {pack_id} manifest body does not hash to its identity")
    PackManifest.model_validate(doc)
    prov = doc["overlap"].get("provenance_file")
    if prov:
        p = packs_root(data_root) / pack_id / prov
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != doc["overlap"]["provenance_sha256"]:
            raise PackError(f"pack {pack_id} provenance file missing or altered")
    return doc


# ---------------------------------------------------------------------------
# 4. Contributors from verified packages (accepted R1B trust boundary) and the replay source
# ---------------------------------------------------------------------------


def prepare_contributors(data_root: Path, receipts, slices: list[tuple[str, datetime, datetime, str]],
                         hook: Hook = _no_hook, on_phase=None, counters: dict | None = None,
                         pins: dict[str, tuple[str, str]] | None = None) -> list[Contributor]:
    """Per-source receipt-pinned caches for (dataset_id, start, end, origin) slices; verified once when cold.

    ``pins`` (dataset_id -> (source manifest sha, cache manifest sha)) require the exact pinned bytes (rebuild).
    """
    from ..observe.contracts import SourceKind
    from ..observe.sources import prepare_stream_source

    out = []
    for i, (ds, a, b, origin) in enumerate(slices):
        hook("prepare source caches", i, len(slices), "sources")
        pin = (pins or {}).get(ds)
        prep = prepare_stream_source(data_root, SourceKind.DATASET, ds, receipts=receipts, verify_hook=hook,
                                     build_hook=hook, on_phase=on_phase, counters=counters,
                                     expected_manifest_sha256=pin[0] if pin else None,
                                     created_by={"pack_contributor": ds})
        if pin and prep.cache.manifest_sha256 != pin[1]:
            raise PackError(f"source cache of {ds} does not reproduce the pinned cache manifest")
        m = md.load_manifest(md.dataset_path(data_root, ds))
        out.append(Contributor(ds, prep.source_manifest_sha256, m.request.start, m.request.end, a, b, origin,
                               prep.cache, m.instrument, sum(x.bytes for x in m.files)))
    hook("prepare source caches", len(slices), len(slices), "sources")
    return out


def pack_receipt(conn, pack_id: str) -> dict | None:
    return conn.execute("SELECT * FROM corpus_packs WHERE pack_id = %s", (pack_id,)).fetchone()


def prepare_pack_source(data_root: Path, pack_id: str, *, receipts, verify_hook=None, build_hook=None,
                        on_phase=None, counters: dict | None = None, expected_manifest_sha256: str | None = None,
                        fault=None):
    """Replay source for a published pack (observe source kind ``pack``)."""
    from datetime import UTC
    from datetime import datetime as _dt

    from ..observe.contracts import SourceKind, SourceSummary, SourceVerification
    from ..observe.sources import MODELED_LABEL, LoadedSource, PreparedSource, SourceRejected

    hook = verify_hook or _no_hook
    counters = counters if counters is not None else {}
    receipt = pack_receipt(receipts.conn, pack_id)
    try:
        doc = open_pack(data_root, pack_id, receipt)
    except PackError as exc:
        raise SourceRejected(str(exc)) from None
    msha = receipt["manifest_sha256"]
    if expected_manifest_sha256 is not None and msha != expected_manifest_sha256:
        raise SourceRejected(f"pack {pack_id} receipt differs from the manifest pinned at launch")
    feed = doc["feed"]
    cid = feed["cache_id"]
    crec = receipts.get(cid)
    if crec is None or crec["cache_manifest_sha256"] != feed["cache_manifest_sha256"]:
        raise SourceRejected(f"pack {pack_id}: its feed cache has no matching trusted receipt")
    cache, warm = None, False
    try:
        cache = fc.open_cache(data_root, cid, expected_manifest_sha256=feed["cache_manifest_sha256"])
        warm = True
    except fc.CacheError as exc:
        cdir = fc.cache_root(data_root) / cid
        if cdir.exists():
            moved = fc.quarantine_dir(cdir, cid, f"pack cache does not match its receipt: {exc}")
            counters["cache_quarantined"] = {"dir": moved.name if moved else None, "reason": str(exc)}
        if on_phase:
            on_phase("BUILDING_FEED")
        preset = ps.Preset.model_validate(doc["preset"])
        pins = {s["dataset_id"]: (s["source_manifest_sha256"], s["cache_manifest_sha256"]) for s in doc["sources"]}
        slices = [(s["dataset_id"], _dt.fromisoformat(s["start"]), _dt.fromisoformat(s["end"]), "local")
                  for s in doc["sources"]]
        work = fc.cache_root(data_root) / f".pack-rebuild-{uuid.uuid4().hex[:8]}"
        try:
            contribs = prepare_contributors(data_root, receipts, slices, hook, None, counters, pins)
            cache, _stats = build_pack_cache(data_root, contribs, preset, work, build_hook or hook, counters, fault)
        except (PackError, SourceRejected, fc.CacheError) as exc:
            raise SourceRejected(f"pack {pack_id}: feed cache could not be rebuilt from its pinned sources: {exc}") \
                from None
        finally:
            shutil.rmtree(work, ignore_errors=True)
        if cache.manifest_sha256 != feed["cache_manifest_sha256"]:
            fc.quarantine(cache, "rebuild does not reproduce the trusted receipt")
            raise SourceRejected(f"pack {pack_id}: the rebuilt feed cache does not reproduce its trusted receipt")
        counters["pack_cache_rebuilt"] = True
    fm = cache.feed_manifest
    summary = SourceSummary(
        kind=SourceKind.PACK, source_id=pack_id, source_schema=PACK_SCHEMA_VERSION, inst_id=fm.inst_id,
        index_id=fm.index_id, source_status=doc["status"].lower(), coverage=fm.coverage,
        warnings=tuple(doc["limitations"]), exclusions=(),
        notes=(f"preset {doc['preset']['preset_id']} · {len(doc['sources'])} source slice(s) · "
               f"{doc['composition_policy']}",))
    method = (f"pack {pack_id}: manifest SHA-256 equals its publication receipt and re-hashes to its id; feed cache "
              f"{cid} {'reused under its trusted receipt' if warm else 'rebuilt from the pinned source slices and '}"
              f"{'' if warm else 'reproduced its receipt'}; partitions SHA-256-verified when read")
    verification = SourceVerification(verified=True, method=method, problems=(), checked_at=_dt.now(UTC))
    loaded = LoadedSource(summary, verification, cache.feed_meta, MODELED_LABEL, f"packs/{pack_id}")
    return PreparedSource(loaded, cache, warm, msha, crec)
