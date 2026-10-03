# Project State

Updated: 2026-10-03 — September Market replay check closed; WP-010 accepted; R2 implementation active

**Current task: [task.md](task.md) — WP-008-R2 causal temporal substrate (ACTIVE executor implementation).** Product authority: [FOUNDATION.md](FOUNDATION.md) v3.1. Executor rules: [AGENTS.md](AGENTS.md). How to run the app: [README.md](README.md). Chronology and earlier package evidence: [delivery/DELIVERY-HISTORY.md](delivery/DELIVERY-HISTORY.md).

Goal (Foundation v3.1): an integrated BTC adviser with persistent actionable LONG/SHORT calls, entry area, targets, stop/exit guidance and holding horizon. Capital, size, leverage and orders stay human. Historical ACCEPTED/READY/HOLD labels in older documents do not authorize work; only task.md does.

## 1. Current implementation

**M3 is complete and reusable:** immutable real evidence → causal feed → observable state → durable Market replay. **No professional adviser, market prediction or trade call exists.** Real replay is observation-only; synthetic trader/account output is DEMO.

Implemented and in use:
- OKX BTC-USDT-SWAP public evidence (`marketdata.v1`, frozen), causal feed/observable state (`feed.v1`, provisional), public live recorder with measured local receipt times (`recorder.v1`, provisional).
- Durable observation replay (`observe.v1` revision 2, provisional) on the streaming engine: immutable receipt-pinned feed cache, one incremental causal kernel, sparse checkpoints with direct restore, fenced publication, bounded terminal reconciliation `observe.stream-reconciliation` v2.
- Shared operational contract `algotrader.ops.v1`: status, phase, health and assurance as separate facts; durable launch; phase timing/ETA; pause/step/speed/cancel; diagnostic copy/export at every status.
- Optional Deep validation (`observe.deep-reference` v1): an explicitly launched reference re-execution of a run's committed prefix over its canonical feed cache, along a separate execution path but with the shared reducer; not a wholly independent method and not an audit of the original source files.
- Historical Workbench (`#backtest`): prepare a month of the corpus (only `btc-okx-2025-09` is preparable), start a *Market replay — data and engine check*, follow it and **Copy report for chat**. Adviser backtest is shown as unavailable.
- Task-first UI pass (`d8144ad`): plain run status shared by Workbench and Replay Lab, technical detail behind disclosures. It improves Workbench/Replay Lab only.

Historical datasets use **modeled** availability (a declared convention: a bar counts as known at its close, funding at its funding time), not measured historical publication or receipt times. Recordings use **recorded** client receipt times.

## 2. Accepted evidence

| Item | Evidence | Scope / limits |
|---|---|---|
| WP-001 – WP-007 (M1–M3) | Accepted commits and CI listed in [history](delivery/DELIVERY-HISTORY.md) | Infrastructure and observation only |
| WP-008 Workbench + corpus bootstrap | `a14f58b`, CI `36773558450` | Observation-only evaluation; adviser metrics UNAVAILABLE |
| WP-008-R1A observable lifecycle | `0919001`, [review](delivery/WP-008-R1A-DIRECTOR-REVIEW.md) | Operational slice, not a speedup |
| WP-008-R1B streaming replay | `9d814ec`, [review](delivery/WP-008-R1B-DIRECTOR-REVIEW.md) | Structural slice |
| WP-008-R1C assurance + gates | `99e0ca5`, CI `37111371473`, [review](delivery/WP-008-R1C-DIRECTOR-REVIEW.md), [gate inventory](delivery/evidence/WP-008-R1C-benchmark-gates-v2.md) | Month-only release; synthetic structural benchmark |
| **Owner September Market replay check — CLOSED** | Evaluation `eval-20261003T091928-a7eb00`, replay `obs-20261003T091928-363a3d` | See below |
| UX pass | `d8144ad`, CI `37116003888` (checks incl. E2E, compose-smoke) | Workbench/Replay Lab only |

**September closure (Director decision, 2026-10-03).** COMPLETED; coverage COMPLETE 129600/129600; runtime assurance PASSED; `observe.stream-reconciliation` v2 PASS 9/9; trusted receipt/cache/run pin matched; entire feed consumed; elapsed 60.4 s; 27 committed transactions; zero delivery rows; zero recoveries. The original replay performance incident is closed. Evidence is the Owner's copied terminal report reviewed by the Director, not an independently rerun benchmark. No Deep validation of this run was performed. No adviser or trading performance was evaluated.

## 3. Open limits

These remain open after the September closure; they are not contradicted by it:
- **Annual application performance gates: NOT_MEASURED / PENDING.** Annual component timings are comparisons, not gates. Only September 2025 is preparable; do not launch other months or a year.
- Recording-volume evidence is limited.
- Windows directory fsync (power-loss durability of publication) remains unproven.
- Data, Recorder and mobile UX are not closed by the UX pass.
- The old CI Copy-feedback failure (job `111166819975`) has a plausible, not proven, cause; downloading the Markdown report is the fallback.
- Not yet built (Foundation requirements): live Home lens cockpit and dominant direction/call panel; persistent entry validity and thesis guidance; in-app call alerts; explicit cycle/timing and news/event dispositions in the integrated method; startup catch-up; fixed reusable historical pack beyond the September chunk (storage mechanism undecided); advisory call/outcome sections in reports; adviser `semantic.v2`.
- Always-NO_TRADE is not product success: integrated evaluations must report coverage, frequency, entry windows and the candidate/rejection funnel.

## 4. Next step

1. **Now:** WP-008-R2 implementation is activated by task.md and [the bounded temporal specification](delivery/WP-008-R2-CAUSAL-TEMPORAL-SPEC.md). WP-010 is accepted. MP-001, R3 and WP-009 are not active.
2. **Next Director action:** review R2 implementation against the temporal specification, then define MP-001 integrated method closure before context acquisition.
3. Remaining Foundation/SR-003 sequence (each needs its own task.md activation): R2 → MP-001 → R3 method-required context/presets → WP-009 integrated adviser v0 → Owner Backtest A. Sequence and rationale: [integrated delivery plan](delivery/FOUNDATION-V3-INTEGRATED-PLAN.md) §9–10 and [SR-003 disposition](strategic_reviews/SR-003-DIRECTOR-DISPOSITION.md).

### WP-010 accepted evidence (base `e9c01b9`; implementation `f7ad4bc`)

- Chronology moved verbatim (heading levels only) from STATE.md and README.md to [delivery/DELIVERY-HISTORY.md](delivery/DELIVERY-HISTORY.md); STATE is reorganized as implementation / evidence / limits / next step; README is an operation guide (start, upgrade, data and report locations, normal Workbench path, limits); plan §9–10 and the SR-003 current pointer updated.
- UX/report wording: pause shows *Pause requested* until the worker parks the run (no "nothing is processed" promise before `paused`); replay status no longer claims knowledge "exactly as it would have been known" and states the modeled availability convention vs recorded receipt times; Deep validation is described as a reference re-execution with the shared reducer and canonical-cache scope, not a wholly independent method or source audit (UI, Workbench report text, Deep scope string for new validations, mismatch warning). Stored reports, validator ids/versions and the reconciliation scope string are unchanged.
- Checks: `tests/test_ux_wording.py` (3 tests; pause/availability assertions fail on the previous `runStory.ts`); 398 non-E2E passed and 10/10 E2E on a disposable PostgreSQL 18.6 container (Owner stack untouched); web typecheck/build; markdown link check of the changed documents (34 links, 0 problems). Compose smoke left to CI.

The next product objective is the first complete adviser path, not an isolated rule. Timing/cycle, news/event and derivatives roles need explicit bounded dispositions; missing optional context cannot become endless infrastructure work or silent neutral confirmation.

## Stable reference

**Product path:** available evidence → causal observable state → derived professional observations → integrated MarketView → scenarios → candidate plan → actionability → persistent call / NO_TRADE → reassessment.

**Architecture (SR-001, M3):** market evidence → causal availability feed → centrally owned observable market state → professional reasoning → MarketView / prediction / trade recommendation. The professional layer consumes causal observable state, not raw datasets. Mandatory distinctions: event vs availability vs retrieval time; deterministic processing order; traded/mark/index/funding roles; missing vs invalid vs stale vs unknown; market view vs trade decision; directional expectation vs actionability; NO_TRADE as a legitimate decision.

**Professional coverage decisions** (plan §3): structure/trend/location and movement/momentum are required core; participation/volume is included with limited non-voting authority; volatility is required context/scale; timing/cycles and news/events require explicit closure, not silent omission; derivatives/liquidity are factual context with limited interpretation.

**Contracts.** Frozen: `algotrader.semantic.v1` (synthetic DEMO shell), `algotrader.marketdata.v1`. Provisional: `algotrader.feed.v1`, `algotrader.recorder.v1`, `algotrader.observe.v1` (revision 2). Operational: `algotrader.ops.v1`. Advisory `semantic.v2` is introduced only with an activated integrated specification (no `semantic.v2` during R1–R3).

**Market-data source:** public/read-only OKX `BTC-USDT-SWAP` as reference evidence, not an execution decision.

**Research retained, not governing:** RP-001 is closed as development evidence, not a production method ([review](research/first_trader/RP-001-DIRECTOR-REVIEW.md)). Its six real cutoffs cannot estimate frequency or profitability; frozen cases and labels stay byte-identical. Details are in the [history](delivery/DELIVERY-HISTORY.md).

**Knowledge baseline:** `source_notes/` and `knowledge/registry.yaml` (initial snapshot `3bf9de0d88fd97360bff7a6517bbb61544f5db68`) are provenance, not workflow instructions; preserve them unchanged.

**Repository:** force pushes are prohibited; executors do not pull (AGENTS.md). The earlier stale-parent history repair merge `ea88a97` is recorded in the [history](delivery/DELIVERY-HISTORY.md).

## WP-010 Director closure — 2026-10-03

ACCEPTED at `f7ad4bc8d067d3b5ab46945cd899da8d074f04d3`. Independently checked commit diff, current documents/history organization, pause/availability/reference wording and CI `37127341286`: checks (including E2E, web typecheck/build) and compose-smoke SUCCESS. Full local suites were reported by the executor, not rerun by the Director. Scope remains documentation and truthful presentation; no method or assurance criteria changed. The reconciliation v2 sentence “No independent reference replay was performed in this run” stays unchanged: it is a negative scope claim, and Deep's shared reducer/cache limits are explicit. The reported executor fetch --dry-run violated the standing no-sync rule; no update occurred, and the rule remains in AGENTS without a new approval flow. Next is a bounded Director R2 specification, not another general infrastructure pass.

## R2 activation — 2026-10-03

Director specification completed and implementation activated: `delivery/WP-008-R2-CAUSAL-TEMPORAL-SPEC.md`. Bounded factual aggregation/clock/readiness and restorable state only, no economic rules. Default horizon roles are conventions; MP-001 owns actual observation lookbacks and decision authority. No new Owner replay, acquisition or general hardening is assigned. Earlier specification-only pointers are historical.
