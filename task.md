# Active Task — RP-001: First Professional Trader Formalization Research

Status: READY  
Owner: Project & Research Director  
Executor: Claude Code  
Type: bounded research / formalization — **NO PRODUCTION TRADER CODE**

## Read first

Read in full:

1. `FOUNDATION.md`
2. `STATE.md`
3. `AGENTS.md`
4. `strategic_reviews/ASTRA-SR-002-REVIEW.md`
5. `strategic_reviews/SR-002-DIRECTOR-DISPOSITION.md`
6. `research/RP-001-FIRST-TRADER-FORMALIZATION.md`

Then follow the reading/source instructions inside RP-001.

## Objective

Execute only RP-001.

The accepted first professional trader **candidate** is:

**directional context → move/reaction assessment → conditional continuation opportunity → trigger → actionability → LONG/SHORT/NO_TRADE → reassessment**

The first actionable playbook candidate is continuation after a controlled pullback/reaction.

Your job is to make that process explicit, causal, falsifiable and auditable before implementation.

## Hard stop

Do not create or modify production trader behavior.

Do not:

- create `semantic.v2`;
- implement a derived-observation engine;
- implement swing/level/indicator code;
- generate real MarketViews or recommendations;
- add LONG/SHORT logic to the application;
- run profitability optimization;
- perform threshold/timeframe sweeps;
- modify `source_notes/`;
- add account sizing/leverage/execution;
- import legacy Trading Bot artifacts.

This task produces research/specification/case artifacts only.

## Required outputs

Produce all deliverables specified by:

`research/RP-001-FIRST-TRADER-FORMALIZATION.md`

including:
- RP-001A process translation;
- RP-001B causal structure/levels;
- RP-001C complete advisory policy;
- RP-001D actionability assumptions;
- RP-001E evaluation registration;
- causal case register and separate prefix/outcome case files;
- external source registry;
- real-case data requirement if adequate immutable BTC evidence is unavailable.

## Research configuration

Start with:
- 1h context;
- 5m setup;
- 1m trigger/reassessment;
- traded price for structural/trigger predicates.

These are research conventions, not proven parameters.

Do not change them because of outcomes.

If they cannot express the intended professional distinctions causally, document the failure before any outcome analysis. Do not choose replacements without Director review.

## Source discipline

Clearly mark:
- SOURCE-SUPPORTED;
- PROJECT ADAPTATION;
- DESIGN_CONVENTION;
- UNRESOLVED.

Do not convert a practitioner statement or an FX result into BTC evidence.

If external source retrieval is unavailable, state that explicitly instead of inventing content.

## Case discipline

Case selection is for concept formalization, not performance.

Must include:
- favorable;
- failed;
- ambiguous;
- insufficient-data;
- both long and short.

Outcome masking is mandatory.

Do not silently revise a prefix classification after seeing its suffix.

## Git workflow

Before editing:

`git pull --ff-only origin main`

Then perform only the RP-001 work, commit and push normally to `main`.

No force-push, reset or shared-history rewrite.

## Checks

Follow RP-001's lightweight checks.

No full product redesign or unrelated refactor.

## Completion report

Return exactly the completion information requested by RP-001, including:
- source verification status;
- design conventions;
- case counts/types;
- real-case gate;
- unresolved ambiguities;
- closure status for A–E;
- recommendation: ACCEPT / ACCEPT WITH SPECIFIC FOLLOW-UP / HOLD-REVISE / REJECT candidate.

Do not declare RP-001 accepted.

Final research acceptance and any authorization to implement the real trader belong to the Project & Research Director.
