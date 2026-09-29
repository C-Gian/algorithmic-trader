"""Run validation checks computed from the persisted semantic journal.

These check operational/contract invariants, not trading quality.
"""

from __future__ import annotations

from collections import Counter
from decimal import Decimal
from typing import Any

from .account import AccountState
from .contracts import EXPOSED_ACTIONS, FLAT_ACTIONS, Action, Fill

DEMO_BEHAVIOURS = (
    "LONG",
    "SHORT",
    "NO_TRADE",
    "HOLD",
    "REDUCE",
    "EXIT",
    "risk_rejection",
    "stale_data",
    "plan_activation",
)


def _check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def demo_coverage(events: list[dict[str, Any]]) -> dict[str, bool]:
    seen = {k: False for k in DEMO_BEHAVIOURS}
    for ev in events:
        p = ev["payload"]
        if ev["kind"] == "decision":
            seen[p["permitted_action"]] = True
            if p["blocking_reasons"]:
                seen["risk_rejection"] = True
        elif ev["kind"] == "market_view" and p["validity"] == "STALE":
            seen["stale_data"] = True
        elif ev["kind"] == "trade_plan" and p["status"] == "TRIGGERED":
            seen["plan_activation"] = True
    return seen


def validate_run(
    events: list[dict[str, Any]], steps_processed: int, initial_collateral: Decimal, instrument_id: str, complete: bool
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    seqs = [e["seq"] for e in events]
    checks.append(_check("seq_contiguous", seqs == list(range(len(seqs))), f"{len(seqs)} events"))

    decisions = [e for e in events if e["kind"] == "decision"]
    per_step = Counter(e["step"] for e in decisions)
    ok = sorted(per_step) == list(range(steps_processed)) and all(v == 1 for v in per_step.values())
    checks.append(_check("one_decision_per_step", ok, f"{len(decisions)} decisions for {steps_processed} steps"))

    fills = [e for e in events if e["kind"] == "fill"]
    fill_ids = [f["payload"]["fill_id"] for f in fills]
    checks.append(
        _check("no_duplicate_fills", len(fill_ids) == len(set(fill_ids)), f"{len(fill_ids)} fills, unique ids")
    )

    submitted = {
        e["payload"]["order_id"]: e for e in events if e["kind"] == "order" and e["payload"]["status"] == "SUBMITTED"
    }
    causal = True
    for f in fills:
        order = submitted.get(f["payload"]["order_ref"])
        if (
            order is None
            or f["step"] <= order["step"]
            or f["payload"]["fill_time"] < order["payload"]["submitted_at"]
            or Decimal(f["payload"]["quantity"]) != Decimal(order["payload"]["quantity"])
        ):
            causal = False
    checks.append(
        _check("fills_causal", causal, "every fill follows a prior submitted order on a later bar, same quantity")
    )

    caps = [Decimal(e["payload"]["approved_exposure_fraction"]) for e in events if e["kind"] == "risk_decision"]
    max_cap = max(caps, default=Decimal(0))
    checks.append(_check("approved_exposure_within_1x", max_cap <= 1, f"max approved {max_cap}x equity"))

    semantics_ok = True
    for d in decisions:
        exposed = Decimal(d["payload"]["current_exposure"]["quantity"]) != 0
        allowed = EXPOSED_ACTIONS if exposed else FLAT_ACTIONS
        if Action(d["payload"]["permitted_action"]) not in allowed:
            semantics_ok = False
    checks.append(
        _check("decision_semantics", semantics_ok, "flat: LONG/SHORT/NO_TRADE; exposed: HOLD/REDUCE/EXIT")
    )

    accounts = [e for e in events if e["kind"] == "account"]
    if accounts:
        acct = AccountState(instrument_id=instrument_id, initial_collateral=initial_collateral)
        for f in fills:
            acct = acct.apply_fill(Fill.model_validate(f["payload"]))
        last = accounts[-1]["payload"]
        if last["mark_price"] is not None:
            acct = acct.mark(Decimal(last["mark_price"]))
        recon = (
            acct.equity == Decimal(last["equity"])
            and acct.realized_pnl == Decimal(last["realized_pnl"])
            and acct.fees_paid == Decimal(last["fees_paid"])
            and acct.quantity == Decimal(last["position"]["quantity"])
            and Decimal(last["equity"]) == Decimal(last["collateral_balance"]) + Decimal(last["unrealized_pnl"])
        )
        checks.append(
            _check("account_reconciles_with_fills", recon, f"replayed {len(fills)} fills -> equity {acct.equity}")
        )

    coverage = demo_coverage(events)
    if complete:
        missing = [k for k, v in coverage.items() if not v]
        checks.append(
            _check("demo_fixture_coverage", not missing, "missing: " + ", ".join(missing) if missing else "all present")
        )
    return {
        "passed": all(c["passed"] for c in checks),
        "checks": checks,
        "demo_coverage": coverage,
        "note": "Operational/contract checks only. Not a measure of trading quality.",
    }
