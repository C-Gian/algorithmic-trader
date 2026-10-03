"""Small reference aggregator for differential tests and Deep validation v2 (``temporal.reference.v1``).

Deliberately naive and separate from ``engine``: it keeps every admitted minute of every unsealed interval in plain
dictionaries, recomputes each aggregate from scratch at sealing (sorting minutes), derives its own closure barrier
times and recomputes the reference-comparable aggregate chain. It shares only the UTC calendar helpers, the
canonical JSON encoding and the documented record-content formula with the engine; it does not implement
dispatch/readiness/deadline callbacks (those are covered by hand-expected fixtures), so its comparison scope is the
sequence of sealed aggregates: identity, status, counts, exact values, known_at, sealing barrier and admitted cursor.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta
from decimal import Decimal

from ..feed.contracts import ChannelCoverage, EventKind, Family, FeedEvent, QualityReason
from ..feed.ordering import canonical
from .calendar import MINUTE, interval_end, interval_start
from .contracts import ClockPolicy, Horizon
from .engine import INITIAL_AGGREGATE, aggregate_link, chain, record_content

REFERENCE_ID = "temporal.reference.v1"
BARS = (Family.TRADE_BAR_1M, Family.MARK_BAR_1M, Family.INDEX_BAR_1M)


def _fmt(v: Decimal | None) -> str | None:
    return None if v is None else str(v)


class ReferenceAggregator:
    def __init__(self, coverage: tuple[ChannelCoverage, ...], horizons: tuple[Horizon, ...],
                 allowance: timedelta, clock_policy: ClockPolicy) -> None:
        if clock_policy == ClockPolicy.RECORDED_DISPATCH_TAPE:
            raise ValueError("the reference derives barriers from the streamed input; tape replay is fixture-only")
        self.policy = clock_policy
        self.allowance = allowance
        self.channels = {c.channel.channel_id: c for c in coverage if c.channel.family in BARS}
        self.horizons = horizons
        # minute -> compact tuple (valid, reason, available, open, high, low, close, contracts, base, quote,
        #                          base_ccy, quote_ccy, index_id); plain data only, so the naive store stays small
        self.minutes: dict[str, dict[datetime, tuple]] = {cid: {} for cid in self.channels}
        # next unsealed interval start per (channel, horizon)
        self.next: dict[tuple[str, Horizon], datetime] = {
            (cid, h): interval_start(h, c.covered_from) for cid, c in self.channels.items() for h in horizons}
        self.cursor = 0
        self.chain = INITIAL_AGGREGATE
        self.sealed: list[dict] = []
        self.clock: datetime | None = None
        self.late = 0
        self.floors: dict[str, datetime] = {}

    # -- barrier derivation -----------------------------------------------------------------------

    def _deadline(self, cid: str, h: Horizon) -> datetime | None:
        s, cov = self.next[(cid, h)], self.channels[cid]
        if s >= cov.covered_until:
            return None
        return min(interval_end(h, s), cov.covered_until) + self.allowance

    def _closure_deadlines_before(self, limit: datetime, inclusive: bool) -> list[datetime]:
        out = []
        for cid, h in sorted(self.next, key=lambda k: (k[0], k[1].value)):
            d = self._deadline(cid, h)
            if d is not None and (d < limit or (inclusive and d == limit)) and (self.clock is None or d > self.clock):
                out.append(d)
        return sorted(set(out))

    def feed(self, e: FeedEvent) -> None:
        a = e.available_time
        while True:  # each closure deadline strictly before this admission is a barrier with the prefix so far
            ds = self._closure_deadlines_before(a, inclusive=False)
            if not ds:
                break
            self.barrier(ds[0])
        self._admit(e)
        if self.policy == ClockPolicy.RECORDED_SYNTHETIC_BARRIER:
            self.barrier(a)

    def finish(self, clock_end: datetime) -> None:
        while True:
            ds = self._closure_deadlines_before(clock_end, inclusive=False)
            if not ds:
                break
            self.barrier(ds[0])
        self.barrier(clock_end)

    # -- admission / sealing ----------------------------------------------------------------------

    def _admit(self, e: FeedEvent) -> None:
        self.cursor += 1
        cid = e.channel.channel_id
        if cid not in self.channels or e.event_end_time != e.event_time + MINUTE:
            return
        cov = self.channels[cid]
        if not cov.covered_from <= e.event_time < cov.covered_until:
            return
        if any(interval_start(h, e.event_time) < self.next[(cid, h)] for h in self.horizons):
            self.late += 1
        p = e.payload
        if e.kind == EventKind.BAR_OBSERVATION:
            trade = e.channel.family == Family.TRADE_BAR_1M
            self.minutes[cid][e.event_time] = (
                True, None, e.available_time, p.open, p.high, p.low, p.close,
                p.volume_contracts if trade else None, p.volume_base if trade else None,
                p.volume_quote if trade else None, p.volume_base_ccy if trade else None,
                p.volume_quote_ccy if trade else None, getattr(p, "index_id", None))
        else:
            self.minutes[cid][e.event_time] = (False, p.reason, e.available_time)

    def barrier(self, t: datetime) -> None:
        self.clock = t
        for cid, h in sorted(self.next, key=lambda k: (k[0], k[1].value)):
            cov = self.channels[cid]
            while self.next[(cid, h)] < cov.covered_until:
                s = self.next[(cid, h)]
                end = interval_end(h, s)
                lo, hi = max(s, cov.covered_from), min(end, cov.covered_until)
                due = hi + self.allowance <= t
                if not due and end > t:
                    break  # neither due nor ended: nothing to check (avoids building month-sized lists)
                in_cov = [lo + MINUTE * i for i in range(int((hi - lo) / MINUTE))]
                if not due:
                    mins = self.minutes[cid]
                    have = [m for m in in_cov if m in mins and mins[m][2] <= t]
                    if not (in_cov and len(have) == len(in_cov)):
                        break
                self._seal(cid, h, s, end, in_cov, t)
                self.next[(cid, h)] = end
        # drop minutes no longer needed by any horizon (only when the oldest unsealed start moved)
        for cid in self.channels:
            floor = min(self.next[(cid, h)] for h in self.horizons)
            if self.floors.get(cid) != floor:
                self.floors[cid] = floor
                self.minutes[cid] = {m: ev for m, ev in self.minutes[cid].items() if m >= floor}

    def _seal(self, cid: str, h: Horizon, s: datetime, end: datetime, in_cov: list[datetime], t: datetime) -> None:
        expected = int((end - s) / MINUTE)
        reasons: dict[str, int] = {}
        valid: list[tuple] = []
        missing = rejected = 0
        for m in in_cov:
            ev = self.minutes[cid].get(m)
            # only evidence for THIS interval admitted while it was unsealed counts (late evidence never joins)
            if ev is None:
                reasons["ABSENT_AT_SEAL"] = reasons.get("ABSENT_AT_SEAL", 0) + 1
                missing += 1
            elif ev[0]:
                valid.append(ev)
            else:
                r = ev[1].value
                reasons[r] = reasons.get(r, 0) + 1
                if ev[1] == QualityReason.MISSING:
                    missing += 1
                else:
                    rejected += 1
        outside = expected - len(in_cov)
        if outside:
            reasons["OUTSIDE_COVERAGE"] = outside
            missing += outside
        if outside:
            status = "OUTSIDE_COVERAGE"
        elif len(valid) == expected:
            status = "COMPLETE"
        else:
            status = "INCOMPLETE"
        values = None
        if valid:  # in_cov is in market-slot order, so valid[0] / valid[-1] are the first / last slots
            first, last = valid[0], valid[-1]
            fam = self.channels[cid].channel.family
            values = {"open": str(first[3]), "high": str(max(v[4] for v in valid)),
                      "low": str(min(v[5] for v in valid)), "close": str(last[6]),
                      "volume_contracts": None, "volume_base": None, "volume_base_ccy": None, "volume_quote": None,
                      "volume_quote_ccy": None, "index_id": None}
            if fam == Family.TRADE_BAR_1M:
                values.update(volume_contracts=_fmt(sum((v[7] for v in valid), Decimal(0))),
                              volume_base=_fmt(sum((v[8] for v in valid), Decimal(0))),
                              volume_quote=_fmt(sum((v[9] for v in valid), Decimal(0))),
                              volume_base_ccy=last[10], volume_quote_ccy=last[11])
            elif fam == Family.INDEX_BAR_1M:
                values["index_id"] = last[12]
        known = max([end, *(v[2] for v in valid)]) if status == "COMPLETE" else t
        counts = {"expected": expected, "valid": len(valid), "missing": missing, "rejected": rejected,
                  "reasons": dict(sorted(reasons.items()))}
        rid = f"{cid}/{h.value}/{s.isoformat()}"
        digest = hashlib.sha256(canonical(record_content(rid, status, counts, values, known.isoformat(),
                                                         s.isoformat(), end.isoformat()))).hexdigest()
        link = aggregate_link(rid, digest, t.isoformat(), self.cursor)
        self.chain = chain(self.chain, link)
        self.sealed.append({**link, "status": status, "counts": counts, "values": values})
