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

**WP-001R1 — Fix first real CI run before WP-001 acceptance**

See `task.md`.

## Base knowledge snapshot

`3bf9de0d88fd97360bff7a6517bbb61544f5db68` — professional dossiers only.

## Accepted foundation/workflow commit

`e424c5cc779f616f1ff757ad6ff250abd279ccc8`

## Blockers

No product blocker. WP-001 implementation is present, but its first GitHub Actions run failed before the test suite because `astral-sh/setup-uv@v10` is not a resolvable action tag. The independent Docker Compose smoke job passed.

## Next action

The Owner pulls the Director's updated `task.md` and hands it to Claude Code. Claude Code fixes WP-001R1, runs the required checks, commits and pushes. The Owner relays only Claude's completion report. The Project & Research Director then verifies the pushed commit and GitHub Actions directly before accepting WP-001 or issuing another correction.
