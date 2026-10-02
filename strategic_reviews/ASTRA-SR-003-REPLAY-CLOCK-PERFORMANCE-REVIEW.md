# ASTRA SR-003 — Replay clock, performance and Owner workflow

Status: **INDEPENDENT REVIEW — awaiting Director disposition**  
Date: 2026-10-01  
Reviewed main: `009c3420b588f2f0422d08fbe5d92e8ddf88b15f`  
Scope: temporal architecture, historical execution, durability, validation and observability. No implementation, trading-rule calibration or repository-direction changes.

The governing materials are the current Owner instructions, `FOUNDATION.md` v3.0, `STATE.md`, `AGENTS.md`, the integrated delivery plan, Owner realignment and SR-003 brief. The current `task.md` correctly pauses implementation. The actual WP-008-R1 draft was recovered and reviewed at `d1d85d75b60b6fdd4860ec6607ec89aa6fbe3d46`; it is no longer the contents of current `task.md`. RP-001's Director disposition was read as development evidence, not a production mandate. Private Project Instructions in other chats are not accessible through this repository; no additional instructions from those chats are presumed.

This review uses the clean-room repository and the present Owner report. It imports no architecture, experiments or conclusions from the legacy Trading Bot project. Repository dossiers may contain historical project commentary; that commentary does not govern this review.

Evidence labels used below: **observed** means reported by the Owner; **code finding** means verified in pinned source; **decision** means an engineering/product recommendation; **unverified** means neither measured nor established here. No benchmark or historical evaluation was executed for this review.

## 1. Executive decision

**Replace event-by-event durable observation replay with one streaming causal engine, bounded in-memory execution, restorable checkpoints and sparse semantic audit records. Do not approve WP-008-R1 unchanged.**

Keep the accepted evidence semantics and exact source-event ordering. Remove the architectural coupling between an evidence event and a database transaction, full snapshot, full reasoning pass, delivery row or UI frame. Batching transactions alone leaves significant CPU, storage, recovery and API problems intact.

Decide now:

- Retain completed 1m traded bars as the finest default historical price evidence for the first adviser. Retain the existing mark/index evidence; do not discard or redownload September. This is a bar-based adviser, not a microstructure simulator.
- Use a hybrid reasoning clock: scheduled horizon closes, dependency-driven material events, and explicit timers. Broader interpretation does not run three times per minute because traded, mark and index arrive separately.
- Start with 15m setup context, 1h tactical context, 4h/daily broad context, weekly background and monthly long-range location. Use 1m for aggregation and bounded entry/lifecycle observation. These are versioned starting conventions, not empirically optimal parameters.
- Preserve one economic/causal engine across live observation, interactive replay and fast historical evaluation. Change pacing, storage and presentation policies, not the decision semantics.
- Give every significant operation a durable job and visible phase, including source verification and feed construction before replay. Separate worker liveness from work progress and recovery ownership.
- Use incremental integrity checks on every run, checkpoint/final state hashes, protected reference comparisons in CI, and optional deep validation. Stop mandatory full per-event snapshot re-derivation at termination.
- Keep the one-year evaluation target, but add pre-evaluation history at multiple resolutions. A year of evaluation is not a year of sufficient initialization or proof of cyclical skill.
- Preserve the old run as incomplete diagnostic evidence; run the new engine under a new run ID against the same verified dataset. Do not make legacy-run salvage a release gate.

Do **not** introduce advisory `semantic.v2` in the performance packages. Do version changed operational artifacts and the later derived-clock contract honestly. Preserve frozen `semantic.v1` DEMO and `marketdata.v1` evidence. A prohibition on changing provisional observation artifacts must not force the inefficient delivery-log architecture to survive.

The central outcome is a locally usable, inspectable adviser workflow. Infrastructure work closes against measurable gates below, then the project resumes integrated method closure and adviser implementation.

## 2. What the Owner's month run actually proved

### Evidence and its limits

The reported 129,600 events in roughly 3,600 seconds imply approximately **36 applied events/second**. Finalization then consumed at least another 20 minutes without a terminal report. This establishes a product failure on the Owner's machine. It does not establish a maximum language/runtime throughput, a hardware limit, or anything about a professional trader's quality: no adviser was connected.

The CLEAN dataset result supports accepted data-quality checks for that package. It does not establish measured publication times, historical news coverage, economic representativeness, funding coverage, or correctness of the uncompleted replay. The three reported bar-family counts sum to 129,600; funding availability must be read from the actual manifest, not inferred from the word CLEAN.

CPU near one logical core is consistent with expensive serial work. RAM of 1.65 GiB is an observation, not evidence of a memory leak. This review has no profiler trace from that run. The duration split among serialization, reduction, hashing, SQL, source construction and pacing remains unmeasured.

### Findings in the current implementation

| Pinned code location | Finding | Consequence |
|---|---|---|
| `observe/core.py`: `ReplayCore.step` | Every event applies the reducer, creates a full snapshot, calculates a delta and creates a delivery record. | Batch SQL alone leaves the expensive event path intact. |
| `feed/state.py`: `_apply_channel`, `apply`, `snapshot` | History tuples are scanned/copied; snapshots serialize all bounded histories, recursively strip provenance and hash the result. | Work scales with history size as well as event count. With fixed history this is large-constant O(N), not proven quadratic in total N. Expanding the raw history limit would worsen it. |
| `observe/worker.py`: `commit` | Each event renews the lease, updates the checkpoint and inserts an `observation_deliveries` row in one transaction. | Durable I/O and row count scale with raw delivery count. |
| `observe/worker.py`: `_restore` | A checkpoint stores a view/digest, not the restorable reducer state; recovery rebuilds the entire committed prefix. | Recovery cost grows with elapsed history. |
| `observe/artifacts.py`: `validate` | Replays deliveries through `core.step`, checks every snapshot history for future knowledge, then additionally derives the final cutoff snapshot. | Repeats much of the main CPU work. This is re-execution through shared code, not a fully independent implementation proof. |
| `observe/worker.py`: `finalize` | Loads all delivery records and synchronously writes/validates artifacts without heartbeat renewal inside that work. | Explains a lease/health failure mode during genuine CPU activity. Another worker could reclaim; this is more than cosmetic. |
| `observe/api.py`: `_runtime`, `_eta` | An expired running lease maps to RECOVERING even before reclaim. ETA only counts remaining deliveries. | False recovery wording and zero remaining replay time conceal unfinished phases. |
| `observe/control.py`: `create_replay`; `evaluation/api.py`: `start` | Source verification/feed building occur before the launch becomes a durable visible replay, inside the launch flow. | Significant preparation can block an HTTP request before the Owner has a job to monitor. |
| `observe/sources.py`, `feed/adapter.py` | `load_dataset` verifies, then `build_feed` verifies again. Worker loading rebuilds again. Feed construction materializes rows and a full tuple, sorts, and builds whole-feed identity representations. | Repeated preparation and eager memory use need fixing, not merely faster commits. |
| `observe/api.py`: deliveries/traded-bars | Charts and inspection read delivery rows. | Removing those rows requires a replacement bounded, cursor-filtered evidence-query path. |
| `evaluation/report.py` | Reports correctly label adviser metrics unavailable, but normal report access requires a terminal manifest. | A stuck run lacks the copyable diagnostic report the Owner needs most. |
| `corpus/job.py` | Already has independent heartbeat/progress publication, but acquisition restarts a bounded chunk on interruption and verification progress is coarse. | Reuse the durable-job pattern; improve its phase detail. Do not assume existing corpus behavior satisfies every long-phase requirement. |

The default feed history limit is 240 events per channel and default bar freshness is two minutes (`feed/ordering.py`). Both are explicitly developer inspection defaults. They cannot become the professional method's history or timeframe policy. A four-hour raw buffer cannot provide daily/weekly interpretation; raising it to millions of minute bars is the wrong repair.

The draft's terminal-validation redesign is substantially better than the existing implementation. Its remaining unconditional delivery-row requirement, permissive prefix rebuild, and missing preparation/streaming redesign make it insufficient as the long-lived solution.

## 3. Evidence resolution vs professional reasoning clock

### Six different units

| Unit | Meaning | Recommended frequency |
|---|---|---|
| Evidence event | A newly available observation or quality fact with its own source identity and order | Apply every accepted event exactly once within the committed prefix; never skip it merely for speed. |
| Derived-state update | Update affected aggregates, factual descriptors and dependency flags | Incrementally when relevant input arrives; no full history reconstruction. |
| Reasoning trigger | Reconsider the affected professional interpretation or lifecycle | Selected closes, material dependency changes, scheduled deadlines and explicit fresh reassessment. |
| Durable checkpoint | A recoverable execution boundary | Bounded wall-time/work intervals, pause/step and termination; independent of thesis changes. |
| Audit record | Source references plus significant reasoning/call transitions | Input evidence retained once; concise reasoning receipts at dispatches; detailed immutable records at material changes. |
| UI frame | A sampled presentation of committed progress and current understanding | Normally 2–4 frames/second maximum in fast mode; material alerts delivered once after commit. |

### What 1m can and cannot do

One-minute bars are a useful compromise for this product: reusable aggregation material, minute-scale trigger and invalidation inspection, entry-window duration and historical visual replay. They are **not** tick data, order flow, quoted spread, queue position or a known intraminute path.

A completed minute's high/low becomes usable when that bar is available. It cannot justify publishing a call earlier inside that minute. A bar touching both target and stop does not reveal their order. If a call is issued at the close, earlier movement within its input candle is not a fill opportunity for that new call. Future outcome evaluation must retain ambiguous and unassessable cases, declared human response delay and quote/fill limitations.

Keep this evidence resolution for v0. Add finer data only when a specified decision cannot be represented honestly with completed bars. Do not acquire ticks to solve a throughput problem or claim microstructure capability from 1m candles.

### Hybrid dispatch and asynchronous information

Maintain a causal dispatcher above the evidence reducer:

1. Admit each evidence item at its modeled availability or recorded local receipt time, preserving the accepted total order and full prefix cursor.
2. Update only dependent factual/derived state. All horizons coexist in memory; no future raw file is exposed to the adviser.
3. Schedule selected close/deadline triggers and record material-change triggers. Merge redundant triggers at the same dispatch boundary, recording all reasons.
4. At dispatch, evaluate affected observations and the integrated scenario/actionability consequences. Reuse unchanged higher-horizon context; do not reread it from scratch.
5. Persist the resulting reasoning receipt and every meaningful MarketView/call revision. Unchanged evaluation still has a compact receipt or aggregated counters sufficient for coverage diagnostics.

For historical modeled data, a scheduled boundary at time T consumes the complete accepted evidence prefix with availability <= T before that boundary's scheduled reasoning. Equal-time evidence uses the existing family/series/event ordering. Derived completion follows its prerequisites; lifecycle reassessment occurs before a new call is published. No economic ordering depends on a transport batch size.

This must not become an offline-only synchronization advantage. Live/recorded execution dispatches against an explicit **admitted prefix cursor** as well as a timestamp. A scheduler cannot wait indefinitely for all channels to deliver the same nominal minute. Record dispatch time/cursor and timer order in the operational replay journal; replay those boundaries for recorded sessions. Late arrivals update state and may trigger another reassessment; they never modify an earlier decision. Modeled zero-delay historical replay remains labeled an idealized availability convention, not exact historical live knowledge.

Freeze a versioned tie policy: admitted evidence at the boundary, causal derived updates, expiry/freshness/lifecycle checks, then integrated reasoning/new publication. Timers with equal deadlines have stable IDs/order. Logical deadlines fire even when no new candle arrives. A late prerequisite completing an older higher-timeframe bar makes that bar known **now**, not at its nominal close. Do not regress the latest current bar when inserting late historical evidence.

Distinguish a calendar close from completed evidence. An incomplete aggregate can be exposed as FORMING/PARTIAL, but cannot silently enter a completed-bar rule. Missing constituent data yields an incomplete observation and explicit dependency limitation. A gap does not produce a fabricated close.

Freshness is dependency-specific. Retain both time since economic observation and time since availability; a just-received old bar is not current merely because its receipt is recent. A completed daily bar remains the latest completed daily context until the next expected completion, subject to source quality and the method's declared use; it must not inherit the two-minute inspection timeout. Track expected next availability, missing updates and calendar completeness separately from a thesis becoming invalid. Settled funding is a historical fact whose age is visible, not a continuously refreshed estimate. Timers update freshness even during a source outage, and only affected required dependencies restrict actionability.

### Prices and funding

Traded price/volume owns market structure and declared price-touch predicates. Mark and index remain separate reference/anomaly context, never substitutes for traded execution prices. Settled funding remains a settled fact; a later indicative funding feed needs separate semantics.

Mark/index/funding arrivals update their factual state immediately. They cause professional reassessment only when an active dependency changes materially, a quality/freshness condition changes, or a scheduled reasoning boundary uses them. An ordinary reference-price update does not require a full thesis pass. Cross-price comparisons require explicit observation-time alignment/tolerance and age; asynchronous latest values must not manufacture an apparent basis anomaly. Numerical anomaly thresholds belong in the later coherent method, not this performance package.

## 4. Recommended initial timeframe/horizon hierarchy

The architecture separates **bar interval**, **observation lookback**, **forecast horizon**, **expected holding duration** and **reassessment deadline**. They must not share a single `timeframe` field. A 15m setup does not imply a 15m forecast or mandatory exit.

| Layer | Initial evidence/clock | Professional responsibility |
|---|---|---|
| Long-range background | Weekly completed structure; monthly completed bars/location | Major reference context and broad regime description. Context-only initially; no automatic monthly veto and no fixed cycle forecast. |
| Broad MarketView | Daily and 4h observations; scheduled updates at their closes | Structural environment, important areas, scale and medium-horizon alternatives. Material failure can invalidate an interpretation before the next close. |
| Tactical context | 1h completed observations | Current progression/reaction within the broad environment; scenario applicability and obstacles. |
| Setup/opportunity review | 15m completed observations plus material events | Coherent candidate formation and scenario reconciliation. This is the ordinary integrated review cadence. |
| Entry monitoring | Completed traded 1m evidence while a candidate/call needs it | Trigger status, remaining room, entry validity and short-lived constraints. No independent minute-by-minute directional strategy. |
| Post-call monitoring | Each relevant 1m observation, dependency change and deadline; 15m integrated review | Detect targets/invalidation/expiry, close entry when appropriate, maintain or revise the thesis with explicit reasons. Do not wait four hours to withdraw an invalid call. |

At a shared close, update available higher layers before interpreting dependent lower layers, then reconcile once. Between closes, cheap price/quality monitors can mark a structural hypothesis challenged and dispatch reassessment without inventing a completed higher-timeframe bar. Data-age badges continue moving even when the thesis is unchanged.

Do not activate 5m, 30m and 45m as additional mandatory lenses now. The aggregation facility may support them, but they need a distinct job before they become method inputs. Annual candles are not a reasoning layer for v0. Displaying a long-range chart is not giving its bars predictive authority.

Cross-horizon disagreement is a relationship, not a vote. Example: daily upward structure, 4h balance and 1h downward reaction can form one coherent state: a tactical decline inside a broader upward environment. A long continuation scenario and a shorter downward scenario may have different activation conditions and destinations. Which, if either, is actionable depends on scenario applicability, location and remaining room—not “two green horizons beat one red horizon.” Higher horizons constrain interpretation but do not automatically veto every opposing lower-horizon opportunity.

The Home summary must label its dominant expectation's horizon and retain the alternatives. More context is not automatically better: a monthly bullish label must not prevent the system from describing a useful multi-hour decline.

Use UTC, half-open intervals, intraday boundaries anchored at 00:00 UTC, daily closes at 00:00 UTC, weeks starting Monday 00:00 UTC, and calendar months. These are reproducibility conventions, not claims about a superior market session. Any later session-based observation is separate and explicitly timezone/DST aware.

Derive 15m/1h/4h/daily bars from complete traded 1m evidence where available. Aggregate OHLC in order and volumes in their original units; mark/index have no invented traded volume. Validate a fixed overlap against native higher-timeframe candles as an acquisition/aggregation check, not as a recurring second evidence vote. Differences must be classified (alignment, missing constituents, source revisions, units), not silently “fixed” with hindsight.

Native older coarse bars are acceptable for coarse context. Pin instrument, interval, timezone, completion and availability convention. OKX's documentation distinguishes UTC+8 and UTC+0 higher-period candle variants; the adapter must request/validate the intended boundary rather than assume an unsuffixed daily bar is UTC. This does not establish how far back each series is actually available. [External source E1]

## 5. Historical depth / corpus recommendation

**Keep the fixed evaluation window `[2025-09-01, 2026-09-01)` UTC. Extend context history separately.** Do not reset the project or use profitability to choose a new window.

Initial acquisition/storage plan, subject to verified venue availability:

| Purpose | Requested depth | Resolution and scope |
|---|---|---|
| Registered evaluation | Existing twelve-month target | 1m traded/mark/index as already planned; settled funding when genuinely available. Retain September unchanged. |
| Fine initialization | 30 complete days before evaluation start: `[2025-08-02, 2025-09-01)` | 1m traded history; required reference channels for active short-horizon dependencies. Prefer a reusable bounded pack, not repeated downloads. |
| Tactical/structural context | Two years before evaluation start, retained through the evaluation period | 1h traded series before the fine-history boundary; derive 4h/daily where applicable. No older 1m mark/index requirement by default. |
| Long-range location | Five years before evaluation start: request back to 2020-09-01 | Daily traded series for the same instrument where available; weekly/monthly derived. No fabricated pre-inception history. |

The context tiers overlap for verification but have one declared authoritative source per interval. They are not concatenated into duplicate observations. A resolution/source switch is part of the manifest and initialization policy. Derived aggregates crossing a tier boundary use an explicit compatible construction or start at the next complete interval; never double-count an overlap.

These depths are **engineering coverage defaults**, not minimum sample sizes proven to make trading effective. Thirty days of fine initialization does not validate a cycle theory. Five years is roughly sixty monthly observations, still a small, dependent sample for long-cycle claims. One evaluated year is useful for workflow and initial integrated diagnostics, not robust proof across all BTC regimes.

Require each future observation to declare its actual lookback, initialization method and readiness condition. The 30-day fine pack is an initial provision, not permission to label an under-initialized longer dependency ready. Older coarse context may initialize compatible state causally; it cannot initialize minute-level path features it does not contain. Recursive estimators need a documented initialization/error convention rather than an arbitrary “enough bars” claim.

Warmup produces derived context but no scored calls. Reset candidate/call state at the evaluation start for the initial protocol; disclose the initial boundary effect. Maintain state continuously across monthly storage chunks after that point. Calls near the final evaluation boundary remain unresolved or are followed through a separately declared outcome tail; never force a favorable terminal exit.

If the perpetual has less than the requested history, disclose the limitation. A separate BTC spot/reference series may support long-range context after a source decision, but must not be spliced into perpetual OHLC or treated as the same tradable instrument. Lack of five years of this exact contract must not block the replay performance release or all shorter-horizon adviser development.

Do not download years of 1m data merely to obtain monthly levels. No annual-cycle forecasting is authorized. Broader economic robustness can later use additional fixed evaluation windows chosen before inspecting their results; it is not a prerequisite to deliver the first usable adviser.

Keep bounded manifests and distributable data packs compatible with Foundation's repository/offline-reuse requirement. Measure pack size before deciding ordinary Git versus an explicitly approved pinned archive/LFS arrangement. Do not silently introduce paid storage, a remote database or a daily download requirement.

## 6. Replay/backtest execution architecture

### One causal kernel, several operational modes

Use a streaming source reader → ordered evidence iterator → incremental observable/derived state → dispatcher → adviser/lifecycle → output journal. In observation-only mode, the adviser stage is absent and clearly labeled.

The fast path is the normal kernel without animation waits, per-event persistence or unnecessary snapshot materialization. It is **not** a vectorized substitute that skips the evolving state/call path. Retain the current pure/reference implementation for small differential fixtures and investigations, not as a second production trader.

Changes required:

1. Persist a queued job before expensive preparation. Launch should return promptly. Verification, construction and warmup belong to the worker, with progress.
2. Build a reusable immutable feed cache keyed by source hashes, adapter version, ordering policy and availability policy. Validate source bytes at preparation, reuse that validation result within the job, and eliminate nested duplicate verification. A prepared source must remain read-only/pinned while consumed; do not trust filename or modification time alone as identity.
3. Stream bounded Parquet/record blocks and merge ordered channel streams. Initially day-sized partitions are sufficient. Do not materialize a full year as millions of Python/Pydantic event objects, a full delivery list and multiple JSON trees.
4. Validate/decode records at admission, then keep efficient bounded state. Materialize full public snapshots at checkpoints, explicit inspections and finalization; materialize only required views at reasoning boundaries. A changed compact internal representation must match reference semantics.
5. Maintain separate bounded histories and incremental aggregates by horizon. The adviser reads a cutoff-safe state interface, never the unrestricted source cache. Store source-backed longer history behind a prefix-aware query interface when needed.
6. Use bounded processing chunks and independent progress/control handling. Poll controls roughly every 250ms of wall time; persist progress no more often than necessary. Do not query PostgreSQL after every evidence item.
7. Read chart windows from immutable indexed evidence filtered by the **committed knowledge cursor**, including availability order for late records. Sampling frames must not omit audit records, infer missing bars, or reveal a future bar to the Owner during replay.

For the existing feed identity format, stream its exact canonical representation or cache the identity after a verified build; do not silently substitute a chain hash for `ordered_event_hash` or the current content digest. If a new partitioned manifest requires a different identity definition, version it and retain the old adapter/reader.

### Causality and evaluation separation

Outcome evaluation may incrementally consume subsequent evidence for already issued calls, but its state/results never feed the adviser during the same run. Original call geometry and revisions remain immutable. A separate later outcome pass is also allowed if bounded and observable. Every report identifies the outcome policy and unresolved/ambiguous cases. Capital, quantity, leverage, collateral and real order placement remain absent.

Run preparation knows the dataset's full size and quality report. That administrative metadata must not become trader knowledge: a later outage, final quality classification, future event count or full-period range must not leak into earlier reasoning. Only causally available quality events and approved initialization context enter the adviser.

### Multicore policy

Parallelize independent file hashing, decoding/normalization of partitions, source verification, report sections, and independent runs when memory permits. Parallel preparation merges into the single deterministic order. Start conservatively with two preparation workers and one sequential causal worker on a modest machine; measure before adding concurrency.

Keep the evolving single-instrument state, timer dispatch, scenario/call lifecycle and checkpoint commits sequential. Do not split one year into twelve independent trader months: that loses context and cross-month calls. Do not parallelize time slices of a stateful adviser and merge their advice afterward. Avoid introducing a distributed scheduler or a new analytics platform for 1.6 million annual bar events.

Local shutdown/restart resumes the job. Live catch-up reuses cached history, suppresses historical re-alerts, and requires a fresh reassessment before a reconstructed call becomes actionable. It does not pretend the application watched the market while off.

## 7. Persistence/checkpoint/audit design

**Fast historical evaluation does not need one durable `observation_deliveries` row per event.** Keep old rows readable for old runs; do not write them for every new fast run.

### Minimum retained record

Retain the immutable source/normalized evidence and feed manifest once; per run retain:

- Run identity, code/environment/configuration versions, source hashes, availability/order/clock policies and evaluation boundaries.
- A manifest of processed input ranges with contiguous start/end cursors, counts, first/last order keys and cumulative canonical input integrity commitment.
- Restorable checkpoints, each tied to the input prefix and output-journal boundary.
- Compact reasoning dispatch receipts, material observation/MarketView transitions, all candidate/call lifecycle changes, and evaluation records once those features exist.
- Operational phase history, controls, attempts, fencing generations, timing and diagnostics.
- Final integrity result, snapshot/state digest and terminal report/artifact manifest.

A chain/rolling digest is an integrity commitment, not evidence that the reducer implemented the right mathematics. Maintain independent counters/order checks and reference tests. Distinguish the digest of consumed input, the digest of state, and the digest of output history. Do not call them interchangeable.

Detailed event-by-event snapshots can be regenerated from retained source, pinned code/configuration and a nearby checkpoint as a visible diagnostic job. Preserve reproducible dependency locks and the build identity; a Git SHA alone is not an executable environment. Optional full trace mode is for short diagnostics, not routine history.

### Checkpoint contents

Persist enough to continue without replaying from time zero:

- Exact source partition/offset and global next cursor; last accepted total-order key; input integrity state and counts.
- Observable reducer state, per-channel quality/latest values and required bounded histories.
- Partial/completed horizon aggregates, current aggregation intervals, dependency readiness and freshness state.
- Dispatcher watermark, pending timers/IDs, dirty dependencies, and any partially consumed same-time dispatch boundary.
- Later: observations, MarketView/scenarios, candidates/calls, lifecycle/deadline state, evaluation accumulators and next deterministic output sequence.
- Output segment references/last sequence; state format/version, state digest and complete source/config compatibility fingerprint.

Do not serialize opaque language objects as the only checkpoint format. Use a versioned, validated representation. Verify hashes and compatibility before restoration. If a checkpoint is damaged, fall back to a previously verified checkpoint and replay the bounded suffix; if none is valid, fail explicitly or offer a visible rebuild. A digest detects corruption, not logical correctness; restoration equivalence is tested separately.

### Commit and publication protocol

For v0, keep bounded checkpoint state and small output records in PostgreSQL transactions. Keep bulk immutable evidence and optional larger output segments as files. This avoids introducing file/DB coordination unnecessarily for small records.

Where file segments are used: write and durably close a uniquely named temporary segment, publish it immutably on the persistent volume, then atomically commit its hash/reference, checkpoint and expected prior cursor in PostgreSQL under a fencing generation. A file written before a failed transaction is an unreferenced orphan; a committed manifest never references an unfinished segment. Retain and verify referenced files. A rename by itself is not a cross-resource transaction or proof of power-loss durability. Test crash behavior on the supported Docker volume setup.

Only the lease owner with the current monotonically increasing generation can commit checkpoints, output pointers or terminal status. Compare-and-set the expected preceding cursor/generation. Retries reuse deterministic record identities. Stale workers may not overwrite the final manifest even if their computation finishes after a reclaim. Finalization is staged/idempotent and published only after artifact checks and a fenced terminal commit.

External UI alerts come from committed outputs with stable IDs. No duplicate alerts after retry, refresh or restart. UI progress distinguishes computed and safely saved work if both are exposed; the primary replay cursor and inspectable chart are committed.

### Cadence and controls

Initial defaults: checkpoint when **either 2 seconds of active compute or 5,000 input events** have accumulated, whichever comes first, and at pause/step/termination. These are engineering controls, not semantic times. Split a expensive unit cooperatively; do not make 5,000-event batches uninterruptible once the adviser grows.

Target at most about two seconds of compute to redo after a crash, plus one bounded in-flight unit; require a measured hard operational bound of five seconds for normal workloads. Retain the latest two valid checkpoints and final state; sparse long-range inspection checkpoints may be retained separately. Disk growth should follow retained state/output policy, not repeated full raw-history copies.

Pause finishes a small safe boundary, commits and parks. Resume restores that checkpoint. STEP remains exactly one **source evidence event**, durably committed; display that definition. It may not change the thesis or advance a full candle. A future “next reasoning update” control is separate. If a same-time group is incomplete after STEP, its deferred scheduled reasoning stays pending and is checkpointed. Fast mode preserves this behavior; it does not redefine STEP as one batch.

Cancel commits the accepted prefix and produces a partial diagnostic report without launching full historical revalidation. During final publication, briefly show “Finishing current save” rather than pretend cancellation already occurred. Slow interactive mode may checkpoint more often, but has identical causal/decision outputs for the same prefix.

## 8. Validation strategy

Use three assurance layers. Do not downgrade correctness to a checksum and do not repeat the complete reference computation after every successful run.

| Layer | Required checks | When |
|---|---|---|
| Source/admission integrity | Immutable source and cache identity; schema/units; exact order; unique slot/event policy; availability; valid/quality separation; explicit missing-slot handling | On verified preparation/cache creation, with content integrity verification for each run's consumed artifacts |
| Runtime and terminal integrity | Prefix continuity/counts; monotonic order; admission cutoff; derived prerequisite readiness; contiguous output IDs; checkpoint/source/config compatibility; final state hash; final cursor/counts and artifact hashes | Incrementally during every run; bounded reconciliation at finalization |
| Reference assurance | Optimized vs pure state at multiple cutoffs, deterministic outputs, aggregation and dispatch semantics, faults/restarts, corruption and future-perturbation tests | Protected CI fixtures and engine changes; optional deeper diagnostic runs |

Every normal run verifies what it actually consumed, including all quality and auxiliary events. A materialized feed cache is checked against its manifest; cold preparation links it to verified source bytes. Cache corruption fails explicitly. Do not repeatedly parse and verify the same immutable input at launch, worker claim and finalization without a new trust boundary.

No-future assurance belongs at admission and dependency construction, plus protected adversarial tests. Check that every derived input's known-at/cursor is within the dispatch prefix; the output's known-at is no earlier than its latest prerequisite. Test that appending or changing future evidence leaves earlier observations and calls unchanged. Repeatedly scanning the same 240 histories after each event is not a stronger proof.

Each normal finalization reconciles expected versus consumed prefix, verifies checkpoint/output continuity and hashes, builds one final public snapshot, validates final artifacts and publishes a report. It does **not** reapply the entire source simply to call the result PASS. Label this accurately: **runtime integrity passed; engine reference-tested**. The existing phrase “independent validation passed” must not survive if it falsely implies a fresh independent replay on every run.

An optional Deep validation job independently replays the source and compares selected checkpoints, outputs and final state. It has its own progress/cancellation/report; failure flags the originating run's assurance without rewriting its original records. Use it when changing reducer/checkpoint serialization, investigating divergence, and periodically on a fixed diagnostic sample—not as an obligatory hours-long tax.

Before removing per-event snapshot checks, establish differential tests against the existing pure implementation on bounded protected fixtures, plus hand-calculated cases. Shared code can share bugs: include independent expected results for late data, ties, gaps, source boundaries, forming/complete aggregates, future leakage and OHLC ambiguity. Test batch sizes 1, small, default and randomized; pause/step/speed/checkpoint spacing must not affect economic outputs. Wall timestamps and checkpoint locations are operational differences, so whole report bytes across separate runs need not match; semantic digests must.

Normal-run assurance cannot mathematically prove arbitrary software correct. Its justified claim is pinned input integrity, checked causal invariants, verified persistence and deterministic behavior supported by reference/fault tests. State that scope rather than using “proof” to conceal it.

## 9. Performance targets

These are **release budgets to measure**, not predictions of achieved speed. Reference environment: local Windows/Docker, SSD-backed persistent data, at least four logical CPUs and 8 GiB available to Docker, without server hardware. Record actual allocation/CPU/storage so a smaller Owner machine is interpreted honestly. Do not require a hardware upgrade before fixing the present architecture.

Times below include cached-source checking, feed loading, replay and ordinary finalization/report, exclude network acquisition and optional Deep validation, and use max-speed compute with sampled UI. Report cold feed construction separately and also show total launch-to-report time.

| Workload | Desired band | Initial release ceiling on reference environment |
|---|---|---|
| Sep-sized observation month, 129,600 bar events plus actual other events | 30–90 seconds | **2 minutes** |
| Observation year, ~1.58 million bar events plus other events | 5–10 minutes | **15 minutes** |
| First integrated adviser month | 2–5 minutes | **10 minutes** |
| First integrated adviser year | 20–40 minutes | **60 minutes** |
| Normal final validation + report, observation month | 1–5 seconds | **10 seconds** |
| Normal final validation + report, year/adviser report | 5–15 seconds | **30 seconds**, with visible progress |

The adviser budgets are architectural reservations until its method exists. They are not a reason to skip reasoning events. Reserve performance by reusing context and bounded incremental state. A measured overrun requires a named bottleneck and bounded fix, not silent overnight work or arbitrary thinning of calls.

Cold source verification/build should target <=2 minutes for the month and <=15 minutes for a year, then reuse the cache. These are additional first-preparation costs, always visible. Network acquisition has no universal time promise: show measured rates, retries and coverage progress. No repeated download is allowed merely to run another evaluation.

Relative acceptance on the Owner machine: seek at least a **20× reduction in the reported month end-to-end time**, while meeting the reference ceiling on declared comparable hardware. Do not claim a speedup from an unmatched synthetic baseline. Record event counts and all phases for the actual Owner rerun.

Responsiveness: launch acknowledgement <=1 second; status/control acknowledgement <=1 second; visible phase/progress refresh <=2 seconds; pause/cancel applied normally <=2 seconds and <=5 seconds at a bounded safe unit; restart-to-resume target <=10 seconds with an intact checkpoint/cache, excluding an explicitly shown source recheck. Test these under CPU load.

Target <=2 GiB replay-worker memory for a year of observation, and <=4 GiB for the full basic app/DB worker stack on the reference configuration. These are budgets, not universal hard limits. Memory should plateau with bounded cache/history, not grow in proportion to all previously replayed event objects. Record peak memory, output/checkpoint bytes, SQL commit/row counts, snapshot count, events/s and reasoning dispatch counts. Display a simple elapsed/phase view to the Owner; include diagnostics in the copyable report.

Do not make noisy wall-clock thresholds the only CI gate. CI gates structural counts and deterministic correctness; bounded offline benchmarks record throughput. Full real-data runs remain Owner-launched through the application.

## 10. Long-operation progress / ETA / heartbeat UX

### A common durable job model

Use one operational job/phase contract for corpus preparation, replay, validation and reporting, even if workers remain separate. Separate **status** (queued/running/paused/terminal), **phase** (what work), **health** (alive/progressing/waiting/unresponsive), and **assurance** (not checked/passed/failed). Do not overload one string with all four meanings.

Persist phase/attempt ID, phase start, active elapsed, total wall elapsed, progress sequence and last-progress time, completed/total/unit when known, ETA estimate/basis when justified, worker heartbeat, lease generation, control state and current diagnostic message. Browser refresh attaches to this durable state. Downtime and pauses are not included in active-throughput estimates; total elapsed includes them and explains the difference.

| Phase | Honest progress denominator | ETA and control behavior |
|---|---|---|
| QUEUED | Queue position if known; otherwise no percentage | Waiting reason, elapsed waiting, cancel available. |
| PREPARING_SOURCE / DOWNLOADING | Completed fixed date windows/channels; pages/bytes as secondary counts | Window progress is coverage/work progress, not byte percent. Rate-limited/retrying shown explicitly. ETA only after useful throughput; otherwise unknown. Cancel at request/page boundary with bounded network timeout. |
| VERIFYING_SOURCE | Bytes hashed / manifest bytes; rows checked / known rows as separate substages | Throughput-based ETA per homogeneous substage; chunked cancellation. |
| BUILDING_FEED / INITIALIZING | Rows/partitions processed; warmup evidence or source-time coverage | Separate sorting/merge/indexing subphase if substantial. Unknown denominator gets activity count and elapsed, not an invented percentage. |
| REPLAYING / EVALUATING | Applied evidence / known total; simulated time; reasoning/output counts secondary | ETA from recent active throughput, reset after mode changes. Explicitly excludes unmeasured later phases. Pause/step/cancel supported. |
| FINALIZING | Output segments/checkpoints sealed / known total | Short atomic save may be indeterminate. Show elapsed and “Finishing current save”; never force 99%. |
| VALIDATING | Bytes/records/checkpoints checked / known work for current subphase | Weighted only where measured work units justify it; otherwise separate checks with an indeterminate active check. Cooperative cancel. |
| GENERATING_REPORT | Known sections/artifacts completed, or bytes emitted where meaningful | Section count is not automatically a time estimate. Show elapsed; ETA unknown until defensible. |
| COMPLETED / FAILED / CANCELLED | Final coverage and result | Terminal report or diagnostic report available; no perpetual spinner waiting for an optional export. |

Prefer a phase timeline plus **one current-phase bar**, with nested substages only when needed. Do not invent a globally weighted 0–100% bar. “Replay 100% — validating results” is honest. Completion belongs to the whole job only after report publication and integrity checks. Suppress unhelpful subsecond flicker but retain phase timing in the report.

An example `VALIDATING — 62% — 01:43 elapsed — ~01:02 remaining` is acceptable only if 62% refers to measured comparable work and the ETA is derived from its observed rate. Otherwise show `VALIDATING — checking checkpoint 8 of 12 — 01:43 elapsed — time remaining not yet known`. Reset/range unstable ETAs rather than showing false precision.

### Heartbeat is not progress

Run a lightweight job supervisor separately from CPU-intensive computation, using its own database connection. It renews a fenced lease and publishes liveness roughly every two seconds through preparation, validation and publication. The compute process emits progress milestones and responds cooperatively to controls. The supervisor verifies the child still exists; it must not mask a dead child with a cheerful heartbeat.

Use a lease comfortably above normal scheduling/DB jitter, initially 30 seconds, with measured thresholds. CPU usage is diagnostic, not proof of useful progress. A healthy supervisor with no compute milestones becomes **alive, no progress observed** after the phase-specific expected interval; long opaque work must expose smaller milestones or an explicit waiting reason. Only a detected timeout/fault triggers controlled interruption/reclaim.

Missing heartbeat means **worker unresponsive / awaiting recovery**, not “RECOVERING” until a new fenced attempt actually starts restoring. Database/API disconnection is its own state. Local PC sleep is an interruption to resume from, not a claim the worker continued. A paused job needs no active compute heartbeat to be healthy.

The shell may show degraded capability when a worker is genuinely unavailable, but validation activity must remain available and labeled VALIDATING. Retain a diagnostic snapshot even if report generation fails. “Copy report for chat” must work for queued, running, paused, interrupted, failed and cancelled jobs, with incomplete/unvalidated clearly stated.

## 11. Backtest/Workbench product terminology

Name the destination **Historical Workbench**. Present explicit run types:

- **Market replay — data and engine check**: available now. “Replays historical market evidence. No adviser or trade calls are evaluated.”
- **Adviser backtest**: visibly unavailable until implemented. Later this runs the full integrated adviser and call-outcome evaluation on the same engine.
- **Deep validation**: an optional diagnostic action attached to a run, not a competing trading product.

The primary launch button and run/report title use the selected type. Observation reports have call/outcome fields unavailable, never numeric zero that could be mistaken for an always-NO_TRADE trader. In the future, a real adviser producing zero calls is a measured result with its funnel/coverage diagnosis.

Keep the real evidence viewer distinct from the synthetic demo. Do not redesign the entire application in SR-003. Record broader Home, visual hierarchy and usability refinement as later product work; complete this job lifecycle and terminology now.

## 12. Treatment of the existing stuck run

**Preserve it as incomplete diagnostic evidence and create a new run using the same Sep-2025 dataset.**

Before migration, preserve its DB rows/checkpoint, configuration, available artifacts/logs, source binding and identities. Quiesce the old worker through controlled shutdown/fencing; do not let an old finalizer race the new system. Add an operational annotation linking the old run to the replacement: replay reportedly reached 129,600, terminal assurance/report incomplete. Do not rewrite its event identities, fabricate PASS or label it a completed new-engine benchmark.

The product should export a lightweight legacy diagnostic report from the persisted facts, including “terminal validation not completed.” This does not require regenerating every old delivery snapshot. If a legacy manifest is actually present, verify and report that fact rather than assume failure from the UI alone.

An optional later legacy finalization can be offered if cheap and requested, preserving the old engine identity and naming the new validator version. It is not a dependency for the performance release. Supporting arbitrary cross-version execution-state migration is unnecessary here.

Prepare/reverify the existing immutable dataset locally and build the new cache. No September network request is needed. The new run receives its own engine/configuration identity and serves as the performance acceptance run. The old elapsed time remains diagnostic, not a result relabeled under the new code.

## 13. What should change in WP-008-R1 before Claude implements it

The historical draft is a useful starting point, but replace its mandate with the architecture above through bounded packages. Specific dispositions:

| Draft requirement | Disposition |
|---|---|
| Many sequential events in memory, atomic periodic checkpoint | **Retain**, with time/work limits, restorable state and fencing generations. |
| Event-level delivery identities | **Retain** in canonical source/feed; durable raw delivery rows are not required to preserve them. |
| All delivery rows included in every batch transaction | **Remove for new fast runs.** Persist prefix/checkpoint integrity and semantic outputs instead. |
| Full snapshot/delivery construction inside every step | **Remove from the hot path**, not merely from terminal validation. |
| Recovery may rebuild all committed evidence | **Restrict to explicit fallback/diagnostics.** Normal restart restores a verified checkpoint. |
| Pure final-state re-derivation on every normal completion | **Replace** with layered runtime integrity and protected reference tests; optional Deep validation. |
| Heartbeat only addressed at finalization | **Expand** to all long phases, launch preparation, independent supervisor, truthful health and stalled-progress detection. |
| Existing full-cursor run must finalize under new implementation | **Remove as acceptance gate.** Preserve/export diagnostics; new run, same dataset. |
| Existing delivery-table API/UI assumptions | **Replace** with cutoff-filtered evidence reads and output-journal views; retain old-run compatibility. |
| No changes to any domain/artifact version | **Narrow.** Frozen evidence/DEMO contracts remain frozen; changed provisional operational artifact guarantees require an explicit revision/reader. No deceptive unchanged schema. |
| Timeframes deferred entirely | **Split.** Freeze causal clock/aggregation boundary decisions now; implement factual temporal substrate after performance acceptance, before adviser semantics. No strategy rules in R1. |
| Performance evidence mainly transaction-count reduction | **Expand** to snapshot counts, preparation, memory, restore, validation, output bytes and launch-to-report performance. |

A transaction benchmark can pass while the Owner still waits an hour. Acceptance must cover the whole path. Equally, do not spend another milestone building a general-purpose event platform: use the existing Python/FastAPI, React, PostgreSQL, Parquet and Compose stack, with focused internal refactoring.

## 14. Exact implementation package sequence after this review

These are ordered deliverables and release boundaries for Director disposition, not an executor task prompt. Package names are proposed to avoid conflating performance work with trading-method work.

| Order | Package | Bounded deliverable and exit |
|---|---|---|
| 0 | **Director SR-003 disposition** | Accept/modify decisions; reconcile Foundation/STATE/integrated plan/task/README and relevant contract notices. Preserve historical documents. Specify the one active package; do not leave the paused draft as competing instruction. |
| 1 | **WP-008-R1A — Observable job lifecycle and diagnosis** | Common phase/progress contract, durable prompt launch, supervisor/fenced lifecycle, copyable incomplete report, old-run preservation, targeted instrumentation. Short CPU-bound/offline checks prove no false recovery. This is not yet READY for a real-month retry. |
| 2 | **WP-008-R1B — Streaming replay and durable checkpoints** | Bounded source/cache reader, efficient sequential kernel, sparse persistence, complete checkpoint restore, cutoff-safe chart/audit queries, pause/step/cancel and idempotent artifact publication. Differential/fault tests accompany each change. No adviser or corpus redownload. |
| 3 | **WP-008-R1C — Assurance and performance acceptance** | Layered validator, optional diagnostic deep path, final reports/phase UX, bounded representative offline benchmark and structural gates. Director code review, then **READY FOR OWNER MARKET REPLAY**. Owner launches the new Sep run against existing data and copies its report. Close performance defect only from that evidence. |
| 4 | **WP-008-R2 — Causal multi-horizon substrate** | Versioned completion/known-at/clock contract, UTC aggregation, typed timers, dependency readiness, per-horizon bounded state, recorded dispatch boundaries and prefix-leakage tests. Fixed fixtures demonstrate the selected hierarchy without directional strategy logic. |
| 5 | **WP-008-R3 — Context corpus and evaluation presets** | Multi-resolution manifests/readers, context/fine initialization packs, source-overlap checks and continuous multi-chunk run support. Owner starts any substantial acquisition from the app; September reused. Register development/protected windows and warmup/outcome-tail rules before adviser outcomes. Missing optional long-range coverage is reported, not an indefinite gate. |
| 6 | **MP-001 — Bounded integrated method closure** | Complete the existing coherent adviser specification using the accepted clock: concrete professional observations/scenarios, candidate coverage, actionability and persistent lifecycle; cycle/news disposition; required lookbacks and timing semantics. No parameter/timeframe tournament. Optional gaps have explicit limited roles. |
| 7 | **WP-009 — Integrated adviser v0 and advisory semantic.v2** | Same engine, Home and Workbench integration, calls/reassessment, separate normalized outcome evaluation and copyable diagnostic report. No account/execution scope. Short engineering verification, then **READY FOR OWNER BACKTEST**. |
| 8 | **Owner Backtest A → bounded corrections** | Owner runs registered development preset; Director assesses correctness, practical call windows, coverage/frequency, rejection funnel and outcomes. Assign diagnosed changes; later protected/prospective checks. |

Do not delay R1 to acquire five years of data or resolve a cycle theory. Do not connect adviser reasoning before R2's clock/aggregation contract exists. Do not use R3 to browse future evaluated price paths or tune horizon choices. Significant Owner jobs remain in the application; executors use short deterministic fixtures and bounded engineering benchmarks.

## 15. Acceptance criteria for the performance hardening

R1 is complete only when all applicable gates below pass and limitations are explicit. Adviser-specific gates attach to WP-009; they are not a pretext to claim a trader exists now.

### Causal/deterministic behavior

- Existing source-event total order, identities, availability labels, traded/mark/index/funding roles and quality admission preserved; no silent event dropping, forward filling or price substitution.
- Fast, paced and one-event STEP agree with protected pure reference at selected prefixes/final state. Later adviser semantic outputs agree across pacing/checkpoint/batch settings.
- Adversarial fixtures cover tied times, delayed/out-of-order market times, gaps, corruption, duplicates, cancellation, end-of-source and source-partition boundaries. Future-suffix perturbations leave earlier outputs unchanged.
- Aggregation/dispatch fixtures before adviser integration cover close versus known-at, missing constituents, calendar boundaries, live prefix/timer receipts, stale dependencies and no-event expiry.
- Warmup, evaluation and outcome tail are separate; no future quality summary or uncommitted chart data crosses into adviser state or replay display.

### Durability/recovery

- Inject crash before/after checkpoint transaction, after segment publication before DB commit, during terminal publication, and during lease transfer. Observe no duplicate committed semantic outputs, no missing referenced artifact, and no stale-worker overwrite.
- Resume from a valid checkpoint without replaying the full prefix. Restore/corruption/fallback behavior is explicit and measured; DB failure does not silently lose already published advice.
- Pause/step/cancel meet responsiveness bounds; refresh and local restart preserve the run and its diagnostic report. Cancelling at 100% replay during validation is supported and does not imply successful completion.
- Old Sep run and dataset remain intact; old-run reader/diagnostic export works. New evaluation reuses the verified dataset without network acquisition.

### Structural performance

- No mandatory `observation_deliveries` row per event in new fast runs; DB rows/transactions track checkpoints, operational progress and semantic outputs.
- No full snapshot/hash per source event in the normal hot path or terminal validator. Instrument actual counts; don't merely assert complexity.
- Bounded source streaming and history caches; no full-year `fetchall()`/Python event tuple/JSON history duplication on the critical path. Memory reaches a bounded working plateau on a representative year-sized offline stream.
- Normal final validation does not replay the complete history. Deep validation is explicit and separately observable.
- Report per-phase duration, source/cache state, CPU/memory, event/dispatch/checkpoint/snapshot counts and bytes. Meet the reference month/year observation ceilings or present a specific failing gate to the Director—no unqualified “performance fixed.”

### Owner workflow

- Every significant phase is visible and retains elapsed time across refresh. Unknown percentage/ETA is explicitly unknown; no 100% whole-job display while validation is unfinished.
- CPU-bound validation longer than the lease duration remains alive, progressing and VALIDATING. A live but stuck child, dead child, DB outage and actual reclaim produce different truthful states.
- In-progress, failed, cancelled and completed runs all provide Copy report plus Markdown/JSON. Failed final report generation still leaves a compact operational diagnostic export.
- Historical Workbench names observation-only runs accurately. Chart playback remains usable without slowing computation to animation speed; detailed history remains inspectable.
- The Owner's new September launch reaches a terminal result and report, with actual phase timings and validation scope. The Director compares it with the reported baseline. Executors do not perform the substantial historical evaluation invisibly in CLI.

## 16. Questions, if any, that genuinely require Owner choice

**None blocks this architecture.** The Owner has already chosen local intermittent operation, manual execution, persistent calls and application-operated tests. Exact hardware can be captured automatically and confirmed in the diagnostic report; it is not a reason to ask the Owner to design the engine.

The remaining professional evidence questions are bounded:

- The exact causal structure, trigger, invalidation, material-change predicates and lookbacks need MP-001's coherent method specification. The infrastructure can implement their scheduling interfaces now without inventing the rules.
- Cycle/timing concepts need causal definitions and source-supported decision roles; monthly bars or five years of history alone do not provide them. Keep that lens explicitly limited/unavailable until bounded closure, without blocking all calls.
- News/event integration needs historical as-known schedules/publications/revisions and an explicit decision role. Current news cannot enter past decisions; absence of coverage is not “no news.”
- Historical venue/instrument coverage and native/coarse compatibility require a bounded data capability check. This determines obtainable context, not which timeframe had the best backtest.
- Human entry usability at minute resolution and the declared delay/cost assumptions need later integrated evaluation. If minute bars cannot assess a case, mark it ambiguous; do not invent an intraminute sequence or add tick infrastructure speculatively.

No additional literature search is needed to decide that evidence, reasoning, checkpoints and UI have different clocks; that several correlated horizons are not independent votes; or that repeating full snapshots and durable rows per event is unnecessary. The selected horizon roles can be implemented now as versioned defaults. Their profitability and precise method predicates remain unproven.

### Evidence references

All repository references below are pinned to the reviewed main unless otherwise stated:

- [Foundation and authority](https://github.com/C-Gian/algorithmic-trader/blob/009c3420b588f2f0422d08fbe5d92e8ddf88b15f/FOUNDATION.md), [STATE](https://github.com/C-Gian/algorithmic-trader/blob/009c3420b588f2f0422d08fbe5d92e8ddf88b15f/STATE.md), [integrated plan](https://github.com/C-Gian/algorithmic-trader/blob/009c3420b588f2f0422d08fbe5d92e8ddf88b15f/delivery/FOUNDATION-V3-INTEGRATED-PLAN.md), [Owner realignment](https://github.com/C-Gian/algorithmic-trader/blob/009c3420b588f2f0422d08fbe5d92e8ddf88b15f/strategic_reviews/OWNER-REALIGNMENT-2026-09-30.md).
- [SR-003 authoritative brief](https://github.com/C-Gian/algorithmic-trader/blob/009c3420b588f2f0422d08fbe5d92e8ddf88b15f/strategic_reviews/SR-003-REPLAY-CLOCK-PERFORMANCE-BRIEF.md); [actual WP-008-R1 draft in prior commit](https://github.com/C-Gian/algorithmic-trader/blob/d1d85d75b60b6fdd4860ec6607ec89aa6fbe3d46/task.md).
- Code findings: [observe core](https://github.com/C-Gian/algorithmic-trader/blob/009c3420b588f2f0422d08fbe5d92e8ddf88b15f/src/algotrader/observe/core.py), [worker](https://github.com/C-Gian/algorithmic-trader/blob/009c3420b588f2f0422d08fbe5d92e8ddf88b15f/src/algotrader/observe/worker.py), [artifacts/validation](https://github.com/C-Gian/algorithmic-trader/blob/009c3420b588f2f0422d08fbe5d92e8ddf88b15f/src/algotrader/observe/artifacts.py), [feed state](https://github.com/C-Gian/algorithmic-trader/blob/009c3420b588f2f0422d08fbe5d92e8ddf88b15f/src/algotrader/feed/state.py), [feed adapter](https://github.com/C-Gian/algorithmic-trader/blob/009c3420b588f2f0422d08fbe5d92e8ddf88b15f/src/algotrader/feed/adapter.py). Also inspected the corresponding ordering/contracts, source loading, control/API, DB migrations, marketdata dataset, corpus job, evaluation API/report and Backtest/health presentation paths.
- [RP-001 Director disposition](https://github.com/C-Gian/algorithmic-trader/blob/009c3420b588f2f0422d08fbe5d92e8ddf88b15f/research/first_trader/RP-001-DIRECTOR-REVIEW.md): causal lessons retained; old 1h/5m/1m/120-minute conventions and pullback-only mandate not governing.
- [LIB-008 dossier](https://github.com/C-Gian/algorithmic-trader/blob/009c3420b588f2f0422d08fbe5d92e8ddf88b15f/source_notes/LIB-008-WHICH-TREND-IS-YOUR-FRIEND.md): the underlying source's filter-redundancy and horizon distinctions support avoiding duplicate evidence credit. Its cross-asset findings do not validate the BTC intervals chosen here. [LIB-020 dossier](https://github.com/C-Gian/algorithmic-trader/blob/009c3420b588f2f0422d08fbe5d92e8ddf88b15f/source_notes/LIB-020-TRADING-AND-EXCHANGES-MARKET-MICROSTRUCTURE-FOR-PRACTITIONERS.md): source-level market-microstructure distinctions inform the limits of candle evidence; no legacy project interpretation is adopted.
- **E1:** [OKX official API documentation — historical candles](https://www.okx.com/docs-v5/en/#rest-api-market-data-get-candlesticks-history), checked 2026-10-01, for UTC+0/UTC+8 interval variants. Availability of any specific five-year instrument dataset remains unverified.

### Final disposition requested from the Director

1. **Architecture:** one streaming causal engine, hybrid reasoning clock, bounded incremental state, restorable checkpoints, sparse durable outputs and fully observable jobs. Preserve evidence integrity; remove per-event durable/snapshot coupling.
2. **WP-008-R1 change:** retain sequential batching and control semantics, but remove mandatory delivery rows, full-prefix recovery and routine full revalidation; add preparation/cache streaming, fencing, truthful phase UX and new-run treatment of September.
3. **Exact order:** disposition → R1A job lifecycle → R1B streaming/checkpoints → R1C assurance/performance → Owner September replay → R2 temporal substrate → R3 context corpus/presets → MP-001 coherent method closure → WP-009 adviser/semantic.v2 → Owner Backtest A.
4. **Acceptance:** protected causal/reference/fault tests; no per-event full snapshots or DB rows; bounded recovery/memory; all phases observable; reference observation month <=2 minutes and year <=15 minutes; terminal month validation/report <=10 seconds; Owner rerun produces an honest report using existing data.
5. **Decidable now:** 1m evidence is retained; 15m setup, 1h tactical, 4h/daily broad and weekly/monthly contextual roles; minute-level active-call monitoring; material events/timers between closes; UTC aggregation and explicit cross-horizon relationships. No 30m/45m/annual method layer is necessary now.
6. **Evidence still needed:** exact professional predicates/lookbacks, source-grounded cycle/event roles, obtainable older instrument history and eventual entry/delay realism. These are bounded method/data decisions, not blockers to the replay architecture and not permission for another open-ended research programme.
