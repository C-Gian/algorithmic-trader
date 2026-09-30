> **HISTORICAL SCOPE NOTICE — 30 September 2026.** FOUNDATION.md v3.0 implements the Owner's direct clarification and supersedes inconsistent scope/workflow instructions below. This document is retained as historical/advisory evidence. Its former ACCEPTED/READY/HOLD status is not current authorization. In particular, the mandatory pullback-only path, blanket cycle/news deferrals and RP-001 closure gate are no longer project direction. Reuse compatible findings only through the current task; preserve original evidence and failed cases. See the current FOUNDATION.md, STATE.md and task.md.

# RP-001 — First Professional Trader Formalization Research

Status: READY  
Owner: Project & Research Director  
Executor: Claude Code as bounded research/documentation executor  
Authority: `FOUNDATION.md`, `STATE.md`, `strategic_reviews/SR-002-DIRECTOR-DISPOSITION.md`

## Purpose

Close the scientific/formalization gate between:
- accepted M3 causal observable state; and
- any future production professional-trader code.

The candidate process is fixed for this package:

**directional context → move/reaction assessment → conditional continuation opportunity → trigger → actionability → LONG/SHORT/NO_TRADE → reassessment**

This package does **not** test whether that process makes money.

It asks whether the process can be translated into explicit, causal, internally coherent, auditable behavior without hindsight or hidden executor discretion.

## Hard boundaries

Do not implement production trader logic.

Do not create:
- `semantic.v2`;
- derived-observation production code;
- indicators;
- levels engine;
- live recommendations;
- backtests/P&L optimization;
- parameter sweeps;
- account/risk/execution logic.

Do not modify `source_notes/`.

Do not import anything from the legacy Trading Bot project.

## Read first

Read in full:

1. `FOUNDATION.md`
2. `STATE.md`
3. `AGENTS.md`
4. `strategic_reviews/ASTRA-SR-002-REVIEW.md`
5. `strategic_reviews/SR-002-DIRECTOR-DISPOSITION.md`
6. `knowledge/registry.yaml`
7. relevant professional dossiers, especially:
   - LIB-002 Expected Returns
   - LIB-003 Quantitative Trading
   - LIB-004 Systematic Trading
   - LIB-005 Market Wizards: The Next Generation
   - LIB-008 Which Trend Is Your Friend?
   - LIB-012 Advances in Financial Machine Learning
   - LIB-020 Trading and Exchanges
8. accepted market/feed/observe contracts only as needed to preserve causal semantics.

## Targeted external primary/practitioner sources

SR-002 introduced the following targeted external sources:

- Adam Grimes — `Fundamental Trading Patterns`
  - https://www.adamhgrimes.com/fundamental-trading-patterns/
- Adam Grimes — `One step ahead…`
  - https://www.adamhgrimes.com/one-step-ahead/
- Carol Osler — `Support for Resistance: Technical Analysis and Intraday Exchange Rates`
  - https://www.newyorkfed.org/research/epr/00v06n2/0007osle.html
- Carol Osler — `Currency Orders and Exchange-Rate Dynamics: Explaining the Success of Technical Analysis`
  - https://www.newyorkfed.org/research/staff_reports/sr125.html

Use only what you can actually retrieve/read.

If your environment cannot retrieve an external source:
- do not fabricate its contents;
- use the Astra review only as a pointer/secondary summary;
- mark the primary-source verification as blocked.

Register external sources separately from the immutable dossier registry.

## Initial translation configuration

For this bounded research package use:

- context sampling role: completed 1h bars;
- setup sampling role: completed 5m bars;
- trigger/reassessment role: completed 1m bars.

These are predeclared research conventions, not product invariants.

Do not run a timeframe tournament.

A change is allowed only if the process cannot be expressed coherently/causally with this configuration, and:
- the failure is demonstrated before performance outcomes are inspected;
- the Director is informed;
- no alternative grid search occurs.

Use traded price as the structural/trigger/invalidation/target price role.

Mark/index/funding remain separate factual context and must not silently satisfy traded-price predicates.

## Deliverables

Create:

### 1. `research/first_trader/RP-001A-PROCESS-TRANSLATION.md`

Define observable distinctions for:
- directional progress;
- impulse/move;
- controlled reaction/pullback;
- overlap/indecision;
- opposing initiative;
- structural damage/failure;
- continuation-supporting response.

For each concept include:
- source support;
- project adaptation;
- observable inputs;
- what it explicitly does not imply;
- positive example;
- negative/counterexample;
- unknown/ambiguous case.

Separate:
- source-supported statement;
- proposed formalization;
- unresolved design convention.

Never use hidden-intent claims such as smart money, trapped participants or institutional accumulation as facts.

### 2. `research/first_trader/RP-001B-CAUSAL-STRUCTURE-LEVELS.md`

Specify a candidate causal structure process covering:

- higher-timeframe aggregation completeness;
- swing candidate;
- swing confirmation;
- extremum time vs confirmation time;
- directional leg;
- initialization/warmup;
- frozen variability scale;
- threshold/tolerance semantics;
- same-bar path ambiguity;
- setup pullback boundary;
- horizontal reference area;
- zone creation;
- interaction;
- revision;
- weakening;
- invalidation;
- ageing/retirement;
- nearest defensible opposing destination.

The directional-change swing method is a candidate, not a required conclusion.

If a simpler process preserves the intended professional distinctions better, explain it.

No hindsight pivots.

No adaptive zone widening to save a thesis.

No automatic resistance→support role flip.

### 3. `research/first_trader/RP-001C-ADVISORY-POLICY.md`

Define the complete first long process and its exact short mirror.

Specify:

- context applicability;
- setup detection;
- opportunity WATCHING/ARMED semantics;
- trigger predicate;
- trigger confirmation;
- entry interval;
- entry-location-lost rule;
- local invalidation;
- primary target selection precedence;
- scenario activation;
- expected response;
- setup expiry;
- entry validity expiry;
- thesis/forecast expiry;
- recommendation issue/withdrawal;
- view/recommendation revision;
- entry lifecycle;
- thesis assessment lifecycle;
- new setup vs re-entry;
- no automatic reversal.

Define a candidate public NO_TRADE taxonomy.

Every mandatory predicate must have:
- satisfied;
- contradicted;
- unknown/unassessable.

No numeric confidence.

No free-text-only trigger or invalidation semantics.

### 4. `research/first_trader/RP-001D-ACTIONABILITY-ASSUMPTIONS.md`

Define initial normalized assumptions for later evaluation only:

- decision-known time;
- plausible human response delay as a small declared range;
- entry observation reference;
- fee assumptions;
- spread/slippage treatment;
- cost unresolved state;
- cost dominates state;
- ambiguous OHLC path treatment;
- when quote evidence becomes required.

Do not use:
- Owner capital;
- leverage;
- quantity;
- personal fee tier unless explicitly provided later.

Do not optimize assumptions for outcome.

### 5. `research/first_trader/RP-001E-EVALUATION-REGISTRATION.md`

Pre-register the eventual evaluation before economic results are used to alter the method.

Define:
- evaluation unit / unique opportunity episode;
- candidate funnel;
- MarketView audit cadence;
- scenario outcome states;
- recommendation outcome states;
- primary forecast horizon candidate and justification;
- earlier response checkpoint;
- target-before-invalidation treatment;
- terminal signed movement;
- MFE/MAE-like descriptive excursions;
- missed entry;
- ambiguity/censoring;
- simple controls;
- role-level ablations;
- development/protected/prospective separation;
- dependence handling;
- falsification/stopping conditions.

Do not compute profitability in RP-001.

### 6. `research/first_trader/cases/CASE-REGISTER.yaml`

Build a small bounded causal case library.

Required case categories:
- clean continuation;
- failed recovery;
- deep reversal;
- overlapping/indecisive reaction;
- late confirmation / entry lost;
- insufficient room due to obstacle;
- target/invalidation order ambiguity;
- missing/stale required evidence.

Both long and short must be represented across the pack.

Each case record must include:
- case id;
- REAL or SYNTHETIC;
- source reference;
- visible-prefix cutoff;
- allowed evidence at cutoff;
- hidden outcome reference;
- intended concept/question;
- expected classification under the proposed formalization;
- ambiguity/data-quality notes.

### 7. Case files

Create:
- `research/first_trader/cases/prefixes/`
- `research/first_trader/cases/outcomes/`

Keep prefix and outcome separate.

The Director must be able to inspect the prefix without reading its future outcome.

Small normalized excerpts may be committed if they are:
- bounded;
- provenance-linked;
- non-sensitive;
- not substitutes for the immutable source evidence.

Large source data stays outside Git.

### 8. `knowledge/external_registry.yaml`

Create a separate registry for the targeted external sources actually used.

For each source record:
- id;
- title;
- author;
- URL;
- retrieval date;
- source type;
- which RP-001 question it informs;
- verification status;
- transfer limitations.

Do not modify the original `knowledge/registry.yaml` source-study snapshot unless the Director later decides to consolidate registries.

## Real-case requirement

RP-001 must not claim completion using only invented diagrams.

Use synthetic cases for predicate mechanics where useful.

Before RP-001 acceptance, include a bounded set of real BTC cases from immutable accepted evidence if such evidence is accessible in the local environment.

If adequate real evidence is not available:
- do not fabricate it;
- produce `research/first_trader/REAL-CASE-DATA-REQUIREMENT.md`;
- specify exactly what dataset/coverage is needed through the existing app/data workflow;
- mark RP-001 as incomplete on the real-case gate.

Do not make the Owner copy raw logs into chat.

## Case selection anti-bias rules

Case selection is for **concept translation**, not profitability estimation.

Therefore:
- no P&L sorting;
- no selecting only pretty textbook winners;
- include adverse and ambiguous cases deliberately;
- record why each case was selected;
- mask the suffix while labeling the prefix;
- do not revise the rule after opening the outcome without recording the revision.

If multiple plausible formalizations remain, preserve at most a small predeclared contrast.

No threshold grid search.

## Numbers and design conventions

Any numeric value not source-supported must be explicitly tagged:

`DESIGN_CONVENTION`

Examples:
- swing reversal threshold;
- volatility window;
- zone tolerance;
- setup expiry;
- entry expiry;
- forecast deadline;
- geometry floor.

For every design convention include:
- why it exists;
- what behavioral distinction it is meant to preserve;
- plausible alternative(s);
- sensitivity concern.

Do not choose it by later P&L.

## Outcome masking workflow

For each REAL case:

1. establish the immutable source identity;
2. choose a prefix cutoff without using the later outcome to define the rule;
3. export only causally available evidence/state needed for the research artifact;
4. label the prefix under the proposed definitions;
5. freeze the classification/reason;
6. only then inspect/reveal the outcome file;
7. record whether the case:
   - supports the formalization;
   - exposes ambiguity;
   - falsifies/narrows a definition;
   - reveals a missing-data requirement.

Do not rewrite the original prefix label after the reveal.
A later revised rule gets a new version.

## What RP-001 may decide

RP-001 may:
- narrow concepts;
- reject the directional-change swing candidate;
- decide a required predicate is not operationalizable;
- conclude quote evidence is necessary;
- conclude 1h/5m/1m is behaviorally inadequate before outcome evaluation;
- reject the entire first playbook as not faithfully formalizable.

Negative conclusions are valid research outcomes.

## What RP-001 may NOT decide

RP-001 may not conclude:
- the method is profitable;
- a Sharpe/expectancy target is met;
- real capital is justified;
- one parameter is optimal;
- another playbook should be added because this one had bad outcomes.

## Checks

This is primarily a research/documentation task.

At minimum:
- validate YAML files parse;
- verify all repository links/source references used in artifacts exist;
- verify no `source_notes/` files changed;
- verify no production code/contracts/schema baselines changed;
- run any lightweight existing checks needed to prove no accidental code change.

No need to run long application E2E if no production code changed.

## Completion report

Report:

- base/final SHA;
- files produced;
- sources read directly vs only through existing dossiers/Astra summary;
- external sources successfully verified vs blocked;
- exact initial design conventions proposed;
- whether any of 1h/5m/1m had to change and why;
- number/type of synthetic and real cases;
- how outcome masking was enforced;
- unresolved ambiguities;
- whether A, B, C, D and E each satisfy their closure condition;
- whether real-case gate is complete;
- whether you recommend:
  - ACCEPT RP-001;
  - ACCEPT WITH A SPECIFIC FOLLOW-UP;
  - HOLD / REVISE;
  - REJECT candidate process.

Do not implement trader code.

Final acceptance belongs to the Project & Research Director.
