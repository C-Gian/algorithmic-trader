# WP-012 engineering evidence — MP-003 v0.4 (pre-confirmation A reaction anchor)

Executor evidence for Director review. **Not acceptance.** No Owner economic run was launched; no Owner data was read; no protected period touched.

**Scope.** Base `68f26da` (product source identical to the accepted `3fcbfc5`).
- Implemented: `btc.context-action.v0.4` / `mp003.rules.v0.4` from closed [MP-003 v0.2](../MP-003-A-REACTION-ANCHOR-DISPOSITION.md), the [Astra closure](../MP-003-ASTRA-CLOSURE.md) and the [complete register](../MP-003-PARAMETERS.json).
- v0.4 is selectable in the historical and live paths.
- v0.2 and v0.3 are preserved.

Structured data:
- [JSON](WP-012-ENGINEERING-EVIDENCE.json): fixture table, identity matrix, checks.
- [Fixture table generator](WP-012-FIXTURE-TABLE.py).
- [Bounded measurement](WP-012-bench-mp003.json).

## 1. What changed (and what did not)

**`adviser/core4.py` (`adviser.core.v4`)** subclasses the v0.3 fold. It overrides only the A pre-confirmation domains.

- **Local contact.** A newly admitted complete interval, wholly after the active anchor's actual publication, with LONG `low <= V` (SHORT `high >= V`, inclusive):
  - invalidates that anchor (`ANCHOR_LOST`, `INVALIDATED`);
  - the same scenario returns to WATCH;
  - owner, latch, zones, child budget, birth A/B/S15/z and the original deadline are unchanged.
- **Ambiguous contacts.** These make only the anchor `UNASSESSABLE`:
  - an interval straddling the anchor publication;
  - a late-admitted interval that lies in an earlier epoch's domain and reaches that epoch's V.
- **Dead anchors** are never re-tested.
- **Replacement (`REARM`).** It must come from a 15m bar that completes in the current dispatch and meets all of:
  - market end at/after the lost contact-interval end;
  - clean reaction strictly deeper than the lost R;
  - R > A+z and R < B − 0.25·birth S15;
  - allowed context, no opposite expansion.

  Then K = that bar's high and V = R − birth z. Publication is the actual dispatch time/cursor, after contacts, structural terminals and the 15m close predicates. No interval admitted at or before the publication can confirm it.
- **Supersession without contact (`REVISE`)** keeps the inherited inclusive tie.
- **Destination B** is monitored only from the immutable first-arm publication time/cursor, and stays monitored in WATCH after a loss:
  - straddling origin → scenario `UNASSESSABLE`;
  - local contact and destination in the same interval → `UNASSESSABLE`, no replacement.
- **Before the first arm**, only the inherited spend (> B+z) and the A+z close withdrawal apply.
- **An ever-armed unconfirmed scenario** needs fresh/complete 1m and 15m evidence: a gap or staleness → `UNASSESSABLE`.
- **After the first confirmation**, R/K/V are frozen (`FROZEN_AT_CONFIRMATION`) and everything is v0.3:
  - WAIT/RETURN, caps, costs, selection;
  - call protection;
  - evaluator.

**Shared plumbing, behaviour-neutral for v0.3.** `core3.py`/`runtime3.py` gained hooks:
- scenario class, state format and record-kind table;
- `_scen_extra`, `_monitored`, and a per-interval helper `_scen_interval` (an extract of the unchanged loop body).

All 38 v0.2/v0.3 fixed-fixture outputs (journal + evaluation sequence/chain + calls) equal pins computed on the unchanged base: `tests/fixtures/wp012_v02_v03_base_pins.json`, `tests/test_mp003_versions.py`.

**Unchanged:**
- every numerical value (101/101 numeric register leaves and the typed parameters are equal to MP-002);
- the evaluator (`adviser.evaluator.v3` reused; adviser-evaluation.v1 stays revision 3);
- the v0.2/v0.3 codecs, readers and stored results;
- frozen schemas, source notes and research.

No database migration.

## 2. Identity matrix

| | v0.2 | v0.3 | v0.4 |
|---|---|---|---|
| model / rules | btc.context-action.v0.2 / mp001.rules.v0.2 | …v0.3 / mp002.rules.v0.3 | …v0.4 / mp003.rules.v0.4 |
| rules identity | MP-001 file hash | MP-002 file hash | manifest hash: MP-003 delta + MP-002 rules + MP-002 disposition + MP-001 rules |
| core / state | adviser.core.v2 / adviser-state.v2 | adviser.core.v3 / adviser-state.v3 | adviser.core.v4 / adviser-state.v4 |
| runtime / engine | runtime.v2 / observe.stream.v3 | runtime.v3 / observe.stream.v4 | runtime.v4 / observe.stream.v5 |
| evaluator / eval state | evaluator.v2 / eval-state.v1 | evaluator.v3 / eval-state.v2 | evaluator.v3 / eval-state.v2 (reused) |
| report / reconciliation / Deep | report.v2 / 5 / 6 | report.v3 / 6 / 7 | report.v4 / 7 / 8 |
| semantic.v2 emitted revision | 1 | 2 | 3 |
| status | ACCEPTED_BASELINE | TECHNICALLY_ACCEPTED (corrected; identity unchanged) | ENGINEERING_REVIEW_PENDING |

Default (absent selection) stays v0.2. A changed inherited text changes the v0.4 rules identity (test with a modified disposition copy).

Public contracts:
- **semantic.v2 revision 3:** `ScenarioStateV4`, plus transitions `ANCHOR_LOST` and `REARM`.
- **observe.v1 revision 7:** value-only. It admits the method `v0.4` and engine `observe.stream.v5`. No field, type or shape changed; it was bumped because the documented value domain of a public field changed.

Both have changelogs. Frozen baselines are byte-identical (`algotrader schema` matches).

## 3. MP-003 §6 fixtures (fixture → expected → actual)

All rows are hand-expected tapes on the MP-002 base A path: A 97000, B 100900, birth S15 2000, z 200, first ARM 03:45 with R 100000 / K 100700 / V 99800. Each runs LONG, and the positive-price reflection runs SHORT; the actual SHORT sequence is identical in every row.

Tests: `tests/test_mp003_paths.py` (46 cases); generator `WP-012-FIXTURE-TABLE.py`.

| §6 row | Expected (hand) | Actual (v0.4) |
|---|---|---|
| 1 never armed | no terminal at high ≥ B or at high = B+z; spend > B+z | SPENT 04:15 only |
| 2 first-arm source touched B | no retroactive terminal; later minute ≥ B terminates | ARM 03:45; DESTINATION 03:51 |
| 2 delayed publication/backlog | B contact admitted before the delayed ARM ignored | ARM published 03:50; DESTINATION 03:51 |
| 2/12 straddling origin + B | UNASSESSABLE, not success | ARM 03:45:30; UNASSESSABLE FIRST_ARM_DESTINATION_CONTACT_TIME_AMBIGUOUS 03:46 |
| 3 lost anchor, B later | destination still monitored in WATCH | ANCHOR_LOST 03:51; DESTINATION 04:21 |
| 4–5 contact → WATCH → deeper reaction | old anchor journalled; prospective new epoch; later fresh confirmation | ANCHOR_LOST 03:51 e1; REARM 04:00 e2 (R 99790 K 100300 V 99590); CONFIRM 04:09 |
| equality / ties | low = V is contact; replacement strict; supersession inclusive | ANCHOR_LOST at V; no REARM at lost R, REARM one tick deeper; REVISE at R |
| 6 contact + seal in one dispatch | loss first, REARM same dispatch, no retroactive confirmation | ANCHOR_LOST + REARM 04:00 (same cursor, loss first); CONFIRM 04:01 from [04:00,04:01) |
| 6 admitted recoveries | minutes admitted before a delayed REARM never confirm | REARM 04:05; CONFIRM 04:06 (04:00–04:04 closes ≥ K+tick ignored) |
| old bar | bar ending before the contact cutoff never re-arms | ANCHOR_LOST 04:03; REARM 04:20 from [04:00,04:15) |
| late earlier-epoch evidence | newer anchor unassessable | REVISE 04:05 e2; ANCHOR_LOST UNASSESSABLE 04:05:30 |
| 7 15m close ≤ A+z | terminal, no replacement | WITHDRAWN 04:00 |
| 11/7 wick through A+z; no eligible reaction | WATCH until deadline; no call | EXPIRED 05:30, 0 calls |
| 8 deadline vs candidate | expiry first | EXPIRED 05:30, no REARM (control variant re-arms 05:15) |
| 9 confirmed WAIT + V contact | terminal, no re-anchor/reconfirm | INVALIDATED 04:02; entry WAIT_OPEN → TERMINAL |
| 10 issued call + V contact | existing protection, identical to v0.3 | revisions and paths equal v0.3 |
| 12 local + destination / gap / straddling local | UNASSESSABLE / structural terminal / anchor-only ambiguity | as expected (see table) |
| 13 cost profiles, evaluator on/off, appended future, restore, STEP/paced, live tape | identical normalized structural lineage | K 2/14/500 bps identical structural records; evaluator on/off identical digests; production pack/unpack at 7 cuts identical bytes; DB and live checks below |

## 4. Checks run (local, disposable PostgreSQL 18.6 on port 55439; Owner stack untouched)

| Check | Result |
|---|---|
| v0.4 pure fixtures `tests/test_mp003_paths.py` | 46 passed |
| v0.4 versions / codec / parity `tests/test_mp003_versions.py` | 55 passed (incl. 38 v0.2/v0.3 byte pins, B/C + post-confirmation parity on 9 tapes) |
| v0.4 durable DB `tests/test_mp003_db.py` | 11 passed (equals pure fold; reconciliation v7; crash/reclaim at 5 anchor stages; STEP/paced/cadence; corrupt-restore fallback; no cross-method resume; Deep v8 match, start tamper, nonzero-cursor resume tamper; paired v0.2/v0.3/v0.4 reports + comparison; cancelled-run prefix report) |
| v0.4 live (synthetic tapes, fake clients) `tests/test_mp003_live.py` | 5 passed (with DB) |
| Browser `tests/e2e/test_mp003_e2e.py` | 1 passed (v0.3 baseline; v0.4 paused under observation; STEP to new anchor; result anchors; cancel; comparison + copy = Markdown; 1024/390 px no overflow) |
| Final full non-E2E (`ALGOTRADER_REQUIRE_DB=1`) | 824 passed, 2 failed (both the deliberate observe.v1 revision pin 6->7 in tests/test_observe.py; pins updated, tests/test_observe.py rerun 21 passed); 42m43s, ALGOTRADER_REQUIRE_DB=1 |
| Full E2E (Playwright, all journeys incl. v0.3 and v0.4) | 20 passed (6m13s) |
| Web typecheck + build; `algotrader schema` | pass; only semantic.v2 r3 / observe.v1 r7 baselines rewritten |

Sequence:
- Focused suites were run during development.
- One final full non-E2E run (2 expected revision-pin failures, then `tests/test_observe.py` rerun).
- A cosmetic line re-wrap in `core3.py` followed, after which the affected suites were rerun (MP-003 paths/versions, MP-002 paths/rules: 137 passed).
- Full E2E last, on a fresh web build.

The expected pin updates in existing tests:
- v0.3 status → TECHNICALLY_ACCEPTED;
- revisions (3, 3, 7);
- the "unknown method" example is now v0.9;
- comparison Markdown heading;
- v0.3 badge text.

Existing suites guarding the touched plumbing:
- WP-011 suites: MP-002 paths/rules/correction/state-compat/db/live;
- WP-009 correction and assurance suites (Deep pause/resume tamper, cancel/fence/terminal ordering);
- observe/stream suites.

They ran in the full suite. No blanket fault matrix was repeated.

## 5. Bounded scaling (synthetic, this machine; not a month/year or performance-gate claim)

`scripts/bench_mp003.py` → [WP-012-bench-mp003.json](WP-012-bench-mp003.json).
- **Wall time, 1 → 2 synthetic days:**
  - v0.3: 0.68 → 1.26 s (ratio 1.86);
  - v0.4: 0.64 → 1.28 s (ratio 1.99).
- **Restore state:** 10.4 → 13.0 kB (ratio 1.24, both methods).
- **Direct restore:** ≤ 4.3 ms.
- **Process RSS peak:** ≈ 91 MB.

The regime-switching walk produced no anchor loss. The anchor fixture's active history is bounded at 16 entries per scenario (asserted).

Durable v0.4 anchor fixture (6,495 events):
- completed with assurance passed in 4.1 s;
- 15 transactions;
- 0 prefix events replayed after crash/reclaim (direct restore);
- pause request → parked in 0.27 s.

## 6. Interpretations for Director review (not silently decided rules)

1. **Monitoring after a loss.** An ever-armed scenario waiting in WATCH needs complete fresh 1m/15m trade evidence (MP-003 §3/§4 "required coverage/monitoring gap"); a missing minute or staleness ends it UNASSESSABLE.
2. **Late earlier-epoch evidence.** A late-admitted complete interval wholly inside an earlier anchor epoch's domain that reaches that epoch's V marks the current anchor UNASSESSABLE (LATE_CONTACT_WITH_EARLIER_ANCHOR_EPOCH_n): the newer anchor was published without that evidence. Reachable only with recorded/delayed receipts.
3. **Replacement source.** The 15m bar containing the contact minute is an eligible replacement source (its end ≥ the contact interval end, and its low is ≤ V < lost R).
4. **Tie conventions.** A tie with the lost R is not "strictly deeper". Supersession without contact keeps MP-001's inclusive tie.
5. **Live publication.** Live anchor publication is the actual dispatch tick after receipt (e.g. 04:00:01.5 for the 04:00 bar), never the bar close.
6. **Presentation-only changes:**
   - the v0.3 report heading/status text now reads "technically accepted";
   - the comparison Markdown names A baseline / B candidate for every pair (v0.2/v0.3 keep their dislocation limitation);
   - the pack method label is shown as an input-requirement label;
   - comparison defaults follow the run list (latest v0.3 vs latest v0.4) until the Owner picks a pair.

## 7. Limits

- Engineering evidence only: tests demonstrate implemented semantics on synthetic tapes, not usefulness.
- No v0.4 call is promised; the October LONG is not claimed to be recovered.
- Deep v8 shares the reducer implementation; it is not an independent method validation.
- Exact-SHA CI (full suites + compose-smoke) is Owner-operated: PENDING / NOT CHECKED by the executor.

## 8. Inactive Owner handoff (prepared, NOT activated)

After Director acceptance and exact-SHA green CI only, per MP-003 §8:
- **Sequence:** October, November, December 2025, in that order.
- **Packs:** separate single-month packs with registered warmup/tail.
- **Runs:** Historical Workbench → Adviser evaluation → **Candidate v0.4**, max pacing, same pack/profile as the baseline.
- **Baseline:** **Revised v0.3**. For October, reuse the completed run `eval-20261006T175135-9ddf6d` (pack `pack-30c0661f…`), whose pins match; a build commit difference alone is not a different input profile. For November and December, run v0.3 then v0.4 on each new pack.
- **Report:** Copy comparison for chat (A = baseline v0.3, B = candidate v0.4) and Copy report.
- **Time:** the October v0.3 run took about 2 minutes for 152,295 events. v0.4 per-event cost was within about 10 % of v0.3 on the synthetic measurement, so expect about 2–3 minutes per month on the same machine. This is an estimate, not a measured real-month claim.
- **Classes:**
  - October is redesign-exposed development;
  - November/December are development follow-up, not protected proof;
  - the old v0.3 series remains partial/suspended.
- **Not authorized:** no parameter changes, no Deep requirement, no download, no protected period.

READY FOR DIRECTOR REVIEW — WP-012 ONLY
