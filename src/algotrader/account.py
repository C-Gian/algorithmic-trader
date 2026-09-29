"""Paper account and bar-based simulated execution (DEMO assumptions).

Fees and slippage are explicit placeholder assumptions. Funding and
mark/index behaviour are NOT modelled; this is recorded in every account
snapshot and run manifest so the dummy P&L cannot be mistaken for evidence.
"""

from __future__ import annotations

from datetime import datetime
from decimal import ROUND_HALF_EVEN, Decimal

from pydantic import BaseModel, ConfigDict

from .contracts import (
    AccountSnapshot,
    CostAssumptions,
    ExposureSummary,
    Fill,
    Order,
    OrderStatus,
    Position,
    Side,
)

MONEY = Decimal("0.00000001")
ZERO = Decimal("0")

FILL_MODEL = "next_bar_open_market_taker_v1"


def q(value: Decimal) -> Decimal:
    if value == 0:
        return ZERO
    return value.quantize(MONEY, rounding=ROUND_HALF_EVEN)


class AccountState(BaseModel):
    """Mutable-by-copy account ledger state (checkpointable)."""

    model_config = ConfigDict(extra="forbid")

    instrument_id: str
    initial_collateral: Decimal
    realized_pnl: Decimal = ZERO
    fees_paid: Decimal = ZERO
    quantity: Decimal = ZERO  # signed BTC
    average_entry_price: Decimal | None = None
    mark_price: Decimal | None = None

    @property
    def collateral_balance(self) -> Decimal:
        return q(self.initial_collateral + self.realized_pnl - self.fees_paid)

    @property
    def unrealized_pnl(self) -> Decimal:
        if self.quantity == ZERO or self.mark_price is None or self.average_entry_price is None:
            return ZERO
        return q((self.mark_price - self.average_entry_price) * self.quantity)

    @property
    def equity(self) -> Decimal:
        return q(self.collateral_balance + self.unrealized_pnl)

    @property
    def side(self) -> str:
        if self.quantity > 0:
            return "LONG"
        if self.quantity < 0:
            return "SHORT"
        return "FLAT"

    def exposure(self) -> ExposureSummary:
        notional = q(abs(self.quantity) * self.mark_price) if self.mark_price is not None else ZERO
        equity = self.equity
        fraction = q(notional / equity) if equity > 0 else ZERO
        return ExposureSummary(
            side=self.side, quantity=self.quantity, notional=notional, exposure_fraction=fraction
        )

    def snapshot(self, as_of: datetime) -> AccountSnapshot:
        exp = self.exposure()
        return AccountSnapshot(
            as_of=as_of,
            collateral_balance=self.collateral_balance,
            realized_pnl=q(self.realized_pnl),
            unrealized_pnl=self.unrealized_pnl,
            fees_paid=q(self.fees_paid),
            equity=self.equity,
            mark_price=self.mark_price,
            position=Position(
                instrument_id=self.instrument_id,
                side=self.side,
                quantity=self.quantity,
                average_entry_price=self.average_entry_price,
            ),
            exposure_notional=exp.notional,
            exposure_fraction=exp.exposure_fraction,
        )

    def mark(self, price: Decimal) -> AccountState:
        return self.model_copy(update={"mark_price": price})

    def apply_fill(self, fill: Fill) -> AccountState:
        """Return the account after one fill. Handles open/increase/reduce/flip."""
        signed = fill.quantity if fill.side == Side.BUY else -fill.quantity
        qty = self.quantity
        avg = self.average_entry_price
        realized = self.realized_pnl
        new_qty = qty + signed

        if qty == ZERO or (qty > 0) == (signed > 0):
            # open or increase: weighted average entry
            total_cost = (abs(qty) * (avg or ZERO)) + (abs(signed) * fill.price)
            new_avg = q(total_cost / abs(new_qty))
        else:
            closed = min(abs(qty), abs(signed))
            direction = Decimal(1) if qty > 0 else Decimal(-1)
            realized = realized + (fill.price - avg) * closed * direction
            if new_qty == ZERO:
                new_avg = None
            elif (new_qty > 0) == (qty > 0):
                new_avg = avg  # partial reduction keeps entry
            else:
                new_avg = fill.price  # flipped through zero
        return self.model_copy(
            update={
                "quantity": new_qty,
                "average_entry_price": new_avg,
                "realized_pnl": q(realized),
                "fees_paid": q(self.fees_paid + fill.fee),
            }
        )


def simulate_market_fill(
    order: Order, open_price: Decimal, fill_time: datetime, costs: CostAssumptions, fill_id: str
) -> Fill:
    """Fill a market order at the next available bar open with slippage + fee.

    Candle data carries no depth/queue information; this deliberately simple
    model is a DEMO placeholder and must not be read as execution fidelity.
    """
    assert order.status == OrderStatus.SUBMITTED
    slip = open_price * costs.slippage_bps / Decimal(10_000)
    price = open_price + slip if order.side == Side.BUY else open_price - slip
    price = price.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
    fee = q(price * order.quantity * costs.fee_bps / Decimal(10_000))
    return Fill(
        fill_id=fill_id,
        order_ref=order.order_id,
        instrument_id=order.instrument_id,
        side=order.side,
        quantity=order.quantity,
        price=price,
        fee=fee,
        fill_time=fill_time,
        model=FILL_MODEL,
    )
