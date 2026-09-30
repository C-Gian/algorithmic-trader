# Project State

Updated: 2026-09-30

## Authority

Canonical directive: `FOUNDATION.md` — version 2.0.

## Corrected accepted product scope

Algorithmic Trader is a **BTC market-analysis and trade-decision system**, not an autonomous account-management/trading bot.

The system must:

- maintain a current professional MarketView;
- state plausible/primary scenarios and expected market behavior;
- decide LONG / SHORT / NO_TRADE;
- when a trade exists, expose trigger/entry logic, invalidation, target(s), expected room/time and reasons;
- keep market understanding distinct from trade recommendation;
- update the view/recommendation as the market evolves.

The human Owner independently decides:

- capital allocation;
- position size;
- leverage;
- collateral/margin;
- actual order placement;
- personal portfolio/account risk.

Those choices are outside the algorithm's recommendation semantics.

## Current milestone

**M3 — Trustworthy real-market observation and causal reasoning readiness**

The operational shell and source-auditable OKX market-data evidence layer are accepted.

The next objective is to create the long-lived causal boundary:

**market evidence → availability feed → observable market state → later professional reasoning**

No real professional trader intelligence enters M3 yet.

## Accepted work

### WP-001 — Repository bootstrap and observable dummy run
Accepted implementation lineage:
- `92014aa03060332b4c947ef10329b79cde7d51b2`
- CI correction `a49c0f75be7d9d885c65901c9cc73f3ed3a66a99`

The dummy account/risk/order/fill path remains DEMO infrastructure scaffolding only.

### WP-002 — Replay/operations shell and semantic baseline
Accepted implementation:
- `803b3f215c5a33499a4d901ae000ee112b75e691`

Accepted outcomes include durable replay controls, restart recovery, runtime visibility and frozen `algotrader.semantic.v1`.

`algotrader.semantic.v1` is the synthetic-shell baseline, not the final professional trader contract.

### WP-003 — OKX BTC-USDT-SWAP public data provenance
Accepted implementation:
- `6b45728074e470bb85b06cce1995dad90f81cb62`

Acceptance evidence:
- GitHub Actions run `36688980492`: SUCCESS;
- `checks`: SUCCESS;
- `compose-smoke`: SUCCESS;
- live public OKX integration succeeded;
- `algotrader.marketdata.v1` remains separate from semantic contracts;
- event, modeled availability and retrieval time are distinct;
- incomplete/invalid/gap/duplicate evidence is surfaced without silent repair.

Accepted WP-003 interpretations remain unchanged.

## SR-001 strategic review

Inputs retained:

- `strategic_reviews/ASTRA-SR-001-REVIEW.md`
- `strategic_reviews/CLAUDE-SR-001-REVIEW.md`

Both were useful. Astra is the primary strategic reviewer; Claude is retained as a secondary independent/technical review.

Director disposition:

`strategic_reviews/SR-001-DIRECTOR-DISPOSITION.md`

The Owner clarified after both reviews that account sizing, leverage and capital allocation are human responsibilities. Foundation v2.0 supersedes inconsistent Foundation v1.x language.

Accepted SR-001 architecture:

- heterogeneous causal events;
- centrally owned observable market state;
- per-channel freshness/quality;
- explicit event/availability/retrieval times;
- role-specific traded/mark/index/funding information;
- replay/live parity;
- no raw dataset access from professional reasoning;
- no bar-indexed assumption as the long-lived engine boundary.

Rejected as product requirements:

- autonomous 1x account-equity control;
- leverage selection;
- position sizing;
- margin/collateral management;
- full perpetual account/liquidation modeling.

Trade execution/cost mechanics remain relevant only when needed to fairly evaluate a concrete recommendation.

## Contract strategy

Keep frozen:

- `algotrader.semantic.v1` — synthetic shell;
- `algotrader.marketdata.v1` — market evidence.

Next introduce:

- provisional `algotrader.feed.v1` — causal deliveries and observable-state contracts.

Do **not** introduce `semantic.v2` until the first real professional trader specification is designed.

## Initial market-data source

Public/read-only reference source:

**OKX `BTC-USDT-SWAP`**

Source decision:
`knowledge/market_sources/OKX-BTC-USDT-SWAP.md`

This is a data/reference source choice, not a broker or automated-execution decision.

## Active task

**WP-004 — Causal feed and observable market state pure core**

See `task.md`.

## Base knowledge snapshot

`3bf9de0d88fd97360bff7a6517bbb61544f5db68` — professional dossiers only.

## Parallel pre-trader research gaps

Before the first real professional trader specification, the Director must resolve only what the chosen trader actually requires, especially:

1. professional intraday multi-timeframe context → trigger → invalidation → target/management process;
2. causal structure/levels/support-resistance formalization;
3. venue/data mechanics required by that process.

Broad literature collection, cycle theory, retracement ratios, order flow/L2 and liquidation-flow interpretation are not automatic prerequisites.

## Next action

Owner pulls latest `main` after the Director merges this scope correction.

Claude Code then implements only WP-004 from `task.md`.

After WP-004 acceptance, the expected next package is observation-only real replay plus prospective public receipt-time recording. No professional trader logic is introduced before a later trader-design checkpoint.
