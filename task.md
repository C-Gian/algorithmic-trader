# Current Task — Owner Backtest A causal dossier
Status: **ACTIVE — EXECUTOR READ-ONLY EVIDENCE EXTRACTION; NO PRODUCT IMPLEMENTATION**
Date: 2026-10-05.

Execute [Director disposition and bounded assignment](delivery/WP-009-OWNER-BACKTEST-A-DIRECTOR-DISPOSITION.md), adopting Astra §6 of [the review](delivery/WP-009-OWNER-BACKTEST-A-ASTRA-REVIEW.md). Target existing evaluation `eval-20261005T120047-e6cc50`, replay `obs-20261005T120047-bc6947` only. Preserve [original report](delivery/evidence/WP-009-OWNER-BACKTEST-A.json).

Extract a one-time causal dossier from committed existing records: 38 trigger rows with geometry/zone cutoffs and minimum-confirmation feasibility; 109 candidate histories, bounded upstream coverage and max five outcome-free timelines. Exact facts, derived fields and missing evidence must be distinguished. Read-only local DB/API/cache access authorized within disposition; no writes/services/Owner data changes, replay/Deep/backtest, future-outcome selection, method change or source acquisition.

Deliver full JSON/CSV and SUMMARY.md under delivery/evidence/WP-009-OWNER-BACKTEST-A-DOSSIER/. Verify original counts/provenance/cutoffs and small arithmetic examples; no full product-suite/Compose rerun or product-code changes for this extraction. Stop on inaccessible evidence; report what is missing without constructing a replacement replay. Update STATE with actual evidence; commit/push normally. CI waiting and standing workflow are in AGENTS.md.

Completion: **READY FOR DIRECTOR REVIEW — OWNER BACKTEST A DOSSIER ONLY**. No next method/replay package activated.
