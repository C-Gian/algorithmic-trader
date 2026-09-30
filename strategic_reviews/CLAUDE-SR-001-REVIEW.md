# ASTRA-SR-001 — Independent Architecture Review before the Real Trader

Status: **REVIEW SUBMITTED — for Director decision** (not project direction until accepted)
Responds to: `strategic_reviews/SR-001-PRE-REAL-TRADER-ARCHITECTURE.md`
Repository reviewed: `main` at `b47b3cb72dbc23bc02caf40de1451d9949cb962c` (WP-003 implementation `6b45728`)
Date: 2026-09-30

---

## 0. Summary

**Recommendation: REVISE, then GO.** Do not stop the project, and do not start WP-004 as currently written.

The foundations are sound: the three-layer separation of view, plan and decision; immutable evidence; distinct time fields; and deterministic durable replay. They should be kept. The problem is narrower but costly to reverse. The current engine is a *bar-indexed, single-observation, BTC-unit* loop. If real data is plugged into it first and perpetual accounting is fixed afterwards, three things get built twice: the journal record types, the artifacts and the UI. Meanwhile real-data runs would carry DEMO economics.

Core positions:

1. **Architecture.** Use a hybrid (option A3) with two separate clocks.
   - An *event clock* applies causally ordered source events to a single, centrally owned **observable market state**.
   - A *decision clock* invokes the trader at defined decision points. It receives an immutable **snapshot plus the events that arrived since its last decision**.
   - The trader never reads evidence, datasets or account internals directly.
2. **Freeze now:** the layer boundaries and the direction of dependencies between them, the three-time model, the event ordering key, the roles of each price series, position units and the conversion rules, instrument pinning, the "invalid never becomes valid" rule, and a replay/live *parity* principle.
3. **Do not freeze now:** the trader's cadence and horizons, the internal structure of MarketView and TradePlan, which data channels the trader consumes, cost numbers, risk budgets, how funding is interpreted, and schemas for future data families.
4. **`semantic.v2`: not now.** Keep `semantic.v1` frozen as the synthetic-shell baseline. Add two new, explicitly **provisional** contract namespaces, one for the causal feed and observable state and one for perpetual accounting. Freeze them at M3 exit, after mathematical validation. Introduce `semantic.v2`, covering the trader-facing MarketView, TradePlan and Decision, only together with the first real-trader specification.
5. **Resequence M3.** Specify and implement the *pure cores* first:
   - (a) perpetual ledger mathematics;
   - (b) the causal feed and the state reducer, including tie ordering and freshness;
   - then integrate both into the engine **once**, together with the execution simulator.

   Start **live public-data recording early**. Wall-clock evidence only accumulates prospectively.
6. **Four policy decisions** must be made by the Director (and Owner where noted) before implementation. Each has concrete options in §7 and §9:
   - how the 1x cap is measured, including shorts drifting above it;
   - the funding settlement boundary convention;
   - the fill-timing convention when availability is later than bar close;
   - the modeled availability delay.
7. **Knowledge gaps that genuinely block the first trader:**
   - an intraday multi-timeframe *playbook process* source;
   - a causal definition of *structure and levels*, needed for invalidation geometry;
   - venue documentation checks for funding, mark and fees. These matter for correctness, not alpha.

   Everything else can wait.

Uncertainty is preserved where the sources are silent or disagree (§8, §9).

---

## 1. Scope, evidence and reviewer disclosure

**What was read:** `FOUNDATION.md`, `STATE.md`, `AGENTS.md`, SR-001, the OKX source decision, both schema baselines, and the referenced code (`engine`, `contracts`, `trader`, `account`, `risk`, `synthetic`, `marketdata/{contracts,dataset,okx}`).

**Dossiers:**
- in full: LIB-004 (Carver), LIB-020 (Harris), LIB-001 (Johnson, partial source), LIB-019 (Hull), LIB-005 (Schwager/Coyle), LIB-012 (López de Prado);
- targeted sections: LIB-003 (Chan: point-in-time data, truncated-history test, paper/live reconciliation, stops) and LIB-008 (trend-filter equivalence).

**Clean-room note:** several dossiers contain interpretation passages written for a legacy project. They mention "Trading Bot", "System G2", `peso_base/peso2`, "G1 runtime" and fixed 15m cadences. **All such passages were ignored.** Only the dossiers' *source claims* are cited here. No legacy architecture, threshold or conclusion is used.

**Direct source checks done for this review** (public, read-only):
- `GET /api/v5/public/funding-rate?instId=BTC-USDT-SWAP` was sampled three times between 08:41 and 08:43 UTC on 2026-09-30.
- It exposes a *pre-settlement* `fundingRate` for the **next** settlement (`fundingTime` 16:00Z, `method=current_period`), which **changed between samples**: `0.0000256545…`, `0.0000256108…`, `0.0000260368…`.
- It also exposes `premium`, `nextFundingTime`, and the just-settled `settFundingRate` (`0.0000337200721784`, identical to the historical 08:00Z row in WP-003 data).
- The historical endpoint returns only settled events.
- This is an *observed* behaviour. The documented semantics of each field could not be retrieved automatically and must be confirmed (§8, V-1).

**Disclosure:** this review was written by the same assistant that implemented WP-002 and WP-003 in this workspace. The red-team findings on those packages (§9) are therefore partly self-review. The Director should weigh them with that in mind and check them independently.

---

## 2. Recommended architecture (SR-001 §A, request 1)

### 2.1 Layers and dependency direction

```
L0  Evidence            immutable source packages (algotrader.marketdata.v1)         — exists
L1  Causal feed         evidence/live source -> ordered AvailabilityEvents            — new
L2  Observable state    pure reducer: state' = apply(state, event); per-channel       — new
                        latest-valid values, bounded history, freshness, validity
L3  Trader              decision clock: (snapshot, events-since-last, own memory)     — interface revised
                        -> MarketView, TradePlans, ActionProposal (exposure intent)
L4  Risk                independent; pinned instrument; mark-valued exposure          — revised
L5  Execution sim       orders -> fills using ONLY later traded-price events          — revised
L6  Perp account        contract ledger; mark valuation; fees; funding cash flows     — replaced
```

Rules:

- **One-way dependency.** A layer reads only the published outputs of the layers below it. The trader never touches L0 datasets, the raw feed, or ledger internals. It receives an account *snapshot*, the same object that risk and the UI see.
- **One implementation of causality.** Ordering, freshness, missingness and completion status are computed once, in L1 and L2. Trader implementations must not re-derive them. This is the main reason to prefer the hybrid over a raw event stream (option A2).
- **Interpretation stays in L3.** L2 holds *observations and their quality*, never meanings. "Mark is 0.3% below index" can be an L2 *measurement* if it is defined purely arithmetically. "Therefore a squeeze is likely" is L3.
- **Same code, different clocks.** Historical replay, recorded-session replay and live paper operation differ only in the L1 adapter (dataset reader, recorded journal, wall-clock poller) and in the execution adapter. L2 to L6 are identical (Foundation §6).

### 2.2 Why A3 (hybrid) and not A1 or A2

| Option | Main failure mode for *this* product |
|---|---|
| A1 synchronized `MarketFrame` per decision | Forces all channels onto one timestamp grid. That invites forward-filling and flattening, hides per-channel freshness, and becomes the "flat feature row" the Foundation warns against. It also cannot represent sparse events such as funding without contortion. |
| A2 raw heterogeneous event stream straight to the trader | Correct, but every trader must re-implement buffering, ordering, staleness and completion handling. Causal correctness then depends on each trader's own bookkeeping, and the UI and risk need their own copies. Hard to audit and easy to leak. |
| **A3 event clock → state → snapshot to trader** | Causal logic lives in one place. The trader sees a consistent, typed, freshness-annotated state. Asynchrony is preserved because each channel carries its own times. |

**Refinement over the SR-001 wording:** give the trader **snapshot + delta** — the events that became available since its previous decision — not the snapshot alone. Professional reasoning is largely about *what changed* and *whether the market responded as expected* (LIB-005 §14.5 and §15.3). Reconstructing deltas by diffing snapshots is error-prone, so pass them explicitly.

### 2.3 Decision points

- The **event clock** advances on every availability event.
- The **decision clock** is a separate, declared policy, for example "after every completed 1m traded-price bar, once all events with the same availability time have been applied". Other policies can be added later: timers, or "on a funding settlement". The engine must support policy-defined decision points. It must **not** hard-wire "one step equals one 1m bar".
- The trader's own horizons (minutes to hours) are built by the trader or by an L2 aggregation service from 1m channels. Derived higher-timeframe bars must carry a **completion status**, the same discipline as OKX's `confirm`. A forming 15m or 1h bar is never presented as complete.

### 2.4 What the trader outputs

Keep the v1 separation: MarketView (interpretation), TradePlan (conditional plan), ActionProposal, then risk, then Decision. Change *what the proposal is denominated in*:

- the trader proposes **exposure intent**: direction plus a target fraction of the allowed exposure, or a target risk unit;
- **risk** converts that into contracts using the pinned instrument and the current mark (§6);
- the trader should never reason in contract counts.

This keeps the trader venue-agnostic and puts instrument arithmetic in one audited place.

---

## 3. Decisions to freeze now (request 2)

"Freeze" here means a principle that later work packages must satisfy. It does not mean a byte-level schema; see §4 for contracts.

| # | Freeze | Rationale |
|---|---|---|
| F1 | **Layer boundaries and one-way dependencies (§2.1).** The trader receives snapshot, delta, account snapshot and its own memory, and nothing else. | Protects causality and auditability. This is the Foundation's separation, made concrete. |
| F2 | **Three-time model on every record:** `event_time` (source), `available_time` (with an `availability_basis` of `modeled` or `recorded` and a policy id), `recorded_at`/`retrieved_at` (provenance). A decision's `information_cutoff` equals its decision time. **Nothing with `available_time > cutoff` may influence the decision.** | Already true in marketdata.v1. It must extend through the feed, state, trader, execution and account layers. |
| F3 | **A single deterministic ordering key for events** (§5.2). | Tie handling must be a property of the system, not of each module. |
| F4 | **Price roles (§5.1):** traded price for market reading and fills; mark for valuation, unrealized P&L and exposure; index as a reference and basis measurement; funding settlements as cash flows. **No silent substitution of one for another.** | Mixing roles is the most likely source of plausible but wrong economics. |
| F5 | **Units:** the ledger holds contracts. Exposure and risk are expressed as base-equivalent BTC valued at mark in the settlement currency (USDT). Conversions happen only through the pinned instrument. Every financial number is a `Decimal`, and every quantity names its unit. | Removes the v1 "signed BTC" ambiguity for good. |
| F6 | **Instrument pinning:** every run references a specific instrument snapshot by content hash. No code path reads "current" instrument metadata during a run. | Old runs cannot be rewritten by venue changes. |
| F7 | **Invalid and missing never become valid.** No forward-filled *observation* is ever created. A last valid value may be *carried* only with its age and source attached. | Already a principle in WP-003, extended to the state layer and the account. |
| F8 | **Replay/live parity.** A channel may feed the trader only if it can be reconstructed point-in-time historically, or has been recorded prospectively. A live-only signal stays out of trader inputs until a recorded archive of it exists. | Concrete case: the pre-settlement funding rate (§1, §9 R12). |
| F9 | **The hard exposure cap is checked on projected post-trade exposure at mark**, including pending orders. It is checked independently of what the trader claims to request. | The current check validates the *proposal's* fraction, not the resulting position (§9 R6). |

---

## 4. Decisions explicitly NOT to freeze yet (request 3)

- **Decision cadence and trader horizons.** These belong to the first trader specification (Foundation §6 already defers them).
- **The internal structure of MarketView**: horizon set, scenario fields, how confidence is represented, what "expected response" contains. These should come from the trader specification and from what must be *scoreable* (§9 R17), not from data plumbing.
- **The TradePlan trigger and invalidation language.** It depends on the unresolved structure/levels gap (§8).
- **Which channels the trader consumes.** Keep a *versioned channel registry*, not a closed enum. The first trader may legitimately ignore index and funding.
- **How funding is interpreted:** as a cost only, as a carry/crowding context, or as directional evidence. LIB-019's warning against reading derivative premia naively as directional forecasts argues for "cost/context only" by default. That should be a trader-specification decision, not an architecture one.
- **Cost and slippage numbers, fee tiers, latency values and risk budgets.** They should be parameters with required explicit values, stress-tested, and frozen by the Director only before evidentiary paper operation (Foundation §4).
- **Schemas for future data families** (open interest, trades, order book, spot).
- **Whether decisions can occur more often than once per minute.** The architecture must not preclude it, but nothing needs it now.
- **Liquidation and margin-mode modeling**, provided the continuous exposure policy (§7.3) makes liquidation provably unreachable.

---

## 5. Price roles, asynchrony and the deterministic causal model (SR-001 §C–§D, request 5)

### 5.1 Roles of the four OKX series

| Series | Observable state (L2) | Trader reasoning (L3) | Risk / account (L4, L6) | Execution (L5) |
|---|---|---|---|---|
| **Traded price (OHLC + volumes in 3 units)** | Yes, the primary market-reading channel | Yes: structure, trend, volatility, participation | Decision reference price for implementation shortfall only | **Yes, the only fill-price source** |
| **Mark price** | Yes | Only as a *measurement* (for example the mark–trade gap). No default directional meaning | **Yes: unrealized P&L, exposure, cap checks, funding position value** | No |
| **Index price** | Yes | Only as a measurement (for example premium versus index, a spot reference). Interpretation needs the knowledge gap in §8 closed | Reference only | No |
| **Funding settlement events** | Yes, as sparse events | Optional, as cost/carry context (see §4) | **Yes: cash flow at settlement** | No |
| **Pre-settlement funding estimate** (live only) | **Recorded only, not a trader input** until an archive exists (F8) | Later, if validated | Could inform *expected* carry cost later | No |

**Missing or stale values constrain *actions*, never erase the *view*.** The rules by role:

- **Mark stale or missing:** valuation becomes uncertain. Risk **blocks new exposure and increases**. **Reductions and exits remain allowed**, because they fill on traded prices. The account keeps the last valid mark with its age. If a fallback such as the traded close is ever allowed, it must be a named policy recorded on each valuation (`mark_basis = fallback:<policy>`), never a silent substitution. The current engine does exactly this silent substitution (§9 R4).
- **Traded price missing:** no fill is possible for that interval. Pending orders keep working until an expiry (§6.2). Views that depend on traded price become stale per component. Risk blocks entries.
- **Index missing:** nothing is blocked unless a trader rule explicitly depends on it. Such dependence is declared in the plan.
- **Funding event missing:** detection needs an expected-schedule model, and the schedule can change. Treat it as a *quality finding* for the account ledger. Do not interpolate a funding charge. Any run whose position spans a suspected missing settlement is marked economically degraded.

### 5.2 The event model and ordering key

Each availability event carries:
- `available_time`, `availability_basis` and `policy_id`;
- `event_time`;
- `channel` (a family plus an instrument or series id);
- `kind`: observation, quality, settlement or venue;
- a payload or a quality reason;
- `source_ref`: the dataset id plus a page or row reference, or a live-record reference.

Events are processed in order of the key:

1. `available_time`.
2. **Processing class** at equal `available_time`:
   1. **Settlement events.** Funding cash flows apply to the position *as it stood before any same-instant fill or decision* (see the convention below).
   2. **Observations and quality events**, in a fixed family rank: traded, mark, index, others. The rank only exists for determinism; per-channel state updates commute.
   3. **Execution resolution.** Pending orders whose fill-defining traded-price event is now available are filled.
   4. **Valuation**: mark-to-market using the mark channel.
   5. **Decision point(s)**, if the decision policy fires at this instant.
   6. **Risk, then order submission.** Submissions can only fill on *later* events.
3. `event_time`.
4. A stable source sequence (page and row order, or a live receipt sequence).

This matches the spirit of the current per-step ordering in `engine.py`. It generalizes it from "one bar" to heterogeneous events.

**Funding boundary convention (a decision needed now).** With a candle close and a funding settlement both at `T`, the order above makes the settlement apply to the position held *before* any decision taken at `T`. So an entry decided at `T` does not pay or receive funding at `T`, and an exit decided at `T` still does. OKX's actual snapshot semantics at the settlement instant were not verified (§8, V-1). Adopt this convention as a labeled policy, and **stress the alternative** in evaluation. Funding is small relative to minutes-to-hours price risk, but it is systematic for positions held across settlements.

### 5.3 Freshness and missingness

- Freshness belongs to each channel: it is the gap between decision time and the latest valid event's available time, set against the channel's expected cadence.
- States: `FRESH`, `LATE` (within a grace period), `STALE`, `MISSING`, `INVALID_ONLY` (a record exists but was rejected), and `NEVER_SEEN` (warm-up).
- Expected cadence and grace periods are per-channel configuration.
- **MarketView validity should be per component or per horizon, not one global flag**, so that a stale mark or index does not force the whole view stale (§9 R3).

### 5.4 Answers to the specific cases in SR-001 §D

| Case | Behaviour |
|---|---|
| Traded candle present, mark missing | View updates on traded price. Valuation uses the last valid mark with its age. Risk blocks new exposure and increases if the mark exceeds its staleness limit. Reductions and exits remain allowed. |
| Mark or index arrives later (live) | Recorded arrival time is used (`availability_basis=recorded`). A decision at `T` sees only what had arrived by `T`. Historical replay uses the modeled policy. The two bases are never mixed within one run without being declared. |
| Funding at the same instant as a candle close | The class ordering in §5.2: settlement, then observations, then execution, then valuation, then decision. |
| One channel stale, another fresh | Freshness per channel. Components that depend on the stale channel degrade; others stay valid. |
| Row marked `INVALID` or a conflicting duplicate | Emitted as a **quality event** (no values) so the state knows "slot invalid", which is not the same as "slot missing". Never an observation. |
| Candle `confirm=0` | Never a completed observation (already enforced in WP-003). Derived higher-timeframe bars carry the same completion flag. |

**Modeled availability delay.** The current policy says "available at bar close". That is optimistic: the confirmed bar is published at some unknown delay after close. Make it `available = close + δ`, with δ as an explicit policy parameter. Measure δ from live recording (§7.4). This interacts with fill timing: see §9 R9, one of the most important findings.

---

## 6. Minimum perpetual accounting and execution before trader evaluation (SR-001 §E–§F, request 6)

### 6.1 Accounting (linear USDT-settled BTC perpetual, no leverage amplification)

Notation from the pinned instrument: `ctVal` (0.01 BTC for this contract), `ctMult`, `lotSz`, `minSz`, `tickSz`, `settleCcy` (USDT).

- **Position:** a signed quantity in contracts, an integer multiple of `lotSz`, respecting `minSz`.
- **Base-equivalent exposure:** `base = contracts × ctVal × ctMult` (BTC).
- **Notional at mark:** `notional = |base| × mark` (USDT).
- **Average entry price:** weighted by base quantity. It is kept unrounded internally; rounding happens only at display or at the venue's precision where the venue defines one. The current code quantizes average entry at every fill, so drift accumulates (§9 R5).
- **Realized P&L on a reduction** (USDT): `(exit − entry) × closed_base × side_sign`.
- **Unrealized P&L** (USDT): `(mark − entry) × base × side_sign`.
- **Fees** (USDT): `|fill_price × base_filled| × fee_rate(liquidity_role)`. The fee rate is a **required run parameter**, drawn from a named fee scenario and never defaulted (§9 R8).
- **Funding** (USDT), at a settlement event, applied only when the position is non-zero under the §5.2 boundary rule: `cash = −side_sign × position_value × rate`. Positive rates mean longs pay.
  - *Which* price defines "position value", and *which* field is charged (`fundingRate` or `realizedRate`), must be confirmed from OKX documentation (V-1).
  - Record both fields. They were equal in all samples observed so far.
- **Cash balance** = initial collateral + realized P&L − fees + net funding.
- **Equity** = cash balance + unrealized P&L (mark-based).
- **Exposure fraction** = `notional_at_mark / equity`. This drives the cap check (F9, §7.3).
- **Instrument history:**
  - OKX public data provides only the *current* definition. The WP-003 snapshot is taken *at retrieval*, not at the historical market time.
  - The pin therefore has to be stated as "these parameters are assumed for the whole interval".
  - Add a cheap **consistency check**: if historical prices are off the pinned `tickSz` grid (or volumes off the `lotSz` grid), the assumption is falsified for that interval.
- **Liquidation and margin:** not modeled. This is acceptable only if §7.3 guarantees equity never approaches maintenance levels. Assert it as an invariant that runs fail on, not as a comment.

### 6.2 Execution (1m OHLC only)

What must exist before any trader is evaluated:

1. **Market orders only** for entries, reductions and exits. Plans that want a limit-style entry ("buy at level") are represented as *conditional triggers*. A trigger is evaluated on completed bars and becomes a market order at the next executable price. The model **never fills at a limit price inside a bar** (Foundation §6; LIB-003 on high/low false fills; LIB-020 and LIB-001 on non-fill and adverse selection).
2. **Timing:**
   - decision at `T` (the decision point);
   - order arrival at `T + latency`, with latency an explicit parameter;
   - the fill uses **the first traded-price reference whose event time is at or after arrival**, and never a price stamped before the decision (see §9 R9 for why "next bar open" breaks once δ > 0).
3. **A reported bracket, not a single point:**
   - **base:** the first executable open;
   - **pessimistic:** the adverse extreme of the fill bar (the high for buys, the low for sells);
   - **alternative:** the fill bar's close.

   Economic results are reported for all three. The base result is never reported alone.
4. **Costs:** fees plus a spread/slippage parameter in basis points, with stress multipliers such as ×2 and ×3. Record a **participation diagnostic** (order base quantity ÷ bar base volume) and flag trades whose participation is too high for a fixed-bps model to be credible (LIB-001 §10).
5. **Missing bar at fill time:** the order keeps working until an expiry measured in bars (a parameter), then is cancelled and recorded as a **non-fill**.
6. **Stops and invalidation:**
   - thesis invalidation is evaluated on completed bars and filled at the next executable price plus the gap;
   - a *resting* stop-market can be modeled on 1m bars. If a bar's adverse extreme crosses the stop, fill at the worse of the stop and the bar open, plus slippage. This is causal because the stop existed before the bar.
   - **If two resting exits are both touched in one bar**, take the adverse one first, and count such ambiguous bars as a diagnostic.
   - Stop prices do not cap losses through gaps (Foundation §4; LIB-003 §21).
7. **Implementation-shortfall record for every trade:** decision reference price, arrival reference, fill price, fees and funding. This lets evaluation separate forecast error from execution error (LIB-001 §9, LIB-020 §13).

**Can be deferred** until higher-fidelity data exists: passive limit orders, queue position, depth-based or non-linear impact, partial fills, latency distributions, the liquidation engine, cross/isolated margin, dynamic fee tiers, and reproducing OKX's mark-price formula.

---

## 7. Review of the proposed WP-004 → WP-005 sequence (SR-001 §G, request 7)

### 7.1 Problems with the current proposal

1. **WP-004 would be built on the wrong spine.** Today `Engine.step` means "one bar, one step". It embeds fills and accounting and asserts `bar_index == step`. Plugging real datasets into that loop means either:
   - bending the new event and state layer around BTC-unit account records, which WP-005 then tears out; or
   - rewriting the journal event kinds, artifacts, trace hashes and UI a second time in WP-005.
2. **"Avoid producing meaningful P&L" is hard to enforce.** A real-data run through the current account emits real-looking P&L computed on DEMO semantics (trade-close mark, BTC units, placeholder costs). Labels help, but they are not a structural guarantee.
3. **Contracts come after the plumbing in this order.** The feed events and the perpetual ledger records *are* the interface WP-004 would journal. Designing them after the journal exists inverts the dependency.

### 7.2 Recommended sequence

- **WP-004: specifications and pure cores (no engine integration).**
  - *4a, perpetual ledger mathematics.* Contract, base and notional conversions, average entry, realized and unrealized P&L, fees, funding, equity and the exposure fraction. Validated with hand-computed worked examples, property tests (for example: round trips conserve cash apart from costs, and funding signs are correct) and source-grounded examples.
  - *4b, causal feed and observable state.* Event model, ordering key, freshness and completion status, the quality-event path, and the channel registry. Validated with ordering and tie tests plus Chan's **truncated-history invariance test** (LIB-003 §9): decisions and state before time *t* must not change when data after *t* is removed.
  - Both ship as **provisional** versioned contracts (§8 of this review; §4 of SR-001).
  - These pieces are small, independent and cheap to verify. Most future errors would originate in them.
- **WP-005: engine integration.**
  - Replace fixture stepping with feed-driven decision points.
  - Plug in the execution simulator (§6.2 with the bracket), the new ledger and risk (F9, §7.3).
  - Keep durable, restartable real-dataset replay and show freshness in the UI.
  - Use only **non-intelligent test traders**: a null trader, and a *time-scripted* trader that trades at fixed timestamps. Their P&L is labeled **mechanical validation only**.
  - Keep the synthetic fixture as a regression source through the same new feed interface.
- **WP-006 (can overlap with WP-005 or start earlier): live public-data recording.**
  - A wall-clock adapter that *records* completed candles, mark and index candles, funding settlements **and** pre-settlement funding snapshots, together with actual arrival times.
  - No trading, no trader.
  - Purpose: measure δ, create the point-in-time archive that parity rule F8 requires, and start accumulating prospective evidence, which cannot be recovered retroactively.
  - Its first acceptance test is a replay/live reconciliation: identical pre-execution state for identical recorded inputs (Foundation §6; LIB-003 §17).
- **Also during M3, not blocking WP-004:** multi-dataset *series* catalogs spanning more than 31 days, with seam checks, so a development/evaluation split exists before a trader is specified.
- **Then:** the trader-design review and the first real-trader specification, which introduces `semantic.v2`.

### 7.3 Policy decisions needed before WP-004 or WP-005 (Director, and Owner where marked)

1. **How the 1x cap is measured (Owner confirmation advised).** "Exposure ≤ 1x equity" is ambiguous in three ways: mark versus entry valuation, whether pending orders are included, and at-entry versus continuous.
   - For shorts the difference is material. A short at exactly 1x after a +10% move has notional 1.1E against equity 0.9E, which is **≈1.22x**.
   - Options:
     - (a) a continuous hard cap that forces a reduction;
     - (b) an entry cap below 1x with headroom, plus a continuous hard limit.
   - Either option also closes off liquidation (§6.1).
2. **Funding boundary convention:** §5.2, plus a stress test of the alternative.
3. **The fill convention when δ > 0:** §6.2 item 2 and §9 R9.
4. **The initial value of δ and the latency parameter.** Set them conservatively until WP-006 has measured them.

---

## 8. `semantic.v1` / `v2` strategy (SR-001 §B, request 4)

**Assessment of v1.** Its *decision semantics* are good and worth carrying forward: observation, interpretation (MarketView and scenarios), conditional plan, proposal, independent risk, decision, order intent, order and fill. Its *market and economic semantics* are synthetic and must not propagate:

- `MarketObservation` has a single ambiguous `volume` and assumes one channel.
- `Order`, `Fill` and `Position` quantities are "signed BTC", and the unit exists only in code comments; the schema never says so.
- `AccountSnapshot.mark_price` is the last traded close. `funding` is the literal `NOT_MODELED`.
- `InstrumentIdentity` lacks `ctVal`, `ctValCcy` and settlement semantics.
- `DataQualityState` and `ViewValidity` are single global states.
- `RiskDecision` is expressed in BTC quantities.
- `Fill` has no fee rate or basis and no reference prices.
- `RunManifest.fixture` is an untyped dict.

**Cost comparison:**
- *Freezing v2 now* would bake guesses into the trader-facing contract: MarketView shape, horizon structure, plan triggers. None of these has a specification yet. Changing them later means v3 churn and migration.
- *Staying informal* (ad-hoc internal structures) is the real danger SR-001 identifies: real-data and execution assumptions harden silently without a schema, a version or a review.

**Recommendation: the middle path.**

1. `algotrader.semantic.v1` stays frozen and labeled as the **synthetic-shell baseline**. Its runs remain readable.
2. Introduce **two new namespaces now**, each with a checked-in schema, drift tests and a changelog, but with status **`PROVISIONAL`**. Breaking changes are allowed during M3, but each one needs a changelog entry and Director sign-off.
   - `algotrader.feed.v1`: AvailabilityEvent, the channel registry entry, QualityEvent, the ObservableState snapshot and delta, and channel freshness.
   - `algotrader.perp.v1`: InstrumentPin, contract Position, LedgerEntry (fill, fee, funding, realized), the valuation record, the order and fill records with reference prices, and the exposure measure.
3. **Freeze** feed.v1 and perp.v1 at M3 acceptance, after WP-004 validation and WP-005 integration.
4. Introduce **`algotrader.semantic.v2`** only with the first trader specification. It revises MarketView, TradePlan, ActionProposal (as exposure intent) and Decision, and *references* feed.v1 and perp.v1 records instead of redefining market or economic data. Make v2 **scoreable by construction**: structured expected-response and invalidation claims, plus per-component validity (§9 R17).

The marketdata.v1 evidence layer stays as it is. feed.v1 events reference its records through `source_ref`.

---

## 9. Red-team findings (request 9)

Findings are ordered by the risk they pose to the eventual professional trader or to evidence validity.

- **R9. Next-bar-open fills are only causal when availability delay δ = 0.**
  - With a realistic δ > 0, the decision happens at `close_t + δ`, but the "next bar open" price is stamped `close_t`, *before* the decision.
  - The fill then uses a price from a moment when the decision had not yet been made. That is optimistic lookahead in the execution layer, introduced by a convention that looks conservative.
  - Fix: the §6.2 timing rule (first executable price at or after arrival) and the bracket.
  - **High impact for short-horizon evaluation.**
- **R12. Live and historical funding information are asymmetric** (observed, §1).
  - In live operation the next settlement's rate is visible and evolving hours ahead. Historically only settled values exist.
  - A trader that uses the live estimate cannot be replayed faithfully. Rule F8 and WP-006 recording fix this.
  - The funding formula and method also changed during 2026 (per SR-001), so `method` and `formulaType` must travel with every funding event and may matter for interpretation.
- **R10. The instrument snapshot is taken at retrieval time, not at the historical market time.** WP-003 persists the *current* definition. Nothing proves it held for past intervals. Fix: §6.1 pin semantics plus the tick and lot grid consistency check.
- **R6. The exposure-cap check validates the proposal, not the resulting position.**
  - `risk.evaluate` checks `proposal.target_exposure_fraction ≤ 1`. It does not check post-rounding, post-fill notional at mark against equity, and it ignores the pending order's contribution.
  - Shorts can also drift above 1x through price moves (§7.3).
- **R4. Mark equals the last traded close (`engine.py` step 4).** This is exactly the silent role substitution F4 forbids. The same applies to risk sizing with `last_valid_close`.
- **R3. Data quality is one global status, and view validity is a single flag.** This conflicts with per-channel asynchrony and with the Foundation's rule that missing input must not erase the last valid view by component. It would force coarse "all stale" behaviour.
- **R1. Record identity is keyed by bar index** (`D{step:04d}`, `O{step}`, `F-O…`, the `bar_index == step` assertion). Real multi-channel data with gaps and different start times breaks bar-index identity. Identity should derive from decision time plus a sequence number.
- **R2. The trader receives one observation and keeps an opaque `dict` of state.** Nothing separates the trader's *interpretive memory* from *observable history*, so each trader could buffer raw data differently. With A3, L2 owns observable history and the trader state holds interpretation only (versioned and checkpointed).
- **R5. Hard-coded precision.**
  - Fill prices are quantized to `0.01` (the instrument tick is `0.1`).
  - Money is quantized to `1e-8` at every step.
  - Average entry is re-quantized at each fill, so rounding drift accumulates.

  Precision should come from the pinned instrument and venue rules, with rounding points documented.
- **R8. Cost defaults are embedded** (`DEFAULT_COSTS` 5/2 bps). Placeholders with defaults tend to become de facto assumptions. Real-data runs should *require* explicit named cost scenarios.
- **R11. Replay identity is tied to the acquisition package.** Accepted WP-003 semantics mean the same economic content can have several `dataset_id`s (different base URL or page size). Replay reproducibility should key on a **normalized-content hash** as well as the package id. Multi-package series need seam checks for overlaps and boundary duplicates.
- **R13. The semantic trace hash covers prose `reason` strings.** Rewording an explanation changes the trace even when the decision is identical. Consider a decision-core hash that excludes rendered explanations, consistent with the Foundation's "explanations rendered from structured evidence".
- **R14. The worker loop is replay-only.** The Foundation requires the same engine for live paper. The feed-source interface needs defining now (§2.1) so that live operation is not bolted on later.
- **R15. Foundation ambiguity: the 1x measure** (§7.3.1). This needs an explicit Foundation-level definition.
- **R16. Higher-timeframe context from 1m data needs completion discipline internally** (§2.3). Otherwise a forming 1h bar is a lookahead vector.
- **R17. v1 MarketView is barely scoreable.** Foundation §10 wants market views evaluated at scheduled timestamps, but bias plus qualitative confidence plus prose gives little to score. Not an M3 blocker, but semantic.v2 must include structured, falsifiable claims such as expected response, invalidation observable and horizon.
- **R18. Trend-family redundancy (LIB-008, LIB-004)** is not an M3 issue. It is noted so the channel and measurement design does not encourage many equivalent trend transforms to count as independent "confirmations" in L2. L2 exposes *measurements*; families and roles are an L3 concern.

---

## 10. Knowledge gaps that actually block the first trader (SR-001 §H, request 8)

### Must know before the first coherent trader

1. **K1: an intraday professional *process* source for a 24/7 derivative market.**
   - How a professional combines higher-timeframe context with lower-timeframe triggers, defines invalidation and time stops, and chooses NO_TRADE, at minutes-to-hours horizons.
   - LIB-005 gives cross-trader *priors*: roles of information, reaction-versus-expectation, regime dependence, bounded invalidation. It is equities and events oriented and was chosen with severe survivorship bias. It is not a playbook.
2. **K2: a causal definition of structure and levels** (swing structure, ranges, "location relative to causally identified levels").
   - TradePlan requires trigger and invalidation *geometry*, and the Foundation's market-state list includes location relative to levels. The corpus has no formal source (a registry gap).
   - Needed as soon as the first playbook uses levels, which is highly likely.
   - Retracement and extension ratios are **not** required for this.
3. **K3: venue-mechanics verification (V-1).** This comes from official documentation, not literature:
   - funding snapshot timing at settlement;
   - which field is charged (`fundingRate` or `realizedRate`) and the price defining "position value";
   - the settlement schedule and how changes to it are announced;
   - the mark-price definition, at the level needed to trust it as the valuation source;
   - fee schedule structure.

   These block *accounting correctness*, not alpha.

### Can be added later

- Interpreting funding and basis as crowding, carry or directional context. The default is cost-only until sourced (LIB-019's caution about premia).
- Liquidation mechanics and cascade dynamics. They need data the project does not have.
- Order flow and liquidity from trades or L2 data (LIB-020 and LIB-012 on interpreting flow structurally).
- BTC spot–perpetual interaction beyond index-as-reference.
- BTC intraday seasonality and liquidity by hour or weekday. Useful for cost and slippage calibration, but it can come from the project's own recorded data (WP-006).

### Not needed for the first trader

- Cyclical and temporal methodology.
- Retracement and extension formalization.
- Options, Greeks and implied volatility.
- Queue, market-making or HFT models.
- Broad additional literature collection.

---

## 11. Final recommendation (request 10)

**REVISE, then GO. Not STOP.**

- **Not STOP:** nothing found invalidates the Foundation, the product scope or the accepted work. The operational shell and the evidence layer are the right assets to build on.
- **Not GO as written:** WP-004 in its current form would couple real data to synthetic economics and to a bar-indexed spine. It would also build the journal and UI around records about to be replaced, and it would carry R9 (a fill-timing lookahead once δ > 0) into the first real-data runs.

**Conditions to proceed** (Director decisions, no code needed):

1. Accept or amend the layered A3 architecture and freeze principles F1–F9.
2. Accept or amend the contract strategy: v1 stays frozen, provisional feed.v1 and perp.v1 are introduced now, and v2 waits for the trader specification.
3. Resequence M3: pure cores (4a ledger, 4b feed and state), then integration (5), with live recording (6) starting early.
4. Decide the four policies in §7.3; the 1x measure needs Owner confirmation.
5. Commission the V-1 documentation check (funding, mark, fees) before WP-004a's funding and fee mathematics is accepted.
6. Record K1 and K2 as the only literature gaps that block the first trader. Start them in parallel with M3 so the trader specification is not delayed.

Where evidence is uncertain, this review has said so rather than inventing a precise rule:
- the funding snapshot semantics;
- the real availability delay δ;
- whether 1m bars are enough for the first playbook's execution;
- how funding should be interpreted.

These should be resolved by source documentation or recorded data, not by convention.