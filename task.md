# Active Task — WP-004: Causal Feed and Observable Market State Pure Core

Status: READY  
Owner: Project & Research Director  
Executor: Claude Code  
Base: latest `main` after the Owner runs `git pull`.

## Read first

Read in full:

1. `FOUNDATION.md` — version 2.0 is authoritative.
2. `STATE.md`
3. `AGENTS.md`
4. `task.md`
5. `strategic_reviews/SR-001-DIRECTOR-DISPOSITION.md`
6. `strategic_reviews/ASTRA-SR-001-REVIEW.md`
7. `strategic_reviews/CLAUDE-SR-001-REVIEW.md`
8. `knowledge/market_sources/OKX-BTC-USDT-SWAP.md`

Where the advisory reviews conflict with Foundation v2.0 or the Director disposition, Foundation v2.0 and the Director disposition win.

## Context

WP-001–WP-003 are accepted.

The Owner clarified the product scope after SR-001:

**Algorithmic Trader is a professional market-analysis and trade-decision system. It is not an autonomous account sizing, leverage or capital-management bot.**

Do not implement autonomous position sizing, leverage, collateral/margin, account-level risk, liquidation or real execution in this task.

The accepted market evidence layer already exists as `algotrader.marketdata.v1`.

The next long-lived boundary is:

**immutable market evidence → causal availability feed → centrally owned observable market state**

This task implements only that boundary as a pure domain core. It does **not** connect the real data to the current dummy trader/account path yet.

## Objective

Build a deterministic, versioned causal feed and observable-state core that can consume the accepted OKX market-data evidence without lookahead, preserve asynchronous source timing/quality, and produce point-in-time market-state snapshots suitable for a future professional trader.

The core must be independent of:

- UI;
- PostgreSQL;
- worker leases;
- dummy trader;
- account/P&L;
- trade execution;
- professional trading rules.

## 1. Provisional feed contract namespace

Create a separate provisional contract namespace:

`algotrader.feed.v1`

It must not mutate:

- `algotrader.semantic.v1`;
- `algotrader.marketdata.v1`.

Create a checked-in machine-readable schema baseline plus drift tests.

Mark the namespace clearly as **PROVISIONAL during M3**. Unlike the frozen semantic/marketdata baselines, controlled breaking changes remain possible until M3 acceptance, but they must require:

- schema version/change note;
- explicit Director approval in a future task.

Do not create `semantic.v2` in WP-004.

## 2. Availability-event model

Define a typed event envelope that can represent causally available market evidence.

At minimum include:

- stable event identity;
- channel/family identity;
- instrument/series identity;
- event kind;
- event/economic time;
- availability time;
- availability basis: at least `MODELED` or `RECORDED`;
- availability-policy identifier;
- retrieval/recording/provenance reference where applicable;
- source record reference;
- deterministic ordering fields;
- payload reference or typed payload;
- validity/quality semantics where applicable.

Required event categories include at least:

- valid market observation;
- quality/invalid/missing-slot event;
- sparse funding event.

Do not model account settlements, orders or fills.

## 3. Deterministic causal ordering

Implement one total ordering policy for feed events.

Requirements:

- primary ordering is availability time;
- stable deterministic tie-breaking independent of filesystem order, HTTP page order and database return order;
- observations from different families at the same modeled availability time have deterministic ordering;
- quality events and valid observations for the same slot cannot produce ambiguous state;
- the ordering policy is named/versioned and written into snapshots/manifests produced by this core;
- identical causal inputs produce identical ordered-event hashes.

Do not encode a claim that the ordering represents the true exchange micro-order when source evidence does not establish it. It is a deterministic historical/replay convention.

No trade/execution/account phase ordering belongs in WP-004.

## 4. Dataset → causal-feed adapter

Create a pure adapter that reads an accepted `algotrader.marketdata.v1` dataset and produces feed events.

Requirements:

- consume normalized market-data artifacts/manifest, not live network calls;
- preserve source/provenance references;
- never expose `confirm=0` as a valid completed observation;
- rows marked INVALID cannot become valid observation events;
- gaps/conflicting excluded rows must be representable as quality/coverage events rather than silently disappearing;
- traded, mark, index and funding remain distinct channels;
- no silent substitution between channels;
- no synthetic forward-filled market observations;
- preserve exact Decimal values.

The adapter must not mutate WP-003 dataset artifacts.

## 5. Availability transformation

WP-003 stores source evidence and an accepted historical modeling policy.

WP-004 must make availability an explicit feed transformation.

Requirements:

- support the existing marketdata modeled availability as an input;
- permit an explicit non-negative modeled delay parameter/policy to be applied in the feed layer without rewriting the source dataset;
- record which availability policy produced each feed event;
- a delayed availability transformation must never change the market/event time;
- no default numeric delay should be presented as measured fact.

Tests must prove that increasing the modeled delay can only delay knowledge, never move an event earlier.

Actual live receipt-time measurement is deferred to the next package.

## 6. Observable market state reducer

Implement a pure reducer:

`state' = apply(state, event)`

It owns observable market history/state. The future professional trader must not need to buffer raw source records independently.

At minimum maintain independently for each in-scope channel:

- latest valid observation/event;
- latest event/economic time;
- latest availability time;
- age relative to an explicit snapshot/as-of time;
- quality/validity state;
- coverage/missingness information needed to distinguish missing from invalid;
- source/dependency references.

Support at least these distinct states/conditions:

- never seen / warm-up;
- fresh;
- stale;
- missing/gap;
- invalid-only / rejected evidence.

Exact freshness thresholds are configuration/policy, not universal constants.

A last valid value may remain visible with its original timestamp and stale status. It must not become a fabricated fresh observation.

## 7. Snapshot and delta

Create a typed point-in-time observable-state snapshot.

A snapshot must include:

- snapshot identity;
- as-of/knowledge cutoff;
- feed/order-policy version;
- channel states;
- dependency/source references sufficient for audit;
- explicit quality/freshness.

Also provide a deterministic delta/change representation between snapshots or since a prior feed cursor so the future trader can know **what changed** without re-reading raw datasets.

Do not put professional interpretation in the snapshot.

Examples of content that belong in state:

- latest traded candle and its freshness;
- latest mark candle and freshness;
- latest index candle and freshness;
- latest funding event and its event/availability time;
- coverage gap.

Examples that do **not** belong in state in WP-004:

- “support is defended”;
- “continuation likely”;
- “bullish”;
- “buy”;
- target price;
- confidence.

## 8. Price/source roles

The core must preserve role-specific channels.

Freeze no directional interpretation.

At minimum:

- traded data remains traded evidence;
- mark remains mark;
- index remains index/reference;
- funding remains funding/carry evidence.

Do not create one generic current-price field that silently chooses among them.

A convenience projection may expose clearly named values, but role identity must remain explicit.

## 9. Prefix / truncated-history invariance

Add strong causality tests.

For a pinned dataset/event sequence and cutoff `T`:

- observable state at or before `T` must be identical whether the adapter is given only evidence available through `T` or the full later dataset;
- adding evidence with availability strictly after `T` cannot change the snapshot at `T`;
- changing replay speed/order of file reads cannot change the causal ordered result;
- delayed availability must change only snapshots after the delayed knowledge time.

Include late-arrival and same-time multi-family cases.

## 10. Dataset-composition identity

WP-003 `dataset_id` identifies an acquisition/evidence package, and equivalent normalized economic content may exist under multiple package IDs.

For feed/replay identity, add a deterministic normalized-content identity/reference sufficient to detect equivalent ordered normalized source records independent of irrelevant acquisition pagination.

Do not delete or replace dataset/package IDs; retain both:

- evidence-package identity;
- normalized feed-content identity.

Define the identity narrowly for current in-scope records. Do not build a universal data-lake deduplication framework.

## 11. Pure-core inspection tooling

Add a small CLI/test utility that can:

- load an existing dataset;
- build its causal feed under a selected availability policy;
- advance to a supplied UTC cutoff;
- print a concise observable-state snapshot and channel freshness/quality;
- print feed event count/hash and normalized-content identity.

This is developer/Director inspection, not Owner UI yet.

Do not integrate the new feed/state into the browser or run worker in WP-004.

## Required tests

At minimum cover:

- schema baseline and provisional contract checks;
- deterministic event ordering;
- stable tie-breaking;
- dataset adapter for trade/mark/index/funding;
- INVALID record exclusion from valid state;
- gap vs invalid vs never-seen distinction;
- no forward fill;
- last-valid carried only as stale;
- modeled availability delay monotonicity;
- prefix/truncated-history invariance;
- same-time heterogeneous events;
- late-arrival event;
- deterministic snapshot/delta;
- normalized feed-content identity;
- equivalent normalized content from different acquisition packaging where fixture support permits;
- all WP-001/WP-002/WP-003 tests remain green.

CI `checks` and `compose-smoke` must remain green.

## Acceptance criteria

WP-004 is complete only if:

1. `algotrader.feed.v1` exists separately and is explicitly provisional;
2. accepted marketdata datasets can be transformed into deterministic causal events;
3. event/economic time and availability/knowledge time remain distinct;
4. modeled delay cannot create lookahead;
5. the observable-state reducer is pure and deterministic;
6. traded/mark/index/funding retain separate identities;
7. per-channel freshness/quality/missingness is explicit;
8. invalid evidence never enters valid state;
9. future evidence cannot change a past snapshot;
10. snapshot + delta are sufficient for a future professional reasoning layer without raw-dataset access;
11. dataset acquisition identity and normalized feed-content identity are both preserved;
12. no professional trading interpretation, account sizing, leverage, P&L or execution is introduced;
13. existing CI remains green.

## Prohibited changes

Do not:

- modify `source_notes/`;
- revert or weaken Foundation v2.0;
- create `semantic.v2`;
- implement MarketView/trader logic;
- implement indicators, market structure, support/resistance or directional rules;
- implement trade entry/targets;
- implement account/equity/collateral/margin/leverage logic;
- implement orders/fills/execution simulation;
- implement fee/funding P&L;
- connect authenticated APIs;
- add a second venue/source;
- build the live recorder yet;
- redesign the UI;
- weaken existing WP-001–003 tests.

The existing DEMO account/order code may remain untouched for regression compatibility.

## Git / completion workflow

After implementation and local checks:

1. commit the bounded task;
2. push normally to the current branch/origin;
3. do not force-push or rewrite history;
4. resolve genuine WP-004 CI failures without expanding scope.

## Completion report

Report:

- base commit and final pushed SHA;
- pushed branch;
- files/components changed;
- exact feed-contract version/status;
- ordering and availability policies implemented;
- deterministic/prefix-invariance evidence;
- normalized-content identity evidence;
- all local checks and results;
- GitHub Actions result;
- deviations/unresolved issues.

Do not declare WP-004 accepted. Acceptance belongs to the Project & Research Director.
