"""Prospective public recorder (algotrader.recorder.v1, PROVISIONAL): offline, deterministic.

Scripts are built from real captured OKX public messages (tests/fixtures/okx_ws,
see PROVENANCE.json); variants that alter them are labelled "derived".
"""

from __future__ import annotations

import json
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from recorder_fake import BUSINESS, ENDPOINTS, PUBLIC, REST, FakeClock, captured_script, record_session

from algotrader import schema
from algotrader.feed.contracts import AvailabilityBasis, ChannelCondition, EventKind
from algotrader.feed.state import snapshot_at
from algotrader.feed.ordering import default_freshness
from algotrader.recorder import contracts as rc
from algotrader.recorder.contracts import Connection, ParseStatus, SessionStatus
from algotrader.recorder.feed_bridge import RECORDED_POLICY, build_recorded_feed
from algotrader.recorder.journal import (
    RecordingError,
    SessionWriter,
    finalize,
    iter_lifecycle,
    iter_records,
    load_report,
    ns_to_dt,
    recover,
    verify,
)
from algotrader.recorder.contracts import Endpoints
from algotrader.recorder.okx_live import (
    DEFAULT_ENDPOINTS,
    FORBIDDEN_HEADERS,
    REST_ALLOWED_PATHS,
    Recorder,
    make_config,
    validate_endpoints,
)

FRESH = default_freshness()
TRADE_BAR_1 = 1790768640000  # bar open ms (fixture)
TRADE_CONFIRM_1 = 1790768700590111500  # first completed trade push for that bar (local receipt ns)
TRADE_FORMING_LAST_1 = 1790768700590094600  # forming push 17 us earlier


def fixture_scripts(**kw):
    return {PUBLIC: [captured_script("public", **kw)], BUSINESS: [captured_script("business", **kw)]}


def finalize_(path, reason="test", recovered=False):
    return finalize(path, reason, recovered, "test-host", 1, None)


# ---------------------------------------------------------------------------
# Contract
# ---------------------------------------------------------------------------


def test_recorder_contract_is_separate_provisional_and_baselined():
    assert rc.RECORDER_SCHEMA_VERSION == "algotrader.recorder.v1" and rc.RECORDER_CONTRACT_STATUS == "PROVISIONAL"
    assert rc.RECORDER_CHANGELOG[-1][0] == rc.RECORDER_SCHEMA_REVISION
    stored = json.loads(schema.baseline_path(rc.RECORDER_SCHEMA_VERSION).read_text(encoding="utf-8"))
    assert stored == schema.recorder_baseline()
    assert (stored["status"], stored["revision"]) == ("PROVISIONAL", rc.RECORDER_SCHEMA_REVISION)
    fields = {p for d in stored["$defs"].values() for p in d.get("properties", {})}
    for banned in ("bias", "confidence", "recommendation", "target", "position", "equity", "leverage", "pnl", "order"):
        assert banned not in fields, banned
    assert "exchange" not in rc.RECEIPT_POINT.split("not the exchange")[0]  # receipt point never claims publication


# ---------------------------------------------------------------------------
# Recording from captured messages
# ---------------------------------------------------------------------------


def test_captured_session_records_raw_messages_with_local_receipt_timing(tmp_path):
    path, net, reason, _ = record_session(tmp_path, fixture_scripts())
    m = finalize_(path, reason)
    assert verify(path) == [] and m.status == SessionStatus.CLEAN
    assert set(m.channels_subscribed) == set(m.channels_requested) and m.reconnects == 0
    recs = list(iter_records(path))
    assert [r.seq for r in recs] == list(range(1, len(recs) + 1))
    ws = [r for r in recs if r.kind == "ws_message"]
    expected = sorted(captured_script("public") + captured_script("business"), key=lambda i: i[1])
    assert [(r.recv_utc_ns, r.raw) for r in ws] == [(t, raw) for _, t, raw in expected]  # exact bytes and times
    assert all(r.generation == 1 for r in ws)
    rest = [r for r in recs if r.kind == "rest_response"]
    assert {r.purpose for r in rest} >= {"instrument", "server_time"}
    assert all(r.request_sent_utc_ns <= r.recv_utc_ns for r in rest)
    # local receipt order is preserved even 17 us apart (forming push, then the completing push)
    forming = next(r for r in ws if r.recv_utc_ns == TRADE_FORMING_LAST_1)
    confirm = next(r for r in ws if r.recv_utc_ns == TRADE_CONFIRM_1)
    assert forming.seq < confirm.seq and forming.recv_mono_ns <= confirm.recv_mono_ns
    assert json.loads(forming.raw)["data"][0][-1] == "0" and json.loads(confirm.raw)["data"][0][-1] == "1"
    assert {r.parse_status for r in ws} == {ParseStatus.EVENT, ParseStatus.DATA, ParseStatus.PONG}
    # only public subscribe operations were ever sent; no login/private/order ops, no auth headers
    ops = [json.loads(t)["op"] for _, t in net.sent if t != "ping"]
    assert set(ops) == {"subscribe"} and all("login" not in t for _, t in net.sent)
    for url, headers in net.rest_calls:
        assert not {h.lower() for h in headers} & FORBIDDEN_HEADERS
        assert any(url.startswith(REST + p) for p in REST_ALLOWED_PATHS)


def test_report_measures_first_completed_receipt_delay(tmp_path):
    path, *_ = record_session(tmp_path, fixture_scripts())
    finalize_(path)
    r = load_report(path)
    bars = {b.channel_key: b for b in r.bars}
    trade = bars["candle1m:BTC-USDT-SWAP"]
    assert trade.completed_bars == 2 and trade.forming_updates == 4 and trade.duplicate_completed == 0
    assert trade.delay_raw.min_s == pytest.approx(0.5901115) and trade.delay_raw.max_s == pytest.approx(1.6648917)
    assert bars["mark-price-candle1m:BTC-USDT-SWAP"].delay_raw.min_s == pytest.approx(1.0842661)
    assert bars["index-candle1m:BTC-USDT"].delay_raw.max_s == pytest.approx(1.4960403)
    assert all(b.delay_raw.negative_count == 0 and not b.missing_completions_while_healthy for b in r.bars)
    index = [json.loads(line) for line in (path / "bars_index.jsonl").read_text().splitlines()]
    assert len(index) == 6
    first = next(i for i in index if i["channel_key"] == "candle1m:BTC-USDT-SWAP" and i["bar_open_ms"] == TRADE_BAR_1)
    assert first["first_completed_recv_utc_ns"] == TRADE_CONFIRM_1
    assert r.funding.snapshots_ws == 2 and {"fundingRate", "settFundingRate", "premium", "nextFundingTime",
                                            "fundingTime", "ts"} <= set(r.funding.fields_seen)
    assert r.clock.clock_quality == "observed" and "not an exchange publication time" in r.note


def test_clock_offset_is_observed_not_applied(tmp_path):
    path, *_ = record_session(tmp_path, fixture_scripts(), server_offset_ms=250)
    finalize_(path)
    r = load_report(path)
    assert r.clock.offset_estimate_ms_median == pytest.approx(250, abs=1.0)
    trade = next(b for b in r.bars if b.channel_key == "candle1m:BTC-USDT-SWAP")
    assert trade.delay_raw.min_s == pytest.approx(0.5901115)  # raw receipt never corrected
    assert trade.delay_offset_adjusted.min_s == pytest.approx(0.5901115 + 0.25, abs=0.002)
    obs = [json.loads(l) for l in (path / "clock.jsonl").read_text().splitlines()]
    assert obs[0]["status"] == "ok" and obs[0]["offset_bound_ns"] >= 1_000_000


def test_unknown_clock_is_labelled(tmp_path):
    path, *_ = record_session(tmp_path, fixture_scripts(), rest={"/api/v5/public/time": (503, b"unavailable")})
    finalize_(path)
    r = load_report(path)
    assert r.clock.clock_quality == "unknown" and r.clock.offset_estimate_ms_median is None
    assert any("clock offset unknown" in p.detail for p in r.unusable_timing_periods)
    assert all(b.delay_offset_adjusted is None for b in r.bars)


def test_duplicate_changed_and_out_of_order_pushes(tmp_path):
    # derived: after the captured session, the source re-sends a completed bar, changes one and repeats an old bar
    base = fixture_scripts()
    business = base[BUSINESS][0]
    confirm = next(i for i in business if i[1] == TRADE_CONFIRM_1)
    changed = json.loads(confirm[2])
    changed["data"][0][4] = "1.0"
    t = business[-1][1]
    business += [("msg", t + 1_000_000, confirm[2]), ("msg", t + 2_000_000, json.dumps(changed))]
    path, *_ = record_session(tmp_path, base)
    finalize_(path)
    trade = next(b for b in load_report(path).bars if b.channel_key == "candle1m:BTC-USDT-SWAP")
    assert (trade.duplicate_completed, trade.post_completion_changes, trade.out_of_order_updates) == (1, 1, 2)
    feed = build_recorded_feed(path).feed  # first completion wins; later pushes stay raw evidence only
    ev = next(e for e in feed.events if e.channel.family.value == "trade_bar_1m" and e.event_time == ns_to_dt(TRADE_BAR_1 * 1_000_000))
    assert ev.payload.close == Decimal(json.loads(confirm[2])["data"][0][4]) and ev.available_time == ns_to_dt(TRADE_CONFIRM_1)


def test_reconnect_resubscribes_and_never_fabricates_the_gap(tmp_path):
    business = captured_script("business")
    cut = next(i for i, item in enumerate(business) if item[1] > 1790768702_000_000_000)
    first, second = business[:cut], business[cut:]
    resub = [("msg", second[0][1] - 10_000_000 + k, raw) for k, (_, _, raw) in enumerate(business[:3])]  # acks
    scripts = {PUBLIC: [captured_script("public")],
               BUSINESS: [first + [("close", 1790768705_000_000_000)], "refuse", resub + second]}
    path, *_ = record_session(tmp_path, scripts)
    m = finalize_(path)
    assert m.status == SessionStatus.PARTIAL and m.reconnects == 1 and m.connections == 3
    events = [e.event for e in iter_lifecycle(path)]
    assert events.count("disconnected") == 1 and "connect_failed" in events and events.count("subscribe_sent") == 3
    gens = {r.generation for r in iter_records(path) if r.connection == Connection.BUSINESS}
    assert gens == {1, 2}
    r = load_report(path)
    outage = next(o for o in r.outages if o.connection == Connection.BUSINESS)
    assert outage.start == ns_to_dt(1790768705_000_000_000) and outage.end is not None
    assert "not market gaps" in r.note
    feed = build_recorded_feed(path).feed
    assert all(e.kind == EventKind.BAR_OBSERVATION for e in feed.events)  # no fabricated quality/gap events
    assert feed.manifest.event_counts.get("trade_bar_1m/bar_observation") == 2


def test_missing_completion_while_healthy_is_reported(tmp_path):
    # derived: the source never sends the completion of the first index bar although the connection is healthy
    scripts = fixture_scripts()
    scripts[BUSINESS][0] = [i for i in scripts[BUSINESS][0]
                            if not ('"index-candle1m"' in i[2] and '"1790768640000"' in i[2] and i[2].endswith('"1"]]}'))]
    path, *_ = record_session(tmp_path, scripts)
    finalize_(path)
    idx = next(b for b in load_report(path).bars if b.channel_key == "index-candle1m:BTC-USDT")
    assert idx.missing_completions_while_healthy == (ns_to_dt(TRADE_BAR_1 * 1_000_000),)


def test_negative_delay_is_flagged_and_not_bridged(tmp_path):
    # derived: the completing trade push carries a local receipt before the bar end (clock inconsistency)
    scripts = fixture_scripts()
    b = scripts[BUSINESS][0]
    i = next(k for k, item in enumerate(b) if item[1] == TRADE_CONFIRM_1)
    b[i] = ("msg", 1790768699_900_000_000, b[i][2])
    b.sort(key=lambda item: item[1])
    path, *_ = record_session(tmp_path, scripts)
    finalize_(path)
    trade = next(x for x in load_report(path).bars if x.channel_key == "candle1m:BTC-USDT-SWAP")
    assert trade.delay_raw.negative_count == 1
    bridge = build_recorded_feed(path)
    assert len(bridge.excluded) == 1 and "precedes bar end" in bridge.excluded[0]


# ---------------------------------------------------------------------------
# Funding (live information preserved, not treated as settlements)
# ---------------------------------------------------------------------------


def test_live_funding_is_preserved_point_in_time_and_not_bridged(tmp_path):
    # derived: a later push reports the next funding period (settlement boundary observed)
    scripts = fixture_scripts()
    pub = scripts[PUBLIC][0]
    last_funding = [i for i in pub if '"funding-rate"' in i[2] and '"data"' in i[2]][-1]
    doc = json.loads(last_funding[2])
    doc["data"][0]["fundingTime"] = str(int(doc["data"][0]["fundingTime"]) + 8 * 3600 * 1000)
    pub.append(("msg", pub[-1][1] + 1_000_000, json.dumps(doc)))
    path, *_ = record_session(tmp_path, scripts)
    finalize_(path)
    f = load_report(path).funding
    assert f.snapshots_ws == 3 and len(f.distinct_funding_times) == 2 and len(f.funding_time_transitions) == 1
    raws = [r.raw for r in iter_records(path) if r.channel == "funding-rate" and r.parse_status == ParseStatus.DATA]
    assert raws[:2] == [i[2] for i in captured_script("public") if '"funding-rate"' in i[2] and '"data"' in i[2]]
    bridge = build_recorded_feed(path)
    assert not any(e.channel.family.value == "funding_settlement" for e in bridge.feed.events)
    assert "not settlements" in bridge.funding_note


def test_funding_falls_back_to_labelled_rest_polling(tmp_path):
    err = ('{"event":"error","msg":"Subscribe failed, wrong URL or channel:funding-rate,instId:BTC-USDT-SWAP '
           'doesn\'t exist.","code":"60018","connId":"x"}')
    t0 = captured_script("business")[0][1]
    funding_body = json.dumps({"code": "0", "msg": "", "data": [json.loads(
        [i for i in captured_script("public") if '"data"' in i[2]][0][2])["data"][0]]}).encode()
    scripts = {PUBLIC: [[("msg", t0 - 1000, err)]], BUSINESS: [captured_script("business")]}
    path, *_ = record_session(tmp_path, scripts, rest={"/api/v5/public/funding-rate": (200, funding_body)},
                              funding_poll_interval=timedelta(milliseconds=5))
    m = finalize_(path)
    polls = [r for r in iter_records(path) if r.purpose == "funding_poll_fallback"]
    assert polls and all(p.poll_interval_s == 0.005 and p.request_sent_utc_ns <= p.recv_utc_ns for p in polls)
    assert polls[0].previous_observation_utc_ns is None
    if len(polls) > 1:
        assert polls[1].previous_observation_utc_ns == polls[0].recv_utc_ns  # availability bound preserved
    assert "fallback_enabled" in [e.event for e in iter_lifecycle(path)]
    assert m.status == SessionStatus.PARTIAL and "funding-rate:BTC-USDT-SWAP" not in m.channels_subscribed
    assert load_report(path).funding.snapshots_poll == len(polls)


# ---------------------------------------------------------------------------
# Durability, integrity, recovery
# ---------------------------------------------------------------------------


def test_finalized_session_is_immutable_and_tamper_evident(tmp_path):
    path, *_ = record_session(tmp_path, fixture_scripts())
    finalize_(path)
    with pytest.raises(RecordingError, match="already finalized"):
        finalize_(path)
    with pytest.raises(RecordingError, match="already exists"):
        SessionWriter(tmp_path, make_config("rec-test", endpoints=ENDPOINTS), FakeClock(1))
    seg = next((path / "journal").glob("raw-*.jsonl"))
    seg.write_bytes(seg.read_bytes().replace(b"83900.1", b"83900.9", 1))
    problems = verify(path)
    assert any("hash/size mismatch" in p for p in problems) and any("raw hash mismatch" in p for p in problems)


def test_crash_recovery_truncates_torn_tail_without_duplicates(tmp_path):
    clock = FakeClock(1790768690_000_000_000)
    config = make_config("rec-crash", endpoints=ENDPOINTS, segment_max_bytes=600)  # force segment rotation
    w = SessionWriter(tmp_path, config, clock)
    w.lifecycle("session_start")
    for k, (_, t, raw) in enumerate(captured_script("business")[:8]):
        clock.advance_to(t)
        doc = json.loads(raw)
        w.record(kind="ws_message", connection=Connection.BUSINESS, generation=1, endpoint=BUSINESS,
                 recv_utc_ns=t, recv_mono_ns=clock.monotonic_ns(), raw=raw,
                 parse_status=ParseStatus.EVENT if "event" in doc else ParseStatus.DATA,
                 channel=doc["arg"]["channel"], inst_id=doc["arg"]["instId"])
    w.sync()  # the process dies here (no close/finalize); a partial line was being written
    segs = sorted((w.dir / "journal").glob("raw-*.jsonl"))
    assert len(segs) > 1
    with segs[-1].open("a", encoding="utf-8") as f:
        f.write('{"seq": 9, "kind": "ws_mess')
    assert (w.dir / "ACTIVE").is_file()
    removed = recover(w.dir, clock, "test crash")
    assert list(removed.values()) == [len('{"seq": 9, "kind": "ws_mess')]
    m = finalize_(w.dir, "recovered after crash", recovered=True)
    assert m.status == SessionStatus.PARTIAL and m.recovered_after_crash and m.record_count == 8
    assert [r.seq for r in iter_records(w.dir)] == list(range(1, 9)) and verify(w.dir) == []
    assert not (w.dir / "ACTIVE").exists() and "recovered" in [e.event for e in iter_lifecycle(w.dir)]
    with pytest.raises(RecordingError):
        recover(w.dir, clock, "again")


# ---------------------------------------------------------------------------
# Recorded session -> feed.v1 (RECORDED)
# ---------------------------------------------------------------------------


def test_recorded_feed_uses_first_completed_receipt_without_leakage(tmp_path):
    path, *_ = record_session(tmp_path, fixture_scripts())
    finalize_(path)
    full = build_recorded_feed(path).feed
    assert full.manifest.availability_policy == RECORDED_POLICY and RECORDED_POLICY.basis == AvailabilityBasis.RECORDED
    assert full.manifest.event_counts == {"index_bar_1m/bar_observation": 2, "mark_bar_1m/bar_observation": 2,
                                          "trade_bar_1m/bar_observation": 2}
    ev = next(e for e in full.events if e.channel.family.value == "trade_bar_1m")
    assert ev.availability_basis == AvailabilityBasis.RECORDED and ev.available_time == ns_to_dt(TRADE_CONFIRM_1)
    assert ev.event_time == ns_to_dt(TRADE_BAR_1 * 1_000_000) and ev.source.row_index is not None
    assert ev.payload.close == Decimal("83900.1")  # completed value, not the forming 83900.0
    before = snapshot_at(full, ns_to_dt(TRADE_CONFIRM_1 - 1000), FRESH)
    trade = next(c for c in before.channels if c.channel.family.value == "trade_bar_1m")
    assert trade.condition == ChannelCondition.NEVER_SEEN  # forming pushes never become observations
    after = snapshot_at(full, ns_to_dt(TRADE_CONFIRM_1), FRESH)
    assert next(c for c in after.channels if c.channel.family.value == "trade_bar_1m").condition == ChannelCondition.VALID


def test_recorded_feed_prefix_invariance(tmp_path):
    path, *_ = record_session(tmp_path, fixture_scripts())
    finalize_(path)
    full = build_recorded_feed(path).feed
    cutoffs = [TRADE_CONFIRM_1 - 1000, TRADE_CONFIRM_1, 1790768701_496040300, 1790768760_000_000_000,
               1790768761_664891700]
    for t in cutoffs:
        prefix = build_recorded_feed(path, until_utc_ns=t).feed
        a, b = snapshot_at(full, ns_to_dt(t), FRESH), snapshot_at(prefix, ns_to_dt(t), FRESH)
        assert a.content_digest == b.content_digest, t
    # the recorded journal identity is independent of the observable state's bounded history
    tiny = snapshot_at(full, ns_to_dt(cutoffs[-1]), default_freshness(history_limit=1))
    assert all(len(c.history) <= 1 for c in tiny.channels)
    assert build_recorded_feed(path).feed.manifest.ordered_event_hash == full.manifest.ordered_event_hash


OFFICIAL_ENDPOINT_SETS = [
    # global
    ("wss://ws.okx.com:8443/ws/v5/public", "wss://ws.okx.com:8443/ws/v5/business", "https://www.okx.com"),
    ("wss://ws.okx.com:8443/ws/v5/public", "wss://ws.okx.com:8443/ws/v5/business", "https://openapi.okx.com/"),
    # EEA
    ("wss://wseea.okx.com:8443/ws/v5/public", "wss://wseea.okx.com:8443/ws/v5/business", "https://eea.okx.com"),
    # US
    ("wss://wsus.okx.com:8443/ws/v5/public", "wss://wsus.okx.com:8443/ws/v5/business", "https://us.okx.com"),
    # other legitimate *.okx.com regional host, explicit default port, case-insensitive host
    ("wss://WS.OKX.COM:8443/ws/v5/public", "wss://ws.okx.com:8443/ws/v5/business", "https://tr.okx.com:443"),
    ("wss://ws.okx.com:8443/ws/v5/public", "wss://ws.okx.com:8443/ws/v5/business", "https://my.okx.com"),
]

BAD_WS_PUBLIC = [
    "wss://example.com/ws/v5/public",  # arbitrary host
    "wss://example.com:8443/ws/v5/public",
    "wss://okx.com.evil.example:8443/ws/v5/public",  # deceptive suffix
    "wss://evilokx.com:8443/ws/v5/public",
    "wss://ws.okx.com.:8443/ws/v5/public",  # trailing-dot host
    "wss://ws..okx.com:8443/ws/v5/public",
    "wss://-ws.okx.com:8443/ws/v5/public",
    "ws://ws.okx.com:8443/ws/v5/public",  # plain ws
    "https://ws.okx.com:8443/ws/v5/public",
    "wss://user:pw@ws.okx.com:8443/ws/v5/public",  # userinfo
    "wss://evil.example@ws.okx.com:8443/ws/v5/public",
    "wss://ws.okx.com@evil.example:8443/ws/v5/public",
    "wss://ws.okx.com:8443/ws/v5/public?x=1",  # query
    "wss://ws.okx.com:8443/ws/v5/public?",
    "wss://ws.okx.com:8443/ws/v5/public#frag",  # fragment
    "wss://ws.okx.com:8443/ws/v5/private",  # private
    "wss://ws.okx.com:8443/ws/v5/business",  # business path on the public endpoint
    "wss://ws.okx.com:8443/evil/ws/v5/public",  # wrong path (suffix match only)
    "wss://ws.okx.com:8443/ws/v5/public/",
    "wss://ws.okx.com:8443/other",
    "wss://ws.okx.com:9443/ws/v5/public",  # arbitrary port
    "wss://ws.okx.com:443/ws/v5/public",
    "wss://ws.okx.com/ws/v5/public",  # undocumented portless form
    "wss://ws.okx.com:notaport/ws/v5/public",
    " wss://ws.okx.com:8443/ws/v5/public",
    "wss://ws.okx.com\\@evil.example:8443/ws/v5/public",
]

BAD_WS_BUSINESS = [
    "wss://okx.com.evil.example/ws/v5/business",
    "wss://example.com:8443/ws/v5/business",
    "ws://ws.okx.com:8443/ws/v5/business",
    "wss://ws.okx.com:8443/ws/v5/public",
    "wss://ws.okx.com:8443/ws/v5/private",
    "wss://ws.okx.com:1234/ws/v5/business",
]

BAD_REST = [
    "https://example.com",  # arbitrary host
    "https://okx.com.evil.example",
    "https://evilokx.com",
    "https://www.okx.com.",
    "http://www.okx.com",  # plain http
    "wss://www.okx.com",
    "https://user@www.okx.com",  # userinfo
    "https://user:pw@www.okx.com",
    "https://www.okx.com?x=1",  # query
    "https://www.okx.com#frag",  # fragment
    "https://www.okx.com/api",  # path
    "https://www.okx.com/api/v5/public/time",
    "https://www.okx.com:8443",  # arbitrary port
    "https://www.okx.com:8080",
    "www.okx.com",
    "",
]


def test_endpoint_validation_accepts_official_regional_endpoints():
    validate_endpoints(ENDPOINTS)
    validate_endpoints(DEFAULT_ENDPOINTS)
    for pub, bus, rest in OFFICIAL_ENDPOINT_SETS:
        validate_endpoints(Endpoints(ws_public_url=pub, ws_business_url=bus, rest_base_url=rest))


@pytest.mark.parametrize("field,url", [("ws_public_url", u) for u in BAD_WS_PUBLIC]
                         + [("ws_business_url", u) for u in BAD_WS_BUSINESS]
                         + [("rest_base_url", u) for u in BAD_REST])
def test_endpoint_validation_rejects_non_official_or_insecure_endpoints(field, url):
    with pytest.raises(ValueError):
        validate_endpoints(ENDPOINTS.model_copy(update={field: url}))


def test_non_okx_host_cannot_produce_an_okx_recording(tmp_path):
    for field, url in (("ws_public_url", "wss://example.com:8443/ws/v5/public"),
                       ("ws_business_url", "wss://okx.com.evil.example:8443/ws/v5/business"),
                       ("rest_base_url", "https://evilokx.com")):
        config = make_config("rec-evil", endpoints=ENDPOINTS.model_copy(update={field: url}))
        with pytest.raises(ValueError, match="official OKX host"):
            SessionWriter(tmp_path, config, FakeClock(0))  # refused before any session artifact is written
        good = SessionWriter(tmp_path / "ok", make_config(f"rec-ok-{field}", endpoints=ENDPOINTS), FakeClock(0))
        try:
            with pytest.raises(ValueError, match="official OKX host"):
                Recorder(config, good)  # and the recorder itself refuses before any network call
        finally:
            good.close()
    assert not any(p.name == "rec-evil" for p in tmp_path.rglob("*"))


def test_recorder_source_has_no_private_or_account_access():
    src = "\n".join(p.read_text(encoding="utf-8") for p in Path("src/algotrader/recorder").glob("*.py"))
    for forbidden in ('"op": "login"', "OK-ACCESS-KEY", "/api/v5/trade", "/api/v5/account", "secret"):
        assert forbidden not in src
