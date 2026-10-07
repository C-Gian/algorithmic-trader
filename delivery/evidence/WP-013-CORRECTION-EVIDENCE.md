# WP-013 correction evidence — Astra review F1–F2 of `41790dd` (executor; not accepted)

Date: 2026-10-07. Base `41790ddd956138e62ecb7f87542199da69bd662c`. READY FOR DIRECTOR REVIEW — WP-013 CORRECTION ONLY.

Scope: findings F1 (completeness of the copyable report) and F2 (outcomes not yet recorded) only. The Owner launch stays INACTIVE.

**Unchanged:** the method, kernel, evaluator, parameters, temporal protocol, stored records, contracts/schemas, the registered protocol text and the Workbench UI. Copy report for chat already copies the same `report.md` the export serves, so it carries the new text without a UI change.

No acquisition, Owner-DB extraction or economic run was performed.

## What changed

The only product file with substantive changes is `src/algotrader/adviser/report_periods.py`. `report4.py` now passes the run's actual `status` through to it. All JSON changes are additive inside `periods`. Every earlier key keeps its value, including `sum_price_net_normalized` and `sum_price_net_pct_presentation`. Single-month and fine-warmup reports have no `periods` section and are unchanged.

### F1 — what the per-section JSON now records

For each variant, TOTAL and each month record:
- `expected_pairs`;
- `records_available`;
- `awaiting_terminal_record` and `awaiting_meaning`;
- `by_status`: CLOSED, NO_ENTRY, CENSORED, UNRESOLVED and AMBIGUOUS, with zeros kept, and `other_status`;
- `sum_population` (closed with price-net / records available / expected pairs);
- `economic_result_observed`.

### F1 — what the Markdown now shows

The Markdown is both the Copy report and the `.md` export.

- **Variant table.** One row per period × variant, with:
  - expected pairs and available records;
  - pairs without a terminal record yet (labelled "missing (run completed)" for a completed run);
  - CLOSED and CLOSED with price-net;
  - NO_ENTRY, CENSORED, UNRESOLVED and AMBIGUOUS;
  - exits after the period end;
  - the sum together with its population, e.g. `+0.250% over 1 closed`.
- **Sums without a result.** When no CLOSED outcome has a price-net, the cell reads `none observed (0 closed)`, never a bare `0.000%`. The PRIMARY column of the summary table uses the same wording.
- **Per-period lines** for TOTAL and each month:
  - MarketView: covered, assessable and unavailable minutes, plus row minutes;
  - samples: count by view, and 1h/4h directional matching/scored with the number of unavailable endpoints;
  - scenario transitions, A confirmations and D / N;
  - calls: guidance, routing and WAIT endings. These lines replace the earlier per-month line that showed sensitivity sums without their population.

### F2 — expected outcomes versus terminal records

**Expected pairs.** Expected pairs = the evaluable calls × the variants pinned in the run's evaluator identity (`engine.adviser.evaluator.profiles`).
- Evaluable calls are those issued inside the evaluation window with origin HISTORICAL_MODELED, which is the evaluator's own rule.
- Calls are attributed to their month of issue.

**Counting missing pairs.** Missing pairs are counted per variant and per month of issue (`outcome_completeness.by_variant[v].awaiting_by_issue_month`). Nothing is inferred for them: no entry, outcome, economic result or censoring.

**Reconciliation versus completeness.**
- `reconciliation` now declares `scope: ARITHMETIC_OF_AVAILABLE_RECORDS`.
- Its Markdown line reads "PASS (arithmetic of the available records only; it is not outcome completeness)".
- Two checks are added: every available record is attributed to an evaluated call, and there are no repeated terminal records. A repeated record for the same pair is counted once and reported.

**Completeness states.** `outcome_completeness.state` uses the run's actual status, not feed coverage:

| Run status | Missing pairs | State | Markdown |
|---|---|---|---|
| any | none | `COMPLETE` | expected/available count |
| not completed | some | `OUTCOMES_NOT_YET_RECORDED_AT_CHECKPOINT` | "outcome not yet recorded at checkpoint", by variant and issue month |
| completed | some | `REPORT_INCOMPLETE_EXPECTED_TERMINAL_RECORD_MISSING` | **REPORT INCOMPLETE**, with the same breakdown |

- A completed run with missing pairs is reported incomplete, and the run's saved status and assurance are not modified.
- If no evaluator is pinned, the state is `UNKNOWN_EVALUATOR_NOT_PINNED`, never COMPLETE.

## Fail-before / pass-after

**Pure tests** — `tests/test_wp013_correction.py`, 7 new tests covering the requested verifications 1–6, plus a separate "feed coverage is not finalization" case.
- Against `41790dd`: **7 of 7 failed**. Six failed because `periods()` had no run status (`TypeError`) and one because `outcome_completeness` was missing (`KeyError`).
- To show the behaviour behind those failures, the old renderer was also run on the same synthetic inputs, with ENTRY_DELAY_0 missing and with no terminal records at all. Its Markdown had:
  - only PRIMARY counts;
  - `ENTRY_DELAY_0 0.000%, ENTRY_DELAY_120 0.000%, HORIZON_ONLY 0.000%` with no population;
  - no MarketView, sample, scenario or D/N lines;
  - no mention of the missing outcomes;
  - "Reconciliation total vs months: PASS".
- After the fix: 7 passed.

**DB test** — the extended `tests/test_wp013_continuous_db.py::test_report_attests_context_pins_the_launch_and_reconciles_monthly_sections`.
- It runs a real receipt-pinned explicit-initialization pack and a v0.4 run through the worker, then reads the API JSON, Markdown and download export.
- It asserts:
  - `COMPLETE` 4/4 with the four pinned variants, identical in the JSON and the export;
  - the variant row and the monthly MarketView, sample and scenario lines in the Markdown.
- It then deletes the HORIZON_ONLY terminal record from the disposable DB and asserts:
  - the report becomes `REPORT_INCOMPLETE…`, with HORIZON_ONLY 1 in 2025-08, the month of issue;
  - the arithmetic reconciliation still passes;
  - the Markdown says **REPORT INCOMPLETE**;
  - the replay row's status (`completed`) and assurance are byte-identical before and after.
- With `src/` restored to `41790dd`, it fails (`KeyError: 'outcome_completeness'`); after the fix it passes.

## Checks run

All checks used a disposable PostgreSQL 18.6 container (`wp013c-testdb`, port 55439), never the Owner stack.

| Check | Result |
|---|---|
| `test_wp013_correction.py` + `test_wp013_continuous.py` + `test_wp013_continuous_db.py` (`ALGOTRADER_REQUIRE_DB=1`) | 22 passed |
| Related report/evaluation suites: `test_mp003_db.py`, `test_mp003_versions.py`, `test_mp002_db.py`, `test_evaluation.py` (`ALGOTRADER_REQUIRE_DB=1`) | 79 passed (20 min) |
| E2E `tests/e2e/test_wp013_e2e.py` (browser: Copy report for chat equals the Markdown export and carries the sections; the UI was not changed or rebuilt) | 1 passed |

The full suite was not rerun; the remote full suite is left to the Owner-operated CI.

## Limits

- The verifications use synthetic records and a tiny synthetic pack. No real four-month run was executed.
- Outcome completeness is computed from committed records at report time; it is not stored as a run fact.
- The registered protocol's reading rule 1 lists examples of technical blockers. It is unchanged here. An explicit mention of `REPORT INCOMPLETE` there would be a Director decision.

CI: PENDING / NOT CHECKED (Owner-operated).
