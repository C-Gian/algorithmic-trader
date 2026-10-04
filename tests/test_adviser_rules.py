"""WP-009 dispatch-level rule checks (pure) for the MP-001 Astra blockers and ordering: context change before a
coincident trigger (B2), frozen landmark widths / BROKEN marks / opposing-area block (B3), RETIRED slot release
before any pending hypothetical fill (B5), residual-time closure and straddling-publication contact ambiguity (B6),
A renewal latches and compression birth tokens (B1). The core is primed with explicit complete bars, then exactly one
dispatch is applied; decisions and reasons are asserted at that boundary."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from adviser_rig import Rig, rec

from algotrader.adviser.core import Attempt, Box, Call, Landmark
from algotrader.adviser.harness import trade_bar
from algotrader.adviser.measures import Bar

D = Decimal
MIN = timedelta(minutes=1)
P0 = D(100000)
T = datetime(2025, 9, 2, 12, 0, tzinfo=UTC)


def _bars(start: datetime, span: timedelta, closes: list, rng=None, first_open=None) -> list[Bar]:
    out, o = [], D(first_open if first_open is not None else closes[0])
    for i, c in enumerate(closes):
        c = D(c)
        s = start + i * span
        if rng is None:
            h, lo = max(o, c), min(o, c)
        else:
            mid = (o + c) / 2
            h, lo = max(max(o, c), mid + D(rng) / 2), min(min(o, c), mid - D(rng) / 2)
        out.append(Bar(s, s + span, o, h, lo, c, D(1), s + span, f"r{span}-{i}"))
        o = c
    return out


def prime(rig: Rig, now: datetime, m15_closes: list, h1_bars: list[Bar] | None = None, rng15=30) -> None:
    """Complete contiguous 15m bars ending at ``now`` (+ optional 1h bars) and a fresh 1m bar at ``now``."""
    core = rig.core
    m15 = _bars(now - len(m15_closes) * timedelta(minutes=15), timedelta(minutes=15), m15_closes, rng=rng15)
    core.m15.extend(m15)
    core.last_sealed_end["15m"] = m15[-1].end
    if h1_bars:
        core.h1.extend(h1_bars)
        core.last_sealed_end["1h"] = h1_bars[-1].end
        core._derive_1h(now)
    core._derive_15m(now)
    c = m15[-1].c
    core.last_1m = Bar(now - MIN, now, c, c, c, c, D(1), now, "m-prime")
    core.last_1m_end = now
    core.clock = now
    rig.t = now
    core.journal = []


def balanced_h1(end: datetime, n=21, step=D("-11.25")) -> list[Bar]:
    """n 1h bars with TR 100 drifting by ``step``: 8-transition displacement -0.9*S1h, ER8 1 -> BALANCED."""
    out, o = [], P0
    start = end - n * timedelta(hours=1)
    for i in range(n):
        c = o + step
        h, lo = o + (D(100) + step) / 2, o - (D(100) - step) / 2
        s = start + i * timedelta(hours=1)
        out.append(Bar(s, s + timedelta(hours=1), o, h, lo, c, D(1), s + timedelta(hours=1), f"h{i}"))
        o = c
    return out


def _armed_b_long(rig: Rig, now: datetime, k: D, v: D) -> Attempt:
    core = rig.core
    bx = Box("box-t", P0 - 100, P0 + 100, P0, D(30), D(3), now - timedelta(hours=1), 1, now + timedelta(hours=3),
             ["s"])
    bx.used["B+"] = True
    bx.broken["U"] = True
    core.box = bx
    a = Attempt(aid="BL-test", family="B", d=1, owner=bx.bid, born_at=now - timedelta(minutes=30), born_seq=1,
                sources=["s"], deadline=now + timedelta(minutes=30), s15=D(30), z=D(3), status="ARMED", k_t=k, v_t=v,
                arm_at=now - timedelta(minutes=15), arm_seq=2)
    core.attempts[a.aid] = a
    return a


def _hour_dispatch(rig: Rig, now: datetime, h1_close_step: D, trigger_close: D, close15: D) -> list[dict]:
    """Dispatch at now+15m (a whole hour): the 15m close, the 1h record and the 1m trigger bar together."""
    t1 = now + timedelta(minutes=15)
    core = rig.core
    last_h = core.h1[-1]
    o = last_h.c
    c = o + h1_close_step
    core.admit_sealed(rec("1h", t1 - timedelta(hours=1), o, max(o, c) + 30, min(o, c) - 70 + (c - o + 40), c))
    core.admit_sealed(rec("15m", t1 - timedelta(minutes=15), close15, close15 + 1, close15 - 1, close15))
    core.admit_event(trade_bar(t1 - MIN, trigger_close - 1, trigger_close, trigger_close - 1, trigger_close),
                     rig.cursor)
    rig.cursor += 1
    return rig.dispatch(t1)


@pytest.mark.parametrize("flip", [True, False])
def test_b2_forbidden_context_withdraws_before_a_coincident_trigger(flip):
    now = T - timedelta(minutes=15)  # 11:45; the next dispatch at 12:00 closes 15m and 1h together
    rig = Rig()
    prime(rig, now, [P0 + (10 if i % 2 else -10) for i in range(30)], balanced_h1(T - timedelta(hours=1)))
    assert rig.core.context(now) == "BALANCED"
    a = _armed_b_long(rig, now, k=P0 + 150, v=P0 + 90)
    out = _hour_dispatch(rig, now, D(-40) if flip else D("-11.25"), trigger_close=P0 + 152, close15=P0 + 151)
    kinds = [(e["kind"], e["record"].get("transition"), e["record"].get("reason")) for e in out]
    if flip:
        assert rig.core.context(T) == "DOWN"
        w = [k for k in kinds if k[0] == "candidate"]
        assert w and w[0][1] == "WITHDRAW" and w[0][2].startswith("CONTEXT_OR_ADVERSE_EXPANSION:DOWN")
        assert not [k for k in kinds if k[0] == "actionability"]  # never evaluated as a trigger
    else:
        assert rig.core.context(T) == "BALANCED"
        assert [k for k in kinds if k[0] == "actionability"]  # the same minute is a trigger evaluation
        assert a.aid not in rig.core.attempts  # consumed by its first trigger evaluation (issued or rejected)


def test_b3_landmark_zone_is_frozen_at_creation_and_far_edge_close_breaks_it():
    rig = Rig()
    prime(rig, T, [P0 + (5 if i % 2 else -5) for i in range(30)])
    core = rig.core
    lm = Landmark("lm-x", "PIVOT_HIGH_15M", "HIGH", P0 + 100, D(1), D(10), "15m", ["b"], None, T, 1,
                  T + timedelta(hours=24))
    core.landmarks[lm.lid] = lm
    core.s15 = D(20)  # a later, wider scale never widens the frozen zone
    core._mark_broken(Bar(T, T + timedelta(minutes=15), P0, P0 + 102, P0, P0 + 101, None, T, "x"), T)
    assert lm.status == "ACTIVE"  # close 101 is not strictly beyond the far edge 101
    core._mark_broken(Bar(T, T + timedelta(minutes=15), P0, P0 + 102, P0, P0 + D("101.5"), None, T, "y"), T)
    assert lm.status == "BROKEN" and lm.z == D(1)
    # a BROKEN level is ineligible; an eligible zone containing the trigger price blocks entry
    lm2 = Landmark("lm-y", "PIVOT_HIGH_1H", "HIGH", P0 + 200, D(2), D(20), "1h", ["b"], None, T, 1,
                   T + timedelta(days=7))
    core.landmarks[lm2.lid] = lm2
    a = Attempt(aid="AL-t", family="A", d=1, owner=None, born_at=T, born_seq=1, sources=["s"],
                deadline=T + timedelta(hours=2), s15=D(10), z=D(1), a_t=P0 - 100, b_t=P0 + 50)
    t_t, ttype, info, block = core._resolve_target(a, P0 + 199, T)
    assert block == "AT_OPPOSING_AREA" and info["landmark_id"] == "lm-y"
    t_t, ttype, info, block = core._resolve_target(a, P0 + 150, T)
    assert block is None and t_t == P0 + 198 and info["landmark_id"] == "lm-y"  # near edge; lm-x is broken


def test_b3_pivot_zone_freezes_the_scale_known_at_its_creation():
    rig = Rig()
    prime(rig, T - timedelta(minutes=15), [P0 + (5 if i % 2 else -5) for i in range(30)], rng15=10)
    core = rig.core
    s15_before = core.s15
    # one more complete bar: the bar two closes earlier (high P0+30) is a strict local high vs two bars each side
    core.m15[-1] = Bar(core.m15[-1].start, core.m15[-1].end, P0, P0 + 11, P0 - 5, P0 + 5, D(1), core.m15[-1].end, "k1")
    core.m15[-2] = Bar(core.m15[-2].start, core.m15[-2].end, P0, P0 + 30, P0 - 5, P0, D(1), core.m15[-2].end, "k0")
    core.m15[-3] = Bar(core.m15[-3].start, core.m15[-3].end, P0, P0 + 12, P0 - 5, P0, D(1), core.m15[-3].end, "km")
    core.m15[-4] = Bar(core.m15[-4].start, core.m15[-4].end, P0, P0 + 10, P0 - 5, P0, D(1), core.m15[-4].end, "kn")
    core.m15.append(Bar(T - timedelta(minutes=15), T, P0, P0 + 15, P0 - 5, P0, D(1), T, "k2"))
    core.last_sealed_end["15m"] = T
    core._derive_15m(T)
    pivots = [lm for lm in core.landmarks.values() if lm.ltype == "PIVOT_HIGH_15M"]
    assert len(pivots) == 1 and pivots[0].price == P0 + 30 and pivots[0].created_at == T
    p = pivots[0]
    assert p.s15 == core.s15 and p.z == max(D("0.2"), D("0.1") * p.s15)
    assert p.s15 is not None and s15_before is not None
    core.s15 = p.s15 * 3  # a later scale change never widens the frozen zone
    assert p.z == max(D("0.2"), D("0.1") * p.s15)


def _ongoing_call(now: datetime, *, issued: datetime, family="A", progress_at=None, hard=None) -> Call:
    return Call(cid="call-x", aid="AL-x", family=family, d=1, origin="HISTORICAL_MODELED", issued_at=issued,
                issue_seq=1, trigger_start=issued - MIN, ref=P0, v=P0 - 50, t=P0 + 400, target_type="LANDMARK",
                limiting=None, s15=D(30), area=(P0 - 7, P0 + 7), expected=(30, 180), min_residual=30,
                hard_deadline=hard or issued + timedelta(hours=4), progress_at=progress_at or issued + timedelta(hours=2),
                premise_kind="15M_CLOSE_BEYOND_IMPULSE_A", premise_level=P0 - 500, last_end=now)


def test_b5_retired_guidance_frees_the_slot_before_a_coincident_trigger():
    """Half-horizon STALLED retirement at 12:00 and an armed C trigger in the same dispatch: the slot is released
    first, so the new call issues immediately (no wait for any hypothetical pending exit)."""
    now = T - MIN
    rig = Rig()
    prime(rig, now, [P0 + (10 if i % 2 else -10) for i in range(30)], balanced_h1(T - timedelta(minutes=59)))
    core = rig.core
    core.call = _ongoing_call(now, issued=T - timedelta(hours=2), progress_at=T)
    core.call.max_fav_t = D(3)  # < 0.5 * S15 (15)
    bx = Box("box-c", P0 - 300, P0 + 1900, P0 + 800, D(30), D(3), T - timedelta(hours=1), 1, T + timedelta(hours=3),
             ["s"])
    core.box = bx
    a = Attempt(aid="CL-t", family="C", d=1, owner=bx.bid, born_at=T - timedelta(minutes=15), born_seq=1,
                sources=["s"], deadline=T + timedelta(minutes=15), s15=D(30), z=D(3), status="ARMED",
                k_t=P0, v_t=P0 - 40, arm_at=T - timedelta(minutes=15), arm_seq=2)
    core.attempts[a.aid] = a
    rig._bar(T - MIN, P0, P0 + 2, P0 - 1, P0 + 1)
    out = rig.dispatch(T)
    revs = [e["record"] for e in out if e["kind"] == "call_revision"]
    calls = [e["record"] for e in out if e["kind"] == "call"]
    assert revs and revs[0]["thesis_status"] == "RETIRED" and revs[0]["terminal_reason"] == "STALLED"
    assert calls and calls[0]["attempt_id"] == "CL-t"
    seqs = [e["seq"] for e in out if e["kind"] in ("call_revision", "call")]
    assert seqs == sorted(seqs)  # retirement journalled before the new issue


def test_b5_progress_uses_max_favorable_close_not_last_close_or_intrabar_high():
    rig = Rig()
    now = T - timedelta(minutes=2)
    prime(rig, now, [P0 + (10 if i % 2 else -10) for i in range(30)], balanced_h1(T - timedelta(minutes=58)))
    core = rig.core
    core.call = _ongoing_call(now, issued=T - timedelta(hours=2), progress_at=T)
    core.call.max_fav_t = D(18)  # an earlier close +0.6*S15
    rig._bar(T - 2 * MIN, P0, P0, P0, P0)
    rig.dispatch(T - MIN)
    rig._bar(T - MIN, P0, P0 + 40, P0, P0)  # intrabar high only; last close back to the reference
    out = rig.dispatch(T)
    assert core.call is not None and core.call.progress_done and core.call.thesis == "ONGOING"
    assert not [e for e in out if e["kind"] == "call_revision" and e["record"]["thesis_status"] == "RETIRED"]


def test_b6_residual_time_closes_new_entry_without_ending_the_thesis():
    rig = Rig()
    now = T - MIN
    prime(rig, now, [P0 + (10 if i % 2 else -10) for i in range(30)], balanced_h1(T - timedelta(minutes=59)))
    core = rig.core
    core.call = _ongoing_call(now, issued=T - timedelta(hours=3, minutes=31), hard=T + timedelta(minutes=29),
                              progress_at=T - timedelta(hours=1))
    core.call.progress_done = True
    rig._bar(T - MIN, P0, P0 + 1, P0 - 1, P0)
    out = rig.dispatch(T)
    rev = [e["record"] for e in out if e["kind"] == "call_revision"][-1]
    assert rev["thesis_status"] == "ONGOING" and rev["entry_status"] == "CLOSED" and "TOO_LATE" in rev["entry_reasons"]
    assert rev["duration_window_minutes"] is None  # remaining 29 < 30: no entry-duration window offered


def test_b6_straddling_issue_minute_with_possible_contact_is_unassessable():
    """Recorded/live clock: issue published 12:00:30; the complete minute [12:00, 12:01) straddles it and its high
    reaches T: contact time cannot be certified -> UNASSESSABLE, never TARGET_REACHED."""
    rig = Rig()
    issued = T + timedelta(seconds=30)
    prime(rig, issued, [P0 + (10 if i % 2 else -10) for i in range(30)], balanced_h1(T - timedelta(minutes=30)))
    core = rig.core
    core.call = _ongoing_call(issued, issued=issued)
    core.call.last_end = None
    rig._bar(T, P0, P0 + 400, P0 - 1, P0 + 1)
    out = rig.dispatch(T + MIN + timedelta(seconds=2))
    rev = [e["record"] for e in out if e["kind"] == "call_revision"][-1]
    assert rev["thesis_status"] == "UNASSESSABLE" and rev["terminal_reason"] == "CONTACT_TIME_AMBIGUOUS"


def test_a_renewal_latch_requires_terminal_then_false_then_new_true(monkeypatch):
    rig = Rig()
    prime(rig, T, [P0 + i for i in range(30)])
    core = rig.core
    script: list[bool | None] = []
    monkeypatch.setattr(core, "_qa", lambda d, t: script.pop(0) if d == 1 else None)
    bar = core.m15[-1]
    births = []

    def obs(v):
        script.append(v)
        before = {a for a in core.attempts}
        core._a_births(bar, T)
        births.extend(sorted(set(core.attempts) - before))

    obs(True)  # first assessable observation true: initial birth
    assert len(births) == 1
    obs(True)  # true while the episode is pending never queues a replacement
    obs(False)  # false while pending does not count
    core.attempts.clear()  # the episode becomes terminal
    obs(True)  # still true after terminal: no rolling re-anchor
    assert len(births) == 1 and core.counters["a_true_while_pending"] == 1
    obs(False)
    obs(True)  # terminal -> false -> new true
    assert len(births) == 2


def test_box_birth_token_one_per_compression_episode(monkeypatch):
    rig = Rig()
    prime(rig, T, [P0 + (5 if i % 2 else -5) for i in range(30)])
    core = rig.core
    phases: list[str] = []
    monkeypatch.setattr(core, "phase_now", lambda t: phases.pop(0))
    bar = core.m15[-1]
    seq = []
    for ph in ("TRANSITION", "COMPRESSION", "COMPRESSION", "ROTATION"):
        phases.append(ph)
        core._box_birth(bar, T)
        seq.append(core.box_token)
    # INIT -> READY (first assessable not compression) -> TOKEN on false->true -> geometry not qualified keeps the
    # token while compression lasts -> discarded when compression ends
    assert seq == ["READY", "TOKEN", "TOKEN", "READY"] and core.box is None
    assert core.counters["box_tokens_discarded"] == 1
