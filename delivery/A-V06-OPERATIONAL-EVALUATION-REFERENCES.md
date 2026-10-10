# A v0.6 operational evaluation — frozen references (executor addendum, not authoritative)

**Operational addendum** prepared by the executor on base `7c16bc97ee13d6b6b2785d130b1626fd73008681` and updated on base `aff2a3d4747a71238c864129955a9f06fdbdb008` (Astra authorizations relayed by the Owner, 10 October 2026: documentary preparation only).
- **Authority.** The [design](A-V06-OPERATIONAL-EVALUATION-DESIGN.md), the [orchestrator decision](A-V06-OPERATIONAL-EVALUATION-CLOSURE.md) and the [decision on the study references](HDP-001-A-V06-REFERENCES-DECISION.md) prevail. The first two are unchanged.
- **Identities.** They come only from the project's existing functions (`adviser/methods.py` release `V06`, `adviser/identity.py` `historical_profile`, `EvaluatorV3.identity`). This addendum creates no new identity scheme.
- **Status.** References registered; study path technically prepared on synthetic evidence (§8); study not launchable (§8.6). Execution INACTIVE.

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


## 8. Study path — technical preparation (synthetic evidence only; study INACTIVE)

Prepared on base `77420cd`. The path is **technically ready** only to the extent the synthetic checks below show. The **study is not launchable**: §8.6 lists what is still needed. Evidence: [`evidence/A-V06-STUDY-PREPARATION/`](evidence/A-V06-STUDY-PREPARATION/).

### 8.1 Existing path and the impediments found

| Step | Existing tool | Status for this window |
|---|---|---|
| Window and preset | `corpus/presets.py`, registered `presets.json` | **Blocked.** `check_windows` accepts only whole calendar months inside the target [2025-09-01, 2026-09-01). `classify` would also label any window outside both periods as DEVELOPMENT. |
| Dataset composition | Pack job: local reuse, missing slices of at most 31 days split at UTC months, one immutable receipt-pinned pack and feed cache | Works for any window once the preset is accepted. Acquisition is possible only after the tail end. |
| Initialization | `REGISTERED_EXPLICIT_INITIALIZATION` (WP-013): context only, never evaluated; warmup calls and waiting children cleared at the start | Works: 35 days ≥ the 96 h fine warmup |
| Continuous launch | `/api/evaluations` on a pack, adviser v0.6, one run with no monthly reset (`internal_month: CONTINUE_NO_FINISH_NO_RESET`) | Works; the protected guard is unchanged |
| Checkpoint and resume | Observation worker: fenced checkpoints, crash reclaim, pause/step/resume | Works (existing v0.6 coverage plus §8.4) |
| Boundaries | No new call at or after the evaluation end; tail only completes paths; calls outside the window are not evaluated | Works, unchanged |
| Evaluator | `adviser.evaluator.v3`, PRIMARY path with 60 s delay, price_net or total_net | Unchanged |
| Per-call results | `GET /api/adviser/runs/{replay_id}/calls` (calls with their hypothetical paths), journal pages, `report.json` | Available, but no study-level arrangement existed: issue-hour attribution, undetermined paths, owner register |

### 8.2 Minimal adaptation (diff circumscribed)

**Product (`src/`)** — the only changes since `b47b997`:

| File | Change |
|---|---|
| `corpus/study_presets.json` (new) | One registered study preset, `a-v06-operational-evaluation-2027-v1` (SHA-256 LF `d3592119…db43`; preset identity `861455df…19ca`). Initialization [2026-12-21T00:00Z, 2027-01-25T00:00Z), evaluation [2027-01-25T00:00Z, 2027-07-26T00:00Z), tail to 2027-07-26T06:05Z. It pins the design, orchestrator decision and references decision by hash. Method v0.6; adviser evaluation only. |
| `corpus/presets.py` | `check_windows` accepts **only** a preset equal, field for field, to a registered study preset. That preset still needs the explicit initialization, the file's tail and the `REGISTERED_STUDY_WINDOW` class, and may not overlap the development or protected periods. `classify` labels it `REGISTERED_STUDY_WINDOW`. `resolve` finds it by id. The month builder and every other preset keep the earlier checks. The registered `presets.json` is unchanged. |
| `corpus/pack_api.py` | `GET /api/corpus/presets` also lists the registered study presets, so the Workbench shows them under its other presets. No UI code changed. |
| `evaluation/api.py` | A study-window pack admits only the run its study registers (adviser evaluation, method v0.6). Observation-only and every other method are refused (409). |

**Study tool (not product).** [`scripts/a_v06_study_ledger.py`](../scripts/a_v06_study_ledger.py) (`a-v06.study-ledger.v1`, SHA-256 LF `400c6c72…210a` after the review correction of §8.8).
- `export` copies one evaluation GET-only into a new directory with file hashes.
- `ledger`, offline, produces:
  - an identity check against `identities-b47b997.json`;
  - the primary population (every A call issued in the window), with B/C and out-of-window calls kept apart;
  - per-call PRIMARY results (`price_net`, or `total_net` only with certified funding);
  - UTC issue-hour attribution: hours without an A call are 0, and an hour holding an undetermined included path has no value;
  - NO_ENTRY kept apart from entered-but-undetermined paths;
  - weekly issue and entry counts, and the A owner register;
  - a balance that stays INCOMPLETE when any included path is undetermined;
  - no balance and no hourly value at all unless identity and completeness are attested (§8.8).
- The bootstrap is **not computed** (§8.6).

### 8.3 Diff map against `b47b997`

Product tree since `b47b997`:
- **Unchanged:** `schemas/`, dependencies (`pyproject.toml`, `uv.lock`), `Dockerfile`, `docker-compose.yml`, every `delivery/MP-00*` document.
- **Changed:** the four `src/` items of §8.2, and UI-only `web/` changes (live cockpit, call history, the Workbench result view's labels).

| Area that can change decisions or outcomes | Modules | Diff since `b47b997` |
|---|---|---|
| Input construction and temporal availability | `marketdata/`, `feed/`, `temporal/`, `corpus/pack.py`, `observe/feedcache.py` | none |
| Initialization | `presets.py` (window facts), `adviser/engine.py` (`initialization_pin`), `report_periods.py` | window acceptance only: the registered study window becomes admissible; initialization semantics unchanged |
| Boundaries (start, end, tail, clock end) | the adviser cores (`eval_start`/`eval_end` gating), `engine_config` | none; window values come from the accepted preset |
| State, checkpoint and resume | `observe/` (job, kernel, worker, control), adviser runtimes and codecs | none |
| Selection, slots, conflicts, protections | `adviser/core*.py`, `methods.py`, `params.py`, `method/` | none |
| Management and costs | the adviser cores, `geometry.py`, the MP-005 register | none |
| Evaluator | `evaluator.py`, `evaluator3.py`, `evaluation_contracts.py` | none |
| Reports | `adviser/report*.py`, `evaluation/report.py` | none |
| Launch and API | `evaluation/api.py`, `corpus/pack_api.py` | additive: one refusal and one listing entry |
| Dependencies | `pyproject.toml`, `uv.lock` | none |

**Combined statement.** The code examination and the comparisons below support the following, for inputs that `b47b997` accepts:
- the executive build changes no decision or outcome;
- the study window is new input data, fed to unchanged code.

**Not claimed.**
- This is not a general equivalence proof.
- One synthetic tape cannot exercise every branch.
- The Director's acceptance of the executive build is pending.

### 8.4 Comparisons and synthetic checks actually run

- **Reference against the build, on the same input** ([`compare_builds.py`](evidence/A-V06-STUDY-PREPARATION/compare_builds.py)).
  - **Setup.** `git archive b47b997 src` was run against the candidate executive tree (base `77420cd` plus this diff), each on a fresh disposable database. The input was one synthetic v0.6 A call tape, in a fixture window that both trees accept.
  - **Durable path** (pack job → evaluation API → worker → report) matched:
    - the pack id;
    - the journal digests (87 records) and the evaluation-record digests (10);
    - the finish commitment;
    - the call and its PRIMARY path (CLOSED, price_net −0.0014);
    - the report with volatile fields removed, **byte-equal**.

    The volatile fields are ids, times, the build, and the run-manifest file hash, which embeds the replay id, the launch time and the build.
  - **Pure fold** with the study fixture windows: equal digests on both trees.
  - **Files:** `compare-b47b997.json`, `compare-build.json` and both `.report.json`.
- **Window extension, build only** (the reference cannot prepare it, and it is not altered to do so). `tests/test_a_v06_study.py` (6 passed) and `tests/test_a_v06_study_db.py` (3 passed, disposable PostgreSQL) show:
  - the packaged study preset states the pinned design windows (35-day initialization, 365 min tail = MP-005 register) and is accepted against the real `presets.json`;
  - shifted, renamed or re-classed copies, the month builder outside the target, and an overlap with the protected period are refused;
  - earlier presets keep their labels;
  - a tiny registered study window outside the fixture target, crossing the Aug/Sep 2025 month boundary, is prepared by the real pack job and listed by the API;
  - observation-only, the default method and v0.5 are refused (409); v0.6 runs to COMPLETED with assurance passed;
  - the durable journal equals the pure fold, so there is one continuous fold with no monthly reset; the report's month sections (Aug, Sep) reconcile;
  - a crash right after the first September delivery, then reclaim, and a pause before the reference with stepping through the issue, then resume, each equal the uninterrupted run (journal, evaluation records, finish commitment);
  - the A call issued 04:03 in the window is resolved 06:03 in the tail and is DETERMINED in the ledger;
  - every other hour is 0; the identities match the registered ones; the owner is BORN_IN_WINDOW.
- **Pure ledger cases.**
  - A confirmation in the warmup: the owner is PRE_EXISTING_AT_START and CONFIRMED, nothing is issued, and the reason is kept.
  - A window ending before the issue: no call after the boundary, with the reason kept.
  - Data ending before the exit: the path is UNDETERMINED, the hour has no value, and the balance is INCOMPLETE. Nothing is imputed.
- **Regression on the touched paths.** pack/preset (`test_pack`, `test_pack_correction`), WP-013 continuity (`test_wp013_continuous`, `_db`), evaluation launch (`test_evaluation`), MP-005 v0.6 (`test_mp005_db`, `test_mp005_versions`), the new study tests and the HDP-001 executor tests: **167 passed** (15 min 46 s, disposable PostgreSQL 18.6). `algotrader schema`: all baselines match. No full suite or E2E was run.
- **Synthetic artifacts.**
  - `synthetic-export/` and `synthetic-ledger/`: one study-window run, labelled SYNTHETIC.
  - Regenerated after the §8.8 correction. The build recorded there is `21619c3…-dirty`: the evidence files were being rewritten during the run; `src/` equals `be44370`.

### 8.5 Identities registered now

| Item | Value |
|---|---|
| Frozen behaviour reference | `b47b997ee93513c7a358b49e961020705e4fbb85` (unchanged) |
| Method, parameters, implementation, evaluator, profile | §2–§3 above, unchanged and re-checked by the ledger against `identities-b47b997.json` |
| Study preset | `a-v06-operational-evaluation-2027-v1`, preset identity `861455dfd8f993cdb08c6c0191f1cb64bccdfb9408060c67e1cf525e325919ca`; file `d3592119c393a54e93be875a28ddaedd53fdcf574419aadb8dbd4242dbb3db43` |
| Executive build | **not yet accepted or identified as final.** The candidate is `be44370f958a9b60f4b02e036102a23247f361d8`. Its `src/` differs from `b47b997` only by §8.2, and the comparisons ran on the identical `src/` tree. Later commits whose `src/` and dependencies equal this one carry the same behaviour, but each still needs its own CI and identification. |
| Synthetic inputs (engineering only) | Fixture comparison pack `pack-d7656fe07cd850f0a4fc5ab89c36e57933a93dc6`; study fixture pack `pack-82683f8d12fd7162f5b80fcace39ef6bfea9abdd`, feed `feedcontent.v1:001e4756…93ad` |
| Future pack, run pins, composite identity | To be registered when they exist (§4); nothing is certified now |

### 8.6 Technically ready vs. study launchable — residual dependencies

**Technically ready, as demonstrated synthetically:**
- the window can be prepared through the app;
- an unauthorized run on it is refused;
- one continuous run crosses months, survives a crash or a pause, and resolves tail paths;
- per-call results, hours and owners can be arranged without imputation.

**Still needed before the study can start or be computed:**
1. **Director**:
   - accept or reject this executive build and its equivalence evidence (§8.3–8.4), deciding on any further targeted checks;
   - complete the freeze before **2027-01-25T00:00Z**, or the window lapses (design §5).
2. **Exact-SHA CI** of the executive build, reported by the Owner (not polled).
3. **Computation conventions** to register before computing, already listed in §7:
   - the bootstrap draw procedure;
   - how included entered paths without a determinable result are represented in the bootstrap and in the balance.

   The ledger stops there: `NOT_COMPUTED_CONVENTIONS_OPEN`.
4. **Separate assignments:**
   - acquisition after 2027-07-26T06:05Z;
   - the Owner's preparation and launch through the Workbench;
   - the GET export and ledger;
   - the bootstrap computation.

   The run duration for about 217 days is not measured here.
5. **Exposure declarations** in the [study exposure register](STUDY-EXPOSURE-REGISTER.md).

**Noted, not changed.** The pack manifest keeps its existing input-requirement label (`btc.context-action.v0.2` register of `presets.json`), as for every pack. The method of the run is the pinned v0.6 identity.

### 8.7 Technical commands (no real launch is authorized)

```text
# after the tail end, under the executive assignment, in the app:
Historical Workbench → Prepare data → other presets → "A v0.6 operational evaluation — 2027-01-25 to 2027-07-26 …" → Prepare
Historical Workbench → Adviser evaluation → that pack → method v0.6 → Start
# then, read-only:
uv run python scripts/a_v06_study_ledger.py export --api http://127.0.0.1:8000 --evaluation <evaluation id> --out <new dir>
uv run python scripts/a_v06_study_ledger.py ledger --export <that dir> --out <new dir> --assignment "<assignment reference>"
```

### 8.8 Review correction — ledger attestation (base `2018634`)

The ledger now presents a COMPLETE balance or any hourly value only when every check of `attest` passes:
- the identities match `identities-b47b997.json`;
- the run is completed, with report completion COMPLETE and the clock end reached;
- the same evaluation and replay ids appear in the export manifest, evaluation, report, calls and both journal exports;
- the exported in-window calls equal the report's own in-window call list and count;
- the exported PRIMARY paths equal the report's PRIMARY path count.

**If any check fails.** The balance status is `NOT_ATTESTED_IDENTITY_OR_COMPLETENESS`. There is no complete balance, and every hour has no value with status `NOT_ATTESTED`. Possibly missing calls are therefore never shown as abstention hours. This is separate from `INCOMPLETE_UNDETERMINED_PATHS` (included paths without a result).

**Limit of the GET surfaces.**
- No authoritative per-kind count of journal records is exposed, so the completeness of the scenario/entry journal pages cannot be attested.
- The owner register stays descriptive and is never a completeness proof.
- Neither the API nor persistence was changed.

**Checks.**
- `tests/test_a_v06_study.py`: 11 passed. They cover identity mismatch, a run not completed, an export of another run, an incomplete call list, and the complete valid case keeping the earlier results.
- `tests/test_a_v06_study_db.py`: 3 passed on a disposable PostgreSQL, which was removed; the evidence was regenerated and is attested and COMPLETE.

**Build.** `src/` is unchanged, so the executive build candidate is still `be44370`; only the ledger script hash changed. Studies INACTIVE.

## 9. Statistical completion — offline bootstrap (base `b2ebf20`; synthetic evidence only; study INACTIVE)

**Authoritative decision — registered afterwards.** At the time of the tool delivery (`e52f237`) the decision text had not been received. It is now registered verbatim in a separate [decision](A-V06-STATISTICAL-CONVENTIONS-DECISION.md) (base `e52f237`). That decision:
- approves the two conventions: the bootstrap draw procedure of §9.2, and the undetermined-path and attestation protections of §9.3;
- accepts `be44370` as the designated executive build candidate, with behaviour reference `b47b997`.

It certifies neither general equivalence, nor green CI, nor readiness for real execution. The conventions therefore close the open items of §7 and §8.6(3). The design term is not extended.

**Status.** Decision registered; statistical implementation delivered, awaiting the Director's final review; studies INACTIVE.

### 9.1 Identities, product and tools kept separate

| Kind | Item | Identity |
|---|---|---|
| Product | Behaviour reference | `b47b997ee93513c7a358b49e961020705e4fbb85` |
| Product | Designated executive build candidate | `be44370f958a9b60f4b02e036102a23247f361d8`; `src/` unchanged since; no equivalence in general and no CI is certified |
| Study tool | Ledger `a-v06.study-ledger.v2` | [`scripts/a_v06_study_ledger.py`](../scripts/a_v06_study_ledger.py), SHA-256 (LF) `08fd3e4a612ed0a96b48802a4d05d609c9221cb4dbec3a8778f379c1119ae929` |
| Study tool | Bootstrap `a-v06.study-bootstrap.v1` | [`scripts/a_v06_study_bootstrap.py`](../scripts/a_v06_study_bootstrap.py), SHA-256 (LF) `5ca2ca827000fad690dcbd0c3bc07b333526f063ccd27a19fcb708f5ea7ed57a` |
| Configuration | Frozen bootstrap configuration | L 168, B 10,000, seed 0, p 0.025 / 0.975; canonical SHA-256 `82341f37ea73dcdf650e462e594bd5931167db8b32ddf262843f2fc045068db0` |

The tool commits are the delivery commits recorded in STATE. The study tools are not product code and are not part of the build candidate.

### 9.2 Procedure implemented

- **Grid.** The complete UTC hourly grid of the evaluation window (N = 4368 for the study), never compressed to the hours with calls.
- **Values.** Each hour carries the ledger's attested value. A zero is only an attested null contribution (no A call, or NO_ENTRY only); it is never missing data or an unresolved path.
- **Blocks.** Moving blocks of L = 168 h, k = ceil(N/L) (26 for the study), the last block truncated to N - L(k-1), no circular wrap.
- **Draws.** One `random.Random(0)`, one `randrange(N - L + 1)` per block, in the order resample b = 0..9,999, then block j = 0..k-1.
- **Statistic.** The exact sum of the resampled hourly values.
- **Interval.** 95% percentile interval, Hyndman-Fan type 7, p = 0.025 / 0.975, h = (B - 1)p. It is reported separately from the observed balance, with no automatic verdict (design §7).
- **Traceability.** The output records:
  - ledger and hour-series hashes, the ledger tool and script hash, the evaluation and replay ids, the build and identity;
  - the configuration and its hash, the procedure text and the percentile convention;
  - block lengths and the start range;
  - the resampled-statistics file and its SHA-256.

  Outputs go to a new directory only. Runs are labelled SYNTHETIC or STUDY; a STUDY run needs the frozen configuration, the STUDY ledger of the registered window, and an assignment reference. The study status is never updated by the tools.

### 9.3 Protections (ledger v2 + bootstrap)

| Case | Ledger balance | Bootstrap |
|---|---|---|
| Identity or completeness not attested | `NOT_ATTESTED_IDENTITY_OR_COMPLETENESS`. No observed or complete balance, **no subtotal**, no hourly value. | `NOT_COMPUTED_NOT_ATTESTED` |
| Attested, at least one included PRIMARY path undetermined | `INCOMPLETE_UNDETERMINED_PATHS`. No observed or complete balance; `partial_subtotal` labelled **PARTIAL** (determined paths only, count excluded, no conclusion on the overall balance). | `NOT_COMPUTED_UNDETERMINED_PATHS` |
| Attested and all determinable | `COMPLETE`, with the observed balance | `COMPUTED`: interval separate from the observed balance, no verdict |

Further refusals: a ledger version other than v2, a grid that is not the window's complete hourly grid, an hour without an attested value, hourly values that do not sum to the observed balance, and a grid shorter than one block.

The owner register stays descriptive (`owner_register_scope`). It is not an exhaustive diagnosis of missing confirmations or issues, and it is separate from the attested primary calls and paths.

### 9.4 Checks run

- `tests/test_a_v06_study_bootstrap.py` (5 passed). Expected statistics are recomputed independently in the test: explicit slices, the test's own generator, Fraction type-7.
  - A hand-specified 7-hour series with zeros in place gives lengths [3, 3, 1]. The statistics equal the expected ones and differ both from the transposed draw order and from a grid compressed to non-zero hours. The interval is exact, reproducible and never overwritten.
  - Undetermined paths and an unattested ledger: no statistics and no interval.
  - The frozen configuration on a synthetic 4368-hour window: 26 x 168 blocks, starts 0..4200, 10,000 statistics equal to the independent recomputation. A STUDY run refuses a non-frozen configuration, a missing assignment, and a synthetic ledger.
  - A pure-fold study ledger through the bootstrap.
- `tests/test_a_v06_study.py` (11 passed), adapted to the v2 balance. A failed attestation now blocks the subtotal too, and the undetermined case gives an explicit PARTIAL subtotal.
- `tests/test_a_v06_study_db.py::...end_to_end...` (1 passed, disposable PostgreSQL, removed).
- No product suite: `src/` unchanged.

**Synthetic evidence**, built offline from the registered `synthetic-export/`, with no earlier output overwritten:
- `synthetic-ledger-v2/`: attested, COMPLETE, -0.0014, 7 hours.
- `synthetic-bootstrap/`: SYNTHETIC configuration L 3, B 1,000 (the 7-hour window is shorter than 168 h); COMPUTED; statistics hash `d7d877d7...`.

### 9.5 Residual conditions

- The orchestrator decision is registered ([decision](A-V06-STATISTICAL-CONVENTIONS-DECISION.md)); the Director's final review of the statistical implementation is pending.
- Exact-SHA CI of the executive build, reported by the Owner.
- Data and provenance: acquisition after 2027-07-26T06:05Z, then the pack registration.
- Pre-execution controls: the Director's acceptance of the build and its equivalence evidence; the freeze completed before **2027-01-25T00:00Z** (design term unchanged).
- A separate authorization for acquisition, the Owner launch, export, ledger and bootstrap.
- The real run duration (about 217 days of data) is not measured.

## 10. Input provisioning (technical path; no real data acquired)

**Source availability (consulted 10 October 2026; no market-data request was made).**
- **Official OKX API documentation**, <https://www.okx.com/docs-v5/en/> and <https://my.okx.com/docs-v5/en/>. The table of contents lists the endpoints the adapter uses:
  - *Order Book Trading › Market Data › Get candlesticks history*, `GET /api/v5/market/history-candles`;
  - *Public Data › REST API*: *Get mark price candlesticks history*, *Get index candlesticks history*, *Get funding rate history*.

  The text of those sections (retention depth, rate limit, pagination) **could not be read**: the rendered page available to the executor stops before them. The retention depth per endpoint is therefore **not confirmed from the official text in this session**.
- **Search-index excerpts** of the official domain state that *Get funding rate history* "can retrieve data from the last 3 months". This is not read in the section itself.
- **Official historical-data page**, <https://www.okx.com/historical-data>. It lists downloadable datasets: candlestick (OHLC) "from July 2023 onwards", funding rate "from March 2022 onwards", trade history "from September 2021 onwards". This is a separate download product, not the REST endpoints the adapter uses; using it would be a source change and is not proposed.
- **Project evidence (documented, not guaranteed).** On 2026-10-03 the Owner's real preparation obtained complete trade, mark and index 1m rows for 2025-08-28 → 2025-10-01 06:05, about 13 months back. The same preparation returned 0 funding rows in every window (`EMPTY_UNKNOWN`): [evidence](evidence/WP-008-R3-OWNER-SEPTEMBER-PREPARATION.md).
- **Adapter limits** (`marketdata/okx.py`, `dataset.py`): public REST only, no key; `after`/`before` exclusive paging, newest first, `limit` ≤ 100 rows per page, ≤ 4 requests/s; `confirm=0` bars are never used; each dataset spans at most 31 days.

**Documented vs guaranteed.** Recovery of 1m candles about 3 months (HDP-001) and 7 months (A v0.6) back is consistent with the project evidence above. It is **not guaranteed**: retention can change, and the official per-endpoint text was not read. Acquiring promptly after each window's end lowers the risk but is not a guarantee.

**Series required by the registered profile** (§3, design §4).
- **Trade 1m.** Setups, triggers, targets and the evaluator's price path.
- **Mark and index 1m.** The expected base profile row needs `dislocation` enabled, which `engine_config` grants only when the pack has mark and index channels. Without them the profile becomes the "no mark/index" row of §3, an identity the design did not register as the base.
- **Funding.** Optional. The result is PRICE_NET_ONLY unless the pack's funding capability is `AUTHORITATIVE_COMPLETE`.

**Exact coverage.** The registered study preset: initialization 2026-12-21T00:00Z → evaluation [2027-01-25T00:00Z, 2027-07-26T00:00Z) → tail to 2027-07-26T06:05Z. Trade, mark and index cover [2026-12-21T00:00Z, 2027-07-26T06:05Z), UTC half-open whole minutes. Funding settlements are fetched over the same interval. Clock end = tail end + 0 allowance. Nothing is added.

**Funding limit — reported, not resolved.**
- The API funding history is consistent with a window of about 3 months (above). After the tail end, settlements from December 2026 to about April 2027 would no longer be retrievable through the adapter.
- Certified funding would therefore need either collection during the window (preventive collection) or a different source; neither is started or proposed here.
- With the registered design this does not block the study: the run stays PRICE_NET_ONLY (expected base row `7c868…0296` / `85504…615c`), as the design foresees.
- PRICE_NET_ONLY is already admitted by the design and the disposition (§10.1); no new funding decision is required. Uncovered funding is never read as zero funding or as a complete net result.

**Acquisition plan** (existing pack job, `UTC_MONTH_AND_MAX_SPAN`). With no local package there are 8 parts:
- [2026-12-21, 2027-01-01);
- then each calendar month 2027-01 … 2027-06;
- [2027-07-01, 2027-07-26T06:05).

A compatible local package already covering part of the range, for example the HDP-001 December 2026 dataset, is reused and never re-fetched. If the source values changed between the two acquisitions, composition fails visibly on the conflict; it never chooses one silently.

**Steps** (after 2027-07-26T06:05Z, only under the executive assignment; no real launch now):

```text
Historical Workbench → Prepare data → other presets → "A v0.6 operational evaluation — 2027-01-25 to 2027-07-26 …" → Prepare
(pack job: reuse local parts, acquire missing parts, compose one immutable receipt-pinned pack; preparation report: Copy)
Historical Workbench → Adviser evaluation → that pack → method v0.6 → Start   (a READY_WITH_LIMITATIONS pack needs acknowledgement)
then the GET export, ledger and bootstrap of §8.7 / §9
```

**Controls and artifacts** (existing, unchanged).
- Every source package is verified once through the receipt-pinned cache boundary.
- Composition: identical overlapping slots collapse; a MISSING placeholder yields to valid evidence; conflicting values fail the job; a source rejection or API error is a failed part, never a trusted empty package.
- The pack manifest records sources, slices, coverage counts per family and window, overlap facts, a provenance file and capability facts (funding `EMPTY_UNKNOWN` unless observed).
- Pack identity is content-addressed. A new acquisition with different content gives a new pack, never a replaced one.
- Completeness is counted per minute and per family in the manifest coverage, not inferred from file names or request success.
- **Delivered to the executor:** `pack_id`, feed content identity, windows and clock end are pinned by the run (`engine_config`) and re-checked by the ledger.

**Synthetic checks run.**
- `tests/test_a_v06_study.py` (12 passed): the study window's exact acquisition plan (8 parts, no margin), and reuse of a local part.
- `tests/test_a_v06_study_db.py` end-to-end (passed): the composed pack's id, feed content identity, requested start and tail end equal the run pins and the ledger.
- `tests/test_pack.py` + `tests/test_pack_correction.py` (disposable PostgreSQL; 31 passed together with the end-to-end test) cover the composition path:
  - boundary slices between contiguous parts and local reuse (`test_local_month_reused_only_boundary_slices_downloaded…`, `test_larger_covering_package_is_sliced…`);
  - gaps and conflicting overlaps (`test_conflicts_fail_and_gap_placeholders_yield_to_valid_evidence`);
  - equivalent packagings with identical semantics, overlaps collapsed (`test_equivalent_packagings_compose_identical_semantics`);
  - source-boundary cutoff, honest capabilities, acknowledgement of gaps, crash/tamper recovery.

**No product change.** `src/` is unchanged, so the candidate stays `be44370` with no re-examination needed. No study tool changed: the HDP-001 executor, ledger and bootstrap identities are unchanged; only tests were added.

**Residual.**
- The official per-endpoint retention is unconfirmed (above).
- Funding not covered: PRICE_NET_ONLY applies (§10.1); no preventive collection or source change is authorized.
- Acquisition after 2027-07-26T06:05Z and Owner preparation and launch, under a separate authorization.
- Pre-execution controls, including exact-SHA CI reported by the Owner; design term 2027-01-25T00:00Z.
- The real preparation and run duration are not measured.

### 10.1 Orchestrator disposition on input provisioning (verbatim; registered 10 October 2026)

Registered on base `6e55e509b2f6faa944c8c43b0e000bc28a717372`, after the executor's provisioning notes above, which are kept unchanged as delivered. The text below is the orchestrator's disposition, verbatim, as relayed by the Owner. Only this heading and sentence are editorial.

```text
Accetto il limite documentale e mantengo il recupero post-finestra previsto. Non autorizzo raccolta preventiva o cambio di fonte.

È un’accettazione del rischio che lo studio possa risultare ineseguibile o incompleto, non una certificazione della disponibilità futura. Il recupero storico già riuscito sostiene la fattibilità, ma non garantisce che le stesse serie saranno recuperabili nel 2027.

Possiamo quindi chiudere lo step distinguendo:

- Percorso tecnico documentato e verificato sinteticamente, sulla base della review e delle evidenze dell’executor.
- Disponibilità futura della fonte non attestata, da verificare quando sarà autorizzata l’acquisizione.
- Funding non coperto: resta applicabile PRICE_NET_ONLY, senza interpretarlo come funding nullo o risultato netto completo.
- Serie necessarie mancanti: applicare soltanto i trattamenti delle lacune già registrati; se non consentono una valutazione valida, dichiararla non valutabile. Nessuna sostituzione, modifica del profilo o spostamento della finestra impliciti.

Direttore, registra questa disposizione nei riferimenti esistenti e chiudi autonomamente lo step. Non serve un altro incarico di ricerca documentale per tentare di ottenere una garanzia che la documentazione potrebbe comunque non offrire. Se emergerà una comunicazione ufficiale concreta di dismissione o riduzione dello storico, quella sarà una nuova evidenza da portarmi prima dell’acquisizione.

Con questa chiusura termina il ciclo preparatorio dei due studi: non continuiamo ad aggiungere controlli o infrastruttura in assenza di un impedimento concreto. Restano le condizioni pre-esecuzione già elencate e l’autorizzazione separata.

Entrambi gli studi restano INACTIVE; v0.6 e HDP-001 congelati. Nessuna acquisizione, consultazione di dati Owner o interrogazione CI.
```

**Status after the disposition.**
- The preparatory cycle is closed within the documented limits.
- Future source availability is not attested; the risk is accepted.
- Funding not covered: PRICE_NET_ONLY.
- Missing required series get only the registered gap treatments, or the result is NOT_EVALUABLE.
- No implicit substitution, profile change or window shift.
- The pre-execution conditions and a separate authorization remain.
- A v0.6 INACTIVE.
