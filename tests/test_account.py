"""Account/position transitions for long and short paper positions."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from algotrader.account import AccountState, simulate_market_fill
from algotrader.contracts import CostAssumptions, Fill, Order, OrderStatus, Side

T = datetime(2026, 1, 1, tzinfo=UTC)
D = Decimal


def fill(side: Side, qty: str, price: str, fee: str = "0") -> Fill:
    return Fill(
        fill_id=f"F{side}{qty}{price}",
        order_ref="O",
        instrument_id="X",
        side=side,
        quantity=D(qty),
        price=D(price),
        fee=D(fee),
        fill_time=T,
        model="test",
    )


def acct() -> AccountState:
    return AccountState(instrument_id="X", initial_collateral=D("10000"))


def test_long_open_increase_reduce_close():
    a = acct().apply_fill(fill(Side.BUY, "0.1", "60000", "3"))
    assert a.quantity == D("0.1") and a.side == "LONG" and a.average_entry_price == D("60000")
    a = a.apply_fill(fill(Side.BUY, "0.1", "62000", "3"))
    assert a.quantity == D("0.2") and a.average_entry_price == D("61000")
    a = a.mark(D("63000"))
    assert a.unrealized_pnl == D("400")  # (63000-61000)*0.2
    a = a.apply_fill(fill(Side.SELL, "0.05", "63000", "1"))
    assert a.quantity == D("0.15") and a.average_entry_price == D("61000")
    assert a.realized_pnl == D("100")
    a = a.apply_fill(fill(Side.SELL, "0.15", "60000", "1"))
    assert a.quantity == 0 and a.side == "FLAT" and a.average_entry_price is None
    assert a.realized_pnl == D("100") + D("-150")
    assert a.fees_paid == D("8")
    assert a.equity == D("10000") - D("50") - D("8")


def test_short_open_reduce_close_profits_when_price_falls():
    a = acct().apply_fill(fill(Side.SELL, "0.2", "60000", "6"))
    assert a.quantity == D("-0.2") and a.side == "SHORT"
    a = a.mark(D("59000"))
    assert a.unrealized_pnl == D("200")
    assert a.exposure().exposure_fraction == (D("0.2") * D("59000") / a.equity).quantize(D("0.00000001"))
    a = a.apply_fill(fill(Side.BUY, "0.1", "59000", "3"))
    assert a.quantity == D("-0.1") and a.realized_pnl == D("100")
    a = a.apply_fill(fill(Side.BUY, "0.1", "61000", "3"))
    assert a.quantity == 0 and a.realized_pnl == D("0")
    assert a.equity == D("10000") - D("12")


def test_flip_through_zero_resets_entry():
    a = acct().apply_fill(fill(Side.BUY, "0.1", "60000"))
    a = a.apply_fill(fill(Side.SELL, "0.3", "61000"))
    assert a.quantity == D("-0.2") and a.average_entry_price == D("61000")
    assert a.realized_pnl == D("100")


def test_equity_identity_holds():
    a = acct().apply_fill(fill(Side.SELL, "0.1", "60000", "2")).mark(D("60500"))
    assert a.equity == a.collateral_balance + a.unrealized_pnl
    snap = a.snapshot(T)
    assert snap.funding == "NOT_MODELED"
    assert snap.position.side == "SHORT"


def test_market_fill_slippage_is_adverse_and_fee_charged():
    costs = CostAssumptions(fee_bps=D("5"), slippage_bps=D("2"))
    base = dict(
        intent_ref="I", instrument_id="X", quantity=D("0.1"), filled_quantity=D("0"),
        reduce_only=False, submitted_at=T, status=OrderStatus.SUBMITTED,
    )
    buy = simulate_market_fill(Order(order_id="B", side=Side.BUY, **base), D("60000"), T, costs, "FB")
    sell = simulate_market_fill(Order(order_id="S", side=Side.SELL, **base), D("60000"), T, costs, "FS")
    assert buy.price == D("60012.00") and sell.price == D("59988.00")
    assert buy.fee == D("3.0006")
