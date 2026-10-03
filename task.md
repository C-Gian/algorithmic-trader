# Current Task — WP-010 Documentation clarity and bounded UX wording
Status: **ACTIVE — EXECUTOR IMPLEMENTATION**
Date: 2026-10-03 (Europe/Rome)
Director assignment following the Owner's instruction to proceed. Read AGENTS.md for permanent workflow rules.

## Purpose
Make the current operational truth immediately readable, preserve historical evidence, and correct three misleading UX descriptions. This is a bounded closure task, not a new strategic review, redesign or infrastructure programme.

## Current Director decisions
The Owner September check is accepted and its original replay performance incident is closed:
- evaluation `eval-20261003T091928-a7eb00`; replay `obs-20261003T091928-363a3d`;
- COMPLETED; coverage COMPLETE 129600/129600; runtime assurance PASSED; observe.stream-reconciliation v2 PASS 9/9;
- trusted receipt/cache/run pin matched; entire feed consumed; elapsed 60.4 s; 27 committed transactions; zero delivery rows; zero recoveries;
- evidence is the Owner's copied terminal report, reviewed by the Director, not an independently rerun benchmark;
- no Deep validation of this run was performed; no adviser or trading performance was evaluated.
Annual application performance gates remain NOT_MEASURED/PENDING; recording-volume evidence is limited; Windows directory fsync power-loss durability remains unproven.
The UX pass at `d8144ad` has independently green CI `37116003888` (checks including E2E and compose-smoke). It improves Workbench/Replay Lab; it does not close the UX of Data, Recorder or mobile. Old Copy-feedback failure cause remains plausible, not proven.

## Work
1. Reorganize STATE.md as current implementation, accepted evidence, open limits and next step. Move its displaced chronology to one clearly historical document in an existing review/delivery area, preserving factual evidence and links. Do not create a new ADR/changelog framework.
2. Make README an operational guide to implemented capabilities: startup/upgrade, reusable local data, normal Workbench path, report location and relevant limitations. Link history rather than repeat acceptance/rejection chronology.
3. Update the integrated delivery plan and SR-003 disposition's current-action pointers: September is closed, this task is active, and the next Director action is a bounded R2 substrate specification reviewed against adviser dependencies, followed by integrated method closure. Preserve the Foundation's sequence; this task does not activate R2, MP-001, R3 or WP-009.
4. Correct UX/report wording wherever shared:
   - a pause REQUEST or pausing state must say pause requested/pausing until actually paused; do not promise no processing before acknowledgement;
   - modeled historical replay must not claim exact measured historical availability; explain the dataset availability convention, retaining measured-vs-modeled distinctions;
   - Deep validation is a reference re-execution with a shared reducer and canonical-cache scope, not a wholly independent method or original-source audit.
5. Maintain the same visual style and all data/control access. Make no broader UX redesign.
6. Validate changed state presentations and documentation links. Use small meaningful regressions for pause-state and availability wording; use required existing checks appropriate to the changes. Report checks unavailable locally honestly.

## Boundaries
No engine/reducer, fencing, checkpoint or assurance-criteria changes. No schema/migration/contract changes; no acquisition, historical profitability runs, Owner stack access or modification of frozen sources/cases. No new general infrastructure or automatic documentation bureaucracy.
FOUNDATION.md stays the stable product authority; AGENTS.md contains recurring execution rules. Existing review evidence must remain traceable.
The next product objective is the first complete adviser path, not a rushed isolated LONG rule. Timing/cycle/news/derivatives roles require explicit bounded dispositions; missing optional context cannot become endless infrastructure work or silent neutral confirmation.

## Acceptance
A fresh executor can find the current status/task without reconstructing the delivery chronology. README describes actual usage. September closure and residual limits are distinct. Historical facts remain accessible with working links. Pause pending vs paused, modeled vs measured availability, and reference-vs-runtime assurance are explained truthfully across affected UI text.
In the completion report identify historical content moved, authoritative current sections, wording corrected, checks actually run and any unresolved inconsistencies. Director review is required; do not activate the next package.
