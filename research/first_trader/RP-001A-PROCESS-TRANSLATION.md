> **HISTORICAL SCOPE NOTICE — 30 September 2026.** FOUNDATION.md v3.0 implements the Owner's direct clarification and supersedes inconsistent scope/workflow instructions below. This document is retained as historical/advisory evidence. Its former ACCEPTED/READY/HOLD status is not current authorization. In particular, the mandatory pullback-only path, blanket cycle/news deferrals and RP-001 closure gate are no longer project direction. Reuse compatible findings only through the current task; preserve original evidence and failed cases. See the current FOUNDATION.md, STATE.md and task.md.

# RP-001A — Process Translation

Status: PROPOSED (research artifact; no production code)  
Scope: the fixed candidate process **directional context → move/reaction assessment → conditional continuation opportunity → trigger → actionability → LONG/SHORT/NO_TRADE → reassessment**  
Numbers: every numeric value is a `DESIGN_CONVENTION` from [`DESIGN-CONVENTIONS.yaml`](DESIGN-CONVENTIONS.yaml) (cited as DC-xx). Structural objects (swings, legs, zones) are defined in [RP-001B](RP-001B-CAUSAL-STRUCTURE-LEVELS.md).

## Evidence labels used throughout

| Label | Meaning |
|---|---|
| **SOURCE-SUPPORTED** | A statement actually made in a source read for RP-001 (dossier or verified external text, cited). |
| **PROJECT ADAPTATION** | Our operational translation of a source idea into observable BTC predicates. Not claimed by the source. |
| **DESIGN_CONVENTION** | A value/choice not supported by any source, made to render a distinction explicit (DC-xx). |
| **UNRESOLVED** | A question RP-001 could not settle; stated with what would resolve it. |

## What the sources actually support (and do not)

**Read directly for RP-001:** EXT-001, EXT-002 (Grimes web texts), EXT-003 (Osler 2000 full PDF), EXT-004 (Osler SR125 intro/conclusions) — see [`knowledge/external_registry.yaml`](../../knowledge/external_registry.yaml). **Read only through the immutable dossiers** (not the underlying books): LIB-002, LIB-003, LIB-004, LIB-005, LIB-008, LIB-012, LIB-020.

1. **Pullback continuation is an established practitioner process family.** EXT-001: “The pullback is a trade intended to enter a trending market … the alternation of with-trend legs with counter-trend pullbacks”; entry “as the market turns back into the trend (on a breakout of the pattern) or somewhere near the bottom (on a failure test).” Complex pullbacks: a first resumption attempt can fail before a second succeeds. *SOURCE-SUPPORTED.*
2. **The character of the reaction to a strong move is the informative object.** EXT-002: “how far it will extend, how quickly, and how the next pause might set up another trade”; if the market “goes dull and flat, or even turns back down,” the edge favors the other side. *SOURCE-SUPPORTED as a practitioner judgement on one S&P example; no thresholds.*
3. **Expected vs observed response is information; bounded invalidation and time stops are recurrent.** LIB-005 §§13, 14.4–14.5, 15.3 (Bandazian time stops, Chiu reaction mismatch, Berry “fantastic fill”). *SOURCE-SUPPORTED (dossier), practitioner evidence with survivorship bias.*
4. **Context conditions setup meaning; roles differ (selection, direction, timing, risk, execution).** LIB-005 §§6, 12, 14.2, 15.1; LIB-004 §18. *SOURCE-SUPPORTED (dossiers).*
5. **Multiple trend transforms are not independent evidence.** LIB-008 §§21.1–21.5. *SOURCE-SUPPORTED (dossier).*
6. **Practitioner skepticism about levels and ratios.** EXT-002: support/resistance “mostly coincidence”, “retracement rations don't really work” (author's summary of unpublished work). *SOURCE-SUPPORTED as a constraint on claims.*
7. **Level effects can exist in specific settings.** EXT-003: FX firm-published levels predicted intraday trend *interruptions* modestly (60.8% vs 56.2% bounce frequency), varying by firm and currency. *SOURCE-SUPPORTED for FX 1996–98 published levels; not for BTC or for generated zones, and not for continuation.*

**No source supplies** a swing threshold, impulse size, depth limit, speed ratio, trigger boundary, entry band, target rule, deadline or BTC evidence. All of those below are PROJECT ADAPTATIONS or DESIGN_CONVENTIONS.

LIB-005 contains no pullback-specific rule; it supports the *process shape* (context, conditional setup, response monitoring, bounded invalidation), not the pullback method itself. The pullback method's only direct source in RP-001 is EXT-001/EXT-002.

## Observable vocabulary (inputs)

Only causally available traded-price evidence from accepted `feed.v1` observable state, aggregated per RP-001B:

- completed 1h bars (context), completed 5m bars (setup), completed 1m bars (trigger/reassessment), each with `known_at`;
- the frozen variability scale S (S1h, S5) per DC-03/DC-04;
- confirmed swings, legs and reference zones from RP-001B with separate extremum and confirmation times;
- derived measurements: displacement, depth, bars elapsed, speed (displacement per completed bar).

Excluded as inputs of this method: mark, index and funding (factual context only), volume (descriptive only; SR-002 disposition §7), any hidden-intent attribute (smart money, trapped traders, stop hunts, accumulation), round numbers.

## Concept translations

Each concept: source support → proposed formalization (PROJECT ADAPTATION) → what it does not imply → positive / negative / ambiguous example (case IDs refer to [`cases/CASE-REGISTER.yaml`](cases/CASE-REGISTER.yaml)).

### A1. Directional progress (context and setup scale)

- **Source support.** EXT-001 (trend = alternation of with-trend legs and pullbacks); LIB-002 §8 and LIB-008 §21 (trend/persistence is a real information family, but transforms are redundant).
- **Formalization.** *Context* (1h, DC-09): **UP** iff the two most recent confirmed 1h swing highs are rising (H₁ < H₂), the two most recent confirmed swing lows are rising (L₁ < L₂), and no structural damage: the last complete 1h close is above L₂ and, if a down-leg is developing after H₂, its running low is still above L₂. **DOWN** mirrors. Otherwise **NOT_DIRECTIONAL** (overlapping/mixed) or **UNKNOWN** (fewer than 2+2 confirmed swings, scale unavailable, or a required 1h bar not complete). *Setup* progress: the 5m impulse extreme B exceeds every completed 5m high of the current 5m structure epoch before the impulse origin A (the epoch high-water mark, DC-31; a new high inside the current context leg for long).
- **Does not imply.** That the trend will continue; that UP is “bullish pressure”; any strength score; that 1h and 5m agreement are two independent confirmations (they share the same price path).
- **Examples.** Positive: SYN-L01 (context UP, HH/HL). Negative: SYN-S04 (context mixed → NOT_DIRECTIONAL). Unknown: REAL-FIX-01 (20 minutes of evidence; no 1h context).

### A2. Impulse / move

- **Source support.** EXT-002 (“sharp move”, “strong move”); displacement and speed are the dimensions the author names. “Conviction” is the author's interpretation and is **not** adopted.
- **Formalization.** An impulse is the most recent **confirmed** 5m directional leg A→B in the context direction (A = confirmed swing low, B = confirmed swing high for long) with size I = |B − A| ≥ 4.0 × S5 (DC-10), and B beyond the epoch high-water mark before A (A1 progress, DC-31). The 5m swings come from the current structure epoch (DC-30), whose S5 is frozen at the epoch origin. Duration n_I = completed 5m bars from A's bar to B's bar; speed v_I = I / n_I.
- **Does not imply.** Informed buying, participation, or that a large candle is a catalyst. Size relative to recent variability is all it measures.
- **Examples.** Positive: SYN-L01, SYN-S01. Negative: SYN-S04 (leg < 4 × S5). Unknown: SYN-L08 (a constituent minute missing inside the leg → impulse not assessable).

### A3. Controlled reaction / pullback

- **Source support.** EXT-001 (counter-trend pullback leg), EXT-002 (reaction “how far … how quickly”).
- **Formalization.** The reaction is the counter-leg after B, observed on completed 5m bars, with running extreme R (lowest completed 5m low since B, long). Depth D = (B − R)/I; reaction speed v_R = (B − R)/n_R with n_R completed 5m bars since B's bar; ratio ρ = v_R / v_I. **CONTROLLED** iff D ≤ 0.50 (DC-11) **and** the speed ratio is either not yet assessed or ρ ≤ 1.0 (DC-12: ρ is assessed only when D > 0.25 and n_R ≥ 3) **and** OPPOSING_INITIATIVE has not been observed on this reaction **and** n_R ≤ 3 × n_I (DC-13) **and** no completed 5m close below A. Note: because B is confirmed only after a reversal ≥ 2 × S5 (DC-05), every observable reaction already has depth ≥ 2 × S5 / I.
- **Does not imply.** That the pullback “will hold”; that 0.50 is a meaningful ratio (it only encodes “most of the impulse's progress is retained”, DC-11); that buyers are absorbing.
- **Examples.** Positive: SYN-L01. Negative: SYN-L03 (D = 0.615, DEEP). Ambiguous: SYN-S05 (D = 0.50 and ρ = 1.0 exactly; classified by the strict rule, flagged as sensitive).

### A4. Overlap / indecision

- **Source support.** EXT-002 (“goes dull and flat” after a strong move favors the other side). LIB-002 §8 (trend struggles when range-bound).
- **Formalization.** At setup scale **INDECISIVE** iff the reaction has lasted n_R > 3 × n_I completed 5m bars without a confirmed trigger (stall), or there is no qualifying impulse because the latest confirmed 5m legs fail the progress test (A1) in both directions (nested swings). At context scale, NOT_DIRECTIONAL (A1).
- **Does not imply.** That a breakout is imminent, or that the opposite direction is preferred; only that the move/reaction relationship this method needs is absent.
- **Examples.** Positive (indecisive): SYN-S04. Negative: SYN-S01. Ambiguous: SYN-L06 (stall allowance ends inside the setup-expiry window; both clocks apply, earliest wins).

### A5. Opposing initiative

- **Source support.** EXT-002 (“or even turns back down”); LIB-005 §14.5 (failure to behave as expected is information).
- **Formalization.** **OPPOSING_INITIATIVE** iff an assessed ρ > 1.0 (D > 0.25 and n_R ≥ 3: the counter-move is faster per bar than the impulse over a comparable span), or D ≥ 1.0 without a completed close beyond A (full retracement on wicks). Once observed it is sticky for that reaction (DC-12 r3). It takes precedence over REACTION_DEEP when both hold.
- **Does not imply.** A reversal trade (out of scope, SR-002), that the context has flipped, or who is trading.
- **Examples.** Positive: SYN-S06. Negative: SYN-L01. Ambiguous: SYN-S05.

### A6. Structural damage / failure

- **Source support.** EXT-001 (complex pullback: the resumption effort fails); LIB-005 §14.5.
- **Formalization.** Setup **STRUCTURAL_FAILURE** iff a completed 5m close is beyond the impulse origin A (below A for long). Context damage: a complete 1h close below the most recent confirmed 1h higher low L₂ (long context) → context no longer UP. Local thesis failure (after trigger) is the local invalidation V (RP-001C), which is narrower than setup failure.
- **Does not imply.** That the opposite trend has begun; the broader MarketView may still describe the larger context separately.
- **Examples.** Positive: SYN-L03 (after reveal, close below A). Negative: SYN-L01. Ambiguous: SYN-L07 (wick below A but close above → not failure; flagged).

### A7. Continuation-supporting response (trigger)

- **Source support.** EXT-001: enter “as the market turns back into the trend (on a breakout of the pattern)”. LIB-005: expected response should follow promptly.
- **Formalization.** Recovery boundary K = high (long) of the anchor bar: the most recent completed 5m bar whose low equals the reaction extreme R. **Trigger** = the first completed 1m bar starting at or after the anchor bar's end whose close ≥ K + 1 tick (DC-23), evaluated only while the opportunity is ARMED. The alternative source entry style (“near the bottom, failure test”) is **excluded** in v1: it requires predicting the reaction low.
- **Does not imply.** That the pullback is over; it is the observable event that activates the conditional continuation scenario.
- **Examples.** Positive: SYN-L01. Negative: SYN-L02 (recovery fails; invalidation first). Ambiguous: SYN-L09 (one 1m bar spans both V and K).

## Scope exclusions (explicit)

| Excluded | Reason |
|---|---|
| Complex pullbacks after a failed trigger | A second attempt within the same reaction is re-entry; v1 forbids it (RP-001C §12). Grimes notes such structures can precede strong moves; this is a known coverage loss. |
| Failure-test entries near the pullback low | Requires anticipating the low; not a response-confirmed entry. |
| Reversal entries | Out of scope (SR-002). A failed continuation becomes a scenario outcome, never an automatic reversal. |
| Volume confirmation | Non-voting per SR-002 disposition §7; no source-grounded non-redundant role found in RP-001. |
| Round-number, trendline, profile levels | Deferred (SR-002). EXT-004 mechanism relies on order data we lack. |
| Hidden-intent narratives | Not observable; never stated as fact. |

## Unresolved

- **U-A1.** Whether 1h HH/HL with k = 2.0 produces enough assessable context in BTC's 24/7 flow (UNKNOWN frequency). Resolve by measuring UNKNOWN share on development data; not by changing k after outcomes.
- **U-A2.** Whether a 1m-close trigger is too early relative to the 5m reaction structure (a 1m recovery can occur while the 5m bar still makes a lower low). Handled mechanically by invalidation-first/ambiguity rules; the behavioral adequacy needs Director review of cases.
- **U-A3.** Whether “speed ratio” is better measured on closes than extremes. A predeclared contrast is allowed later; no search.
- **U-A4.** Professional-fidelity oracle: the author of these rules cannot be the sole judge (SR-002 §13). Director independent labeling of masked prefixes is required; until then this is an *internally coherent approximation*, not verified reproduction of expertise.
