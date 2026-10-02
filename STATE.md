# Project State

Updated: 2026-10-03 — R1C implemented by the executor; Director review pending

## Authority and active direction

Canonical directive: **FOUNDATION.md v3.1**. The Owner's direct clarification supersedes the SR-002 mandatory pullback scope and RP-001 completion gate. Historical ACCEPTED/READY/HOLD labels cannot reactivate them.

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

### WP-008 — Owner Evaluation Workbench + Corpus Bootstrap

Accepted implementation:
- `a14f58bde1f00508f234c8ccba9d08f98f57d71f`

Acceptance evidence:
- one fast-forward implementation commit over `18638b23f7daaa9e587808f0d032473a4fa30da5`;
- GitHub Actions run `36773558450`: `checks` SUCCESS and `compose-smoke` SUCCESS;
- 308 non-E2E tests and 10 E2E tests reported green;
- all five accepted/frozen schema baseline blobs are byte-identical to the WP-008 base;
- corpus plan target is exactly `2025-09-01 → 2026-09-01 UTC` with twelve calendar chunks and only `btc-okx-2025-09` enabled;
- Prepare queues a durable PostgreSQL job owned by a separate corpus worker; the browser does not own acquisition;
- verified bindings are reused without network, and exact matching local datasets can be adopted without network;
- acquisition uses the accepted official-OKX marketdata path, verifies before binding and never creates a second market-data format;
- cancellation/restart semantics are explicit and preserve finalized immutable datasets;
- the Backtest page reuses the accepted observation replay rather than forking a second replay/backtest engine;
- completed/cancelled/failed runs produce deterministic Markdown/JSON reports with `Copy report for chat`;
- adviser/MarketView/call/outcome metrics remain UNAVAILABLE/null rather than fabricated or zero;
- fast chart display is sampled while backend causal event processing remains complete;
- no trader logic, `semantic.v2`, P&L strategy evaluation or real Sep-2025 acquisition was performed by the executor.

Accepted limitations to measure on the Owner machine:
- real Sep-2025 acquisition throughput/ETA is not yet measured;
- a month is expected to produce roughly 130k feed events, and the current observation worker commits one transaction per event and re-derives state for terminal validation, so replay may take many minutes;
- historical acceptance note: at WP-008 this was a measurement gate; the subsequent Owner run now establishes a product-blocking performance defect (SR-003);
- storage mechanism for the eventual reusable corpus pack remains undecided until measured month size is available;
- local startup catch-up and the real adviser remain pending.

## Current action

**WP-008-R1A is ACCEPTED at `0919001fb689909080e139801641eb4c7105702f` for the operational slice. R1B correction is ACCEPTED at `9d814ec` for the structural slice. WP-008-R1C — Assurance and performance release gates is the only active implementation package (`task.md`); executor implementation delivered, Director review pending.** NOT READY FOR OWNER MARKET REPLAY until Director release acceptance.

Executor evidence (base `fb19de247350f205ad8c9da2cb18adeb7ea885b6`, final `66a2dce90619848776e891e7f50f0f8440d95eb4`; claims below are subject to the Director findings):
- shared operational contract `algotrader.ops.v1` (`src/algotrader/ops.py`): separate status / phase / health / assurance; current-phase-only ETA; phase spans with active vs wall time;
- durable observation/evaluation launch: `ObservationLaunch` envelope, identity/total PENDING until worker-owned PREPARING_SOURCE / VERIFYING_SOURCE / BUILDING_FEED persist the verified config before the first causal step; cheap source preview; preparation errors are visible failed runs;
- supervisor + separate compute process (`observe/worker.py`, `observe/job.py`), heartbeat 2 s / lease 30 s; lease renewed only while the compute process exists; monotonic `lease_generation` fencing of every durable write (observation and corpus, incl. corpus binding); generation-scoped immutable artifact publication (`g<generation>/`) before the fenced terminal commit;
- distinct health: progressing, waiting, alive_no_progress, compute_lost, unresponsive, recovering (only while a new generation restores), suspended, finished; API 503 `disconnected`; supervisor DB outages logged;
- cooperative progress/cancellation hooks in verification, feed build, prefix rebuild, serialization and validation (mathematics unchanged); cancel during VALIDATING at full cursor -> CANCELLED with INCOMPLETE assurance;
- diagnostic Markdown/JSON + Copy for every status (observation, evaluation, corpus), including missing manifest and failed publication; terminal evaluation reports remain byte-deterministic;
- migration 6 (additive); pre-upgrade nonterminal replays get an additive operational suspension, never claimed/finalized, exportable read-only; Owner upgrade procedure in README (stop old containers first, never `--volumes`);
- `observe.v1` revision 2 (optional additions; revision-1 artifacts readable); `semantic.v1`, `marketdata.v1`, `feed.v1`, `recorder.v1` baseline bytes unchanged;
- UI: Historical Workbench (route `#backtest` kept), explicit run types (Market replay available, Adviser backtest unavailable, Deep validation planned), phase timeline + current-phase bar, honest PENDING/unknown fields;
- local checks: 320 non-E2E + 10 E2E tests green on a disposable PostgreSQL 18.6, TypeScript typecheck/build green. Compose smoke deferred to CI (the Owner's live stack runs on the executor machine);
- remaining costs unchanged by design (R1B/R1C): eager feed build with duplicate verification, one transaction + delivery row + full snapshot per event, full prefix rebuild on restore/resume, full terminal re-derivation. Re-derivation after an already requested cancellation is an R1A control defect to correct, not a cost deferred to R1B.

R1A correction (executor evidence reviewed and accepted for bounded operational scope; base `adcf127`, final `0919001`):
- bounded cancellation: after an observed cancel the job finishes from config + committed checkpoint only (no prefix load, source reload or re-derivation), in every phase incl. paused/resumed and FINALIZING/VALIDATING/GENERATING_REPORT; the final publication rename + terminal commit run under the replay row lock (the documented atomic boundary), so a cancel reaching the lock first prevents a COMPLETED publication;
- measured on the offline fixture: cancel after 20+ committed events -> CANCELLED in 0.14 s (separate compute process under per-event CPU load) / 0.28 s (inline), 0 deliveries re-derived, 0 delivery rows loaded, no source re-verification; paused/resumed cancel at cursor 8 -> 0.13 s with zero reference work; terminal-phase cancels finish CANCELLED/INCOMPLETE without a COMPLETED publication;
- ETA: replay window starts at REPLAYING (not at claim), resets on resume/pacing change, labelled as wall-clock at configured pacing; substage/unit/total/phase/generation changes start a new rate window; fixture: ETA 5.2 s vs pacing-implied 4.6 s after 5.1 s preparation;
- timing: explicit wall / waiting / active per span, declared pacing waits excluded from active, interrupted spans unmeasured (null, counted, never zero), terminal-phase text follows the actual cursor and separates completion from assurance;
- checks: full non-E2E + E2E suites, web typecheck/build, and an isolated Compose smoke (separate project, image tag, port and volumes; the Owner stack/image/volumes verified untouched). Schema baselines unchanged by the correction (no contract revision).

Director evidence: CI run `37038947330` has successful `checks` and `compose-smoke` jobs. Source inspection found unbounded partial-cancellation finalization and misleading phase ETA/timing. A small stdlib-only numerical check reproduced ETA 110 s versus 10 s when preparation is included; no full local suite or Owner data/stack was used. These initial findings are closed by the correction review in `delivery/WP-008-R1A-DIRECTOR-REVIEW.md`.

Director closure: independently confirmed CI `37044401955` checks/compose-smoke SUCCESS, inspected correction source and regressions, and executed small stdlib timing/ETA checks. Schema-related files remain byte-identical to the correction base. Full local suites and reported timings were not independently rerun. R1A acceptance is not a performance release; remaining large-input serialization/control bounds belong to R1B/C. The acknowledged executor no-op pull violated AGENTS; the rule now explicitly prohibits startup/no-op pull habits.

Accepted R1B scope: bounded immutable feed/cache, one incremental causal kernel, sparse committed ranges, directly restorable versioned checkpoints and committed-prefix inspection. No real-month retry until R1C review.

R1B executor evidence (base `17b5720`; Director acceptance pending):
- streaming dataset adapter + streaming recorded bridge (identical events to the reference builders); immutable feed cache with bounded external sorts, exact canonical content identity / ordered-event hash, SHA-256-pinned gzip partitions, rolling prefix commitment, atomic publication, quarantine on corruption, verify-once trust boundary (cold 1 verification, warm 0);
- one incremental kernel on the accepted reducer; snapshots only at checkpoints; explicit JSON restorable state with fingerprint; checkpoints = one fenced CAS transaction with a compact range + restore point (2 retained + terminal); direct restore with bounded-suffix fallback and visible failure without a valid point;
- committed-prefix cache inspection (bounded windows); bounded terminal reconciliation `observe.stream-reconciliation` v1 (explicitly not reference equivalence); migration 7 (additive, suspends pre-R1B nonterminal runs); no observe contract revision;
- tests: differential digests at every committed cursor across checkpoint cadences 1/3/7/5000 and paced mode; restore at cursors 1/13/30/60; crafted ties/late arrival/gap/rejection/partition boundaries/end of source with a hand-expected order; duplicate-slot rejection; future-suffix perturbation; cold/warm cache; partition/manifest/source tampering; interrupted build; restore-point corruption/fallback/no valid point; DB failure inside a checkpoint; stale generation and cursor CAS; structural scaling (4,323 vs 17,292 events: Python-heap peak 15.0 vs 16.1 MB, transactions = checkpoints + 1, 0 delivery rows) and direct restore at 8,000/17,292;
- bounded synthetic measurement (Windows, separate compute process): ~3,700-4,300 events/s replay, cold cache build 2.3 s / 17,292 events, reconciliation 0.08 s; not a month/year budget claim.

R1B correction (executor evidence reviewed and accepted for structural scope; base `418d033`, final `9d814ec`) for `delivery/WP-008-R1B-DIRECTOR-REVIEW.md`:
- bounded cold preparation: disk-backed exact sqlite indexes for absent slots (incl. unsorted Parquet) and raw-page classification; recorded first-completion dedup on disk, exclusions spilled and hash-pinned, lifecycle first/max only; streaming request-log verification with incremental dataset identity; external sort with bounded fan-in (multi-pass); hooks in every scan/no-yield stretch; all handles closed before cleanup;
- verified-byte boundary: private source snapshot, verified once, the only input to normalization and source facts;
- trusted receipts (migration 8) written after fsynced publication; deterministic cache manifests; warm launches require a matching receipt; compatible manifest alterations and receipt-less caches are quarantined and rebuilt to the receipt;
- tests (`tests/test_stream_bounds.py`): long-gap + shuffled Parquet + multi-pass merge reference-exact; recorded duplicates/exclusion exact vs an independent copy of the accepted bridge; fresh-process heap/RSS for increasing gaps and duplicates; cancellation in five no-yield stages with nothing left behind; post-verification source mutation (manifest unchanged) never becomes cache evidence; pre-snapshot data/manifest mutation rejected; recording report mutation after snapshot ignored; compatible source_facts / feed metadata / partition hash / final commitment alteration rejected on a NEW warm run; crashes before/after the publication rename and before the receipt commit; receipt with vanished cache reproduced;
- local: 366 non-E2E + 10 E2E, web typecheck/build, isolated Compose smoke.

R1C executor evidence (base `d2ee918`; Director acceptance pending):
- assurance: `observe.stream-reconciliation` v2 (migration 9 adds per-range `snapshot_digest`/`state_sha256`): contiguous positive ranges and strictly ordered bounds, exact consumed-input re-hash with the input commitment recomputed at every range boundary, terminal state SHA-256 + snapshot digest, cache/receipt/run pin, exactly-once consumption for completed runs, separate input/state/output commitments; cancelled/interrupted -> INCOMPLETE; scope "Runtime integrity verified, engine reference-tested … no independent reference replay was performed in this run"; replay loop refuses admission discontinuity; R1A/R1B validator claims preserved;
- artifact publication fsyncs staged files and (POSIX) directories, then re-hashes every manifest artifact before reference; diagnostics re-hash referenced artifacts ≤ 64 MiB; Windows directory fsync remains unproven;
- Deep validation `observe.deep-reference` v1: separate durable job table `observation_deep_validations` (one active per run), claimed by the existing worker with fencing generation, phase timeline, health, pause/resume/cancel, resumable saved state (5,000 events / 2 s), Markdown/JSON/Copy report at every status; independent sequential reducer fold over the receipt-checked canonical cache compared at every range boundary and restore point; canonical-cache scope disclosed (not a source audit; reducer shared); mismatch -> persistent linked assurance warning in run detail, evaluation view and copied diagnostics; originating run never modified; never auto-launched;
- controls/durability (`tests/test_controls.py`): 1 MiB byte-level hooks in snapshot copy and single-file hashing; measured control application ≤ 0.7 s in snapshot copy, source hashing, gap walk, external merge, replay, reconciliation, report, pause and STEP; acknowledgements ≤ 0.55 s; progress age ≤ 0.1 s; lost cache rebuilt to its receipt, lost cache + changed source fails safely, lost/corrupt artifacts reported; `tests/test_assurance.py`: tamper classes, partial publication, Deep match/mismatch/cancel/pause/resume/restart/unsupported/lost cache;
- structural benchmark `scripts/bench_observe.py`, evidence `delivery/evidence/WP-008-R1C-BENCHMARK.md`: synthetic month (129,690 events) warm 31.4 s, terminal 0.84 s, cold prep 36.8 s; year component (1,576,800 events) replay 326 s, terminal re-hash 6.8 s, cache build 157 s (verification not included); all six reference gates pass on this machine; a first run with tracemalloc active failed the year replay gate (984 s) and is retained with its root cause;
- UI: Deep validation listed as implemented per run with its scope; Deep validation panel in Historical Workbench and Replay Lab; committed vs computed cursor; current assurance headline/warnings; reports include worker host (OS, CPU, logical CPUs, RAM, cgroup limits);
- proposed Owner procedure (README) for the replacement September Market replay, pending Director release acceptance.

SR-003 review is now retained at `strategic_reviews/ASTRA-SR-003-REPLAY-CLOCK-PERFORMANCE-REVIEW.md`. Director disposition: `strategic_reviews/SR-003-DIRECTOR-DISPOSITION.md`, ACCEPT WITH MODIFICATION. This is documentation/architecture acceptance, not an implemented performance fix or a reproduced benchmark.

Confirmed base: `009c3420b588f2f0422d08fbe5d92e8ddf88b15f`. Director inspected relevant source and the historical R1 draft; no runtime tests, benchmarks or Owner artifacts were accessed. Current code still has per-event full snapshots/transactions, prefix restore and expensive terminal revalidation. R1A makes operation trustworthy/observable; R1B/C remove those costs and close assurance/performance.

Owner-reported September evidence: CLEAN preparation; 129,600 events; roughly one hour replay plus at least twenty minutes validation without visible terminal report; false stalled/RECOVERING health. Preserve dataset, old run, bindings and artifacts; no redownload, automatic salvage or new-engine relabeling. Verify actual manifest presence before describing local terminal state.

Release sequence: R1A -> R1B -> R1C -> Owner September Market replay -> R2 causal temporal substrate -> MP-001 integrated method closure -> R3 method-required context/presets -> WP-009 adviser -> Owner Backtest A. Only task.md authorizes implementation; all later packages are planned. R1A completion is READY FOR DIRECTOR REVIEW, not READY FOR OWNER MARKET REPLAY.

Initial horizon roles and provisional context requests are versioned conventions, not profitability results. Final data depth depends on method requirements and available source history. No new adviser/semantic.v2 or long historical CLI evaluation is authorized.

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

The Owner prepares the current checkout before launching the executor. Executors inspect that prepared base and do not pull; see AGENTS.md.

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

## R1B Director review — 2026-10-02

Historical initial review: implementation `464f449e5961e240eab588876d21ab1bdd444145` was **CHANGES REQUIRED**; the later `9d814ec` correction closes these findings. CI `37052483628` checks/compose-smoke independently confirmed SUCCESS; executor reports 348 non-E2E + 10 E2E, fixture timings/memory not independently rerun. Schema-related files have no diff from the base.

Retain kernel/sparse persistence/direct restore and short differential evidence. Initial R1B defects (closed by the correction below): input-sized in-memory preparation sets/lists and unbounded external-merge fan-in; source bytes mutable between verification and normalization; compatible cache-manifest alterations accepted on a fresh warm launch without a trusted prior pin. Independent stdlib probes of actual extracted code accepted changed compatible cache facts and showed 10 simultaneous spill readers for 20 records/block2. See `delivery/WP-008-R1B-DIRECTOR-REVIEW.md` and task.md. No full local suite or Owner stack/data accessed. At that initial review R1C and Owner September retry remained inactive; the current action and correction closure below supersede this activation status.

## R1B correction accepted; R1C activated — 2026-10-02

Director accepted `9d814ec957e17fc33c1fcfbfb96034844e416444` after source inspection of private verified snapshots, trusted PostgreSQL cache receipts, deterministic durable publication and bounded disk-index/multipass preparation, plus the added regressions. CI `37065434955` checks/compose-smoke independently confirmed SUCCESS. Executor reports 366 non-E2E + 10 E2E and fresh-process memory measurements; Director did not rerun full suites or Windows measurements. Independent actual-sorter stdlib probe passed (100 records, block2, fan-in3; max 3 readers, 3 merge passes). Schema-related files unchanged from correction base.

This closes the earlier `464f449` findings; see the closure in `delivery/WP-008-R1B-DIRECTOR-REVIEW.md`. R1C now closes layered assurance, explicit optional Deep validation, representative long-unit control/durability tests and reproducible structural performance gates. Directory fsync on Windows remains unproven; metadata/disk growth remains disclosed. No achieved month/year performance or Owner improvement is claimed. Owner September retry still blocked until Director R1C release acceptance.
