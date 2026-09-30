"""Causal feed and observable market state (algotrader.feed.v1, PROVISIONAL).

Offline: datasets are acquired from captured OKX fixtures through the WP-003
pipeline (FakeOkx), then transformed by the pure feed adapter/reducer.
"""

from __future__ import annotations

import json
import random
from datetime import UTC, datetime, timedelta

import pytest
from okx_fake import CONFIRMED_END, FIXTURE_END, FIXTURE_START, FakeOkx, client

from algotrader import schema
from algotrader.feed import contracts as fc
from algotrader.feed.adapter import Feed, assemble_feed, build_feed, event_id, make_event
from algotrader.feed.contracts import (
    AvailabilityBasis,
    ChannelCondition,
    ChannelCoverage,
    ChannelRef,
    EventKind,
    Family,
    Freshness,
    MarkBarPayload,
    QualityReason,
    SourceRef,
)
from algotrader.feed.ordering import (
    FeedError,
    default_freshness,
    modeled_availability,
    order_events,
    ordered_event_hash,
)
from algotrader.feed.state import (
    advance,
    apply,
    events_known_at,
    initial_state,
    make_delta,
    snapshot,
    snapshot_at,
    state_at,
)
from algotrader.marketdata.contracts import Family as MdFamily
from algotrader.marketdata.dataset import acquire

M = timedelta(minutes=1)
T = lambda h, m, s=0: datetime(2026, 9, 30, h, m, s, tzinfo=UTC)  # noqa: E731
FRESH = default_freshness()
TRADE = "okx/BTC-USDT-SWAP/trade_bar_1m"
MARK = "okx/BTC-USDT-SWAP/mark_bar_1m"
INDEX = "okx/BTC-USDT/index_bar_1m"
FUNDING = "okx/BTC-USDT-SWAP/funding_settlement"


def dataset(tmp_path, name="d", fake=None, start=FIXTURE_START, end=CONFIRMED_END, **kw):
    return acquire(client(fake or FakeOkx(), **kw.pop("client_kw", {})), tmp_path / name, start, end, **kw).path


def ch(snap, channel_id):
    return next(c for c in snap.channels if c.channel_id == channel_id)


# ---------------------------------------------------------------------------
# Contract / schema
# ---------------------------------------------------------------------------


def test_feed_contract_is_separate_provisional_and_baselined():
    assert fc.FEED_SCHEMA_VERSION == "algotrader.feed.v1"
    assert fc.FEED_CONTRACT_STATUS == "PROVISIONAL"
    assert fc.FEED_CHANGELOG[-1][0] == fc.FEED_SCHEMA_REVISION
    stored = json.loads(schema.baseline_path(fc.FEED_SCHEMA_VERSION).read_text(encoding="utf-8"))
    assert stored == schema.feed_baseline(), "feed contract drift: bump FEED_SCHEMA_REVISION + changelog"
    assert (stored["status"], stored["revision"]) == ("PROVISIONAL", fc.FEED_SCHEMA_REVISION)
    assert stored["ordering_policy"]["id"] == fc.ORDERING_POLICY_ID
    for name in ("FeedEvent", "ObservableSnapshot", "SnapshotDelta", "FeedManifest", "ChannelSnapshot"):
        assert name in stored["public_contracts"]
    # separate from the frozen namespaces
    others = [json.loads(schema.baseline_path(v).read_text(encoding="utf-8"))["public_contracts"]
              for v in ("algotrader.semantic.v1", "algotrader.marketdata.v1")]
    assert not any(set(stored["public_contracts"]) & set(o) for o in others)


def test_provisional_baseline_requires_revision_bump(tmp_path, monkeypatch):
    path = schema.write_baseline(tmp_path, fc.FEED_SCHEMA_VERSION)
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["$defs"]["ChannelRef"]["title"] = "tampered"
    path.write_text(schema.render(doc), encoding="utf-8")
    with pytest.raises(SystemExit, match="PROVISIONAL baseline at revision 1"):
        schema.write_baseline(tmp_path, fc.FEED_SCHEMA_VERSION)
    monkeypatch.setattr(fc, "FEED_SCHEMA_REVISION", 2)
    monkeypatch.setattr(fc, "FEED_CHANGELOG", (*fc.FEED_CHANGELOG, (2, "2026-10-01", "test change")))
    assert json.loads(schema.write_baseline(tmp_path, fc.FEED_SCHEMA_VERSION).read_text())["revision"] == 2


def test_contracts_carry_no_interpretation_or_account_fields():
    stored = json.loads(schema.baseline_path(fc.FEED_SCHEMA_VERSION).read_text(encoding="utf-8"))
    fields = {p for d in stored["$defs"].values() for p in d.get("properties", {})}
    for banned in ("bias", "confidence", "action", "recommendation", "target", "position", "equity",
                   "leverage", "pnl", "price"):
        assert banned not in fields, banned


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


def test_adapter_emits_role_specific_channels_with_exact_values(tmp_path):
    path = dataset(tmp_path)
    before = {p: p.read_bytes() for p in path.rglob("*") if p.is_file()}
    feed = build_feed(path)
    assert {p: p.read_bytes() for p in path.rglob("*") if p.is_file()} == before  # dataset untouched
    m = feed.manifest
    assert m.event_counts == {
        "funding_settlement/funding_observation": 1, "index_bar_1m/bar_observation": 19,
        "mark_bar_1m/bar_observation": 19, "trade_bar_1m/bar_observation": 19}
    assert {c.channel.channel_id for c in m.coverage} == {TRADE, MARK, INDEX, FUNDING}
    trade = [e for e in feed.events if e.channel.channel_id == TRADE]
    raw = {int(r[0]): r for r in json.loads((path / "raw/trade_candles_1m/0000.json").read_bytes())["data"]}
    first = trade[0]
    src = raw[int(first.event_time.timestamp() * 1000)]
    assert [str(first.payload.open), str(first.payload.close), str(first.payload.volume_contracts),
            str(first.payload.volume_quote)] == [src[1], src[4], src[5], src[7]]
    assert (first.payload.volume_base_ccy, first.payload.volume_quote_ccy) == ("BTC", "USDT")
    assert {type(e.payload).__name__ for e in feed.events} == {
        "TradeBarPayload", "MarkBarPayload", "IndexBarPayload", "FundingPayload"}
    idx = next(e for e in feed.events if e.channel.channel_id == INDEX)
    assert idx.payload.index_id == "BTC-USDT"
    assert first.source.dataset_id == m.dataset_ids[0] and first.source.raw_page_ref == "trade_candles_1m/0000"
    # three times stay distinct
    assert first.event_time == FIXTURE_START and first.event_end_time == FIXTURE_START + M
    assert first.available_time == first.event_end_time and first.source.retrieved_at != first.available_time
    assert m.availability_policy.measured is False and "not a measurement" in m.availability_policy.note


def test_invalid_rows_never_enter_valid_state(tmp_path):
    def corrupt(rows):
        rows[5][2] = "1"  # high below low -> INVALID row (07:59 is rows[0]; rows[5] is 07:54)
        return rows

    feed = build_feed(dataset(tmp_path, fake=FakeOkx().mutate(MdFamily.TRADE_CANDLES, corrupt)))
    q = [e for e in feed.events if e.kind == EventKind.SLOT_QUALITY]
    assert len(q) == 1 and q[0].payload.reason == QualityReason.INVALID_ROW
    assert "ohlc_inconsistent" in q[0].payload.flags and not hasattr(q[0].payload, "close")
    bad_slot = q[0].event_time
    snap = snapshot_at(feed, bad_slot + M, FRESH)
    t = ch(snap, TRADE)
    assert t.condition == ChannelCondition.REJECTED and t.freshness == Freshness.STALE
    assert t.latest_valid.event_time == bad_slot - M  # previous valid bar carried, not replaced
    assert bad_slot not in {h.event_time for h in t.history}
    later = ch(snapshot_at(feed, CONFIRMED_END, FRESH), TRADE)
    assert bad_slot not in {h.event_time for h in later.history} and later.counts.invalid_row == 1


def test_gap_is_reported_not_filled_and_last_valid_stays_stale(tmp_path):
    drop = {"1790754900000", "1790754960000", "1790755020000"}  # 07:55..07:57
    fake = FakeOkx().mutate(MdFamily.MARK_CANDLES, lambda rows: [r for r in rows if r[0] not in drop])
    feed = build_feed(dataset(tmp_path, fake=fake))
    missing = [e for e in feed.events if e.kind == EventKind.SLOT_QUALITY]
    assert [(e.channel.channel_id, e.event_time, e.payload.reason) for e in missing] == [
        (MARK, T(7, m), QualityReason.MISSING) for m in (55, 56, 57)]
    snap = snapshot_at(feed, T(7, 58), FRESH)  # 07:57 slot known missing at 07:58
    mk, tr = ch(snap, MARK), ch(snap, TRADE)
    assert (mk.condition, mk.freshness, mk.quality_slots_since_valid) == (ChannelCondition.GAP, Freshness.STALE, 3)
    assert mk.latest_valid.event_time == T(7, 54) and mk.latest_valid.available_time == T(7, 55)  # original times
    assert mk.age_since_available == timedelta(minutes=3)
    assert (tr.condition, tr.freshness) == (ChannelCondition.VALID, Freshness.FRESH)  # other channel unaffected
    assert len([e for e in feed.events if e.channel.channel_id == MARK and e.kind == EventKind.BAR_OBSERVATION]) == 16
    after = ch(snapshot_at(feed, T(7, 59), FRESH), MARK)
    assert (after.condition, after.freshness, after.quality_slots_since_valid) == (
        ChannelCondition.VALID, Freshness.FRESH, 0)
    assert [h.event_time.minute for h in after.history] == [50, 51, 52, 53, 54, 58]  # no filled slots


def test_never_seen_invalid_only_and_incomplete_are_distinct(tmp_path):
    feed = build_feed(dataset(tmp_path, end=FIXTURE_END))  # includes the live-captured confirm=0 08:09 bar
    snap0 = snapshot_at(feed, FIXTURE_START, FRESH)
    assert all(c.condition == ChannelCondition.NEVER_SEEN and c.freshness == Freshness.UNKNOWN
               for c in snap0.channels)
    incomplete = [e for e in feed.events if e.kind == EventKind.SLOT_QUALITY]
    assert {(e.channel.family, e.event_time, e.payload.reason) for e in incomplete} == {
        (f, T(8, 9), QualityReason.INCOMPLETE_REJECTED)
        for f in (Family.TRADE_BAR_1M, Family.MARK_BAR_1M, Family.INDEX_BAR_1M)}
    end = snapshot_at(feed, FIXTURE_END, FRESH)
    assert ch(end, TRADE).condition == ChannelCondition.REJECTED and ch(end, TRADE).counts.incomplete_rejected == 1

    def all_invalid(rows):  # derived: first two bars (07:50, 07:51) invalid
        for r in rows[-2:]:
            r[4] = "-1"
        return rows

    bad = build_feed(dataset(tmp_path, "bad", fake=FakeOkx().mutate(MdFamily.INDEX_CANDLES, all_invalid)))
    s = ch(snapshot_at(bad, T(7, 52), FRESH), INDEX)
    assert (s.condition, s.freshness, s.latest_valid) == (ChannelCondition.INVALID_ONLY, Freshness.UNKNOWN, None)


def test_conflicting_duplicate_is_classified_from_raw_evidence(tmp_path):
    def dup(page):
        conflicting = [page[1][0], page[1][1], page[1][2], page[1][3], "1", *page[1][5:]]
        return [*page, conflicting]

    fake = FakeOkx()
    fake.page_hook = lambda family, page: dup(page) if family == MdFamily.TRADE_CANDLES and page else page
    feed = build_feed(dataset(tmp_path, fake=fake))
    q = [e for e in feed.events if e.kind == EventKind.SLOT_QUALITY]
    assert [(e.channel.channel_id, e.payload.reason) for e in q] == [(TRADE, QualityReason.CONFLICTING_DUPLICATE)]


def test_unverifiable_dataset_is_refused(tmp_path):
    path = dataset(tmp_path)
    (path / "quality.json").write_text("{}", encoding="utf-8")
    with pytest.raises(FeedError, match="failed verification"):
        build_feed(path)


# ---------------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------------


def test_ordering_is_total_deterministic_and_input_order_independent(tmp_path):
    path = dataset(tmp_path)
    a, b = build_feed(path), build_feed(path)
    assert a.manifest.ordered_event_hash == b.manifest.ordered_event_hash and a.events == b.events
    shuffled = list(a.events)
    for seed in range(5):
        random.Random(seed).shuffle(shuffled)
        assert order_events(shuffled) == a.events
        assert ordered_event_hash(order_events(shuffled)) == a.manifest.ordered_event_hash


def test_same_time_heterogeneous_events_have_a_fixed_tie_order(tmp_path):
    feed = build_feed(dataset(tmp_path))
    at_8 = [e for e in feed.events if e.available_time == T(8, 0)]
    assert [(e.channel.family, e.event_time) for e in at_8] == [
        (Family.TRADE_BAR_1M, T(7, 59)), (Family.MARK_BAR_1M, T(7, 59)), (Family.INDEX_BAR_1M, T(7, 59)),
        (Family.FUNDING_SETTLEMENT, T(8, 0))]
    snap = snapshot_at(feed, T(8, 0), FRESH)  # all four known together, none hides another
    assert all(c.condition == ChannelCondition.VALID for c in snap.channels)
    assert ch(snap, FUNDING).freshness == Freshness.NOT_APPLICABLE  # sparse: no schedule assumed


def test_ambiguous_slot_and_duplicate_delivery_are_rejected(tmp_path):
    feed = build_feed(dataset(tmp_path))
    obs = feed.events[0]
    q = make_event(obs.channel, EventKind.SLOT_QUALITY, obs.event_time, obs.event_end_time, obs.available_time,
                   feed.manifest.availability_policy, obs.source,
                   fc.SlotQualityPayload(reason=QualityReason.MISSING, detail="conflicting claim"))
    with pytest.raises(FeedError, match="ambiguous slot"):
        order_events([*feed.events, q])
    st = apply(initial_state(feed, FRESH), obs)
    with pytest.raises(FeedError, match="not after the cursor"):
        apply(st, obs)


# ---------------------------------------------------------------------------
# Availability transformation
# ---------------------------------------------------------------------------


def test_modeled_delay_only_postpones_knowledge(tmp_path):
    path = dataset(tmp_path)
    feeds = {d: build_feed(path, modeled_availability(timedelta(seconds=d), timedelta(seconds=d)))
             for d in (0, 30, 90)}
    base = {e.event_id: e for e in feeds[0].events}
    for d, feed in feeds.items():
        for e in feed.events:
            b = base[e.event_id]
            assert e.event_time == b.event_time and e.event_end_time == b.event_end_time  # market time unchanged
            assert e.available_time == b.available_time + timedelta(seconds=d) >= b.available_time
            assert e.availability_policy_id == feed.manifest.availability_policy.policy_id
        assert feed.manifest.content_identity == feeds[0].manifest.content_identity
    for cutoff in (T(7, 51), T(7, 55, 30), T(8, 0), T(8, 9)):
        known = {d: {e.event_id for e in events_known_at(f, cutoff)} for d, f in feeds.items()}
        assert known[90] <= known[30] <= known[0]  # more delay never reveals more
        for d in (30, 90):  # a uniform delay shifts knowledge exactly
            assert known[d] == {e.event_id for e in events_known_at(feeds[0], cutoff - timedelta(seconds=d))}
    with pytest.raises(ValueError, match="non-negative"):
        modeled_availability(timedelta(seconds=-1))


def test_family_specific_delay_models_late_arrival(tmp_path):
    feed = build_feed(dataset(tmp_path), modeled_availability(bar_delay=timedelta(0), funding_delay=timedelta(0)))
    events = []
    for e in feed.events:  # derived: mark bars arrive 90 s late (as a live source might)
        if e.channel.channel_id == MARK:
            new_t = e.available_time + timedelta(seconds=90)
            e = e.model_copy(update={"available_time": new_t,
                                     "order": e.order.model_copy(update={"available_time": new_t})})
        events.append(e)
    late = assemble_feed(events, feed.manifest.coverage, feed.manifest.availability_policy,
                         feed.manifest.dataset_ids, "BTC-USDT-SWAP", "BTC-USDT", {})
    snap = snapshot_at(late, T(8, 1), FRESH)
    assert ch(snap, TRADE).latest_valid.event_time == T(8, 0)  # closed 08:01, known at 08:01
    assert ch(snap, MARK).latest_valid.event_time == T(7, 58)  # 07:59 mark bar not known until 08:01:30
    assert ch(snap, MARK).latest_valid.available_time == T(8, 0, 30)
    assert ch(snap, MARK).freshness == Freshness.FRESH  # arrived 30 s ago, within the 2 min policy
    assert ch(snapshot_at(late, T(8, 2), FRESH), MARK).latest_valid.event_time == T(7, 59)


def test_late_older_observation_enters_history_without_regressing_latest(tmp_path):
    chan = ChannelRef(source="okx", family=Family.MARK_BAR_1M, series_id="BTC-USDT-SWAP")
    pol = modeled_availability().model_copy(update={"basis": AvailabilityBasis.RECORDED, "policy_id": "recorded-test"})
    src = SourceRef(dataset_id="test", artifact="synthetic", row_index=None, raw_page_ref=None, retrieved_at=None,
                    source_availability_policy="test")

    def bar(minute, arrive):
        p = MarkBarPayload(open=1, high=2, low=1, close=minute)
        return make_event(chan, EventKind.BAR_OBSERVATION, T(7, minute), T(7, minute) + M, arrive, pol, src, p)

    events = [bar(50, T(7, 51)), bar(52, T(7, 53)), bar(51, T(7, 53, 30))]  # 07:51 bar arrives late
    cov = (ChannelCoverage(channel=chan, covered_from=T(7, 50), covered_until=T(7, 53), expected_cadence=M),)
    feed = assemble_feed(events, cov, pol, ("test",), "BTC-USDT-SWAP", "BTC-USDT", {})
    assert [e.event_time.minute for e in feed.events] == [50, 52, 51]
    s1 = ch(snapshot_at(feed, T(7, 53), FRESH), MARK)
    assert [h.event_time.minute for h in s1.history] == [50, 52] and s1.latest_valid.event_time == T(7, 52)
    s2 = ch(snapshot_at(feed, T(7, 54), FRESH), MARK)
    assert [h.event_time.minute for h in s2.history] == [50, 51, 52]  # sorted by market time
    assert s2.latest_valid.event_time == T(7, 52)  # latest never regresses
    assert s2.latest_valid.payload.close == 52


# ---------------------------------------------------------------------------
# Prefix / truncated-history invariance
# ---------------------------------------------------------------------------


def test_future_evidence_never_changes_a_past_snapshot(tmp_path):
    feed = build_feed(dataset(tmp_path))
    for cutoff in (T(7, 50), T(7, 53, 20), T(7, 59, 59), T(8, 0), T(8, 5)):
        prefix = assemble_feed(events_known_at(feed, cutoff), feed.manifest.coverage,
                               feed.manifest.availability_policy, feed.manifest.dataset_ids,
                               "BTC-USDT-SWAP", "BTC-USDT", {})
        full = snapshot_at(feed, cutoff, FRESH)
        only_prefix = snapshot(state_at(prefix, cutoff, FRESH), cutoff, feed)
        assert full.content_digest == only_prefix.content_digest
        assert full.channels == only_prefix.channels


def test_truncated_dataset_gives_identical_state_before_its_end(tmp_path):
    full = build_feed(dataset(tmp_path, "full"))
    short = build_feed(dataset(tmp_path, "short", end=T(8, 0)))
    assert short.manifest.dataset_ids != full.manifest.dataset_ids
    for cutoff in (T(7, 50), T(7, 51), T(7, 55, 30), T(7, 59, 59)):
        a, b = snapshot_at(full, cutoff, FRESH), snapshot_at(short, cutoff, FRESH)
        assert a.content_digest == b.content_digest and a.snapshot_id != b.snapshot_id  # provenance differs
    # Boundary: funding settles at 08:00 = the short package's exclusive end. The short package
    # cannot speak for it, so at 08:00 exactly the funding channel differs; bar channels agree.
    a, b = snapshot_at(full, T(8, 0), FRESH), snapshot_at(short, T(8, 0), FRESH)
    assert ch(a, FUNDING).condition == ChannelCondition.VALID and ch(b, FUNDING).condition == ChannelCondition.NEVER_SEEN
    for cid in (TRADE, MARK, INDEX):
        assert ch(a, cid).latest_valid.event_id == ch(b, cid).latest_valid.event_id
    assert ch(snapshot_at(short, T(8, 0, 1), FRESH), FUNDING).beyond_coverage is True


def test_replay_speed_and_cursor_stepping_do_not_change_results(tmp_path):
    feed = build_feed(dataset(tmp_path))
    direct = snapshot_at(feed, CONFIRMED_END, FRESH)
    for step in (timedelta(seconds=1), timedelta(seconds=37), timedelta(minutes=3)):
        st, t = initial_state(feed, FRESH), FIXTURE_START
        while t < CONFIRMED_END:
            t = min(t + step, CONFIRMED_END)
            st, _ = advance(feed, st, t)
        assert snapshot(st, CONFIRMED_END, feed) == direct


def test_snapshot_cannot_precede_applied_knowledge(tmp_path):
    feed = build_feed(dataset(tmp_path))
    st = state_at(feed, T(7, 55), FRESH)
    with pytest.raises(FeedError, match="precedes applied knowledge"):
        snapshot(st, T(7, 54), feed)


def test_reducer_is_pure(tmp_path):
    feed = build_feed(dataset(tmp_path))
    st = state_at(feed, T(7, 55), FRESH)
    before = snapshot(st, T(7, 55), feed)
    nxt = apply(st, feed.events[st.cursor.applied_events])
    assert snapshot(st, T(7, 55), feed) == before and nxt is not st and nxt.cursor.applied_events == st.cursor.applied_events + 1


# ---------------------------------------------------------------------------
# Snapshot / delta
# ---------------------------------------------------------------------------


def test_snapshot_and_delta_are_deterministic_and_complete(tmp_path):
    feed = build_feed(dataset(tmp_path))
    s1_state = state_at(feed, T(7, 55), FRESH)
    s1 = snapshot(s1_state, T(7, 55), feed)
    s2_state, applied = advance(feed, s1_state, T(8, 0))
    s2 = snapshot(s2_state, T(8, 0), feed)
    delta = make_delta(s1, s2, applied)
    assert delta == make_delta(s1, s2, applied) and delta.delta_id.startswith("delta-")
    assert delta.events == tuple(e for e in feed.events if T(7, 55) < e.available_time <= T(8, 0))
    changes = {c.channel_id: c for c in delta.channel_changes}
    assert changes[TRADE].new_events == 5 and changes[FUNDING].new_events == 1
    assert (changes[FUNDING].condition_before, changes[FUNDING].condition_after) == (
        ChannelCondition.NEVER_SEEN, ChannelCondition.VALID)
    assert changes[TRADE].latest_valid_after == event_id(ch(s2, TRADE).channel, EventKind.BAR_OBSERVATION, T(7, 59))
    # applying the delta's events to the earlier state reproduces the later snapshot
    assert snapshot(s2_state, T(8, 0), feed) == snapshot_at(feed, T(8, 0), FRESH) == s2
    assert s2.labels == ("OBSERVATION_ONLY", "NO_INTERPRETATION")
    assert s2.as_of == s2.information_cutoff and s2.ordering_policy_id == fc.ORDERING_POLICY_ID
    assert len(ch(s2, TRADE).history) == 10 and ch(s2, TRADE).history[-1].event_time == T(7, 59)
    with pytest.raises(FeedError, match="cursor distance"):
        make_delta(s1, s2, applied[:-1])


def test_history_is_bounded_by_policy(tmp_path):
    feed = build_feed(dataset(tmp_path))
    snap = snapshot_at(feed, CONFIRMED_END, default_freshness(history_limit=4))
    t = ch(snap, TRADE)
    assert [h.event_time.minute for h in t.history] == [5, 6, 7, 8] and t.counts.valid == 19


# ---------------------------------------------------------------------------
# Normalized feed-content identity
# ---------------------------------------------------------------------------


def test_content_identity_is_independent_of_acquisition_packaging(tmp_path):
    a = build_feed(dataset(tmp_path, "a"))
    b = build_feed(dataset(tmp_path, "b", page_limit=7))  # different pagination -> different package id
    c = build_feed(dataset(tmp_path, "c", client_kw={"base_url": "https://eea.okx.com"}))  # regional host
    ids = {f.manifest.dataset_ids[0] for f in (a, b, c)}
    assert len(ids) == 3  # evidence-package identities retained, all distinct
    assert a.manifest.content_identity == b.manifest.content_identity == c.manifest.content_identity
    assert a.manifest.content_identity.startswith("feedcontent.v1:")
    sa, sb = snapshot_at(a, T(8, 5), FRESH), snapshot_at(b, T(8, 5), FRESH)
    assert sa.content_digest == sb.content_digest and sa.snapshot_id != sb.snapshot_id
    assert sa.dataset_ids == a.manifest.dataset_ids and sb.dataset_ids == b.manifest.dataset_ids

    def revise(rows):
        rows[3][4] = "1"
        return rows

    d = build_feed(dataset(tmp_path, "d", fake=FakeOkx().mutate(MdFamily.MARK_CANDLES, revise)))
    assert d.manifest.content_identity != a.manifest.content_identity  # different economic content
    e = build_feed(dataset(tmp_path, "e", end=T(8, 5)))
    assert e.manifest.content_identity != a.manifest.content_identity  # different coverage


def test_cli_inspect_prints_snapshot_identity_and_policies(tmp_path, capsys):
    from algotrader.cli import main

    path = dataset(tmp_path)
    main(["feed", "inspect", path.name, "--root", str(tmp_path / "d"), "--cutoff", "2026-09-30T07:55Z",
          "--bar-delay-seconds", "15"])
    out = capsys.readouterr().out
    feed = build_feed(path, modeled_availability(timedelta(seconds=15)))
    assert feed.manifest.content_identity in out and feed.manifest.ordered_event_hash in out
    assert "PROVISIONAL" in out and fc.ORDERING_POLICY_ID in out and "bar+PT15S" in out
    assert "measured=False" in out and "NO_INTERPRETATION" in out
    for cid in (TRADE, MARK, INDEX, FUNDING):
        assert cid in out
    main(["feed", "inspect", path.name, "--root", str(tmp_path / "d"), "--cutoff", "2026-09-30T07:55Z", "--json"])
    doc = json.loads(capsys.readouterr().out)
    assert doc["snapshot"]["as_of"].startswith("2026-09-30T07:55") and doc["feed"]["schema_version"] == "algotrader.feed.v1"


def test_feed_core_is_independent_of_ui_db_worker_trader_account_execution():
    import ast
    from pathlib import Path

    import algotrader.feed as pkg

    banned = {"db", "api", "worker", "control", "engine", "trader", "account", "risk", "artifacts", "validation",
              "psycopg", "fastapi", "uvicorn", "okx"}
    for path in Path(pkg.__file__).parent.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom):
                parts = set((node.module or "").split("."))
            elif isinstance(node, ast.Import):
                parts = {p for a in node.names for p in a.name.split(".")}
            else:
                continue
            assert not parts & banned, f"{path.name} imports {parts & banned}"
    # transitively too: importing the feed core must not load those layers
    import subprocess
    import sys

    probe = ("import sys, algotrader.feed.adapter, algotrader.feed.state, algotrader.feed.ordering; "
             "print(','.join(sorted(m for m in sys.modules if m.startswith(('algotrader', 'psycopg', 'fastapi')))))")
    loaded = set(subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True, check=True)
                 .stdout.strip().split(","))
    forbidden = {f"algotrader.{m}" for m in ("db", "api", "worker", "control", "engine", "trader", "account",
                                              "risk", "artifacts", "validation")} | {"psycopg", "fastapi"}
    assert not loaded & forbidden, loaded & forbidden
