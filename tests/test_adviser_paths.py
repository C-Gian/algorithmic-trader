"""WP-009 complete hand-expected paths (pure): A/B/C LONG and their exact SHORT reflections, no-trigger / no-room /
stop / stall / progress / no-entry variants, box ownership (B1), total view table rows (B2), evaluator independence
and direct restore at arbitrary cursors. Every expected number is derived by hand from the fixture construction in
``adviser_fixtures`` (S15 = 15 or 600, z = 0.1*S15); none is read back from the implementation."""

from __future__ import annotations

from collections import Counter
from datetime import timedelta
from decimal import Decimal, localcontext

import pytest
from adviser_fixtures import DAY1, DAY2, P0, a_fixture, box_fixture, mirror

from algotrader.adviser.harness import build_events, run_pure, temporal_for
from algotrader.adviser.runtime import AdviserRuntime
from algotrader.adviser.engine import _dt  # noqa: F401  (import check)
from algotrader.temporal import engine as te

D = Decimal


def P(x) -> Decimal:
    return P0 + D(str(x))


def V(x) -> Decimal | None:
    return None if x is None else D(str(x))


def S(x) -> str:
    return str(P0 - D(str(x)))


def _t(res, kind):
    return [e for e in res.journal if e["kind"] == kind]


@pytest.fixture(scope="module")
def a_long():
    return run_pure(DAY1, a_fixture(), eval_start=DAY2)


@pytest.fixture(scope="module")
def a_short():
    return run_pure(DAY1, mirror(a_fixture()), eval_start=DAY2)


def test_a_long_continuation_full_path_is_hand_expected(a_long):
    cands = a_long.candidates("A")
    assert [(c["env"]["clock_time"], c["transition"]) for c in cands] == [
        ("2025-09-01T05:00:00Z", "BIRTH"), ("2025-09-01T05:15:00Z", "ARM"), ("2025-09-01T05:21:00Z", "ISSUE")]
    birth, arm = cands[0], cands[1]
    assert birth["reason"] == "FALSE_TO_TRUE"  # balanced warmup observations were false; first true at 05:00
    assert V(birth["setup"]["impulse_A"]) == P(135) and V(birth["setup"]["impulse_B"]) == P(240)
    assert birth["setup"]["s15"] == "15" and D(birth["setup"]["zone_halfwidth"]) == D("1.5")
    # reaction bar 05:00-05:15: low P0+228 < B - 0.25*S15, > A + z; K = anchor high = B, V = R - z
    assert V(arm["trigger_level"]) == P(240) and V(arm["invalidation_level"]) == P("226.5")
    [call] = a_long.calls()
    assert call["issued_at"] == "2025-09-01T05:21:00Z" and call["trigger_minute_start"] == "2025-09-01T05:20:00Z"
    assert V(call["issue_reference"]) == P(242) and V(call["invalidation"]) == P("226.5")
    # target: nearest opposing near edge ahead = spike high P0+800 - z(1.5); 1h pivot (created day 1 05:15) wins the
    # equal-edge tie with the previous-day high (created at the day-2 boundary) by creation time
    assert V(call["target"]) == P("798.5") and call["target_type"] == "LANDMARK"
    assert call["limiting_landmark"]["type"] == "PIVOT_HIGH_1H"
    # structural area [max(V+tick, tc-0.25*15), min(T-tick, tc+3.75)] rounded inward
    assert [V(x) for x in call["structural_area"]] == [P("238.3"), P("245.7")]
    assert call["hard_deadline"] == "2025-09-01T09:21:00Z" and call["progress_check_at"] == "2025-09-01T07:21:00Z"
    a = call["actionability"]
    g, q = D(a["gain_bps"]), D(a["risk_bps"])
    assert abs(g - D(10000) * D("556.5") / D(100242)) < D("1e-20") and abs(q - D(10000) * D("15.5") / D(100242)) < D("1e-20")
    revs = a_long.revisions(call["call_id"])
    assert revs[-1]["thesis_status"] == "TARGET_REACHED"
    assert revs[-1]["env"]["clock_time"] == "2025-09-01T08:27:00Z"  # minute [08:26,08:27) high 242+3*186 >= 798.5
    assert [r["revision"] for r in revs] == list(range(1, len(revs) + 1))
    paths = {p["variant"]: p for p in a_long.paths()}
    assert V(paths["PRIMARY"]["entry"]["price"]) == P(245) and paths["PRIMARY"]["entry"]["time_start"].endswith("05:22:00Z")
    assert paths["PRIMARY"]["exit_class"] == "TARGET" and V(paths["PRIMARY"]["exit"]["price"]) == P("798.5")
    assert V(paths["ENTRY_DELAY_0"]["entry"]["price"]) == P(242)  # delay 0: the issue minute's own open
    # delay 120: boundary 05:23 opens at P0+248, outside the area; never re-enters: a target WITHOUT entry is no win
    assert paths["ENTRY_DELAY_120"]["status"] == "NO_ENTRY" and paths["ENTRY_DELAY_120"]["entry_attempts"] >= 1
    assert paths["HORIZON_ONLY"]["exit"]["time_start"].endswith("09:22:00Z")  # issue + 4h + 60 s, ceil minute
    e, x = P(245), P("798.5")
    with localcontext() as ctx:
        ctx.prec = 50  # the evaluator's declared accounting precision
        assert D(paths["PRIMARY"]["gross"]) == x / e - 1
        assert D(paths["PRIMARY"]["price_net"]) == (x / e - 1) - (D("0.0005") + D("0.0002")) * (1 + x / e)
    assert paths["PRIMARY"]["total_net"] is None and paths["PRIMARY"]["funding_status"].startswith("PRICE_NET_ONLY")


def test_a_short_is_the_exact_price_reflection(a_long, a_short):
    [lc], [sc_] = a_long.calls(), a_short.calls()
    assert sc_["direction"] == "SHORT" and sc_["family"] == "A"
    for k in ("issued_at", "trigger_minute_start", "hard_deadline", "target_type"):
        assert sc_[k] == lc[k]
    for k in ("issue_reference", "invalidation", "target"):
        assert D(sc_[k]) == 2 * P0 - D(lc[k])
    assert [D(x) for x in sc_["structural_area"]] == [2 * P0 - D(lc["structural_area"][1]),
                                                       2 * P0 - D(lc["structural_area"][0])]
    assert sc_["limiting_landmark"]["type"] == "PIVOT_LOW_1H"
    assert [r["thesis_status"] for r in a_short.revisions()][-1] == "TARGET_REACHED"
    lp = {p["variant"]: p for p in a_long.paths()}
    sp = {p["variant"]: p for p in a_short.paths()}
    for v in lp:
        assert (sp[v]["status"], sp[v]["exit_class"]) == (lp[v]["status"], lp[v]["exit_class"])
        if lp[v]["entry"]:
            assert D(sp[v]["entry"]["price"]) == 2 * P0 - D(lp[v]["entry"]["price"])


@pytest.mark.parametrize("kind", ["B", "C"])
def test_box_families_long_and_short_reflection(kind):
    lr = run_pure(DAY1, box_fixture(kind), eval_start=DAY2)
    sr = run_pure(DAY1, mirror(box_fixture(kind)), eval_start=DAY2)
    box = [e["record"]["values"] for e in _t(lr, "observation") if e["record"]["name"] == "compression_box"][0]
    # box born at the 04:00 close: prior 16 bars span [P0, P0+1800]; S15 = 600 (TR of the 600-point bars); z = 60
    assert (V(box["low"]), V(box["up"]), V(box["mid"]), V(box["s15"])) == (P(0), P(1800), P(900), 600)
    assert D(box["zone_halfwidth"]) == 60 and box["er16"] == "0"
    [lc], [sc_] = lr.calls(), sr.calls()
    if kind == "B":
        # break close 1900 > U+z; retest low 1780 in [1740,1860], close 1850 > U: K = max(U+tick, 1850), V = 1780-60
        arm = [c for c in lr.candidates("B") if c["transition"] == "ARM"][0]
        assert V(arm["trigger_level"]) == P(1850) and V(arm["invalidation_level"]) == P(1720)
        assert V(lc["issue_reference"]) == P(1860) and V(lc["target"]) == P(3600)  # projection U + (U - L), no nearer level
        assert lc["target_type"] == "PROJECTED_BOX_WIDTH" and lc["issued_at"] == "2025-09-01T04:46:00Z"
        assert [D(x) for x in lc["structural_area"]] == [(P("1720.1")), (P(2010))]
    else:
        # reclaim low -70 < L-z, close 100 in (L+z, M): K = 100, V = -70 - 60; target = frozen midpoint
        arm = [c for c in lr.candidates("C") if c["transition"] == "ARM"][0]
        assert V(arm["trigger_level"]) == P(100) and V(arm["invalidation_level"]) == P(-130)
        assert V(lc["issue_reference"]) == P(110) and V(lc["target"]) == P(900) and lc["target_type"] == "MIDPOINT"
        assert [D(x) for x in lc["structural_area"]] == [(P(-40)), (P(260))]
        assert [V(x) for x in lc["actionability"]["admissible_bounds"]] == [P(-40), P("197.9")]  # (T+1.2V)/(2.2*1.0014)
    assert sc_["family"] == kind and sc_["direction"] == "SHORT"
    for k in ("issue_reference", "invalidation", "target"):
        assert D(sc_[k]) == 2 * P0 - D(lc[k])
    assert sc_["issued_at"] == lc["issued_at"]


@pytest.mark.parametrize("variant,terminal,reason,primary", [
    ("stop", "INVALIDATED", "CERTIFIED_INVALIDATION_CONTACT", ("CLOSED", "STOP", P("226.5"))),
    ("stall", "RETIRED", "STALLED", ("CLOSED", "GUIDANCE_RETIRED", None)),
    ("wick", "RETIRED", "STALLED", ("CLOSED", "GUIDANCE_RETIRED", None)),     # an intrabar high alone is not progress
    ("progress", "TIME_EXPIRED", "HARD_DEADLINE", ("CLOSED", "GUIDANCE_TIME_EXPIRED", None)),  # +0.6*S15 close once
])
def test_post_issue_variants(variant, terminal, reason, primary):
    res = run_pure(DAY1, a_fixture(after_issue=variant), eval_start=DAY2)
    [call] = res.calls()
    last = res.revisions(call["call_id"])[-1]
    assert last["thesis_status"] == terminal and last["terminal_reason"].startswith(reason)
    p = {x["variant"]: x for x in res.paths()}["PRIMARY"]
    assert (p["status"], p["exit_class"]) == primary[:2]
    if primary[2]:
        assert V(p["exit"]["price"]) == primary[2] and p["exit"]["reason"] == "STOP_TOUCH"
    if terminal == "RETIRED":
        # guidance withdrawal at 07:21 -> modeled exit request ceil(07:21 + 60 s) = 07:22 open
        assert last["env"]["clock_time"] == "2025-09-01T07:21:00Z" and p["exit"]["time_start"].endswith("07:22:00Z")
        assert res.runtime.core.call is None  # RETIRED freed the recommendation slot immediately


def test_no_trigger_and_no_room_are_diagnosed_not_forced():
    fade = run_pure(DAY1, a_fixture(after_arm="fade"), eval_start=DAY2)
    assert not fade.calls()
    assert [(c["transition"], c["reason"]) for c in fade.candidates("A")][-1] == ("EXPIRE", "ATTEMPT_DEADLINE")
    assert fade.candidates("A")[-1]["env"]["clock_time"] == "2025-09-01T07:00:00Z"  # birth 05:00 + 120 min
    near = run_pure(DAY1, a_fixture(spike=300), eval_start=DAY2)
    assert not near.calls()
    rej = [c for c in near.candidates("A") if c["transition"] == "REJECT"]
    assert rej and rej[0]["reason"] == "NO_ROOM_AFTER_COSTS"
    act = [a for a in (e["record"] for e in _t(near, "actionability")) if not a["actionable"]][0]
    assert "NO_ROOM_AFTER_COSTS" in act["blockers"] and D(act["gain_bps"]) < 14


def test_b1_return_inside_cancels_b_keeps_box_and_c_can_arm():
    res = run_pure(DAY1, box_fixture("B_RETURN"), eval_start=DAY2)
    b = res.candidates("BL")
    assert [(c["transition"], c["reason"]) for c in b] == [("BIRTH", None), ("WITHDRAW", "RETURNED_INSIDE_BEFORE_RETEST")]
    boxes = [e for e in _t(res, "observation") if e["record"]["name"] == "compression_box"]
    retired = [e for e in boxes if e["record"]["category"] == "BOX_RETIRED"]
    assert retired[0]["record"]["values"]["reason"] == "BOX_EXPIRY"  # never destroyed by the wick/reclaim
    assert [c["transition"] for c in res.candidates("CL")][:2] == ["BIRTH", "ARM"]
    assert [c["family"] for c in res.calls()] == ["C"]


def test_b1_opposite_far_edge_close_cancels_and_retires_atomically():
    res = run_pure(DAY1, box_fixture("B_OPPOSITE"), eval_start=DAY2)
    w = [c for c in res.candidates("BL") if c["transition"] == "WITHDRAW"][0]
    ret = [e for e in _t(res, "observation") if e["record"]["name"] == "compression_box"
           and e["record"]["category"] == "BOX_RETIRED"][0]
    assert w["env"]["clock_time"] == ret["clock_time"] == "2025-09-01T04:45:00Z"
    assert ret["record"]["values"]["reason"].startswith("OPPOSITE_FAR_EDGE_CLOSE_DURING_B_LONG")
    # retirement leaves no owner for the same close: no B_SHORT is born from the bar that retired the box
    assert not [c for c in res.candidates("BS") if c["env"]["clock_time"] == "2025-09-01T04:45:00Z"]


def test_total_view_table_rows_and_observed_context_is_not_expected_direction(a_long):
    rows = [(e["clock_time"], e["record"]["table_row"], e["record"]["expected_direction"],
             e["record"]["observed_context"]) for e in _t(a_long, "market_view")]
    assert rows[0][1:3] == ("REQUIRED_CONTEXT_UNAVAILABLE", "UNAVAILABLE")
    armed = [r for r in rows if r[1] == "ARMED_SCENARIO"]
    assert armed and armed[0][0] == "2025-09-01T05:15:00Z" and armed[0][2] == "UP"
    ongoing = [r for r in rows if r[1] == "ONGOING_CALL"]
    assert ongoing and ongoing[0][0] == "2025-09-01T05:21:00Z"
    balanced = [r for r in rows if r[1] == "BALANCED_RANGE"]
    assert all(r[2] == "BALANCED" and r[3] == "BALANCED" for r in balanced)
    nsp = [r for r in rows if r[1] == "NO_SUPPORTED_PLAN"]
    assert all(r[2] == "UNCERTAIN" for r in nsp)  # e.g. a context-only UP never forces an expected UP
    v = [e["record"] for e in _t(a_long, "market_view") if e["record"]["table_row"] == "ARMED_SCENARIO"][0]
    assert v["conditional"] is True and v["principal"]["family"] == "A" and v["uncertainty"].startswith("QUALITATIVE")


def test_evaluator_disabled_emits_byte_identical_semantics():
    mins = a_fixture()
    on = run_pure(DAY1, mins, eval_start=DAY2)
    off = run_pure(DAY1, mins, eval_start=DAY2, evaluator=False)
    assert [e["digest"] for e in on.journal] == [e["digest"] for e in off.journal]
    assert on.runtime.core.journal_chain == off.runtime.core.journal_chain and off.records == []


@pytest.mark.parametrize("cuts", [[1], [7, 13, 501], [5000]])
def test_direct_restore_at_arbitrary_cursors_reproduces_every_output(cuts):
    """Encode/decode the temporal + professional state at the given cursors (incl. inside tie groups) and continue:
    outputs equal one uninterrupted fold (checkpoint cadence never changes semantics)."""
    mins = a_fixture()
    base = run_pure(DAY1, mins, eval_start=DAY2)
    events, cov = build_events(DAY1, mins)
    from algotrader.adviser.harness import make_runtime

    rt = make_runtime(eval_start=DAY2)
    temporal = temporal_for(cov)
    rt.attach(temporal)
    journal, records = [], []
    for i, e in enumerate(events):
        if i in cuts:
            j, r = rt.take()
            journal += j
            records += r
            tdoc = te.pack(temporal)
            temporal = te.unpack(*tdoc)
            import json

            from algotrader.adviser.core import AdviserConfig  # noqa: F401
            from algotrader.feed.ordering import canonical

            raw = canonical(rt.encode())
            rt = AdviserRuntime.decode(json.loads(raw), rt.core.cfg, make_runtime(eval_start=DAY2).ev)
            assert canonical(rt.encode()) == raw
            rt.attach(temporal)
        temporal.on_event(e, i)
        rt.before_admit(e)
        rt.admit(e, i)
    end = DAY1 + len(mins) * timedelta(minutes=1)
    temporal.finish(end)
    rt.finish(end)
    j, r = rt.take()
    journal += j
    records += r
    assert [e["digest"] for e in journal] == [e["digest"] for e in base.journal]
    assert [r["digest"] for r in records] == [r["digest"] for r in base.records]


def test_hourly_view_samples_are_after_dispatch_and_keep_denominators(a_long):
    samples = a_long.samples()
    assert len(samples) >= 9 and samples[0]["sample_time"] == "2025-09-01T00:00:00Z"
    by = Counter(s["view"] for s in samples)
    assert by["UNAVAILABLE"] + by["UNCERTAIN"] + by["BALANCED"] + by["UP"] + by["DOWN"] == len(samples)
    s6 = next(s for s in samples if s["sample_time"] == "2025-09-01T06:00:00Z")
    assert s6["view"] == "UP" and s6["anchor_price"] is not None  # ongoing call at 06:00 -> conditional UP
    assert s6["outcome_1h"] == "UP"  # +1h endpoint close above the frozen anchor (rally)
