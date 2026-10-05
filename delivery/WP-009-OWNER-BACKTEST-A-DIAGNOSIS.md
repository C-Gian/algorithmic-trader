# Owner Backtest A — September result and targeted method diagnosis

Date: 2026-10-05. Status: **ENGINE WORKFLOW CONFIRMED; METHOD USEFULNESS NOT ACCEPTED ON THIS DEVELOPMENT MONTH.** Director diagnosis and targeted Astra review; no executor implementation active.

## Evidence ownership

The Owner launched the prescribed app Adviser evaluation and supplied its copied Markdown and [original JSON](evidence/WP-009-OWNER-BACKTEST-A.json). Evaluation `eval-20261005T120047-e6cc50`, replay `obs-20261005T120047-bc6947`, application code `6f95273b54674081fe6b3896a84d62a015384fe5`, adviser.core.v2 / btc.context-action.v0.2 / mp001.rules.v0.2. Pack `pack-427d5f5d0e26d595ff0c131c70a9435b26692dbe`; identity `a59d0cb632ca6b2780f5ff98b5e6a006dabe58c1581bfb703d5201e8f3361ed8`. This is Owner evidence, not a Director reproduction or a new agent economic run. September remains development; protected Jan–Aug 2026 not used.

Completed all 147,975 warmup/evaluation/tail events in 135.2 s, runtime reconciliation v5 PASS 20/20, 64 transactions, no prefix restore or recoveries. All 43,200 evaluation minutes assessable; complete trade/mark/index price slots. Funding, calendar/news, historical quotes, predictive cycles and other absent capability scopes remain limitations. Runtime integrity does not establish economic quality; no Deep validation requested.

## Measured method behavior

- 109 candidate births (A 85, B 12, C 12), 47 arms, 38 evaluated triggers, **zero issued calls**. One warmup call excluded, correctly not a scored September outcome.
- Rejection reasons: NO_ROOM_AFTER_COSTS 18; REWARD_RISK_BELOW_MINIMUM 14; AT_OPPOSING_AREA 6. No slot/priority/conflict rejection, core missing-data or calendar veto recorded.
- 42,087/43,200 minutes without an armed scenario (97.42%); 1,113 minutes ARMED_SCENARIO. NO_SUPPORTED_PLAN 33,001 minutes, BALANCED_RANGE 9,086. ISSUABLE_IF_TRIGGERED is operational common-blocker/slot freedom, **not** profitable geometry or the existence of an opportunity. Its 100% value does not contradict zero calls.
- 45 A episodes spent by a pre-reaction high beyond the frozen impulse destination; this is another observed coverage attrition point, not yet proof of a defective rule.
- For the 32 triggers with G/Q: A 26, B 1, C 5. The other six have opposing-area rejection and no geometric G/Q; the staged list has 32 rows and is not truncated.

| Family | G median (bps) | Q median (bps) | K (bps) | Margin max (bps) |
|---|---:|---:|---:|---:|
| A | 11.2616 | 16.5951 | 14 | -7.6915 |
| B | 17.6195 | 1.2241 | 14 | -14.6493 |
| C | 12.3666 | 16.8057 | 14 | -32.2424 |

Margin is the actual per-trigger G−1.2Q−2.2K distribution, not arithmetic on unrelated medians. Every calculated margin is negative. With K=14, the required G is 1.2Q+30.8 bps; even zero risk cannot make sub-30.8bps gross room satisfy that gate. This does not authorize lowering cost or reward/risk assumptions.

A staged evidence: reaction-to-target room median 30.9616bps, trigger room median 11.2616bps; median per-row erosion reaction→trigger 14.7489bps. 15/26 A trigger rooms <=14bps; 22/26 reaction rooms >14bps. **24/26** A rows show negative room from the impulse B price to the selected target (target lies before the old impulse extreme in the trade direction). These are diagnostic calculations against the target frozen at trigger; the reaction price is an anchor extreme and the later selected target need not have been eligible/known at that earlier time. They do not establish an earlier executable entry or authorize retrospective entry at the reaction low.

Limiting-landmark counts across all 38 trigger evaluations: 15m pivots 18, 1h pivots 4, IMPULSE_B 9, NONE 7. Type/family/case attribution is not fully joined in the export; do not blame IMPULSE_B alone. Nearest opposing target caps, 15m zone policy and trigger recovery interact.

No entered paths means **no evidence of wins, losses or profitability**; the zero price-net sum is not proof of break-even safety. Hourly view scores use only 18 directional samples versus 702 abstentions; persistence uses 720 samples. Those aggregate accuracies are not a matched-subset superiority comparison.

## Initial Director diagnosis and uncertainty

The process is operationally usable (~2m15 for a month), but this method translation does not yet meet the product's useful-call objective on September. Do not congratulate blanket abstention, force a weekly quota or reject all professional reasoning based on one month.

Source inspection matches the declared v0.2 policy at the central bottleneck: `_resolve_target` rejects inside an active opposing zone and chooses the nearest ahead; A includes its owned impulse-B zone. `_a_close` arms from a completed reaction bar, sets K to that bar's high, and requires a later complete 1m close through K. Confirming a recovery while targeting a nearby prior destination may consume much of the available net room. Small pivots can also cap the target. This is a **method-scale/target/trigger compatibility hypothesis**, not a demonstrated implementation bug or a reason to skip real intervening resistance.

Available summary lacks a fully joined per-trigger trace of actual price/stop/target, all eligible opposing zones, source ages, arm/trigger timestamps and causal feasibility at earlier checkpoints. Do not claim a uniquely proved cause without it. If indispensable, identify a minimal read-only export of the existing committed journal; no rerun, parameter sweep or generalized analytics infrastructure.

## Targeted Astra review — required output

Read FOUNDATION.md, current STATE/task; [MP-001 v0.2](MP-001-INTEGRATED-METHOD-PROPOSAL.md), [register](MP-001-PARAMETERS.json), [accepted method disposition](MP-001-DIRECTOR-DISPOSITION.md), this diagnosis and the original report. Inspect only relevant source: adviser/core.py (qualification, arm, target, geometry), geometry.py, report.py. A brief read-only review, **not a new general strategic checkpoint**.

1. Separate declared method behavior, possible implementation/diagnostic defects and economic hypotheses. Challenge the Director's target/trigger explanation rather than assuming it.
2. Assess the integrated net-feasibility of A/B/C and their scale/horizons. Are conservative local targets and confirmation rules compatible with the declared costs/stop geometry? Discuss sparse scenario/view coverage and pre-reaction spending as well as target distance.
3. If recommending a revision, specify the smallest coherent behavioral proposal: causal observations/eligibility, targets versus intermediate obstacles, entry/trigger and invalidation, expected/hard horizon, ownership and expiry. Preserve human usability and no-lookahead. Do not merely move T past every inconvenient zone, enter at a hindsight low, reduce K/RR or relax thresholds until September emits calls.
4. Identify the **minimum** missing case evidence if it changes the decision. Existing-journal read/export is allowed as a proposal; no economic rerun, source acquisition or protected-period inspection. The current report alone cannot recover absent joint distributions.
5. Return: confirmed facts; competing explanations and confidence; one recommended bounded next step; explicit rules/choices needing Director decision; tiny hand-expected tests and an Owner-run development/protected validation plan. No method change or implementation is authorized by this review. No win-rate/frequency guarantee.

Use targeted primary research only if a concrete missing professional-method question needs it; no Internet census or threshold tournament. The Director decides whether to request case export, fix a bug or issue a versioned method proposal before Claude implementation.

## Operating boundary

No new Owner run requested now. No active Claude code task. Substantial tests remain app-operated by the Owner; the Director analyzes reports, Claude implements bounded changes, and future CI waiting is Owner-operated under AGENTS.md. Preserve this failed-to-produce-calls baseline and original report unchanged.
