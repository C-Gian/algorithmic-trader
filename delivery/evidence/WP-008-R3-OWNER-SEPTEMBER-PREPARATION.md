# Owner September pack preparation — accepted preparation evidence
Date: 2026-10-03 (Owner report received23:21 Europe/Rome).
Evidence: Owner's copied terminal preparation report, reviewed by Director. Not independently acquired or rerun; no replay/backtest occurred.

Job `pack-job-20261003T212006-fe74a7`: COMPLETED, outcome prepared, generation1, attempt1, health finished.
Pack `pack-427d5f5d0e26d595ff0c131c70a9435b26692dbe`: READY,147975 canonical events.
Preset `btc-september-development-v1`, preset hash prefix4b56ad2f472aaee3; methodbtc.context-action.v0.2 / mp001.rules.v0.2, register prefixe2e2dd8ef050, profile prefixb343c88c95c5. Content identity reported only in abbreviated form `feedcontent.v1:2cc523c7adf54…`; full hash not inferred.

UTC half-open windows:
- Warmup2025-08-28T00:00:00Z→2025-09-01T00:00:00Z, unscored.
- Evaluation2025-09-01T00:00:00Z→2025-10-01T00:00:00Z, development; adviser scoring unavailable.
- Tail2025-10-01T00:00:00Z→2025-10-01T06:05:00Z, unscored.
- Clock end2025-10-01T06:05:00Z.

One local slice reused, two missing boundary slices downloaded,3193906 bytes reported:
- `okx-btc-usdt-swap-1m-20250828T0000-20250901T0000-6bcd709fcf05`, completed four-day warmup.
- `okx-btc-usdt-swap-1m-20251001T0000-20251001T0605-8fcaee4b43d2`, completed365-minute tail.
Source package bytes25459470 (referenced); added pack-cache bytes10544979. Different counters describe package/download/cache storage; no inference of byte identity from these aggregates. No overlap, collapsed duplicates or superseded gaps.

| Series | Warmup usable | Evaluation usable | Tail usable | Missing/rejected |
|---|---|---|---|---|
| trade1m |5760/5760|43200/43200|365/365|0/0 in every window|
| mark1m |5760/5760|43200/43200|365/365|0/0 in every window|
| index1m |5760/5760|43200/43200|365/365|0/0 in every window|

Arithmetic check:(5760+43200+365)×3=147975. Trade/mark/index OBSERVED_COMPLETE for requested windows. All funding windows0 rows, EMPTY_UNKNOWN, never no-settlement proof. Calendar NONE_UNKNOWN; incidents/quotes/OI/liquidations/depth/flow NOT_COVERED; source capability probes NOT_PROBED. Metadata PINNED_RETRIEVAL_SNAPSHOT_ASSUMED_FOR_WINDOW, historical effective date unproven. Future evaluation scope PRICE_NET_ONLY/TOTAL_NET_UNAVAILABLE unless funding coverage is separately proven.

Director disposition: preparation handoff CLOSED. Confirms actual boundary acquisition and complete requested price rows as reported; does not independently establish runtime replay validation, model frequency/utility/profitability or historical metadata/funding/calendar completeness. No new observation check, Deep run, other months or economic evaluation requested. Continue to WP-009 implementation specification using this reusable pack.
