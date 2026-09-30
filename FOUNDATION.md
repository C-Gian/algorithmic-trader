# Algorithmic Trader — Foundation

Version: **3.0 — Owner-directed product realignment, 30 September 2026**  
Authority: canonical product, architecture and delivery directive. Implements the Owner's direct clarification of 30 September, superseding inconsistent earlier review/disposition/research instructions.

## 1. Product and authority

Build a personal BTC trading adviser: an application that reads the market as an excellent professional trader would, explains what it expects, and issues usable LONG/SHORT calls with entry conditions, targets, stop/exit guidance and expected holding horizon. The Owner manually decides whether to follow a call and handles capital, size, leverage, margin and all actual orders.

The main feature is the **trade call**. Continuous market opinion and visible professional observations make the adviser understandable and inspectable. Continuous analysis does not mean trading every second.

This is product engineering and professional-knowledge translation. Existing professional methods are the starting point. Targeted study resolves concrete translation/data questions; it must not become indefinite alpha discovery, isolated-signal tournaments or a reason never to deliver an integrated application. Human practice does not automatically provide executable rules or guarantee our BTC translation works. A recalled 6–7 winning calls out of 10 describes the desired experience, not a promised or verified win rate. Evaluate frequency, practicality, gains/losses and costs together.

Roles:
- Owner: product intent, practical constraints and material spending/automation choices; launches substantial backtests in the app.
- Project Director: ordinary product/technical choices, integrated method synthesis, bounded tasking, review and diagnosis. Do not ask the Owner to select indicators, thresholds or economic theories.
- Codex/Claude: implement the active task, run bounded engineering checks, commit/push and report.
- Astra: strategic challenge and difficult architecture/method review. A review cannot override the Owner.

Authority: current Owner instruction → this Foundation → current STATE/task → compatible specifications explicitly activated by the current task. Former ACCEPTED/HOLD labels in historical documents are not independent authorization. This Owner instruction authorizes documentation realignment.

Clean-room remains mandatory: never import/reconstruct the legacy Trading Bot architecture, terminology, experiments, thresholds, results or conclusions. Legacy prescriptions embedded in dossiers are not instructions. Preserve source_notes/ unchanged.

## 2. Scope and intermittent local operation

- BTC only initially; accepted primary reference remains public OKX BTC-USDT-SWAP. Spot/external sources may inform context.
- Human-usable opportunities, generally minutes to hours; broader context is allowed. No permanent 120-minute forecast or 1h/5m/1m architecture.
- Local-first, single-user browser app. The Owner starts it after work; use persisted history plus bounded incremental catch-up.
- No mandatory always-on PC, daily multi-hour collection campaign or VPS prerequisite. Later hosting is optional.
- While running and connected, observe and update automatically. While stopped, no monitoring/alerts are promised.
- On restart, identify the gap, catch up obtainable history, re-evaluate and distinguish reconstruction from live observations. Never claim historical backfill has measured receipt timing or complete missed-news coverage.
- Do not re-alert expired calls as new. A reconstructed idea requires a fresh current assessment before becoming actionable.
- Manageable live observation sessions supplement historical evaluation; missing H24 evidence limits dependent claims, not all progress indefinitely.

Excluded: autonomous orders, account allocation/sizing/leverage, personal liquidation management, HFT, multi-user SaaS, distributed compute, runtime LLM trading decisions and automatic strategy self-modification. Existing dummy account machinery remains DEMO only.

## 3. Integrated professional reasoning

The long-lived path remains:

**available evidence → causal observable state → derived observations → context/MarketView → scenarios → candidate plan → actionability → call and reassessment**

Observation, interpretation, prediction and action are distinct. Relevant information works together through explicit roles/dependencies, not equal bullish/bearish votes. Structure can invalidate a plan, an upcoming event can restrict timing, and volatility can alter expected room without supplying direction. Any numerical weighting needs a defined meaning; correlated transformations do not create independent confirmation.

Specify the whole first process before splitting implementation into components. Components need not independently make money. Unit/causality tests are valid; isolated-indicator profitability rankings are not the project plan.

### Required coverage decisions

The first integrated specification must explicitly address each role, its sources, causal inputs, decision effect and limitations:

| Role | Question |
|---|---|
| Structure, trend, levels/location across useful horizons | Where are we, what behavior is occurring, and what would invalidate the interpretation? |
| Momentum, participation, volatility | Is movement progressing/weakening, how does its reaction behave, and what scale/room is plausible? |
| Timing and cyclical analysis | Is there a source-grounded phase/timing concept that changes the scenario or entry window? |
| News, economic/political events and market response | What known catalyst/event risk affects the BTC thesis, and how is price responding? |
| Derivatives, liquidity and execution context | What distinct evidence or practical restriction affects this opportunity? |

This does not require every tool or make every lens a mandatory gate. It forbids silently excluding cycles/news/other roles because a price-only prototype is easier. Cyclical analysis is an explicit Owner priority for source-based assessment. Do not assume one named proprietary method, fixed periodicity or future-confirmed cycle low. Define the concept and causal observables before giving it predictive authority. If knowledge is insufficient, identify the exact missing rule/data and bounded next step; do not invent certainty or declare the whole field irrelevant.

For events, distinguish schedules, publication/as-known content, revised values and observed price response. Current articles cannot enter past decisions. Deterministic typed event records and policies can support first integration; a news feed alone is not professional reasoning. Unknown coverage is visible, not “no news”.

The former continuation-after-pullback candidate is **one reusable candidate, not the mandated trader**. The Director may retain, revise or replace it and include a small complementary process for coherent coverage. The first version need not trade every regime; it must disclose its domain and demonstrate useful coverage. Do not implement every strategy at once or require pullbacks to succeed before assessing necessary context.

RP-001 findings remain useful development evidence. Its numerical conventions do not become production requirements automatically. Poor results require diagnosed translation/model changes and versioned evaluation, not arbitrary threshold loosening to fit a winner or abandonment of the product goal.

## 4. Market view and persistent call semantics

### Continuous view

Expose the current directional expectation with horizon, alternatives, levels, reasons, counterevidence and what would change it. UP/DOWN may use green/red arrows; BALANCED/UNCERTAIN/UNAVAILABLE must exist. Never force direction from missing evidence. Show age and scope.

A directional view can coexist with NO_TRADE. Targets are not calibrated expected returns. Initially use qualitative uncertainty; probabilities require a defined event and calibration evidence.

### Durable calls

A call is a durable versioned object, not a one-candle notification. It includes:
- stable ID, instrument, LONG/SHORT, thesis and model/config/evidence references;
- issue/update times, knowledge cutoff and freshness;
- trigger/entry area and whether **entry is still valid now**;
- thesis invalidation and concrete protective stop/exit guidance;
- target(s), remaining room, expected holding horizon/range;
- reassessment/deadline, early-exit and expiry conditions;
- plain-language reasons, uncertainties and cost/delay assumptions;
- what changed since the preceding version.

Entry remains available while the current opportunity is worthwhile, even after some original room is consumed. Do not expire it merely because the first signal instant passed. Close entry when price, room, time, data or thesis no longer supports it. Validity is a reassessed price/time/condition window, not an arbitrary notification TTL; method-specific hard deadlines need reasons.

Separate **watch/pending → entry available → entry closed** from **thesis ongoing → target/invalidated/expired/unassessable**. Preserve closed calls and subsequent guidance. “Hold/exit if following this call” does not assert a human position. Stops are guidance, not submitted orders or guaranteed fills. Revisions are explicit; original outcome criteria are never silently moved.

Automatically alert new actionable calls and material changes/withdrawals in-app, without repeating the same call every refresh. Manual reassessment may supplement this. Do not promise alerts while the local app is off.

## 5. Home: live control board

Home is the working decision cockpit:
1. Live BTC chart with relevant levels and call entry/target/stop areas.
2. Observation/lens cards: name, human meaning, current result, change/time, freshness, role in the conclusion and unavailable/deferred state. Update automatically in-page when results change.
3. Dominant right-hand panel on desktop: expected direction/horizon, then active call or why none exists. Entry validity, target, stop and duration must be immediately readable. Preserve priority on smaller screens.
4. Material-change timeline and **Copy analysis for chat**.

UI refresh follows actual source/analysis cadence. A completed-bar method need not pretend to recompute every tick. Label forming/completed inputs, connection health and age. Pending real capability stays PENDING; dummy output stays DEMO.

Explain what is expected, whether entry is still good and what invalidates it in plain language. Technical detail is inspectable, not the default screen.

## 6. Owner-operated visual backtests

Replay the same reasoning/call lifecycle using historical availability and a simulated clock. Future information is forbidden. Replay speed/rendering must not affect results.

The Owner launches substantial evaluations on a dedicated app page: fixed dataset/model, prepared period/preset, Start, pause/resume, cancel, speed and inspection. Show progressing candles, simulated time, current lens/view/call outputs, call/outcome markers, progress, elapsed time and measured ETA. Historical mode is unmistakable.

Decouple compute from animation: fast mode may sample visual frames while processing every required event and retaining the complete inspectable trace. Avoid ever-growing full-prefix reconstruction on every event. Checkpoint/recovery must remain practical.

Initial engineering budgets to measure, not claims about existing speed: smoke around one minute; routine comparison around 15 minutes; larger interactive run around one hour with upfront estimate/budget. If substantially longer, offer a shorter diagnostic preset and identify performance work; do not silently launch overnight work. Jobs must checkpoint/resume across local restarts.

### Executor handoff

Executors may run normal unit/integration/causality checks and short bounded engineering smoke runs. They must not launch full-dataset profitability evaluations, sweeps or long research jobs in an agent shell. At that boundary report **READY FOR OWNER BACKTEST**, exact app preset/config, expected time and question. The Owner starts it and copies the report; the Director diagnoses and assigns the next bounded change.

If launch/visualization/export is missing, build it first. Do not require the Owner to run Python, interpret terminal output or assemble screenshots.

### Copyable results

Every run, including interrupted/failed runs, provides **Copy report for chat**, downloadable Markdown and structured JSON/CSV:
- run/dataset/model/config IDs, dates, actual coverage and completion status;
- plain-language purpose, change from baseline and limitations;
- distinct calls, calls per evaluated week, entry-window durations and longest no-call interval;
- wins/losses/expired/unresolved/ambiguous outcomes with denominator;
- targets/stops, expected versus actual duration, gain/loss magnitudes and normalized gross/net outcomes under declared delay/costs;
- candidate funnel, rejection reasons, unsupported-domain and missing-data time;
- timestamped examples and comparison with the declared baseline on the same data;
- conclusion: improved / worsened / mixed / insufficient evidence, and next diagnostic question.

No assumed account size/leverage. Direction forecasts and actionable-call results are separate. Win rate alone is inadequate. Keep the copyable summary compact and link full artifacts.

## 7. Reusable fixed historical corpus

Acquire a fixed versioned BTC corpus once, reuse locally, and never redownload it per backtest. Hash verification is allowed; refresh explicitly creates a new version.

The Owner requests a repository data pack: **bounded immutable chunks with manifest, provenance and quality committed in Git where practical**, available with a normal checkout. Large raw acquisition archives and generated run artifacts stay outside ordinary Git history. If measured size/storage constraints prevent normal Git, explain a Git LFS or pinned-archive/automatic-cache alternative before adopting it; no silent paid storage or loss of offline reuse.

Initial planning target: twelve complete months, **2025-09-01 inclusive to 2026-09-01 exclusive, UTC**. Verify actual source coverage, pack size and acquisition time first. This is a target, not a claim all necessary history is available. No fabricated gaps or silent instrument substitutions. The Director fixes development/protected windows before inspecting evaluation outcomes; exposed RP-001 cases remain development evidence.

Start with traded history and include historical inputs actually required by the integrated method. Derive higher timeframes causally where sufficient. Missing news/cycle/derivative evidence is visible: price-only replay cannot validate an unimplemented context method. Acquisition can be chunked/resumed; routine operation must not repeat it.

## 8. Accepted architecture preserved

Retain Python/FastAPI, React/TypeScript, PostgreSQL, immutable Parquet artifacts and Docker Compose. Preserve M3 evidence/feed/observable-state/replay boundaries, durable jobs, checkpoints and provenance. No empty-repository restart.

The professional layer consumes available state/deltas and versioned derived observations, not future raw rows. Share causal derivations centrally. Deterministic reasoning, typed dependencies/rules and explicit lifecycle transitions remain appropriate; no universal trading DSL is required.

Track event time, availability/knowledge time, retrieval provenance and deterministic order/cursor. Modeled historical availability is not measured live receipt. Timers reassess/expire calls without fabricating bars; admit only evidence known at their recorded dispatch boundary. Missing/stale required data affects dependent conclusions; missing optional context is not a universal veto.

Traded, mark, index and funding are separate. Traded evidence supports price-structure and declared trigger/target predicates; reference prices are not fills; indicative funding is not settlement. Missing is not neutral. Higher-timeframe completion, intrabar ambiguity and human-response delay remain explicit.

semantic.v1 stays frozen DEMO; marketdata.v1 stays frozen evidence; feed/recorder/observe retain version discipline. Introduce advisory semantic.v2 with a bounded coherent process/call specification. **RP-001 closure is no longer its mandatory gate.** No personal account fields, inferred fills or sizing policy. Hypothetical normalized outcomes belong to separate evaluation semantics.

## 9. Delivery and acceptance

Deliver vertical slices: usable operation → integrated reading/calls → Owner-run backtest → diagnosed improvement. The next Director plan jointly covers method definition and app/data/report gaps. Each targeted study has a concrete missing decision, bounded sources/cases and a deliverable enabling implementation. Optional unresolved concepts cannot block all progress.

**Persistent non-use is a product failure to investigate.** Days without a good call are normal. An always-NO_TRADE system or negligible operating coverage is not accepted as excellent risk discipline. Each integrated evaluation reports frequency, practical entry duration, coverage and candidate/rejection funnel. A no-call development run must distinguish data problems, bugs, warmup, conflicting gates, geometry/cost assumptions and insufficient method coverage, and produce a corrective plan. “Wait for more signals” alone is not a plan.

“A few per week” is the Owner's usability expectation to assess over varied periods, **not a forced weekly trade quota**. Before formal evaluation the Director states the intended opportunity/coverage range, reports departures and revises/rejects unsuitable process versions. Never manufacture calls or promise opportunities.

Revise whole-process behavior on declared development data. Preserve original forecasts/calls, version changes and negative findings. Reused data are development, not independent proof. Protected periods and manageable prospective sessions check generalization. No hindsight adaptation, threshold/timeframe tournaments or optimization to known answers. Role-level ablations are optional diagnostics of an integrated method, not endless prerequisites.

Negative results can reject a particular translation; they do not automatically invalidate the product goal. Professional existence does not guarantee profitability either. Acceptance must demonstrate useful call behavior, understandable outcomes and local workflow practicality.

## 10. Repository and continuity

- FOUNDATION.md: this canonical directive.
- STATE.md: implementation facts, current work and unmet requirements.
- task.md: one bounded executor handoff including the Owner backtest boundary.
- AGENTS.md: executor workflow.
- README.md: actual operation, separating implemented and planned.
- source_notes/ and registries: knowledge/provenance, not legacy instructions.
- strategic_reviews/ and research/: historical/advisory unless a current task activates a compatible specification.

Preserve accepted M1–M3 work. Mark former narrow mandates and research HOLD gates superseded. Frozen case data/labels and source dossiers stay byte-identical; surrounding scope notices identify them as historical. Never rewrite failed cases for the new direction.

Executors commit/push bounded work normally, no force-push, and report SHA/branch/checks/limitations. The Director reviews and replaces task.md; the Owner relays between chats. Repository changes cannot edit private Project Instructions in another chat: the Owner must synchronize those separately.

## Revision history

- 2026-09-30 — v3.0: direct Owner realignment. Call-first adviser, integrated coverage including cycle/event assessment, persistent entry validity, Owner-run visual backtests/reports, fixed reusable corpus, intermittent local use, inactivity diagnosis. Supersedes SR-002/RP-001's mandatory narrow path; preserves causal correctness.
- 2026-09-30 — v2.0: separated market advice from human capital allocation/execution; boundary retained.
- 2026-09-29 — v1.x: bootstrap/workflow; accepted infrastructure retained.
