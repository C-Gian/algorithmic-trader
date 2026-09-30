# Algorithmic Trader — Foundation

Version: 2.0 accepted · 30 September 2026  
Authority: canonical product, architecture and research directive

## 1. Mandate and authority

Build a personal BTC-only **market-analysis and trade-decision system** that reproduces, as faithfully as practical, the market-reading and trade-decision process of an excellent professional trader.

The product continuously understands the market, maintains an explicit current view, states what it expects to happen, and decides whether a professional trade opportunity exists.

The core product is **decision support for the human trader**, not autonomous portfolio management or autonomous order execution.

A useful output should answer questions such as:

- What is the market doing and why?
- What are the plausible scenarios?
- What is most likely or most relevant next?
- Is there a trade worth taking now?
- LONG, SHORT or NO_TRADE?
- What must happen before entry?
- Where is the thesis invalidated?
- What price areas or targets are relevant?
- What time horizon is the idea about?
- What evidence supports or contradicts the view?
- What would change the system's mind?

The Owner remains the human trader. The Owner decides independently whether to act and, if so:

- how much capital to use;
- position size;
- leverage;
- margin/account settings;
- actual order placement;
- personal portfolio and capital-risk management.

The system must not present those human capital-allocation choices as part of its professional market opinion.

The Owner owns product intent and any future real-capital authorization. The Project & Research Director owns product translation, architecture, research direction, repository/workflow design, UX decisions, tasking, independent acceptance, validation strategy, interpretation of results and next actions. Codex and Claude Code are implementation executors. Astra is used for foundational redesigns and difficult scientific review. The Director does not perform hands-on implementation code.

Start application design from zero. Import only external professional knowledge and source metadata. Ignore every prescription from the legacy Trading Bot project, including old architectures, terminology, experiments, thresholds, conclusions, tasks, ADRs and workflows. Legacy references embedded inside source dossiers are not current instructions.

### Accepted product scope

- Asset: BTC only.
- Primary analyzed/trade-reference instrument: BTC perpetual futures.
- BTC spot and other defensible BTC-related sources may be observed as context/reference when justified.
- Primary flat-state recommendation: LONG, SHORT or NO_TRADE.
- An active recommended trade/thesis may later be updated with HOLD, REDUCE/TAKE-PARTIAL, EXIT or INVALIDATED semantics where the professional methodology requires them.
- Intended opportunity horizon: generally minutes to hours, not days.
- Broader market horizons may be observed when useful for context.
- Single user, local-first browser application.
- Research, replay and advisory/paper observation only.
- No autonomous real-money orders.
- No autonomous leverage selection, position sizing, collateral allocation or account-level portfolio management.

The product may model execution timing/costs **only to evaluate whether a recommendation was realistically actionable and economically meaningful**. That research harness must not become the product's capital-allocation policy.

## 2. Evidence baseline

The initial professional knowledge snapshot is repository commit `3bf9de0d88fd97360bff7a6517bbb61544f5db68`, containing twenty dossiers under `source_notes/`. The dossiers are the project's initial knowledge base and remain immutable source-study artifacts.

This foundation was reviewed against those dossiers. Their reported source coverage must remain distinct from our own verification. Material qualifications include: LIB-001 is partially reviewed because the source artifact contains damaged pages; LIB-014 and LIB-015 are secondary summaries rather than the full underlying papers; LIB-010 and LIB-011 are related datasets rather than independent confirmations; reconstructed external histories require version pinning.

The knowledge base is an input, not a closed universe. If the intended trader genuinely needs a weakly covered concept, open a targeted knowledge-gap study before formalizing it. Do not exclude a necessary professional concept merely because the initial dossiers are incomplete, and do not expand literature without a concrete implementation/research need.

## 3. Professional reasoning model

Implement one stateful, deterministic professional reasoning system whose sequence is:

**available evidence → observable market state → professional interpretation / MarketView → competing scenarios → conditional trade opportunity / plan → recommendation → observed response and reassessment**

Observation, interpretation, prediction and recommendation are distinct records.

Examples:

- “1m traded volume increased” is an observation.
- “Participation supports continuation” is an interpretation.
- “The primary scenario is continuation toward X over the next 30–90 minutes” is a market prediction/scenario.
- “LONG only if price confirms Y; invalid below Z; targets A/B” is a conditional trade recommendation.
- “NO_TRADE despite bearish view because expected room is too small” is a legitimate decision.

Unobservable claims about hidden intent or institutional behavior must never be recorded as facts.

The observable market state may describe, where justified: structure, trend/persistence, momentum, volatility, location relative to causally identified levels, participation, liquidity, trustworthy order-flow context, temporal context, derivatives context, external context and data quality. Every state item has a horizon, provenance and freshness. Different horizons may disagree without contradiction. Missing input is not neutral evidence.

Maintain competing scenarios rather than one unconditional forecast. Each scenario should be explicit enough to evaluate later: supporting and opposing evidence, expected behavior, relevant horizon, expiry and observable invalidation/change conditions.

Information has roles rather than equal votes. Multiple transforms of the same underlying information cannot manufacture independent confirmation. Do not begin with a flat vote, universal weighted score, black-box regime router or LLM making runtime decisions.

The MarketView is intentionally richer than the set of trade opportunities. The system may understand the market well while still returning NO_TRADE.

## 4. Product decision semantics

Every published state/recommendation includes:

- instrument/market context;
- market/simulation time;
- information cutoff;
- input/dependency references;
- engine/configuration versions;
- validity/freshness;
- source/model limitations relevant to the conclusion.

### MarketView

`MarketView` represents the current professional interpretation of the market. It should eventually contain, as justified by the trader specification:

- horizon-specific state;
- competing scenarios;
- directional/structural bias where appropriate;
- relevant levels/locations;
- uncertainty;
- expected response;
- what would confirm or contradict the current interpretation;
- what would change the view.

Begin with qualitative confidence. A numeric score is not a probability. Publish probabilities, return estimates or calibrated intervals only after the prediction target and calibration evidence exist.

### TradeOpportunity / TradePlan

A trade opportunity/plan represents a professional market opportunity, not account sizing.

It may contain:

- thesis/scenario reference;
- LONG or SHORT direction;
- eligibility;
- trigger / entry condition or entry zone;
- invalidation condition/price;
- target(s) or expected destination/room;
- expected time horizon / expiry;
- management logic if part of the professional method;
- reasons to abstain;
- execution/cost viability assumptions when relevant.

It must **not** require the product to choose:

- account percentage;
- leverage;
- contract quantity;
- collateral allocation;
- user-specific portfolio risk.

### Recommendation / Decision

While no recommendation is active, LONG, SHORT and NO_TRADE are legitimate outputs.

A directional MarketView does not require a trade recommendation.

If an opportunity is active, the system may update its recommendation when the thesis evolves, for example HOLD, TAKE_PARTIAL/REDUCE, EXIT or INVALIDATED, but these states refer to the **trade thesis/recommendation**, not to autonomous account management.

A recommendation must remain understandable even if the Owner chooses not to execute it.

## 5. Causal market architecture

Use a modular monolith:

- Python domain/reasoning engine and backend.
- FastAPI application API.
- React/TypeScript web UI.
- PostgreSQL operational persistence.
- Immutable Parquet market/run artifacts.
- Docker Compose for the local application.

The long-lived market boundary is:

**immutable market evidence → causal availability feed / event clock → centrally owned observable market state → professional reasoning → MarketView / scenarios / trade recommendation**

The trader does not read raw datasets directly.

Heterogeneous source events update one observable state. At a decision point, the professional reasoning layer receives a point-in-time snapshot plus the causally available changes/history it is allowed to know.

This preserves asynchronous sources without forcing them into one flat synchronized feature row and without making each reasoning module reimplement ordering, gaps, revisions and freshness.

Core responsibility boundaries:

| Component | Responsibility |
|---|---|
| Data adapters/catalog | Ingest, validate, timestamp, version and preserve market evidence. |
| Causal feed / availability clock | Deliver source evidence according to recorded or explicitly modeled availability. |
| Observable market state | Maintain typed family-specific current state, history, freshness, coverage, missingness and descriptive measurements. |
| Professional reasoning | Interpret observable state into MarketView, scenarios, predictions and trade opportunities. |
| Recommendation policy | Decide LONG / SHORT / NO_TRADE and manage the life of an active recommendation/thesis. |
| Evaluation harness | Evaluate prediction quality, opportunity quality and realistic trade outcomes without choosing the Owner's capital allocation. |
| Run worker | Own clocks, ordered event processing, durable jobs, checkpoints and recovery. |
| API/projections | Accept commands and expose snapshots, history, progress and artifacts. |
| Web application | Home, replay, runs, data and understandable inspection/control. |

PostgreSQL-backed jobs, leases, heartbeats, idempotent processing, immutable artifacts and replay controls from the accepted shell remain valid infrastructure.

## 6. Causality, clocks and price roles

Historical replay and live observation must share the same market-state/reasoning semantics. Only the source/clock adapter changes. Replay speed must not change the view or recommendation.

Track at least:

- market/event/economic time;
- availability/knowledge time;
- retrieval/recording/provenance time;
- deterministic processing order.

Nothing with an availability time after a decision's information cutoff may influence that decision.

Use actual recorded receipt order/timing where available. Historical data with unknown publication latency uses an explicit versioned availability policy; modeled timing is never presented as measured fact.

Traded price, mark price, index price and funding information retain explicit identities and must never be silently substituted.

General roles:

- **traded price / OHLC / typed volumes:** primary evidence of what traded; market reading; later trade-outcome reference where defensible;
- **mark price:** derivative valuation/reference information and potentially derivatives context; not an execution price;
- **index price:** external/reference benchmark and possible basis context; not an execution price;
- **funding:** event/carry context; predictive interpretation requires separate evidence and historically available inputs.

Missing/stale/invalid information invalidates only dependent conclusions where possible. It must not automatically erase unrelated valid parts of the MarketView.

Invalid rows remain evidence for audit but cannot silently enter valid observable state.

Higher-timeframe context derived from lower-timeframe data must preserve causal completion. A forming higher-timeframe bar must never masquerade as completed history.

## 7. Trade-outcome and execution evaluation

The product does not execute trades for the Owner, but recommendations must eventually be tested against realistic actionability.

The evaluation harness may model:

- when a recommendation became known;
- when an order could first have been submitted/executed;
- plausible entry/exit reference prices;
- fees, spread/slippage and delay;
- gaps and ambiguous intra-bar ordering;
- whether targets/invalidation were reached;
- normalized return / price movement / R-like outcomes;
- sensitivity to reasonable execution assumptions.

It must not model the Owner's personal account as if it were part of the algorithm.

No recommendation may receive a historical fill from a price timestamped before the recommendation was known.

One-minute OHLC cannot prove queue position, depth, passive fills or exact intrabar paths. When the available evidence cannot determine an execution outcome, preserve the ambiguity or use explicitly labeled alternative/stress scenarios rather than inventing precision.

A normalized standard trade unit may be used for evaluation where needed. It is an evaluation convention, not a capital recommendation.

Perpetual fees/funding/contract mechanics may be modeled when they materially affect the economic viability of a recommendation. They are trade-outcome costs, not account-sizing rules.

## 8. Knowledge becomes behavior

Preserve supplied dossiers unchanged. Maintain a compact source registry and concept catalog, not an indicator shopping list.

Each concept records: source/section, evidence type and coverage, mechanism, role, observable inputs, availability/horizon, scope limits, correlated concepts, formalization, examples/counterexamples, failure conditions and evidence status.

Keep separate statuses for:

- source-supported;
- formalized;
- behaviorally verified;
- informationally evaluated;
- economically evaluated where applicable.

None implies the next. A textbook's authority cannot establish BTC predictive value or trade usefulness.

Translate only concepts required by the current professional process. Link implemented professional rules to provenance and tests to intended behavior. Preserve unresolved source disagreements.

## 9. Dummy shell and Owner experience

The existing dummy trader/account/risk/execution pieces are accepted **infrastructure scaffolding only**. They must not define the real product's capital-management semantics.

Home should eventually show:

- live/current BTC market view;
- what changed;
- scenarios and expected behavior;
- prediction/horizon;
- LONG / SHORT / NO_TRADE recommendation;
- conditional entry/trigger or entry zone;
- invalidation;
- targets / expected room;
- reasons and opposing evidence;
- what would change the view;
- active recommendation/thesis status where relevant;
- data freshness/limitations;
- runtime health.

It should not require the product to tell the Owner how much money, leverage or collateral to use.

Replay should be the same analyst/trader experience moving rapidly through historical time with play/pause/step/speed and event inspection.

Long runs remain application-owned and durable. Raw logs remain secondary.

## 10. Development sequence

1. Foundation and workflow.
2. Operational shell with deterministic dummy trader.
3. Trustworthy market evidence and causal observable-state/replay substrate.
4. First coherent professional market-reading/trade-decision specification.
5. First real professional trader implementation.
6. Integrated development and validation of market views, predictions and trade recommendations.
7. Prospective advisory/paper-observation evidence.
8. Any future real-capital or automation discussion only after explicit Owner authorization.

Do not build all possible professional lenses before completing one coherent end-to-end trader.

Add another playbook or information source only to resolve a documented limitation or required capability.

## 11. Validation without indicator mining

Use separate questions:

1. Does the software implement the intended professional process?
2. Does the MarketView/prediction contain useful information?
3. Does the recommendation policy identify worthwhile LONG/SHORT opportunities and abstain appropriately?
4. Are recommended opportunities still worthwhile under realistic execution/cost assumptions?

Do not evaluate success by account growth from an arbitrary portfolio-sizing scheme.

Useful evaluation may include:

- direction and scenario outcome;
- target/invalidation behavior;
- expected-vs-observed response;
- time-to-resolution;
- excursion/adverse excursion;
- recommendation hit/quality metrics once formally defined;
- abstention quality;
- normalized trade return / expectancy;
- execution/cost sensitivity;
- concentration and regime slices;
- missed/avoided-opportunity diagnostics.

Develop on declared development data and bounded case libraries with favorable, adverse, ambiguous and no-opportunity episodes. Mask future outcomes during reasoning review.

Before a research run, record the question, mechanism, changed behavior, bounded alternatives, data exposure, metrics, falsification conditions and stopping rule. Retain unsuccessful and abandoned trials.

Protected evaluation and prospective evidence remain distinct from development evidence.

## 12. Repository and workflow

Use:

- `FOUNDATION.md`: canonical product, architecture and research directive.
- `README.md`: startup, operation and repository navigation.
- `AGENTS.md`: reading order, executable checks, clean-room boundary and executor limits.
- `STATE.md`: accepted state, milestone, active task, blockers and next action.
- `source_notes/`: immutable professional source dossiers.
- `knowledge/registry.yaml` and `knowledge/concepts/` as needed.
- `strategic_reviews/`: major advisory reviews and Director dispositions.
- `task.md`: exactly one active executor handoff.
- `src/`, `web/`, `tests/` and later `research/` as needed.

Keep large market data and run artifacts outside Git in durable volumes with immutable IDs/hashes.

The Director maintains exactly one active implementation handoff. Executors implement only the active task, test, commit and push normally. The Director independently reviews remote diff, CI and evidence before acceptance.

Escalate to the Owner for product intent, material scope/cost, UX preferences that materially change the product, or capital/automation authorization.

## 13. Explicitly outside initial product scope

- autonomous real-money orders;
- autonomous position sizing;
- autonomous leverage choice;
- autonomous collateral/margin allocation;
- account-level portfolio optimization;
- assets other than BTC;
- HFT / market making / institutional smart routing;
- pretending order-book reconstruction from candles;
- autonomous strategy self-modification;
- online weight optimization;
- unrestricted parameter sweeps;
- runtime LLM trading decisions;
- unsourced cyclical or retracement rules;
- multi-user SaaS;
- distributed compute infrastructure.

SHORT recommendations and BTC perpetual analysis are explicitly inside scope.

A future user may manually execute recommendations with any capital/leverage choices they independently make. Those choices are outside the algorithm's recommendation semantics.

## 14. Accepted-work interpretation

WP-001, WP-002 and WP-003 remain accepted within their original bounded purposes.

In particular:

- the durable application shell, worker, checkpoints, replay controls, UI and artifact infrastructure remain valuable;
- `algotrader.semantic.v1` remains a frozen synthetic-shell baseline, not the final professional trader contract;
- the dummy account/risk/order/fill path remains DEMO scaffolding and must not constrain the real trader;
- `algotrader.marketdata.v1` remains the accepted immutable evidence baseline for the initial OKX data;
- no accepted dummy P&L, account quantity, 1x rule or execution placeholder is project direction for the real trader.

## Revision history

- 2026-09-30 — **v2.0 product-scope correction after Owner clarification and SR-001 reviews.** The product is a professional BTC market-analysis and trade-decision system. Capital allocation, leverage, account sizing and autonomous execution are explicitly Owner/human responsibilities. Accepted shell/account scaffolding remains DEMO only. Architecture refocused on causal market evidence, observable state, prediction, trade recommendation and normalized outcome evaluation.
- 2026-09-29 — v1.2 workflow clarification: executors commit and push completed bounded tasks; Owner relays the report; Director reviews the remote repository/CI and rewrites `task.md`.
- 2026-09-29 — v1.1 workflow clarification: one active `task.md`; Owner handled pull/push; superseded by v1.2.
- 2026-09-29 — v1.0 initial accepted Foundation; superseded where inconsistent with v2.0 product clarification.
