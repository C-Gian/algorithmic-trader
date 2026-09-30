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

**M2 — Operational shell with deterministic dummy trader**

WP-001 is accepted. The first executable shell, durable worker, PostgreSQL persistence, artifacts, UI, crash recovery and CI are proven. One final operational-shell package remains before real BTC data/execution readiness.

## Accepted work

### WP-001 — Repository bootstrap and one observable dummy run

Accepted implementation lineage:
- initial implementation: `92014aa03060332b4c947ef10329b79cde7d51b2`
- CI correction: `a49c0f75be7d9d885c65901c9cc73f3ed3a66a99`

Acceptance evidence:
- GitHub Actions run `36682981308`: SUCCESS;
- `checks`: SUCCESS, including PostgreSQL-backed tests and Playwright E2E;
- `compose-smoke`: SUCCESS;
- E2E artifact verified by the Director, including browser reopen, worker crash/recovery, deterministic trace, LONG/SHORT/NO_TRADE, risk blocks, cancellation and inspectable artifacts.

## Active task

**WP-002 — Complete replay/operations shell and freeze semantic contracts**

See `task.md`.

## Base knowledge snapshot

`3bf9de0d88fd97360bff7a6517bbb61544f5db68` — professional dossiers only.

## Blockers

None at product level.

Initial real market/data venue selection remains intentionally deferred until the operational shell is complete.

## Next action

The Owner pulls the latest repository and hands `task.md` to Claude Code. Claude Code implements WP-002, runs the required checks, commits and pushes. The Owner relays only Claude's completion report. The Project & Research Director then reviews the remote diff, CI and evidence directly.

If WP-002 is accepted, the project moves to **M3 — Data and execution readiness for BTC perpetual paper operation**.
