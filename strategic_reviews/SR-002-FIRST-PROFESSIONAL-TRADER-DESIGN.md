# SR-002 — First Professional Trader Design

Status: READY FOR ASTRA  
Date: 2026-09-30  
Requested by: Project & Research Director  
Role expected: highest-level strategic/scientific architect and independent red-team reviewer

## Clean-room instruction

This is the clean-room **Algorithmic Trader** project.

Do not import or reconstruct architecture, terminology, experiments, thresholds, conclusions, ADRs, workflows or implementation decisions from the previous Trading Bot project.

Use only:
- this repository;
- the professional source dossiers in `source_notes/`;
- their provenance/status in `knowledge/registry.yaml`;
- external professional knowledge only if clearly distinguished and genuinely needed.

Foundation v2.0 and STATE.md are authoritative.

## Why this review exists

M3 is complete.

The project now has a trustworthy observation substrate:

**immutable real market evidence → causal feed deliveries → centrally owned observable market state → durable replay/product visibility**

The professional trader does **not** exist yet.

The next architectural decision is therefore not “which indicator should we code first?”

It is:

> **What is the first coherent professional market-reading and trade-decision process that should sit on top of the accepted causal market-state substrate, and what exact semantics must software expose so that process can be implemented and scientifically validated without collapsing into signal voting, hindsight or backtest mining?**

This review is the gate before:
- `semantic.v2`;
- first real trader implementation;
- professional MarketView;
- scenarios/predictions;
- LONG/SHORT/NO_TRADE;
- trigger/invalidation/targets.

## Product truth that must not be changed

Algorithmic Trader is a BTC market-analysis and trade-decision system.

It should eventually:
- continuously understand BTC market state;
- maintain a current MarketView;
- state plausible/primary scenarios;
- express expected market behavior and horizon;
- decide LONG / SHORT / NO_TRADE;
- when a trade exists, define trigger/entry condition or zone, invalidation, target(s), expected room/time and reasons;
- update the view/recommendation as the market evolves.

The human Owner independently decides:
- capital amount;
- position size;
- leverage;
- margin/collateral;
- actual order placement;
- personal portfolio/account risk.

Do not reintroduce autonomous capital management.

## Critical semantic principle

**Market view / prediction is not the same thing as trade decision.**

The trader may hold a directional or structural view while still returning NO_TRADE because:
- location/timing is poor;
- expected movement is too small;
- uncertainty is high;
- evidence conflicts;
- costs/execution uncertainty are too large;
- the geometry is unattractive.

NO_TRADE must not mean “the system does not understand the market.”

## Read first

Read in full:

1. `FOUNDATION.md`
2. `STATE.md`
3. `strategic_reviews/SR-001-DIRECTOR-DISPOSITION.md`
4. `knowledge/registry.yaml`
5. `knowledge/PROFESSIONAL-MARKET-REASONING-SYNTHESIS.md` if present
6. accepted causal/evidence contracts:
   - `src/algotrader/marketdata/contracts.py`
   - `src/algotrader/feed/contracts.py`
   - `src/algotrader/feed/state.py`
   - `src/algotrader/recorder/contracts.py`
   - `src/algotrader/observe/contracts.py`
7. the source dossiers under `source_notes/`, with particular attention to material relevant to:
   - practitioner trading process;
   - trend/persistence;
   - expected-return combination;
   - execution/microstructure;
   - derivatives context;
   - research methodology / overfitting.

You may inspect implementation details only where necessary to understand the accepted boundary. Do not let current scaffolding dictate the professional design.

## Existing professional-knowledge synthesis to preserve unless you can improve it

Current project direction already holds that:

- professional observations are not flat indicator votes;
- correlated observations must not be double-counted as independent evidence;
- volatility often describes context/opportunity/risk rather than direction by itself;
- liquidity/execution constraints can veto a trade without negating the underlying market view;
- multiple horizons can disagree;
- continuous market understanding should coexist with selective trade decisions;
- component usefulness does not imply standalone profitability;
- causal point-in-time validation is mandatory;
- protected evaluation and prospective evidence matter;
- the mission is to formalize existing professional trading knowledge, not to invent novel alpha.

Challenge any of these if the evidence justifies it, but do not discard them casually.

## Current observable substrate

The real replay currently exposes causal, factual market state for:

- traded 1m OHLC + typed volume;
- mark 1m OHLC;
- index 1m OHLC;
- settled funding when present;
- channel condition / freshness / quality / gaps / rejected evidence;
- availability time vs market time;
- bounded per-channel history;
- source provenance.

Prospective recordings additionally preserve evolving pre-settlement funding raw evidence, but it is not yet promoted into a settled-funding state channel.

The architecture is deliberately not permanently bar-indexed:
- replay step = one causal feed delivery;
- multiple heterogeneous evidence families may arrive at the same or different knowledge times.

## Do not assume current 1m evidence is sufficient

A professional trader may require:
- derived higher-timeframe bars;
- causal market structure;
- swing points;
- support/resistance;
- trend/persistence state;
- momentum/participation;
- volatility state;
- retracement/extension concepts;
- temporal/session context;
- derivatives context;
- trustworthy order flow;
- liquidity state;
- external context.

Your task is to decide which of these belong in the **first coherent trader** and which should be deferred.

Do not include a lens merely because it exists in trading literature.

## Central design questions

### 1. What is the first coherent professional process?

Define an explicit reasoning sequence.

For example, should the trader conceptually proceed through something like:

**higher-timeframe context → local structure/location → current pressure/participation → scenario formation → trigger → trade geometry → actionability vetoes → recommendation**

or should it use a materially different professional structure?

Do not merely list indicators or feature families.

Explain:
- what each stage is trying to know;
- what inputs it is allowed to use;
- what output it produces;
- how later stages depend on earlier stages;
- where uncertainty enters;
- what is descriptive vs predictive vs decision-oriented.

### 2. Multi-timeframe / multi-horizon design

Decide:
- which horizons matter for an initial BTC intraday trader;
- whether horizons are fixed durations, market-structure horizons, or both;
- how conflicts between horizons should be represented;
- whether a broader bearish context can coexist with a short-term bullish scenario;
- how horizon disagreement affects recommendation rather than being resolved by crude voting.

Avoid arbitrary timeframe proliferation.

### 3. Market state vs derived professional observations

Define the boundary between:
- raw observable state;
- causally derived observations/features;
- professional interpretation.

Which derived observations should be centrally computed and reusable rather than independently recomputed by each reasoning component?

Examples to assess:
- completed higher-timeframe bars;
- returns/ranges;
- realized volatility;
- swing structure;
- trend state;
- momentum state;
- volume/participation state;
- levels/zones;
- distance-to-level / room-to-target;
- funding/derivatives context.

Specify where derivation ends and interpretation begins.

### 4. Price structure and levels

The project currently has a knowledge gap around causal support/resistance and market-structure formalization.

Decide:
- whether the first real trader requires explicit swing structure / S&R;
- if yes, what professional concept should be formalized;
- how to avoid hindsight pivots;
- how levels/zones should be created, updated, weakened, invalidated and aged causally;
- whether exact lines or zones are more defensible;
- which concepts can be postponed.

If current knowledge is insufficient, state the exact research required before implementation.

### 5. Trend, momentum and participation

Decide the justified roles of:
- trend/persistence;
- momentum;
- volume/participation.

Do not permit three correlated expressions of the same phenomenon to become three “votes.”

Explain:
- what distinct question each lens answers;
- how redundancy should be controlled;
- whether any should be omitted from the first trader.

### 6. Volatility

Decide whether volatility in the first trader is used for:
- regime/context;
- expected movement;
- target/invalidation scaling;
- trade filtering;
- timing;
- some combination.

Do not make volatility directional without evidence.

### 7. Derivatives context

Given BTC-USDT perpetuals, assess what the first trader truly needs from:
- settled funding;
- evolving pre-settlement funding;
- mark/index relationship;
- basis/premium;
- open interest if later sourced;
- liquidation/order-flow data if later sourced.

Distinguish:
- essential for first trader;
- useful later;
- attractive but not defensible yet.

Do not demand new data unless the professional process actually requires it.

### 8. Scenario formation and prediction semantics

Define what a “scenario” should mean operationally.

The trader should not merely produce a direction.

Consider whether a scenario needs:
- state/condition;
- expected path or behavior;
- horizon;
- relevant levels;
- confirmation;
- invalidation;
- expiry;
- competing alternative;
- qualitative uncertainty.

Decide what belongs in `semantic.v2`.

### 9. Trade decision semantics

Define exactly when the reasoning layer can transition from market understanding to:
- LONG;
- SHORT;
- NO_TRADE.

The decision should be conditional on more than directional belief.

Define professional actionability concepts such as:
- trigger;
- location;
- room;
- invalidation;
- target;
- expected horizon;
- evidence conflict;
- data uncertainty;
- estimated cost/execution relevance.

Do not include capital size or leverage.

### 10. Trade geometry

Clarify the semantics of:
- trigger / entry condition;
- entry zone vs exact price;
- invalidation;
- target(s);
- time expiry;
- thesis management after recommendation.

Distinguish:
- thesis invalidation;
- stop/exit guidance;
- target;
- profit-taking;
- “view changed” events.

We need semantics clear enough to validate later without pretending to manage the Owner's account.

### 11. NO_TRADE taxonomy

Design a useful NO_TRADE model.

Potential categories include:
- no edge / balanced;
- directional view but poor location;
- insufficient room;
- trigger not confirmed;
- conflict across horizons;
- data uncertainty/staleness;
- costs/execution dominate;
- volatility/liquidity unsuitable;
- thesis expired.

Decide what should be explicit versus internal.

### 12. Confidence / uncertainty

Decide whether v1 should expose:
- qualitative confidence;
- ordinal conviction;
- calibrated probability;
- scenario weights;
- no confidence score at all initially.

Do not use pseudo-probabilities without a validation route.

Explain how uncertainty should influence actionability.

### 13. Rule architecture

Recommend how the professional process should be represented in software:

- deterministic state machine;
- hierarchical rules;
- typed evidence graph;
- scoring with constrained semantics;
- probabilistic model;
- hybrid;
- another architecture.

The project does not allow runtime LLM trading decisions.

Avoid a flat weighted sum unless you can justify why it faithfully represents professional reasoning.

### 14. semantic.v2

Propose the minimum durable public semantic contract for the first real trader.

At least consider:

- MarketView;
- horizon-specific state;
- scenario;
- evidence references;
- uncertainty;
- recommendation;
- NO_TRADE reason(s);
- trigger;
- invalidation;
- target(s);
- expected horizon / expiry;
- recommendation lifecycle/update semantics;
- what changed;
- data-quality/knowledge-cutoff references.

Explicitly state what must **not** be in `semantic.v2`, especially:
- account balance;
- position sizing;
- leverage;
- margin;
- autonomous orders.

Do not freeze fields simply because the old synthetic semantic.v1 had them.

### 15. Validation design

Define how to validate the first trader scientifically.

We need to test both:

**A. behavioral fidelity**
- does software implement the professional concepts as intended?
- are states/scenarios/levels causally correct?
- do transitions occur for the intended reasons?

and

**B. economic usefulness**
- are directional expectations / scenarios / recommendations useful after realistic costs?
- does NO_TRADE improve selectivity?
- do triggers/invalidation/targets behave sensibly?

Avoid:
- isolated signal tournaments;
- repeated threshold mining;
- tuning on the test set;
- changing methodology after every failed trade.

Address:
- walk-forward / held-out periods;
- prospective live observation;
- ablations;
- regime robustness;
- calibration if probabilities are used;
- recommendation-level outcome definitions;
- how to evaluate MarketView separately from trade decision.

### 16. Research gaps before implementation

For every required missing concept, give a narrowly scoped research question.

Do not answer “read more books.”

Examples:
- “formalize causal S/R from source X into explicit zone lifecycle rules”;
- “determine whether pre-settlement funding contributes a distinct decision role beyond price/mark/index”;
- “establish a professional multi-timeframe process adaptable to 24/7 BTC.”

Rank gaps only by **dependency order / prerequisite relationship**, not by subjective importance score.

## Red-team requirements

Actively challenge:

- whether the current evidence families are enough;
- whether a 1m source base creates hidden path-dependence;
- whether using higher-timeframe bars derived from 1m is adequate;
- whether a deterministic professional trader risks becoming brittle;
- whether scenario logic can become unfalsifiable storytelling;
- whether support/resistance formalization is too subjective;
- whether “many professional lenses” creates disguised overfitting;
- whether the first trader should deliberately be narrower than the eventual product;
- whether BTC 24/7 trading invalidates assumptions imported from session-based markets.

Do not merely agree with the Director's framing.

## Deliverable

Write:

`strategic_reviews/ASTRA-SR-002-REVIEW.md`

Structure the review as:

1. Executive decision
2. What the first real trader should and should not be
3. Recommended reasoning architecture
4. Professional lenses: include now / defer / reject
5. Multi-timeframe and temporal design
6. Derived causal observation layer
7. Market structure / levels design
8. Scenario and prediction semantics
9. Trade-decision and NO_TRADE semantics
10. Trigger / invalidation / target / lifecycle semantics
11. Proposed `semantic.v2` shape
12. Required data additions, if any
13. Required targeted research before coding
14. Validation and falsification plan
15. Failure modes / red-team objections
16. Recommended implementation sequence after this review
17. Open decisions that genuinely require the Owner

Be concrete enough that the Director can turn the disposition into bounded research and implementation work packages.

Do not write implementation code.

Do not declare the project ready for real capital.
