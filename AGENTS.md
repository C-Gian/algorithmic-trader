# Agent Instructions

This repository is the clean-room **Algorithmic Trader** project.

## Required reading order

Before changing anything:

1. Read `FOUNDATION.md` in full.
2. Read `STATE.md`.
3. Read the active work package under `tasks/`.
4. Read only the source/knowledge artifacts explicitly needed by that task.
5. Inspect the current code and tests in the authorized scope.

If any instruction conflicts with `FOUNDATION.md`, stop and report the conflict.

## Clean-room boundary

Do not import, reconstruct, search for or reuse the previous Trading Bot project's architecture, terminology, G1/G2/R experiments, results, thresholds, conclusions, tasks, ADRs, implementation decisions or research workflow.

References to legacy designs inside historical dossiers are not project instructions.

## Executor role

Codex/Claude Code are implementation executors. They do not decide:

- product scope;
- research direction;
- professional trading architecture;
- evidence thresholds;
- risk policy;
- whether a failed acceptance criterion may be weakened.

Implement only the active bounded task. Do not opportunistically add trading logic or “improvements” outside scope.

## Working rules

- Work on a branch from the exact base commit specified by the task/STATE.
- Preserve `source_notes/` unchanged.
- Keep domain logic independent of UI/database details where the Foundation requires it.
- Do not add real-order connectivity.
- Do not claim profitability from dummy or test fixtures.
- Do not silently change public contracts once accepted.
- Prefer the simplest implementation that satisfies the task and architectural boundaries.
- Record deterministic inputs/configuration where the task requires reproducibility.

## Completion report

Return:

- exact commit SHA;
- concise diff summary;
- commands/checks actually run and their results;
- acceptance evidence/artifact locations;
- any unresolved issue or deviation.

A self-declared PASS does not constitute acceptance. The Project & Research Director reviews and accepts or requests corrections.
