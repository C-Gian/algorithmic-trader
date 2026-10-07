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

---

# F2-R1 — one expected population for path records (base `6f49ae7`; READY FOR DIRECTOR REVIEW — WP-013 F2-R1 ONLY)

Astra found that the F2 summary counted path records by pair without comparing them with the expected population: a path for a nonexistent call was silently ignored while reconciliation passed, a non-pinned variant was counted, and a LIVE call's paths entered the sums. F1 is not reopened. The method, kernel, evaluator, parameters, stored data and assurance are unchanged.

## What changed (`report_periods.py`)

- **One expected population:** evaluable calls in the window (HISTORICAL_MODELED) × the variants pinned in the run's evaluator.
- **Admission before deduplication.** `_admit_paths` compares EVERY available path record with that population before any filtering. Each record is exactly one of:
  - an admitted pair (first record kept);
  - extraneous, with the first failing reason: `UNKNOWN_CALL`, `CALL_NOT_EVALUABLE`, `VARIANT_NOT_CONFIGURED`, `CALL_OUTSIDE_EVALUATION_WINDOW`;
  - a duplicate of an admitted pair.
- **Only admitted pairs** enter available counts, states and sums. Attribution stays the month of issue; duplicates are counted once.
- **New JSON block `periods.path_records`:** available, admitted, expected_missing, extraneous by reason, duplicates, up to 10 examples each, and the variant-check mode.
- **Reconciliation checks:**
  - `path_records_accounted`: available = admitted + extraneous + duplicates;
  - `admitted_path_records_attributed`;
  - `no_extraneous_path_records`;
  - `no_duplicate_terminal_records`.
  - An extraneous or repeated record fails reconciliation.
- **Completeness is unchanged in meaning.** All expected pairs present stays COMPLETE, but the Markdown appends "reconciliation FAILED (see the path-record anomalies above)". A missing outcome is never counted as extraneous.
- **Markdown (Copy report for chat):** one compact line, `- Path records: N available · A admitted · M expected missing · E extraneous (reasons) · D duplicates`, plus an examples line when there are anomalies.
- **No pinned evaluator:** stays `UNKNOWN_EVALUATOR_NOT_PINNED`; the variant check is reported as not possible and expected-missing as unknown; the call checks still apply.

## Protocol

Rule 1 of [the protocol](../WP-013-CONTINUOUS-REFERENCE-PROTOCOL.md) records the Director decision verbatim: REPORT INCOMPLETE blocks the economic reading even with run COMPLETED and assurance PASSED, does not retroactively change saved status/assurance, and a failed reconciliation remains a distinct block.

## Fail-before / pass-after

**Pure regressions** (`tests/test_wp013_correction.py`, 4 new tests):
1. All expected outcomes plus a path for the nonexistent call "alien".
2. Only PRIMARY pinned, with PRIMARY and HORIZON_ONLY records.
3. A LIVE call in the window with four paths, plus a call outside the window with a path.
4. Unpinned evaluator stays UNKNOWN, and a missing outcome is not extraneous.

Results:
- On `6f49ae7`: **4/4 fail** on behaviour, not just new keys:
  - the alien case gave reconciliation `all_passed = True`;
  - HORIZON_ONLY was counted `(1, 1, '0.002')` instead of `(0, 0, '0')`;
  - the LIVE paths changed the admitted sums (`'0.301'` instead of `'0.001'`);
  - the fourth test failed with `KeyError: 'path_records'`.
- After the fix: pass. The tests assert that admitted counts, states and sums are identical with and without the extraneous records, and that the anomalies are visible in the copyable Markdown.
- The earlier duplicate, missing-record, actual-run-status and cross-month attribution tests are kept and pass.

**DB test** (`test_wp013_continuous_db.py`):
- A path record for an unknown call is inserted into the completed run's records in the disposable DB.
- The API JSON shows `UNKNOWN_CALL 1` and failed reconciliation, with the admitted totals unchanged.
- The Markdown shows `1 extraneous (unknown call 1)` and `Reconciliation total vs months: FAIL`.
- The run's status and assurance are unchanged.
- It fails on `6f49ae7` and passes after.

## Checks run (disposable PostgreSQL 18.6 container, port 55439; never the Owner stack)

| Check | Result |
|---|---|
| `test_wp013_correction.py` + `test_wp013_continuous.py` + `test_wp013_continuous_db.py` (`ALGOTRADER_REQUIRE_DB=1`) | 26 passed |
| E2E `tests/e2e/test_wp013_e2e.py` (Copy report for chat = Markdown export) | 1 passed |

- The related single-month report suites were not rerun. `periods()` returns None for single-month windows, so their reports do not reach this code.
- No benchmark or economic run.
- The disposable container was stopped; no verification process remains running.

CI: PENDING / NOT CHECKED (Owner-operated).

