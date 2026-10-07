# WP-013 engineering evidence — continuous v0.4 reference support (executor; not accepted)

Date: 2026-10-07. Base `2d6fe9e`. This is executor evidence for the Director's technical review: READY FOR DIRECTOR REVIEW — WP-013 ONLY.

The registered protocol and the Owner instructions are in [WP-013-CONTINUOUS-REFERENCE-PROTOCOL.md](../WP-013-CONTINUOUS-REFERENCE-PROTOCOL.md); the Owner launch is INACTIVE.

**Boundaries kept.**
- No economic run, real acquisition or Owner-DB extraction.
- No change to the method rules or values, the kernel, the evaluator or any stored result.

## Preceding records in this delivery

**Q4 dossier closure at `2d6fe9e`.** Recorded in STATE as: "Accettato come evidenza descrittiva; associazione RETURN–terminali osservata; causalità non identificata; nessuna modifica metodologica autorizzata".

**Non-blocking typo in `dossier.json → erratum_vs_091df18`.**
- The authoritative total is now quoted as −0.0130817434351891232589748454948995…, both in the dossier and in the script string.
- The earlier figure was the Director's transcription. Its comparison field is renamed `director_quoted_total_typo_superseded`.
- Regenerated from the existing local exports only, with no Owner-DB read. `calls.csv` and `confirmations.csv` are byte-identical; only `dossier.json` changed.

## What changed (product)

| Area | Change | Compatibility |
|---|---|---|
| `corpus/presets.py` | Optional `Preset.initialization = REGISTERED_EXPLICIT_INITIALIZATION`. An explicit initialization must end at the evaluation start and last at least the fine warmup. `initialization_doc`. `windows_doc` adds `initialization` only for such presets. | The field is omitted when absent, so the WP-008-R3 and month-builder presets keep byte-identical documents, `preset_sha256` and windows. The file-level `fine_warmup_hours` stays 96. |
| `corpus/presets.json` = `delivery/WP-013-PRESETS.json` | One added preset, `btc-2025-09-to-2025-12-continuous-init35d-v1`: 2025-07-28 → 09-01 initialization, 09-01 → 2026-01-01 evaluation, 365-minute tail. Identity `fabd1c55…2dbc`. | `delivery/WP-008-R3-PRESETS.json` is unchanged. |
| `corpus/pack_contracts.py`, schema | `algotrader.corpus-pack.v1` revision 2, with a changelog entry. | `pack.manifest_revision`: fine-warmup manifests keep `schema_revision` 1, so a rebuild keeps its pack id. Only explicit-initialization packs declare revision 2. |
| `adviser/engine.py` | `initialization_pin(pack)`: a launch-time `initialization` key (window, preset identity, initialization coverage rows, continuity statement), added only for explicit-initialization packs. | Earlier engine documents are unchanged. No validator re-derives the engine document. |
| `adviser/report_periods.py` (new) + `report4.py` | `initial_context`, `launch_pins` and `periods` (whole-run total plus calendar-month sections, exact reconciliation), and their Markdown. | Added only for an explicit initialization and/or a multi-month evaluation window, so single-month v0.4 reports are unchanged. |
| `evaluation/report.py`, `corpus/pack_api.py` | The Markdown says "Initialization … context only, not evaluated" for such packs. | Fine-warmup wording is unchanged. |
| Web (`api.ts`, `PackPrep.tsx`, `Backtest.tsx`) | The pack panel shows the initialization separately, with an explanatory note. The run setup and report hints adapt. The fixed "4 days" lede is generalized. | The fine-warmup display is unchanged ("Warmup (not scored)"). |

**The kernel is unchanged.** The existing v0.4 state machine already has a single WARMUP→EVALUATION transition (`core3._windows`) and no calendar-month logic, so a 122-day evaluation window is one continuous run.

## Report semantics added

**Context attestation at the evaluation start.**
- Initialization coverage rows.
- Readiness of the 1m/15m/1h scales at the start, and their first READY times.
- Required periods: previous day, previous week (Monday-based), previous month, and the 15m and 1h pivot memory windows (from the register: 24 h and 168 h). Each is labelled `COVERED`, `INSUFFICIENT_BEFORE_INITIALIZATION` or `INITIALIZATION_TRADE_COVERAGE_INCOMPLETE_UNLOCATED`.
- Previous day/week/month levels, labelled `BUILT_ACTIVE`, `BUILT_THEN_{BROKEN|RETIRED}` (with the stored reason; `_FOR_ANOTHER_PERIOD` if the latest instance is not the required period), `NOT_BUILT_DATA_INSUFFICIENT`, or `NOT_BUILT_WITH_COVERED_PERIOD_UNEXPLAINED_NOT_CERTIFIED`.
- Pivots: counts by state at the start, earliest extremum, memory window. Completeness is always `NOT_CERTIFIED`.
- Records published at the start dispatch count.

**Monthly sections, one per calendar month of the evaluation window.**
- Coverage: minutes, assessable and unavailable minutes, MarketView rows.
- View samples by sample time.
- Scenario transitions and A confirmations, routing and D/N by publication time.
- WAITs by opening time, with their ending wherever it falls.
- Calls by issue month, followed to the guidance outcome even after that month ends.
- Per-variant hypothetical paths: status, exits after the period end, censored/unresolved counts, exact price-net sums.

**Reconciliation checks.**
- Calls are partitioned without duplicates.
- Calls, A confirmations and WAITs equal the report totals.
- Minutes, assessable minutes and samples sum to the total.
- Per-variant exact price-net sums and path counts sum to the total.

The sum's meaning (normalized, not an account return; funding not covered) and the censoring are stated in the section.

## Synthetic verifications (run locally)

All checks used a disposable PostgreSQL 18.6 container (`wp013-testdb`), not the Owner stack.

| Check | Result |
|---|---|
| `tests/test_wp013_continuous.py`: earlier preset identities, exact new windows, initialization validation, engine pin, single transition and continuity across a month boundary (pure kernel, call issued 31 Aug 23:32 → TARGET 1 Sep 00:08; one birth; PRIMARY enters in August and exits in September), attestation with complete data, built/broken/retired levels, insufficient/never-built/unlocated gaps, monthly attribution with a call resolved next month, exact reconciliation, mismatch detection, launch pins | 11 passed |
| `tests/test_wp013_continuous_db.py`: real receipt-pinned explicit-initialization pack → v0.4 run equals the pure fold (journal and paths); one evaluation-start transition; crash and restore inside the open call across the month boundary give identical digests and commitments; API report, Copy-report Markdown and JSON export carry the attestation, pins and reconciled monthly sections; a fine-warmup run keeps its engine document and report shape | 4 passed |
| `tests/e2e/test_wp013_e2e.py` (browser): the Workbench shows the initialization separately and says it is not evaluated → Prepare → Ready → run-setup note → one v0.4 run completes → Copy report for chat equals the Markdown export and contains every new section → 390 px without overflow | 1 passed |
| Related existing journeys: `test_pack_workbench.py` (fine-warmup wording) and `test_mp003_e2e.py` | 2 passed |
| `tests/test_pack.py`, `test_pack_correction.py`, `test_schema.py`, `test_corpus.py`; `algotrader schema` (every baseline matches) | 55 passed |
| Full non-E2E suite (method reference cases, v0.2/v0.3 byte pins, v0.4 paths, DB, reports), `ALGOTRADER_REQUIRE_DB=1` | 860 passed (46 min) |
| Web typecheck and build | passed |

## Limits

- The month-boundary continuity is shown on tiny synthetic tapes; no real four-month run was executed. That run is the Owner's, from the app, after review and CI.
- The attestation reports facts and states. It never certifies pivot memory completeness, and it cannot tell why a level was not built when its period was covered; it flags this as unexplained.
- Pack preparation for the new preset will download the missing initialization days (at least 28–31 July and August 2025, unless already local), through the existing verified path. Its size and time are shown before Prepare. No acquisition was performed here.
- Evidence class: new development evidence. It does not isolate the warmup effect from the cross-month continuity.

CI: PENDING / NOT CHECKED (Owner-operated).
