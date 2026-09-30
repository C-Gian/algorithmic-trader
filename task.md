# Active Task — WP-005: Prospective OKX Public Live Recorder and Measured Receipt-Time Evidence

Status: READY  
Owner: Project & Research Director  
Executor: Claude Code  
Base: latest `main` after the Owner runs `git pull --ff-only origin main`.

## Read first

Read in full:

1. `FOUNDATION.md` — version 2.0 is authoritative.
2. `STATE.md`
3. `AGENTS.md`
4. `task.md`
5. `strategic_reviews/SR-001-DIRECTOR-DISPOSITION.md`
6. `knowledge/market_sources/OKX-BTC-USDT-SWAP.md`
7. the accepted feed implementation under `src/algotrader/feed/`
8. the accepted market-data implementation under `src/algotrader/marketdata/`

Where earlier review assumptions conflict with Foundation v2.0 or STATE.md, Foundation/STATE win.

## Context

WP-004 is accepted.

The project now has:

- immutable historical/public source evidence: `algotrader.marketdata.v1`;
- a deterministic causal feed/state core: provisional `algotrader.feed.v1`;
- explicit MODELED vs RECORDED availability semantics.

The next priority is **prospective public recording**.

Historical REST acquisition cannot reconstruct exact client receipt times or the evolving live-only information visible before a funding settlement. That evidence can only be accumulated going forward.

This task records public market information only. It does not implement the professional trader, recommendations, account sizing, P&L, orders or authenticated exchange access.

## Objective

Build a durable, auditable, public/read-only OKX live recorder for `BTC-USDT-SWAP` that captures raw pushed/polled source messages together with **actual local receipt timestamps** and enough connection/session provenance to later reconstruct RECORDED feed availability.

The recorder must establish measured **client-observed receipt timing**, not claim to measure the exchange's internal publication instant.

It must be usable for multi-hour sessions and observable/controllable from the application where practical.

## Current source constraints

Use only current official OKX public/unauthenticated interfaces.

Relevant source families remain:

- traded 1m candles;
- mark-price 1m candles;
- index-price 1m candles;
- settled/current funding information;
- evolving pre-settlement funding information when exposed by the official current public API/channel.

Prefer official public WebSocket push channels for timing-sensitive recording.

Where a required family is not available/reliable through the selected official WebSocket endpoint or regional domain, a bounded public REST poller may be used as a fallback, but its availability basis must be labeled **POLL_OBSERVED** / polling-observed rather than exchange publication time.

No API key, login, private/account or order endpoint is allowed.

Base REST and WebSocket endpoints must be configurable for regional OKX domains. Do not hard-code one universal hostname.

## 1. Recorder session contract

Create a separate recording/session contract namespace appropriate to this task.

Do not mutate frozen:

- `algotrader.semantic.v1`;
- `algotrader.marketdata.v1`.

Do not freeze professional `semantic.v2`.

You may extend provisional `algotrader.feed.v1` only if WP-005 truly requires additional generic RECORDED-availability fields. Any feed contract change must:

- bump `FEED_SCHEMA_REVISION`;
- add a changelog entry;
- update the checked-in schema baseline;
- preserve backward readability of revision-1 artifacts where relevant.

Prefer a separate recorder/session manifest contract if the required fields are operational/provenance rather than causal feed semantics.

At minimum a recording session must identify:

- source/venue;
- instrument/series;
- configured REST and WS endpoints;
- start/stop times;
- code version;
- recorder/session schema version;
- host/process/session identity;
- wall-clock source used for receipt timestamps;
- channels requested and channels successfully subscribed;
- reconnects/disconnections/errors;
- raw record counts;
- per-channel first/last receipt;
- raw artifact hashes;
- clean/partial/failed status.

## 2. Receipt-time semantics

For each received source message/record preserve separately:

- source market/event timestamp(s), where supplied;
- source server/data-return timestamp(s), where supplied;
- **local receipt time in UTC**, captured immediately when the message is received by the recorder process;
- a monotonic in-process sequence / monotonic clock sample sufficient to preserve local receipt order even if wall clock shifts;
- raw payload bytes/text exactly enough to hash/replay;
- channel/subscription identity;
- connection/reconnect generation;
- parser/normalization status;
- any source sequence/update identifier if supplied.

Never call local receipt time “exchange publication time”.

For WebSocket data the later causal basis is `RECORDED`.

For REST polling fallback, distinguish:

- request sent time;
- response received time;
- source timestamp;
- poll interval/policy.

Polling observation establishes only that the value was available **no later than the response receipt and no earlier than the previous observation/request bound**. Preserve that uncertainty.

## 3. Clock quality

Receipt timing is useful only if the host clock is visible/auditable.

Record at session start and periodically where practical:

- local UTC wall time;
- monotonic time;
- a public OKX/server-time observation if available through an unauthenticated official endpoint;
- estimated local-vs-source clock offset/round-trip bound when calculable.

Do not silently correct raw receipt timestamps.

If server-time probing is unavailable, the recorder still works but must label clock offset as unknown.

Do not add external NTP infrastructure.

## 4. Raw immutable recording

Write recording sessions outside Git under the configured data/artifact root.

Use an immutable session layout such as:

`<data-root>/recordings/<session-id>/...`

A completed/stopped session must contain or reference:

- session manifest;
- append-only raw message/event journal;
- subscription/connection lifecycle log;
- normalized recorder index if useful;
- integrity hashes;
- clock-quality observations;
- concise quality/summary report.

Requirements:

- do not overwrite a completed session;
- tolerate process restart without corrupting prior durable records;
- no duplicate logical receipt record on recovery;
- append-only/raw-first design;
- bounded memory use;
- fsync/flush policy explicit enough that a crash cannot silently lose an unbounded interval;
- partial/crashed sessions remain inspectable and clearly labeled.

Do not commit live recordings to Git.

## 5. Channels and data to record

Record the following public source families when available from current official interfaces:

### A. Traded 1m candle stream

Capture raw candle updates, including forming and completed states if the source sends both.

Important goal:

- identify the **first locally received update that establishes a bar as completed/final**;
- preserve all earlier forming updates needed to prove that transition;
- later compute observed delay between bar end and first receipt of completion.

Do not normalize a forming bar into a completed feed event.

### B. Mark-price 1m candle stream

Same raw-first and first-completed-receipt discipline.

### C. Index-price 1m candle stream

Same raw-first and first-completed-receipt discipline.

### D. Funding stream/snapshots

Capture the public funding information as it evolves before settlement, including every returned field that may change over time, such as when present:

- funding rate;
- funding/next funding time;
- settlement state;
- settlement funding rate;
- premium;
- formula/method fields;
- source timestamp.

Do not infer a trading meaning from funding.

The purpose is to build a point-in-time archive so a later trader can only use funding information that was actually known then.

## 6. Reconnect and failure semantics

The recorder must survive ordinary network instability.

Requirements:

- explicit connection states;
- heartbeat/ping/pong as required by the official current interface;
- bounded reconnect backoff;
- resubscribe after reconnect;
- increment connection generation;
- record disconnect/reconnect intervals;
- never fabricate messages for the gap;
- identify possible coverage loss caused by disconnection;
- duplicate source pushes after reconnect are retained or deduplicated only under an explicit identity rule; raw evidence must remain auditable.

A reconnect gap is not automatically equivalent to “the market had no update”.

## 7. Recorded-session → feed bridge

Add a **minimal pure adapter** that converts a completed/partial recorded session into `algotrader.feed.v1` RECORDED events for the source families whose semantics are already supported by feed.v1.

Requirements:

- use local receipt time as `available_time` for recorded WebSocket observations;
- preserve original market/event time;
- preserve recording/source provenance;
- do not use a later final bar value before its first completed receipt;
- no future message may alter an earlier snapshot except through an explicit later delivery/revision event;
- no forward fill;
- no channel substitution;
- duplicate/idempotency handling must not depend on the observable state's bounded history.

If pre-settlement funding snapshots do not fit the current `funding_settlement` channel semantically, **do not force them into it**. Record them faithfully and either:
- extend provisional feed.v1 with an explicitly distinct funding-indicative channel (with revision bump), or
- leave them recorder-only until a later task.

Choose the semantically honest option.

## 8. Measured availability report

For each session produce a structured report with at least:

- session duration/status;
- channel receipt counts;
- disconnect/reconnect periods;
- completed bars observed per bar family;
- distribution/summary of:
  - bar-end → first completed receipt delay;
- negative/impossible delay detection;
- local/source clock-offset observations;
- duplicate/update counts;
- missing expected completed-bar receipts during periods when connection was healthy;
- periods where timing evidence is unusable due to recorder outage or unknown clock quality;
- funding snapshot/update count and settlement-boundary observations.

Do not promote a single session into a universal latency constant.

The report is evidence for later selecting/testing an availability policy.

## 9. Durable recorder job

The recording process is hours-scale operational work and should not live only in an executor shell.

Integrate a minimal durable recorder job into the existing application infrastructure where practical.

Owner-facing requirements:

- start a public recording session;
- stop it cleanly;
- see status;
- elapsed time;
- heartbeat/connection state;
- current subscribed channels;
- message counts;
- last receipt time;
- reconnect count;
- output session id/path/reference;
- failure explanation.

The browser must not own the recorder.

Closing/reopening the browser must not stop the process.

If using the existing PostgreSQL job infrastructure, keep recorder operational state distinct from semantic trader runs and do not mutate frozen `semantic.v1`.

Do not add trading controls.

## 10. Minimal UI

Add a small recorder surface under Data or another natural existing operations location.

It should be clearly labeled something like:

**Public Market Recorder — no trading**

Show enough information for the Owner to know whether useful prospective evidence is being collected.

Do not redesign the whole application.

## 11. Offline deterministic tests

CI must not depend on live OKX.

Create small captured/synthetic WebSocket and REST message fixtures and fake transports/timing.

Test at least:

- subscribe/ack/data parsing;
- forming → completed candle transition;
- first completed receipt timestamp;
- out-of-order pushes;
- duplicate pushes;
- reconnect/resubscribe;
- gap caused by disconnect;
- raw journal immutability/integrity;
- crash/restart/idempotency;
- local receipt order despite equal source timestamp;
- server-time/clock-quality calculation;
- recorded session → feed RECORDED adapter;
- prefix invariance on recorded sessions;
- no future final-bar value leakage;
- funding snapshots preserved separately from settlements if semantics differ;
- no authenticated endpoint/header usage.

All previous tests remain green.

## 12. Explicit live integration evidence

Run a short real public recording check if executor network access is available.

At minimum:

1. connect using a documented current official public endpoint for the configured region/default;
2. subscribe/observe the target BTC perpetual source families available there;
3. collect a bounded live sample;
4. stop cleanly;
5. verify session hashes;
6. build the recorded-feed projection for supported channels;
7. report exact endpoint(s), session id, duration, counts, reconnects/errors and observed completion-delay summary.

If enough time passes to observe no completed 1m bar, extend the check only as reasonably necessary for one or more completions; do not run an unbounded hidden task.

If the environment cannot establish public WebSocket access, demonstrate the offline recorder and report the exact blocker. Do not fake live success.

## 13. Known WP-003 hardening

Fix the narrow instrument-parser issue already recorded in STATE:

- a numeric `ctMult=0` must not silently become `1` through Python truthiness;
- explicitly validate/handle missing vs zero according to the source contract;
- add a regression test.

Do not expand this into perpetual account modeling.

## Acceptance criteria

WP-005 is complete only if:

1. public recording requires no credentials/authentication;
2. raw source messages and actual local receipt timing are durably preserved;
3. source/event time, source-return time and local receipt time are not collapsed;
4. reconnect/outage intervals are visible and never fabricated as market gaps;
5. first completed-bar receipt can be measured for each supported candle family;
6. live-only/evolving funding information is preserved point-in-time without being misrepresented as settled history;
7. recorded sessions are immutable/hash-verifiable and crash-inspectable;
8. duplicate/idempotency protection is independent of the bounded state history;
9. supported recorded data can produce RECORDED feed events without lookahead;
10. measured delay reports preserve clock/network uncertainty;
11. the recorder is launchable/observable outside a hidden executor shell;
12. frozen semantic/marketdata baselines remain unchanged;
13. no MarketView, LONG/SHORT recommendation, account sizing, leverage, P&L or real execution is introduced;
14. all CI remains deterministic/offline and green;
15. a bounded live public integration check succeeds or an exact external blocker is documented.

## Prohibited changes

Do not:

- modify `source_notes/`;
- create professional trader logic;
- create `semantic.v2`;
- implement indicators/structure/levels/predictions/targets;
- implement account sizing/leverage/collateral/margin;
- implement order placement or authenticated connectivity;
- implement autonomous execution;
- add a second exchange;
- commit real recording data to Git;
- treat REST polling receipt as exact exchange publication;
- silently convert pre-settlement funding into settled funding;
- weaken existing tests.

## Git / completion workflow

Before editing, verify local `main` contains the latest remote history.

Use:

`git pull --ff-only origin main`

Do not force-push or reset shared history.

After implementation:

1. run all required local checks;
2. commit the bounded task;
3. push normally to `main`;
4. inspect/fix genuine WP-005 CI failures without scope expansion.

## Completion report

Report:

- base/final SHA and branch;
- files/components changed;
- session/recorder contract/version;
- exact live public endpoints/channels used;
- recording durability/restart model;
- recorded→feed semantics;
- clock-quality model;
- deterministic fixture evidence;
- live bounded session id/duration/counts/reconnects/errors;
- completion-delay summary from live evidence if observed;
- local checks;
- GitHub Actions result;
- deviations/unresolved issues.

Do not declare WP-005 accepted. Acceptance belongs to the Project & Research Director.
