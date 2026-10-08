"""MP-004 ``btc.context-action.v0.5`` professional fold (implementation ``adviser.core.v5``; state
``algotrader.adviser-state.v5``).

It is the v0.4 fold (``core4.AdviserCoreV4``: MP-003 pre-confirmation anchors over MP-002 v0.3) with ONLY the A RETURN
child changed (MP-004 §§1–5). Scenarios, anchors, confirmation, routing, IMMEDIATE, B/C, the inherited WAIT
protections (timers, context veto, target/cap contacts, causal caps), costs, deadlines, selection, issued-call
protection and the evaluator are inherited unchanged.

* **WAIT_RETURN** (the inherited WAIT_PRICE): the first complete 1m bar that would be a usable v0.4 RETURN (corridor,
  economics, non-selection gates, post-confirmation domain, no forbidden contact) no longer enters selection: it
  PREPARES one immutable local reference - H0/L0, bar id and interval, the actual publication p0 (this dispatch) and
  the admitted factual cursor c0. A blocked bar does not prepare. No replacement, retry or renewal.
* **WAIT_RESPONSE**: every later complete bar of the local domain is checked; the domain starts at p0 (a bar ending
  at/before p0 gives no local response; a bar straddling p0 cannot confirm and, if it breaks the contrary extreme,
  makes the child UNASSESSABLE ``LOCAL_CONTACT_TIME_AMBIGUOUS``; no bar admitted in the preparation dispatch is ever
  examined). LONG contradiction ``low < L0``; recovery ``close >= H0 + tick`` and ``low >= L0`` (SHORT reflects);
  contrary equality is allowed; a violation and a favourable close in one bar is a contradiction. Within one dispatch
  every bar feeds the safety checks first (inherited protections, then local contradiction/ambiguity, MP-004 §2
  decision order) and only then the first ordered recovery decides.
* **First recovery**: evaluated once in the same dispatch. If it is not the current usable bar (the dispatch's latest
  complete minute, the inherited sampling) it is a late observation: not issuable, no later bar searched. Otherwise
  the inherited return gates are re-evaluated on it (current cap/corridor/zones, economics at the historical close or
  the live side price, context/coverage/freshness, residual time) and then slot/conflict/priority: ISSUE, or the
  child ends ``RESPONSE_NOT_ISSUABLE`` with every blocker and one deterministic primary reason. Pre-recovery
  emptiness of the corridor/economic region is evaluated at that bar (MP-004 §2/§4 order), never terminal earlier.

Records: the v0.4 kinds; the ``entry_attempt`` variant ``EntryAttemptV5`` adds ``response`` (reference, phase, bars
checked, decisive bar and outcome). RESPONSE_OBSERVED is never stored state: the dispatch ends with ISSUE or a
terminal record carrying the observation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from . import contracts as sc
from . import geometry as geo
from .core import _d, _dt, _iso, _s, dname, tbar
from .core3 import Scen, Wait
from .core4 import AdviserCoreV4
from .identity import Execution
from .measures import Bar

STATE_FORMAT = "algotrader.adviser-state.v5"

# MP-004 §7: deterministic primary reason of a not-issuable first recovery = first class, then the sorted code
ECONOMICS_GEOMETRY = frozenset({
    "EMPTY_RETURN_CORRIDOR", "CLOSE_OUTSIDE_RETURN_CORRIDOR", "SIDE_PRICE_OUTSIDE_RETURN_CORRIDOR", "BLOCKED_BY_ZONE",
    "SIDE_PRICE_INSIDE_OPPOSING_ZONE", "NO_ECONOMIC_RETURN_REGION", "TEMPORARY_COST_BLOCKED", "NO_ROOM_AFTER_COSTS",
    "AT_OR_BEYOND_INVALIDATION", "REWARD_RISK_BELOW_MINIMUM", "INVALID_INPUT"})
SELECTION = frozenset({"SLOT_OCCUPIED", "CONFLICTED", "PRIORITY"})
LATE = "RESPONSE_OBSERVED_LATE_NOT_CURRENT"
REASON_CLASSES = ("ECONOMICS_GEOMETRY", "OTHER_GATES", "SELECTION")


def reason_class(code: str) -> str:
    c = code.split(":")[0]
    if c == LATE:
        return "LATE_OBSERVATION"
    return "ECONOMICS_GEOMETRY" if c in ECONOMICS_GEOMETRY else "SELECTION" if c in SELECTION else "OTHER_GATES"


def primary_reason(blockers: list[str]) -> str:
    """One deterministic primary reason (MP-004 §7): economics/geometry, then other gates, then selection; inside a
    class the smallest code. Every blocker stays recorded; incidences are never summed."""
    order = {c: i for i, c in enumerate(("LATE_OBSERVATION",) + REASON_CLASSES)}
    return min(blockers, key=lambda b: (order[reason_class(b)], b.split(":")[0]))


def local_verdict(d: int, h0: Decimal, l0: Decimal, tick: Decimal, low: Decimal, high: Decimal,
                  close: Decimal) -> str:
    """MP-004 §1 predicate of one complete bar against a prepared reference: CONTRADICTION / RECOVERY / NONE.
    LONG: contradiction low < L0; recovery close >= H0 + tick (and low >= L0). SHORT: contradiction high > H0;
    recovery close <= L0 - tick (and high <= H0). Contrary equality is allowed; violation wins in the same bar."""
    if d > 0:
        if low < l0:
            return "CONTRADICTION"
        return "RECOVERY" if close >= h0 + tick else "NONE"
    if high > h0:
        return "CONTRADICTION"
    return "RECOVERY" if close <= l0 - tick else "NONE"


@dataclass
class Wait5(Wait):
    """The v0.4 WAIT_PRICE child plus the MP-004 phase and its single immutable local reference (market prices)."""

    phase: str = "WAIT_RETURN"  # WAIT_RETURN (inherited WAIT_PRICE) / WAIT_RESPONSE
    ref: dict | None = None  # {bar, start, end, H0, L0, close, published_at (p0), cursor (c0)}: set once, never moved
    checked: int = 0  # complete bars examined in the local domain (audit)


class AdviserCoreV5(AdviserCoreV4):
    WAIT_CLS = Wait5
    STATE_FMT = STATE_FORMAT
    KINDS = sc.KIND_CONTRACTS_V5

    def __init__(self, config) -> None:
        super().__init__(config)
        self.counters["v5"] = {"references_prepared": 0, "local_contradictions": 0, "local_ambiguous": 0,
                               "responses_observed": 0, "late_responses": 0, "not_issuable": 0, "issued": 0,
                               "ended_after_reference": 0}
        # transient per-dispatch context (never encoded: a restore happens between dispatches)
        self._disp_bars: list[Bar] = []
        self._notes: dict[str, dict[str, str | None]] = {}
        self._closing: Wait5 | None = None

    # ----------------------------------------------------------------------------------------------------------
    # dispatch context
    # ----------------------------------------------------------------------------------------------------------

    def dispatch(self, t: datetime) -> list[dict]:
        self._disp_bars, self._notes = [], {}
        return super().dispatch(t)

    def _ingest_minutes(self, bars, t: datetime):
        items = super()._ingest_minutes(bars, t)
        self._disp_bars = [x for x in items if isinstance(x, Bar)]
        return items

    def _count(self, key: str) -> None:
        if self.window == "EVALUATION":
            self.counters["v5"][key] += 1

    # ----------------------------------------------------------------------------------------------------------
    # WAIT_RETURN -> prepared reference
    # ----------------------------------------------------------------------------------------------------------

    def _wait_step(self, s: Scen, w: Wait5, minutes: list[Bar], zones: list, t: datetime) -> dict | None:
        if w.phase == "WAIT_RESPONSE":
            return self._response_step(s, w, minutes, zones, t)
        return super()._wait_step(s, w, minutes, zones, t)

    def _return_usable(self, s: Scen, w: Wait5, m: Bar, cor, econ, price, source, k, chk, t: datetime) -> None:
        """The first usable return PREPARES the reference instead of entering selection (MP-004 §1)."""
        self.counters["v3"]["usable_returns"] += 1
        w.phase = "WAIT_RESPONSE"
        w.ref = {"bar": m.rid, "start": _iso(m.start), "end": _iso(m.end), "H0": str(m.h), "L0": str(m.lo),
                 "close": str(m.c), "published_at": _iso(t), "cursor": str(self.cursor)}
        self._count("references_prepared")
        self._emit_wait(s, w, "RESPONSE_REFERENCE", m.rid, t, price=price, k=k, chk=chk, econ=econ)
        self._touch()
        return None

    # ----------------------------------------------------------------------------------------------------------
    # WAIT_RESPONSE
    # ----------------------------------------------------------------------------------------------------------

    def _response_step(self, s: Scen, w: Wait5, minutes: list[Bar], zones: list, t: datetime) -> dict | None:
        ref = w.ref
        p0 = _dt(ref["published_at"])
        d, tick = w.d, self.tick
        h0, l0 = Decimal(ref["H0"]), Decimal(ref["L0"])
        first: Bar | None = None
        end: tuple[str, Bar] | None = None
        for m in minutes:
            if m.end <= p0:
                continue  # wholly at/before the publication: no local response
            w.checked += 1
            v = local_verdict(d, h0, l0, tick, m.lo, m.h, m.c)
            if m.start < p0:  # straddles p0: can never confirm; a contrary break cannot be dated
                if v == "CONTRADICTION":
                    end = ("LOCAL_CONTACT_TIME_AMBIGUOUS", m)
                    break
                continue
            if v == "CONTRADICTION":
                end = ("LOCAL_RESPONSE_CONTRADICTED", m)
                break
            if v == "RECOVERY" and first is None:
                first = m
        if end is not None:  # local contradiction / ambiguity precede the recovery (MP-004 §2)
            reason, m = end
            note = {"outcome": "CONTRADICTED" if reason == "LOCAL_RESPONSE_CONTRADICTED" else "UNASSESSABLE",
                    **_bar_note("decisive", m)}
            if first is not None:
                note["recovery_close_observed_before_priority"] = first.rid
            self._notes[s.eid] = note
            self._count("local_contradictions" if note["outcome"] == "CONTRADICTED" else "local_ambiguous")
            self._wait_end(s, w, f"{reason}:{m.rid}", t)
            return None
        if first is None:
            return None
        self._count("responses_observed")
        current = first is minutes[-1]
        note = {**_bar_note("response", first), "response_current": str(current).lower()}
        if not current:  # first recovery observed late: not issuable, no later bar searched (MP-004 §3/§8)
            self._count("late_responses")
            self._not_issuable(s, w, note, [LATE], t)
            return None
        p = self.p
        cor = w.corridor(tick)
        price, source, k, qb = self._side_price(d, t)
        hist = self.cfg.profile.execution == Execution.HISTORICAL_BASE
        econ = (geo.admissible_bounds(d, cor, w.v, w.cap, k, p.rr_min, tick)
                if k is not None and cor is not None else None)
        blockers, price, source, chk = self._return_gates(s, w, first, cor, econ, zones, price, source, k, qb, t)
        if hist and cor is not None and econ is None:
            blockers = sorted(set(blockers) | {"NO_ECONOMIC_RETURN_REGION"})
        if blockers:
            self._not_issuable(s, w, note, blockers, t, price=price, k=k, chk=chk, econ=econ)
            return None
        note["outcome"] = "ISSUED"  # provisional: selection may still reject (then NOT_ISSUABLE)
        self._notes[s.eid] = note
        return self._return_candidate(s, w, first, cor, price, source, k, chk)

    def _not_issuable(self, s: Scen, w: Wait5, note: dict, blockers: list[str], t: datetime, *, transition="TERMINAL",
                      price=None, k=None, chk=None, econ=None) -> None:
        prim = primary_reason(blockers)
        note.update(outcome="NOT_ISSUABLE", primary_reason=prim, primary_class=reason_class(prim))
        self._notes[s.eid] = note
        self._count("not_issuable")
        g = self._wait_geometry(w)
        g.update(price=_s(price), K_cost=_s(k), economic_current=_rng(econ),
                 G=_s(chk.g if chk else None), Q=_s(chk.q if chk else None), margin=_s(chk.margin if chk else None))
        self._entry_end(s, "TERMINAL", transition, f"RESPONSE_NOT_ISSUABLE:{prim}", t, blockers=sorted(set(blockers)),
                        geometry=g, cap_history=w.caps)

    def _return_rejected(self, e: dict, transition: str, reasons: list[str], t: datetime) -> None:
        w, s = e["wait"], e["s"]
        if w.ref is None:  # not reachable: every v0.5 RETURN candidate comes from a first recovery
            super()._return_rejected(e, transition, reasons, t)
            return
        note = dict(self._notes.get(s.eid) or {})
        self._not_issuable(s, w, note, list(reasons), t, transition=transition, price=e["price"], k=e["k"],
                           chk=e["chk"])

    def _issue3(self, e: dict, t: datetime) -> None:
        w = e.get("wait")
        if w is not None:
            self._count("issued")
        self._closing = w
        try:
            super()._issue3(e, t)
        finally:
            self._closing = None

    def _entry_end(self, s: Scen, state: str, transition: str, reason: str, t: datetime, **kw) -> None:
        w = self.waits.get(s.eid)
        if w is not None and w.ref is not None and s.eid not in self._notes and s.entry in ("PENDING", "WAIT"):
            # ended by an inherited / priority cause while waiting for the response (MP-004 §2: X)
            note: dict[str, str | None] = {"outcome": "CLEARED" if state == "CLEARED" else "ENDED_BY_PRIORITY_CAUSE"}
            note.update(self._priority_annotation(w))
            self._notes[s.eid] = note
            self._count("ended_after_reference")
        self._closing = w
        try:
            super()._entry_end(s, state, transition, reason, t, **kw)
        finally:
            self._closing = None

    def _priority_annotation(self, w: Wait5) -> dict[str, str | None]:
        """Local conditions observed in this dispatch's bars when an inherited cause ended the child first: annotated
        without counting a second terminal and never as a decisive recovery (MP-004 §2)."""
        p0 = _dt(w.ref["published_at"])
        h0, l0 = Decimal(w.ref["H0"]), Decimal(w.ref["L0"])
        for m in self._disp_bars:
            if m.start < p0:
                continue
            v = local_verdict(w.d, h0, l0, self.tick, m.lo, m.h, m.c)
            if v != "NONE":
                return {"observed_in_priority_dispatch": f"{v}:{m.rid}"}
        return {}

    # ----------------------------------------------------------------------------------------------------------
    # records / views
    # ----------------------------------------------------------------------------------------------------------

    def _emit_entry(self, s: Scen, state: str, *a, **kw) -> None:
        w = self.waits.get(s.eid)
        if state == "WAIT_PRICE" and w is not None and w.phase == "WAIT_RESPONSE":
            state = "WAIT_RESPONSE"
        super()._emit_entry(s, state, *a, **kw)

    def _entry_extra(self, s: Scen) -> dict:
        w = self.waits.get(s.eid)
        if w is None and self._closing is not None and self._closing.sid == s.sid:
            w = self._closing
        return {"response": self._response_doc(s, w)}

    def _response_doc(self, s: Scen, w: Wait5 | None) -> dict[str, str | None] | None:
        if w is None or w.ref is None:
            return None
        r = w.ref
        doc: dict[str, str | None] = {
            "phase": w.phase, "reference_bar": r["bar"], "reference_start": r["start"], "reference_end": r["end"],
            "H0": r["H0"], "L0": r["L0"], "reference_close": r["close"], "published_at": r["published_at"],
            "published_cursor": r["cursor"], "bars_checked": str(w.checked), "outcome": None}
        doc.update(self._notes.get(s.eid) or {})
        return {k: doc[k] for k in sorted(doc)}

    def _diag_conditions(self, t: datetime) -> list[str]:
        out = set(super()._diag_conditions(t))
        if any(w.phase == "WAIT_RESPONSE" for w in self.waits.values()):
            out.add("WAITING_FOR_LOCAL_RESPONSE")
            if all(w.phase == "WAIT_RESPONSE" for w in self.waits.values()):
                out.discard("WAITING_FOR_USABLE_PRICE")
        return sorted(out)

    def scenarios_view(self, t: datetime | None) -> list[dict]:
        rows = super().scenarios_view(t)
        for row in rows:
            w = self.waits.get(f"{row['scenario_id']}#entry")
            if w is None or w.phase != "WAIT_RESPONSE" or "waiting" not in row:
                continue
            r = w.ref
            row["waiting"]["text"] = ("Scenario confirmed; return reference prepared — waiting for a local recovery "
                                      "close (no call yet, no entry).")
            row["waiting"]["phase"] = "WAIT_RESPONSE"
            row["waiting"]["response"] = {
                "reference_bar": r["bar"], "H0": r["H0"], "L0": r["L0"], "published_at": r["published_at"],
                "recovery_close": str(Decimal(r["H0"]) + self.tick) if w.d > 0 else str(Decimal(r["L0"]) - self.tick),
                "recovery_rule": (f"a later complete 1m close >= {Decimal(r['H0']) + self.tick} with low >= {r['L0']}"
                                  if w.d > 0 else
                                  f"a later complete 1m close <= {Decimal(r['L0']) - self.tick} with high <= {r['H0']}"),
                "contradiction_rule": (f"low < {r['L0']} ends this entry attempt" if w.d > 0 else
                                       f"high > {r['H0']} ends this entry attempt"),
                "bars_checked": w.checked}
        for row in rows:
            if "waiting" in row and "phase" not in row["waiting"]:
                row["waiting"]["phase"] = "WAIT_RETURN"
        return rows

    def inspect(self) -> dict:
        out = super().inspect()
        out["method_semantics"] = ("MP-004 v0.5: v0.4 structural scenarios and anchors + A RETURN reference then "
                                   "local recovery + child entry attempts")
        out["responses"] = {eid: {"phase": w.phase, "direction": dname(w.d), "reference": w.ref,
                                  "bars_checked": w.checked}
                            for eid, w in sorted(self.waits.items())}
        return out


def _bar_note(prefix: str, m: Bar) -> dict[str, str | None]:
    return {f"{prefix}_bar": m.rid, f"{prefix}_low": str(m.lo), f"{prefix}_high": str(m.h),
            f"{prefix}_close": str(m.c)}


def _rng(x) -> str | None:
    return None if x is None else f"{x[0]}..{x[1]}"


_ = (_d,)
