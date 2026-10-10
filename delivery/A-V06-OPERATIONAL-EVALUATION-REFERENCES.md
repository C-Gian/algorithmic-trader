# A v0.6 operational evaluation — frozen references (executor addendum, not authoritative)

**Operational addendum** prepared by the executor on base `7c16bc97ee13d6b6b2785d130b1626fd73008681` and updated on base `aff2a3d4747a71238c864129955a9f06fdbdb008` (Astra authorizations relayed by the Owner, 10 October 2026: documentary preparation only).
- **Authority.** The [design](A-V06-OPERATIONAL-EVALUATION-DESIGN.md), the [orchestrator decision](A-V06-OPERATIONAL-EVALUATION-CLOSURE.md) and the [decision on the study references](HDP-001-A-V06-REFERENCES-DECISION.md) prevail. The first two are unchanged.
- **Identities.** They come only from the project's existing functions (`adviser/methods.py` release `V06`, `adviser/identity.py` `historical_profile`, `EvaluatorV3.identity`). This addendum creates no new identity scheme.
- **Status.** References registered; executive preparation still incomplete (§5–§7). Execution INACTIVE.

Machine-readable output: [identities-b47b997.json](evidence/A-V06-REFERENCES/identities-b47b997.json), produced by [v06_identity.py](evidence/A-V06-REFERENCES/v06_identity.py) from `git archive b47b997 src delivery`. The same script gives an identical document on the trees of `7c16bc9` and `aff2a3d` (recomputed 10 October). It runs no adviser, evaluation or replay.

| Document | SHA-256 (LF) | Commit |
|---|---|---|
| Design | `b33335808687c9b866e86c18160a8847afa55f187014b4b6129d85f473472923` | `6710474bcab32ea4be8a96d258594d7a1b79ec3f` |
| Orchestrator decision | `4842ff0bafa30c2c0cee21b27ccc36587a68c495eb2e6fc7e4eea0c4f440c5f6` | `6710474bcab32ea4be8a96d258594d7a1b79ec3f` |

## 1. Technical reference — verified

`b47b997ee93513c7a358b49e961020705e4fbb85` ("WP-015 correction F1", 2026-10-09T22:52:18+02:00).
- **Ancestry.** It exists locally and is an ancestor of the base. 18 commits separate it from the base.
- **Unchanged since.** Nothing changed between `b47b997` and the base in `src/`, `schemas/`, `scripts/`, `pyproject.toml`, `uv.lock`, `Dockerfile`, `docker-compose.yml` or any `delivery/MP-00*` document.
- **Changed since.**
  - `web/`: 7 UI files (live cockpit, call history and the Workbench result view);
  - `tests/`: 6 files;
  - `delivery/`: 53 evidence and documentation files;
  - `README.md`, `STATE.md` and `task.md`;
  - one Owner-uploaded `source_notes/` file.
- **The latest product commit is not the study build.** These later UI commits do not make the newest commit the study build (see §5).

## 2. Method, parameters, implementation, evaluator — fixed now (at `b47b997` = base)

| Item | Value |
|---|---|
| Model / rules version | `btc.context-action.v0.6` / `mp005.rules.v0.6` |
| Rules manifest SHA-256 (`Release.rules_sha256`) | `57bf2309990d5085326f62fae9e6a88808b1de566a837995341910692e832e66` |
| Register `MP-005-PARAMETERS.json`: file SHA-256 (LF) / canonical SHA-256 | `c623a612dc724a1b2a733518e8ebc1925fe276fb48d02ed8a8508eb068582959` / `98ef101e4c23fbdfee80b2e1f0adf61eea92aeb8665db777bb8582b0ae4c5bda` |
| Implementation | `adviser.core.v6` |
| Evaluator | `adviser.evaluator.v3`; PRIMARY profile `mp002.evaluation.primary.v1` |
| PRIMARY path terms | entry delay 60 s; exit delay 60 s; fee 0.0005 per leg; allowance 0.0002 per leg; adequacy envelope 14 bps |
| Formats | state `algotrader.adviser-state.v6`, runtime `algotrader.adviser-runtime.v6`, evaluator state `algotrader.adviser-evaluation-state.v2`, engine `observe.stream.v7`, report `adviser.report.v6`, reconciliation 9, Deep 10 |
| Outcome tail (register `outcome_tail_minutes`) | 365 min |

The register's `outcome_tail_minutes` is the registered evaluator limit that design §5 refers to.

**Rules manifest** (the documents hashed into `rules_sha256`). The packaged copies are byte-identical (LF) to `delivery/`.

| Role | File | SHA-256 (LF) |
|---|---|---|
| DELTA | MP-005-V06-INITIAL-RESPONSE-INCOMPATIBILITY.md | `e4744fa13cf773f39dc247500b682f26c917876a2e117315252fd1de7089ed3e` |
| DELTA_DIRECTOR_CLOSURE | MP-005-DIRECTOR-CLOSURE.md | `fa9928030b1929ef6e1a478ad1bdd14cb79c887b63409935084fa888a3d67fd4` |
| INHERITED_MP004_RULES | MP-004-V05-RETURN-RESPONSE.md | `ddb09102cf31e31336dcfb440aea20dad01381b0e0dd769c206b212e39103c51` |
| INHERITED_MP004_CLOSURE | MP-004-DIRECTOR-CLOSURE.md | `77be8677e335972bf6f6ceb1026b33561fa79dad78fdf31c5927885e8c6d91b0` |
| INHERITED_MP003_RULES | MP-003-A-REACTION-ANCHOR-DISPOSITION.md | `11ef1dedc8d8b850e85f69d0a3b852099b14cabdfad4a6c080758ece26e467e7` |
| INHERITED_MP002_RULES | MP-002-SCENARIO-CONFIRMATION-ENTRY-PROPOSAL.md | `558afdb9c80e07f98f352effb899587e18d01fb9577a10ef812471772027fdca` |
| INHERITED_MP002_DISPOSITION | MP-002-DIRECTOR-DISPOSITION.md | `e4c7ff2389b85ec75797d6eb41e9673bc232a2581376f873d12e95743b08b5b5` |
| INHERITED_MP001_RULES | MP-001-INTEGRATED-METHOD-PROPOSAL.md | `1ca01b416b9ec3562a74bab4687cdc71a6ebf30036596dba48780e32e4f1471d` |

**Closures not in the manifest.** Some closure documents are frozen by design §2 but are not part of the composite identity. They are unchanged since `b47b997`:

| File | SHA-256 (LF) |
|---|---|
| MP-001-DIRECTOR-DISPOSITION.md | `178e2b4e8280d15ec8fb1349962f325dbd9a181ecb8187c8c2978ce8292bd3d1` |
| MP-002-ASTRA-CLOSURE.md | `f95acb2ed56544d2d7f4a100650e1a52e870805a6e6adf6690ae8b6a00efe798` |
| MP-003-ASTRA-CLOSURE.md | `77c48a0b1ada18a0337a4e43559ad69b895d52e8230a1670429f93367db954fe` |
| MP-004-ERRATUM-SECTION-6-RATIOS.md | `c42c2108dfdab93766f14a2cd2e001a9d9dde96aefb3bf0ca7756e0ae750b81e` |

## 3. Profile and evaluator identity — selected by the future pack

`engine_config` already derives the historical profile from the pack:
- dislocation is enabled only with mark and index channels;
- funding is `AUTHORITATIVE_IF_COVERED` only if the pack's funding capability is `AUTHORITATIVE_COMPLETE`, otherwise `PRICE_NET_ONLY`.

All four possible values are fixed now. Which one applies is known only when the pack exists.

| Pack facts | Profile SHA-256 | Evaluator identity SHA-256 |
|---|---|---|
| mark+index, funding not certified (**expected base: PRICE_NET_ONLY**) | `7c86833734da7258f62f8f7569b2a74253867e4b82e5b537907749f910220296` | `85504d5843e144d0b86a0ee3e693c064f4d7f64e7928c1e54fb9c9e9f308615c` |
| mark+index, funding certified | `b3bde17d388a72011f350e7a665a23e2029817d360864bed208486a85c56b64e` | `16bc0242e9127d743edcf825fb3c00326f3ba37818bab402a3b824c7f7d2dade` |
| no mark/index, funding not certified | `a57826169e54f2c52d97a22860e8235f457dc1d3194674b0432bf212583f7fab` | `85504d58…615c` |
| no mark/index, funding certified | `3ffbe4fe4a9ff8c9badb8d5b9ffd4e242f645e3c0167a78c9da7c5c882287a9f` | `16bc0242…dade` |

The evaluator identity does not depend on the tick (checked with ticks 0.1 and 1).

**Cross-check.** The expected-base profile hash `7c868…0296` and evaluator identity `85504…615c` equal the values stored by the Owner's continuous v0.4 run (`WP-013-CONTINUOUS-V04-DIAGNOSIS/dossier.json` `provenance`). The profile hash also matches Backtest A's stored identity.

## 4. Future data and hashes (to register when they exist)

**Windows (arithmetic only).**
- Initialization: [2026-12-21T00:00Z, 2027-01-25T00:00Z), 35 days.
- Window: [2027-01-25T00:00Z, 2027-07-26T00:00Z), 182 days = 4368 hourly grid points.
- Tail: [2027-07-26T00:00Z, 06:05Z).
- Bootstrap: L = 168, so k = 26 blocks of exactly 168 h, with starts in {0 … 4200}.

**Recorded later.**
- **Pack.** Pack id and manifest/receipt SHA-256, provenance and integrity checks (design §2), coverage and funding capability (which selects the §3 row).
- **Run pins.** Recorded by the run itself at launch through `engine_config`: `feed_content_identity`, `availability_policy_id`, `tick`, `channels`, the evaluation window and `clock_end`.
- **Composite identity.** `identity_sha256` is computed at launch. It includes the pins and `build`.
- **Exports.** Identities of the per-call results export used for the bootstrap.

## 5. Behaviour freeze and executive build (decision of 10 October)

The [decision](HDP-001-A-V06-REFERENCES-DECISION.md) §2 freezes the behaviour, not the inadequacy of the tools. This section only registers the dependency.

**Frozen reference.**
- `b47b997ee93513c7a358b49e961020705e4fbb85` stays the authoritative reference of the behaviour to evaluate.
- Running the whole repository exactly at `b47b997` is not required.

**Identities already verifiable.** §1 to §3 above:
- rules manifest, register, implementation, evaluator, formats and tail;
- the four pack-selected profile/evaluator rows.

They are identical at `b47b997`, `7c16bc9` and `aff2a3d`.

**Executive build and equivalence checks — still to complete.**
- **Build.** A distinct future executive build is admitted to prepare the approved window. It is **not yet identified**.
- **Scope of equivalence with `b47b997`.** Every part that can change decisions or outcomes:
  - construction and temporal availability of the inputs;
  - initialization;
  - boundaries;
  - selection;
  - management;
  - costs;
  - the evaluator.

  Version names or the method module alone are not enough.
- **Method.** A comparison of dependencies and of the relevant code, combined with targeted synthetic tests. Passing a few fixtures is not general equivalence.
- **Differences.** Any difference able to change decisions or results needs an explicit decision.
- **Workbench limit.** The Workbench limit (presets accept only whole months inside [2025-09-01, 2026-09-01); `corpus/presets.py` `check_windows`) and the technical preparation of the window stay **dependencies**.
  - The technical preparation is a separate assignment and is not activated.
  - The limit does not authorize changing the window, splitting it into monthly runs with resets, or using protected periods.

**Deadline.** Design §5: the freeze must be completed before **2027-01-25T00:00Z**, otherwise the window lapses. There is no retrospective recovery and no automatic shift. The build and the equivalence checks must be resolved within that deadline.

## 6. Operational points closed by the design (no new choice)

| Point | Determined by |
|---|---|
| A call's result is attributed to the UTC grid hour [h, h+1h) containing its `issued_at` | Design §6 ("ora di emissione"), the window's half-open UTC hourly grid |
| Hourly value = sum of the attributed results of A calls issued in that hour; hours without an A call = 0 | Design §6 |
| Per-call result = PRIMARY path `price_net` under PRICE_NET_ONLY; `total_net` only with certified funding | Design §4; evaluator fields |
| A NO_ENTRY call is no modeled operation and adds nothing to the sum, as in the existing report `sum_price_net` | Design §3; `report.py` |
| Per-resample statistic = sum of the hourly values over the N = 4368 resampled grid hours, against abstention 0 | Design §4 and §6 |
| B/C calls are reported separately, outside the primary sum | Design §2 |

## 7. Still to fix or obtain before execution

- **Bootstrap draw procedure.** Design §6 fixes the blocks, B, the seed, the uniform starts, no wrap, truncation and the percentiles. It does not fix the order and method of the draws from `random.Random(0)`, which reproducibility requires.
- **Included entered paths with no determinable result** (UNRESOLVED / AMBIGUOUS / CENSORED). Design §3–4 forbid imputing zero or deleting them, and say they prevent a complete primary conclusion. How the bootstrap and the reported balance represent them must be fixed before computing.
- **Executive build and equivalence checks** (§5).
- **CI.** Green exact-SHA CI for `b47b997` and for the executive build, reported by the Owner. Not polled.
- **Separate assignments** (design §8):
  - acquisition after the tail;
  - Owner launch;
  - access to per-call results with identities and times;
  - a check that the existing report covers the owner register (design §3);
  - the bootstrap computation.
- **Exposure declarations** in the common [study exposure register](STUDY-EXPOSURE-REGISTER.md).

v0.6 and HDP-001 frozen; January–August 2026 protected. References registered; executive preparation still incomplete; execution INACTIVE.
