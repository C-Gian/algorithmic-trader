# RP-001D — Initial Actionability Assumptions (for later evaluation only)

Status: PROPOSED — assumptions declared **before** any economic outcome is viewed; not optimized  
Depends on: [RP-001C](RP-001C-ADVISORY-POLICY.md). Numbers: [`DESIGN-CONVENTIONS.yaml`](DESIGN-CONVENTIONS.yaml).  
No Owner capital, leverage, quantity, collateral or personal fee tier is used anywhere.

## D1. Decision-known time

`t_known` = the `known_at` of the completed 1m bar that satisfies `P-TRIG` (plus the recorded evaluation of all gates at the same dispatch boundary; processing time is not modeled in v1).

- Historical datasets (MODELED availability): `t_known` = bar close (zero-extra-delay lower bound — optimistic; never presented as measured).
- Recorded sessions (RECORDED availability): `t_known` = client-observed receipt of the first completed push (WP-005 fixture delays ~0.6–1.7 s after bar end; session-specific, not a constant).

## D2. Human response delay

Evaluate every recommendation at both declared delays **Δ ∈ {60 s, 180 s}** (DC-25); display 120 s nominal. Never choose the delay per trade. The entry-validity window (10 min, DC-19) exceeds both.

## D3. Entry observation reference (normalized, not a fill)

- `t_ref = t_known + Δ`. Reference price = **open of the first completed 1m bar with open_time ≥ t_ref** (coarse; a candle open is not an executable quote).
- If that open is above `K + e` (long) → `MISSED_ENTRY_LOCATION` (the episode is recorded, no hypothetical trade outcome).
- If a completed 1m low ≤ V occurs at or before the reference bar → `INVALIDATED_BEFORE_ENTRY`.
- If the entry window closed before `t_ref` → `MISSED_ENTRY_WINDOW`.
- Never use the trigger price or the boundary K as a fictional fill.

## D4. Fees

Normalized taker fee assumption **2–5 bps per side** (DC-26). **UNVERIFIED**: RP-001 did not retrieve OKX's public fee schedule, and account-specific fee endpoints are prohibited. The envelope must be checked against the public schedule before any economic claim. No maker/rebate scenario is assumed (passive fills are unobservable from candles; LIB-020 §6.2, LIB-003 §8).

## D5. Spread and slippage

Normalized **0.5–3 bps per side** (DC-26). The tick (0.1 USDT ≈ 0.0012% at 84,000) makes the nominal quoted spread negligible; the envelope represents slippage and quote movement during a human's action and the difference between a candle open and an executable price. It is an assumption, not a measurement; candle volume cannot establish depth (LIB-020 §10).

Round-trip envelope: **c_low = 5 bps, c_high = 16 bps** (entry + exit, taker/taker).

## D6. Funding

Thesis horizon is ≤ 120 min. If the tracked interval crosses an 8-hourly settlement, apply the absolute settled funding rate known at that settlement as an additional cost bound (sign-agnostic: `|rate|`), because the realized rate is not known at entry. If the settlement value is unavailable in the evidence → cost state `UNRESOLVED` for that episode. Live pre-settlement funding remains recorder-only (WP-005) and is not used.

## D7. Cost viability states (per opportunity, at arming and at trigger)

`G_bps` = conservative room `G` (RP-001C C8) in bps of the worst entry `K + e` (long) / `K − e` (short).

| State | Rule (DC-27) | Public effect |
|---|---|---|
| `VIABLE` | c_high ≤ 0.25 × G_bps | issuance allowed |
| `UNRESOLVED` | otherwise and not DOMINATES | NO_TRADE `COST_OR_DELAY_VIABILITY_UNRESOLVED` |
| `DOMINATES` | c_low ≥ 0.50 × G_bps | NO_TRADE `COST_OR_DELAY_DOMINATES`; not ARMED |

Delay viability is folded in at evaluation (D3): the evaluation reports how often Δ turns a VIABLE geometry into a missed entry.

### Worked geometry examples (arithmetic only; no market outcome)

| Case | G (USDT) | worst entry | G_bps | VIABLE test: 16 ≤ 0.25·G_bps | DOMINATES test: 5 ≥ 0.5·G_bps | State |
|---|---|---|---|---|---|---|
| SYN-L01 | 115.0 | 84,270.0 | 13.6 | 16 ≤ 3.4 ✗ | 5 ≥ 6.8 ✗ | UNRESOLVED |
| SYN-L05 | 575.0 | 83,810.0 | 68.6 | 16 ≤ 17.2 ✓ | — | VIABLE |
| SYN-L10 | 33.0 | 84,082.0 | 3.9 | ✗ | 5 ≥ 2.0 ✓ | DOMINATES |
| C18 example | 85.0 | 83,300.0 | 10.2 | ✗ | 5 ≥ 5.1 ✗ | UNRESOLVED |

Thresholds implied by the envelope: VIABLE needs G_bps ≥ 64 (≈ 540 USDT at 84,000); DOMINATES whenever G_bps ≤ 10.

## D8. Consequence flagged before outcomes (not a configuration change)

Under DC-26/27, a long setup is cost-VIABLE only if conservative room exceeds **64 bps** (≈ 540 USDT at 84,000 USDT). With S5 of tens of USDT and an impulse minimum of 4 × S5, typical 5m-scale destinations (the prior impulse extreme) are likely to be far below that. **Expected consequence: most otherwise valid 5m setups will publish `COST_OR_DELAY_VIABILITY_UNRESOLVED` or `DOMINATES`.** This is recorded now, before any outcome is inspected. It is an *economic* observation, not a behavioral/causal inadequacy of 1h/5m/1m, so RP-001 does **not** change the configuration (RP-001 brief: changes only for causal/process failure). It is escalated to the Director as the principal open actionability question (see D10).

## D9. Ambiguous OHLC paths

- Target and invalidation inside one 1m bar → `AMBIGUOUS_ORDER`; report both admissible outcomes (target-first and invalidation-first) and count the episode in the unresolved fraction. Never assume target-first or a stop fill at V.
- A reference bar whose range contains both the band edge and V → `AMBIGUOUS_ENTRY`; excluded from trade-outcome means but reported.

## D10. When quote evidence becomes required

A prospective public best-bid/ask (and trade print) sample with receipt times becomes **required** before any net-usefulness claim if, in the registered development evaluation (RP-001E), either:

1. ≥ 25% of triggered opportunities are cost-`UNRESOLVED`; or
2. ≥ 10% of trade-outcome episodes are `AMBIGUOUS_ORDER`/`AMBIGUOUS_ENTRY`; or
3. conclusions change sign between c_low and c_high.

Given D8, condition 1 is expected to hold; quote evidence (and a verified fee schedule) should therefore be planned. A prospective quote sample cannot establish historical spreads; historical cost remains an envelope with sensitivity bounds.

## D11. Explicitly not modeled

Capacity/market impact beyond the slippage envelope; partial fills; queue position; liquidation; leverage; any account path. Unknown capacity stays unknown.
