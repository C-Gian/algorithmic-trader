# WP-009 correction — Director review

Date: 2026-10-05. Reviewed commit: `d16c9251e9cb8d20ab2f4db78526d8b057423997`; base `03f2dda7ae84cbd2c54c66abdc910dbb5cc4e050`.
Disposition: **CHANGES REQUIRED — one remaining case under original finding 7 only.** Owner Backtest A remains inactive.

## Evidence and closed findings

The original [review](WP-009-DIRECTOR-REVIEW.md) remains historical evidence. Reviewed the correction diff, relevant source and regression tests against the unchanged MP-001 v0.2 rules/register. Independently retrieved exact-SHA [CI 37289189340](https://github.com/C-Gian/algorithmic-trader/actions/runs/37289189340): checks and Compose smoke SUCCESS; checks log records 594 non-E2E passed and 18 E2E passed.

Independent offline checks in an isolated archive, Python 3.12.14 (not the project's Python 3.14 CI runtime): 40 focused pure correction tests passed; one DB version test skipped because no test database was configured, not counted as verified locally. The full DB/browser suites were not rerun by the Director. Re-ran the original tiny Director probe: ordinary adverse-open stop fill, both-age freshness, residual timer, delayed C withdrawal and disconnected entry now give the required outcomes. No source acquisition, Owner stack changes or economic evaluation.

Findings 1–6, 8 and 9 are closed for this slice: corrected evaluator/timers/C admission, taped connection adequacy and current-session presentation, owned cooperative startup, committed/cutoff-safe inspection, fresh copy-operation state with a causal browser regression, and bounded durable condition-duration/staged-room diagnostics. Changed implementation identities and additive evaluation r2 preserve saved outputs and explicitly reject incompatible unfinished adviser runs.

Executor interpretations accepted: ordinary target gaps retain the conservative T/ambiguity convention; transitions between two unusable entry states are journaled without another withdrawal alert; the LIVE/lease/recent-heartbeat/connection current-session boundary is an operational presentation rule, not proof of market freshness (method dependencies still apply); staged target reconstruction from exact trigger price/gain is diagnostic and tick-rounded, not a new method parameter.

## Remaining finding 7 — resumed Deep drops newly detected storage inconsistencies

Severity: **MEDIUM, acceptance-blocking assurance defect.** Narrow scope: optional Deep v5 resume verification; not a newly discovered trading-rule defect.

In `observe/deep.py::_validate`, `_adv_load_stored` runs on each launch/resume and detects stored byte/digest/chain/sequence inconsistencies. Its problems are appended to comparisons only under `if not start`. The comment assumes the saved comparisons already contain them, which is false when storage changes while the validation is paused.

Concrete counterexample: pause a previously clean Deep after a nonzero saved cursor; alter a journal row's digest column only, leaving record bytes and chain unchanged. On resume the loader detects `adviser_journal_stored_bytes`, but the `if not start` branch drops it. `_adv_compare` compares regenerated output against the recomputed digest/chain (which are unchanged and correct), and `_adv_extra` sees no extra row. The newly detected storage inconsistency contributes zero mismatches and therefore cannot prevent a final match. A last-row chain-only alteration has the analogous boundary risk. This contradicts v5's claimed stored digest/sequence/chain verification.

[Probe JSON](evidence/WP-009-CORRECTION-DIRECTOR-RESUME-PROBE.json) and [script](evidence/WP-009-CORRECTION-DIRECTOR-RESUME-PROBE.py) execute the actual loader/comparison/extra methods and actual resume conditional with mocked storage. Loader detects one inconsistency; resumed comparisons have three comparisons and zero mismatches. This is an isolated exact-code counterexample, not a claim that a full DB validation was launched by the Director.

The existing resume regression alters record bytes **before** the first launch, so its already saved mismatch survives. It does not cover a clean pause followed by alteration while paused.

Required correction: incorporate and persist storage problems discovered on every resume, retaining earlier mismatches and avoiding uncontrolled duplicate diagnostics. Never suppress a new inconsistency merely because a factual prefix was saved. Do not overwrite original runs, their artifacts or saved completed validation results.

Required DB regressions: clean validation paused at nonzero cursor, then journal and evaluation digest-only alterations; last-row chain-only alteration; resume yields mismatch/error, never match. Keep record-only tampering, clean repeated pause/resume, cancellation, generation fencing and deterministic completed-report tests. Show fail-before/fixed-after against this reviewed commit. Preserve MP-001 and current economic implementation identities; any diagnostic version/scope decision must be explicit and leave saved v5 results intact.

## Next boundary

Only the resume assurance fix and directly necessary regressions/docs are active. No new method, optimization, acquisition, live campaign or economic agent run. After review acceptance, the Owner launches September Adviser evaluation through the web app and supplies its copied report; the Director analyzes it and assigns bounded code work to Claude. Full historical backtests remain Owner-operated.

## Follow-up acceptance — 2026-10-05

**ACCEPTED at `6f95273b54674081fe6b3896a84d62a015384fe5`.** `_adv_merge_stored` retains newly discovered storage problems on every launch/resume and deduplicates stored problems within the bounded mismatch list. Source review and the new DB regressions cover clean nonzero-cursor pause followed by digest-only alteration in both tables, last-row chain-only alteration, repeated resumes and clean continuation. Independent exact-method probe (mock diagnostic sink, no DB run): new resume problem retained, three resumes count it once, another new problem retained, full list stays bounded and remains mismatch. Full DB/browser tests were not rerun by the Director.

Independently retrieved [CI 37300338202](https://github.com/C-Gian/algorithmic-trader/actions/runs/37300338202) for that exact SHA: checks and Compose smoke SUCCESS; logs confirm 599 non-E2E and 18 E2E passed. Executor fail-before/fixed-after evidence is [recorded](evidence/WP-009-CORRECTION-FOLLOWUP-EVIDENCE.json). New adviser Deep launches use v6; saved v5 results are unchanged and unfinished v5 validations receive the stricter mismatch merge without changing their recorded version. MP-001 and core/evaluator identities unchanged.

Original findings 1–9 are closed for this implementation slice. Existing resumed comparison recounting and bounded duplicate regenerated-record diagnostics are disclosed and do not turn a mismatch into a match. No economic usefulness is inferred from acceptance. **READY FOR OWNER BACKTEST A — September only**, as specified in [the Owner handoff](WP-009-OWNER-BACKTEST-A.md). No new Claude package; no agent economic run.
