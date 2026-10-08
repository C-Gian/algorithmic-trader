# WP-014 — MP-004 v0.5 engineering evidence

> **Corrected by the WP-014 correction (§9).** Sections 3, 4 and 7 below describe the corrected semantics; the
> superseded readings of `0526641` (dispatch-level local precedence, economic emptiness deferred to the recovery, a
> separate late class, "always straddles" in live) are listed in §9 and are no longer implemented.

Base `776752e` (main). Executor evidence for Director review — **not acceptance**. Synthetic bounded inputs only: no acquisition, no Owner data or stack, no economic evaluation, no protected period. Remote CI: Owner-operated, PENDING / NOT CHECKED.

## 1. Registration

| Document | Role |
|---|---|
| [MP-004-V05-RETURN-RESPONSE.md](../MP-004-V05-RETURN-RESPONSE.md) | Authoritative specification, byte-identical to the Owner's attachment (SHA-256 `ddb09102…3c51`) |
| [MP-004-DIRECTOR-CLOSURE.md](../MP-004-DIRECTOR-CLOSURE.md) | Director closure recorded verbatim (both §8 joints accepted; semantics, not effectiveness) |
| [WP-014-MP-004-IMPLEMENTATION-SPEC.md](../WP-014-MP-004-IMPLEMENTATION-SPEC.md) | Activation recorded verbatim + index |
| [MP-004-PARAMETERS.json](../MP-004-PARAMETERS.json) | **Executor-derived** register: every MP-003 key and all 108 numerical values unchanged, plus the categorical `mp004_policy` transcribing MP-004 (for Director review) |
| [WP-014-CONTINUOUS-V04-V05-PLAN.md](../WP-014-CONTINUOUS-V04-V05-PLAN.md) | Continuous Sep–Dec v0.4/v0.5 comparison, **INACTIVE** |

## 2. Identity matrix

| | v0.4 (unchanged) | v0.5 (new) |
|---|---|---|
| Model / rules | `btc.context-action.v0.4` / `mp003.rules.v0.4` | `btc.context-action.v0.5` / `mp004.rules.v0.5` |
| Rules identity | manifest: MP-003 delta + MP-002 rules/disposition + MP-001 | manifest: MP-004 delta + MP-004 Director closure + MP-003 + MP-002 rules/disposition + MP-001 |
| Implementation / state / runtime | `adviser.core.v4` / `adviser-state.v4` / `adviser-runtime.v4` | `adviser.core.v5` / `adviser-state.v5` / `adviser-runtime.v5` |
| Evaluator | `adviser.evaluator.v3`, `adviser-evaluation-state.v2` | same (reused unchanged) |
| Engine / report | `observe.stream.v5` / `adviser.report.v4` | `observe.stream.v6` / `adviser.report.v5` |
| Reconciliation / Deep | v7 / v8 | v8 (+ A RETURN response lineage) / v9 |
| Contracts | semantic.v2 r3 | semantic.v2 **r4** (`EntryAttemptV5.response`); observe.v1 **r8** (value `v0.5` only); adviser-evaluation.v1 r3 unchanged; no DB migration |

Absent selection is still v0.2. A run or live lineage is never converted across methods (`INCOMPATIBLE_ADVISER_IDENTITY`, `METHOD_CHANGED:v0.4->v0.5`).

## 3. Kernel delta (`adviser/core5.py`)

`AdviserCoreV5` subclasses the v0.4 fold. `core3.py` gained behaviour-neutral hooks only (WAIT class, `_wait_protect`/`_wait_step` split, `_return_gates`, `_return_usable`, `_return_candidate`, `_return_rejected`, `_entry_extra`). The previous-version outputs prove neutrality (§5).
- **WAIT_RETURN** = the inherited WAIT_PRICE. The first bar that would be a usable v0.4 RETURN prepares the reference (H0, L0, bar, interval, p0 = this dispatch, c0 = admitted cursor); a blocked bar does not prepare.
- **WAIT_RESPONSE.**
  - Inherited protections run first, unchanged: deadline, context veto, target/cap contacts, causal caps, plus the scenario V/destination and coverage handled earlier in the dispatch.
  - Then the inherited corridor/economic terminals, after the cap updates and before any local response: an empty effective corridor → `EMPTY_RETURN_CORRIDOR`; an empty historical economic region → `NO_ECONOMIC_RETURN_REGION` (both X). A live envelope too wide for any admissible price is only a temporary blocker (`TEMPORARY_COST_BLOCKED` at the recovery).
  - Then the local sequence is read in bar order and consumed by its **first decisive event**: a bar ending at/before p0 is ignored; a bar straddling p0 (start < p0 < end; start = p0 is in the domain) cannot confirm, and a contrary break there gives `LOCAL_CONTACT_TIME_AMBIGUOUS`; a contrary break gives `LOCAL_RESPONSE_CONTRADICTED`; a recovery is the first recovery. A later bar of the same dispatch never reclassifies it.
  - A first recovery that is not the dispatch's current (latest) bar is `RESPONSE_NOT_ISSUABLE:RESPONSE_OBSERVED_LATE_NOT_CURRENT` (class OTHER_GATES, counted as late). Otherwise the inherited return gates are evaluated on it (historical close / live side price), then slot/conflict/priority → ISSUE or `RESPONSE_NOT_ISSUABLE:<primary>` with all blockers.
- **Records.** `response` on every entry record of a prepared child (reference, phase, bars checked, decisive bar, outcome, primary reason/class; inherited endings annotate local conditions seen in that dispatch without counting them). RESPONSE_OBSERVED is never stored state.

## 4. MP-004 §6 fixtures → expected → actual

Base path (MP-002 fixture): confirmation 04:01, corridor [99900, 100049.9], V 99700, T 100700, deadline 05:30; reference [04:01,04:02) H0 100008 / L0 99990, published 04:02. SHORT = reflection about 100000, economics checked separately with the independent rational reference. All rows pass, LONG and SHORT (`tests/test_mp004_paths.py`, 61 tests).

| §6 row | Tape (LONG) | Expected = actual |
|---|---|---|
| Valid | [04:02,04:03) 99995/100012/99992/100012 | ISSUE 04:03 at 100012; PRIMARY enters 04:04 open (ISSUE ≠ fill); v0.4 issues 04:02 at 99995 |
| Contrary equality + exact threshold | low 99990, close 100008.1 | ISSUE 04:03 at 100008.1 |
| Favourable equality only | close 100008 | no recovery; ORIGINAL_SETUP_DEADLINE 05:30, 87 bars checked |
| Intermediate violation, then valid | low 99989.9, then valid | CONTRADICTED 04:03; later valid bar never examined |
| Violation + recovery same bar | low 99989.9, close 100012 | CONTRADICTED, no ISSUE |
| V + recovery same bar | low 99700, close 100012 | scenario INVALIDATED V_CONTACT has priority; local condition annotated, not counted |
| Economics insufficient | close 100030 (in corridor) | RESPONSE_NOT_ISSUABLE:REWARD_RISK_BELOW_MINIMUM, consumed |
| Outside corridor | close 100060 | RESPONSE_NOT_ISSUABLE:CLOSE_OUTSIDE_RETURN_CORRIDOR |
| Selection: slot / conflict / priority | white-box occupier / opposite / earlier same-direction candidate | REJECT RESPONSE_NOT_ISSUABLE: SLOT_OCCUPIED / CONFLICTED / PRIORITY (class SELECTION) |
| Deadline exactly at the recovery | recovery [05:29,05:30) | ORIGINAL_SETUP_DEADLINE first; recovery annotated only |
| New cap before the recovery | reference 04:45, pivot cap 100495 at 05:00 (WAIT_RESPONSE CAP_REVISION), recovery 05:01 | not issuable on economics with the new cap; reference unchanged |
| Cap contact inside the activation bar | [04:59,05:00) high 100500 ≥ new cap | CAP_ACTIVATION_CONTACT_AMBIGUOUS first |
| Reference published late | reference received 04:03, [04:02,04:03) received 04:03:30 | that bar ignored (recovery or violation); [04:03,04:04) issues 04:04 |
| Recovery received with the next bar (§8 joint 2) | [04:02,04:03) delayed into the 04:04 dispatch | not issuable, late (OTHER_GATES); second valid bar never used; a later break in the same dispatch does not reclassify it |
| Live quote invalid at the recovery | live tape, quote missing for that minute | RESPONSE_NOT_ISSUABLE:QUOTE_STALE (R=1, N=1, I=0) — `test_mp004_live.py` |
| Bar straddling p0 (§8 joint 1) | p0 04:02:30, [04:02,04:03) breaks L0 | LOCAL_CONTACT_TIME_AMBIGUOUS, no renewal; without a break it cannot confirm, a later bar issues |
| Missing data / gap | missing [04:02,04:03) | scenario UNASSESSABLE REQUIRED_MONITORING_GAP; no issue through the hole |
| Warmup / window | eval start 04:03; eval end 04:30 | CLEARED (reference never reused); EVALUATION_WINDOW_ENDED |

The §6 table's own illustrative tuples (R 1000 …) are also checked literally (`local_verdict`, inherited predicate).

## 5. Preservation, durability, assurance

- **Previous versions.** `tests/fixtures/wp014_v04_base_pins.json` was computed on the unchanged base `776752e` in a disposable detached worktree with [WP-014-V04-BASE-PINS.py](WP-014-V04-BASE-PINS.py). It covers 53 v0.4 fixtures (v0.2/v0.3 A/B/C tapes, the 14 MP-003 tapes, the 20 MP-004 tapes), and all reproduce byte for byte. The WP-012 v0.2/v0.3 pins (38) still pass.
- **v0.4/v0.5 parity.** Over 33 fixed tapes, without an A RETURN wait the whole normalized journal and every path are identical (IMMEDIATE, B/C, geometry, costs, deadlines, post-issue). With one, every record before the first usable return is identical, and scenario/landmark lineage is identical throughout.
- **Durable restore.** Production pack/unpack at cuts before the WAIT, in WAIT_RETURN, in WAIT_RESPONSE, after a contradiction, around a late first recovery, inside a long wait and after the issue reproduces the uninterrupted digests (`test_mp004_versions.py`). Cross-method decode is refused.
- **DB** (`test_mp004_db.py`, 12):
  - pure ≡ durable, reconciliation v8 PASS;
  - crash/reclaim at 6 stages with identical outputs and exactly one reference/ISSUE;
  - STEP through WAIT/preparation/issue, paced, and corrupted restore fallback;
  - a v0.5 run never resumes as v0.4;
  - Deep v9 MATCH, and MISMATCH on reference tamper at launch and after a nonzero-cursor resume;
  - API/report/Markdown/comparison;
  - cancelled run with a partial report (A = 1 at the cutoff) and prefix equality.
- **Lineage** (`test_mp004_lineage.py`, 29): every fixture journal passes. Each tampering fails: second or moved reference, wrong publication, call without a reference, same-dispatch or pre-p0 decision, record after ending, inconsistent outcome, RETURN_USABLE record.
- **Report** (`test_mp004_report.py`, 33): §7 counts and identities on the fixture journals; month attribution with a September child issued on 1 October; months summing to the total; partial report; warmup clearings apart; undefined ratios; Markdown; comparison summary; release pins.
- **Live** (`test_mp004_live.py`, 14): method pinned; reference published at the actual dispatch; ISSUE on MEASURED_ASK/BID; no alert before the call; stale quote consumes the child; straddling bar; tape reproduction; restart; DB start.
- **Browser** (`tests/e2e/test_mp004_e2e.py`, 1): v0.5 recognisable before Start, paused response wait shown as "not a call", §7 result, Copy report = Markdown, v0.4/v0.5 comparison, 1024/390 px, live selector.

## 6. Checks run locally (exact)

Disposable PostgreSQL 18.6 container `wp014-pg-disposable` (127.0.0.1:55441, removed afterwards); the Owner's running stack was never touched.
- v0.3/v0.4 refactor guard: `test_mp002_paths`, `test_mp003_paths`, `test_mp002_versions`, `test_mp003_versions`, `test_mp003_correction` — 151 passed, 1 DB skipped (no DB at that time).
- New suites: paths 61, versions 98, report 33, lineage 29, live 14 (with DB), DB 12 — all passed (counts above; DB/live runs with `ALGOTRADER_TEST_DATABASE_URL`).
- Browser: `tests/e2e/test_mp004_e2e.py` 1 passed (after `npm run build`).
- Web `npm run typecheck` and `npm run build` pass; `algotrader schema --write` changed only `observe.v1` (r8) and `semantic.v2` (r4); frozen baselines match.
- Relevant regression set with `ALGOTRADER_REQUIRE_DB=1`: see §8.
- **Not run locally:** the full non-E2E suite, the full E2E suite and the Compose smoke — left to the final exact-SHA CI (Owner-operated). No bounded scaling benchmark was run.

## 7. Interpretations and open decisions for the Director

No semantic conflict required a new rule. These readings are flagged for confirmation; each has a test.
1. **First decisive local event (corrected, F1).** Inherited protections cover the whole dispatch; the local sequence is consumed by its first ordered decisive event. Recovery [04:02,04:03) then break [04:03,04:04) in one dispatch → late first recovery (C=0, R=1, N=1, I=0); break then recovery → C; break and recovery in one bar → C.
2. **Economic terminals in WAIT_RESPONSE (corrected, F2).** `EMPTY_RETURN_CORRIDOR` and `NO_ECONOMIC_RETURN_REGION` keep the v0.4 place: after the cap updates/protections, before the local response (X). A non-empty historical region with an unsuitable recovery price is N; a live temporary cost block is non-terminal until the recovery.
3. **"Current usable bar"** = the dispatch's latest complete minute (the inherited sampling). A late first recovery is classified OTHER_GATES with its specific reason and a separate late count (aligned; no fourth class).
4. **Live publication timing (aligned).** A bar straddles p0 only when start < p0 < end; start = p0 is in the active domain. In live, p0 is the dispatch at the bar's receipt; when that falls strictly inside the next bar's interval (the usual case, receipt shortly after the close) that next bar straddles and cannot confirm, and a break there is UNASSESSABLE. Historical modeled replay publishes at the bar close, so the next bar starts at p0 and can confirm. The inherited confirmation-publication rule behaves the same way.
5. **Month attribution.** A child belongs to the month its WAIT opened and is followed to its ending (the WP-013 WAIT convention); every identity holds per month.
6. **Register.** `MP-004-PARAMETERS.json` is executor-derived; the Director accepts it only for the choices Astra verified (108 inherited values unchanged, `references_per_child = 1`). The inherited `development_evaluation_registration` block is kept byte-identical and not applicable to v0.5; no v0.5 reading criterion is registered, and the earlier 20-owner convention is NOT_APPLICABLE to v0.5 (F3).
7. **Spec erratum (registered separately).** [MP-004-ERRATUM-SECTION-6-RATIOS.md](../MP-004-ERRATUM-SECTION-6-RATIOS.md): SHORT valid ratio 197783/102217 = 1.934932545… (not ≈ 2.08); SHORT insufficient 0.971777…. The pinned spec and its identity are unchanged.
8. **Status labels.** v0.4 keeps its recorded "engineering review pending" label; WP-014 does not change it.
9. **Comparison release pins.** *Pinned release vs current package* is reported as a fact, not a verdict change, so earlier comparisons keep their verdicts. The inactive plan makes MATCHES_CURRENT_PACKAGE a precondition for reusing the v0.4 baseline.

## 8. Regression set (local, exact)

One run with `ALGOTRADER_REQUIRE_DB=1` on the disposable database, after the WP-014 code was complete: `test_mp002_*`, `test_mp003_*`, `test_mp004_*`, `test_observe`, `test_evaluation`, `test_wp013_*`, `test_schema`, `test_contracts`, `test_adviser_method`, `test_adviser_correction_versions`, `test_assurance`, `test_ux_reporting`, `test_ux_wording`, `test_adviser_live`, `test_adviser_integration` → **638 passed, 1 failed** (42 min). The failure was a missed deliberate observe.v1 revision pin (`("PROVISIONAL", 7)` → 8) in `test_observe.py`; it was corrected.

Afterwards (also covering the later comparison release-pin addition): `test_observe`, `test_mp004_report`, `test_mp002_correction`, the paired v0.4/v0.5 DB comparison test, and the browser journeys `test_mp004_e2e` and `test_mp003_e2e` → **82 passed**. Typecheck and build were rerun after the last UI change.

Not run locally: the full non-E2E suite, the remaining E2E journeys and the Compose smoke (left to the exact-SHA CI, Owner-operated). The disposable container was stopped and removed, and the base worktree removed.

## 9. WP-014 correction (Astra review of `0526641`; F1–F3 and alignments only)

MP-004 and every methodological decision are unchanged; no identity, contract or schema changes (the corrected kernel stays `adviser.core.v5`: no v0.5 run exists beyond the executor's synthetic tests).

| Item | Change | Regressions (`tests/test_mp004_correction.py`, LONG/SHORT) |
|---|---|---|
| F1 | `core5._response_step`: the local sequence is consumed by its first ordered decisive event; inherited protections still cover the whole dispatch | recovery → violation: `RESPONSE_OBSERVED_LATE_NOT_CURRENT`, C=0 R=1 N=1 I=0, decisive bar 04:02; violation → recovery: C; same bar: C; recovery then V contact: inherited X |
| F2 | `EMPTY_RETURN_CORRIDOR` / `NO_ECONOMIC_RETURN_REGION` restored during WAIT_RESPONSE after the cap updates, before the local response; the v0.5-only "empty corridor" gate branch removed from `core3._return_gates` (original code) | cap revision to 100300 empties the historical region → X at 05:00, no reopening; empty effective corridor (white-box cap) → X; non-empty region, unsuitable price → N; live temporary cost block → still WAIT_RESPONSE (A), later ISSUE; live block at the recovery → N `TEMPORARY_COST_BLOCKED` |
| F3 | report v5 sets the earlier 20-owner threshold to NOT_APPLICABLE (count kept, minimum null, no substitute); completed verdict REPORTED_FOR_DIRECTOR_REVIEW independent of it; Markdown line, Workbench metric and comparison conclusion/Markdown follow; v0.3/v0.4 unchanged | inherited minimum 2 vs 1 (the 19 → 20 crossing) gives identical v0.5 verdict/Markdown; v0.4 still moves; comparison verdict identical for baseline INSUFFICIENT/REACHED and candidate 19/20 |
| Alignments | late recovery → OTHER_GATES (specific reason, late count); straddling only start < p0 < end (docs; code already so); WAIT-open cohort explanation in the comparison (JSON `responses.cohort`, Markdown, Workbench); erratum registered separately | late class; start = p0 decides; cohort text in comparison |

**Fail-before / pass-after.** On the unchanged `0526641` code: 13 of 27 new correction tests failed (F1 recovery → violation ×2, F2 empty region ×2 and empty corridor ×2, late class, F3 verdict/Markdown, comparison ×4, cohort); the 14 guards passed (violation → recovery, same bar, whole-dispatch protection, unsuitable price, live temporary/at-recovery blocks, v0.4 threshold, start = p0). After the correction: 27/27 pass.

**Earlier v0.5 tests corrected.** `test_in_one_dispatch_the_safety_checks_of_every_bar_precede_the_recovery` encoded the wrong precedence; it is now `test_in_one_dispatch_the_first_decisive_local_event_consumes_the_sequence`. The late class assertions and the report-count precedence assertion were updated accordingly.

**Checks run (exact).** Pure v0.5 suites (`test_mp004_paths`, `_report`, `_lineage`, `_live`, `_correction`, `test_mp002_correction`): 188 passed, 1 DB test deselected/skipped. On a disposable PostgreSQL 18.6 (`wp014c-pg-disposable`, 127.0.0.1:55442, removed afterwards): see §10. Web typecheck/build pass. The full suite and Compose smoke are left to CI.

## 10. Correction checks (local, exact)

Disposable PostgreSQL 18.6 `wp014c-pg-disposable` (127.0.0.1:55442), stopped and removed afterwards; the Owner stack was never touched.
- **One run with `ALGOTRADER_REQUIRE_DB=1`** → **318 passed, 1 failed** (28 min):
  - `test_mp004_versions` (53 v0.4 base pins, v0.4/v0.5 parity, restore at every response stage), `test_mp004_db`, `test_mp004_live`, `test_mp004_correction`;
  - `test_mp003_versions` and `test_mp002_versions` (v0.2/v0.3 pins), `test_mp003_paths`, `test_mp002_paths`, `test_mp003_db`, `test_wp013_correction`, `test_wp013_continuous`;
  - browser `test_mp004_e2e` and `test_mp003_e2e`.
- **The one failure** was the new browser assertion, which looked for the not-applicable hint on the metric *value* element (test locator only). The UI showed the count "1" without "/ 20", as intended. The locator was moved to the funnel container and the v0.5 journey rerun → **1 passed**. It checks: the count without "/ 20"; "earlier 20-owner criterion not applicable"; "NOT_APPLICABLE to v0.5"; Copy report containing "evidence criterion NOT_APPLICABLE"; the comparison cohort text ("WAIT-open cohort", "month of issue"); and "no registered evidence criterion for the candidate".
- Also run: pure v0.5 suites (188 passed, see §9), web typecheck and build.
- Not run locally: the full suite, the other browser journeys and the Compose smoke (CI, Owner-operated). There is no economic run, no acquisition and no Owner data.
