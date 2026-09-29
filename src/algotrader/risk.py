"""Independent risk skeleton.

Risk evaluates a trader's proposal without trusting the trader: it caps
exposure at 1x equity (Foundation hard limit), blocks new exposure on
unsafe data or accumulated loss, and enforces action/position consistency.

Numeric values other than the 1x cap are DEMO placeholders. The Director
freezes real simulation risk budgets before evidentiary paper operation.
"""

from __future__ import annotations

from datetime import datetime
from decimal import ROUND_DOWN, Decimal

from pydantic import BaseModel, ConfigDict

from .account import ZERO, AccountState, q
from .contracts import (
    EXPOSED_ACTIONS,
    FLAT_ACTIONS,
    Action,
    ActionProposal,
    DataQuality,
    DataQualityState,
    RiskCheck,
    RiskDecision,
)

HARD_MAX_EXPOSURE_FRACTION = Decimal("1")


class RiskPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    max_exposure_fraction: Decimal = HARD_MAX_EXPOSURE_FRACTION
    max_accumulated_loss_fraction: Decimal = Decimal("0.20")
    block_new_exposure_on_bad_data: bool = True
    label: str = "DEMO_PLACEHOLDER_NOT_FROZEN"

    def model_post_init(self, __context) -> None:
        if self.max_exposure_fraction > HARD_MAX_EXPOSURE_FRACTION:
            raise ValueError("exposure above 1x account equity is outside product scope")


def _size(fraction: Decimal, equity: Decimal, price: Decimal, step: Decimal) -> Decimal:
    raw = fraction * equity / price
    return (raw / step).to_integral_value(rounding=ROUND_DOWN) * step


def evaluate(
    policy: RiskPolicy,
    proposal: ActionProposal,
    account: AccountState,
    quality: DataQualityState,
    sizing_price: Decimal | None,
    quantity_step: Decimal,
    order_pending: bool,
    as_of: datetime,
    risk_decision_id: str,
) -> RiskDecision:
    action = proposal.action
    current = account.quantity
    exposed = current != ZERO
    checks: list[RiskCheck] = []

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append(RiskCheck(name=name, passed=passed, detail=detail))

    # 1. Action must match the exposure state.
    allowed = EXPOSED_ACTIONS if exposed else FLAT_ACTIONS
    check(
        "action_matches_exposure_state",
        action in allowed,
        f"{action} while {'exposed' if exposed else 'flat'}",
    )

    # 2. Compute requested target quantity.
    requested = current
    increases = False
    if action in (Action.LONG, Action.SHORT) and sizing_price is not None:
        size = _size(proposal.target_exposure_fraction, account.equity, sizing_price, quantity_step)
        requested = size if action == Action.LONG else -size
        increases = True
    elif action in (Action.LONG, Action.SHORT):
        increases = True
    elif action == Action.EXIT:
        requested = ZERO
    elif action == Action.REDUCE and sizing_price is not None and exposed:
        size = _size(proposal.target_exposure_fraction, account.equity, sizing_price, quantity_step)
        requested = size if current > 0 else -size
        check("reduce_reduces", abs(requested) < abs(current), f"target {requested} vs current {current}")

    if action in (Action.LONG, Action.SHORT, Action.REDUCE):
        check("sizing_price_available", sizing_price is not None, "last valid close required for sizing")

    # 3. Hard exposure cap (1x equity).
    fraction = proposal.target_exposure_fraction if increases else ZERO
    check(
        "exposure_cap_1x",
        fraction <= policy.max_exposure_fraction,
        f"requested {fraction}x equity; cap {policy.max_exposure_fraction}x",
    )

    # 4. Data quality blocks new exposure (reductions/exits stay permitted).
    if increases and policy.block_new_exposure_on_bad_data:
        check(
            "data_quality_for_new_exposure",
            quality.status == DataQuality.OK,
            f"data {quality.status}; {quality.bars_since_valid} bar(s) since valid",
        )

    # 5. Accumulated loss limit blocks new exposure.
    if increases:
        floor = account.initial_collateral * (1 - policy.max_accumulated_loss_fraction)
        check("accumulated_loss_limit", account.equity >= floor, f"equity {account.equity} vs floor {q(floor)}")

    # 6. One working order at a time.
    if requested != current:
        check("no_pending_order", not order_pending, "an order is still working" if order_pending else "none")

    failed = tuple(c.name for c in checks if not c.passed)
    approved = not failed
    approved_target = requested if approved else current
    equity = account.equity
    approved_fraction = (
        q(abs(approved_target) * sizing_price / equity) if sizing_price is not None and equity > 0 else ZERO
    )
    return RiskDecision(
        risk_decision_id=risk_decision_id,
        as_of=as_of,
        proposed_action=action,
        requested_target_quantity=requested,
        approved=approved,
        approved_target_quantity=approved_target,
        approved_exposure_fraction=approved_fraction,
        checks=tuple(checks),
        blocking_reasons=failed,
    )


def permitted_action(proposal: ActionProposal, risk: RiskDecision, exposed: bool) -> Action:
    if risk.approved:
        return proposal.action
    return Action.HOLD if exposed else Action.NO_TRADE
