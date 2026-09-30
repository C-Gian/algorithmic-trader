# RP-001B — Causal Structure and Reference Areas

Status: PROPOSED (specification only — no swing/level/indicator code exists or is authorized)  
Depends on: [RP-001A](RP-001A-PROCESS-TRANSLATION.md). Numbers: [`DESIGN-CONVENTIONS.yaml`](DESIGN-CONVENTIONS.yaml).

## B0. Principles

1. Every structural object has **identity, method version, event interval, extremum time, confirmation (known-at) time, frozen scale, dependency references and status**. Its known-at can never precede the known-at of its last required input.
2. Nothing is drawn or used before it is confirmed. A provisional running extreme is labeled provisional.
3. No hindsight pivots, no adaptive widening, no merging, no automatic role flip.
4. Unknown is a state, never false and never neutral.

Method identifier proposed for this specification: `structure.dc.v1` (directional-change swings on completed bars with frozen median-TR scale).

## B1. Higher-timeframe aggregation completeness

- Windows: UTC-aligned half-open `[t, t+5m)` and `[t, t+1h)` (DC-01).
- A derived bar is **COMPLETE** iff all 5 (or 60) constituent traded 1m slots are VALID `bar_observation` events whose `available_time ≤ cutoff`. OHLC = first open, max high, min low, last close; typed volumes summed (descriptive only). `known_at = max(constituent available_time)` (DC-02).
- **PENDING**: some constituent not yet known at the cutoff (e.g. a 10:59 minute has arrived, the 11:00-close 1h bar is still pending until the 10:59 slot is known — which *is* its close; an early constituent never completes the bar).
- **QUALITY_AFFECTED**: any constituent is a `slot_quality` event (MISSING, INVALID_ROW, INCOMPLETE_REJECTED, CONFLICTING_DUPLICATE, EXCLUDED_UNCLASSIFIED). Never bridged, never partially summed.
- **BEYOND_COVERAGE / RECORDER_OUTAGE**: no event exists because evidence cannot speak for that time (recorded outage or coverage end). Treated like PENDING forever: the bar is not complete. This is not a market gap and must not be labeled MISSING.
- Required history for any predicate is **contiguous COMPLETE bars**; a non-complete bar inside a required window makes the dependent predicate UNKNOWN.

The accepted reducer's bounded `history` is not proof of contiguity; completeness must be checked per slot (SR-002 §6).

## B2. Variability scale (frozen)

- `S` per role: median true range of the last 24 contiguous COMPLETE bars of that role ending at the reference bar (DC-03). S5 covers 2 h of 5m bars; S1h covers 24 h of 1h bars.
- Unavailable if fewer than 24 contiguous complete bars → all S-dependent predicates UNKNOWN.
- **Freeze points** (DC-04): a 1h leg uses S1h frozen at the confirmation that began it; 5m swings use S5 frozen at the start of the current 5m structure epoch (DC-30); a zone uses S at its creation; an opportunity uses S5 at each (re)arming revision; an issued recommendation never changes.
- All S-derived distances are rounded up to 0.1 USDT ticks (DC-08).

## B3. Swing candidates, confirmation, and directional legs (`structure.dc.v1`)

Candidate procedure (directional change). It is **a candidate**, retained here because it is causal, deterministic and has one scale-relative parameter. A simpler alternative is considered in B12.

State per role series: `mode ∈ {INIT, UP, DOWN}`, running extreme `(P, t_P)`, threshold `θ = k × S_frozen` with k = 2.0 (DC-05).

**Where each series starts (DC-30).** The 1h procedure runs **incrementally from the start of contiguous history** (after its 24-bar scale warm-up) and never restarts. The 5m procedure runs in **epochs**: for a long assessment the epoch origin is the extremum bar of the most recent confirmed 1h swing LOW known at the evaluation instant (short: swing HIGH); the 5m procedure starts at that bar in INIT with S5 frozen from the 24 complete 5m bars ending at the origin. A new epoch begins only when a newer 1h swing of that role is confirmed; objects of earlier epochs stay in history, unchanged, but are not used for new setups. (Pre-data revision: an earlier draft restarted 5m tracking on a sliding lookback, which would relabel past swings as the window moved.)

Process each newly COMPLETE bar `b` in time order (never a pending/quality-affected bar; a non-complete bar **suspends** the series — see B5):

- **INIT.** Track running max `(Hmax, t)` and running min `(Lmin, t)` from the first bar after S is available. The first time `b.low ≤ Hmax − θ` → confirm swing HIGH at `(Hmax, t_Hmax)`; mode DOWN from `b`. The first time `b.high ≥ Lmin + θ` → confirm swing LOW; mode UP. If both occur in the same bar → AMBIGUOUS_PATH; stay INIT and continue.
- **UP** (running high `(H, t_H)`):
  1. If `b.high > H` **and** `b.low ≤ H − θ` → **same-bar ambiguity** (DC-07): treat as extension (`H ← b.high, t_H ← b.t`), flag `AMBIGUOUS_PATH`, no confirmation on this bar.
  2. Else if `b.high > H` → extension. Equal highs do not extend (DC-06).
  3. Else if `b.low ≤ H − θ` → **confirm swing HIGH** `(H, t_H)`. `confirmed_at = b.known_at`. Switch to DOWN with running low `(b.low, b.t)` and a new θ frozen now.
- **DOWN**: exact mirror.

Outputs:

| Object | Fields |
|---|---|
| `Swing` | id, role (5m/1h), kind HIGH/LOW, price, extremum_time `t_P`, confirmed_at, θ used, S frozen, flags (AMBIGUOUS_PATH), method version |
| `Leg` | from swing → to swing, direction, size, duration in completed bars, speed = size/duration |
| `RunningExtreme` | provisional; kind, price, time, since_confirmation; **never** a swing |

**Extremum time vs confirmation time.** A swing high at 10:15 confirmed by the 10:35 bar is *known from 10:40* (the bar's known_at). Any predicate evaluated at 10:39 must see only a provisional running extreme.

## B4. Initialization and warm-up

| Role | Requirement before assessable |
|---|---|
| 1h | 24 complete 1h bars for S1h, then the incremental procedure; context needs ≥ 72 contiguous complete hours of history and ≥ 2 confirmed swing highs and ≥ 2 confirmed swing lows with extremum inside the last 48 complete 1h bars (DC-09). |
| 5m | a current epoch (DC-30) with S5 available from the 24 complete 5m bars ending at the epoch origin, and confirmed swings A (origin of the impulse) and B (impulse extreme) inside the epoch; progress is measured against the epoch high-water mark before A (DC-31). |

Before that: `WARMUP` (public reason `WARMUP_OR_REQUIRED_DATA_UNAVAILABLE`). The 1h result depends on where contiguous history begins (initialization); this is recorded, and the context rule uses only the latest two confirmed highs/lows, which are rarely affected once several swings exist. A stability check (history start shifted by ±1 bar) is registered in RP-001E.

## B5. Gaps, outages, late data

- A non-complete bar in the series **suspends** the procedure: no extension and no confirmation can be computed across it. On resumption, the running extreme is kept but marked `GAP_AFFECTED` (the missing bar might have held a more extreme price). A swing confirmed after a gap-affected extreme carries the flag; any setup depending on it is UNKNOWN until the gap-affected leg is superseded by a later clean confirmation.
- Late constituents delay the derived bar; they never rewrite already-published derived bars (first-completed evidence only; no revision path exists yet — SR-002 §6).

## B6. Setup pullback boundary (long; short mirrors)

Given impulse A→B (RP-001A A2) and the reaction observed on completed 5m bars:

- **Reaction extreme** `R` = lowest low of completed 5m bars after B's bar (provisional until the opportunity ends).
- **Anchor bar** = the most recent completed 5m bar whose low equals `R`. **Recovery boundary** `K = anchor.high`.
- **Local invalidation** `V = R − b`, b = max(1 tick, 0.25 × S5 frozen at arming) (DC-14). Crossed by a completed 1m low ≤ V.
- **Re-anchoring (pre-trigger only).** A later completed 5m bar with a lower low (still above A, reaction still CONTROLLED) re-anchors: new K, R, V and a new opportunity **revision** (same opportunity id, revision+1, reason `REANCHOR`). After a trigger or issuance, geometry is immutable (DC-04).

## B7. Horizontal reference areas (zones)

**Creation.** Each confirmed swing (5m or 1h) creates one zone at confirmation time: swing HIGH at price P → resistance-side zone `[P − z, P]`; swing LOW → `[P, P + z]`, z = 0.25 × S_role (DC-16) frozen at creation. Zone id = swing id. Roles are **locational descriptions** ("prior swing high area"), not claims of latent supply/demand.

**Interaction events** (recorded append-only, each with known-at):

| Event | Definition (resistance-side zone; support mirrors) |
|---|---|
| APPROACH | a completed 1m high within 1 × S5 below the zone's near edge |
| TOUCH | a completed 1m high ≥ near edge `P − z` |
| PENETRATION | a completed 1m high > P |
| CLOSE_BEYOND | a completed 5m close > P |
| RETURN | after CLOSE_BEYOND, a completed 5m close < `P − z` |

A touch alone is not rejection; a wick is not a trapped-trader fact.

**Revision.** None. A new swing near an old one creates a separate zone; displays may group nearby zones visually, preserving identities. No adaptive merging, no widening.

**Weakening.** v1 records interactions but does not score them: whether repeated touches strengthen or consume a zone is a source disagreement/empirical question (EXT-003 found publisher strength ratings uninformative; EXT-002 skeptical). Not used in rules.

**Invalidation (BROKEN).** CLOSE_BEYOND marks the zone BROKEN: it is no longer eligible as a target or obstacle for this method. **No automatic role flip** — a broken resistance is not promoted to support; a new support claim would require a new swing and a new zone.

**Ageing/retirement.** 5m-origin zones retire 24 h after confirmation; 1h-origin zones 7 days (DC-22). Retired/broken zones remain in history (auditable) but are ineligible. Data loss suspends interaction assessment (no inferred "held").

## B8. Nearest defensible opposing destination (long; short mirrors)

At arming, candidate destinations are **eligible zones** (not broken, not retired, confirmed before the arming known-at) on the **opposing side above the entry band**: resistance-side zones from 5m and 1h swings, including the impulse extreme B's own zone. The **primary target** is the eligible zone whose near edge `T_near = P − z` is the lowest price strictly above the entry band's worst edge `K + e`. If none exists → `NO_TARGET` (the method withholds action; it never fabricates a distance or a reward multiple).

Because any older resistance zone between A and B was necessarily closed beyond by the impulse (or not — if the impulse only wicked through it, the zone is *not* broken and **is** a nearer obstacle), the obstacle case arises naturally: a prior swing high that the impulse penetrated but did not close beyond remains a nearer destination and can make room insufficient (case SYN-S03 mirror).

## B9. Context structure (1h)

Uses the same procedure on complete 1h bars with S1h (B3) and the rule in RP-001A A1. The context result is `UP | DOWN | NOT_DIRECTIONAL | UNKNOWN`, with its dependency references (the four swings, the last complete 1h close, S1h). 1h swings also create zones (B7) that can be destinations/obstacles.

## B10. Same-bar ambiguity catalogue

| Where | Situation | Rule |
|---|---|---|
| Swing extraction | bar extends extreme and reaches θ from prior extreme | extension + AMBIGUOUS_PATH, confirm later (DC-07) |
| Arming vs trigger | the anchor 5m bar is the same period that contains the trigger minute | impossible by construction: trigger minutes start at/after the anchor bar's end |
| Trigger vs invalidation | one 1m bar has low ≤ V and close ≥ K + tick | order unknown → opportunity **UNASSESSABLE** (withdrawn; no LONG), reason `SAME_BAR_AMBIGUITY` |
| Target vs invalidation (post-activation) | one 1m bar has high ≥ T_near and low ≤ V | thesis `AMBIGUOUS_ORDER`; both outcome bounds reported; never target-first |

## B11. Replay of annotated prefixes

The synthetic cases in [`cases/`](cases/) exercise B3–B10 predicates with declared S values; the real cases apply the same definitions to accepted OKX evidence prefixes (see `cases/SELECTION-PROTOCOL.md`). Consistency requirement: the same visible prefix must yield the same labels regardless of what follows; any case where a label would need the suffix is recorded as a definition failure.

## B12. Simpler alternative considered (contrast, not adopted)

**Fixed-window pivots** (a bar is a pivot high if its high exceeds the n bars on each side) are simpler but confirm exactly n bars late regardless of reaction size and ignore scale; they label tiny wiggles as structure in quiet markets and miss structure in fast ones. DC swings tie confirmation to a scale-relative reaction, which is the distinction the process needs ("a reaction worth the name"). The directional-change candidate is retained; this contrast may be run later as a predeclared stability check, not as a search.

## Limitations recorded

- **L-B1.** Directional-change confirmation always lags the extreme by at least θ of counter-movement: the impulse extreme B is known only once the pullback has already reached 2 × S5. Setups can never be detected earlier than that.
- **L-B2.** Pullbacks shallower than 2 × S5 are invisible to this method (the impulse is still "developing"). This is a deliberate coverage limit.
- **L-B3.** 1h results depend on where contiguous history begins (INIT); 5m results depend on the epoch origin (DC-30). Both are deterministic from the prefix; epoch restarts are counted and reported.
- **L-B4.** Zone tolerance and retirement are conventions; EXT-003's five-day persistence is FX-specific.
- **L-B5.** No revision path for corrected data exists; the first completed evidence rules.
