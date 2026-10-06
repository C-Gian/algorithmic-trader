# WP-011 final Director acceptance

Date: 2026-10-06. Reviewed product: 3fcbfc5412065984eeb00be61b638b73101be4b7.

## Decision

ACCEPTED FOR OWNER DEVELOPMENT COMPARISON. This closes WP-011 engineering review, including F1/F2 at 9b05a3e and F3 at 3fcbfc5. It does not certify economic usefulness or activate protected-period evaluation.

Exact-SHA CI [37494574273](https://github.com/C-Gian/algorithmic-trader/actions/runs/37494574273) is completed/success; checks and compose-smoke both succeeded. The Owner supplied the green notification; the Director verified the SHA and jobs once. No background monitoring or economic run was launched.

## Compatibility disposition

Production unpack_runtime preserves the byte-exact legacy shape when core.v3.deps is absent, distinguishes absent from present-empty, and retains the dependency snapshot for new checkpoints. SHA and canonical round-trip guards remain unchanged. The Director reproduced successful legacy/new production-codec round trips and ran 20 compatibility tests successfully using the supplied generator against the reviewed legacy source. This regenerated fixture is not claimed to be the downloaded binary fixture. Executor DB evidence covers legacy mid-run and final restore points; independent DB tests were not rerun by the Director.

The first sealed ingestion after restoring an old checkpoint may lack envelope dependencies. Missing metadata is not invented. Deep v7 can report state-hash mismatches on pre-snapshot v0.3 engineering runs because the regenerated state contains the new optional snapshot. This is an accepted legacy diagnostic limitation, not evidence of an economic mismatch or permission to weaken validation. Old artifacts and results remain untouched. Those old engineering runs are excluded from the Owner comparison; launch fresh runs on the accepted product.

## Owner handoff

READY FOR OWNER DEVELOPMENT COMPARISON — OCTOBER FIRST.

Update the application using the README data-preserving upgrade. In Historical Workbench, prepare a single-month October 2025 development pack (including its registered warmup and tail). Run Adviser evaluation at max with Original v0.2, then Revised v0.3 on exactly the same prepared pack and evaluator settings. Both must complete with runtime assurance passed. Use the read-only comparison and Copy comparison for chat; retain both individual reports. If either fails, copy that run's report and stop the pair.

Expected duration: a few minutes per monthly replay; unmeasured for October. Data preparation may take longer and is a separate visible job. Do not launch concurrent pairs, parameter sweeps, protected months, or automatic Deep validation. November and December remain the fixed subsequent development sequence, advanced after the Director diagnoses October without modifying the method mid-comparison.

The comparison is of integrated versions, including the v0.3 dislocation correction; it cannot isolate the RETURN effect alone. Examine coverage, A confirmation/WAIT/RETURN funnel, D/N, actual 60-second entries and hypothetical outcomes. The registered 20 distinct RETURN-owner threshold is an evidence criterion, not a trade quota. No profitability claim follows from engineering acceptance.
