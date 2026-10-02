# Agent Instructions

This is the clean-room Algorithmic Trader project.

## Required reading and authority

Read FOUNDATION.md in full, then STATE.md, this file and task.md. Read only the compatible specifications/sources required for that task.

Current Owner instructions supersede earlier project documents. FOUNDATION.md v3.1 retains the 30 September direct clarification. Historical ACCEPTED/READY/HOLD labels in strategic_reviews/ and research/ do not authorize work; the current task must explicitly activate compatible scope. Report unresolved conflicts instead of silently choosing an old instruction.

## Roles and scope

Codex/Claude implement the single active task. Do not independently change product scope, integrated method, evidence criteria or risk policy. The Director owns these choices. An explicit Owner assignment can authorize strategic/documentation work, as in the v3.0 realignment.

Never import/reconstruct the legacy Trading Bot architecture, terminology, experiments, thresholds, results or conclusions. Preserve source_notes/ unchanged. Preserve frozen research cases/labels; do not “fix” a historical outcome to support a new method.

Capital, quantity, leverage, margin and orders are human decisions. No real-order connectivity. Do not claim dummy outputs are professional analysis.

## Local workflow and backtests

- The Owner updates the checkout before launching Claude. Never instruct Claude to pull and never run pull, including a no-op `pull --ff-only`, a startup habit or a synchronization alias. Do not synchronize/update the Owner-prepared checkout. Inspect the prepared branch, base and worktree; preserve unrelated changes and stop on unexpected divergence.
- Build only the bounded task. Preserve public contract versioning and M3 causal guarantees.
- Run required unit/integration/causality checks and bounded engineering smoke tests.
- **Do not launch substantial historical profitability runs, parameter sweeps or long research/backtests in an agent CLI.**
- Hand those evaluations to the Owner through the application: **READY FOR OWNER BACKTEST**, exact preset/config, expected time, purpose and where Copy report for chat is available.
- If the required app controls/reporting are missing, identify/implement them within an authorized task. Do not send the Owner raw-log or Python-command chores.
- Reuse fixed local datasets. No routine redownload or mandatory H24 collection.
- Always-NO_TRADE is not successful acceptance: expose coverage/candidate/rejection diagnostics. Do not force calls or weaken rules just to raise frequency.

## Git and reporting

After bounded changes and required checks succeed, the executor commits and pushes normally at the end of the work unless the task says otherwise. No force-push, history rewrite, secrets or unrelated changes. Stop on unexpected divergence; do not reconstruct main from a stale parent.

Report:
- base/final SHA and branch;
- what changed and why;
- checks actually run and results;
- implemented versus still planned capability;
- evidence/artifact locations and unresolved issues;
- Owner app backtest handoff when applicable.

The Director independently reviews; an executor's PASS is not acceptance.

## SR-003 operational boundary

Read `strategic_reviews/SR-003-DIRECTOR-DISPOSITION.md` for approved execution architecture. The Astra review is evidence; only task.md activates a package. R1A is not a real-month retry release. Preserve pre-upgrade September runs/datasets and legacy readers; no automatic salvage/relabel/redownload. All expensive phases need durable progress and incomplete diagnostic export. Changed provisional operational contracts require explicit revision/changelog and compatibility; frozen evidence/DEMO baselines remain unchanged. No advisory semantic.v2 during performance hardening. Never claim health/progress from CPU activity or heartbeat alone.

## Standing execution and handoff rules

Keep recurring instructions in this file; task.md and executor prompts contain only the active assignment and its specific acceptance evidence. Update README for implemented behavior/limitations and STATE with actual executor evidence; Director acceptance remains pending until independently reviewed. Do not activate the next package.

Use disposable, isolated services for engineering checks. Never run destructive Compose cleanup or rebuild shared image tags against the Owner's live stack. Report unavailable checks honestly and use isolated CI evidence when applicable; a silently skipped DB suite is not a pass.

Director handoff prompts must be ready to copy in a fenced text block, with no destination labels or surrounding explanation inside the block. Label the recipient outside it. For an Astra handoff, use a prominent level-one warning explicitly saying ASTRA, so the Owner cannot mistake it for a Claude prompt. These presentation rules do not authorize an executor to delegate work.
