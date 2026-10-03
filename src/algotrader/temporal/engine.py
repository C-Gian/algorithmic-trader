"""Centrally owned temporal reducer and logical clock (engine ``temporal.engine.v1``).

Driven beside the accepted factual reducer by each admitted canonical feed event and by explicit clock barriers:

* ``admit(event, cursor)`` adds one admitted 1m bar (or quality / funding event) to the open accumulators of every
  configured horizon, in market-slot order regardless of admission order; evidence for an already sealed interval is
  counted as late-excluded (``temporal.seal-no-revision.v1``) and never revises anything.
* ``advance_to(t)`` processes every due deadline <= t as its own barrier (each barrier: closures in interval order,
  readiness, due callbacks expiry < reasoning < publication), then one barrier at t. Every barrier with reasons
  yields exactly one ``Dispatch`` for its (clock time, admitted cursor); reasons sharing it are coalesced.
* ``on_event`` applies the clock policy: MODELED fires a barrier only once the next event is available strictly
  later (the whole tie group <= t is admitted first); RECORDED_SYNTHETIC_BARRIER adds a receipt barrier after every
  admitted event; RECORDED_DISPATCH_TAPE leaves barriers to explicit commands.

State is bounded: per channel/horizon only the open accumulators (a slot table of at most one calendar month,
<= ``max_open_intervals`` of them) and the last ``retention`` sealed records are held; minute history is discarded at
closure. The explicit JSON state (``algotrader.temporal-state.v1``) restores directly - never by prefix replay.
"""

from __future__ import annotations

import base64
import hashlib
import json
import zlib
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from ..feed.contracts import (
    AvailabilityBasis,
    ChannelCoverage,
    ChannelRef,
    EventKind,
    Family,
    FeedEvent,
    QualityReason,
)
from ..feed.ordering import canonical
from .calendar import MINUTE, expected_minutes, interval_end, interval_start, is_minute_aligned
from .contracts import (
    DEADLINE_KIND_RANK,
    HORIZON_ORDER,
    HORIZON_ROLE,
    READINESS_PRECEDENCE,
    AggregateStatus,
    AggregateValues,
    ClockPolicy,
    ConstituentCounts,
    Deadline,
    DeadlineKind,
    Dependency,
    Dispatch,
    Horizon,
    Readiness,
    ReadinessStatus,
    TemporalAggregate,
    TemporalProfile,
)

STATE_FORMAT = "algotrader.temporal-state.v1"
ENGINE_ID = "temporal.engine.v1"
RETENTION_HARD_MAX = 2000  # sealed records per channel/horizon (operational ceiling, not a method lookback)
RECENT_DISPATCHES = 16
BAR_FAMILIES = (Family.TRADE_BAR_1M, Family.MARK_BAR_1M, Family.INDEX_BAR_1M)
VALID, MISSING, REJECTED = 1, 2, 3

# Engineering defaults (configuration inputs, not method choices): retention per horizon and a demonstration
# dependency set used only to exercise readiness queries. MP-001 chooses production lookbacks and authority.
DEFAULT_RETENTION = {Horizon.M15: 96, Horizon.H1: 72, Horizon.H4: 42, Horizon.D1: 31, Horizon.W1: 8, Horizon.MO1: 3}
DEFAULT_RECORDED_ALLOWANCE = timedelta(seconds=120)
DEMONSTRATION_DEPENDENCIES = (
    Dependency(name="demo.trade.15m", family=Family.TRADE_BAR_1M, horizon=Horizon.M15, required_complete=4,
               freshness_allowance=timedelta(minutes=30)),
    Dependency(name="demo.trade.1h", family=Family.TRADE_BAR_1M, horizon=Horizon.H1, required_complete=4,
               freshness_allowance=timedelta(hours=2)),
    Dependency(name="demo.trade.4h", family=Family.TRADE_BAR_1M, horizon=Horizon.H4, required_complete=2,
               freshness_allowance=timedelta(hours=8)),
    Dependency(name="demo.trade.1d", family=Family.TRADE_BAR_1M, horizon=Horizon.D1, required_complete=1,
               freshness_allowance=timedelta(days=2)),
    Dependency(name="demo.trade.1w", family=Family.TRADE_BAR_1M, horizon=Horizon.W1, required_complete=1,
               freshness_allowance=timedelta(days=8)),
    Dependency(name="demo.trade.1mo", family=Family.TRADE_BAR_1M, horizon=Horizon.MO1, required_complete=1,
               freshness_allowance=timedelta(days=32)),
    Dependency(name="demo.mark.15m", family=Family.MARK_BAR_1M, horizon=Horizon.M15, required_complete=1,
               freshness_allowance=timedelta(minutes=30)),
    Dependency(name="demo.index.15m", family=Family.INDEX_BAR_1M, horizon=Horizon.M15, required_complete=1,
               freshness_allowance=timedelta(minutes=30)),
    Dependency(name="demo.funding", family=Family.FUNDING_SETTLEMENT, horizon=None, required_complete=1,
               freshness_allowance=timedelta(hours=9)),
)


class TemporalError(Exception):
    """Input outside the supported order/coverage assumptions, or an invalid configuration/state (visible)."""


def default_profile(clock_policy: ClockPolicy, closure_allowance: timedelta, *,
                    dependencies: tuple[Dependency, ...] = DEMONSTRATION_DEPENDENCIES,
                    retention: dict[Horizon, int] | None = None, max_open_intervals: int = 3,
                    deadlines=(), clock_end: datetime | None = None) -> TemporalProfile:
    return TemporalProfile(retention=dict(retention or DEFAULT_RETENTION), closure_allowance=closure_allowance,
                           max_open_intervals=max_open_intervals, clock_policy=clock_policy,
                           dependencies=dependencies, deadlines=tuple(deadlines), clock_end=clock_end)


def profile_doc(profile: TemporalProfile) -> dict:
    return json.loads(profile.model_dump_json())


def profile_fingerprint(profile: TemporalProfile, context: dict | None = None) -> str:
    return hashlib.sha256(canonical({"engine": ENGINE_ID, "state": STATE_FORMAT, "profile": profile_doc(profile),
                                     "context": context or {}})).hexdigest()


def _iso(t: datetime | None) -> str | None:
    return None if t is None else t.isoformat()


def _dt(s: str | None) -> datetime | None:
    return None if s is None else datetime.fromisoformat(s)


def chain(h: str, doc: dict) -> str:
    return hashlib.sha256(bytes.fromhex(h) + canonical(doc)).hexdigest()


INITIAL_SEALED = hashlib.sha256(b"algotrader.temporal.sealed-records.v1\x00").hexdigest()
INITIAL_DISPATCH = hashlib.sha256(b"algotrader.temporal.dispatches.v1\x00").hexdigest()
INITIAL_AGGREGATE = hashlib.sha256(b"algotrader.temporal.aggregate-chain.v1\x00").hexdigest()


def aggregate_link(record_id: str, content_digest: str, sealed_at: str, admitted_cursor: int) -> dict:
    """The reference-comparable part of a sealed record (what a separate reference aggregator recomputes)."""
    return {"record_id": record_id, "content_digest": content_digest, "sealed_at": sealed_at,
            "admitted_cursor": admitted_cursor}


def record_content(record_id: str, status: str, counts: dict, values: dict | None, known_at: str, start: str,
                   end: str) -> dict:
    """Content covered by ``TemporalAggregate.content_digest`` (market content, status, counts and times)."""
    return {"record_id": record_id, "status": status, "counts": counts, "values": values, "known_at": known_at,
            "start": start, "end": end}


@dataclass
class _Acc:
    """Open accumulator of one calendar interval: a bounded slot table plus running exact aggregates."""

    start: datetime
    end: datetime
    slots: bytearray
    valid: int = 0
    missing: int = 0
    rejected: int = 0
    reasons: dict[str, int] = field(default_factory=dict)
    open_idx: int | None = None
    open: Decimal | None = None
    close_idx: int | None = None
    close: Decimal | None = None
    high: Decimal | None = None
    low: Decimal | None = None
    vol_contracts: Decimal | None = None
    vol_base: Decimal | None = None
    vol_quote: Decimal | None = None
    base_ccy: str | None = None
    quote_ccy: str | None = None
    index_id: str | None = None
    max_available: datetime | None = None

    def add(self, idx: int, code: int, e: FeedEvent) -> None:
        if self.slots[idx]:
            raise TemporalError(f"second evidence for slot {e.event_time.isoformat()} in {self.start.isoformat()}")
        self.slots[idx] = code
        if self.max_available is None or e.available_time > self.max_available:
            self.max_available = e.available_time
        if code != VALID:
            reason = e.payload.reason.value
            self.reasons[reason] = self.reasons.get(reason, 0) + 1
            if code == MISSING:
                self.missing += 1
            else:
                self.rejected += 1
            return
        p = e.payload
        self.valid += 1
        if self.open_idx is None or idx < self.open_idx:
            self.open_idx, self.open = idx, p.open
        if self.close_idx is None or idx > self.close_idx:
            self.close_idx, self.close = idx, p.close
        self.high = p.high if self.high is None or p.high > self.high else self.high
        self.low = p.low if self.low is None or p.low < self.low else self.low
        if e.channel.family == Family.TRADE_BAR_1M:
            self.vol_contracts = (self.vol_contracts or Decimal(0)) + p.volume_contracts
            self.vol_base = (self.vol_base or Decimal(0)) + p.volume_base
            self.vol_quote = (self.vol_quote or Decimal(0)) + p.volume_quote
            if self.base_ccy is not None and (self.base_ccy, self.quote_ccy) != (p.volume_base_ccy, p.volume_quote_ccy):
                raise TemporalError("volume currencies changed inside one channel; units cannot be summed")
            self.base_ccy, self.quote_ccy = p.volume_base_ccy, p.volume_quote_ccy
        elif e.channel.family == Family.INDEX_BAR_1M:
            self.index_id = p.index_id

    def values(self) -> AggregateValues | None:
        if self.valid == 0:
            return None
        return AggregateValues(open=self.open, high=self.high, low=self.low, close=self.close,
                               volume_contracts=self.vol_contracts, volume_base=self.vol_base,
                               volume_base_ccy=self.base_ccy, volume_quote=self.vol_quote,
                               volume_quote_ccy=self.quote_ccy, index_id=self.index_id)

    def encode(self) -> dict:
        d = {k: getattr(self, k) for k in ("valid", "missing", "rejected", "reasons", "open_idx", "close_idx",
                                            "base_ccy", "quote_ccy", "index_id")}
        for k in ("open", "close", "high", "low", "vol_contracts", "vol_base", "vol_quote"):
            v = getattr(self, k)
            d[k] = None if v is None else str(v)
        d.update(start=_iso(self.start), end=_iso(self.end), max_available=_iso(self.max_available),
                 slots=base64.b64encode(bytes(self.slots)).decode())
        return d

    @classmethod
    def decode(cls, d: dict) -> _Acc:
        a = cls(start=_dt(d["start"]), end=_dt(d["end"]), slots=bytearray(base64.b64decode(d["slots"])))
        for k in ("valid", "missing", "rejected", "open_idx", "close_idx", "base_ccy", "quote_ccy", "index_id"):
            setattr(a, k, d[k])
        a.reasons = dict(d["reasons"])
        for k in ("open", "close", "high", "low", "vol_contracts", "vol_base", "vol_quote"):
            setattr(a, k, None if d[k] is None else Decimal(d[k]))
        a.max_available = _dt(d["max_available"])
        return a


@dataclass
class _Track:
    channel: ChannelRef
    horizon: Horizon
    cov_from: datetime
    cov_until: datetime
    next_start: datetime  # earliest unsealed interval; every interval before it is sealed
    retention: int
    open: dict[datetime, _Acc] = field(default_factory=dict)
    sealed: deque = field(default_factory=deque)
    late_excluded: int = 0
    sealed_by_status: dict[str, int] = field(default_factory=dict)
    hint: _Acc | None = None  # last touched accumulator (performance only; not state)

    @property
    def key(self) -> str:
        return f"{self.channel.channel_id}/{self.horizon.value}"

    def done(self) -> bool:
        return self.next_start >= self.cov_until

    def next_end(self) -> datetime:
        return interval_end(self.horizon, self.next_start)

    def deadline(self, allowance: timedelta) -> datetime | None:
        if self.done():
            return None
        return min(self.next_end(), self.cov_until) + allowance

    def in_coverage_minutes(self, start: datetime, end: datetime) -> int:
        lo, hi = max(start, self.cov_from), min(end, self.cov_until)
        return max(int((hi - lo) / MINUTE), 0)

    def evidence_complete(self) -> bool:
        acc = self.open.get(self.next_start)
        need = self.in_coverage_minutes(self.next_start, self.next_end())
        have = 0 if acc is None else acc.valid + acc.missing + acc.rejected
        return need > 0 and have == need


def _newest_complete(t: _Track) -> dict | None:
    for rec in reversed(t.sealed):
        if rec["status"] == AggregateStatus.COMPLETE.value:
            return rec
    return None


class TemporalEngine:
    def __init__(self, profile: TemporalProfile, coverage: tuple[ChannelCoverage, ...], *, basis: AvailabilityBasis,
                 availability_policy_id: str, content_identity: str, context: dict | None = None) -> None:
        self.profile = profile
        self.context = dict(context or {})
        self.fingerprint = profile_fingerprint(profile, self.context)
        self.basis = basis
        self.availability_policy_id = availability_policy_id
        self.content_identity = content_identity
        self._validate_profile()
        self.coverage = tuple(sorted(coverage, key=lambda c: c.channel.channel_id))
        self.tracks: dict[str, _Track] = {}
        self.funding: dict[str, dict | None] = {}
        self.funding_cov: dict[str, ChannelCoverage] = {}
        for c in self.coverage:
            if c.channel.family in BAR_FAMILIES:
                for h in profile.horizons:
                    t = _Track(channel=c.channel, horizon=h, cov_from=c.covered_from, cov_until=c.covered_until,
                               next_start=interval_start(h, c.covered_from), retention=profile.retention[h])
                    t.sealed = deque(maxlen=t.retention)
                    self.tracks[t.key] = t
            elif c.channel.family == Family.FUNDING_SETTLEMENT:
                self.funding[c.channel.channel_id] = None
                self.funding_cov[c.channel.channel_id] = c
        self.clock: datetime | None = None
        self.cursor = 0
        self._last_order: str | None = None
        self._last_order_obj = None  # OrderKey of the newest admitted event (string built lazily)
        self.pending: datetime | None = None  # newest admitted availability time not yet covered by a barrier
        self.deadlines: dict[str, Deadline] = {d.deadline_id: d for d in profile.deadlines}
        self.dispatch_seq = 0
        self.dispatch_commitment = INITIAL_DISPATCH
        self.sealed_commitment = INITIAL_SEALED
        self.aggregate_chain = INITIAL_AGGREGATE
        self.recent: deque = deque(maxlen=RECENT_DISPATCHES)
        self.readiness_last: dict[str, str] = {}
        self.continuations: deque = deque(maxlen=RECENT_DISPATCHES)  # source continuation / reset log
        self.counters = {"admitted": 0, "late_excluded": 0, "misaligned_excluded": 0, "outside_coverage_excluded": 0,
                         "sealed": 0, "dispatches": 0, "barriers": 0, "deadline_callbacks": 0}
        self.sealed_listeners: list = []  # test seams (e.g. collect every sealed record); not part of state
        self.dispatch_listeners: list = []  # test seams (collect every dispatch); not part of state
        self._nd: tuple[bool, datetime | None] = (False, None)
        self._chan_tracks: dict[str, list[_Track]] = {}
        for t in self.tracks.values():
            self._chan_tracks.setdefault(t.channel.channel_id, []).append(t)
        for lst in self._chan_tracks.values():
            lst.sort(key=lambda t: HORIZON_ORDER.index(t.horizon))  # next-deadline cache (derived, not state)
        self._dep_tracks = {d.name: next((t for t in self.tracks.values() if t.channel.family == d.family
                                          and t.horizon == d.horizon), None) for d in profile.dependencies}

    # -- configuration -----------------------------------------------------------------------------

    def _validate_profile(self) -> None:
        p = self.profile
        for h in p.horizons:
            n = p.retention.get(h)
            if n is None or not 1 <= n <= RETENTION_HARD_MAX:
                raise TemporalError(f"retention for {h.value} must be 1..{RETENTION_HARD_MAX} (got {n})")
        for d in p.dependencies:
            if d.horizon is not None and d.horizon in p.horizons and d.required_complete > p.retention[d.horizon]:
                raise TemporalError(f"configuration rejected: dependency {d.name} needs {d.required_complete} "
                                    f"consecutive {d.horizon.value} records but retention is {p.retention[d.horizon]}")
            if d.horizon is None and d.family != Family.FUNDING_SETTLEMENT:
                raise TemporalError(f"dependency {d.name}: only funding may omit a horizon")
            if d.family == Family.FUNDING_SETTLEMENT and d.required_complete != 1:
                raise TemporalError(f"dependency {d.name}: sparse funding has no scheduled completeness")

    @property
    def last_order(self) -> str | None:
        o = self._last_order_obj
        if o is not None:
            self._last_order = (f"{o.available_time.isoformat()}|{o.family_rank}|{o.series_id}|"
                                f"{o.event_time.isoformat()}|{o.kind_rank}|{o.event_id}")
            self._last_order_obj = None
        return self._last_order

    def default_clock_end(self) -> datetime:
        if self.profile.clock_end is not None:
            return self.profile.clock_end
        ends = [t.cov_until for t in self.tracks.values()] or [c.covered_until for c in self.coverage]
        return max(ends) + self.profile.closure_allowance

    # -- source continuation ------------------------------------------------------------------------

    def _new_track(self, c: ChannelCoverage, h: Horizon) -> _Track:
        t = _Track(channel=c.channel, horizon=h, cov_from=c.covered_from, cov_until=c.covered_until,
                   next_start=interval_start(h, c.covered_from), retention=self.profile.retention[h])
        t.sealed = deque(maxlen=t.retention)
        return t

    def extend_coverage(self, coverage: tuple[ChannelCoverage, ...], content_identity: str) -> list[dict]:
        """Continue with the next source chunk (e.g. the next calendar month) WITHOUT losing temporal state.

        A channel whose next coverage starts exactly where its previous coverage ended (same channel/instrument)
        continues: open accumulators, sealed history, counters and readiness state are preserved and its coverage end
        moves forward. Any other case (coverage gap or overlap, instrument/series change, new channel) resets ONLY that
        channel's tracks (or funding context) and records why; other channels and dependencies are untouched.
        Intervals already sealed against the previous coverage end stay sealed (seal-no-revision), so continuation must
        be applied before the clock passes the previous coverage end + closure allowance to avoid such cuts.
        """
        merged = {c.channel.channel_id: c for c in self.coverage}
        log: list[dict] = []
        for c in sorted(coverage, key=lambda x: x.channel.channel_id):
            cid = c.channel.channel_id
            old = merged.get(cid)
            if old is not None and old.channel == c.channel and c.covered_from == old.covered_until:
                merged[cid] = old.model_copy(update={"covered_until": c.covered_until})
                for t in self._chan_tracks.get(cid, ()):
                    t.cov_until = c.covered_until
                if cid in self.funding_cov:
                    self.funding_cov[cid] = merged[cid]
                log.append({"channel": cid, "action": "continued", "covered_until": _iso(c.covered_until)})
                continue
            if old is None:
                reason = "new channel in the continuation source"
            elif old.channel != c.channel:
                reason = "instrument/series changed"
            else:
                reason = (f"coverage discontinuity: previous coverage ends {_iso(old.covered_until)}, next starts "
                          f"{_iso(c.covered_from)}")
            merged[cid] = c
            if c.channel.family in BAR_FAMILIES:
                for h in self.profile.horizons:
                    self.tracks[f"{cid}/{h.value}"] = self._new_track(c, h)
            elif c.channel.family == Family.FUNDING_SETTLEMENT:
                self.funding[cid] = None
                self.funding_cov[cid] = c
            log.append({"channel": cid, "action": "reset", "reason": reason,
                        "covered_from": _iso(c.covered_from), "covered_until": _iso(c.covered_until)})
        self.coverage = tuple(sorted(merged.values(), key=lambda x: x.channel.channel_id))
        self._chan_tracks = {}
        for t in self.tracks.values():
            self._chan_tracks.setdefault(t.channel.channel_id, []).append(t)
        for lst in self._chan_tracks.values():
            lst.sort(key=lambda t: HORIZON_ORDER.index(t.horizon))
        self._dep_tracks = {d.name: next((t for t in self.tracks.values() if t.channel.family == d.family
                                          and t.horizon == d.horizon), None) for d in self.profile.dependencies}
        self._nd = (False, None)
        self.continuations.append({"at_cursor": self.cursor, "clock": _iso(self.clock),
                                   "content_identity": content_identity, "channels": log})
        return log

    # -- commands ----------------------------------------------------------------------------------

    def on_event(self, e: FeedEvent, cursor: int) -> None:
        """Clock policy for streamed canonical input (the kernel calls this for every applied event)."""
        policy = self.profile.clock_policy
        if policy == ClockPolicy.RECORDED_DISPATCH_TAPE:
            self.admit(e, cursor)
            return
        self._run_barriers(e.available_time, inclusive=False)
        self.admit(e, cursor)
        if policy == ClockPolicy.RECORDED_SYNTHETIC_BARRIER:
            self.advance_to(e.available_time, barrier="receipt")

    def register(self, d: Deadline) -> None:
        if self.clock is not None and d.due <= self.clock:
            raise TemporalError(f"deadline {d.deadline_id} at {d.due.isoformat()} is not after the clock")
        if d.deadline_id in self.deadlines:
            raise TemporalError(f"deadline id {d.deadline_id} already registered")
        self.deadlines[d.deadline_id] = d
        self._nd = (False, None)

    def cancel(self, deadline_id: str) -> None:
        self.deadlines.pop(deadline_id, None)
        self._nd = (False, None)

    def admit(self, e: FeedEvent, cursor: int) -> None:
        if cursor != self.cursor:
            raise TemporalError(f"admission discontinuity: event at cursor {cursor}, temporal cursor {self.cursor}")
        if self.clock is not None and e.available_time < self.clock:
            raise TemporalError(f"{e.event_id} available {e.available_time.isoformat()} before the processed barrier "
                                f"{self.clock.isoformat()}: it cannot join an already dispatched prefix")
        self.cursor += 1
        self.counters["admitted"] += 1
        self._last_order_obj = e.order
        if self.pending is None or e.available_time > self.pending:
            self.pending = e.available_time
        fam = e.channel.family
        cid = e.channel.channel_id
        if fam == Family.FUNDING_SETTLEMENT:
            if e.kind == EventKind.FUNDING_OBSERVATION and cid in self.funding:
                self.funding[cid] = {"event_time": _iso(e.event_time), "known_at": _iso(e.available_time),
                                     "funding_rate": str(e.payload.funding_rate), "event_id": e.event_id}
                self._nd = (False, None)
            return
        slot = e.event_time
        if not is_minute_aligned(slot) or e.event_end_time != slot + MINUTE:
            self.counters["misaligned_excluded"] += 1
            return
        if e.kind == EventKind.BAR_OBSERVATION:
            code = VALID
        elif e.payload.reason == QualityReason.MISSING:
            code = MISSING
        else:
            code = REJECTED
        for t in self._chan_tracks.get(cid, ()):
            h = t.horizon
            if not t.cov_from <= slot < t.cov_until:
                self.counters["outside_coverage_excluded"] += 1
                break
            acc = t.hint
            if acc is not None and acc.start <= slot < acc.end and t.open.get(acc.start) is acc:
                s = acc.start
            else:
                s = interval_start(h, slot)
                acc = t.open.get(s)
            if s < t.next_start:
                t.late_excluded += 1  # sealed interval: never revised (seal-no-revision)
                self.counters["late_excluded"] += 1
                continue
            if acc is None:
                if len(t.open) >= self.profile.max_open_intervals:
                    raise TemporalError(f"{t.key}: more than {self.profile.max_open_intervals} open intervals "
                                        f"(slot {slot.isoformat()}); input outside the supported order assumptions")
                end = interval_end(h, s)
                acc = _Acc(start=s, end=end, slots=bytearray(expected_minutes(h, s)))
                t.open[s] = acc
            acc.add(int((slot - s) / MINUTE), code, e)
            t.hint = acc

    def advance_to(self, t: datetime, barrier: str = "tape") -> Dispatch | None:
        """Explicit clock barrier at t: every earlier due deadline is its own barrier first."""
        if self.pending is not None and t < self.pending:
            raise TemporalError(f"barrier {t.isoformat()} precedes admitted evidence {self.pending.isoformat()}")
        self._run_barriers(t, inclusive=False)
        return self._barrier(t, barrier)

    def finish(self, clock_end: datetime | None = None) -> Dispatch | None:
        """Finite replay end: advance to ``clock_end`` (default coverage end + allowance) and stop."""
        if clock_end is not None:
            if self.clock is not None and clock_end < self.clock:
                raise TemporalError("clock_end precedes the processed clock")
            if self.pending is not None and self.pending > clock_end:
                raise TemporalError(f"admitted evidence available at {self.pending.isoformat()} is after clock_end")
            end = clock_end
        else:
            # the default end never cuts admitted evidence or moves the clock back (e.g. a receipt that arrived
            # after coverage end + allowance, or a delayed last funding event)
            end = max(t for t in (self.default_clock_end(), self.clock, self.pending) if t is not None)
        return self.advance_to(end, barrier="finish")

    # -- barriers ----------------------------------------------------------------------------------

    def next_deadline(self) -> datetime | None:
        ok, cached = self._nd
        if ok:
            return cached
        value = self._compute_next_deadline()
        self._nd = (True, value)
        return value

    def _compute_next_deadline(self) -> datetime | None:
        cands = []
        allowance = self.profile.closure_allowance
        for t in self.tracks.values():
            d = t.deadline(allowance)
            if d is not None:
                cands.append(d)
        cands.extend(d.due for d in self.deadlines.values())
        cands.extend(self._staleness_deadlines())
        if self.clock is not None:
            cands = [c for c in cands if c > self.clock]
        return min(cands) if cands else None

    def _staleness_deadlines(self) -> list[datetime]:
        out = []
        for dep in self.profile.dependencies:
            k = self._latest_known(dep)
            if k is not None:
                out.append(k + dep.freshness_allowance)
        return out

    def _run_barriers(self, limit: datetime, inclusive: bool) -> None:
        while True:
            d = self.next_deadline()
            if d is None or d > limit or (d == limit and not inclusive):
                return
            self._barrier(d, "scheduled")

    def _dispatch_id(self, seq: int, t: datetime) -> str:
        h = hashlib.sha256(canonical({"fp": self.fingerprint, "seq": seq, "t": _iso(t), "cursor": self.cursor}))
        return f"dsp-{seq:08d}-{h.hexdigest()[:12]}"

    def _barrier(self, t: datetime, kind: str) -> Dispatch | None:
        if self.clock is not None and t < self.clock:
            raise TemporalError(f"clock cannot move backwards ({t.isoformat()} < {self.clock.isoformat()})")
        self.clock = t
        self._nd = (False, None)
        self.counters["barriers"] += 1
        seq = self.dispatch_seq + 1
        did = self._dispatch_id(seq, t)
        closed = self._seal_due(t, did)
        due = sorted((d for d in self.deadlines.values() if d.due <= t),
                     key=lambda d: (d.due, DEADLINE_KIND_RANK[DeadlineKind(d.kind)], d.priority, d.deadline_id))
        for d in due:
            del self.deadlines[d.deadline_id]
        readiness = self.readiness(t)
        changes = []
        for r in readiness:
            if self.readiness_last.get(r.dependency) != r.status.value:
                changes.append(f"readiness:{r.dependency}:{r.status.value}")
                self.readiness_last[r.dependency] = r.status.value
        reasons = [f"closed:{rec.channel_id}/{rec.horizon.value}:{rec.status.value}" for rec in closed]
        reasons += changes + [f"deadline:{d.kind}:{d.deadline_id}" for d in due]
        if not reasons:
            return None
        self.counters["deadline_callbacks"] += len(due)
        disp = Dispatch(dispatch_id=did, seq=seq, clock_time=t, barrier=kind, admitted_cursor=self.cursor,
                        last_order=self.last_order, clock_policy_id=self.profile.clock_policy.value,
                        profile_fingerprint=self.fingerprint, reasons=tuple(sorted(set(reasons))),
                        callbacks=tuple(d.deadline_id for d in due),
                        closed_record_ids=tuple(r.record_id for r in closed), readiness=tuple(readiness))
        self.dispatch_seq = seq
        self.dispatch_commitment = chain(self.dispatch_commitment, json.loads(disp.model_dump_json()))
        self.recent.append({"dispatch_id": did, "seq": seq, "clock_time": _iso(t), "barrier": kind,
                            "admitted_cursor": self.cursor, "reasons": list(disp.reasons)})
        self.counters["dispatches"] += 1
        for fn in self.dispatch_listeners:
            fn(disp)
        return disp

    def _seal_due(self, t: datetime, dispatch_id: str) -> list[TemporalAggregate]:
        allowance = self.profile.closure_allowance
        closed: list[TemporalAggregate] = []
        for key in sorted(self.tracks):
            tr = self.tracks[key]
            while not tr.done():
                end = tr.next_end()
                due = min(end, tr.cov_until) + allowance <= t
                early = end <= t and tr.evidence_complete()
                if not (due or early):
                    break
                rec = self._seal(tr, t, dispatch_id)
                closed.append(rec)
        return closed

    def _seal(self, tr: _Track, t: datetime, dispatch_id: str) -> TemporalAggregate:
        h, s = tr.horizon, tr.next_start
        end = interval_end(h, s)
        acc = tr.open.pop(s, None)
        expected = expected_minutes(h, s)
        in_cov = tr.in_coverage_minutes(s, end)
        outside = expected - in_cov
        valid = acc.valid if acc else 0
        miss = acc.missing if acc else 0
        rej = acc.rejected if acc else 0
        absent = in_cov - valid - miss - rej
        reasons = dict(acc.reasons) if acc else {}
        if absent:
            reasons["ABSENT_AT_SEAL"] = absent
        if outside:
            reasons["OUTSIDE_COVERAGE"] = outside
        counts = ConstituentCounts(expected=expected, valid=valid, missing=miss + absent + outside, rejected=rej,
                                   reasons=dict(sorted(reasons.items())))
        if outside:
            status = AggregateStatus.OUTSIDE_COVERAGE
        elif valid == expected:
            status = AggregateStatus.COMPLETE
        else:
            status = AggregateStatus.INCOMPLETE
        vals = acc.values() if acc else None
        known = max(end, acc.max_available) if status == AggregateStatus.COMPLETE else t
        rid = f"{tr.channel.channel_id}/{h.value}/{s.isoformat()}"
        content = record_content(rid, status.value, counts.model_dump(mode="json"),
                                 None if vals is None else vals.model_dump(mode="json"), _iso(known), _iso(s),
                                 _iso(end))
        rec = TemporalAggregate(
            record_id=rid, profile_id=self.profile.profile_id, channel=tr.channel, channel_id=tr.channel.channel_id,
            horizon=h, role=HORIZON_ROLE[h], interval_start=s, interval_end=end, status=status, counts=counts,
            values=vals if status == AggregateStatus.COMPLETE else None,
            partial_diagnostic=None if status == AggregateStatus.COMPLETE else vals, known_at=known, sealed_at=t,
            admitted_cursor=self.cursor, closure_dispatch_id=dispatch_id, availability_basis=self.basis,
            availability_policy_id=self.availability_policy_id, feed_content_identity=self.content_identity,
            seal_policy_id=self.profile.seal_policy_id,
            content_digest=hashlib.sha256(canonical(content)).hexdigest())
        doc = json.loads(rec.model_dump_json())
        tr.sealed.append(doc)
        tr.next_start = end
        tr.sealed_by_status[status.value] = tr.sealed_by_status.get(status.value, 0) + 1
        self.sealed_commitment = chain(self.sealed_commitment, doc)
        self.aggregate_chain = chain(self.aggregate_chain, aggregate_link(rid, rec.content_digest, _iso(t),
                                                                          self.cursor))
        self.counters["sealed"] += 1
        for fn in self.sealed_listeners:
            fn(rec)
        return rec

    # -- readiness ---------------------------------------------------------------------------------

    def _dep_track(self, dep: Dependency) -> _Track | None:
        return self._dep_tracks.get(dep.name)

    def _latest_known(self, dep: Dependency) -> datetime | None:
        if dep.family == Family.FUNDING_SETTLEMENT:
            latest = [v for v in self.funding.values() if v]
            return max(_dt(v["known_at"]) for v in latest) if latest else None
        t = self._dep_track(dep)
        latest = _newest_complete(t) if t is not None else None
        return None if latest is None else _dt(latest["known_at"])

    def readiness(self, at: datetime | None = None) -> list[Readiness]:
        at = at or self.clock
        return [self.query(d, at) for d in self.profile.dependencies]

    def query(self, dep: Dependency, at: datetime | None) -> Readiness:
        """Dependency-specific readiness at clock time ``at`` with every applicable blocker listed."""
        blockers: list[tuple[ReadinessStatus, str]] = []
        latest_id = age_end = age_known = None
        consecutive = 0
        if dep.family == Family.FUNDING_SETTLEMENT:
            if not self.funding:
                blockers.append((ReadinessStatus.UNAVAILABLE, "no funding settlement channel in this source"))
            else:
                cid = sorted(self.funding)[0]
                cov, latest = self.funding_cov[cid], self.funding[cid]
                if at is not None and (at < cov.covered_from or at > cov.covered_until + self.profile.closure_allowance):
                    blockers.append((ReadinessStatus.OUTSIDE_COVERAGE, "clock outside funding coverage"))
                if latest is None:
                    blockers.append((ReadinessStatus.WARMING_UP, "no settled funding known yet (sparse; no schedule "
                                                                 "is assumed)"))
                else:
                    consecutive, latest_id = 1, latest["event_id"]
                    if at is not None:
                        age_known = at - _dt(latest["known_at"])
                        age_end = at - _dt(latest["event_time"])
                        if age_known >= dep.freshness_allowance:
                            blockers.append((ReadinessStatus.STALE, f"latest settlement known {age_known} ago >= "
                                                                    f"allowance {dep.freshness_allowance}"))
        elif dep.horizon not in self.profile.horizons:
            blockers.append((ReadinessStatus.UNAVAILABLE, f"horizon {dep.horizon} is not in profile "
                                                          f"{self.profile.profile_id}"))
        else:
            t = self._dep_track(dep)
            if t is None:
                blockers.append((ReadinessStatus.UNAVAILABLE, f"no {dep.family.value} channel in this source"))
            else:
                if at is not None and (at < t.cov_from or at > t.cov_until + self.profile.closure_allowance):
                    blockers.append((ReadinessStatus.OUTSIDE_COVERAGE, "clock outside the channel's coverage"))
                broken = None
                for rec in reversed(t.sealed):
                    if rec["status"] == AggregateStatus.COMPLETE.value:
                        consecutive += 1
                        if consecutive >= dep.required_complete:
                            break
                    else:
                        broken = rec
                        break
                newest = _newest_complete(t)
                if consecutive < dep.required_complete:
                    if broken is not None and broken["status"] == AggregateStatus.INCOMPLETE.value:
                        blockers.append((ReadinessStatus.GAP, f"{broken['record_id']} sealed INCOMPLETE "
                                                              f"({broken['counts']['reasons']}); {consecutive}/"
                                                              f"{dep.required_complete} consecutive complete"))
                    else:
                        blockers.append((ReadinessStatus.WARMING_UP, f"{consecutive}/{dep.required_complete} "
                                                                     "consecutive complete records"))
                if newest is not None:  # staleness is judged against the newest COMPLETE record
                    latest_id = newest["record_id"]
                    if at is not None:
                        age_known = at - _dt(newest["known_at"])
                        age_end = at - _dt(newest["interval_end"])
                        if age_known >= dep.freshness_allowance:
                            blockers.append((ReadinessStatus.STALE, f"newest complete record known {age_known} ago "
                                                                    f">= allowance {dep.freshness_allowance}"))
        rank = {s: i for i, s in enumerate(READINESS_PRECEDENCE)}
        status = min((b[0] for b in blockers), key=lambda s: rank[s], default=ReadinessStatus.READY)
        return Readiness(dependency=dep.name, status=status, blockers=tuple(f"{s.value}: {m}" for s, m in blockers),
                         complete_consecutive=consecutive, required=dep.required_complete, latest_record_id=latest_id,
                         age_since_end=age_end, age_since_known=age_known)

    # -- inspection --------------------------------------------------------------------------------

    def sealed_records(self, channel_id: str, horizon: Horizon) -> list[dict]:
        return list(self.tracks[f"{channel_id}/{horizon.value}"].sealed)

    def summary(self, recent: int = 5) -> dict[str, Any]:
        tracks = []
        for key in sorted(self.tracks):
            t = self.tracks[key]
            newest = t.sealed[-1] if t.sealed else None
            tracks.append({
                "track": key, "family": t.channel.family.value, "horizon": t.horizon.value,
                "role": HORIZON_ROLE[t.horizon],
                "newest_sealed": None if newest is None else {
                    "record_id": newest["record_id"], "status": newest["status"], "known_at": newest["known_at"],
                    "interval_start": newest["interval_start"], "interval_end": newest["interval_end"],
                    "valid": newest["counts"]["valid"], "expected": newest["counts"]["expected"]},
                "forming": [{"interval_start": _iso(a.start), "valid": a.valid, "missing": a.missing,
                             "rejected": a.rejected, "expected": len(a.slots)} for _, a in sorted(t.open.items())],
                "next_unsealed_start": None if t.done() else _iso(t.next_start),
                "late_excluded": t.late_excluded, "sealed_by_status": dict(sorted(t.sealed_by_status.items())),
                "retained": len(t.sealed), "retention": t.retention})
        return {
            "format": STATE_FORMAT, "engine": ENGINE_ID, "profile_id": self.profile.profile_id,
            "profile_fingerprint": self.fingerprint, "clock_policy": self.profile.clock_policy.value,
            "seal_policy": self.profile.seal_policy_id, "closure_allowance_seconds":
                self.profile.closure_allowance.total_seconds(),
            "clock_time": _iso(self.clock), "admitted_cursor": self.cursor, "pending_tie_time":
                _iso(self.pending) if self.pending is not None and (self.clock is None or self.pending > self.clock)
                else None,
            "next_deadline": _iso(self.next_deadline()), "dispatch_seq": self.dispatch_seq,
            "sealed_commitment": self.sealed_commitment, "dispatch_commitment": self.dispatch_commitment,
            "aggregate_chain": self.aggregate_chain, "counters": dict(self.counters), "tracks": tracks,
            "readiness": [json.loads(r.model_dump_json()) for r in self.readiness()] if self.clock else [],
            "recent_dispatches": list(self.recent)[-recent:], "labels": list(self.profile.labels),
        }

    def commitment(self) -> str:
        """Combined output commitment (sealed records + dispatches) recorded at checkpoint boundaries."""
        return hashlib.sha256(canonical({"sealed": self.sealed_commitment, "dispatch": self.dispatch_commitment,
                                         "aggregate": self.aggregate_chain, "seq": self.dispatch_seq,
                                         "cursor": self.cursor})).hexdigest()

    # -- explicit state codec ----------------------------------------------------------------------

    def encode(self) -> dict[str, Any]:
        return {
            "format": STATE_FORMAT, "engine": ENGINE_ID, "fingerprint": self.fingerprint,
            "profile": profile_doc(self.profile), "context": self.context, "basis": self.basis.value,
            "availability_policy_id": self.availability_policy_id, "content_identity": self.content_identity,
            "coverage": [c.model_dump(mode="json") for c in self.coverage],
            "clock": _iso(self.clock), "cursor": self.cursor, "last_order": self.last_order,
            "pending": _iso(self.pending),
            "deadlines": [d.model_dump(mode="json") for _, d in sorted(self.deadlines.items())],
            "dispatch_seq": self.dispatch_seq, "dispatch_commitment": self.dispatch_commitment,
            "sealed_commitment": self.sealed_commitment, "aggregate_chain": self.aggregate_chain,
            "recent": list(self.recent),
            "readiness_last": dict(sorted(self.readiness_last.items())), "counters": dict(sorted(self.counters.items())),
            "funding": dict(sorted(self.funding.items())), "continuations": list(self.continuations),
            "tracks": [[k, {"next_start": _iso(t.next_start), "late_excluded": t.late_excluded,
                            "sealed_by_status": dict(sorted(t.sealed_by_status.items())), "sealed": list(t.sealed),
                            "open": [a.encode() for _, a in sorted(t.open.items())]}]
                       for k, t in sorted(self.tracks.items())],
        }

    @classmethod
    def decode(cls, doc: dict[str, Any]) -> TemporalEngine:
        if doc.get("format") != STATE_FORMAT or doc.get("engine") != ENGINE_ID:
            raise TemporalError(f"temporal state format {doc.get('format')!r}/{doc.get('engine')!r} is not "
                                f"{STATE_FORMAT}/{ENGINE_ID}")
        profile = TemporalProfile.model_validate(doc["profile"])
        eng = cls(profile, tuple(ChannelCoverage.model_validate(c) for c in doc["coverage"]),
                  basis=AvailabilityBasis(doc["basis"]), availability_policy_id=doc["availability_policy_id"],
                  content_identity=doc["content_identity"], context=doc["context"])
        if eng.fingerprint != doc["fingerprint"]:
            raise TemporalError("temporal state fingerprint does not match its profile/context")
        eng.clock, eng.cursor, eng._last_order = _dt(doc["clock"]), doc["cursor"], doc["last_order"]
        eng.pending = _dt(doc["pending"])
        eng.deadlines = {d["deadline_id"]: Deadline.model_validate(d) for d in doc["deadlines"]}
        eng.dispatch_seq, eng.dispatch_commitment = doc["dispatch_seq"], doc["dispatch_commitment"]
        eng.sealed_commitment = doc["sealed_commitment"]
        eng.aggregate_chain = doc["aggregate_chain"]
        eng.recent = deque(doc["recent"], maxlen=RECENT_DISPATCHES)
        eng.readiness_last = dict(doc["readiness_last"])
        eng.counters = dict(doc["counters"])
        eng.funding = dict(doc["funding"])
        eng.continuations = deque(doc["continuations"], maxlen=RECENT_DISPATCHES)
        if set(eng.tracks) != {k for k, _ in doc["tracks"]}:
            raise TemporalError("temporal state tracks do not match the profile/coverage")
        for k, td in doc["tracks"]:
            t = eng.tracks[k]
            t.next_start, t.late_excluded = _dt(td["next_start"]), td["late_excluded"]
            t.sealed_by_status = dict(td["sealed_by_status"])
            t.sealed = deque(td["sealed"], maxlen=t.retention)
            t.open = {a.start: a for a in (_Acc.decode(x) for x in td["open"])}
        return eng


def pack(engine: TemporalEngine) -> tuple[bytes, str]:
    raw = canonical(engine.encode())
    return zlib.compress(raw, 6), hashlib.sha256(raw).hexdigest()


def unpack(blob: bytes, sha256: str) -> TemporalEngine:
    try:
        raw = zlib.decompress(blob)
    except zlib.error as exc:
        raise TemporalError(f"temporal state blob not decompressible: {exc}") from None
    if hashlib.sha256(raw).hexdigest() != sha256:
        raise TemporalError("temporal state SHA-256 mismatch (corrupt)")
    try:
        doc = json.loads(raw)
    except ValueError as exc:
        raise TemporalError(f"temporal state JSON unreadable: {exc}") from None
    eng = TemporalEngine.decode(doc)
    if canonical(eng.encode()) != raw:
        raise TemporalError("temporal state does not round-trip exactly")
    return eng


def for_feed(manifest, profile: TemporalProfile) -> TemporalEngine:
    """Engine bound to a feed manifest's coverage, availability and content identity."""
    ap = manifest.availability_policy
    return TemporalEngine(profile, tuple(manifest.coverage), basis=ap.basis, availability_policy_id=ap.policy_id,
                          content_identity=manifest.content_identity,
                          context={"feed_content_identity": manifest.content_identity,
                                   "availability_policy_id": ap.policy_id})


def profile_for_feed(manifest, **kw) -> TemporalProfile:
    """Default engineering profile for a feed: modeled sources use the complete-prefix clock with the declared
    availability delay as closure allowance; recordings use the synthetic receipt barrier (no dispatch tape)."""
    ap = manifest.availability_policy
    if ap.basis == AvailabilityBasis.MODELED:
        return default_profile(ClockPolicy.MODELED_COMPLETE_PREFIX, ap.bar_delay, **kw)
    return default_profile(ClockPolicy.RECORDED_SYNTHETIC_BARRIER, DEFAULT_RECORDED_ALLOWANCE, **kw)


__all__ = ["HORIZON_ORDER", "TemporalEngine", "TemporalError", "default_profile", "for_feed", "pack", "unpack",
           "profile_for_feed"]
