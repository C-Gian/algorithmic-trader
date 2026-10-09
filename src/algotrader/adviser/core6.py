"""MP-005 ``btc.context-action.v0.6`` professional fold (implementation ``adviser.core.v6``; state
``algotrader.adviser-state.v6``).

It is the v0.5 fold (``core5.AdviserCoreV5``: MP-004 A RETURN reference then local recovery over the v0.4 anchors) with
ONE addition (MP-005 §§2-5): right after a usable MP-004 RETURN has prepared and published the single local reference,
in the SAME dispatch, the initial compatibility of the confirming close is checked on the tick grid:

* F = {p >= H0 + tick} (LONG) / {p <= L0 - tick} (SHORT): the domain of the confirming CLOSE only;
* C0 = the effective corridor at the preparation (inherited inward rounding, caps updated by the existing precedences);
* A0 = the historical economic region of the fixed registered profile (14 bps, net ratio 1.2, inherited formulas,
  operational V and rounding) - the region ``geometry.admissible_bounds`` already computed for this dispatch;
* historical: F ∩ C0 = ∅ -> terminal ``INITIAL_RESPONSE_INCOMPATIBLE`` base ``CORRIDOR`` (the concurrent economic
  incompatibility is annotated); F ∩ C0 ≠ ∅ and F ∩ C0 ∩ A0 = ∅ -> base ``HISTORICAL_ECONOMICS``;
* live: ONLY F ∩ C0 = ∅ (cost-independent) -> base ``CORRIDOR``; no economic terminal, no future minimum cost: a
  temporary live cost restriction keeps the MP-004 behaviour;
* a single admissible tick is a non-empty intersection; bounds are inclusive where the inherited predicates hold.

The terminal ends the CHILD (never the structural scenario), in the preparation dispatch after the RESPONSE_REFERENCE
record: P and X, never C/R/N/I/A; no renewal, reopening, replacement or later local classification. Inherited
protections keep their precedence (they run before the preparation and keep their own reasons). The certified empty
intersection cannot become non-empty (MP-005 §4: frozen reference/corridor/V/target, caps only tighten, fixed historical
cost), so nothing is re-checked later.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from . import contracts as sc
from .core import _iso, _s
from .core3 import Scen
from .core4 import Scen4
from .core5 import AdviserCoreV5, Wait5, _rng
from .identity import Execution

STATE_FORMAT = "algotrader.adviser-state.v6"
REASON = "INITIAL_RESPONSE_INCOMPATIBLE"
CORRIDOR = "CORRIDOR"
HISTORICAL_ECONOMICS = "HISTORICAL_ECONOMICS"
BASES = (CORRIDOR, HISTORICAL_ECONOMICS)


def f_bound(d: int, h0: Decimal, l0: Decimal, tick: Decimal) -> Decimal:
    """The confirming-close threshold of F (MP-005 §2): LONG H0 + tick (p >= it), SHORT L0 - tick (p <= it)."""
    return h0 + tick if d > 0 else l0 - tick


def f_meet(d: int, thr: Decimal, region: tuple[Decimal, Decimal] | None) -> tuple[Decimal, Decimal] | None:
    """F ∩ region on the tick grid (inclusive bounds; a single price is non-empty); None when empty."""
    if region is None:
        return None
    lo, hi = region
    if d > 0:
        lo = max(lo, thr)
    else:
        hi = min(hi, thr)
    return (lo, hi) if lo <= hi else None


@dataclass(frozen=True)
class Compatibility:
    compatible: bool
    base: str | None  # CORRIDOR / HISTORICAL_ECONOMICS when incompatible
    annotations: tuple[str, ...]  # concurrent incompatibilities annotated (never a second terminal)
    f_bound: Decimal
    f_cap_c0: tuple[Decimal, Decimal] | None
    j0: tuple[Decimal, Decimal] | None  # historical F ∩ C0 ∩ A0; None live (not a terminal basis)


def initial_compatibility(d: int, h0: Decimal, l0: Decimal, tick: Decimal, c0: tuple[Decimal, Decimal] | None,
                          a0: tuple[Decimal, Decimal] | None, historical: bool) -> Compatibility:
    """MP-005 §3: the initial compatibility of the prepared reference. ``a0`` is the fixed-profile historical economic
    region inside C0 (``geometry.admissible_bounds``); it is ignored live (cost-independent corridor test only)."""
    thr = f_bound(d, h0, l0, tick)
    fc = f_meet(d, thr, c0)
    j0 = f_meet(d, thr, a0) if historical and fc is not None else None
    econ_empty = historical and (fc is None or j0 is None)
    if fc is None:
        return Compatibility(False, CORRIDOR, (HISTORICAL_ECONOMICS,) if econ_empty else (), thr, None, None)
    if historical and j0 is None:
        return Compatibility(False, HISTORICAL_ECONOMICS, (), thr, fc, None)
    return Compatibility(True, None, (), thr, fc, j0)


@dataclass
class Scen6(Scen4):
    """The v0.4 structural scenario plus the v0.6 record of an ended child entry attempt (presentation only: the
    scenario lifecycle never reads it; a terminated attempt is not an invalidated scenario)."""

    entry_ended: dict | None = None  # {reason, base, at}


class AdviserCoreV6(AdviserCoreV5):
    SCEN_CLS = Scen6
    WAIT_CLS = Wait5
    STATE_FMT = STATE_FORMAT
    KINDS = sc.KIND_CONTRACTS_V6

    def __init__(self, config) -> None:
        super().__init__(config)
        self.counters["v6"] = {"initial_incompatible": 0, CORRIDOR: 0, HISTORICAL_ECONOMICS: 0}

    def _return_usable(self, s: Scen, w: Wait5, m, cor, econ, price, source, k, chk, t: datetime) -> None:
        """MP-005 §5 order: (3) prepare and publish the single reference (MP-004), then (4) the initial check, then
        (5) the immediate terminal in this same dispatch, or WAIT_RESPONSE continues per MP-004."""
        super()._return_usable(s, w, m, cor, econ, price, source, k, chk, t)
        hist = self.cfg.profile.execution == Execution.HISTORICAL_BASE
        ref = w.ref
        c = initial_compatibility(w.d, Decimal(ref["H0"]), Decimal(ref["L0"]), self.tick, cor, econ if hist else None,
                                  hist)
        if not c.compatible:
            self._initial_incompatible(s, w, c, cor, econ, price, k, chk, hist, t)
        return None

    def _initial_incompatible(self, s: Scen, w: Wait5, c: Compatibility, cor, econ, price, k, chk, hist: bool,
                              t: datetime) -> None:
        d = w.d
        note: dict[str, str | None] = {
            "outcome": REASON, "incompatibility_base": c.base,
            "incompatibility_annotations": ",".join(c.annotations) or None,
            "execution_profile": "HISTORICAL_FIXED" if hist else "LIVE",
            "F": (f">= {c.f_bound}" if d > 0 else f"<= {c.f_bound}"), "C0": _rng(cor),
            "A0": _rng(econ) if hist else None,
            "F_cap_C0": _rng(c.f_cap_c0), "J0": _rng(c.j0) if hist else None,
            "economic_basis": "FIXED_HISTORICAL_PROFILE" if hist else "NOT_A_TERMINAL_BASIS_LIVE"}
        self._notes[s.eid] = note
        self._count("ended_after_reference")
        if self.window == "EVALUATION":
            self.counters["v6"]["initial_incompatible"] += 1
            self.counters["v6"][c.base] += 1
        g = self._wait_geometry(w)
        g.update(price=_s(price), K_cost=_s(k), economic_current=_rng(econ),
                 G=_s(chk.g if chk else None), Q=_s(chk.q if chk else None), margin=_s(chk.margin if chk else None))
        s.entry_ended = {"reason": REASON, "base": c.base, "at": _iso(t)}
        self._entry_end(s, "TERMINAL", "TERMINAL", f"{REASON}:{c.base}", t, geometry=g, cap_history=w.caps)

    # ----------------------------------------------------------------------------------------------------------
    # views
    # ----------------------------------------------------------------------------------------------------------

    def scenarios_view(self, t: datetime | None) -> list[dict]:
        rows = super().scenarios_view(t)
        for row in rows:
            s = self.scen.get(row["scenario_id"])
            if s is None or not s.entry_ended:
                continue
            x = s.entry_ended
            row["entry_ended"] = {
                "reason": x["reason"], "base": x["base"], "at": x["at"], "scenario_invalidated": False,
                "text": ("Entry attempt ended at the return reference: a confirming close could not lie in the usable "
                         + ("corridor" if x["base"] == CORRIDOR else "historical economic region")
                         + ". The structural scenario is NOT invalidated and keeps its own lifecycle; no call can come "
                           "from this attempt.")}
        return rows

    def inspect(self) -> dict:
        out = super().inspect()
        out["method_semantics"] = ("MP-005 v0.6: MP-004 v0.5 + initial response incompatibility of the prepared A "
                                   "RETURN reference (child terminal, scenario unchanged)")
        return out
