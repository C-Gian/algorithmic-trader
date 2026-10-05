"""Separate normalized hypothetical evaluator (``algotrader.adviser-evaluation.v1``; MP-001 §11).

Reads only the semantic journal (issued calls and their revisions, with publication times) and complete trade/mark
1m minutes and settled funding. It never feeds anything back to the reasoning core: the core's emissions are
byte-identical with the evaluator disabled.

* One primary first-entry path per issued call (entry delay 60 s), plus separate entry-delay 0 s / 120 s paths on
  the SAME calls and a horizon-only baseline conditioned on the primary entry (exit request at original issue + family
  hard horizon, no stop/target). Exit delay 60 s for every path. Cost stress reprices the primary path only.
* Candidate entry boundaries are UTC minute starts at/after ceil-minute(issue + delay). At boundary s the call must be
  nonterminal with entry conditions enabled (and residual time) according to the latest revision published at or
  before s (the pre-open dispatch prefix); then the minute's own OPEN must lie in the frozen structural area and pass
  the primary G/Q/K predicate. The minute's later high/low/close can never grant the entry. Protective checks start
  with the entry minute.
* Collision table: single T or V contact in a complete post-entry minute closes the path; both in one minute is
  AMBIGUOUS with bounds; at a pending-exit boundary an open gap through V is a stop at the adverse open, an open beyond
  T without a V gap is a conservative T, otherwise a discretionary open fill. A missing/rejected minute before a
  certified exit censors the path from that minute; data/tail end is UNRESOLVED.
* N0 = 1 (abstract unit), q = 1/E: gross = d*(X/E-1); fees f*(1+X/E); allowances a*(1+X/E). Funding at settlement
  u = -d*q*mark_u*rate_u with the declared ownership boundaries; without authoritative coverage the path stays
  PRICE_NET_ONLY with TOTAL_NET unavailable — never zero by assumption.
* Hourly MarketView and direction-persistence samples after all dispatch updates, scored on fixed +1h/+4h complete
  trade-minute closes against the frozen known anchor; abstentions and unavailable endpoints keep their counts.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal, localcontext
from typing import Any

from ..feed.ordering import canonical
from . import geometry as geo
from .evaluation_contracts import EVALUATION_VERSION, EvaluatorProfile, Fill, HypotheticalPath, ViewSample
from .measures import PRECISION, Bar, div
from .params import Params

STATE_FORMAT = "algotrader.adviser-evaluation-state.v1"
# v2: WP-009 correction — ordinary protective stop gaps fill at the adverse open (MP-001 §11)
EVALUATOR_IMPLEMENTATION = "adviser.evaluator.v2"
MINUTE = timedelta(minutes=1)
INITIAL_RECORDS = hashlib.sha256(b"algotrader.adviser-evaluation.records.v1\x00").hexdigest()
BPS = Decimal(10000)


def _iso(t: datetime | None) -> str | None:
    return None if t is None else t.isoformat()


def _dt(s: str | None) -> datetime | None:
    return None if s is None else datetime.fromisoformat(s)


def ceil_minute(t: datetime) -> datetime:
    f = t.replace(second=0, microsecond=0)
    return f if f == t else f + MINUTE


def _sign(x: Decimal) -> str:
    return "UP" if x > 0 else "DOWN" if x < 0 else "FLAT"


@dataclass
class PathState:
    variant: str
    entry_delay: int
    exit_mode: str  # GUIDANCE / HORIZON_ONLY
    status: str = "WAIT_ENTRY"  # WAIT_ENTRY / OPEN / DONE
    next_boundary: str | None = None
    attempts: int = 0
    rejected: int = 0
    entry_price: str | None = None
    entry_time: str | None = None
    pending_exit_at: str | None = None
    exit_class: str | None = None
    hi_t: str | None = None  # max transformed high since entry
    lo_t: str | None = None
    last_end: str | None = None
    notes: list[str] = field(default_factory=list)

    def encode(self) -> dict:
        return dict(self.__dict__)

    @classmethod
    def decode(cls, d: dict) -> PathState:
        return cls(**d)


class Evaluator:
    def __init__(self, params: Params, tick: Decimal, *, eval_start: datetime | None, eval_end: datetime | None,
                 funding_mode: str = "PRICE_NET_ONLY", sample_views: bool = True) -> None:
        self.p = params
        self.tick = tick
        self.eval_start, self.eval_end = eval_start, eval_end
        self.funding_mode = funding_mode
        self.sample_views = sample_views
        p = params
        self.f = div(p.fee_bps, BPS)
        self.a = div(p.allowance_bps, BPS)
        self.a_stress = div(p.stress_allowance_bps, BPS)
        self.k = p.hist_k_bps
        self.calls: dict[str, dict] = {}
        self.records: list[dict] = []  # emitted immutable evaluation records (drained by the runtime)
        self.record_seq = 0
        self.record_chain = INITIAL_RECORDS
        self.samples: list[dict] = []  # pending hourly samples (bounded: <= 5 open)
        self.next_sample: datetime | None = None
        self.funding: list[dict] = []  # settlements (bounded: pruned once no open path can own them)
        self.mark_closes: dict[str, str] = {}  # minute end -> mark close (bounded: recent settlement candidates)
        self.last_trade: Bar | None = None
        self.last_trade_end: datetime | None = None
        self.aggregates = {"paths": {}, "samples": {"taken": 0}}
        self.now: datetime | None = None  # transient: clock of the dispatch/finish being processed (resolved_at)

    # ---------------------------------------------------------------------------------------------------------
    # profiles
    # ---------------------------------------------------------------------------------------------------------

    def profile(self, variant: str) -> EvaluatorProfile:
        delay = {"PRIMARY": self.p.eval_primary_delay, "ENTRY_DELAY_0": 0, "ENTRY_DELAY_120": 120,
                 "HORIZON_ONLY": self.p.eval_primary_delay}[variant]
        return EvaluatorProfile(profile_id=f"mp001.evaluation.{variant.lower()}.v1", entry_delay_seconds=delay,
                                exit_delay_seconds=self.p.eval_exit_delay, fee_per_leg=self.f,
                                allowance_per_leg=self.a, adequacy_envelope_bps=self.k, funding=self.funding_mode,
                                exit_mode="HORIZON_ONLY" if variant == "HORIZON_ONLY" else "GUIDANCE")

    def identity(self) -> dict:
        body = {"format": EVALUATION_VERSION, "implementation": EVALUATOR_IMPLEMENTATION, "profiles": {v: json.loads(self.profile(v).model_dump_json())
                                                           for v in ("PRIMARY", "ENTRY_DELAY_0", "ENTRY_DELAY_120",
                                                                     "HORIZON_ONLY")},
                "stress_allowance_per_leg": str(self.a_stress), "exit_delay_sensitivities": "NOT_IMPLEMENTED_SECONDARY",
                "view_sampling": "EVERY_UTC_HOUR_AFTER_DISPATCH_UPDATES", "horizons_hours": [1, 4]}
        return {**body, "sha256": hashlib.sha256(canonical(body)).hexdigest()}

    # ---------------------------------------------------------------------------------------------------------
    # inputs from the runtime
    # ---------------------------------------------------------------------------------------------------------

    def next_deadline(self, after: datetime | None) -> datetime | None:
        if not self.sample_views or self.eval_start is None:
            return None
        if self.next_sample is None:
            self.next_sample = self.eval_start
        ns = self.next_sample
        if self.eval_end is not None and ns >= self.eval_end:
            return None
        if after is not None and ns <= after:
            return None
        return ns

    def on_minutes(self, items: list, mark: list[tuple[datetime, Decimal]]) -> None:
        """Complete trade minutes (Bar) or ("GAP", start, reason) items in slot order, BEFORE the core processes the
        same dispatch (the core's later state can never inform an earlier opening boundary)."""
        for end, close in mark:
            self.mark_closes[_iso(end)] = str(close)
        for it in items:
            if isinstance(it, tuple):
                self._gap(it[1], it[2])
                end = it[1] + MINUTE
                self.last_trade_end = max(self.last_trade_end or end, end)
                continue
            if self.last_trade_end is not None and it.start > self.last_trade_end:
                self._gap(self.last_trade_end, "TRADE_1M_DISCONTINUITY")
            self._minute(it)
            self.last_trade, self.last_trade_end = it, it.end
            self._resolve_samples(it)
        if len(self.mark_closes) > 600:
            for k in sorted(self.mark_closes)[:-600]:
                del self.mark_closes[k]

    def on_funding(self, x: dict) -> None:
        self.funding.append(x)

    def on_journal(self, entries: list[dict]) -> None:
        for e in entries:
            k = e["kind"]
            if k == "call":
                self._new_call(e["record"])
            elif k == "call_revision":
                self._revision(e["record"])
            elif k == "candidate":
                self._candidate(e["record"])

    def after_dispatch(self, t: datetime, core) -> None:
        """Hourly MarketView/persistence sample at a UTC hour, after every dispatch update at that time."""
        if not self.sample_views or self.eval_start is None:
            return
        if self.next_sample is None:
            self.next_sample = self.eval_start
        while self.next_sample is not None and self.next_sample <= t and (self.eval_end is None or
                                                                           self.next_sample < self.eval_end):
            if self.next_sample == t:
                self._sample(t, core)
            else:
                self._sample(self.next_sample, None)  # no dispatch at that hour: nothing assessable was known
            self.next_sample = self.next_sample + timedelta(hours=1)

    def finish(self, t: datetime) -> None:
        self.now = t
        for cid in sorted(self.calls):
            c = self.calls[cid]
            for v in sorted(c["paths"]):
                ps = c["paths"][v]
                if ps.status == "DONE":
                    continue
                if ps.status == "WAIT_ENTRY" and c["terminal"] is not None:
                    self._close(c, ps, "NO_ENTRY", "CALL_TERMINAL_BEFORE_QUALIFYING_OPEN", None, None)
                else:
                    self._close(c, ps, "UNRESOLVED", "DATA_OR_TAIL_END_BEFORE_REQUIRED_EVIDENCE", None,
                                _dt(ps.last_end) if ps.last_end else None)
        for s in self.samples:
            s.setdefault("outcome_1h", None)
            s.setdefault("outcome_4h", None)
            self._emit_sample(s)
        self.samples = []

    # ---------------------------------------------------------------------------------------------------------
    # calls
    # ---------------------------------------------------------------------------------------------------------

    def _in_window(self, t: datetime) -> bool:
        return (self.eval_start is None or t >= self.eval_start) and (self.eval_end is None or t < self.eval_end)

    def _new_call(self, r: dict) -> None:
        issued = _dt(r["issued_at"])
        if not self._in_window(issued) or r["env"]["origin"] != "HISTORICAL_MODELED":
            return
        d = 1 if r["direction"] == "LONG" else -1
        hard = _dt(r["hard_deadline"]) - issued
        c = {"cid": r["call_id"], "attempt": r["attempt_id"], "family": r["family"], "d": d, "issued_at": r["issued_at"],
             "v": r["invalidation"], "t": r["target"], "area": list(r["structural_area"]), "hard": hard.total_seconds(),
             "timeline": [[r["issued_at"], True, True]], "terminal": None, "paths": {}}
        for variant, delay in (("PRIMARY", self.p.eval_primary_delay), ("ENTRY_DELAY_0", 0), ("ENTRY_DELAY_120", 120)):
            c["paths"][variant] = PathState(variant, delay, "GUIDANCE",
                                            next_boundary=_iso(ceil_minute(issued + timedelta(seconds=delay))))
        c["paths"]["HORIZON_ONLY"] = PathState("HORIZON_ONLY", self.p.eval_primary_delay, "HORIZON_ONLY",
                                               next_boundary=None)
        c["paths"]["HORIZON_ONLY"].pending_exit_at = _iso(ceil_minute(issued + hard +
                                                                     timedelta(seconds=self.p.eval_exit_delay)))
        self.calls[c["cid"]] = c

    def _revision(self, r: dict) -> None:
        c = self.calls.get(r["call_id"])
        if c is None:
            return
        at = r["env"]["published_at"]
        ongoing = r["thesis_status"] == "ONGOING"
        c["timeline"].append([at, bool(r["entry_conditions_enabled"]) and ongoing, ongoing])
        if not ongoing and c["terminal"] is None:
            c["terminal"] = {"status": r["thesis_status"], "reason": r["terminal_reason"], "at": at}
            if r["thesis_status"] in ("RETIRED", "UNASSESSABLE", "TIME_EXPIRED"):
                gap = r["thesis_status"] == "UNASSESSABLE" and "GAP" in (r["terminal_reason"] or "")
                for v, ps in c["paths"].items():
                    if v == "HORIZON_ONLY" or ps.status != "OPEN" or gap:
                        continue  # a missing interval censors the path itself; it is not repaired by an exit print
                    if ps.pending_exit_at is None:
                        ps.pending_exit_at = _iso(ceil_minute(_dt(at) + timedelta(seconds=self.p.eval_exit_delay)))
                        ps.exit_class = f"GUIDANCE_{r['thesis_status']}"

    def _candidate(self, r: dict) -> None:
        if r["transition"] in ("ISSUE", "REJECT"):
            for s in self.samples:
                if s.get("scenario_id") == r["attempt_id"] and s.get("activated_at") is None:
                    s["activated_at"] = r["env"]["published_at"]

    def _state_at(self, c: dict, s: datetime) -> tuple[bool, bool]:
        """(entry enabled, thesis ongoing) per the latest revision published at or before s."""
        enabled, ongoing = False, False
        for at, en, og in c["timeline"]:
            if _dt(at) <= s:
                enabled, ongoing = en, og
            else:
                break
        return enabled, ongoing

    # ---------------------------------------------------------------------------------------------------------
    # minutes
    # ---------------------------------------------------------------------------------------------------------

    def _minute(self, m: Bar) -> None:
        for cid in sorted(self.calls):
            c = self.calls[cid]
            for v in ("PRIMARY", "ENTRY_DELAY_0", "ENTRY_DELAY_120", "HORIZON_ONLY"):
                ps = c["paths"].get(v)
                if ps is None or ps.status == "DONE":
                    continue
                if ps.status == "WAIT_ENTRY":
                    if v == "HORIZON_ONLY":
                        continue  # conditioned on the primary entry (copied when it enters)
                    self._try_entry(c, ps, m)
                    if ps.status != "OPEN":
                        continue
                    if v == "PRIMARY":
                        h = c["paths"]["HORIZON_ONLY"]
                        h.status, h.entry_price, h.entry_time = "OPEN", ps.entry_price, ps.entry_time
                        h.attempts, h.rejected = ps.attempts, ps.rejected
                        self._path_minute(c, h, m)
                    self._path_minute(c, ps, m)
                elif ps.status == "OPEN":
                    self._path_minute(c, ps, m)
        self._prune()

    def _try_entry(self, c: dict, ps: PathState, m: Bar) -> None:
        nb = _dt(ps.next_boundary)
        if m.start < nb:
            return
        enabled, ongoing = self._state_at(c, m.start)
        if not ongoing:
            self._close(c, ps, "NO_ENTRY", "CALL_TERMINAL_BEFORE_QUALIFYING_OPEN", None, None)
            return
        ps.next_boundary = _iso(m.end)
        if not enabled:
            return
        ps.attempts += 1
        d = c["d"]
        p = m.o
        area = (Decimal(c["area"][0]), Decimal(c["area"][1]))
        chk = geo.predicate(d, p, Decimal(c["v"]), Decimal(c["t"]), self.k, self.p.rr_min)
        if not geo.in_area(p, area) or not chk.ok:
            ps.rejected += 1
            return
        ps.status, ps.entry_price, ps.entry_time = "OPEN", str(p), _iso(m.start)

    def _path_minute(self, c: dict, ps: PathState, m: Bar) -> None:
        d = c["d"]
        v_t, t_t = Decimal(c["v"]) * d, Decimal(c["t"]) * d
        o_t = m.o * d
        h_t, l_t = (m.h, m.lo) if d > 0 else (-m.lo, -m.h)
        if ps.last_end is not None and m.start > _dt(ps.last_end):
            self._close(c, ps, "CENSORED", "MISSING_PATH_MINUTE", None, _dt(ps.last_end))
            return
        pe = _dt(ps.pending_exit_at) if ps.pending_exit_at else None
        if pe is not None and m.start == pe:
            if ps.exit_mode == "HORIZON_ONLY":
                self._fill_exit(c, ps, m.o, "DISCRETIONARY_OPEN", m.start, m.start, "HORIZON_EXIT")
            elif o_t <= v_t:
                self._fill_exit(c, ps, m.o, "STOP_GAP_ADVERSE_OPEN", m.start, m.start, "STOP_GAP")
            elif o_t >= t_t:
                self._fill_exit(c, ps, Decimal(c["t"]), "TARGET_GAP_CONSERVATIVE", m.start, m.start, "TARGET_GAP")
            else:
                self._fill_exit(c, ps, m.o, "DISCRETIONARY_OPEN", m.start, m.start, ps.exit_class or "GUIDANCE")
            return
        if pe is not None and m.start > pe:
            raise RuntimeError(f"path {c['cid']}/{ps.variant}: pending exit boundary {pe} skipped")
        ps.last_end = _iso(m.end)
        ps.hi_t = str(max(Decimal(ps.hi_t), h_t)) if ps.hi_t else str(h_t)
        ps.lo_t = str(min(Decimal(ps.lo_t), l_t)) if ps.lo_t else str(l_t)
        if ps.exit_mode == "HORIZON_ONLY":
            return
        if o_t <= v_t:
            # MP-001 §11: a protective stop gap fills at the adverse open (known model opening boundary), never at V;
            # the open is the minute's first known price, so later intrabar levels cannot change it.
            self._fill_exit(c, ps, m.o, "STOP_GAP_ADVERSE_OPEN", m.start, m.start, "STOP_GAP")
            return
        hit_t, hit_v = h_t >= t_t, l_t <= v_t
        if hit_t and hit_v:
            self._close(c, ps, "AMBIGUOUS", "BOTH_T_AND_V_IN_ONE_MINUTE", None, None, interval=(m.start, m.end))
        elif hit_t:
            self._fill_exit(c, ps, Decimal(c["t"]), "TARGET_TOUCH", m.start, m.end, "TARGET")
        elif hit_v:
            self._fill_exit(c, ps, Decimal(c["v"]), "STOP_TOUCH", m.start, m.end, "STOP")

    def _gap(self, start: datetime, reason: str) -> None:
        for cid in sorted(self.calls):
            c = self.calls[cid]
            for v in sorted(c["paths"]):
                ps = c["paths"][v]
                if ps.status == "OPEN":
                    self._close(c, ps, "CENSORED", f"MISSING_PATH_MINUTE:{reason}", None, start)
                elif ps.status == "WAIT_ENTRY" and ps.next_boundary and start >= _dt(ps.next_boundary):
                    ps.next_boundary = _iso(start + MINUTE)  # no observable open at that boundary
        self._prune()

    # ---------------------------------------------------------------------------------------------------------
    # accounting / records
    # ---------------------------------------------------------------------------------------------------------

    def _fill_exit(self, c: dict, ps: PathState, price: Decimal, reason: str, t0: datetime, t1: datetime,
                   klass: str) -> None:
        self._close(c, ps, "CLOSED", klass, Fill(price=price, reason=reason, time_start=t0, time_end=t1), None)

    def _funding(self, c: dict, e: Decimal, entry_t: datetime, x: Fill | None) -> tuple[Decimal | None, str]:
        if self.funding_mode != "AUTHORITATIVE_IF_COVERED":
            return None, "PRICE_NET_ONLY_TOTAL_NET_UNAVAILABLE"
        if x is None:
            return None, "NO_EXIT_TOTAL_NET_UNAVAILABLE"
        d = c["d"]
        total = Decimal(0)
        for f in self.funding:
            u = _dt(f["event_time"])
            if u <= entry_t:
                continue  # entered strictly before u is required; an entry exactly at u neither pays nor receives
            if x.time_start == x.time_end:  # certified open boundary
                if u > x.time_start:
                    continue
            else:  # intrabar protective fill: [minute_start, minute_end)
                if u >= x.time_end:
                    continue  # protection exited before the settlement
                if x.time_start < u < x.time_end:
                    return None, "FUNDING_OWNERSHIP_AMBIGUOUS_TOTAL_NET_UNAVAILABLE"
            mark = self.mark_closes.get(_iso(u))
            if mark is None:
                return None, "SETTLEMENT_MARK_PRICE_MISSING_TOTAL_NET_UNAVAILABLE"
            total += -d * div(Decimal(mark) * Decimal(f["rate"]), e)
        return total, "AUTHORITATIVE_COVERED"

    def _close(self, c: dict, ps: PathState, status: str, klass: str, x: Fill | None,
               censored_from: datetime | None, interval: tuple | None = None) -> None:
        d = c["d"]
        entry = None
        e = Decimal(ps.entry_price) if ps.entry_price else None
        if e is not None:
            entry = Fill(price=e, reason="OPEN", time_start=_dt(ps.entry_time), time_end=_dt(ps.entry_time))
        gross = fees = allow = net = stress = funding = total = None
        fstatus = "NO_ENTRY" if e is None else "PRICE_NET_ONLY_TOTAL_NET_UNAVAILABLE"
        bounds: dict[str, Decimal | None] = {}
        if e is not None and x is not None:
            with localcontext() as ctx:  # one declared precision for every accounting step (deterministic)
                ctx.prec = PRECISION
                r = x.price / e
                gross = d * (r - 1)
                fees = self.f * (1 + r)
                allow = self.a * (1 + r)
                net = gross - fees - allow
                stress = gross - fees - self.a_stress * (1 + r)
                funding, fstatus = self._funding(c, e, entry.time_start, x)
                total = None if funding is None else net + funding
        if e is not None and status == "AMBIGUOUS":
            for name, px in (("favorable_target", Decimal(c["t"])), ("adverse_stop", Decimal(c["v"]))):
                r = div(px, e)
                bounds[f"{name}_price_net"] = d * (r - 1) - (self.f + self.a) * (1 + r)
        mfe = mae = None
        if e is not None and ps.hi_t is not None:
            mfe = div(Decimal(ps.hi_t) - e * d, e)
            mae = div(Decimal(ps.lo_t) - e * d, e)
        if e is not None and status in ("CENSORED", "UNRESOLVED"):
            bounds["known_prefix_mfe"], bounds["known_prefix_mae"] = mfe, mae
        held = None
        if e is not None and x is not None:
            held = Decimal(int((x.time_start - entry.time_start).total_seconds())) / 60
        path = HypotheticalPath(
            path_id=f"{c['cid']}#{ps.variant.lower()}", call_id=c["cid"], profile=self.profile(ps.variant),
            variant=ps.variant, family=c["family"], direction="LONG" if d > 0 else "SHORT", status=status,
            exit_class=klass, entry=entry, exit=x, entry_attempts=ps.attempts, rejected_opens=ps.rejected,
            gross=gross, fees=fees, allowances=allow, price_net=net,
            stress_price_net=stress if ps.variant == "PRIMARY" else None, funding=funding, total_net=total,
            funding_status=fstatus, bounds=bounds, mfe=mfe, mae=mae, held_minutes=held, censored_from=censored_from,
            notes=tuple(ps.notes + ([f"ambiguous minute {interval[0].isoformat()}"] if interval else [])),
            resolved_at=self.now)
        ps.status = "DONE"
        self._emit("path", json.loads(path.model_dump_json()))
        if ps.variant == "PRIMARY" and status == "NO_ENTRY":
            h = c["paths"].get("HORIZON_ONLY")
            if h is not None and h.status == "WAIT_ENTRY":
                self._close(c, h, "NO_ENTRY", "PRIMARY_PATH_NO_ENTRY", None, None)
        agg = self.aggregates["paths"].setdefault(ps.variant, {})
        agg[status] = agg.get(status, 0) + 1

    def _prune(self) -> None:
        for cid in [k for k, c in self.calls.items() if all(p.status == "DONE" for p in c["paths"].values())]:
            del self.calls[cid]
        if not self.calls and self.funding:
            last = self.last_trade_end
            self.funding = [f for f in self.funding if last is None or _dt(f["event_time"]) >= last]

    def _emit(self, kind: str, doc: dict) -> None:
        self.record_seq += 1
        digest = hashlib.sha256(canonical(doc)).hexdigest()
        self.record_chain = hashlib.sha256(bytes.fromhex(self.record_chain) + bytes.fromhex(digest)).hexdigest()
        self.records.append({"seq": self.record_seq, "kind": kind, "record_id": doc.get("path_id") or
                             f"sample-{doc.get('sample_time')}", "digest": digest, "chain": self.record_chain,
                             "record": doc})

    # ---------------------------------------------------------------------------------------------------------
    # view samples
    # ---------------------------------------------------------------------------------------------------------

    def _sample(self, h: datetime, core) -> None:
        s: dict[str, Any] = {"sample_time": _iso(h), "anchor_price": None, "view": "UNAVAILABLE", "conditional": False,
                             "scenario_id": None, "persistence": None, "activated_at": None}
        if core is not None:
            lb = core.last_1m
            if lb is not None and lb.known_at <= h and core.ready_1m(h):
                s["anchor_price"] = str(lb.c)
            v = core.view or {}
            if v:
                s["view"] = v["expected_direction"]
                s["conditional"] = bool(v.get("conditional"))
                s["scenario_id"] = (v.get("principal") or {}).get("scenario_id")
            h1 = list(core.h1)
            if len(h1) >= 2 and core.ready_1h(h) and h1[-1].start == h1[-2].end:
                s["persistence"] = _sign(h1[-1].c - h1[-2].c)
        self.aggregates["samples"]["taken"] += 1
        if s["anchor_price"] is None:
            s["outcome_1h"] = s["outcome_4h"] = None
            s["return_1h"] = s["return_4h"] = None
            self._emit_sample(s)
            return
        self.samples.append(s)

    def _resolve_samples(self, m: Bar) -> None:
        keep = []
        for s in self.samples:
            h = _dt(s["sample_time"])
            a = Decimal(s["anchor_price"])
            for hrs in (1, 4):
                key = f"outcome_{hrs}h"
                if key in s:
                    continue
                end = h + timedelta(hours=hrs)
                if m.end == end:
                    s[key] = _sign(m.c - a)
                    s[f"return_{hrs}h"] = str(div(m.c - a, a))
                elif m.end > end:
                    s[key], s[f"return_{hrs}h"] = None, None  # endpoint minute missing: unavailable, not guessed
            if "outcome_1h" in s and "outcome_4h" in s:
                self._emit_sample(s)
            else:
                keep.append(s)
        self.samples = keep

    def _emit_sample(self, s: dict) -> None:
        h = _dt(s["sample_time"])

        def act(hrs: int) -> bool | None:
            if not s.get("scenario_id"):
                return None
            at = _dt(s.get("activated_at"))
            return at is not None and at <= h + timedelta(hours=hrs)

        vs = ViewSample(sample_time=h, anchor_price=Decimal(s["anchor_price"]) if s.get("anchor_price") else None,
                        view=s["view"], conditional=s["conditional"], scenario_id=s.get("scenario_id"),
                        persistence=s.get("persistence"), outcome_1h=s.get("outcome_1h"),
                        outcome_4h=s.get("outcome_4h"),
                        return_1h=Decimal(s["return_1h"]) if s.get("return_1h") else None,
                        return_4h=Decimal(s["return_4h"]) if s.get("return_4h") else None,
                        antecedent_activated_1h=act(1), antecedent_activated_4h=act(4))
        self._emit("view_sample", json.loads(vs.model_dump_json()))

    # ---------------------------------------------------------------------------------------------------------
    # codec
    # ---------------------------------------------------------------------------------------------------------

    def encode(self) -> dict:
        calls = {}
        for cid, c in sorted(self.calls.items()):
            calls[cid] = {**{k: v for k, v in c.items() if k != "paths"},
                          "paths": {v: ps.encode() for v, ps in sorted(c["paths"].items())}}
        return {"format": STATE_FORMAT, "calls": calls, "record_seq": self.record_seq,
                "record_chain": self.record_chain, "samples": self.samples, "next_sample": _iso(self.next_sample),
                "funding": self.funding, "mark_closes": dict(sorted(self.mark_closes.items())),
                "last_trade": self.last_trade.encode() if self.last_trade else None,
                "last_trade_end": _iso(self.last_trade_end), "aggregates": self.aggregates,
                "pending_records": self.records}

    def restore(self, doc: dict) -> None:
        if doc.get("format") != STATE_FORMAT:
            raise ValueError(f"evaluator state format {doc.get('format')!r} is not {STATE_FORMAT}")
        self.calls = {}
        for cid, c in doc["calls"].items():
            self.calls[cid] = {**{k: v for k, v in c.items() if k != "paths"},
                               "paths": {v: PathState.decode(ps) for v, ps in c["paths"].items()}}
        self.record_seq, self.record_chain = doc["record_seq"], doc["record_chain"]
        self.samples = list(doc["samples"])
        self.next_sample = _dt(doc["next_sample"])
        self.funding = list(doc["funding"])
        self.mark_closes = dict(doc["mark_closes"])
        self.last_trade = Bar.decode(doc["last_trade"]) if doc["last_trade"] else None
        self.last_trade_end = _dt(doc["last_trade_end"])
        self.aggregates = doc["aggregates"]
        self.records = list(doc["pending_records"])
