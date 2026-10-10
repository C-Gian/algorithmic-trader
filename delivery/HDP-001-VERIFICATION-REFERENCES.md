# HDP-001 — Verification references (executor addendum, not authoritative)

**Operational addendum** prepared by the executor on base `7c16bc97ee13d6b6b2785d130b1626fd73008681` and updated on base `aff2a3d4747a71238c864129955a9f06fdbdb008` (Astra authorizations relayed by the Owner, 10 October 2026: documentary preparation only). It adds no methodological decision.
- **Authority.** The authoritative texts below are unchanged, byte for byte, and so is the [decision on the study references](HDP-001-A-V06-REFERENCES-DECISION.md). Where this addendum and they differ, they prevail.
- **Status.** References registered; executive preparation still incomplete (§6). **Execution INACTIVE.** No acquisition, Owner extraction or computation is authorized here.

## 1. Authoritative documents and frozen artifacts

SHA-256 values are taken over the LF-normalized bytes (the Git content). Each file is identical at its acceptance commit and at the base.

| Role | File | Commit | SHA-256 (LF) |
|---|---|---|---|
| Protocol (authoritative, Italian) | [HDP-001-HOURLY-DIRECTIONAL-PERSISTENCE.md](HDP-001-HOURLY-DIRECTIONAL-PERSISTENCE.md) | `7b5aaf2fdc3c7b01ed0c8f3c931f12b6583dca8a` | `7fb2f545a92436fac3fe32a05c23d700ef26a6771f8e7970a74060f1f581f6d1` |
| Director decision: registration, seed 0 | [HDP-001-DIRECTOR-CLOSURE.md](HDP-001-DIRECTOR-CLOSURE.md) | `7b5aaf2fdc3c7b01ed0c8f3c931f12b6583dca8a` | `195a11ccc876bf641db58053391b88ce0835f0b79486795ca43b18464e0203e1` |
| Exploration closure and verification freeze | [HDP-001-EXPLORATION-CLOSURE.md](HDP-001-EXPLORATION-CLOSURE.md) | `c8e982e1b2fa1373491a138f4f81c852910e2e2f` | `b8c33cd32a887b38b9525b0f966c6cd9754cb25934df8492083846a201597d0e` |
| Window proposal and Director clarifications (§5) | [HDP-001-VERIFICATION-WINDOW-PROPOSAL.md](HDP-001-VERIFICATION-WINDOW-PROPOSAL.md) | `cf18dbd04ef92e39f7c92955a6a67ed9b9b3a506` | `b110d48734a95456e64a22fc5f7bb21bb31c12deae6fc73301ab985f946058ec` |
| Decision on the study references (verbatim) | [HDP-001-A-V06-REFERENCES-DECISION.md](HDP-001-A-V06-REFERENCES-DECISION.md) | this commit | `7b91a1b3e667965dba19cb8771285fd39c4f662d7c7c06882feae2795c77ffb8` |
| Accepted exploration (Director, `cf18dbd`) | [SUMMARY.md](evidence/HDP-001-EXPLORATION/SUMMARY.md) | `cf18dbd04ef92e39f7c92955a6a67ed9b9b3a506` | `2f2d53ffe349ffebfed6da9b06f1ed9796139421f20a4b78eafae5c6b2f44533` |
| Exploration script | [explore_hdp001.py](evidence/HDP-001-EXPLORATION/explore_hdp001.py) | `cf18dbd…` | `35fa53cc34688117a24b20c0e5941c2cfde36725d36295c439ea376f0f4c5059` |
| Exploration results | [results.json](evidence/HDP-001-EXPLORATION/results.json) | `cf18dbd…` | `eef4ef4126829351279530c3afefd13dcedab7eebfc2f7b8af3a2db3ab0db1c8` |
| Exploration hour register | [hours.csv](evidence/HDP-001-EXPLORATION/hours.csv) | `cf18dbd…` | `f712e59fcb810d9eb0bde4c084da7ff0e75df8ab22912d559208b90ba3160596` |
| Exploration input | [samples.csv](evidence/MARKETVIEW-PERSISTENCE-TABULATION/samples.csv) | `ced7b2f2017a4b4f3e73121dc625c2d150da34e8` | `8f04588f873f6f6cf73d48544135ddf4d1733210088aa6f06331f53e0da90953` |

The samples.csv hash equals the input hash recorded in `results.json`. The exploration's bootstrap Delta vector hash `adf224eab5c1721757b899f9d60120387cd7470aec77b5fbb423ef8f2808488a` is recorded in `results.json`. The exploration was **not re-run** for this addendum.

## 2. Fixed and verified now

**Frozen by the closure.**
- Constant reference **UP**: chosen by §4 in the exploration (UP 1471 > DOWN 1456).
- Window **[2026-11-02T00:00Z, 2027-01-25T00:00Z)**.
- Bootstrap: 168 h blocks, 10,000 resamples, `random.Random(0)`, Hyndman–Fan type 7 percentiles.
- Boundary: the last cutoff is kept; the endpoint equal to the end is not scored.

**Rules of the protocol (by section, not repeated here).**
- Instrument and price role: §2.
- Prediction and outcome: §2.
- FLAT and missing data: §3.
- Paired denominator: §5.
- Masks kept, no circular wrap, last block truncated: §5.
- Reading categories: §6.
- Stop: §8.

**Operational details already registered with the accepted exploration** (SUMMARY "Reproducibility"):
- Block starts are drawn with `randrange(N−L+1)`, in the order resample 0…9999, then block 0…k−1.
- Statistic per resample: Delta* = (persistence hits − constant hits) / paired count over the resampled grid. A zero paired count is counted, and the result is then inconclusive.
- Percentiles: p = 0.025 and 0.975, type 7.

**Bootstrap draw procedure of the verification executor.** Registered on 10 October 2026, before any synthetic execution of the executor. It applies the exploration procedure above unchanged; no A v0.6 convention is used.
1. `rng = random.Random(0)` is created once, before the first resample. No other code draws from it.
2. The grid is the N planned cutoffs in time order. Every hour is kept, with its masks; the resample is never compressed to evaluable hours.
3. With k = ⌈N / L⌉, the block lengths are L for blocks 0 … k−2 and N − L·(k−1) for block k−1 (the truncated last block; with N = 2016 it is 168).
4. For resample b = 0 … 9999, and within it block j = 0 … k−1, one draw `s = rng.randrange(N − L + 1)` gives the block hours s … s + length_j − 1. Every block lies inside the window; there is no circular wrap.
5. Delta*_b = (Σ persistence_correct − Σ constant_correct) / Σ paired over the resampled hours, with the constant reference fixed at UP. If Σ paired = 0, the resample is counted and the interval is not computed (inconclusive). The block length is never adapted.
6. If N < 2L, nothing is drawn and the result is inconclusive (protocol §5).
7. The interval uses Hyndman–Fan type 7 on the sorted Delta* values, at p = 0.025 and 0.975, with h = (B − 1)·p.

**Derived from the frozen window (arithmetic only).**

| Item | Value |
|---|---|
| Planned cutoffs | t = 2026-11-02T00:00Z … 2027-01-24T23:00Z, **N = 2016** |
| BOUNDARY_NOT_SCORED | cutoff 2027-01-24T23:00Z (endpoint = end); its outcome is never read |
| Last scorable cutoff | 2027-01-24T22:00Z (endpoint 23:00Z) |
| History for the first prediction | hourly bars [2026-11-01T22:00Z, 23:00Z) and [23:00Z, 2026-11-02T00:00Z) |
| Trade 1m minutes needed | **[2026-11-01T22:00Z, 2027-01-24T23:00Z)** |
| Blocks | L = 168, k = 12 blocks of exactly 168 h (no truncated block); starts s ∈ {0 … 1848}; randrange(1849) |

## 3. The exploration script is not the verification executor

`explore_hdp001.py` stays unchanged. It is a record of the exploration, not a runner for future data:
- **Input.** It reads only the adviser-derived `samples.csv` fields:
  - `s_persistence`, from temporal.v1 COMPLETE contiguous 1h bars of run `eval-20261009T155751-be8b2b`;
  - `s_outcome_1h`, the close of the 1m bar ending exactly at t+1h minus the last 1m close known at t.

  It does not build C_t from raw 1m bars.
- **Phase.** Phase bounds are hard-coded to Sep–Dec 2025. It also exits on any missing hourly row instead of flagging it.
- **Reference.** It **recomputes the constant reference** from the phase outcomes (§4, exploration only). For the verification the reference is the frozen UP and must not be recomputed.
- **Reading.** It assigns no §6 reading.

**Construction difference** (registered as required by the decision §1). The exploration stays unchanged.

| | Exploration (`samples.csv`, run v0.5) | Verification (decision §1) |
|---|---|---|
| Prediction | sign of the last two temporal.v1 COMPLETE, contiguous 1h closes | the same: both hours COMPLETE |
| Outcome | close of the 1m bar ending exactly at t+1h minus the last 1m close known at t; the endpoint hour was not required to be COMPLETE | C_(t+1) − C_t, with **both hours COMPLETE**; the last minute's close alone does not certify an hour; no interpolation |

The numerical equivalence observed on the exploration samples (outcome(t) = prediction(t+1h) on 2927/2927, 0 unavailable) is attributed only to that evidence: complete coverage of that run. It does not extend to cases with missing minutes.

Its grid, mask, bootstrap and percentile code is the registered reference for the shared computation. The verification executor is a separate tool, [`scripts/hdp001_verify.py`](../scripts/hdp001_verify.py) (§7); the exploration script stays unchanged.

## 4. Future data and hashes (to register when they exist)

- Data route, chosen in the executive assignment:
  - the existing pack preparation cannot represent this window, because presets require whole calendar months inside [2025-09-01, 2026-09-01) (`corpus/presets.py` `check_windows`);
  - `algotrader data fetch-okx` makes bounded `marketdata.v1` datasets of at most 31 days each; every dataset requests all four historical families (trade, mark, index, funding), and HDP-001 reads the trade family only.
- Dataset or pack identities, manifests and SHA-256 values, provenance, coverage and quality: recorded after acquisition, before any computation.
- Verification hour register, results and bootstrap vector hash: produced only by the authorized run.

## 5. Points resolved by the decision of 10 October

[Decision](HDP-001-A-V06-REFERENCES-DECISION.md) §1. These are clarifications for faithful execution; the hypothesis is unchanged.

1. **Completeness.** Every hourly close used, for prediction or outcome, belongs to an hour that is complete under the existing temporal semantics: `algotrader.temporal.v1` COMPLETE, meaning every expected minute admitted valid. For retrospective historical data the existing semantics is the modeled complete-prefix clock with seal-no-revision. The UP reference uses no close.
   - The last minute's close alone is not enough.
   - No interpolation.
2. **Reference and sample.**
   - UP is fixed and never recomputed.
   - Both predictors use the same evaluable observations: the paired set of protocol §5.
   - No new minimum percentage.
   - Reduced coverage or concentrated absences limit the conclusion even when the computation is correct.
3. **Gaps vs non-evaluable.**
   - An identified and correctly represented gap gives PREDICTION_UNAVAILABLE / OUTCOME_UNAVAILABLE (protocol §3); grid and masks are kept.
   - If identity, temporal alignment, prices or masks cannot be attested, the result is **not evaluable**.
4. **Exposure register.** Designated: [STUDY-EXPOSURE-REGISTER.md](STUDY-EXPOSURE-REGISTER.md), common to the studies.

## 6. Residual dependencies and what must be fixed before execution

**Prepared in the executor (§7), pending Director review:**
- the concrete attestation checks for identity, instrument, price role, timestamps, grid, bar validity and aggregate construction, which separate UNAVAILABLE gaps from a NOT_EVALUABLE result;
- the coverage and concentration facts reported with the reading: unavailable cutoffs per 168 h block, runs of consecutive unavailable cutoffs, and incomplete hourly bars with their reasons. There is no threshold.

**Still to fix before any computation:**
- the data route, chosen in the executive assignment (§4); the executor reads verified `marketdata.v1` datasets;
- review of the executor and of its checks.

**Registered when they exist:** dataset or pack identities, manifests, hashes, provenance and quality (§4).

**Authorizations still needed:**
- an executive assignment after 2027-01-25 covering acquisition, data registration and the computation with the reviewed executor;
- declarations in the exposure register.

There is no consultation of outcomes during the window. v0.6 frozen; January–August 2026 protected. References registered; executive preparation still incomplete; execution INACTIVE.

## 7. Verification executor — prepared, synthetic evidence only

**Identity.**
- Tool: [`scripts/hdp001_verify.py`](../scripts/hdp001_verify.py), `hdp001.verify.v1`; script SHA-256 (LF) `a4f0761071c6b77d6f649d6e29399ac6f4f8b4315ae42ce1afd51705f591acdc`.
- Frozen configuration SHA-256 (canonical JSON) `32739a3c673c8b38ce48e2c418110888dff8b8b62cff850d03185184390239d4`. Contents: window [2026-11-02T00:00Z, 2027-01-25T00:00Z), L = 168, B = 10,000, seed 0, reference UP, BTC-USDT-SWAP trade, p = 0.025 / 0.975.
- Tests: [`tests/test_hdp001_verify.py`](../tests/test_hdp001_verify.py).
- Every run records the script hash, the git code version, the configuration hash and the hashes of the four authoritative sources. A VERIFICATION run refuses to start if any authoritative source differs from its pinned hash, if the configuration is not the frozen one, or if no assignment reference is given.

**Command** (only under the separate executive assignment; it is not authorized now):

```text
uv run python scripts/hdp001_verify.py --assignment "<assignment reference>" --out <new empty directory> <dataset_dir> [<dataset_dir> ...]
```

**Input.**
- Verified `marketdata.v1` dataset directories (for example from `algotrader data fetch-okx`, at most 31 days each), in any order.
- They must start and end on whole UTC hours and be contiguous, without overlap.
- Together they must cover exactly [2026-11-01T22:00Z, 2027-01-24T23:00Z).

The tool downloads nothing, uses no service or database, and writes only `results.json` and `hours.csv` into a new directory. It never writes into the exploration directory and never updates the reference, the study status or the exposure register.

**Construction.**
- Each dataset goes through the existing causal feed (`build_feed`, modeled availability with zero delay) and the existing `temporal.v1` engine (modeled complete-prefix clock, seal-no-revision).
- An hour is used only if its 1h trade aggregate is COMPLETE: all 60 minutes present and valid.
- Prediction, outcome, flags, the paired set and the fixed UP reference follow protocol §2–§5 and the decision §1.
- The boundary endpoint H(2027-01-25T00:00Z) is outside the required range and is never read.

**Integrity checks.** Any failure gives NOT_EVALUABLE, and nothing is computed.

| Check | Attests |
|---|---|
| C1 | `marketdata.verify` per dataset: manifest schema, file hashes and sizes, Parquet row counts, raw page hashes, dataset_id recomputed from raw pages. An unreadable artifact counts as a failure. |
| C2 | Source okx; instrument BTC-USDT-SWAP SWAP in the request and in the instrument snapshot |
| C3 | Hour-aligned, contiguous, non-overlapping datasets whose union is exactly the required range |
| C4 | Feed and aggregation build without error; modeled zero-delay availability policy; exactly one `trade_bar_1m` channel for the instrument (mark, index and funding unused) |
| C5 | Temporal counters: no late, misaligned or outside-coverage evidence |
| C6 | Exactly one trade observation or quality event per minute slot of each dataset |
| C7 | One sealed 1h trade record per hour, in order |
| C8 | Recount from the trade events, independent of the aggregator. COMPLETE iff 60 valid minutes; the close equals the last minute's close; known at the hour end. INCOMPLETE has fewer valid minutes and keeps its reasons. Any other status inside the range is inconsistent. |
| C9 | One hourly bar per required hour for the N cutoffs |

**Scope of the checks.**
- These checks attest **internal consistency** only.
- A gap that passes them is an identified gap: an INCOMPLETE hour with recorded reasons (MISSING, INVALID_ROW, CONFLICTING_DUPLICATE, INCOMPLETE_REJECTED and so on). It becomes PREDICTION_UNAVAILABLE / OUTCOME_UNAVAILABLE, with grid and masks kept.
- **Not attested by any hash**, and listed in every output as needing external provenance:
  - the authenticity of the OKX responses;
  - the agreement of the history-candle prices with the traded market;
  - the absence of alteration before the hashes were first recorded.

**Output.**
- Mode and label. SYNTHETIC outputs say that they are not the verification and carry no reading.
- Executor identity, sources, configuration, input identities: dataset_id, manifest hash, request, retrieval times, base URL, feed content identity, ordered event hash, temporal profile fingerprint.
- The integrity checks, the population and its flags (counted separately), the paired table with exact accuracies and Delta.
- The bootstrap, following the §2 procedure: block lengths, start range, zero-denominator count, the Delta* vector hash, the type-7 interval and its cross-check.
- The absence distribution and the hour register hash.
- The status: COMPUTED, INCONCLUSIVE_DURATION, INCONCLUSIVE_ZERO_DENOMINATOR, INCONCLUSIVE_NO_PAIRED_HOURS or NOT_EVALUABLE.
- **VERIFICATION runs only.** The protocol §6 interval position, with the note that coverage and concentration limit the conclusion and that the reading is the Director's.

**Synthetic evidence** (10 October 2026). `tests/test_hdp001_verify.py`: 15 passed. All values were hand-derived in the test, and the bootstrap draws were recomputed there independently. The cases are:
- four paired cells with a FLAT outcome, a FLAT prediction with a FLAT outcome, and a majority-DOWN sample where UP stays fixed;
- an incomplete hour masking exactly its dependent cutoffs;
- the boundary endpoint never read, and the first prediction from prior history;
- the registered draws, with masks kept;
- N < 2L, and all-zero denominators;
- the frozen-grid arithmetic (2016 cutoffs, 12 × 168 h, starts 0 … 1848) on synthetic hourly closes;
- full offline runs through real `marketdata.v1` packages built from synthetic rows:
  - complete;
  - one internal minute missing with the final close present;
  - two contiguous datasets, equal to one;
- tampered, corrupt, partial, overlapping and non-hour-aligned inputs, all NOT_EVALUABLE;
- no overwrite, and the VERIFICATION guards.

Three temporary mutations were each detected and reverted:
- an incomplete hour certified by its last close;
- the reference re-estimated from the outcomes;
- the boundary endpoint read.

A 7-day synthetic package took about 6 s, so a 12-week verification should take about 1–2 minutes (estimate, not measured).

**Not demonstrated.**
- No real or verification-window data was used, and no real run has taken place.
- C2 with a wrong instrument and C5–C7 failures were not provoked by a fixture: they are covered by code reading, not tests.
- External provenance stays outside the tool.
