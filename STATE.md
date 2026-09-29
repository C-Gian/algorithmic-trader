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

**M1 — Foundation and repository workflow**

Foundation decisions are resolved and the canonical directive is being established.

## Active task

**WP-001 — Repository bootstrap and one observable dummy run**

See `tasks/WP-001.md`.

## Base knowledge snapshot

`3bf9de0d88fd97360bff7a6517bbb61544f5db68` — professional dossiers only.

## Blockers

None at product level.

Initial market/data venue selection is intentionally deferred; it does not block WP-001 because WP-001 uses deterministic synthetic data.

## Next action

Run WP-001 through an implementation executor, then have the Director independently review its diff, tests and runtime artifacts before acceptance.

## Accepted implementation commit

Pending merge of the Foundation/workflow bootstrap.
