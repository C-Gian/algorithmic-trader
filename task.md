# Current task — WP-014 CORRECTION (Astra review of 0526641)
Date: 2026-10-08. Status: DELIVERED — READY FOR DIRECTOR REVIEW — WP-014 CORRECTION ONLY ([evidence §9](delivery/evidence/WP-014-ENGINEERING-EVIDENCE.md)); remote CI Owner-operated, PENDING / NOT CHECKED. The continuous v0.4/v0.5 plan stays INACTIVE.

Correct only F1–F3 and the listed alignments on [WP-014](delivery/WP-014-MP-004-IMPLEMENTATION-SPEC.md) (commit `0526641`). [MP-004](delivery/MP-004-V05-RETURN-RESPONSE.md), its [closure](delivery/MP-004-DIRECTOR-CLOSURE.md) and the methodological decisions stay unchanged.

- **F1:** keep the inherited protections over the whole dispatch, but consume the local sequence at its first ordered decisive event; a later local violation never reclassifies an already consumed late first recovery.
- **F2:** preserve `EMPTY_RETURN_CORRIDOR` and `NO_ECONOMIC_RETURN_REGION` during WAIT_RESPONSE, after the cap updates/protections and before the local response. Distinguish an empty historical region, a single unsuitable price and a live temporary cost block.
- **F3:** the earlier 20-owner RETURN criterion is NOT_APPLICABLE to v0.5: keep the descriptive counts, remove its effect on verdict, Markdown, UI and comparison, and introduce no substitute. Earlier versions keep their behaviour.
- **Alignments:**
  - late first recovery in OTHER_GATES (specific reason and late count kept, no fourth class);
  - straddling only when start < p0 < end;
  - WAIT-open cohort explanation in the monthly comparison;
  - a separate erratum of the pinned spec's §6 ratios (SHORT valid 1.934932545…, insufficient ≈ 0.971777) without rewriting the authoritative document or its identity.
- **Register:** accepted only for the choices Astra verified (108 inherited values, `references_per_child = 1`). No other methodological change.

Synthetic bounded data only; no acquisition, Owner extraction, backtest or economic run; the Owner stack stays untouched. Follow AGENTS for isolated checks, commit/push and Owner-operated CI.
