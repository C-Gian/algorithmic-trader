# Active Task — WP-006: Product-Grade Application UI Redesign

Status: READY  
Owner: Project & Research Director  
Executor: Claude Code  
Base: latest `main` after `git pull --ff-only origin main`.

## Read first

Read in full:

1. `FOUNDATION.md`
2. `STATE.md`
3. `AGENTS.md`
4. `task.md`
5. current `web/` implementation
6. current API types/endpoints used by the UI
7. existing UI/E2E tests

Foundation v2.0 and STATE.md define the product. The current screen layout is not product direction.

## Mandatory design workflow

**Before coding, invoke/read and actively use your front-end design / frontend-design skill.**

This is not an incidental styling task. Treat it as a real product-design and front-end architecture pass.

Use the skill to reason about:

- information hierarchy;
- navigation;
- visual rhythm;
- density;
- typography;
- responsive layout;
- states and affordances;
- chart/dashboard composition;
- premium-product polish.

Do not merely restyle the existing DOM with darker colors.

## Owner feedback that triggers this task

The current application is functionally useful but visually unacceptable as a product:

- it feels like a tiny boxed engineering/admin UI;
- it wastes desktop space;
- hierarchy is weak;
- the interface does not feel like something that could be sold or shown publicly;
- the product's future trader purpose is not obvious;
- old DEMO account/position scaffolding is visually over-prominent;
- the lack of real professional signals is confusing because the UI does not clearly distinguish future trader intelligence from current infrastructure.

The redesign must address all of those problems.

## Product truth

Algorithmic Trader is a **BTC market-analysis and trade-decision system**.

The future product will continuously show:

- current MarketView;
- what changed;
- prediction / primary and alternative scenarios;
- LONG / SHORT / NO_TRADE;
- trigger / entry condition or zone;
- invalidation;
- target(s) / expected destination;
- expected horizon;
- supporting and opposing evidence;
- uncertainty;
- what would change the view.

However, **the real professional trader does not exist yet**.

Therefore this task must create the product surface for those concepts **without fabricating any real signal, prediction, target or recommendation**.

Current real capabilities are:

- durable application/worker shell;
- synthetic DEMO replay;
- historical real OKX datasets and quality/provenance;
- causal feed/state core (not yet application-integrated);
- public live recorder and receipt-time evidence;
- health/runtime state;
- run artifacts.

## Objective

Transform the web application into a polished, premium, professional desktop product that is credible as a sellable beta/prototype while preserving the current functional behavior.

The result should feel like a modern professional trading/research terminal, not an internal admin panel.

This task is primarily front-end. Backend/domain semantics should remain unchanged unless a very small read-only API adjustment is strictly necessary to expose data the backend already has. Do not create new trading semantics.

## Visual direction

Aim for:

- dark-first professional interface;
- full-width / full-height desktop composition;
- strong hierarchy;
- restrained, premium color palette;
- excellent typography and spacing;
- crisp cards/panels;
- information-dense but calm;
- modern status pills/badges;
- clear positive/negative/neutral/warning semantics;
- subtle borders/elevation, not heavy boxes everywhere;
- polished empty/loading/error states;
- coherent iconography if a lightweight icon library is justified;
- high-quality hover/focus/active states;
- responsive behavior, with desktop as the primary target.

Avoid:

- 1990s/admin-dashboard appearance;
- tiny centered content;
- giant unused margins;
- neon/cyberpunk styling;
- casino-like green/red flashing;
- gratuitous gradients;
- fake trading numbers;
- decorative complexity that reduces readability.

Do not clone another product. Create an original interface appropriate to Algorithmic Trader.

## Information architecture

Replace the current two-tab feel with a real application shell.

At minimum provide clear destinations equivalent to:

### 1. Overview / Market

This becomes the default landing page and future professional trader cockpit.

It must communicate the product purpose immediately.

The page should include visually strong areas for:

- BTC / BTC-PERP identity and market-status header;
- current trader-intelligence state;
- MarketView;
- scenario/prediction area;
- trade-decision area;
- trade geometry: trigger/entry, invalidation, targets, horizon;
- evidence / conflicts / what-would-change-the-view;
- data freshness / system readiness.

Because the professional engine is not implemented:

- these trader-intelligence areas must show an explicit, polished **NOT YET IMPLEMENTED / awaiting professional trader engine** state;
- do not populate them from the synthetic DEMO trader;
- do not invent placeholder prices/signals that can be mistaken for real output.

The Overview may show **real current infrastructure readiness**, derived from existing endpoints where available, such as:

- API/worker health;
- recorder health/status;
- number/latest historical datasets;
- latest completed recorder session;
- whether real causal trader integration is available yet.

Make a clear visual distinction between **real operational readiness** and **future trader intelligence**.

### 2. Replay Lab

Move the existing synthetic replay here.

Keep all current capabilities:

- start run;
- speed;
- fault injection;
- run selection;
- pause/resume/step/cancel;
- runtime state;
- progress;
- ETA;
- worker heartbeat;
- synthetic chart;
- dummy market view/decision;
- action history;
- artifacts;
- recovery/control logs.

But present it as a clearly bounded **DEMO / SYNTHETIC LAB**.

The current synthetic account/position scaffolding must not look like a product feature. Either:

- demote it into a collapsible `DEMO internals` / `synthetic account scaffolding` section; or
- visually subordinate it strongly.

Do not remove the data needed by existing tests unless tests are updated without weakening their behavioral intent.

### 3. Data

Keep historical dataset inspection but redesign it as a professional data/evidence workspace.

Improve:

- dataset list/scanning;
- source/instrument/coverage summary;
- quality state;
- gaps;
- provenance;
- file/hash inspection;
- empty/loading/error states.

Remove stale product wording that implies the real product owns a 1x exposure policy.

### 4. Recorder

Give the public recorder its own first-class destination instead of burying it inside Data.

Preserve all existing recorder behavior:

- start/stop;
- duration;
- state;
- heartbeat;
- connections;
- subscriptions;
- message counts;
- last receipt;
- reconnects/errors;
- output reference;
- measured completion timing;
- manifest/report access.

Make it obvious that this is:

**Public market evidence collection — no trading.**

### 5. Operations / Artifacts

You may either create a dedicated destination or keep run artifacts naturally inside Replay Lab if that yields a cleaner product.

Do not create empty navigation solely to satisfy a label.

## Application shell

Create a coherent top-level shell, for example:

- persistent sidebar or high-quality desktop navigation;
- product mark/name;
- current section;
- compact global system-health indicator;
- content workspace that uses the screen properly.

Choose the exact shell through the frontend-design skill.

Requirements:

- desktop widths around 1366–1920 px must use the available space well;
- avoid a hard tiny max-width;
- navigation should remain usable at narrower widths;
- horizontal overflow should be intentional only for data tables where necessary.

## Design system / reusable primitives

Create a lightweight internal design system rather than one-off CSS.

Use reusable concepts/components for things such as:

- app shell/navigation;
- page header;
- surface/card;
- section header;
- metric;
- status badge;
- empty state;
- notice/callout;
- button variants;
- form controls;
- table treatment;
- skeleton/loading state;
- health indicator.

A full external UI-framework migration is not required and should not be done unless clearly justified.

Prefer maintainable React/CSS over a giant monolithic `App.tsx`.

Refactor the current oversized front-end file into coherent components/views where useful.

## Chart presentation

The current synthetic chart is functional but visually basic.

Improve its product framing:

- larger, well-proportioned chart area;
- better labels/context;
- stronger readability;
- responsive sizing;
- synthetic/demo identity unmistakable.

Do not add fake technical indicators or signals.

Do not spend this task implementing a professional charting engine.

## Copy and semantic cleanup

All owner-facing copy must align with Foundation v2.0.

In particular:

- capital allocation / leverage / position sizing are human decisions;
- DEMO account/risk scaffolding is not the real product;
- recorder is public read-only evidence collection;
- synthetic replay is not market evidence;
- professional trader intelligence is not implemented yet.

Remove or rewrite stale UI copy implying an accepted product-level `1x exposure cap`.

Do not change historical frozen contract names simply because some v1 DEMO types still contain old account/risk concepts.

## Theme

Use a deliberate premium dark theme as the default product experience.

A light theme is optional, not required for this task.

Do not rely solely on `prefers-color-scheme` to determine whether the primary product design looks intentional.

If theme switching is added, keep it simple and persistent; it is not required.

## Accessibility / usability

At minimum:

- keyboard-focus states must be visible;
- controls need accessible names;
- status must not rely on color alone;
- text contrast should remain reasonable;
- click targets should be comfortable;
- tables and controls should remain usable without pixel-perfect viewport assumptions.

## Functional preservation

The redesign must not break:

- synthetic replay controls;
- SSE run updates;
- run selection;
- recorder operations;
- dataset inspection/verification;
- manifest/artifact links;
- health visibility.

Do not alter backend domain behavior to fit a visual idea.

## Routing/state

The current hash-based navigation may be retained or cleaned up.

Deep links currently used by tests/flows should either remain compatible or be migrated deliberately with updated tests.

Refresh on a section/deep link should return to the appropriate view.

Do not add a routing framework solely for fashion if the existing needs can be satisfied simply.

## No fake trader

Absolutely do not:

- create a fake “live bullish/bearish” signal;
- invent confidence values;
- invent BTC prices;
- invent targets/stops;
- use the DEMO trader to populate the real Overview;
- imply that causal feed/state is already wired into the app;
- label synthetic output as real market analysis.

The Overview should look complete as a product surface while honestly stating which intelligence modules are pending.

## Suggested real Overview content available today

Use existing APIs where practical to show truthful readiness information, for example:

- system operational / degraded;
- run worker alive count;
- recorder worker alive count;
- historical dataset count;
- latest dataset source/coverage/quality;
- active/latest recorder session;
- evidence pipeline stage;
- real trader engine: `Not implemented`;
- real causal replay integration: `Pending WP-007`.

Avoid exposing internal WP numbers prominently to a future end user unless inside a secondary development/status detail.

## Tests

Update/add front-end/E2E tests to preserve behavior and cover the new shell.

At minimum verify:

- default landing page is Overview/Market;
- navigation reaches Replay, Data and Recorder;
- synthetic DEMO labeling remains obvious in Replay;
- replay start → run → controls still work;
- Data still lists/opens/verifies datasets;
- Recorder UI still starts/stops a session in offline E2E;
- Overview never presents synthetic output as real trader intelligence;
- key not-yet-implemented trader areas are clearly labeled;
- no critical horizontal overflow at a normal desktop viewport.

Do not weaken existing backend/domain tests.

## Visual validation

Before completion, inspect the rendered application in a browser at minimum around:

- 1440×900;
- 1920×1080;
- a narrower desktop/tablet-like width around 1024 px.

Use your frontend-design skill to do at least one refinement pass after seeing the rendered result.

Check:

- hierarchy;
- spacing;
- page width usage;
- navigation;
- readability;
- table overflow;
- empty states;
- DEMO vs REAL distinction;
- recorder state;
- Overview placeholder honesty.

If your environment supports screenshots, capture them for your own review and mention the reviewed viewport(s) in the completion report. Do not commit screenshot binaries unless specifically needed for a test.

## Acceptance criteria

WP-006 is complete only if:

1. the application has a coherent premium product shell, not the old tiny boxed/admin layout;
2. Overview/Market is the default landing experience;
3. the future professional trader information hierarchy is obvious without fake signals;
4. Replay is clearly a synthetic DEMO lab and all existing controls still work;
5. synthetic account/risk scaffolding is visually demoted from product prominence;
6. Data is a polished evidence workspace;
7. Recorder is a first-class polished operational view;
8. current functionality and owner observability are preserved;
9. stale 1x/account-product wording is removed from owner-facing UI;
10. responsive desktop layouts use available space well;
11. reusable front-end structure/design primitives replace the current monolithic styling where appropriate;
12. E2E behavior remains green;
13. web typecheck/build remain green;
14. all existing backend/unit/contract tests and compose smoke remain green;
15. no professional trading logic or fabricated signal is introduced.

## Prohibited changes

Do not:

- modify `source_notes/`;
- implement the professional trader;
- create `semantic.v2`;
- wire real feed/state into the trader/replay engine;
- implement market structure/indicators/levels;
- create real predictions, targets or recommendations;
- create autonomous account/leverage/sizing logic;
- add authenticated exchange connectivity;
- implement real order execution;
- rewrite backend architecture for UI convenience;
- weaken tests to accommodate the redesign.

## Git workflow

Before editing:

`git pull --ff-only origin main`

Then:

1. use the frontend-design skill;
2. inspect current UI;
3. implement the bounded redesign;
4. run required checks;
5. visually inspect and refine;
6. commit;
7. push normally to `main`.

No force-push, reset or shared-history rewrite.

## Completion report

Report:

- base/final SHA and branch;
- confirmation that the frontend-design skill was used;
- main information-architecture decisions;
- main visual/design-system decisions;
- files/components added/refactored;
- what each top-level destination now does;
- which Overview content is real today vs intentionally pending;
- behavior preserved;
- viewport(s) visually inspected;
- web/E2E/backend checks and exact results;
- GitHub Actions result;
- deviations/limitations.

Do not declare WP-006 accepted. Acceptance belongs to the Project & Research Director.
