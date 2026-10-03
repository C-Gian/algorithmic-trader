# Current Task — WP-008-R2 causal temporal substrate
Status: **ACTIVE — EXECUTOR IMPLEMENTATION**
Date: 2026-10-03 (Europe/Rome)
Prerequisites: R1A/B/C and WP-010 accepted; Owner September incident closed.

Read AGENTS.md for standing workflow rules and implement [WP-008-R2-CAUSAL-TEMPORAL-SPEC.md](delivery/WP-008-R2-CAUSAL-TEMPORAL-SPEC.md) in full.

## Purpose
Add shared factual UTC multi-horizon aggregation and explicit causal clock/dispatch state to the accepted streaming kernel, with bounded incremental state and direct checkpoint restore. This enables the first integrated adviser; it is not a strategy or a new general infrastructure programme.

## Required result
- Separate trade/mark/index aggregates: 15m, 1h, 4h, day, Monday week and calendar month; exact completion/known-at and explicit incomplete/outside-coverage states.
- Conservative sealed-interval late policy; modeled complete-prefix barriers distinct from logged recorded receipt/dispatch barriers; deterministic timers, finite clock horizon, pause/STEP semantics.
- Dependency-specific readiness/freshness, bounded retention and restorable temporal/dispatch state in the existing fenced checkpoints.
- Explicit new contract/state/engine/validator versions where necessary; preserve legacy runs, cache/source identities, readers and immutable evidence.
- Minimal expandable temporal inspection and copyable diagnostics; no broader UX redesign.
- The specification's hand-expected, cutoff, clock/tie, timer, restore, bounded-state and compatibility evidence plus required checks.

## Exclusions
No semantic.v2, professional observations/economic thresholds, scenarios/calls, P&L, corpus acquisition, real-month agent run, live connections or Owner stack changes. Do not activate MP-001/R3/WP-009. Production lookbacks and decision authority remain MP-001 choices; optional horizon unavailability is not a universal gate.

Report actual changes/checks/limits and contract revisions precisely. Director review only; no new September Owner run is requested.
