"""Sequential causal professional fold — MP-001 ``btc.context-action.v0.2`` (implementation ``adviser.core.v2``).

The core consumes only admitted factual inputs (complete trade/mark/index 1m bars and slot-quality events, settled
funding), already sealed R2 temporal records, typed capability inputs (quotes, event/incident records, origin
changes) and its own timers. It never reads raw datasets, future rows, evaluator outcomes or suffix metadata.

One professional dispatch at clock time t processes, in MP-001 §5 order:

1. admitted 1m facts (slot order) and newly sealed 15m/1h/4h/day/week/month records (1h before 15m);
2. derived updates: 1h observed context, 15m scale/phase, pivots/period landmarks, BROKEN marks, retirements;
3. expiry and existing-object invalidations: call contacts/gaps/premise/progress/deadline, attempt and box expiry,
   B cancellation + opposite-edge retirement (derived together from the pre-dispatch attempt state, applied
   atomically), A spent/withdrawn, context-forbidden/adverse-expansion withdrawals;
4. revise / create / arm episodes, boxes and B/C attempts;
5. trigger evaluation on eligible complete 1m bars (start >= actual arm publication);
6. geometry/actionability, selection (slot, conflict, A>B>C priority), issue;
7. entry reassessment of the ongoing call; MarketView; journal publication of material changes.

SHORT rules are the exact price-axis reflection of LONG (P -> -P, high -> -low, low -> -high): every family state
machine below runs in "transformed" coordinates x' = d*x and converts back, so mirrored inequalities need no ad hoc
choices. All arithmetic is Decimal.

State is explicit, bounded and restorable (``encode``/``decode``; format ``algotrader.adviser-state.v2``). Complete
call history lives in the journal, never in unbounded hot memory.
"""

from __future__ import annotations

import hashlib
import json
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from ..feed.contracts import EventKind, Family as FeedFamily, FeedEvent
from ..feed.ordering import canonical
from . import contracts as sc
from . import geometry as geo
from .identity import CapabilityProfile, Execution
from .measures import Bar, ZERO, div, displacement, efficiency, median, round_down, round_up, scale, trs, zone_halfwidth
from .params import Params

STATE_FORMAT = "algotrader.adviser-state.v2"  # v2: taped live candle-connection adequacy
MINUTE = timedelta(minutes=1)
EPS = timedelta(microseconds=1)
INITIAL_JOURNAL = hashlib.sha256(b"algotrader.adviser.journal.v1\x00").hexdigest()
FAM_RANK = {"A": 0, "B": 1, "C": 2}
PRICE_REASONS = frozenset({"PRICE_OUTSIDE_STRUCTURAL_AREA", "NO_ROOM_AFTER_COSTS", "AT_OR_BEYOND_INVALIDATION",
                           "REWARD_RISK_BELOW_MINIMUM"})
QUOTE_REASONS = frozenset({"QUOTE_UNAVAILABLE", "QUOTE_STALE", "QUOTE_CLOCK_UNCERTAIN"})
# live candle-session adequacy (taped connection commands): entry cannot be verified, the thesis is not judged by it
CONNECTION_REASONS = frozenset({"CANDLE_CONNECTION_LOST", "CANDLE_CONNECTION_AWAITING_FRESH_BAR",
                                "LIVE_SESSION_STOPPED"})
UNVERIFIED_REASONS = QUOTE_REASONS | CONNECTION_REASONS
CONNECTION_STATES = {"CONNECTED": None, "DISCONNECTED": "CANDLE_CONNECTION_LOST",
                     "AWAITING_FRESH_BAR": "CANDLE_CONNECTION_AWAITING_FRESH_BAR", "STOPPED": "LIVE_SESSION_STOPPED"}
TERMINAL_THESIS = frozenset({"TARGET_REACHED", "INVALIDATED", "TIME_EXPIRED", "UNASSESSABLE", "RETIRED"})


def _iso(t: datetime | None) -> str | None:
    return None if t is None else t.isoformat()


def _dt(s: str | None) -> datetime | None:
    return None if s is None else datetime.fromisoformat(s)


def _d(x: str | None) -> Decimal | None:
    return None if x is None else Decimal(x)


def _s(x: Decimal | None) -> str | None:
    return None if x is None else str(x)


def _h(*parts: Any) -> str:
    return hashlib.sha256(canonical(list(parts))).hexdigest()[:12]


def dname(d: int) -> str:
    return "LONG" if d > 0 else "SHORT"


def tbar(b: Bar, d: int) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    """(o', h', l', c') of a bar in the direction-transformed price axis."""
    if d > 0:
        return b.o, b.h, b.lo, b.c
    return -b.o, -b.lo, -b.h, -b.c


def ctx_t(ctx: str, d: int) -> str:
    if d > 0 or ctx in ("BALANCED", "UNAVAILABLE"):
        return ctx
    return {"UP": "DOWN", "DOWN": "UP"}[ctx]


# --------------------------------------------------------------------------------------------------------------
# Inputs
# --------------------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Quote:
    """A validated public ticker snapshot (live). Validation (positive, uncrossed, instrument, monotone source time,
    not future) happens in the quote client; the core applies freshness on BOTH source and receipt time."""

    bid: Decimal
    ask: Decimal
    source_ts: datetime
    received_at: datetime
    inst_id: str
    raw_sha256: str

    def encode(self) -> dict:
        return {"bid": str(self.bid), "ask": str(self.ask), "source_ts": _iso(self.source_ts),
                "received_at": _iso(self.received_at), "inst_id": self.inst_id, "raw_sha256": self.raw_sha256}

    @classmethod
    def decode(cls, d: dict) -> Quote:
        return cls(Decimal(d["bid"]), Decimal(d["ask"]), _dt(d["source_ts"]), _dt(d["received_at"]), d["inst_id"],
                   d["raw_sha256"])


@dataclass(frozen=True)
class EventInput:
    """Typed known-event / incident record (availability-versioned; MP-001 §7)."""

    event_id: str
    revision: int
    event_type: str
    scope: str
    schedule_time: datetime | None
    schedule_known_at: datetime | None
    content_known_at: datetime | None
    provenance_sha256: str
    cancelled: bool = False
    incident: bool = False
    resolved: bool = False

    def encode(self) -> dict:
        return {"event_id": self.event_id, "revision": self.revision, "event_type": self.event_type,
                "scope": self.scope, "schedule_time": _iso(self.schedule_time),
                "schedule_known_at": _iso(self.schedule_known_at), "content_known_at": _iso(self.content_known_at),
                "provenance_sha256": self.provenance_sha256, "cancelled": self.cancelled, "incident": self.incident,
                "resolved": self.resolved}

    @classmethod
    def decode(cls, d: dict) -> EventInput:
        return cls(d["event_id"], d["revision"], d["event_type"], d["scope"], _dt(d["schedule_time"]),
                   _dt(d["schedule_known_at"]), _dt(d["content_known_at"]), d["provenance_sha256"], d["cancelled"],
                   d["incident"], d["resolved"])


@dataclass(frozen=True)
class AdviserConfig:
    instrument: str
    tick: Decimal
    profile: CapabilityProfile
    method: sc.MethodRef
    clock_policy: str
    params: Params
    eval_start: datetime | None = None  # historical evaluation window; None = live session
    eval_end: datetime | None = None
    origin: str = sc.Origin.HISTORICAL_MODELED.value
    channel_ids: dict[str, str] = field(default_factory=dict)  # family -> channel id (trade/mark/index)

    def fingerprint(self) -> str:
        return hashlib.sha256(canonical({
            "format": STATE_FORMAT, "instrument": self.instrument, "tick": str(self.tick),
            "profile": self.profile.model_dump(mode="json"), "method": self.method.model_dump(mode="json"),
            "clock_policy": self.clock_policy, "eval_start": _iso(self.eval_start), "eval_end": _iso(self.eval_end),
            "channels": dict(sorted(self.channel_ids.items())),
        })).hexdigest()


# --------------------------------------------------------------------------------------------------------------
# State objects
# --------------------------------------------------------------------------------------------------------------


@dataclass
class Landmark:
    lid: str
    ltype: str
    side: str  # HIGH / LOW
    price: Decimal
    z: Decimal
    s15: Decimal
    horizon: str
    sources: list[str]
    extremum_time: datetime | None
    created_at: datetime
    created_seq: int
    retire_at: datetime | None
    status: str = "ACTIVE"
    status_reason: str | None = None
    owner: str | None = None

    def encode(self) -> dict:
        return {"lid": self.lid, "ltype": self.ltype, "side": self.side, "price": str(self.price), "z": str(self.z),
                "s15": str(self.s15), "horizon": self.horizon, "sources": self.sources,
                "extremum_time": _iso(self.extremum_time), "created_at": _iso(self.created_at),
                "created_seq": self.created_seq, "retire_at": _iso(self.retire_at), "status": self.status,
                "status_reason": self.status_reason, "owner": self.owner}

    @classmethod
    def decode(cls, d: dict) -> Landmark:
        return cls(d["lid"], d["ltype"], d["side"], Decimal(d["price"]), Decimal(d["z"]), Decimal(d["s15"]),
                   d["horizon"], list(d["sources"]), _dt(d["extremum_time"]), _dt(d["created_at"]), d["created_seq"],
                   _dt(d["retire_at"]), d["status"], d["status_reason"], d["owner"])

    def opposes(self, d: int) -> bool:
        return (self.side == "HIGH") == (d > 0)

    def p_t(self, d: int) -> Decimal:
        return self.price * d

    def info(self, t: datetime) -> dict[str, str | None]:
        return {"landmark_id": self.lid, "type": self.ltype, "price": str(self.price), "zone_halfwidth": str(self.z),
                "source": ",".join(self.sources), "created_at": _iso(self.created_at),
                "age_minutes": str(int((t - self.created_at) / MINUTE))}


@dataclass
class Attempt:
    """One persistent episode/attempt (A episode, B or C attempt). Prices with suffix _t are transformed (d*x)."""

    aid: str
    family: str
    d: int
    owner: str | None
    born_at: datetime
    born_seq: int
    sources: list[str]
    deadline: datetime
    s15: Decimal
    z: Decimal
    status: str = "WATCH"  # WATCH / ARMED (pending); terminal states leave the active table
    k_t: Decimal | None = None
    v_t: Decimal | None = None
    arm_at: datetime | None = None
    arm_seq: int | None = None
    pre_live: bool = False  # armed before live activation: cannot issue a live call
    # A
    a_t: Decimal | None = None  # impulse A (transformed low extreme)
    b_t: Decimal | None = None  # impulse B (transformed high extreme)
    bars_seen: int = 0
    lower_close: bool = False
    prev_close_t: Decimal | None = None
    r_t: Decimal | None = None
    anchor: str | None = None
    anchor_h_t: Decimal | None = None
    b_broken: bool = False
    renewal: str | None = None
    # B
    retest_seen: int = 0

    def encode(self) -> dict:
        return {k: (str(v) if isinstance(v, Decimal) else _iso(v) if isinstance(v, datetime) else v)
                for k, v in self.__dict__.items()}

    @classmethod
    def decode(cls, d: dict) -> Attempt:
        x = dict(d)
        for k in ("born_at", "deadline", "arm_at"):
            x[k] = _dt(x[k])
        for k in ("s15", "z", "k_t", "v_t", "a_t", "b_t", "prev_close_t", "r_t", "anchor_h_t"):
            x[k] = _d(x[k])
        x["sources"] = list(x["sources"])
        return cls(**x)


@dataclass
class Box:
    bid: str
    low: Decimal
    up: Decimal
    mid: Decimal
    s15: Decimal
    z: Decimal
    created_at: datetime
    created_seq: int
    expires_at: datetime
    sources: list[str]
    used: dict[str, bool] = field(default_factory=lambda: {"B+": False, "B-": False, "C+": False, "C-": False})
    broken: dict[str, bool] = field(default_factory=lambda: {"U": False, "L": False})

    def encode(self) -> dict:
        return {"bid": self.bid, "low": str(self.low), "up": str(self.up), "mid": str(self.mid), "s15": str(self.s15),
                "z": str(self.z), "created_at": _iso(self.created_at), "created_seq": self.created_seq,
                "expires_at": _iso(self.expires_at), "sources": self.sources, "used": dict(sorted(self.used.items())),
                "broken": dict(sorted(self.broken.items()))}

    @classmethod
    def decode(cls, d: dict) -> Box:
        return cls(d["bid"], Decimal(d["low"]), Decimal(d["up"]), Decimal(d["mid"]), Decimal(d["s15"]),
                   Decimal(d["z"]), _dt(d["created_at"]), d["created_seq"], _dt(d["expires_at"]), list(d["sources"]),
                   dict(d["used"]), dict(d["broken"]))

    def edges_t(self, d: int) -> tuple[Decimal, Decimal, Decimal]:
        """(L', U', M') in the transformed axis of direction d."""
        return (self.low, self.up, self.mid) if d > 0 else (-self.up, -self.low, -self.mid)


@dataclass
class Call:
    cid: str
    aid: str
    family: str
    d: int
    origin: str
    issued_at: datetime
    issue_seq: int
    trigger_start: datetime
    ref: Decimal
    v: Decimal
    t: Decimal
    target_type: str
    limiting: dict | None
    s15: Decimal
    area: tuple[Decimal, Decimal]
    expected: tuple[int, int]
    min_residual: int
    hard_deadline: datetime
    progress_at: datetime
    premise_kind: str
    premise_level: Decimal  # real price; failure is a 15m close strictly beyond it (adverse side)
    entry: str = "AVAILABLE"
    entry_reasons: list[str] = field(default_factory=list)
    conditions_ok: bool = True
    thesis: str = "ONGOING"
    terminal_reason: str | None = None
    terminal_at: datetime | None = None
    revision: int = 0
    max_fav_t: Decimal | None = None  # max d*(close - ref) over wholly post-issue complete minutes
    last_end: datetime | None = None  # end of the last processed post-issue minute (contiguity)
    entry_reopens: int = 0
    progress_done: bool = False

    def encode(self) -> dict:
        out = {}
        for k, v in self.__dict__.items():
            if isinstance(v, Decimal):
                out[k] = str(v)
            elif isinstance(v, datetime):
                out[k] = v.isoformat()
            elif k == "area":
                out[k] = [str(v[0]), str(v[1])]
            elif k == "expected":
                out[k] = list(v)
            else:
                out[k] = v
        return out

    @classmethod
    def decode(cls, d: dict) -> Call:
        x = dict(d)
        for k in ("issued_at", "trigger_start", "hard_deadline", "progress_at", "terminal_at", "last_end"):
            x[k] = _dt(x[k])
        for k in ("ref", "v", "t", "s15", "premise_level", "max_fav_t"):
            x[k] = _d(x[k])
        x["area"] = (Decimal(x["area"][0]), Decimal(x["area"][1]))
        x["expected"] = (x["expected"][0], x["expected"][1])
        x["entry_reasons"] = list(x["entry_reasons"])
        return cls(**x)


# --------------------------------------------------------------------------------------------------------------
# Core
# --------------------------------------------------------------------------------------------------------------


class AdviserError(Exception):
    """Inconsistent input order or state (visible failure, never silent repair)."""


class AdviserCore:
    def __init__(self, config: AdviserConfig) -> None:
        self.cfg = config
        self.p = config.params
        self.tick = config.tick
        ret = self.p.retention
        self.m15: deque[Bar] = deque(maxlen=ret.get("trade_15m", 128))
        self.h1: deque[Bar] = deque(maxlen=ret.get("trade_1h", 192))
        self.broad: dict[str, deque[Bar]] = {"4h": deque(maxlen=ret.get("trade_4h", 8)),
                                             "1d": deque(maxlen=ret.get("trade_day", 3)),
                                             "1w": deque(maxlen=ret.get("trade_week", 2)),
                                             "1mo": deque(maxlen=ret.get("trade_month", 2))}
        self.last_sealed_end: dict[str, datetime | None] = {"15m": None, "1h": None}
        self.gaps: dict[str, int] = {"15m": 0, "1h": 0, "1m": 0}
        self.last_1m: Bar | None = None
        self.last_1m_end: datetime | None = None
        self.recent_1m: deque[Bar] = deque(maxlen=4)  # bounded: event pre-reference (strictly before event time)
        self.s15_hist: deque[tuple[str, str]] = deque(maxlen=4)  # (known_at, S15) for the event pre-event scale
        # derived
        self.s15: Decimal | None = None
        self.phase = {"phase": "UNAVAILABLE", "dir": None, "cr": None, "er6": None, "disp6": None, "since": None,
                      "prev": None, "net3": None}
        self.ctx = {"ctx": "UNAVAILABLE", "er8": None, "disp8": None, "s1h": None, "since": None}
        self.part: Decimal | None = None
        # landmarks
        self.landmarks: dict[str, Landmark] = {}
        self.pending_pivots: list[dict] = []
        self.pending_periods: list[dict] = []
        # candidates
        self.attempts: dict[str, Attempt] = {}
        self.latch: dict[str, str] = {"1": "INIT", "-1": "INIT"}
        self.qa_last: dict[str, bool | None] = {"1": None, "-1": None}
        self.box: Box | None = None
        self.box_token = "INIT"  # INIT / NEED_FALSE / READY / TOKEN
        self.comp_prev: bool | None = None
        # calls
        self.call: Call | None = None
        self.recent_calls: deque[dict] = deque(maxlen=12)
        self.call_count = 0
        # derivatives / events / quotes
        self.slot_px: dict[str, dict[str, str]] = {}  # pending same-slot closes (trade/mark/index)
        self.disl: dict[str, dict] = {"TRADE_MARK": {"base": [], "last_slot": None, "cur": None, "status": "UNAVAILABLE"},
                                      "TRADE_INDEX": {"base": [], "last_slot": None, "cur": None, "status": "UNAVAILABLE"}}
        self.funding_last: dict | None = None
        self.events: dict[str, dict] = {}
        self.quote: Quote | None = None
        self.quote_status = "NOT_COVERED" if config.profile.execution == Execution.HISTORICAL_BASE else "UNAVAILABLE"
        # live candle-session connection (taped input; None = not a live session input, e.g. historical)
        self.connection: dict | None = None
        self._entry_prev: str | None = None  # transient: entry status before the revision being emitted
        # clock / frontier / identity
        self.clock: datetime | None = None
        self.seq = 0  # professional input sequence
        self.cursor = 0  # admitted factual cursor
        self.origin = config.origin
        self.live_since: datetime | None = None
        self.window = "WARMUP" if config.eval_start is not None else "LIVE"
        self.boundary: dict[str, Any] = {}
        # outputs
        self.journal: list[dict] = []
        self.journal_seq = 0
        self.journal_chain = INITIAL_JOURNAL
        self.view_key: tuple | None = None
        self.view: dict | None = None
        self.obs_last: dict[str, str] = {}
        self.counters: dict[str, Any] = _new_counters()
        # bounded durable diagnosis accumulator (MP-001 §11 / WP-009 §4): elapsed time per named condition
        self.diag: dict[str, Any] = _new_diag()
        # pending inputs of the current barrier (bounded: one tie group)
        self._bars: list[FeedEvent] = []
        self._sealed: list[dict] = []
        self._inputs: list[tuple[str, Any]] = []
        self._dirty_nd = True
        self._nd: datetime | None = None
        self._deps: tuple[sc.DependencyRef, ...] = ()

    # ----------------------------------------------------------------------------------------------------------
    # input admission (buffered until the professional barrier)
    # ----------------------------------------------------------------------------------------------------------

    def admit_event(self, e: FeedEvent, cursor: int) -> None:
        self.cursor = cursor + 1
        self.seq += 1
        if e.channel.family == FeedFamily.FUNDING_SETTLEMENT:
            if e.kind == EventKind.FUNDING_OBSERVATION:
                self._inputs.append(("funding", {"event_time": _iso(e.event_time), "known_at": _iso(e.available_time),
                                                 "rate": str(e.payload.funding_rate), "event_id": e.event_id}))
            return
        self._bars.append(e)

    def admit_sealed(self, rec: dict) -> None:
        self.seq += 1
        self._sealed.append(rec)

    def admit_quote(self, q: Quote) -> None:
        self.seq += 1
        self._inputs.append(("quote", q))

    def admit_capability(self, ev: EventInput) -> None:
        self.seq += 1
        self._inputs.append(("event", ev))

    def set_origin(self, origin: str, at: datetime) -> None:
        """Live session origin transition (RECONSTRUCTED -> LIVE activation, or LIVE -> RECONSTRUCTED catch-up)."""
        self.seq += 1
        self._inputs.append(("origin", {"origin": origin, "at": _iso(at)}))

    def admit_connection(self, state: str) -> None:
        """Live candle-session connection change (taped): CONNECTED (subscription confirmed), DISCONNECTED,
        STOPPED. A (re)connection only becomes adequate after a fresh complete trade bar received after it."""
        if state not in ("CONNECTED", "DISCONNECTED", "STOPPED"):
            raise AdviserError(f"unknown connection state {state!r}")
        self.seq += 1
        self._inputs.append(("connection", {"state": state}))

    def admit_restart(self, reason: str) -> None:
        self.seq += 1
        self._inputs.append(("restart", reason))

    def has_pending(self) -> bool:
        return bool(self._bars or self._sealed or self._inputs)

    # ----------------------------------------------------------------------------------------------------------
    # timers
    # ----------------------------------------------------------------------------------------------------------

    def next_deadline(self) -> datetime | None:
        if not self._dirty_nd:
            return self._nd
        c: list[datetime] = []
        for a in self.attempts.values():
            c.append(a.deadline)
        if self.box is not None:
            c.append(self.box.expires_at)
        call = self.call
        if call is not None:
            # residual time holds while remaining >= minimum: the first too-late instant is one microsecond after
            c += [call.hard_deadline, call.progress_at, call.hard_deadline - timedelta(minutes=call.min_residual) + EPS]
        # freshness requires BOTH ages <= allowance: the first stale instant is min(end, known_at) + allowance + 1 us
        # (a recently received old bar never gets an extended life)
        if self.last_1m is not None:
            c.append(min(self.last_1m.end, self.last_1m.known_at) + self.p.fresh_1m + EPS)
        if self.m15:
            c.append(min(self.m15[-1].end, self.m15[-1].known_at) + self.p.fresh_15m + EPS)
        if self.h1:
            c.append(min(self.h1[-1].end, self.h1[-1].known_at) + self.p.fresh_1h + EPS)
        c += [lm.retire_at for lm in self.landmarks.values() if lm.retire_at is not None and lm.status == "ACTIVE"]
        for e in self.events.values():
            for k in ("restrict_start", "schedule_time", "post_min_end"):
                if e.get(k):
                    c.append(_dt(e[k]))
        if self.quote is not None and self.cfg.profile.execution == Execution.LIVE_QUOTED:
            c.append(min(self.quote.source_ts, self.quote.received_at) + self.p.fresh_quote + EPS)
        c += [x for x in (self.cfg.eval_start, self.cfg.eval_end) if x is not None]
        if self.clock is not None:
            c = [x for x in c if x > self.clock]
        self._nd = min(c) if c else None
        self._dirty_nd = False
        return self._nd

    def _touch(self) -> None:
        self._dirty_nd = True

    # ----------------------------------------------------------------------------------------------------------
    # dispatch
    # ----------------------------------------------------------------------------------------------------------

    def dispatch(self, t: datetime) -> list[dict]:
        """Process one professional barrier at clock time t. Returns the journal entries emitted (also appended to
        ``self.journal`` for the runtime to drain)."""
        if self.clock is not None and t < self.clock:
            raise AdviserError(f"professional clock cannot move backwards ({t.isoformat()} < {self.clock.isoformat()})")
        for e in self._bars:
            if e.available_time > t:
                raise AdviserError(f"{e.event_id} available {e.available_time.isoformat()} after barrier {t.isoformat()}")
        self._diag_credit(t)  # the conditions published at the previous dispatch held over [previous, t)
        self.clock = t
        self.seq += 1  # the dispatch command itself is part of the professional input sequence
        self._touch()
        self.counters["dispatches"] += 1
        start = len(self.journal)
        bars, sealed, inputs = self._bars, self._sealed, self._inputs
        self._bars, self._sealed, self._inputs = [], [], []

        # 0. evaluation window boundaries (historical)
        self._windows(t)
        # 1. capability inputs, 1m facts
        for kind, x in inputs:
            self._capability(kind, x, t)
        items = self._ingest_minutes(bars, t)
        new_trade = [x for x in items if isinstance(x, Bar)]
        if (self.connection is not None and self.connection["state"] == "AWAITING_FRESH_BAR"
                and any(b.known_at >= _dt(self.connection["since"]) for b in new_trade)):
            self.connection = {"state": "CONNECTED", "since": _iso(t)}  # fresh usable input after reconnection
        # 2. sealed records and derived updates
        closes15 = self._ingest_sealed(sealed, t)
        self._deps = self._dependencies(t)
        self._landmark_timers(t)
        self._events_tick(t)
        for b in closes15:
            self._mark_broken(b, t)
        # 3. expiry / invalidation of existing objects
        self._call_lifecycle(items, closes15, t)
        self._attempt_expiry(t)
        if closes15:
            self._box_close_flags(closes15[-1], t)
            for b in closes15:
                self._a_close(b, t)
        self._context_withdrawals(t, closes15)
        # 4. revise / create / arm
        if closes15:
            b = closes15[-1]
            self._a_births(b, t)
            self._box_birth(b, t)
            self._bc_geometry(b, t)
        # 5-6. triggers, selection, issue
        triggered = self._triggers(new_trade, t)
        if triggered:
            self._select_and_issue(triggered, new_trade[-1], t)
        # 7. entry reassessment, view, observations
        self._reassess_call(t)
        self._publish_view(t)
        self._publish_observations(t)
        self._diag_update(t)
        return self.journal[start:]

    # -- diagnosis accumulator ---------------------------------------------------------------------------------

    def _diag_conditions(self, t: datetime) -> list[str]:
        """Named conditions holding after this dispatch (several may overlap). Common blockers prevent any new call;
        slot/priority/conflict exposures say why a coincident trigger would be suppressed; NO_ARMED_SCENARIO says
        nothing could trigger."""
        out = {b.split(":")[0] for b in self._common_blockers(t)}
        out.update(self.connection_blockers())
        if self.origin == sc.Origin.RECONSTRUCTED.value:
            out.add("RECONSTRUCTED_CATCH_UP")
        if out:
            out.add("ANY_COMMON_BLOCKER")
        armed = [a for a in self.attempts.values() if a.status == "ARMED"]
        slot = self.call is not None and self.call.thesis == "ONGOING"
        if slot:
            out.add("SLOT_OCCUPIED")
            if armed:
                out.add("SLOT_OCCUPIED_WITH_ARMED")
        elif len({a.d for a in armed}) > 1:
            out.add("CONFLICTED_ARMED")
        elif len(armed) > 1:
            out.add("PRIORITY_COMPETITION")
        if not armed and not slot:
            out.add("NO_ARMED_SCENARIO")
        return sorted(out)

    def _diag_update(self, t: datetime) -> None:
        d = self.diag
        new = self._diag_conditions(t)
        for c in set(new) - set(d["active"]):
            if self._diag_in_window(t):
                d["onsets"][c] = d["onsets"].get(c, 0) + 1
        d["active"], d["last"] = new, _iso(t)

    def _diag_in_window(self, t: datetime) -> bool:
        es, ee = self.cfg.eval_start, self.cfg.eval_end
        return (es is None or t >= es) and (ee is None or t < ee)

    def _diag_credit(self, t: datetime) -> None:
        d = self.diag
        last = _dt(d["last"]) if d["last"] else None
        if last is None or t <= last:
            return
        es, ee = self.cfg.eval_start, self.cfg.eval_end
        a, b = max(last, es) if es else last, min(t, ee) if ee else t
        if b <= a:
            return
        us = (b - a) // timedelta(microseconds=1)
        d["covered_us"] += us
        for c in d["active"]:
            d["us"][c] = d["us"].get(c, 0) + us
        if "ANY_COMMON_BLOCKER" not in d["active"] and "SLOT_OCCUPIED" not in d["active"]:
            # a qualifying trigger at this time could have issued a call (no common blocker, slot free)
            d["us"]["ISSUABLE_IF_TRIGGERED"] = d["us"].get("ISSUABLE_IF_TRIGGERED", 0) + us

    # ----------------------------------------------------------------------------------------------------------
    # windows / capability inputs
    # ----------------------------------------------------------------------------------------------------------

    def _windows(self, t: datetime) -> None:
        es, ee = self.cfg.eval_start, self.cfg.eval_end
        if es is None:
            return
        if self.window == "WARMUP" and t >= es:
            cleared = {"attempts": sorted(self.attempts), "box": self.box.bid if self.box else None,
                       "call": self.call.cid if self.call else None,
                       "latch": dict(self.latch), "box_token": self.box_token}
            for a in sorted(self.attempts.values(), key=lambda a: a.aid):
                self._candidate(a, "CLEARED", "EVALUATION_START_CLEARS_CANDIDATES", t, terminal=True)
            self.attempts.clear()
            if self.box is not None:
                self._retire_box("EVALUATION_START_CLEARS_CANDIDATES", t)
            if self.call is not None:
                self._terminate(self.call, "UNASSESSABLE", "EVALUATION_START_CLEARS_WARMUP_CALL", t)
            self.latch = {"1": "INIT", "-1": "INIT"}
            self.box_token = "INIT"
            self.window = "EVALUATION"
            self.boundary["evaluation_start"] = {"at": _iso(t), "cleared": cleared,
                                                 "warmup_calls": self.counters["calls_issued_warmup"]}
            self._touch()
        if self.window == "EVALUATION" and ee is not None and t >= ee:
            self.window = "TAIL"
            self.boundary["evaluation_end"] = {"at": _iso(t), "open_call": self.call.cid if self.call else None,
                                               "pending_attempts": sorted(self.attempts)}

    def _capability(self, kind: str, x: Any, t: datetime) -> None:
        if kind == "funding":
            self.funding_last = x
        elif kind == "quote":
            q: Quote = x
            if self.quote is not None and q.source_ts <= self.quote.source_ts:
                self.counters["quotes_not_newer"] += 1  # repeating an old snapshot never refreshes its age
                return
            self.quote = q
            self.counters["quotes_admitted"] += 1
        elif kind == "event":
            self._event_input(x, t)
        elif kind == "connection":
            prev = self.connection["state"] if self.connection else None
            state = "AWAITING_FRESH_BAR" if x["state"] == "CONNECTED" else x["state"]
            if state == "AWAITING_FRESH_BAR" and prev in ("CONNECTED", "AWAITING_FRESH_BAR"):
                state = prev  # a repeated confirmation of the same subscription is not a reconnection
            if state != prev:
                self.connection = {"state": state, "since": _iso(t)}
                self.counters["connection_changes"] = self.counters.get("connection_changes", 0) + 1
        elif kind == "restart":
            if self.call is not None and self.call.thesis == "ONGOING":
                self._terminate(self.call, "UNASSESSABLE", x, t)
        elif kind == "origin":
            prev = self.origin
            self.origin = x["origin"]
            if self.origin == sc.Origin.LIVE.value:
                self.live_since = t
                for a in self.attempts.values():
                    a.pre_live = True
                if self.call is not None and self.call.origin != sc.Origin.LIVE.value:
                    self.call.entry_reasons = sorted(set(self.call.entry_reasons) | {"RECONSTRUCTED_REQUIRES_FRESH_CALL"})
            self._emit("observation", t, {
                "lens": "execution", "name": "origin", "values": {"origin": self.origin, "previous": prev},
                "category": self.origin, "decision_role": "LIVE_ACTIVATION_BOUNDARY",
                "meaning": ("Live advice: inputs are current receipts." if self.origin == "LIVE" else
                            "Reconstructed catch-up from fetched history: no current advice, no alerts.")})
        self._touch()

    # ----------------------------------------------------------------------------------------------------------
    # 1m facts
    # ----------------------------------------------------------------------------------------------------------

    def _ingest_minutes(self, bars: list[FeedEvent], t: datetime) -> list[Bar | tuple]:
        """Trade minute items in slot order: complete Bars, or ("GAP", start, reason) for a missing/rejected or
        discontinuous trade minute (processed in order with contacts by the call lifecycle)."""
        items: list[Bar | tuple] = []
        trade_ch = self.cfg.channel_ids.get("trade")
        for e in sorted(bars, key=lambda e: (e.event_time, e.order.family_rank, e.event_id)):
            fam = e.channel.family
            if trade_ch is not None and fam == FeedFamily.TRADE_BAR_1M and e.channel.channel_id != trade_ch:
                continue
            slot = _iso(e.event_time)
            if e.kind == EventKind.SLOT_QUALITY:
                if fam == FeedFamily.TRADE_BAR_1M:
                    self.gaps["1m"] += 1
                    items.append(("GAP", e.event_time, f"TRADE_1M_{e.payload.reason.value}"))
                    self.last_1m_end = max(self.last_1m_end or e.event_end_time, e.event_end_time)
                else:
                    self._disl_break(fam)
                continue
            p = e.payload
            if fam == FeedFamily.TRADE_BAR_1M:
                b = Bar(e.event_time, e.event_end_time, p.open, p.high, p.low, p.close, p.volume_base,
                        e.available_time, e.event_id)
                if self.last_1m_end is not None and b.start > self.last_1m_end:
                    self.gaps["1m"] += 1
                    items.append(("GAP", self.last_1m_end, "TRADE_1M_DISCONTINUITY"))
                if self.last_1m_end is not None and b.end <= self.last_1m_end:
                    raise AdviserError(f"trade minute {slot} not after the last processed minute")
                self.recent_1m.append(b)
                self.last_1m = b
                self.last_1m_end = b.end
                items.append(b)
                self.slot_px.setdefault(slot, {})["trade"] = str(p.close)
            elif fam == FeedFamily.MARK_BAR_1M:
                self.slot_px.setdefault(slot, {})["mark"] = str(p.close)
            elif fam == FeedFamily.INDEX_BAR_1M:
                self.slot_px.setdefault(slot, {})["index"] = str(p.close)
        self._dislocation_update()
        return items

    def _disl_break(self, fam) -> None:
        pair = "TRADE_MARK" if fam == FeedFamily.MARK_BAR_1M else "TRADE_INDEX"
        self.disl[pair]["base"] = []
        self.disl[pair]["last_slot"] = None

    def _dislocation_update(self) -> None:
        """Matched same-slot close pairs; baseline = median |b| of the previous 60 contiguous matched slots."""
        if not self.slot_px:
            return
        slots = sorted(self.slot_px)
        keep = slots[-2:]  # bounded: the current/previous slot may still be waiting for its other families
        for slot in slots:
            px = self.slot_px[slot]
            if "trade" not in px:
                continue
            for pair, ref in (("TRADE_MARK", "mark"), ("TRADE_INDEX", "index")):
                st = self.disl[pair]
                if ref not in px or st.get("cur_slot") == slot:
                    continue
                r = Decimal(px[ref])
                if r <= 0:
                    st["status"] = "UNAVAILABLE"
                    continue
                b = div(10000 * (Decimal(px["trade"]) - r), r)
                last = st["last_slot"]
                if last is not None and datetime.fromisoformat(slot) != datetime.fromisoformat(last) + MINUTE:
                    st["base"] = []
                base = [Decimal(x) for x in st["base"]]
                prior = self.p.disl_prior
                if len(base) >= prior:
                    thr = max(self.p.disl_min_bps, self.p.disl_mult * median([abs(x) for x in base[-prior:]]))
                    st["status"] = "DISLOCATED" if abs(b) > thr else "NORMAL"
                    st["threshold"] = str(thr)
                else:
                    st["status"] = "UNAVAILABLE"
                    st["threshold"] = None
                st["cur"] = str(b)
                st["cur_slot"] = slot
                base.append(b)
                st["base"] = [str(x) for x in base[-prior:]]
                st["last_slot"] = slot
        self.slot_px = {s: self.slot_px[s] for s in keep}

    def dislocation_blocks(self) -> list[str]:
        if self.cfg.profile.dislocation.value != "ENABLE_WHERE_SUPPORTED":
            return []
        return [f"DISLOCATION_{pair}" for pair, st in sorted(self.disl.items()) if st["status"] == "DISLOCATED"]

    # ----------------------------------------------------------------------------------------------------------
    # sealed records / derived updates
    # ----------------------------------------------------------------------------------------------------------

    def _ingest_sealed(self, sealed: list[dict], t: datetime) -> list[Bar]:
        trade_ch = self.cfg.channel_ids.get("trade")
        order = {"1mo": 0, "1w": 1, "1d": 2, "4h": 3, "1h": 4, "15m": 5}
        closes15: list[Bar] = []
        h1_changed = False
        for rec in sorted(sealed, key=lambda r: (order[r["horizon"]], r["interval_start"])):
            if rec["channel"]["family"] != "trade_bar_1m" or (trade_ch and rec["channel_id"] != trade_ch):
                continue
            h = rec["horizon"]
            complete = rec["status"] == "COMPLETE"
            bar = None
            if complete:
                v = rec["values"]
                bar = Bar(_dt(rec["interval_start"]), _dt(rec["interval_end"]), Decimal(v["open"]), Decimal(v["high"]),
                          Decimal(v["low"]), Decimal(v["close"]),
                          None if v.get("volume_base") is None else Decimal(v["volume_base"]), _dt(rec["known_at"]),
                          rec["record_id"])
            if h in ("15m", "1h"):
                win = self.m15 if h == "15m" else self.h1
                last_end = self.last_sealed_end[h]
                start = _dt(rec["interval_start"])
                contiguous = last_end is None or start == last_end
                self.last_sealed_end[h] = _dt(rec["interval_end"])
                if not complete or not contiguous:
                    if win or rec["status"] == "INCOMPLETE" or not contiguous:
                        self.gaps[h] += 1
                    win.clear()
                    self._required_gap(h, rec, t)
                    continue
                win.append(bar)
                if h == "15m":
                    closes15.append(bar)
                else:
                    h1_changed = True
            else:
                if complete:
                    self.broad[h].append(bar)
                    if h in ("1d", "1w", "1mo"):
                        self._period_landmark(h, bar, t)
        if h1_changed:
            self._derive_1h(t)
        if closes15:
            self._derive_15m(t)
        return closes15

    def _required_gap(self, h: str, rec: dict, t: datetime) -> None:
        """A required 15m/1h gap resets rolling windows and expires unfinished structural objects (MP-001 §4)."""
        reason = f"REQUIRED_GAP_{h}:{rec['record_id']}:{rec['status']}"
        if h == "15m":
            self.s15 = None
            self.phase = {**self.phase, "phase": "UNAVAILABLE", "dir": None, "since": t, "prev": self.phase["phase"]}
            self.pending_pivots = [p for p in self.pending_pivots if p["horizon"] != "15m"]
            for a in sorted(self.attempts.values(), key=lambda a: a.aid):
                self._end_attempt(a, "EXPIRED", reason, t)
            if self.box is not None:
                self._retire_box(reason, t)
            self.latch = {"1": "INIT", "-1": "INIT"}  # demands fresh contiguous warmup
            self.box_token = "INIT"
            self.comp_prev = None
            if self.call is not None and self.call.thesis == "ONGOING":
                self._terminate(self.call, "UNASSESSABLE", reason, t)
        else:
            self.ctx = {**self.ctx, "ctx": "UNAVAILABLE", "since": t}
            self.pending_pivots = [p for p in self.pending_pivots if p["horizon"] != "1h"]
        self._touch()

    def _derive_1h(self, t: datetime) -> None:
        bars = list(self.h1)
        n = self.p.ctx_transitions
        prev = self.ctx["ctx"]
        s1h = scale(bars, self.p.median_tr) if len(bars) >= self.p.ready_1h else None
        if s1h is None or len(bars) < n + 1:
            new = {"ctx": "UNAVAILABLE", "er8": None, "disp8": None, "s1h": s1h}
        else:
            closes = [b.c for b in bars[-(n + 1):]]
            er8, d8 = efficiency(closes), displacement(closes, s1h)
            if d8 >= self.p.ctx_disp and er8 >= self.p.ctx_eff:
                c = "UP"
            elif d8 <= -self.p.ctx_disp and er8 >= self.p.ctx_eff:
                c = "DOWN"
            else:
                c = "BALANCED"
            new = {"ctx": c, "er8": er8, "disp8": d8, "s1h": s1h}
        new["since"] = self.ctx["since"] if new["ctx"] == prev else t
        self.ctx = new
        self._pivots("1h", t)

    def _derive_15m(self, t: datetime) -> None:
        bars = list(self.m15)
        p = self.p
        self.s15 = scale(bars, p.median_tr) if len(bars) >= p.median_tr + 1 else None
        self.s15_hist.append((_iso(t), _s(self.s15)))
        prev = self.phase["phase"]
        out: dict[str, Any] = {"phase": "UNAVAILABLE", "dir": None, "cr": None, "er6": None, "disp6": None, "net3": None}
        need = p.ph_short + p.ph_prev + 1
        if self.s15 is not None and len(bars) >= max(need, p.ready_15m):
            tr = trs(bars[-need:])
            den = median(tr[:p.ph_prev])
            cr = div(median(tr[-p.ph_short:]), den) if den > 0 else None
            closes = [b.c for b in bars[-(p.ph_exp_transitions + 1):]]
            er6 = efficiency(closes)
            d6 = displacement(closes, self.s15)
            net3 = bars[-1].c - bars[-1 - p.ph_reaction_transitions].c
            out.update(cr=cr, er6=er6, disp6=d6, net3=net3)
            ctx = self.context(t)
            if cr is None:
                out["phase"] = "UNAVAILABLE"
            elif er6 >= p.ph_exp_er_min and abs(d6) >= p.ph_exp_disp:
                out["phase"], out["dir"] = "EXPANSION", ("UP" if d6 > 0 else "DOWN")
            elif cr <= p.ph_cr_max and er6 <= p.ph_comp_er_max:
                out["phase"] = "COMPRESSION"
            elif ctx == "UNAVAILABLE":
                out["phase"] = "UNAVAILABLE"
            elif (ctx == "UP" and net3 < 0) or (ctx == "DOWN" and net3 > 0):
                out["phase"] = "REACTION"
            elif self.ctx["er8"] is not None and self.ctx["er8"] <= p.ph_rot_er8_max and er6 <= p.ph_comp_er_max:
                out["phase"] = "ROTATION"
            else:
                out["phase"] = "TRANSITION"
        out["prev"] = prev if out["phase"] != prev else self.phase.get("prev")
        out["since"] = self.phase.get("since") if out["phase"] == prev else t
        self.phase = out
        # participation (descriptive only)
        vols = [b.vol for b in bars[-(p.vol_bars + 1):] if b.vol is not None]
        if len(vols) == p.vol_bars + 1:
            base = median(vols[:-1])
            self.part = div(vols[-1], base) if base > 0 else None
        else:
            self.part = None
        self._pivots("15m", t)
        self._create_pending_pivots(t)

    # -- freshness / dependencies -------------------------------------------------------------------------------

    def _fresh(self, bar: Bar | None, allowance: timedelta, t: datetime) -> bool:
        return bar is not None and t - bar.end <= allowance and t - bar.known_at <= allowance

    def ready_15m(self, t: datetime) -> bool:
        return len(self.m15) >= self.p.ready_15m and self.s15 is not None and self._fresh(self.m15[-1], self.p.fresh_15m, t)

    def ready_1h(self, t: datetime) -> bool:
        return len(self.h1) >= self.p.ready_1h and self._fresh(self.h1[-1], self.p.fresh_1h, t)

    def ready_1m(self, t: datetime) -> bool:
        return self._fresh(self.last_1m, self.p.fresh_1m, t)

    def context(self, t: datetime) -> str:
        return self.ctx["ctx"] if self.ready_1h(t) else "UNAVAILABLE"

    def phase_now(self, t: datetime) -> str:
        return self.phase["phase"] if self.ready_15m(t) else "UNAVAILABLE"

    def _dep(self, name: str, win, need: int, allowance: timedelta, t: datetime) -> sc.DependencyRef:
        last = win[-1] if win else None
        if last is None:
            status = "WARMING_UP"
        elif not self._fresh(last, allowance, t):
            status = "STALE"
        elif len(win) < need:
            status = "WARMING_UP"
        else:
            status = "READY"
        return sc.DependencyRef(name=name, status=status, latest_ref=last.rid if last else None,
                                event_end=last.end if last else None, known_at=last.known_at if last else None)

    def _dependencies(self, t: datetime) -> tuple[sc.DependencyRef, ...]:
        p = self.p
        deps = [self._dep("trade.15m", self.m15, p.ready_15m, p.fresh_15m, t),
                self._dep("trade.1h", self.h1, p.ready_1h, p.fresh_1h, t),
                self._dep("trade.1m", [self.last_1m] if self.last_1m else [], 1, p.fresh_1m, t)]
        if self.cfg.profile.execution == Execution.LIVE_QUOTED:
            q = self.quote
            st = self._quote_state(t)
            deps.append(sc.DependencyRef(name="quotes", status=st, latest_ref=q.raw_sha256[:16] if q else None,
                                         event_end=q.source_ts if q else None, known_at=q.received_at if q else None))
        return tuple(deps)

    def _quote_state(self, t: datetime) -> str:
        if self.cfg.profile.execution != Execution.LIVE_QUOTED:
            return "NOT_COVERED"
        q = self.quote
        if q is None:
            return "UNAVAILABLE"
        if t - q.source_ts > self.p.fresh_quote or t - q.received_at > self.p.fresh_quote:
            return "STALE"
        if q.source_ts > t + timedelta(seconds=1):
            return "CLOCK_UNCERTAIN"
        return "READY"

    # ----------------------------------------------------------------------------------------------------------
    # landmarks
    # ----------------------------------------------------------------------------------------------------------

    def _zone(self) -> Decimal | None:
        if self.s15 is None:
            return None
        return zone_halfwidth(self.s15, self.tick, self.p.zone_frac, self.p.zone_min_ticks)

    def _pivots(self, h: str, t: datetime) -> None:
        win = list(self.m15 if h == "15m" else self.h1)
        L, R = self.p.pivot_left, self.p.pivot_right
        if len(win) < L + R + 1:
            return
        seg = win[-(L + R + 1):]
        k = seg[L]
        others = seg[:L] + seg[L + 1:]
        for side in ("HIGH", "LOW"):
            if side == "HIGH" and all(k.h > o.h for o in others):
                price = k.h
            elif side == "LOW" and all(k.lo < o.lo for o in others):
                price = k.lo
            else:
                continue
            self.pending_pivots.append({"horizon": h, "side": side, "price": str(price), "bar": k.rid,
                                        "extremum_time": _iso(k.start), "confirmed_by": seg[-1].rid,
                                        "confirmed_at": _iso(t)})
        self.pending_pivots = self.pending_pivots[-(2 * self.p.max_pivots):]

    def _create_pending_pivots(self, t: datetime) -> None:
        z = self._zone()
        if z is None or not self.pending_pivots:
            return
        for pp in self.pending_pivots:
            h = pp["horizon"]
            age = self.p.pivot_age_15m if h == "15m" else self.p.pivot_age_1h
            lid = f"lm-pv{h}-{pp['side'][0]}-{pp['extremum_time']}-{_h(self.cfg.method.rules_sha256, pp['bar'], pp['side'])}"
            if lid in self.landmarks:
                continue
            lm = Landmark(lid, f"PIVOT_{pp['side']}_{h.upper()}", pp["side"], Decimal(pp["price"]), z, self.s15, h,
                          [pp["bar"], pp["confirmed_by"]], _dt(pp["extremum_time"]), t, self.seq, t + age)
            self._add_landmark(lm, t)
            self.counters["landmarks_created"] += 1
        self.pending_pivots = []
        for h in ("15m", "1h"):
            piv = sorted((lm for lm in self.landmarks.values() if lm.horizon == h and lm.ltype.startswith("PIVOT")
                          and lm.status == "ACTIVE"), key=lambda lm: (lm.created_at, lm.lid))
            refs = self._active_refs()
            while len(piv) > self.p.max_pivots:
                victim = next((x for x in piv if x.lid not in refs), None)
                if victim is None:
                    break
                piv.remove(victim)
                self._retire_landmark(victim, "CAPACITY_OLDEST_FIRST", t)

    def _period_landmark(self, h: str, bar: Bar, t: datetime) -> None:
        z = self._zone()
        for lm in list(self.landmarks.values()):
            if lm.ltype.startswith(f"PREV_{h.upper()}_") and lm.status == "ACTIVE":
                self._retire_landmark(lm, "NEXT_PERIOD_COMPLETED", t)
        self.pending_periods = [x for x in self.pending_periods if x["horizon"] != h]
        if z is None:
            self.pending_periods.append({"horizon": h, "bar": bar.rid, "high": str(bar.h), "low": str(bar.lo),
                                         "end": _iso(bar.end)})
            return
        self._make_period(h, bar.rid, bar.h, bar.lo, bar.end, z, t)

    def _make_period(self, h: str, rid: str, hi: Decimal, lo: Decimal, end: datetime, z: Decimal, t: datetime) -> None:
        retire = end + self.p.period_age[h]
        for side, price in (("HIGH", hi), ("LOW", lo)):
            lid = f"lm-prev{h}-{side[0]}-{_iso(end)}-{_h(rid, side)}"
            lm = Landmark(lid, f"PREV_{h.upper()}_{side}", side, price, z, self.s15, h, [rid], None, t, self.seq,
                          retire)
            self._add_landmark(lm, t)
            self.counters["landmarks_created"] += 1

    def _add_landmark(self, lm: Landmark, t: datetime) -> None:
        self.landmarks[lm.lid] = lm
        self._emit_landmark(lm, t)
        self._touch()

    def _retire_landmark(self, lm: Landmark, reason: str, t: datetime) -> None:
        if lm.status == "RETIRED":
            return
        lm.status, lm.status_reason = "RETIRED", reason
        self._emit_landmark(lm, t)
        self.landmarks.pop(lm.lid, None)
        self._touch()

    def _active_refs(self) -> set[str]:
        c = self.call
        if c is None or c.limiting is None:
            return set()
        return {c.limiting.get("landmark_id") or ""}

    def _landmark_timers(self, t: datetime) -> None:
        refs = self._active_refs()
        for lm in sorted(list(self.landmarks.values()), key=lambda x: x.lid):
            if lm.retire_at is not None and lm.retire_at <= t and lm.lid not in refs:
                self._retire_landmark(lm, "AGE", t)
        # periods whose S15 was unavailable at completion: created at the first usable S15 (known_at = now)
        z = self._zone()
        if z is not None and self.pending_periods:
            for pp in self.pending_periods:
                end = _dt(pp["end"])
                if t - end <= self.p.period_age[pp["horizon"]]:
                    self._make_period(pp["horizon"], pp["bar"], Decimal(pp["high"]), Decimal(pp["low"]), end, z, t)
            self.pending_periods = []

    def _mark_broken(self, b: Bar, t: datetime) -> None:
        bx = self.box
        if bx is not None and bx.created_at < t:
            if b.c > bx.up + bx.z:
                bx.broken["U"] = True
            if b.c < bx.low - bx.z:
                bx.broken["L"] = True
        for lm in sorted(self.landmarks.values(), key=lambda x: x.lid):
            if lm.status != "ACTIVE":
                continue
            if (lm.side == "HIGH" and b.c > lm.price + lm.z) or (lm.side == "LOW" and b.c < lm.price - lm.z):
                lm.status, lm.status_reason = "BROKEN", f"15M_CLOSE_BEYOND_FAR_EDGE:{b.rid}"
                self._emit_landmark(lm, t)

    def _opposing(self, d: int, t: datetime, owner_zones: list[tuple[str, Decimal, Decimal, dict]]) -> list[tuple]:
        """Eligible opposing zones for direction d in transformed coordinates: (near', far', info, created, id)."""
        out = []
        for lm in self.landmarks.values():
            if lm.status != "ACTIVE" or not lm.opposes(d):
                continue
            p = lm.p_t(d)
            out.append((p - lm.z, p + lm.z, lm.info(t), lm.created_at, lm.lid))
        for zid, p_t, z, info in owner_zones:
            out.append((p_t - z, p_t + z, info, _dt(info["created_at"]), zid))
        return out

    def _owner_zones(self, d: int, t: datetime) -> list[tuple[str, Decimal, Decimal, dict]]:
        zones = []
        for a in self.attempts.values():
            if a.family == "A" and a.d == d and a.b_t is not None and not a.b_broken:
                zones.append((f"{a.aid}#B", a.b_t, a.z, {"landmark_id": f"{a.aid}#B", "type": "IMPULSE_B",
                                                          "price": str(a.b_t * d), "zone_halfwidth": str(a.z),
                                                          "source": ",".join(a.sources),
                                                          "created_at": _iso(a.born_at),
                                                          "age_minutes": str(int((t - a.born_at) / MINUTE))}))
        bx = self.box
        if bx is not None and not bx.broken["U" if d > 0 else "L"]:
            _, u_t, _ = bx.edges_t(d)
            zones.append((f"{bx.bid}#{'U' if d > 0 else 'L'}", u_t, bx.z,
                          {"landmark_id": f"{bx.bid}#{'U' if d > 0 else 'L'}", "type": "BOX_UPPER" if d > 0 else "BOX_LOWER",
                           "price": str(u_t * d), "zone_halfwidth": str(bx.z), "source": ",".join(bx.sources),
                           "created_at": _iso(bx.created_at), "age_minutes": str(int((t - bx.created_at) / MINUTE))}))
        return zones

    # ----------------------------------------------------------------------------------------------------------
    # 15m close processing
    # ----------------------------------------------------------------------------------------------------------

    def _qa(self, d: int, t: datetime) -> bool | None:
        """Q_A for direction d at the latest 15m close; None when not assessable."""
        p = self.p
        bars = list(self.m15)
        if not self.ready_15m(t) or len(bars) < p.a_source_bars:
            return None
        ctx = self.context(t)
        if ctx == "UNAVAILABLE":
            return None
        closes_t = [tbar(x, d)[3] for x in bars[-p.a_source_bars:]]
        er = efficiency(closes_t)
        disp = displacement(closes_t, self.s15)
        return ctx_t(ctx, d) == "UP" and er >= p.a_er_min and disp >= p.a_disp

    def _a_births(self, b: Bar, t: datetime) -> None:
        if self.window == "TAIL":
            return
        for d in (1, -1):
            key = str(d)
            qa = self._qa(d, t)
            self.qa_last[key] = qa
            if qa is None:
                continue
            pending = any(a.family == "A" and a.d == d for a in self.attempts.values())
            st = self.latch[key]
            if qa is False:
                if not pending and st == "NEED_FALSE":
                    self.latch[key] = "READY"
                elif st == "INIT":
                    self.latch[key] = "READY"  # first assessable observation false: next true is a transition
                continue
            # qa True
            if pending:
                self.counters["a_true_while_pending"] += 1
                continue
            if st in ("INIT", "READY"):
                self._new_a(d, b, t, renewal=("FIRST_ASSESSABLE_TRUE" if st == "INIT" else "FALSE_TO_TRUE"))
                self.latch[key] = "NEED_FALSE"

    def _new_a(self, d: int, b: Bar, t: datetime, renewal: str) -> None:
        p = self.p
        src = list(self.m15)[-p.a_source_bars:]
        z = self._zone()
        lows = [tbar(x, d)[2] for x in src]
        highs = [tbar(x, d)[1] for x in src]
        aid = f"A{dname(d)[0]}-{_iso(b.start)}-{_h(self.cfg.method.rules_sha256, self.cfg.instrument, 'A', d, b.rid)}"
        a = Attempt(aid=aid, family="A", d=d, owner=None, born_at=t, born_seq=self.seq, sources=[x.rid for x in src],
                    deadline=t + p.a_lifetime, s15=self.s15, z=z, a_t=min(lows), b_t=max(highs),
                    prev_close_t=tbar(b, d)[3], renewal=renewal)
        self.attempts[aid] = a
        self.counters["episodes"]["A"][dname(d)] += 1
        self._candidate(a, "BIRTH", renewal, t)
        self._touch()

    def _a_close(self, b: Bar, t: datetime) -> None:
        """A episode reaction tracking, spend/withdraw/revise/arm on a complete 15m close."""
        p = self.p
        for a in sorted([x for x in self.attempts.values() if x.family == "A"], key=lambda x: x.aid):
            if a.born_at >= t:
                continue  # born at this barrier: its first post-birth bar is the next one
            o_t, h_t, l_t, c_t = tbar(b, a.d)
            a.bars_seen += 1
            if a.prev_close_t is not None and c_t < a.prev_close_t:
                a.lower_close = True
            a.prev_close_t = c_t
            if c_t > a.b_t + a.z:
                a.b_broken = True  # the impulse destination zone is BROKEN by a close beyond its far edge
            if a.status == "WATCH" and h_t > a.b_t + a.z:
                self._end_attempt(a, "EXPIRED", "SPENT_HIGH_BEYOND_B_BEFORE_REACTION", t)
                continue
            if c_t <= a.a_t + a.z:
                self._end_attempt(a, "WITHDRAWN", "CLOSE_AT_OR_BEYOND_A_PLUS_ZONE", t)
                continue
            if a.status == "WATCH":
                # R = lowest reaction low since birth; the most recent bar attaining it is the anchor
                if a.r_t is None or l_t <= a.r_t:
                    a.r_t, a.anchor, a.anchor_h_t = l_t, b.rid, h_t
                reaction = (a.lower_close and a.r_t < a.b_t - p.a_reaction_min * a.s15 and a.r_t > a.a_t + a.z)
                if reaction:
                    if self._a_context_ok(a, t):
                        a.k_t, a.v_t = a.anchor_h_t, a.r_t - a.z
                        a.status, a.arm_at, a.arm_seq = "ARMED", t, self.seq
                        self.counters["armed"]["A"] += 1
                        self._candidate(a, "ARM", None, t)
                    # a forbidden context / adverse expansion is handled by the withdrawal pass of this dispatch
                elif a.bars_seen >= p.a_reaction_max_bars:
                    self._end_attempt(a, "EXPIRED", "NO_QUALIFYING_REACTION_WITHIN_8_BARS", t)
            elif l_t <= a.r_t and l_t > a.a_t + a.z:
                # a lower (or equal: most recent anchor) clean reaction low revises K/V before trigger; the original
                # episode deadline is never extended
                a.r_t, a.anchor, a.anchor_h_t = l_t, b.rid, h_t
                a.k_t, a.v_t = h_t, l_t - a.z
                a.arm_at, a.arm_seq = t, self.seq
                self._candidate(a, "REVISE", "LOWER_CLEAN_REACTION_REANCHOR", t)

    def _a_context_ok(self, a: Attempt, t: datetime) -> bool:
        ph = self.phase_now(t)
        opp = ph == "EXPANSION" and self.phase["dir"] == ("DOWN" if a.d > 0 else "UP")
        return ctx_t(self.context(t), a.d) == "UP" and not opp

    # -- box ----------------------------------------------------------------------------------------------------

    def _box_close_flags(self, b: Bar, t: datetime) -> None:
        """Timer/gap retirement happened earlier; derive B cancellations and opposite-edge retirement from the
        PRE-dispatch attempt state, then apply them atomically."""
        bx = self.box
        if bx is None:
            return
        cancels: list[Attempt] = []
        retire = None
        for a in sorted(self.attempts.values(), key=lambda x: x.aid):
            if a.family != "B" or a.owner != bx.bid:
                continue
            l_t, u_t, _ = bx.edges_t(a.d)
            c_t = tbar(b, a.d)[3]
            if c_t < u_t - bx.z:
                cancels.append(a)
            if c_t < l_t - bx.z:
                retire = f"OPPOSITE_FAR_EDGE_CLOSE_DURING_B_{dname(a.d)}:{b.rid}"
        for a in cancels:
            self._end_attempt(a, "WITHDRAWN", "RETURNED_INSIDE_BEFORE_RETEST", t)
        if retire is not None:
            self._retire_box(retire, t)

    def _box_birth(self, b: Bar, t: datetime) -> None:
        p = self.p
        ph = self.phase_now(t)
        if ph == "UNAVAILABLE":
            return
        comp = ph == "COMPRESSION"
        prev = self.comp_prev
        self.comp_prev = comp
        tok = self.box_token
        if self.box is not None:
            return  # no replacement while an owner is live; transitions never queue
        if tok == "INIT":
            if comp:
                tok = "TOKEN"
            else:
                tok = "READY"
        elif tok == "NEED_FALSE":
            if not comp:
                tok = "READY"
        elif tok == "READY":
            if comp and prev is False:
                tok = "TOKEN"
            elif comp and prev is None:
                tok = "TOKEN"
        elif tok == "TOKEN" and not comp:
            tok = "READY"  # unused birth token expires when compression ends
            self.counters["box_tokens_discarded"] += 1
        self.box_token = tok
        if tok != "TOKEN" or self.window == "TAIL":
            return
        bars = list(self.m15)
        need = p.box_prior + 2
        if len(bars) < need or self.s15 is None:
            return
        prior = bars[-(p.box_prior + 1):-1]
        closes = [bars[-(p.box_prior + 2)].c] + [x.c for x in prior]
        er16 = efficiency(closes)
        low, up = min(x.lo for x in prior), max(x.h for x in prior)
        width = up - low
        z = self._zone()
        upper_touch = sum(1 for x in prior if x.h >= up - z)
        lower_touch = sum(1 for x in prior if x.lo <= low + z)
        ok = (er16 <= p.box_er_max and p.box_width[0] * self.s15 <= width <= p.box_width[1] * self.s15
              and upper_touch >= p.box_touch and lower_touch >= p.box_touch and low <= b.c <= up)
        if not ok:
            self.counters["box_geometry_not_qualified"] += 1
            return
        mid = (low + up) / 2
        bid = f"box-{_iso(b.start)}-{_h(self.cfg.method.rules_sha256, self.cfg.instrument, b.rid)}"
        self.box = Box(bid, low, up, mid, self.s15, z, t, self.seq, t + p.box_lifetime, [x.rid for x in prior] + [b.rid])
        self.box_token = "NEED_FALSE"
        self.counters["boxes"] += 1
        self._emit("observation", t, {
            "lens": "structure", "name": "compression_box", "category": "BOX_BORN",
            "values": {"box_id": bid, "low": str(low), "up": str(up), "mid": str(mid), "s15": str(self.s15),
                       "zone_halfwidth": str(z), "er16": str(er16), "upper_touches": str(upper_touch),
                       "lower_touches": str(lower_touch), "expires_at": _iso(self.box.expires_at)},
            "decision_role": "OWNER_OF_B_AND_C_ATTEMPTS",
            "meaning": "A compression-qualified range: breaks with retest (B) or failed exits (C) may follow."},
            lineage=(bid,))
        self._touch()

    def _retire_box(self, reason: str, t: datetime) -> None:
        bx = self.box
        if bx is None:
            return
        for a in sorted(self.attempts.values(), key=lambda x: x.aid):
            if a.owner == bx.bid:
                self._end_attempt(a, "WITHDRAWN" if "EXPIR" not in reason else "EXPIRED", f"BOX_RETIRED:{reason}", t)
        self._emit("observation", t, {
            "lens": "structure", "name": "compression_box", "category": "BOX_RETIRED",
            "values": {"box_id": bx.bid, "reason": reason, "low": str(bx.low), "up": str(bx.up)},
            "decision_role": "OWNER_OF_B_AND_C_ATTEMPTS", "meaning": "The compression range no longer owns attempts."},
            lineage=(bx.bid,))
        self.box = None
        self.box_token = "NEED_FALSE"
        self._touch()

    def _bc_geometry(self, b: Bar, t: datetime) -> None:
        bx = self.box
        if bx is None or self.window == "TAIL":
            return
        both = b.lo < bx.low - bx.z and b.h > bx.up + bx.z
        for d in (1, -1):
            l_t, u_t, m_t = bx.edges_t(d)
            o_t, h_t, lo_t, c_t = tbar(b, d)
            key = "+" if d > 0 else "-"
            # B: first complete close beyond the far upper edge
            if c_t > u_t + bx.z and not bx.used["B" + key]:
                bx.used["B" + key] = True
                a = self._new_bc("B", d, bx, b, t, t + self.p.b_lifetime)
                ctx = ctx_t(self.context(t), d)
                if ctx in ("DOWN", "UNAVAILABLE"):
                    self._end_attempt(a, "WITHDRAWN", f"CONTEXT_FORBIDDEN_AT_BIRTH:{ctx}", t)
            # C: reclaim geometry of a failed exit through the lower edge
            if lo_t < l_t - bx.z and c_t > l_t + bx.z and c_t < m_t and not bx.used["C" + key]:
                if both:
                    self.counters["c_both_edge_ambiguous"] += 1
                    continue
                if h_t > u_t + bx.z:
                    continue
                bx.used["C" + key] = True
                a = self._new_bc("C", d, bx, b, t, t + self.p.c_lifetime)
                ctx = self.context(t)
                ph = self.phase_now(t)
                if ctx != "BALANCED":
                    self._end_attempt(a, "WITHDRAWN", f"CONTEXT_NOT_BALANCED_AT_BIRTH:{ctx}", t)
                elif ph == "EXPANSION":
                    self._end_attempt(a, "WITHDRAWN", f"DIRECTIONAL_EXPANSION_AT_BIRTH:{self.phase['dir']}", t)
                else:
                    a.k_t, a.v_t = c_t, lo_t - bx.z
                    a.status, a.arm_at, a.arm_seq = "ARMED", t, self.seq
                    self.counters["armed"]["C"] += 1
                    self._candidate(a, "ARM", None, t)
        # B retests for existing WATCH attempts (bars after the break bar)
        for a in sorted(self.attempts.values(), key=lambda x: x.aid):
            if a.family != "B" or a.status != "WATCH" or a.owner != bx.bid or a.born_at >= t:
                continue
            l_t, u_t, _ = bx.edges_t(a.d)
            o_t, h_t, lo_t, c_t = tbar(b, a.d)
            a.retest_seen += 1
            if u_t - bx.z <= lo_t <= u_t + bx.z and c_t > u_t and lo_t > l_t:
                if self._b_context_ok(a, t):
                    a.k_t, a.v_t = max(u_t + self.tick, c_t), lo_t - bx.z
                    a.status, a.arm_at, a.arm_seq = "ARMED", t, self.seq
                    self.counters["armed"]["B"] += 1
                    self._candidate(a, "ARM", None, t)
            elif a.retest_seen >= self.p.b_retest_bars:
                self._end_attempt(a, "EXPIRED", "NO_RETEST_WITHIN_4_BARS", t)

    def _new_bc(self, fam: str, d: int, bx: Box, b: Bar, t: datetime, life_end: datetime) -> Attempt:
        aid = (f"{fam}{dname(d)[0]}-{_iso(b.start)}-"
               f"{_h(self.cfg.method.rules_sha256, self.cfg.instrument, fam, d, bx.bid, b.rid)}")
        a = Attempt(aid=aid, family=fam, d=d, owner=bx.bid, born_at=t, born_seq=self.seq, sources=[b.rid],
                    deadline=min(bx.expires_at, life_end), s15=bx.s15, z=bx.z)
        self.attempts[aid] = a
        self.counters["episodes"][fam][dname(d)] += 1
        self._candidate(a, "BIRTH", None, t)
        self._touch()
        return a

    def _b_context_ok(self, a: Attempt, t: datetime) -> bool:
        ph = self.phase_now(t)
        opp = ph == "EXPANSION" and self.phase["dir"] == ("DOWN" if a.d > 0 else "UP")
        return ctx_t(self.context(t), a.d) not in ("DOWN", "UNAVAILABLE") and not opp

    def _c_context_ok(self, a: Attempt, t: datetime) -> bool:
        ph = self.phase_now(t)
        adverse = ph == "EXPANSION" and self.phase["dir"] == ("DOWN" if a.d > 0 else "UP")
        return self.context(t) == "BALANCED" and not adverse

    def _context_ok(self, a: Attempt, t: datetime) -> bool:
        return {"A": self._a_context_ok, "B": self._b_context_ok, "C": self._c_context_ok}[a.family](a, t)

    def _context_withdrawals(self, t: datetime, closes15: list[Bar]) -> None:
        """At every dispatch a forbidden context / adverse expansion withdraws an unissued attempt (before any
        coincident trigger). C additionally withdraws on a 15m close below L-z: every close NEWLY admitted at this
        dispatch is examined exactly once, whatever its market end versus the dispatch (receipt) time."""
        for a in sorted(list(self.attempts.values()), key=lambda x: x.aid):
            if not self._context_ok(a, t):
                self._end_attempt(a, "WITHDRAWN", f"CONTEXT_OR_ADVERSE_EXPANSION:{self.context(t)}/"
                                                  f"{self.phase_now(t)}:{self.phase['dir']}", t)
        # C: a 15m close beyond L-z before trigger withdraws
        bx = self.box
        if bx is None:
            return
        for b in closes15:  # attempts present here were all born at an earlier dispatch (births follow this step)
            for a in sorted(list(self.attempts.values()), key=lambda x: x.aid):
                if a.family == "C" and a.owner == bx.bid:
                    l_t, _, _ = bx.edges_t(a.d)
                    if tbar(b, a.d)[3] < l_t - bx.z:
                        self._end_attempt(a, "WITHDRAWN", "CLOSE_BEYOND_LOWER_FAR_EDGE_BEFORE_TRIGGER", t)

    def _attempt_expiry(self, t: datetime) -> None:
        if self.box is not None and self.box.expires_at <= t:
            self._retire_box("BOX_EXPIRY", t)
        for a in sorted(list(self.attempts.values()), key=lambda x: x.aid):
            if a.deadline <= t:
                self._end_attempt(a, "EXPIRED", "ATTEMPT_DEADLINE", t)

    def _end_attempt(self, a: Attempt, status: str, reason: str, t: datetime) -> None:
        if a.aid not in self.attempts:
            return
        del self.attempts[a.aid]
        self.counters["attempt_end"][f"{a.family}:{status}:{reason.split(':')[0]}"] = \
            self.counters["attempt_end"].get(f"{a.family}:{status}:{reason.split(':')[0]}", 0) + 1
        self._candidate(a, {"EXPIRED": "EXPIRE", "WITHDRAWN": "WITHDRAW", "REJECTED": "REJECT",
                            "ISSUED": "ISSUE", "CLEARED": "CLEARED"}[status], reason, t, terminal=True,
                        status=status)
        self._touch()

    # ----------------------------------------------------------------------------------------------------------
    # triggers / selection / issue
    # ----------------------------------------------------------------------------------------------------------

    def _triggers(self, minutes: list[Bar], t: datetime) -> list[tuple[Attempt, Bar]]:
        out: list[tuple[Attempt, Bar]] = []
        if not minutes:
            return out
        for a in sorted([x for x in self.attempts.values() if x.status == "ARMED"], key=lambda x: x.aid):
            for m in minutes:
                if m.start < a.arm_at:
                    if m.end > a.arm_at:  # straddling-arm bar: cannot trigger; contact with V withdraws
                        if tbar(m, a.d)[2] <= a.v_t:
                            self._end_attempt(a, "WITHDRAWN", "ARM_CONTACT_TIME_AMBIGUOUS", t)
                            break
                    continue
                if not self.ready_1m(t):
                    continue
                _, h_t, l_t, c_t = tbar(m, a.d)
                if c_t >= a.k_t + self.tick * self.p.trigger_ticks:
                    if l_t <= a.v_t:
                        if a.family == "A":
                            self._end_attempt(a, "REJECTED", "TRIGGER_CONTACT_AMBIGUOUS", t)
                            self.counters["rejections"]["TRIGGER_CONTACT_AMBIGUOUS"] += 1
                            break
                        continue  # B/C: the trigger predicate requires low > V; not a trigger minute
                    out.append((a, m))
                    self.counters["triggered"][a.family] += 1
                    break
        return out

    def _resolve_target(self, a: Attempt, tc: Decimal, t: datetime) -> tuple[Decimal | None, str, dict | None, str | None]:
        """Transformed target T', its type, limiting landmark info and a blocking reason (if any)."""
        d = a.d
        tc_t = tc * d
        zones = self._opposing(d, t, self._owner_zones(d, t))
        for near, far, info, created, zid in zones:
            if near <= tc_t <= far:
                return None, "BLOCKED", info, "AT_OPPOSING_AREA"
        ahead = sorted((z for z in zones if z[0] > tc_t), key=lambda z: (z[0], z[3], z[4]))
        best = ahead[0] if ahead else None
        if a.family == "A":
            if best is None:
                return None, "NONE", None, "NO_TARGET"
            return best[0], "LANDMARK", best[2], None
        bx = self.box
        if a.family == "B":
            l_t, u_t, _ = bx.edges_t(d)
            proj = u_t + (u_t - l_t)
            if best is not None and best[0] <= proj:
                return best[0], "LANDMARK", best[2], None
            return proj, "PROJECTED_BOX_WIDTH", None, None
        _, _, m_t = bx.edges_t(d)
        if best is not None and best[0] < m_t:
            return best[0], "LANDMARK", best[2], None
        return m_t, "MIDPOINT", None, None

    def _side_price(self, d: int, t: datetime) -> tuple[Decimal | None, str | None, Decimal | None, list[str]]:
        """(price, source, cost envelope K bps, blockers) under the execution profile."""
        p = self.p
        if self.cfg.profile.execution == Execution.HISTORICAL_BASE:
            if self.last_1m is None:
                return None, None, p.hist_k_bps, ["TRADE_1M_UNAVAILABLE"]
            return self.last_1m.c, "MODELED_LATEST_COMPLETE_TRADE_MINUTE_CLOSE", p.hist_k_bps, []
        st = self._quote_state(t)
        q = self.quote
        if st != "READY":
            return None, None, None, [{"UNAVAILABLE": "QUOTE_UNAVAILABLE", "STALE": "QUOTE_STALE",
                                       "CLOCK_UNCERTAIN": "QUOTE_CLOCK_UNCERTAIN"}.get(st, "QUOTE_UNAVAILABLE")]
        mid = (q.bid + q.ask) / 2
        half = div(10000 * (q.ask - q.bid), 2 * mid)
        k = 2 * p.live_fee_bps + 2 * p.live_slip_bps + half
        return (q.ask if d > 0 else q.bid), ("MEASURED_ASK" if d > 0 else "MEASURED_BID"), k, []

    def connection_blockers(self) -> list[str]:
        r = CONNECTION_STATES[self.connection["state"]] if self.connection is not None else None
        return [r] if r else []

    def _common_blockers(self, t: datetime) -> list[str]:
        out = []
        if not self.ready_15m(t):
            out.append("TRADE_15M_NOT_READY")
        if not self.ready_1h(t):
            out.append("TRADE_1H_NOT_READY")
        if not self.ready_1m(t):
            out.append("TRADE_1M_STALE")
        out += self._event_blockers(t)
        out += self.dislocation_blocks()
        return out

    def _select_and_issue(self, triggered: list[tuple[Attempt, Bar]], last: Bar, t: datetime) -> None:
        p = self.p
        evaluated = []
        for a, m in triggered:
            tc = m.c
            blockers: list[str] = []
            if self.window in ("TAIL",) or (self.cfg.eval_end is not None and t >= self.cfg.eval_end):
                blockers.append("EVALUATION_WINDOW_ENDED")
            if a.pre_live and self.origin == sc.Origin.LIVE.value:
                blockers.append("ARMED_BEFORE_LIVE_ACTIVATION")
            if self.origin == sc.Origin.RECONSTRUCTED.value:
                blockers.append("RECONSTRUCTED_CATCH_UP_NO_NEW_CALL")
            blockers += self.connection_blockers()
            t_t, ttype, limiting, tb = self._resolve_target(a, tc, t)
            s15 = self.s15
            geom = None
            if tb:
                blockers.append(tb)
            elif s15 is None:
                blockers.append("SCALE_UNAVAILABLE")
            else:
                d = a.d
                v_real = round_down(a.v_t, self.tick) * d if d > 0 else -round_down(a.v_t, self.tick)
                t_real = round_down(t_t, self.tick) * d if d > 0 else -round_down(t_t, self.tick)
                area = geo.structural_area(d, tc, v_real, t_real, s15, p.area_scale, self.tick)
                if area is None:
                    blockers.append("EMPTY_STRUCTURAL_AREA")
                geom = {"v": v_real, "t": t_real, "area": area, "type": ttype, "limiting": limiting}
            blockers += self._common_blockers(t)
            price, source, k, qb = self._side_price(a.d, t)
            blockers += qb
            chk = None
            if geom is not None and geom["area"] is not None and price is not None:
                if not geo.in_area(price, geom["area"]):
                    blockers.append("PRICE_OUTSIDE_STRUCTURAL_AREA")
                chk = geo.predicate(a.d, price, geom["v"], geom["t"], k, p.rr_min)
                if not chk.ok:
                    blockers.append(chk.reason)
            evaluated.append({"a": a, "m": m, "geom": geom, "blockers": blockers, "price": price, "source": source,
                              "k": k, "chk": chk})
            self._record_gate_stats(a, chk, k, geom, t)
        actionable = [e for e in evaluated if not e["blockers"]]
        dirs = {e["a"].d for e in actionable}
        slot = self.call is not None and self.call.thesis == "ONGOING"
        winner = None
        if actionable and not slot and len(dirs) == 1:
            winner = sorted(actionable, key=lambda e: (FAM_RANK[e["a"].family], e["a"].born_at, e["a"].aid))[0]
        for e in evaluated:
            a = e["a"]
            if e is winner:
                continue
            extra = []
            if not e["blockers"]:
                if slot:
                    extra.append("SLOT_OCCUPIED")
                elif len(dirs) > 1:
                    extra.append("CONFLICTED")
                else:
                    extra.append("PRIORITY")
            reasons = e["blockers"] + extra
            self._actionability(a.aid, False, reasons, e, t)
            for r in reasons:
                self.counters["rejections"][r.split(":")[0]] = self.counters["rejections"].get(r.split(":")[0], 0) + 1
            if "SLOT_OCCUPIED" in extra:
                self.counters["suppressed_by_slot"].append({"attempt": a.aid, "at": _iso(t),
                                                            "call": self.call.cid if self.call else None})
                self.counters["suppressed_by_slot"] = self.counters["suppressed_by_slot"][-50:]
            self._end_attempt(a, "REJECTED", ",".join(reasons), t)
        if winner is not None:
            self._issue(winner, t)

    def _record_gate_stats(self, a: Attempt, chk, k, geom, t) -> None:
        if chk is None or chk.g is None:
            return
        fam = a.family
        st = self.counters["gates"].setdefault(fam, [])
        st.append({"at": _iso(t), "attempt": a.aid, "G": str(chk.g), "Q": str(chk.q), "K": str(k),
                   "margin": str(chk.margin), "ok": chk.ok,
                   "limiting_type": (geom or {}).get("limiting", {}).get("type") if geom and geom.get("limiting") else
                   (geom or {}).get("type"),
                   "limiting_age_minutes": ((geom or {}).get("limiting") or {}).get("age_minutes")})
        if len(st) > 400:
            del st[: len(st) - 400]

    def _issue(self, e: dict, t: datetime) -> None:
        a, m, g = e["a"], e["m"], e["geom"]
        p = self.p
        hard = p.hard(a.family)
        cid = f"call-{a.family}{dname(a.d)[0]}-{_iso(t)}-{_h(a.aid, _iso(t))}"
        premise = {"A": ("15M_CLOSE_BEYOND_IMPULSE_A", a.a_t * a.d if a.a_t is not None else None),
                   "B": ("15M_CLOSE_BEYOND_U_MINUS_Z", None), "C": ("15M_CLOSE_BEYOND_L_MINUS_Z", None)}[a.family]
        level = premise[1]
        if a.family in ("B", "C"):
            bx = self.box
            l_t, u_t, _ = bx.edges_t(a.d)
            lvl_t = (u_t - bx.z) if a.family == "B" else (l_t - bx.z)
            level = lvl_t * a.d
        call = Call(cid=cid, aid=a.aid, family=a.family, d=a.d, origin=self.origin, issued_at=t, issue_seq=self.seq,
                    trigger_start=m.start, ref=m.c, v=g["v"], t=g["t"], target_type=g["type"], limiting=g["limiting"],
                    s15=self.s15, area=g["area"], expected=p.expected(a.family), min_residual=p.residual_min[a.family],
                    hard_deadline=t + hard, progress_at=t + _scaled(hard, p.progress_fraction), premise_kind=premise[0],
                    premise_level=level, entry="AVAILABLE", entry_reasons=[], conditions_ok=True)
        self.call = call
        self.call_count += 1
        if self.window == "WARMUP":
            self.counters["calls_issued_warmup"] += 1
        else:
            self.counters["calls_issued"][a.family][dname(a.d)] += 1
        self._end_attempt(a, "ISSUED", cid, t)
        act = self._actionability(cid, True, [], e, t)
        self._emit_call(call, act, t)
        self._touch()

    def _actionability(self, subject: str, ok: bool, blockers: list[str], e: dict, t: datetime) -> dict:
        g = e.get("geom") or {}
        chk = e.get("chk")
        area = g.get("area")
        bounds = None
        if area is not None and e.get("k") is not None:
            bounds = geo.admissible_bounds(e["a"].d if "a" in e else self.call.d, area, g["v"], g["t"], e["k"],
                                           self.p.rr_min, self.tick)
        rec = {"subject_id": subject, "actionable": ok, "blockers": tuple(blockers),
               "execution_mode": self.cfg.profile.execution.value, "side_price": e.get("price"),
               "side_price_source": e.get("source"), "cost_envelope_bps": e.get("k"),
               "gain_bps": chk.g if chk else None, "risk_bps": chk.q if chk else None,
               "reward_risk_margin": chk.margin if chk else None, "structural_area": area,
               "admissible_bounds": bounds, "remaining_minutes": None, "limiting_landmark": g.get("limiting")}
        self._emit("actionability", t, rec, lineage=(subject,))
        return rec

    # ----------------------------------------------------------------------------------------------------------
    # call lifecycle
    # ----------------------------------------------------------------------------------------------------------

    def _progress(self, call: Call, t: datetime) -> bool:
        """Half-horizon check on wholly post-issue complete-minute closes ending <= progress_at. True if retired."""
        call.progress_done = True
        best = call.max_fav_t
        if best is None or best < self.p.progress_min_scale * call.s15:
            self._terminate(call, "RETIRED", "STALLED", t)
            return True
        return False

    def _call_lifecycle(self, items: list, closes15: list[Bar], t: datetime) -> None:
        call = self.call
        if call is None or call.thesis != "ONGOING":
            return
        d = call.d
        for m in items:
            if call.thesis != "ONGOING":
                return
            if isinstance(m, tuple):  # missing/rejected/discontinuous trade minute
                if m[1] + MINUTE > call.issued_at:
                    self._terminate(call, "UNASSESSABLE", f"REQUIRED_MONITORING_GAP:{m[2]}", t)
                    return
                continue
            if m.end <= call.issued_at:
                continue  # detection/pre-issue minute: never certified
            if m.start < call.issued_at:
                # straddling issue publication: a possible T/V contact cannot be certified as post-issue
                _, h_t, l_t, _ = tbar(m, d)
                if h_t >= call.t * d or l_t <= call.v * d:
                    self._terminate(call, "UNASSESSABLE", "CONTACT_TIME_AMBIGUOUS", t)
                    return
                call.last_end = m.end  # freshness only: no progress extremum from a straddling interval
                continue
            if call.last_end is not None and m.start > call.last_end:
                self._terminate(call, "UNASSESSABLE", "REQUIRED_MONITORING_GAP:TRADE_1M_DISCONTINUITY", t)
                return
            if not call.progress_done and m.end > call.progress_at:
                if self._progress(call, t):  # every minute ending <= progress_at was already processed
                    return
            call.last_end = m.end
            _, h_t, l_t, c_t = tbar(m, d)
            hit_t, hit_v = h_t >= call.t * d, l_t <= call.v * d
            if hit_t and hit_v:
                self._terminate(call, "UNASSESSABLE", "BOTH_PROTECTIVE_LEVELS_CONTACTED_SAME_MINUTE", t)
                return
            if hit_t:
                self._terminate(call, "TARGET_REACHED", f"CERTIFIED_TARGET_CONTACT:{m.rid}", t)
                return
            if hit_v:
                self._terminate(call, "INVALIDATED", f"CERTIFIED_INVALIDATION_CONTACT:{m.rid}", t)
                return
            if m.end <= call.progress_at:
                fav = c_t - call.ref * d
                call.max_fav_t = fav if call.max_fav_t is None else max(call.max_fav_t, fav)
        for b in closes15:
            if b.end <= call.issued_at:
                continue
            if tbar(b, d)[3] < call.premise_level * d:
                self._terminate(call, "RETIRED", f"THESIS_FAILED:{call.premise_kind}:{b.rid}", t)
                return
        if (not call.progress_done and t >= call.progress_at and call.last_end is not None
                and call.last_end >= call.progress_at.replace(second=0, microsecond=0)):
            if self._progress(call, t):
                return
        if not self.ready_1m(t):
            self._terminate(call, "UNASSESSABLE", "REQUIRED_TRADE_1M_STALE", t)
            return
        # a progress minute that never arrives is caught by the stale/gap rules above (never guessed)
        if t >= call.hard_deadline:
            self._terminate(call, "TIME_EXPIRED", "HARD_DEADLINE", t)

    def _terminate(self, call: Call, status: str, reason: str, t: datetime) -> None:
        if call.thesis != "ONGOING":
            return
        call.thesis, call.terminal_reason, call.terminal_at = status, reason, t
        call.entry = "CLOSED"
        call.entry_reasons = ["THESIS_TERMINAL"]
        call.conditions_ok = False
        self.counters["terminal"][status] = self.counters["terminal"].get(status, 0) + 1
        self._revision(call, t, changed=("thesis",), guidance=_terminal_guidance(call))
        self.recent_calls.append({"call_id": call.cid, "family": call.family, "direction": dname(call.d),
                                  "issued_at": _iso(call.issued_at), "terminal": status, "reason": reason,
                                  "terminal_at": _iso(t), "origin": call.origin})
        self.call = None  # RETIRED/terminal guidance frees the recommendation slot immediately
        self._touch()

    def _reassess_call(self, t: datetime) -> None:
        call = self.call
        if call is None or call.thesis != "ONGOING":
            return
        reasons = list(self._common_blockers(t))
        remaining = call.hard_deadline - t
        if remaining < timedelta(minutes=call.min_residual):
            reasons.append("TOO_LATE")
        if call.origin != sc.Origin.LIVE.value and self.origin == sc.Origin.LIVE.value:
            reasons.append("RECONSTRUCTED_REQUIRES_FRESH_CALL")
        if self.origin == sc.Origin.RECONSTRUCTED.value:
            reasons.append("RECONSTRUCTED_CATCH_UP")
        price, source, k, qb = self._side_price(call.d, t)
        reasons += qb
        reasons += self.connection_blockers()
        conditions_ok = not reasons
        chk = None
        if price is not None:
            if not geo.in_area(price, call.area):
                reasons.append("PRICE_OUTSIDE_STRUCTURAL_AREA")
            chk = geo.predicate(call.d, price, call.v, call.t, k, self.p.rr_min)
            if not chk.ok:
                reasons.append(chk.reason)
        non_quote = [r for r in reasons if r not in UNVERIFIED_REASONS]
        status = "AVAILABLE" if not reasons else ("UNVERIFIED" if not non_quote else "CLOSED")
        reasons = sorted(set(reasons))
        key_changed = (status != call.entry or reasons != call.entry_reasons or conditions_ok != call.conditions_ok)
        if key_changed:
            self._entry_prev = call.entry
            if status == "AVAILABLE" and call.entry != "AVAILABLE":
                call.entry_reopens += 1
            changed = ["entry"] if status != call.entry else ["entry_reasons"]
            call.entry, call.entry_reasons, call.conditions_ok = status, reasons, conditions_ok
            self._revision(call, t, changed=tuple(changed), guidance=_entry_guidance(call), price=price, k=k, chk=chk)

    # ----------------------------------------------------------------------------------------------------------
    # events (typed calendar / incidents)
    # ----------------------------------------------------------------------------------------------------------

    def _event_input(self, ev: EventInput, t: datetime) -> None:
        prof = self.cfg.profile
        if ev.incident:
            if prof.incident_tape.value != "TYPED_TAPE":
                return
        elif prof.calendar.value == "NONE_UNKNOWN":
            return
        if (not ev.incident and prof.calendar.value == "STRICT_AS_KNOWN_ALLOW_UNKNOWN"
                and (ev.schedule_known_at is None or ev.schedule_known_at > t)):
            self.counters["events_unknown_vintage"] += 1
            return
        cur = self.events.get(ev.event_id)
        if cur is not None and cur["revision"] >= ev.revision:
            return
        rec = {**ev.encode(), "status": "UNKNOWN_TIME" if ev.schedule_time is None and not ev.incident else "SCHEDULED",
               "restrict_start": None, "post_min_end": None, "restriction_end": None, "response": None}
        if ev.incident:
            rec["status"] = "RESOLVED" if ev.resolved else "BLOCKING"
        elif ev.cancelled:
            rec["status"] = "CANCELLED"
        elif ev.schedule_time is not None:
            rec["restrict_start"] = _iso(ev.schedule_time - self.p.ev_pre)
            rec["post_min_end"] = _iso(ev.schedule_time + self.p.ev_post_min)
            rec["pre_reference"] = None
        self.events[ev.event_id] = rec
        self._emit_event(rec, t)
        self._touch()

    def _events_tick(self, t: datetime) -> None:
        for eid in sorted(self.events):
            e = self.events[eid]
            if e.get("incident") or e["status"] in ("CANCELLED", "UNKNOWN_TIME", "CLOSED"):
                continue
            st = _dt(e["schedule_time"])
            if e.get("pre_reference") is None and st is not None and t >= st:
                # last complete 1m trade close known STRICTLY before the event time, and the S15 known then
                lb = next((b for b in reversed(self.recent_1m) if b.known_at < st), None)
                sc15 = next((x[1] for x in reversed(self.s15_hist) if _dt(x[0]) < st), None)
                e["pre_reference"] = {"price": _s(lb.c) if lb else None, "time": _iso(lb.end) if lb else None,
                                      "s15": sc15}
            if e["status"] == "SCHEDULED" and t >= _dt(e["restrict_start"]):
                e["status"] = "RESTRICTING"
                self._emit_event(e, t)
            if e["status"] == "RESTRICTING" and t >= _dt(e["post_min_end"]) and self.m15:
                resp = next((b for b in self.m15 if b.start >= st), None)
                if resp is not None:
                    e["restriction_end"] = _iso(max(_dt(e["post_min_end"]), resp.end))
                    e["status"] = "CLOSED"
                    self._event_response(e, resp, t)
                    self._emit_event(e, t)

    def _event_blockers(self, t: datetime) -> list[str]:
        out = []
        for eid in sorted(self.events):
            e = self.events[eid]
            if e.get("incident"):
                if e["status"] == "BLOCKING":
                    out.append(f"INCIDENT:{eid}")
            elif e["status"] == "RESTRICTING" or (e["status"] == "SCHEDULED" and e["restrict_start"]
                                                  and _dt(e["restrict_start"]) <= t):
                out.append(f"EVENT_RESTRICTION:{eid}")
        return out

    def _event_response(self, e: dict, resp: Bar, t: datetime) -> None:
        pre = e.get("pre_reference") or {}
        ref, s = _d(pre.get("price")), _d(pre.get("s15"))
        unavailable = []
        disp = trr = None
        prev_close = None
        for x, y in zip(self.m15, list(self.m15)[1:]):
            if y.rid == resp.rid:
                prev_close = x.c
        if ref is None or s is None:
            unavailable.append("pre_event_reference_or_scale")
        else:
            disp = div(resp.c - ref, s)
            if prev_close is not None:
                trr = div(max(resp.h - resp.lo, abs(resp.h - prev_close), abs(resp.lo - prev_close)), s)
            else:
                unavailable.append("true_range_previous_close")
        flags = {}
        for lm in self.landmarks.values():
            if lm.created_at <= _dt(e["schedule_time"]):
                near = lm.price - lm.z if lm.side == "HIGH" else lm.price + lm.z
                if lm.side == "HIGH":
                    flags[lm.lid] = resp.h > lm.price + lm.z and resp.c < near
                else:
                    flags[lm.lid] = resp.lo < lm.price - lm.z and resp.c > near
        e["response"] = {"displacement_scale": _s(disp), "true_range_scale": _s(trr), "bar": resp.rid}
        self._emit("event_response", t, {
            "event_id": e["event_id"], "pre_event_reference": ref, "pre_event_reference_time": _dt(pre.get("time")),
            "pre_event_scale": s, "response_bar_start": resp.start, "displacement_scale": disp,
            "true_range_scale": trr, "reclaim_flags": dict(sorted((k, v) for k, v in flags.items() if v)),
            "unavailable_fields": tuple(unavailable)}, lineage=(e["event_id"],), event=(resp.start, resp.end))

    # ----------------------------------------------------------------------------------------------------------
    # view and observations
    # ----------------------------------------------------------------------------------------------------------

    def _scenario(self, a: Attempt) -> dict:
        exp = self.p.expected(a.family)
        return {"scenario_id": a.aid, "family": a.family, "direction": dname(a.d),
                "antecedent": (f"a later eligible complete 1m close {'>=' if a.d > 0 else '<='} "
                               f"{a.k_t * a.d + self.tick * self.p.trigger_ticks * a.d} with "
                               f"{'low >' if a.d > 0 else 'high <'} {a.v_t * a.d}"),
                "trigger_level": a.k_t * a.d if a.k_t is not None else None,
                "invalidation_level": a.v_t * a.d if a.v_t is not None else None,
                "conditional_target": "nearest eligible opposing landmark at trigger" + (
                    " (or box-width projection)" if a.family == "B" else " (or frozen midpoint)" if a.family == "C"
                    else ""),
                "alternative": "no call: withdrawal, expiry or a failed trigger/geometry check",
                "expires_at": a.deadline, "candidate_domain": f"{a.family} expected {exp[0]}-{exp[1]}m"}

    def compute_view(self, t: datetime) -> dict:
        ctx = self.context(t)
        ph = self.phase_now(t)
        armed = sorted([a for a in self.attempts.values() if a.status == "ARMED"],
                       key=lambda a: (FAM_RANK[a.family], a.born_at, a.aid))
        dirs = {a.d for a in armed}
        call = self.call if self.call is not None and self.call.thesis == "ONGOING" else None
        blockers: list[str] = []
        principal = None
        alts: list[dict] = []
        conditional = False
        reasons: list[str] = []
        counter: list[str] = []
        if not self.ready_15m(t) or not self.ready_1h(t):
            row, exp = "REQUIRED_CONTEXT_UNAVAILABLE", "UNAVAILABLE"
            blockers = [x for x in ("TRADE_15M_NOT_READY" if not self.ready_15m(t) else "",
                                    "TRADE_1H_NOT_READY" if not self.ready_1h(t) else "") if x]
        elif len(dirs) > 1 or (call is not None and any(a.d != call.d for a in armed)):
            row, exp = "OPPOSING_SCENARIOS", "UNCERTAIN"
            alts = [self._scenario(a) for a in armed]
            reasons.append("valid armed scenarios point in opposite directions" if call is None else
                           "the ongoing call is opposed by a valid armed scenario")
        elif call is not None:
            row, exp = "ONGOING_CALL", "UP" if call.d > 0 else "DOWN"
            conditional = True
            reasons.append(f"ongoing {call.family} {dname(call.d)} toward {call.t} while the premise survives")
            if ctx_t(ctx, call.d) not in ("UP",):
                counter.append(f"1h observed context now {ctx}")
        elif armed:
            row, exp = "ARMED_SCENARIO", "UP" if armed[0].d > 0 else "DOWN"
            conditional = True
            principal = self._scenario(armed[0])
            alts = [self._scenario(a) for a in armed[1:]]
            reasons.append(f"{armed[0].family} {dname(armed[0].d)} armed: call only if the antecedent occurs")
        elif ctx == "BALANCED" and ph in ("COMPRESSION", "ROTATION"):
            row, exp = "BALANCED_RANGE", "BALANCED"
            reasons.append("balanced 1h context in " + ph.lower() + (
                f"; rotation inside [{self.box.low}, {self.box.up}]" if self.box else "; no qualified box"))
        else:
            row, exp = "NO_SUPPORTED_PLAN", "UNCERTAIN"
            reasons.append(f"observed {ctx}/{ph} without a supported prospective plan")
        levels = self._levels(t)
        hz = None
        if call is not None:
            rem = int((call.hard_deadline - t) / MINUTE)
            hz = (min(call.expected[0], rem), min(call.expected[1], rem))
        elif principal is not None:
            e = self.p.expected(principal["family"])
            hz = (e[0], e[1])
        return {"observed_context": ctx, "phase": ph, "expected_direction": exp, "conditional": conditional,
                "table_row": row, "principal": principal, "alternatives": tuple(alts),
                "ongoing_call_id": call.cid if call else None, "horizon_minutes": hz, "levels": levels,
                "reasons": tuple(reasons), "counterevidence": tuple(counter), "blockers": tuple(blockers)}

    def _levels(self, t: datetime) -> dict[str, str | None]:
        price = self.last_1m.c if self.last_1m else None
        out: dict[str, str | None] = {"last_trade_close": _s(price)}
        if price is not None:
            above = sorted((lm.price - lm.z, lm.lid) for lm in self.landmarks.values()
                           if lm.status == "ACTIVE" and lm.side == "HIGH" and lm.price - lm.z > price)
            below = sorted(((lm.price + lm.z, lm.lid) for lm in self.landmarks.values()
                            if lm.status == "ACTIVE" and lm.side == "LOW" and lm.price + lm.z < price), reverse=True)
            out["nearest_resistance_near_edge"] = str(above[0][0]) if above else None
            out["nearest_support_near_edge"] = str(below[0][0]) if below else None
        if self.box is not None:
            out.update(box_low=str(self.box.low), box_up=str(self.box.up), box_mid=str(self.box.mid))
        return out

    def _publish_view(self, t: datetime) -> None:
        v = self.compute_view(t)
        key = (v["table_row"], v["expected_direction"], v["observed_context"], v["phase"],
               (v["principal"] or {}).get("scenario_id"), tuple(a["scenario_id"] for a in v["alternatives"]),
               v["ongoing_call_id"], v["blockers"])
        self.view = v
        if key == self.view_key:
            return
        self.view_key = key
        self.counters["view_changes"] += 1
        rec = dict(v)
        rec["principal"] = sc.Scenario(**v["principal"]) if v["principal"] else None
        rec["alternatives"] = tuple(sc.Scenario(**a) for a in v["alternatives"])
        self._emit("market_view", t, rec)

    def lenses(self, t: datetime) -> list[dict]:
        """Current lens cards (human meaning, result, role, freshness). Inspection only; not journal records."""
        ctx, ph = self.context(t), self.phase_now(t)
        last = self.last_1m
        disl = self.disl
        out = [
            {"lens": "structure", "name": "Structure & levels", "result": self._structure_text(t),
             "role": "Targets come from the nearest eligible opposing level; inside an opposing zone blocks entry.",
             "status": "READY" if self.ready_15m(t) else "WARMING_UP"},
            {"lens": "momentum", "name": "Momentum (1h context)", "result": ctx,
             "detail": {"er8": _s(self.ctx["er8"]), "displacement8_scale": _s(self.ctx["disp8"])},
             "role": "Context gate: A needs UP for LONG, B must not be against, C needs BALANCED. Not a vote.",
             "status": "READY" if ctx != "UNAVAILABLE" else "UNAVAILABLE", "since": _iso(self.ctx.get("since"))},
            {"lens": "volatility", "name": "Volatility & phase", "result": ph,
             "detail": {"s15": _s(self.s15), "compression_ratio": _s(self.phase["cr"]), "er6": _s(self.phase["er6"]),
                        "expansion_direction": self.phase["dir"]},
             "role": "Scale for zones/room; COMPRESSION gates box birth; adverse EXPANSION withdraws attempts.",
             "status": "READY" if ph != "UNAVAILABLE" else "UNAVAILABLE", "since": _iso(self.phase.get("since"))},
            {"lens": "timing", "name": "Timing / cycle", "result": f"phase {ph} (age descriptive)",
             "role": "Observed contraction/expansion phase only. Predictive periodic cycles: NOT COVERED.",
             "status": "LIMITED"},
            {"lens": "participation", "name": "Participation (volume)", "result": _s(self.part),
             "role": "Descriptive only; never confirms a call.", "status": "READY" if self.part is not None else
             "UNAVAILABLE"},
            {"lens": "events", "name": "News & events", "result": self._events_text(t),
             "role": "Known scheduled events restrict new entry around release; unknown coverage is shown, not 'no news'.",
             "status": self.cfg.profile.calendar.value},
            {"lens": "derivatives", "name": "Derivatives (mark/index, funding)",
             "result": {k: v["status"] for k, v in sorted(disl.items())},
             "detail": {"trade_mark_bps": disl["TRADE_MARK"].get("cur"), "trade_index_bps": disl["TRADE_INDEX"].get("cur"),
                        "funding_last": self.funding_last},
             "role": "Dislocation above threshold blocks execution adequacy; no direction. OI/liquidations NOT COVERED.",
             "status": self.cfg.profile.dislocation.value},
            {"lens": "execution", "name": "Execution adequacy", "result": self._quote_state(t),
             "detail": {"quote": self.quote.encode() if self.quote else None, "last_trade_close": _s(last.c if last else None)},
             "role": ("Live entry uses the measured ask (LONG) / bid (SHORT); missing quotes => UNVERIFIED."
                      if self.cfg.profile.execution == Execution.LIVE_QUOTED else
                      "Historical mode: MODELED latest complete trade-minute close; never a measured quote."),
             "status": self.cfg.profile.execution.value},
        ]
        return out

    def _structure_text(self, t: datetime) -> str:
        lv = self._levels(t)
        parts = []
        if lv.get("nearest_resistance_near_edge"):
            parts.append(f"resistance near {lv['nearest_resistance_near_edge']}")
        if lv.get("nearest_support_near_edge"):
            parts.append(f"support near {lv['nearest_support_near_edge']}")
        if self.box is not None:
            parts.append(f"compression box {self.box.low}–{self.box.up}")
        return "; ".join(parts) or "no eligible level yet"

    def _events_text(self, t: datetime) -> str:
        if self.cfg.profile.calendar.value == "NONE_UNKNOWN":
            return "calendar coverage UNKNOWN (no typed schedule tape): unscheduled/unknown news not covered"
        bl = self._event_blockers(t)
        return ", ".join(bl) if bl else "no known restriction now (bounded calendar subset only)"

    def _publish_observations(self, t: datetime) -> None:
        obs = {
            "context": (self.context(t), "momentum", {"er8": _s(self.ctx["er8"]), "displacement8_scale": _s(self.ctx["disp8"]),
                                                      "s1h": _s(self.ctx["s1h"])}, "FAMILY_CONTEXT_GATE",
                        "1h observed path label (not a forecast)."),
            "phase": (self.phase_now(t), "volatility", {"compression_ratio": _s(self.phase["cr"]), "er6": _s(self.phase["er6"]),
                                                        "displacement6_scale": _s(self.phase["disp6"]),
                                                        "s15": _s(self.s15), "expansion_direction": self.phase["dir"]},
                      "BOX_BIRTH_AND_ADVERSE_EXPANSION_GATES", "Observed volatility/structure phase; age descriptive."),
            "dislocation": ("/".join(f"{k}:{v['status']}" for k, v in sorted(self.disl.items())), "derivatives",
                            {"trade_mark_bps": self.disl["TRADE_MARK"].get("cur"),
                             "trade_index_bps": self.disl["TRADE_INDEX"].get("cur")}, "EXECUTION_ADEQUACY_RESTRICTION",
                            "Trade vs mark/index dislocation; never a direction."),
            "readiness": ("/".join(f"{x.name}:{x.status}" for x in self._deps), "execution", {}, "DATA_READINESS",
                          "Named dependency readiness (event-end and known-at age)."),
        }
        if self.cfg.profile.execution == Execution.LIVE_QUOTED:
            obs["quotes"] = (self._quote_state(t), "execution", {"bid": _s(self.quote.bid) if self.quote else None,
                                                                 "ask": _s(self.quote.ask) if self.quote else None},
                             "EXECUTION_ADEQUACY", "Measured public bid/ask freshness (indicative, not a fill).")
        for name in sorted(obs):
            cat, lens, values, role, meaning = obs[name]
            if self.obs_last.get(name) == cat:
                continue
            self.obs_last[name] = cat
            self._emit("observation", t, {"lens": lens, "name": name, "values": values, "category": cat,
                                          "decision_role": role, "meaning": meaning})

    # ----------------------------------------------------------------------------------------------------------
    # journal emission
    # ----------------------------------------------------------------------------------------------------------

    def _envelope(self, kind: str, rid: str, t: datetime, revision: int = 0, lineage: tuple = (),
                  event: tuple[datetime | None, datetime | None] | None = None) -> sc.Envelope:
        ev = event or (None, None)
        lim = []
        if self.cfg.profile.calendar.value == "NONE_UNKNOWN":
            lim.append("CALENDAR_COVERAGE_UNKNOWN")
        if self.cfg.profile.execution == Execution.HISTORICAL_BASE:
            lim.append("HISTORICAL_MODELED_EXECUTION_NOT_MEASURED_QUOTES")
        if self.cfg.profile.funding_outcomes.value == "PRICE_NET_ONLY":
            lim.append("FUNDING_COMPLETENESS_UNPROVEN")
        if self.origin == sc.Origin.RECONSTRUCTED.value:
            lim.append("RECONSTRUCTED_NOT_MEASURED_RECEIPT")
        return sc.Envelope(record_id=rid, revision=revision, kind=kind, method=self.cfg.method,
                           instrument=self.cfg.instrument, price_role="TRADE", origin=sc.Origin(self.origin),
                           clock_policy=self.cfg.clock_policy, professional_seq=self.seq, factual_cursor=self.cursor,
                           clock_time=t, event_start=ev[0], event_end=ev[1], known_at=t, published_at=t,
                           dependencies=self._deps, limitations=tuple(lim), lineage=tuple(lineage))

    def _emit(self, kind: str, t: datetime, body: dict, rid: str | None = None, revision: int = 0,
              lineage: tuple = (), event: tuple | None = None) -> dict:
        self.journal_seq += 1
        rid = rid or f"{kind}-{self.journal_seq:08d}"
        env = self._envelope(kind, rid, t, revision, lineage, event)
        model = sc.KIND_CONTRACTS[kind](env=env, **body)
        doc = json.loads(model.model_dump_json())
        digest = hashlib.sha256(canonical(doc)).hexdigest()
        self.journal_chain = hashlib.sha256(bytes.fromhex(self.journal_chain) + bytes.fromhex(digest)).hexdigest()
        entry = {"seq": self.journal_seq, "kind": kind, "record_id": rid, "clock_time": doc["env"]["clock_time"],
                 "professional_seq": self.seq, "factual_cursor": self.cursor, "origin": self.origin,
                 "subject": (lineage[0] if lineage else None), "digest": digest, "chain": self.journal_chain,
                 "record": doc}
        self.journal.append(entry)
        return entry

    def _emit_landmark(self, lm: Landmark, t: datetime) -> None:
        self._emit("landmark", t, {
            "landmark_id": lm.lid, "landmark_type": lm.ltype, "side": lm.side, "price": lm.price,
            "zone_low": lm.price - lm.z, "zone_high": lm.price + lm.z, "zone_halfwidth": lm.z, "frozen_scale": lm.s15,
            "horizon": lm.horizon, "source_ids": tuple(lm.sources), "extremum_time": lm.extremum_time,
            "status": lm.status, "status_reason": lm.status_reason, "owner": lm.owner}, lineage=(lm.lid,))

    def _candidate(self, a: Attempt, transition: str, reason: str | None, t: datetime, terminal: bool = False,
                   status: str | None = None) -> None:
        st = status or ("ARMED" if a.status == "ARMED" else "WATCH")
        setup = {"s15": str(a.s15), "zone_halfwidth": str(a.z), "sources": ",".join(a.sources[-3:]),
                 "renewal": a.renewal, "pre_live": str(a.pre_live)}
        if a.family == "A":
            setup.update(impulse_A=_s(a.a_t * a.d if a.a_t is not None else None),
                         impulse_B=_s(a.b_t * a.d if a.b_t is not None else None),
                         reaction=_s(a.r_t * a.d if a.r_t is not None else None), anchor=a.anchor,
                         bars_seen=str(a.bars_seen), latch_long=self.latch["1"], latch_short=self.latch["-1"])
        elif self.box is not None and a.owner == self.box.bid:
            setup.update(box_low=str(self.box.low), box_up=str(self.box.up), box_mid=str(self.box.mid))
        self._emit("candidate", t, {
            "attempt_id": a.aid, "owner_id": a.owner, "family": sc.Family(a.family), "direction": sc.Direction(dname(a.d)),
            "status": st, "transition": transition, "reason": reason,
            "trigger_level": a.k_t * a.d if a.k_t is not None else None,
            "invalidation_level": a.v_t * a.d if a.v_t is not None else None, "setup": setup,
            "arm_published_at": a.arm_at, "expires_at": a.deadline},
            rid=f"{a.aid}#{transition.lower()}-{self.journal_seq + 1}", lineage=(a.aid,) + ((a.owner,) if a.owner else ()))

    def _emit_call(self, call: Call, act: dict, t: datetime) -> None:
        p = self.p
        thesis = (f"{dname(call.d)} {call.family} ({_FAMILY_TEXT[call.family]}): from {call.ref} toward "
                  f"{call.t} ({call.target_type.lower()}), invalidated at {call.v}")
        self._emit("call", t, {
            "call_id": call.cid, "attempt_id": call.aid, "family": sc.Family(call.family),
            "direction": sc.Direction(dname(call.d)), "thesis": thesis, "trigger_minute_start": call.trigger_start,
            "issue_reference": call.ref, "issued_at": call.issued_at, "invalidation": call.v, "target": call.t,
            "target_type": call.target_type, "limiting_landmark": call.limiting, "frozen_scale": call.s15,
            "structural_area": call.area, "expected_minutes": call.expected, "minimum_residual_minutes": call.min_residual,
            "hard_deadline": call.hard_deadline, "progress_check_at": call.progress_at,
            "premise": f"{call.premise_kind} {call.premise_level}", "entry_status": call.entry,
            "thesis_status": call.thesis, "actionability": sc.Actionability(env=self._envelope(
                "actionability", f"{call.cid}#act", t), **act),
            "cost_assumptions": (f"HISTORICAL_BASE K={p.hist_k_bps}bps (fees {p.fee_bps}/leg + allowance "
                                 f"{p.allowance_bps}/leg; declared assumptions, not account rates)"
                                 if self.cfg.profile.execution == Execution.HISTORICAL_BASE else
                                 f"LIVE_QUOTED fees {p.live_fee_bps}/leg + slippage {p.live_slip_bps}/leg + prospective "
                                 "exit half-spread; entry spread already in the side quote"),
            "uncertainties": ("no calibrated probability", "targets are not expected returns",
                              "stop is guidance, not an order or guaranteed fill",
                              "unknown news/calendar coverage" if self.cfg.profile.calendar.value == "NONE_UNKNOWN"
                              else "bounded calendar subset only")},
            rid=call.cid, lineage=(call.aid,), event=(call.trigger_start, call.trigger_start + MINUTE))
        self._material(call, "NEW_CALL", f"New {dname(call.d)} call ({call.family}): entry available inside "
                                         f"{call.area[0]}–{call.area[1]}, target {call.t}, stop {call.v}", t)

    def _revision(self, call: Call, t: datetime, changed: tuple, guidance: str, price=None, k=None, chk=None) -> None:
        call.revision += 1
        rem = call.hard_deadline - t
        rem_m = Decimal(int(rem.total_seconds())) / 60 if rem > timedelta(0) else ZERO
        window = None
        if call.thesis == "ONGOING" and rem_m >= call.min_residual:
            window = (Decimal(call.expected[0]), min(Decimal(call.expected[1]), rem_m))
        bounds = None
        if call.thesis == "ONGOING":
            kk = k if k is not None else (self.p.hist_k_bps if self.cfg.profile.execution == Execution.HISTORICAL_BASE
                                          else None)
            if kk is not None:
                bounds = geo.admissible_bounds(call.d, call.area, call.v, call.t, kk, self.p.rr_min, self.tick)
        prog = div(call.max_fav_t, call.s15) if call.max_fav_t is not None else None
        self._emit("call_revision", t, {
            "call_id": call.cid, "revision": call.revision, "entry_status": call.entry,
            "entry_reasons": tuple(call.entry_reasons), "entry_conditions_enabled": call.conditions_ok,
            "thesis_status": call.thesis, "terminal_reason": call.terminal_reason, "current_admissible_bounds": bounds,
            "remaining_minutes": rem_m, "duration_window_minutes": window, "guidance": guidance, "changed": changed,
            "progress_max_favorable_scale": prog},
            rid=f"{call.cid}#r{call.revision}", revision=call.revision, lineage=(call.cid,))
        if "thesis" in changed:
            self._material(call, "TERMINAL", f"{call.thesis}" + (f" ({call.terminal_reason})" if call.terminal_reason
                                                                 else "") + f": {guidance}", t)
        elif "entry" in changed:
            ct = {"AVAILABLE": "ENTRY_REOPENED", "CLOSED": "ENTRY_WITHDRAWN", "UNVERIFIED": "ENTRY_UNVERIFIED"}[call.entry]
            # withdrawal of USABLE entry (AVAILABLE -> CLOSED/UNVERIFIED) alerts once; a further change between two
            # unusable states (CLOSED <-> UNVERIFIED) is recorded but never re-alerted; recovery alerts as reopened
            usable_change = call.entry == "AVAILABLE" or self._entry_prev == "AVAILABLE"
            owner_stop = "LIVE_SESSION_STOPPED" in call.entry_reasons  # the Owner's own Stop is not an alert
            self._material(call, ct, guidance, t, alert=usable_change and not owner_stop)

    def _material(self, call: Call, ctype: str, summary: str, t: datetime, alert: bool = True) -> None:
        alertable = alert and call.origin == sc.Origin.LIVE.value and self.origin == sc.Origin.LIVE.value
        self._emit("material_change", t, {"change_id": f"{call.cid}#{ctype.lower()}#{call.revision}",
                                          "subject_id": call.cid, "change_type": ctype, "summary": summary,
                                          "alertable": alertable},
                   rid=f"{call.cid}#mc{call.revision}-{ctype.lower()}", lineage=(call.cid,))

    def _emit_event(self, e: dict, t: datetime) -> None:
        self._emit("event_context", t, {
            "event_id": e["event_id"], "event_revision": e["revision"], "event_type": e["event_type"],
            "scope": e["scope"], "schedule_time": _dt(e["schedule_time"]), "schedule_known_at": _dt(e["schedule_known_at"]),
            "content_known_at": _dt(e["content_known_at"]), "provenance_sha256": e["provenance_sha256"],
            "coverage_start": None, "coverage_end": None, "cancelled": e["cancelled"],
            "restriction_start": _dt(e["restrict_start"]), "restriction_end": _dt(e["restriction_end"]),
            "status": e["status"]}, lineage=(e["event_id"],))

    # ----------------------------------------------------------------------------------------------------------
    # inspection
    # ----------------------------------------------------------------------------------------------------------

    def call_view(self, t: datetime | None = None) -> dict | None:
        call = self.call
        if call is None:
            return None
        t = t or self.clock
        rem = call.hard_deadline - t
        rem_m = max(int(rem.total_seconds()) // 60, 0)
        k = self.p.hist_k_bps if self.cfg.profile.execution == Execution.HISTORICAL_BASE else self._side_price(call.d, t)[2]
        bounds = geo.admissible_bounds(call.d, call.area, call.v, call.t, k, self.p.rr_min, self.tick) if k else None
        return {"call_id": call.cid, "family": call.family, "family_text": _FAMILY_TEXT[call.family],
                "direction": dname(call.d), "origin": call.origin, "issued_at": _iso(call.issued_at),
                "issue_reference": str(call.ref), "target": str(call.t), "target_type": call.target_type,
                "stop": str(call.v), "structural_area": [str(call.area[0]), str(call.area[1])],
                "admissible_bounds": [str(bounds[0]), str(bounds[1])] if bounds else None,
                "entry_status": call.entry, "entry_reasons": call.entry_reasons, "thesis_status": call.thesis,
                "hard_deadline": _iso(call.hard_deadline), "remaining_minutes": rem_m,
                "expected_minutes": list(call.expected),
                "duration_window": [call.expected[0], min(call.expected[1], rem_m)] if rem_m >= call.min_residual else None,
                "progress_check_at": _iso(call.progress_at), "premise": f"{call.premise_kind} {call.premise_level}",
                "limiting_landmark": call.limiting, "revision": call.revision,
                "guidance": _entry_guidance(call)}

    def inspect(self) -> dict:
        t = self.clock
        return {
            "format": STATE_FORMAT, "clock": _iso(t), "professional_seq": self.seq, "factual_cursor": self.cursor,
            "origin": self.origin, "window": self.window, "live_since": _iso(self.live_since),
            "connection": self.connection, "view": _jsonable(self.view), "diagnostics": self.diag, "call": self.call_view(t) if t else None,
            "recent_calls": list(self.recent_calls), "lenses": _jsonable(self.lenses(t)) if t else [],
            "attempts": [{"attempt_id": a.aid, "family": a.family, "direction": dname(a.d), "status": a.status,
                          "trigger_level": _s(a.k_t * a.d if a.k_t is not None else None),
                          "invalidation_level": _s(a.v_t * a.d if a.v_t is not None else None),
                          "expires_at": _iso(a.deadline), "owner": a.owner}
                         for a in sorted(self.attempts.values(), key=lambda a: a.aid)],
            "box": self.box.encode() if self.box else None, "latch": dict(self.latch), "box_token": self.box_token,
            "landmarks": [{"id": lm.lid, "type": lm.ltype, "price": str(lm.price), "zone": [str(lm.price - lm.z),
                                                                                         str(lm.price + lm.z)],
                           "status": lm.status} for lm in sorted(self.landmarks.values(), key=lambda x: x.lid)],
            "readiness": [x.model_dump(mode="json") for x in self._deps],
            "journal_seq": self.journal_seq, "journal_chain": self.journal_chain,
            "counters": _jsonable(self.counters), "boundary": self.boundary,
        }

    # ----------------------------------------------------------------------------------------------------------
    # explicit state codec
    # ----------------------------------------------------------------------------------------------------------

    def encode(self) -> dict:
        return {
            "format": STATE_FORMAT, "fingerprint": self.cfg.fingerprint(),
            "m15": [b.encode() for b in self.m15], "h1": [b.encode() for b in self.h1],
            "broad": {k: [b.encode() for b in v] for k, v in sorted(self.broad.items())},
            "last_sealed_end": {k: _iso(v) for k, v in sorted(self.last_sealed_end.items())}, "gaps": self.gaps,
            "last_1m": self.last_1m.encode() if self.last_1m else None, "last_1m_end": _iso(self.last_1m_end),
            "s15": _s(self.s15), "phase": _jsonable(self.phase), "ctx": _jsonable(self.ctx), "part": _s(self.part),
            "landmarks": [lm.encode() for _, lm in sorted(self.landmarks.items())],
            "pending_pivots": self.pending_pivots,
            "attempts": [a.encode() for _, a in sorted(self.attempts.items())],
            "latch": self.latch, "qa_last": self.qa_last, "box": self.box.encode() if self.box else None,
            "box_token": self.box_token, "comp_prev": self.comp_prev,
            "call": self.call.encode() if self.call else None, "recent_calls": list(self.recent_calls),
            "call_count": self.call_count, "slot_px": self.slot_px, "disl": self.disl, "funding_last": self.funding_last,
            "events": self.events, "quote": self.quote.encode() if self.quote else None,
            "quote_status": self.quote_status, "connection": self.connection,
            "clock": _iso(self.clock), "seq": self.seq, "cursor": self.cursor,
            "origin": self.origin, "live_since": _iso(self.live_since), "window": self.window, "boundary": self.boundary,
            "journal_seq": self.journal_seq, "journal_chain": self.journal_chain,
            "view_key": _jsonable(list(self.view_key)) if self.view_key else None, "view": _jsonable(self.view),
            "obs_last": self.obs_last, "counters": _jsonable(self.counters), "diag": self.diag,
            "recent_1m": [b.encode() for b in self.recent_1m], "s15_hist": [list(x) for x in self.s15_hist],
            "pending_periods": self.pending_periods,
            "pending": {"bars": [e.model_dump(mode="json") for e in self._bars], "sealed": self._sealed,
                        "inputs": [[k, x.encode() if hasattr(x, "encode") else x] for k, x in self._inputs]},
        }

    @classmethod
    def decode(cls, doc: dict, cfg: AdviserConfig) -> AdviserCore:
        if doc.get("format") != STATE_FORMAT:
            raise AdviserError(f"adviser state format {doc.get('format')!r} is not {STATE_FORMAT}")
        if doc["fingerprint"] != cfg.fingerprint():
            raise AdviserError("adviser state fingerprint does not match the pinned configuration")
        c = cls(cfg)
        c.m15.extend(Bar.decode(x) for x in doc["m15"])
        c.h1.extend(Bar.decode(x) for x in doc["h1"])
        for k, v in doc["broad"].items():
            c.broad[k].extend(Bar.decode(x) for x in v)
        c.last_sealed_end = {k: _dt(v) for k, v in doc["last_sealed_end"].items()}
        c.gaps = dict(doc["gaps"])
        c.last_1m = Bar.decode(doc["last_1m"]) if doc["last_1m"] else None
        c.last_1m_end = _dt(doc["last_1m_end"])
        c.s15 = _d(doc["s15"])
        c.phase = _phase_decode(doc["phase"])
        c.ctx = _ctx_decode(doc["ctx"])
        c.part = _d(doc["part"])
        c.landmarks = {d["lid"]: Landmark.decode(d) for d in doc["landmarks"]}
        c.pending_pivots = list(doc["pending_pivots"])
        c.attempts = {d["aid"]: Attempt.decode(d) for d in doc["attempts"]}
        c.latch, c.qa_last = dict(doc["latch"]), dict(doc["qa_last"])
        c.box = Box.decode(doc["box"]) if doc["box"] else None
        c.box_token, c.comp_prev = doc["box_token"], doc["comp_prev"]
        c.call = Call.decode(doc["call"]) if doc["call"] else None
        c.recent_calls = deque(doc["recent_calls"], maxlen=12)
        c.call_count = doc["call_count"]
        c.slot_px, c.disl, c.funding_last = doc["slot_px"], doc["disl"], doc["funding_last"]
        c.events = doc["events"]
        c.quote = Quote.decode(doc["quote"]) if doc["quote"] else None
        c.quote_status = doc["quote_status"]
        c.connection = doc["connection"]
        c.clock, c.seq, c.cursor = _dt(doc["clock"]), doc["seq"], doc["cursor"]
        c.origin, c.live_since, c.window = doc["origin"], _dt(doc["live_since"]), doc["window"]
        c.boundary = doc["boundary"]
        c.journal_seq, c.journal_chain = doc["journal_seq"], doc["journal_chain"]
        c.view_key = _view_key_decode(doc["view_key"])
        c.view = _view_decode(doc["view"])
        c.obs_last = dict(doc["obs_last"])
        c.counters = doc["counters"]
        c.diag = doc["diag"]
        c.recent_1m = deque((Bar.decode(x) for x in doc["recent_1m"]), maxlen=4)
        c.s15_hist = deque((tuple(x) for x in doc["s15_hist"]), maxlen=4)
        c.pending_periods = list(doc["pending_periods"])
        c._bars = [FeedEvent.model_validate(x) for x in doc["pending"]["bars"]]
        c._sealed = list(doc["pending"]["sealed"])
        c._inputs = [(k, Quote.decode(x) if k == "quote" else EventInput.decode(x) if k == "event" else x)
                     for k, x in doc["pending"]["inputs"]]
        return c


def _scaled(td: timedelta, frac: Decimal) -> timedelta:
    """Exact fraction of a whole-second duration (e.g. half of the hard horizon)."""
    us = Decimal(int(td.total_seconds())) * 1_000_000 * frac
    if us != us.to_integral_value():
        raise AdviserError(f"{frac} of {td} is not a whole microsecond")
    return timedelta(microseconds=int(us))


_FAMILY_TEXT = {"A": "continuation after a reaction", "B": "compression exit with retest",
                "C": "failed exit of a compression range"}


def _entry_guidance(call: Call) -> str:
    if call.thesis != "ONGOING":
        return _terminal_guidance(call)
    if call.entry == "AVAILABLE":
        return (f"Entry still valid now inside the admissible part of {call.area[0]}–{call.area[1]}; stop {call.v}, "
                f"target {call.t}, hard deadline {call.hard_deadline.isoformat()}.")
    if call.entry == "UNVERIFIED":
        return "Thesis ongoing; current entry cannot be verified (no fresh quote). Do not treat as ready now."
    return ("Thesis ongoing but new entry is closed now (" + ", ".join(call.entry_reasons) +
            "). If following this call: hold with stop " + str(call.v) + ", target " + str(call.t) + ".")


def _terminal_guidance(call: Call) -> str:
    return {
        "TARGET_REACHED": "Target reached: the call's guidance is complete.",
        "INVALIDATED": "Invalidation level touched: the thesis is invalid; exit guidance if following this call.",
        "TIME_EXPIRED": "Hard deadline reached: exit guidance if following this call.",
        "UNASSESSABLE": "Cannot be assessed any more (data gap/ambiguity): exit guidance if following this call; no "
                        "safety is assumed for unseen intervals.",
        "RETIRED": ("Thesis retired (" + str(call.terminal_reason).split(":")[0] + "): exit guidance if following this "
                    "call. This is guidance withdrawal, not a statement about any position."),
    }.get(call.thesis, "")


def _new_diag() -> dict:
    """Fixed-size accumulator: microseconds per named condition (overlapping), onsets per condition, the covered
    evaluation-window time (denominator), the conditions currently holding and the time they were published."""
    return {"covered_us": 0, "us": {}, "onsets": {}, "active": [], "last": None}


def _new_counters() -> dict:
    return {"dispatches": 0, "episodes": {f: {"LONG": 0, "SHORT": 0} for f in "ABC"},
            "armed": {"A": 0, "B": 0, "C": 0}, "triggered": {"A": 0, "B": 0, "C": 0},
            "calls_issued": {f: {"LONG": 0, "SHORT": 0} for f in "ABC"}, "calls_issued_warmup": 0,
            "rejections": {"TRIGGER_CONTACT_AMBIGUOUS": 0}, "attempt_end": {}, "terminal": {}, "gates": {},
            "suppressed_by_slot": [], "boxes": 0, "box_tokens_discarded": 0, "box_geometry_not_qualified": 0,
            "landmarks_created": 0, "a_true_while_pending": 0, "c_both_edge_ambiguous": 0, "view_changes": 0,
            "quotes_admitted": 0, "quotes_not_newer": 0, "events_unknown_vintage": 0}


def _jsonable(x: Any) -> Any:
    if isinstance(x, Decimal):
        return str(x)
    if isinstance(x, datetime):
        return x.isoformat()
    if isinstance(x, dict):
        return {k: _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    return x


def _phase_decode(d: dict) -> dict:
    return {**d, "cr": _d(d["cr"]), "er6": _d(d["er6"]), "disp6": _d(d["disp6"]), "net3": _d(d.get("net3")),
            "since": _dt(d["since"])}


def _ctx_decode(d: dict) -> dict:
    return {**d, "er8": _d(d["er8"]), "disp8": _d(d["disp8"]), "s1h": _d(d["s1h"]), "since": _dt(d["since"])}


def _view_key_decode(x: list | None) -> tuple | None:
    if x is None:
        return None
    return (x[0], x[1], x[2], x[3], x[4], tuple(x[5]), x[6], tuple(x[7]))


def _view_decode(v: dict | None) -> dict | None:
    if v is None:
        return None
    out = dict(v)
    out["alternatives"] = tuple(v["alternatives"])
    out["reasons"] = tuple(v["reasons"])
    out["counterevidence"] = tuple(v["counterevidence"])
    out["blockers"] = tuple(v["blockers"])
    out["horizon_minutes"] = tuple(v["horizon_minutes"]) if v["horizon_minutes"] else None
    return out
