# Algorithmic Trader

Algorithmic Trader is a clean-room BTC-only research and paper-trading project whose goal is to translate professional market-reading and trade-decision practice into a deterministic, inspectable software trader.

## Current state

The project is completing the **operational shell (WP-002: replay/operations controls and semantic contract baseline v1)**. The repository contains the accepted foundation, the professional source dossiers and a runnable shell driven by a scripted **DEMO dummy trader** on a **synthetic** BTC-perpetual fixture. The real trader has not been implemented; nothing the shell shows is market data or research evidence.

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
| `src/algotrader/schema.py`, `schemas/` | Semantic contract JSON Schema baseline and its generator |
| `src/algotrader/artifacts.py`, `validation.py` | Immutable run artifacts and validation checks |
| `src/algotrader/api.py`, `cli.py` | FastAPI app (commands, snapshots, SSE, artifacts) and CLI |
| `web/` | React + TypeScript UI (Vite) |
| `tests/`, `tests/e2e/` | Test suite and Playwright end-to-end smoke |

Toolchain pins: Python 3.14.7 (`.python-version`, `uv.lock`), Node 24.14.1 (`.nvmrc`, `web/package-lock.json`), PostgreSQL 18.6 image, uv 0.12.10.

The Project & Research Director replaces `task.md` after reviewing each pushed implementation.
