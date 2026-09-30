# Algorithmic Trader

Algorithmic Trader is a clean-room BTC-only research and paper-trading project whose goal is to translate professional market-reading and trade-decision practice into a deterministic, inspectable software trader.

## Current state

Algorithmic Trader is a BTC **market-analysis and trade-decision** system (Foundation v2.0): capital, position size, leverage and order placement remain the human Owner's decisions. The operational shell (WP-001/WP-002) and the OKX BTC-USDT-SWAP market-data evidence layer (WP-003) are accepted. The project is in **M3 — trustworthy real-market observation and causal reasoning readiness**; WP-004 adds the causal feed and observable market state pure core. The runnable shell still uses a scripted **DEMO dummy trader** on a **synthetic** fixture; its account/order path is DEMO scaffolding only. No professional trader exists yet, and nothing the DEMO replay shows is market data or research evidence. Acquired OKX datasets are real public market data, not trading results.

## Read first

1. `FOUNDATION.md` — canonical product, architecture and research directive.
2. `STATE.md` — current milestone, active task and next action.
3. `AGENTS.md` — executor workflow and clean-room rules.
4. `task.md` — the single current task to implement.
5. `source_notes/` and `knowledge/registry.yaml` — professional knowledge provenance.

## Product scope

Initial paper operation is **BTC perpetual futures**, LONG/SHORT/NO_TRADE, with no leverage above 1x exposure. Intended trades are short-duration (generally minutes to hours), while broader horizons may inform market context.

No real-money trading is authorized.

## Start the application

One command (Docker + Docker Compose required):

```sh
docker compose up --build
```

Then open <http://localhost:8000>. Click **Start synthetic replay** to launch a run; the worker executes it independently of the browser. `docker compose down` stops the stack (add `--volumes` to delete the database and run artifacts).

Without Docker (local PostgreSQL 18, Python via `uv`, Node 24):

```sh
uv sync --locked
npm --prefix web ci && npm --prefix web run build
export ALGOTRADER_DATABASE_URL=postgresql://USER:PASS@localhost:5432/algotrader   # existing, empty database
uv run algotrader serve          # migrates, starts a supervised worker + API on http://127.0.0.1:8000
```

Useful environment variables: `ALGOTRADER_ARTIFACT_ROOT` (default `./var/artifacts`, outside Git), `ALGOTRADER_PORT`, `ALGOTRADER_LEASE_SECONDS`.

## Operation

- **Runs**: start (replay speed, optional DEMO fault injection), cancel, status, progress, elapsed time, heartbeat, attempt, failure text and recovery log.
- **Replay controls** (UI buttons; `POST /api/runs/{id}/pause|resume|step|cancel`, `POST /api/runs/{id}/speed {"speed": n}`): all control state is persisted in PostgreSQL and survives browser close and API/worker restarts.
  - *Pause* lets the worker finish the bar in progress, then parks the run at the committed checkpoint (status `paused`, no lease held, no new events). Pause is not cancel and not terminal.
  - *Step one bar* (only while paused) advances exactly one input bar, committed normally, and the run stays paused. Repeated steps are queued one bar each.
  - *Resume* continues a paused run. *Speed* (bars/s, `max` = no pacing) can change at any time before the run ends. *Cancel* also works while paused.
  - Speed and control are operational pacing only: they are not part of the run config or the semantic trace, and are recorded separately in the run's `control_log` (shown in the UI, manifest and `report.md`).
- **Runtime state** shown per run: `queued`, `running`, `pausing`, `paused`, `stepping`, `recovering` (lease expired, awaiting reclaim), `cancel_requested`, `completed`, `cancelled`, `failed`. The **ETA** is computed only from bars/s observed since the last start/resume/speed change and is shown as *unavailable* otherwise. **Worker health** comes from worker heartbeats (`GET /api/health` → `workers`).
- **Restarts**: stopping and restarting the API and worker processes needs no manual repair. A run that was mid-step resumes from its last committed checkpoint after its lease expires; a crash-loop guard fails a run only after 3 consecutive lease-expiry interruptions with no step committed between them.
- **Home / current run**: DEMO/SYNTHETIC banner, simulation time, synthetic price chart, latest MarketView, decision/action and reason (including risk blocks), paper position, action history.
- **Artifacts**: every completed/cancelled/failed run writes `manifest.json`, Parquet records (events, market views, decisions, risk decisions, plans, orders, fills, account/equity, observations), `validation.json` and `report.md` under `<artifact root>/runs/<run_id>/`. They are listed and viewable in the UI and via `GET /api/runs/{id}/manifest` and `/api/runs/{id}/artifacts[/{name}[?format=json]]`.
- **Fault injection (DEMO)**: `crash worker once` kills the worker process mid-step; after the lease expires a restarted worker resumes from the last committed checkpoint. `crash worker every attempt` ends as `failed` with an explanation after 3 attempts.
- `uv run algotrader replay` runs the engine in-process and prints the semantic trace hash.

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

- **Base URL** is configuration (`--base-url` or `ALGOTRADER_OKX_BASE_URL`; default `https://www.okx.com`). OKX documents regional domains (e.g. `https://my.okx.com`, `https://eea.okx.com`); none is assumed valid everywhere.
- **Datasets** live outside Git under `ALGOTRADER_DATA_ROOT` (default `./var/data`; Docker volume `marketdata`) in `datasets/<dataset_id>/`. Each has the exact raw source responses, a request/page log, the normalized instrument snapshot, normalized Parquet per family, `quality.json` and `manifest.json` with SHA-256 for every file.
- **Identity/immutability**: `dataset_id` is derived from the logical request, the market-data schema version, the availability policy and the SHA-256 of every raw response. Re-fetching identical source bytes reuses the existing dataset untouched. Changed source bytes create a new dataset, whose manifest lists the earlier versions in `prior_versions`. Existing dataset directories are never overwritten.
- **Time semantics**: candles keep the source `open_time`, a computed `close_time`, the modeled `available_time` and `retrieved_at` as separate fields. `available_time` follows the labelled modeling policy `okx.completed_1m_bar_available_at_close.v1` (bar close), which is not a measured publication time. Funding events keep the source `funding_time` and are never made available earlier. Unconfirmed candles (`confirm=0`) are rejected and reported.
- **Units**: traded candles keep contract volume, base-currency volume and quote-currency volume as separate fields with their currencies. Mark and index candles have no volume fields. Prices, rates and volumes are exact decimals (stored as the source decimal strings).
- **Quality**: gaps, duplicates (identical or conflicting), out-of-order pages, incomplete bars, invalid OHLC, prices or volumes, and out-of-window rows are reported with a severity (`info`, `warning`, `degraded`, `invalid`). Nothing is filled or repaired; invalid rows are kept with `quality=INVALID`.
- **Data view**: the UI's *Data* tab (and `GET /api/datasets[/{id}[/verify|/files/{name}]]`) shows source, instrument, coverage, row counts, quality and gaps, retrieval time, schema version, hashes and provenance files.
- Contracts are versioned separately as **`algotrader.marketdata.v1`** (`schemas/algotrader.marketdata.v1.json`, same frozen-baseline rules as below). Exchange-advertised leverage is stored as metadata only. Funding is recorded, not applied to any account.

## Causal feed and observable market state (WP-004, `algotrader.feed.v1` PROVISIONAL)

A pure domain core (`src/algotrader/feed/`), with no UI, database, worker, trader, account or execution dependency. It sits at the boundary **market evidence → causal availability feed → observable market state**. It is not yet wired into the worker or browser.

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

## Semantic contract baseline

The public semantic contracts (`src/algotrader/contracts.py`: journal payloads such as MarketObservation, MarketView, TradePlan, RiskDecision, Decision, OrderIntent, Order, Fill and AccountSnapshot, plus Run, RunConfig, ReplayControl and RunManifest) are frozen as **`algotrader.semantic.v1`**. Their JSON Schema is checked in at `schemas/algotrader.semantic.v1.json`, and every run manifest records the version in `schema_version`.

- `uv run algotrader schema` checks that the code still matches the baseline; `tests/test_schema.py` does the same in CI and fails on any drift.
- An intentional breaking change never edits a published baseline. Bump `SCHEMA_VERSION` (e.g. `algotrader.semantic.v2`) and run `uv run algotrader schema --write` to add a new file next to the old one; `--write` refuses to overwrite an existing baseline whose content differs.
- The PostgreSQL schema is migrated separately and in place (`db.MIGRATIONS`, recorded in `schema_migrations`).

Without `ALGOTRADER_TEST_DATABASE_URL` the database tests are skipped (CI sets `ALGOTRADER_REQUIRE_DB=1`, which turns that into a failure). CI (`.github/workflows/ci.yml`) runs all of the above and a Docker Compose smoke.

## Repository layout

| Path | Contents |
|---|---|
| `src/algotrader/contracts.py` | Semantic contracts (instrument, observation, MarketView, scenario, plan, decision, risk, order, fill, account, run, manifest) |
| `src/algotrader/synthetic.py` | Deterministic synthetic BTC-perpetual fixture |
| `src/algotrader/trader.py` | Trader interface + scripted DEMO dummy trader |
| `src/algotrader/risk.py`, `account.py` | Independent risk skeleton (1x cap); paper account and next-bar-open fill model |
| `src/algotrader/engine.py` | Pure, deterministic step engine and semantic trace hash |
| `src/algotrader/worker.py`, `db.py` | PostgreSQL-backed durable worker (leases, fencing, checkpoints, idempotent journal, parking of paused runs) and migrations |
| `src/algotrader/control.py` | Durable replay-control commands (pause/resume/step/speed/cancel) |
| `src/algotrader/schema.py`, `schemas/` | Semantic and market-data contract JSON Schema baselines and their generator |
| `src/algotrader/marketdata/` | Market-data contracts, OKX public REST adapter, bounded dataset acquisition/quality/verification |
| `src/algotrader/feed/` | Causal feed contracts (provisional), dataset→feed adapter, ordering/availability policies, pure observable-state reducer, snapshots/deltas |
| `tests/fixtures/okx/` | Small captured OKX public responses (see `PROVENANCE.json`) for offline tests |
| `src/algotrader/artifacts.py`, `validation.py` | Immutable run artifacts and validation checks |
| `src/algotrader/api.py`, `cli.py` | FastAPI app (commands, snapshots, SSE, artifacts) and CLI |
| `web/` | React + TypeScript UI (Vite) |
| `tests/`, `tests/e2e/` | Test suite and Playwright end-to-end smoke |

Toolchain pins: Python 3.14.7 (`.python-version`, `uv.lock`), Node 24.14.1 (`.nvmrc`, `web/package-lock.json`), PostgreSQL 18.6 image, uv 0.12.10.

The Project & Research Director replaces `task.md` after reviewing each pushed implementation.
