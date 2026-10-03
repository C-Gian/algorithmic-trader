# Current Task — Owner September Market replay check

Status: **READY FOR OWNER MARKET REPLAY — SEPTEMBER 2025 ONLY**
Date: 2026-10-03 (Europe/Rome)
Accepted implementation: `99e0ca5b9bfed7cb57cae1aff5c7b899234e8cac`.
Director release decision: `delivery/WP-008-R1C-DIRECTOR-REVIEW.md` (correction closure).

No executor implementation package is active. R2 and later packages remain HOLD while the Owner runs the app check. Do not launch real historical work in an agent CLI.

## Owner action

1. Stop old application containers, update the prepared checkout and start the rebuilt stack with the controlled README upgrade. Preserve database/data/artifact volumes.
2. Historical Workbench → Run setup → Market replay → EXISTING Verified September 2025 chunk → pacing max, not start-paused → Start. One new run ID; preserve the old suspended run and local source; no Prepare/download/salvage.
3. Copy terminal Markdown/report into the Director chat. If failed, cancelled or slow, copy its current diagnostic instead. If Copy gives no confirmation, attach the downloaded Markdown. Deep validation is optional and has its own report.

Expected useful result: COMPLETED, committed cursor equal to this run's verified total, runtime assurance passed with cache_receipt_and_pin and completed_consumed_entire_feed, actual timings/host/source identity and disclosed warnings/limits. The historical 129,600 is a comparison fact, not a hard-coded acceptance test. Synthetic reference timing is not a promise for the Owner PC.

If the run is substantially beyond ~10 minutes, send the current diagnostic and do not launch another run. The Director assesses it; no manual logs/SQL/CLI benchmark is required.

## Director next action

Review the Owner result against source/preset, preserved old evidence, actual coverage, runtime/reference assurance, controls, phase timing and claimed structural improvement. Link old/new IDs when actually supplied. Close the September incident or define a bounded evidence-based correction; only then activate the next implementation package.

Annual application gates remain NOT_MEASURED/PENDING, recording volume remains limited, and Windows directory-fsync power-loss durability is unproven. The earlier Copy feedback E2E failure is recorded for follow-up; final CI passes but root cause is not isolated. No annual-readiness or adviser/P&L claim is authorized.
