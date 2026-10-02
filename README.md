# Algorithmic Trader

Algorithmic Trader is a clean-room, local BTC trading adviser: professional market reading and persistent trade calls for a human who independently chooses capital, size, leverage and orders. FOUNDATION.md v3.1 is the canonical direction.

## Current state

**M3 is complete:** immutable real evidence, causal feed/state, public recorder and durable observation replay are implemented. **No production professional analyst or trade-call engine exists yet.** Synthetic trader/account output is DEMO.

The 30 September Owner clarification supersedes the mandatory pullback-only/RP-001 research path. Read FOUNDATION.md v3.1 and task.md for the current Director handoff. Old reviews/research are historical evidence, not current work authorization.

### SR-003 current work — R1A accepted, R1B active, R1B/R1C not implemented

The Owner's September run exposed a replay/finalization performance defect. The Director approved a bounded redesign in `strategic_reviews/SR-003-DIRECTOR-DISPOSITION.md`. **WP-008-R1A (observable lifecycle and diagnosis) is accepted by the Director at `0919001` for its operational scope; WP-008-R1B is now the active task**; see *Observable job lifecycle (WP-008-R1A)* below. It makes long operations visible, truthful and diagnosable; **it does not make replay faster.** The WP-007 engine costs (eager feed build, one transaction + delivery row + full snapshot per event, full prefix rebuild on restore, full terminal re-derivation of a run that completes) remain until R1B/R1C. Since the R1A correction an observed cancellation never triggers that re-derivation.

Do not retry the real month after R1A alone (**NOT READY FOR OWNER MARKET REPLAY**). The Director will hand off READY FOR OWNER MARKET REPLAY after R1B/C and review. Reuse September locally in a new run; preserve old rows/artifacts/identity. No automatic old-run salvage or September download. No professional adviser or achieved speedup is claimed.

### Required next product capabilities — not yet implemented

Live Home chart and changing professional-lens results, dominant directional view and persistent entry-valid call; integrated context including explicit cycle/event decisions; optional local sessions with catch-up; fixed repository historical pack (only the September 2025 bootstrap chunk is preparable today; the storage mechanism is undecided); advisory call/outcome sections in the Backtest report. The Owner-operated **observation-only** evaluation workflow with copy/export reports exists (WP-008, below).

The Owner launches substantial evaluations from the app. Executors run bounded engineering checks, then hand off **READY FOR OWNER BACKTEST**. Never mistake the existing observation-only replay for evaluation of a real trader.

## Read first

1. `FOUNDATION.md` — canonical product, architecture and research directive.
2. `STATE.md` — current milestone, active task and next action.
3. `AGENTS.md` — executor workflow and clean-room rules.
4. `task.md` — the single current task to implement.
5. `source_notes/` and `knowledge/registry.yaml` — professional knowledge provenance.

## Product scope

Initial advisory/research operation is **BTC perpetual futures**, with LONG/SHORT/NO_TRADE as the eventual primary recommendation states. Intended opportunities are generally minutes to hours, while broader horizons may inform market context. Calls stay entry-valid while their current conditions/room remain worthwhile, not merely for the first signal instant.

Capital allocation, position size, leverage, margin/collateral and actual order placement are human Owner decisions outside the algorithm's recommendation semantics. The application never places orders or chooses account exposure; the Owner's manual decisions are outside its scope.

## Start the application

One command (Docker + Docker Compose required):

```sh
docker compose up --build
```

Then open <http://localhost:8000>. The app opens on **Market** (the future trader cockpit, with real system/data readiness and clearly pending trader areas). Navigate with the sidebar: **Historical Workbench** (`#backtest`; prepare the historical corpus, launch a *Market replay — data and engine check*, copy its report or a diagnostic snapshot at any time), **Replay Lab** (**Market Replay** of real evidence — the primary mode — and the secondary **Synthetic Demo**), **Data** (historical datasets) and **Recorder** (public evidence collection). In Replay Lab, pick a dataset or finalized recording and click **Start market replay**, or switch to *Synthetic Demo* and click **Start synthetic replay**; the workers execute replays independently of the browser. `docker compose down` stops the stack. **Never add `--volumes` to an upgrade**: it deletes the database, the prepared corpus and all run artifacts.

Without Docker (local PostgreSQL 18, Python via `uv`, Node 24):

```sh
uv sync --locked
npm --prefix web ci && npm --prefix web run build
export ALGOTRADER_DATABASE_URL=postgresql://USER:PASS@localhost:5432/algotrader   # existing, empty database
uv run algotrader serve          # migrates, starts supervised run/recorder/observation/corpus workers + API on :8000
```

Useful environment variables: `ALGOTRADER_ARTIFACT_ROOT` (default `./var/artifacts`, outside Git), `ALGOTRADER_PORT`, `ALGOTRADER_LEASE_SECONDS`.

## Implemented operation (synthetic controls unless specified)

- **Runs**: start (replay speed, optional DEMO fault injection), cancel, status, progress, elapsed time, heartbeat, attempt, failure text and recovery log.
- **Replay controls** (UI buttons; `POST /api/runs/{id}/pause|resume|step|cancel`, `POST /api/runs/{id}/speed {"speed": n}`): all control state is persisted in PostgreSQL and survives browser close and API/worker restarts.
  - *Pause* lets the worker finish the bar in progress, then parks the run at the committed checkpoint (status `paused`, no lease held, no new events). Pause is not cancel and not terminal.
  - *Step one bar* (only while paused) advances exactly one input bar, committed normally, and the run stays paused. Repeated steps are queued one bar each.
  - *Resume* continues a paused run. *Speed* (bars/s, `max` = no pacing) can change at any time before the run ends. *Cancel* also works while paused.
  - Speed and control are operational pacing only: they are not part of the run config or the semantic trace, and are recorded separately in the run's `control_log` (shown in the UI, manifest and `report.md`).
- **Runtime state** shown per run: `queued`, `running`, `pausing`, `paused`, `stepping`, `recovering` (lease expired, awaiting reclaim), `cancel_requested`, `completed`, `cancelled`, `failed`. The **ETA** is computed only from bars/s observed since the last start/resume/speed change and is shown as *unavailable* otherwise. **Worker health** comes from worker heartbeats (`GET /api/health` → `workers`).
- **Restarts**: stopping and restarting the API and worker processes needs no manual repair. A run that was mid-step resumes from its last committed checkpoint after its lease expires; a crash-loop guard fails a run only after 3 consecutive lease-expiry interruptions with no step committed between them.
- **Current DEMO replay**: synthetic fixture, synthetic chart, dummy MarketView/decision scaffolding and legacy paper-account traces used only to exercise the shell. These are not the product's future capital-management semantics.
- **Artifacts**: every completed/cancelled/failed run writes `manifest.json`, Parquet records (events, market views, decisions, risk decisions, plans, orders, fills, account/equity, observations), `validation.json` and `report.md` under `<artifact root>/runs/<run_id>/`. They are listed and viewable in the UI and via `GET /api/runs/{id}/manifest` and `/api/runs/{id}/artifacts[/{name}[?format=json]]`.
- **Fault injection (DEMO)**: `crash worker once` kills the worker process mid-step; after the lease expires a restarted worker resumes from the last committed checkpoint. `crash worker every attempt` ends as `failed` with an explanation after 3 attempts.
- `uv run algotrader replay` is a bounded DEMO engineering diagnostic, not the Owner's evaluation workflow or permission for long CLI backtests.

## Checks

```sh
uv sync --locked
npm --prefix web ci
npm --prefix web run typecheck
npm --prefix web run build
uv run playwright install chromium            # once; CI uses --with-deps

# Database tests create/drop throwaway databases on this server:
export ALGOTRADER_TEST_DATABASE_URL=postgresql://postgres:PASS@localhost:5432/postgres
uv run pytest --ignore=tests/e2e              # unit, contracts, accounting, determinism, idempotency/recovery, API
uv run pytest tests/e2e                       # browser UI -> API -> worker process -> PostgreSQL -> UI
python scripts/stack_smoke.py http://127.0.0.1:8000   # against a running stack
```

## Market data (OKX BTC-USDT-SWAP, public/read-only)

Source decision: `knowledge/market_sources/OKX-BTC-USDT-SWAP.md`. No API keys; only the public instrument, history-candles (traded, mark, index; 1m) and funding-rate-history endpoints are reachable through the adapter (`src/algotrader/marketdata/okx.py`).

```sh
# bounded historical dataset (start inclusive, end exclusive, UTC, whole minutes; max 31 days)
uv run algotrader data fetch-okx --start 2026-09-29T00:00Z --end 2026-09-29T06:00Z [--base-url https://www.okx.com] [--root var/data]
uv run algotrader data list
uv run algotrader data verify <dataset_id>      # re-check every hash, row count and the dataset identity
uv run algotrader data live-check --minutes 30  # manual live integration check (never run in CI)
# Docker: docker compose run --rm api algotrader data fetch-okx --start ... --end ...
```

- **Base URL** is configuration (`--base-url` or `ALGOTRADER_OKX_BASE_URL`; default `https://www.okx.com`). OKX documents regional domains (e.g. `https://my.okx.com`, `https://eea.okx.com`, `https://us.okx.com`); none is assumed valid everywhere. Only official OKX hosts (`okx.com` or `*.okx.com`) over `https` with no path/query/fragment/userinfo and port 443 or none are accepted; anything else is rejected before any request (`marketdata/okx_authority.py`).
- **Current acquired datasets** live outside Git under `ALGOTRADER_DATA_ROOT` (default `./var/data`; Docker volume `marketdata`) in `datasets/<dataset_id>/`. Each has the exact raw source responses, a request/page log, the normalized instrument snapshot, normalized Parquet per family, `quality.json` and `manifest.json` with SHA-256 for every file.
- **Identity/immutability**: `dataset_id` is derived from the logical request, the market-data schema version, the availability policy and the SHA-256 of every raw response. Re-fetching identical source bytes reuses the existing dataset untouched. Changed source bytes create a new dataset, whose manifest lists the earlier versions in `prior_versions`. Existing dataset directories are never overwritten.
- **Time semantics**: candles keep the source `open_time`, a computed `close_time`, the modeled `available_time` and `retrieved_at` as separate fields. `available_time` follows the labelled modeling policy `okx.completed_1m_bar_available_at_close.v1` (bar close), which is not a measured publication time. Funding events keep the source `funding_time` and are never made available earlier. Unconfirmed candles (`confirm=0`) are rejected and reported.
- **Units**: traded candles keep contract volume, base-currency volume and quote-currency volume as separate fields with their currencies. Mark and index candles have no volume fields. Prices, rates and volumes are exact decimals (stored as the source decimal strings).
- **Quality**: gaps, duplicates (identical or conflicting), out-of-order pages, incomplete bars, invalid OHLC, prices or volumes, and out-of-window rows are reported with a severity (`info`, `warning`, `degraded`, `invalid`). Nothing is filled or repaired; invalid rows are kept with `quality=INVALID`.
- **Data view**: the UI's **Data** workspace (`#data`) (and `GET /api/datasets[/{id}[/verify|/files/{name}]]`) shows source, instrument, coverage, row counts, quality and gaps, retrieval time, schema version, hashes and provenance files.
- Contracts are versioned separately as **`algotrader.marketdata.v1`** (`schemas/algotrader.marketdata.v1.json`, same frozen-baseline rules as below). Exchange-advertised leverage is stored as venue metadata only; it is not a recommendation or product risk policy. Funding is recorded as market evidence.

### Fixed local corpus

Foundation v3.0 requires an immutable reusable historical corpus (target 2025-09-01 inclusive → 2026-09-01 exclusive, UTC). WP-008 implements its **logical plan and local preparation**, not the pack itself: the checked-in plan `src/algotrader/corpus/plan.json` lists twelve monthly chunks; only `btc-okx-2025-09` (2025-09-01 → 2025-10-01) is preparable, later months are PLANNED/locked. Prepared chunks are ordinary `marketdata.v1` datasets in the local data root (outside Git) and are reused, never re-downloaded per run. No acquired data is committed and no Git LFS is used; the storage mechanism (Git pack / LFS / pinned archive) is a later Director decision based on the sizes the Backtest page and report measure.

Local startup catch-up and the advisory backtest (calls/outcomes) are pending. Current recorder sessions work only while the local processes run; no H24 operation is required by the product.

## Causal feed and observable market state (WP-004, `algotrader.feed.v1` PROVISIONAL)

A pure domain core (`src/algotrader/feed/`), with no UI, database, worker, trader, account or execution dependency. It sits at the boundary **market evidence → causal availability feed → observable market state**. WP-007 now connects it to the durable observation worker and Market Replay browser view.

```sh
uv run algotrader feed inspect <dataset_id> --cutoff 2026-09-30T08:00Z [--bar-delay-seconds 15] [--history 240] [--json]
```

- **Events**: each verified `marketdata.v1` dataset becomes ordered `FeedEvent`s:
  - bar observations (traded / mark / index, 1m);
  - sparse funding observations;
  - slot-quality events (`MISSING`, `INVALID_ROW`, `CONFLICTING_DUPLICATE`, `INCOMPLETE_REJECTED`). Excluded slots are classified from the retained raw pages.

  Invalid or unconfirmed evidence never becomes a valid observation, nothing is forward-filled, and channels are never substituted for each other. The dataset is never modified.
- **Times**: `event_time`/`event_end_time` (market), `available_time` (knowledge, with `availability_basis` MODELED|RECORDED and a policy id) and `source.retrieved_at` (provenance) stay distinct.
- **Availability**: `modeled_availability(bar_delay, funding_delay)` adds a non-negative delay to the marketdata.v1 modeled availability without changing market time. The default zero delay is a lower-bound convention, not a measurement. RECORDED receipt times come with the live recorder, which is not part of WP-004.
- **Ordering** (`feed.order.availability-family-series-time-kind.v1`): a total order by availability time, then family rank (trade, mark, index, funding), series, market time, kind and event id. It is a replay convention, not a claim about exchange micro-order. Two events for the same channel slot are rejected as ambiguous. Input order never matters.
- **State**: the pure reducer `apply(state, event)` owns bounded per-channel history. Each channel reports:
  - `condition`: NEVER_SEEN / VALID / GAP / REJECTED / INVALID_ONLY;
  - `freshness`: UNKNOWN / FRESH / STALE / NOT_APPLICABLE (sparse funding);
  - ages, counts, coverage and the latest valid value. That value is carried with its original times when stale.

  Snapshots (`snapshot_at`) and deltas (`make_delta`) are deterministic. They carry the ordering, availability and freshness policy ids, and the labels `OBSERVATION_ONLY` / `NO_INTERPRETATION`.
- **Identity**: the evidence-package `dataset_id` is kept. A separate `feedcontent.v1:` content identity covers the normalized event content and coverage, independent of pagination, base URL and retrieval time. A snapshot's `content_digest` covers market content only; its `snapshot_id` adds provenance.
- **Status**: the contracts are PROVISIONAL during M3. Any change bumps `FEED_SCHEMA_REVISION`, adds a `FEED_CHANGELOG` entry and needs Director approval; `algotrader schema --write` refuses to rewrite the baseline otherwise.

## Public market recorder (WP-005, `algotrader.recorder.v1` PROVISIONAL) — no trading

This component prospectively records **public, unauthenticated** OKX BTC-USDT-SWAP information together with **actual local receipt times**. Historical REST data cannot reconstruct those times. It uses no API keys, no login, no private/account channels and no orders.

- **Sources** (verified 2026-09-30):
  - candle channels on the WebSocket *business* endpoint: `candle1m`, `mark-price-candle1m`, `index-candle1m` (index id from the instrument);
  - `funding-rate` (evolving pre-settlement information) on the *public* endpoint;
  - REST `public/time` (clock probe) and `public/instruments` (instrument snapshot at session start).

  Endpoints are configurable for regional domains (`ALGOTRADER_OKX_WS_PUBLIC_URL`, `ALGOTRADER_OKX_WS_BUSINESS_URL`, `ALGOTRADER_OKX_BASE_URL`, or API overrides) but must pass the same official-source rule: `wss://<*.okx.com>:8443` with path exactly `/ws/v5/public` or `/ws/v5/business` (e.g. `ws.okx.com`, `wseea.okx.com`, `wsus.okx.com`), and an official `https` REST base. Invalid endpoints are rejected, never rewritten. If the WS funding channel is unavailable, a bounded REST poll is used and labelled POLL_OBSERVED. Each poll records its request-sent time, response time, interval and previous observation.
- **Receipt semantics**: every message is journaled raw, with:
  - `recv_utc_ns`, the host wall clock read immediately after the read returns, before parsing. This is *client-observed receipt, not exchange publication*;
  - `recv_mono_ns` and a contiguous `seq`, which preserve local order;
  - the connection generation and the parse status.

  Source timestamps remain inside the raw payload. Raw receipt times are never corrected. The offset to OKX server time is observed separately (offset estimate ± round-trip bound, or "unknown").
- **Durability**: sessions live under `<ALGOTRADER_DATA_ROOT>/recordings/<session_id>/`, outside Git. The layout is an append-only segmented journal, a lifecycle log, clock observations, the first-completion bar index, `report.json` and `manifest.json` (written last, with sha256 for every file).
  - Every line is flushed immediately; files are fsynced at least every second.
  - A crashed session is recovered by truncating only a torn final line and is finalized as PARTIAL. It is never resumed, and records are never rewritten, so a receipt cannot be duplicated.
  - A finalized session is never modified.
- **Reconnects**: a text `ping` keeps connections alive; reconnect uses bounded exponential backoff and resubscribes with a new connection generation. Disconnect intervals are reported as recorder coverage loss, never as market gaps, and nothing is fabricated.
- **Measured availability report** (per session; evidence, not a universal constant):
  - bar end → first completed (`confirm=1`) receipt delay per candle family, on the raw local clock and as an offset-adjusted estimate;
  - negative-delay detection;
  - duplicate, changed and out-of-order pushes;
  - missing completions while connected;
  - outages and clock quality;
  - funding snapshots and fundingTime transitions.
- **Recorded → feed.v1**: `build_recorded_feed` turns each bar's *first completed receipt* into a RECORDED feed event (`available_time` = local receipt).
  - Forming updates never become observations, and later pushes never replace the first completion.
  - Deduplication uses an explicit journal identity, independent of the observable state's bounded history.
  - Clock-inconsistent completions (received before the bar end) are excluded and reported, not clamped.
  - Live funding snapshots are *not* settlements and stay recorder-only.
- **Operation**: the **Recorder** view (`#recorder`, *Public market evidence collection — no trading*) has start (max duration), stop, status, elapsed time, heartbeat, connection states, subscribed channels, counts, last receipt, reconnects/errors, output path and the measured-timing summary. The `recorder` Docker Compose service (or `algotrader serve`) runs `algotrader recorder-worker`; the browser does not own the recording.
  - CLI: `algotrader recorder run --minutes N` (foreground bounded session) and `algotrader recorder inspect <session_id>`.

## Real-market observation replay (WP-007, `algotrader.observe.v1` PROVISIONAL) — observation only

A separate operational path from the synthetic `semantic.v1` shell: **verified evidence → `feed.v1` causal deliveries → pure observable-state reducer → durable replay/product visibility**. It never creates MarketViews, decisions, orders, fills or account records and never imports the synthetic trader/risk/account/engine modules.

- **R1A note**: launch, supervision, fencing, phases and diagnostics changed in WP-008-R1A (next section); the clock, order, digests, per-event commit and validation mathematics below are unchanged.
- **Sources**: a verified `marketdata.v1` dataset (feed built with the accepted adapter and the explicit zero-extra-delay **MODELED** availability convention — *not measured publication timing*), or a finalized CLEAN/PARTIAL `recorder.v1` session (accepted bridge; **RECORDED** availability = first completed push's *client-observed* local receipt time). Sources are verified (hashes, identity) by the worker-owned preparation after a durable launch and again on every worker claim; FAILED/unusable sessions cannot launch; PARTIAL outages are listed as recorder availability loss, never as market gaps; bridge exclusions stay visible.
- **Clock**: one step = one causal feed delivery in the accepted total order; information time = that delivery's `available_time`. Pacing is **events/s** (`max` allowed) and never changes order, state or digests. Freshness uses the named inspection default (`feed.freshness.v1(...)`), persisted per replay.
- **Durability**: `observe-worker` processes (`observe:` worker ids; Compose service `observer`) own replays under a lease. Each delivery commits atomically: cursor compare-and-set (`k → k+1`) + snapshot digest/view + append-only delivery row (unique per `(replay, seq)` and `(replay, event_id)`). On claim the state is rebuilt as the pure feed prefix and must match the persisted digest, otherwise the replay fails explicitly. Pause parks at a committed cursor; *Step one event* applies exactly one delivery; 3 consecutive interruptions without progress fail the replay.
- **API**: `/api/observations` (`sources`, `sources/{kind}/{id}` preflight, create/list/get, `state`, `deliveries`, `traded-bars`, `pause|resume|step|speed|cancel`, `stream` (SSE), `manifest`, `files/{name}`).
- **Artifacts** (revision 1: `<artifact root>/observations/<replay_id>/`; revision 2: the generation-scoped `observations/<replay_id>/g<generation>/`): `config.json`, `deliveries.jsonl`, `final_snapshot.json`, `validation.json` (independent re-derivation from the immutable source: order, no duplicates, per-delivery digests, no future knowledge, final = `snapshot_at`) and `manifest.json` (hashes; source evidence referenced, not copied).
- **Health** (`GET /api/health` → `capabilities`) is capability-aware: core, market replay, recorder and synthetic replay each report `available`, `unavailable` (worker offline; limits that capability only) or `stalled` (jobs waiting with no worker).

## Observable job lifecycle (WP-008-R1A) — operational only, not a speedup

Shared operational contract `algotrader.ops.v1` (`src/algotrader/ops.py`) for observation replays/evaluations and corpus jobs. Four facts are kept separate: **status** (queued/running/paused/completed/failed/cancelled), **phase** (`QUEUED`, `PREPARING_SOURCE`, `VERIFYING_SOURCE`, `BUILDING_FEED`, `INITIALIZING`, `REPLAYING`, `FINALIZING`, `VALIDATING`, `GENERATING_REPORT`; corpus also `DOWNLOADING`, `BINDING`), **health** (`progressing`, `waiting`, `alive_no_progress`, `compute_lost`, `unresponsive`, `recovering`, `suspended`, `finished`; API-level `disconnected`) and **assurance** (`not_checked`/`incomplete`/`passed`/`failed`, with validator, version and scope).

- **Durable launch** (`POST /api/observations`, `POST /api/evaluations`): validates cheap fields and local existence only, persists an `ObservationLaunch` envelope (and the evaluation row, atomically) and returns; no hashing, parsing or feed build in the request (measured well under 1 s on the offline fixture while verification was deliberately slowed). Source/config/feed identity and the total event count are `PENDING` (`null`) until the worker has verified the source and built the feed; the verified config is persisted **before the first causal step**. Evaluations re-check the corpus binding's manifest hash in `PREPARING_SOURCE`. `GET /api/observations/sources/{kind}/{id}` is now a cheap preview (no verification). Preparation errors become visible failed runs with reports.
- **Supervisor + compute process**: `observe-worker` is a lightweight supervisor (own DB connection, heartbeat ~2 s, fenced lease 30 s) that starts a separate **compute process** per claimed attempt and renews the lease only while that process exists. CPU-bound replay/validation cannot starve the heartbeat. A dead compute process is recorded and its lease released at once (`compute_lost`); a lapsed lease without a recorded exit is `unresponsive`; `recovering` is shown only while a new fenced attempt is actually restoring. A supervisor DB outage renews nothing and is logged (`db_outage`) once the DB is reachable; an unreachable DB makes the API answer 503 `disconnected`. `--inline-compute` exists for diagnostics only.
- **Fencing**: every claim/reclaim increments `lease_generation` (also for the same worker id). Phase/progress, prepared config, checkpoint cursor + delivery rows, parking, controls consumption, artifact references and terminal status are written only by `(lease_owner, lease_generation, status='running')`; terminal publication also checks the expected committed cursor. Artifacts are staged then published immutably into `g<generation>/` before the fenced DB commit, so a stale finalizer can never overwrite current files. Corpus jobs use the same generations for progress, binding (`corpus_chunks.bound_generation`) and terminal status.
- **Progress, timing, ETA**: phase spans persist in `phase_history` with explicit meanings: **wall** = start-to-end clock time; **waiting** = declared intentional waits inside the span (queue wait, configured replay pacing sleeps); **active** = compute-process time minus declared waits. Paused time lies in no span. An interrupted span whose compute time could not be measured keeps `active_seconds: null` (`measured: false`) and is counted as *unmeasured*, never as zero; totals say `active_complete: false`. The open span's active time comes only from the compute process's last milestone. Compute milestones (`progress`, `last_progress_at`, `progress_seq`) are separate from heartbeats; phase-specific inactivity limits drive `alive_no_progress`. ETAs are **current window only**: the replay ETA window starts when `REPLAYING` starts (and on resume/pacing change), never at claim or preparation, and is labelled as wall-clock time at the configured pacing (declared pacing waits are not active throughput). Other phases use active compute time of the current substage; a new phase, substage, unit, total or generation starts a new window; too little observation stays unknown. During `FINALIZING/VALIDATING/GENERATING_REPORT` the state is `finishing`, with text that states the actual committed cursor (complete or partial) and the target status; operational completion and assurance are reported separately. Cheap per-generation counters (events applied, snapshots built, transactions, delivery rows, prefix-restore events, re-derived deliveries, source verifications, output bytes, CPU seconds, max RSS where supported) are recorded for the R1B/C baseline.
- **Controls**: status/control acknowledgement is an immediate DB write; the compute process reads cancellation at bounded milestones (~0.5 s). Cancel works in every phase. **Bounded cancellation**: once a cancellation is observed (while preparing, initializing, replaying, paused, or in `FINALIZING`/`VALIDATING`/`GENERATING_REPORT`), the run ends `cancelled` with assurance **INCOMPLETE** on a bounded path: no committed-prefix load, no source reload, no reference re-derivation; the generation directory holds `config.json`, `validation.json` (`validation_not_run` / or the partial `VALIDATING` checks) and `manifest.json` from the committed checkpoint; committed delivery rows stay in the database. The only atomic boundary is the final publication rename + terminal commit, done under the replay row lock that the cancel command also takes: a cancel reaching the lock first prevents a COMPLETED publication; a cancel after that commit is rejected as already completed. Cancelling during `VALIDATING` at a full cursor ends `cancelled` with INCOMPLETE checks (never PASS). Pause during preparation parks at cursor 0 after preparation; STEP is exactly one source event and needs a prepared total; pause/step are disabled (with reason) after the replay cursor completes. Monolithic units (`order events`, `feed identity hashes`, recorded-journal bridge) are labelled non-interruptible.
- **Diagnostics at every status**: `GET /api/observations/{id}/report.md|json`, `/api/evaluations/{id}/report.md|json` (snapshot with capture time while non-terminal or without a manifest; terminal reports stay byte-deterministic) and `/api/corpus/jobs/{id}/report.md|json`. Built from persisted facts only (no source re-execution, no full delivery read); manifest existence/size/hash is checked where claimed. A failed final publication leaves a failed run with no manifest and a working diagnostic export.
- **Contracts**: `algotrader.observe.v1` revision 2 (Director-approved, additive optional fields; revision-1 manifests remain readable and unchanged). `semantic.v1`, `marketdata.v1`, `feed.v1`, `recorder.v1` baselines are byte-identical. DB migration 6 is additive.

### Owner upgrade to R1A (preserves the September evidence)

1. Stop **all** old application containers first so no old binary can keep publishing during the migration: `docker compose stop api worker recorder observer corpus` (leave `db` running). Do **not** use `down --volumes`.
2. Update the checkout (`git pull --ff-only origin main`), then `docker compose up --build -d`. The `migrate` service applies migration 6 before any new worker starts.
3. Migration 6 adds an operational **suspension** to every pre-upgrade nonterminal replay (e.g. the September run): its rows, checkpoint, delivery rows, configuration, source binding and any files stay exactly as they were; new workers never claim, restore or finalize it; controls are disabled. Open it in Replay Lab or the Historical Workbench and use **Copy diagnostics for chat** (it reports the committed cursor, missing terminal validation and whether a manifest exists on disk).
4. Do not start a replacement September run yet; R1C will hand that off (new run, same verified local dataset, no download).

## Owner evaluation workbench (WP-008) — observation-only, no adviser

The **Historical Workbench** page (`#backtest`, formerly *Backtest*) is the Owner workflow the future adviser will reuse:

- **A · Historical corpus**: the twelve-month ledger from the checked-in plan, each chunk's local state (`prepared`, `preparing`, `not_prepared`, `invalid`, `planned`), dataset identity, verification, quality, measured bytes (raw / Parquet / metadata, files, pages, rows) and reuse state. **Prepare** only inserts a durable PostgreSQL job (`corpus_jobs`); the `corpus-worker` (Compose service `corpus`, `corpus:` worker ids) owns it: it reuses a verified binding or adopts an exactly matching local dataset without network, otherwise acquires the month via the accepted `OkxPublicClient` + `marketdata.dataset.acquire` (official OKX hosts only), verifies it and only then binds it (`corpus_chunks`). Progress shows phase, fixed windows done/total, pages, bytes, elapsed, heartbeat and an ETA only after measured throughput. Cancel stops at the next source page and binds nothing; finalized datasets are never deleted. A crashed worker's job is reclaimed after its lease and the chunk restarts **from scratch** (no byte-level resume; 3 interruptions fail it).
- **B · Run setup**: explicit run types — **Market replay — data and engine check** (available), **Adviser backtest** (unavailable until the adviser exists), **Deep validation** (planned, not an action). Prepared chunk, pacing and optional start-paused. There are no model parameters: *Professional adviser not connected yet.*
- **C · Run & report**: the accepted durable observation replay (same worker, controls, chart, observable state, artifacts); the chart shows a bounded 240-bar tail refreshed at most once per second while the worker processes every event. Every run has **Copy report for chat**, Markdown and JSON at every status: a diagnostic snapshot while queued/running/paused/validating, a terminal report (`OBSERVATION_ONLY_EVALUATION`) once completed, cancelled or failed. Every call/MarketView/outcome metric is `UNAVAILABLE` with value `null`, never zero.
- **API**: `/api/corpus` (status, `chunks/{id}/prepare`, `jobs`, `jobs/{id}`, `jobs/{id}/cancel`) and `/api/evaluations` (create/list/get, `report.md`, `report.json`, `?download=true`). Health reports a `corpus` capability.

## Semantic contract baseline

The public semantic contracts (`src/algotrader/contracts.py`: journal payloads such as MarketObservation, MarketView, TradePlan, RiskDecision, Decision, OrderIntent, Order, Fill and AccountSnapshot, plus Run, RunConfig, ReplayControl and RunManifest) are frozen as **`algotrader.semantic.v1`**. Their JSON Schema is checked in at `schemas/algotrader.semantic.v1.json`, and every run manifest records the version in `schema_version`.

- `uv run algotrader schema` checks that the code still matches the baseline; `tests/test_schema.py` does the same in CI and fails on any drift.
- An intentional breaking change never edits a published baseline. The real advisory semantic.v2 must be introduced separately under the active task; do not turn the DEMO account/order schema into the real trader contract. Existing schema generation refuses to overwrite a differing baseline.
- The PostgreSQL schema is migrated separately and in place (`db.MIGRATIONS`, recorded in `schema_migrations`).

Without `ALGOTRADER_TEST_DATABASE_URL` the database tests are skipped (CI sets `ALGOTRADER_REQUIRE_DB=1`, which turns that into a failure). CI (`.github/workflows/ci.yml`) runs all of the above and a Docker Compose smoke.

## Repository layout

| Path | Contents |
|---|---|
| `src/algotrader/contracts.py` | DEMO semantic contracts (instrument, observation, MarketView, scenario, plan, decision, risk, order, fill, account, run, manifest) |
| `src/algotrader/corpus/` | Corpus plan (`plan.json`), local bindings, durable corpus-preparation jobs/worker, API |
| `src/algotrader/evaluation/` | Observation-only evaluation facade and Markdown/JSON reports |
| `src/algotrader/synthetic.py` | Deterministic synthetic BTC-perpetual fixture |
| `src/algotrader/trader.py` | Trader interface + scripted DEMO dummy trader |
| `src/algotrader/risk.py`, `account.py` | DEMO-only risk skeleton (1x cap), paper account and next-bar-open fill model; not adviser policy |
| `src/algotrader/engine.py` | Pure, deterministic step engine and semantic trace hash |
| `src/algotrader/worker.py`, `db.py` | PostgreSQL-backed durable worker (leases, fencing, checkpoints, idempotent journal, parking of paused runs) and migrations |
| `src/algotrader/control.py` | Durable replay-control commands (pause/resume/step/speed/cancel) |
| `src/algotrader/schema.py`, `schemas/` | Semantic and market-data contract JSON Schema baselines and their generator |
| `src/algotrader/marketdata/` | Market-data contracts, OKX public REST adapter, bounded dataset acquisition/quality/verification |
| `src/algotrader/recorder/` | Public live recorder: contracts (provisional), OKX WS/REST adapter, append-only journal, analysis/report, recorded→feed bridge, durable job |
| `src/algotrader/observe/` | Real-market observation replay (provisional contracts, sources/verification, pure event-driven core, durable worker/control, artifacts/validation, API) |
| `src/algotrader/feed/` | Causal feed contracts (provisional), dataset→feed adapter, ordering/availability policies, pure observable-state reducer, snapshots/deltas |
| `tests/fixtures/okx/` | Small captured OKX public responses (see `PROVENANCE.json`) for offline tests |
| `src/algotrader/artifacts.py`, `validation.py` | Immutable run artifacts and validation checks |
| `src/algotrader/api.py`, `cli.py` | FastAPI app (commands, snapshots, SSE, artifacts) and CLI |
| `web/` | React + TypeScript UI (Vite) |
| `tests/`, `tests/e2e/` | Test suite and Playwright end-to-end smoke |

Toolchain pins: Python 3.14.7 (`.python-version`, `uv.lock`), Node 24.14.1 (`.nvmrc`, `web/package-lock.json`), PostgreSQL 18.6 image, uv 0.12.10.

The Project & Research Director replaces `task.md` after reviewing each pushed implementation.
