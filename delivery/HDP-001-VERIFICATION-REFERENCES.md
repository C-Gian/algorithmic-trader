# HDP-001 — Verification references (executor addendum, not authoritative)

**Operational addendum** prepared by the executor on base `7c16bc97ee13d6b6b2785d130b1626fd73008681` (Astra authorization relayed by the Owner, 10 October 2026: documentary preparation only). It adds no methodological decision. The authoritative texts below are unchanged, byte for byte; where this addendum and they differ, they prevail. **Execution INACTIVE.** No acquisition, Owner extraction or computation is authorized here.

## 1. Authoritative documents and frozen artifacts

SHA-256 values are taken over the LF-normalized bytes (the Git content). Each file is identical at its acceptance commit and at the base.

| Role | File | Commit | SHA-256 (LF) |
|---|---|---|---|
| Protocol (authoritative, Italian) | [HDP-001-HOURLY-DIRECTIONAL-PERSISTENCE.md](HDP-001-HOURLY-DIRECTIONAL-PERSISTENCE.md) | `7b5aaf2fdc3c7b01ed0c8f3c931f12b6583dca8a` | `7fb2f545a92436fac3fe32a05c23d700ef26a6771f8e7970a74060f1f581f6d1` |
| Director decision: registration, seed 0 | [HDP-001-DIRECTOR-CLOSURE.md](HDP-001-DIRECTOR-CLOSURE.md) | `7b5aaf2fdc3c7b01ed0c8f3c931f12b6583dca8a` | `195a11ccc876bf641db58053391b88ce0835f0b79486795ca43b18464e0203e1` |
| Exploration closure and verification freeze | [HDP-001-EXPLORATION-CLOSURE.md](HDP-001-EXPLORATION-CLOSURE.md) | `c8e982e1b2fa1373491a138f4f81c852910e2e2f` | `b8c33cd32a887b38b9525b0f966c6cd9754cb25934df8492083846a201597d0e` |
| Window proposal and Director clarifications (§5) | [HDP-001-VERIFICATION-WINDOW-PROPOSAL.md](HDP-001-VERIFICATION-WINDOW-PROPOSAL.md) | `cf18dbd04ef92e39f7c92955a6a67ed9b9b3a506` | `b110d48734a95456e64a22fc5f7bb21bb31c12deae6fc73301ab985f946058ec` |
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

Its grid, mask, bootstrap and percentile code is the registered reference for the shared computation. A verification executor must be written under the executive assignment and must implement the frozen conventions without adding new ones.

## 4. Future data and hashes (to register when they exist)

- Data route, chosen in the executive assignment:
  - the existing pack preparation cannot represent this window, because presets require whole calendar months inside [2025-09-01, 2026-09-01) (`corpus/presets.py` `check_windows`);
  - `algotrader data fetch-okx` makes bounded `marketdata.v1` datasets of at most 31 days each; every dataset requests all four historical families (trade, mark, index, funding), and HDP-001 reads the trade family only.
- Dataset or pack identities, manifests and SHA-256 values, provenance, coverage and quality: recorded after acquisition, before any computation.
- Verification hour register, results and bootstrap vector hash: produced only by the authorized run.

## 5. Open points for the Director (not resolved here)

1. **Operational C_t / completeness.** §2–3 require exact closes of complete, contiguous hourly bars; incomplete inputs or endpoints become UNAVAILABLE. In the exploration:
   - the prediction used temporal.v1 COMPLETE 1h bars (all 60 minutes admitted valid);
   - the outcome used the 1m close at exactly t+1h against the last 1m close known at t, without requiring the endpoint hour to be COMPLETE.

   The two coincide on complete data (2927/2927 identity, 0 unavailable). They differ when minutes are missing. A rule for building C_t and its completeness from 1m bars is not registered for the verification.
2. **"Integrità insufficiente" (§6).** No criterion separates masked missing hours from a "non valutabile" result.
3. **Exposure register.** §7 and the closure require exposures influencing research decisions to be declared. No designated register or location exists (window proposal §3, gap 1).

## 6. Still needed before execution

- An executive assignment, after 2027-01-25, covering:
  - acquisition of the trade 1m range above;
  - registration of the data identities;
  - a verification executor and its review;
  - the computation.
- Decisions on points 1–3 above before any computation.
- No consultation of outcomes during the window. v0.6 frozen; January–August 2026 protected.
