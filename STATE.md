# Project State

Updated: 2026-09-30

## Authority

Canonical directive: `FOUNDATION.md` — version 2.0.

## Accepted product scope

Algorithmic Trader is a BTC market-analysis and trade-decision system, not an autonomous account-management/trading bot.

The system must eventually:

- maintain a current professional MarketView;
- state plausible/primary scenarios and expected market behavior;
- decide LONG / SHORT / NO_TRADE;
- when a trade exists, expose trigger/entry logic, invalidation, target(s), expected room/time and reasons;
- keep market understanding distinct from trade recommendation;
- update the view/recommendation as the market evolves.

The human Owner independently decides capital allocation, position size, leverage, collateral/margin, actual order placement and personal portfolio/account risk.

## Current milestone

**M3 — Trustworthy real-market observation and causal reasoning readiness**

The application shell, immutable OKX evidence layer, causal feed/observable-state core and prospective live recorder are accepted.

Before wiring real replay/state into the application, the Owner requested a deliberate **product-quality UI redesign** so the application becomes a credible, polished control/observation surface rather than an internal engineering panel.

This UI pass does not introduce professional trader intelligence.

## Accepted work

### WP-001 — Repository bootstrap and observable dummy run
Accepted implementation lineage:
- `92014aa03060332b4c947ef10329b79cde7d51b2`
- CI correction `a49c0f75be7d9d885c65901c9cc73f3ed3a66a99`

The dummy account/risk/order/fill path remains DEMO infrastructure scaffolding only.

### WP-002 — Replay/operations shell and semantic baseline
Accepted implementation:
- `803b3f215c5a33499a4d901ae000ee112b75e691`

Accepted outcomes include durable replay controls, restart recovery, runtime visibility and frozen `algotrader.semantic.v1`.

`algotrader.semantic.v1` remains the synthetic-shell baseline.

### WP-003 — OKX BTC-USDT-SWAP public data provenance
Accepted implementation:
- `6b45728074e470bb85b06cce1995dad90f81cb62`

Acceptance evidence includes GitHub Actions run `36688980492`, successful public OKX integration, frozen `algotrader.marketdata.v1`, immutable source evidence and explicit event/availability/retrieval timing.

### WP-004 — Causal feed and observable market state pure core
Accepted implementation:
- `82e6c8488eec146dfb4fd170fe37966750a84f60`

Acceptance evidence:
- GitHub Actions run `36708401496`: SUCCESS;
- `checks`: SUCCESS;
- `compose-smoke`: SUCCESS;
- `algotrader.feed.v1` PROVISIONAL revision 1;
- deterministic causal ordering and prefix invariance;
- role-specific traded/mark/index/funding channels;
- explicit freshness/quality/missingness;
- packaging-independent normalized feed-content identity.

Accepted interpretations remain:
- modeled availability is a declared convention, not measured publication timing;
- default freshness/history values are inspection defaults only;
- live/incremental duplicate protection belongs at the recorder/journal boundary.

### WP-005 — Prospective OKX public live recorder and measured receipt-time evidence
Accepted implementation:
- primary implementation `3dc890392223ea2634bda8b0c975b2c99c5ddc33`;
- provenance hardening `0cd1ea00074a4740db2761ce00d6777e23540ba3`.

Acceptance evidence:
- GitHub Actions run `36712746921`: SUCCESS;
- WP-005-R1 GitHub Actions run `36718997076`: SUCCESS;
- both `checks` and `compose-smoke` passed on the final commit;
- frozen/provisional `semantic.v1`, `marketdata.v1`, `feed.v1` and `recorder.v1` schema blobs are byte-identical across R1;
- live public recording succeeded against OKX;
- traded/mark/index completed-bar receipt timing is recorded prospectively;
- evolving live funding snapshots are preserved separately from settled funding semantics;
- append-only raw journal, crash recovery/finalization, hashes and clock-quality evidence are present;
- first completed candle receipt becomes RECORDED feed availability without future-value leakage;
- recorder job is durable and browser-independent;
- source authority is enforced before network/artifact creation through one shared rule for recorder and historical OKX acquisition;
- only secure syntactically official `okx.com` / `*.okx.com` endpoint forms are admitted.

Accepted WP-005 interpretations:
- `recv_utc_ns` is client-observed receipt time after the WebSocket/REST read returns, not exchange publication time;
- library buffering/scheduling/network latency remain part of observed receipt delay;
- crashed sessions finalize PARTIAL rather than resume;
- live session latency evidence is session-specific and must not be promoted into a universal constant;
- funding pre-settlement snapshots remain recorder evidence until a later professional process justifies a feed/state interpretation;
- a host clock ahead of OKX (`server - local < 0`) implies offset-adjusted receipt delay is lower than raw delay; the earlier opposite wording in the executor report was prose-only and not a code defect.

## Repository history note

PR #8 had been merged as `64f3fa7`. Commit `887dfe0` was later created from stale parent `b47b3cb`, temporarily dropping the PR #8 tree from main.

The history was repaired without rewriting shared history by merge commit:

`ea88a978d3c44729f60705c332888116af3ecda6`

Future local writes must start from a fresh:

`git pull --ff-only origin main`

Force pushes remain prohibited.

## SR-001 strategic direction

Retained reviews:

- `strategic_reviews/ASTRA-SR-001-REVIEW.md`
- `strategic_reviews/CLAUDE-SR-001-REVIEW.md`

Director disposition:

- `strategic_reviews/SR-001-DIRECTOR-DISPOSITION.md`

Accepted long-lived boundary:

**market evidence → causal availability feed → centrally owned observable market state → professional reasoning → MarketView / prediction / trade recommendation**

## Contract strategy

Frozen:
- `algotrader.semantic.v1` — synthetic shell;
- `algotrader.marketdata.v1` — historical/public market evidence.

Provisional during M3:
- `algotrader.feed.v1`;
- `algotrader.recorder.v1`.

Do not introduce `semantic.v2` until the first real professional trader specification is designed.

## Initial market-data source

Public/read-only reference source:

**OKX `BTC-USDT-SWAP`**

Official-source validation now applies to both historical acquisition and prospective recording.

### WP-006 — Product-grade application UI redesign
Accepted implementation:
- `18242cd39ac9d530a572b3aee962dbc0fdca0d33`

Acceptance evidence:
- one fast-forward implementation commit over `aefb88c76a81424694c8a3cea05e24f901a3162e`;
- GitHub Actions run `36724278731`: `checks` SUCCESS and `compose-smoke` SUCCESS;
- backend/domain code and public contracts were not modified;
- Market is now the default product cockpit and reads only real operational/evidence endpoints;
- synthetic DEMO output is isolated in Replay Lab and cannot populate Market;
- real / synthetic / pending visual materials make implementation truth explicit;
- Data and Recorder are first-class product workspaces;
- synthetic account scaffolding is demoted to DEMO internals;
- E2E covers default Market landing, navigation/deep links, no synthetic leakage, preserved replay/data/recorder behavior and desktop overflow;
- executor visually reviewed/refined 1440×900, 1920×1080 and 1024×768.

Accepted UI direction:
- premium dark decision-desk shell;
- Market reserved for the eventual professional MarketView / scenario / recommendation output;
- Replay Lab separates real observation replay from synthetic DEMO scaffolding;
- Data and Recorder remain evidence/operations surfaces, not trader intelligence.

Non-blocking follow-up:
- global shell health currently degrades for missing run workers but not missing recorder workers; real-replay integration should make the global operational verdict capability-aware rather than imply every subsystem is healthy.

## Active task

**WP-007 — Durable real-market observation replay and observable-state integration**

See `task.md`.

This is the final M3 integration package before the next strategic professional-trader design checkpoint. It must connect accepted real evidence through the accepted causal feed/state core into the durable application experience without introducing interpretation or recommendations.

## UI product direction

The application should look and behave like a serious premium trading/research product, while remaining honest about what is implemented.

The redesigned information architecture should make the product hierarchy clear:

1. **Market / Home** — future professional trader cockpit; currently shows honest not-yet-implemented states plus real system/data readiness.
2. **Replay / Lab** — current synthetic DEMO replay and, later, real causal replay.
3. **Data** — datasets, provenance, quality and future market-state inspection.
4. **Recorder** — live public evidence collection and measured receipt timing.
5. **Artifacts / Operations** — detailed run/evidence inspection where useful.

The synthetic account/position path is DEMO scaffolding and must not dominate the main product experience.

## What comes after WP-007

If WP-007 is accepted, M3 has the required observation/replay substrate:

**real evidence → causal deliveries → centrally owned observable state → durable replay/product visibility**

The next action is a strategic professional-trader design checkpoint before any real trader implementation.

# 🚨🚨🚨 QUESTO VA MANDATO AD ASTRA 🚨🚨🚨

That checkpoint will define the first coherent professional market-reading and trade-decision process and the semantics that justify `semantic.v2`.

Do not implement the professional trader before that checkpoint.

## Known non-blocking technical follow-ups

- WP-004 does not establish expected funding-settlement completeness.
- current feed freshness defaults are inspection-only.
- recorded pre-settlement funding has not yet been promoted into causal observable state.
- no professional market-reading methodology is implemented yet.

## Base knowledge snapshot

`3bf9de0d88fd97360bff7a6517bbb61544f5db68` — professional dossiers only.

## Parallel pre-trader research gaps

Before the first real professional trader specification, resolve only what the selected professional process requires, especially:

1. coherent intraday multi-timeframe context → trigger → invalidation → target/management process;
2. causal structure/levels/support-resistance formalization;
3. venue/data mechanics required by that process.

## Next action

Owner pulls latest `main`.

Claude Code executes only WP-007 from `task.md`.

After WP-007 completion, the Director independently reviews causal correctness, restart/idempotency, real-vs-synthetic separation, UI evidence and CI. If accepted, the project moves to the Astra strategic trader-design checkpoint rather than directly coding trader intelligence.
