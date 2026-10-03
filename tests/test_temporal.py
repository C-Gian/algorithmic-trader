"""WP-008-R2 evidence (pure, no database): causal temporal substrate - UTC anchors, exact aggregates, seal-no-revision
late policy, cutoff invariance, modeled/recorded clock barriers, deadlines, restore, readiness and bounded state.

Tiny hand-authored fixtures plus a differential comparison with the separate naive reference aggregator. These are
engineering correctness checks of factual infrastructure, not market evaluations.
"""

from __future__ import annotations

import json
import tracemalloc
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from algotrader.feed.adapter import make_event
from algotrader.feed.contracts import (
    AvailabilityBasis,
    AvailabilityPolicy,
    ChannelCoverage,
    ChannelRef,
    EventKind,
    Family,
    FundingPayload,
    IndexBarPayload,
    MarkBarPayload,
    QualityReason,
    SlotQualityPayload,
    SourceRef,
    TradeBarPayload,
)
from algotrader.feed.ordering import modeled_availability, order_events
from algotrader.temporal import calendar as cal
from algotrader.temporal import engine as te
from algotrader.temporal.contracts import (
    AggregateStatus,
    ClockPolicy,
    Deadline,
    DeadlineKind,
    Dependency,
    Horizon,
    ReadinessStatus,
)
from algotrader.temporal.reference import ReferenceAggregator

MIN = timedelta(minutes=1)
INST, IDX = "BTC-USDT-SWAP", "BTC-USDT"
TRADE = ChannelRef(source="okx", family=Family.TRADE_BAR_1M, series_id=INST)
MARK = ChannelRef(source="okx", family=Family.MARK_BAR_1M, series_id=INST)
INDEX = ChannelRef(source="okx", family=Family.INDEX_BAR_1M, series_id=IDX)
FUND = ChannelRef(source="okx", family=Family.FUNDING_SETTLEMENT, series_id=INST)
SRC = SourceRef(dataset_id="fixture", artifact="fixture", row_index=None, raw_page_ref=None, retrieved_at=None,
                source_availability_policy="fixture")
MODELED = modeled_availability()
RECORDED = AvailabilityPolicy(policy_id="recorded.fixture.v1", basis=AvailabilityBasis.RECORDED,
                              base_policy_id="fixture", bar_delay=timedelta(0), funding_delay=timedelta(0),
                              measured=True, note="fixture receipt times")
T0 = datetime(2025, 9, 1, tzinfo=UTC)  # a Monday


def D(x) -> Decimal:
    return Decimal(str(x))


def bar(ch: ChannelRef, t: datetime, o, h, l, c, *, vol=("1", "0.01", "100"), received: datetime | None = None,
        policy: AvailabilityPolicy = MODELED):
    if ch.family == Family.TRADE_BAR_1M:
        p = TradeBarPayload(open=D(o), high=D(h), low=D(l), close=D(c), volume_contracts=D(vol[0]),
                            volume_base=D(vol[1]), volume_base_ccy="BTC", volume_quote=D(vol[2]),
                            volume_quote_ccy="USDT")
    elif ch.family == Family.MARK_BAR_1M:
        p = MarkBarPayload(open=D(o), high=D(h), low=D(l), close=D(c))
    else:
        p = IndexBarPayload(index_id=IDX, open=D(o), high=D(h), low=D(l), close=D(c))
    return make_event(ch, EventKind.BAR_OBSERVATION, t, t + MIN, received or t + MIN, policy, SRC, p)


def flat(ch: ChannelRef, t: datetime, price=100, **kw):
    return bar(ch, t, price, price, price, price, **kw)


def quality(ch: ChannelRef, t: datetime, reason: QualityReason, *, received=None, policy=MODELED):
    return make_event(ch, EventKind.SLOT_QUALITY, t, t + MIN, received or t + MIN, policy, SRC,
                      SlotQualityPayload(reason=reason, detail="fixture"))


def funding(t: datetime, rate="0.0001", policy=MODELED):
    return make_event(FUND, EventKind.FUNDING_OBSERVATION, t, None, t, policy, SRC,
                      FundingPayload(funding_rate=D(rate), realized_rate=None, method=None, formula_type=None))


def cov(ch: ChannelRef, start: datetime, end: datetime) -> ChannelCoverage:
    return ChannelCoverage(channel=ch, covered_from=start, covered_until=end,
                           expected_cadence=None if ch.family == Family.FUNDING_SETTLEMENT else MIN)


def engine(coverage, policy=ClockPolicy.MODELED_COMPLETE_PREFIX, allowance=timedelta(0), basis=None, **kw):
    prof = te.default_profile(policy, allowance, **kw)
    b = basis or (AvailabilityBasis.MODELED if policy == ClockPolicy.MODELED_COMPLETE_PREFIX
                  else AvailabilityBasis.RECORDED)
    return te.TemporalEngine(prof, tuple(coverage), basis=b, availability_policy_id="fixture",
                             content_identity="feedcontent.fixture")


def run(eng: te.TemporalEngine, events, *, finish=True):
    sealed, disps = [], []
    eng.sealed_listeners.append(sealed.append)
    eng.dispatch_listeners.append(disps.append)
    for i, e in enumerate(order_events(events)):
        eng.on_event(e, i)
    if finish:
        eng.finish()
    return sealed, disps


def find(sealed, channel: ChannelRef, h: Horizon, start: datetime):
    rid = f"{channel.channel_id}/{h.value}/{start.isoformat()}"
    hits = [r for r in sealed if r.record_id == rid]
    assert len(hits) == 1, rid
    return hits[0]


def minutes(ch, start, n, price=100, **kw):
    return [flat(ch, start + MIN * i, price, **kw) for i in range(n)]


# ---------------------------------------------------------------------------
# A. UTC anchors
# ---------------------------------------------------------------------------


def test_utc_anchors_weeks_months_and_dst_irrelevance():
    t = datetime(2025, 9, 3, 13, 47, tzinfo=UTC)  # Wednesday
    assert cal.interval_start(Horizon.M15, t) == datetime(2025, 9, 3, 13, 45, tzinfo=UTC)
    assert cal.interval_start(Horizon.H1, t) == datetime(2025, 9, 3, 13, tzinfo=UTC)
    assert cal.interval_start(Horizon.H4, t) == datetime(2025, 9, 3, 12, tzinfo=UTC)
    assert cal.interval_start(Horizon.D1, t) == datetime(2025, 9, 3, tzinfo=UTC)
    assert cal.interval_start(Horizon.W1, t) == datetime(2025, 9, 1, tzinfo=UTC)  # Monday 00:00 UTC
    sunday_late = datetime(2025, 9, 7, 23, 59, tzinfo=UTC)
    assert cal.interval_start(Horizon.W1, sunday_late) == datetime(2025, 9, 1, tzinfo=UTC)
    assert cal.interval_start(Horizon.W1, datetime(2025, 9, 8, tzinfo=UTC)) == datetime(2025, 9, 8, tzinfo=UTC)
    assert cal.interval_start(Horizon.MO1, t) == datetime(2025, 9, 1, tzinfo=UTC)
    # calendar months: actual length (leap and non-leap February, December roll-over)
    assert cal.expected_minutes(Horizon.MO1, datetime(2024, 2, 1, tzinfo=UTC)) == 29 * 1440
    assert cal.expected_minutes(Horizon.MO1, datetime(2025, 2, 1, tzinfo=UTC)) == 28 * 1440
    assert cal.expected_minutes(Horizon.MO1, datetime(2025, 9, 1, tzinfo=UTC)) == 30 * 1440
    assert cal.interval_end(Horizon.MO1, datetime(2025, 12, 1, tzinfo=UTC)) == datetime(2026, 1, 1, tzinfo=UTC)
    assert cal.expected_minutes(Horizon.MO1, datetime(2025, 12, 1, tzinfo=UTC)) == 31 * 1440
    # DST is irrelevant: the European/US switch days are ordinary 1440-minute UTC days
    for d in (datetime(2025, 3, 30, tzinfo=UTC), datetime(2025, 3, 9, tzinfo=UTC), datetime(2025, 10, 26, tzinfo=UTC)):
        assert cal.expected_minutes(Horizon.D1, d) == 1440
    # an aware non-UTC time maps to the same UTC anchor; naive times are rejected
    from zoneinfo import ZoneInfo

    rome = datetime(2025, 3, 30, 3, 30, tzinfo=ZoneInfo("Europe/Rome"))  # 01:30 UTC
    assert cal.interval_start(Horizon.D1, rome) == datetime(2025, 3, 30, tzinfo=UTC)
    with pytest.raises(cal.CalendarError):
        cal.interval_start(Horizon.H1, datetime(2025, 3, 30, 1))


def test_partial_coverage_intervals_are_outside_coverage_with_visible_reasons():
    start, end = T0 + timedelta(minutes=40), T0 + timedelta(hours=2, minutes=20)
    eng = engine([cov(TRADE, start, end)])
    sealed, _ = run(eng, minutes(TRADE, start, 100))
    first = find(sealed, TRADE, Horizon.H1, T0)
    assert first.status == AggregateStatus.OUTSIDE_COVERAGE and first.values is None
    assert first.counts.expected == 60 and first.counts.valid == 20 and first.counts.reasons == {"OUTSIDE_COVERAGE": 40}
    middle = find(sealed, TRADE, Horizon.H1, T0 + timedelta(hours=1))
    assert middle.status == AggregateStatus.COMPLETE
    last = find(sealed, TRADE, Horizon.H1, T0 + timedelta(hours=2))
    assert last.status == AggregateStatus.OUTSIDE_COVERAGE and last.counts.reasons == {"OUTSIDE_COVERAGE": 40}
    # a coverage cut never produces a complete truncated higher bar
    assert all(r.status != AggregateStatus.COMPLETE for r in sealed if r.horizon in (Horizon.H4, Horizon.D1))
    # counts always reconcile exactly
    for r in sealed:
        c = r.counts
        assert c.valid + c.missing + c.rejected == c.expected
        assert sum(c.reasons.values()) == c.missing + c.rejected


# ---------------------------------------------------------------------------
# B. Exact OHLC / typed volumes per family; funding sparse and distinct
# ---------------------------------------------------------------------------


def test_exact_ohlc_and_decimal_typed_volumes_per_family_and_sparse_funding():
    end = T0 + timedelta(minutes=15)
    rows = [("100.5", "101", "100", "100.7"), ("100.7", "103.25", "100.1", "102"), ("102", "102.5", "99.75", "100")]
    rows += [("100", "100.5", "100", "100.25")] * 12
    trade = [bar(TRADE, T0 + MIN * i, *r, vol=("0.1", "0.001", "10.05")) for i, r in enumerate(rows)]
    mark = [bar(MARK, T0 + MIN * i, *r) for i, r in enumerate(rows)]
    index = [bar(INDEX, T0 + MIN * i, *r) for i, r in enumerate(rows)]
    eng = engine([cov(TRADE, T0, end), cov(MARK, T0, end), cov(INDEX, T0, end),
                  cov(FUND, T0, end)])
    sealed, _ = run(eng, trade + mark + index + [funding(T0 + timedelta(minutes=8))])
    t = find(sealed, TRADE, Horizon.M15, T0)
    assert t.status == AggregateStatus.COMPLETE and t.counts.valid == t.counts.expected == 15
    v = t.values
    assert (v.open, v.high, v.low, v.close) == (D("100.5"), D("103.25"), D("99.75"), D("100.25"))
    assert v.volume_contracts == D("1.5") and v.volume_base == D("0.015") and v.volume_quote == D("150.75")
    assert (v.volume_base_ccy, v.volume_quote_ccy) == ("BTC", "USDT")
    m = find(sealed, MARK, Horizon.M15, T0).values
    assert (m.open, m.high, m.low, m.close) == (D("100.5"), D("103.25"), D("99.75"), D("100.25"))
    assert m.volume_contracts is m.volume_base is m.volume_quote is None  # no fabricated volume
    i = find(sealed, INDEX, Horizon.M15, T0).values
    assert i.index_id == IDX and i.volume_contracts is None
    assert t.known_at == end and t.sealed_at == end  # modeled: known at the last prerequisite's availability
    # funding: sparse settlement context only - no candle records, never summed into price/volume
    assert not [r for r in sealed if r.channel.family == Family.FUNDING_SETTLEMENT]
    fund = [x for x in eng.readiness() if x.dependency == "demo.funding"][0]
    assert fund.status == ReadinessStatus.READY and fund.latest_record_id is not None


def test_ohlc_follows_market_slot_order_not_admission_order():
    """Recorded receipts out of slot order: open is the earliest slot, close the latest slot."""
    start, end = T0, T0 + timedelta(minutes=15)
    evs = []
    for i in range(15):
        recv = T0 + timedelta(minutes=15, seconds=59 - i)  # later slots received earlier
        evs.append(bar(TRADE, start + MIN * i, 100 + i, 100 + i, 100 + i, 100 + i, received=recv, policy=RECORDED))
    eng = engine([cov(TRADE, start, end)], ClockPolicy.RECORDED_SYNTHETIC_BARRIER, timedelta(seconds=120))
    sealed, _ = run(eng, evs)
    r = find(sealed, TRADE, Horizon.M15, start)
    assert r.status == AggregateStatus.COMPLETE
    assert (r.values.open, r.values.close, r.values.high, r.values.low) == (D(100), D(114), D(114), D(100))
    assert r.known_at == T0 + timedelta(minutes=15, seconds=59)  # max(end, latest prerequisite receipt)


# ---------------------------------------------------------------------------
# C. Missing / rejected / late
# ---------------------------------------------------------------------------


def test_missing_or_rejected_constituent_never_completes():
    end = T0 + timedelta(minutes=30)
    evs = minutes(TRADE, T0, 30)
    evs[3] = quality(TRADE, T0 + MIN * 3, QualityReason.MISSING)
    evs[20] = quality(TRADE, T0 + MIN * 20, QualityReason.INVALID_ROW)
    sealed, _ = run(engine([cov(TRADE, T0, end)]), evs)
    a = find(sealed, TRADE, Horizon.M15, T0)
    assert a.status == AggregateStatus.INCOMPLETE and a.values is None and a.partial_diagnostic is not None
    assert (a.counts.valid, a.counts.missing, a.counts.rejected, a.counts.reasons) == (14, 1, 0, {"MISSING": 1})
    b = find(sealed, TRADE, Horizon.M15, T0 + timedelta(minutes=15))
    assert b.status == AggregateStatus.INCOMPLETE
    assert (b.counts.valid, b.counts.rejected, b.counts.reasons) == (14, 1, {"INVALID_ROW": 1})
    assert a.known_at == a.sealed_at  # incompleteness becomes known at the sealing barrier


def test_late_before_barrier_contributes_and_late_after_seal_never_revises():
    allowance = timedelta(seconds=120)
    end = T0 + timedelta(hours=1)  # evidence exists for the first 30 minutes only
    evs = []
    for i in range(30):
        recv = T0 + MIN * (i + 1) + timedelta(seconds=2)
        if i == 13:
            recv = T0 + timedelta(minutes=15, seconds=90)  # late, but before the 15m barrier (end + 120 s)
        if i == 29:
            recv = T0 + timedelta(minutes=33)  # after the second interval's barrier (30:00 + 120 s)
        evs.append(flat(TRADE, T0 + MIN * i, 100 + i, received=recv, policy=RECORDED))
    eng = engine([cov(TRADE, T0, end)], ClockPolicy.RECORDED_SYNTHETIC_BARRIER, allowance)
    sealed, disps = [], []
    eng.sealed_listeners.append(sealed.append)
    eng.dispatch_listeners.append(disps.append)
    ordered = order_events(evs)
    chain_before_late = None
    for i, e in enumerate(ordered):
        if e.event_time == T0 + MIN * 29:
            chain_before_late = (eng.aggregate_chain, [r.record_id for r in sealed])
        eng.on_event(e, i)
    first = find(sealed, TRADE, Horizon.M15, T0)
    assert first.status == AggregateStatus.COMPLETE  # the late-but-in-time minute contributed
    assert first.known_at == T0 + timedelta(minutes=15, seconds=90) and first.sealed_at == first.known_at
    second = find(sealed, TRADE, Horizon.M15, T0 + timedelta(minutes=15))
    assert second.status == AggregateStatus.INCOMPLETE and second.counts.reasons == {"ABSENT_AT_SEAL": 1}
    assert second.sealed_at == T0 + timedelta(minutes=32)  # its closure barrier: end + allowance
    # the late minute after the seal: counted, never revises the sealed record or regresses the newest interval
    t15 = eng.tracks[f"{TRADE.channel_id}/15m"]
    assert t15.late_excluded == 1
    assert t15.sealed[-1]["record_id"] == second.record_id and t15.sealed[-1]["status"] == "INCOMPLETE"
    assert chain_before_late[1] == [r.record_id for r in sealed][:len(chain_before_late[1])]
    # it still contributes to the hour, which was not sealed yet (per-interval policy)
    eng.finish()
    hour = find(sealed, TRADE, Horizon.H1, T0)
    assert hour.counts.valid == 30 and hour.status == AggregateStatus.INCOMPLETE
    assert hour.counts.reasons == {"ABSENT_AT_SEAL": 30}


# ---------------------------------------------------------------------------
# D. Cutoff perturbation
# ---------------------------------------------------------------------------


def test_events_after_a_dispatch_cutoff_cannot_change_it():
    end = T0 + timedelta(hours=2)
    base = minutes(TRADE, T0, 120) + minutes(MARK, T0, 120)
    cutoff = 140  # admitted events in canonical order
    ordered = order_events(base)
    perturbed = list(ordered[:cutoff]) + [flat(e.channel, e.event_time, 777) for e in ordered[cutoff:]]

    def until_cutoff(events):
        eng = engine([cov(TRADE, T0, end), cov(MARK, T0, end)])
        disps = []
        eng.dispatch_listeners.append(disps.append)
        for i, e in enumerate(order_events(events)):
            if i == cutoff:
                break
            eng.on_event(e, i)
        return te.pack(eng)[1], [json.loads(d.model_dump_json()) for d in disps], eng

    sha_a, disp_a, eng_a = until_cutoff(ordered)
    sha_b, disp_b, _ = until_cutoff(perturbed)
    assert sha_a == sha_b and disp_a == disp_b and disp_a
    assert all(d["admitted_cursor"] <= cutoff for d in disp_a)
    # and the full perturbed run differs only after the cutoff
    eng_full = engine([cov(TRADE, T0, end), cov(MARK, T0, end)])
    full = []
    eng_full.dispatch_listeners.append(full.append)
    for i, e in enumerate(order_events(perturbed)):
        eng_full.on_event(e, i)
    assert [json.loads(d.model_dump_json()) for d in full][:len(disp_a)] == disp_a


# ---------------------------------------------------------------------------
# E. Modeled ties and pending boundaries
# ---------------------------------------------------------------------------


def test_modeled_barrier_sees_the_whole_tie_group_and_restores_a_pending_boundary():
    end = T0 + timedelta(minutes=30)
    evs = minutes(TRADE, T0, 30) + minutes(MARK, T0, 30) + minutes(INDEX, T0, 30)
    covs = [cov(TRADE, T0, end), cov(MARK, T0, end), cov(INDEX, T0, end)]
    eng = engine(covs)
    sealed, disps = run(eng, evs, finish=False)
    closure = [d for d in disps if d.clock_time == T0 + timedelta(minutes=15)]
    assert len(closure) == 1
    d = closure[0]
    # the barrier at 00:15 ran after all three families' 00:14 bars (available 00:15) were admitted
    assert d.admitted_cursor == 45
    assert sorted(x.split(":")[1].split("/")[2] for x in d.reasons if x.startswith("closed:")) == [
        "index_bar_1m", "mark_bar_1m", "trade_bar_1m"]
    assert set(d.closed_record_ids) == {f"{c.channel_id}/15m/{T0.isoformat()}" for c in (TRADE, MARK, INDEX)}
    # restore exactly inside the tie group at 00:15 (first of three events admitted, barrier still pending)
    ordered = order_events(evs)
    ref = engine(covs)
    for i, e in enumerate(ordered):
        ref.on_event(e, i)
    for cut in (42, 43, 44, 45, 46):
        a = engine(covs)
        for i, e in enumerate(ordered[:cut]):
            a.on_event(e, i)
        if cut in (43, 44):
            assert a.summary()["pending_tie_time"] == (T0 + timedelta(minutes=15)).isoformat()
            assert a.dispatch_seq == 0  # the 00:15 dispatch is pending until the tie group is complete
        b = te.unpack(*te.pack(a))
        for i, e in enumerate(ordered[cut:], start=cut):
            b.on_event(e, i)
        assert b.commitment() == ref.commitment() and te.pack(b)[1] == te.pack(ref)[1]


def test_stepwise_checkpointing_at_every_event_equals_one_pass():
    end = T0 + timedelta(hours=5)
    evs = minutes(TRADE, T0, 300) + minutes(MARK, T0, 300) + [funding(T0 + timedelta(hours=4))]
    evs[50] = quality(TRADE, T0 + MIN * 50, QualityReason.MISSING)
    covs = [cov(TRADE, T0, end), cov(MARK, T0, end), cov(FUND, T0, end)]
    deadlines = (Deadline(deadline_id="r1", due=T0 + timedelta(hours=1, minutes=7)),)
    one = engine(covs, deadlines=deadlines)
    run(one, evs)
    step = engine(covs, deadlines=deadlines)
    for i, e in enumerate(order_events(evs)):
        step = te.unpack(*te.pack(step))  # pause/STEP/checkpoint boundary at every event
        step.on_event(e, i)
    step = te.unpack(*te.pack(step))
    step.finish()
    assert te.pack(step)[1] == te.pack(one)[1] and step.commitment() == one.commitment()


# ---------------------------------------------------------------------------
# F. Recorded / live-style execution
# ---------------------------------------------------------------------------


def test_recorded_equal_time_receipts_get_separate_barriers_and_delayed_close_completes_early():
    end = T0 + timedelta(minutes=15)
    evs = [flat(TRADE, T0 + MIN * i, received=T0 + MIN * (i + 1) + timedelta(seconds=3), policy=RECORDED)
           for i in range(14)]
    same = T0 + timedelta(minutes=15, seconds=30)  # delayed close of 00:14 and a mark bar share a receipt time
    evs.append(flat(TRADE, T0 + MIN * 14, received=same, policy=RECORDED))
    evs.append(flat(MARK, T0 + MIN * 14, received=same, policy=RECORDED))
    eng = engine([cov(TRADE, T0, end), cov(MARK, T0 + MIN * 14, end)], ClockPolicy.RECORDED_SYNTHETIC_BARRIER,
                 timedelta(seconds=120))
    sealed, disps = run(eng, evs, finish=False)
    at_same = [d for d in disps if d.clock_time == same]
    assert [d.admitted_cursor for d in at_same] == [15, 16]  # no wait for a 'complete' tie group
    trade15 = find(sealed, TRADE, Horizon.M15, T0)
    assert trade15.sealed_at == same and trade15.admitted_cursor == 15 and trade15.status == AggregateStatus.COMPLETE
    assert trade15.closure_dispatch_id == at_same[0].dispatch_id
    # the equal-time mark receipt completes the mark interval's only in-coverage minute: its own later dispatch
    mark15 = find(sealed, MARK, Horizon.M15, T0)
    assert at_same[1].closed_record_ids == (mark15.record_id,) and mark15.admitted_cursor == 16
    assert mark15.status == AggregateStatus.OUTSIDE_COVERAGE and mark15.counts.reasons == {"OUTSIDE_COVERAGE": 14}
    assert ClockPolicy.RECORDED_SYNTHETIC_BARRIER.value == "temporal.clock.recorded-replay-synthetic-barrier.v1"
    from algotrader.temporal.contracts import CLOCK_POLICY_TEXT

    assert "NOT a reproduction" in CLOCK_POLICY_TEXT[ClockPolicy.RECORDED_SYNTHETIC_BARRIER]


def _tape():
    """Admission/clock command tape: equal-timestamp receipts with a barrier between them."""
    r = T0 + timedelta(minutes=15, seconds=5)
    evs = [flat(TRADE, T0 + MIN * i, received=T0 + MIN * (i + 1) + timedelta(seconds=1), policy=RECORDED)
           for i in range(14)]
    evs += [flat(TRADE, T0 + MIN * 14, received=r, policy=RECORDED), flat(MARK, T0 + MIN * 14, received=r,
                                                                         policy=RECORDED)]
    ordered = order_events(evs)
    cmds: list[tuple] = []
    for i, e in enumerate(ordered):
        cmds.append(("admit", i, e))
        if i in (13, 14, 15):  # the trade close, then a barrier, then the equal-time mark receipt, another barrier
            cmds.append(("advance", e.available_time))
        if i == 14:
            cmds.append(("register", Deadline(deadline_id="pub", due=r + timedelta(seconds=10),
                                              kind=DeadlineKind.PUBLICATION)))
    cmds.append(("advance", r + timedelta(seconds=30)))
    return cmds, (cov(TRADE, T0, T0 + timedelta(minutes=15)), cov(MARK, T0 + MIN * 14, T0 + timedelta(minutes=15)))


def _exec(eng, cmd):
    if cmd[0] == "admit":
        eng.on_event(cmd[2], cmd[1])
    elif cmd[0] == "advance":
        eng.advance_to(cmd[1])
    else:
        eng.register(cmd[1])


def test_dispatch_tape_replay_equals_live_style_incremental_execution():
    cmds, covs = _tape()
    live = engine(covs, ClockPolicy.RECORDED_DISPATCH_TAPE, timedelta(seconds=120))
    seen = []
    live.dispatch_listeners.append(seen.append)
    for c in cmds:  # live-style: the process is checkpointed and restored between every command
        live = te.unpack(*te.pack(live))
        live.dispatch_listeners.append(seen.append)
        _exec(live, c)
    replay = engine(covs, ClockPolicy.RECORDED_DISPATCH_TAPE, timedelta(seconds=120))
    rep = []
    replay.dispatch_listeners.append(rep.append)
    for c in cmds:
        _exec(replay, c)
    assert [json.loads(d.model_dump_json()) for d in seen] == [json.loads(d.model_dump_json()) for d in rep]
    assert replay.commitment() == live.commitment()
    same = [d for d in rep if d.clock_time == T0 + timedelta(minutes=15, seconds=5)]
    # the later equal-time receipt causes a later dispatch with a different admitted cursor
    assert [d.admitted_cursor for d in same] == [15, 16]
    assert any(d.callbacks == ("pub",) for d in rep)
    # a receipt time before an already processed barrier cannot be admitted (no reordering into perfect batches)
    late = flat(INDEX, T0, received=T0 + timedelta(minutes=1), policy=RECORDED)
    with pytest.raises(te.TemporalError):
        replay.admit(late, replay.cursor)


# ---------------------------------------------------------------------------
# G. Deadlines, finite clock end, ordered ids
# ---------------------------------------------------------------------------


def test_equal_time_expiry_runs_before_publication_and_timers_fire_without_events():
    end = T0 + timedelta(hours=3)
    due = T0 + timedelta(hours=1, minutes=30)  # inside a 40-minute evidence gap
    dl = (Deadline(deadline_id="z-pub", due=due, priority=0, kind=DeadlineKind.PUBLICATION),
          Deadline(deadline_id="a-reason", due=due, priority=9, kind=DeadlineKind.REASONING),
          Deadline(deadline_id="m-expiry", due=due, priority=5, kind=DeadlineKind.EXPIRY),
          Deadline(deadline_id="after-end", due=end + timedelta(hours=5), kind=DeadlineKind.EXPIRY))
    evs = [e for e in minutes(TRADE, T0, 180) if not (T0 + timedelta(hours=1, minutes=10)
                                                     <= e.event_time < T0 + timedelta(hours=1, minutes=50))]
    eng = engine([cov(TRADE, T0, end)], ClockPolicy.RECORDED_SYNTHETIC_BARRIER, timedelta(seconds=60),
                 deadlines=dl, basis=AvailabilityBasis.RECORDED)
    sealed, disps = run(eng, [flat(TRADE, e.event_time, received=e.available_time, policy=RECORDED) for e in evs])
    fired = [d for d in disps if d.callbacks]
    assert fired[0].clock_time == due and fired[0].callbacks == ("m-expiry", "a-reason", "z-pub")
    assert fired[0].admitted_cursor == 70  # no event in the gap; no bar fabricated
    assert all(r.counts.valid <= r.counts.expected for r in sealed)
    gap15 = find(sealed, TRADE, Horizon.M15, T0 + timedelta(hours=1, minutes=15))
    assert gap15.counts.valid == 0 and gap15.counts.reasons == {"ABSENT_AT_SEAL": 15}
    # finite clock end: stops there; a later deadline never fires and nothing advances further
    assert eng.clock == end + timedelta(seconds=60) and "after-end" in eng.deadlines
    seqs = [d.seq for d in disps]
    assert seqs == list(range(1, len(disps) + 1)) and len({d.dispatch_id for d in disps}) == len(disps)


def test_clock_and_cursor_are_monotone_and_registered_ids_unique():
    eng = engine([cov(TRADE, T0, T0 + timedelta(hours=1))])
    run(eng, minutes(TRADE, T0, 20), finish=False)
    with pytest.raises(te.TemporalError):
        eng.advance_to(T0)  # backwards
    with pytest.raises(te.TemporalError):
        eng.on_event(flat(TRADE, T0 + MIN * 30), 5)  # cursor discontinuity
    eng.register(Deadline(deadline_id="x", due=T0 + timedelta(hours=2)))
    with pytest.raises(te.TemporalError):
        eng.register(Deadline(deadline_id="x", due=T0 + timedelta(hours=3)))


# ---------------------------------------------------------------------------
# H. Differential: separate reference aggregator; restore anywhere
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("policy", [ClockPolicy.MODELED_COMPLETE_PREFIX, ClockPolicy.RECORDED_SYNTHETIC_BARRIER])
def test_engine_matches_the_separate_reference_aggregator(policy):
    import random

    rnd = random.Random(7)
    start = datetime(2025, 8, 31, 22, 37, tzinfo=UTC)  # crosses a week, a month and coverage cuts
    end = start + timedelta(hours=30)
    evs = []
    recorded = policy != ClockPolicy.MODELED_COMPLETE_PREFIX
    p = RECORDED if recorded else MODELED
    for ch in (TRADE, MARK, INDEX):
        for i in range(30 * 60):
            t = start + MIN * i
            recv = t + MIN + timedelta(seconds=rnd.choice([1, 2, 5, 40, 150, 400])) if recorded else None
            x = rnd.random()
            if x < 0.01:
                continue  # absent (recorder outage)
            if x < 0.02:
                evs.append(quality(ch, t, QualityReason.MISSING, received=recv, policy=p))
            elif x < 0.025:
                evs.append(quality(ch, t, QualityReason.CONFLICTING_DUPLICATE, received=recv, policy=p))
            else:
                v = 100 + rnd.random()
                evs.append(bar(ch, t, f"{v:.2f}", f"{v + 1:.2f}", f"{v - 1:.2f}", f"{v:.1f}",
                               vol=(f"{rnd.random():.3f}", "0.001", "1.5"), received=recv, policy=p))
    allowance = timedelta(seconds=120) if recorded else timedelta(0)
    covs = [cov(ch, start, end) for ch in (TRADE, MARK, INDEX)]
    eng = engine(covs, policy, allowance)
    ref = ReferenceAggregator(tuple(covs), te.HORIZON_ORDER, allowance, policy)
    for i, e in enumerate(order_events(evs)):
        eng.on_event(e, i)
        ref.feed(e)
        if i % 997 == 0:
            assert eng.aggregate_chain == ref.chain, f"diverged at cursor {i + 1}"
    eng.finish()
    ref.finish(eng.default_clock_end())
    assert eng.aggregate_chain == ref.chain and eng.counters["sealed"] == len(ref.sealed)
    if recorded:
        assert eng.counters["late_excluded"] > 0  # the fixture really exercises late evidence


# ---------------------------------------------------------------------------
# I. Readiness, staleness, optional unknown, capacity, bounded state
# ---------------------------------------------------------------------------


def test_readiness_is_dependency_specific_with_all_blockers_and_staleness_without_events():
    end = T0 + timedelta(hours=6)
    deps = (Dependency(name="t15", family=Family.TRADE_BAR_1M, horizon=Horizon.M15, required_complete=4,
                       freshness_allowance=timedelta(minutes=30)),
            Dependency(name="t1d", family=Family.TRADE_BAR_1M, horizon=Horizon.D1, required_complete=1,
                       freshness_allowance=timedelta(days=2)),
            Dependency(name="mark4h", family=Family.MARK_BAR_1M, horizon=Horizon.H4, required_complete=1,
                       freshness_allowance=timedelta(hours=8)),
            Dependency(name="t15-again", family=Family.TRADE_BAR_1M, horizon=Horizon.M15, required_complete=2,
                       freshness_allowance=timedelta(minutes=30)))
    eng = engine([cov(TRADE, T0, end)], deadlines=(), dependencies=deps)
    evs = minutes(TRADE, T0, 120)
    evs[70] = quality(TRADE, T0 + MIN * 70, QualityReason.MISSING)  # 01:00-01:15 interval incomplete
    run(eng, evs, finish=False)
    r = {x.dependency: x for x in eng.readiness()}
    # 01:00-01:15 sealed INCOMPLETE breaks the required run of 4 (01:15 and 01:30 complete since): GAP
    assert r["t15"].status == ReadinessStatus.GAP and r["t15"].complete_consecutive == 2
    assert r["t1d"].status == ReadinessStatus.WARMING_UP  # one horizon warming does not affect another
    assert r["mark4h"].status == ReadinessStatus.UNAVAILABLE and "no mark_bar_1m channel" in r["mark4h"].blockers[0]
    # GAP: required run broken by an INCOMPLETE record
    eng2 = engine([cov(TRADE, T0, end)], dependencies=deps)
    run(eng2, evs[:80] + minutes(TRADE, T0 + MIN * 80, 10), finish=False)
    eng2.advance_to(T0 + timedelta(hours=1, minutes=30))
    g = {x.dependency: x for x in eng2.readiness()}
    assert g["t15"].status == ReadinessStatus.GAP and g["t15"].complete_consecutive == 1
    # STALE with no new event: the clock passes the freshness allowance; blockers list every applicable status
    eng2.advance_to(T0 + timedelta(hours=2, minutes=20))
    s = {x.dependency: x for x in eng2.readiness()}["t15-again"]
    assert s.status == ReadinessStatus.GAP
    stale = [x for x in s.blockers if x.startswith("STALE")] + [x for x in s.blockers if x.startswith("GAP")]
    assert stale and s.age_since_known is not None and s.age_since_end is not None


def test_stale_without_new_events_and_ready():
    """A 1h dependency with a 30-minute allowance turns STALE at known_at + 30 min while no closure is due."""
    end = T0 + timedelta(hours=3)
    dep = Dependency(name="h1", family=Family.TRADE_BAR_1M, horizon=Horizon.H1, required_complete=1,
                     freshness_allowance=timedelta(minutes=30))
    eng = engine([cov(TRADE, T0, end)], dependencies=(dep,))
    sealed, disps = [], []
    eng.dispatch_listeners.append(disps.append)
    for i, e in enumerate(order_events(minutes(TRADE, T0, 61))):
        eng.on_event(e, i)
    assert eng.readiness()[0].status == ReadinessStatus.READY  # 00:00-01:00 complete, known 01:00
    for i, e in enumerate(order_events(minutes(TRADE, T0 + MIN * 61, 40)), start=61):
        eng.on_event(e, i)  # evidence keeps arriving, but no 1h closure is due before 02:00
    r = eng.readiness()[0]
    assert r.status == ReadinessStatus.STALE and r.age_since_known >= timedelta(minutes=30)
    stale = [d for d in disps if "readiness:h1:STALE" in d.reasons]
    assert stale and stale[0].clock_time == T0 + timedelta(hours=1, minutes=30)
    # coalesced with the 15m closure due at the same barrier; no 1h record is closed or fabricated there
    assert not [x for x in stale[0].closed_record_ids if "/1h/" in x]
    eng.finish()
    # evidence stopped at 01:41: the 01:00-02:00 hour seals INCOMPLETE at the finite clock end -> GAP (and STALE)
    end_r = eng.readiness()[0]
    assert end_r.status == ReadinessStatus.GAP and any(b.startswith("STALE") for b in end_r.blockers)


def test_unavailable_optional_horizon_and_capacity_rejection():
    dep_bad = Dependency(name="too-long", family=Family.TRADE_BAR_1M, horizon=Horizon.D1, required_complete=40,
                         freshness_allowance=timedelta(days=2))
    with pytest.raises(te.TemporalError, match="configuration rejected"):
        engine([cov(TRADE, T0, T0 + timedelta(days=1))], dependencies=(dep_bad,))
    with pytest.raises(te.TemporalError, match="retention"):
        engine([cov(TRADE, T0, T0 + timedelta(days=1))], retention={**te.DEFAULT_RETENTION,
                                                                    Horizon.M15: te.RETENTION_HARD_MAX + 1})
    prof = te.default_profile(ClockPolicy.MODELED_COMPLETE_PREFIX, timedelta(0))
    prof = prof.model_copy(update={"horizons": (Horizon.M15, Horizon.H1)})
    eng = te.TemporalEngine(prof, (cov(TRADE, T0, T0 + timedelta(hours=2)),), basis=AvailabilityBasis.MODELED,
                            availability_policy_id="fixture", content_identity="c")
    run(eng, minutes(TRADE, T0, 120), finish=False)
    eng.advance_to(T0 + timedelta(hours=2))
    r = {x.dependency: x.status for x in eng.readiness()}
    assert r["demo.trade.4h"] == ReadinessStatus.UNAVAILABLE  # horizon not in the profile
    assert r["demo.trade.15m"] == ReadinessStatus.READY  # unaffected by the unavailable optional horizon


def test_bounded_state_is_independent_of_input_length():
    def state_for(days: int) -> tuple[int, int, int]:
        start = datetime(2025, 9, 1, tzinfo=UTC)
        end = start + timedelta(days=days)
        covs = [cov(ch, start, end) for ch in (TRADE, MARK, INDEX)]
        eng = engine(covs)
        tracemalloc.start()
        n = 0
        for ch in (TRADE, MARK, INDEX):
            pass
        evs = (flat(ch, start + MIN * i) for i in range(days * 1440) for ch in (TRADE, MARK, INDEX))
        for e in evs:  # already in canonical order (availability, then family rank)
            eng.on_event(e, n)
            n += 1
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        raw = len(json.dumps(eng.encode()))
        retained = sum(len(t.sealed) for t in eng.tracks.values())
        return raw, peak, retained

    short = state_for(2)
    longer = state_for(9)
    # the open month accumulator is bounded by 31 days; sealed history by the declared retention
    assert longer[2] <= sum(te.DEFAULT_RETENTION.values()) * 3
    assert longer[0] < short[0] * 2.0, (short, longer)
    assert longer[1] < short[1] * 2.0, (short, longer)
    assert cal.MAX_INTERVAL_MINUTES == 44640


# ---------------------------------------------------------------------------
# Source continuation (monthly chunks) and discontinuity
# ---------------------------------------------------------------------------


def test_contiguous_source_continuation_preserves_temporal_state_exactly():
    cut, end = T0 + timedelta(hours=2, minutes=40), T0 + timedelta(hours=5)
    evs = minutes(TRADE, T0, 300) + minutes(MARK, T0, 300)
    ordered = order_events(evs)
    one = engine([cov(TRADE, T0, end), cov(MARK, T0, end)])
    for i, e in enumerate(ordered):
        one.on_event(e, i)
    one.finish()
    two = engine([cov(TRADE, T0, cut), cov(MARK, T0, cut)])
    first = [e for e in ordered if e.event_time < cut]
    for i, e in enumerate(first):
        two.on_event(e, i)
    two = te.unpack(*te.pack(two))  # chunk boundary is also a restore boundary
    log = two.extend_coverage((cov(TRADE, cut, end), cov(MARK, cut, end)), "feedcontent.next-chunk")
    assert {x["action"] for x in log} == {"continued"}
    for i, e in enumerate([e for e in ordered if e.event_time >= cut], start=len(first)):
        two.on_event(e, i)
    two.finish()
    assert two.aggregate_chain == one.aggregate_chain  # e.g. the 00:00-04:00 interval spans the chunk cut: COMPLETE
    four = [r for r in two.sealed_records(TRADE.channel_id, Horizon.H4) if r["interval_start"] == "2025-09-01T00:00:00Z"]
    assert four and four[0]["status"] == "COMPLETE"


def test_discontinuity_resets_only_the_affected_channel_and_records_why():
    cut, end = T0 + timedelta(hours=2), T0 + timedelta(hours=4)
    dep_t = Dependency(name="t15", family=Family.TRADE_BAR_1M, horizon=Horizon.M15, required_complete=2,
                       freshness_allowance=timedelta(hours=1))
    dep_m = Dependency(name="m15", family=Family.MARK_BAR_1M, horizon=Horizon.M15, required_complete=2,
                       freshness_allowance=timedelta(hours=1))
    eng = engine([cov(TRADE, T0, cut), cov(MARK, T0, cut)], dependencies=(dep_t, dep_m))
    first = order_events(minutes(TRADE, T0, 120) + minutes(MARK, T0, 120))
    for i, e in enumerate(first):
        eng.on_event(e, i)
    gap_start = cut + timedelta(minutes=10)  # trade resumes 10 minutes later: a discontinuity
    log = eng.extend_coverage((cov(TRADE, gap_start, end), cov(MARK, cut, end)), "feedcontent.next")
    acts = {x["channel"]: x for x in log}
    assert acts[TRADE.channel_id]["action"] == "reset" and "discontinuity" in acts[TRADE.channel_id]["reason"]
    assert acts[MARK.channel_id]["action"] == "continued"
    assert eng.sealed_records(TRADE.channel_id, Horizon.M15) == []  # only the affected channel was reset
    assert len(eng.sealed_records(MARK.channel_id, Horizon.M15)) == 7
    second = order_events(minutes(TRADE, gap_start, 110) + minutes(MARK, cut, 120))
    for i, e in enumerate(second, start=len(first)):
        eng.on_event(e, i)
    eng.advance_to(end)
    r = {x.dependency: x for x in eng.readiness()}
    assert r["m15"].status == ReadinessStatus.READY and r["t15"].status == ReadinessStatus.READY
    first_after = eng.sealed_records(TRADE.channel_id, Horizon.M15)[0]  # 02:00-02:15 cut by the new coverage start
    assert first_after["status"] == "OUTSIDE_COVERAGE" and first_after["counts"]["reasons"] == {"OUTSIDE_COVERAGE": 10}
    assert eng.continuations[-1]["content_identity"] == "feedcontent.next"
    assert te.unpack(*te.pack(eng)).commitment() == eng.commitment()

