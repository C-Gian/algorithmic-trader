# Active Task — WP-001R1: Fix First Real CI Run

Status: READY  
Owner: Project & Research Director  
Executor: Claude Code  
Base: latest `main` after the Owner runs `git pull`.

## Context

WP-001 implementation is already pushed at commit `92014aa03060332b4c947ef10329b79cde7d51b2`.

The Director reviewed the pushed implementation and the first real GitHub Actions run.

What is already confirmed:

- the Docker Compose smoke job **passed** on GitHub Actions, so the documented `docker compose up --build` stack has now been exercised successfully outside the developer machine;
- the local implementation report showed the unit/integration/E2E suite passing;
- the `checks` CI job failed **before tests started**, during runner setup;
- the exact failure was:
  `Unable to resolve action astral-sh/setup-uv@v10, unable to find version v10`.
- the upstream repository currently publishes the stable immutable release `astral-sh/setup-uv@v10.2.0` (published 2026-09-21).

WP-001 is not accepted until the required CI checks actually run and pass.

## Objective

Repair the CI configuration so the full `checks` job can execute, preserve the already-passing Compose smoke, and push the correction.

This is a correction-only task. Do not start the next work package.

## Required work

1. Inspect `.github/workflows/ci.yml` and the existing WP-001 implementation before editing.
2. Replace the invalid setup-uv action reference with the verified stable immutable release:
   `astral-sh/setup-uv@v10.2.0`.
3. Check the workflow for any immediately related version/reference mistake that would prevent the existing intended CI from starting. Do not opportunistically redesign CI.
4. Do not change application/trading behavior unless a CI failure after the reference fix exposes a genuine implementation defect.
5. Run appropriate local validation for any files you change.
6. Commit the bounded correction with a meaningful message and push it to the current branch/origin. Do not force-push.

## If CI exposes another failure after push

If you can inspect the GitHub Actions result from your environment:

- inspect the failing job/step;
- fix only genuine WP-001 defects;
- rerun relevant local checks;
- commit and push the correction;
- repeat until the WP-001 workflow is green or you hit a blocker you cannot resolve safely.

If you cannot inspect GitHub Actions after pushing, stop after the push and report the final commit SHA. The Director will inspect CI remotely.

## Acceptance

The Director will accept WP-001 only when:

- GitHub Actions `checks` completes successfully, including PostgreSQL-backed tests and browser E2E;
- GitHub Actions `compose-smoke` remains successful;
- no unrelated scope was added;
- the deterministic/dummy-only boundary remains intact.

## Prohibited changes

Do not:

- modify `FOUNDATION.md`, `STATE.md`, `AGENTS.md` or `source_notes/`;
- start real market-data or trader work;
- replace PostgreSQL or alter architecture as part of this correction;
- change demo risk/cost placeholders merely to make tests pass;
- weaken/remove tests or acceptance criteria;
- force-push or rewrite shared history.

## Completion report

Report only what the Owner needs to relay to the Director:

- base commit and final pushed commit SHA;
- files changed;
- local checks actually run and results;
- pushed branch;
- GitHub Actions result if you were able to inspect it;
- any unresolved issue/deviation.

Do not declare WP-001 accepted; acceptance belongs to the Director.
