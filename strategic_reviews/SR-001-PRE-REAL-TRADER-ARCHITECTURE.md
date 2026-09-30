# SR-001 — Pre-Real-Trader Architecture Review

Status: REQUESTED  
Reviewer: Astra  
Requested by: Project & Research Director  
Date: 2026-09-30  
Repository state to review: main through WP-003 implementation `6b45728074e470bb85b06cce1995dad90f81cb62`

## Purpose

Perform a high-level strategic/scientific architecture review **before** we connect real BTC-perpetual data to the trader/execution engine and before any professional trader logic is implemented.

This is not a coding task. Do not design UI polish, repository chores, or implementation details that can be delegated to the Director/Claude Code.

The question is whether the next long-lived architecture faithfully supports the project goal:

> reproduce, as faithfully as practical, the market-reading and trade-decision process of an excellent professional BTC trader, while keeping market view distinct from trade action and preserving causal/reproducible research.

## Binding context

Read these first:

1. `FOUNDATION.md`
2. `STATE.md`
3. `AGENTS.md`
4. `knowledge/market_sources/OKX-BTC-USDT-SWAP.md`
5. `schemas/algotrader.semantic.v1.json`
6. `schemas/algotrader.marketdata.v1.json`

Then inspect these implementation boundaries:

- `src/algotrader/engine.py`
- `src/algotrader/contracts.py`
- `src/algotrader/trader.py`
- `src/algotrader/account.py`
- `src/algotrader/risk.py`
- `src/algotrader/synthetic.py`
- `src/algotrader/marketdata/contracts.py`
- `src/algotrader/marketdata/dataset.py`
- `src/algotrader/marketdata/okx.py`

Use the professional dossiers under `source_notes/` where relevant, especially the material on forecast-vs-action, execution, microstructure, validation, trend-family redundancy, and derivatives. Do not import legacy Trading Bot architecture or conclusions embedded in historical notes.

## Accepted product scope

- BTC only.
- Operational paper instrument: BTC perpetual futures.
- LONG / SHORT / NO_TRADE.
- HOLD / REDUCE / EXIT while exposed.
- No leverage above 1x account-equity exposure.
- Short-duration trading: generally minutes to hours, not days.
- Broader timeframes may inform market context.
- Research/paper only; no real-money authorization.
- Single-user local-first application.

## What is already accepted

### Operational shell

WP-001 and WP-002 established:

- deterministic trader interface;
- durable PostgreSQL jobs/checkpoints;
- replay speed/pause/resume/step;
- same engine semantics across replay speeds/restarts;
- explicit runtime vs trading state;
- UI observability;
- immutable run artifacts;
- frozen semantic contract baseline `algotrader.semantic.v1`.

### Real market-data evidence layer

WP-003 established:

- public/read-only OKX `BTC-USDT-SWAP`;
- separate `algotrader.marketdata.v1` baseline;
- source-auditable instrument metadata;
- traded-price 1m candles;
- mark-price 1m candles;
- index-price 1m candles;
- funding-rate events;
- exact decimals;
- raw response retention + hashes;
- immutable datasets;
- gap/duplicate/incomplete-bar auditing;
- event time, modeled availability time and retrieval time kept distinct;
- no silent forward filling;
- no authenticated trading/account connectivity.

## Important current limitations / synthetic scaffolding

The existing engine is intentionally not yet a real perpetual engine.

Today:

1. `Engine` is constructed from a synthetic `Fixture`.
2. The primary trader input is one `MarketObservation` carrying OHLC and one ambiguous `volume`.
3. The dummy trader is scripted by bar index.
4. Account quantity is effectively treated as BTC/base units.
5. Mark-to-market uses the last valid synthetic traded close.
6. Funding is `NOT_MODELED`.
7. Fees/slippage are DEMO placeholders.
8. A market order fills at the next available bar open using a simple bar-based model.
9. `algotrader.semantic.v1` was frozen before real market data was connected.

These are deliberate scaffolding and must not be mistaken for accepted real-perpetual semantics.

## Current source facts that matter

From current official OKX documentation for linear perpetuals:

- derivative size is expressed in contracts;
- for linear contracts, position notional is based on contract count × contract value × mark price (with contract multiplier where applicable);
- unrealized P&L is mark-price based;
- funding fees are based on position value × funding rate;
- positive funding means longs pay shorts; negative funding reverses that;
- a funding fee only applies when the position is held at the settlement event;
- funding frequency/formula can change, and OKX changed its funding-rate formula in June 2026;
- historical funding endpoint gives event rows containing `fundingTime`, `fundingRate`, `realizedRate`, method/formula metadata;
- maker/taker fees depend on account/fee tier and must not be silently frozen from a generic source.

Do not assume these facts imply how the software architecture must look; use them as constraints.

## Strategic decisions to review

### A. What is the correct boundary between market-data evidence and trader input?

We intentionally have immutable source evidence in `algotrader.marketdata.v1`.

Should the real trader consume:

1. a single synchronized `MarketFrame` assembled at each decision time;
2. an ordered causal event stream of heterogeneous events (trade candle, mark candle, funding event, etc.);
3. a hybrid model where an event clock updates a persistent observable market state and the trader receives a snapshot;
4. something else?

We need a recommendation that preserves asynchronous source timing, explicit missingness/freshness, multi-horizon context and future extensibility without turning everything into one flat “feature row.”

### B. Should `algotrader.semantic.v2` be introduced now?

`semantic.v1` contains a single `MarketObservation` with ambiguous volume and was sufficient for the synthetic shell.

Options include:

- keep v1 and add real-data mechanics outside semantic contracts until the real trader is specified;
- intentionally introduce `semantic.v2` now with explicit real-market input semantics;
- replace `MarketObservation` with a more expressive market-input/state contract;
- preserve v1 records but add new orthogonal contracts.

Assess the cost of premature freezing versus the cost of letting real-data/execution assumptions leak into ad-hoc internal structures.

### C. How should multiple price concepts enter the system?

For a linear BTC perpetual we now have:

- traded price / OHLC;
- mark price;
- index price;
- funding events.

Clarify their professional/software roles:

- what belongs to market observation/state;
- what belongs to account/risk;
- what can affect trader reasoning;
- what is only execution/accounting;
- how missing or stale values should constrain action without erasing the market view.

Avoid flat indicator voting.

### D. How should gaps and asynchronous availability work?

The data layer can report gaps, invalid rows, incomplete candles and family-specific timestamps.

Review the correct causal behavior when, for example:

- traded candle exists but mark candle is missing;
- mark/index arrives later under the modeled availability convention;
- funding event occurs at the same timestamp as a candle close;
- one family is stale while another is fresh;
- a row is marked INVALID.

We need a deterministic tie-ordering/freshness policy that prevents hidden lookahead and supports later live paper operation.

### E. Perpetual accounting and position units

The current account model is synthetic and must not be generalized blindly.

Review the proper conceptual model for a linear USDT-settled BTC perpetual with no leverage amplification:

- positions in contract units;
- base-equivalent exposure;
- quote/settlement notional;
- 1x exposure cap;
- average entry;
- realized P&L;
- unrealized P&L based on mark;
- fees;
- funding cash flows;
- collateral/equity.

Should risk reason in contract quantity, BTC-equivalent, USDT notional, or a combination with explicit conversions?

Where should instrument metadata/history be pinned so a change in tick/lot/contract parameters cannot rewrite old runs?

### F. Execution simulation fidelity

We have only 1m OHLC for the first data layer.

The Foundation explicitly forbids pretending candle data provides queue/depth fidelity.

Review what the **minimum scientifically defensible execution model** should be before the first real trader is evaluated:

- market-order timing;
- next-bar-open vs other conservative conventions;
- spreads/slippage;
- missing bars;
- stop/invalidation handling;
- ambiguous intra-bar ordering;
- funding/fee timing;
- partial fills/non-fill (whether to defer until richer data).

Identify what must exist before trader evaluation versus what can be deferred to higher-fidelity future data.

### G. Proposed M3 sequence

The Director's tentative sequence is:

**WP-004:** real-dataset causal replay plumbing, but no real trading/account economics yet.  
Use the accepted market dataset as a replay/event source; prove missingness/timing/real-data UI and deterministic restart/replay. Prevent invalid rows from entering as valid observations. Avoid producing meaningful P&L.

**WP-005:** correct BTC-USDT-SWAP contract/account/execution/funding model.  
Implement unit conversion, mark-based equity, funding events, instrument pinning and explicit parameterized costs/fill assumptions; validate with synthetic mathematical cases and source-grounded examples.

Then, only after M3 is accepted:

**Astra/Director trader-design review → first coherent professional trader specification → implementation.**

Assess whether this sequence is correct, should be combined, or should be reordered.

### H. Knowledge gaps before real trader design

Given the initial 20 dossiers and the actual product scope (BTC perpetual intraday), identify only the gaps that are **material enough to block** the first coherent trader design.

Examples that may or may not be blockers:

- BTC/perpetual-specific market microstructure;
- funding/basis interpretation;
- liquidation mechanics;
- support/resistance formalization;
- retracement/extension;
- cycle/temporal methodology;
- trustworthy order-flow data;
- how professional discretionary traders combine multi-timeframe context with triggers.

Do not recommend broad literature collection by default. Distinguish:
- must know before first trader;
- can be added later;
- not needed.

## What I want from Astra

Produce a concise but deep architecture review with:

1. **Recommended architecture** for the market-data → observable-state → trader → risk → account/execution chain.
2. **Decisions to freeze now**, with rationale.
3. **Decisions explicitly NOT to freeze yet**.
4. **Assessment of semantic.v1/v2 strategy**.
5. **Recommended deterministic causal/tie-order model**.
6. **Minimum perpetual accounting/execution model required before trader evaluation**.
7. **Review of proposed WP-004/WP-005 sequence**.
8. **Only material pre-trader knowledge gaps**.
9. **Red-team findings**: anything in the current Foundation/WP-001..003 implementation that could constrain the eventual professional trader incorrectly.
10. A final **go / revise / stop-before-next-implementation** recommendation, with specific reasons.

Do not write code or executor tasks. The Director will translate accepted conclusions into implementation work.

If evidence is uncertain or professional sources disagree, preserve the uncertainty instead of inventing a single precise rule.
