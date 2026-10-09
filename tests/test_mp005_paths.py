"""WP-015 / MP-005 fixtures for btc.context-action.v0.6 (pure, database-free).

Layer 1 checks the MP-005 §8 (historical, tick 1) and §9 (live, tick 0.01) rows literally through the pinned functions:
``geometry.admissible_bounds``/``predicate``, ``core5.local_verdict``, ``core6.initial_compatibility`` and the live cost
envelope of ``AdviserCore._side_price``. Layer 2 runs reachable LONG/SHORT state machines on the MP-002 base A path
(``adviser6_fixtures``): every expected transition, reason, base, dispatch and (P, X, C, R, N, I, A) tuple is written
by hand from the specification; SHORT is the positive-price reflection. Engineering inputs only, no market data."""

from __future__ import annotations

import json
from datetime import timedelta
from decimal import Decimal

import adviser5_fixtures as f5
import adviser6_fixtures as fx
import pytest
from adviser3_fixtures import Stepper
from test_mp004_versions import FIX, _ids, _norm, _sub

from algotrader.adviser import geometry as geo
from algotrader.adviser import reconcile as arc
from algotrader.adviser import report6 as r6
from algotrader.adviser.core5 import local_verdict
from algotrader.adviser.core6 import CORRIDOR, HISTORICAL_ECONOMICS, REASON, initial_compatibility
from algotrader.adviser.harness import run_pure
from algotrader.adviser.measures import round_down, round_up

D = Decimal
T = fx.T
ENG = {"adviser": {"eval_start": fx.DAY2.isoformat(), "eval_end": (fx.DAY2 + timedelta(days=1)).isoformat()}}


def run(ms, method="v0.6", **kw):
    kw.setdefault("eval_start", fx.DAY2)
    return run_pure(fx.DAY1, ms, method=method, **kw)


def side_ms(fixture, side):
    ms = fixture()
    return ms if side == "L" else fx.mirror(ms)


def a_ents(journal) -> list[dict]:
    return [e["record"] for e in journal if e["kind"] == "entry_attempt" and e["record"]["scenario_id"][:2] in ("AL", "AS")
            and e["record"]["transition"] != "BLOCKERS"]


def steps(journal) -> list[tuple]:
    return [(r["env"]["clock_time"][11:19], r["transition"], (r["reason"] or "").split(",")[0] if r["transition"]
             not in ("ISSUE", "RESPONSE_REFERENCE") else r["transition"]) for r in a_ents(journal)]


def pxcrnia(journal, upto: str | None = None) -> tuple:
    """(P, X, C, R, N, I, A) as MP-005 §7 orders them, from the committed records up to ``upto`` (report cutoff)."""
    j = journal if upto is None else [e for e in journal if e["record"]["env"]["clock_time"] <= upto]
    c = r6.response_accounting(engine=ENG, journal=j, status="completed")["total"]["counts"]
    return tuple(c[k] for k in ("P", "X", "C", "R", "N", "I", "A"))


# =====================================================================================================================
# Layer 1 — MP-005 §8 / §9 rows, literally
# =====================================================================================================================

def corridor(d, r, k, v, t, tick):
    """``core3._corridor`` (inward ticks on the transformed axis) in market prices."""
    lo_t, hi_t = max(round_up(r * d, tick), v * d + tick), min(round_down(k * d, tick), t * d - tick)
    return None if hi_t < lo_t else ((lo_t, hi_t) if d > 0 else (-hi_t, -lo_t))


def live_k(bid, ask):
    """The registered live envelope (``AdviserCore._side_price``): 2*5 + 2*2 + 10000*(ask-bid)/(2*mid) bps."""
    bid, ask = D(bid), D(ask)
    mid = (bid + ask) / 2
    return 2 * D(5) + 2 * D(2) + geo.div(10000 * (ask - bid), 2 * mid)


@pytest.mark.parametrize("side", ["L", "S"])
def test_section_8_geometry_with_the_pinned_rounding(side):
    r, k, v, t, cor, econ = fx.SEC8["geometry"][side]
    d = 1 if side == "L" else -1
    c = corridor(d, D(r), D(k), D(v), D(t), D(1))
    assert c == (D(cor[0]), D(cor[1]))
    assert geo.admissible_bounds(d, c, D(v), D(t), D(14), D("1.2"), D(1)) == (D(econ[0]), D(econ[1]))
    assert geo.predicate(d, D(100), D(v), D(t), D(14), D("1.2")).ok  # close 100: a usable RETURN under MP-004


@pytest.mark.parametrize("side", ["L", "S"])
@pytest.mark.parametrize("row,f,meet,j0", [
    ("H1", {"L": 104, "S": 96}, {"L": (104, 110), "S": (90, 96)}, None),
    ("H2", {"L": 111, "S": 89}, None, None),
    ("H3", {"L": 103, "S": 97}, {"L": (103, 110), "S": (90, 97)}, {"L": (103, 103), "S": (97, 97)}),
])
def test_section_8_historical_rows(side, row, f, meet, j0):
    _, _, v, t, cor, econ = fx.SEC8["geometry"][side]
    d = 1 if side == "L" else -1
    b0, b1, base = fx.SEC8[row][side]
    o, h0, l0, c0 = (D(x) for x in b0)
    assert D(cor[0]) <= c0 <= D(cor[1]) and D(econ[0]) <= c0 <= D(econ[1])  # B0 is a usable RETURN
    res = initial_compatibility(d, h0, l0, D(1), (D(cor[0]), D(cor[1])), (D(econ[0]), D(econ[1])), True)
    assert res.f_bound == D(f[side])
    assert res.compatible == (base is None) and res.base == base
    assert res.f_cap_c0 == (None if meet is None else tuple(D(x) for x in meet[side]))
    assert res.j0 == (None if j0 is None else tuple(D(x) for x in j0[side]))
    if row == "H2":  # the concurrent economic incompatibility is annotated, the primary base stays CORRIDOR
        assert res.annotations == (HISTORICAL_ECONOMICS,)
    # B1 satisfies (H1, H2) or meets (H3) the local recovery predicate arithmetically
    lo, hi, cl = D(b1[2]), D(b1[1]), D(b1[3])
    assert local_verdict(d, h0, l0, D(1), lo, hi, cl) == "RECOVERY"
    if row == "H3":  # exactly at the favourable threshold, contrary equality, price on the economic edge: issuable
        assert cl == res.f_bound and (lo == l0 if d > 0 else hi == h0)
        assert geo.predicate(d, cl, D(v), D(t), D(14), D("1.2")).ok
        assert not geo.predicate(d, cl + d, D(v), D(t), D(14), D("1.2")).ok  # one tick further is inadmissible


@pytest.mark.parametrize("side", ["L", "S"])
def test_section_8_h5_bars_would_be_a_contradiction_then_a_recovery(side):
    d = 1 if side == "L" else -1
    b0, b1, b2 = fx.SEC8["H5"][side]
    h0, l0 = D(b0[1]), D(b0[2])
    assert local_verdict(d, h0, l0, D(1), D(b1[2]), D(b1[1]), D(b1[3])) == "CONTRADICTION"
    assert local_verdict(d, h0, l0, D(1), D(b2[2]), D(b2[1]), D(b2[3])) == "RECOVERY"


@pytest.mark.parametrize("side", ["L", "S"])
def test_section_9_live_rows(side):
    r, k, v, t, cor = (fx.SEC9["geometry"][side][i] for i in range(5))
    d, tick = (1 if side == "L" else -1), D("0.01")
    v, t = D(v), D(t)
    c = corridor(d, D(r), D(k), v, t, tick)
    assert c == (D(cor[0]), D(cor[1]))
    o, h0, l0, c0 = (D(x) for x in fx.SEC9["B0"])
    # L1: midpoint 100, half-spread 1 bps, live cost 15 bps; ask LONG / bid SHORT inside the corridor and admissible
    bid, ask = fx.SEC9["quotes"]["L1"]
    assert live_k(bid, ask) == D(15)
    p1 = D(ask) if d > 0 else D(bid)
    assert c[0] <= p1 <= c[1] and c[0] <= c0 <= c[1] and geo.predicate(d, p1, v, t, D(15), D("1.2")).ok
    res = initial_compatibility(d, h0, l0, tick, c, None, False)
    assert res.compatible and res.f_bound == (D("100.02") if d > 0 else D("99.98"))  # F meets the corridor
    # L2: midpoint 100, half-spread 20 bps, cost 34: the current region is empty, the side prices sit on the edges
    bid, ask = fx.SEC9["quotes"]["L2"]
    assert live_k(bid, ask) == D(34) and geo.admissible_bounds(d, c, v, t, D(34), D("1.2"), tick) is None
    assert (D(ask) if d > 0 else D(bid)) == (c[1] if d > 0 else c[0])
    b1 = [D(x) for x in fx.SEC9["B1"]]
    assert local_verdict(d, h0, l0, tick, b1[2], b1[1], b1[3]) == "NONE"  # contrary equality, no confirmation
    # the live check is cost-independent: no economic region can make it incompatible
    assert initial_compatibility(d, h0, l0, tick, c, None, False).compatible
    # L3: exact cost (never a rounded 15), ratio > 1.2, close/side prices in the corridor, the recovery confirms
    bid, ask = fx.SEC9["quotes"]["L3"][side]
    k3 = live_k(bid, ask)
    # LONG mid 100.03 -> 14.9997..., SHORT mid 99.97 -> 15.0003...: near 15 by the exact formula, never replaced by 15
    assert k3 != D(15) and abs(k3 - D(15)) < D("0.001")
    assert k3 == 14 + geo.div(D(10000) * (D(ask) - D(bid)), D(ask) + D(bid))
    p3 = D(ask) if d > 0 else D(bid)
    chk = geo.predicate(d, p3, v, t, k3, D("1.2"))
    assert chk.ok and (chk.g - k3) / (chk.q + k3) > D("1.2")
    b2 = [D(x) for x in fx.SEC9["B2"][side]]
    assert c[0] <= b2[3] <= c[1] and c[0] <= p3 <= c[1]
    assert local_verdict(d, h0, l0, tick, b2[2], b2[1], b2[3]) == "RECOVERY"


@pytest.mark.parametrize("d", [1, -1])
def test_live_corridor_incompatibility_is_cost_independent_and_single_tick_is_not_empty(d):
    tick = D("0.01")
    cor = (D("100.00"), D("100.20")) if d > 0 else (D("99.80"), D("100.00"))
    edge = cor[1] if d > 0 else cor[0]
    h0, l0 = (edge, D("99.99")) if d > 0 else (D("100.01"), edge)
    res = initial_compatibility(d, h0, l0, tick, cor, (cor[0], cor[0]), False)  # any region: ignored live
    assert not res.compatible and res.base == CORRIDOR and res.annotations == ()
    h0, l0 = (edge - tick, D("99.99")) if d > 0 else (D("100.01"), edge + tick)  # F meets the corridor on one tick
    res = initial_compatibility(d, h0, l0, tick, cor, None, False)
    assert res.compatible and res.f_cap_c0 == (edge, edge)


# =====================================================================================================================
# Layer 2 — reachable LONG/SHORT engine paths
# =====================================================================================================================

OPEN = ("04:01:00", "WAIT_OPEN", "IMMEDIATE_ECONOMIC_FAILURE_RETURN_CORRIDOR_USABLE")
REF = ("04:02:00", "RESPONSE_REFERENCE", "RESPONSE_REFERENCE")


@pytest.mark.parametrize("side", ["L", "S"])
@pytest.mark.parametrize("fixture,base", [("h1_economics", HISTORICAL_ECONOMICS), ("h2_corridor", CORRIDOR)])
def test_h1_h2_prepare_and_end_in_the_same_dispatch(side, fixture, base):
    res = run(side_ms(getattr(fx, fixture), side))
    assert steps(res.journal) == [OPEN, REF, ("04:02:00", "TERMINAL", f"{REASON}:{base}")]
    ref, end = a_ents(res.journal)[1:]
    # same dispatch, documented order: the reference record first, then the terminal
    assert (end["env"]["clock_time"], end["env"]["factual_cursor"]) == (ref["env"]["clock_time"],
                                                                        ref["env"]["factual_cursor"])
    assert end["env"]["professional_seq"] == ref["env"]["professional_seq"]  # one professional dispatch
    seqs = [i for i, e in enumerate(res.journal) if e["record"] is ref or e["record"] is end]
    assert len(seqs) == 2 and res.journal[seqs[0]]["record"] is ref  # journal order: reference, then terminal
    resp = end["response"]
    assert resp["outcome"] == REASON and resp["incompatibility_base"] == base and resp["bars_checked"] == "0"
    assert resp["execution_profile"] == "HISTORICAL_FIXED" and resp["economic_basis"] == "FIXED_HISTORICAL_PROFILE"
    long_ = side == "L"
    assert resp["C0"] == ("99900..100049.9" if long_ else "99950.1..100100")
    assert resp["A0"] == ("99900..100014.5" if long_ else "99985.5..100100")
    if base == HISTORICAL_ECONOMICS:
        assert resp["F"] == (">= 100014.6" if long_ else "<= 99985.4") and resp["J0"] is None
        assert resp["F_cap_C0"] == ("100014.6..100049.9" if long_ else "99950.1..99985.4")
        assert resp["incompatibility_annotations"] is None
    else:
        assert resp["F"] == (">= 100050.0" if long_ else "<= 99950.0") and resp["F_cap_C0"] is None
        assert resp["incompatibility_annotations"] == HISTORICAL_ECONOMICS
    assert end["geometry"]["economic_current"] == resp["A0"] and end["geometry"]["K_cost"] == "14"
    assert pxcrnia(res.journal) == (1, 1, 0, 0, 0, 0, 0) and not res.calls()
    # the scenario is not invalidated by the child terminal: it is still CONFIRMED and ends later by its own rules
    scen = [e["record"] for e in res.journal if e["kind"] == "scenario" and e["record"]["scenario_id"][:2] in ("AL", "AS")]
    assert not [s for s in scen if s["env"]["clock_time"] == "2025-09-01T04:02:00Z"]
    assert scen[-1]["env"]["clock_time"] > "2025-09-01T05:00:00Z"


@pytest.mark.parametrize("side", ["L", "S"])
def test_h3_single_tick_waits_then_issues_at_the_exact_edge(side):
    res = run(side_ms(fx.h3_single_tick, side))
    assert steps(res.journal) == [OPEN, REF, ("04:03:00", "ISSUE", "ISSUE")]
    assert pxcrnia(res.journal, upto="2025-09-01T04:02:00Z") == (1, 0, 0, 0, 0, 0, 1)
    assert pxcrnia(res.journal) == (1, 0, 0, 1, 0, 1, 0)
    [call] = res.calls()
    assert call["issue_reference"] == ("100014.5" if side == "L" else "99985.5")
    # v0.5 gives the same journal on this tape (identifiers normalized)
    r5 = run(side_ms(fx.h3_single_tick, side), method="v0.5")
    kinds = tuple({e["kind"] for e in r5.journal})
    assert _norm(res.journal, kinds) == _norm(r5.journal, kinds)


@pytest.mark.parametrize("side", ["L", "S"])
def test_h4_inherited_deadline_precedes_the_preparation(side):
    res = run(side_ms(fx.h4_deadline_collision, side))
    assert steps(res.journal) == [OPEN, ("05:30:00", "TERMINAL", "ORIGINAL_SETUP_DEADLINE")]
    acc = r6.response_accounting(engine=ENG, journal=res.journal, status="completed")["total"]
    assert pxcrnia(res.journal) == (0, 0, 0, 0, 0, 0, 0)
    assert acc["counts"]["W"] == 1 and acc["ended_before_reference"] == {"ORIGINAL_SETUP_DEADLINE": 1}
    assert acc["identities_hold"] and acc["initial_incompatibility"]["count"] == 0
    assert not [r for r in a_ents(res.journal) if r["env"]["clock_time"] > "2025-09-01T05:30:00Z"]


@pytest.mark.parametrize("side", ["L", "S"])
def test_h5_no_later_c_or_r_and_no_wait_left_after_the_dispatch(side):
    st = Stepper(side_ms(fx.h5_persistence, side), method="v0.6")
    st.run_until(T(4, 2))  # the preparation dispatch: P -> X, and no active wait remains for the child
    assert not st.core.waits and st.core.counters["v6"]["initial_incompatible"] == 1
    scen = next(s for s in st.core.scen.values() if s.family == "A")
    assert scen.status == "CONFIRMED" and scen.entry == "TERMINAL"
    assert scen.entry_ended == {"reason": REASON, "base": HISTORICAL_ECONOMICS, "at": "2025-09-01T04:02:00+00:00"}
    st.finish()
    assert steps(st.journal) == [OPEN, REF, ("04:02:00", "TERMINAL", f"{REASON}:{HISTORICAL_ECONOMICS}")]
    assert pxcrnia(st.journal) == (1, 1, 0, 0, 0, 0, 0) and not [e for e in st.journal if e["kind"] == "call"]


@pytest.mark.parametrize("side", ["L", "S"])
def test_view_distinguishes_an_ended_attempt_from_an_invalidated_scenario(side):
    st = Stepper(side_ms(fx.h1_economics, side), method="v0.6")
    st.run_until(T(4, 3))
    [row] = [r for r in st.core.scenarios_view(T(4, 3)) if r["family"] == "A"]
    assert row["status"] == "CONFIRMED" and row["entry_state"] == "TERMINAL" and "waiting" not in row
    e = row["entry_ended"]
    assert (e["reason"], e["base"], e["scenario_invalidated"]) == (REASON, HISTORICAL_ECONOMICS, False)
    assert "NOT invalidated" in e["text"]


def test_v05_on_the_same_tapes_prepares_and_waits_instead():
    """The MP-005 delta itself: under v0.5 the H1/H2 references stay in WAIT_RESPONSE and the next bar is a decisive
    recovery that is not issuable (R = N = 1); under v0.6 that classification is lost (declared, no counterfactual)."""
    for fixture in (fx.h1_economics, fx.h2_corridor):
        r5 = run(fixture(), method="v0.5")
        assert [s[1] for s in steps(r5.journal)] == ["WAIT_OPEN", "RESPONSE_REFERENCE", "TERMINAL"]
        assert a_ents(r5.journal)[-1]["reason"].startswith("RESPONSE_NOT_ISSUABLE")
        assert pxcrnia(r5.journal) == (1, 0, 0, 1, 1, 0, 0) and pxcrnia(run(fixture()).journal) == (1, 1, 0, 0, 0, 0, 0)


# -- parity with v0.5 outside the new terminal -------------------------------------------------------------------------

EXTRA = {"mp005_h1": fx.h1_economics, "mp005_h2": fx.h2_corridor, "mp005_h3": fx.h3_single_tick,
         "mp005_h4": fx.h4_deadline_collision, "mp005_h5": fx.h5_persistence,
         "mp004_two_valid": f5.two_valid, "mp004_recovery_then_violation": f5.recovery_then_violation,
         "mp004_blocked_first": f5.blocked_first, "mp004_new_cap_before_recovery": f5.new_cap_before_recovery,
         "mp004_cap_contact_in_activation_bar": f5.cap_contact_in_activation_bar,
         "mp004_cap_empties_economic_region": lambda: f5.cap_empties_economic_region(*f5.neutral(1), f5.VALID)}
PARITY = {**FIX, **EXTRA, **{f"{k}_short": (lambda f: lambda: fx.mirror(f()))(f) for k, f in EXTRA.items()}}


@pytest.mark.parametrize("name", sorted(PARITY))
def test_v06_equals_v05_outside_the_new_terminal(name):
    """Without an INITIAL_RESPONSE_INCOMPATIBLE terminal the whole v0.6 journal and every hypothetical path equal v0.5;
    with one, every record published before that dispatch is identical and the structural scenarios/landmarks are
    identical throughout (the child terminal never touches the scenario lifecycle)."""
    r5, r6_ = run(PARITY[name](), method="v0.5"), run(PARITY[name](), method="v0.6")
    ends = [r for r in a_ents(r6_.journal) if str(r["reason"] or "").startswith(REASON)]
    kinds = tuple(sorted({e["kind"] for e in r5.journal} | {e["kind"] for e in r6_.journal}))
    if not ends:
        assert _norm(r6_.journal, kinds) == _norm(r5.journal, kinds)
        i5, i6 = _ids(r5.journal), _ids(r6_.journal)
        assert [_sub(json.dumps(p, sort_keys=True), i6) for p in r6_.paths()] == \
            [_sub(json.dumps(p, sort_keys=True), i5) for p in r5.paths()]
        return
    cut = ends[0]["env"]["clock_time"]
    assert [x for x in _norm(r6_.journal, kinds) if x[1] < cut] == [x for x in _norm(r5.journal, kinds) if x[1] < cut]
    assert _norm(r6_.journal, ("scenario", "landmark")) == _norm(r5.journal, ("scenario", "landmark"))
    # v0.5 had a prepared reference in that very dispatch; v0.6 adds exactly one terminal record there
    at5 = [r["transition"] for r in a_ents(r5.journal) if r["env"]["clock_time"] == cut]
    at6 = [r["transition"] for r in a_ents(r6_.journal) if r["env"]["clock_time"] == cut]
    assert "RESPONSE_REFERENCE" in at5 and at6 == at5 + ["TERMINAL"]


def test_the_pre_existing_v03_return_tape_now_ends_on_the_corridor():
    """``a3_return_long``: the first usable return has H0 100050 above the corridor top 100049.9, so no confirming
    close can be inside the corridor (v0.5 waits for a recovery that can only be not issuable)."""
    for side in "LS":
        res = run(FIX["a3_return_long" if side == "L" else "a3_return_short"]())
        assert steps(res.journal)[-1] == ("04:02:00", "TERMINAL", f"{REASON}:{CORRIDOR}")


# -- reconciliation lineage (the v0.6 check is a pure function of the stored records) ----------------------------------

def test_v06_lineage_accepts_real_journals_and_detects_tampering():
    good = [run(side_ms(f, s)).journal for f in (fx.h1_economics, fx.h2_corridor, fx.h3_single_tick, fx.h4_deadline_collision)
            for s in "LS"]
    for j in good:
        assert arc._v5_response_lineage(j) == [] and arc._v6_initial_compatibility(j, True) == []
    j = good[0]
    idx = next(i for i, e in enumerate(j) if str(e["record"].get("reason") or "").startswith(REASON))
    moved = [dict(e) for e in j]
    rec = json.loads(json.dumps(moved[idx]["record"]))
    rec["env"]["clock_time"] = "2025-09-01T04:03:00Z"
    moved[idx] = {**moved[idx], "record": rec}
    assert any("not in the dispatch of its own reference" in x for x in arc._v6_initial_compatibility(moved, True))
    rebased = [dict(e) for e in j]
    rec = json.loads(json.dumps(rebased[idx]["record"]))
    rec["reason"] = f"{REASON}:{CORRIDOR}"
    rec["response"]["incompatibility_base"] = CORRIDOR
    rebased[idx] = {**rebased[idx], "record": rec}
    assert any("recomputed HISTORICAL_ECONOMICS differs" in x for x in arc._v6_initial_compatibility(rebased, True))
    # a compatible reference recorded as incompatible (H3 journal with an injected terminal) is flagged too
    j3 = good[4]
    ref_i = next(i for i, e in enumerate(j3) if e["kind"] == "entry_attempt"
                 and e["record"]["transition"] == "RESPONSE_REFERENCE")
    fake = json.loads(json.dumps(j3[ref_i]))
    fake["record"].update(transition="TERMINAL", state="TERMINAL", reason=f"{REASON}:{CORRIDOR}")
    fake["record"]["response"].update(outcome=REASON, incompatibility_base=CORRIDOR, bars_checked="0")
    probs = arc._v6_initial_compatibility(j3[:ref_i + 1] + [fake], True)
    assert any("recomputed COMPATIBLE differs" in x for x in probs)
    # and an incompatible reference left waiting (terminal removed) is flagged
    assert any("left waiting" in x for x in arc._v6_initial_compatibility(j[:idx], True))
