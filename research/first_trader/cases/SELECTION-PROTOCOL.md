# RP-001 Real-Case Selection and Outcome-Masking Protocol

Status: **PREDECLARED** — committed and pushed before any real BTC evidence beyond the accepted 20-minute test fixture was acquired or viewed by the executor.

## 1. Evidence source and acquisition (accepted workflow only)

- Instrument / source: OKX `BTC-USDT-SWAP`, public read-only history, via the accepted WP-003 workflow:
  `uv run algotrader data fetch-okx --start 2026-09-25T00:00Z --end 2026-09-30T00:00Z --root <data root>`
  then `uv run algotrader data verify <dataset_id> --root <data root>`.
- Window rule (fixed now, not chosen from prices): **the five complete UTC days immediately preceding the RP-001 start date (2026-09-30)**: `[2026-09-25T00:00Z, 2026-09-30T00:00Z)`.
- The dataset lives outside Git (data root). Only bounded excerpts produced by `tools/export_case_excerpt.py` are committed; each carries the dataset id, manifest SHA-256, feed content identity and ordered-event hash, so the excerpt is re-derivable.
- If acquisition fails or verification fails, no real grid case is produced and `REAL-CASE-DATA-REQUIREMENT.md` is written instead.

## 2. Cutoff grid (all cases, whatever they show)

Six cutoffs, every 8 hours, each with ≥ 72 hours of prior evidence and ≥ 4 hours of later evidence inside the window:

| Case | Visible-prefix cutoff (UTC) |
|---|---|
| REAL-G01 | 2026-09-28T04:00Z |
| REAL-G02 | 2026-09-28T12:00Z |
| REAL-G03 | 2026-09-28T20:00Z |
| REAL-G04 | 2026-09-29T04:00Z |
| REAL-G05 | 2026-09-29T12:00Z |
| REAL-G06 | 2026-09-29T20:00Z |

No cutoff is added, moved or dropped after acquisition. A cutoff that shows `NO_SUPPORTED_SETUP`, `CONTEXT_OUTSIDE_METHOD` or `WARMUP` remains a case. Case categories for real cases are therefore **whatever the prefix shows**; required categories not observed in real prefixes remain covered by synthetic mechanics cases and are reported as not observed in real evidence. (Selecting real cutoffs for "failed recovery" or "target/invalidation ambiguity" would require looking at outcomes; that is not done.)

## 3. Causality of the prefix

- Availability: MODELED zero-extra-delay (`feed.modeled.v1(bar+PT0S,funding+PT0S)`): a 1m bar is known at its close.
- A prefix contains only feed events with `available_time ≤ cutoff`, aggregated per RP-001B B1 (complete-only 1h/5m bars).
- Prefix content: all 1h bars known at the cutoff (from window start), 5m bars of the last 12 hours (extended backwards to the 5m epoch origin if that is older — still prefix-only), 1m bars of the last 60 minutes, and the latest mark/index/settled-funding values (factual context; never used in predicates).

## 4. Labeling (before any outcome is exported)

1. Export all six prefixes (`tools/export_case_excerpt.py prefix`). The outcome command is **not run** in this step.
2. Apply RP-001A/B/C and `DESIGN-CONVENTIONS.yaml` exactly as committed, by hand, with arithmetic aids only (sorting/median, subtraction). No swing, level or policy code is written or run. Every intermediate (S1h, S5, swings with extremum/confirmation times, epoch origin, impulse, reaction, K/V/band/target, predicates) is recorded in `prefixes/REAL-Gxx.label.yaml`.
3. Where a definition cannot be applied to the prefix without judgement, record `DEFINITION_GAP` with the exact point — do not improvise a rule.
4. **Freeze**: commit and push all prefixes and labels. The commit SHA is the freeze point.

## 5. Reveal (after the freeze commit exists on `origin/main`)

1. Run `tools/export_case_excerpt.py outcome` for each cutoff (horizon 240 minutes) into `outcomes/REAL-Gxx.json`.
2. Apply the frozen rules forward on the suffix (triggers, invalidation, target, deadlines) and record in `outcomes/REAL-Gxx.reveal.yaml` whether the case **supports** the formalization, **exposes ambiguity**, **falsifies/narrows** a definition, or **reveals a missing-data requirement**.
3. Prefix labels are never edited after the freeze. Any rule change prompted by a reveal is recorded as a new versioned proposal (`DESIGN-CONVENTIONS.yaml` revision marked `post-reveal`) and is not applied retroactively to the frozen labels.

## 5a. Amendment A1 (recorded after export, before any real prefix was viewed)

Later prefixes contain earlier cutoffs' 4-hour outcome windows (e.g. REAL-G02's prefix covers REAL-G01's suffix). Therefore labels are frozen **one case at a time in chronological order**: each `REAL-Gxx.json` + `REAL-Gxx.label.yaml` is committed and pushed before the next prefix is opened. Prefixes were exported with `--m5-hours 24` (a superset of the 12 h in §3).

## 6. What the real cases can and cannot show

They test whether the definitions can be applied to real causal prefixes consistently and without hidden discretion, and they expose data/definition gaps. Six cutoffs from five days are not a performance sample; no hit rate, return or profitability is computed or implied.
