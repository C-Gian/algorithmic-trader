# RP-001 — Director Review under Foundation v3.0

Status: **CLOSED AS DEVELOPMENT EVIDENCE — NOT ACCEPTED AS PRODUCTION METHOD**  
Date: 2026-09-30  
Reviewed base lineage: `f9da67c` → `38b2fb6`  
Current authority: `FOUNDATION.md` v3.0 and `STATE.md`

## Executive disposition

RP-001 is substantially complete as a bounded historical/formalization experiment and is retained as useful development evidence.

It is **not** accepted as:
- the production professional trader;
- the mandatory first trader;
- a gate that must be repaired before product work continues;
- evidence that the pullback-continuation candidate is economically useful on BTC;
- evidence that 1h/5m/1m, 120 minutes, or DC-01..DC-31 are production parameters.

Foundation v3.0 supersedes the earlier pullback-only/RP-001 mandate. The relevant output is therefore the evidence RP-001 created: causal definitions, failure modes, masking discipline, and concrete indications that this candidate translation is too restrictive in several ways.

## What was independently verified

### Commit/freeze chronology

The Git history confirms this sequence:

- `852ee08` — A–E formalization, design conventions, synthetic cases, selection protocol; committed before real data acquisition.
- `5c7e9a3` — acquisition/progress record.
- `a43dc45` — REAL-G01 prefix + frozen label.
- `53bf65b` — REAL-G02 prefix + frozen label.
- `544e206` — REAL-G03 prefix + frozen label.
- `85ae86f` — REAL-G04 prefix + frozen label.
- `972d6a2` — REAL-G05 prefix + frozen label.
- `0047ea6` — REAL-G06 prefix + frozen label.
- `38b2fb6` — only after all six freezes, real outcome exports/reveals plus final register/progress update.

Each real-case freeze commit contains only that case's prefix/label, except G01 also records the protocol amendment. The outcome files first appear in `38b2fb6`.

This supports the executor's claim that the six real labels were frozen before their corresponding outcome export/reveal.

### Protocol amendment A1

The original protocol would have allowed a later prefix to contain an earlier case's outcome period. The executor detected this before opening the later prefixes and changed the procedure to chronological one-case-at-a-time freeze.

That amendment is methodologically acceptable because it tightened masking before the affected evidence was viewed rather than after an outcome.

### Real-data acquisition

The executor's five-day public OKX acquisition is acceptable under the RP-001 process in force at the time.

`cases/SELECTION-PROTOCOL.md` explicitly predeclared:
- the public/read-only WP-003 `fetch-okx` workflow;
- the fixed window `[2026-09-25T00:00Z, 2026-09-30T00:00Z)`;
- verification before use;
- storage outside Git;
- six fixed 8-hour cutoffs.

Therefore acquiring that bounded dataset was not an unauthorized strategy/data-selection action.

This historical conclusion does not override Foundation v3.0's current Owner-operated data/backtest workflow requirements.

## YAML defects

The executor correctly reported that these frozen labels are not valid YAML:

- `REAL-G02.label.yaml`
- `REAL-G03.label.yaml`
- `REAL-G05.label.yaml`

The structural defect is that a sequence under `h1_series_continued_from_...` is followed by mapping keys at the same indentation level.

The files remain byte-identical to their freeze commits:

- G02 blob: `c84d4ef1647b20c205cd8b660d7870f79e15a3b0`
- G03 blob: `3b3650333654358cdc7667e8d35b8418c0c3c945`
- G05 blob: `d07a32a24518a2a810a4f44de757167c8993dc95`

### Director decision on the syntax-only edit

**Do not edit the frozen files.**

Foundation v3.0 explicitly requires frozen RP-001 labels/cases to remain byte-identical. The failed YAML check is retained as a known defect in the historical research artifact.

If future tooling genuinely needs these labels in machine-readable form, create a separate normalized/derived sidecar that:
- references the original frozen file and blob SHA;
- performs syntax-only structural normalization;
- never replaces or rewrites the frozen original;
- makes clear that the semantic label is historical evidence, not current production policy.

No such sidecar is required now.

## Assessment of the formalization work

### Useful retained work

RP-001 produced several durable lessons that remain compatible with Foundation v3.0:

- clear separation of SOURCE-SUPPORTED / PROJECT ADAPTATION / DESIGN_CONVENTION / UNRESOLVED;
- explicit causal completion and known-at semantics for derived bars;
- extremum time separated from swing confirmation time;
- explicit same-bar OHLC ambiguity rather than invented path order;
- immutable recommendation geometry as a useful advisory-lifecycle principle;
- separation of MarketView, opportunity, recommendation and thesis lifecycle;
- explicit UNKNOWN states rather than treating missing evidence as neutral;
- outcome masking and versioned reveal discipline;
- explicit warning against hidden-intent narratives and indicator double-counting;
- the need to diagnose coverage/frequency instead of celebrating NO_TRADE by itself.

These are reusable design/research patterns, not acceptance of the frozen candidate method.

### Candidate-method problems exposed by real cases

The six real cutoffs are far too small to estimate general trading frequency or profitability, but they exposed concrete translation problems.

1. **Context confirmation lag.** Confirmed 1h swing context can arrive late and can remain directional through a deep counter-move until a later swing is confirmed.
2. **Single-leg impulse bias.** Stair-step directional progress can be ignored because no individual 5m leg exceeds the frozen impulse threshold.
3. **Epoch high-water progress lockout.** DC-31 can make the method blind to new same-direction opportunities for many hours after a large counter-move.
4. **Geometry-floor construction.** With the impulse extreme usually serving as nearest target, shallow controlled pullbacks naturally have small remaining room while invalidation still includes meaningful downside distance. DC-17 therefore blocks many otherwise coherent setups by construction.
5. **Target-zone source gap.** The candidate does not fully specify which 5m swing series owns the target-zone set when long/short epochs use different structure state.
6. **Display-semantics gaps.** Some public reason wording does not cleanly match the actual state, including `SCENARIOS_CONTESTED` for a single-direction opposing reaction.
7. **Cost model dominates too early.** RP-001D's unverified 5–16 bps envelope plus DC-27 requires roughly 64 bps conservative room to classify an opportunity as VIABLE. That is a design consequence, not verified BTC execution economics.

These are not minor polish items. They show that the frozen pullback-only translation should not be promoted unchanged into the real adviser.

### What the real cases did not establish

The six grid cutoffs do **not** establish:

- that professional pullback continuation is unprofitable on BTC;
- that the product should abandon continuation setups;
- that the system will generally produce no calls;
- that another timeframe or threshold is superior;
- that the revealed later price path validates the frozen NO_TRADE decisions economically;
- that the 5–16 bps cost envelope is realistic;
- that the old 1h/5m/1m structure should be optimized.

They are development cases, not a representative outcome study.

## Closure status relative to the old RP-001 brief

Under the historical RP-001 brief:

- A — process translation: materially completed.
- B — causal structure/reference areas: materially completed but contains a known zone-source definition gap and exposed structural limitations.
- C — advisory policy: materially completed as a specification but retains unresolved policy questions and wording gaps.
- D — actionability assumptions: completed as a declared assumption set, but the fee/spread/slippage envelope is explicitly unverified.
- E — evaluation registration: materially completed.

The real-case gate was completed.

However, one required repository check failed because three frozen label files are invalid YAML. Therefore RP-001 cannot honestly be called a fully clean PASS under its original checklist.

Foundation v3.0 makes repairing that historical checklist unnecessary as a product gate.

## Final Director disposition

**RP-001 is closed and retained as development evidence.**

It is neither discarded nor promoted to production.

The pullback candidate remains one potentially reusable professional component, but its old mandatory scope and its numeric conventions are superseded by Foundation v3.0.

No frozen case/label is modified by this review.

No production trader code, schema, source dossier or evaluation result is changed.

## Workflow state

Per the Owner's direct instruction in the current conversation, the Director does not issue or describe the next implementation package yet.

The project is paused for the Owner's clarification before further direction.
