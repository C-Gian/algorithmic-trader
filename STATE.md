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

The application shell, immutable OKX evidence layer and pure causal feed/observable-state core are now accepted.

M3 next prioritizes **prospective public recording** because true receipt timing and live-only information cannot be reconstructed retroactively.

No professional trader intelligence enters M3 yet.

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

Accepted WP-003 interpretations remain unchanged.

### WP-004 — Causal feed and observable market state pure core
Accepted implementation:
- `82e6c8488eec146dfb4fd170fe37966750a84f60`

Acceptance evidence:
- GitHub Actions run `36708401496`: SUCCESS;
- `checks`: SUCCESS;
- `compose-smoke`: SUCCESS;
- Director verified `algotrader.semantic.v1` and `algotrader.marketdata.v1` blobs are byte-identical to the pre-WP-004 base;
- new `algotrader.feed.v1` is PROVISIONAL revision 1 with schema-drift/revision controls;
- dataset evidence converts to deterministic role-specific feed events;
- modeled availability delay can only postpone knowledge;
- prefix/truncated-history invariance is tested;
- observable state is pure, deterministic and independent of UI/DB/worker/trader/account modules;
- invalid/unconfirmed evidence cannot enter valid state;
- packaging-independent normalized feed-content identity is distinct from acquisition package identity.

Accepted WP-004 interpretations:
- `feedcontent.v1` identifies normalized market/feed content and intentionally excludes acquisition packaging and availability policy; those remain separately recorded;
- `ordered_event_hash` includes provenance, so equivalent economic content acquired through different packages may have different ordered-event hashes;
- a historical missing-slot quality event at the slot's modeled availability is a replay modeling convention, not proof that a live client observed the outage at that instant;
- default 2-minute bar freshness and 240-event history are developer-inspection defaults only, not trader/research parameters;
- sparse funding has no completeness schedule in WP-004;
- live/incremental duplicate/idempotency protection must live in the future recorder/journal boundary rather than rely solely on the bounded observable-state history.

## Repository history note

PR #8 had been merged as `64f3fa7`. Commit `887dfe0` was later created from stale parent `b47b3cb` and contained only `strategic_reviews/CLAUDE-SR-001-REVIEW.md`, temporarily dropping the PR #8 tree from main.

The history was repaired without rewriting shared history by merge commit:

`ea88a978d3c44729f60705c332888116af3ecda6`

Its resulting tree matches `64f3fa7`.

The commit graph alone does not prove which local command/tool moved the branch. Future local writes must start from a fresh `git pull --ff-only origin main`; force pushes remain prohibited.

## SR-001 strategic direction

Retained reviews:

- `strategic_reviews/ASTRA-SR-001-REVIEW.md`
- `strategic_reviews/CLAUDE-SR-001-REVIEW.md`

Director disposition:

- `strategic_reviews/SR-001-DIRECTOR-DISPOSITION.md`

Accepted long-lived boundary:

**market evidence → causal availability feed → centrally owned observable market state → later professional reasoning → MarketView / prediction / trade recommendation**

## Contract strategy

Frozen:
- `algotrader.semantic.v1` — synthetic shell;
- `algotrader.marketdata.v1` — market evidence.

Provisional during M3:
- `algotrader.feed.v1` — causal deliveries and observable state.

Do not introduce `semantic.v2` until the first real professional trader specification is designed.

## Initial market-data source

Public/read-only reference source:

**OKX `BTC-USDT-SWAP`**

Source decision:
`knowledge/market_sources/OKX-BTC-USDT-SWAP.md`

This is a data/reference source choice, not a broker or automated-execution decision.

## WP-005 review status

Implementation under review:
- `3dc890392223ea2634bda8b0c975b2c99c5ddc33`

Verified by Director:
- one fast-forward implementation commit over `de5f3cf970f4791ee4cd4ab6c170c3099ee824a0`;
- GitHub Actions run `36712746921`: `checks` SUCCESS and `compose-smoke` SUCCESS;
- frozen `algotrader.semantic.v1`, `algotrader.marketdata.v1` and provisional `algotrader.feed.v1` schema blobs are unchanged;
- recorder contracts are separate as provisional `algotrader.recorder.v1`;
- append-only journal, crash finalization, receipt-time semantics, first-completed-bar bridge, funding separation and durable recorder job/UI are materially consistent with WP-005;
- current official OKX documentation supports the public/business WebSocket separation, candlestick channels, funding-rate public channel, system-time endpoint and regional OKX domains.

One blocking correction remains before acceptance:

**source authority validation**.

The recorder currently validates URL scheme/path but does not validate that the configured host is actually an official OKX domain. The API accepts endpoint overrides, so a non-OKX HTTPS/WSS host could produce a session whose manifest still says `source="okx"`. Plain `ws://` is also currently accepted.

The same source-authority weakness exists in the historical OKX public client: its configurable REST base URL validates HTTPS shape but not OKX host authority.

This is a provenance/research-integrity issue, not a recorder-mechanics redesign.

## Active task

**WP-005-R1 — Enforce official OKX source authority**

See `task.md`.

## Why recorder comes before application replay integration

Historical REST evidence cannot recover:

- actual client receipt time of completed candles;
- connection/reconnect behavior;
- the evolving pre-settlement funding value visible live;
- the precise delay between source market timestamps and what our process actually received.

This evidence only accumulates prospectively, so recording starts before the observation-only replay/UI integration package.

## Known non-blocking technical follow-ups

- WP-003 `ctMult` zero/missing hardening was completed in WP-005.
- WP-004 does not establish expected funding-settlement completeness.
- current feed freshness defaults are inspection-only.
- the WP-005 live completion report prose said a host clock ahead by ~0.26 s implied true delays were longer than raw delays; the implemented calculation is the opposite and is correct: with `offset = server - local < 0`, adjusted delay is lower than raw. This was a report-description mistake, not a code defect.

None of these blocks WP-005-R1.

## Base knowledge snapshot

`3bf9de0d88fd97360bff7a6517bbb61544f5db68` — professional dossiers only.

## Parallel pre-trader research gaps

Before the first real professional trader specification, resolve only what the chosen trader requires, especially:

1. professional intraday multi-timeframe context → trigger → invalidation → target/management process;
2. causal structure/levels/support-resistance formalization;
3. venue/data mechanics required by that process.

## Next action

Owner pulls latest `main`.

Claude Code implements only WP-005-R1 from `task.md`.

After the narrow source-authority correction passes Director review, WP-005 can be accepted without repeating the full recorder implementation. The next expected package is durable observation-only real replay/UI integration using the accepted feed/state core and recorded-session evidence.
