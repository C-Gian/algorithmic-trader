"""Professional clock and input frontier beside the factual reducer and the R2 temporal engine.

One runtime drives the same sequential professional fold for historical (max / paced / STEP), recorded and live
execution; only the input policy differs:

* the kernel applies a factual event, lets the temporal engine run its barriers strictly before the event's
  availability (sealed records are captured through the engine's listener), then calls ``before_admit(e)``: every
  professional barrier strictly before ``e.available_time`` is dispatched in time order (admitted minute facts,
  sealed records, quotes/capability inputs and the core's own timers); then ``admit(e)`` buffers the event;
* ``advance(limit, inclusive)`` is the explicit tape/clock command used at the finite clock end and by live sessions.

So an entire modeled tie group (all evidence available at t) is admitted before the dispatch at t, exactly like the
temporal complete-prefix policy, and a dispatch never runs twice for the same (time, frontier). The evaluator sees a
dispatch's new trade minutes BEFORE the core processes that dispatch (pre-open rule) and the core's journal after it.

State (``pending`` inputs, core, evaluator) is explicit and restorable at any factual cursor; dispatches happen
lazily, so checkpoint cadence and pacing never change the semantic output.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from ..feed.contracts import EventKind, Family as FeedFamily, FeedEvent
from .core import AdviserConfig, AdviserCore, EventInput, Quote, STATE_FORMAT as CORE_FORMAT
from .evaluator import Evaluator
from .measures import Bar

RUNTIME_FORMAT = "algotrader.adviser-runtime.v2"  # v2: taped connection inputs; core state v2


def _iso(t: datetime | None) -> str | None:
    return None if t is None else t.isoformat()


class AdviserRuntime:
    def __init__(self, core: AdviserCore, evaluator: Evaluator | None = None) -> None:
        self.core = core
        self.ev = evaluator
        self.pending: list[tuple[datetime, int, str, Any]] = []  # (time, order, kind, payload)
        self._order = 0
        self.journal_out: list[dict] = []
        self.records_out: list[dict] = []
        self.dispatches = 0
        self.finished = False
        self.admitted = core.cursor  # factual events admitted into the professional frontier (incl. a pending tie group)

    # -- wiring ---------------------------------------------------------------------------------------------------

    def attach(self, temporal) -> None:
        temporal.sealed_listeners.append(self.on_sealed)

    def on_sealed(self, rec) -> None:
        if rec.channel.family != FeedFamily.TRADE_BAR_1M:
            return
        doc = json.loads(rec.model_dump_json())
        self._push(rec.sealed_at, "sealed", doc)

    def _push(self, t: datetime, kind: str, payload: Any) -> None:
        self._order += 1
        self.pending.append((t, self._order, kind, payload))

    # -- factual stream -------------------------------------------------------------------------------------------

    def before_admit(self, e: FeedEvent) -> None:
        self.advance(e.available_time, inclusive=False)

    def admit(self, e: FeedEvent, cursor: int) -> None:
        if cursor != self.admitted:
            raise ValueError(f"adviser admission discontinuity: event at cursor {cursor}, admitted {self.admitted}")
        self.admitted = cursor + 1
        self._push(e.available_time, "event", (e, cursor))

    def quote(self, q: Quote, at: datetime) -> None:
        self._push(at, "quote", q)

    def capability(self, ev: EventInput, at: datetime) -> None:
        self._push(at, "capability", ev)

    def origin(self, origin: str, at: datetime) -> None:
        self._push(at, "origin", origin)

    def connection(self, state: str, at: datetime) -> None:
        """Live candle-session connection change (CONNECTED / DISCONNECTED / STOPPED), dispatched at ``at``."""
        self._push(at, "connection", state)

    def capability_restart(self, at: datetime, reason: str) -> None:
        """Live restart after downtime: a gap overlapping an ongoing thesis makes it UNASSESSABLE (MP-001 §9)."""
        self._push(at, "restart", reason)

    # -- clock ------------------------------------------------------------------------------------------------------

    def next_time(self) -> datetime | None:
        c = [x[0] for x in self.pending]
        nd = self.core.next_deadline()
        if nd is not None:
            c.append(nd)
        if self.ev is not None:
            ed = self.ev.next_deadline(self.core.clock)
            if ed is not None:
                c.append(ed)
        return min(c) if c else None

    def advance(self, limit: datetime, inclusive: bool = True) -> int:
        n = 0
        while True:
            t = self.next_time()
            if t is None or t > limit or (t == limit and not inclusive):
                return n
            self._dispatch(t)
            n += 1

    def finish(self, clock_end: datetime) -> None:
        self.advance(clock_end, inclusive=True)
        if self.ev is not None:
            self.ev.finish(clock_end)
            self.records_out.extend(self.ev.records)
            self.ev.records = []
        self.finished = True

    def _dispatch(self, t: datetime) -> None:
        now = [x for x in self.pending if x[0] <= t]
        self.pending = [x for x in self.pending if x[0] > t]
        now.sort(key=lambda x: x[1])
        core = self.core
        trade_items: list = []
        marks: list = []
        for _, _, kind, payload in now:
            if kind == "event":
                e, cursor = payload
                core.admit_event(e, cursor)
                if self.ev is not None:
                    fam = e.channel.family
                    if fam == FeedFamily.TRADE_BAR_1M and (core.cfg.channel_ids.get("trade") in (None, e.channel.channel_id)):
                        trade_items.append(e)
                    elif fam == FeedFamily.MARK_BAR_1M and e.kind == EventKind.BAR_OBSERVATION:
                        marks.append((e.event_end_time, e.payload.close))
                    elif fam == FeedFamily.FUNDING_SETTLEMENT and e.kind == EventKind.FUNDING_OBSERVATION:
                        self.ev.on_funding({"event_time": e.event_time.isoformat(),
                                            "rate": str(e.payload.funding_rate), "event_id": e.event_id})
            elif kind == "sealed":
                core.admit_sealed(payload)
            elif kind == "quote":
                core.admit_quote(payload)
            elif kind == "capability":
                core.admit_capability(payload)
            elif kind == "origin":
                core.set_origin(payload, t)
            elif kind == "restart":
                core.admit_restart(payload)
            elif kind == "connection":
                core.admit_connection(payload)
        if self.ev is not None:
            self.ev.now = t
            self.ev.on_minutes(_trade_items(trade_items, self.ev.last_trade_end), marks)
        entries = core.dispatch(t)
        self.dispatches += 1
        if self.ev is not None:
            self.ev.on_journal(entries)
            self.ev.after_dispatch(t, core)
            if self.ev.records:
                self.records_out.extend(self.ev.records)
                self.ev.records = []
        self.journal_out.extend(core.journal)
        core.journal = []

    # -- outputs / state --------------------------------------------------------------------------------------------

    def take(self) -> tuple[list[dict], list[dict]]:
        j, r = self.journal_out, self.records_out
        self.journal_out, self.records_out = [], []
        return j, r

    def commitment(self) -> dict:
        ev = self.ev
        return {"professional_seq": self.core.seq, "factual_cursor": self.admitted,
                "clock": _iso(self.core.clock), "journal_seq": self.core.journal_seq,
                "journal_chain": self.core.journal_chain, "evaluation_seq": ev.record_seq if ev else None,
                "evaluation_chain": ev.record_chain if ev else None}

    def encode(self) -> dict:
        if self.journal_out or self.records_out:
            raise RuntimeError("undrained adviser outputs at a state boundary")
        pend = []
        for t, order, kind, payload in self.pending:
            if kind == "event":
                e, cursor = payload
                pend.append([_iso(t), order, kind, {"event": e.model_dump(mode="json"), "cursor": cursor}])
            elif kind in ("quote", "capability"):
                pend.append([_iso(t), order, kind, payload.encode()])
            else:
                pend.append([_iso(t), order, kind, payload])
        return {"format": RUNTIME_FORMAT, "core_format": CORE_FORMAT, "core": self.core.encode(),
                "evaluator": self.ev.encode() if self.ev else None, "pending": pend, "order": self._order,
                "dispatches": self.dispatches, "finished": self.finished, "admitted": self.admitted}

    @classmethod
    def decode(cls, doc: dict, cfg: AdviserConfig, evaluator: Evaluator | None) -> AdviserRuntime:
        if doc.get("format") != RUNTIME_FORMAT:
            raise ValueError(f"adviser runtime format {doc.get('format')!r} is not {RUNTIME_FORMAT}")
        core = AdviserCore.decode(doc["core"], cfg)
        if (doc["evaluator"] is None) != (evaluator is None):
            raise ValueError("evaluator presence differs from the pinned configuration")
        if evaluator is not None:
            evaluator.restore(doc["evaluator"])
        rt = cls(core, evaluator)
        for t, order, kind, payload in doc["pending"]:
            tt = datetime.fromisoformat(t)
            if kind == "event":
                payload = (FeedEvent.model_validate(payload["event"]), payload["cursor"])
            elif kind == "quote":
                payload = Quote.decode(payload)
            elif kind == "capability":
                payload = EventInput.decode(payload)
            rt.pending.append((tt, order, kind, payload))
        rt._order, rt.dispatches, rt.finished = doc["order"], doc["dispatches"], doc["finished"]
        rt.admitted = doc["admitted"]
        return rt


def _trade_items(events: list[FeedEvent], last_end: datetime | None) -> list:
    out: list = []
    for e in sorted(events, key=lambda e: e.event_time):
        if e.kind == EventKind.SLOT_QUALITY:
            out.append(("GAP", e.event_time, f"TRADE_1M_{e.payload.reason.value}"))
            continue
        p = e.payload
        out.append(Bar(e.event_time, e.event_end_time, p.open, p.high, p.low, p.close, p.volume_base, e.available_time,
                       e.event_id))
    return out
