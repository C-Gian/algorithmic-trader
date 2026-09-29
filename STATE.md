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

See `task.md`.

## Base knowledge snapshot

`3bf9de0d88fd97360bff7a6517bbb61544f5db68` — professional dossiers only.

## Accepted foundation/workflow commit

`e424c5cc779f616f1ff757ad6ff250abd279ccc8`

## Blockers

None at product level.

Initial real market/data venue selection is intentionally deferred; WP-001 uses deterministic synthetic data.

## Next action

The Owner pulls the latest repository and hands `task.md` to Claude Code. Claude Code implements only that task locally and reports its checks/evidence. The Owner then commits/pushes the completed work. The Project & Research Director reviews the updated repository and either accepts it or replaces `task.md` with corrections/the next bounded task.
