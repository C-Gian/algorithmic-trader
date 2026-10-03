# Current Task — WP-008-R2 terminal reference correction
Status: **ACTIVE — EXECUTOR CORRECTION**
Date: 2026-10-03
Base implementation under review: `44ce68a`.

Read AGENTS.md and [WP-008-R2-DIRECTOR-REVIEW.md](delivery/WP-008-R2-DIRECTOR-REVIEW.md). Correct finding 1 only, within [the R2 specification](delivery/WP-008-R2-CAUSAL-TEMPORAL-SPEC.md).

Deep validation must compare a completed run's terminal clock-end aggregates and published temporal output with the separate reference, as well as existing committed-boundary checks. Preserve exact prefix-only scope for unfinished/partial targets and immutable original evidence. Missing or inconsistent required terminal evidence must not produce MATCH.

Provide the requested pending-final-tie / higher-horizon / terminal-output-tamper regressions and required repository checks; report version/scope decisions and final CI evidence. No new Owner run, acquisition or benchmark is requested. Do not activate MP-001, R3 or WP-009. Director acceptance remains pending.
