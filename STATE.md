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

## SR-002 disposition

Astra review:
- `strategic_reviews/ASTRA-SR-002-REVIEW.md`

Director disposition:
- `strategic_reviews/SR-002-DIRECTOR-DISPOSITION.md`

Status:

**ACCEPTED WITH MODIFICATIONS**

The first professional trader candidate is now bounded to:

**directional context → move/reaction assessment → conditional continuation opportunity → trigger → actionability → LONG/SHORT/NO_TRADE → reassessment**

The initial actionable playbook is **continuation after a controlled pullback/reaction**, implemented for long and short.

This is a candidate professional process, not a profitability claim and not the complete eventual trader.

Accepted architectural direction:
- separate versioned derived causal observation layer downstream of observable state;
- typed dependency graph + hierarchical rules + small state machines;
- no flat indicator voting;
- MarketView broader than the actionable playbook;
- causal structure/pullback boundaries/horizontal reference areas only at first;
- trend/persistence, move/reaction momentum and one volatility scale have distinct roles;
- volume is not required in the first decision path unless the bounded research establishes a non-redundant role;
- mark/index/funding stay factual context initially;
- no numeric confidence/probability initially;
- scenario, opportunity, recommendation and advisory updates remain distinct;
- one primary trigger/invalidation/target and one primary actionable thesis at a time for the first release.

Not yet frozen:
- exact 1h/5m/1m permanence;
- 120-minute forecast horizon;
- swing thresholds;
- zone widths;
- variability windows;
- trigger construction;
- entry band;
- geometry floor;
- expiry/deadline values;
- exact NO_TRADE enum.

`semantic.v2` remains prohibited until the formalization research closes.

## Active research task

**RP-001 — First Professional Trader Formalization Research**

Brief:
- `research/RP-001-FIRST-TRADER-FORMALIZATION.md`

RP-001 must close:
- A — process translation;
- B — causal structure/reference areas;
- C — complete advisory policy;
- D — initial actionability assumptions;
- E — evaluation registration;
- a bounded outcome-masked causal case library, including real BTC evidence before acceptance.

This is research/formalization work, not production trader implementation.

## Initial translation configuration

Use 1h / 5m / 1m as a predeclared research configuration.

They are not permanent product invariants.

One pre-outcome change is allowed only for demonstrated behavioral/causal inadequacy, not based on profitability.

## Known deferred research areas

Do not expand RP-001 into:
- reversal playbooks;
- range fading;
- breakout-chasing;
- cycles;
- Fibonacci/retracement ratios;
- VWAP/profile/oscillator systems;
- OI/liquidation directional models;
- predictive funding;
- spot/cross-venue;
- macro/news;
- order-book inference;
- ML optimization.

A future addition requires a documented limitation of the first accepted process.

## Base professional knowledge snapshot

`3bf9de0d88fd97360bff7a6517bbb61544f5db68`

The `source_notes/` dossiers remain immutable source-study artifacts.

## Next action

Owner pulls latest `main`.

Claude Code executes only RP-001 from `task.md` and `research/RP-001-FIRST-TRADER-FORMALIZATION.md`.

No production trader code, derived engine, `semantic.v2`, indicators, levels engine or recommendations are authorized.

After RP-001 completion, the Project & Research Director reviews the formalization and cases before deciding whether any professional implementation work may begin.
