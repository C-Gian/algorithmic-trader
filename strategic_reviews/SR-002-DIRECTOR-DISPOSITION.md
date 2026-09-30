# SR-002 — Director Disposition

Status: ACCEPTED WITH MODIFICATIONS  
Date: 2026-09-30  
Authority: Project & Research Director  
Input review: `strategic_reviews/ASTRA-SR-002-REVIEW.md`

## Executive disposition

Astra's core proposal is accepted:

> the first real professional trader candidate will be a **stateful price-action analyst with one selective continuation-after-pullback recommendation method**, implemented symmetrically for long and short, while continuously preserving a richer MarketView than the set of currently actionable trades.

This is accepted as the **first candidate professional process**, not as:
- a claim of BTC profitability;
- the complete eventual professional trader;
- a universal theory of market behavior;
- a mandate to add every lens discussed in the literature.

The first implementation path therefore remains narrow:

**causal derived observations → structural/context interpretation → move/reaction assessment → scenario → conditional opportunity → actionability gates → LONG / SHORT / NO_TRADE → reassessment**

Professional-rule implementation remains **HOLD** until the bounded formalization research defined below closes.

## Why this candidate is accepted

The candidate matches the project's core objective better than an indicator-first architecture because it integrates:

- directional context;
- reaction/correction behavior;
- location;
- trigger timing;
- invalidation;
- target/destination;
- remaining room;
- evidence conflict;
- abstention.

It also naturally preserves the required distinction between:
- understanding the market;
- forming a prediction/scenario;
- deciding whether an opportunity is currently actionable.

The external check used by Astra supports pullback/continuation as an established practitioner process family, while also making clear that its exact formalization is not a BTC-proven rule. The New York Fed support/resistance work is relevant as evidence that level-related effects can exist in some FX settings, but it is not accepted as evidence that our future BTC zones possess predictive power.

## Accepted architectural decisions

### 1. Derived causal observation layer

Accept.

Create a separate, versioned derived-observation layer between:
- accepted observable market state; and
- professional interpretation.

It must contain reproducible causal descriptions, not opaque interpretations.

Candidate objects include:
- completed higher-timeframe bars;
- returns/ranges/overlap/durations;
- one trailing variability scale;
- causal swing candidates/confirmations;
- directional legs;
- level/zone objects;
- impulse/reaction measurements;
- geometry measurements.

The exact public contract is not frozen yet.

Do not put these derivations into `feed.v1`. They are downstream of observable state.

Do not put interpretive labels such as `bullish_pressure` or a universal `trend_score` into the derived layer.

### 2. Reasoning architecture

Accept.

Use:
- typed dependencies;
- explicit evidence references;
- hierarchical rules;
- small state machines;
- explicit satisfied / contradicted / unknown states.

Reject:
- flat indicator voting;
- universal weighted conviction scores;
- compensating numerically for missing mandatory evidence;
- runtime LLM decisions.

The dependency graph records logical/evidential relationships, not economic causation.

### 3. One recommendation playbook first

Accept.

The first actionable playbook is:
- continuation after a controlled pullback/reaction inside a causally supported directional context.

Failed continuation remains:
- a competing/failure scenario;
- an invalidation/update reason.

It does **not** automatically become a reversal entry.

Range-fading, breakout chasing, reversal trading, liquidation prediction, cycle forecasting and additional playbooks remain deferred.

### 4. MarketView remains broader than the playbook

Accept.

The analyst may describe:
- directional progress;
- correction;
- overlap;
- transition/failure evidence;
- competing scenarios;

even when the active playbook cannot recommend a trade.

A possible reversal can therefore coexist with:
- preferred reversal interpretation; and
- NO_TRADE because reversal entry logic is outside the first method.

### 5. Structure and levels

Accept with scope limitation.

The first process requires:
- causal swing/leg structure;
- pullback boundaries;
- nearby previously observed horizontal reference areas;
- a local invalidation;
- a defensible first destination.

It does **not** require a universal support/resistance engine.

Start with horizontal reference areas only.

Defer:
- trendlines;
- profile nodes;
- round-number hierarchy;
- Fibonacci/retracement ratios;
- multiple competing level generators.

A directional-change swing extractor is accepted only as a **candidate measurement procedure for formalization research**, not yet as production behavior.

### 6. Trend / momentum / volatility

Accept the role separation.

Trend/persistence:
- describes directional progression and durability.

Momentum:
- initially means move/reaction measurements such as displacement, elapsed time and follow-through;
- no separate RSI/MACD voting module.

Volatility:
- provides scale/context and geometry normalization;
- is not directional.

Use one transparent trailing variability method in the first research specification.

Do not compare a large family of volatility estimators.

### 7. Volume / participation

Modify Astra's proposal.

Venue-local traded volume may remain available as descriptive evidence, but it is **not required in the first decision path** unless process-translation research identifies a source-grounded, non-redundant role.

Therefore:
- no volume confirmation gate;
- no participation score;
- no inferred aggressor intent;
- no claim of global BTC participation from one venue's candles.

We prefer omission over decorative sophistication.

### 8. Derivatives context

Accept deferral.

For the first price-based method:
- mark, index and settled funding remain factual context;
- none is a mandatory directional confirmation;
- evolving funding, OI, liquidation data, spot/cross-venue and macro/news are deferred.

No new directional data family is required before formalizing the first process.

If later evidence shows that the selected process cannot make defensible actionability claims without quotes/spread data, add that evidence for the specific role only.

### 9. Scenario semantics

Accept.

A scenario is a timestamped, conditional, falsifiable claim about future observable behavior.

It must preserve:
- exact knowledge cutoff/cursor;
- structural applicability;
- activation condition;
- expected behavior;
- destination/obstacle;
- deadline;
- confirmation/disconfirmation;
- counterevidence;
- competing alternative;
- immutable revision history.

Distinguish:
- unconditional expectation now;
- conditional expectation if a future trigger occurs.

`NOT_ACTIVATED`, unresolved expiry and ambiguous outcomes must remain valid outcomes.

### 10. Recommendation semantics

Accept.

LONG / SHORT means:
- this professional method currently supports a new directional entry opportunity.

It does not mean:
- an order exists;
- a position exists;
- the Owner should use a certain size;
- leverage has been selected.

Before trigger confirmation:
- publish NO_TRADE;
- expose a watch direction / pending opportunity where useful.

After confirmation:
- recommendation remains valid only while entry geometry and expiry are still acceptable.

### 11. NO_TRADE taxonomy

Accept conceptually, do not freeze the exact enum yet.

Required public distinctions include at least:
- required data unavailable / warmup;
- no supported setup;
- context outside method;
- contested scenario;
- trigger pending;
- entry location lost;
- insufficient room / geometry;
- cost/delay unresolved or dominating;
- expired / invalidated;
- existing thesis but no new entry.

The exact public enum is frozen only after the complete advisory policy research closes.

Detailed predicate failures remain internally inspectable.

### 12. Trigger / invalidation / target lifecycle

Accept.

Initially prefer:
- one primary trigger;
- one local invalidation;
- one primary target/destination;
- one active primary actionable thesis per BTC instrument.

Do not add:
- discretionary trailing;
- multi-target ladders;
- repeated re-entry;
- automatic reversal.

Recommendation geometry is immutable once issued.
A revision creates a new version rather than silently widening or moving boundaries.

Separate:
- entry/opportunity lifecycle; and
- thesis-assessment lifecycle.

HOLD-like advisory states must refer to the thesis, never imply that the Owner actually has a position.

### 13. Confidence / uncertainty

Accept.

Do not expose:
- numeric confidence;
- pseudo-probabilities;
- normalized scenario weights;
- A/B/C trade grades.

Initial uncertainty is qualitative and typed:
- supported;
- contested;
- insufficient;
plus explicit missing dependencies/counterevidence.

Probabilities require a later fixed event universe and calibration evidence.

## Decisions accepted only as research conventions, not architecture

The following Astra proposals are useful candidates but are **not yet frozen production semantics**:

- 1h context;
- 5m setup;
- 1m trigger;
- 120-minute primary forecast horizon;
- exact response checkpoint;
- setup-expiry deadline;
- entry-validity deadline;
- swing reversal threshold;
- zone width;
- geometry floor;
- exact trigger boundary;
- exact variability window.

### Timeframe policy for the next research package

Use **1h / 5m / 1m as the initial predeclared translation configuration**.

This avoids a timeframe tournament while giving the case study a concrete language.

However, these scales may be changed **once before outcome evaluation** if causal/process-fidelity work shows that they cannot express the intended professional distinctions.

Any such change must:
- be justified by behavioral/causal failure;
- occur before economic results are inspected;
- be recorded explicitly;
- not trigger a multi-timeframe optimization search.

They are not a permanent product invariant.

### Forecast-horizon policy

Treat 120 minutes as a **candidate primary evaluation horizon**, not an accepted forecast constant.

The formalization package must decide:
- when a forecast starts;
- which earlier response checkpoint exists;
- when a setup expires;
- when an entry opportunity expires;
- when a thesis becomes unresolved/expired.

These deadlines must be fixed before performance evaluation.

## Professional time / timers

Accept Astra's concern and make it explicit.

The professional runtime will eventually need deterministic timer/deadline events in addition to market-source deliveries.

Timers are:
- not fabricated market evidence;
- not part of `feed.v1`;
- part of the professional reasoning/runtime clock.

At a deadline:
1. admit only evidence actually known by the recorded dispatch boundary;
2. preserve exact cursor/order;
3. evaluate expiry/response predicates;
4. do not retrospectively include later same-timestamp arrivals.

Replay/live parity must cover timer behavior.

Do not implement this until the policy definitions below are accepted.

## semantic.v2 disposition

Do **not** create `semantic.v2` yet.

Astra's proposed object family is accepted as the working design direction:

- common causal envelope;
- DerivedObservationRef;
- HorizonState;
- MarketView;
- Level/Zone reference;
- Scenario;
- Opportunity;
- Recommendation;
- AdvisoryUpdate;
- Uncertainty/Blocker.

But the concrete schema waits for formalization research A–C.

The first v2 predicate vocabulary must be small and typed.
Free text cannot be the only machine-readable trigger/invalidation/target semantics.

Do not carry forward semantic.v1 account/order/fill/risk coupling.

Explicitly excluded from required trader semantics:
- balance/equity;
- quantity/contracts;
- position fraction;
- leverage;
- margin/collateral;
- personal liquidation level;
- autonomous order intent/order/fill;
- inferred human position.

Evaluation outcomes and hypothetical fills belong in a separate later evaluation contract.

## Validation disposition

Accept Astra's four-claim separation:

1. causal correctness;
2. professional-process fidelity;
3. forecast information;
4. recommendation usefulness.

No one layer proves the next.

The first integrated evaluation must:
- use unique opportunity episodes;
- retain NO_TRADE/candidate funnel;
- use predeclared delays/cost assumptions;
- preserve ambiguous/censored outcomes;
- compare to simple persistence/base-rate controls;
- keep development, protected evaluation and prospective advisory evidence separate;
- avoid repeated threshold/timeframe mining;
- include role-level ablations only after the integrated method exists.

An always-NO_TRADE system is not successful merely because it avoids losses.

## Targeted research gate before coding

Astra's dependency chain A–E is accepted, with one consolidation:

### RP-001A — Process translation
Define what distinguishes:
- directional progress;
- controlled reaction;
- overlap/indecision;
- opposing initiative;
- structural failure.

Use:
- existing professional dossiers;
- the specific external practitioner/source material cited in SR-002;
- explicit source-vs-project-adaptation labels.

No hidden-intent language.

### RP-001B — Causal structure / reference areas
Define and test on masked causal prefixes:
- swing candidate vs confirmation;
- directional legs;
- frozen scale;
- initialization;
- same-bar ambiguity;
- pullback boundary;
- horizontal reference-zone lifecycle;
- local invalidation;
- nearest defensible opposing destination.

This phase may reject/narrow the directional-change candidate.

### RP-001C — Complete advisory policy
Freeze one coherent policy:
- context applicability;
- setup arming;
- trigger construction;
- entry interval;
- entry lost;
- invalidation;
- target precedence;
- scenario activation;
- response checkpoint;
- setup expiry;
- entry expiry;
- forecast expiry;
- recommendation revision;
- no re-entry policy for v1;
- public NO_TRADE reasons.

Every required predicate needs:
- positive case;
- negative case;
- unknown/ambiguous case.

### RP-001D — Initial actionability assumptions
Before economic claims:
- define a bounded human-response-delay model;
- define fee/spread/slippage assumptions or unresolved ranges;
- decide whether public quote evidence is required;
- define when cost/delay viability is unresolved vs dominating.

No Owner capital inputs.

### RP-001E — Evaluation registration
Before outcome-led iteration:
- define episode universe;
- audit cadence;
- scenario/recommendation outcomes;
- primary metrics;
- controls;
- protected periods;
- ambiguity/censoring;
- ablations;
- stopping/falsification rule.

## Case-library requirement

Create a small outcome-masked causal translation set containing both long and short examples of:

- clean continuation;
- failed recovery;
- deep reversal;
- overlapping/indecisive reaction;
- late confirmation / entry lost;
- insufficient room due to obstacle;
- target/invalidation ordering ambiguity;
- missing or stale required evidence.

The Director must be able to inspect the visible prefix without future outcome leakage.

Synthetic examples may be used to prove predicate mechanics.
They do not prove BTC edge.

At least some later cases must use real immutable BTC evidence before professional-rule implementation is accepted.

## External-source disposition

Astra's cited external additions are accepted as **targeted research pointers**, not as new project truths.

The Director independently confirmed:
- Grimes explicitly presents pullbacks as trend-entry/continuation structures with several entry styles;
- the New York Fed Osler work reports predictive effects for support/resistance levels in specific historical FX samples and firms.

These sources do not establish:
- BTC profitability;
- our future swing thresholds;
- our zone definitions;
- our trigger;
- our timeframes.

Any durable project research artifact must keep these limitations attached.

## Explicitly deferred

Do not research or implement yet:

- reversal playbook;
- range fade;
- breakout-chasing playbook;
- cycle prediction;
- Fibonacci ratios;
- VWAP bands;
- profile;
- oscillator divergence;
- trendline engine;
- OI/liquidation directional models;
- predictive funding rule;
- spot/cross-venue context;
- news/macroeconomic model;
- order-book reconstruction;
- ML/online optimization.

A future addition requires a documented limitation of the accepted first process.

## Next project action

The next task is **research/formalization, not trader implementation**.

Produce the bounded RP-001 artifacts and case specification.

No production derived-observation engine, no `semantic.v2`, and no recommendation code is authorized until the Director accepts RP-001A–C.

RP-001D/E may be developed in parallel where definitions permit, but economic evaluation may not begin until they are frozen.

## Final Director decision

SR-002 is **ACCEPTED WITH MODIFICATIONS**.

The project adopts the narrow continuation-after-pullback process as its first professional trader candidate.

The review does **not** authorize production trader code.

The next acceptance gate is the complete, causal and falsifiable formalization of that process.
