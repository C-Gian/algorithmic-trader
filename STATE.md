# Project State

Updated: 2026-09-30

## Authority

Canonical directive: `FOUNDATION.md` — version 2.0.

## Accepted product scope

Algorithmic Trader is a BTC market-analysis and trade-decision system, not an autonomous account-management/trading bot.

The system must eventually:

- maintain a current professional MarketView;
- state plausible/primary scenarios and expected market behavior;
- decide LONG / SHORT / NO_TRADE;
- when a trade exists, expose trigger/entry logic, invalidation, target(s), expected room/time and reasons;
- keep market understanding distinct from trade recommendation;
- update the view/recommendation as the market evolves.

The human Owner independently decides capital allocation, position size, leverage, collateral/margin, actual order placement and personal portfolio/account risk.

## Milestone status

**M3 — Trustworthy real-market observation and causal reasoning readiness: COMPLETE**

The project now has an accepted end-to-end observation substrate:

**immutable real market evidence → causal feed deliveries → centrally owned observable market state → durable replay/product visibility**

M3 intentionally stops before professional market interpretation.

No real MarketView, prediction, LONG/SHORT/NO_TRADE recommendation, trigger, invalidation or target logic exists yet.

## Accepted work

### WP-001 — Repository bootstrap and observable dummy run
Accepted implementation lineage:
- `92014aa03060332b4c947ef10329b79cde7d51b2`
- CI correction `a49c0f75be7d9d885c65901c9cc73f3ed3a66a99`

The dummy account/risk/order/fill path remains DEMO infrastructure scaffolding only.

### WP-002 — Replay/operations shell and semantic baseline
Accepted implementation:
- `803b3f215c5a33499a4d901ae000ee112b75e691`

`algotrader.semantic.v1` remains the frozen synthetic-shell baseline.

### WP-003 — OKX BTC-USDT-SWAP public data provenance
Accepted implementation:
- `6b45728074e470bb85b06cce1995dad90f81cb62`

Acceptance includes immutable public OKX evidence, explicit source/event/availability/retrieval timing and frozen `algotrader.marketdata.v1`.

### WP-004 — Causal feed and observable market state
Accepted implementation:
- `82e6c8488eec146dfb4fd170fe37966750a84f60`

Acceptance includes:
- provisional `algotrader.feed.v1`;
- deterministic causal ordering;
- role-specific traded/mark/index/funding channels;
- explicit quality/freshness/missingness;
- prefix invariance;
- pure centrally owned observable-state reducer.

Accepted interpretations:
- modeled availability is a declared replay convention, not measured exchange publication;
- inspection freshness/history defaults are not professional-trader parameters;
- no silent forward fill or cross-channel substitution.

### WP-005 — Prospective OKX public live recorder and measured receipt-time evidence
Accepted implementation:
- primary `3dc890392223ea2634bda8b0c975b2c99c5ddc33`;
- source-authority hardening `0cd1ea00074a4740db2761ce00d6777e23540ba3`.

Acceptance includes:
- provisional `algotrader.recorder.v1`;
- raw public receipt-time evidence;
- append-only/hash-verifiable sessions;
- reconnect/outage provenance;
- first-completed candle receipt semantics;
- RECORDED feed bridge without future leakage;
- live pre-settlement funding retained separately from settled funding semantics;
- durable browser-independent recorder job;
- official secure OKX source authority.

### WP-006 — Product-grade application UI redesign
Accepted implementation:
- `18242cd39ac9d530a572b3aee962dbc0fdca0d33`

Acceptance includes:
- premium dark decision-desk shell;
- Market as future professional trader cockpit;
- explicit REAL / SYNTHETIC / PENDING product truth;
- Synthetic Demo isolated in Replay Lab;
- Data and Recorder as first-class evidence/operations workspaces;
- no synthetic output leaking into Market;
- responsive/browser-validated product layout.

### WP-007 — Durable real-market observation replay and observable-state integration
Accepted implementation:
- `1afdb21cf69998c108bdcc703d1eaeac4a466e33`

Acceptance evidence:
- one fast-forward implementation commit over `91fcb2b094e94e5b3b7b54937b5593aa5b2042ed`;
- GitHub Actions run `36731331649`: `checks` SUCCESS and `compose-smoke` SUCCESS;
- 289 non-E2E tests and 9 E2E tests reported green;
- new provisional `algotrader.observe.v1` revision 1;
- frozen/provisional `semantic.v1`, `marketdata.v1`, `feed.v1` and `recorder.v1` baseline blobs remain unchanged;
- real replay is a separate `src/algotrader/observe/` path and does not import or write synthetic trader/account/risk/order/fill semantics;
- historical datasets use explicit MODELED zero-extra-delay availability and are re-verified;
- finalized recorder sessions use RECORDED first-completed client receipt times;
- one replay step equals one causal feed delivery, not one candle;
- checkpoint recovery rebuilds the pure feed prefix and verifies the persisted snapshot digest;
- atomic cursor compare-and-set plus unique delivery identities prevent duplicate committed delivery;
- crash-before-commit and crash-after-commit recovery are digest-identical to uninterrupted replay in tests;
- PARTIAL recorder outages remain recorder coverage loss and do not become fabricated market gaps;
- real Replay Lab shows traded/mark/index/funding observable state without professional interpretation;
- Market Replay and Synthetic Demo remain visibly and operationally separate;
- global health is capability-aware.

Accepted WP-007 interpretations:
- `algotrader.observe.v1` is an operational observation-replay contract, not the future professional trader semantic contract;
- historical MODELED replay remains a lower-bound knowledge-time convention and must not inherit measured live latency as a universal constant;
- RECORDED timing remains client-observed receipt, not exchange publication;
- inspection freshness policy remains development UI state, not a trading rule;
- recorded pre-settlement funding remains outside settled-funding observable state until a professional process justifies a distinct causal meaning;
- observation replay may be hours-scale; current implementation prioritizes correctness/auditability over premature optimization.

Non-blocking follow-up:
- terminal validation can report PASS/FAIL independently from terminal replay status; the UI exposes validation explicitly. Revisit whether validation failure should automatically change operational terminal status only if future evidence shows ambiguity for users or automation.
- `/api/health` retains legacy top-level `labels: ["DEMO","SYNTHETIC"]`; capability-aware health is now authoritative.

## Repository history note

PR #8 had been merged as `64f3fa7`. Commit `887dfe0` was later created from stale parent `b47b3cb`, temporarily dropping the PR #8 tree from main.

The history was repaired without rewriting shared history by merge commit:

`ea88a978d3c44729f60705c332888116af3ecda6`

Future local writes must start from:

`git pull --ff-only origin main`

Force pushes remain prohibited.

## Accepted long-lived architecture

From SR-001 and the accepted M3 implementation:

**market evidence → causal availability feed → centrally owned observable market state → professional reasoning → MarketView / prediction / trade recommendation**

The professional trader must consume causal observable state rather than raw datasets.

Distinct concepts that remain mandatory:

- event/economic time;
- availability/knowledge time;
- retrieval/recording provenance time;
- deterministic processing order;
- traded vs mark vs index vs funding roles;
- missing vs invalid vs stale vs unknown;
- market view vs trade decision;
- directional expectation vs actionability;
- NO_TRADE as a legitimate decision despite market understanding.

## Contract strategy

Frozen:
- `algotrader.semantic.v1` — synthetic DEMO shell;
- `algotrader.marketdata.v1` — market evidence.

Accepted but still provisional:
- `algotrader.feed.v1` — causal feed / observable state;
- `algotrader.recorder.v1` — prospective public receipt-time evidence;
- `algotrader.observe.v1` — durable real-market observation replay.

Do **not** introduce `semantic.v2` until the strategic trader-design checkpoint defines the first coherent professional trader semantics.

## Initial market-data source

Public/read-only reference source:

**OKX `BTC-USDT-SWAP`**

This is a market-evidence/reference decision, not an autonomous broker/execution decision.

## Current strategic checkpoint

# 🚨🚨🚨 QUESTO VA MANDATO AD ASTRA 🚨🚨🚨

**SR-002 — First Professional Trader Design**

Brief:
`strategic_reviews/SR-002-FIRST-PROFESSIONAL-TRADER-DESIGN.md`

This is not an implementation task.

Astra must independently challenge the Director's assumptions and define the first coherent, testable professional market-reading and trade-decision process to sit on top of the accepted M3 observation substrate.

## What SR-002 must decide

At minimum:

1. the first coherent professional decision process from observable market state to MarketView/scenarios/recommendation;
2. which professional lenses are essential in v1 of the real trader and which should be deferred;
3. multi-timeframe/horizon structure;
4. how context, trigger, invalidation, target and expected horizon interact;
5. when a directional view should still produce NO_TRADE;
6. how uncertainty/conflicting evidence is represented without flat voting;
7. what derived causal features/observations must exist between raw observable state and reasoning;
8. which existing knowledge gaps must be researched before implementation;
9. what semantics `semantic.v2` should expose and what it must deliberately omit;
10. how the first trader will be validated without turning the project into indicator mining or backtest overfitting.

## Known research gaps entering SR-002

Current knowledge registry gaps include:

- BTC-specific market mechanisms;
- BTC perpetual/spot interaction;
- formal support/resistance;
- retracement/extension formalization;
- cyclical/temporal methodology;
- modern crypto order flow/liquidation mechanics.

These are **candidate gaps**, not mandatory features. Astra should require only what the selected coherent process actually needs.

## Base professional knowledge snapshot

`3bf9de0d88fd97360bff7a6517bbb61544f5db68`

The `source_notes/` dossiers are the clean-room professional knowledge base. They are evidence inputs, not automatic trading rules.

## Active implementation task

**NONE — strategic review gate is active.**

Claude Code / Codex must not implement trader intelligence, `semantic.v2`, indicators, levels, signals or recommendations until SR-002 is reviewed and disposed by the Project & Research Director.

## Next action

Owner opens the Astra strategic chat and sends the SR-002 brief.

After Astra returns its review, the Project & Research Director will:
- independently review/challenge it;
- write the Director disposition;
- resolve any required targeted research gaps;
- only then define the next implementation task.
