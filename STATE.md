# Project State

Updated: 2026-09-29

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

**M2 — Operational shell with deterministic dummy trader**

The Foundation and repository workflow baseline are accepted on `main`.

## Active task

**WP-001 — Repository bootstrap and one observable dummy run**

See `tasks/WP-001.md`.

## Base knowledge snapshot

`3bf9de0d88fd97360bff7a6517bbb61544f5db68` — professional dossiers only.

## Accepted foundation/workflow commit

`e424c5cc779f616f1ff757ad6ff250abd279ccc8`

## Blockers

None at product level.

Initial real market/data venue selection is intentionally deferred; WP-001 uses deterministic synthetic data.

## Next action

Assign WP-001 to one implementation executor. The executor works from the repository instructions and task brief, then reports a branch/commit plus test/runtime evidence. The Project & Research Director independently reviews the diff and evidence before accepting or requesting corrections.
