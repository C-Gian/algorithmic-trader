# Active Task — WP-005-R1: Enforce Official OKX Source Authority

Status: READY  
Owner: Project & Research Director  
Executor: Claude Code  
Base: latest `main` after `git pull --ff-only origin main`.

## Read first

Read:

1. `FOUNDATION.md`
2. `STATE.md`
3. `AGENTS.md`
4. `task.md`
5. `knowledge/market_sources/OKX-BTC-USDT-SWAP.md`
6. the WP-005 recorder code and tests
7. the existing OKX public market-data client

This is a **narrow correction**. Do not redesign WP-005.

## Why this correction exists

WP-005 correctly restricts paths/channels to public/business interfaces, but endpoint validation currently accepts arbitrary hosts.

Examples that must NOT be accepted:

- `wss://example.com/ws/v5/public`
- `wss://okx.com.evil.example/ws/v5/business`
- `https://example.com`
- plain `ws://...`

A recording from such a host could still be persisted with `source="okx"`, contaminating provenance.

The historical OKX public REST client has the same authority weakness: it requires HTTPS shape but not an official OKX host.

## Objective

Enforce that all configurable OKX source endpoints used by:

- the prospective recorder; and
- the historical/public OKX market-data client

resolve syntactically to **official OKX-controlled hostnames and official secure endpoint forms** before any network call is allowed.

This is source-provenance hardening only.

## Required behavior

### 1. Shared/consistent OKX host authority rule

Implement one clear rule or shared helper, rather than two divergent ad-hoc rules.

At minimum:

- hostname must be exactly `okx.com` or a subdomain ending in `.okx.com`;
- comparison is case-insensitive after URL parsing/normalization;
- reject deceptive suffixes such as `okx.com.evil.tld` or `evilokx.com`;
- reject embedded credentials/userinfo;
- reject fragments;
- preserve support for currently documented regional/global domains such as:
  - `www.okx.com`
  - `openapi.okx.com`
  - `eea.okx.com`
  - `us.okx.com`
  - `tr.okx.com`
  - `ws.okx.com`
  - `wseea.okx.com`
  - `wsus.okx.com`
  and other legitimate `*.okx.com` regional hosts.

Do not build a network/DNS ownership checker. This is a deterministic syntactic authority boundary.

### 2. Recorder WebSocket validation

Require:

- scheme exactly `wss`;
- official OKX hostname;
- exact path:
  - `/ws/v5/public` for public endpoint;
  - `/ws/v5/business` for business endpoint;
- no query string;
- no fragment;
- no userinfo.

If explicit ports are accepted, restrict them to the documented secure WebSocket port used by the supported OKX endpoint form (currently 8443) or omit the port if the implementation deliberately supports a documented default form. Do not accept arbitrary ports.

Do not allow `/ws/v5/private`.

### 3. Recorder REST validation

Require:

- scheme exactly `https`;
- official OKX hostname;
- base URL only: no path other than empty/`/`;
- no query;
- no fragment;
- no userinfo;
- no arbitrary nonstandard port.

The existing path allow-list remains authoritative for calls.

### 4. Historical OKX public client

Apply equivalent REST base-authority validation to `OkxPublicClient`.

Do not change:

- dataset semantics;
- frozen marketdata contracts;
- paging;
- acquisition identity rules except insofar as invalid source hosts are now rejected before acquisition.

Existing datasets remain interpretable.

### 5. Recorder/API provenance

Endpoint overrides through API/environment remain supported **only when they pass the official-source validation**.

The manifest continues to record the actual endpoints used.

Do not silently rewrite an invalid endpoint to a valid one; reject it explicitly.

### 6. Tests

Add/adjust deterministic tests covering at least:

Accepted:
- global OKX REST/public/business endpoints;
- EEA REST + WS endpoints;
- US REST + WS endpoints;
- other valid `*.okx.com` host with otherwise correct secure form.

Rejected:
- arbitrary HTTPS/WSS host;
- `okx.com.evil.example`;
- `evilokx.com`;
- plain `http` and `ws`;
- userinfo;
- query/fragment;
- wrong WS path;
- private WS path;
- arbitrary port;
- historical marketdata client with non-OKX base URL.

Keep fake transports offline by using official-looking endpoint URLs; do not weaken source validation merely to make tests easy.

### 7. Regression requirements

Verify:

- WP-005 recorder tests remain green;
- all previous tests remain green;
- frozen `semantic.v1`, `marketdata.v1`, `feed.v1` remain byte-identical;
- `recorder.v1` schema should not need to change unless the contract itself actually changes;
- no live trader/recommendation/account/execution logic enters this correction.

## Acceptance criteria

WP-005-R1 is complete only if:

1. a non-OKX host cannot produce an artifact labelled as OKX through recorder or historical acquisition;
2. recorder network endpoints are secure public/business OKX forms only;
3. regional OKX endpoints remain configurable;
4. API endpoint overrides are still supported but validated;
5. all tests/CI are green;
6. no unrelated scope expansion occurs.

## Git workflow

Before editing:

`git pull --ff-only origin main`

Then implement, test, commit and push normally to `main`.

No force-push, reset or history rewrite.

## Completion report

Report:

- base/final SHA;
- exact authority validation rule;
- accepted/rejected endpoint examples covered by tests;
- files changed;
- local checks;
- GitHub Actions result;
- any deviation.

Do not declare WP-005 accepted. Final acceptance belongs to the Director.
