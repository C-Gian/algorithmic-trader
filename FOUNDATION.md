# Algorithmic Trader — Foundation

Version: 1.0 accepted · 29 September 2026  
Authority: canonical product, architecture and research directive

## 1. Mandate and authority

Build a personal BTC-only utility that maintains an explicit, current understanding of the market and makes selective, risk-controlled paper trading decisions. The objective is to reproduce, as faithfully as practical, the market-reading and trade-decision process of an excellent professional trader. The project is not primarily an alpha-discovery, indicator-mining or UI project.

The Owner owns product intent and any future capital authorization. The Project & Research Director owns product translation, architecture, research direction, repository/workflow design, UX decisions, tasking, independent acceptance, validation strategy, interpretation of results and next actions. Codex and Claude Code are implementation executors. Astra is used for foundational redesigns and difficult scientific review. The Director does not perform hands-on implementation code.

Start application design from zero. Import only external professional knowledge and source metadata. Ignore every prescription from the legacy Trading Bot project, including old architectures, terminology, experiments, thresholds, conclusions, tasks, ADRs and workflows. Legacy references embedded inside source dossiers are not current instructions.

### Accepted product scope

- Asset: BTC only.
- Operational paper instrument: BTC perpetual futures.
- Permitted directional actions while flat: LONG, SHORT or NO_TRADE.
- While exposed, HOLD, REDUCE and EXIT are distinct from NO_TRADE.
- No leverage: intended exposure is capped at 1x account equity. The system must not depend on leveraged risk taking.
- One net BTC position at a time.
- Trading style: short-duration trading, generally minutes to hours; positions are not intended to remain open for days.
- Broader market horizons may be observed when useful for context even when the trade itself is short-lived.
- BTC spot may be observed as market context/reference; it is not the initial operational execution instrument.
- Single user, local-first browser application.
- Research and paper operation only. No real-money orders or capital without explicit Owner approval.

Instrument, venue, contract and quote/settlement semantics are explicit configuration. The Director will select the initial data/execution venue after checking current access, history and contract specifications. Venue selection does not block the operational shell.

## 2. Evidence baseline

The initial professional knowledge snapshot is repository commit `3bf9de0d88fd97360bff7a6517bbb61544f5db68`, containing twenty dossiers under `source_notes/`. The dossiers are the project's initial knowledge base and remain immutable source-study artifacts.

This foundation was reviewed against those dossiers. Their reported source coverage must remain distinct from our own verification. Material qualifications include: LIB-001 is partially reviewed because the source artifact contains damaged pages; LIB-014 and LIB-015 are secondary summaries rather than the full underlying papers; LIB-010 and LIB-011 are related datasets rather than independent confirmations; reconstructed external histories require version pinning.

The knowledge base is an input, not a closed universe. Coverage is comparatively weak for BTC-specific mechanisms, formal support/resistance, retracement/extension concepts and cyclical/temporal timing. If the intended trader genuinely needs a weakly covered concept, open a targeted knowledge-gap study before formalizing it. Do not exclude a necessary professional concept merely because the initial dossiers are incomplete, and do not expand literature without a concrete implementation/research need.

## 3. Professional reasoning model

Implement one stateful, deterministic trader whose reasoning sequence is:

**available observations → contextual market state → competing scenarios → conditional trade plans → independent risk and execution checks → action → observed response and reassessment**

Observation, interpretation and decision are distinct records. “Volume increased” is an observation; “participation supports continuation” is an interpretation; “enter after confirmation” is a conditional plan. Unobservable claims about hidden intent or institutional behavior must never be recorded as facts.

The market state may describe, where justified: structure, trend/persistence, momentum, volatility, location relative to causally identified levels, participation, liquidity, trustworthy order-flow context, temporal/cyclical context, derivatives context, external context and data quality. Every state item has a horizon and freshness. Different horizons may disagree without contradiction. Missing input is not neutral evidence.

Maintain a small set of competing scenarios such as continuation, balance/range persistence and transition/failure. These are hypotheses rather than exhaustive laws. Each scenario carries supporting and opposing observations, applicability conditions, expected behavior, expiry and observable invalidation.

Information has roles rather than equal votes. Structure/trend may organize direction and context; momentum may describe persistence or deterioration; levels/location may define geometry, obstacles and invalidation; participation may qualify price response; volatility may inform expected movement, uncertainty and risk; liquidity/flow may influence timing, executability and sometimes scenario updates. Temporal, derivatives and external context enter only with a sourced mechanism and point-in-time data.

Group equivalent transforms under their underlying concept. Multiple trend formulas cannot manufacture independent confirmation. Do not start with a universal weighted score, black-box regime router or LLM making runtime decisions. Begin with transparent state, scenarios and bounded rule tables. Explanations are rendered from structured evidence and state transitions, not invented after outcomes.

The MarketView is intentionally richer than the set of trade playbooks. The trader may understand a bearish, bullish, balanced or transitional market while still having no worthwhile trade.

## 4. Contracts and decision semantics

Every published state includes the instrument, simulation/market time, information cutoff, input references, engine/configuration versions and validity/freshness status.

`MarketView` contains horizon-specific state, scenario ordering, uncertainty, relevant levels, expected response and the observations that would change the view. Begin with explicitly qualitative confidence. A numeric score is not a probability. Publish probabilities, return estimates or intervals only after target definition and calibration evidence exist.

`TradePlan` contains scenario/thesis reference, direction, eligibility, trigger, invalidation, exit logic, expiry, size constraints and cost assumptions. A plan is not an order.

`Decision` records proposed action, permitted action, blocking reasons and current exposure. While flat, LONG, SHORT and NO_TRADE are legitimate outputs. While exposed, HOLD, REDUCE and EXIT are explicit management states. A directional market view does not require a trade.

Risk policy independently limits exposure, intended loss, accumulated loss and operational uncertainty. No confidence estimate can override hard limits. Exposure must not exceed 1x account equity in V1 paper operation. Before evidentiary paper operation, the Director freezes numeric simulation risk budgets and shutdown rules. Stop prices do not guarantee exact loss caps through discontinuous price moves.

Account, order and fill records distinguish desired exposure, approved quantity, submitted order, partial/full fill, rejection, cancellation, balance/collateral, position and realized/unrealized P&L. Perpetual-specific economics such as fees, funding and contract mark/index behavior must be explicitly modeled before real-market evidence is trusted. Missing economics or unsafe data can block new exposure without erasing the last valid market view.

## 5. Components and technical shape

Use a modular monolith:

- Python domain engine and backend.
- FastAPI application API.
- React/TypeScript web UI.
- PostgreSQL operational persistence.
- Immutable Parquet market/run artifacts.
- Docker Compose for the local application.

Share the same Python engine package between API-facing runtime, replay and worker processes. There must not be a second research implementation with different decision semantics.

Core responsibility boundaries:

| Component | Responsibility |
|---|---|
| Data adapters/catalog | Ingest, validate, timestamp, version and expose available observations. |
| Trader engine | Update observations, market state, scenarios and plans; no UI/database dependency. |
| Risk/account/execution | Enforce limits, manage orders/positions, simulate fills and reconcile economics. |
| Run worker | Own clocks, ordered event processing, durable jobs, checkpoints and recovery. |
| API/projections | Accept commands and expose snapshots, history, progress and artifacts. |
| Web application | Home, replay, runs and understandable inspection/control. |
| Evaluation | Score views, decisions, execution and economics from immutable records. |

Initially use PostgreSQL-backed jobs with leases/heartbeats and idempotent processing. Do not introduce Redis, a distributed broker or microservice fleet without a measured need. Keep a durable append-only decision/order journal plus checkpoints without imposing full event sourcing on every table. Use server-sent events for live UI updates with snapshot recovery.

The browser never owns a running job. Long runs belong to the application's worker. Optimize measured bottlenecks only; performance changes must preserve causal semantics.

## 6. One trader, different clocks

Real-time paper and historical replay use the identical engine, risk and accounting logic. Only the clock, event source and execution adapter differ. Simulation speed must not change decisions.

Track event time and availability time separately. Never backfill revised information into historical decisions. Define warm-up, tie ordering, gaps, duplicate events and late arrivals. Future outcomes enter evaluation only after they mature.

The product is intraday/short-duration, but do not freeze an arbitrary holding-period constant at foundation level. Exact market-view cadences, horizons and trade expiry rules belong to the first real-trader specification after the operational shell and data/execution layer exist. Broader context may be slower than the trade horizon.

Initial historical execution may be conservative bar-based simulation, but it must not pretend candle data provides queue/depth fidelity. No fill may occur from information unavailable at decision time. Passive touch does not automatically imply fill. Fee, spread, slippage, delay, funding and ambiguous within-bar ordering assumptions must be explicit and stressable. Higher-fidelity simulation is justified only by higher-fidelity data.

Persist inputs and versions so a recorded paper session can reproduce its pre-execution decisions in replay. Replay never mutates the original run.

## 7. Knowledge becomes behavior

Preserve supplied dossiers unchanged. Maintain a compact source registry and a concept catalog, not an indicator shopping list.

Each concept records: source/section, evidence type and coverage, mechanism, role, observable inputs, availability/horizon, scope limits, correlated concepts, formalization, examples/counterexamples, failure conditions and evidence status.

Keep separate statuses for:

- source-supported;
- formalized;
- behaviorally verified;
- economically evaluated.

None implies the next. A textbook's authority cannot establish BTC profitability.

Translate only concepts required by the current work package. Link every implemented professional rule to its concept provenance and every test to the behavior being checked. Preserve unresolved source disagreements.

## 8. Dummy application and long runs

The dummy trader is disposable infrastructure scaffolding. It implements the real contracts with scripted deterministic behavior and is visibly labeled DEMO. It must exercise bullish, bearish, balanced/uncertain views; LONG, SHORT and NO_TRADE; plan activation; HOLD/REDUCE/EXIT; rejection; missing data and failure. Dummy returns/confidence are never research evidence.

Home should eventually show the BTC chart, current market view and changes, scenarios, permitted action and reasons, position/risk, data freshness and runtime health. Replay should be the same trader experience at historical time with play/pause/step/speed and event inspection. Runs must expose launch, cancel, status, phase, progress, elapsed time, heartbeat, failure explanation and resume where supported. ETA is shown only when defensibly estimable.

Jobs survive browser closure. Worker failure becomes explicit recoverable/failed state with no silent duplicate accounting events. Each run produces a manifest, structured view/decision/order/fill records, equity series, validation results and a concise report. The UI and Director/executors read the same artifacts. Raw logs remain secondary debugging material.

## 9. Development sequence

1. Foundation and workflow.
2. Complete operational shell with deterministic dummy trader.
3. Data and execution readiness for BTC perpetual paper operation.
4. First coherent professional trader.
5. Integrated development and validation.
6. Frozen prospective paper evidence.
7. Any future real-capital discussion only after explicit Owner authorization.

Do not build all possible professional lenses before completing one coherent end-to-end trader. Add another playbook or information source only to resolve a documented limitation or required capability.

The operational/dummy shell remains the first implementation milestone. There is no concrete reason from the Foundation review to change this order.

## 10. Validation without indicator mining

Use three distinct questions:

1. Does the software implement the intended professional process?
2. Does the market assessment contain useful information?
3. Does the selective trading policy produce useful net outcomes?

Develop on declared development data and a case library containing favorable, adverse, ambiguous and no-opportunity episodes. Include synthetic cases for causal and operational invariants. Mask future outcomes while assessing historical reasoning. These cases test process fidelity, not profitability.

Before a research run, record the question, mechanism, changed behavior, bounded alternatives, data exposure, metrics, falsification conditions and stopping rule. Retain unsuccessful and abandoned trials. A coding bug may be fixed immediately; one losing trade is not by itself a reason to redesign a model.

Permit source-grounded development and limited calibration, while keeping protected evaluation materially less adaptive. Once evaluation results influence redesign, that interval becomes exposed evidence and cannot independently certify the successor. Prospective paper evidence remains a stronger evidence class.

Evaluate market views at scheduled timestamps including NO_TRADE periods. Evaluate trade policy separately using net expectancy, returns, drawdown/time underwater, turnover, exposure, cost/funding sensitivity, tails, concentration and predefined missed/avoided-opportunity diagnostics. Compare compatible baselines without turning baselines into the objective.

Use chronological checks, overlap-aware safeguards where necessary, dependence-aware uncertainty, regime slices, cost/delay stress and nearby-parameter sensitivity. Many overlapping forecasts are not independent observations.

Ablate a component only against its claimed role in the complete trader. A liquidity gate does not need to be profitable as a standalone strategy. DSR/PBO and related methods are diagnostics when their assumptions fit; they are never universal pass scores or optimization targets.

Promotion requires causal correctness, intended behavior, operational reliability and criteria fixed before protected evaluation. “Insufficient evidence” is a valid result. Separate risk suspension from scientific conclusion that a mechanism has died.

## 11. Minimal repository and working state

Use only what current work needs:

- `FOUNDATION.md`: this accepted directive; sole architectural/governance authority.
- `README.md`: startup, operation and repository navigation.
- `AGENTS.md`: reading order, executable checks, clean-room boundary and executor limits.
- `STATE.md`: accepted commit, milestone, active task, blockers and next action.
- `source_notes/`: immutable professional source dossiers.
- `knowledge/registry.yaml` and later `knowledge/concepts/`.
- `tasks/`: bounded work-package briefs and dispositions.
- `src/`, `web/`, `tests/`, `infra/` as implementation begins.
- `research/` when research cases/data splits/trial ledger become necessary.

Keep large market data and run artifacts outside Git in durable volumes with immutable IDs/hashes; keep manifests and retrieval references in the product. Pin dependencies, datasets, configurations and random seeds when they become executable inputs. CI verifies contracts, causal invariants and the runnable smoke path.

Do not create overlapping mission documents or an empty governance bureaucracy.

## 12. Director–executor workflow

The Director issues one bounded task containing objective, base commit, authorized scope, referenced contracts/concepts, acceptance criteria, prohibited changes and expected evidence.

One executor owns implementation on a branch. A second executor may independently review consequential engine/data/risk changes when explicitly tasked. Executors do not choose product direction, redesign research, or weaken acceptance criteria to make work pass.

Executors report the exact commit, actual checks/results, artifacts and unresolved issues. A self-reported PASS is insufficient. The Director inspects the diff and evidence, independently checks material assumptions, requests correction where necessary, and merges only accepted work. `STATE.md` and task disposition are updated with acceptance.

Escalate to the Owner only for product intent, material scope/cost, UX preference that meaningfully changes the product, or any capital authorization.

Hours-scale work belongs to the application worker once available, not a hidden agent shell.

## 13. Explicitly outside initial product scope

- real-money orders or capital;
- leverage above 1x exposure;
- assets other than BTC;
- multiple simultaneous portfolio positions;
- HFT/market making/institutional smart routing;
- pretending order-book reconstruction from candles;
- autonomous strategy self-modification;
- online weight optimization;
- unrestricted parameter sweeps;
- LLM runtime trading decisions;
- unsourced cyclical or retracement rules;
- multi-user SaaS;
- distributed compute infrastructure.

Perpetual futures paper execution and SHORT are explicitly inside scope. Their market mechanics must be modeled before economic evidence is trusted.

## 14. First work package after acceptance

**WP-001: Repository bootstrap and one observable dummy run.**

Preserve the dossiers. Add minimal project instructions/state, provenance registry, pinned toolchain, CI and the first semantic contracts. Implement one synthetic deterministic BTC-perpetual stream, one scripted dummy trader, a minimal risk/account skeleton, durable job execution, artifact persistence and a thin Home/Run interface. This is infrastructure, not the real trader.

Acceptance requires:

1. One documented startup command opens the local application.
2. The Owner can start a synthetic replay from the UI and see market/simulation time, dummy MarketView, action/reason and progress.
3. The deterministic fixture demonstrates at least LONG, SHORT and NO_TRADE and one position-management transition.
4. Closing/reopening the browser preserves job state/results.
5. A controlled worker interruption produces visible recovery/failure behavior without duplicate accounting events.
6. Repeating the same pinned run reproduces the semantic event trace; replay speed does not alter decisions.
7. Completion and cancellation leave inspectable manifests and structured artifacts through the UI/API.
8. CI checks core contracts/accounting and an end-to-end smoke path.
9. No real professional trading rule, BTC profitability claim, optimizer, real market connectivity or live-order connectivity enters WP-001.

After WP-001 acceptance, the next work package continues the operational shell and failure paths before real trader intelligence begins.

## Revision history

- 2026-09-29 — v1.0 accepted after Owner decisions: BTC perpetual paper execution; LONG/SHORT/NO_TRADE; no leverage (1x exposure cap); short-duration minutes-to-hours trading; broader horizons permitted for context.
