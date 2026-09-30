"""OKX BTC-USDT-SWAP public data: parsing, time semantics, pagination, quality, immutability.

Fully offline: every test goes through the real ``OkxPublicClient`` with the
``FakeOkx`` transport serving captured fixture rows (tests/fixtures/okx).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pyarrow.parquet as pq
import pytest
from okx_fake import (
    CONFIRMED_END,
    FIXTURE_END,
    FIXTURE_START,
    NOW,
    FakeOkx,
    FixedClock,
    client,
    envelope,
    fixture_bytes,
    fixture_data,
)

from algotrader.marketdata import contracts as md
from algotrader.marketdata.contracts import Family, QualityStatus, RowQuality
from algotrader.marketdata.dataset import (
    MAX_SPAN,
    DatasetError,
    acquire,
    dataset_path,
    list_manifests,
    load_manifest,
    load_quality,
    parse_utc,
    verify,
)
from algotrader.marketdata.okx import (
    InstrumentIncompatible,
    MalformedResponse,
    OkxApiError,
    OkxPublicClient,
    RawResponse,
    SourceError,
    parse_candle,
    parse_funding,
    parse_instrument,
)

M = timedelta(minutes=1)


def instrument():
    c = client(FakeOkx())
    return parse_instrument(c.instrument("BTC-USDT-SWAP"), "BTC-USDT-SWAP", "instrument/0000")


def findings(q, check):
    return [f for f in q.findings if f.check == check]


def fam(q, family):
    return next(f for f in q.families if f.family == family)


def read(path, family):
    return pq.read_table(path / f"{family.value}.parquet").to_pylist()


# ---------------------------------------------------------------------------
# Instrument
# ---------------------------------------------------------------------------


def test_instrument_snapshot_from_captured_source():
    inst = instrument()
    assert (inst.inst_id, inst.inst_type, inst.ct_type) == ("BTC-USDT-SWAP", "SWAP", "linear")
    assert (inst.underlying, inst.inst_family, inst.index_id) == ("BTC-USDT", "BTC-USDT", "BTC-USDT")
    assert (inst.ct_val, inst.ct_val_ccy, inst.settle_ccy) == (Decimal("0.01"), "BTC", "USDT")
    assert (inst.tick_sz, inst.lot_sz, inst.min_sz, inst.state) == (Decimal("0.1"), Decimal("0.01"), Decimal("0.01"), "live")
    assert inst.list_time == datetime(2019, 11, 12, 11, 16, 48, tzinfo=UTC)
    assert inst.advertised_max_leverage == "100"  # venue metadata only
    assert inst.retrieved_at == NOW and len(inst.raw_sha256) == 64


@pytest.mark.parametrize("change, message", [
    ({"ctType": "inverse"}, "ctType"),
    ({"instType": "FUTURES"}, "instType"),
    ({"expTime": "1790755200000"}, "expTime"),
    ({"ctValCcy": "USDT"}, "ctValCcy"),
    ({"ctVal": "0"}, "ctVal must be positive"),
    ({"settleCcy": ""}, "settleCcy"),
    ({"ctMult": "0"}, "ctMult must be positive"),  # regression: zero was silently mapped to 1
    ({"ctMult": ""}, "ctMult"),
    ({"ctMult": "-1"}, "ctMult must be positive"),
])
def test_incompatible_instrument_fails_explicitly(change, message):
    fake = FakeOkx()
    doc = json.loads(fake.instrument_body)
    doc["data"][0].update(change)
    fake.instrument_body = json.dumps(doc).encode()
    c = client(fake)
    with pytest.raises(InstrumentIncompatible, match=message):
        parse_instrument(c.instrument("BTC-USDT-SWAP"), "BTC-USDT-SWAP", "p")


def test_instrument_without_ctmult_is_not_defaulted():
    fake = FakeOkx()
    doc = json.loads(fake.instrument_body)
    del doc["data"][0]["ctMult"]
    fake.instrument_body = json.dumps(doc).encode()
    with pytest.raises(InstrumentIncompatible, match="ctMult"):
        parse_instrument(client(fake).instrument("BTC-USDT-SWAP"), "BTC-USDT-SWAP", "p")
    assert instrument().ct_mult == Decimal("1")  # the captured source value, parsed explicitly


def test_missing_instrument_fails_explicitly():
    fake = FakeOkx()
    fake.instrument_body = envelope([])
    with pytest.raises(InstrumentIncompatible, match="exactly one"):
        parse_instrument(client(fake).instrument("BTC-USDT-SWAP"), "BTC-USDT-SWAP", "p")


# ---------------------------------------------------------------------------
# Parsing, units and time semantics
# ---------------------------------------------------------------------------


def test_trade_candle_preserves_exact_values_and_volume_units():
    inst = instrument()
    raw = [r for r in fixture_data("trade_candles_1m.json") if r[8] == "1"][0]
    rec = parse_candle(Family.TRADE_CANDLES, raw, inst, NOW, "p").record
    assert isinstance(rec, md.TradeCandle1m)
    assert [str(rec.open), str(rec.high), str(rec.low), str(rec.close)] == raw[1:5]  # exact source text
    assert (str(rec.volume_contracts), str(rec.volume_base), str(rec.volume_quote)) == tuple(raw[5:8])
    assert (rec.volume_base_ccy, rec.volume_quote_ccy) == ("BTC", "USDT")
    # contracts * ctVal = base volume for this linear contract: units are distinct, not interchangeable
    assert rec.volume_contracts * inst.ct_val == rec.volume_base
    assert rec.volume_contracts != rec.volume_base


@pytest.mark.parametrize("family, name, cls", [
    (Family.MARK_CANDLES, "mark_candles_1m.json", md.MarkCandle1m),
    (Family.INDEX_CANDLES, "index_candles_1m.json", md.IndexCandle1m),
])
def test_mark_and_index_candles_have_no_fake_volume(family, name, cls):
    raw = [r for r in fixture_data(name) if r[5] == "1"][0]
    rec = parse_candle(family, raw, instrument(), NOW, "p").record
    assert isinstance(rec, cls) and not any("volume" in f for f in cls.model_fields)
    assert [str(rec.open), str(rec.high), str(rec.low), str(rec.close)] == raw[1:5]
    if family == Family.INDEX_CANDLES:
        assert rec.index_id == "BTC-USDT"


def test_unconfirmed_candle_is_never_a_completed_bar():
    live_edge = fixture_data("trade_candles_live_edge.json")
    assert live_edge[0][8] == "0"  # captured live: the still-forming bar
    parsed = parse_candle(Family.TRADE_CANDLES, live_edge[0], instrument(), NOW, "p")
    assert parsed.confirmed is False and parsed.record is None
    with pytest.raises(MalformedResponse, match="confirm"):
        parse_candle(Family.TRADE_CANDLES, [*live_edge[1][:8], "maybe"], instrument(), NOW, "p")


def test_event_availability_and_retrieval_times_are_distinct():
    retrieved = datetime(2026, 9, 30, 12, 34, 56, 789000, tzinfo=UTC)
    raw = fixture_data("trade_candles_1m.json")[-1]  # 07:50 bar
    rec = parse_candle(Family.TRADE_CANDLES, raw, instrument(), retrieved, "p").record
    assert rec.open_time == FIXTURE_START  # source event time
    assert rec.close_time == FIXTURE_START + M
    assert rec.available_time == rec.close_time  # modeled: not before the bar closes
    assert rec.available_time > rec.open_time
    assert rec.retrieved_at == retrieved  # provenance only, never used as market time
    assert len({rec.open_time, rec.available_time, rec.retrieved_at}) == 3
    assert rec.availability_policy == md.AVAILABILITY_POLICY_ID
    assert "MODELING POLICY" in md.AVAILABILITY_POLICY_TEXT and "not a measured" in md.AVAILABILITY_POLICY_TEXT
    for name in ("open_time", "close_time", "available_time", "retrieved_at", "availability_policy"):
        assert md.TradeCandle1m.model_fields[name].is_required()  # cannot be omitted or silently defaulted


def test_funding_event_is_not_smeared_backwards():
    raw = fixture_data("funding_rates.json")[0]
    rec = parse_funding(raw, instrument(), NOW, "p").record
    assert rec.funding_time == datetime(2026, 9, 30, 8, 0, tzinfo=UTC)
    assert rec.available_time == rec.funding_time  # never earlier than the source event
    assert str(rec.funding_rate) == raw["fundingRate"] and str(rec.realized_rate) == raw["realizedRate"]
    assert (rec.method, rec.formula_type, rec.inst_type) == ("current_period", "withRate", "SWAP")
    assert rec.retrieved_at == NOW
    blank = {**raw, "realizedRate": "", "method": ""}
    rec2 = parse_funding(blank, instrument(), NOW, "p").record
    assert rec2.realized_rate is None and rec2.method is None


def test_financial_values_are_never_floats():
    for model in (md.TradeCandle1m, md.MarkCandle1m, md.IndexCandle1m, md.FundingRateEvent, md.InstrumentSnapshot):
        for name, f in model.model_fields.items():
            assert "float" not in str(f.annotation), f"{model.__name__}.{name}"
    with pytest.raises(MalformedResponse):
        parse_candle(Family.MARK_CANDLES, ["1790754600000", 1.5, "2", "1", "1", "1"], instrument(), NOW, "p")


# ---------------------------------------------------------------------------
# Client: errors, retries, pacing, safety
# ---------------------------------------------------------------------------


def test_okx_error_code_is_raised_without_retry():
    fake = FakeOkx()
    fake.queued.append((200, fixture_bytes("error_51001.json")))  # captured live 51001 response
    c = client(fake)
    with pytest.raises(OkxApiError, match="51001") as exc:
        c.get("/api/v5/market/history-candles", {"instId": "NOPE-SWAP", "bar": "1m"})
    assert exc.value.code == "51001" and len(fake.calls) == 1


def test_rate_limit_and_server_errors_are_retried_with_bounded_backoff():
    fake = FakeOkx()
    fake.queued += [(429, b"slow down"), (200, envelope([], "50011", "Too Many Requests")), (503, b"")]
    slept = []
    c = OkxPublicClient(transport=fake, sleep=slept.append, min_interval=0, backoff=0.5, clock=FixedClock())
    assert c.instrument("BTC-USDT-SWAP").code == "0"
    assert len(fake.calls) == 4 and slept == [0.5, 1.0, 2.0]
    fake.queued += [(503, b"")] * 4
    with pytest.raises(SourceError, match="giving up after 4 attempts"):
        c.instrument("BTC-USDT-SWAP")


def test_network_errors_are_retried_then_reported():
    calls = []

    def broken(url, headers, timeout):
        calls.append(timeout)
        raise TimeoutError("read timed out")

    c = OkxPublicClient(transport=broken, sleep=lambda s: None, timeout=3.5, max_attempts=2)
    with pytest.raises(SourceError, match="network error"):
        c.instrument("BTC-USDT-SWAP")
    assert calls == [3.5, 3.5]


@pytest.mark.parametrize("status, body, message", [
    (200, b"<html>blocked</html>", "not JSON"),
    (200, b'{"data": []}', "envelope"),
    (200, b'{"code": "0", "data": {"x": 1}}', "not a list"),
    (403, b'{"code": "0", "data": []}', "HTTP 403"),
])
def test_malformed_responses_are_rejected(status, body, message):
    fake = FakeOkx()
    fake.queued.append((status, body))
    with pytest.raises(MalformedResponse, match=message):
        client(fake).instrument("BTC-USDT-SWAP")


def test_client_is_read_only_paced_and_identified():
    fake = FakeOkx()
    slept = []
    ticks = iter([0.0, 0.1, 0.25])  # 1st request at 0.0; 2nd asked at 0.1 -> waits 0.15
    c = OkxPublicClient(transport=fake, sleep=slept.append, min_interval=0.25, monotonic=lambda: next(ticks),
                        clock=FixedClock())
    c.instrument("BTC-USDT-SWAP")
    c.instrument("BTC-USDT-SWAP")
    assert slept == [pytest.approx(0.15)]
    assert fake.calls[0][2]["User-Agent"].startswith("algotrader-research/")
    for path in ("/api/v5/trade/order", "/api/v5/account/balance", "/api/v5/market/books"):
        with pytest.raises(ValueError, match="not an allowed"):
            c.get(path, {})
    for bad in ("http://www.okx.com", "https://www.okx.com/api", "www.okx.com"):
        with pytest.raises(ValueError):
            OkxPublicClient(base_url=bad)
    assert OkxPublicClient(base_url="https://eea.okx.com/").base_url == "https://eea.okx.com"


@pytest.mark.parametrize("url", ["https://www.okx.com", "https://openapi.okx.com", "https://eea.okx.com",
                                 "https://us.okx.com", "https://tr.okx.com", "https://my.okx.com",
                                 "https://okx.com", "https://www.okx.com:443", "https://EEA.OKX.com/"])
def test_client_accepts_official_okx_rest_bases(url):
    OkxPublicClient(base_url=url, transport=FakeOkx())


@pytest.mark.parametrize("url", ["https://example.com", "https://okx.com.evil.example", "https://evilokx.com",
                                 "https://www.okx.com.", "http://www.okx.com", "https://user:pw@www.okx.com",
                                 "https://evil.example@www.okx.com", "https://www.okx.com@evil.example",
                                 "https://www.okx.com?x=1", "https://www.okx.com#f", "https://www.okx.com:8443",
                                 "https://www.okx.com/api/v5", "wss://ws.okx.com:8443"])
def test_client_rejects_non_official_rest_bases(url):
    with pytest.raises(ValueError):
        OkxPublicClient(base_url=url, transport=FakeOkx())


def test_non_okx_host_cannot_produce_an_okx_dataset(tmp_path):
    fake = FakeOkx()
    for url in ("https://example.com", "https://okx.com.evil.example", "https://evilokx.com"):
        with pytest.raises(ValueError, match="official OKX host"):
            acquire(OkxPublicClient(base_url=url, transport=fake, clock=FixedClock()),
                    tmp_path, FIXTURE_START, FIXTURE_END)
    assert fake.calls == [] and not any(tmp_path.rglob("*"))  # refused before any network call or artifact


def test_raw_response_hash_is_of_exact_bytes():
    fake = FakeOkx()
    r = client(fake).instrument("BTC-USDT-SWAP")
    assert isinstance(r, RawResponse) and r.body == fake.instrument_body
    import hashlib

    assert r.sha256 == hashlib.sha256(fake.instrument_body).hexdigest()


# ---------------------------------------------------------------------------
# Acquisition, pagination, quality
# ---------------------------------------------------------------------------


def test_fixture_acquisition_is_clean_complete_and_verifiable(tmp_path):
    fake = FakeOkx()
    res = acquire(client(fake), tmp_path, FIXTURE_START, CONFIRMED_END)
    m, q = res.manifest, load_quality(res.path)
    assert not res.reused and verify(res.path) == []
    assert m.schema_version == md.MARKETDATA_SCHEMA_VERSION and q.status == QualityStatus.CLEAN
    assert m.dataset_id.startswith("okx-btc-usdt-swap-1m-20260930T0750-20260930T0809-")
    assert m.availability_policy == md.AVAILABILITY_POLICY_ID
    assert m.instrument.ct_val == Decimal("0.01") and m.request.base_url == "https://www.okx.com"
    rows = {f.family: f.rows for f in m.families}
    assert rows == {Family.TRADE_CANDLES: 19, Family.MARK_CANDLES: 19, Family.INDEX_CANDLES: 19, Family.FUNDING: 1}
    for f in m.families[:3]:
        assert (f.first_time, f.last_time) == (FIXTURE_START, CONFIRMED_END - M)
    assert {f.endpoint for f in m.families} == {
        "/api/v5/market/history-candles", "/api/v5/market/history-mark-price-candles",
        "/api/v5/market/history-index-candles", "/api/v5/public/funding-rate-history"}
    names = {f.name for f in m.files}
    assert {"instrument.json", "quality.json", "request_log.jsonl", "raw/instrument/0000.json",
            "trade_candles_1m.parquet", "mark_candles_1m.parquet", "index_candles_1m.parquet",
            "funding_rates.parquet"} <= names
    trade = read(res.path, Family.TRADE_CANDLES)
    times = [r["open_time"] for r in trade]
    assert times == sorted(times) and len(set(times)) == 19  # chronological, unique
    assert all(r["confirm"] and r["quality"] == "OK" for r in trade)
    src = {int(r[0]): r for r in fixture_data("trade_candles_1m.json")}
    first = trade[0]
    assert [first["open"], first["volume_contracts"], first["volume_quote"]] == [
        src[1790754600000][1], src[1790754600000][5], src[1790754600000][7]]
    funding = read(res.path, Family.FUNDING)
    assert [r["funding_rate"] for r in funding] == ["0.0000337200721784"]
    index_req = [p for p in fake.calls if p[0].endswith("history-index-candles")]
    assert index_req and all(p[1]["instId"] == "BTC-USDT" for p in index_req)  # derived from the instrument


def test_incomplete_candle_is_rejected_and_its_interval_reported_missing(tmp_path):
    res = acquire(client(FakeOkx()), tmp_path, FIXTURE_START, FIXTURE_END)
    q = load_quality(res.path)
    for family in md.CANDLE_FAMILIES:
        fq = fam(q, family)
        assert (fq.rows, fq.expected_rows, fq.missing_rows) == (19, 20, 1)
        assert fq.gaps[0].first_missing_open_time == CONFIRMED_END and fq.status == QualityStatus.DEGRADED
        assert all(r["open_time"] < CONFIRMED_END for r in read(res.path, family))
    rejected = findings(q, "incomplete_candle_rejected")
    assert len(rejected) == 3 and all(f.count == 1 and f.severity == "warning" for f in rejected)
    assert q.status == QualityStatus.DEGRADED
    assert {f.family: f.rejected_incomplete for f in res.manifest.families}[Family.TRADE_CANDLES] == 1


@pytest.mark.parametrize("page_limit", [1, 4, 7, 19, 100])
def test_pagination_boundaries_give_identical_normalized_data(tmp_path, page_limit):
    fake = FakeOkx()
    ref = acquire(client(FakeOkx()), tmp_path / "ref", FIXTURE_START, CONFIRMED_END)
    res = acquire(client(fake), tmp_path / "paged", FIXTURE_START, CONFIRMED_END, page_limit=page_limit)
    for family in md.HISTORICAL_FAMILIES:
        a = [{k: v for k, v in r.items() if k not in ("raw_page_ref",)} for r in read(ref.path, family)]
        b = [{k: v for k, v in r.items() if k not in ("raw_page_ref",)} for r in read(res.path, family)]
        assert a == b
    trade_calls = [p for p in fake.calls if p[0].endswith("history-candles")]
    lo, hi = int(FIXTURE_START.timestamp() * 1000), int(CONFIRMED_END.timestamp() * 1000)
    for _, params, _ in trade_calls:  # every request stays inside [start, end)
        assert int(params["before"]) >= lo - 1 and int(params["after"]) <= hi
        assert params["limit"] == str(page_limit)
    assert verify(res.path) == [] and load_quality(res.path).status == QualityStatus.CLEAN
    assert res.manifest.dataset_id != ref.manifest.dataset_id or page_limit == 100  # page config is part of identity


def test_funding_pagination_follows_the_after_cursor(tmp_path):
    # derived: two extra funding events added around the captured 08:00Z event
    def extra(rows):
        base = rows[0]
        return [*rows, {**base, "fundingTime": "1790726400000"}, {**base, "fundingTime": "1790697600000"}]

    fake = FakeOkx().mutate(Family.FUNDING, extra)
    start = datetime(2026, 9, 29, 16, 0, tzinfo=UTC)
    res = acquire(client(fake), tmp_path, start, CONFIRMED_END, page_limit=1)
    funding = read(res.path, Family.FUNDING)
    assert [r["funding_time"] for r in funding] == [
        datetime(2026, 9, 29, 16, 0, tzinfo=UTC), datetime(2026, 9, 30, 0, 0, tzinfo=UTC),
        datetime(2026, 9, 30, 8, 0, tzinfo=UTC)]  # start is inclusive, chronological
    funding_calls = [p[1] for p in fake.calls if p[0].endswith("funding-rate-history")]
    assert [c["after"] for c in funding_calls] == ["1790755740000", "1790755200000", "1790726400000"]


def test_rows_outside_the_window_are_excluded_but_kept_raw(tmp_path):
    # derived: a sloppy source ignoring the requested bounds
    fake = FakeOkx()
    outside = ["1790754540000", "1", "1", "1", "1", "1", "0.01", "1", "1"]  # 07:49, before start
    fake.page_hook = lambda family, page: [*page, outside] if family == Family.TRADE_CANDLES else page
    res = acquire(client(fake), tmp_path, FIXTURE_START, CONFIRMED_END)
    q = load_quality(res.path)
    assert all(r["open_time"] >= FIXTURE_START for r in read(res.path, Family.TRADE_CANDLES))
    assert findings(q, "outside_requested_interval")[0].count == 1
    raw = json.loads((res.path / "raw/trade_candles_1m/0000.json").read_bytes())
    assert outside in raw["data"]


def test_gaps_are_reported_never_filled(tmp_path):
    # derived: bars 07:55..07:57 removed from the traded-price series
    drop = {"1790754900000", "1790754960000", "1790755020000"}
    fake = FakeOkx().mutate(Family.TRADE_CANDLES, lambda rows: [r for r in rows if r[0] not in drop])
    res = acquire(client(fake), tmp_path, FIXTURE_START, CONFIRMED_END)
    q = load_quality(res.path)
    fq = fam(q, Family.TRADE_CANDLES)
    assert (fq.rows, fq.missing_rows, len(fq.gaps)) == (16, 3, 1)
    gap = fq.gaps[0]
    assert (gap.first_missing_open_time, gap.last_missing_open_time, gap.missing_bars) == (
        datetime(2026, 9, 30, 7, 55, tzinfo=UTC), datetime(2026, 9, 30, 7, 57, tzinfo=UTC), 3)
    assert len(read(res.path, Family.TRADE_CANDLES)) == 16  # nothing forward-filled
    assert fq.status == QualityStatus.DEGRADED and fam(q, Family.MARK_CANDLES).status == QualityStatus.CLEAN
    assert q.status == QualityStatus.DEGRADED


def test_gap_spanning_windows_is_merged(tmp_path):
    drop = {str(1790754600000 + i * 60000) for i in range(3, 9)}  # 07:53..07:58, crosses 5-minute windows
    fake = FakeOkx().mutate(Family.MARK_CANDLES, lambda rows: [r for r in rows if r[0] not in drop])
    res = acquire(client(fake), tmp_path, FIXTURE_START, CONFIRMED_END, page_limit=5)
    fq = fam(load_quality(res.path), Family.MARK_CANDLES)
    assert [(g.missing_bars, g.first_missing_open_time.minute) for g in fq.gaps] == [(6, 53)]


def test_duplicates_identical_kept_once_conflicting_rejected(tmp_path):
    def dup(page):
        first = page[0]
        conflicting = [page[1][0], page[1][1], page[1][2], page[1][3], "1", *page[1][5:]]
        return [first, first, *page[1:], conflicting]

    fake = FakeOkx()
    fake.page_hook = lambda family, page: dup(page) if family == Family.TRADE_CANDLES and page else page
    res = acquire(client(fake), tmp_path, FIXTURE_START, CONFIRMED_END)
    q = load_quality(res.path)
    identical, conflicting = findings(q, "duplicate_identical"), findings(q, "duplicate_conflicting")
    assert identical[0].count == 1 and identical[0].severity == "warning"
    assert conflicting[0].count == 2 and conflicting[0].severity == "invalid"
    trade = read(res.path, Family.TRADE_CANDLES)
    times = [r["open_time"] for r in trade]
    assert len(times) == len(set(times)) == 18  # conflicting key kept by neither copy
    assert fam(q, Family.TRADE_CANDLES).missing_rows == 1 and q.status == QualityStatus.INVALID


def test_out_of_order_source_is_reported_and_sorted(tmp_path):
    fake = FakeOkx()
    fake.page_hook = lambda family, page: list(reversed(page)) if family == Family.INDEX_CANDLES else page
    res = acquire(client(fake), tmp_path, FIXTURE_START, CONFIRMED_END)
    q = load_quality(res.path)
    assert findings(q, "source_out_of_order")[0].family == Family.INDEX_CANDLES
    times = [r["open_time"] for r in read(res.path, Family.INDEX_CANDLES)]
    assert times == sorted(times) and fam(q, Family.INDEX_CANDLES).status == QualityStatus.WARNING


def test_invalid_values_are_flagged_not_repaired(tmp_path):
    def corrupt(rows):
        rows[1][2] = "1"  # high below low -> OHLC inconsistent
        rows[2][5] = "-5"  # negative contract volume
        rows[3][4] = "0"  # nonpositive close (also breaks OHLC)
        return rows

    fake = FakeOkx().mutate(Family.TRADE_CANDLES, corrupt)
    res = acquire(client(fake), tmp_path, FIXTURE_START, CONFIRMED_END)
    q = load_quality(res.path)
    trade = read(res.path, Family.TRADE_CANDLES)
    bad = [r for r in trade if r["quality"] == RowQuality.INVALID]
    assert len(trade) == 19 and len(bad) == 3  # kept for evidence, classified invalid
    checks = {f.check for f in q.findings if f.severity == "invalid"}
    assert {"ohlc_inconsistent", "negative_volume_contracts", "nonpositive_price"} <= checks
    assert q.status == QualityStatus.INVALID and res.manifest.quality_status == QualityStatus.INVALID


# ---------------------------------------------------------------------------
# Immutability, identity, verification
# ---------------------------------------------------------------------------


def snapshot_dir(path):
    return {p.relative_to(path).as_posix(): p.read_bytes() for p in path.rglob("*") if p.is_file()}


def test_identical_source_content_is_idempotent(tmp_path):
    first = acquire(client(FakeOkx()), tmp_path, FIXTURE_START, CONFIRMED_END)
    before = snapshot_dir(first.path)
    later = client(FakeOkx(), clock=FixedClock(NOW + timedelta(hours=3)))  # refetched later
    again = acquire(later, tmp_path, FIXTURE_START, CONFIRMED_END)
    assert again.reused and again.manifest.dataset_id == first.manifest.dataset_id
    assert snapshot_dir(first.path) == before  # untouched, original retrieval times kept
    assert again.manifest.retrieval_started_at == NOW
    assert [m.dataset_id for m in list_manifests(tmp_path)] == [first.manifest.dataset_id]
    assert not [p for p in (tmp_path / "datasets").iterdir() if p.name.startswith(".tmp")]


def test_changed_source_content_creates_a_new_version(tmp_path):
    first = acquire(client(FakeOkx()), tmp_path, FIXTURE_START, CONFIRMED_END)
    before = snapshot_dir(first.path)

    def revise(rows):  # derived: the source later reports a different close for one bar
        rows[5][4] = str(Decimal(rows[5][4]) + Decimal("0.1"))
        return rows

    later = client(FakeOkx().mutate(Family.MARK_CANDLES, revise), clock=FixedClock(NOW + timedelta(days=1)))
    second = acquire(later, tmp_path, FIXTURE_START, CONFIRMED_END)
    assert not second.reused and second.manifest.dataset_id != first.manifest.dataset_id
    assert second.manifest.logical_request_key == first.manifest.logical_request_key
    assert second.manifest.prior_versions == (first.manifest.dataset_id,)  # difference is visible
    assert snapshot_dir(first.path) == before and verify(first.path) == [] and verify(second.path) == []
    assert len(list_manifests(tmp_path)) == 2


def test_verify_detects_tampering(tmp_path):
    res = acquire(client(FakeOkx()), tmp_path, FIXTURE_START, CONFIRMED_END)
    raw = res.path / "raw/trade_candles_1m/0000.json"
    raw.write_bytes(raw.read_bytes().replace(b'"1"]', b'"0"]', 1))
    problems = verify(res.path)
    assert any("raw page trade_candles_1m/0000" in p for p in problems)
    assert any("hash/size mismatch for raw/trade_candles_1m/0000.json" in p for p in problems)
    (res.path / "quality.json").write_text("{}", encoding="utf-8")
    assert any("quality.json" in p for p in verify(res.path))
    with pytest.raises(DatasetError, match="fails verification"):  # never overwrites a damaged dataset
        acquire(client(FakeOkx()), tmp_path, FIXTURE_START, CONFIRMED_END)


def test_manifest_and_request_log_carry_provenance(tmp_path):
    res = acquire(client(FakeOkx()), tmp_path, FIXTURE_START, CONFIRMED_END)
    m = load_manifest(res.path)
    log = [md.RawPageRef.model_validate_json(x) for x in (res.path / "request_log.jsonl").read_text().splitlines()]
    assert len(log) == m.raw_page_count == 5 and log[0].family == Family.INSTRUMENT
    assert all(p.base_url == "https://www.okx.com" and p.retrieved_at == NOW and p.source_code == "0" for p in log)
    assert m.instrument.raw_sha256 == log[0].sha256
    assert m.request.start == FIXTURE_START and m.request.end == CONFIRMED_END
    assert m.identity_basis.startswith("sha256(") and "REAL_MARKET_DATA" in m.labels
    assert "NOT_A_TRADING_RESULT" in m.labels
    assert dataset_path(tmp_path, m.dataset_id) == res.path
    assert dataset_path(tmp_path, "../x") is None and dataset_path(tmp_path, "nope") is None


@pytest.mark.parametrize("start, end, message", [
    (FIXTURE_START + timedelta(seconds=30), CONFIRMED_END, "whole minute"),
    (CONFIRMED_END, FIXTURE_START, "after start"),
    (FIXTURE_START, NOW + M, "future"),
    (NOW - MAX_SPAN - timedelta(days=2), NOW - timedelta(days=1), "bounded maximum"),
])
def test_request_is_bounded_and_validated(tmp_path, start, end, message):
    with pytest.raises(DatasetError, match=message):
        acquire(client(FakeOkx()), tmp_path, start, end)


def test_utc_parsing_requires_explicit_offset():
    assert parse_utc("2026-09-30T07:50Z") == FIXTURE_START
    assert parse_utc("2026-09-30T09:50+02:00") == FIXTURE_START
    with pytest.raises(DatasetError, match="UTC offset"):
        parse_utc("2026-09-30T07:50")


def test_source_error_during_acquisition_leaves_no_dataset(tmp_path):
    fake = FakeOkx()
    fake.page_hook = lambda family, page: (_ for _ in ()).throw(RuntimeError("boom")) if family == Family.FUNDING else page
    with pytest.raises(RuntimeError):
        acquire(client(fake), tmp_path, FIXTURE_START, CONFIRMED_END)
    assert list((tmp_path / "datasets").iterdir()) == []
