# Owner Backtest A — September development

Status: **READY FOR OWNER BACKTEST A**. Date: 2026-10-05.
Accepted product code: `6f95273b54674081fe6b3896a84d62a015384fe5`; [acceptance](WP-009-CORRECTION-DIRECTOR-REVIEW.md). MP-001 v0.2, adviser.core.v2 / adviser.evaluator.v2; primary historical profile and its pinned costs/delay, no parameter changes.

## Purpose and evidence boundary

First integrated economic development evaluation: assess whether opportunities are reachable, practical entry windows, calls per evaluated week, coverage, candidate/rejection/blocker diagnosis and hypothetical price-net outcomes. A few calls per week is a usability expectation to assess, not an issuance quota or acceptance guarantee. Zero calls requires diagnosis, not forced trades. A first month cannot establish usefulness or generalization; September is development, not protected evidence.

No economic run has been performed by the Director or executor. The Owner starts it in the app and returns its copied report. No year acquisition, sweep, mandatory live session or Deep replay is requested.

## App flow

1. Update the Owner checkout and application using README's safe upgrade: stop application services (`api worker recorder observer corpus adviser`), update checkout, `docker compose up --build -d`. Preserve all volumes; never use `--volumes`. This is an Owner update, not a Claude synchronization task.
2. Open Historical Workbench. At Prepare data select the already prepared preset **btc-september-development-v1** and existing READY pack **pack-427d5f5d0e26d595ff0c131c70a9435b26692dbe**. No new Prepare/download is needed. If that exact pack is missing or invalid, return the app diagnostic rather than selecting different data.
3. At Start a run select **Adviser evaluation**, that pack, speed **max**, then **Start**. Do not select Market replay (observation-only). Keep default pinned method/profile; create a new run, do not reuse an old observation result.
4. Follow the run. Estimated 3–6 minutes, extrapolated from small synthetic evidence, not a measured September runtime. If it fails/stalls or substantially exceeds roughly 15 minutes, use its current Copy report for chat and return that diagnostic; no repeated retries or overnight wait.
5. Once it finishes, check COMPLETED and the run's own runtime assurance PASSED. Full source feed is expected to be **147,975 events** including warmup/tail; compare committed cursor with that run's verified total, not 129,600 from the old September-only observation. Copy the Adviser evaluation report using **Copy report for chat** and paste it to the Director. Do not launch Deep validation unless separately requested.

## How to read it

- Warmup 28 August–1 September UTC builds context and is unscored. Evaluation 1 September–1 October UTC is the scored development month. Tail to 1 October 06:05 UTC follows eligible calls without issuing new ones.
- Runtime PASS means software/input integrity checks passed, not that calls are good or profitable.
- Read distinct calls, calls/week, entry durations and candidate/blocker funnel together; outcomes need their denominator, ambiguous/unresolved cases and cost/delay assumptions.
- Funding completeness is unproven: PRICE_NET_ONLY, TOTAL_NET_UNAVAILABLE. Calendar/news and other missing capability limits remain visible; absent inputs are not proof they were unnecessary.
- Stop after the copied report. The Director diagnoses the results and assigns any bounded versioned implementation change to Claude. Substantial reruns remain Owner-operated in the web app.
