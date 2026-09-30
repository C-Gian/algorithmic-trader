> **HISTORICAL SCOPE NOTICE — 30 September 2026.** FOUNDATION.md v3.0 implements the Owner's direct clarification and supersedes inconsistent scope/workflow instructions below. This document is retained as historical/advisory evidence. Its former ACCEPTED/READY/HOLD status is not current authorization. In particular, the mandatory pullback-only path, blanket cycle/news deferrals and RP-001 closure gate are no longer project direction. Reuse compatible findings only through the current task; preserve original evidence and failed cases. See the current FOUNDATION.md, STATE.md and task.md.

# ASTRA SR-002 — First Professional Trader Design

**Independent strategic review · 30 September 2026 · Advisory, pending Director disposition**

Reviewed repository: [C-Gian/algorithmic-trader at `8003ddc15a50e7ca5d811374345ccda140bd6297`](https://github.com/C-Gian/algorithmic-trader/tree/8003ddc15a50e7ca5d811374345ccda140bd6297).

Authority: the current Owner instructions, Foundation v2.0, STATE.md and the accepted SR-001 Director disposition. The earlier account-management framing is superseded. This review does not carry forward its 1x rule, ledger prerequisites or autonomous risk responsibilities. Capital, size, leverage, collateral, orders and personal account risk remain entirely human decisions.

Reading basis: the current foundation/state/disposition, registry, SR-002 brief, marketdata/feed/recorder/observe contracts and the observable-state reducer; professional claims, methods and limitations across the twenty source dossiers, with detailed attention to the practitioner, combination, trend, execution and validation material. The optional `knowledge/PROFESSIONAL-MARKET-REASONING-SYNTHESIS.md` is absent at the reviewed commit. No legacy project architecture, experiments or conclusions are used. Source-dossier interpretations are not automatically current direction. This is a design review, not a code/test execution audit or a new empirical BTC study.

References such as [D05] identify pinned dossiers; [E1–E4] identify a small external primary-source refresh. References and their scope are recorded at the end. **Source-supported concept**, **proposed formalization**, and **empirically supported BTC behavior** are different evidence statuses throughout.

## 1. Executive decision

**Choose one initial professional process: read a directional move and its subsequent reaction, then recommend continuation only when a controlled pullback resolves with adequate location, invalidation and remaining room. Implement both long and short versions.**

The first analyst should continuously distinguish directional progression, correction, overlapping action and possible failure. Its first recommendation method should be narrower: **continuation after a pullback within an established intraday directional context**. Failed continuation remains an explicit alternative scenario and an exit/invalidation reason; it does not automatically become a reversal trade.

This is a tractable starting process because it connects context, changing behavior, location, timing, invalidation and destination. It is not selected because the corpus proves it profitable on BTC. The professional sources support conditional setups, preparation, response monitoring and separation of forecasts from actions. They do not supply an executable, validated BTC method. [D02–D05, D20]

A targeted external check supports studying the move–reaction–continuation process as an existing practitioner method. It also reveals important disagreement about how much independent predictive value ordinary support/resistance possesses. That disagreement should constrain our claims, not be resolved by declaring every visible level meaningful. [E1–E4]

**Disposition: GO for bounded formalization research and contract design; HOLD professional-rule implementation until the definitions and causal cases in §13 are accepted.** Introduce `semantic.v2` with that accepted first-trader specification. Do not reopen M3 wholesale, and do not add an account engine.

Freeze now: responsibility boundaries, causal evidence lineage, prediction/action separation, advisory lifecycle semantics, the first process's limited scope and the validation questions. Do not freeze undocumented swing thresholds, zone widths, timeouts or profitability claims merely to start coding.

## 2. What the first real trader should and should not be

It should be a **stateful price-action analyst with one selective recommendation method**, not a collection of independent strategies. It should answer:

1. What directional progress has actually occurred at the context and setup scales?
2. Is the current movement a continuation, a correction, or evidence that the prior structure is failing?
3. Which observable next response would discriminate those explanations?
4. Where could a continuation be entered without chasing, where would that local thesis be wrong, and what is the first defensible destination?
5. Is there enough room and time left for a human-actionable recommendation under stated cost assumptions?

Outside its recommendation domain, it must still publish its descriptive understanding, relevant levels, alternatives and uncertainty. “No supported continuation setup” must not be presented as “nothing will happen.” An emerging reversal may be the preferred interpretation while the recommendation remains NO_TRADE because reversal entries are not yet implemented.

Do not start with range fading, breakout chasing, news trading, liquidation prediction, cycle forecasts, passive execution tactics or a portfolio of playbooks. Do not pretend that omitting them makes their market effects disappear. The product should identify its price-based scope and explain when the cause of a move is unknown.

**Challenge to the mission framing:** formalizing professional knowledge still requires a testable predictive hypothesis. Existing professional practice does not remove the need to establish incremental information and net usefulness in this instrument and horizon. “We are not discovering a new theory” is a sound research constraint; “therefore the professional rules already have an edge here” is not. Long-horizon, diversified trend results do not validate minute/hour BTC continuation, and one institutional dossier specifically cautions against transferring fast-trend success across time. [D06–D11, D15]

The result is a first specialization within the eventual professional analyst—not a claim to have encoded an excellent trader in full.

## 3. Recommended reasoning architecture

Use a hybrid of **centrally derived causal observations, a typed dependency graph, hierarchical decision rules and small explicit state machines**. Numeric measurements are useful; a universal weighted conviction score is not required. No runtime LLM is involved.

| Stage | Question and admissible inputs | Output and dependency |
| --- | --- | --- |
| Evidence admissibility | Are the required time windows complete and sufficiently current? Use observable snapshots/deltas, source timing and coverage. | A dependency-specific usable/degraded/unavailable assessment. Unknown is not false or neutral. |
| Structural description | What progress, reversals and overlap occurred? Use completed bars, causal swings and descriptive measurements. | Horizon-specific facts with methods and confirmation times. No prediction yet. |
| Context interpretation | Does the progression support continuation, correction, overlap or transition? | MarketView claims with evidence and counterevidence; a context label is an interpretation, not hidden economic truth. |
| Move–reaction assessment | How does the pullback compare with the preceding directional leg in depth, speed, overlap and structural damage? | Candidate continuation thesis, specific competing failure thesis, and observations that would distinguish them. |
| Scenario commitment | What behavior is preferred or plausible next, conditional on what, by when? | Timestamped, scoreable scenario records independent of whether an entry exists. |
| Opportunity construction | Can location, trigger, local invalidation and destination be identified from current knowledge? | A conditional opportunity with immutable geometry revisions and readiness state. |
| Actionability | Is the trigger confirmed, entry still within bounds, destination not consumed, geometry acceptable, data adequate and cost/delay tolerance credible? | LONG/SHORT or explicit NO_TRADE reasons. No sizing. |
| Reassessment | Did subsequent price action produce the specified response, contradict it, or remain unresolved? | View/scenario/recommendation updates; no assumed human fill and no rewriting earlier forecasts. |

The graph records relationships such as *derived from*, *supports*, *contradicts*, *required by* and *blocks action*. It does not prove economic causation. Structured reason records should generate explanations; explanatory prose must not be an independent source of rules.

Rule outcomes should distinguish **satisfied, contradicted and unknown**. A strong-looking setup cannot compensate numerically for an unknown trigger or invalid dependency. Conversely, missing optional funding or index context must not veto a method that does not depend on it.

Use continuous depth, distance and speed measurements before categorical decisions. Use predeclared tolerance bands and explicit state transitions to prevent tiny changes from constantly relabeling the market. Hysteresis is a stability convention to test, not a license to ignore new contradictory evidence.

The core explanation should read approximately: “The larger intraday structure is rising. The current decline has not broken its reference low. A recovery through the local reaction boundary would support another test of the prior high; a break of the local pullback invalidation defeats this entry thesis. No entry yet.” This describes a conditional argument, not three bullish votes.

## 4. Professional lenses: include now / defer / reject

| Lens | Initial treatment | Distinct role and limitation |
| --- | --- | --- |
| Price structure and location | **Include** | Establish progression, pullback boundaries, obstacles and thesis geometry. A visible pivot is not automatically proven support/resistance. |
| Trend/persistence | **Include, structurally** | Describe the direction and durability of recent progression. Do not add moving-average, breakout and return signals as independent confirmations. |
| Momentum | **Include as move–reaction measurements** | Compare displacement per elapsed time and follow-through between impulse and reaction. Do not create an independent RSI/MACD voting module. |
| Volatility/range | **Include** | Establish scale, unusual expansion, measurement tolerance and whether stop/target geometry is overwhelmed by ordinary variation. It supplies no direction by itself. |
| Volume/participation | **Include descriptively; initially non-voting and non-gating** | Report venue-local activity during impulse/reaction against a trailing causal baseline. High volume is activity, not proof of aggressive buying, informed flow or global BTC participation. Promote a decision role only after a specific source-supported rule is formalized. |
| Multiple horizons | **Include three roles only** | Context, setup, trigger. The same price path at three scales is not three independent sources. |
| Time | **Include elapsed time, deadlines and response timing** | Tests whether the scenario behaves as expected. Predictive session seasonality is deferred. |
| Spread/liquidity/cost | **Include as qualified actionability/evaluation constraints** | State what cost and delay the opportunity can tolerate. Current candles do not measure depth or executable spread. |
| Mark/index/settled funding | **Retain as factual context; no directional rule initially** | Preserve price roles and available derivatives facts without making them mandatory confirmation. |
| Evolving funding, OI and liquidation flow | **Defer** | Require separate causal meanings and a specified decision role. Do not add them just because this is a perpetual. |
| Spot/cross-venue, macro/news | **Defer for this method** | They may explain moves or improve context later. The first product must say those causes were not analyzed. |
| Retracement | **Include measured depth and duration only** | Describe the correction relative to its own preceding leg; no privileged Fibonacci ratios. |
| Volume profile, VWAP bands, oscillator divergences, trendlines | **Defer** | Each introduces alternative level/confirmation definitions. None is necessary to finish this first process. |
| Predictive cycles, inferred stop hunts, institutional intent from candles | **Reject as initial rules** | Insufficient operational evidence; these cannot be promoted from evocative explanations to factual state. |

A measurement can serve two legitimate roles without constituting two confirmations. For example, the impulse's displacement can establish the setup and determine its scale. Record that shared dependency. Do not multiply confidence because trend, momentum and higher-timeframe direction share it. The trend-equivalence result in LIB-008 concerns a defined class of linear filters; it does not establish that every technical concept is mathematically identical. [D02, D04, D08]

Volatility should initially use one transparent trailing range scale, with its estimation window and missing-data requirements fixed before outcome evaluation. A robust trailing true-range summary is an adequate candidate; adding GARCH or several competing volatility estimators is unnecessary. Freeze scale at the creation of a geometry object so an expanding range cannot retrospectively widen its invalidation. Historical variability is not a calibrated future-movement interval, and target distance must not be advertised as expected return. [D04, D09, D19]

## 5. Multi-timeframe and temporal design

Use **completed 1-hour bars for context, completed 5-minute bars for setup structure, and completed 1-minute bars for trigger confirmation and prompt reassessment**. These are proposed engineering defaults for a human-facing minutes-to-hours process, not empirically optimal BTC periods or rules copied from the dossiers. Do not run a timeframe tournament.

The analyst needs both clock scales and structural horizons. A 5-minute bar is a sampling unit; a pullback is a price episode spanning an irregular number of bars; a 120-minute forecast is a prediction horizon. Keep all three distinct.

| Role | Initial purpose | Restriction |
| --- | --- | --- |
| 1h context | Locate the setup in an established intraday progression and identify nearby larger obstacles. | No daily/4h ensemble initially; insufficient context history yields unresolved context, not fabricated balance. |
| 5m setup | Identify the directional leg, reaction and reference boundaries. | Only completed constituent windows establish completed bars. |
| 1m trigger | Detect a predeclared local recovery/failure and manage recommendation age. | No sub-minute trigger, exact touch entry or retrospective intrabar path. |

Use UTC-aligned half-open aggregation windows. Alignment is a convention, not a BTC economic session. A 1h bar ending at 11:00 becomes available only when all required valid constituents have arrived; an early 10:59 delivery alone does not establish completeness. Delayed constituents delay the derived bar. Never sum partial volume or quietly bridge an absent minute and call the result complete.

Broader bearish context can coexist with an upward local reaction. Preserve both statements. In the first method, a long against an established bearish 1h context is **outside the entry scope**, even if a bounce is plausible. The analyst can then watch whether the bounce becomes a controlled rally offering a short continuation. Likewise, an upward 1h context plus a sharp downward 5m move is a conflict to investigate, not automatically a buy-the-dip signal. This is a scope decision for the first method, not a universal higher-timeframe veto.

For the initial evaluation specification, nominate **120 minutes after forecast issuance/conditional activation as the primary outcome horizon**, with a separately recorded earlier response checkpoint. An untriggered opportunity needs its own shorter setup-expiry deadline, and an entry recommendation needs a still shorter entry-validity deadline. The exact checkpoint and expiry values belong to the behavioral formalization in §13; they must be fixed there before P&L is viewed. Do not interpret 120 minutes as an estimated arrival time, or reset the clock on every snapshot.

A timer must expire an idea even if no fresh candle arrives. M3's observation replay advances on deliveries; the professional runtime therefore needs journaled evaluation timers in addition to source deliveries. Do not invent a source bar to advance time. At a common timestamp, apply the declared available evidence prefix and derived updates before evaluating due conditions; record the exact cursor as well as the timestamp. This means evidence admitted before the timer's recorded dispatch boundary, not every event later found to share that timestamp. Persist that boundary/order so live operation never waits for unknowable future arrivals and replay never inserts them retrospectively. Replay/live parity must include timer behavior and outages.

Reconsider the view on required new evidence, material contradiction and deadlines, not on every irrelevant mark or index delivery. Continuous maintenance means continuity of a truthful view, including its increasing age, not continual generation of a new forecast.

BTC's 24/7 clock removes any justification for importing an equity opening auction, overnight gap rule or mandatory daily reset. Session labels can initially be descriptive research slices. Predictive effects of regional hours, weekdays or scheduled announcements need their own point-in-time evidence before becoming gates.

## 6. Derived causal observation layer

Add a **versioned derived-observation layer between accepted observable state and professional interpretation**. It consumes state/deltas and maintains declared rolling state. The trader must not fetch raw datasets to circumvent bounded history.

| Derived object | Central calculation | Interpretation left to the trader |
| --- | --- | --- |
| Completed 5m/1h bars | OHLC aggregation, typed volume sums, exact constituent identities and coverage. | Whether the bar indicates strength or failure. |
| Returns, ranges, overlap and elapsed durations | Explicit formulas, denominator and time window; undefined values remain unavailable. | Whether movement is directional, corrective or unusually disorderly. |
| Trailing variability scale | One method using only earlier eligible bars; estimator/version and coverage retained. | Whether current geometry is suitable for the chosen method. |
| Swing candidates/confirmations and legs | A documented causal extraction procedure with separate extremum and confirmation times. | Trend, trend damage and support/resistance hypotheses. |
| Level/zone objects | Anchors, bounds, source scale, creation/version times and observed interactions. | Why the zone matters, whether a response supports a scenario, and whether to trade it. |
| Impulse/reaction measurements | Displacement, depth relative to impulse, duration, overlap and progress relative to frozen scale. | “Controlled correction” versus “opposing initiative.” |
| Venue participation | Base-volume or quote-turnover summaries with a causal comparator; retain units. | Whether activity is relevant to this thesis. No aggressor attribution. |
| Geometry measurements | Direction-aware distances from an entry interval to invalidation and first obstacle; cost-profile references. | Whether the resulting opportunity is acceptable. |

Do not centrally publish an opaque `trend_score` or `bullish_pressure` as if it were a fact. The descriptive sequence of higher confirmed highs/lows is reproducible; a claim that this sequence makes continuation preferable is a professional interpretation.

For this first method, structure, recovery triggers, invalidation and targets refer to **traded price**. Mark and index observations cannot satisfy those predicates or substitute for missing traded evidence. They remain separately named contextual references; settled funding remains a carry observation. Any later predicate using another price role must declare that role explicitly.

Every derived object needs identity/version, event interval, known-at time, dependency references, method/configuration, scale/units and coverage/validity. Its knowledge time cannot precede its last required input. Keep provisional, confirmed, amended and invalidated objects distinguishable.

The current reducer retains bounded **valid** observations; that history is not proof of contiguous coverage. Derived windows must check slot coverage and quality events, not merely count valid rows. Configure sufficient retained state for context, or build incremental summaries/checkpoints from causal deltas. Snapshot/UI history limits must not silently become the professional lookback or delete an active level's lineage.

Two accepted details require care:

- `Freshness.FRESH` currently depends on age since availability. A recently received old bar may still be too old for a recommendation. The professional dependency policy must also use `age_since_event_end`, coverage and the required horizon; never inherit inspection defaults as trading thresholds.
- The current feed admits at most one event per channel/slot; the recorder preserves post-completion changes raw. Do not claim generic causal revision handling already exists. The first trader should explicitly use first-completed recorded evidence, or introduce an accepted revision path before using corrections. Neither path may rewrite an already published opinion.

## 7. Market structure / levels design

**Explicit structure is necessary; a universal support/resistance engine is not.** The minimum is a causal sequence of swings/legs, the relevant impulse/pullback boundaries, and nearby previously observed obstacles. Start with horizontal reference areas. Defer diagonals, profile nodes, round-number hierarchies and many competing level generators.

Recommend a **directional-change swing extractor** as the reference candidate for the formalization study: track a running extremum and confirm it only after a reversal exceeding a declared distance measured against a previously available, frozen range scale. Use a deterministic minimum tick tolerance. This is a proposed measurement procedure—not a sourced BTC edge or an already accepted numerical rule. §13 must establish its scale, initialization, tie handling and ability to preserve the intended professional distinctions.

The running extremum remains provisional. Store both its market time and the later confirmation time. Never draw it on an earlier replay screen as a confirmed pivot. When a bar can both extend the extremum and cross the reversal threshold but OHLC cannot reveal order, do not infer a high-to-low path: postpone the confirmation or mark it ambiguous under one predeclared policy. Initialization and insufficient-history states must remain visible.

Use the resulting objects as follows:

1. **Create:** a confirmed contextual swing creates a candidate reference zone; its relevance and directional role are interpretations. A currently developing pullback extreme may define a provisional setup boundary without being mislabeled a confirmed swing.
2. **Bound:** use an anchor price and a small, deterministic tick/range tolerance fixed at creation. Zones represent measurement/location tolerance, not demonstrated depth or a probability distribution. A precise invalidation boundary can still be published against a zone.
3. **Observe:** record approach, penetration, close beyond, return and later displacement separately. A touch alone does not establish rejection; a wick is not proof of trapped traders.
4. **Update:** append observed interactions and explicit revisions. Never widen the zone retrospectively to preserve a winning narrative. Nearby objects may be displayed together while retaining their identities; avoid an adaptive merging algorithm initially.
5. **Weaken:** a failed expected response or persistent overlap can reduce this method's reliance on the zone. Do not assume repeated touches universally strengthen it or universally consume it; that is a source disagreement/empirical question.
6. **Invalidate:** a specified boundary/response violation invalidates the dependent thesis. Crossing resistance does not automatically turn it into proven support. A role change requires a new observed response and a new interpretation version.
7. **Age/retire:** retain original time and interactions; retire under a declared maximum relevance window or superseding structure. Data loss suspends assessment rather than pretending the zone held. A stale object can remain visible historically without remaining eligible for recommendations.

For initial targets, prefer the **nearest relevant previously observed opposing area**, often the preceding impulse extreme. If none exists in the supported history, say so and withhold this method's actionable recommendation; do not fabricate a distant target by applying a convenient reward multiple. Later extensions can study projected destinations separately.

The professional evidence is insufficient to freeze the exact swing/zone lifecycle today. The required research is a bounded translation study, not “find a better indicator.” Osler's FX evidence makes levels worth studying but is not BTC evidence; Grimes's skeptical comments show that practitioner authority does not establish a universal level effect. [E2–E4]

## 8. Scenario and prediction semantics

A scenario is **a timestamped, conditional, falsifiable claim about subsequent observable behavior**, not a paragraph that can be reinterpreted after the outcome.

For the initial process maintain a preferred continuation scenario when justified, a concrete failure alternative, and an unresolved/no-progress possibility. They need not always be exhaustive or assigned numeric weights. In overlapping action, no scenario need be preferred. “Unknown” is permitted; invented forecasts are not a requirement of continuous analysis.

Each scenario contains:

- its originating view and exact knowledge cutoff/cursor;
- applicable structural state and any activation condition;
- expected sequence/response and named destination or obstacle;
- forecast start rule, response checkpoint and terminal expiry;
- supporting evidence, contrary evidence and missing dependencies;
- explicit confirmation and disconfirmation predicates;
- a competing alternative and current qualitative preference;
- outcome-definition version and lifecycle history.

Distinguish **unconditional expectation now** from **expectation if a future trigger occurs**. A continuation scenario conditional on recovery above a boundary is not a forecast that recovery will occur. Failure to activate by expiry is `NOT_ACTIVATED`, not a successful prediction and not necessarily a failed post-activation prediction.

Do not count the trigger itself as the scenario's successful outcome. For an activated long continuation, an appropriate primary claim is that price reaches the named destination before the specified invalidation and before expiry. Subsequent failure is observable evidence against that version. If neither boundary resolves, label expiry/no resolution; if their order is unknowable, label ambiguity. A scenario can succeed while its recommendation was unusable, and a sensible recommendation can lose.

Separate direction at the horizon from path. Price can finish higher after first violating the thesis. Record terminal signed movement, barrier order, maximum excursions and time-to-resolution separately. Do not silently switch to whichever criterion makes the forecast correct.

Qualitative uncertainty should expose **evidence adequacy, scenario preference and material unresolved questions**, not an aggregate confidence number. Use descriptive states such as supported/contested/insufficient with rule-specific reasons. Do not publish “70% confidence,” normalized scenario weights or an A+ rating whose empirical meaning is unknown. Later probability calibration requires a fixed event, horizon, sampling policy and genuinely held-out reliability evidence.

View updates do not erase outstanding forecast records. A changed mind creates a revision linked to its predecessor; the original remains evaluable. Expected deadlines cannot be pushed forward repeatedly without recording that the earlier expectation expired.

## 9. Trade-decision and NO_TRADE semantics

**LONG/SHORT means this method currently supports a new directional entry under the published conditions. It never means an order was placed, a position exists, or the Owner should use a particular size.**

A pending bullish conditional plan should publish `NO_TRADE` with a visible `watch_direction=LONG` and the missing trigger. This avoids making “LONG if…” indistinguishable from an actionable LONG. After confirmation, a recommendation is valid only within its entry bounds and deadline; it is not a permanent instruction to chase the same thesis.

The reference long process is:

1. An established upward 1h progression is causally supported; a structural failure or missing context blocks this method.
2. A 5m upward leg has made meaningful progress relative to earlier known structure and local variability. “Meaningful” must be operationally defined in §13, not left to generated prose.
3. A subsequent reaction occurs. Its measured depth, duration and damage are compatible with correction rather than a demonstrated opposing structural break. Strong counterevidence produces a contested view and no entry.
4. Before the trigger, identify a local recovery boundary, the pullback invalidation, an acceptable entry interval and the first opposing destination. No destination or inadequate room means no actionable setup.
5. A later completed 1m observation confirms recovery through the declared boundary. Recheck the actual currently known location, expiry and geometry: confirmation may arrive too late to remain attractive.
6. Publish LONG only if required evidence is usable, this entry is still permitted, the local failure condition is intact and cost/delay constraints are met under the declared model.

The short process mirrors price relations and signed movement, but long and short outcomes must be evaluated separately; symmetry of syntax does not prove symmetry of market behavior.

For a first trigger formalization, prefer **a completed 1m close through a predeclared local pullback boundary**, rather than a touch or a predicted reversal. One bounded candidate is the relevant completed 5m countertrend bar's boundary identified while arming. Which bar legitimately represents that recovery threshold must be resolved by the causal case study. Do not select the best boundary after the breakout. Arming and confirming cannot be backdated into the same completed bar merely because its high/low contains both events.

All actionability gates are typed requirements, not weights. Record all applicable blockers plus a primary display reason; hard data failures take display precedence over geometry issues, without implying those other issues disappeared.

| Public NO_TRADE reason | Meaning |
| --- | --- |
| `WARMUP_OR_REQUIRED_DATA_UNAVAILABLE` | The selected inference cannot yet be supported. |
| `NO_SUPPORTED_SETUP` | No opportunity in this method's domain; not proof that the market has no edge. |
| `CONTEXT_OUTSIDE_METHOD` | For example, a countertrend entry against the established context. |
| `SCENARIOS_CONTESTED` | Required evidence does not discriminate the relevant alternatives sufficiently. |
| `TRIGGER_PENDING` | A conditional plan exists but is not confirmed. |
| `ENTRY_LOCATION_LOST` | Price has already moved outside the acceptable entry band. |
| `INSUFFICIENT_ROOM_OR_GEOMETRY` | The first destination is too close relative to local invalidation/noise. |
| `COST_OR_DELAY_VIABILITY_UNRESOLVED` | An actionable claim cannot be supported under the available cost/delay evidence. |
| `COST_OR_DELAY_DOMINATES` | Declared assumptions consume the available opportunity. |
| `MOVEMENT_OUTSIDE_SUPPORTED_SCALE` | The model's variability/response assumptions are no longer suitable. This is not a measured liquidity claim. |
| `EXPIRED_OR_INVALIDATED` | This opportunity is over, even if the broader directional view remains. |
| `EXISTING_THESIS_NO_NEW_ENTRY` | An existing recommendation is being tracked, but no new entry is offered. |

Keep lower-level predicate failures internally inspectable. Do not use `NO_EDGE` as a synonym for balanced price action or insufficient evidence. Maintain a separate market bias/scenario preference beside the recommendation.

Geometry is necessary but cannot establish positive expectancy. Report conservative room after assumed costs, distance to invalidation and their ratio. Do not select a universal 2:1 hurdle from folklore. The first method needs a declared acceptance floor, chosen with its source/case rationale before outcome testing; sensitivity then tests dependence on that choice rather than searching for the winning threshold.

## 10. Trigger / invalidation / target / lifecycle semantics

| Concept | Required meaning |
| --- | --- |
| Trigger | A predicate over future causally available observations, with price role, comparator, observation cadence and validity window. Confirmation has both market and knowledge times. |
| Entry interval | Prices for which this recommendation's geometry remains acceptable. It is neither a promised fill nor an order type. |
| Thesis invalidation | An observable condition that defeats the local reasoning, such as loss of the pullback boundary. It may differ from failure of the broader trend. |
| Protective exit guidance | A separately stated price/time/behavior boundary at which someone following the idea should consider the thesis no longer suitable to hold. It is advice, not a submitted stop or a loss guarantee. |
| Target | A named destination/area expected or relevant under the scenario, including its provenance and horizon. A barrier being touched does not prove an executable exit. |
| Profit-taking | An optional recommendation response to reaching a target. The first version should report completion at its primary target; defer partial-allocation percentages and multi-target ladders. |
| Time expiry | Ends the claim's original opportunity/forecast window; it does not erase it or assert that the opposite view is true. |
| View change | New evidence changes the interpretation. This may happen without invalidating a local recommendation, or after its entry window closed. Record the relationship explicitly. |

Prefer one primary target and one local invalidation initially. The preceding impulse extreme is a plausible first destination, subject to a nearer pre-existing opposing area. An ambitious second target is not a substitute for inadequate room to the first obstacle.

Freeze the active recommendation's geometry at issuance. A new pullback extreme before entry can invalidate/revise a candidate, but cannot silently widen the bounds of an already active recommendation. Initially, do not add discretionary trailing or repeated re-entry. A new entry requires a genuinely new qualified setup with a new ID, linked to the same episode if relevant.

Use **two lifecycle dimensions**:

- **Opportunity/entry:** WATCHING → ARMED → CONFIRMED/OPEN_FOR_ENTRY → CLOSED_TO_ENTRY, or EXPIRED/INVALIDATED. These describe recommendation availability.
- **Thesis assessment:** TRACKING → TARGET_REACHED, INVALIDATED, EXPIRED_UNRESOLVED, or UNASSESSABLE. Tracking begins at the specified scenario activation/recommendation reference, not at an inferred human fill.

An entry window can close while its thesis continues to be tracked. Public new-entry action then becomes NO_TRADE, while an advisory update can say “thesis remains intact” or “EXIT guidance if following this idea.” HOLD must mean continuing the recommendation thesis; it must never assert that the Owner has a position. The first release need not offer TAKE_PARTIAL/REDUCE: useful later guidance can identify an area to consider taking profit without choosing a fraction, but it adds evaluation choices that are unnecessary initially.

Issue at most one primary active actionable thesis per instrument in the first release, while retaining alternative scenarios. This is a presentation/research constraint, not one-net-position accounting. An opposite candidate first withdraws the incompatible entry recommendation; it is not an automatic account reversal. If both directions appear equally admissible, abstain and expose the conflict.

**Illustrative invented episode, not a current BTC recommendation:** the causal context is upward; the pullback recovery boundary is 100,000 USDT, local invalidation 99,700, and first target area begins at 100,650. A declared acceptable entry band is 100,000–100,050. Before a later confirmation the action is NO_TRADE/TRIGGER_PENDING. After confirmation within that band, conservative gross room is 600 and distance to invalidation is up to 350; the configured cost/geometry policy still decides eligibility. If confirmation is only known once the observed location has reached 100,500, the bullish scenario may remain intact but a new LONG is withheld. If the invalidation is then observed, the local thesis fails even if the 1h trend remains upward. No part of this example assumes the Owner traded.

If the next available candle contains both target and invalidation and their order matters, the outcome is ambiguous. Do not choose target-first, imply a safe stop fill, or score a correct direction as a successful trade.

## 11. Proposed `semantic.v2` shape

Introduce a clean advisory contract namespace with the first accepted professional specification. Do not mutate v1 or carry over its account/action coupling. v2 should reuse accepted evidence references without embedding raw source datasets or operational replay controls.

| Public object | Minimum content |
| --- | --- |
| Common envelope | Object ID/revision, instrument and price role, event interval, published/known-at time, exact input cutoff and cursor, snapshot/dependency refs, schema/model/config versions, validity and limitations. |
| DerivedObservationRef | Method/version, input lineage, covered interval, confirmation time, units, provisional/confirmed status and coverage. Detailed values may reside in a separate versioned derived-observation artifact. |
| HorizonState | Sampling scale, structural episode references, descriptive state, interpretation, evidence/counterevidence and age. Sampling scale is distinct from forecast horizon. |
| MarketView | Horizon states, relevant levels, preferred/competing scenarios, evidence adequacy, uncertainty, scope and material changes. No mandatory directional opinion when unsupported. |
| Level/Zone | Price role, bounds/anchor, origin/confirmation times, source horizon, method version, interactions, status and revision lineage. |
| Scenario | Applicability/activation, expected behavior, destination, start/deadline, confirmation/disconfirmation, alternatives, evidence and outcome-definition reference. |
| Opportunity | Scenario link, direction, readiness, trigger, entry interval, local invalidation, primary target, expected horizon/deadlines, geometry and actionability assessment. |
| Recommendation | LONG/SHORT/NO_TRADE, opportunity ref if any, reasons, issue/entry-validity times, new-entry eligibility and thesis-tracking status. |
| AdvisoryUpdate | Prior version, what changed, new evidence, affected predicates, entry withdrawal or thesis-management guidance, effective knowledge time. |
| Uncertainty/Blocker | Type, affected claim/action, dependency, consequence and what evidence could resolve it. Not a generic confidence float. |

Conditions need **typed executable semantics plus a human explanation**: a named/versioned predicate, its operands and price role, observation resolution, confirmation rule and deadline. Do not use free-text strings as the sole machine-readable trigger, target or invalidation. A small finite predicate catalog is preferable to designing a universal trading language.

The public record should explain why it says NO_TRADE without requiring an internal trace dump. Conversely, the trace must be sufficient to reconstruct which dependency blocked action. IDs and explicit relationships matter more than long generated narratives.

**Must not appear as required trader fields:** account balance/equity, budget, quantity/contracts, target position fraction, leverage, margin/collateral, portfolio exposure, capital-loss limits, liquidation levels for the Owner, order intents/orders/fills or an inferred human position. No frozen demo 1x policy. Instrument metadata references can support price precision and normalized evaluation without becoming a sizing recommendation.

Keep recommendation evaluation outcomes and hypothetical fill assumptions in a separate evaluation contract, linked to immutable recommendation versions. Runtime status, worker health and source-recorder lifecycle remain in their accepted operational namespaces.

Freeze the envelope, roles and distinctions after Director disposition. Freeze the first predicate vocabulary and concrete v2 schema only after the targeted formalization closes. Future models can change interpretation payloads with explicit versions; do not freeze an exhaustive ontology of professional trading now.

## 12. Required data additions, if any

**No new directional data family is a prerequisite for the first price-based process.** The accepted traded 1m evidence can support causal higher-timeframe bars, structure, behavior and provisional recommendation research, provided the coverage/history requirements are met. Mark/index/funding stay available in their proper factual roles.

That does not mean current evidence is sufficient for all economic claims:

| Need | Minimum next evidence | Gate |
| --- | --- | --- |
| Multi-hour context and warmup | Adequate contiguous causal traded history, with gaps and recorder outages distinguished. | Required before a valid context-dependent opinion; longer retention/composition is an infrastructure need, not a new alpha feed. |
| Entry practicality for a human | Explicit decision-to-display/action delay assumptions; prospective observations of recommendation age and available price when acted upon in the harness. | Required for human-actionability validation. Immediate agent execution is the wrong reference. |
| Spread and timely price | A small prospective public best-bid/ask and associated receipt-time sample if candle-cost bounds cannot decide viability. | Required before claiming narrow/rapid entries are demonstrably executable; not required to formalize the analyst or run coarse labeled research. |
| Trade-outcome costs | Declared fee and slippage/spread ranges; appropriate funding information if the evaluation hold crosses assessment. | Required for net-usefulness claims, with uncertainty retained. No personal fee-tier or account integration required. |
| Intrabar sequencing | Finer trade/quote evidence for cases whose recommendation outcome remains materially ambiguous. | Required only if ambiguity prevents a defensible conclusion; never reconstructed from OHLC. |

A prospective quote sample cannot retroactively establish historical spreads. Any historical cost envelope remains an assumption with sensitivity bounds. Without sufficient evidence, publish cost viability as conditional/unresolved, not “liquid enough” inferred from candle volume.

**Derivatives choices:** settled funding is past carry evidence; evolving funding is a distinct as-known estimate. Neither becomes a contrarian directional signal by default. Mark–index and traded–index comparisons require compatible intervals and explicit timestamp skew; a stale index can create a false premium. None of these comparisons is essential to the selected first method, so defer predictive formalization. OI does not identify who is right; liquidation feeds need coverage and semantics verification. Do not add them now. [D19–D20]

For later normalized economic evaluation, funding can affect a hypothetical trade without any account ledger. If actual rate/assessment applicability cannot be established, report a cost interval or an unresolved outcome. Do not charge a later realized rate as if it had been known when recommending entry.

## 13. Required targeted research before coding

Rank work by **dependency**, not an importance score. Use one compact concept/case specification and its evidence, rather than a new governance document for each question. External additions must be registered separately; original dossiers remain unchanged.

| Dependency | Narrow question | Required result / closure condition |
| --- | --- | --- |
| **A — process translation** | What distinguishes a continuation-supporting reaction from an opposing move or indecisive overlap in the selected professional method? | Translate the move–reaction process from the relevant LIB-005 interviews and targeted Grimes material into observable claims, counterexamples and explicit scope exclusions. Distinguish source statements from our BTC adaptation. No appeal to unobservable “strong hands.” |
| **B — structure and levels, after A** | Can one causal swing/zone procedure preserve those distinctions without hindsight or adaptive zone rescue? | Specify directional-change confirmation, scale freezing, initialization, ambiguous OHLC handling, zone lifecycle and precise local invalidation. Replay annotated prefixes through successful, failed and indeterminate examples. If the same visible prefix cannot be labeled consistently, revise or narrow the concept before implementation. |
| **C — complete advisory policy, after A/B** | Exactly when is a setup armed, a trigger confirmed, entry too late, expected response absent, or the thesis complete? | Lock one trigger construction, entry-band rule, geometry floor, target-selection precedence, response checkpoint, setup/entry/forecast deadlines and re-entry policy. Every required predicate must have a positive, negative and unknown case. No executor discretion to invent trading semantics. |
| **D — actionability evidence, informed by C** | Does the anticipated room survive plausible human delay and normalized costs, and what evidence would resolve uncertainty? | A compact declared delay/cost envelope and examples of viable, nonviable and unresolved geometry. Decide whether quotes are necessary. No account capital or leverage inputs. |
| **E — evaluation registration, after C/D** | What exact observations would support, falsify or leave unresolved the process's informational and economic claims? | Freeze forecast/opportunity episodes, denominators, labels, primary metrics, baselines, period partitions, uncertainty treatment and stopping rule before outcome-led iteration. |

A and bounded data-feasibility work can proceed without waiting for every later definition. B precedes professional feature coding; C precedes recommendation coding and final v2 predicate freezing; D precedes claims of actionable net usefulness; E precedes evaluation used to select direction.

The external refresh in this review is a starting source pointer, not completion of A/B. Read only the original material needed to resolve the chosen predicates and examples. Do not turn the study into a catalogue of all Grimes patterns, all support/resistance methods or all BTC microstructure theories.

Create a small outcome-masked translation set spanning clear continuation, false recovery, deep reversal, overlapping action, late entry, near obstacle, boundary ambiguity and missing evidence, with both directions represented. The Director should independently label the visible prefixes before seeing the proposed rule output. Disagreements need documented reasons; an LLM or the author of the rule cannot be its sole professional-fidelity oracle. Where expert judgment is unavailable, label the result an internally coherent approximation, not verified reproduction of professional expertise.

Numerical values unsupported by sources must be identified as **design conventions** and selected for stable behavioral distinctions on this development set. Do not search hundreds of thresholds to maximize later trade outcomes. If several plausible definitions remain, retain only a small predeclared contrast and record the choice and its uncertainty.

## 14. Validation and falsification plan

Separate four claims: causal correctness, professional-process fidelity, forecast information and recommendation usefulness. Passing one does not establish another.

### A. Causality and behavioral fidelity

Require prefix invariance by knowledge cutoff/cursor, replay-speed/restart equality, deterministic timer expiry, and complete input lineage for each derived object and claim. Test late constituent arrival, stale-but-recently-received data, missing interior minutes, recorded outages, simultaneous boundaries and an extremum that is not yet confirmed. A future suffix must not change prior meanings; acquisition IDs or whole-run metadata may differ and should not be confused with prediction changes.

Use adversarial cases that break the intended process: a nominal bullish pattern directly below an obstacle; an impulsive countertrend move mislabeled a pullback; trigger and invalidation inside one candle; a delayed confirmation after the entry interval has passed; a disappearing feed at expiry. Require the intended abstention/uncertainty, not a manufactured precise decision.

Behavioral review is conducted on masked prefixes. Track agreement/disagreement and concept ambiguity, not only attractive chart examples. Synthetic cases can prove predicate mechanics; they cannot prove professional quality or BTC edge.

### B. MarketView and scenario information

Evaluate a fixed audit sample of views—for example every completed 5m setup interval—including NO_TRADE periods and states outside the playbook. Do not sample only at recommendation triggers. Freeze the audit cadence separately from runtime update cadence.

Score issued unconditional direction/path expectations and activated conditional scenarios separately. Preserve `NO_PREFERRED_SCENARIO`, `NOT_ACTIVATED`, expiry, data loss and ambiguous outcomes. Report coverage of informative claims; an analyst that says nothing cannot win by avoiding errors.

For the primary 120-minute specification, report direction/terminal movement, destination-before-invalidation frequency, time-to-resolution and adverse/favorable excursions as distinct outputs. Comparators should include a simple persistence forecast and an unconditional/base-rate reference on the same eligible information set. These are controls for the whole process, not a signal competition.

Qualitative labels can be checked for outcome ordering and coverage. Do not score uncalibrated labels with probability scoring rules. If probabilities are introduced later, define the event universe first, then use held-out reliability curves and proper scores; simple accuracy is insufficient.

### C. Recommendation-level usefulness

The primary unit is a **unique opportunity episode**, not every minute that its recommendation persists. Revisions remain linked; repeated retries in one pullback remain dependent. Preserve the full candidate funnel: detected, armed, triggered, blocked, recommended and expired. The outcome of an absent human trade is never treated as observed account P&L.

Specify a separate normalized reference policy for evaluation: entry only after the recommendation becomes known plus a declared human-response delay, only within the entry interval, followed by the predeclared invalidation/target/expiry rules. With candles, an eligible subsequent open is a coarse reference—not proof of an executable quote. Missed entries stay missed; never use the earlier trigger price as a fictional fill. Report a small fixed range of plausible delays, not the best one for each trade.

Measure net directional return in basis points, gross/net room consumed, excursion, resolution time, target/invalidation ordering, missed-entry frequency and ambiguity/censoring. Optional R-like normalization uses the original entry-to-invalidation distance as an analytical denominator; it neither prescribes capital risk nor bounds the realized loss. No leveraged returns, compounded account-growth leaderboard or assumed sizing policy.

Determine whether NO_TRADE improves selectivity by comparing recommended episodes with the **predefined eligible candidate universe** and a controlled version that omits one actionable gate. Include missed useful opportunities as well as avoided bad ones. Do not mark every profitable later move during NO_TRADE a mistake, and do not invent a perfect retrospective entry for rejected candidates. An always-NO_TRADE policy fails coverage/usefulness objectives even if it loses no hypothetical money.

Cost sensitivity and ambiguous intrabar paths must be visible. Report both admissible outcome bounds where feasible, plus the unresolved fraction; dropping ambiguous or data-loss episodes would bias results. A target touch is not a guaranteed exit, and a protective boundary is not a guaranteed execution price.

### D. Development, protected evaluation and prospective evidence

Use chronological development periods, then one untouched later evaluation period and subsequent prospective advisory observation. Within development, walk-forward checks can assess stability, but no automatic rolling optimization is required. Split labels by their full outcome intervals: purge overlaps with protected periods, declare any embargo, and preserve causally available past warmup. A 1h context shared by adjacent observations is not independent evidence.

Keep every material source/formalization/policy trial, including failed ideas. Once results influence redesign, that interval becomes development evidence. Do not keep reopening the same “holdout.” Source disagreements about permissible refinement are handled by this separation: reasoned development is allowed; recycled tests are not independent. [D03–D04, D12–D13, D16–D18]

Predeclare a small set of **role-level ablations**, such as removing context restriction, removing location/room screening, or replacing response-sensitive timing with a fixed entry convention. Keep downstream definitions and denominators coherent. If a role has no measurable contribution, simplify; do not promote its isolated backtest performance to a new strategy. Descriptive volume needs no profitability test while it has no decision role.

Assess long/short, variability, time-of-week and trending/overlapping slices with recorded sample sizes and dependence-aware uncertainty. Define live-usable strata causally; hindsight regime labels may be diagnostic only. Use episode/day or longer blocks as dependence requires, not IID confidence intervals over overlapping minute forecasts. Rare cases may remain inconclusive.

Prospective observation must preserve every issued view, timestamp, entry window and withdrawal before outcomes are known. Replay the same recorded stream and compare meanings. Test the Owner-facing latency budget through the harness without requiring the Owner to place trades.

### E. Falsification and stopping

Before evaluation, fix the observation horizon and review date or episode-collection target, primary metric and materiality criterion. Do not sample until significance appears. Stop a research iteration to repair causality/semantic defects; do not patch the trading method after one loss.

Reject or narrow the current candidate if any of the following persists under the registered evaluation:

- its professional distinctions cannot be reproduced consistently from causal prefixes;
- it adds no demonstrable information beyond the declared simple references;
- claimed entry usefulness disappears under plausible human delay/costs or depends on favorable ambiguous paths;
- the abstention policy only achieves attractive results by near-zero coverage or excluding difficult outcomes;
- small reasonable changes in bar alignment, measurement tolerance or availability cause qualitatively incompatible recommendations;
- apparent usefulness is concentrated in an unexplained narrow slice with no supported operating-domain claim.

Insufficient evidence is a third outcome, not automatic approval or proof of no effect. DSR/PBO can be relevant to a suitable recorded selection process, but are not required badges for this single initial specification and do not repair causality or execution errors. Do not transplant the dossiers' numerical significance thresholds. [D13, D16–D18]

## 15. Failure modes / red-team objections

| Objection | Review judgment and consequence |
| --- | --- |
| “This is still a hand-written technical strategy.” | It is. The distinction is a source-grounded, falsifiable integrated reasoning process—not sophistication of its name. If it lacks information or usefulness, reject it rather than add decorative lenses. |
| “The selected pullback process was chosen because candles are available.” | Partly an intentional scope/data fit, but not sufficient justification. Translation research must establish professional coherence. If essential distinctions require unavailable data, obtain that evidence or withdraw those claims rather than fake them. |
| “Many successful professionals rely on catalysts.” | Correct. The first version is not those professionals' full process. Do not copy their breakout rules while stripping out the catalyst and then attribute the resulting method to them. |
| “One-minute data loses decisive paths.” | Correct. Intrabar pivots, recovery/failure order and touch fills can be unknowable. Delay/ambiguity rules are necessary; finer evidence becomes mandatory when that uncertainty controls the conclusion. |
| “Aggregated higher-timeframe bars solve the problem.” | They preserve OHLC/volume for complete aligned windows, not hidden order flow or intrabar sequence. Late/missing constituents and alignment sensitivity remain. |
| “Determinism makes a professional trader brittle.” | Determinism aids auditability; rigid poorly chosen predicates cause brittleness. Use graded measurements, explicit unknown states, stability tests and narrow domain limits. Do not secretly add discretionary overrides. |
| “Scenarios explain everything after the fact.” | Prevented only by frozen predicates, time-bounded claims, immutable versions and scoring the original expectation. A library of scenarios without committed expectations is storytelling. |
| “Support/resistance is subjective.” | The extraction can be reproducible while predictive meaning remains uncertain. Use reference areas first; investigate their response rather than asserting latent liquidity. |
| “Many lenses make it more professional.” | They also create combinatorial search freedom. Add a lens only when it supplies a missing role and improves the whole method under the registered evaluation. |
| “The current FRESH state licenses a recommendation.” | No. Inspection freshness, history bounds and delivery cadence are not professional validity rules. §6 identifies the additional dependency checks. |
| “M3 already handles every relevant event.” | M3 handles accepted source deliveries. Timer-only expiries, derived windows and explicit revision semantics need bounded extensions. This does not invalidate M3's accepted observation scope. |
| “UTC day/session boundaries are natural BTC structure.” | They are conventions until an effect is demonstrated. Do not import equity open/close or weekend closure assumptions. |
| “No sizing means execution can be ignored.” | False. A recommendation can be too late or too small in price room after costs. Evaluate that conditionally without choosing the Owner's capital. Unknown capacity stays unknown. |
| “A 2:1 target proves an opportunity.” | False. Geometry gives conditional payoff structure, not the chance or path of realization. Target selection cannot be driven by a desired ratio. |
| “A funding premium identifies trapped longs.” | Not from these records. Separate observed derivatives facts from unsupported participant-intent stories. |

The most consequential risk is **professional-looking explanations outrunning evidence**. Explanations must make limitations and counterevidence easier to see, not conceal them behind a confident narrative.

## 16. Recommended implementation sequence after this review

These are bounded outcomes for Director planning, not executor task instructions.

1. **Director disposition and one process specification.** Accept/change the proposed specialization and complete research A–C, with D's initial actionability assumptions and E's evaluation design. Produce the causal case set, exact predicate definitions and explicit source/adaptation boundaries. Resolve the parameter register before feature implementation; do not defer cost/delay semantics until after recommendations have been designed.
2. **Derived observations and professional-time support.** Add only the aggregation, coverage, variability, swing/level and timer semantics required by that specification. Prove causality and stable checkpoint reconstruction; publish no invented recommendations to conceal incomplete semantics.
3. **First `semantic.v2` and analyst slice.** Publish horizon states, reference areas, competing scoreable scenarios and material changes on real evidence. Reuse the accepted substrate and keep synthetic DEMO separate. This slice may describe direction while no opportunity is ready.
4. **One complete advisory process.** Add the chosen long/short pullback opportunity, actionability gates, NO_TRADE reasons and separate entry/thesis lifecycles. Completion means the whole path works, including invalidation and expiry—not just attractive entry examples.
5. **Normalized outcome harness and registered integrated evaluation.** Operationalize D/E and close any remaining evidence gaps before making usefulness claims; enforce human delay, cost assumptions, episode accounting and ambiguity. Add prospective quote evidence only if required to resolve actionability. Run the declared baselines/ablations and preserve negative findings. Harness construction may accompany steps 3–4; outcome-led selection must wait for the registered evaluation gate.
6. **Prospective advisory observation.** Publish frozen-version opinions before outcomes, reconcile replay, and decide whether to retain, narrow, revise or reject the process. Only a documented limitation justifies a second playbook or new predictive data family.

Steps 3–4 can be one coherent bounded slice if separation adds overhead. The conceptual distinction must remain even when delivery is combined. Long runs continue through the application's durable job/monitoring infrastructure; no hidden optimization programme in an agent shell.

Do not wait for an exhaustive theory of professional trading. Do not start by coding a swing indicator in isolation and hoping a professional process emerges later. The next concrete output should be the accepted move–reaction specification and causal examples, not an indicator implementation or another infrastructure milestone.

## 17. Open decisions that genuinely require the Owner

**None blocks this design review or its next bounded research step.** The Owner has already settled the material product boundary: market understanding and recommendations; capital allocation and execution remain human.

The Director can decide the initial methodological specialization, proposed sampling scales, definition conventions and research evidence gates. The 1h/5m/1m proposal is reviewable and revisable without transferring an ordinary research choice to the Owner.

The system should expose recommendation age and an entry-validity window; evaluation should cover plausible human delays rather than asking the Owner now for a promised reaction time. Material paid-data costs, a demand for sub-minute opportunities, a different intended use, or any automation/account integration would require a later explicit Owner decision. None is silently assumed here.

**Final recommendation:** accept a narrow, response-driven continuation analyst as the first candidate; complete its targeted formalization before coding; then implement and evaluate the integrated advisory process. Keep broader market understanding, uncertainty and failed-thesis alternatives visible throughout. Preserve the right to conclude that this professional approximation is coherent but not economically useful on BTC.

---

### Evidence references and limits

All dossier links below are pinned to the review commit. Dossier coverage statements describe the original source-study work, not a claim that this review independently reread every underlying book or dataset. Legacy project prescriptions inside those files are excluded.

| Ref | Source and relevant sections | Use in this review / limitation |
| --- | --- | --- |
| D01 | [Johnson — Algorithmic Trading & DMA](https://github.com/C-Gian/algorithmic-trader/blob/8003ddc15a50e7ca5d811374345ccda140bd6297/source_notes/LIB-001-ALGORITHMIC-TRADING-AND-DMA.md), §§2, 4, 7, 9–10 | Selection/execution distinction, delay and cost components. Partially reviewed damaged source; historical institutional execution parameters are not BTC defaults. |
| D02 | [Ilmanen — Expected Returns](https://github.com/C-Gian/algorithmic-trader/blob/8003ddc15a50e7ca5d811374345ccda140bd6297/source_notes/LIB-002-EXPECTED-RETURNS.md), §§3–4, 8, 11, 15, 19, 27–28 | Expectations versus realizations, redundancy, horizon dependence and costs; no intraday BTC parameter evidence. |
| D03 | [Chan — Quantitative Trading](https://github.com/C-Gian/algorithmic-trader/blob/8003ddc15a50e7ca5d811374345ccda140bd6297/source_notes/LIB-003-QUANTITATIVE-TRADING-ERNEST-CHAN.md), §§8–9, 12–14, 17, 21, 28 | Causality, fills, reasoned refinement, prospective reconciliation and strategy-dependent exits. |
| D04 | [Carver — Systematic Trading](https://github.com/C-Gian/algorithmic-trader/blob/8003ddc15a50e7ca5d811374345ccda140bd6297/source_notes/LIB-004-SYSTEMATIC-TRADING.md), §§3, 6, 16, 18, 21, 24 | Forecast/action distinction, constrained research, costs, overlapping information; its portfolio sizing framework is not adopted. |
| D05 | [Market Wizards: The Next Generation](https://github.com/C-Gian/algorithmic-trader/blob/8003ddc15a50e7ca5d811374345ccda140bd6297/source_notes/LIB-005-MARKET-WIZARDS-THE-NEXT-GENERATION.md), §§3, 5–14, 16–17 | Conditional setups, scenario preparation, expected-response monitoring and context. Selected retrospective interviews, not a unified algorithm or causal BTC proof. |
| D06 | [Trend Following: Equity and Bond Crisis Alpha](https://github.com/C-Gian/algorithmic-trader/blob/8003ddc15a50e7ca5d811374345ccda140bd6297/source_notes/LIB-006-MAN-AHL-TREND-FOLLOWING-EQUITY-AND-BOND-CRISIS-ALPHA.md), §§3, 6, 9, 24–25 | External trend mechanism background; diversified monthly, largely gross simulations do not transfer directly. |
| D07 | [Trend Following and Drawdowns](https://github.com/C-Gian/algorithmic-trader/blob/8003ddc15a50e7ca5d811374345ccda140bd6297/source_notes/LIB-007-TREND-FOLLOWING-AND-DRAWDOWNS-IS-THIS-TIME-DIFFERENT.md), §§3–4, 7, 12, 15–16 | Horizon/edge-decay caution and evidence-class distinctions; no BTC verdict or guarantee of recovery. |
| D08 | [Which Trend Is Your Friend?](https://github.com/C-Gian/algorithmic-trader/blob/8003ddc15a50e7ca5d811374345ccda140bd6297/source_notes/LIB-008-WHICH-TREND-IS-YOUR-FRIEND.md), §§3–7, 15–16 | Equivalence/redundancy of defined linear trend filters; not independence of different chart timeframes or all technical concepts. |
| D09 | [A Century of Evidence on Trend-Following Investing](https://github.com/C-Gian/algorithmic-trader/blob/8003ddc15a50e7ca5d811374345ccda140bd6297/source_notes/LIB-009-A-CENTURY-OF-EVIDENCE-ON-TREND-FOLLOWING-INVESTING.md), §§5, 14, 16, 19, 25–26 | Regime causality and delay caveats; no intraday trigger/target specification. |
| D10 | [TSMOM Factors, Monthly](https://github.com/C-Gian/algorithmic-trader/blob/8003ddc15a50e7ca5d811374345ccda140bd6297/source_notes/LIB-010-TIME-SERIES-MOMENTUM-FACTORS-MONTHLY.md), §§1, 5, 7, 13, 20 | Reconstructed/versioned external history; not BTC training data or an independent second proof of the original study. |
| D11 | [TSMOM Original Paper Data](https://github.com/C-Gian/algorithmic-trader/blob/8003ddc15a50e7ca5d811374345ccda140bd6297/source_notes/LIB-011-TIME-SERIES-MOMENTUM-ORIGINAL-PAPER-DATA.md), §§1, 5, 9–11, 13 | Related factor dataset; insufficient by itself for full methodology or intraday transfer. |
| D12 | [Advances in Financial Machine Learning](https://github.com/C-Gian/algorithmic-trader/blob/8003ddc15a50e7ca5d811374345ccda140bd6297/source_notes/LIB-012-ADVANCES-IN-FINANCIAL-MACHINE-LEARNING.md), data/labeling/validation material and §§10–12 | Dependence, availability, outcome definition and limits of repeated backtests. ML, probability sizing and institutional workflow are not required. |
| D13 | [Deflated Sharpe Ratio](https://github.com/C-Gian/algorithmic-trader/blob/8003ddc15a50e7ca5d811374345ccda140bd6297/source_notes/LIB-013-DEFLATED-SHARPE-RATIO.md), §§2, 7–8, 13–14, 20, 25 | Selection burden and limits of corrections; no universal initial acceptance threshold. |
| D14 | [Value and Momentum Everywhere](https://github.com/C-Gian/algorithmic-trader/blob/8003ddc15a50e7ca5d811374345ccda140bd6297/source_notes/LIB-014-VALUE-AND-MOMENTUM-EVERYWHERE.md), §§1–3, 5, 7 | Secondary summary; does not justify adding a BTC value/carry lens. |
| D15 | [Time Series Momentum](https://github.com/C-Gian/algorithmic-trader/blob/8003ddc15a50e7ca5d811374345ccda140bd6297/source_notes/LIB-015-TIME-SERIES-MOMENTUM.md), §§1–5, 11–12 | Secondary summary; long-horizon persistence claim, not minute-scale evidence. |
| D16 | [Cross-Section of Expected Returns](https://github.com/C-Gian/algorithmic-trader/blob/8003ddc15a50e7ca5d811374345ccda140bd6297/source_notes/LIB-016-CROSS-SECTION-OF-EXPECTED-RETURNS.md), §§3, 5, 17, 19–21, 28 | Multiple-testing/search disclosure and statistical versus economic relevance. Equity-factor cutoffs do not transfer mechanically. |
| D17 | [PBO Mathematical Appendices](https://github.com/C-Gian/algorithmic-trader/blob/8003ddc15a50e7ca5d811374345ccda140bd6297/source_notes/LIB-017-MATHEMATICAL-APPENDICES-PROBABILITY-OF-BACKTEST-OVERFITTING.md), §§3, 14–15, 19–20 | Conditional assumptions and limitations of selection diagnostics. |
| D18 | [Probability of Backtest Overfitting](https://github.com/C-Gian/algorithmic-trader/blob/8003ddc15a50e7ca5d811374345ccda140bd6297/source_notes/LIB-018-THE-PROBABILITY-OF-BACKTEST-OVERFITTING.md), §§4–7, 17–21, 28 | Actual-trial disclosure and limits of PBO; not a replacement for causal/economic validation. |
| D19 | [Hull — Options, Futures, and Other Derivatives](https://github.com/C-Gian/algorithmic-trader/blob/8003ddc15a50e7ca5d811374345ccda140bd6297/source_notes/LIB-019-OPTIONS-FUTURES-AND-OTHER-DERIVATIVES-6E.md), §§3–6, 11, 20–21 | Derivative pricing versus prediction and model limits. No current perpetual directional rule or account requirement follows. |
| D20 | [Harris — Trading and Exchanges](https://github.com/C-Gian/algorithmic-trader/blob/8003ddc15a50e7ca5d811374345ccda140bd6297/source_notes/LIB-020-TRADING-AND-EXCHANGES-MARKET-MICROSTRUCTURE-FOR-PRACTITIONERS.md), §§3, 5–9 | Comparative advantage, liquidity and order tradeoffs; candle activity cannot establish executable depth or participant intent. |

Targeted external additions, retrieved 2026-09-30:

- **E1 — [Adam Grimes, Fundamental Trading Patterns](https://www.adamhgrimes.com/fundamental-trading-patterns/).** Practitioner description of pullbacks and distinct entry approaches. Used to identify an existing process family, not to infer BTC profitability or copy all its patterns.
- **E2 — [Adam Grimes, One step ahead…](https://www.adamhgrimes.com/one-step-ahead/), 8 October 2014.** Move/reaction framing and explicit uncertainty about familiar technical tools. Practitioner judgment, not a controlled BTC study. Our swing, timeframe and recommendation rules remain proposed adaptations.
- **E3 — [Carol Osler, Support for Resistance: Technical Analysis and Intraday Exchange Rates](https://www.newyorkfed.org/research/epr/00v06n2/0007osle.html), FRBNY, July 2000.** Primary research summary reports level-related predictive effects that vary across currencies/firms. It motivates a bounded question; it does not validate our generated zones.
- **E4 — [Carol Osler, Currency Orders and Exchange-Rate Dynamics](https://www.newyorkfed.org/research/staff_reports/sr125.html), FRBNY Staff Report 125, April 2001.** Primary research summary describes order-clustering mechanisms in a bank's FX data. It cannot establish hidden order concentrations from OKX candles. The linked full studies remain candidates for the targeted level-mechanism study; this review does not claim a new replication.

Accepted architectural references: [Foundation v2.0](https://github.com/C-Gian/algorithmic-trader/blob/8003ddc15a50e7ca5d811374345ccda140bd6297/FOUNDATION.md), [STATE](https://github.com/C-Gian/algorithmic-trader/blob/8003ddc15a50e7ca5d811374345ccda140bd6297/STATE.md), [SR-001 disposition](https://github.com/C-Gian/algorithmic-trader/blob/8003ddc15a50e7ca5d811374345ccda140bd6297/strategic_reviews/SR-001-DIRECTOR-DISPOSITION.md), [registry](https://github.com/C-Gian/algorithmic-trader/blob/8003ddc15a50e7ca5d811374345ccda140bd6297/knowledge/registry.yaml), [market-data contracts](https://github.com/C-Gian/algorithmic-trader/blob/8003ddc15a50e7ca5d811374345ccda140bd6297/src/algotrader/marketdata/contracts.py), [feed contracts](https://github.com/C-Gian/algorithmic-trader/blob/8003ddc15a50e7ca5d811374345ccda140bd6297/src/algotrader/feed/contracts.py), [state reducer](https://github.com/C-Gian/algorithmic-trader/blob/8003ddc15a50e7ca5d811374345ccda140bd6297/src/algotrader/feed/state.py), [recorder contracts](https://github.com/C-Gian/algorithmic-trader/blob/8003ddc15a50e7ca5d811374345ccda140bd6297/src/algotrader/recorder/contracts.py), [observation contracts](https://github.com/C-Gian/algorithmic-trader/blob/8003ddc15a50e7ca5d811374345ccda140bd6297/src/algotrader/observe/contracts.py), and the [SR-002 request](https://github.com/C-Gian/algorithmic-trader/blob/8003ddc15a50e7ca5d811374345ccda140bd6297/strategic_reviews/SR-002-FIRST-PROFESSIONAL-TRADER-DESIGN.md).
