# Active Task — WP-003: OKX BTC-USDT-SWAP Public Data Provenance and Bounded Historical Dataset

Status: READY  
Owner: Project & Research Director  
Executor: Claude Code  
Base: latest `main` after the Owner runs `git pull`.

## Context

WP-001 and WP-002 are accepted. The operational shell is complete enough to begin M3.

The professional trader is **not** being implemented yet.

The Director has selected one initial public/read-only market-data source for this milestone:

- venue/source: OKX;
- instrument: `BTC-USDT-SWAP`;
- role: first real BTC-perpetual market-data/reference source;
- authentication: none;
- real orders/account access: prohibited.

Read `knowledge/market_sources/OKX-BTC-USDT-SWAP.md` before implementation. It is the source-specific directive for this work package.

The current semantic trader contract baseline `algotrader.semantic.v1` is frozen. Market-data acquisition must not silently mutate it.

## Objective

Build a source-auditable, causal and immutable **bounded historical data pipeline** for OKX `BTC-USDT-SWAP`.

The result must prove that the application can:

1. identify exactly which perpetual contract the source describes;
2. retrieve a bounded interval of relevant public historical market data;
3. preserve raw source evidence and provenance;
4. normalize it without losing units or timestamp semantics;
5. audit gaps/duplicates/completeness rather than silently repairing them;
6. write immutable, content-hashed dataset artifacts suitable for later causal replay work.

This package establishes data correctness. It does **not** decide trading rules and does **not** simulate real perpetual P&L.

## Source endpoints in scope

Implement read-only support for these official OKX public endpoint families:

1. Instrument definition:
   - `GET /api/v5/public/instruments`
   - target `instType=SWAP`, `instId=BTC-USDT-SWAP`

2. Traded-price candles:
   - `GET /api/v5/market/history-candles`
   - target instrument `BTC-USDT-SWAP`
   - initial normalized granularity: **1m**

3. Mark-price candles:
   - `GET /api/v5/market/history-mark-price-candles`
   - target instrument `BTC-USDT-SWAP`
   - initial normalized granularity: **1m**

4. Index-price candles:
   - `GET /api/v5/market/history-index-candles`
   - derive the index identifier from the instrument metadata where possible; do not duplicate a magic identifier if the source supplies it
   - initial normalized granularity: **1m**

5. Funding-rate history:
   - `GET /api/v5/public/funding-rate-history`
   - target instrument `BTC-USDT-SWAP`

Do not add trades, order book, open interest, liquidations, options, spot feeds or other source families in this work package.

## 1. Source client and configuration

Create a narrow source adapter/interface and an OKX public REST implementation.

Requirements:

- no API keys, secrets, account endpoints or trading endpoints;
- configurable REST base URL, with a documented default;
- do not assume one hostname is universally valid for every region;
- explicit connect/read timeout;
- bounded retry/backoff for safe GET requests only;
- clear handling of OKX non-zero response codes and malformed payloads;
- rate-limit-aware pagination without uncontrolled request bursts;
- user-agent identifying this research application;
- source response bytes/payload must be hashable for provenance.

Do not use an unofficial SDK if a small direct HTTP client is sufficient.

## 2. Instrument snapshot and validation

Before acquiring a dataset, fetch and persist the current public instrument definition.

Normalize at least the source fields necessary to establish:

- `instId`;
- `instType`;
- `ctType`;
- `uly` / instrument family;
- `ctVal`;
- `ctValCcy`;
- `settleCcy`;
- `tickSz`;
- `lotSz`;
- `minSz`;
- `state`;
- listing time where supplied.

Validate that the response describes the requested `BTC-USDT-SWAP` and a linear perpetual/SWAP.

Persist:

- exact raw response;
- source endpoint/base URL;
- retrieval timestamp;
- source-payload SHA-256;
- normalized snapshot.

If the instrument definition is incompatible with what this adapter expects, fail explicitly rather than guessing.

Exchange-advertised leverage is metadata only. It must not alter the project's hard 1x exposure rule and must not be used to introduce leverage behavior.

## 3. Separate market-data contract baseline

Create a market-data-specific versioned contract namespace/baseline such as:

`algotrader.marketdata.v1`

It must be separate from frozen `algotrader.semantic.v1`.

Define explicit typed records for at least:

- source/instrument snapshot;
- traded-price 1m candle;
- mark-price 1m candle;
- index-price 1m candle;
- funding-rate event;
- raw-page provenance/reference;
- dataset manifest;
- data-quality report.

Preserve numeric source values with appropriate exact decimal handling. Do not convert financial values through binary floating-point where that can change their value.

Add a deterministic checked-in JSON Schema (or equivalent explicit baseline) plus schema-drift tests. Intentional future breaking changes require a new market-data schema version; do not overwrite the frozen v1 baseline.

## 4. Timestamp and causal semantics

Timestamp semantics must be explicit and testable.

### Candles

For each 1m candle preserve:

- source opening timestamp;
- computed bar-end timestamp;
- source `confirm` status where supplied;
- retrieval timestamp;
- a separately named modeled availability timestamp/policy.

Rules:

- never normalize `confirm=0` as a completed historical candle;
- do not claim OKX provides an exact historical publication timestamp when it does not;
- for this initial completed-bar dataset, a modeled availability at bar close may be used only if explicitly labeled as a **modeling policy**, not a measured publication fact;
- do not make the completed candle available before the end of its interval;
- do not infer or fill missing OHLC bars.

### Funding

Preserve the source funding event timestamp and the returned fields, including fields such as funding rate / realized rate / formula or method when present.

Do not smear a funding rate backward into periods before the source event time. This work package records funding events only; it does not yet apply funding cash flows to the account.

### Retrieval time

Retrieval time is provenance and is distinct from market event time and modeled availability time.

Add tests that make these distinctions impossible to accidentally collapse.

## 5. Preserve units

Do not treat derivative volume fields as interchangeable.

For OKX derivative candles preserve the documented distinctions between:

- volume in contracts;
- base-currency volume;
- quote-currency volume.

Mark/index candle shapes may differ from traded-price candle shapes; model them explicitly rather than forcing fake volume fields.

Do not convert contract quantity to BTC exposure inside this package beyond storing the source instrument semantics needed for later conversion.

## 6. Bounded historical acquisition

Implement one deterministic application command for acquiring a **bounded interval**, for example:

`algotrader data fetch-okx ...`

Exact CLI shape is implementation detail, but it must accept:

- start UTC timestamp;
- end UTC timestamp;
- output/catalog root;
- configurable base URL.

The acquisition must fetch all four in-scope historical data families for the requested interval:

- trade candles;
- mark candles;
- index candles;
- funding events.

Requirements:

- correct pagination;
- no rows outside the requested normalized interval except source pages retained as raw provenance;
- stable chronological normalized ordering;
- duplicate detection;
- idempotent behavior for an identical completed request;
- no silent overwrite of a different dataset version;
- bounded memory use: do not require loading multi-year source data into memory as one object.

This task is intentionally **bounded**. Do not build the final multi-year background backfill UI/job yet.

## 7. Immutable dataset layout and provenance

Write real acquired data outside Git under the configured data/artifact root.

A completed dataset must have an immutable dataset ID derived from its pinned identity/content and contain or reference:

- instrument snapshot;
- raw source pages/responses or immutable raw-response artifacts;
- normalized Parquet for each in-scope data family;
- dataset manifest;
- data-quality report;
- source request/page log;
- SHA-256 hashes for raw and normalized artifacts;
- software/code version where available;
- market-data schema version;
- requested time range;
- actual first/last records per family;
- row/page counts;
- source base URL and endpoint paths;
- availability-policy identifier.

If the same logical request is fetched later and source bytes/content differ, do not silently mutate the old dataset. Create a distinct version/dataset identity and make the difference visible.

Do not commit real historical datasets or large raw responses to Git.

## 8. Data-quality audit

Produce a structured quality report for each acquired dataset.

At minimum inspect/report:

- duplicate timestamps/keys;
- out-of-order source/normalized records;
- missing expected 1m candle intervals;
- incomplete candles encountered/rejected;
- OHLC consistency (where applicable);
- negative/invalid volume;
- invalid/nonpositive prices;
- interval boundary/alignment issues;
- requested vs actual coverage;
- instrument snapshot consistency;
- funding event duplicate/order issues.

Do **not** automatically repair or forward-fill a gap.

Classify findings so downstream replay can later distinguish usable data from degraded/invalid data.

A clean quality report is evidence about the acquired interval only, not a claim that the entire OKX history is complete.

## 9. Offline deterministic tests and captured fixtures

CI must not depend on OKX network availability.

Commit only small, clearly identified captured/source-shape fixtures sufficient to test:

- instrument parsing;
- each candle family;
- funding parsing;
- pagination;
- duplicate/out-of-order handling;
- incomplete candle rejection;
- gaps;
- source error codes;
- immutable dataset/version behavior.

Record fixture provenance/retrieval metadata. Do not commit a large historical sample.

Use an HTTP mock/fake transport around the same adapter used for live access; do not maintain a second parser for tests.

## 10. Explicit live public integration check

Add a manual/non-CI live integration command/check that:

1. performs the instrument probe;
2. fetches a small recent completed interval;
3. writes a real dataset;
4. validates its hashes/manifest/quality report;
5. prints a concise result containing dataset ID, coverage and quality status.

Run it during this task if public network access is available.

Its output is integration evidence, not a trading result.

If the configured/default OKX public hostname is inaccessible from the executor environment, do not weaken CI or fake success. Report the exact failure and demonstrate the deterministic offline pipeline instead.

## 11. Minimal application visibility

Add a small read-only **Data** view or equivalent Owner-facing application surface that can inspect already-created dataset manifests/quality reports from the configured data root.

It should show at least:

- source/venue;
- instrument;
- dataset ID;
- requested/actual coverage;
- row counts by family;
- quality status and gap counts;
- source retrieval time;
- market-data schema version;
- hashes/provenance access.

This view does not need to launch a multi-year import yet. Do not turn WP-003 into a UI redesign.

The Owner must not need to open raw Parquet or terminal logs to understand whether a dataset is present and healthy.

## Required tests/evidence

At minimum:

- market-data schema baseline/drift tests;
- source parsing/unit tests for all five endpoint families (instrument + four historical families);
- timestamp/availability-policy tests;
- pagination boundary tests;
- duplicate/gap/incomplete-bar tests;
- idempotent identical acquisition test;
- changed-source-content creates distinct immutable dataset/version test;
- manifest/hash verification;
- API/UI test for dataset inspection;
- all WP-001/WP-002 tests remain green.

CI `checks` and `compose-smoke` must remain green.

Provide a small deterministic fixture-derived dataset in tests and, if live access succeeds, report the live bounded dataset ID/coverage/quality summary without committing the real dataset.

## Acceptance criteria

WP-003 is complete only if:

1. source identity and instrument semantics are explicit and persisted;
2. a bounded interval can be fetched from the in-scope OKX public endpoints with correct pagination;
3. only completed candles enter normalized completed-bar datasets;
4. event time, modeled availability time and retrieval time are distinct;
5. source units are preserved without ambiguous conversions;
6. raw provenance and normalized artifacts are immutable and hash-verifiable;
7. quality checks expose gaps/duplicates/incomplete data without silently repairing them;
8. repeated identical source content is idempotent, while changed source content cannot silently overwrite prior evidence;
9. market-data contracts are versioned separately from `algotrader.semantic.v1`;
10. CI remains deterministic/offline and green;
11. the application can inspect dataset/provenance/quality information without raw-log work;
12. no real orders, credentials, professional trader logic or economic performance claims are introduced.

## Prohibited changes

Do not:

- modify `FOUNDATION.md` or `source_notes/`;
- change or overwrite `algotrader.semantic.v1`;
- implement any real trading strategy or indicator;
- connect authenticated account/trading endpoints;
- add API credentials/secrets;
- simulate funding P&L yet;
- freeze real fee/slippage assumptions;
- ingest order book/L2, individual trades, open interest, liquidations or options;
- infer order flow or directional meaning from source data;
- build an unrestricted/multi-year backfill service;
- add a second exchange/source;
- select a future real-money broker;
- start execution economics or WP-004.

## Git / completion workflow

After implementation and local checks:

1. commit the complete bounded task with a meaningful commit message;
2. push normally to the current branch/origin;
3. do not force-push or rewrite history;
4. if GitHub Actions is inspectable, fix genuine WP-003 failures without expanding scope until green or blocked.

## Completion report

Report:

- base commit and final pushed commit SHA;
- pushed branch;
- concise components/files changed;
- local checks and results;
- market-data schema/version evidence;
- deterministic fixture acquisition evidence;
- live OKX integration result if available, including exact configured base URL, dataset ID, interval, row counts and quality summary;
- GitHub Actions result;
- unresolved issues/deviations.

Do not declare WP-003 accepted. Acceptance belongs to the Project & Research Director.
