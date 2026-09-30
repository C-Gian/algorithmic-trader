# Active Task — WP-008: Owner Evaluation Workbench + Corpus Bootstrap

Status: READY  
Owner: Project & Research Director  
Executor: Claude Code  
Type: bounded product/infrastructure delivery — **NO PROFESSIONAL TRADER YET**

## Authority

Read in full:

1. `FOUNDATION.md` v3.0
2. `STATE.md`
3. `AGENTS.md`
4. `delivery/FOUNDATION-V3-INTEGRATED-PLAN.md`
5. `strategic_reviews/OWNER-REALIGNMENT-2026-09-30.md`
6. current marketdata / observe / UI implementation relevant to this task

Historical SR-002/RP-001 material is not work authorization.

Do not resume pullback-only research.

## Goal

Build the **Owner-operated historical evaluation workflow** that the real adviser will later reuse.

At the end of WP-008 the Owner must be able to:

1. open the web application;
2. see the planned reusable BTC historical corpus;
3. prepare one bounded corpus chunk from the app using the accepted public/read-only OKX path;
4. watch durable acquisition progress;
5. verify and reuse the resulting immutable dataset without redownloading it routinely;
6. launch an **observation-only historical evaluation** from a dedicated Backtest/Evaluation surface;
7. watch real candles/replay progress;
8. pause/resume/cancel/change speed using the accepted durable replay;
9. finish/cancel/fail and still obtain an understandable report;
10. click **Copy report for chat** or download Markdown/JSON.

This task does **not** create a real trader or claim trading performance.

## Product truth

The current real Market Replay is observation-only.

Until a professional adviser is implemented:

- do not call an observation run a trader backtest;
- do not show fake MarketView/calls/outcomes;
- call metrics must be explicitly unavailable;
- the report must say why.

The purpose of WP-008 is to make the Owner workflow ready before the adviser arrives.

## 1. New Backtest / Evaluation destination

Add a first-class application destination, preferably **Backtest** or **Evaluation**, using the accepted WP-006 shell/design system.

It should be product-grade, not an admin panel.

The page should contain three coherent stages:

### A. Historical corpus

Show:
- corpus target;
- available/prepared chunk(s);
- missing chunk(s);
- source/instrument;
- requested coverage;
- local verification state;
- quality status;
- dataset identity;
- actual local bytes once prepared;
- retrieval timestamp;
- reuse state.

### B. Run setup

For this task the only run type is:

**Observation-only historical evaluation**

Show an explicit notice:
> Professional adviser not connected yet. This run validates data/replay/product workflow only; trade-call metrics are unavailable.

Run setup chooses:
- a prepared dataset/corpus chunk;
- replay speed/pacing;
- optional start paused if supported cleanly.

Do not add fake model parameters.

### C. Active / completed run

Reuse the accepted real Market Replay UI/behavior rather than reimplementing the replay core.

Show:
- REAL / MODELED labels;
- source coverage;
- real traded-price chart;
- simulated/information time;
- progress;
- elapsed time;
- measured ETA when defensible;
- worker/recovery state;
- pause/resume/step/cancel;
- current observable channels;
- validation state;
- report actions.

Do not duplicate the entire Replay Lab implementation if components can be shared safely.

Replay Lab remains available for detailed inspection.

## 2. Corpus plan

Create a small checked-in logical corpus plan/config.

Foundation target:

`2025-09-01T00:00:00Z` inclusive  
→ `2026-09-01T00:00:00Z` exclusive

Do **not** download the full target in this task.

The initial Owner-preparable bootstrap chunk is:

`2025-09-01T00:00:00Z`  
→ `2025-10-01T00:00:00Z`

Reason:
- first chronological full month of the Foundation target;
- chosen without seeing adviser outcomes;
- within the accepted 31-day acquisition bound.

Give it a stable logical id such as:

`btc-okx-2025-09`

The corpus plan may list later monthly chunks as PLANNED, but:

- no “download whole year” action in WP-008;
- only the initial chunk needs an enabled Prepare action;
- later chunks remain visibly planned/locked for future expansion.

The checked-in plan contains logical coverage, not acquired market bytes.

## 3. Local corpus state

Maintain local corpus state separately from the checked-in plan.

A prepared logical chunk must record/reference:

- logical chunk id;
- exact start/end;
- source/instrument;
- dataset id;
- dataset manifest/hash identity;
- quality status;
- verification result/time;
- bytes on disk;
- retrieval time;
- local status.

Do not duplicate the immutable dataset itself.

If a chunk already references a local dataset and verification passes:
- **reuse it**;
- do not routinely redownload.

A future explicit refresh can create a new version, but refresh UI is not required now.

Do not silently bind a logically different interval/source to an existing chunk.

## 4. Durable corpus acquisition job

The Owner must be able to click **Prepare** in the app.

The network acquisition must not be owned by the browser request.

Implement a durable PostgreSQL-backed acquisition job with a worker/service or another architecture consistent with existing durable jobs.

Required states at minimum:
- queued;
- running;
- cancel_requested;
- completed;
- cancelled;
- failed;
- recovering if restart/lease recovery semantics make that truthful.

The browser can close/reopen without killing the job.

Use the existing accepted:
- `OkxPublicClient`;
- official-source validation;
- `marketdata.dataset.acquire`;
- verification logic;
- immutable dataset behavior.

Do not create another market-data format.

### Progress

Expose useful progress without pretending precision.

At minimum:
- current family/phase;
- pages or windows completed if available;
- elapsed time;
- heartbeat;
- bytes written if practical;
- a measured ETA only after enough throughput exists.

If the existing acquisition function needs a small optional callback/hook to expose progress/cancellation:
- keep default behavior byte-for-byte equivalent;
- do not change `marketdata.v1`;
- test direct CLI acquisition behavior remains intact.

### Cancellation / failure

Cancellation should stop at a safe acquisition boundary and clean temporary work where appropriate.

A failed/cancelled preparation must not register a corpus chunk as prepared.

Existing finalized immutable datasets must never be deleted by job cancellation.

### Restart

A worker/API/browser restart must not make a completed corpus binding disappear.

If an interrupted in-progress acquisition cannot safely resume inside a single dataset request, it may restart that **one bounded monthly chunk** from scratch after recovery.

Do not claim byte-level resume if it is not implemented.

The UI/report must state the actual recovery behavior.

## 5. No executor live acquisition

Claude Code must **not** acquire the Sep-2025 month from OKX as part of implementation/testing.

Tests use:
- fake clients;
- deterministic fixtures;
- tiny local datasets.

The actual network preparation is an **Owner action in the app after implementation**.

No full-year acquisition is authorized.

## 6. Corpus size/storage decision support

Foundation wants a reusable repository data pack where practical, but the actual month size is not yet measured.

After the Owner prepares the first chunk, the UI/report must expose enough information for the Director to decide later among:
- ordinary Git bounded pack;
- Git LFS;
- pinned archive / automatic local cache.

Therefore report:
- total dataset bytes;
- raw bytes if available;
- normalized/parquet bytes if available;
- file count;
- page count;
- row counts;
- coverage/quality.

Do **not** add Git LFS or commit acquired raw data in WP-008.

Storage mechanism is a later Director decision based on measured evidence.

## 7. Observation evaluation launch

The Backtest/Evaluation page must launch the existing durable observation replay against a prepared chunk.

Do not fork the observation engine.

Use:
- accepted MODELED availability;
- existing event-driven replay;
- existing worker/recovery;
- existing chart/state APIs.

This task may add a thin evaluation façade if useful, but source-of-truth replay state remains the accepted observation path.

## 8. Observation evaluation report

Extend terminal observation runs so completed, cancelled and failed evaluations provide:

### Compact Markdown report

Human-readable and suitable for **Copy report for chat**.

At minimum:

- report kind: `OBSERVATION_ONLY_EVALUATION`;
- replay id/status;
- dataset/corpus logical id;
- source/instrument;
- requested and actual coverage;
- quality status;
- availability basis/policy;
- feed event count/applied events;
- runtime elapsed;
- recovery/attempt summary;
- validation PASS/FAIL;
- final information time;
- relevant source/data warnings;
- corpus storage size summary if available;
- explicit capability section:
  - professional adviser: NOT IMPLEMENTED;
  - MarketView metrics: UNAVAILABLE;
  - call count: UNAVAILABLE;
  - win/loss/outcome metrics: UNAVAILABLE;
  - reason: no professional adviser connected yet;
- plain-language conclusion:
  - workflow/data/replay valid;
  - or specific operational failure;
- next diagnostic field may say only that adviser evaluation is pending, not prescribe a new strategy.

### Structured JSON

Provide the same facts in stable machine-readable form.

Do not introduce fake trading fields with zeros.
Use null/unavailable + reason.

### Downloads

Provide:
- Copy report for chat;
- Download Markdown;
- Download JSON.

CSV is optional in WP-008 because no call/outcome rows exist yet.

When the adviser is later connected, the same evaluation surface will gain call/outcome sections.

## 9. Reports for non-completed runs

Cancelled/failed terminal runs must also produce a report.

The report states:
- incomplete coverage;
- where execution stopped;
- whether validation could run;
- failure/cancellation reason;
- no false “successful backtest” conclusion.

## 10. API

Add only the APIs required for:

- corpus plan/status;
- prepare initial chunk;
- acquisition job list/detail/cancel;
- evaluation launch/list/detail if a façade is added;
- terminal report Markdown/JSON.

Keep exact internals an implementation choice.

Do not expose private filesystem paths unnecessarily in the primary Owner UI.

## 11. Health

Add corpus/data-acquisition worker capability to capability-aware health if a new worker exists.

An idle worker is healthy.

A missing optional recorder remains distinct from a broken core evaluation capability.

## 12. App navigation

Add Backtest/Evaluation as a first-class nav item.

Keep:
- Market;
- Replay Lab;
- Data;
- Recorder.

Do not remove existing capabilities.

Suggested product hierarchy:
- Market
- Backtest
- Replay Lab
- Data
- Recorder

Backtest is Owner workflow.
Replay Lab remains detailed replay/debug inspection.

## 13. Visual behavior

Use the accepted WP-006 design system.

At minimum:
- desktop 1440×900;
- 1920×1080;
- ~1024px width.

The page should make:
- corpus readiness;
- current acquisition progress;
- current evaluation progress;
- report action

obvious without reading logs.

Do not redesign the whole application.

## 14. Performance behavior

Do not optimize blindly.

Engineering tests may use tiny fixtures.

The real Owner run will measure:
- acquisition throughput;
- observation replay throughput;
- ETA quality;
- browser responsiveness.

Fast replay must not require rendering every event.
If current chart/update polling becomes the bottleneck, sample UI frames while preserving every backend event.

Do not weaken causal processing.

## 15. Tests

Add deterministic tests for at least:

### Corpus plan/state
- checked-in target and initial chunk are exact;
- only initial chunk is currently preparable;
- existing verified binding reuses local dataset with no network call;
- invalid/missing binding is not reported prepared;
- logical interval mismatch is rejected.

### Acquisition job
- durable create/claim/complete;
- browser/API request is not the owner of execution;
- cancellation leaves no prepared binding;
- worker restart/reclaim behaves as documented;
- successful acquisition verifies before binding;
- non-OKX source remains impossible;
- direct existing marketdata acquisition tests still pass.

### Report
- completed observation run produces Markdown + JSON;
- cancelled/failed terminal run produces report;
- call/MarketView metrics are UNAVAILABLE, not zero;
- Copy report endpoint/content is deterministic enough for E2E.

### UI E2E
Using offline fixtures:
1. open Backtest;
2. see initial corpus chunk unprepared;
3. prepare via fake acquisition worker;
4. observe progress → prepared;
5. launch observation evaluation;
6. see real chart/progress;
7. pause/resume or step;
8. complete;
9. click/call Copy report behavior;
10. verify downloaded/report content identifies observation-only mode;
11. refresh and recover state.

No real network in CI.

## 16. Frozen contracts

Do not modify:
- `algotrader.semantic.v1`;
- `algotrader.marketdata.v1`;
- `algotrader.feed.v1`;
- `algotrader.recorder.v1`;
- `algotrader.observe.v1`;

unless a generic contract defect genuinely blocks the task.

Prefer operational DB/API additions that do not alter accepted domain contracts.

Do not create `semantic.v2`.

## 17. No professional trading logic

Absolutely do not implement in WP-008:

- MarketView;
- scenario engine;
- indicators;
- cycles;
- news interpretation;
- support/resistance engine;
- trade setup rules;
- LONG/SHORT/NO_TRADE logic;
- targets/stops as trader output;
- P&L strategy evaluation;
- account sizing/leverage;
- execution/authenticated exchange access.

The only evaluation is observation/data/replay workflow.

## 18. Git workflow

Before editing:

`git pull --ff-only origin main`

Implement only WP-008.

Run required unit/integration/E2E/build checks.

Do not perform the real Sep-2025 acquisition.

Commit and push normally to `main`.

No force-push/reset/shared-history rewrite.

## 19. Completion report

Report:

- base/final SHA and branch;
- architecture of corpus plan/local state/acquisition job;
- files/tables/services added;
- exact initial corpus preset;
- reuse/no-redownload behavior;
- cancellation/restart behavior;
- progress/ETA behavior;
- Backtest/Evaluation UI flow;
- observation report Markdown/JSON shape;
- Copy report implementation;
- how non-completed runs report;
- health changes;
- E2E evidence;
- viewports visually reviewed;
- all checks/results;
- GitHub Actions result;
- deviations/limitations.

Then stop with:

**READY FOR OWNER CORPUS PREP**

and give:
- exact app navigation;
- exact preset name;
- what the Owner should click;
- what question this run answers;
- where Copy report for chat appears.

Do not run the substantial Owner acquisition/evaluation yourself.

Acceptance belongs to the Project & Research Director.
