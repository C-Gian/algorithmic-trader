# Market Source Decision — OKX BTC-USDT-SWAP

Status: accepted initial M3 data/reference source  
Decision date: 2026-09-30  
Scope: public market data and paper-simulation reference only

## Decision

Use OKX `BTC-USDT-SWAP` as the first real BTC perpetual market-data/reference venue for M3.

This does **not** select a future real-money broker, authorize an account, permit real orders, or make OKX data the permanent/only source. It is the first bounded source used to establish data provenance, causal replay and perpetual-market semantics.

All access in the first data work package is public/read-only and must require no API key.

## Why this source is suitable for the first integration

The current official public instrument endpoint exposes the contract identity and trading-unit semantics needed to avoid treating a ticker as a complete instrument definition.

Official historical-data coverage also exists for candlesticks, funding rates, tick trades and high-resolution L2 order-book data. Only the subset explicitly required by the active work package should be integrated; availability of richer data is not a reason to ingest it prematurely.

OKX documents regional API domains. Base URLs must therefore be configurable rather than embedded throughout the code.

## Verified current instrument snapshot

Verified from the official public instruments response on 2026-09-30:

- instrument: `BTC-USDT-SWAP`
- instrument type: `SWAP`
- contract type: `linear`
- underlying/index family: `BTC-USDT`
- contract value: `0.01`
- contract value currency: `BTC`
- settlement currency: `USDT`
- tick size: `0.1`
- lot size: `0.01`
- minimum size: `0.01`
- state: `live`

The response also advertises exchange leverage capability. That is venue metadata only and does not alter the project's hard product rule of no exposure above 1x account equity.

Do not hard-code these values as eternal facts. Fetch and persist the source snapshot, retrieval time and hash whenever creating a real dataset.

## Official references

- Current public instrument response:
  https://www.okx.com/api/v5/public/instruments?instType=SWAP&instId=BTC-USDT-SWAP
- OKX API documentation:
  https://www.okx.com/docs-v5/en/
- OKX Europe historical market data:
  https://www.okx.com/it/historical-data
- OKX Europe API documentation/domain:
  https://my.okx.com/docs-v5/en/

Relevant public endpoints documented by OKX include:

- `GET /api/v5/public/instruments`
- `GET /api/v5/market/history-candles`
- `GET /api/v5/market/history-mark-price-candles`
- `GET /api/v5/market/history-index-candles`
- `GET /api/v5/public/funding-rate-history`

## Historical coverage documented by OKX

The official historical-data page currently states availability from:

- tick trades: September 2021;
- perpetual funding rates: March 2022;
- high-resolution L2 order book: March 2023;
- downloadable OHLC candlesticks: July 2023.

These are source-availability statements, not claims that every interval is complete or suitable. Every acquired dataset must be audited for gaps, duplicates, ordering, revisions and exact covered interval.

## Causal/data-quality rules

- Preserve source timestamps and raw source values.
- Never treat an incomplete candle (`confirm=0`) as a completed historical observation.
- For confirmed bars, distinguish source event/open time from the modeled earliest availability time. The API does not provide an exact historical publication timestamp for each completed bar; any bar-close availability convention must be labeled as a modeling policy, not a measured fact.
- Preserve retrieval time separately from event/availability time.
- Do not silently forward-fill missing market observations.
- Funding records must remain event records; do not smear a funding rate backward over periods in which it was not yet known.
- Raw/source artifacts and normalized datasets must be immutable and content-hashed. A changed source response creates a new version rather than silently replacing old evidence.
- Market-data provenance must remain separate from semantic trader contracts.

## Regional-domain rule

OKX currently documents regional API domains, including `eea.okx.com` for EU-registered users. Public-data code must accept a configured base URL/domain. Tests must not assume that one public hostname is universally valid for every region.

CI should remain deterministic and should not depend on live OKX availability. Use captured source-shape fixtures for automated tests; live public connectivity is a separate explicit integration check.

## Deferred

Not part of the first data package:

- authenticated account endpoints;
- order submission or cancellation;
- API keys or secrets;
- fee-tier/account-specific data;
- execution calibration;
- order-book/L2 ingestion;
- order-flow interpretation;
- liquidation signals;
- professional trader logic;
- source combination or multi-venue voting.

Those require later, explicit work packages.
