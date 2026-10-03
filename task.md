# Current Task — WP-008-R3 correction
Status: **ACTIVE — EXECUTOR CORRECTION ONLY**
Date: 2026-10-03
Reviewed implementation: 33c2b83. Decision: CORRECTION REQUIRED.

Fix findings1–3 in [Director review](delivery/WP-008-R3-DIRECTOR-REVIEW.md): verified ownership of contributor facts, actual artifact-byte validation/POSIX directory durability before receipt publication, and staging cleanup scoped to safe attempt ownership. Preserve the [R3 specification](delivery/WP-008-R3-CONTEXT-PRESETS-SPEC.md), registered windows, source/frozen contract semantics and accepted method.

Required regressions: real cold/warm contributor mutation and pinned rebuild; altered manifest/provenance with no successful trusted publication, fsync ordering/crash/cancel/fence/convergence; two concurrent pack jobs/workers and reclaim without deleting another live staging directory. Keep earlier composition/continuity/reuse/Deep/browser tests and required checks. Report actual evidence and unresolved limits in STATE. Standing workflow is in AGENTS.md.

No Owner preparation/run handoff, substantial acquisition, method change, semantic.v2 or WP-009 activation. Completion: READY FOR DIRECTOR REVIEW — R3 CORRECTION ONLY.
