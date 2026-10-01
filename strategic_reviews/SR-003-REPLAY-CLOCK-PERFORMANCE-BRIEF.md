# SR-003 — Replay/Backtest Architecture, Professional Timeframes and Owner Observability

Status: READY FOR ASTRA  
Date: 2026-10-01  
Requested by: Project & Research Director  
Owner concern: the current historical workflow is too slow, too opaque during long phases, and may be conflating 1-minute evidence resolution with the future professional trader's reasoning timeframe.

## Authority

Read first:

1. `FOUNDATION.md` v3.0
2. `STATE.md`
3. `delivery/FOUNDATION-V3-INTEGRATED-PLAN.md`
4. `strategic_reviews/OWNER-REALIGNMENT-2026-09-30.md`
5. `research/first_trader/RP-001-DIRECTOR-REVIEW.md`
6. current accepted marketdata/feed/observe/corpus/evaluation implementation relevant to replay/backtest
7. current `task.md` (WP-008-R1), but treat it as a Director draft that you are explicitly allowed to challenge

Historical SR-002 / pullback-only direction is not governing.

## Why this review is needed

The first real Owner-run month exposed two coupled design questions:

1. **Professional reasoning clock / timeframe**
   - the current evidence pipeline is based on 1-minute traded/mark/index bars;
   - the Owner correctly questions whether a professional trading adviser should actually reason primarily at 1-minute resolution;
   - the future adviser has not yet been implemented, so this is still the right time to decide the hierarchy cleanly.

2. **Replay/backtest architecture and product UX**
   - September 2025 contains 43,200 traded 1m bars + 43,200 mark 1m bars + 43,200 index 1m bars = 129,600 causal feed events;
   - the current observation replay took roughly one hour to apply those events;
   - after reaching `129600 / 129600`, terminal validation remained CPU-bound for at least another ~20 minutes;
   - Docker showed observer CPU ~98.8% (roughly one logical core) and ~1.65 GiB RAM;
   - the worker was alive, but final validation stopped heartbeating, so the UI falsely showed:
     - System Degraded
     - Market replay stalled
     - RECOVERING
   - there was no visible validation progress, progress bar, elapsed-time phase or ETA.

This is unacceptable for the intended Owner workflow.

## Owner's product intent

The Owner is not technical and should not need to understand database transactions, worker leases or raw logs.

The application should behave like a finished product.

For every long-running operation, the Owner expects a visible phase with:
- what is happening now;
- progress bar / progress count where meaningful;
- elapsed time;
- ETA when defensibly estimable;
- clear completed/failed/cancelled outcome.

No substantial phase should disappear “behind the scenes.”

This applies at least to:
- historical data acquisition;
- verification/preparation;
- feed/replay preparation if non-trivial;
- historical replay/backtest;
- terminal validation;
- report generation.

The Owner wants important backtests/evaluations launched and understood from the app.

## Important terminology clarification

The current Backtest page runs an **observation-only historical replay**.

It currently performs:

**historical immutable evidence → causal feed → observable market state**

It does **not** yet perform:

**→ professional reasoning → MarketView → scenario → LONG/SHORT/NO_TRADE call → target/stop/horizon → call outcome evaluation**

The Owner found the page name “Backtest” confusing because a normal interpretation of backtest is “run the trading algorithm through historical data as if it were live.”

Astra must recommend clear product terminology/state presentation while preserving the eventual goal that this same Workbench becomes the true adviser backtest surface.

## Central question A — Evidence resolution vs professional reasoning timeframe

The current base evidence uses completed 1-minute bars.

Do not assume this means the future adviser should reason every minute.

Evaluate the distinction between:

### Evidence resolution
The finest causal source resolution retained for:
- accurate aggregation;
- precise known-at timing;
- trigger reconstruction;
- lower-timeframe inspection;
- future microstructure/entry timing where justified.

### Professional reasoning clock
When the adviser actually recomputes:
- higher-level context;
- MarketView;
- scenarios;
- setups;
- call lifecycle.

### Horizon hierarchy
Which time scales should serve:
- structural / macro context;
- tactical context;
- setup/decision;
- trigger/entry timing;
- post-call reassessment.

The Owner's intuition is that professional traders often rely more heavily on scales such as:
- 15m;
- 30m / 45m;
- 1h;
- 4h;
- daily;
- weekly;
- monthly;
- possibly annual/very-long-range context,

with 1m potentially useful only as a base/entry-resolution tool.

Do not merely agree with that intuition. Assess it.

Answer:

1. Is 1m a sensible **base evidence resolution** for this project?
2. What roles, if any, should 1m have in the adviser?
3. Should the adviser recompute on every 1m event, every selected timeframe close, material state changes, or a hybrid event clock?
4. What initial horizon hierarchy best fits the Owner's desired BTC adviser?
5. Which horizons should influence MarketView vs setup vs entry vs lifecycle?
6. How should conflicts across horizons be represented without flat voting?
7. Should mark/index/funding cause a full reasoning cycle every time they update, or only update factual context until a relevant reasoning boundary?
8. Does deriving higher-timeframe bars causally from 1m provide enough fidelity, or should native higher-timeframe source data also be retained/checked?
9. If monthly/annual context is genuinely useful, how much historical depth is needed? Is the current 2025-09 → 2026-09 one-year corpus target too short?

## Central question B — What should a historical backtest actually process?

Challenge the current assumption that every 1m source event must imply:
- a database commit;
- a full adviser reasoning pass;
- a full snapshot hash;
- a rendered UI update.

Separate the concepts:

- evidence event;
- derived-state update;
- reasoning trigger;
- durable checkpoint;
- audit record;
- UI frame.

Recommend which of these must happen:
- per event;
- per batch;
- per reasoning boundary;
- per material change;
- periodically.

The system must preserve exact causal correctness, but causal correctness does not automatically require one SQL transaction per evidence event.

## Central question C — Replay persistence / batching architecture

The Director's current WP-008-R1 draft proposes bounded in-memory batches and periodic atomic checkpoints.

Astra must challenge or refine that.

Consider whether the correct architecture should use some combination of:

- sequential causal processing in memory;
- batched DB writes;
- periodic durable checkpoints;
- rolling hashes / Merkle-like or chained integrity metadata;
- append-only files rather than DB rows for every delivery;
- regeneration of event-level audit detail from immutable evidence instead of permanently persisting every delivery;
- state snapshots only at meaningful boundaries;
- separate “interactive replay” and “fast backtest” persistence policies using identical semantics;
- parallel processing only where causal independence permits it.

Answer explicitly:

1. Do we actually need one durable `observation_deliveries` row for every causal event in fast historical evaluation?
2. If not, what minimum durable evidence is enough to guarantee auditability and restart safety?
3. What should be checkpointed?
4. How much work is acceptable to redo after a crash?
5. How should pause/step behave in fast mode?
6. Can the same engine support both:
   - interactive slow replay; and
   - very fast full-history backtest?
7. Which components can safely use multiple CPU cores?
8. Which components must stay sequential?
9. Should the future adviser backtest operate on the same event engine or on a semantically equivalent accelerated path?

The answer must preserve replay/live semantic parity.

## Central question D — Validation design

Current validation is too expensive.

Today it effectively:
- replays the full committed history again;
- builds/hashes snapshots repeatedly;
- performs expensive no-future checks repeatedly;
- does not heartbeat while doing so.

Recommend a validation model that remains scientifically trustworthy but is asymptotically and practically cheaper.

At minimum the final system must still be able to demonstrate:
- immutable source/feed identity;
- exact event ordering;
- no duplicate/missing causal application;
- no future leakage;
- deterministic final state;
- correct checkpoint/recovery behavior;
- equivalent results between fast replay and reference/pure replay on protected fixtures.

Challenge whether all of those need to be re-proven on every large historical run.

Consider layered assurance:

- heavy reference validation in CI / deterministic fixtures;
- cheap integrity checks on every production backtest;
- sampled or checkpoint validation;
- rolling digest;
- final state recomputation;
- optional “deep validation” mode.

Recommend what should run:
- every time;
- periodically;
- only in CI/research diagnostics.

## Central question E — Performance targets

The current measured behavior (~1 hour processing + >20 min finalization for one month without a trader) is not acceptable.

Propose practical product performance budgets for the Owner's local workflow.

Do not assume server-class hardware.

Use the observed baseline:
- 129,600 evidence events/month;
- ~one logical CPU saturated in final validation;
- local Windows + Docker environment;
- future adviser reasoning will add cost.

Define target bands for:
- one month observation replay;
- one year observation replay;
- one month adviser backtest;
- one year adviser backtest;
- terminal validation/report.

The goal is not benchmark vanity. The goal is fast enough iteration that the Owner can realistically run experiments from the app.

If absolute budgets depend too much on hardware, define:
- relative targets;
- acceptable interaction latency;
- performance diagnostics the product should show.

## Central question F — Full observability of long operations

This is an explicit Owner requirement.

Design a unified phase/progress model for long jobs.

Example phases to consider:

- QUEUED
- PREPARING_SOURCE
- VERIFYING_SOURCE
- BUILDING_FEED
- REPLAYING / EVALUATING
- FINALIZING
- VALIDATING
- GENERATING_REPORT
- COMPLETED / FAILED / CANCELLED

For each phase specify:
- what progress metric exists;
- when a percent is meaningful;
- what elapsed timer is shown;
- when ETA is meaningful;
- heartbeat behavior;
- cancelability;
- what happens across browser refresh/restart.

Important:
- a live CPU-bound worker must never be shown as “stalled” merely because it is validating;
- “stalled” should mean actual absence of worker progress/heartbeat;
- progress/ETA should not be fabricated.

Recommend whether nested phase bars or one global weighted progress bar is better.

## Central question G — Product language / UX

The Owner should not need to understand that “Backtest” is currently only an observation replay.

Recommend the cleanest product structure.

Possible approaches:
- keep “Backtest” as destination, but make run type explicit (“Data/Replay Validation” today, “Adviser Backtest” later);
- rename temporarily;
- use a Workbench with multiple run types.

Decide what is least confusing and most future-proof.

Also record, but do not expand this review into, the Owner's broader point:

> the application still needs future UI/UX/feature refinement beyond this specific workflow.

## Central question H — Corpus depth and higher-timeframe context

Current Foundation corpus target is one year:
- 2025-09-01 → 2026-09-01 UTC.

If the professional adviser is expected to use:
- daily;
- weekly;
- monthly;
- annual/long-term context,

evaluate whether one year is sufficient for:
- warmup;
- relative regime context;
- levels/structure;
- cycle/timing studies;
- robust backtesting.

Recommend:
- minimum raw-history depth to retain;
- minimum pre-roll/warmup before an evaluation window;
- whether full-resolution 1m must be retained for all years;
- whether older history can be stored at coarser resolution without damaging the intended adviser.

Do not select history length by later P&L optimization.

## Central question I — What should happen to the already-stuck Owner run?

The Owner has:
- Sep-2025 dataset successfully prepared and CLEAN;
- replay with all `129600/129600` events apparently committed;
- no final report due to the expensive/faulty finalization path.

Recommend whether the implementation should:
- salvage/finalize the existing run after the new validation engine is installed;
- mark it as superseded/incomplete and start a new replay using the already downloaded dataset;
- preserve it only as performance evidence.

Do not require re-downloading the dataset.

## Constraints

Do not:
- implement code;
- design the actual LONG/SHORT strategy in detail;
- re-open pullback-only RP-001 as governing;
- optimize thresholds;
- recommend sacrificing causal correctness for speed;
- assume the Owner will inspect logs;
- assume H24 operation;
- introduce autonomous order execution/account sizing.

You may recommend changes to the current WP-008-R1 draft.

## Required deliverable

Produce:

`strategic_reviews/ASTRA-SR-003-REPLAY-CLOCK-PERFORMANCE-REVIEW.md`

Structure:

1. Executive decision
2. What the Owner's month run actually proved
3. Evidence resolution vs professional reasoning clock
4. Recommended initial timeframe/horizon hierarchy
5. Historical depth / corpus recommendation
6. Replay/backtest execution architecture
7. Persistence/checkpoint/audit design
8. Validation strategy
9. Performance targets
10. Long-operation progress / ETA / heartbeat UX
11. Backtest/Workbench product terminology
12. Treatment of the existing stuck run
13. What should change in WP-008-R1 before Claude implements it
14. Exact implementation package sequence after this review
15. Acceptance criteria for the performance hardening
16. Questions, if any, that genuinely require Owner choice

Be decisive.

The Director needs an implementable architecture and ordered work plan, not another broad research agenda.
