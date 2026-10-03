# Delivery history — M3 to the September Market replay check

Status: **HISTORICAL RECORD — not current status or work authorization.**
Moved: 2026-10-03 by WP-010 from `STATE.md` and `README.md` at `e9c01b9`. The text below is preserved verbatim (only heading levels are shifted); words such as *current*, *active*, *pending* or *not authorized yet* describe the moment each entry was written and are superseded.

Current status: [STATE.md](../STATE.md) · current task: [task.md](../task.md) · operation guide: [README.md](../README.md) · product authority: [FOUNDATION.md](../FOUNDATION.md).

Paths quoted in backticks below are relative to the repository root. Evidence referenced by these entries:
- Director reviews: [WP-008-R1A](WP-008-R1A-DIRECTOR-REVIEW.md), [WP-008-R1B](WP-008-R1B-DIRECTOR-REVIEW.md), [WP-008-R1C](WP-008-R1C-DIRECTOR-REVIEW.md);
- benchmark evidence: [R1C benchmark](evidence/WP-008-R1C-BENCHMARK.md), [gate inventory v2](evidence/WP-008-R1C-benchmark-gates-v2.md);
- SR-003: [Director disposition](../strategic_reviews/SR-003-DIRECTOR-DISPOSITION.md), [Astra review](../strategic_reviews/ASTRA-SR-003-REPLAY-CLOCK-PERFORMANCE-REVIEW.md);
- RP-001: [Director review](../research/first_trader/RP-001-DIRECTOR-REVIEW.md), [real labeling progress](../research/first_trader/cases/REAL-LABELING-PROGRESS.md);
- plan: [Foundation v3 integrated delivery plan](FOUNDATION-V3-INTEGRATED-PLAN.md).

## Closure of the September Market replay check — 2026-10-03

Recorded by the Director in `task.md` (WP-010) from the Owner's copied terminal report: evaluation `eval-20261003T091928-a7eb00`, replay `obs-20261003T091928-363a3d`; COMPLETED; coverage COMPLETE 129600/129600; runtime assurance PASSED; `observe.stream-reconciliation` v2 PASS 9/9; trusted receipt/cache/run pin matched; entire feed consumed; elapsed 60.4 s; 27 committed transactions; zero delivery rows; zero recoveries. Reviewed by the Director, not an independently rerun benchmark; no Deep validation of this run; no adviser or trading performance evaluated. The original replay performance incident is closed. The UX pass `d8144ad` has independently green CI `37116003888`.

## From STATE.md — WP-008 acceptance (2026-09/10)

#### WP-008 — Owner Evaluation Workbench + Corpus Bootstrap

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

## From STATE.md — SR-003 R1A/R1B/R1C current-action record

### Current action

**WP-008-R1A is ACCEPTED at `0919001fb689909080e139801641eb4c7105702f` for the operational slice. R1B correction is ACCEPTED at `9d814ec` for the structural slice. R1C correction `99e0ca5` is ACCEPTED for the month-only Owner check. No implementation package is active.** **READY FOR OWNER MARKET REPLAY — SEPTEMBER 2025 ONLY** (task.md).

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

R1C correction executor evidence (base `3281303`, implementation under review `6745117`; Director acceptance pending), for `delivery/WP-008-R1C-DIRECTOR-REVIEW.md`:
- receipt: `cache_receipt_and_pin` now requires a trusted receipt. Absent receipt, or a receipt whose manifest SHA-256 / event count differs from the cache and run pin, fails the check and the assurance (FAILED, never PASS). Validator id/version unchanged (v2 corrected); stored reports and readers keep their recorded check details. Regressions cover direct validation (absent / mismatched manifest / mismatched count) and a real run whose receipt is deleted after preparation: COMPLETED, assurance FAILED, only that check failing, warning headline;
- Deep terminal boundary: `DeepJob._finish` commits under `SELECT … FOR UPDATE` of the fenced diagnostic row, the same lock `deep.control` takes. A cancel that wins the lock turns COMPLETED/MATCH into CANCELLED/INCOMPLETE and keeps the exact covered/target events. A cancel after the commit is rejected (409, already terminal). A cancel seen at PREPARING_SOURCE or VALIDATING entry finishes without reference work. A stale generation writes nothing. Regressions: cancel at PREPARING_SOURCE / VALIDATING / GENERATING_REPORT entry, just before the lock, held lock with an uncommitted cancel, concurrent cancel blocked by the held terminal lock then rejected, after-commit rejection, stale generation. Each also checks report determinism and that the originating run row and all artifact bytes are unchanged;
- assurance summary: runtime (the run's own validation) and reference (latest Deep validation) are reported as separate fields and headline parts. A failed/incomplete/not_checked runtime result stays in the headline and in a warning even with a Deep MATCH. Mismatches warn even when found before a stop. A cancelled latest Deep validation shows INCOMPLETE and names any earlier match only as earlier. Partial Deep coverage is a limitation. The run diagnostic report and UI show both lines. Regressions: failed runtime (receipt deleted, later restored) + Deep MATCH; cancelled run (INCOMPLETE runtime) + prefix-only Deep MATCH; cancelled Deep after a preceding MATCH;
- the Workbench evaluation report now lists `cache_receipt_and_pin`, `completed_consumed_entire_feed` and any failed check with their recorded details, so the Owner can compare the committed cursor with the run's own verified total;
- 12 of the 18 assurance tests fail on the reviewed `6745117` code and pass on the correction. Some fail only because the new test seams did not exist there;
- benchmark gate inventory: evaluator v2 in `scripts/bench_observe.py` splits month application gates (PASS only within limit **and** completed/passed run), annual component comparisons (not gates) and annual application gates (NOT_MEASURED / PENDING). `--evaluate-only` re-evaluates stored raw reports without measuring. `delivery/evidence/WP-008-R1C-benchmark-gates-v2.{json,md}` is computed from the unchanged clean raw report. Both raw JSON files, including the traced first run, are kept with their original v1 labels. `tests/test_bench_gates.py` pins this. No benchmark rerun: the changed code paths (receipt comparison, Deep terminal lock, summary text) do not affect the measured month path materially;
- proposed Owner handoff: **month-only September Market replay**, with annual readiness explicitly pending (README). Not READY FOR OWNER MARKET REPLAY before Director acceptance;
- local checks on a disposable PostgreSQL 18.6 container (separate name/port; Owner stack untouched): 390 non-E2E passed, 0 skipped; 10 E2E passed; web typecheck/build green. Compose smoke is left to isolated CI because the Owner's live stack runs on the executor machine. Schema baseline files unchanged; no migration;
- CI run `37110331958` on `57ae0f8`: `compose-smoke` SUCCESS. In `checks`, the non-E2E step passed and the E2E step FAILED (98 s, a normal duration). The executor has no GitHub authentication, so it could not read that job's log. The failure did not reproduce: E2E passed 10/10 three times locally on Windows and once in a disposable Linux container (node 24.14.1 trixie, Python 3.14, same PostgreSQL 18.6). The cause is unknown; see the CI run of the follow-up commit.

SR-003 review is now retained at `strategic_reviews/ASTRA-SR-003-REPLAY-CLOCK-PERFORMANCE-REVIEW.md`. Director disposition: `strategic_reviews/SR-003-DIRECTOR-DISPOSITION.md`, ACCEPT WITH MODIFICATION. This is documentation/architecture acceptance, not an implemented performance fix or a reproduced benchmark.

Confirmed base: `009c3420b588f2f0422d08fbe5d92e8ddf88b15f`. Director inspected relevant source and the historical R1 draft; no runtime tests, benchmarks or Owner artifacts were accessed. Current code still has per-event full snapshots/transactions, prefix restore and expensive terminal revalidation. R1A makes operation trustworthy/observable; R1B/C remove those costs and close assurance/performance.

Owner-reported September evidence: CLEAN preparation; 129,600 events; roughly one hour replay plus at least twenty minutes validation without visible terminal report; false stalled/RECOVERING health. Preserve dataset, old run, bindings and artifacts; no redownload, automatic salvage or new-engine relabeling. Verify actual manifest presence before describing local terminal state.

Release sequence: R1A -> R1B -> R1C -> Owner September Market replay -> R2 causal temporal substrate -> MP-001 integrated method closure -> R3 method-required context/presets -> WP-009 adviser -> Owner Backtest A. Only task.md authorizes implementation; all later packages are planned. R1A completion is READY FOR DIRECTOR REVIEW, not READY FOR OWNER MARKET REPLAY.

Initial horizon roles and provisional context requests are versioned conventions, not profitability results. Final data depth depends on method requirements and available source history. No new adviser/semantic.v2 or long historical CLI evaluation is authorized.

## From STATE.md — RP-001 research detail

### Research retained, not governing

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

## From STATE.md — accepted implementation history WP-001 to WP-007 and repository history

### Accepted implementation history

The records below retain accepted engineering facts. Historical package-local limitations describe what those packages implemented, not permanent exclusions on the product. In particular, former hours-scale correctness-first choices do not waive Foundation v3.0's local-use performance requirements.

### Accepted work

#### WP-001 — Repository bootstrap and observable dummy run
Accepted implementation lineage:
- `92014aa03060332b4c947ef10329b79cde7d51b2`
- CI correction `a49c0f75be7d9d885c65901c9cc73f3ed3a66a99`

The dummy account/risk/order/fill path remains DEMO infrastructure scaffolding only.

#### WP-002 — Replay/operations shell and semantic baseline
Accepted implementation:
- `803b3f215c5a33499a4d901ae000ee112b75e691`

`algotrader.semantic.v1` remains the frozen synthetic-shell baseline.

#### WP-003 — OKX BTC-USDT-SWAP public data provenance
Accepted implementation:
- `6b45728074e470bb85b06cce1995dad90f81cb62`

Acceptance includes immutable public OKX evidence, explicit source/event/availability/retrieval timing and frozen `algotrader.marketdata.v1`.

#### WP-004 — Causal feed and observable market state
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

#### WP-005 — Prospective OKX public live recorder and measured receipt-time evidence
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

#### WP-006 — Product-grade application UI redesign
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

#### WP-007 — Durable real-market observation replay and observable-state integration
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

### Repository history note

PR #8 had been merged as `64f3fa7`. Commit `887dfe0` was later created from stale parent `b47b3cb`, temporarily dropping the PR #8 tree from main.

The history was repaired without rewriting shared history by merge commit:

`ea88a978d3c44729f60705c332888116af3ecda6`

The Owner prepares the current checkout before launching the executor. Executors inspect that prepared base and do not pull; see AGENTS.md.

Force pushes remain prohibited.

## From STATE.md — dated Director review entries and Owner usability pass

### R1B Director review — 2026-10-02

Historical initial review: implementation `464f449e5961e240eab588876d21ab1bdd444145` was **CHANGES REQUIRED**; the later `9d814ec` correction closes these findings. CI `37052483628` checks/compose-smoke independently confirmed SUCCESS; executor reports 348 non-E2E + 10 E2E, fixture timings/memory not independently rerun. Schema-related files have no diff from the base.

Retain kernel/sparse persistence/direct restore and short differential evidence. Initial R1B defects (closed by the correction below): input-sized in-memory preparation sets/lists and unbounded external-merge fan-in; source bytes mutable between verification and normalization; compatible cache-manifest alterations accepted on a fresh warm launch without a trusted prior pin. Independent stdlib probes of actual extracted code accepted changed compatible cache facts and showed 10 simultaneous spill readers for 20 records/block2. See `delivery/WP-008-R1B-DIRECTOR-REVIEW.md` and task.md. No full local suite or Owner stack/data accessed. At that initial review R1C and Owner September retry remained inactive; the current action and correction closure below supersede this activation status.

### R1B correction accepted; R1C activated — 2026-10-02

Director accepted `9d814ec957e17fc33c1fcfbfb96034844e416444` after source inspection of private verified snapshots, trusted PostgreSQL cache receipts, deterministic durable publication and bounded disk-index/multipass preparation, plus the added regressions. CI `37065434955` checks/compose-smoke independently confirmed SUCCESS. Executor reports 366 non-E2E + 10 E2E and fresh-process memory measurements; Director did not rerun full suites or Windows measurements. Independent actual-sorter stdlib probe passed (100 records, block2, fan-in3; max 3 readers, 3 merge passes). Schema-related files unchanged from correction base.

This closes the earlier `464f449` findings; see the closure in `delivery/WP-008-R1B-DIRECTOR-REVIEW.md`. R1C now closes layered assurance, explicit optional Deep validation, representative long-unit control/durability tests and reproducible structural performance gates. Directory fsync on Windows remains unproven; metadata/disk growth remains disclosed. No achieved month/year performance or Owner improvement is claimed. Owner September retry still blocked until Director R1C release acceptance.

### R1C Director review — 2026-10-03

Implementation `6745117ee1010510abfa6247bfc40c1331fff7c1`: **CHANGES REQUIRED**. The active task is the R1C correction, not an Owner retry. CI `37075370604` checks/compose-smoke independently confirmed SUCCESS; full suites and Windows measurements remain executor evidence, not Director reruns. No schema-related diff.

Retain useful full-month synthetic measurements and implemented integrity/Deep functionality. Blocking findings: reconciliation accepts an absent receipt; Deep final success can overwrite an accepted cancel; Deep MATCH headline can incorrectly promote failed runtime assurance. Independent focused stdlib code probes confirmed these behaviors. Annual component timings are useful but annual application gates remain NOT_MEASURED/PENDING. See `delivery/WP-008-R1C-DIRECTOR-REVIEW.md`. Director review may authorize a scoped September app check after fixes; no annual-readiness claim or real historical CLI evaluation is accepted.

R1C correction pushed by the executor (see *R1C correction executor evidence* above): READY FOR DIRECTOR REVIEW — R1C CORRECTION ONLY. Annual application gates remain NOT_MEASURED/PENDING; the proposed Owner handoff is month-only and is not active before Director acceptance.

### Director R1C closure — Owner September check active

Accepted correction `99e0ca5` for the month-only app check; **READY FOR OWNER MARKET REPLAY — SEPTEMBER 2025 ONLY**. Mandatory receipt, locked Deep cancellation, separated assurance and gate interpretation reviewed; independent actual-summary probes pass. CI `37111371473` checks/compose-smoke SUCCESS independently verified. Full test/benchmark timings remain executor evidence, not local Director reruns.

Previous CI failure is now localized from retrieved job `111166819975`: Workbench terminal Copy did not show Copied within 5 s at E2E line 173; 1 failed/9 passed. Root cause unisolated; an older uncancelled copy-reset timer is a hypothesis. Final CI on unchanged product code passes. Record follow-up; use downloaded Markdown if feedback/copy fails. See review closure for evidence limits.

Current task is one Owner-launched NEW September run on the existing Verified local chunk, preserving old run/data/volumes. No executor implementation package or R2 activation. The real incident remains open until actual Owner source/count/assurance/timing report is reviewed; no replacement ID has been invented. Annual application gates NOT_MEASURED/PENDING and Windows directory durability remain qualified.

### Owner usability pass — executor evidence (Director review pending)

Direct Owner instruction after the September check (Owner-reported, not re-run by the executor: COMPLETED, 129,600/129,600 events, 9/9 checks PASS, 60.4 s). task.md had no active implementation package; the Owner instruction supersedes it for this bounded UX scope. No engine, contract, schema, assurance-meaning or data change; R2 and later packages remain inactive.

Implemented (base `21f5cf4`):
- task-first information architecture: plain purpose per sidebar entry, *What you can do now* on Market, global queued/running activity indicator from health;
- Historical Workbench as three numbered steps (prepare data / start a check / follow and get the report) with settings beside their actions, plain month state, one plain run status shared with Replay Lab (status sentence, progress, controls, four-step summary), result directly below with three separate facts (run / integrity checks / trading adviser not built), limits, next step and Copy report for chat; all technical facts, logs, exports, Deep validation, observable state and artifacts remain available through labelled disclosures;
- September report inconsistencies: terminal runs read *All phases done* / `finished (last phase … closed)` instead of a current GENERATING_REPORT phase; the WORKFLOW_VALID text names the run's own runtime integrity checks and states that no independent reference re-execution was performed; code version is the image build commit (`<sha>+image`, uncommitted changes undetectable) or explicitly *not available* (Compose no longer defaults it to the literal `unknown`);
- found while verifying in the browser: pending runtime checks during a run no longer raise an ASSURANCE WARNING (FAILED still does); the run's assurance summary refreshes when a Deep validation finishes without a page reload; Replay Lab's finished-run text no longer points to a report card it does not have; the copy confirmation can no longer be cleared by an older timer or a late manifest/terminal update (plausible cause of CI job `111166819975`, not proven); a duplicated data-quality limit line removed; no page-level horizontal overflow at 390 px.

Checks: 395 non-E2E passed, 0 skipped; E2E 10/10 (three local runs); web typecheck/build; scripted beginner browser journey (landing → prepare → start → pause/step → finish → copy report → expert disclosures → Deep validation) at 1440 px with overflow checks at 1024 and 390 px; isolated image build (temporary tag, removed) recorded HEAD as `+image`. Disposable PostgreSQL only; Owner stack untouched. CI result to be read from the pushed commit.

## From README.md — SR-003 status summary

#### SR-003 current work — R1A and R1B accepted; R1C accepted for the month-only Owner check

The Owner's September run exposed a replay/finalization performance defect. The Director approved a bounded redesign in `strategic_reviews/SR-003-DIRECTOR-DISPOSITION.md`. **WP-008-R1A (observable lifecycle and diagnosis) is accepted at `0919001`. WP-008-R1B (streaming replay and restorable checkpoints) is accepted at correction `9d814ec` for the structural slice**; see *Streaming replay engine (WP-008-R1B)* below. New runs no longer build the feed eagerly, snapshot every event, write a delivery row/transaction per event or rebuild the prefix on restore. R1C (layered assurance, optional Deep validation, control/durability closure, structural benchmark) is accepted at correction `99e0ca5` for the month-only Owner check; see *Assurance, Deep validation and release gates (WP-008-R1C)*. Synthetic structural gates are not an achieved Owner month/year result.

Do not retry the real month after R1A alone (**NOT READY FOR OWNER MARKET REPLAY**). The Director will hand off READY FOR OWNER MARKET REPLAY after R1B/C and review. Reuse September locally in a new run; preserve old rows/artifacts/identity. No automatic old-run salvage or September download. No professional adviser or achieved speedup is claimed.

## From README.md — Owner upgrade notes R1A and R1B

#### Owner upgrade to R1A (preserves the September evidence)

1. Stop **all** old application containers first so no old binary can keep publishing during the migration: `docker compose stop api worker recorder observer corpus` (leave `db` running). Do **not** use `down --volumes`.
2. Update the checkout (`git pull --ff-only origin main`), then `docker compose up --build -d`. The `migrate` service applies migration 6 before any new worker starts.
3. Migration 6 adds an operational **suspension** to every pre-upgrade nonterminal replay (e.g. the September run): its rows, checkpoint, delivery rows, configuration, source binding and any files stay exactly as they were; new workers never claim, restore or finalize it; controls are disabled. Open it in Replay Lab or the Historical Workbench and use **Copy diagnostics for chat** (it reports the committed cursor, missing terminal validation and whether a manifest exists on disk).
4. Do not start a replacement September run yet; R1C will hand that off (new run, same verified local dataset, no download).

#### Owner upgrade to R1B

Caches built by the first R1B commit carry no receipt and are quarantined/rebuilt on first use (migration 8). Same procedure as R1A: stop the application containers (`docker compose stop api worker recorder observer corpus`), update the checkout, `docker compose up --build -d` (never `--volumes`). Migration 7 suspends any unfinished R1A run read-only. Feed caches are created on the existing market-data volume on first use. Do not start the replacement September run yet (R1C).

## From README.md — R1C month-only September handoff

#### Owner upgrade to R1C and the replacement September run — authorized month-only handoff

The Director accepted `99e0ca5` for this **month-only** check: **READY FOR OWNER MARKET REPLAY — SEPTEMBER 2025 ONLY**. Annual application gates stay NOT_MEASURED/PENDING; do not launch other months or a year.

1. Stop the application containers (`docker compose stop api worker recorder observer corpus`; leave `db`), update the checkout, `docker compose up --build -d`. Never `down --volumes`. Migration 9 is additive; the old September run stays suspended and read-only.
2. Historical Workbench → **2 · Start a check** → *Market replay — data and engine check* → select the **existing prepared September 2025 chunk** (badge *Verified*; nothing is downloaded) → pacing **max** → no start-paused → **Start**. This creates a **new** run id; the old run is not resumed, salvaged or relabeled.
3. **Expected time.** The first run builds the feed cache: *Verifying source → Building feed*, then *Replaying → Validating → Generating report*. Release objectives on the reference machine are ≤120 s cold preparation, ≤120 s cached observation and ≤10 s terminal validation/report. The executor's synthetic month took ~70 s cold. Your hardware differs; if the run goes far beyond ~10 minutes, copy the diagnostic report while it is still running instead of waiting.
4. **Check the copied report** (all fields are in it; nothing needs a terminal):
   - status COMPLETED, last phase *Generating report* closed, no unmeasured spans;
   - assurance **passed** (`observe.stream-reconciliation` v2), including `cache_receipt_and_pin` and `completed_consumed_entire_feed`;
   - the *Current assurance* section's Runtime and Reference lines, plus every WARNING and Limitation line;
   - **coverage:** the committed cursor must equal *this run's* verified total events (report *Feed* / *Committed cursor* lines and the `completed_consumed_entire_feed` detail `cursor N/N`). The earlier Owner-reported count of 129,600 is only a comparison: report any difference to the Director. Neither number is assumed.
5. **Copy report for chat** (run panel in Historical Workbench or Replay Lab) and paste it to the Director. It contains build, worker host, feed identity and counts, per-phase timings, counters, controls, assurance and limits. **Deep validation** is optional: if you run it, copy its own report from its panel. If Copy provides no confirmation, download the Markdown report and attach it; the earlier CI copy-feedback failure is recorded for follow-up. Also copy the old suspended run's diagnostics if not already shared.
6. No CLI commands, raw logs or retries are needed. If anything fails or is cancelled, copy the report as it is.

## From README.md — Director review and release-status notes

#### Historical initial R1B Director review

The initial implementation at `464f449` required corrections, now closed by `9d814ec`. Streaming/sparse persistence/direct restore are implemented, but cold preparation still has input-sized memory and unbounded merge fan-in, and the verified-source/cache metadata trust boundaries require correction. See `delivery/WP-008-R1B-DIRECTOR-REVIEW.md`. Short fixture rates/memory do not establish month/year readiness. R1C and Owner September retry remain inactive.

#### Current R1C status

The earlier R1B findings are closed by Director review of `9d814ec`. R1C is implemented by the executor and awaits Director review; it is not accepted. No Owner September retry is authorized yet; Windows power-loss directory durability and actual (non-synthetic) month/year timings on the Owner's hardware remain unproven.

#### Director R1C review — corrections required

Review of `6745117` requires receipt enforcement, Deep terminal-cancel correctness and truthful separation of runtime versus reference assurance. See `delivery/WP-008-R1C-DIRECTOR-REVIEW.md`. The full synthetic month measurements are useful; annual component comparisons do not establish full annual application/preparation/report gates, which remain NOT_MEASURED/PENDING. No Owner September retry is authorized yet.

#### R1C correction — executor evidence, Director review pending

The correction implements all three findings: required trusted receipt, Deep terminal boundary under the row lock, and separate runtime/reference assurance. It also adds the gate inventory evaluator v2 with month-only handoff and annual gates PENDING. Details are above. Director acceptance is pending, and the Owner September run stays blocked until then.

#### Owner usability pass — executor evidence, Director review pending

Owner-requested UX restructuring after the September check, preserving the visual identity, every datum, control and inspection path, and the engine/assurance semantics:

- **Task-first navigation**: plain purpose under each sidebar entry; *What you can do now* on Market; global *Working / Nothing running* indicator.
- **Historical Workbench** as three numbered steps with settings next to the action they affect; result and **Copy report for chat** directly below the run status; technical facts behind labelled disclosures (see *Owner evaluation workbench*).
- **One plain run status** shared by Historical Workbench and Replay Lab; a finished run never shows its last phase as current (*All phases done*; reports say `finished (last phase … closed)`), and pending runtime checks during a run are *pending*, not an assurance warning (a FAILED result still is). Replay Lab states its purpose (event-by-event inspection) and links to the Workbench for routine checks; its diagnostics export stays visible.
- **Report wording**: the WORKFLOW_VALID text says the run's own runtime integrity checks (bounded terminal reconciliation) passed and that no independent reference re-execution was performed (optional Deep validation). A duplicated data-quality limit line is no longer repeated.
- **Code version**: `ALGOTRADER_CODE_VERSION` defaults to empty in Compose (it used to default to the literal `unknown`). The image records the commit it is built from (only `.git/HEAD`, `.git/refs`, `.git/packed-refs` enter the build context) as `<sha>+image`, described as *commit the application image was built from; uncommitted local changes cannot be detected*. Without git metadata nothing is recorded and reports say *not available*. Runs recorded earlier keep their stored value (`unknown` is shown as not available). Health and the sidebar show the build commit.

#### Director release status — 2026-10-03

R1C correction at `99e0ca5` is accepted for the single September Owner app check above. Earlier review-pending/blocked notes describe prior checkpoints and are superseded for that bounded action. Annual application readiness remains pending. The earlier E2E failure was terminal Copy feedback, not an established replay/assurance failure; its root cause is unisolated. Final CI passed on the same product code. The real September incident closes only after the Director reviews the Owner report.
