> **HISTORICAL SCOPE NOTICE — 30 September 2026.** FOUNDATION.md v3.0 implements the Owner's direct clarification and supersedes inconsistent scope/workflow instructions below. This document is retained as historical/advisory evidence. Its former ACCEPTED/READY/HOLD status is not current authorization. In particular, the mandatory pullback-only path, blanket cycle/news deferrals and RP-001 closure gate are no longer project direction. Reuse compatible findings only through the current task; preserve original evidence and failed cases. See the current FOUNDATION.md, STATE.md and task.md.

# RP-001C — Complete Advisory Policy (long process and exact short mirror)

Status: PROPOSED (policy specification; no recommendation code exists or is authorized)  
Depends on: [RP-001A](RP-001A-PROCESS-TRANSLATION.md), [RP-001B](RP-001B-CAUSAL-STRUCTURE-LEVELS.md). Numbers: [`DESIGN-CONVENTIONS.yaml`](DESIGN-CONVENTIONS.yaml).  
Every predicate below is typed, has named operands and a price role (traded), and evaluates to **SATISFIED / CONTRADICTED / UNKNOWN**. No numeric confidence exists anywhere in this policy.

## C0. Objects and identities

| Object | Identity and immutability |
|---|---|
| `MarketView` | versioned at each evaluation that changes it; states per horizon (1h context, 5m setup) with evidence refs; may say `NO_PREFERRED_SCENARIO` |
| `Opportunity` | id created when a setup first becomes WATCHING; revisions (`rev`) only before trigger (re-anchoring, re-arming); frozen at trigger |
| `Scenario` | continuation / failure / unresolved records linked to an opportunity revision; immutable once activated |
| `Recommendation` | LONG / SHORT / NO_TRADE with reasons; issued at a known-at time; geometry immutable |
| `Thesis` | the tracked assessment of an issued recommendation's scenario; outcomes append-only |

Evaluation instants: every newly known completed 1m bar, every newly known completed 5m/1h bar, and every due timer (deadline). At an instant, **all evidence known up to the recorded dispatch boundary is applied first**, then derived objects, then predicates, then timers due at that instant (SR-002 disposition, professional time). The exact cursor is recorded.

## C1. Context applicability — `P-CTX(dir)`

| State | Long (`dir = LONG`) | Short |
|---|---|---|
| SATISFIED | 1h context = UP (RP-001A A1) | DOWN |
| CONTRADICTED | context = DOWN or NOT_DIRECTIONAL | UP or NOT_DIRECTIONAL |
| UNKNOWN | context = UNKNOWN (warm-up, scale unavailable, non-complete 1h bar in lookback) | same |

Contradicted → public `CONTEXT_OUTSIDE_METHOD` (DOWN/UP opposite) or `NO_SUPPORTED_SETUP` (NOT_DIRECTIONAL). A long against DOWN context is outside scope even if a bounce is plausible; the MarketView may still describe the bounce.

## C2. Setup detection (5m) and MarketView setup state

Setup state, evaluated on each completed 5m bar for the context direction only:

| Setup state | Meaning (long) |
|---|---|
| `NO_IMPULSE` | no confirmed qualifying impulse A→B (A2) in the context direction |
| `IMPULSE_DEVELOPING` | a running extreme beyond the prior swing exists but B is not yet confirmed (reaction < 2 × S5) |
| `REACTION_CONTROLLED` | A3 satisfied |
| `REACTION_DEEP` | 0.50 < D < 1.0, not opposing initiative |
| `OPPOSING_INITIATIVE` | A5 (sticky for the reaction; precedence over REACTION_DEEP) |
| `INDECISIVE` | A4 stall |
| `STRUCTURAL_FAILURE` | A6 (completed 5m close below A) |
| `UNKNOWN` | a required 5m bar non-complete, S5 unavailable, or a gap-affected leg (B5) |

Typed predicates:

| Predicate | SATISFIED | CONTRADICTED | UNKNOWN |
|---|---|---|---|
| `P-SCALE` | S5 and S1h available (24 contiguous complete bars each) | — (cannot be contradicted) | fewer than 24 contiguous complete bars |
| `P-IMP` | confirmed A→B in context direction inside the current epoch (DC-30), I ≥ 4 × S5, B beyond the epoch high-water mark before A (DC-31) | latest confirmed leg in context direction fails size or progress | required swings unconfirmed / gap-affected / non-complete bars inside A→B |
| `P-REACT` | D ≤ 0.50, ρ not assessed or ≤ 1.0 (assessed only when D > 0.25 and n_R ≥ 3), no OPPOSING_INITIATIVE observed on this reaction, n_R ≤ 3 × n_I | any bound exceeded, or OPPOSING observed earlier (sticky) | a non-complete 5m bar since B |
| `P-NOFAIL` | no completed 5m close below A | a completed 5m close below A | a non-complete 5m bar since B |
| `P-SCALEBAND` | latest complete 5m TR ≤ 4 × S5_frozen and current S5 within ×0.5–×2 of frozen (DC-28) | outside | S5 unavailable |

## C3. Opportunity lifecycle (entry dimension)

```
            P-CTX,P-IMP,P-REACT,P-NOFAIL SATISFIED
 (none) ───────────────────────────────────────────▶ WATCHING
 WATCHING ── P-TGT & P-GEOM SATISFIED, P-COST ≠ DOMINATES ──▶ ARMED
 ARMED ── re-anchor (new lower completed 5m low, still controlled) ──▶ ARMED (rev+1)
 ARMED ── geometry/target no longer satisfied ──▶ WATCHING (rev+1)
 ARMED ── P-TRIG SATISFIED ──▶ TRIGGERED
 TRIGGERED ── all issuance gates SATISFIED ──▶ OPEN_FOR_ENTRY  (Recommendation LONG issued)
 TRIGGERED ── any gate not SATISFIED ──▶ CLOSED_TO_ENTRY (NO_TRADE with reason; scenario still activated)
 OPEN_FOR_ENTRY ── 10 min elapsed | completed 1m close outside band | invalidation ──▶ CLOSED_TO_ENTRY
 WATCHING/ARMED ── setup contradicted (deep, opposing, failure, context lost) ──▶ INVALIDATED
 WATCHING/ARMED ── 1m low ≤ V before trigger ──▶ INVALIDATED
 ARMED ── 60 min since first ARMED ──▶ EXPIRED
 ARMED ── same-bar trigger/invalidation ambiguity ──▶ UNASSESSABLE
 any ── required evidence UNKNOWN for the pending step ──▶ state held, reason WARMUP_OR_REQUIRED_DATA_UNAVAILABLE; if held past a deadline, the deadline applies
```

Terminal entry states: `CLOSED_TO_ENTRY`, `EXPIRED`, `INVALIDATED`, `UNASSESSABLE`. WATCHING has no own expiry; it ends when the setup is contradicted or superseded by a new impulse (a new opportunity id).

## C4. Trigger — `P-TRIG`

- **Operands:** recovery boundary K (anchor bar high, B6), tick 0.1, price role traded, observation = completed 1m bars with `open_time ≥ anchor.end` and `known_at > arming.known_at`.
- **SATISFIED:** first such bar with `close ≥ K + 1 tick` (DC-23), while ARMED and not expired. Confirmation has market time (bar close) and knowledge time (bar known_at).
- **CONTRADICTED:** a completed 1m bar with `low ≤ V` before any satisfying bar (→ INVALIDATED), or the 60-minute setup expiry passes.
- **UNKNOWN:** a traded 1m slot since arming is quality-affected/pending/beyond coverage (the trigger or invalidation might be hidden). While UNKNOWN, no LONG can be issued; if the slot later remains non-complete past expiry → EXPIRED with data flag.
- **Ambiguity:** one bar with `low ≤ V` and `close ≥ K + tick` → UNASSESSABLE (B10).

## C5. Entry interval and entry-location-lost — `P-BAND`, `P-VALIDITY`

- Entry interval `[K, K + e]`, e = 0.5 × S5 frozen at arming (DC-15). It is neither an order nor a promised fill.
- `P-BAND` at trigger: SATISFIED if trigger close ≤ K + e; CONTRADICTED if trigger close > K + e (→ `ENTRY_LOCATION_LOST`; the continuation scenario still activates and is tracked, but no LONG is offered); UNKNOWN never (the trigger bar is complete by definition).
- `P-VALIDITY` while OPEN_FOR_ENTRY: SATISFIED while < 10 min since trigger known-at (DC-19) and every later completed 1m close is within `[V, K + e]`; CONTRADICTED at 10 min, or on the first completed 1m close outside the band (above → location lost; at/below V → invalidation); UNKNOWN if a traded 1m slot in the window is non-complete (entry offer suspended: public reason `WARMUP_OR_REQUIRED_DATA_UNAVAILABLE`).
- Price returning into the band after leaving it does **not** reopen entry (no re-entry).

## C6. Local invalidation — `P-INTACT`

- `V = R − b` (long), b = max(1 tick, 0.25 × S5 frozen at arming) (DC-14), R = reaction extreme of the current revision.
- SATISFIED: no completed 1m low ≤ V since arming (pre-trigger) / since activation (thesis). CONTRADICTED: such a bar exists. UNKNOWN: a non-complete traded 1m slot in the interval.
- Invalidation defeats the local thesis only; the 1h context may remain UP and the MarketView says so.

## C7. Primary target selection precedence — `P-TGT`

1. Candidates: eligible zones (not BROKEN, not retired, confirmed before arming known-at) on the opposing side (RP-001B B8), from 5m and 1h swings, including the impulse extreme's zone.
2. Keep those with near edge `T_near > K + e` (long).
3. Primary target = the lowest `T_near` (nearest). Ties → the 5m-origin zone, then the earliest confirmation.
4. No candidate → `P-TGT` CONTRADICTED (`INSUFFICIENT_ROOM_OR_GEOMETRY`, sub-reason `NO_TARGET`). UNKNOWN if a required swing is gap-affected.
5. The target never comes from a reward multiple, a projection or a round number.

## C8. Geometry and actionability gates

| Predicate | SATISFIED | CONTRADICTED | UNKNOWN |
|---|---|---|---|
| `P-GEOM` | G = T_near − (K + e) ≥ 1.0 × Rd, Rd = (K + e) − V (DC-17) | G < Rd | target unknown |
| `P-COST` | VIABLE per DC-27 (c_high ≤ 0.25 × G_bps) | DOMINATES (c_low ≥ 0.50 × G_bps) | UNRESOLVED (between) |
| `P-DATA` | DC-24 satisfied at the evaluation instant | — | newest traded 1m older than 120 s, or required bar non-complete |
| `P-EXCL` | no Thesis in TRACKING and no Opportunity OPEN_FOR_ENTRY (either direction) | one exists | — |

**Issuance gates for LONG/SHORT at trigger:** `P-DATA`, `P-SCALE`, `P-SCALEBAND`, `P-CTX`, `P-NOFAIL`, `P-INTACT`, `P-TGT`, `P-GEOM`, `P-BAND`, `P-EXCL` all SATISFIED **and** `P-COST` = VIABLE. `P-REACT` is evaluated at the latest completed 5m bar before the trigger (a trigger minute inside a still-forming 5m bar cannot change the completed-bar reaction state). Any gate CONTRADICTED or UNKNOWN → NO_TRADE with all failing gates recorded and one display reason (C14).

## C9. Scenarios

At WATCHING/ARMED the MarketView carries, for the opportunity revision:

| Scenario | Claim (long) | Activation |
|---|---|---|
| `CONTINUATION` (conditional) | "If P-TRIG is satisfied at t_a, price reaches T_near (completed 1m high ≥ T_near) before a completed 1m low ≤ V and before t_a + 120 min." | trigger known-at |
| `FAILURE` (alternative) | "Before trigger: a completed 1m low ≤ V occurs first; after activation: V is crossed before T_near." | always open |
| `UNRESOLVED` | "Neither boundary within the claim window / setup expires untriggered." | — |

- **Unconditional preference before trigger:** `NO_PREFERRED_SCENARIO`. The method makes only the conditional claim; it does not forecast that the trigger will occur. (A future version may add an unconditional preference only with its own registered evaluation.)
- **Expected response** after activation: by t_a + 30 min some completed 1m high ≥ K + 0.5 × (T_near − K) (DC-20). Absent → `RESPONSE_ABSENT` advisory update (thesis weakening; no automatic exit in v1).
- **Scenario outcomes** (immutable, versioned definition `scenario.continuation.v1`): `NOT_ACTIVATED` (expired/invalidated before trigger), `TARGET_BEFORE_INVALIDATION`, `INVALIDATION_BEFORE_TARGET`, `EXPIRED_UNRESOLVED`, `AMBIGUOUS_ORDER`, `UNASSESSABLE_DATA`. The trigger itself is never scored as success.

## C10. Deadlines (all measured on professional time; timers fire even without a new candle)

| Deadline | Value | Start | Effect |
|---|---|---|---|
| Setup expiry | 60 min (DC-18) | first ARMED known-at of the opportunity | ARMED → EXPIRED; scenario NOT_ACTIVATED |
| Stall | n_R > 3 × n_I completed 5m bars (DC-13) | B's bar | setup INDECISIVE → opportunity INVALIDATED (reason SETUP_CONTRADICTED) |
| Entry validity | 10 min (DC-19) | trigger known-at | OPEN_FOR_ENTRY → CLOSED_TO_ENTRY |
| Response checkpoint | 30 min (DC-20) | activation | RESPONSE_ABSENT or RESPONDING recorded |
| Thesis / forecast expiry | 120 min (DC-21) | activation | EXPIRED_UNRESOLVED if unresolved |

A deadline evaluated during a data outage uses only evidence known by its dispatch boundary; if the resolving evidence is missing, the outcome is `UNASSESSABLE_DATA`, never assumed.

## C11. Thesis assessment lifecycle (separate dimension)

`TRACKING → TARGET_REACHED | INVALIDATED | EXPIRED_UNRESOLVED | AMBIGUOUS_ORDER | UNASSESSABLE`

- Starts at activation (trigger known-at), regardless of whether a LONG was issued (so a thesis can be tracked while entry was lost).
- Uses completed 1m bars after the trigger bar. Target: high ≥ T_near. Invalidation: low ≤ V. Both in one bar → AMBIGUOUS_ORDER (B10).
- Advisory wording refers to the **thesis**: "thesis intact / weakening / defeated / target area reached" — never "your position".
- No trailing, no partials, no second target in v1.

## C12. Recommendation issue, withdrawal, revision

- **Issue:** LONG at the trigger known-at iff all issuance gates hold (C8). The record freezes K, e, V, T_near, deadlines, S5, dependency refs, cursor.
- **While OPEN_FOR_ENTRY:** public action LONG.
- **Withdrawal:** on entry-window close, invalidation, context loss, data-currency failure, or an incompatible opposite-direction ARMED setup → public action NO_TRADE with `EXISTING_THESIS_NO_NEW_ENTRY` (thesis still TRACKING) or `EXPIRED_OR_INVALIDATED` (thesis terminal). A withdrawal is a new advisory version linked to the issued one; the issued record is never edited.
- **View revision without recommendation change:** e.g. 1h context turns NOT_DIRECTIONAL while a thesis is tracking → MarketView revised, advisory update "context no longer supports new entries; local thesis intact" — the thesis is not auto-invalidated (its V/T definitions are unchanged).
- **Pre-trigger revisions** (re-anchor, re-arm) create opportunity revisions; each revision's scenario is a separate conditional claim; only the revision that triggers activates.

## C13. New setup vs re-entry; one thesis; no automatic reversal

- **No re-entry:** after an opportunity reaches any terminal entry state, no second trigger on the same reaction. A new opportunity requires a **new confirmed impulse** (a new B beyond the prior B, or a new A→B leg after a new confirmed origin).
- **One primary actionable thesis:** while a Thesis is TRACKING or an opportunity is OPEN_FOR_ENTRY, no new LONG/SHORT is issued in either direction (`EXISTING_THESIS_NO_NEW_ENTRY`); other setups may be shown as WATCHING.
- **No automatic reversal:** an invalidated long never becomes a short. A short requires its own DOWN context, impulse, reaction, trigger and gates, after the long thesis ends.
- **Conflict:** if long and short both appear admissible at one instant (possible only with inconsistent context evidence) → NO_TRADE `SCENARIOS_CONTESTED`.

## C14. Candidate public NO_TRADE taxonomy and display precedence

Public action is NO_TRADE unless an opportunity is OPEN_FOR_ENTRY. All failing predicates are recorded internally; one **display reason** is chosen by this precedence (first match):

| # | Public reason | Trigger (failing predicate / state) |
|---|---|---|
| 1 | `WARMUP_OR_REQUIRED_DATA_UNAVAILABLE` | P-DATA or P-SCALE UNKNOWN; context UNKNOWN; required evidence UNKNOWN |
| 2 | `EXISTING_THESIS_NO_NEW_ENTRY` | P-EXCL CONTRADICTED |
| 3 | `MOVEMENT_OUTSIDE_SUPPORTED_SCALE` | P-SCALEBAND CONTRADICTED |
| 4 | `CONTEXT_OUTSIDE_METHOD` | P-CTX CONTRADICTED by the opposite direction |
| 5 | `SCENARIOS_CONTESTED` | long and short both admissible; or setup OPPOSING_INITIATIVE / REACTION_DEEP while context holds |
| 6 | `NO_SUPPORTED_SETUP` | context NOT_DIRECTIONAL; NO_IMPULSE; IMPULSE_DEVELOPING; INDECISIVE |
| 7 | `EXPIRED_OR_INVALIDATED` | the most recent opportunity ended (EXPIRED, INVALIDATED, UNASSESSABLE, STRUCTURAL_FAILURE) and no new one exists |
| 8 | `INSUFFICIENT_ROOM_OR_GEOMETRY` | P-TGT or P-GEOM CONTRADICTED (sub-reason NO_TARGET / ROOM_BELOW_FLOOR) |
| 9 | `COST_OR_DELAY_DOMINATES` | P-COST DOMINATES |
| 10 | `COST_OR_DELAY_VIABILITY_UNRESOLVED` | P-COST UNRESOLVED |
| 11 | `TRIGGER_PENDING` | ARMED, awaiting P-TRIG; `watch_direction` published |
| 12 | `ENTRY_LOCATION_LOST` | P-BAND or P-VALIDITY CONTRADICTED by price outside the band |

`NO_EDGE` is not a reason. The MarketView (context state, setup state, scenario records, zones) is published beside the action in all cases.

## C15. Predicate case coverage (positive / negative / unknown)

| Predicate | SATISFIED example | CONTRADICTED example | UNKNOWN example |
|---|---|---|---|
| P-DATA | SYN-L01 | — | SYN-S08 (stale 1m at trigger) |
| P-SCALE | SYN-L01 | — | REAL-FIX-01 (20 min of evidence) |
| P-CTX | SYN-L01 | SYN-S04 (NOT_DIRECTIONAL) | REAL-FIX-01 |
| P-IMP | SYN-S01 | SYN-S04 (leg too small) | SYN-L08 (missing minute in leg) |
| P-REACT | SYN-L01 | SYN-L03 (deep), SYN-S06 (opposing), SYN-L06 (stall) | SYN-L08 |
| P-NOFAIL | SYN-L07 (wick below A, close above) | SYN-L03 (outcome: close below A) | SYN-L08 |
| P-TGT | SYN-L01 | SYN-S03 variant `NOTGT` (no eligible zone beyond band) | SYN-L08 |
| P-GEOM | SYN-L01 | SYN-S03 (obstacle) | SYN-L08 (target unknown) |
| P-COST | SYN-L05 (VIABLE) | SYN-L10 (DOMINATES) | SYN-L01, SYN-S01 (UNRESOLVED) |
| P-TRIG | SYN-L01 | SYN-L02 variant `PRE` (invalidation before trigger) | SYN-S08 |
| P-BAND | SYN-L05 | SYN-L04 (entry lost) | — |
| P-VALIDITY | SYN-L05 | SYN-L04 variant `B` (price leaves band during window) | SYN-S08 |
| P-INTACT | SYN-L01 | SYN-L02 | SYN-L09 (same-bar ambiguity) |
| P-EXCL | SYN-L05 | SYN-S02 variant `EXCL` (short trigger while a long thesis tracks) | — |
| P-SCALEBAND | SYN-L01 | SYN-S06 variant `SCALE` (5m TR spike) | REAL-FIX-01 |

(`—` = cannot take that value by definition.)

## C16. Short mirror (exact)

| Long | Short |
|---|---|
| context UP (rising highs/lows, close above L₂) | context DOWN (falling lows/highs, close below H₂) |
| impulse A (swing low) → B (swing high), B above prior swing high | impulse A (swing high) → B (swing low), B below prior swing low |
| reaction extreme R = lowest low since B | R = highest high since B |
| D = (B − R)/I | D = (R − B)/I |
| structural failure: completed 5m close < A | completed 5m close > A |
| anchor bar: latest completed 5m bar with low = R; K = anchor.high | latest completed 5m bar with high = R; K = anchor.low |
| trigger: completed 1m close ≥ K + tick | completed 1m close ≤ K − tick |
| V = R − b; invalidation: 1m low ≤ V | V = R + b; 1m high ≥ V |
| entry band [K, K + e] | [K − e, K] |
| target: nearest eligible resistance-side zone with near edge T_near > K + e | nearest eligible support-side zone with near edge T_near < K − e |
| G = T_near − (K + e); Rd = (K + e) − V | G = (K − e) − T_near; Rd = V − (K − e) |
| response: 1m high ≥ K + 0.5 (T_near − K) | 1m low ≤ K − 0.5 (K − T_near) |
| target reached: 1m high ≥ T_near | 1m low ≤ T_near |

Long and short are evaluated and reported separately; syntactic symmetry is not a claim of behavioral symmetry.

## C17. Unresolved policy questions (for Director review; not decided by outcomes)

- **U-C1 — wick vs close at the impulse origin.** Structural failure uses completed 5m *closes* beyond A; a wick-only full retracement is OPPOSING_INITIATIVE (SYN-L07). Whether a wick beyond the origin should also end the setup is a professional-fidelity question.
- **U-C2 — outage while ARMED.** Hidden minutes keep trigger/invalidation UNKNOWN until setup expiry (SYN-S08). An alternative (re-arm after N clean minutes with a new revision) is plausible but adds a convention; left open.
- **U-C3 — 1m trigger inside a forming 5m bar.** The trigger minute may belong to a 5m bar that later makes a lower low (A U-A2). Handled by invalidation/ambiguity rules; behavioral adequacy needs review on real cases.
- **U-C4 — cost envelope verification.** DC-26 is unverified against OKX's public fee schedule (RP-001D D4).
- **U-C5 — no unconditional scenario preference.** v1 publishes only conditional claims before a trigger. Whether a professional MarketView should state an unconditional preference (and how to score it) is deferred.

## C18. Illustrative invented episode (not BTC evidence, not a recommendation)

S5 = 60.0 (frozen). Context UP. A = 83,000.0 (swing low), B = 83,400.0 (confirmed swing high): I = 400.0 ≥ 4 × 60 = 240 ✓; B above prior swing high 83,250 ✓; n_I = 5 bars, v_I = 80/bar. Reaction low R = 83,230.0 after 3 bars: D = 170/400 = 0.425 ✓, v_R = 56.7/bar, ρ = 0.71 ✓. Anchor bar high K = 83,270.0. b = max(0.1, 15.0) = 15.0 → V = 83,215.0. e = 30.0 → band [83,270.0, 83,300.0]. Target: B's zone near edge = 83,400 − 15 = 83,385.0 (z = 0.25 × 60). G = 83,385 − 83,300 = 85.0; Rd = 83,300 − 83,215 = 85.0; G ≥ 1.0 × Rd ✓ (boundary). G_bps ≈ 10.2 bps → c_high 16 > 0.25 × 10.2 and c_low 5 ≥ 0.5 × 10.2 = 5.1? No (5 < 5.1) → **UNRESOLVED** → public NO_TRADE `COST_OR_DELAY_VIABILITY_UNRESOLVED` even if triggered. The continuation scenario is still activated and tracked at trigger. This arithmetic illustrates the RP-001D concern that 5m-scale geometry is small relative to costs.
