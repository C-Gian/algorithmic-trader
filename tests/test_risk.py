"""Independent risk skeleton behaviour."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from algotrader.account import AccountState
from algotrader.contracts import Action, ActionProposal, DataQuality, DataQualityState
from algotrader.risk import RiskPolicy, evaluate, permitted_action

T = datetime(2026, 1, 1, tzinfo=UTC)
D = Decimal
OK = DataQualityState(
    status=DataQuality.OK, as_of=T, last_valid_observation_id="o", last_valid_available_time=T, bars_since_valid=0
)
STALE = OK.model_copy(update={"status": DataQuality.STALE, "bars_since_valid": 2})


def run(action: Action, target: str = "0.5", account=None, quality=OK, pending=False, price=D("50000")):
    account = account or AccountState(instrument_id="X", initial_collateral=D("10000"))
    return evaluate(
        RiskPolicy(),
        ActionProposal(action=action, plan_ref=None, target_exposure_fraction=D(target), reason="t"),
        account.mark(price) if price else account,
        quality,
        price,
        D("0.001"),
        pending,
        T,
        "R",
    )


def long_account(qty: str = "0.1") -> AccountState:
    return AccountState(
        instrument_id="X", initial_collateral=D("10000"), quantity=D(qty), average_entry_price=D("50000")
    )


def test_long_is_sized_within_equity():
    r = run(Action.LONG)
    assert r.approved and r.approved_target_quantity == D("0.100")
    assert r.approved_exposure_fraction == D("0.5")


def test_short_is_signed_negative():
    r = run(Action.SHORT, "0.4")
    assert r.approved and r.approved_target_quantity == D("-0.080")


def test_exposure_above_1x_is_rejected():
    r = run(Action.LONG, "1.5")
    assert not r.approved
    assert "exposure_cap_1x" in r.blocking_reasons
    assert r.approved_target_quantity == 0
    assert permitted_action(
        ActionProposal(action=Action.LONG, plan_ref=None, target_exposure_fraction=D("1.5"), reason=""), r, False
    ) == Action.NO_TRADE


def test_stale_data_blocks_new_exposure_but_not_exit():
    assert "data_quality_for_new_exposure" in run(Action.LONG, quality=STALE).blocking_reasons
    r = run(Action.EXIT, account=long_account(), quality=STALE)
    assert r.approved and r.approved_target_quantity == 0


def test_action_must_match_exposure_state():
    assert "action_matches_exposure_state" in run(Action.HOLD).blocking_reasons
    assert "action_matches_exposure_state" in run(Action.LONG, account=long_account()).blocking_reasons


def test_reduce_must_reduce():
    ok = run(Action.REDUCE, "0.25", account=long_account("0.1"))
    assert ok.approved and ok.approved_target_quantity == D("0.050")
    bad = run(Action.REDUCE, "0.9", account=long_account("0.1"))
    assert "reduce_reduces" in bad.blocking_reasons


def test_pending_order_blocks_new_order():
    assert "no_pending_order" in run(Action.LONG, pending=True).blocking_reasons


def test_accumulated_loss_blocks_new_exposure():
    losing = AccountState(instrument_id="X", initial_collateral=D("10000"), realized_pnl=D("-2500"))
    assert "accumulated_loss_limit" in run(Action.LONG, account=losing).blocking_reasons


def test_blocked_exposed_proposal_becomes_hold():
    r = run(Action.LONG, account=long_account())
    assert permitted_action(
        ActionProposal(action=Action.LONG, plan_ref=None, target_exposure_fraction=D("0.5"), reason=""), r, True
    ) == Action.HOLD
