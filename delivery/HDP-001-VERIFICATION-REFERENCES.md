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

Its grid, mask, bootstrap and percentile code is the registered reference for the shared computation. A verification executor must be written under the executive assignment and must implement the frozen conventions without adding new ones.

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

**Fixed before any computation, without changing the frozen rules:**
- the concrete attestation checks for identity, temporal alignment, prices and masks that separate UNAVAILABLE gaps from a non-evaluable result (decision §1 gives the categories, not the checklist);
- the coverage and concentration facts reported with the reading, for example where unavailable hours fall on the grid. Decision §1 says they limit the conclusion and sets no threshold; what is reported is not yet fixed;
- the data route, chosen in the executive assignment (§4);
- a verification executor (§3) and its review.

**Registered when they exist:** dataset or pack identities, manifests, hashes, provenance and quality (§4).

**Authorizations still needed:**
- an executive assignment after 2027-01-25 covering acquisition, data registration, the executor and the computation;
- declarations in the exposure register.

There is no consultation of outcomes during the window. v0.6 frozen; January–August 2026 protected. References registered; executive preparation still incomplete; execution INACTIVE.
