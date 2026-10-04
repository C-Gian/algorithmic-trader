"""WP-009 pure method checks: packaged MP-001 release identity (B8), exact measurements, structural area versus
admissible prices (B4) and the normalized one-unit accounting / funding boundaries (B7). Hand arithmetic from the
Director disposition; no market data."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.adviser import geometry as geo
from algotrader.adviser import identity as idn
from algotrader.adviser import measures as ms
from algotrader.adviser.evaluation_contracts import Fill
from algotrader.adviser.evaluator import Evaluator, PathState, ceil_minute
from algotrader.adviser.params import PROSE, load
from algotrader.corpus import presets as ps
from algotrader.feed.ordering import canonical

ROOT = Path(__file__).resolve().parents[1]
D = Decimal
T0 = datetime(2025, 9, 1, tzinfo=UTC)


# -- B8 identity -------------------------------------------------------------------------------------------------


def test_packaged_rules_and_register_are_the_director_documents_byte_for_byte():
    for name in ("MP-001-INTEGRATED-METHOD-PROPOSAL.md", "MP-001-PARAMETERS.json"):
        packaged = (ROOT / "src/algotrader/adviser/method" / name).read_bytes().replace(b"\r\n", b"\n")
        director = (ROOT / "delivery" / name).read_bytes().replace(b"\r\n", b"\n")
        assert packaged == director, name
    assert idn.register_sha256() == ps.MP001_REGISTER_SHA256  # same register the R3 presets declare
    assert idn.rules_sha256() == hashlib.sha256((ROOT / "delivery/MP-001-INTEGRATED-METHOD-PROPOSAL.md")
                                                .read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    assert idn.register()["model"] == idn.MODEL_ID and idn.register()["rules_version"] == idn.RULES_VERSION


def test_prose_change_with_identical_json_is_a_different_behaviour_identity(monkeypatch, tmp_path):
    base = idn.composite_identity(idn.historical_profile(), {"pack": "x"}, "build")
    changed = tmp_path / "rules.md"
    changed.write_bytes(idn.RULES_FILE.read_bytes().replace(b"K=14bps", b"K=15bps", 1))
    idn.rules_sha256.cache_clear()
    monkeypatch.setattr(idn, "RULES_FILE", changed)
    try:
        other = idn.composite_identity(idn.historical_profile(), {"pack": "x"}, "build")
    finally:
        idn.rules_sha256.cache_clear()
    assert other["register_sha256"] == base["register_sha256"]  # numbers unchanged
    assert other["rules_sha256"] != base["rules_sha256"] and other["identity_sha256"] != base["identity_sha256"]


def test_capability_profiles_have_distinct_identities_and_never_claim_parity():
    hist, live = idn.historical_profile(), idn.live_profile()
    assert hist.sha256() != live.sha256()
    assert idn.historical_profile(dislocation=False).sha256() != hist.sha256()
    assert idn.historical_profile(funding_covered=True).sha256() != hist.sha256()
    a = idn.composite_identity(hist, {}, None)
    b = idn.composite_identity(live, {}, None)
    assert a["identity_sha256"] != b["identity_sha256"]


def test_register_values_are_exact_decimals_and_prose_constants_are_declared():
    p = load()
    assert p.ctx_eff == D("0.35") and p.zone_frac == D("0.1") and p.rr_min == D("1.2") and p.hist_k_bps == D(14)
    assert p.a_hard == timedelta(hours=4) and p.b_hard == timedelta(hours=6) and p.c_hard == timedelta(hours=2)
    assert p.residual_min == {"A": 30, "B": 30, "C": 15} and p.fresh_quote == timedelta(seconds=5)
    assert p.ready_15m == 25 and p.ready_1h == 21 and p.eval_tail_minutes == 365
    assert PROSE["b_attempt_lifetime_minutes"] == 60  # §6 B text, no register key


# -- measures -----------------------------------------------------------------------------------------------------


def _bar(i, o, h, lo, c):
    s = T0 + timedelta(minutes=15 * i)
    return ms.Bar(s, s + timedelta(minutes=15), D(o), D(h), D(lo), D(c), None, s + timedelta(minutes=15), f"b{i}")


def test_true_range_scale_median_efficiency_displacement_are_exact():
    assert ms.true_range(D(105), D(101), D(100)) == D(5)
    assert ms.true_range(D(103), D(101), D(110)) == D(9)  # gap down: |low - prev close|
    assert ms.median([D(1), D(4), D(2), D(3)]) == D("2.5")  # even count: mean of the two middle values
    bars = [_bar(i, 100, 110, 100, 105) for i in range(21)]
    assert ms.scale(bars) == D(10)
    assert ms.scale(bars[:20]) is None  # needs 21 bars
    flat = [_bar(i, 100, 100, 100, 100) for i in range(21)]
    assert ms.scale(flat) is None  # zero scale is UNAVAILABLE
    assert ms.efficiency([D(1), D(1), D(1)]) == D(0)  # zero path with complete inputs -> zero efficiency
    assert ms.efficiency([D(100), D(110), D(105), D(115)]) == D(15) / D(25)
    assert ms.displacement([D(100), D(130)], D(20)) == D("1.5")
    assert ms.round_down(D("100.17"), D("0.1")) == D("100.1") and ms.round_up(D("100.11"), D("0.1")) == D("100.2")
    assert ms.zone_halfwidth(D(10), D("0.1"), D("0.1"), 2) == D(1)
    assert ms.zone_halfwidth(D(1), D("0.1"), D("0.1"), 2) == D("0.2")  # minimum two ticks


# -- B4 structural area versus admissible prices --------------------------------------------------------------------


def test_disposition_b4_structural_area_and_admissible_bound():
    v, t, s, tc = D(99700), D(100700), D(400), D(100000)
    area = geo.structural_area(1, tc, v, t, s, D("0.25"), D("0.1"))
    assert area == (D(99900), D(100100))
    ok = geo.predicate(1, D(100000), v, t, D(14), D("1.2"))
    assert ok.ok and abs(ms.div(ok.g - 14, ok.q + 14) - D("1.2727")) < D("0.0001")
    bad = geo.predicate(1, D(100100), v, t, D(14), D("1.2"))
    assert not bad.ok and abs(ms.div(bad.g - 14, bad.q + 14) - D("0.8514")) < D("0.0001")
    bounds = geo.admissible_bounds(1, area, v, t, D(14), D("1.2"), D("0.1"))
    assert bounds == (D(99900), D("100014.5"))  # inward from ~100014.525; not the structural edge 100100
    assert not geo.predicate(1, D("100014.6"), v, t, D(14), D("1.2")).ok
    # LONG midpoint 100090 / ask 100110: the side price is outside the structural container regardless of midpoint
    assert not geo.in_area(D(100110), area)
    # original positive illustrative case still passes unchanged
    p2 = geo.predicate(1, D(100050), D(99780), D(100800), D(14), D("1.2"))
    assert p2.ok and abs(ms.div(p2.g - 14, p2.q + 14) - D("1.487")) < D("0.001")


def test_short_admissible_bound_is_verified_with_the_direct_short_predicate():
    v, t, tc, s = D(100300), D(99300), D(100000), D(400)
    area = geo.structural_area(-1, tc, v, t, s, D("0.25"), D("0.1"))
    assert area == (D(99900), D(100100))
    lo, hi = geo.admissible_bounds(-1, area, v, t, D(14), D("1.2"), D("0.1"))
    exact = (t + D("1.2") * v) / (D("2.2") * (1 - D(14) / 10000))
    assert lo == ms.round_up(exact, D("0.1")) == D("99985.5") and hi == area[1]
    assert geo.predicate(-1, lo, v, t, D(14), D("1.2")).ok
    assert not geo.predicate(-1, lo - D("0.1"), v, t, D(14), D("1.2")).ok
    assert geo.structural_area(1, D(100000), D("99999.9"), D("100000.0"), D(1), D("0.25"), D("0.1")) is None  # empty


# -- B7 normalized accounting and funding ------------------------------------------------------------------------


def _ev(funding_mode="PRICE_NET_ONLY") -> Evaluator:
    return Evaluator(load(), D("0.1"), eval_start=None, eval_end=None, funding_mode=funding_mode, sample_views=False)


def _call(d=1, v="90", t="120"):
    return {"cid": "c1", "attempt": "a", "family": "A", "d": d, "issued_at": T0.isoformat(), "v": v, "t": t,
            "area": ["95", "105"], "hard": 14400, "timeline": [], "terminal": None, "paths": {}}


def test_disposition_one_unit_accounting_and_known_funding():
    ev = _ev("AUTHORITATIVE_IF_COVERED")
    c = _call()
    ps_ = PathState("PRIMARY", 60, "GUIDANCE", status="OPEN", entry_price="100", entry_time=T0.isoformat())
    u = T0 + timedelta(hours=1)
    ev.funding = [{"event_time": u.isoformat(), "rate": "0.001", "event_id": "f"}]
    ev.mark_closes[u.isoformat()] = "105"
    x = Fill(price=D(110), reason="DISCRETIONARY_OPEN", time_start=T0 + timedelta(hours=2),
             time_end=T0 + timedelta(hours=2))
    ev._close(c, ps_, "CLOSED", "GUIDANCE", x, None)
    p = ev.records[-1]["record"]
    assert D(p["gross"]) == D("0.1") and D(p["price_net"]) == D("0.09853")
    assert D(p["funding"]) == D("-0.00105") and D(p["total_net"]) == D("0.09748")


def test_missing_funding_coverage_is_price_net_only_never_zero():
    ev = _ev()
    ps_ = PathState("PRIMARY", 60, "GUIDANCE", status="OPEN", entry_price="100", entry_time=T0.isoformat())
    ev._close(_call(), ps_, "CLOSED", "GUIDANCE", Fill(price=D(110), reason="DISCRETIONARY_OPEN",
                                                         time_start=T0 + MINUTE, time_end=T0 + MINUTE), None)
    p = ev.records[-1]["record"]
    assert p["funding"] is None and p["total_net"] is None
    assert p["funding_status"] == "PRICE_NET_ONLY_TOTAL_NET_UNAVAILABLE" and D(p["price_net"]) == D("0.09853")


MINUTE = timedelta(minutes=1)


@pytest.mark.parametrize("entry_at,exit_kind,expect", [
    (0, ("open", 120), "pays"),       # held before u, discretionary exit at an open boundary after u
    (60, ("open", 120), "none"),      # entry exactly at u: neither pays nor receives
    (0, ("open", 60), "pays"),        # exit exactly at u after holding before it owes the flow
    (0, ("intrabar", 60), "pays"),    # fill interval [60m, 61m): u <= interval start -> known pre-u holding
    (0, ("intrabar", 59), "none"),    # fill interval [59m, 60m): u >= interval end -> protection exited before u
    (0, ("intrabar", 45), "none"),
])
def test_funding_ownership_boundaries(entry_at, exit_kind, expect):
    ev = _ev("AUTHORITATIVE_IF_COVERED")
    u = T0 + timedelta(minutes=60)
    ev.funding = [{"event_time": u.isoformat(), "rate": "0.001", "event_id": "f"}]
    ev.mark_closes[u.isoformat()] = "100"
    kind, m = exit_kind
    start = T0 + timedelta(minutes=m)
    x = (Fill(price=D(100), reason="DISCRETIONARY_OPEN", time_start=start, time_end=start) if kind == "open" else
         Fill(price=D(100), reason="STOP_TOUCH", time_start=start, time_end=start + MINUTE))
    total, status = ev._funding(_call(), D(100), T0 + timedelta(minutes=entry_at), x)
    assert status == "AUTHORITATIVE_COVERED"
    assert total == (D("-0.001") if expect == "pays" else D(0))


def test_funding_strictly_inside_an_intrabar_fill_interval_is_ambiguous():
    ev = _ev("AUTHORITATIVE_IF_COVERED")
    u = T0 + timedelta(minutes=60, seconds=30)
    ev.funding = [{"event_time": u.isoformat(), "rate": "0.001", "event_id": "f"}]
    x = Fill(price=D(100), reason="STOP_TOUCH", time_start=T0 + timedelta(minutes=60),
             time_end=T0 + timedelta(minutes=61))
    total, status = ev._funding(_call(), D(100), T0, x)
    assert total is None and status == "FUNDING_OWNERSHIP_AMBIGUOUS_TOTAL_NET_UNAVAILABLE"


def test_ceil_minute_alignment():
    assert ceil_minute(datetime(2025, 9, 1, 12, 0, 30, tzinfo=UTC) + timedelta(seconds=60)) == \
        datetime(2025, 9, 1, 12, 2, tzinfo=UTC)  # disposition: guidance 12:00:30 -> planned open 12:02
    assert ceil_minute(datetime(2025, 9, 1, 12, 1, tzinfo=UTC)) == datetime(2025, 9, 1, 12, 1, tzinfo=UTC)


def test_canonical_register_hash_uses_the_register_bytes_not_float_text():
    raw = json.loads(idn.REGISTER_FILE.read_text(encoding="utf-8"))
    assert hashlib.sha256(canonical(raw)).hexdigest() == idn.register_sha256()
