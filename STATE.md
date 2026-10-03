# Project State

Updated: 2026-10-03 — September Market replay check closed; WP-010 accepted; WP-008-R2 accepted; MP-001 proposal written; bounded method review active

**Current task: [task.md](task.md) — MP-001 integrated method review (Director closure / Astra advisory challenge; no executor implementation).** Product authority: [FOUNDATION.md](FOUNDATION.md) v3.1. Executor rules: [AGENTS.md](AGENTS.md). How to run the app: [README.md](README.md). Chronology and earlier package evidence: [delivery/DELIVERY-HISTORY.md](delivery/DELIVERY-HISTORY.md).

Goal (Foundation v3.1): an integrated BTC adviser with persistent actionable LONG/SHORT calls, entry area, targets, stop/exit guidance and holding horizon. Capital, size, leverage and orders stay human. Historical ACCEPTED/READY/HOLD labels in older documents do not authorize work; only task.md does.

## 1. Current implementation

**M3 is complete and reusable:** immutable real evidence → causal feed → observable state → durable Market replay. **No professional adviser, market prediction or trade call exists.** Real replay is observation-only; synthetic trader/account output is DEMO.

Implemented and in use:
- OKX BTC-USDT-SWAP public evidence (`marketdata.v1`, frozen), causal feed/observable state (`feed.v1`, provisional), public live recorder with measured local receipt times (`recorder.v1`, provisional).
- Durable observation replay (`observe.v1` revision 3, provisional) on the streaming engine: immutable receipt-pinned feed cache, one incremental causal kernel, sparse checkpoints with direct restore, fenced publication, bounded terminal reconciliation `observe.stream-reconciliation` v2 for legacy runs and v3 for temporal runs.
- Shared operational contract `algotrader.ops.v1`: status, phase, health and assurance as separate facts; durable launch; phase timing/ETA; pause/step/speed/cancel; diagnostic copy/export at every status.
- Optional Deep validation (`observe.deep-reference` v1 for legacy runs, v3 for new temporal launches; stored v2 results unchanged): an explicitly launched reference re-execution of a run's committed prefix over its canonical feed cache, along a separate execution path but with the shared reducer; not a wholly independent method and not an audit of the original source files.
- Historical Workbench (`#backtest`): prepare a month of the corpus (only `btc-okx-2025-09` is preparable), start a *Market replay — data and engine check*, follow it and **Copy report for chat**. Adviser backtest is shown as unavailable.
- Task-first UI pass (`d8144ad`): plain run status shared by Workbench and Replay Lab, technical detail behind disclosures. It improves Workbench/Replay Lab only.
- **Causal temporal substrate (WP-008-R2 accepted at `ddc1831`):** `algotrader.temporal.v1` r1 (provisional) factual UTC 15m/1h/4h/day/Monday-week/calendar-month aggregates per trade/mark/index series, seal-no-revision late policy, explicit logical clock and dispatches (modeled complete-prefix, recorded synthetic-barrier, dispatch-tape fixture interface), deadlines, dependency readiness, bounded explicit restore state in the fenced checkpoints of new `observe.stream.v2` runs (lifecycle 4), reconciliation v3 and Deep validation v3 for new diagnostic launches on those runs, temporal inspection and copy-report section. No observations, thresholds, calls or `semantic.v2`.

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
| WP-008-R2 causal temporal substrate | `ddc1831`, CI `37138450907`, [review](delivery/WP-008-R2-DIRECTOR-REVIEW.md) | Factual temporal slice; Deep terminal correction accepted; no adviser |
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

1. **Now:** MP-001 [integrated proposal](delivery/MP-001-INTEGRATED-METHOD-PROPOSAL.md) and [conventions](delivery/MP-001-PARAMETERS.json) are written. Bounded Astra challenge under [the review brief](delivery/MP-001-REVIEW-BRIEF.md), then Director disposition; no executor implementation is active.
2. **Next Director action:** resolve specific method findings and close MP-001 before method-led R3 context and WP-009 implementation. No substantial acquisition or isolated signal prototype is authorized.
3. Remaining Foundation/SR-003 sequence (each needs its own task.md activation): R2 → MP-001 → R3 method-required context/presets → WP-009 integrated adviser v0 → Owner Backtest A. Sequence and rationale: [integrated delivery plan](delivery/FOUNDATION-V3-INTEGRATED-PLAN.md) §9–10 and [SR-003 disposition](strategic_reviews/SR-003-DIRECTOR-DISPOSITION.md).

### WP-008-R2 executor evidence (base `9169096`; accepted after correction `ddc1831`)

Implemented against [the temporal specification](delivery/WP-008-R2-CAUSAL-TEMPORAL-SPEC.md); original executor evidence below is retained. Current acceptance and corrected Deep version: [Director review](delivery/WP-008-R2-DIRECTOR-REVIEW.md).
- **New/changed formats:** contract `algotrader.temporal.v1` r1 (new baseline `schemas/algotrader.temporal.v1.json`); `algotrader.observe.v1` r3 (optional manifest `temporal`; changelog entry; r1/r2 readable); engine `observe.stream.v2` (v1 kept for existing runs; factual compatibility fingerprint now includes the engine format); temporal engine `temporal.engine.v1`, state `algotrader.temporal-state.v1`; validators `observe.stream-reconciliation` v3 and `observe.deep-reference` v2 (temporal runs only; v2/v1 and their claims unchanged for R1B/R1C runs); additive migration 10 (temporal columns; suspends pre-R2 unfinished lifecycle-3 runs read-only); lifecycle 4. `feed.v1`, `marketdata.v1`, `semantic.v1`, `recorder.v1` baselines byte-identical.
- **Clock/seal policies:** `temporal.clock.modeled-complete-prefix.v1`, `temporal.clock.recorded-replay-synthetic-barrier.v1` (named convention, not a live-decision reproduction), `temporal.clock.recorded-dispatch-tape.v1` (fixture/tape interface); `temporal.seal-no-revision.v1`; profile `temporal.utc-horizons.v1` with engineering demonstration dependencies only.
- **Evidence:** `tests/test_temporal.py` (21 pure: UTC anchors incl. leap/non-leap February and DST days, partial coverage, exact OHLC/Decimal volumes per family, slot-order independence, missing/rejected, late before/after seal, cutoff perturbation, modeled tie groups and pending-boundary restore, per-event restore equality, recorded equal-time receipts, tape replay = live-style, deadline ordering and no-event timers, finite clock end, monotonicity, differential vs the separate reference aggregator for both streamed policies, readiness/staleness/unavailable/capacity rejection, bounded state, contiguous continuation and discontinuity reset); `tests/test_temporal_integration.py` (12 DB: cadence 7/333/5000 range-by-range equality with the pure fold, STEP/pause/paced, crash after commit at 1/15/42 without duplicate dispatch, corrupt temporal restore fallback, reconciliation v3 tamper/scope, Deep v2 match + tamper detection + pause/resume re-fold, legacy `observe.stream.v1` run with validator v2 / Deep v1, migration-10 suspension, inspection view and copy report); Workbench E2E asserts the temporal disclosure.
- **Bounded synthetic month benchmark** (executor machine; [evidence](delivery/evidence/WP-008-R2-month-benchmark.md)): month application gates PASS — cached observation 43.8 s (R1C without temporal: 31.4 s), terminal 0.87 s, cold preparation 36.1 s; temporal restore state ~75 KB compressed per checkpoint; Deep v2 MATCH in 54.9 s, peak RSS 236 MB. Annual gates remain NOT_MEASURED/PENDING.
- **Checks:** final clean run on a disposable PostgreSQL 18.6 container (Owner stack untouched): 431 non-E2E passed, 0 skipped; E2E 10/10; web typecheck/build; `algotrader schema` (all six baselines match; frozen baselines unchanged); isolated Compose smoke (separate project, image tag, port 18080 and volumes; migration 10 applied; `stack_smoke.py` OK; isolated resources removed afterwards); documentation link check. Two existing tests were updated only for the deliberate version changes (observe r3, engine v2, reconciliation v3, `temporal.json`). The benchmark harness received one race fix (None progress). CI result to be read from the pushed commit.
- **Open limits:** live input ownership, wall-clock catch-up and real dispatch tapes are WP-009 dependencies (tape interface is fixture-only); multi-chunk runs do not exist in the app yet, so source continuation is implemented and tested at engine level only; dispatches are persisted as sequence + commitments + a bounded recent log (barriers are reproducible from input + pinned configuration), not as a per-dispatch table; Deep v2 compared only at committed boundaries (corrected by v3 below for completed runs) and re-folds the temporal prefix on resume; recorded closure allowance 120 s is an engineering default; production lookbacks/authority remain MP-001 decisions.

### WP-008-R2 correction executor evidence (base `35d73fc`; Director review pending)

- **Finding 1 corrected:** Deep validation for temporal runs is now `observe.deep-reference` **v3** (new launches; stored v2 results keep their recorded boundary-only claim; v1 for `observe.stream.v1` runs unchanged). At launch a completed run's published clock-end evidence is pinned (artifact generation, `temporal.json` SHA-256/size from the manifest, manifest `temporal` reference, `clock_end`). After the full committed prefix both the shadow temporal fold and the separate reference aggregator consume the pinned terminal clock command and 11 terminal comparisons run: published file vs manifest reference (aggregate chain, sealed/dispatch commitments, dispatch sequence, clock time), published aggregate chain vs reference and vs shadow, published sealed/dispatch commitments, dispatch sequence and clock time vs shadow / `clock_end`. Missing, unlisted or corrupt evidence ends FAILED with outcome `error` (never MATCH); inconsistent values are mismatches. Paused, cancelled, failed or partial targets keep exact committed-prefix scope (`terminal.compared = false`, no finish applied). The original run, its artifacts and saved diagnostic results are never modified; cancel/terminal serialization and progress hooks are unchanged.
- **Regressions:** pure — the exact 15-minute pending-final-tie case (0 sealed before finish, chains equal; engine finish seals 6 records; equal again only after the reference's finish) and a Monday-to-month-end fixture where the final 15m/1h/4h/day closures and the cut week/month exist only after the terminal command; DB — completed fixture run whose published chain differs from its last range yet Deep v3 MATCHes with 11 terminal comparisons, finished-output-only tamper (file and manifest made consistent, pre-finish records untouched) gives terminal mismatches, absent/corrupt/unlisted evidence never matches, paused and cancelled targets keep prefix-only scope; existing Deep tests updated to v3.
- **Checks:** disposable PostgreSQL 18.6 container (Owner stack untouched): 439 non-E2E passed, 0 skipped; E2E 10/10; web typecheck/build; `algotrader schema` (no contract change in this correction). A first full run failed 3 existing cancelled-Deep report tests because the new scope sentence contained the token MATCH; the scope was reworded and the full suites rerun green. Compose smoke is left to isolated CI (no Docker/packaging change); CI result in the executor report.

### WP-010 accepted evidence (base `e9c01b9`; implementation `f7ad4bc`)

- Chronology moved verbatim (heading levels only) from STATE.md and README.md to [delivery/DELIVERY-HISTORY.md](delivery/DELIVERY-HISTORY.md); STATE is reorganized as implementation / evidence / limits / next step; README is an operation guide (start, upgrade, data and report locations, normal Workbench path, limits); plan §9–10 and the SR-003 current pointer updated.
- UX/report wording: pause shows *Pause requested* until the worker parks the run (no "nothing is processed" promise before `paused`); replay status no longer claims knowledge "exactly as it would have been known" and states the modeled availability convention vs recorded receipt times; Deep validation is described as a reference re-execution with the shared reducer and canonical-cache scope, not a wholly independent method or source audit (UI, Workbench report text, Deep scope string for new validations, mismatch warning). Stored reports, validator ids/versions and the reconciliation scope string are unchanged.
- Checks: `tests/test_ux_wording.py` (3 tests; pause/availability assertions fail on the previous `runStory.ts`); 398 non-E2E passed and 10/10 E2E on a disposable PostgreSQL 18.6 container (Owner stack untouched); web typecheck/build; markdown link check of the changed documents (34 links, 0 problems). Compose smoke left to CI.

The next product objective is the first complete adviser path, not an isolated rule. Timing/cycle, news/event and derivatives roles need explicit bounded dispositions; missing optional context cannot become endless infrastructure work or silent neutral confirmation.

## Stable reference

**Product path:** available evidence → causal observable state → derived professional observations → integrated MarketView → scenarios → candidate plan → actionability → persistent call / NO_TRADE → reassessment.

**Architecture (SR-001, M3):** market evidence → causal availability feed → centrally owned observable market state → professional reasoning → MarketView / prediction / trade recommendation. The professional layer consumes causal observable state, not raw datasets. Mandatory distinctions: event vs availability vs retrieval time; deterministic processing order; traded/mark/index/funding roles; missing vs invalid vs stale vs unknown; market view vs trade decision; directional expectation vs actionability; NO_TRADE as a legitimate decision.

**Professional coverage decisions** (plan §3): structure/trend/location and movement/momentum are required core; participation/volume is included with limited non-voting authority; volatility is required context/scale; timing/cycles and news/events require explicit closure, not silent omission; derivatives/liquidity are factual context with limited interpretation.

**Contracts.** Frozen: `algotrader.semantic.v1` (synthetic DEMO shell), `algotrader.marketdata.v1`. Provisional: `algotrader.feed.v1`, `algotrader.recorder.v1`, `algotrader.observe.v1` (revision 3 since R2: optional manifest `temporal` reference), `algotrader.temporal.v1` (revision 1, R2). Operational: `algotrader.ops.v1`. Advisory `semantic.v2` is introduced only with an activated integrated specification (no `semantic.v2` during R1–R3).

**Market-data source:** public/read-only OKX `BTC-USDT-SWAP` as reference evidence, not an execution decision.

**Research retained, not governing:** RP-001 is closed as development evidence, not a production method ([review](research/first_trader/RP-001-DIRECTOR-REVIEW.md)). Its six real cutoffs cannot estimate frequency or profitability; frozen cases and labels stay byte-identical. Details are in the [history](delivery/DELIVERY-HISTORY.md).

**Knowledge baseline:** `source_notes/` and `knowledge/registry.yaml` (initial snapshot `3bf9de0d88fd97360bff7a6517bbb61544f5db68`) are provenance, not workflow instructions; preserve them unchanged.

**Repository:** force pushes are prohibited; executors do not pull (AGENTS.md). The earlier stale-parent history repair merge `ea88a97` is recorded in the [history](delivery/DELIVERY-HISTORY.md).

## WP-010 Director closure — 2026-10-03

ACCEPTED at `f7ad4bc8d067d3b5ab46945cd899da8d074f04d3`. Independently checked commit diff, current documents/history organization, pause/availability/reference wording and CI `37127341286`: checks (including E2E, web typecheck/build) and compose-smoke SUCCESS. Full local suites were reported by the executor, not rerun by the Director. Scope remains documentation and truthful presentation; no method or assurance criteria changed. The reconciliation v2 sentence “No independent reference replay was performed in this run” stays unchanged: it is a negative scope claim, and Deep's shared reducer/cache limits are explicit. The reported executor fetch --dry-run violated the standing no-sync rule; no update occurred, and the rule remains in AGENTS without a new approval flow. Next is a bounded Director R2 specification, not another general infrastructure pass.

## R2 activation — 2026-10-03

Director specification completed and implementation activated: `delivery/WP-008-R2-CAUSAL-TEMPORAL-SPEC.md`. Bounded factual aggregation/clock/readiness and restorable state only, no economic rules. Default horizon roles are conventions; MP-001 owns actual observation lookbacks and decision authority. No new Owner replay, acquisition or general hardening is assigned. Earlier specification-only pointers are historical.

## R2 initial Director review — historical, superseded by correction acceptance

**Correction required at `44ce68a`:** [one blocking finding](delivery/WP-008-R2-DIRECTOR-REVIEW.md). The Director reproduced a 15-minute modeled fixture where the pre-finish Deep chains match with zero sealed records, but the published clock-end finish produces six unexamined records. The active task extends the optional reference check to that terminal output, without changing the original evidence or partial-prefix semantics. CI 37135564664: compose-smoke, web and non-E2E steps succeeded; final checks/E2E were still pending at this review. No new Owner replay or next package is authorized.

## R2 correction accepted — 2026-10-03

ACCEPTED at `ddc1831b5015692e0b34969bc23390c2dff82a46`. Finding 1 closed: Deep v3 pins and compares completed clock-end output; unusable evidence fails, inconsistent output mismatches, partial targets retain prefix-only scope. Source/test review, independent fifteen-minute terminal-comparison probe and CI 37138450907 (checks including E2E and compose-smoke SUCCESS) support acceptance. Local full suites are executor evidence, not Director reruns. No new Owner run requested. task.md now assigns Director MP-001 specification only; R3/WP-009 and adviser implementation remain inactive.

## MP-001 proposal — 2026-10-03

Director wrote the complete first adviser proposal and parameter register before new economic outcomes: continuation after reaction, compression exit/retest and failed range exit; explicit volatility/structure phase, event-risk windows/response, distinct execution adequacy, persistent call/entry/thesis lifecycles, semantic.v2 design, R3 input inventory and preregistered evaluation assumptions. Source concepts and provisional numerical translations are distinguished; no edge/frequency guarantee is claimed. Current authority is PROPOSED, subject to bounded Astra challenge and Director disposition. No adviser code, data or schema was changed, no market outcome was inspected and no historical run was launched.
