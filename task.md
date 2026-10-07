# Current task — continuous v0.4 diagnosis (read-only)
Date: 2026-10-07 Europe/Rome.
Status: EXECUTOR WORK DELIVERED — READY FOR DIRECTOR REVIEW — CONTINUOUS V0.4 DIAGNOSIS ONLY. No further package activated.

## Preceding record

The Director accepted the continuous v0.4 September–December 2025 run (evaluation `eval-20261007T182934-3f41ad`, replay `obs-20261007T182934-f8c3d4`, build `97a2a8c`, pack `pack-1ae7d36c20adbde0a468a7e0f6d8750a9951aa8e`), registered under [the WP-013 protocol](delivery/WP-013-CONTINUOUS-REFERENCE-PROTOCOL.md):

> “Prova continua accettata come evidenza descrittiva di sviluppo; risultato negativo; causa non identificata; nessuna modifica metodologica autorizzata.”

## Assignment

A bounded, read-only diagnosis of the sequence confirmation → WAIT → issue → entry → outcome for all 13 calls and all 57 WAITs. It distinguishes:
- **H1:** structural deterioration already observable before the issue;
- **H2:** the economic region reached without further recorded structural deterioration.

**Method.** The evidence is defined from existing fields before the outcome analysis, and the same criteria are applied to every case. Every value is labelled STORED, DERIVED or UNAVAILABLE.

**Reconciliation targets.** 89 A confirmations, 57 WAITs, 13 calls, 12 RETURN, 11 RETURN entered PRIMARY, 52 terminal records.

Delivered: [dossier](delivery/evidence/WP-013-CONTINUOUS-V04-DIAGNOSIS/SUMMARY.md).

## Boundaries

- **Access.** The available app export is read first. At most one REPEATABLE READ READ ONLY extraction, limited to this run, is allowed. No write to the Owner DB and no change to or restart of the Owner stack.
- **No new runs.** No replay, re-execution of the core or evaluator, Deep validation, backtest, counterfactual or acquisition.
- **No method work.** No proposal or implementation of rules, parameters, thresholds or infrastructure.
- **Data scope.** January–August 2026 stays protected, except the authorized tail.
- **Checks.** Dossier verifications only; no product suites or Compose.
- **Review.** The Director reviews; the Owner watches CI. Remote CI: PENDING / NOT CHECKED.
