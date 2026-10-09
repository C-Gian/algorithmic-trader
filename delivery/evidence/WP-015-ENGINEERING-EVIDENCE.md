# WP-015 engineering evidence — MP-005 v0.6 (initial incompatibility of the RETURN reference)

Base `3c6af11`. Synthetic engineering inputs only. No acquisition, Owner extraction, real-data replay, Deep validation of a real run, economic run or comparison. The Owner stack was never touched, and no Owner launch is prepared. **READY FOR DIRECTOR REVIEW — WP-015 ONLY; not accepted.**

## 1. Registration and identities

- **Documents.**
  - [MP-005 specification](../MP-005-V06-INITIAL-RESPONSE-INCOMPATIBILITY.md) and [Director closure](../MP-005-DIRECTOR-CLOSURE.md): the relayed authoritative text, split at its separator with no other change.
  - Packaged copies are byte-identical (test).
  - The executive authorization is recorded verbatim, separately, in [WP-015](../WP-015-MP-005-IMPLEMENTATION-SPEC.md).
- **Register** `MP-005-PARAMETERS.json` (executor-derived, for Director review).
  - It is the MP-004 register with `model`, `rules_version` and `identity` changed, plus `mp005_policy`.
  - Every typed parameter is equal to v0.5 (test), so there is no new threshold, tolerance or live minimum cost.
  - New categorical elements only: reason `INITIAL_RESPONSE_INCOMPATIBLE`, bases `CORRIDOR` / `HISTORICAL_ECONOMICS`, CORRIDOR primary when concurrent (the other annotated, one terminal), and response outcome `INITIAL_RESPONSE_INCOMPATIBLE`.
- **Identities.**

| Item | v0.6 |
|---|---|
| model / rules | `btc.context-action.v0.6` / `mp005.rules.v0.6` |
| rules identity | manifest of the MP-005 delta, its closure, the MP-004 rules and closure, MP-003, the MP-002 rules/disposition and MP-001 (all v0.5 texts, hash for hash) |
| implementation / evaluator | `adviser.core.v6` / `adviser.evaluator.v3` (reused) |
| state / runtime / engine | `algotrader.adviser-state.v6` / `algotrader.adviser-runtime.v6` / `observe.stream.v7` |
| report / reconciliation / Deep | `adviser.report.v6` / v9 / v10 |
| contracts | semantic.v2 r5: values only, v0.6 emits the revision-4 shapes. observe.v1 r9: method value only. adviser-evaluation.v1 unchanged (r3). No migration. |

- **Preservation of v0.2–v0.5.**
  - Identities and statuses are unchanged; the v0.5 rules/register hashes are `0e34059a…` / `255ab5b7…`, as pinned by the Owner run.
  - **68 v0.5 fixed-fixture pins** were computed on the unchanged base `3c6af11` in a disposable detached worktree ([generator](WP-015-V05-BASE-PINS.py)). They cover the 53 WP-014 fixtures, 5 more MP-004 tapes and the 10 MP-005 tapes (LONG/SHORT), and all reproduce byte for byte.
  - The v0.4 (53) and v0.2/v0.3 pins pass in their own suites.
  - A v0.5 state never decodes as v0.6 and vice versa.

## 2. Kernel delta

`core6.AdviserCoreV6._return_usable` follows the MP-005 §5 order:
1. The MP-004 preparation publishes the `RESPONSE_REFERENCE`.
2. `initial_compatibility(d, H0, L0, tick, C0, A0, historical)` runs. It is pure; `A0` is the region `geometry.admissible_bounds` already computed for this dispatch.
3. If the reference is incompatible, a TERMINAL `INITIAL_RESPONSE_INCOMPATIBLE:<base>` is recorded in the same dispatch, with the same clock and cursor, ordered after the reference.

Details:
- The response stores the bases `F`, `C0`, `A0`, `F_cap_C0`, `J0`, the profile and annotations.
- Live ignores A0 entirely.
- Inherited protections run earlier (`_wait_protect`) and keep their reasons.
- The child's `entry` becomes TERMINAL; the scenario is untouched. Its `entry_ended` presentation record only feeds the view.

## 3. Fixture → expected → actual

Layer 1 is the MP-005 §8/§9 rows, literally, through the pinned functions (abstract prices, tick 1 / 0.01). The corridor uses the `core3` inward rounding.

| Row | Expected (MP-005) | Actual |
|---|---|---|
| §8 geometry L/S | corridors [95,110] / [90,105]; regions [95,103] / [97,105]; close 100 usable | equal (`admissible_bounds`, `predicate`) |
| H1 L/S | F ≥104 / ≤96; F∩C0 ≠ ∅, J0 = ∅ → HISTORICAL_ECONOMICS; B1 satisfies the predicate | equal; F∩C0 = [104,110] / [90,96] |
| H2 L/S | F ≥111 / ≤89; F∩C0 = ∅ → CORRIDOR, economics annotated | equal |
| H3 L/S | J0 = {103} / {97} non-empty; B1 at the threshold with contrary equality, issuable at the economic edge | equal; one tick further is inadmissible |
| H5 L/S | B1 contradiction, B2 recovery (arithmetically) | equal |
| L1 | cost 15 bps; ask/bid in the corridor and admissible; F ≥100.02 / ≤99.98 meets the corridor | equal |
| L2 | cost 34; current region empty; side prices on the corridor edges; B1 neither confirms nor contradicts; no terminal | equal |
| L3 | exact cost near 15 (LONG 14.9997…, SHORT 15.0003…, never rounded); ratio > 1.2; recovery | equal |

Layer 2 is reachable engine tapes on the MP-002 base A path. Corridor [99900, 100049.9], A0 [99900, 100014.5], L0 99990; SHORT is the reflection. The tuple is (P,X,C,R,N,I,A).

| Tape (LONG and SHORT) | Expected | Actual |
|---|---|---|
| H1 `REF_ECON` (H0 100014.5) | 04:02 reference + TERMINAL HISTORICAL_ECONOMICS, same dispatch; (1,1,0,0,0,0,0); scenario CONFIRMED until its own terminal | equal; F∩C0 [100014.6, 100049.9], J0 ∅ |
| H2 `REF_COR` (H0 100049.9) | CORRIDOR, economics annotated; (1,1,0,0,0,0,0) | equal |
| H3 `REF_ONE` (H0 100014.4) | J0 = {100014.5}: WAIT_RESPONSE (1,0,0,0,0,0,1) at 04:02, ISSUE 04:03 at 100014.5 (1,0,0,1,0,1,0); identical to v0.5 | equal |
| H4 deadline collision | reference bar published at the 05:30 deadline: ORIGINAL_SETUP_DEADLINE, no reference; (0,0,0,0,0,0,0); W counts it before a reference | equal |
| H5 persistence | H1, then contradiction and recovery bars: no C/R, no record; no wait left after the dispatch; restore between them identical | equal |
| live CORRIDOR (`REF_COR`, preparable: close and ask/bid 99995/100005 in the corridor, 14 bps) | reference and CORRIDOR terminal at the 04:04:01 live dispatch; A0/J0 null; no call or alert; view "entry attempt ended — scenario not invalidated" | equal |
| live economics only (`REF_ECON`) | no terminal; recovery 04:06:01 → RESPONSE_NOT_ISSUABLE:REWARD_RISK_BELOW_MINIMUM | equal |
| live temporary cost (REF, then a K = 26 bps quote, then a restored quote) | still WAIT_RESPONSE through the wide quote; ISSUE 04:07:01 on the side price | equal |
| v0.5 on H1/H2 | waits, then R = N = 1 (the classification v0.6 declares lost) | equal |

**No fixture contradicted the actual predicates.** Two arithmetic facts were made explicit: the SHORT L3 cost is 15.0003… bps (the spec says "vicino a 15"), and the professional sequence number is per dispatch, so the order of the two records is the journal order.

## 4. Compatibility checks

- **Parity with v0.5 outside the new terminal**: 75 tapes (every WP-014 fixture, the extra MP-004 tapes and the MP-005 tapes, LONG/SHORT).
  - Without the terminal, the whole normalized journal and every hypothetical path are equal.
  - With it, every record before that dispatch is equal; scenarios and landmarks are equal throughout; and the dispatch adds exactly one TERMINAL after v0.5's reference.
  - Note: the pre-existing v0.3 tape `a3_return_long` (H0 100050 above the corridor top) now ends CORRIDOR (test).
- **Reconciliation v9** (`_v6_initial_compatibility`) checks:
  - same dispatch, clock and cursor as the reference;
  - no bar checked;
  - base, outcome and recomputation from each stored reference's own H0/L0, tick, corridor and region;
  - no incompatible reference left waiting.
  
  Tampering tests: a moved dispatch, a changed base, an injected terminal and a removed terminal are all detected.
- **Deep v10** matches on a clean run and reports a mismatch on an altered stored base.
- **Durability** through the production pack/unpack:
  - Pure: restore before and after the P→X dispatch at four cuts, and inside the H3 single-tick wait. Outputs are identical, with no reopening and one reference and one terminal.
  - DB: crash/reclaim at WAIT_RETURN, at the P→X dispatch, after it, later and at the final commit; STEP through the dispatch. Signatures are identical, there are no duplicates, and nothing follows the terminal.
  - A v0.6 run never resumes under v0.5 (`INCOMPATIBLE_ADVISER_IDENTITY`).
  - A live restart does not reopen or re-prepare.
  - The live input tape replays to the same digests.
- **Reports**:
  - The new count is a subset of X (`initial_incompatible_subset_of_X` identity), never added again.
  - Ratio over P; by base, direction and WAIT-open month; months sum to the total.
  - A cancelled run has A = 0 after a same-dispatch P→X.
  - The declared C/R loss note.
  - The 20-owner criterion is NOT_APPLICABLE.
  - Markdown and Copy report equal the export.
  - The v0.5/v0.6 comparison is COMPARABLE, with the MP-005 limitation and the subset row.

## 5. Checks run (exact)

On disposable PostgreSQL 18.6 `wp015-pg-disposable` (127.0.0.1:55445), removed afterwards. The Owner stack was not touched.

| Suite | Result |
|---|---|
| `test_mp005_paths` | 104 passed |
| `test_mp005_versions` | 83 passed |
| `test_mp005_report` | 14 passed |
| `test_mp005_live` | 9 passed + 1 DB passed |
| `test_mp005_db` (`ALGOTRADER_REQUIRE_DB=1`) | 11 passed |
| E2E `test_mp005_e2e` + regression `test_mp004_e2e` (Playwright, built UI) | 2 passed |
| Regression set, `ALGOTRADER_REQUIRE_DB=1` | see §6 |
| Web typecheck + build | pass |
| `algotrader schema` | matches: only semantic.v2 r5 and observe.v1 r9 rewritten |

Deliberate pin updates in earlier suites:
- the method lists gain v0.6;
- the unknown-method probe moves to v0.7;
- semantic r5 and observe r9;
- the v0.5 run manifest's schema revision is now 9.

Left to the exact-SHA CI (Owner-operated) and not run locally: the full non-E2E suite, the remaining E2E journeys and the Compose smoke.

## 6. Regression set

One run with `ALGOTRADER_REQUIRE_DB=1` on the disposable database after the code was complete. Modules: `test_mp002_*`, `test_mp003_*`, `test_mp004_*`, `test_observe`, `test_evaluation`, `test_schema`, `test_contracts`, `test_adviser_method`, `test_adviser_correction_versions`, `test_assurance`, `test_ux_reporting`, `test_ux_wording`, `test_adviser_live`, `test_adviser_integration`, `test_wp013_*` (non-E2E).

Result: **665 passed, 2 failed** (46 min). Both failures were deliberate pins of the latest release that had been missed:
- `test_mp002_versions` still expected the observe changelog tail 8 and the emitted-revision map without v0.6;
- `test_mp003_db` still expected four method statuses.

They were updated (observe tail 9, map + v0.6 → 5, a fifth ENGINEERING_REVIEW_PENDING). The affected tests were re-run: `test_mp002_versions` 16 passed, and the `test_mp003_db` paired-evaluation test passed. No product code changed after that run.

## 7. Limits

- One synthetic fixture family exercises the engine; the §8/§9 abstract geometries are checked through the pinned functions, not as engine runs.
- The integrated usefulness of v0.6 is unknown, and no economic or frequency claim is made.
- The register is executor-derived and awaits Director review.
- v0.5 and v0.6 both remain *engineering review pending*.
- Under MP-005 §6 the lost C/R classifications are declared, never reconstructed.

## 8. Correction F1 (Astra review of `18f670a`) — READY FOR DIRECTOR REVIEW — WP-015 CORRECTION ONLY

Base `18f670a845a01b16b25db4f1885b27ab2a90ecaf`. Scope: the text of `MP005_LIMITATION` in `adviser/compare.py` only.

- **Defect.** The limitation attributed to the earlier child ending a release of the slot and downstream effects on later selections/outcomes. That is wrong: WAIT_RESPONSE does not hold the slot, and MP-005 neither ends a call nor releases the structural owner.
- **Fix.** The slot-release explanation and its downstream effects are removed. Kept: the loss of the later C/R classifications (no counterfactual reconstructed), and that the new counts show no informational or economic improvement (C/P and R/P changes do not show a better local response; the integrated difference is not a per-call attribution). The limitation id, the comparison shape/version, kernel, method, register, identities and contracts are unchanged. The text reaches the comparison JSON (`limitations`) and its Markdown/Copy text through the same constant.
- **Regression.** `test_mp005_report.py::test_comparison_mp005_limitation_text_in_json_and_markdown` checks the v0.5/v0.6 comparison JSON text and its Markdown line: the retained statements are present; `slot`, `free`, `releas`, `selection`, `downstream` are absent. It fails on the base text and passes on the corrected one.
- **Checks run (pure, no DB).** `tests/test_mp005_report.py` + `tests/test_mp004_report.py`: **48 passed**. Comparison tests in `test_mp002_correction.py` / `test_mp004_correction.py` (`-k compar`): **6 passed**. Per the correction scope, the full suite, E2E, DB suites (including the `test_mp005_db` comparison, whose limitation id assertion is unchanged) and Compose were not run. Remote CI is Owner-operated: PENDING / NOT CHECKED.
