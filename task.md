# Current Task — WP-009 correction follow-up
Status: **ACTIVE — EXECUTOR CORRECTION**
Date: 2026-10-05. Reviewed commit: `d16c9251e9cb8d20ab2f4db78526d8b057423997`.

Correct only the remaining Deep resume case under original finding 7 in [the correction review](delivery/WP-009-CORRECTION-DIRECTOR-REVIEW.md). Findings 1–6, 8 and 9 are closed for this slice. Preserve MP-001 v0.2, accepted correction behavior, frozen schemas, Owner data and saved outputs; no next package.

On every resume, retain newly detected stored record/digest/sequence/chain inconsistencies alongside saved mismatches. No suppression based on a nonzero saved cursor; bound/deduplicate diagnostics as needed. Read the exact-code [probe](delivery/evidence/WP-009-CORRECTION-DIRECTOR-RESUME-PROBE.json).

Acceptance: DB fail-before/fixed-after tests starting from a CLEAN nonzero-cursor pause, then digest-only alterations in both professional record tables and a last-row chain alteration; never MATCH after resume. Clean repeated pause/resume, byte tampering, cancel/fencing and report determinism remain green. Run appropriate focused checks plus final DB-required non-E2E/E2E, web/schema and exact-final-SHA CI including Compose smoke. Record actual evidence, compatibility/diagnostic version decision and limits in README/STATE.

Completion: **READY FOR DIRECTOR REVIEW — WP-009 CORRECTION FOLLOW-UP ONLY**. Owner Backtest A stays inactive until acceptance. Standing workflow is in AGENTS.md: Claude changes code and runs bounded engineering checks; substantial backtests are launched by the Owner through the web app, with Copy report for chat returned to the Director.
