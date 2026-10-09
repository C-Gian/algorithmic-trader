# Current task — four R→N paths of the Owner v0.5 run (read-only diagnosis)
Date: 2026-10-09. Status: DELIVERED — READY FOR DIRECTOR REVIEW — FOUR R→N PATHS DIAGNOSIS ONLY ([summary](delivery/evidence/WP-014-OWNER-V05-RN-DIAGNOSIS/SUMMARY.md)). Remote CI is Owner-operated: PENDING / NOT CHECKED. No further package is activated.

## Preceding record

WP-014 CORRECTION (Astra review of `0526641`) was delivered at `eab7d23`; see the STATE.

## Assignment (Owner-relayed Director instruction)

**Scope.** A bounded diagnosis of the four R→N children of run `eval-20261009T155751-be8b2b` (build `eab7d23`): the first recoveries that were not issuable. There is one LONG and three SHORT. The WAIT-open cohorts are September 1, November 1 and December 2.

**Access.**
- Read-only artifacts and surfaces first.
- If they are insufficient, one REPEATABLE READ READ ONLY extraction from the Owner DB, limited to this run and these paths.
- No write or stack change. Raw exports stay outside Git.

**Per path, document:**
- child/scenario, direction and WAIT opening;
- the reference bar: ID, interval, OHLC, p0, cursor and tick;
- the geometry at the preparation: R/K, structural and operational V, target/cap, corridor, economic region, costs and reward/risk;
- the first recovery: bar, times/cursor, evaluated price, ratio, all blockers and the primary reason;
- only the relevant changes between the preparation and the recovery.

**Definitions.**
- E0 = prices admitted by corridor and economics at the preparation.
- E1 = the same at the recovery.
- F = LONG close ≥ H0 + tick; SHORT close ≤ L0 − tick.

**Checks, separately:**
1. E0 ∩ F empty at the preparation.
2. E0 ∩ F non-empty, but the confirming close is outside the usable region with unchanged geometry.
3. Later documented restrictions that change E0 into E1.

Explanations may coexist, and no exclusive class is forced.

**Labels and method.**
- Every value is labelled STORED, DERIVED or UNAVAILABLE.
- Use the pinned formulas and rounding.
- No parameter search, alternative-rule simulation, future data or intrabar inference.

**Reconcile.**
- R = 4, N = 4, I = 0.
- Blocker incidence: REWARD_RISK_BELOW_MINIMUM 4, CLOSE_OUTSIDE_RETURN_CORRIDOR 1.
- Primary reasons: reward/risk 3, outside the corridor 1.

**Deliverable and boundaries.**
- A table of the four paths and a short summary.
- No general dossier, no link to v0.4 outcomes, no rule, threshold or parameter proposal.
- Record the descriptive acceptance of the result and this task in STATE.
- No product, method, identity, schema or stored-result change.
- No acquisition, replay, Deep validation or economic evaluation.
- No product suites, E2E or Compose are needed.
- CI is followed by the Owner. Commit and push per AGENTS.md.
