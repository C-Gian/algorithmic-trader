# Project State

Updated: 2026-09-30

## Authority

Canonical directive: `FOUNDATION.md`

## Accepted product scope

- BTC only.
- Paper execution instrument: BTC perpetual futures.
- Actions: LONG / SHORT / NO_TRADE; HOLD / REDUCE / EXIT while exposed.
- No leverage above 1x account-equity exposure.
- Intended trade duration: minutes to hours, not days.
- Research/paper only; no real capital.

## Current milestone

**M3 — Data and execution readiness for BTC perpetual paper operation**

The operational/dummy shell is accepted. M3 now establishes trustworthy real BTC-perpetual data, causal replay inputs and later paper-execution economics before any professional trader logic is implemented.

## Accepted work

### WP-001 — Repository bootstrap and one observable dummy run

Accepted implementation lineage:
- initial implementation: `92014aa03060332b4c947ef10329b79cde7d51b2`
- CI correction: `a49c0f75be7d9d885c65901c9cc73f3ed3a66a99`

Acceptance evidence:
- GitHub Actions run `36682981308`: SUCCESS;
- PostgreSQL-backed tests, browser E2E and Docker Compose smoke: SUCCESS;
- Director verified deterministic trace, browser reopen, worker crash recovery, idempotent fills, cancellation and artifacts.

### WP-002 — Complete replay/operations shell and freeze semantic contracts

Accepted implementation:
- `803b3f215c5a33499a4d901ae000ee112b75e691`

Acceptance evidence:
- GitHub Actions run `36685637348`: SUCCESS;
- `checks` and `compose-smoke`: SUCCESS;
- Director verified pause/resume, exact single-step behavior, speed invariance, full API/worker restart recovery, unique fills, browser reconnect and E2E evidence;
- semantic baseline `algotrader.semantic.v1` is frozen with schema-drift tests.

Accepted implementation interpretations:
- replay speed belongs to operational `ReplayControl`, not semantic `RunConfig`;
- `pausing`, `stepping` and `recovering` are runtime/operations states, not market/trading states;
- restart attempt accounting may reset the consecutive-interruption guard after a committed step;
- waiting for lease expiry on an unclean restart is acceptable at this milestone; graceful lease release is not required.

## Initial M3 market-data source decision

First public/read-only reference source: **OKX `BTC-USDT-SWAP`**.

Decision note: `knowledge/market_sources/OKX-BTC-USDT-SWAP.md`.

This is a data/reference choice for paper research, not a future real-money broker selection. No authenticated account or order endpoint is authorized.

## Active task

**WP-003 — OKX BTC-USDT-SWAP public data provenance and bounded historical dataset**

See `task.md`.

## Base knowledge snapshot

`3bf9de0d88fd97360bff7a6517bbb61544f5db68` — professional dossiers only.

## Blockers

None at product level.

Exact historical completeness and regional public endpoint behavior are evidence to be measured by WP-003, not assumed.

## Next action

The Owner pulls the latest repository and hands `task.md` to Claude Code. Claude Code implements WP-003, runs the required checks, commits and pushes. The Owner relays only Claude's completion report. The Project & Research Director then reviews the remote diff, CI, live-source evidence and produced dataset manifest.

WP-003 does not implement the professional trader or paper execution economics.
