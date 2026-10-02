# Active Task — WP-008-R1C correction

Status: **READY — ONLY ACTIVE IMPLEMENTATION PACKAGE**
Date: 2026-10-03 (Europe/Rome)
Implementation under review: `6745117ee1010510abfa6247bfc40c1331fff7c1`.

Correct all findings in `delivery/WP-008-R1C-DIRECTOR-REVIEW.md` under AGENTS.md and the accepted SR-003 disposition. Retain the implemented R1C pipeline and useful measured month evidence.

## Required outcomes

- Reconciliation v2 requires a trusted receipt matching the run/cache pin. An absent receipt cannot produce PASS. Preserve historical stored validator claims/readers.
- Deep cancellation and terminal publication are serialized under the diagnostic row lock and generation fence. A cancellation accepted before terminal commit yields CANCELLED/INCOMPLETE; a later command rejects the terminal job. Cover every applicable phase, including report generation and the final boundary, while keeping original replay records immutable.
- Assurance headlines keep original runtime integrity and Deep reference outcome distinct. Deep MATCH cannot promote failed/incomplete/not_checked runtime assurance or conceal warnings/limited coverage.
- Benchmark/report gates distinguish complete measured month application paths from annual component comparisons. Annual application gates are NOT_MEASURED/PENDING unless actually measured end-to-end under a bounded synthetic engineering budget. Preserve both previous raw measurement runs; no real historical CLI evaluation. A proposed month-only September handoff is permitted for Director review, with annual readiness explicitly pending.

## Required verification and handoff

Implement the regression inventory in the Director review: missing receipt in a real terminal path; Deep preparation/report/final-lock cancellation and post-commit rejection; stale generation; failed/incomplete runtime plus Deep MATCH; cancelled follow-up diagnostics; report determinism and original immutability. Retain existing protected/DB/API/E2E/control/durability checks and run required isolated CI. No redundant benchmark rerun unless changed code affects that measurement.

Update benchmark evaluator/evidence interpretation, README/STATE and proposed app handoff consistently. Keep previous measurement files as historical evidence. Use actual verified run totals and manifests; do not hard-code the Owner-reported 129,600 as proof. Surface warnings and residual limits; no acquisition or automatic retry.

## Boundary and exit

R2/method/adviser work, real historical CLI runs, new corpus acquisition and September retry remain inactive.

Finish **READY FOR DIRECTOR REVIEW — R1C CORRECTION ONLY**, with the revised concrete Owner app handoff and any unclosed annual gates. **Do not announce READY FOR OWNER MARKET REPLAY before Director acceptance.**
