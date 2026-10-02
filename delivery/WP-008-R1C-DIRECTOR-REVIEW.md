# WP-008-R1C Director review

Date: 2026-10-03 (Europe/Rome)
Reviewed implementation: `6745117ee1010510abfa6247bfc40c1331fff7c1`.
Base: `d2ee918e03cf9388d9c017060b528413ca10b378`.
Decision: **CHANGES REQUIRED — R1C ONLY**. Owner September retry remains blocked.

## Evidence and retained work

Independently confirmed CI `37075370604`: checks SUCCESS and compose-smoke SUCCESS. Executor reports 376 non-E2E/zero skips + 10 E2E; Director did not rerun full local suites or the Windows benchmarks. Source inspection covered reconciliation v2, Deep launch/execute/finish/summary, regression fixtures, benchmark script/evidence and publication/control changes. Schema-related files have no diff from base. No Owner database/dataset/live stack was accessed.

Retain separate input/state/output commitments, range-boundary digests, consumed-input re-hashing, disclosed shared-reducer/cache-only Deep scope, durable linked jobs/reports, byte-level hooks and artifact integrity checks. The full synthetic month cold/warm/resume/Deep evidence is useful and does not become real September evidence. Separating tracemalloc memory measurement from speed timing is appropriate; the initial traced result is preserved.

## Required corrections

### 1. Missing receipt is accepted by reconciliation v2

`observe/reconcile.py` checks `cache.manifest_sha256 == pin and (rec is None or rec == pin)`. A missing trusted receipt is therefore a successful cache_receipt_and_pin check. The real finalizer obtains the receipt with a DB SELECT and passes None if absent. This contradicts v2's declared cache == run pin == receipt requirement and weakens the trusted-root boundary after preparation.

Require a matching receipt for current streaming v2 execution, with explicit failed/incomplete diagnostics when absent or incompatible; do not silently disable the check. Old stored reports/readers keep their historical claims. Test both direct validation and an actual run whose receipt is removed between preparation and final reconciliation; neither may produce assurance PASS. Keep mismatched receipt/cache/run-pin tests.

### 2. Deep terminal controls and headline can report false conclusions

`DeepJob._validate` enters GENERATING_REPORT, saves and calls `_finish(completed, result=match)` without a final cancellation check. `_finish` writes status/result under its generation fence but never checks cancel_requested or orders terminal success against Cancel's row lock. A cancel accepted during report generation or immediately before terminal UPDATE can be overwritten by COMPLETED/MATCH. Apply the same locked-before/after terminal boundary used by normal replay: an accepted cancellation that wins the lock must produce CANCELLED/INCOMPLETE, and a later command must reject the already terminal job. Cover preparation and terminal phases, not only the existing validating-loop test. Preserve generation fences, saved diagnostic state and the originating run.

`deep_api.assurance_summary` also unconditionally headlines 'Runtime integrity verified' when Deep outcome is match, even when the original run assurance is failed/incomplete/not_checked. A shared-reducer state match cannot promote failed runtime checks. Display runtime result and reference-match result separately, retaining original failure/warnings and exact diagnostic coverage. Test failed/incomplete originating assurance plus Deep MATCH and a cancelled diagnostic after a preceding MATCH.

Independent stdlib probes executed the actual extracted `_finish` and assurance_summary methods with lightweight DB doubles: pending cancel still recorded completed/match; failed originating assurance plus Deep match produced the misleading verified-runtime headline. The receipt condition was also confirmed directly. These probes are focused reproductions, not full DB integration tests.

### 3. Annual component measurements do not close annual application gates

The month measurements include actual launch/process/DB/terminal path. The annual measurements omit DB/spawn, actual terminal report generation and source snapshot/verification respectively. They are valid component evidence; the cold estimate of roughly 2 x build time is not a measurement. Do not label these as three complete annual release gates PASS or say all six application gates pass.

Reconcile benchmark evaluator, JSON/Markdown, README/STATE and handoff: separate measured month application gates, annual component comparisons and annual application gates NOT_MEASURED/PENDING. Preserve both original measured runs. Either close annual gates with a bounded synthetic end-to-end engineering fixture under declared caps, or propose an explicitly month-only September handoff for Director review with annual readiness still pending. Do not run real historical month/year CLI evaluation or expand the task into adviser/acquisition work. The Director can authorize a scoped September check after the correctness fixes; unmeasured annual readiness is not silently accepted.

## Correction acceptance evidence

Add meaningful regressions for absent receipts through the normal terminal path; Deep cancel at preparation/report entry and immediately before/after the terminal lock; stale generation; assurance headline separation for failed/incomplete originals; deterministic diagnostic results/original immutability. Keep existing corruption, protected expected/differential, pause/resume/restart, controls, reports and E2E tests. Run required isolated checks/CI; report actual results.

Correct the gate inventory without turning estimates or component measurements into application PASS. No rerun of already valid month measurements is required unless implementation changes affect them. Revised Owner procedure must read actual manifest/coverage and compare committed cursor with that run's verified total; the historical reported 129,600 count is a comparison fact, not a hard-coded acceptance substitute. State terminal phase, assurance warnings/limits and where to Copy report; Deep validation remains optional. No Owner retry before Director acceptance.
