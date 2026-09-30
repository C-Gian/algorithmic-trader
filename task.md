# Active Task — WP-007: Durable Real-Market Observation Replay and Observable-State Integration

Status: READY  
Owner: Project & Research Director  
Executor: Claude Code  
Base: latest `main` after `git pull --ff-only origin main`.

## Read first

Read in full:

1. `FOUNDATION.md`
2. `STATE.md`
3. `AGENTS.md`
4. `task.md`
5. `strategic_reviews/SR-001-DIRECTOR-DISPOSITION.md`
6. accepted `src/algotrader/feed/`
7. accepted `src/algotrader/marketdata/`
8. accepted `src/algotrader/recorder/`
9. current durable run/control/worker infrastructure
10. current product UI under `web/`

Where older review text conflicts with Foundation v2.0 or STATE.md, Foundation/STATE win.

## Context

WP-003, WP-004, WP-005 and WP-006 are accepted.

The project now has:

- immutable historical OKX market evidence;
- a causal availability feed;
- a pure centrally owned observable-state reducer;
- prospective RECORDED receipt-time evidence;
- a durable application/worker shell;
- a product-grade UI.

What is still missing is the bridge from those accepted pieces into a real-market replay that the Owner can launch, pause, step, inspect, resume after restart and observe in the application.

The current synthetic replay remains DEMO scaffolding. Do not adapt it into a real trader by substituting real candles.

## Objective

Build a **durable observation-only real-market replay** that consumes accepted market evidence through `algotrader.feed.v1`, advances the accepted observable-state reducer in causal availability order, persists restart-safe progress and exposes that state in the product UI.

The real replay must answer:

> “What market evidence would the system have been allowed to know at this replay instant, and what is the resulting observable market state?”

It must **not** answer:

> “What does the market mean?”  
> “Should I go LONG/SHORT?”  
> “What is the target?”

Those belong to the later professional trader.

## Architectural decision

Real-market observation replay is a **separate operational path** from the frozen synthetic `algotrader.semantic.v1` run.

Do not force real evidence through the dummy trader, paper account, risk skeleton, order/fill events or old semantic run contract.

The long-lived boundary remains:

**immutable evidence → causal feed deliveries → observable market state → later professional reasoning**

WP-007 ends at **observable market state**.

## 1. Supported replay sources

Support both accepted evidence forms:

### A. Historical marketdata dataset

Input:
- one finalized/immutable `algotrader.marketdata.v1` dataset.

Before launch:
- verify dataset integrity/hashes;
- build the feed using the accepted dataset→feed adapter;
- preserve source dataset identity and feed content identity.

Availability:
- use an explicit MODELED availability policy;
- for this observation/development replay, use the accepted zero-extra-delay lower-bound convention unless existing feed code requires another explicit default;
- persist the exact policy in the replay config/manifest;
- label it clearly as **MODELED — not measured publication timing**.

Do not silently turn live receipt measurements from WP-005 into a historical latency constant.

### B. Finalized recorder session

Input:
- one finalized CLEAN or PARTIAL `algotrader.recorder.v1` session with usable market evidence.

Before launch:
- verify session hashes/integrity;
- build the feed using the accepted recorded-session bridge;
- preserve session identity and any bridge exclusions.

Availability:
- use the existing RECORDED first-completion local receipt times;
- make it clear these are **client-observed receipt times**, not exchange publication times.

FAILED/no-usable-data sessions must not launch as successful replays.

PARTIAL sessions may replay, but their partial/outage status must remain visible.

## 2. Separate real-replay operational contract/storage

Do not mutate frozen `algotrader.semantic.v1`.

Create a separate provisional operational namespace/storage appropriate for real observation replay.

A replay record must at least persist:

- replay id;
- source kind: dataset | recording;
- source id;
- source integrity/verification result;
- feed schema/version/revision;
- feed content identity;
- ordered-event hash;
- availability policy and basis;
- freshness policy;
- source coverage;
- total feed events;
- status;
- replay controls;
- current cursor / applied-event count;
- current replay/information time;
- heartbeat / lease / recovery state;
- start/finish times;
- code version;
- errors;
- terminal artifact/manifest reference.

Name the namespace clearly as observation/replay semantics, not professional trader semantics.

If a schema baseline is introduced:
- mark it PROVISIONAL during M3;
- give it revision/changelog controls consistent with feed/recorder contracts.

## 3. Event-driven replay clock

A real replay step is **one causal feed delivery event**, not one bar.

This is intentional.

Do not rebuild the permanent architecture around:
- bar index;
- one bar = one engine call;
- traded candle as the only clock;
- one global data-quality flag.

Processing order must be exactly the accepted feed order.

For each delivery:

1. take the next `FeedEvent`;
2. apply it with the pure `feed.state.apply` reducer;
3. set replay/information time to that event's `available_time`;
4. derive the current `ObservableSnapshot` with the accepted snapshot function;
5. persist the checkpoint atomically with the durable progress journal.

The durable cursor must be sufficient to restart without replaying a committed event twice.

## 4. Freshness policy

Use an explicit named **inspection/development freshness policy** for the observation UI.

The existing default bar freshness/history settings may be reused if appropriate, but they must remain labelled as inspection defaults, not professional-trader thresholds.

Persist the policy with every replay.

Do not turn inspection freshness into a research conclusion.

## 5. Durable execution and controls

Real replay must run outside the browser.

Provide restart-safe durable behavior comparable to the existing shell:

- queued;
- running;
- pausing;
- paused;
- stepping;
- recovering;
- cancel requested;
- completed;
- cancelled;
- failed.

Controls:

- start;
- pause;
- resume;
- step exactly one feed delivery;
- change replay pacing;
- cancel.

Replay pacing is operational only and must not affect feed ordering, state or snapshot digests.

Use units that match the real replay honestly, e.g. **events/s** rather than pretending they are bars/s.

A “max” mode is allowed.

The browser may close/reopen without affecting the run.

## 6. Persistence, fencing and idempotency

Use PostgreSQL-backed durable state.

Requirements:

- lease/fencing so only one worker owns a replay;
- atomic checkpoint + replay journal update;
- crash recovery from last committed feed cursor;
- no duplicate committed delivery after restart;
- no future event applied early;
- repeated process interruption cannot corrupt state;
- explicit terminal failure if recovery cannot be made safe.

You may factor shared durable-control infrastructure from the synthetic worker if it reduces duplication **without coupling real replay to semantic.v1**.

Do not rewrite the accepted synthetic path merely for elegance.

## 7. Replay journal / artifacts

A terminal real replay must produce structured inspectable artifacts.

At minimum preserve/reference:

- replay manifest/config;
- source kind/id;
- source verification;
- feed manifest/content identity/order hash;
- availability/freshness policies;
- ordered committed delivery identities;
- replay control log;
- recovery log;
- final observable snapshot;
- deterministic final snapshot/content digest;
- any bridge exclusions / source warnings;
- validation result.

Avoid needlessly duplicating immutable raw source payloads; reference the accepted immutable evidence package/session.

Artifacts must remain readable by the Director/executors after hours-scale runs.

## 8. Observable state in the UI

Extend the product-grade Replay Lab so that **real Market Replay** is first-class and visually distinct from **Synthetic Demo**.

Recommended information hierarchy:

### Replay Lab / Market Replay

Make real observation replay the primary real-data workflow.

Launch UI should allow the Owner to select:

- a historical dataset; or
- a finalized recorder session.

Before launch show:

- source;
- instrument;
- time/coverage;
- quality/status;
- MODELED vs RECORDED availability;
- event count if available;
- warning for PARTIAL recording sessions.

During replay show:

- REAL badge/material;
- source id/type;
- availability basis;
- runtime/recovery state;
- event progress;
- current information/replay time;
- elapsed/ETA;
- worker health;
- controls;
- current feed cursor.

### Market evidence chart

Show a real traded-price chart from causally delivered completed traded bars only.

Important:
- no future final bar before its event becomes available;
- no indicator overlays;
- no fake signals;
- clearly distinguish gaps/rejected slots where useful;
- mark/index are not substituted into traded price.

### Observable Market State

Show each channel separately, at minimum:

- traded 1m;
- mark 1m;
- index 1m;
- settled funding when present.

For each channel show useful state such as:

- condition;
- freshness;
- latest valid market time;
- latest available/knowledge time;
- latest valid value(s);
- age;
- latest quality reason;
- quality slots since valid;
- coverage/beyond-coverage;
- counts.

Keep role names explicit so a user cannot mistake mark/index for traded price.

### Evidence/change timeline

Show the latest causal deliveries and/or snapshot delta information:

- delivery time;
- market time;
- channel/family;
- observation vs quality event;
- what channel condition/freshness changed.

This is evidence inspection, not market interpretation.

### Intelligence boundary

Keep a visible reminder that:

**Professional interpretation and LONG/SHORT/NO_TRADE are not connected yet.**

Do not populate MarketView/decision cards from observable state with heuristic text.

### Synthetic Demo

Keep the existing synthetic replay available as a secondary DEMO mode.

All existing synthetic E2E behavior must remain supported.

## 9. Launch affordances from Data / Recorder

Where clean and simple, add read-only action affordances such as:

- “Replay dataset” from Data;
- “Replay recording” from a finalized Recorder session.

These should navigate to/preselect Market Replay.

Do not duplicate replay logic inside Data/Recorder.

## 10. API

Provide clean real-replay endpoints separate from synthetic semantic runs.

At minimum support:

- list replayable sources or reuse existing dataset/recorder endpoints;
- create real observation replay;
- list/get replay;
- snapshot/current state;
- delivery/change history needed by UI;
- pause/resume/step/speed/cancel;
- artifact manifest/files.

Use SSE or another existing simple update mechanism if helpful.

Do not expose raw implementation-only mutable state unnecessarily.

## 11. Health semantics

Fix the non-blocking WP-006 issue while touching operations:

The global product health indicator must not say simply “Operational” in a way that implies every capability is healthy when the recorder or real-replay worker is unavailable.

Make health **capability-aware**.

For example:
- core API/database;
- synthetic replay worker;
- recorder worker;
- real replay worker.

The exact UI wording is your implementation choice, but the state must be truthful.

Do not make an optional inactive capability look like a catastrophic whole-system outage.

## 12. Causal correctness tests

Add deterministic tests that prove at least:

### Historical dataset
- feed events are applied in accepted total order;
- first state contains no future evidence;
- prefix at every committed cursor matches pure `state_at/snapshot_at`;
- quality events update condition without leaking invalid values;
- mark/index/trade remain separate;
- replay restart from a checkpoint produces the identical final snapshot digest.

### Recorded session
- first completed receipt is the event availability;
- forming pushes never appear;
- no future completion leaks before receipt;
- PARTIAL/outage evidence is not converted into fabricated market gaps;
- incremental replay produces the same snapshot as the pure recorded feed prefix;
- bridge exclusions remain visible.

### Durable controls
- pause parks at a committed cursor;
- step applies exactly one feed event;
- resume continues from the next event;
- pacing changes do not alter final state/digests;
- cancellation is durable;
- worker crash/reclaim does not duplicate a feed delivery.

### Separation
- no synthetic semantic/account/order/fill event is created by real replay;
- no MarketView/Decision is generated;
- real replay does not import `trader.py`, `risk.py` or `account.py` as part of its domain path.

## 13. E2E

Add/update browser E2E to demonstrate:

1. open Replay Lab;
2. choose real Market Replay;
3. launch a small offline historical dataset replay;
4. observe REAL/MODELED labeling;
5. pause;
6. step one event;
7. refresh/reconnect;
8. resume;
9. complete;
10. inspect channel state and artifacts;
11. separately launch/replay a captured recorder fixture with RECORDED labeling;
12. prove synthetic DEMO remains separate.

CI must stay fully offline/deterministic.

## 14. Visual quality

Integrate this into the accepted WP-006 product shell at the same quality level.

Do not regress into an engineering form/table dump.

Use the existing design system/material semantics:

- REAL for real replay;
- SYNTHETIC for DEMO;
- PENDING only for unimplemented intelligence.

Perform browser review/refinement at least at:
- 1440×900;
- 1920×1080;
- ~1024 px width.

Do not redesign the whole app again.

## 15. Contract rules

Do not modify frozen:

- `algotrader.semantic.v1`;
- `algotrader.marketdata.v1`.

Do not create:
- `semantic.v2`.

Do not change provisional `feed.v1` or `recorder.v1` unless a genuinely generic missing contract field blocks correct replay.

If such a change is necessary:
- stop and explain the requirement in the completion report unless it was clearly unavoidable;
- bump the relevant schema revision;
- add changelog;
- preserve previous artifact readability;
- update baseline deliberately.

Prefer a separate provisional observation-replay contract over contaminating feed semantics with operational job state.

## 16. No trader intelligence

Absolutely do not:

- generate a MarketView;
- infer bullish/bearish state;
- rank scenarios;
- output LONG/SHORT/NO_TRADE;
- calculate trigger/invalidation/targets;
- add technical indicators;
- add support/resistance logic;
- add account sizing/leverage;
- add P&L as a product decision signal;
- place orders;
- add authenticated exchange connectivity.

Observable state is factual causal market evidence only.

## Acceptance criteria

WP-007 is complete only if:

1. historical marketdata and finalized recorded sessions can both launch real observation replays;
2. replay consumes only `feed.v1` events in accepted causal order;
3. one replay step equals one feed delivery, not one candle;
4. current state is produced only by the accepted pure reducer;
5. MODELED vs RECORDED availability is explicit and persisted;
6. restart/crash recovery is idempotent and digest-identical;
7. browser close/reopen does not affect execution;
8. pause/resume/one-event-step/speed/cancel work durably;
9. real replay exposes truthful per-channel observable state;
10. future values cannot leak;
11. recorder outages do not become fabricated market gaps;
12. real replay creates no dummy trader/account/order/fill semantics;
13. Replay Lab clearly separates Market Replay from Synthetic Demo;
14. artifacts are structured, immutable enough for later review and reference source identities;
15. global operational health becomes capability-aware;
16. all deterministic unit/integration/E2E tests pass;
17. CI and compose smoke remain green;
18. no professional interpretation/trade recommendation is introduced.

## Prohibited changes

Do not:

- modify `source_notes/`;
- import legacy Trading Bot work;
- implement the professional trader;
- create `semantic.v2`;
- add indicators/levels/predictions/recommendations;
- add account/leverage/margin management;
- add real execution/authenticated connectivity;
- reinterpret funding live snapshots as settled funding;
- forward fill missing evidence;
- substitute mark/index for traded price;
- use a later event before its availability time;
- weaken tests;
- rewrite shared Git history.

## Git workflow

Before editing:

`git pull --ff-only origin main`

Then implement only WP-007, run all required checks, commit and push normally to `main`.

No force-push/reset/shared-history rewrite.

## Completion report

Report:

- base/final SHA and branch;
- architecture of the separate real-replay path;
- contract/storage namespace/version if introduced;
- DB migration summary;
- source selection and verification rules;
- MODELED/RECORDED availability behavior;
- event-driven clock/control semantics;
- checkpoint/idempotency/recovery model;
- replay artifacts;
- API/UI integration;
- per-channel state shown;
- historical and recorded deterministic evidence;
- crash/restart equivalence evidence;
- E2E evidence;
- visual review viewports;
- schema baseline hashes / revision changes;
- local checks;
- GitHub Actions result;
- deviations/unresolved issues.

Do not declare WP-007 accepted. Acceptance belongs to the Project & Research Director.
