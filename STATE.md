# Project State

Updated: 2026-09-30

## Authority

Canonical directive: `FOUNDATION.md`

## Accepted product scope

- BTC only.
- Paper execution instrument: BTC perpetual futures.
- Actions: LONG / SHORT / NO_TRADE; HOLD / REDUCE / EXIT while exposed.
- No leverage above 1x account-equity exposure.
- Intended trade duration: minutes to hours, not days.
- Research/paper only; no real capital.

## Current milestone

**M3 — Data and execution readiness for BTC perpetual paper operation**

The operational/dummy shell and the first source-auditable BTC-perpetual market-data pipeline are accepted.

Before the next implementation package, the project is at a strategic architecture checkpoint: real market data must be connected to replay/trader/execution semantics without carrying the synthetic engine's quantity/accounting assumptions into the real perpetual system.

## Accepted work

### WP-001 — Repository bootstrap and one observable dummy run
Accepted implementation lineage:
- `92014aa03060332b4c947ef10329b79cde7d51b2`
- CI correction `a49c0f75be7d9d885c65901c9cc73f3ed3a66a99`

### WP-002 — Complete replay/operations shell and freeze semantic contracts
Accepted implementation:
- `803b3f215c5a33499a4d901ae000ee112b75e691`

Accepted outcomes include durable replay control, restart recovery, runtime visibility and frozen `algotrader.semantic.v1`.

### WP-003 — OKX BTC-USDT-SWAP public data provenance and bounded historical dataset
Accepted implementation:
- `6b45728074e470bb85b06cce1995dad90f81cb62`

Acceptance evidence:
- GitHub Actions run `36688980492`: SUCCESS;
- `checks`: SUCCESS, including all existing tests and market-data/API/UI tests;
- `compose-smoke`: SUCCESS;
- Director verified the E2E data view and immutable provenance/hash behavior;
- live public OKX integration succeeded on both `https://www.okx.com` and `https://eea.okx.com`;
- `algotrader.marketdata.v1` is separate from and does not mutate `algotrader.semantic.v1`;
- event time, modeled availability time and retrieval time remain distinct;
- incomplete candles are rejected and gaps/duplicates are surfaced without silent repair.

Accepted WP-003 interpretations:
- the current `dataset_id` identifies an acquisition/evidence package, not a claim of unique economic content; different base URLs or pagination choices may therefore yield different package IDs;
- funding `available_time = funding_time` is a labeled causal modeling policy, not a measured historical publication timestamp and not evidence that the rate was known earlier;
- conflicting duplicate records are conservatively excluded from normalized usable data while their raw source evidence is retained;
- rows marked `INVALID` remain evidence but must be blocked/excluded by default from real replay consumption;
- `state != live` is a warning for historical acquisition, not automatic invalidation;
- the 31-day acquisition cap is a WP-003 operational bound, not a research horizon;
- live datasets created from a `-dirty` code version are integration evidence only, not canonical research datasets.

## Initial M3 market-data source

Public/read-only reference source: **OKX `BTC-USDT-SWAP`**.

Source decision:
`knowledge/market_sources/OKX-BTC-USDT-SWAP.md`

This is not a real-money broker selection. No authenticated account or order endpoint is authorized.

## Active implementation task

**None — strategic review checkpoint SR-001.**

Do not run Claude Code against the old WP-003 task.

Review brief:
`strategic_reviews/SR-001-PRE-REAL-TRADER-ARCHITECTURE.md`

## Base knowledge snapshot

`3bf9de0d88fd97360bff7a6517bbb61544f5db68` — professional dossiers only.

## Why implementation is paused

The current dummy engine still contains synthetic scaffolding that must not be silently generalized:

- its replay input is a synthetic `Fixture`;
- its primary semantic observation is a single OHLCV `MarketObservation`;
- account quantity is effectively treated as BTC units;
- mark price is the last synthetic traded close;
- funding is not modeled;
- fee/slippage values are DEMO placeholders;
- market orders use a deliberately simplified next-bar-open fill.

Real OKX linear perpetual semantics instead involve explicit contract units, contract value, mark/index/traded price roles and funding events.

The next architecture determines the long-lived boundary among:

**market-data evidence → causal event/replay source → professional trader inputs → risk → account/perpetual accounting → execution simulation**

This is a high-cost-to-reverse decision and is therefore reviewed by Astra before implementation.

## Next action

Owner sends SR-001 to the Astra strategic-review chat.

The Project & Research Director then reviews Astra's conclusions, accepts/rejects them explicitly, updates the Foundation/architecture only if warranted, and writes the next bounded Claude Code task.

No real trader logic is implemented before that review.
