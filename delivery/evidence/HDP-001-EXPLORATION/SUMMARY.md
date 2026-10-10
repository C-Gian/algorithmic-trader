# HDP-001 — Exploration (Sep–Dec 2025, already exposed development data)

Base `3ee1278`. Protocol [HDP-001](../../HDP-001-HOURLY-DIRECTIONAL-PERSISTENCE.md) · [Director decision](../../HDP-001-DIRECTOR-CLOSURE.md). The Director authorized the exploration phase only; verification stays INACTIVE. READY FOR DIRECTOR REVIEW — HDP-001 EXPLORATION ONLY; not accepted.

**This is an exploration on exposed data.** The protocol's §6 categories (favorable / unfavorable / inconclusive) apply to the verification only, so none is assigned here. There is no signal promotion and no conclusion about profitability or targets.

## Input and access

- **Input.** Only `delivery/evidence/MARKETVIEW-PERSISTENCE-TABULATION/samples.csv`, unchanged since `ced7b2f`. sha256 `8f04588f…0953`; the raw and LF-normalized hashes are equal.
- **Fields read.** `s_sample_time`, `s_persistence` (= the prediction, sign(C_t − C_(t−1))) and `s_outcome_1h` (= the outcome, sign(C_(t+1) − C_t) with exact endpoint). No MarketView field is read.
- **Not used.** No Owner, DB, cache, acquisition or replay.
- **Provenance limit.** These are the limits already accepted by the Director. The stored sample does not record the end of the last 1h bar or the anchor minute. They are backed by the run's complete coverage and by the identity outcome(t) = prediction(t+1h) on 2927/2927 hours.

## Population and exclusions

| Item | Count |
|---|---|
| Planned hourly cutoffs [2025-09-01T00Z, 2026-01-01T00Z) | 2928 |
| With directional prediction (UP/DOWN) | 2928 |
| PREDICTION_FLAT / PREDICTION_UNAVAILABLE | 0 / 0 |
| BOUNDARY_NOT_SCORED (cutoff 2025-12-31T23:00, endpoint = end; its stored outcome is never read) | 1 |
| OUTCOME_UNAVAILABLE | 0 |
| **Paired** (prediction UP/DOWN, outcome available) | **2927** |
| of which outcome FLAT (wrong for both) | 0 |

Reconciliation: 2928 = 2927 paired + 1 excluded hour, which carries exactly one flag. Flags are recorded separately even when they occur together.

## Constant reference (§4 rule)

Usable outcomes: UP 1471, DOWN 1456, FLAT 0. The rule gives **always UP** (more UP).

This exploratory figure is measured on the same sample used to choose the reference, so it is not independent evidence.

## Paired table (n = 2927, same timestamps)

| | Constant correct | Constant wrong |
|---|---|---|
| **Persistence correct** | 724 (both) | 709 (persistence only) |
| **Persistence wrong** | 747 (constant only) | 747 (neither) |

- **Accuracy:** persistence 1433/2927 = 0.4896; constant 1471/2927 = 0.5026.
- **Delta** = persistence − constant = −38/2927 = **−0.0130**.
- **95% moving-block bootstrap interval of Delta: [−0.0410, +0.0147].**
  - Settings: 168 h blocks, 10,000 resamples, seed 0, 0 resamples with a zero denominator.

## Reproducibility

| Item | Value |
|---|---|
| Environment | CPython 3.14.7, standard library only (no numpy) |
| Generator | `random.Random(0)`, Mersenne Twister MT19937. Block starts come from `randrange(N−L+1)`, in order resample 0…9999, block 0…17. |
| Grid and blocks | Full 2928-hour grid with masks kept; starts on {0…2760}, no circular wrap. 18 blocks: 17 × 168 h plus a final block truncated to 72 h. |
| Statistic | Delta* = (persistence hits − constant hits) / paired count, per resample; the reference stays fixed |
| Percentile convention | Hyndman–Fan type 7 (linear), p = 0.025 / 0.975. It agrees with `statistics.quantiles(n=40, method="inclusive")` within 1.7e−18. |
| Reproducibility checks | Two runs give byte-identical `results.json` and `hours.csv`; bootstrap Delta vector sha256 `adf224ea…488a`. An independent recount of the four cells directly from `samples.csv` gives identical values. |

All choices were fixed in the script header before the first run, and no alternative was tried.

## Artifacts

| File | Content |
|---|---|
| [explore_hdp001.py](explore_hdp001.py) | offline script: `uv run python explore_hdp001.py <samples.csv> <out_dir>` |
| [results.json](results.json) | population, flags, reference, paired table, accuracies, exact Delta, bootstrap settings, interval, input hash |
| [hours.csv](hours.csv) | register of all 2928 cutoffs: prediction, scored outcome, flags, paired, correctness of each predictor |
