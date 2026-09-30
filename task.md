# Active Task — WP-002: Complete Replay/Operations Shell and Freeze Semantic Contracts

Status: READY  
Owner: Project & Research Director  
Executor: Claude Code  
Base: latest `main` after the Owner runs `git pull`.

## Context

WP-001 is accepted.

The current application already proves:

- a deterministic scripted BTC-perpetual dummy trader behind the future trader interface;
- PostgreSQL-backed durable runs with leases, heartbeats, checkpoints and idempotent event/accounting handling;
- browser-independent worker execution;
- worker crash recovery without duplicate fills;
- LONG / SHORT / NO_TRADE plus HOLD / REDUCE / EXIT demo behavior;
- cancellation, failed runs and inspectable structured artifacts;
- FastAPI + React UI;
- reproducible semantic trace;
- green local/CI tests and a green Docker Compose smoke.

The project is **not** ready for real BTC data yet. The Foundation requires the operational shell to be complete first.

This work package closes the remaining operational/replay gaps and establishes the first versioned semantic-contract baseline. It must not implement professional trading intelligence or real market connectivity.

## Objective

Finish the Owner-facing replay/operations shell so a historical run can be controlled like a real trader experience, survive process restarts, and remain deterministic.

After this task, freeze the current semantic contracts as a versioned baseline that the next data/execution milestone can build against.

## Required work

### 1. Durable replay controls

Add persisted replay control semantics for an active run:

- **PAUSE**: stop advancing after the current atomic step/checkpoint without cancelling or finalizing the run;
- **RESUME**: continue a paused run;
- **STEP**: while paused, advance exactly one input step/bar, commit it normally, then remain paused;
- **SPEED CHANGE**: change replay pacing for an existing queued/running/paused run without changing trader decisions.

Requirements:

- control state is persisted in PostgreSQL, not browser memory;
- browser close/reopen preserves it;
- API/worker process restart preserves it;
- pause is distinct from cancel and from terminal run status;
- a paused run must not generate new semantic events until RESUME or STEP;
- STEP must advance exactly one input step, even if that step emits multiple semantic events;
- replay speed is operational pacing only and must never enter the trader's semantic decision input or semantic trace;
- cancellation must remain possible from paused state.

Choose the smallest clean model that preserves these semantics. Do not redesign unrelated contracts.

### 2. UI controls and Owner visibility

Extend the existing DEMO/SYNTHETIC UI with clear controls/status for:

- pause;
- resume;
- step one bar;
- change speed during a run;
- current replay control state;
- current worker/runtime health;
- current phase/progress;
- ETA when defensibly estimable from observed throughput; otherwise display **unavailable** rather than inventing a value.

Keep the UI functional and understandable. This is not a visual redesign task.

The same market-view / decision / position display remains the replay experience; do not create a second fake trader UI.

### 3. Full process-restart durability

Add an automated end-to-end scenario proving that, with PostgreSQL and artifacts preserved:

1. start a run;
2. let it make progress;
3. stop both API and worker processes;
4. start fresh API and worker processes against the same database/artifact root;
5. reconnect with a fresh browser;
6. recover the existing run;
7. finish with the same semantic trace as an uninterrupted reference run;
8. prove no duplicate fill/accounting event was created.

A normal process restart must not require manual database editing or run repair.

Do not require PostgreSQL itself to be killed for this test; database durability is already delegated to PostgreSQL/storage.

### 4. Control-invariance tests

Extend deterministic tests to prove that the same pinned fixture/config produces the same semantic trace when executed through materially different operational paths, including at least:

- uninterrupted max-speed run;
- slow-speed run;
- pause -> wait -> resume;
- repeated single-step progression for a meaningful interval;
- speed changes during a run;
- API/worker restart and recovery.

Operational control events themselves may be recorded separately, but they must not contaminate the trader's semantic trace used for decision reproducibility.

### 5. Freeze semantic contract baseline

The current contracts are still labeled `wp001.v1`.

After reviewing the current contract set and adding only what WP-002 genuinely requires:

- establish a clear versioned **semantic contract baseline v1**;
- replace temporary `wp001` naming with a product-level version identifier;
- generate/store machine-readable JSON Schema (or an equivalently explicit schema artifact) for the public semantic contracts used across engine/worker/API/artifacts;
- add regression tests that fail on accidental schema drift;
- document how an intentional future breaking schema change is versioned rather than silently mutating v1;
- ensure run manifests identify the semantic schema version used.

Do not over-engineer a general schema registry or compatibility framework. A deterministic checked-in baseline plus tests is enough.

### 6. Runtime failure visibility

Preserve all WP-001 behavior and make sure the UI/API clearly distinguish at least:

- queued;
- actively running;
- paused;
- recovering / lease expired where applicable;
- cancel requested;
- completed;
- cancelled;
- failed.

Do not collapse scientific/trading state into runtime state.

## Required tests / evidence

At minimum, extend automated coverage for:

- pause/resume semantics;
- exact one-bar STEP semantics;
- dynamic speed changes;
- cancel while paused;
- browser reopen while paused;
- API + worker process restart with run continuity;
- no duplicate fills after restart/recovery;
- trace invariance across operational control paths;
- schema baseline regression;
- existing WP-001 tests remain green.

Update the Playwright E2E evidence to include screenshots/JSON for:

1. a visibly paused run;
2. a stepped run that remains paused;
3. a completed run after full API/worker restart and browser reconnect.

CI must remain green for both `checks` and `compose-smoke`.

## Acceptance criteria

WP-002 is complete only if:

1. pause/resume/step/speed controls work from the UI and survive browser reconnect;
2. a paused run makes no progress until explicitly resumed or stepped;
3. STEP advances exactly one input bar and returns to paused;
4. changing operational controls cannot change the semantic decision trace;
5. API + worker restart preserves the run and produces the same final trace/fills as the uninterrupted reference;
6. no duplicate accounting/fill records appear under restart/recovery;
7. the UI exposes runtime state/health/progress and defensible ETA or explicitly unavailable;
8. semantic contracts have a checked-in versioned v1 baseline with drift tests;
9. existing cancellation/failure/artifact/recovery behavior remains intact;
10. GitHub Actions `checks` and `compose-smoke` are green;
11. no real-market data, exchange integration, professional trading rule, profitability claim or new research mechanism is introduced.

## Prohibited changes

Do not:

- modify `FOUNDATION.md` or `source_notes/`;
- select/connect a real exchange or data vendor;
- implement indicators, market-structure rules, order-flow interpretation or any real trader logic;
- introduce real funding/fee/slippage values;
- turn DEMO placeholders into accepted risk policy;
- replace PostgreSQL, FastAPI, React or the modular-monolith architecture;
- add Redis, a message broker, Kubernetes or microservices;
- perform a visual/UI redesign unrelated to the required controls;
- weaken existing deterministic, recovery or accounting tests;
- start WP-003.

## Git / completion workflow

After implementation and local checks:

1. commit the complete bounded task with a meaningful commit message;
2. push normally to the current branch/origin;
3. do not force-push or rewrite history;
4. if GitHub Actions is inspectable, resolve genuine WP-002 failures without expanding scope and push corrections until green or blocked.

## Completion report

Report:

- base commit and final pushed commit SHA;
- pushed branch;
- concise files/components changed;
- local checks actually run and results;
- replay-control/restart/schema acceptance evidence;
- GitHub Actions result if available;
- unresolved issues or deviations.

Do not declare WP-002 accepted. Acceptance belongs to the Project & Research Director.
