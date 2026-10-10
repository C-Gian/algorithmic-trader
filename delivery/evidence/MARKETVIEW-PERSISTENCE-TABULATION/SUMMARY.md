# MarketView +1h vs last-hour persistence — descriptive tabulation (run v0.5)

Base `11a74b6`. Evaluation `eval-20261009T155751-be8b2b`, replay `obs-20261009T155751-0f255b`, `btc.context-action.v0.5`, evaluator `adviser.evaluator.v3`. No equivalence with v0.6 is assumed. Feasibility: [MARKETVIEW-PERSISTENCE-FEASIBILITY.md](../MARKETVIEW-PERSISTENCE-FEASIBILITY.md). **Director: descriptive closure of the tabulation at `ced7b2f`.** A later documentary correction (chain wording only) leaves counts and conclusions unchanged.

## Access actually used

- **Extraction.** One `REPEATABLE READ READ ONLY` transaction ([export.sql](export.sql)), limited to `adviser_evaluation_records` with `run_id = obs-20261009T155751-0f255b AND kind = 'view_sample'`. It ran through `docker exec … psql` on the Owner DB.
  - Snapshot `965478:965478:`, `transaction_read_only = on`, 2026-10-10T06:41:20Z.
  - The Owner started the DB container; I did not start, stop or write anything.
- **Raw export.** Kept outside Git (`view_samples.jsonl`, sha256 `d6585a3b…31e6`).
- **Scenario links and cross-checks.** From the existing local GET exports of the R→N diagnosis (`sc_0/1.json`, `report.json`; hashes in `tabulation.json`).
- **Not done.** No GET call, price cache, replay, Deep validation, backtest, product suite or CI query.

## Integrity — executor checks (what was actually checked)

These are the executor's own checks. They are not an independent review; the Director's review and closure are separate.

| Check | Result |
|---|---|
| Rows (server count / extracted) / expected | 2928 / 2928 / 2928 (122 days × 24 h) |
| seq, record_id, sample_time unique | yes; `record_id = sample-<sample_time>` for every row |
| Sample times = hourly grid 2025-09-01T00Z … 2025-12-31T23Z; seq order = time order | yes |
| Per-record digest recomputed (sha256 of canonical record) | 2928/2928 equal |
| Chain checks inside the extracted subset | 2927 successful checks, made of 2926 links between extracted records and one check from the initial seed (seq 1); 0 failed. One link is not verifiable: seq 1349, which follows the 4 non-extracted records, seq 1345–1348. |
| Stored-value consistency (no prices): outcome_1h(h) = sign(anchor(h+1h) − anchor(h)); persistence(h+1h) = outcome_1h(h) | 2927/2927 each (the last hour has no successor) |
| Report cross-check (by_view, samples, 158 scored, 77 matching, 0 endpoint missing; antecedent 132) | all equal |

**Not verified here:** the full evaluation chain and its final commitment. The non-`view_sample` records and the finish commitment were outside the authorized access.

**Reused commitment, by provenance only.** The app's terminal validation of this run reports assurance 21/21 PASSED (local `evaluation.json`/`report.json`). Per code, its adviser checks include `adviser_evaluation_chain`. The local exports do not enumerate the check names, and the validation was not re-executed here.

## 1. Reconciliation of every sample

| Population | Samples |
|---|---|
| All hourly samples | 2928 |
| UP / DOWN | 93 / 65 (= 158) |
| BALANCED / UNCERTAIN (abstentions) | 655 / 2115 |
| UNAVAILABLE | 0 |
| Anchor missing / +1h endpoint missing | 0 / 0 |
| +1h outcome FLAT / persistence FLAT / persistence unassessable | 0 / 0 / 0 (over all 2928) |

Monthly counts are in `tabulation.json` → `reconciliation.by_month_view`; they sum to the totals.

## 2. Paired comparison (same sample)

Population: view UP/DOWN, +1h endpoint UP/DOWN, persistence UP/DOWN. **n = 158.** This equals the whole evaluable directional population, because none were excluded: FLAT 0, missing 0.

| Cell (sign at +1h) | Samples | Distinct scenarios |
|---|---|---|
| Both match | 41 | 35 |
| MarketView only | 36 | 35 |
| Persistence only | 45 | 39 |
| Neither | 36 | 36 |
| **Total** | **158** | 99 (a scenario can fall in several cells) |

- MarketView matching 77/158; persistence matching 86/158. Same denominator, same samples.
- View and persistence have the same sign on 77 samples (41 both, 36 neither) and the opposite sign on 81 (36 MarketView only, 45 persistence only). The two differ only on these 81.

| Paired cells by group | Both | MV only | Persistence only | Neither | n |
|---|---|---|---|---|---|
| UP | 22 | 23 | 25 | 23 | 93 |
| DOWN | 19 | 13 | 20 | 13 | 65 |
| 2025-09 | 5 | 9 | 16 | 7 | 37 |
| 2025-10 | 12 | 12 | 6 | 9 | 39 |
| 2025-11 | 9 | 5 | 7 | 9 | 30 |
| 2025-12 | 15 | 10 | 16 | 11 | 52 |

## 3. MarketView on the whole evaluable directional population

- **Coverage:** 158/2928 hourly samples are directional.
- **Matching sign at +1h:** 77/158; opposite 81; FLAT 0.
- **By direction:** UP 45/93, DOWN 32/65.
- **By month:** Sep 14/37, Oct 24/39, Nov 14/30, Dec 25/52.

The paired subset (§2) is identical here, so the two figures coincide. This is a fact of this run, not a definition.

## 4. Support: scenarios and owners (hours are not independent)

- **Scenarios.** The 158 directional samples come from **99 distinct scenarios**, and every sample is conditional.
- **Owners.** Owner = `owner_id` from the scenario journal. For family A (139 samples) `owner_id` equals the scenario itself. The 19 B/C samples have box owners, and no box owns two of the sampled scenarios. So there are 99 distinct owners, and the owner grouping adds no concentration beyond the scenario grouping.
- **Repetitions:** 61 scenarios × 1 sample, 26 × 2, 5 × 3, 6 × 4 and 1 × 6. The median is 1. The largest scenario is `BS-2025-10-09T01:00…` with 6 samples (3.8 %).

| Month · direction | Samples | Distinct scenarios | Max samples one scenario |
|---|---|---|---|
| 2025-09 UP / DOWN | 27 / 10 | 16 / 9 | 3 / 2 |
| 2025-10 UP / DOWN | 18 / 21 | 11 / 11 | 4 / 6 |
| 2025-11 UP / DOWN | 15 / 15 | 9 / 12 | 4 / 2 |
| 2025-12 UP / DOWN | 33 / 19 | 17 / 14 | 4 / 2 |

Distinct scenarios are not independent observations either: they can overlap in time and share market moves.

## 5. Antecedent at +1h (from the journal's first CONFIRM `published_at`; counts only)

| Class (158 directional samples) | All | UP | DOWN |
|---|---|---|---|
| Already active at cutoff (CONFIRM ≤ h) | 94 | 61 | 33 |
| Activated within +1h (h < CONFIRM ≤ h+1h) | 38 | 22 | 16 |
| Not yet activated at +1h | 26 | 10 | 16 |
| Not assessable | 0 | 0 | 0 |

- The stored flag `antecedent_activated_1h` agrees with the journal class on every sample (0 mismatches): 94 + 38 = 132, as in the report.
- **Annotations; they select nothing.** 2 of the 26 are activated after +1h. Terminal states of the supporting scenario, counted per sample: DESTINATION_REACHED 62, INVALIDATED 46, TIME_EXPIRED 24, WITHDRAWN 14, STALLED 8, EXPIRED 4.
- No accuracy is computed by class.

## Limits

- **Scope of a reading.** Descriptive only, about the moments the v0.5 MarketView selected and the sign at +1h. It says nothing about economic usefulness, destination quality or independent validation. Sep–Dec 2025 is development data that has already been exposed.
- **Not done:**
  - no significance test, no success threshold, no subgroup search;
  - no accuracy restricted to later-activated cases;
  - no hour treated as an independent observation.
- **Same price move on both sides.** Persistence and the +1h outcome come from the same stored anchors, shifted by one hour.
- **v0.6.** No v0.6 statement; it would need its own run.

## Artifacts

| File | Content |
|---|---|
| [export.sql](export.sql) | the single read-only extraction |
| [tabulate_view_persistence.py](tabulate_view_persistence.py) | offline script: `uv run python tabulate_view_persistence.py <vs_export> <journal_export> <out_dir>`; two regenerations are byte-identical |
| [tabulation.json](tabulation.json) | every count above, with denominators, integrity results and input hashes. Its `chain_links_verified_within_subset` = 2927 counts the seed check plus the 2926 links (see `chain_scope`). |
| [samples.csv](samples.csv) | one row per sample (2928). Prefixes: `s_` = STORED in the `view_sample` record; `d_` = DERIVED (month, population, match flags, paired cell, owner, repetition ordinal, antecedent class, first CONFIRM); `a_` = annotation (activation after +1h, scenario terminal) |
