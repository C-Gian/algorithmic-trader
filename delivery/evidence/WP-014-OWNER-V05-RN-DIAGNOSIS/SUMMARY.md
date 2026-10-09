# Four R→N paths of the Owner v0.5 run — read-only diagnosis

Evaluation `eval-20261009T155751-be8b2b` · replay `obs-20261009T155751-0f255b` · build `eab7d23438d7188118600dbb358f9136f96bd32b` · method `btc.context-action.v0.5` / `mp004.rules.v0.5` (rules `0e34059a17f6`, register `255ab5b7cc59`, both re-checked against the build). Scope: the four first recoveries that were observed and not issuable (R = N = 4, I = 0). This is not a general dossier. It makes no link to v0.4 outcomes and proposes no rule.

**Access.** Only the app's own read-only GET surfaces were used: the evaluation, report.json/md, the journal pages of `entry_attempt` and `scenario` records, and the bounded bar window. That window comes from the pinned SHA-verified cache and is clamped to events strictly before the cursor of each recovery dispatch, so no later bar was read. The authorized DB extraction was **not used**. Raw exports stay outside Git; their SHA-256 are listed in [paths.json](paths.json). There was no write, replay, Deep validation, acquisition or economic evaluation.

**Labels.**
- **S** = STORED: a journal or report field, or a bar from the pinned cache.
- **D** = DERIVED: exact arithmetic using the pinned formulas (`geometry.predicate`, `geometry.admissible_bounds`, `core3` corridor rounding, `core5.local_verdict` / `primary_reason`) and register values (net reward/risk ≥ 1.2, historical cost 14 bps). The inputs come only from the record whose cutoff is stated.
- **U** = UNAVAILABLE.

**Definitions.**
- **E0** = corridor ∩ economic region in the preparation record (`RESPONSE_REFERENCE`, published at p0).
- **E1** = the same in the first-recovery record.
- **F** = prices satisfying the local recovery close: LONG close ≥ H0 + tick; SHORT close ≤ L0 − tick.

The stored corridor, E0 and E1 were re-derived from their own records with the pinned formulas and are equal. The stored G, Q, margin and blockers were also re-derived at the evaluated price and are equal.

## Four paths

| Field | Lbl | #1 | #2 | #3 | #4 |
|---|---|---|---|---|---|
| Child (`…#entry`) | S | AS-2025-09-13T16:45…18955ad23d59 | AS-2025-11-17T20:00…6114b7079cf7 | AS-2025-12-01T16:00…cfdb2979f085 | AL-2025-12-25T15:45…6eeeab2b228d |
| Direction · WAIT open (published, cursor) · cohort | S | SHORT · 09-13 18:03, 206289 · 2025-09 | SHORT · 11-17 21:18, 487674 · 2025-11 | SHORT · 12-01 16:55, 547365 · 2025-12 | LONG · 12-25 16:27, 650961 · 2025-12 |
| Reference bar · interval | S | `#obs@…18:15Z` · [18:15, 18:16) | `#obs@…21:43Z` · [21:43, 21:44) | `#obs@…17:07Z` · [17:07, 17:08) | `#obs@…16:37Z` · [16:37, 16:38) |
| O / H0 / L0 / C | S | 115517.1 / 115520 / 115517.1 / 115519.9 | 91873.3 / 92045.5 / 91823.5 / 92031 | 84815 / 84962.5 / 84815 / 84937.9 | 88197.4 / 88197.5 / 88157.2 / 88169.5 |
| p0 · c0 · tick | S | 18:16 · 206328 · 0.1 | 21:44 · 487752 · 0.1 | 17:08 · 547404 · 0.1 | 16:38 · 650994 · 0.1 |
| R · K (trigger) | S | 115560.2 · 115469.7 | 92223.5 · 91877.4 | 85419.2 · 84499.2 | 88125.9 · 88410.7 |
| V structural / V operational | S | 115573.9 / 115573.9 | 92278.475 / 92278.5 | 85463.99 / 85464.0 | 88113.96 / 88113.9 |
| T confirm / cap at preparation | S | 115093.8 / 115093.8 | 91310.1 / 91310.1 | 83825.0 / 83825.0 | 88564.3 / 88564.0 (cap revised 16:30, before p0) |
| Corridor (structural = effective) | S | 115469.7..115560.2 | 91877.4..92223.5 | 84499.2..85419.2 | 88125.9..88410.7 |
| **E0** (economic region in the corridor) | S | **115517.4..115560.2** | **91967.1..92223.5** | **84837.8..85419.2** | **88125.9..88195.0** |
| Cost K · min ratio · ratio at reference close | S·S·D | 14 bps · 1.2 · 1.2255 | 14 · 1.2 · 1.5732 | 14 · 1.2 · 1.5410 | 14 · 1.2 · 1.5140 |
| Domain bars checked (L,H,C → verdict) | S/D | 18:16 (115504.7, 115520, 115504.7) → RECOVERY | 21:44 (91782.7, 92030.9, 91815) → RECOVERY | 17:08 (84837.4, 84937.9, 84917.2) → NONE; 17:09 (84755.9, 84923.1, 84775) → RECOVERY | 16:38 (88169.5, 88200, 88190.1) → NONE; 16:39 (88190, 88222, 88192.7) → NONE; 16:40 (88192.6, 88217, 88216.9) → RECOVERY |
| First recovery: bar · published · cursor · current | S | [18:16, 18:17) · 18:17 · 206331 · yes | [21:44, 21:45) · 21:45 · 487755 · yes | [17:09, 17:10) · 17:10 · 547410 · yes | [16:40, 16:41) · 16:41 · 651003 · yes |
| Evaluated price (historical close) | S | 115504.7 | 91815 | 84775 | 88216.9 |
| (G−K)/(Q+K) · margin | D·S | 1.0792 · −2.415 | 0.6357 · −36.387 | 1.0293 · −16.267 | 0.9872 · −5.465 |
| All blockers → **primary** | S | RR → **RR** | CLOSE_OUTSIDE, RR → **CLOSE_OUTSIDE** | RR → **RR** | RR → **RR** |
| F | D | (−∞, 115517.0] | (−∞, 91823.4] | (−∞, 84814.9] | [88197.6, +∞) |
| Corridor ∩ F | D | 115469.7..115517.0 | **∅** (54.0 short of K) | 84499.2..84814.9 | 88197.6..88410.7 |
| **E0 ∩ F** · gap | D | **∅** · 0.4 (4 ticks) | **∅** · 143.7 | **∅** · 22.9 | **∅** · 2.6 (26 ticks) |
| Reference favourable extreme beyond E0 edge | D | L0 115517.1 < 115517.4 by 0.3 | L0 91823.5 < 91967.1 by 143.6 | L0 84815 < 84837.8 by 22.8 | H0 88197.5 > 88195.0 by 2.5 |
| Intermediate child/scenario records between the preparation and terminal seq, endpoints excluded | S | none (10316 → 10317) | none (24673 → 24675) | none (27714 → 27715) | none (33062 → 33063) |
| Geometric fields, preparation vs terminal snapshot (R, K, V, T confirm, cap, corridor, economic region, K cost) | S | identical | identical | identical | identical |
| Cap history · E0/E1 recomputed from their own records | S·D | identical, no revision after p0 · equal to the stored values | identical, none · equal | identical, none · equal | identical, last revision 16:30 before p0 · equal |
| **E1** | S | 115517.4..115560.2 (= E0) | 91967.1..92223.5 (= E0) | 84837.8..85419.2 (= E0) | 88125.9..88195.0 (= E0) |
| Check 1: E0 ∩ F empty at preparation | D | **yes** | **yes** | **yes** | **yes** |
| Check 2: E0 ∩ F non-empty but close outside, same geometry | D | not applicable | not applicable | not applicable | not applicable |
| Check 3: later documented restriction E0 → E1 | S | no | no | no | no |

Notes on the table:
- **Times and cutoffs.** Times are UTC, dates in 2025. RR = `REWARD_RISK_BELOW_MINIMUM`; CLOSE_OUTSIDE = `CLOSE_OUTSIDE_RETURN_CORRIDOR`.
- **Reference open.** It comes from the pinned cache. Its high, low and close equal the stored H0, L0 and close.
- **Local domain.** Every domain bar starts at or after p0, so none straddles p0. Each verdict was re-derived with the pinned predicate, and the count equals the stored `bars_checked`. The two intrabar overshoots without confirmation are both in #4: at 16:38 (high 88200) and at 16:39 (high 88222), each above H0 + tick = 88197.6 but with closes 88190.1 and 88192.7 below it. The predicate requires the close, so neither is a recovery. In #1 the 18:16 bar is a valid RECOVERY (close 115504.7 ≤ L0 − tick = 115517.0) with high = H0 = 115520: equality on the contrary extreme is allowed.
- **Dependencies at the recovery.** trade.1m/15m/1h were READY with known_at ≤ the publication. The stored limitations were: calendar coverage unknown, modeled historical execution without measured quotes, funding completeness unproven.

## The three checks

1. **E0 ∩ F was already empty at the preparation in all four paths.**
   - The reference close lay inside E0 (it was a usable RETURN). The favourable extreme of the same bar was already beyond E0's near edge: L0 below the SHORT economic floor, H0 above the LONG economic ceiling.
   - F requires a close at least one tick beyond that extreme. No price satisfying the recovery could therefore lie in E0.
   - The most favourable F price inside the corridor gives, with the pinned predicate, 1.1960 (#1), 1.1346 (#3) and 1.1725 (#4). Each is below 1.2. This is boundary arithmetic, not an evaluated price.
   - For #2, F does not meet the corridor at all: L0 − tick lies 54.0 below K.
   - In #4 the cap revision 88564.3 → 88564.0 (16:30, cursor 650970) **precedes** the preparation and is already in E0. The region stored at WAIT open (88125.9..88195.1) was disjoint from F as well.
2. **Not applicable in all four**, because the precondition E0 ∩ F ≠ ∅ is false. Each recovery close lies in F and outside E1 with unchanged geometry. This follows from check 1 rather than being an independent cause.
3. **No restriction between the preparation and the recovery.**
   - **Intermediate records.** No intermediate record of the child/scenario between the preparation sequence and the terminal sequence, endpoints excluded.
   - **Snapshot comparison.** The geometric fields of the preparation and terminal records (R, K, V, T confirm, cap, corridor, K cost, economic region) are identical.
   - **Cap history and recomputation.** The cap history of the two records is identical, with no revision after p0. E0 and E1, recomputed from their own records with the pinned formulas, equal the stored regions. Hence E1 = E0.
   - **Scope.** E1 = E0 holds for the geometric quantities considered. It does not imply that the market or the context was generally unchanged.
   - No zone contains the price, and there is no context, coverage, freshness, timing or selection blocker.
   - Every recovery was the current bar (late first recovery 0).

The explanations are not exclusive; on these four records only check 1 applies.

## Reconciliation

| Quantity | Director | Report (S) | Paths (S) |
|---|---|---|---|
| R / N / I | 4 / 4 / 0 | 4 / 4 / 0 | 4 not issuable, 0 issued |
| Blocker incidence (not summable) | RR 4 · CLOSE_OUTSIDE 1 | RR 4 · CLOSE_OUTSIDE 1 | #1–#4 RR; #2 CLOSE_OUTSIDE |
| Primary reason | RR 3 · CLOSE_OUTSIDE 1 | RR 3 · CLOSE_OUTSIDE 1 | #2 CLOSE_OUTSIDE (same class ECONOMICS_GEOMETRY, smaller code); #1, #3, #4 RR |
| Direction · WAIT-open cohort | 1 LONG, 3 SHORT · Sep 1, Nov 1, Dec 2 | by month/direction: equal | #4 LONG; Sep #1, Nov #2, Dec #3 #4 |

## Limits

- **Intrabar order.** Never inferred and never used (U).
- **Admission cursors of intermediate bars.** Not returned by the surfaces used (U). Only the decision cursors (S) are reported.
- **Availability.** It is modeled historical availability (a bar is known at its close), not measured receipt.
- **What this explains.** It describes why these four first recoveries could not be issued under the pinned method. It does not judge whether that method is useful, and it says nothing about frequency or profit.

## Files

- [paths.json](paths.json): per-path STORED/DERIVED fields, sets, checks, reconciliation and input hashes.
- [extract_rn_paths.py](extract_rn_paths.py): run with `uv run python -I extract_rn_paths.py <export_dir> <out_dir>`. Two runs from the same exports are byte-identical.
