# Foundation v3 — Integrated Adviser Delivery Plan

Status: ACTIVE DIRECTOR PLAN  
Date: 2026-09-30  
Authority: FOUNDATION.md v3.0, STATE.md, Owner realignment

## 1. Product interpretation

Algorithmic Trader is a **BTC trading adviser**.

The product is successful only if it can do both:

1. maintain an understandable professional market view; and
2. produce usable, persistent LONG/SHORT calls when the integrated evidence supports one.

The product is not:
- an autonomous execution/account engine;
- a collection of independent indicators;
- a pullback-only research project;
- a permanent NO_TRADE machine;
- a runtime LLM trader.

The Owner decides whether to follow a call and independently chooses capital, quantity, leverage, margin and actual orders.

## 2. Long-lived reasoning path

The intended product path is:

**available evidence
→ causal observable state
→ derived professional observations
→ integrated context / MarketView
→ explicit scenarios
→ candidate plan
→ actionability
→ persistent call or NO_TRADE
→ reassessment / call lifecycle**

These stages have different responsibilities.

### Evidence / observable state

Facts only:
- traded price/volume;
- mark/index;
- settled funding;
- future approved event/news/derivative/liquidity evidence;
- source provenance, freshness, gaps and uncertainty.

No directional interpretation belongs here.

### Derived professional observations

Reusable causal measurements, not final opinions.

Likely examples:
- completed multi-horizon bars;
- returns/ranges/realized variability;
- causal structure/swing/leg descriptions;
- distance/location relative to reference areas;
- movement progression/reaction measurements;
- participation/volume descriptors;
- timing/event descriptors once their causal definitions exist.

The exact derived contract will be versioned when the first adviser method is implemented.

### Integrated MarketView

The MarketView answers:
- what behavior is occurring;
- direction/structure if one is defensible;
- relevant horizon;
- important location/levels;
- supporting evidence;
- counterevidence;
- missing/unknown context;
- plausible alternatives;
- what would materially change the view.

A MarketView may be directional while the call remains NO_TRADE.

### Scenario

A scenario is a falsifiable conditional expectation:
- current applicability;
- activation/confirmation condition;
- expected behavior;
- horizon;
- relevant destination/obstacle;
- disconfirmation/invalidation;
- expiry;
- alternative scenario.

Do not publish pseudo-probabilities until a calibrated event universe exists.

### Candidate plan

A candidate plan translates a scenario into potential trade geometry:
- direction;
- trigger/entry condition or area;
- thesis invalidation;
- target/destination;
- expected holding horizon;
- remaining room;
- reason the opportunity exists now.

This is still not a call until actionability is satisfied.

### Actionability

Actionability answers whether a human can still use the candidate now.

It considers:
- entry still available;
- remaining room;
- data freshness;
- unresolved conflicts;
- volatility/liquidity conditions;
- declared execution/cost uncertainty;
- event/timing restrictions where implemented.

Actionability does not choose capital, size or leverage.

### Persistent call

A call is a durable versioned advisory object:
- LONG or SHORT;
- stable identity;
- current entry-validity state;
- trigger/entry area;
- target(s);
- thesis invalidation and stop/exit guidance;
- expected holding horizon/range;
- issue/update times and causal knowledge cutoff;
- reasons/counterevidence/limitations;
- what changed from the prior version.

Call lifecycle is separate from any human position:
- WATCH/PENDING;
- ENTRY_AVAILABLE;
- ENTRY_CLOSED;
- THESIS_ONGOING;
- TARGET_REACHED;
- INVALIDATED;
- EXPIRED;
- UNASSESSABLE.

“Hold/exit if following this call” never asserts that the Owner actually entered.

## 3. Required professional lenses

The first integrated adviser specification must explicitly address every role below.

A lens may be:
- ACTIVE;
- CONTEXT_ONLY;
- UNKNOWN/UNAVAILABLE;
- DEFERRED_WITH_REASON.

Missing optional evidence must not silently become neutral confirmation.

### 3.1 Structure / trend / location — REQUIRED CORE

Questions:
- where is price within relevant structure?
- is directional progression present, absent or contested?
- which reference areas matter now?
- what would structurally damage the current interpretation?

Inputs:
- causal traded-price history;
- derived multi-horizon structure/reference areas.

RP-001 contributes useful causal lessons:
- extremum time != confirmation time;
- no hindsight pivots;
- explicit same-bar ambiguity;
- structure can be UNKNOWN;
- old numeric swing/zone conventions are not production defaults.

### 3.2 Momentum / movement quality — REQUIRED CORE

Question:
- is movement progressing, weakening, accelerating or reacting?

Use a small number of non-redundant price-path measurements.
Do not create RSI/MACD/etc. as independent votes merely because they are familiar indicators.

RP-001 move/reaction measurements may be reused selectively, but the adviser is not restricted to one pullback pattern.

### 3.3 Participation / volume — INCLUDED WITH LIMITED AUTHORITY

Question:
- does venue-local traded participation materially support the interpretation of the move?

Current evidence is OKX-local volume, not global BTC participation.

Initial role:
- descriptive/contextual;
- may strengthen or weaken a scenario only through an explicitly defined role;
- cannot independently generate direction.

No “institutional buying”, absorption or aggressor-intent claims from candle volume alone.

### 3.4 Volatility — REQUIRED CONTEXT / SCALE

Questions:
- what movement scale is normal now?
- what amount of room/horizon is plausible?
- is the current movement outside the method's supported scale?

Volatility does not supply direction by itself.

Use one transparent causal scale in the first integrated implementation.
Do not run a volatility-estimator tournament.

### 3.5 Timing / cyclical analysis — EXPLICIT SOURCE CLOSURE REQUIRED

Foundation v3 makes timing/cyclical assessment an Owner priority.

Current corpus supports broad regime/cycle caution but does not yet provide a sufficiently explicit causal BTC timing rule.

Therefore the first adviser design must expose a timing/cycle lens state rather than silently omit it.

Until the bounded source question is closed:
- status = UNAVAILABLE_METHOD;
- it does not support or veto a call;
- UI explains that no source-grounded causal timing rule is active.

Bounded closure question:
> Which professional cycle/timing concept can be translated into causal observables available for BTC without using future-confirmed turning points or fixed periodicity by assumption, and what exact decision role would it have?

A future implementation may conclude:
- ACTIVE;
- CONTEXT_ONLY; or
- NOT_JUSTIFIED.

It must not invent a proprietary cycle theory.

### 3.6 News / economic / political event context — EXPLICIT DATA/POLICY CLOSURE REQUIRED

Professional practitioner material supports catalyst/news context as potentially important, but the current M3 data layer has no historical as-known event/news store.

Therefore:
- event/news coverage is explicit;
- “coverage unknown” != “no news”;
- current articles can never be inserted into historical decisions.

Initial adviser behavior before an event source is integrated:
- event lens = COVERAGE_UNAVAILABLE;
- the call/report carries that limitation;
- event context cannot silently veto or confirm.

Bounded closure questions:
1. Which deterministic event types matter enough for the first BTC adviser?
2. Which source provides scheduled time and as-known publication content/revisions?
3. What exact role can event context play: timing restriction, scenario catalyst, interpretation of response, or all three?

### 3.7 Derivatives / liquidity / execution context — ACTIVE FACTS, LIMITED INTERPRETATION

Current usable evidence:
- mark price;
- index price;
- settled funding;
- exchange/instrument metadata;
- declared execution-cost assumptions later used for evaluation.

Initial roles:
- mark/index divergence or data quality can expose venue/reference anomalies;
- settled funding is factual carry context, not a directional vote;
- execution/cost uncertainty can affect actionability;
- no inference from funding to crowding/direction without crypto-specific evidence.

Potential later additions only if the integrated method needs them:
- quotes/spread/depth;
- OI;
- liquidations;
- spot/cross-venue basis.

## 4. Information-combination rule

Do not count evidence pieces.

The adviser uses typed dependencies:

- structure defines applicable directional hypotheses;
- movement quality describes whether that structure is progressing or deteriorating;
- location determines whether the opportunity geometry is usable;
- volatility defines scale/room;
- participation can modify the quality of an interpretation when its role is defined;
- timing/event context can restrict or reframe a scenario when available;
- derivatives/liquidity can constrain actionability or expose distinct context.

Correlated observations from the same price path are dependencies, not independent confirmations.

The first implementation should prefer:
- explicit predicates/states;
- hierarchical rules;
- small state machines;
- typed blockers/limitations.

A numerical score is allowed only when its meaning is explicit and it is not a disguised vote count.

## 5. RP-001 reuse policy

Reuse:
- causal-completeness discipline;
- known-at semantics;
- explicit UNKNOWN;
- same-bar ambiguity handling;
- separation MarketView / opportunity / recommendation / thesis;
- persistent immutable history/revisions;
- masked-development-case discipline.

Do not inherit automatically:
- pullback-only scope;
- 1h/5m/1m permanence;
- 120-minute expiry;
- DC-01..DC-31 numeric values;
- single-leg impulse requirement;
- epoch high-water lockout;
- geometry floor;
- unverified 5–16 bps cost envelope.

Continuation-after-pullback remains one candidate setup family that may later be retained in revised form.

## 6. Product surfaces

### Home

Eventually shows:
- live BTC chart;
- current integrated MarketView;
- lens cards with current result/freshness/role;
- dominant scenario/horizon;
- active call or clear reason no call exists;
- entry validity, target, stop/invalidation, expected duration;
- material-change timeline;
- Copy analysis for chat.

### Backtest / Evaluation Workbench

One Owner-facing workflow for:
- selecting reusable historical evidence;
- choosing an adviser/model version;
- launching a durable run;
- seeing candles and reasoning evolve;
- pause/resume/cancel/speed;
- progress/elapsed/ETA;
- inspecting calls and outcomes;
- Copy report for chat;
- Markdown + structured export.

Before the adviser exists, this page may run **observation-only evaluation** and must clearly state that call/outcome metrics are unavailable.

Do not create a separate hidden CLI backtest framework later.

### Data / Corpus

The product owns a reusable fixed historical corpus.

Target from Foundation:
- 2025-09-01 inclusive;
- 2026-09-01 exclusive;
- UTC.

Acquisition is chunked, verified and reusable.

Initial bootstrap chunk:
- **2025-09-01T00:00Z → 2025-10-01T00:00Z**.

Reason:
- first chronological complete month of the target;
- selected without looking at future trader outcomes;
- within the accepted 31-day acquisition limit;
- useful to prove corpus/evaluation operation.

This first chunk is engineering/development evidence only.

Before any advisory economic evaluation, the Director must register development/protected windows for the full corpus.

## 7. Local intermittent operation

The system must support:
- app starts after being off;
- local cached history remains reusable;
- bounded incremental catch-up;
- reconstructed historical state is visibly distinct from live receipt evidence;
- current MarketView is recomputed after catch-up;
- expired historical calls are not re-alerted as new;
- a reconstructed opportunity becomes actionable only after a fresh current reassessment.

No H24 PC requirement.

## 8. Evaluation principles

The Owner launches substantial runs from the application.

Executors may run:
- unit/integration/causality tests;
- tiny deterministic fixtures;
- short bounded engineering smoke runs.

Executors do not run:
- full historical profitability evaluation;
- parameter sweeps;
- long research jobs.

A substantial run must end with a compact report containing at least:
- run/model/data/config identity;
- actual coverage/completion;
- call count and calls/week once adviser exists;
- entry-validity duration;
- longest no-call interval;
- candidate funnel/rejection reasons;
- unsupported/missing-context time;
- wins/losses/expired/unresolved/ambiguous outcomes;
- target/stop/duration information;
- normalized gross/net results under declared assumptions;
- baseline comparison;
- limitations;
- conclusion and next diagnostic question.

Win rate alone is not acceptance.

Systematic NO_TRADE is explicitly diagnosed.

## 9. Delivery sequence

### WP-008 — Owner Evaluation Workbench + Corpus Bootstrap

Build the reusable Owner workflow first:
- durable corpus acquisition/preparation from the app;
- initial Sep-2025 monthly chunk preset;
- corpus inventory/verification/size visibility;
- dedicated Backtest/Evaluation page;
- launch real observation replay from that workflow;
- visual progress/candles;
- compact Copy report + Markdown/JSON;
- report honestly says adviser/call metrics unavailable;
- READY FOR OWNER DATA PREP / observation evaluation handoff.

This is not another generic infrastructure project: it is the exact workflow the real adviser will later reuse.

### MP-001 — Integrated Adviser Method Closure

A bounded Director/source task, not open-ended research.

It will freeze:
- initial horizon roles;
- concrete structure/location method;
- movement/momentum/participation/volatility roles;
- cycle/timing disposition;
- event/news disposition;
- initial candidate-plan family or small complementary set;
- actionability policy;
- persistent call lifecycle;
- the minimal advisory semantic.v2 contract.

Only specific source questions identified above may expand the corpus.

### WP-009 — Adviser Core v0 + semantic.v2

Implement:
- causal derived observations;
- integrated MarketView/scenarios;
- candidate plan/actionability;
- persistent call lifecycle;
- Home integration;
- historical evaluation integration into WP-008.

No account sizing/execution.

### Owner Backtest A

Executor stops at READY FOR OWNER BACKTEST.

Owner runs a registered development preset in the app and copies the report.

Director diagnoses:
- coverage;
- call frequency;
- no-call reasons;
- correctness;
- practical entry duration;
- outcomes/cost sensitivity;
- visible reasoning quality.

### WP-010+ — Bounded diagnosed improvements

Only versioned changes tied to observed failure modes.

Then:
- protected evaluation;
- manageable prospective live sessions;
- no real-capital authorization without explicit Owner approval.

## 10. Immediate active package

The active implementation package is WP-008.

No trader semantics are authorized by WP-008.

The purpose is to make the next real adviser immediately testable by the Owner through the product rather than through agent shells.
