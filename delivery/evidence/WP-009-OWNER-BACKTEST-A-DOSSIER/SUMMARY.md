# Owner Backtest A — causal dossier (read-only, one-time)

Date: 2026-10-05. Scope: [Director disposition](../../WP-009-OWNER-BACKTEST-A-DIRECTOR-DISPOSITION.md) adopting Astra §6 A–C. Target: evaluation `eval-20261005T120047-e6cc50`, replay `obs-20261005T120047-bc6947`, code `6f95273+image`, `adviser.core.v2` / `btc.context-action.v0.2` / `mp001.rules.v0.2`. Executor evidence, **not Director acceptance**. No replay, Deep, backtest, parameter variant, download, method/product-code change or later-outcome inspection.

Files: [dossier.json](dossier.json) (full tables, provenance, reconciliation, timelines, self-tests), [triggers.csv](triggers.csv) (38 rows), [candidates.csv](candidates.csv) (109 rows), [extract_dossier.py](extract_dossier.py) (the one-off extraction; reads only the local export described below).

Labels: **ORIGINAL** = a committed journal field. **DERIVED** = exact Decimal algebra on ORIGINAL fields (or a join of them). **DERIVED_PINNED_BAR** = 15m OHLC aggregated from the run's pinned 1m trade bars, never later than the case's own cutoff. **MISSING** = not recorded and not reconstructed.

## Provenance and verification

- **Read access**: one `REPEATABLE READ READ ONLY` psql transaction inside the Owner's `db` container (snapshot `376473:376473:`, `transaction_read_only=on`), selecting only this evaluation/replay row, its checkpoint, professional finish, evaluation-record kinds (contents not read) and its 6,972 journal rows. Byte copy of the pinned feed cache `fc-fa8313524f72…` from the `api` container. No writes, no service start/stop, no migrations; the export stays outside Git.
- **Journal**: all 6,972 digests re-hashed from record bytes, contiguous sequence, chain head `6f868b10…cdaae` equals the professional finish commitment (journal_seq 6972). One generation.
- **Cache**: manifest SHA-256 `d4bd9a04…512a9f` equals the run pin and DB receipt; all 30 partitions verified; 49,325 trade minutes. Aggregated 15m bars reproduce all 896 journaled 15m pivot prices (0 mismatches).
- **Original report**: [WP-009-OWNER-BACKTEST-A.json](../WP-009-OWNER-BACKTEST-A.json) SHA-256 is identical before and after extraction; no original run/artifact file touched.
- **Reconciliation with the original report: all exact.** Births A85/B12/C12 per direction, arms 47, ends and end reasons, 38 trigger evaluations, rejection blockers 18/14/6, limiting histogram (15m pivots 18, 1h pivots 4, IMPULSE_B 9, NONE 7), G/Q/K/margin quantiles for A/B/C and all 26 A staged reaction-room values.
- **Per-row checks (DERIVED)**: T and V reconstructed from side price and G/Q regenerate G, Q, margin and rejection reason exactly (32/32). V equals the candidate invalidation with runtime tick rounding (32/32). The target and limiting zone selected again from the zone set rebuilt at the cutoff equal the recorded ones (38/38, including all six inside-zone refusals). The structural area regenerated from the DERIVED S15 equals the recorded area (32/32).
- **Algebra self-tests** (Astra §8): LONG T=100700, V=99700, K=14, r=1.2 gives bound 100014.525 → threshold 100050 is incompatible; threshold 100000 / close 100100 is overshoot; SHORT mirrors give the same classes.

## Main finding — all 32 geometric rejections fail already at the minimum confirmation price

For each trigger, exact algebra with the trigger-time T/V and K=14, r=1.2 compares the minimum confirming close (K-trigger ± 1 tick) with the extreme admissible price (inward tick-rounded, verified with the predicate):

| Class (DERIVED) | A | B | C | Total |
|---|---:|---:|---:|---:|
| INCOMPATIBLE_NO_ADMISSIBLE_PRICE — no price between V and T passes (T−V span 10.8–29.1 bps < ≈(1+r)K) | 10 | 1 | 3 | 14 |
| INCOMPATIBLE_AT_MINIMUM_CONFIRMATION — admissible prices exist only beyond the confirmation threshold (gap 2.7–37.8 bps, A median 15.5) | 16 | 0 | 2 | 18 |
| OVERSHOOT (threshold compatible, actual close beyond bound) | 0 | 0 | 0 | 0 |
| Actual price admissible / object or rule divergence | 0 | 0 | 0 | 0 |
| INSIDE_OPPOSING_ZONE_REFUSAL (no geometry) | 6 | 0 | 0 | 6 |

- Actual closes were only slightly beyond the minimum confirmation price (A median 1.3 bps, max 18.6). The recorded rejections are therefore **not explained by overshoot or confirmation delay at the trigger minute**. With those targets and stops, the confirmation threshold itself was outside the admissible region.
- At the **latest arm/revise cutoff**, the targets then known (for the minimum confirming close) and the stops then in force give the same class for all 32 rows. Between arm and trigger, the zone set changed in 5 rows: a new 15m pivot was published after arm in 4 rows, and in 1 row the attempt's own impulse-B zone broke. The target known at arm differs from the trigger target in 4 rows. In 2 of them a new pivot made the target nearer. In 1 the broken impulse-B zone made it farther. In 1 the actual close passed a zone that the minimum confirming close would still have faced. None of these differences altered the class. Arm→trigger was short (A median 6.5 min, max 40).
- In one row (`AL-2025-09-30T19:45…`) the minimum confirming close lies before a zone that the actual close passed. With the same zone set its target would be nearer (114488.3 vs 114766.4), so the class is unchanged.
- 27/32 have G < 30.8 bps (the zero-risk floor), consistent with Astra F3. The 14 "no admissible price" rows show this from T−V alone.
- These are geometric statements about **these produced objects** under the declared costs. A non-empty region would not have been a fill. Nothing here shows that different costs, stops or targets would be justified or profitable.

## Per family

**A — continuation (85 births, 38 arms, 32 triggers).**
- Births all `FALSE_TO_TRUE`. Median birth→arm 15 min for the 32 triggered attempts.
- 26 geometric rows: 16 incompatible at confirmation, 10 with no admissible price.
- Targets of the 26: 9 are the attempt's **own impulse-B near edge** (B−z by construction, Astra F4), 15 another landmark before B, 2 beyond B. Limiting types: 15m pivots 13, 1h pivots 4, own IMPULSE_B 9.
- The 6 AT_OPPOSING_AREA refusals:
  - three are uniquely inside the attempt's own impulse-B zone;
  - two lie inside both their own impulse-B zone and a 15m pivot zone;
  - one lies inside four overlapping pivot zones (two 15m, two 1h).
  - For those three, the zone the runtime actually returned is **unrecoverable**: F1 attribution loss is confirmed, and all containing zones are listed.
  - In 5 of 6 the evaluated price was inside the attempt's own impulse-B zone. In 4 of 6 the trigger level (reaction-bar high) was already inside it at arm.
- Upstream attrition, the **45 spent-before-reaction** cases:
  - The spend condition (high beyond B+z) is verified on the pinned terminal bar in 45/45.
  - 40 spent on the first processed 15m bar after birth, 5 on the second.
  - In **11/45** the same terminal bar also satisfied the reaction conditions. OHLC cannot order them intrabar; the runtime's declared precedence spends first.
  - The recorded latch at spend is `NEED_FALSE` in all 45, so a new same-direction episode needs Q_A false→true.
  - The next same-direction A birth followed after 15–3,405 min (median ≈ 315 min; one none before the window ended).
  - 45 distinct impulse-B prices; these are **not** counted as 45 independent opportunities.
- Other A ends: context/adverse-expansion withdrawal 6; close at/beyond A+z 2.

**B — breakout/retest (12 births, 3 arms, 1 trigger).**
- Ends: returned inside before retest 5, deadline 3, box retired 2, context forbidden at birth 1, reject 1.
- The single trigger (`BL-2025-09-13T09:45…`) was capped by a 15m pivot high (target 116212.1, below the box-width projection).
- T−V span 18.8 bps → **no admissible price at any confirmation**. Q=1.2 bps shows that a tight stop does not help when the target room is below the cost floor.
- n=1: no family-level conclusion.

**C — failed exit (12 births, 6 arms, 5 triggers).**
- Ends: not BALANCED at birth 5, directional expansion at birth 1, deadline 1, reject 5.
- Targets: 15m pivots 4, box midpoint 1 (that midpoint row is the seventh "NONE" in the original histogram).
- 3 no admissible price, 2 incompatible at confirmation (gaps 13.2 and 17.5 bps).
- Arm→trigger was 1 min in 4 of 5 rows: the reclaim close arms and the next minute confirms.

**Box owners.**
- 19 boxes were active in the evaluation window; all expired at their 240-min lifetime and none was retired by a break.
- Attempts per box: 3 boxes had none, 8 had one, 8 had two. 24 B/C births in total (B+ 9, B− 3, C+ 4, C− 8): 24 births ≠ 24 independent structures.

**MarketView coverage (DERIVED from published view rows, 43,200 min).**
- NO_SUPPORTED_PLAN 33,001 min:
  - with BALANCED context: 14,614 min;
  - with UP context: 9,689 min;
  - with DOWN context: 8,698 min.
  - Any WATCH candidate (any family) was present in only 1,725 of those minutes.
- BALANCED_RANGE 9,086 min; ARMED_SCENARIO 1,113 min.
- Largest cells: BALANCED/TRANSITION 9,574 min, BALANCED/ROTATION 6,027 (balanced range), BALANCED/EXPANSION 5,040, UP/REACTION 3,247. Full table in `dossier.json`.

## Timelines (outcome-free, fixed criteria; journal records only, ending at the attempt's terminal record)

| Criterion | Attempt |
|---|---|
| A, least negative margin (−7.69 bps; target = own impulse-B near edge 112866.3; bound 112343.5 vs confirmation 112374.0) | `AL-2025-09-08T15:15:00+00:00-1718137de4ca` |
| A, largest reported reaction→trigger erosion | `AS-2025-09-25T20:45:00+00:00-872710567fa6` |
| First AT_OPPOSING_AREA (ambiguous: 15m pivot + own impulse-B) | `AL-2025-09-01T18:45:00+00:00-bcbe300ff3b6` |
| Only B | `BL-2025-09-13T09:45:00+00:00-3df01fe3650a` |
| C, largest G (32.70 bps) | `CS-2025-09-03T00:30:00+00:00-bb9cc4a9db6b` |

## Missing or reconstructed evidence

- **MISSING**: the runtime's chosen blocking zone for 3 of the 6 inside-zone refusals (several zones contain the price). Q_A per 15m close and latch transitions between candidate records. Box used/broken flags and B retest counts (births per box shown instead).
- **DERIVED, not journaled**: S15 at each trigger (from pinned bars; validated by the area regeneration); T and V at trigger (validated as above); impulse-B and box break flags (from pinned 15m closes); hypothetical targets at the minimum confirmation and at arm (zone-set algebra, not a runtime replay); WATCH presence per minute.
- Trigger-minute close = side price is not separately journaled. It is consistent with all 32 regenerated structural areas.

## Classification outcome (stop criterion)

All 38 rejections are reconciled and classified:
- 32 are incompatible already at the minimum confirmation price (14 of them have no admissible price at all);
- 6 are inside-zone refusals with recovered zone evidence (3 unique, 3 ambiguous);
- 0 are overshoot;
- 0 are object/rule divergence;
- 0 have insufficient data for classification.

No method revision is proposed or implemented here; the choice belongs to the Director.

READY FOR DIRECTOR REVIEW — OWNER BACKTEST A DOSSIER ONLY
