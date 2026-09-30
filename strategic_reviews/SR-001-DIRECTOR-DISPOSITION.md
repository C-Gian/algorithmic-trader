> **HISTORICAL SCOPE NOTICE — 30 September 2026.** FOUNDATION.md v3.0 implements the Owner's direct clarification and supersedes inconsistent scope/workflow instructions below. This document is retained as historical/advisory evidence. Its former ACCEPTED/READY/HOLD status is not current authorization. In particular, the mandatory pullback-only path, blanket cycle/news deferrals and RP-001 closure gate are no longer project direction. Reuse compatible findings only through the current task; preserve original evidence and failed cases. See the current FOUNDATION.md, STATE.md and task.md.

# SR-001 — Director Disposition after Owner Product Clarification

Status: ACCEPTED DIRECTION  
Date: 2026-09-30  
Authority: Project & Research Director, grounded in explicit Owner clarification

## Inputs reviewed

- `SR-001-PRE-REAL-TRADER-ARCHITECTURE.md`
- `ASTRA-SR-001-REVIEW.md`
- `CLAUDE-SR-001-REVIEW.md`
- Owner clarification on 2026-09-30 that the product is a professional market-analysis/trade-decision assistant, **not** an autonomous account/position-sizing bot.

Both advisory reviews were produced against Foundation v1.x, which incorrectly encoded account-level exposure/leverage management as product requirements. Their recommendations are therefore accepted selectively under Foundation v2.0.

## Product clarification that supersedes part of the review brief

The system's job is to:

1. understand the BTC market continuously;
2. maintain a current MarketView;
3. state plausible/primary future scenarios;
4. decide LONG / SHORT / NO_TRADE;
5. when a trade exists, describe professional trade geometry such as trigger/entry zone, invalidation, target(s), expected room/time and reasons;
6. update that view/recommendation as the market evolves.

The human Owner decides independently:

- capital size;
- position size;
- leverage;
- margin/collateral;
- actual order placement;
- personal portfolio/account risk.

Therefore no 1x account-equity policy, margin model, liquidation policy or autonomous deleveraging rule is required by the real trader.

## Conclusions accepted from both reviews

### 1. Hybrid causal architecture

Accepted:

**market evidence → causal availability feed/event clock → centrally owned observable market state → professional reasoning → MarketView/scenarios → trade recommendation**

The trader must not read raw datasets directly and must not reimplement freshness, gaps, revision semantics or source ordering independently.

A snapshot may be accompanied by causally available changes/delta/history.

### 2. Preserve distinct times

Accepted invariants:

- event/economic time;
- availability/knowledge time;
- retrieval/recording/provenance time;
- deterministic processing order.

No decision may depend on information whose availability exceeds its information cutoff.

### 3. Heterogeneous sources and role-specific state

Accepted:

- traded, mark, index and funding remain separately typed;
- no silent substitution;
- freshness and missingness are per channel/dependency;
- invalid data remains auditable evidence but never silently becomes a valid observation;
- higher-timeframe derived observations must respect causal completion.

### 4. MarketView remains distinct from trade decision

Accepted and strengthened by Owner clarification.

A directional or predictive market view can coexist with NO_TRADE. Trade opportunity is a selective decision layer, not a synonym for understanding the market.

### 5. Replay/live parity

Accepted:

Any source used by the trader in live operation must either have point-in-time historical reconstruction or be prospectively recorded before it may be used in reproducible research.

This is especially relevant to evolving pre-settlement funding information.

### 6. Current bar-indexed engine is scaffolding

Accepted:

The real path must not be permanently constrained by:

- one bar = one semantic step;
- one global data-quality flag;
- one observation per trader invocation;
- bar-index identities;
- dummy account/fill semantics.

The durable worker/replay/operations shell remains valuable.

## Recommendations changed by Owner clarification

### Account / ledger / 1x exposure

Not adopted as product requirements.

A future evaluation harness may use normalized trade units and trade-level cost models solely to determine whether a recommendation was realistically actionable/economically worthwhile.

It must not tell the Owner how much capital or leverage to use.

### Independent risk

Reinterpreted for the product.

The professional recommendation layer may reject/abstain because of:

- data uncertainty;
- conflicting evidence;
- insufficient expected movement;
- poor location/timing;
- execution/cost uncertainty;
- unusually poor reward-to-invalidation geometry or other method-specific trade-quality constraints.

It is **not** an autonomous portfolio/account risk manager.

### Execution/accounting

A scientifically defensible execution model remains useful for **evaluation**, because recommendation timing and costs matter.

A complete perpetual account, margin or liquidation emulator is not a prerequisite for the real market analyst.

Only the mechanics required to score the proposed trade fairly should be added, when needed.

## Contract-version decision

Astra recommended introducing `semantic.v2` immediately. Claude recommended provisional feed/perpetual namespaces and delaying v2 until the real trader specification.

Under the corrected product scope, the Director adopts the conservative middle path:

- keep `algotrader.semantic.v1` frozen as the accepted synthetic-shell baseline;
- keep `algotrader.marketdata.v1` frozen as the accepted market-evidence baseline;
- introduce a provisional, explicitly versioned **`algotrader.feed.v1`** for causal availability events and observable market state;
- do **not** create a perpetual-account contract namespace solely because the old brief expected autonomous account management;
- introduce **`algotrader.semantic.v2` together with the first real professional trader specification**, when MarketView, prediction and trade-recommendation semantics are actually known well enough to freeze.

This prevents both ad-hoc data plumbing and premature freezing of the professional reasoning contract.

## Revised M3 sequence

M3 is no longer “execution readiness for an autonomous paper trader.”

It becomes **trustworthy real-market observation and causal reasoning readiness**.

Sequence:

### WP-004 — Causal feed and observable market state pure core

- provisional `algotrader.feed.v1`;
- heterogeneous availability events;
- deterministic ordering;
- per-channel freshness/quality;
- dataset → causal-feed adapter;
- pure observable-state reducer;
- prefix/truncated-history invariance;
- no trader intelligence;
- no account/economic P&L.

### WP-005 — Observation-only real replay + prospective public recorder

- integrate feed/state into the durable runner/UI;
- real-data replay without DEMO account economics;
- start recording actual public receipt times for relevant live channels;
- prove recorded-input replay/live state parity;
- preserve replay controls/restart durability.

### Parallel Director research before first trader

Target only the knowledge gaps needed for the first coherent professional process:

1. a professional intraday multi-timeframe context → trigger → invalidation → target/management process applicable or adaptable to BTC/24-7 markets;
2. causal market structure / support-resistance / level formalization;
3. any venue/data mechanics required by the selected professional process.

No broad theory collection by default.

### After M3

Strategic trader-design checkpoint:

- define the first coherent professional trader;
- define scoreable MarketView/prediction/recommendation contracts;
- introduce `algotrader.semantic.v2`;
- implement and validate the trader.

Trade-outcome/cost simulation is added only to the fidelity required to judge those recommendations.

## Explicitly rejected or deferred

Do not presently build:

- autonomous position sizing;
- 1x exposure management;
- autonomous leverage policy;
- margin/collateral management;
- liquidation engine;
- full perpetual portfolio ledger;
- authenticated orders;
- account-specific fee-tier logic;
- order-book reconstruction from candles.

Do not infer from this disposition that costs/execution are irrelevant. They remain part of recommendation evaluation when a concrete trader requires them.

## Final disposition

**GO** with Foundation v2.0 and the revised M3 sequence.

WP-001–WP-003 remain accepted for their original bounded purposes.

The next implementation work is WP-004: causal feed and observable market state, with no professional trader logic and no autonomous account/execution scope.
