# Project State

Updated: 2026-09-30 — direct Owner product realignment

## Authority and active direction

Canonical directive: **FOUNDATION.md v3.0**. The Owner's direct clarification supersedes the SR-002 mandatory pullback scope and RP-001 completion gate. Historical ACCEPTED/READY/HOLD labels cannot reactivate them.

Build an integrated BTC adviser with persistent actionable LONG/SHORT calls, entry area, targets, stop/exit guidance and holding horizon. Human capital/size/leverage/orders remain outside the algorithm. Home exposes live reasoning; the Owner launches substantial backtests in the app and copies their reports. Operation must fit an intermittently running local PC.

## Current implementation truth

**M3 is COMPLETE.** Accepted real evidence → causal feed → observable state → durable Market Replay remains reusable.

No production professional trader, real market prediction or actionable call exists yet. Documentation realignment does not implement one. Existing real replay is observation-only; synthetic trader/account output remains DEMO.

The desired live lens cockpit, full advisory backtest, compact copy report, repository historical pack, practical speed budgets and restart catch-up are requirements to implement/verify, not capabilities claimed complete here.

## Current work and next action

Foundation v3.0 is confirmed and the Director replan is complete.

Current integrated delivery plan:
- `delivery/FOUNDATION-V3-INTEGRATED-PLAN.md`

The long-lived product path is:

**available evidence → causal observable state → derived professional observations → integrated MarketView → scenarios → candidate plan → actionability → persistent call / NO_TRADE → reassessment**

Professional coverage decisions are now explicit:
- structure/trend/location: required core;
- movement/momentum: required core;
- participation/volume: included with limited, non-voting authority;
- volatility: required context/scale;
- timing/cyclical analysis: explicit source-closure requirement, not silently omitted;
- news/event context: explicit data/policy closure requirement, with unknown coverage visible;
- derivatives/liquidity: current factual context with limited interpretation, expanded only when the integrated method needs it.

RP-001 remains historical development evidence only. Its useful causal/masking lessons may be reused; its pullback-only scope and numeric conventions are not production defaults.

### Active package

**WP-008 — Owner Evaluation Workbench + Corpus Bootstrap**

See `task.md`.

WP-008 creates the Owner-operated workflow that the future real adviser will reuse:
- reusable historical corpus planning/preparation;
- durable app-launched acquisition;
- initial fixed bootstrap chunk `2025-09-01 → 2025-10-01 UTC`;
- dedicated Backtest/Evaluation surface;
- real observation-only historical evaluation using accepted replay;
- visible progress/candles/controls;
- compact Copy report for chat + Markdown/JSON.

WP-008 does not implement trader semantics or `semantic.v2`.

After WP-008 acceptance, the Director will close only the specific integrated-method questions required for the first adviser implementation, then authorize the real advisory core.

## Research retained, not governing

RP-001 artifacts exist, including real prefix labels and outcome reveals at the reviewed base commit 38b2fb6bde52714b8875a282e852742bf13df7c0. This documentation change does not accept their rules as production behavior or alter frozen cases.

research/first_trader/cases/REAL-LABELING-PROGRESS.md reports:
- six grid-cutoff labels, none reaching an actionable call under that candidate;
- possible structural restrictions from geometry, context-confirmation lag, epoch progress rules and a single-leg impulse definition;
- known formatting issues in some frozen label YAML.

These are bounded development findings, not a whole-history profitability/frequency estimate. Retain them to diagnose the translation; do not tune retrospectively to make these cases win. The old conventions and blanket deferrals of cycles/news/additional processes are not current constraints.

Director review:
- `research/first_trader/RP-001-DIRECTOR-REVIEW.md`
- status: **CLOSED AS DEVELOPMENT EVIDENCE — NOT ACCEPTED AS PRODUCTION METHOD**;
- the real-data acquisition is accepted as consistent with the predeclared historical RP-001 selection protocol;
- the six-case freeze/reveal chronology was independently verified from Git history;
- `REAL-G02.label.yaml`, `REAL-G03.label.yaml` and `REAL-G05.label.yaml` remain invalid YAML, but Foundation v3.0 requires frozen labels to remain byte-identical, so they will not be edited merely to satisfy the superseded RP-001 checklist;
- the real cases exposed context lag, single-leg impulse blindness, DC-31 epoch lockout, geometry-floor overrestriction, a target-zone source gap and an unverified cost model;
- six cutoffs are insufficient to estimate general call frequency or profitability.

RP-001's useful causal/research patterns remain available for selective reuse. Its numeric conventions and pullback-only scope are not production defaults.

## Unmet product requirements for the next plan

- Automatic current market reading and changing lens outputs on Home; dominant direction/call panel.
- Persistent entry validity and separate ongoing-thesis guidance; no assumed human fill.
- Automatic in-app new-call/change alerts while running.
- Explicit source-based cycle/timing and event/news coverage decisions in the integrated method.
- Startup/catch-up from cached history without H24 operation.
- Fixed reusable historical pack, incremental acquisition and truthful historical coverage.
- Owner-operated visual backtest with practical speed, pause/resume/recovery, understandable normalized outcomes and Copy report for chat.
- Coverage/frequency/entry-window/rejection diagnostics: always-NO_TRADE is not product success.
- A clear READY FOR OWNER BACKTEST handoff; no substantial executor CLI evaluation.

## Accepted implementation history

The records below retain accepted engineering facts. Historical package-local limitations describe what those packages implemented, not permanent exclusions on the product. In particular, former hours-scale correctness-first choices do not waive Foundation v3.0's local-use performance requirements.

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

Introduce advisory semantic.v2 with the next bounded integrated specification under Foundation v3.0; historical RP-001 closure is no longer its gate.

## Initial market-data source

Public/read-only reference source:

**OKX `BTC-USDT-SWAP`**

This is a market-evidence/reference decision, not an autonomous broker/execution decision.


## Knowledge baseline

Professional dossiers: source_notes/ and knowledge/registry.yaml; initial snapshot 3bf9de0d88fd97360bff7a6517bbb61544f5db68. Preserve these and frozen RP-001 cases unchanged. Sources are evidence, not automatic BTC efficacy or active workflow instructions.
