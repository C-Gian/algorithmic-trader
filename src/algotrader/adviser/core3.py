"""MP-002 ``btc.context-action.v0.3`` professional fold (implementation ``adviser.core.v3``; state
``algotrader.adviser-state.v3``).

It reuses the unchanged MP-001 v0.2 fold (``core.AdviserCore``) for every preserved rule — admission, factual 1m and
sealed-record ingestion, scale/context/phase, landmarks and BROKEN marks, box birth, events, dislocation, quotes and
live connection adequacy, issued-call protective contacts/premise/progress/deadline and entry reassessment — and
overrides only the semantics MP-002 names (§§3–8, §12):

* **Structural scenarios** (``Scen``) are owned independently of entry, call and evaluator. A has one discovery owner
  per direction released ONLY by original setup expiry, V/impulse-premise invalidation, narrative-B destination
  contact, required gap/staleness or pre-confirmation withdrawal/spend; renewal needs a Q_A=false observed at/after
  release then a new false->true. B/C box flags are consumed by the first structural birth; the opposite far-edge
  close uses the structural B episode (any status) until its own terminal.
* **Contacts** are certified only against levels active at the interval START (V and destination publications carry
  their actual dispatch time); straddling intervals are unassessable, never invented chronology.
* **A child entry**: exhaustive routing at the first clean confirmation (contact/target -> prerequisites ->
  nonselection gates -> IMMEDIATE v0.2 area -> RETURN corridor WAIT_PRICE -> distinct empty reasons). WAIT_PRICE is
  not a call: an immutable R–K corridor, frozen V/T_confirm, a monotone causal cap, temporary live-cost/zone
  blockers, and one fully actionable later complete-minute return entering the existing slot/conflict/priority
  selection once.
* **Clocks**: A hard deadline = confirmation + 4h for scenario and call; scenario progress = confirmation + 2h from
  the confirmation close/S15; call progress = issue + (H - issue)/2 from the issue close/S15. B/C confirmation =
  issue (their v0.2 clocks coincide).
* **Total MarketView** from structural scenarios only (cost-invariant); guidance lives in call records.

Records: ``scenario`` (structural, cost-invariant) and ``entry_attempt`` (economic child) plus the v0.3 call /
revision / view variants of semantic.v2 revision 2. No ``candidate`` records are emitted by this method.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from ..feed.ordering import canonical
from . import contracts as sc
from . import geometry as geo
from .core import (
    EPS,
    FAM_RANK,
    MINUTE,
    UNVERIFIED_REASONS,
    AdviserConfig,
    AdviserCore,
    AdviserError,
    Call,
    _d,
    _dt,
    _entry_guidance,
    _FAMILY_TEXT,
    _h,
    _iso,
    _jsonable,
    _s,
    _scaled,
    _terminal_guidance,
    ctx_t,
    dname,
    tbar,
)
from .identity import Execution
from .measures import ZERO, Bar, div, median, round_down, round_up

STATE_FORMAT = "algotrader.adviser-state.v3"
BASE_STATE_FORMAT = "algotrader.adviser-state.v2"
A_CAPACITY_PER_DIRECTION = 18  # MP-002 §3 conservative active A scenario capacity (incl. boundary headroom)
BC_CAPACITY = 128  # MP-002 §3 conservative active B/C scenario capacity
ROUTABLE = frozenset({"NO_ROOM_AFTER_COSTS", "REWARD_RISK_BELOW_MINIMUM", "EMPTY_STRUCTURAL_AREA",
                      "PRICE_OUTSIDE_STRUCTURAL_AREA"})
# A owner release reasons are every scenario terminal that can occur before original setup expiry (MP-002 §3 B1)
COVERAGE_REASONS = ("REQUIRED_GAP", "REQUIRED_MONITORING_GAP", "REQUIRED_TRADE_1M_STALE", "REQUIRED_INPUT_STALE")


def _tick_floor(x: Decimal, tick: Decimal) -> Decimal:
    return round_down(x, tick)


def _tick_ceil(x: Decimal, tick: Decimal) -> Decimal:
    return round_up(x, tick)


def _market(lo_t: Decimal, hi_t: Decimal, d: int) -> tuple[Decimal, Decimal]:
    """Transformed interval [lo', hi'] back to market prices (ascending)."""
    return (lo_t, hi_t) if d > 0 else (-hi_t, -lo_t)


def half_point(start: datetime, end: datetime) -> datetime:
    """start + (end - start)/2 at microsecond resolution; an odd microsecond span rounds up (the check never runs
    before the exact midpoint)."""
    us = (end - start) // timedelta(microseconds=1)
    return start + timedelta(microseconds=(us + 1) // 2)


# --------------------------------------------------------------------------------------------------------------
# state objects
# --------------------------------------------------------------------------------------------------------------


@dataclass
class Scen:
    """One structural scenario (MP-002 §3). Prices with suffix _t are direction-transformed (d*x)."""

    sid: str
    family: str
    d: int
    owner: str | None
    born_at: datetime
    born_seq: int
    sources: list[str]
    setup_deadline: datetime
    s15: Decimal
    z: Decimal
    status: str = "WATCH"  # WATCH / ARMED / CONFIRMED (terminal scenarios leave the active table)
    k_t: Decimal | None = None
    v_t: Decimal | None = None
    v_hist: list = field(default_factory=list)  # [[since_iso, v_t]] publications of V (arm + revisions)
    arm_at: datetime | None = None
    arm_seq: int | None = None
    pre_live: bool = False
    # A
    a_t: Decimal | None = None
    b_t: Decimal | None = None
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
    # frozen structural destination / price premise (transformed)
    dest_t: Decimal | None = None
    dest_type: str = "NONE"
    premise_t: Decimal | None = None
    # confirmation
    conf_at: datetime | None = None
    conf_seq: int | None = None
    conf_close_t: Decimal | None = None
    conf_s15: Decimal | None = None
    conf_minute: str | None = None
    conf_deadline: datetime | None = None
    progress_at: datetime | None = None
    progress_done: bool = False
    max_fav_t: Decimal | None = None
    last_end: datetime | None = None
    # child entry attempt (economic side; never part of scenario records)
    entry: str = "PENDING"  # PENDING / WAIT / ISSUED / TERMINAL / CLEARED
    call_id: str | None = None

    _DT = ("born_at", "setup_deadline", "arm_at", "conf_at", "conf_deadline", "progress_at", "last_end")
    _DEC = ("s15", "z", "k_t", "v_t", "a_t", "b_t", "prev_close_t", "r_t", "anchor_h_t", "dest_t", "premise_t",
            "conf_close_t", "conf_s15", "max_fav_t")

    def encode(self) -> dict:
        return {k: (str(v) if isinstance(v, Decimal) else _iso(v) if isinstance(v, datetime) else v)
                for k, v in self.__dict__.items()}

    @classmethod
    def decode(cls, d: dict) -> Scen:
        x = dict(d)
        for k in cls._DT:
            x[k] = _dt(x[k])
        for k in cls._DEC:
            x[k] = _d(x[k])
        x["sources"] = list(x["sources"])
        x["v_hist"] = [list(v) for v in x["v_hist"]]
        return cls(**x)

    @property
    def eid(self) -> str:
        return f"{self.sid}#entry"


@dataclass
class Wait:
    """An A child entry attempt in WAIT_PRICE (MP-002 §§5–6). Market prices unless suffixed _t."""

    sid: str
    d: int
    conf_at: datetime
    conf_cursor: int
    setup_deadline: datetime
    hard: datetime
    v: Decimal
    t_conf: Decimal
    cap: Decimal
    caps: list  # [{cap, since, cursor, zone_id, near_edge}]
    lo_t: Decimal  # fixed structural corridor (transformed)
    hi_t: Decimal
    r: Decimal
    k_trigger: Decimal
    s15: Decimal
    conf_close: Decimal
    seen: list  # eligible opposing zone ids already known (confirmation set + seen later)
    blockers: list = field(default_factory=list)
    samples: int = 0

    _DT = ("conf_at", "setup_deadline", "hard")
    _DEC = ("v", "t_conf", "cap", "lo_t", "hi_t", "r", "k_trigger", "s15", "conf_close")

    def encode(self) -> dict:
        return {k: (str(v) if isinstance(v, Decimal) else _iso(v) if isinstance(v, datetime) else v)
                for k, v in self.__dict__.items()}

    @classmethod
    def decode(cls, d: dict) -> Wait:
        x = dict(d)
        for k in cls._DT:
            x[k] = _dt(x[k])
        for k in cls._DEC:
            x[k] = _d(x[k])
        x["caps"], x["seen"], x["blockers"] = list(x["caps"]), list(x["seen"]), list(x["blockers"])
        return cls(**x)

    def cap_t(self) -> Decimal:
        return self.cap * self.d

    def hi_eff_t(self, tick: Decimal) -> Decimal:
        return min(self.hi_t, self.cap_t() - tick)

    def corridor(self, tick: Decimal) -> tuple[Decimal, Decimal] | None:
        hi = self.hi_eff_t(tick)
        return None if hi < self.lo_t else _market(self.lo_t, hi, self.d)


@dataclass
class CallV3(Call):
    scenario_id: str = ""
    entry_mode: str = "IMMEDIATE"
    confirmed_at: datetime | None = None
    t_confirm: Decimal | None = None
    hard_origin: str = "ISSUE"
    cap_history: list = field(default_factory=list)
    coverage_loss_from: datetime | None = None
    scenario_terminal: str | None = None

    @classmethod
    def decode(cls, d: dict) -> CallV3:
        x = dict(d)
        for k in ("issued_at", "trigger_start", "hard_deadline", "progress_at", "terminal_at", "last_end",
                  "confirmed_at", "coverage_loss_from"):
            x[k] = _dt(x[k])
        for k in ("ref", "v", "t", "s15", "premise_level", "max_fav_t", "t_confirm"):
            x[k] = _d(x[k])
        x["area"] = (Decimal(x["area"][0]), Decimal(x["area"][1]))
        x["expected"] = (x["expected"][0], x["expected"][1])
        x["entry_reasons"] = list(x["entry_reasons"])
        x["cap_history"] = list(x["cap_history"])
        return cls(**x)


# --------------------------------------------------------------------------------------------------------------
# core
# --------------------------------------------------------------------------------------------------------------


class AdviserCoreV3(AdviserCore):
    def __init__(self, config: AdviserConfig) -> None:
        super().__init__(config)
        self.scen: dict[str, Scen] = {}
        self.a_owner: dict[str, dict | None] = {"1": None, "-1": None}  # A discovery owner per direction
        self.waits: dict[str, Wait] = {}  # child entry id -> WAIT_PRICE state
        self.counters.update(_new_counters3())

    # ----------------------------------------------------------------------------------------------------------
    # timers
    # ----------------------------------------------------------------------------------------------------------

    def next_deadline(self) -> datetime | None:
        if not self._dirty_nd:
            return self._nd
        c: list[datetime] = []
        for s in self.scen.values():
            if s.status in ("WATCH", "ARMED"):
                c.append(s.setup_deadline)
            else:
                c += [s.conf_deadline, s.progress_at]
        for own in self.a_owner.values():
            if own is not None:
                c.append(_dt(own["expires"]))
        for w in self.waits.values():
            c += [w.setup_deadline, w.hard - timedelta(minutes=self.p.residual_min["A"]) + EPS]
        if self.box is not None:
            c.append(self.box.expires_at)
        call = self.call
        if call is not None:
            c += [call.hard_deadline, call.progress_at, call.hard_deadline - timedelta(minutes=call.min_residual) + EPS]
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
        c = [x for x in c if x is not None]
        if self.clock is not None:
            c = [x for x in c if x > self.clock]
        self._nd = min(c) if c else None
        self._dirty_nd = False
        return self._nd

    # ----------------------------------------------------------------------------------------------------------
    # dispatch (MP-002 §6 collision precedence)
    # ----------------------------------------------------------------------------------------------------------

    def dispatch(self, t: datetime) -> list[dict]:
        if self.clock is not None and t < self.clock:
            raise AdviserError(f"professional clock cannot move backwards ({t.isoformat()} < {self.clock.isoformat()})")
        for e in self._bars:
            if e.available_time > t:
                raise AdviserError(f"{e.event_id} available {e.available_time.isoformat()} after barrier {t.isoformat()}")
        self._diag_credit(t)
        self.clock = t
        self.seq += 1
        self._touch()
        self.counters["dispatches"] += 1
        start = len(self.journal)
        bars, sealed, inputs = self._bars, self._sealed, self._inputs
        self._bars, self._sealed, self._inputs = [], [], []
        # structural B episodes alive at dispatch entry: they own this dispatch's opposite-edge box retirement even
        # when an earlier step of the same dispatch (protective / V contact, timers) terminates them
        pre_b = [(s.sid, s.d, s.owner) for s in self.scen.values() if s.family == "B"]

        self._windows(t)
        for kind, x in inputs:
            self._capability(kind, x, t)
        items = self._ingest_minutes(bars, t)
        new_trade = [x for x in items if isinstance(x, Bar)]
        if (self.connection is not None and self.connection["state"] == "AWAITING_FRESH_BAR"
                and any(b.known_at >= _dt(self.connection["since"]) for b in new_trade)):
            self.connection = {"state": "CONNECTED", "since": _iso(t)}
        closes15 = self._ingest_sealed(sealed, t)  # required gaps terminate scenarios/children/guidance here
        self._deps = self._dependencies(t)
        self._landmark_timers(t)
        self._events_tick(t)
        for b in closes15:
            self._mark_broken(b, t)
        # issued guidance: MP-001 certified protective contacts / premise / progress / deadline keep precedence
        self._call_lifecycle(items, closes15, t)
        # (1) timers, staleness, owner/box expiry; (2) admitted intervals against active V / destination
        self._scen_timers(t)
        self._scen_intervals(items, t)
        # newly complete derived revisions are applied only after that contact processing
        if closes15:
            self._box_close_flags(closes15[-1], t, pre_b)
            for b in closes15:
                self._a_close(b, t)
                self._premise_close(b, t)
        self._context_withdrawals(t, closes15)
        if closes15:
            b = closes15[-1]
            self._a_births(b, t)
            self._box_birth(b, t)
            self._bc_geometry(b, t)
            self._capacity_check()
        # (2)-(4) WAIT_PRICE children: timers, cap contacts, new caps, return gates
        returns = self._waits(new_trade, t)
        # (4) structural confirmations and A routing / B-C one-shot evaluation
        confirmations = self._confirmations(new_trade, t)
        # (5) joint selection and issue
        self._select3(confirmations, returns, t)
        # (6) entry reassessment, view, observations
        self._reassess_call(t)
        self._publish_view(t)
        self._publish_observations(t)
        self._diag_update(t)
        return self.journal[start:]

    # ----------------------------------------------------------------------------------------------------------
    # windows / capability inputs
    # ----------------------------------------------------------------------------------------------------------

    def _windows(self, t: datetime) -> None:
        es, ee = self.cfg.eval_start, self.cfg.eval_end
        if es is None:
            return
        if self.window == "WARMUP" and t >= es:
            pending = sorted(s.eid for s in self.scen.values() if s.entry in ("PENDING", "WAIT"))
            cleared = {"entry_attempts": pending, "scenarios_kept_as_warmup_context": sorted(self.scen),
                       "call": self.call.cid if self.call else None, "box_kept": self.box.bid if self.box else None,
                       "latch": dict(self.latch), "box_token": self.box_token}
            for s in sorted(self.scen.values(), key=lambda s: s.sid):
                if s.entry in ("PENDING", "WAIT"):
                    self._entry_end(s, "CLEARED", "CLEARED", "EVALUATION_START_CLEARS_PENDING_ENTRY", t)
            if self.call is not None:
                self._terminate(self.call, "UNASSESSABLE", "EVALUATION_START_CLEARS_WARMUP_CALL", t)
            self.window = "EVALUATION"
            self.boundary["evaluation_start"] = {"at": _iso(t), "cleared": cleared,
                                                 "warmup_calls": self.counters["calls_issued_warmup"],
                                                 "note": "structural warmup scenarios remain labelled context; "
                                                         "their pending entry attempts were removed"}
            self._touch()
        if self.window == "EVALUATION" and ee is not None and t >= ee:
            self.window = "TAIL"
            for w in sorted(self.waits.values(), key=lambda w: w.sid):
                self._entry_end(self.scen[w.sid], "TERMINAL", "TERMINAL", "EVALUATION_WINDOW_ENDED", t)
            self.boundary["evaluation_end"] = {"at": _iso(t), "open_call": self.call.cid if self.call else None,
                                               "active_scenarios": sorted(self.scen)}

    def _capability(self, kind: str, x: Any, t: datetime) -> None:
        super()._capability(kind, x, t)
        if kind == "origin" and self.origin == sc.Origin.LIVE.value:
            for s in self.scen.values():
                s.pre_live = True
            for w in sorted(self.waits.values(), key=lambda w: w.sid):
                self._entry_end(self.scen[w.sid], "TERMINAL", "TERMINAL",
                                "CONFIRMED_BEFORE_LIVE_ACTIVATION_NOT_LIVE_ADVICE", t)

    def _dislocation_update(self) -> None:
        """MP-001 §7 dislocation (preserved by MP-002), each matched slot processed ONCE per pair: baseline = median
        |b| of the previous 60 contiguous matched complete slots, current slot excluded. (The v0.2 implementation
        re-processes the older retained slot at every dispatch, which resets its baseline so it never reaches 60
        slots; v0.2 keeps that behaviour unchanged as the frozen baseline.)"""
        if not self.slot_px:
            return
        slots = sorted(self.slot_px)
        keep = slots[-2:]
        for slot in slots:
            px = self.slot_px[slot]
            if "trade" not in px:
                continue
            for pair, ref in (("TRADE_MARK", "mark"), ("TRADE_INDEX", "index")):
                st = self.disl[pair]
                last = st["last_slot"]
                if ref not in px or (last is not None and datetime.fromisoformat(slot) <= datetime.fromisoformat(last)):
                    continue
                r = Decimal(px[ref])
                if r <= 0:
                    st["status"] = "UNAVAILABLE"
                    continue
                b = div(10000 * (Decimal(px["trade"]) - r), r)
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

    def _active_refs(self) -> set[str]:
        """v0.3: a call's limiting landmark is retained as a frozen audit copy inside the call only; it never keeps a
        landmark eligible past its MP-001 age/capacity retirement, so no cost-dependent call can change the
        structural zone set seen by other scenarios (MP-002 §3 normalized structural lineage)."""
        return set()

    def _required_gap(self, h: str, rec: dict, t: datetime) -> None:
        reason = f"REQUIRED_GAP_{h}:{rec['record_id']}:{rec['status']}"
        if h == "15m":
            start = _dt(rec["interval_start"])
            self.s15 = None
            self.phase = {**self.phase, "phase": "UNAVAILABLE", "dir": None, "since": t, "prev": self.phase["phase"]}
            self.pending_pivots = [p for p in self.pending_pivots if p["horizon"] != "15m"]
            if self.call is not None and self.call.thesis == "ONGOING":
                self.call.coverage_loss_from = start
                self._terminate(self.call, "UNASSESSABLE", reason, t)
            for s in sorted(self.scen.values(), key=lambda s: s.sid):
                self._scen_end(s, "UNASSESSABLE", reason, t, coverage_from=start)
            self.a_owner = {"1": None, "-1": None}
            if self.box is not None:
                self._retire_box(reason, t)
            self.latch = {"1": "INIT", "-1": "INIT"}
            self.box_token = "INIT"
            self.comp_prev = None
        else:
            self.ctx = {**self.ctx, "ctx": "UNAVAILABLE", "since": t}
            self.pending_pivots = [p for p in self.pending_pivots if p["horizon"] != "1h"]
        self._touch()

    # ----------------------------------------------------------------------------------------------------------
    # structural scenarios: lifecycle helpers
    # ----------------------------------------------------------------------------------------------------------

    def _owner_active(self, s: Scen) -> bool:
        own = self.a_owner.get(str(s.d))
        return s.family == "A" and own is not None and own["sid"] == s.sid

    def _release_owner(self, d: int, reason: str, t: datetime) -> None:
        own = self.a_owner.get(str(d))
        if own is None:
            return
        self.a_owner[str(d)] = None
        self.counters["v3"]["owner_releases"][reason.split(":")[0]] = \
            self.counters["v3"]["owner_releases"].get(reason.split(":")[0], 0) + 1
        s = self.scen.get(own["sid"])
        if s is not None:  # the confirmed scenario outlives its discovery owner (no new entry budget)
            self._emit_scen(s, "OWNER_RELEASE", reason, t)
        self._touch()

    def _scen_end(self, s: Scen, state: str, reason: str, t: datetime, coverage_from: datetime | None = None) -> None:
        """Structural terminal. Independent of call/entry; blocks new entry, retires linked ongoing guidance with the
        underlying reason (coverage loss -> UNASSESSABLE with its origin, otherwise RETIRED SCENARIO_TERMINAL)."""
        if s.sid not in self.scen:
            return
        del self.scen[s.sid]
        owner = self._owner_active(s)
        if owner:
            self.a_owner[str(s.d)] = None
            self.counters["v3"]["owner_releases"][f"SCENARIO_{state}"] = \
                self.counters["v3"]["owner_releases"].get(f"SCENARIO_{state}", 0) + 1
        key = f"{s.family}:{state}:{reason.split(':')[0]}"
        self.counters["v3"]["scenario_end"][key] = self.counters["v3"]["scenario_end"].get(key, 0) + 1
        self._emit_scen(s, "TERMINAL", reason, t, terminal=state, released=owner)
        if s.entry in ("PENDING", "WAIT"):
            self._entry_end(s, "TERMINAL", "TERMINAL", f"SCENARIO_TERMINAL:{state}:{reason.split(':')[0]}", t)
        elif s.entry == "ISSUED" and self.call is not None and self.call.cid == s.call_id \
                and self.call.thesis == "ONGOING":
            call = self.call
            call.scenario_terminal = f"{state}:{reason}"
            if coverage_from is not None or reason.startswith(COVERAGE_REASONS):
                call.coverage_loss_from = coverage_from or self.last_1m_end
                self._terminate(call, "UNASSESSABLE", f"SCENARIO_TERMINAL:{state}:{reason}", t)
            else:
                self._terminate(call, "RETIRED", f"SCENARIO_TERMINAL:{state}:{reason}", t)
        self._touch()

    def _capacity_check(self) -> None:
        for d in (1, -1):
            n = sum(1 for s in self.scen.values() if s.family == "A" and s.d == d)
            if n > A_CAPACITY_PER_DIRECTION:
                raise AdviserError(f"SCENARIO_CAPACITY_INVARIANT: {n} active A {dname(d)} scenarios > "
                                   f"{A_CAPACITY_PER_DIRECTION} (never an economic eviction)")
        n = sum(1 for s in self.scen.values() if s.family in "BC")
        if n > BC_CAPACITY:
            raise AdviserError(f"SCENARIO_CAPACITY_INVARIANT: {n} active B/C scenarios > {BC_CAPACITY}")

    def _scen_timers(self, t: datetime) -> None:
        if self.box is not None and self.box.expires_at <= t:
            self._retire_box("BOX_EXPIRY", t)
        for d in (1, -1):
            own = self.a_owner.get(str(d))
            if own is not None and _dt(own["expires"]) <= t:
                self._release_owner(d, "ORIGINAL_SETUP_EXPIRY", t)
        # monitoring of an armed/confirmed scenario's V/destination/premise needs fresh 1m and 15m trade evidence
        # (1h staleness withdraws unconfirmed scenarios through the context gates; it is not needed after confirmation)
        m1_stale = self.last_1m is not None and not self.ready_1m(t)
        m15_stale = bool(self.m15) and not self.ready_15m(t)
        for s in sorted(list(self.scen.values()), key=lambda s: s.sid):
            if s.status in ("WATCH", "ARMED"):
                if s.setup_deadline <= t:
                    self._scen_end(s, "EXPIRED", "ORIGINAL_SETUP_DEADLINE", t)
                    continue
            elif t >= s.conf_deadline:
                self._scen_end(s, "TIME_EXPIRED", "CONFIRMED_HARD_DEADLINE", t)
                continue
            if s.status in ("ARMED", "CONFIRMED") and m1_stale:
                self._scen_end(s, "UNASSESSABLE", "REQUIRED_TRADE_1M_STALE", t, coverage_from=self.last_1m_end)
            elif s.status in ("ARMED", "CONFIRMED") and m15_stale:
                self._scen_end(s, "UNASSESSABLE", "REQUIRED_INPUT_STALE:TRADE_15M", t, coverage_from=self.last_1m_end)

    def _scen_progress(self, s: Scen, t: datetime) -> bool:
        """Confirmed-scenario stalled test: max favorable complete-minute close displacement from the confirmation
        close over wholly post-confirmation minutes ending <= progress_at, against 0.5 confirmation-time S15."""
        s.progress_done = True
        if s.conf_s15 is None:
            self._scen_end(s, "UNASSESSABLE", "CONFIRMATION_SCALE_UNAVAILABLE_FOR_PROGRESS", t)
            return True
        if s.max_fav_t is None or s.max_fav_t < self.p.progress_min_scale * s.conf_s15:
            self._scen_end(s, "STALLED", "SCENARIO_PROGRESS_BELOW_HALF_SCALE", t)
            return True
        return False

    def _scen_intervals(self, items: list, t: datetime) -> None:
        """Newly admitted complete intervals against each scenario's V/destination ACTIVE AT THE INTERVAL START
        (actual publication times); straddling publications are unassessable; post-arm missing minutes are coverage
        loss. Confirmed scenarios also accumulate progress extrema on wholly post-confirmation closes."""
        for m in items:
            for s in sorted(list(self.scen.values()), key=lambda s: s.sid):
                if s.status not in ("ARMED", "CONFIRMED") or not s.v_hist:
                    continue
                first = _dt(s.v_hist[0][0])
                if isinstance(m, tuple):
                    if m[1] + MINUTE > first:
                        self._scen_end(s, "UNASSESSABLE", f"REQUIRED_MONITORING_GAP:{m[2]}", t, coverage_from=m[1])
                    continue
                if m.end <= first:
                    continue  # wholly before the arm publication
                _, h_t, l_t, c_t = tbar(m, s.d)
                hit_d = s.dest_t is not None and h_t >= s.dest_t
                if m.start < first:  # straddles the arm publication
                    if l_t <= Decimal(s.v_hist[0][1]) or hit_d:
                        self._scen_end(s, "UNASSESSABLE", "ARM_CONTACT_TIME_AMBIGUOUS", t)
                    continue
                inside = [Decimal(v) for since, v in s.v_hist if m.start < _dt(since) < m.end]
                v_start = Decimal(next(v for since, v in reversed(s.v_hist) if _dt(since) <= m.start))
                if inside and (l_t <= max([v_start] + inside) or hit_d):
                    self._scen_end(s, "UNASSESSABLE", "LEVEL_REVISION_CONTACT_TIME_AMBIGUOUS", t)
                    continue
                hit_v = l_t <= v_start
                if s.status == "CONFIRMED" and not s.progress_done and m.end > s.progress_at:
                    if self._scen_progress(s, t):  # every minute ending <= progress_at was already processed
                        continue
                if hit_v and hit_d:
                    self._scen_end(s, "UNASSESSABLE", f"DESTINATION_AND_INVALIDATION_SAME_INTERVAL:{m.rid}", t)
                    continue
                if hit_v:
                    self._scen_end(s, "INVALIDATED", f"V_CONTACT:{m.rid}", t)
                    continue
                if hit_d:
                    self._scen_end(s, "DESTINATION_REACHED", f"DESTINATION_CONTACT:{m.rid}", t)
                    continue
                if s.status == "CONFIRMED" and m.start >= s.conf_at:
                    s.last_end = m.end
                    if m.end <= s.progress_at:
                        fav = c_t - s.conf_close_t
                        s.max_fav_t = fav if s.max_fav_t is None else max(s.max_fav_t, fav)
                elif s.status == "CONFIRMED":
                    s.last_end = max(s.last_end or m.end, m.end)  # straddling confirmation: freshness only
        # timer-based progress check once the minute ending at the check time was processed in this dispatch (a
        # check minute that never arrives is caught by the stale/gap rules, never guessed)
        for s in sorted([x for x in self.scen.values() if x.status == "CONFIRMED"], key=lambda x: x.sid):
            if (not s.progress_done and t >= s.progress_at and s.last_end is not None
                    and s.last_end >= s.progress_at.replace(second=0, microsecond=0)):
                self._scen_progress(s, t)

    # ----------------------------------------------------------------------------------------------------------
    # 15m close processing (preserved MP-001 setup rules on structural scenarios)
    # ----------------------------------------------------------------------------------------------------------

    def _owner_zones(self, d: int, t: datetime) -> list[tuple[str, Decimal, Decimal, dict]]:
        zones = []
        for s in self.scen.values():
            # A's own B zone: eligible only during structural-owner life and until its 15m far-edge break
            if s.family == "A" and s.d == d and s.b_t is not None and not s.b_broken and self._owner_active(s):
                zones.append((f"{s.sid}#B", s.b_t, s.z, {"landmark_id": f"{s.sid}#B", "type": "IMPULSE_B",
                                                         "price": str(s.b_t * d), "zone_halfwidth": str(s.z),
                                                         "source": ",".join(s.sources),
                                                         "created_at": _iso(s.born_at),
                                                         "age_minutes": str(int((t - s.born_at) / MINUTE))}))
        bx = self.box
        if bx is not None and not bx.broken["U" if d > 0 else "L"]:
            _, u_t, _ = bx.edges_t(d)
            zones.append((f"{bx.bid}#{'U' if d > 0 else 'L'}", u_t, bx.z,
                          {"landmark_id": f"{bx.bid}#{'U' if d > 0 else 'L'}", "type": "BOX_UPPER" if d > 0 else "BOX_LOWER",
                           "price": str(u_t * d), "zone_halfwidth": str(bx.z), "source": ",".join(bx.sources),
                           "created_at": _iso(bx.created_at), "age_minutes": str(int((t - bx.created_at) / MINUTE))}))
        return zones

    def _zones(self, d: int, t: datetime) -> list[tuple]:
        """Eligible opposing zones (near', far', info, created, id), deterministically ordered by (near, created, id)."""
        return sorted(self._opposing(d, t, self._owner_zones(d, t)), key=lambda z: (z[0], z[3], z[4]))

    def _box_close_flags(self, b: Bar, t: datetime, pre_b: list[tuple[str, int, str | None]] | None = None) -> None:
        """B cancellations / premise failures and the opposite-edge retirement, derived together from the
        PRE-dispatch structural B episodes ``pre_b`` (sid, direction, owner) captured at dispatch entry (any status:
        rejected child entries never change box retirement). An episode terminated earlier in this dispatch (e.g. by
        a protective V contact, which keeps precedence) still owns the retirement predicate of this close; its own
        cancellation is moot. Episodes already dead before the dispatch are not in ``pre_b``."""
        bx = self.box
        if bx is None:
            return
        if pre_b is None:
            pre_b = [(s.sid, s.d, s.owner) for s in self.scen.values() if s.family == "B"]
        ends: list[tuple[Scen, str, str]] = []
        retire = None
        for sid, d, owner in sorted(pre_b):
            if owner != bx.bid:
                continue
            l_t, u_t, _ = bx.edges_t(d)
            c_t = tbar(b, d)[3]
            s = self.scen.get(sid)
            if s is not None and c_t < u_t - bx.z:
                ends.append((s, "WITHDRAWN", "RETURNED_INSIDE_BEFORE_RETEST") if s.status != "CONFIRMED" else
                            (s, "PRICE_PREMISE_FAILED", f"15M_CLOSE_BEYOND_U_MINUS_Z:{b.rid}"))
            if c_t < l_t - bx.z:
                retire = f"OPPOSITE_FAR_EDGE_CLOSE_DURING_B_{dname(d)}:{b.rid}"
        for s, state, reason in ends:
            self._scen_end(s, state, reason, t)
        if retire is not None:
            self._retire_box(retire, t)

    def _a_close(self, b: Bar, t: datetime) -> None:
        p = self.p
        for s in sorted([x for x in self.scen.values() if x.family == "A"], key=lambda x: x.sid):
            if s.born_at >= t:
                continue
            o_t, h_t, l_t, c_t = tbar(b, s.d)
            if self._owner_active(s) and c_t > s.b_t + s.z:
                s.b_broken = True  # the impulse destination zone is BROKEN by a close beyond its far edge
            if s.status == "CONFIRMED":
                continue  # no post-confirmation anchor revision; premise handled separately
            s.bars_seen += 1
            if s.prev_close_t is not None and c_t < s.prev_close_t:
                s.lower_close = True
            s.prev_close_t = c_t
            if s.status == "WATCH" and h_t > s.b_t + s.z:
                self._scen_end(s, "EXPIRED", "SPENT_HIGH_BEYOND_B_BEFORE_REACTION", t)
                continue
            if c_t <= s.a_t + s.z:
                self._scen_end(s, "WITHDRAWN", "CLOSE_AT_OR_BEYOND_A_PLUS_ZONE", t)
                continue
            if s.status == "WATCH":
                if s.r_t is None or l_t <= s.r_t:
                    s.r_t, s.anchor, s.anchor_h_t = l_t, b.rid, h_t
                reaction = (s.lower_close and s.r_t < s.b_t - p.a_reaction_min * s.s15 and s.r_t > s.a_t + s.z)
                if reaction:
                    if self._a_context_ok(s, t):
                        s.k_t, s.v_t = s.anchor_h_t, s.r_t - s.z
                        s.status, s.arm_at, s.arm_seq = "ARMED", t, self.seq
                        s.v_hist = [[_iso(t), str(s.v_t)]]
                        self.counters["armed"]["A"] += 1
                        self._emit_scen(s, "ARM", None, t)
                elif s.bars_seen >= p.a_reaction_max_bars:
                    self._scen_end(s, "EXPIRED", "NO_QUALIFYING_REACTION_WITHIN_8_BARS", t)
            elif l_t <= s.r_t and l_t > s.a_t + s.z:
                s.r_t, s.anchor, s.anchor_h_t = l_t, b.rid, h_t
                s.k_t, s.v_t = h_t, l_t - s.z
                s.arm_at, s.arm_seq = t, self.seq
                s.v_hist = (s.v_hist + [[_iso(t), str(s.v_t)]])[-16:]
                self._emit_scen(s, "REVISE", "LOWER_CLEAN_REACTION_REANCHOR", t)

    def _premise_close(self, b: Bar, t: datetime) -> None:
        """Confirmed-scenario family price-premise failure on a newly complete 15m close after confirmation:
        A below impulse A, B below U-z (box gone), C below L-z."""
        for s in sorted([x for x in self.scen.values() if x.status == "CONFIRMED"], key=lambda x: x.sid):
            if b.end <= s.conf_at:
                continue
            c_t = tbar(b, s.d)[3]
            level = s.a_t if s.family == "A" else s.premise_t
            if level is not None and c_t < level:
                self._scen_end(s, "PRICE_PREMISE_FAILED", f"15M_CLOSE_BEYOND_PREMISE:{b.rid}", t)

    def _context_withdrawals(self, t: datetime, closes15: list[Bar]) -> None:
        for s in sorted(list(self.scen.values()), key=lambda x: x.sid):
            if s.status == "CONFIRMED":
                continue  # after confirmation context change is counterevidence only
            if not self._context_ok(s, t):
                self._scen_end(s, "WITHDRAWN", f"CONTEXT_OR_ADVERSE_EXPANSION:{self.context(t)}/"
                                               f"{self.phase_now(t)}:{self.phase['dir']}", t)
        for b in closes15:
            for s in sorted(list(self.scen.values()), key=lambda x: x.sid):
                if s.family == "C" and s.status != "CONFIRMED" and s.premise_t is not None \
                        and tbar(b, s.d)[3] < s.premise_t:
                    self._scen_end(s, "WITHDRAWN", "CLOSE_BEYOND_LOWER_FAR_EDGE_BEFORE_TRIGGER", t)

    def _a_births(self, b: Bar, t: datetime) -> None:
        """MP-002 B1 renewal: the latch reads 'pending' as an OCCUPIED discovery owner; release (processed earlier
        in this dispatch) precedes this Q_A observation, so a false here can reset and a true cannot replace."""
        if self.window == "TAIL":
            return
        for d in (1, -1):
            key = str(d)
            qa = self._qa(d, t)
            self.qa_last[key] = qa
            if qa is None:
                continue
            occupied = self.a_owner.get(key) is not None
            st = self.latch[key]
            if qa is False:
                if not occupied and st == "NEED_FALSE":
                    self.latch[key] = "READY"
                elif st == "INIT":
                    self.latch[key] = "READY"
                continue
            if occupied:
                self.counters["a_true_while_pending"] += 1
                continue
            if st in ("INIT", "READY"):
                self._new_a(d, b, t, renewal=("FIRST_ASSESSABLE_TRUE" if st == "INIT" else
                                              "FALSE_AT_OR_AFTER_RELEASE_TO_TRUE"))
                self.latch[key] = "NEED_FALSE"

    def _new_a(self, d: int, b: Bar, t: datetime, renewal: str) -> None:
        p = self.p
        src = list(self.m15)[-p.a_source_bars:]
        z = self._zone()
        lows = [tbar(x, d)[2] for x in src]
        highs = [tbar(x, d)[1] for x in src]
        sid = f"A{dname(d)[0]}-{_iso(b.start)}-{_h(self.cfg.method.rules_sha256, self.cfg.instrument, 'A', d, b.rid)}"
        s = Scen(sid=sid, family="A", d=d, owner=sid, born_at=t, born_seq=self.seq, sources=[x.rid for x in src],
                 setup_deadline=t + p.a_lifetime, s15=self.s15, z=z, a_t=min(lows), b_t=max(highs),
                 prev_close_t=tbar(b, d)[3], renewal=renewal, dest_t=max(highs), dest_type="IMPULSE_B")
        self.scen[sid] = s
        self.a_owner[str(d)] = {"sid": sid, "expires": _iso(s.setup_deadline)}
        self.counters["episodes"]["A"][dname(d)] += 1
        self._emit_scen(s, "BIRTH", renewal, t)
        self._touch()

    # -- box -----------------------------------------------------------------------------------------------------

    def _retire_box(self, reason: str, t: datetime) -> None:
        bx = self.box
        if bx is None:
            return
        for s in sorted(list(self.scen.values()), key=lambda x: x.sid):
            # retirement invalidates the unissued structural premise; a confirmed narrative keeps its frozen refs
            if s.owner == bx.bid and s.status != "CONFIRMED":
                self._scen_end(s, "WITHDRAWN" if "EXPIR" not in reason else "EXPIRED", f"BOX_RETIRED:{reason}", t)
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
            if c_t > u_t + bx.z and not bx.used["B" + key]:
                bx.used["B" + key] = True  # structural discovery flag: consumed by the first structural birth
                s = self._new_bc("B", d, bx, b, t, t + self.p.b_lifetime)
                s.dest_t, s.dest_type, s.premise_t = u_t + (u_t - l_t), "PROJECTED_BOX_WIDTH", u_t - bx.z
                ctx = ctx_t(self.context(t), d)
                self._emit_scen(s, "BIRTH", None, t)
                if ctx in ("DOWN", "UNAVAILABLE"):
                    self._scen_end(s, "WITHDRAWN", f"CONTEXT_FORBIDDEN_AT_BIRTH:{ctx}", t)
            if lo_t < l_t - bx.z and c_t > l_t + bx.z and c_t < m_t and not bx.used["C" + key]:
                if both:
                    self.counters["c_both_edge_ambiguous"] += 1
                    continue
                if h_t > u_t + bx.z:
                    continue
                bx.used["C" + key] = True
                s = self._new_bc("C", d, bx, b, t, t + self.p.c_lifetime)
                s.dest_t, s.dest_type, s.premise_t = m_t, "FROZEN_MIDPOINT", l_t - bx.z
                self._emit_scen(s, "BIRTH", None, t)
                ctx = self.context(t)
                ph = self.phase_now(t)
                if ctx != "BALANCED":
                    self._scen_end(s, "WITHDRAWN", f"CONTEXT_NOT_BALANCED_AT_BIRTH:{ctx}", t)
                elif ph == "EXPANSION":
                    self._scen_end(s, "WITHDRAWN", f"DIRECTIONAL_EXPANSION_AT_BIRTH:{self.phase['dir']}", t)
                else:
                    s.k_t, s.v_t = c_t, lo_t - bx.z
                    s.status, s.arm_at, s.arm_seq = "ARMED", t, self.seq
                    s.v_hist = [[_iso(t), str(s.v_t)]]
                    self.counters["armed"]["C"] += 1
                    self._emit_scen(s, "ARM", None, t)
        for s in sorted(list(self.scen.values()), key=lambda x: x.sid):
            if s.family != "B" or s.status != "WATCH" or s.owner != bx.bid or s.born_at >= t:
                continue
            l_t, u_t, _ = bx.edges_t(s.d)
            o_t, h_t, lo_t, c_t = tbar(b, s.d)
            s.retest_seen += 1
            if u_t - bx.z <= lo_t <= u_t + bx.z and c_t > u_t and lo_t > l_t:
                if self._b_context_ok(s, t):
                    s.k_t, s.v_t = max(u_t + self.tick, c_t), lo_t - bx.z
                    s.status, s.arm_at, s.arm_seq = "ARMED", t, self.seq
                    s.v_hist = [[_iso(t), str(s.v_t)]]
                    self.counters["armed"]["B"] += 1
                    self._emit_scen(s, "ARM", None, t)
            elif s.retest_seen >= self.p.b_retest_bars:
                self._scen_end(s, "EXPIRED", "NO_RETEST_WITHIN_4_BARS", t)

    def _new_bc(self, fam: str, d: int, bx, b: Bar, t: datetime, life_end: datetime) -> Scen:
        sid = (f"{fam}{dname(d)[0]}-{_iso(b.start)}-"
               f"{_h(self.cfg.method.rules_sha256, self.cfg.instrument, fam, d, bx.bid, b.rid)}")
        s = Scen(sid=sid, family=fam, d=d, owner=bx.bid, born_at=t, born_seq=self.seq, sources=[b.rid],
                 setup_deadline=min(bx.expires_at, life_end), s15=bx.s15, z=bx.z)
        self.scen[sid] = s
        self.counters["episodes"][fam][dname(d)] += 1
        self._touch()
        return s

    # ----------------------------------------------------------------------------------------------------------
    # confirmation and child entry routing
    # ----------------------------------------------------------------------------------------------------------

    def _confirmations(self, minutes: list[Bar], t: datetime) -> list[tuple[Scen, Bar]]:
        out: list[tuple[Scen, Bar]] = []
        if not minutes:
            return out
        for s in sorted([x for x in self.scen.values() if x.status == "ARMED"], key=lambda x: x.sid):
            for m in minutes:
                if s.sid not in self.scen:
                    break
                if m.start < s.arm_at or not self.ready_1m(t):
                    continue  # straddling-arm minutes cannot confirm (their contacts were handled above)
                _, h_t, l_t, c_t = tbar(m, s.d)
                if c_t >= s.k_t + self.tick * self.p.trigger_ticks:
                    if l_t <= s.v_t:  # unreachable: a certified V contact already invalidated the scenario
                        raise AdviserError(f"{s.sid}: confirmation minute {m.rid} touches V after contact processing")
                    self._confirm(s, m, t)
                    out.append((s, m))
                    break
        return out

    def _confirm(self, s: Scen, m: Bar, t: datetime) -> None:
        hard = self.p.hard(s.family)
        s.status, s.conf_at, s.conf_seq = "CONFIRMED", t, self.seq
        s.conf_close_t, s.conf_s15, s.conf_minute = tbar(m, s.d)[3], self.s15, m.rid
        s.conf_deadline, s.progress_at = t + hard, t + _scaled(hard, self.p.progress_fraction)
        s.last_end = m.end
        self.counters["triggered"][s.family] += 1
        self.counters["v3"]["confirmations"][f"{s.family}_{dname(s.d)}"] = \
            self.counters["v3"]["confirmations"].get(f"{s.family}_{dname(s.d)}", 0) + 1
        self._emit_scen(s, "CONFIRM", m.rid, t)

    def _target3(self, s: Scen, price: Decimal, t: datetime) -> dict[str, Any]:
        """Conservative target at a price (MP-001 §3 resolver on the eligible zone set after all newly complete
        updates) with the COMPLETE containing set and the deterministic attribution (first by near, created, id)."""
        d = s.d
        p_t = price * d
        zones = self._zones(d, t)
        containing = [z for z in zones if z[0] <= p_t <= z[1]]
        ahead = [z for z in zones if z[0] > p_t]
        best = ahead[0] if ahead else None
        out: dict[str, Any] = {"containing": [_zone_info(z, d) for z in containing], "selected": None,
                               "t_t": None, "type": "NONE", "limiting": None, "reason": None}
        if containing:
            out["selected"] = _zone_info(containing[0], d)
            out["reason"] = "AT_OPPOSING_AREA"
            out["limiting"] = containing[0][2]
            return out
        if s.family == "A":
            if best is None:
                out["reason"] = "NO_TARGET"
                return out
            out.update(t_t=best[0], type="LANDMARK", limiting=best[2])
            return out
        bx = self.box
        if s.family == "B":
            l_t, u_t, _ = bx.edges_t(d)
            proj = u_t + (u_t - l_t)
            if best is not None and best[0] <= proj:
                out.update(t_t=best[0], type="LANDMARK", limiting=best[2])
            else:
                out.update(t_t=proj, type="PROJECTED_BOX_WIDTH")
            return out
        _, _, m_t = bx.edges_t(d)
        if best is not None and best[0] < m_t:
            out.update(t_t=best[0], type="LANDMARK", limiting=best[2])
        else:
            out.update(t_t=m_t, type="MIDPOINT")
        return out

    def _real_levels(self, d: int, v_t: Decimal, t_t: Decimal | None) -> tuple[Decimal, Decimal | None]:
        """V rounded away from entry, T toward it (market prices)."""
        v_real = round_down(v_t, self.tick) * d if d > 0 else -round_down(v_t, self.tick)
        if t_t is None:
            return v_real, None
        t_real = round_down(t_t, self.tick) * d if d > 0 else -round_down(t_t, self.tick)
        return v_real, t_real

    def _corridor(self, s: Scen, v_real: Decimal, t_real: Decimal) -> tuple[Decimal, Decimal] | None:
        """Immutable LONG corridor [max(ceil R, V+tick), min(floor K_trigger, T-tick)]; SHORT is the price-axis
        reflection rounded inward in market prices. Empty is never reordered."""
        d, tick = s.d, self.tick
        lo = max(_tick_ceil(s.r_t, tick), v_real * d + tick)
        hi = min(_tick_floor(s.k_t, tick), t_real * d - tick)
        return None if hi < lo else (lo, hi)

    def _nonselection(self, s: Scen, t: datetime, price_t: Decimal | None, zones_d: list) -> list[str]:
        out: list[str] = []
        if self.window == "TAIL" or (self.cfg.eval_end is not None and t >= self.cfg.eval_end):
            out.append("EVALUATION_WINDOW_ENDED")
        if s.pre_live and self.origin == sc.Origin.LIVE.value:
            out.append("ARMED_BEFORE_LIVE_ACTIVATION")
        if self.origin == sc.Origin.RECONSTRUCTED.value:
            out.append("RECONSTRUCTED_CATCH_UP_NO_NEW_CALL")
        out += self.connection_blockers()
        out += self._common_blockers(t)
        if price_t is not None and any(z[0] <= price_t <= z[1] for z in zones_d):
            out.append("EXECUTION_PRICE_INSIDE_OPPOSING_ZONE")
        return out

    def _route_a(self, s: Scen, m: Bar, t: datetime) -> dict | None:
        """MP-002 §5 exhaustive routing at the first clean confirmation. Returns an IMMEDIATE selection candidate,
        or None after recording WAIT_PRICE / a terminal reason. Every blocker is computed and recorded; the table
        fixes control-flow precedence."""
        p, d, tick = self.p, s.d, self.tick
        tc = m.c
        tg = self._target3(s, tc, t)
        v_real, t_real = self._real_levels(d, s.v_t, tg["t_t"])
        h_t = tbar(m, d)[1]
        hard = s.conf_at + p.hard("A")
        geom: dict[str, str | None] = {
            "R": _s(s.r_t * d), "K_trigger": _s(s.k_t * d), "V": _s(v_real), "T_confirm": _s(t_real),
            "T_current": _s(t_real), "S15": _s(self.s15), "tick": _s(tick), "confirmation_close": _s(tc),
            "target_type": tg["type"], "K_cost_fixed_historical": _s(p.hist_k_bps)}
        clocks = {"confirmed_at": _iso(s.conf_at), "setup_expiry": _iso(s.setup_deadline), "hard_deadline": _iso(hard),
                  "scenario_progress_at": _iso(s.progress_at)}
        diag: dict[str, str | None] = {"in_D": "false", "exclusion": None}
        # all blockers (recorded); precedence below
        structural = [tg["reason"]] if tg["reason"] else []
        target_contact = t_real is not None and h_t >= t_real * d
        prereq: list[str] = []
        if self.s15 is None:
            prereq.append("SCALE_UNAVAILABLE")
        if t_real is not None and not v_real * d < t_real * d:
            prereq.append("INVALID_GEOMETRY")
        price, source, k, qb = self._side_price(d, t)
        if self.cfg.profile.execution == Execution.HISTORICAL_BASE:
            price, source = tc, "MODELED_CONFIRMATION_COMPLETE_MINUTE_CLOSE"
        zones_d = self._zones(d, t)
        nonsel = self._nonselection(s, t, price * d if price is not None and
                                    self.cfg.profile.execution == Execution.LIVE_QUOTED else None, zones_d) + qb
        if hard - t < timedelta(minutes=p.residual_min["A"]):
            nonsel.append("TOO_LATE")
        # immediate I0 (exact v0.2 width) and the diagnostic corridor for every evaluable confirmation
        imm: list[str] = []
        area = None
        chk = None
        corridor = econ = econ_fixed = None
        if not structural and not prereq and t_real is not None:
            area = geo.structural_area(d, tc, v_real, t_real, self.s15, p.area_scale, tick)
            geom["I0"] = None if area is None else f"{area[0]}..{area[1]}"
            if area is None:
                imm.append("EMPTY_STRUCTURAL_AREA")
            if price is not None and k is not None:
                if area is not None and not geo.in_area(price, area):
                    imm.append("PRICE_OUTSIDE_STRUCTURAL_AREA")
                chk = geo.predicate(d, price, v_real, t_real, k, p.rr_min)
                if not chk.ok:
                    imm.append(chk.reason)
            cor_t = self._corridor(s, v_real, t_real)
            if cor_t is not None:
                corridor = _market(cor_t[0], cor_t[1], d)
                econ_fixed = geo.admissible_bounds(d, corridor, v_real, t_real, p.hist_k_bps, p.rr_min, tick)
                if k is not None:
                    econ = geo.admissible_bounds(d, corridor, v_real, t_real, k, p.rr_min, tick)
            geom.update(corridor=_rng(corridor), economic_current=_rng(econ), economic_fixed_k=_rng(econ_fixed),
                        K_cost=_s(k), price=_s(price), price_source=source,
                        G=_s(chk.g if chk else None), Q=_s(chk.q if chk else None),
                        margin=_s(chk.margin if chk else None))
            diag = {"in_D": "true", "exclusion": None, "corridor_geometric_empty": str(corridor is None).lower(),
                    "corridor_fixed_k_economic_empty": str(corridor is None or econ_fixed is None).lower(),
                    "in_N": str(corridor is None or econ_fixed is None).lower()}
        else:
            diag["exclusion"] = ("INSIDE_ZONE" if "AT_OPPOSING_AREA" in structural else
                                 "NO_TARGET" if "NO_TARGET" in structural else "MISSING_GEOMETRY")
        all_blockers = structural + (["PRE_ENTRY_TARGET_CONTACT"] if target_contact else []) + prereq + nonsel + imm
        common = {"geometry": geom, "containing": tg["containing"], "selected": tg["selected"],
                  "limiting": tg["limiting"], "clocks": clocks, "diagnostic": diag, "blockers": all_blockers}
        self._a_diag_counts(diag, s)
        if structural:
            self._entry_end(s, "TERMINAL", "TERMINAL", structural[0], t, **common)
            return None
        if target_contact:
            self._entry_end(s, "TERMINAL", "TERMINAL", "PRE_ENTRY_TARGET_CONTACT", t, **common)
            return None
        if prereq:
            self._entry_end(s, "TERMINAL", "TERMINAL", f"UNAVAILABLE_GEOMETRY:{prereq[0]}", t, **common)
            return None
        if nonsel:
            reason = "EXECUTION_UNVERIFIED" if any(b in UNVERIFIED_REASONS for b in nonsel) else nonsel[0]
            self._entry_end(s, "TERMINAL", "TERMINAL", f"NONSELECTION_GATE:{reason}", t, **common)
            return None
        if not imm:
            self.counters["v3"]["routes"]["IMMEDIATE"] += 1
            return {"s": s, "m": m, "mode": "IMMEDIATE", "price": price, "source": source, "k": k, "chk": chk,
                    "geom": {"v": v_real, "t": t_real, "area": area, "type": tg["type"], "limiting": tg["limiting"]},
                    "blockers": [], "rec": common, "ref": tc}
        if not set(imm) <= ROUTABLE:
            self._entry_end(s, "TERMINAL", "TERMINAL", f"IMMEDIATE_INCOMPATIBLE:{imm[0]}", t, **common)
            return None
        if corridor is None:
            self._entry_end(s, "TERMINAL", "TERMINAL", "EMPTY_RETURN_CORRIDOR", t, **common)
            return None
        if econ is None:
            self._entry_end(s, "TERMINAL", "TERMINAL", "NO_ECONOMIC_RETURN_REGION", t, **common)
            return None
        cor_t = self._corridor(s, v_real, t_real)
        w = Wait(sid=s.sid, d=d, conf_at=t, conf_cursor=self.cursor, setup_deadline=s.setup_deadline, hard=hard,
                 v=v_real, t_conf=t_real, cap=t_real,
                 caps=[{"cap": str(t_real), "since": _iso(t), "cursor": str(self.cursor), "zone_id": "T_CONFIRM",
                        "near_edge": str(t_real)}],
                 lo_t=cor_t[0], hi_t=cor_t[1], r=s.r_t * d, k_trigger=s.k_t * d, s15=self.s15, conf_close=tc,
                 seen=sorted(z[4] for z in zones_d))
        self.waits[s.eid] = w
        s.entry = "WAIT"
        self.counters["v3"]["routes"]["RETURN_WAIT"] += 1
        self._emit_entry(s, "WAIT_PRICE", "RETURN", "WAIT_OPEN", "IMMEDIATE_ECONOMIC_FAILURE_RETURN_CORRIDOR_USABLE",
                         t, cap_history=w.caps, **{**common, "blockers": imm})
        self._touch()
        return None

    def _a_diag_counts(self, diag: dict, s: Scen) -> None:
        v = self.counters["v3"]["a_denominators"]
        if self.window != "EVALUATION" or s.entry == "CLEARED":
            return
        v["confirmations"] += 1
        if diag.get("in_D") == "true":
            v["D"] += 1
            if diag.get("in_N") == "true":
                v["N"] += 1
        else:
            v["excluded"][diag["exclusion"]] = v["excluded"].get(diag["exclusion"], 0) + 1

    def _eval_bc(self, s: Scen, m: Bar, t: datetime) -> dict:
        """B/C one-shot entry at confirmation (= trigger): exact v0.2 geometry and gates."""
        p, d = self.p, s.d
        tc = m.c
        tg = self._target3(s, tc, t)
        blockers: list[str] = []
        if self.window == "TAIL" or (self.cfg.eval_end is not None and t >= self.cfg.eval_end):
            blockers.append("EVALUATION_WINDOW_ENDED")
        if s.pre_live and self.origin == sc.Origin.LIVE.value:
            blockers.append("ARMED_BEFORE_LIVE_ACTIVATION")
        if self.origin == sc.Origin.RECONSTRUCTED.value:
            blockers.append("RECONSTRUCTED_CATCH_UP_NO_NEW_CALL")
        blockers += self.connection_blockers()
        geom = None
        v_real, t_real = self._real_levels(d, s.v_t, tg["t_t"])
        if tg["reason"]:
            blockers.append(tg["reason"])
        elif self.s15 is None:
            blockers.append("SCALE_UNAVAILABLE")
        else:
            area = geo.structural_area(d, tc, v_real, t_real, self.s15, p.area_scale, self.tick)
            if area is None:
                blockers.append("EMPTY_STRUCTURAL_AREA")
            geom = {"v": v_real, "t": t_real, "area": area, "type": tg["type"], "limiting": tg["limiting"]}
        blockers += self._common_blockers(t)
        price, source, k, qb = self._side_price(d, t)
        blockers += qb
        chk = None
        if geom is not None and geom["area"] is not None and price is not None:
            if not geo.in_area(price, geom["area"]):
                blockers.append("PRICE_OUTSIDE_STRUCTURAL_AREA")
            chk = geo.predicate(d, price, geom["v"], geom["t"], k, p.rr_min)
            if not chk.ok:
                blockers.append(chk.reason)
        rec = {"geometry": {"V": _s(v_real), "T_confirm": _s(t_real), "S15": _s(self.s15), "confirmation_close": _s(tc),
                            "I0": None if geom is None or geom["area"] is None else
                            f"{geom['area'][0]}..{geom['area'][1]}", "K_cost": _s(k), "price": _s(price),
                            "price_source": source, "G": _s(chk.g if chk else None), "Q": _s(chk.q if chk else None),
                            "margin": _s(chk.margin if chk else None), "target_type": tg["type"]},
               "containing": tg["containing"], "selected": tg["selected"], "limiting": tg["limiting"],
               "clocks": {"confirmed_at": _iso(s.conf_at), "hard_deadline": _iso(s.conf_deadline)},
               "diagnostic": {}, "blockers": blockers}
        return {"s": s, "m": m, "mode": "IMMEDIATE", "price": price, "source": source, "k": k, "chk": chk,
                "geom": geom, "blockers": blockers, "rec": rec, "ref": tc}

    # ----------------------------------------------------------------------------------------------------------
    # WAIT_PRICE (MP-002 §6)
    # ----------------------------------------------------------------------------------------------------------

    def _waits(self, minutes: list[Bar], t: datetime) -> list[dict]:
        out: list[dict] = []
        p, tick = self.p, self.tick
        for eid in sorted(self.waits):
            w = self.waits.get(eid)
            if w is None:
                continue
            s = self.scen.get(w.sid)
            if s is None:  # scenario terminal already ended the child
                continue
            d = w.d
            # (1) timers and pre-issue withdrawals (expiry before issue at equality)
            if t >= w.setup_deadline:
                self._wait_end(s, w, "ORIGINAL_SETUP_DEADLINE", t)
                continue
            if not self._a_context_ok(s, t):
                self._wait_end(s, w, f"CONTEXT_FORBIDDEN_PREISSUE:{self.context(t)}/{self.phase_now(t)}", t)
                continue
            # (2) newly admitted intervals against the cap active at their START
            ended = False
            for m in minutes:
                if m.end <= w.conf_at:
                    continue
                _, h_t, _, _ = tbar(m, d)
                if m.start < w.conf_at:
                    if h_t >= w.t_conf * d:
                        self._wait_end(s, w, "PRE_ENTRY_CONTACT_TIME_AMBIGUOUS", t)
                        ended = True
                        break
                    continue
                straddled = [Decimal(c["cap"]) * d for c in w.caps if m.start < _dt(c["since"]) < m.end]
                if straddled and h_t >= min(straddled):
                    self._wait_end(s, w, "CAP_ACTIVATION_CONTACT_AMBIGUOUS", t)
                    ended = True
                    break
                cap_start = Decimal(next(c["cap"] for c in reversed(w.caps) if _dt(c["since"]) <= m.start)) * d
                if h_t >= cap_start:
                    self._wait_end(s, w, "PRE_ENTRY_TARGET_CONTACT", t)
                    ended = True
                    break
            if ended:
                continue
            # (3) causal cap activation from newly eligible opposing zones (first eligibility after confirmation)
            zones = self._zones(d, t)
            for z in zones:
                if z[4] in w.seen:
                    continue
                w.seen.append(z[4])
                near, far = z[0], z[1]
                v_t, cap_t = w.v * d, w.cap_t()
                if v_t < near < cap_t:
                    new_t = _tick_floor(near, tick)
                    close_t = self.last_1m.c * d if self.last_1m is not None else None
                    exe = self._side_price(d, t)[0]
                    exe_t = exe * d if exe is not None and self.cfg.profile.execution == Execution.LIVE_QUOTED else None
                    if (close_t is not None and new_t <= close_t) or (exe_t is not None and new_t <= exe_t):
                        self._wait_end(s, w, "CAP_NOT_AHEAD_NOW", t, zone=z)
                        ended = True
                        break
                    if any(m.start < t <= m.end and tbar(m, d)[1] >= new_t for m in minutes):
                        self._wait_end(s, w, "CAP_ACTIVATION_CONTACT_AMBIGUOUS", t, zone=z)
                        ended = True
                        break
                    w.cap = new_t * d
                    w.caps.append({"cap": str(w.cap), "since": _iso(t), "cursor": str(self.cursor), "zone_id": z[4],
                                   "near_edge": str(near * d)})
                    self.counters["v3"]["cap_revisions"] += 1
                    self._emit_wait(s, w, "CAP_REVISION", f"NEW_ELIGIBLE_ZONE:{z[4]}", t)
                elif near <= v_t < far:
                    self.counters["v3"]["zone_crossing_v_exclusions"] += 1
            if ended:
                continue
            cor = w.corridor(tick)
            if cor is None:
                self._wait_end(s, w, "EMPTY_RETURN_CORRIDOR", t)
                continue
            price, source, k, qb = self._side_price(d, t)
            hist = self.cfg.profile.execution == Execution.HISTORICAL_BASE
            econ = geo.admissible_bounds(d, cor, w.v, w.cap, k, p.rr_min, tick) if k is not None else None
            if hist and econ is None:
                self._wait_end(s, w, "NO_ECONOMIC_RETURN_REGION", t)
                continue
            # (4) return gates on the latest newly admitted complete minute
            m = minutes[-1] if minutes and minutes[-1].start >= w.conf_at else None
            if m is None:
                continue
            w.samples += 1
            blockers: list[str] = []
            if not cor[0] <= m.c <= cor[1]:
                blockers.append("CLOSE_OUTSIDE_RETURN_CORRIDOR")
            if any(z[0] <= m.c * d <= z[1] for z in zones):
                blockers.append("BLOCKED_BY_ZONE")
            if hist:
                price, source = m.c, "MODELED_RETURN_COMPLETE_MINUTE_CLOSE"
            chk = None
            if price is not None and k is not None:
                if not hist:
                    if not cor[0] <= price <= cor[1]:
                        blockers.append("SIDE_PRICE_OUTSIDE_RETURN_CORRIDOR")
                    if any(z[0] <= price * d <= z[1] for z in zones):
                        blockers.append("SIDE_PRICE_INSIDE_OPPOSING_ZONE")
                    if econ is None:
                        blockers.append("TEMPORARY_COST_BLOCKED")
                chk = geo.predicate(d, price, w.v, w.cap, k, p.rr_min)
                if not chk.ok:
                    blockers.append(chk.reason)
            blockers += qb + self._nonselection(s, t, None, zones)
            if w.hard - t < timedelta(minutes=p.residual_min["A"]):
                blockers.append("TOO_LATE")
            blockers = sorted(set(blockers))
            if blockers != w.blockers:
                w.blockers = blockers
                self._emit_wait(s, w, "BLOCKERS", None, t, price=price, k=k, chk=chk, econ=econ)
            if not blockers:
                self.counters["v3"]["usable_returns"] += 1
                self._emit_wait(s, w, "RETURN_USABLE", m.rid, t, price=price, k=k, chk=chk, econ=econ)
                out.append({"s": s, "m": m, "mode": "RETURN", "price": price, "source": source, "k": k, "chk": chk,
                            "geom": {"v": w.v, "t": w.cap, "area": cor, "type": "LANDMARK" if len(w.caps) == 1 else
                                     "LANDMARK_CAP", "limiting": None},
                            "blockers": [], "rec": None, "ref": m.c, "wait": w})
        return out

    def _wait_end(self, s: Scen, w: Wait, reason: str, t: datetime, zone: tuple | None = None) -> None:
        self._entry_end(s, "TERMINAL", "TERMINAL", reason, t, cap_history=w.caps,
                        geometry=self._wait_geometry(w),
                        selected=_zone_info(zone, w.d) if zone is not None else None)

    def _wait_geometry(self, w: Wait) -> dict[str, str | None]:
        cor = w.corridor(self.tick)
        return {"R": _s(w.r), "K_trigger": _s(w.k_trigger), "V": _s(w.v), "T_confirm": _s(w.t_conf),
                "T_current": _s(w.cap), "S15": _s(w.s15), "tick": _s(self.tick), "confirmation_close": _s(w.conf_close),
                "corridor_structural": _rng(_market(w.lo_t, w.hi_t, w.d)), "corridor_effective": _rng(cor)}

    def _emit_wait(self, s: Scen, w: Wait, transition: str, reason: str | None, t: datetime, price=None, k=None,
                   chk=None, econ=None) -> None:
        g = self._wait_geometry(w)
        g.update(price=_s(price), K_cost=_s(k), economic_current=_rng(econ),
                 G=_s(chk.g if chk else None), Q=_s(chk.q if chk else None), margin=_s(chk.margin if chk else None))
        self._emit_entry(s, "WAIT_PRICE", "RETURN", transition, reason, t, blockers=w.blockers, geometry=g,
                         cap_history=w.caps, clocks={"confirmed_at": _iso(w.conf_at),
                                                     "setup_expiry": _iso(w.setup_deadline),
                                                     "hard_deadline": _iso(w.hard)})

    # ----------------------------------------------------------------------------------------------------------
    # selection / issue
    # ----------------------------------------------------------------------------------------------------------

    def _select3(self, confirmations: list[tuple[Scen, Bar]], returns: list[dict], t: datetime) -> None:
        evaluated: list[dict] = []
        for s, m in confirmations:
            if s.entry != "PENDING":
                continue  # child cleared at evaluation start: the structural confirmation stays recorded
            if s.family == "A":
                e = self._route_a(s, m, t)
                if e is not None:
                    evaluated.append(e)
            else:
                evaluated.append(self._eval_bc(s, m, t))
        evaluated += returns
        for e in evaluated:
            if e["chk"] is not None and e["chk"].g is not None:
                self._gate_stats(e, t)
        actionable = [e for e in evaluated if not e["blockers"]]
        dirs = {e["s"].d for e in actionable}
        slot = self.call is not None and self.call.thesis == "ONGOING"
        winner = None
        if actionable and not slot and len(dirs) == 1:
            winner = sorted(actionable, key=lambda e: (FAM_RANK[e["s"].family], e["s"].born_at, e["s"].sid))[0]
        for e in evaluated:
            if e is winner:
                continue
            s = e["s"]
            extra = []
            if not e["blockers"]:
                extra.append("SLOT_OCCUPIED" if slot else "CONFLICTED" if len(dirs) > 1 else "PRIORITY")
            reasons = e["blockers"] + extra
            for r in reasons:
                self.counters["rejections"][r.split(":")[0]] = self.counters["rejections"].get(r.split(":")[0], 0) + 1
            if "SLOT_OCCUPIED" in extra:
                self.counters["suppressed_by_slot"].append({"attempt": s.eid, "at": _iso(t),
                                                            "call": self.call.cid if self.call else None})
                self.counters["suppressed_by_slot"] = self.counters["suppressed_by_slot"][-50:]
            transition = "REJECT" if extra else "TERMINAL"
            if e["mode"] == "RETURN":
                w = e["wait"]
                self._entry_end(s, "TERMINAL", transition, ",".join(reasons), t, cap_history=w.caps,
                                geometry=self._wait_geometry(w))
            else:
                rec = dict(e["rec"])
                rec["blockers"] = reasons
                self._entry_end(s, "TERMINAL", transition, ",".join(reasons), t, **rec)
        if winner is not None:
            self._issue3(winner, t)

    def _gate_stats(self, e: dict, t: datetime) -> None:
        s, chk = e["s"], e["chk"]
        st = self.counters["gates"].setdefault(f"{s.family}:{e['mode']}", [])
        st.append({"at": _iso(t), "attempt": s.eid, "G": str(chk.g), "Q": str(chk.q), "K": str(e["k"]),
                   "margin": str(chk.margin), "ok": chk.ok})
        if len(st) > 400:
            del st[: len(st) - 400]

    def _issue3(self, e: dict, t: datetime) -> None:
        s, m, g = e["s"], e["m"], e["geom"]
        p = self.p
        hard_td = p.hard(s.family)
        if s.family == "A":
            hard, origin = s.conf_at + hard_td, "STRUCTURAL_CONFIRMATION_PUBLICATION"
            progress = half_point(t, hard)
        else:
            hard, origin = t + hard_td, "ISSUE"
            progress = t + _scaled(hard_td, p.progress_fraction)
        cid = f"call-{s.family}{dname(s.d)[0]}-{_iso(t)}-{_h(s.eid, _iso(t))}"
        if s.family == "A":
            prem = ("15M_CLOSE_BEYOND_IMPULSE_A", s.a_t * s.d)
        else:
            prem = ("15M_CLOSE_BEYOND_U_MINUS_Z" if s.family == "B" else "15M_CLOSE_BEYOND_L_MINUS_Z", s.premise_t * s.d)
        w: Wait | None = e.get("wait")
        caps = list(w.caps) if w is not None else []
        call = CallV3(cid=cid, aid=s.eid, family=s.family, d=s.d, origin=self.origin, issued_at=t, issue_seq=self.seq,
                      trigger_start=m.start, ref=m.c, v=g["v"], t=g["t"], target_type=g["type"], limiting=g["limiting"],
                      s15=self.s15, area=g["area"], expected=p.expected(s.family),
                      min_residual=p.residual_min[s.family], hard_deadline=hard, progress_at=progress,
                      premise_kind=prem[0], premise_level=prem[1], entry="AVAILABLE", entry_reasons=[],
                      conditions_ok=True, scenario_id=s.sid, entry_mode=e["mode"], confirmed_at=s.conf_at,
                      t_confirm=w.t_conf if w is not None else g["t"], hard_origin=origin, cap_history=caps)
        self.call = call
        self.call_count += 1
        if self.window == "WARMUP":
            self.counters["calls_issued_warmup"] += 1
        else:
            self.counters["calls_issued"][s.family][dname(s.d)] += 1
            mk = f"{s.family}_{e['mode']}"
            self.counters["v3"]["issued_by_mode"][mk] = self.counters["v3"]["issued_by_mode"].get(mk, 0) + 1
        if w is not None:
            self.waits.pop(s.eid, None)
        s.entry, s.call_id = "ISSUED", cid
        act = {"subject_id": cid, "actionable": True, "blockers": (), "execution_mode": self.cfg.profile.execution.value,
               "side_price": e["price"], "side_price_source": e["source"], "cost_envelope_bps": e["k"],
               "gain_bps": e["chk"].g if e["chk"] else None, "risk_bps": e["chk"].q if e["chk"] else None,
               "reward_risk_margin": e["chk"].margin if e["chk"] else None, "structural_area": g["area"],
               "admissible_bounds": geo.admissible_bounds(s.d, g["area"], g["v"], g["t"], e["k"], p.rr_min, self.tick)
               if e["k"] is not None else None, "remaining_minutes": None, "limiting_landmark": g["limiting"]}
        rec = e.get("rec") or {}
        self._emit_entry(s, "ISSUED", e["mode"], "ISSUE", cid, t, call_id=cid,
                         geometry=rec.get("geometry") or (self._wait_geometry(w) if w is not None else {}),
                         containing=rec.get("containing", ()), selected=rec.get("selected"),
                         limiting=g["limiting"], cap_history=caps,
                         clocks={"confirmed_at": _iso(s.conf_at), "issued_at": _iso(t), "hard_deadline": _iso(hard),
                                 "call_progress_at": _iso(progress), "scenario_progress_at": _iso(s.progress_at)},
                         diagnostic=rec.get("diagnostic") or {})
        self._emit_call(call, act, t)
        self._touch()

    # ----------------------------------------------------------------------------------------------------------
    # issued guidance (MP-001 lifecycle reused; v0.3 records)
    # ----------------------------------------------------------------------------------------------------------

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
            if call.family == "A" and any(z[0] <= price * call.d <= z[1] for z in self._zones(call.d, t)):
                reasons.append("AT_OPPOSING_AREA")  # a later obstacle: current-entry restriction, never a new target
        non_quote = [r for r in reasons if r not in UNVERIFIED_REASONS]
        status = "AVAILABLE" if not reasons else ("UNVERIFIED" if not non_quote else "CLOSED")
        reasons = sorted(set(reasons))
        if status != call.entry or reasons != call.entry_reasons or conditions_ok != call.conditions_ok:
            self._entry_prev = call.entry
            if status == "AVAILABLE" and call.entry != "AVAILABLE":
                call.entry_reopens += 1
            changed = ["entry"] if status != call.entry else ["entry_reasons"]
            call.entry, call.entry_reasons, call.conditions_ok = status, reasons, conditions_ok
            self._revision(call, t, changed=tuple(changed), guidance=_entry_guidance(call), price=price, k=k, chk=chk)

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
            "progress_max_favorable_scale": prog,
            "coverage_loss_from": getattr(call, "coverage_loss_from", None) if call.thesis != "ONGOING" else None,
            "scenario_terminal": getattr(call, "scenario_terminal", None) if call.thesis != "ONGOING" else None},
            rid=f"{call.cid}#r{call.revision}", revision=call.revision, lineage=(call.cid,))
        if "thesis" in changed:
            self._material(call, "TERMINAL", f"{call.thesis}" + (f" ({call.terminal_reason})" if call.terminal_reason
                                                                 else "") + f": {guidance}", t)
        elif "entry" in changed:
            ct = {"AVAILABLE": "ENTRY_REOPENED", "CLOSED": "ENTRY_WITHDRAWN", "UNVERIFIED": "ENTRY_UNVERIFIED"}[call.entry]
            usable_change = call.entry == "AVAILABLE" or self._entry_prev == "AVAILABLE"
            owner_stop = "LIVE_SESSION_STOPPED" in call.entry_reasons
            self._material(call, ct, guidance, t, alert=usable_change and not owner_stop)

    def _emit_call(self, call: Call, act: dict, t: datetime) -> None:
        p = self.p
        mode = getattr(call, "entry_mode", "IMMEDIATE")
        thesis = (f"{dname(call.d)} {call.family} ({_FAMILY_TEXT[call.family]}): from {call.ref} toward "
                  f"{call.t} ({call.target_type.lower()}), invalidated at {call.v}"
                  + (" — entered on a later usable return after confirmation" if mode == "RETURN" else ""))
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
                              else "bounded calendar subset only",
                              "the minimum residual time is an eligibility filter, not a guaranteed holding period"),
            "scenario_id": call.scenario_id, "entry_mode": mode, "confirmed_at": call.confirmed_at,
            "target_at_confirmation": call.t_confirm, "hard_deadline_origin": call.hard_origin,
            "issue_scale": call.s15, "cap_history": tuple(call.cap_history)},
            rid=call.cid, lineage=(call.aid, call.scenario_id), event=(call.trigger_start, call.trigger_start + MINUTE))
        what = "entry available" if mode == "IMMEDIATE" else "usable return price reached; entry available"
        self._material(call, "NEW_CALL", f"New {dname(call.d)} call ({call.family}, {mode}): {what} inside "
                                         f"{call.area[0]}–{call.area[1]}, target {call.t}, stop {call.v}", t)

    # ----------------------------------------------------------------------------------------------------------
    # emission
    # ----------------------------------------------------------------------------------------------------------

    def _emit(self, kind: str, t: datetime, body: dict, rid: str | None = None, revision: int = 0,
              lineage: tuple = (), event: tuple | None = None) -> dict:
        self.journal_seq += 1
        rid = rid or f"{kind}-{self.journal_seq:08d}"
        env = self._envelope(kind, rid, t, revision, lineage, event)
        model = sc.KIND_CONTRACTS_V3[kind](env=env, **body)
        doc = json.loads(model.model_dump_json())
        digest = hashlib.sha256(canonical(doc)).hexdigest()
        self.journal_chain = hashlib.sha256(bytes.fromhex(self.journal_chain) + bytes.fromhex(digest)).hexdigest()
        entry = {"seq": self.journal_seq, "kind": kind, "record_id": rid, "clock_time": doc["env"]["clock_time"],
                 "professional_seq": self.seq, "factual_cursor": self.cursor, "origin": self.origin,
                 "subject": (lineage[0] if lineage else None), "digest": digest, "chain": self.journal_chain,
                 "record": doc}
        self.journal.append(entry)
        return entry

    def _antecedent(self, s: Scen) -> str:
        tick = self.tick * self.p.trigger_ticks * s.d
        if s.status == "WATCH":
            return {"A": f"if a clean reaction and recovery confirm, continuation toward {s.dest_t * s.d}",
                    "B": f"if retest and later recovery confirm, continuation toward the box projection "
                         f"{s.dest_t * s.d}, with obstacles",
                    "C": f"if reclaim and later recovery confirm, rotation toward {s.dest_t * s.d}, with obstacles"
                    }[s.family]
        if s.status == "ARMED":
            return (f"a later eligible complete 1m close {'>=' if s.d > 0 else '<='} {s.k_t * s.d + tick} with "
                    f"{'low >' if s.d > 0 else 'high <'} {s.v_t * s.d} confirms continuation toward "
                    f"{s.dest_t * s.d if s.dest_t is not None else 'n/a'}")
        return (f"confirmed: continuation toward {s.dest_t * s.d if s.dest_t is not None else 'n/a'} while V "
                f"{s.v_t * s.d} holds and before {_iso(s.conf_deadline)}")

    def _emit_scen(self, s: Scen, transition: str, reason: str | None, t: datetime, terminal: str | None = None,
                   released: bool = False) -> None:
        setup = {"s15": str(s.s15), "zone_halfwidth": str(s.z), "sources": ",".join(s.sources[-3:]),
                 "renewal": s.renewal, "pre_live": str(s.pre_live)}
        if s.family == "A":
            setup.update(impulse_A=_s(s.a_t * s.d if s.a_t is not None else None),
                         impulse_B=_s(s.b_t * s.d if s.b_t is not None else None), anchor=s.anchor,
                         bars_seen=str(s.bars_seen), latch_long=self.latch["1"], latch_short=self.latch["-1"],
                         b_zone_broken=str(s.b_broken))
        elif self.box is not None and s.owner == self.box.bid:
            setup.update(box_low=str(self.box.low), box_up=str(self.box.up), box_mid=str(self.box.mid))
        if s.family == "A":
            own = "OCCUPIED" if self._owner_active(s) and not released else "RELEASED"
        else:
            own = None
        es = self.cfg.eval_start
        self._emit("scenario", t, {
            "scenario_id": s.sid, "owner_id": s.owner, "entry_attempt_id": s.eid, "family": sc.Family(s.family),
            "direction": sc.Direction(dname(s.d)), "status": "TERMINAL" if terminal else s.status,
            "transition": transition, "reason": reason, "terminal_state": terminal, "antecedent": self._antecedent(s),
            "trigger_level": s.k_t * s.d if s.k_t is not None else None,
            "invalidation_level": s.v_t * s.d if s.v_t is not None else None,
            "reaction_level": s.r_t * s.d if s.r_t is not None and s.status != "WATCH" else None,
            "destination": s.dest_t * s.d if s.dest_t is not None else None, "destination_type": s.dest_type,
            "premise": None if s.family != "A" and s.premise_t is None else
            (f"15m close beyond {s.a_t * s.d}" if s.family == "A" else f"15m close beyond {s.premise_t * s.d}"),
            "setup": setup, "activated_at": s.arm_at, "original_expiry": s.setup_deadline, "confirmed_at": s.conf_at,
            "confirmation_close": s.conf_close_t * s.d if s.conf_close_t is not None else None,
            "confirmation_scale": s.conf_s15, "confirmed_deadline": s.conf_deadline, "progress_check_at": s.progress_at,
            "discovery_owner": own, "warmup_origin": es is not None and s.born_at < es},
            rid=f"{s.sid}#{transition.lower()}-{self.journal_seq + 1}",
            lineage=(s.sid,) + ((s.owner,) if s.owner and s.owner != s.sid else ()))
        key = f"{s.family}:{transition}"
        if self.window == "EVALUATION":
            self.counters["v3"]["scenario_transitions"][key] = self.counters["v3"]["scenario_transitions"].get(key, 0) + 1

    def _emit_entry(self, s: Scen, state: str, mode: str | None, transition: str, reason: str | None, t: datetime, *,
                    blockers=(), call_id: str | None = None, geometry: dict | None = None, containing=(),
                    selected=None, limiting=None, cap_history=(), clocks: dict | None = None,
                    diagnostic: dict | None = None) -> None:
        self._emit("entry_attempt", t, {
            "entry_attempt_id": s.eid, "scenario_id": s.sid, "family": sc.Family(s.family),
            "direction": sc.Direction(dname(s.d)), "state": state, "mode": mode, "transition": transition,
            "reason": reason, "blockers": tuple(blockers), "call_id": call_id,
            "geometry": {k: v for k, v in sorted((geometry or {}).items())}, "containing_zones": tuple(containing),
            "selected_zone": selected, "limiting_landmark": limiting, "cap_history": tuple(cap_history),
            "clocks": clocks or {}, "diagnostic": diagnostic or {}},
            rid=f"{s.eid}#{transition.lower()}-{self.journal_seq + 1}", lineage=(s.eid, s.sid))
        key = f"{s.family}:{transition}:{(reason or '').split(':')[0].split(',')[0]}"
        if self.window == "EVALUATION":
            self.counters["v3"]["entry_transitions"][key] = self.counters["v3"]["entry_transitions"].get(key, 0) + 1

    def _entry_end(self, s: Scen, state: str, transition: str, reason: str, t: datetime, *, blockers=(),
                   geometry=None, containing=(), selected=None, limiting=None, cap_history=(), clocks=None,
                   diagnostic=None) -> None:
        if s.entry not in ("PENDING", "WAIT"):
            return
        w = self.waits.pop(s.eid, None)
        mode = "RETURN" if w is not None else ("IMMEDIATE" if transition == "REJECT" else None)
        if w is not None and not cap_history:
            cap_history = w.caps
        s.entry = "CLEARED" if state == "CLEARED" else "TERMINAL"
        self._emit_entry(s, state, mode, transition, reason, t, blockers=blockers or ([] if w is None else w.blockers),
                         geometry=geometry if geometry is not None else (self._wait_geometry(w) if w else None),
                         containing=containing, selected=selected, limiting=limiting, cap_history=cap_history,
                         clocks=clocks, diagnostic=diagnostic)
        self._touch()

    # ----------------------------------------------------------------------------------------------------------
    # view (MP-002 §4: structural scenarios only, cost-invariant)
    # ----------------------------------------------------------------------------------------------------------

    def _scenario(self, s: Scen) -> dict:
        exp = self.p.expected(s.family)
        return {"scenario_id": s.sid, "family": s.family, "direction": dname(s.d), "antecedent": self._antecedent(s),
                "trigger_level": s.k_t * s.d if s.k_t is not None else None,
                "invalidation_level": s.v_t * s.d if s.v_t is not None else None,
                "conditional_target": f"narrative destination {s.dest_type.lower()} (the economic target may be nearer)",
                "alternative": "no call: withdrawal, expiry, invalidation or an entry that never becomes usable",
                "expires_at": s.conf_deadline if s.status == "CONFIRMED" else s.setup_deadline,
                "candidate_domain": f"{s.family} expected {exp[0]}-{exp[1]}m", "status": s.status,
                "destination": s.dest_t * s.d if s.dest_t is not None else None, "destination_type": s.dest_type,
                "confirmed_at": s.conf_at}

    def compute_view(self, t: datetime) -> dict:
        ctx = self.context(t)
        ph = self.phase_now(t)
        order = lambda s: (FAM_RANK[s.family], s.born_at, s.sid)  # noqa: E731
        active = sorted(self.scen.values(), key=order)
        strong = [s for s in active if s.status in ("ARMED", "CONFIRMED")]
        watch = [s for s in active if s.status == "WATCH"]
        dirs = {s.d for s in strong}
        principal = None
        alts: list[dict] = []
        reasons: list[str] = []
        counter: list[str] = []
        blockers: list[str] = []
        conditional = False
        if not self.ready_15m(t) or not self.ready_1h(t):
            row, exp = "REQUIRED_CONTEXT_UNAVAILABLE", "UNAVAILABLE"
            blockers = [x for x in ("TRADE_15M_NOT_READY" if not self.ready_15m(t) else "",
                                    "TRADE_1H_NOT_READY" if not self.ready_1h(t) else "") if x]
        elif len(dirs) > 1:
            row, exp = "OPPOSING_SCENARIOS", "UNCERTAIN"
            alts = [self._scenario(s) for s in strong]
            reasons.append("supported armed/confirmed scenarios point in opposite directions: "
                           + ", ".join(f"{s.family} {dname(s.d)} {s.status.lower()}" for s in strong))
        elif strong:
            row, exp = "CONDITIONAL_SCENARIO", "UP" if strong[0].d > 0 else "DOWN"
            conditional = True
            principal = self._scenario(strong[0])
            alts = [self._scenario(s) for s in strong[1:]] + [self._scenario(s) for s in watch if s.d != strong[0].d]
            p0 = strong[0]
            reasons.append(f"{p0.family} {dname(p0.d)} {p0.status.lower()}: " + self._antecedent(p0))
            if p0.status == "CONFIRMED" and ctx_t(ctx, p0.d) not in ("UP",) and p0.family == "A":
                counter.append(f"1h observed context now {ctx}")
            if p0.status == "CONFIRMED" and p0.family in "BC" and ctx_t(ctx, p0.d) == "DOWN":
                counter.append(f"1h observed context now {ctx}")
        elif watch:
            row, exp = "WATCH_ONLY", "UNCERTAIN"
            reasons.append("only conditional WATCH hypotheses: " + ", ".join(
                f"{s.family} {dname(s.d)}" for s in watch) + " (not a forecast, not a call)")
        elif ctx == "BALANCED" and ph in ("COMPRESSION", "ROTATION"):
            row, exp = "BALANCED_RANGE", "BALANCED"
            reasons.append("balanced 1h context in " + ph.lower() + (
                f"; rotation inside [{self.box.low}, {self.box.up}]" if self.box else "; no qualified box"))
        else:
            row, exp = "NO_QUALIFIED_STRUCTURE", "UNCERTAIN"
            reasons.append(f"observed {ctx}/{ph}; missing antecedent: no born A impulse or compression box scenario")
        hz = None
        if principal is not None:
            e = self.p.expected(principal["family"])
            if strong[0].status == "CONFIRMED":
                rem = max(int((strong[0].conf_deadline - t) / MINUTE), 0)
                hz = (min(e[0], rem), min(e[1], rem))
            else:
                hz = (e[0], e[1])
        return {"observed_context": ctx, "phase": ph, "expected_direction": exp, "conditional": conditional,
                "table_row": row, "principal": principal, "alternatives": tuple(alts),
                "watch": tuple(self._scenario(s) for s in watch),
                "ongoing_call_id": None, "horizon_minutes": hz, "levels": self._levels(t),
                "reasons": tuple(reasons), "counterevidence": tuple(counter), "blockers": tuple(blockers)}

    def _publish_view(self, t: datetime) -> None:
        v = self.compute_view(t)
        key = (v["table_row"], v["expected_direction"], v["observed_context"], v["phase"],
               (v["principal"] or {}).get("scenario_id"), (v["principal"] or {}).get("status"),
               tuple((a["scenario_id"], a["status"]) for a in v["alternatives"]),
               tuple(a["scenario_id"] for a in v["watch"]), v["blockers"], v["counterevidence"])
        self.view = v
        if key == self.view_key:
            return
        self.view_key = key
        self.counters["view_changes"] += 1
        rec = dict(v)
        rec["principal"] = sc.ScenarioV3(**v["principal"]) if v["principal"] else None
        rec["alternatives"] = tuple(sc.ScenarioV3(**a) for a in v["alternatives"])
        rec["watch"] = tuple(sc.ScenarioV3(**a) for a in v["watch"])
        self._emit("market_view", t, rec)

    def _diag_conditions(self, t: datetime) -> list[str]:
        out = {b.split(":")[0] for b in self._common_blockers(t)}
        out.update(self.connection_blockers())
        if self.origin == sc.Origin.RECONSTRUCTED.value:
            out.add("RECONSTRUCTED_CATCH_UP")
        if out:
            out.add("ANY_COMMON_BLOCKER")
        armed = [s for s in self.scen.values() if s.status == "ARMED" and s.entry == "PENDING"]
        slot = self.call is not None and self.call.thesis == "ONGOING"
        if self.waits:
            out.add("WAITING_FOR_USABLE_PRICE")
        if slot:
            out.add("SLOT_OCCUPIED")
            if armed or self.waits:
                out.add("SLOT_OCCUPIED_WITH_ARMED")
        elif len({s.d for s in armed}) > 1:
            out.add("CONFLICTED_ARMED")
        elif len(armed) > 1:
            out.add("PRIORITY_COMPETITION")
        if not armed and not slot and not self.waits:
            out.add("NO_ARMED_SCENARIO")
        if any(s.status == "CONFIRMED" for s in self.scen.values()):
            out.add("CONFIRMED_SCENARIO_ACTIVE")
        return sorted(out)

    # ----------------------------------------------------------------------------------------------------------
    # inspection / codec
    # ----------------------------------------------------------------------------------------------------------

    def call_view(self, t: datetime | None = None) -> dict | None:
        v = super().call_view(t)
        if v is None:
            return None
        c = self.call
        v.update(scenario_id=c.scenario_id, entry_mode=c.entry_mode, confirmed_at=_iso(c.confirmed_at),
                 target_at_confirmation=_s(c.t_confirm), hard_deadline_origin=c.hard_origin,
                 cap_history=list(c.cap_history))
        return v

    def scenarios_view(self, t: datetime | None) -> list[dict]:
        out = []
        for s in sorted(self.scen.values(), key=lambda s: (FAM_RANK[s.family], s.born_at, s.sid)):
            w = self.waits.get(s.eid)
            row = {"scenario_id": s.sid, "family": s.family, "family_text": _FAMILY_TEXT[s.family],
                   "direction": dname(s.d), "status": s.status, "antecedent": self._antecedent(s),
                   "trigger_level": _s(s.k_t * s.d if s.k_t is not None else None),
                   "invalidation_level": _s(s.v_t * s.d if s.v_t is not None else None),
                   "destination": _s(s.dest_t * s.d if s.dest_t is not None else None),
                   "destination_type": s.dest_type, "original_expiry": _iso(s.setup_deadline),
                   "confirmed_at": _iso(s.conf_at), "confirmed_deadline": _iso(s.conf_deadline),
                   "progress_check_at": _iso(s.progress_at), "owner": s.owner,
                   "discovery_owner": ("OCCUPIED" if self._owner_active(s) else "RELEASED") if s.family == "A" else None,
                   "entry_state": s.entry, "call_id": s.call_id}
            if w is not None:
                cor = w.corridor(self.tick)
                row["waiting"] = {"text": "Scenario confirmed; waiting for a usable price (no call yet).",
                                  "corridor": [str(cor[0]), str(cor[1])] if cor else None,
                                  "stop_V": str(w.v), "target_now": str(w.cap), "target_at_confirmation": str(w.t_conf),
                                  "wait_until": _iso(w.setup_deadline), "hard_deadline": _iso(w.hard),
                                  "remaining_wait_minutes": (max(int((w.setup_deadline - t) / MINUTE), 0)
                                                             if t is not None else None),
                                  "blockers": list(w.blockers), "caps": list(w.caps)}
            out.append(row)
        return out

    def inspect(self) -> dict:
        out = super().inspect()
        t = self.clock
        out["format"] = STATE_FORMAT
        out["method_semantics"] = "MP-002 v0.3: structural scenarios + child entry attempts"
        out["scenarios"] = self.scenarios_view(t)
        out["attempts"] = [{"attempt_id": s.sid, "family": s.family, "direction": dname(s.d), "status": s.status,
                            "trigger_level": _s(s.k_t * s.d if s.k_t is not None else None),
                            "invalidation_level": _s(s.v_t * s.d if s.v_t is not None else None),
                            "expires_at": _iso(s.conf_deadline if s.status == "CONFIRMED" else s.setup_deadline),
                            "owner": s.owner, "entry_state": s.entry}
                           for s in sorted(self.scen.values(), key=lambda s: s.sid)]
        out["discovery_owners"] = {dname(int(k)): v for k, v in sorted(self.a_owner.items())}
        out["waiting"] = sorted(self.waits)
        return out

    def encode(self) -> dict:
        doc = super().encode()
        doc["format"] = STATE_FORMAT
        doc["v3"] = {"scen": [s.encode() for _, s in sorted(self.scen.items())],
                     "a_owner": {k: v for k, v in sorted(self.a_owner.items())},
                     "waits": [w.encode() for _, w in sorted(self.waits.items())],
                     # dependency snapshot of the last dispatch: records emitted during the next dispatch's sealed
                     # ingestion carry it in their envelope, so a direct restore must reproduce it
                     "deps": [x.model_dump(mode="json") for x in self._deps]}
        return doc

    @classmethod
    def decode(cls, doc: dict, cfg: AdviserConfig) -> AdviserCoreV3:
        if doc.get("format") != STATE_FORMAT:
            raise AdviserError(f"adviser state format {doc.get('format')!r} is not {STATE_FORMAT}")
        base = {**doc, "format": BASE_STATE_FORMAT, "call": None, "view_key": None}
        base.pop("v3")
        c = super().decode(base, cfg)
        c.call = CallV3.decode(doc["call"]) if doc["call"] else None
        c.view_key = _tuples(doc["view_key"]) if doc["view_key"] is not None else None
        if c.view is not None and "watch" in c.view:
            c.view["watch"] = tuple(c.view["watch"])
        v3 = doc["v3"]
        c.scen = {d["sid"]: Scen.decode(d) for d in v3["scen"]}
        c.a_owner = dict(v3["a_owner"])
        c.waits = {f"{d['sid']}#entry": Wait.decode(d) for d in v3["waits"]}
        c._deps = tuple(sc.DependencyRef.model_validate(d) for d in v3.get("deps", ()))  # absent: earlier v3 states
        return c


def _zone_info(z: tuple, d: int) -> dict[str, str | None]:
    info = dict(z[2])
    info.update(near_edge=str(z[0] * d), far_edge=str(z[1] * d), zone_id=z[4])
    return {k: (None if v is None else str(v)) for k, v in sorted(info.items())}


def _tuples(x: Any) -> Any:
    return tuple(_tuples(v) for v in x) if isinstance(x, list) else x


def _rng(x: tuple[Decimal, Decimal] | None) -> str | None:
    return None if x is None else f"{x[0]}..{x[1]}"


def _new_counters3() -> dict:
    return {"v3": {"confirmations": {}, "routes": {"IMMEDIATE": 0, "RETURN_WAIT": 0}, "usable_returns": 0,
                   "issued_by_mode": {}, "cap_revisions": 0, "zone_crossing_v_exclusions": 0,
                   "owner_releases": {}, "scenario_end": {}, "scenario_transitions": {}, "entry_transitions": {},
                   "a_denominators": {"confirmations": 0, "D": 0, "N": 0, "excluded": {}}}}


_ = (_jsonable, _terminal_guidance)
