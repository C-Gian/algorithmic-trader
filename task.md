# Active Task — WP-008-R1A correction

Status: **READY — ONLY ACTIVE IMPLEMENTATION PACKAGE**
Date: 2026-10-02
Implementation under review: `66a2dce90619848776e891e7f50f0f8440d95eb4`.

Correct the Director findings in `delivery/WP-008-R1A-DIRECTOR-REVIEW.md`. Apply the standing rules in AGENTS.md and the accepted SR-003 disposition. Preserve the implemented R1A architecture; this is a bounded correctness/observability correction, not R1B.

## Required outcomes

- Already requested cancellation ends at a bounded safe boundary with CANCELLED/INCOMPLETE diagnostics, without mandatory full-prefix loading, source reload or reference re-derivation. Cancellation during terminal phases is checked before terminal publication/commit. Keep committed evidence and all generation fences. Controls remain normally <=2 s and <=5 s at a bounded safe unit under local CPU load; expose any unavoidable atomic boundary truthfully.
- Replay ETA uses a comparable current replay window; preparation, pause/downtime and declared waits cannot be mislabeled active replay throughput. Reset rate bases when phase, substage/unit/total, generation or relevant controls change; insufficient observations yield unknown.
- Active, wall and waiting durations have explicit consistent meanings. Interrupted unmeasured spans remain visibly unknown/incomplete. Terminal-phase messages reflect actual committed coverage and separate completion from assurance.

## Required verification

Implement the short regression fixtures and acceptance evidence listed in the Director review. Measure cancellation latency and reference-work counters after a meaningful partial prefix, as well as configured paused/resumed and terminal-phase cancellation. Retain existing full-cursor cancellation, supervision and stale-generation publication checks. Verify phase/substage ETA boundaries, pacing/wait accounting and interrupted unknown timing. Run required existing DB/E2E, web checks and isolated CI smoke; report exactly what ran. Preserve revision-1 observe readers and frozen schema bytes; no unnecessary contract revision.

## Boundary and handoff

No streaming/cache rewrite, sparse persistence, new checkpoint/validator design, method/trader changes, old-run salvage, redownload or September retry. R1B remains inactive. Record corrected behavior, regression results, measured latency/counters and remaining performance costs.

Finish with **READY FOR DIRECTOR REVIEW — R1A CORRECTION ONLY**.
**NOT READY FOR OWNER MARKET REPLAY.**
