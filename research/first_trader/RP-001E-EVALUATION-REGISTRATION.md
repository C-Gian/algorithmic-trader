# RP-001E — Evaluation Registration (pre-registered; no outcomes computed in RP-001)

Status: PROPOSED REGISTRATION — frozen before any economic outcome is used to alter the method  
Depends on: [RP-001C](RP-001C-ADVISORY-POLICY.md), [RP-001D](RP-001D-ACTIONABILITY-ASSUMPTIONS.md).  
RP-001 computes **no** profitability, hit rate or expectancy. This document defines what a later, separately authorized evaluation must compute, on what, and when it stops.

## E1. Four claims, evaluated separately

1. **Causal correctness** — prefix invariance, replay/restart equality, deterministic timers. Pass/fail engineering evidence.
2. **Process fidelity** — the same masked prefix yields the same labels; Director independent labels agree or disagreements are documented (RP-001A U-A4).
3. **Forecast information** — activated conditional scenarios and MarketView states carry information beyond simple controls (E6).
4. **Recommendation usefulness** — recommended episodes remain worthwhile under D's delay/cost envelope and ambiguity handling.

Passing one never implies the next.

## E2. Units

- **Opportunity episode** (primary unit): one Opportunity id from first WATCHING to its terminal entry state and, if activated, its terminal thesis state. Revisions stay inside the episode. Retries within one reaction are impossible by C13; episodes sharing an impulse are linked (same `impulse_id`) and treated as dependent.
- **Recommendation episode**: an episode in which LONG/SHORT was issued.
- **Audit point**: every completed 5m bar close (DC-29), for MarketView/scenario coverage, including NO_TRADE time.

## E3. Candidate funnel (always reported, per direction)

`setups WATCHING → ARMED → TRIGGERED → gates passed (issued) | blocked (by display reason and all failing gates) → entry reference obtained | missed (window / location / invalidated-before-entry) → thesis outcome`.

Counts at every stage; no stage may be omitted to improve a ratio.

## E4. Outcome states

**Scenario (conditional continuation, `scenario.continuation.v1`):** `NOT_ACTIVATED`, `TARGET_BEFORE_INVALIDATION`, `INVALIDATION_BEFORE_TARGET`, `EXPIRED_UNRESOLVED`, `AMBIGUOUS_ORDER`, `UNASSESSABLE_DATA`.

**Recommendation (reference trade, per Δ):** `MISSED_ENTRY_WINDOW`, `MISSED_ENTRY_LOCATION`, `INVALIDATED_BEFORE_ENTRY`, `AMBIGUOUS_ENTRY`, then `TARGET_BEFORE_INVALIDATION`, `INVALIDATION_BEFORE_TARGET`, `EXPIRED_UNRESOLVED`, `AMBIGUOUS_ORDER`, `UNASSESSABLE_DATA`.

**Checkpoint (30 min):** `RESPONDING` / `RESPONSE_ABSENT` / `UNASSESSABLE_DATA` — reported separately from terminal outcomes.

## E5. Measurements (descriptive; all per direction)

| Measurement | Definition |
|---|---|
| Primary horizon | 120 min after activation (DC-21). Candidate horizon, justified as the upper end of the minutes-to-hours product horizon and ≥ several 5m impulse durations; not an arrival-time estimate. Fixed before outcomes. |
| Barrier order | target-before-invalidation vs invalidation-before-target within the horizon; ambiguous and unresolved kept as their own categories (never dropped, never imputed). |
| Terminal signed movement | (close of the last completed 1m bar at or before t_a + 120 min − reference) × direction, in bps. Reference: trigger-bar close for scenarios; D3 reference open for recommendations. |
| Excursions | MFE and MAE in bps from the same reference over the horizon (until resolution for barrier-stopped reference trades; full horizon for scenario description). |
| R-normalized | movement / (reference − V) as an analytical denominator only (no capital meaning). |
| Time to resolution | minutes from reference to first boundary. |
| Net reference return | per D: exit at target near edge / V / horizon close, minus c_low and c_high (both reported); ambiguous episodes reported as both bounds. |
| Missed-entry frequency | per Δ. |

## E6. Simple controls (same eligible information set)

1. **Persistence control:** at each audit point with an assessable 1h context, forecast 120-minute terminal direction = context direction; score direction accuracy and signed movement. Compares the whole process against "just follow the 1h context".
2. **Matched-geometry random-time control:** for each activated episode, draw (seeded, recorded) audit points from the same UTC day with the same context direction where no episode is active, and apply the same K/V/T distances (translated to that time's price) with the same horizon and D rules. Outcome-order frequencies and net bps are compared with the actual episodes. This adapts EXT-003's "published vs arbitrary levels" design; it is not a significance recipe.
3. **Unconditional base rate:** frequency of +G before −Rd barrier order (same distances) at all audit points, ignoring setups.

## E7. Role-level ablations (only after the integrated method exists)

Each changes exactly one role and keeps denominators coherent:

| Ablation | Change |
|---|---|
| AB-1 no context | P-CTX treated as SATISFIED in the setup direction |
| AB-2 no reaction control | P-REACT replaced by "D < 1.0 and no structural failure" |
| AB-3 no room screen | P-TGT/P-GEOM/P-COST removed (target still recorded for scoring) |
| AB-4 no response trigger | activation at arming (entry at next 1m open after arming) instead of P-TRIG |

A role with no measurable contribution is simplified away; an ablation is never promoted to a new strategy on its own backtest.

## E8. Period separation

- **RP-001 evidence** (the real cases' acquisition window, see `cases/SELECTION-PROTOCOL.md`) is formalization/development evidence and is **excluded** from any protected evaluation.
- **Development period:** a contiguous span of accepted historical OKX datasets chosen by calendar rule before inspection: the 60 complete UTC days immediately preceding the protected period.
- **Protected period:** the 30 complete UTC days immediately following the development period, acquired and verified but **not replayed through the method** until the method version is frozen; used exactly once. Any look at it converts it to development evidence (recorded).
- **Prospective:** recorder-based observation after freezing (RECORDED availability), issued views preserved before outcomes.
- Purge: episodes whose 120-min horizon crosses a partition boundary belong to the earlier partition and are excluded from the later one; 72 h of warm-up history before a partition may be read (causal context) but produces no scored episodes.

## E9. Dependence and uncertainty

- Episodes on the same UTC day are dependent; uncertainty via **day-block bootstrap** (resample UTC days), 2,000 resamples, seed recorded.
- Audit points are heavily overlapping; report their statistics only with day-block intervals, never IID intervals.
- Long and short reported separately; pooled figures are secondary.
- Slices (causal only): long/short, S5 tercile at arming (thresholds fixed from development period), weekday/weekend. Hindsight regime labels are diagnostic only.

## E10. Falsification and stopping (registered)

Primary metric (recommendation usefulness): mean net reference return per recommendation episode at **c_high and Δ = 180 s**, per direction, with day-block 90% interval.

Evaluation is executed **once** on the protected period after the method version is frozen. The candidate is:

- **Narrowed or rejected** if any registered falsifier holds: (a) Director and rule labels on masked prefixes disagree on > 25% of reviewed cases for a core concept (A2–A7) without a documented resolution; (b) activated continuation scenarios show no improvement in target-before-invalidation frequency over the matched-geometry control (E6.2) in development; (c) the primary metric's interval lies entirely ≤ 0 in both directions; (d) results reverse sign between c_low and c_high or between Δ = 60 s and 180 s; (e) attractive results exist only with < 1 recommendation per 3 UTC days per direction (coverage failure: an always-NO_TRADE method is not success); (f) conclusions depend on ambiguous episodes (sign changes between ambiguity bounds); (g) a ±1-bar alignment shift of 5m/1h windows changes the majority of recommendation directions.
- **Insufficient evidence** if the protected period yields < 30 recommendation episodes in a direction: that direction's usefulness claim is `INSUFFICIENT_EVIDENCE` (not approval, not rejection). No extension of the protected period to "reach significance"; a new protected period requires a new registration.
- **Research iteration stops** to repair causality/semantic defects; the method is never patched after a single loss.

## E11. What this registration forbids

Threshold/timeframe grids, per-trade delay choice, dropping ambiguous or data-loss episodes, re-opening the protected period, reporting only pooled or only favorable directions, and treating geometry ratios as probabilities.
