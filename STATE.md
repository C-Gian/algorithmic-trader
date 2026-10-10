# Project State

Updated: 2026-10-10 — RP-001 hourly directional persistence protocol approved and registered; execution INACTIVE (see the last section). 2026-10-09 — WP-015 (MP-005 v0.6) implemented and delivered: READY FOR DIRECTOR REVIEW — WP-015 ONLY (see the last section). Earlier the same day: the Owner continuous v0.5 run `eval-20261009T155751-be8b2b` was accepted descriptively and its four R→N paths were diagnosed (cb356f2, corrected at 3c6af11). WP-014 (MP-004 v0.5) and its correction remain awaiting Director engineering review.

**Current task: [task.md](task.md) — WP-015 MP-005 v0.6 implementation, delivered; awaiting Director engineering review and Owner-operated CI. No Owner run prepared.** [MP-005](delivery/MP-005-V06-INITIAL-RESPONSE-INCOMPATIBILITY.md) · [closure](delivery/MP-005-DIRECTOR-CLOSURE.md) · [authorization](delivery/WP-015-MP-005-IMPLEMENTATION-SPEC.md) · [evidence](delivery/evidence/WP-015-ENGINEERING-EVIDENCE.md). v0.5: [MP-004](delivery/MP-004-V05-RETURN-RESPONSE.md) · [closure](delivery/MP-004-DIRECTOR-CLOSURE.md) · [erratum](delivery/MP-004-ERRATUM-SECTION-6-RATIOS.md) · [evidence](delivery/evidence/WP-014-ENGINEERING-EVIDENCE.md). Sep–Dec 2025 is exposed development; Jan–Aug 2026 stays protected except the authorized tail.

Goal (Foundation v3.1): an integrated BTC adviser with persistent actionable LONG/SHORT calls, entry area, targets, stop/exit guidance and holding horizon. Capital, size, leverage and orders stay human. Historical ACCEPTED/READY/HOLD labels in older documents do not authorize work; only task.md does.

## Current method decision

Director adopts Astra CHIUDIBILE on eb091648 and closes MP-003 v0.2 design. A pre-confirmation contact invalidates the local anchor rather than automatically releasing the structural owner; replacement is prospective and finite, destination monitoring begins at first actual arm and persists after anchor loss. First confirmation freezes geometry; costs, target policy and durations remain v0.3. Design closure is not engineering/economic acceptance.

WP-012 v0.4 is implemented and technical findings are closed at e3a5afa; release acceptance is pending exact-SHA CI. v0.2/v0.3 remain the accepted baselines at 3fcbfc5. No executor implementation task remains active while waiting. Original October results and old partial/suspended v0.3 series stay unchanged. New Oct/Nov/Dec v0.3/v0.4 development plan remains INACTIVE until engineering review and exact-SHA CI; Owner launches the eventual app runs. The dossier's derived SHORT target-distance display imprecision remains acknowledged without rewriting original evidence.

## 1. Current implementation

**M3 is complete and reusable:** immutable real evidence → causal feed → observable state → durable Market replay. **WP-009 (Director-accepted at 6f95273 for the first development evaluation)** adds the integrated MP-001 v0.2 adviser: live Home cockpit and historical Adviser evaluation with a separate hypothetical evaluator (details below). No economic usefulness, frequency or profitability is established. Market replay runs stay observation-only; synthetic trader/account output is DEMO.

Implemented and in use:
- OKX BTC-USDT-SWAP public evidence (`marketdata.v1`, frozen), causal feed/observable state (`feed.v1`, provisional), public live recorder with measured local receipt times (`recorder.v1`, provisional).
- Durable observation replay (`observe.v1` revision 4, provisional) on the streaming engine: immutable receipt-pinned feed cache, one incremental causal kernel, sparse checkpoints with direct restore, fenced publication, bounded terminal reconciliation `observe.stream-reconciliation` v2 for legacy runs v3 for temporal runs and v4 for pack runs.
- Shared operational contract `algotrader.ops.v1`: status, phase, health and assurance as separate facts; durable launch; phase timing/ETA; pause/step/speed/cancel; diagnostic copy/export at every status.
- Optional Deep validation (`observe.deep-reference` v1 for legacy runs, v3 for new temporal launches, v6 for new adviser-evaluation launches; stored v2/v4/v5 results unchanged): an explicitly launched reference re-execution of a run's committed prefix over its canonical feed cache, along a separate execution path but with the shared reducer; not a wholly independent method and not an audit of the original source files.
- Historical Workbench (`#backtest`): prepare registered evaluation packs (September default, contiguous months on explicit request) or the legacy September chunk, start a *Market replay — data and engine check*, follow it and **Copy report for chat**. Adviser backtest is shown as unavailable.
- Task-first UI pass (`d8144ad`): plain run status shared by Workbench and Replay Lab, technical detail behind disclosures. It improves Workbench/Replay Lab only.
- **Causal temporal substrate (WP-008-R2 accepted at `ddc1831`):** `algotrader.temporal.v1` r1 (provisional) factual UTC 15m/1h/4h/day/Monday-week/calendar-month aggregates per trade/mark/index series, seal-no-revision late policy, explicit logical clock and dispatches (modeled complete-prefix, recorded synthetic-barrier, dispatch-tape fixture interface), deadlines, dependency readiness, bounded explicit restore state in the fenced checkpoints of new `observe.stream.v2` runs (lifecycle 4), reconciliation v3 and Deep validation v3 for new diagnostic launches on those runs, temporal inspection and copy-report section. No observations, thresholds, calls or `semantic.v2`.

- **Evaluation packs (WP-008-R3 accepted at09e23fd):** registered presets (`algotrader.corpus-presets.v1`, byte-identical packaged copy) with warmup/evaluation/tail windows; an Owner-triggered durable pack job reusing local packages, acquiring only missing slices (month/31-day split), composing one immutable receipt-pinned `algotrader.corpus-pack.v1` pack over the full requested interval; one continuous replay per pack (observe source kind `pack`, reconciliation v4, Deep v3 through the pack cache); pack-first Workbench steps with honest capability/coverage facts. No adviser, calls, outcomes or `semantic.v2`.

Historical datasets use **modeled** availability (a declared convention: a bar counts as known at its close, funding at its funding time), not measured historical publication or receipt times. Recordings use **recorded** client receipt times.

## 2. Accepted evidence

| Item | Evidence | Scope / limits |
|---|---|---|
| WP-001 – WP-007 (M1–M3) | Accepted commits and CI listed in [history](delivery/DELIVERY-HISTORY.md) | Infrastructure and observation only |
| WP-008 Workbench + corpus bootstrap | `a14f58b`, CI `36773558450` | Observation-only evaluation; adviser metrics UNAVAILABLE |
| WP-008-R1A observable lifecycle | `0919001`, [review](delivery/WP-008-R1A-DIRECTOR-REVIEW.md) | Operational slice, not a speedup |
| WP-008-R1B streaming replay | `9d814ec`, [review](delivery/WP-008-R1B-DIRECTOR-REVIEW.md) | Structural slice |
| WP-008-R1C assurance + gates | `99e0ca5`, CI `37111371473`, [review](delivery/WP-008-R1C-DIRECTOR-REVIEW.md), [gate inventory](delivery/evidence/WP-008-R1C-benchmark-gates-v2.md) | Month-only release; synthetic structural benchmark |
| **Owner September Market replay check — CLOSED** | Evaluation `eval-20261003T091928-a7eb00`, replay `obs-20261003T091928-363a3d` | See below |
| WP-008-R2 causal temporal substrate | `ddc1831`, CI `37138450907`, [review](delivery/WP-008-R2-DIRECTOR-REVIEW.md) | Factual temporal slice; Deep terminal correction accepted; no adviser |
| Owner September pack preparation — CLOSED | `pack-427d5f5d0e26d595ff0c131c70a9435b26692dbe`, [evidence](delivery/evidence/WP-008-R3-OWNER-SEPTEMBER-PREPARATION.md) | Owner copied report; complete price windows, funding/metadata/calendar limited; no replay or trading result |
| WP-008-R3 context packs | `09e23fd`, CI37152698917, [review](delivery/WP-008-R3-DIRECTOR-REVIEW.md) | Preparation/continuous observation infrastructure; real boundaries unmeasured; no adviser |
| MP-001 integrated method design | v0.2, [disposition](delivery/MP-001-DIRECTOR-DISPOSITION.md) | Design only; no profitability, frequency or product implementation accepted |
| UX pass | `d8144ad`, CI `37116003888` (checks incl. E2E, compose-smoke) | Workbench/Replay Lab only |

**September closure (Director decision, 2026-10-03).** COMPLETED; coverage COMPLETE 129600/129600; runtime assurance PASSED; `observe.stream-reconciliation` v2 PASS 9/9; trusted receipt/cache/run pin matched; entire feed consumed; elapsed 60.4 s; 27 committed transactions; zero delivery rows; zero recoveries. The original replay performance incident is closed. Evidence is the Owner's copied terminal report reviewed by the Director, not an independently rerun benchmark. No Deep validation of this run was performed. No adviser or trading performance was evaluated.

## 3. Open limits

These remain open after the September closure; they are not contradicted by it:
- **Annual application performance gates: NOT_MEASURED / PENDING.** Annual component timings are comparisons, not gates. Pack preparations may select contiguous months explicitly; the legacy chunk workflow still only prepares September. No annual release claim or year run handoff.
- Recording-volume evidence is limited.
- Windows directory fsync (power-loss durability of publication) remains unproven.
- Data, Recorder and mobile UX are not closed by the UX pass.
- The old CI Copy-feedback failure (job `111166819975`) has a plausible, not proven, cause; downloading the Markdown report is the fallback.
- WP-009 executor delivery covers the live cockpit, persistent calls/entry validity, in-app alerts, startup catch-up, advisory report sections and `semantic.v2`; it is **not accepted; correction required** under the [Director review](delivery/WP-009-DIRECTOR-REVIEW.md). Still not built: historical calendar/news tape (calendar UNKNOWN), predictive cycle methodology, OI/liquidations/depth, DST-aware schedule ingestion, incident tape, optional exit-delay sensitivity export, OS/mobile notifications; fixed reusable pack storage beyond September undecided.
- Always-NO_TRADE is not product success: integrated evaluations must report coverage, frequency, entry windows and the candidate/rejection funnel.

## 4. Next step

1. **Now:** MP-001 v0.2 is closed as method design after the [Astra review](delivery/MP-001-ASTRA-REVIEW.md) and [Director disposition](delivery/MP-001-DIRECTOR-DISPOSITION.md). The [rules](delivery/MP-001-INTEGRATED-METHOD-PROPOSAL.md) and [parameter register](delivery/MP-001-PARAMETERS.json) are current; this is not economic validation or implemented adviser capability.
2. **Now:** Owner September pack preparation is [CLOSED](delivery/evidence/WP-008-R3-OWNER-SEPTEMBER-PREPARATION.md): COMPLETED/READY,147975 events, complete trade/mark/index warmup/evaluation/tail, no gaps. No replay/economic result. WP-009 delivered at5d1f2e1, but [review](delivery/WP-009-DIRECTOR-REVIEW.md) requires corrections1–9 under task.md. The adviser is exposed in code but not released for Owner evaluation/live reliance. The prepared pack remains reusable.
3. Remaining sequence: WP-009 implementation/review → Owner Backtest A → diagnosed bounded improvement/protected/prospective checks under separate tasks. No new general infrastructure pass or isolated signal prototype. [Delivery plan](delivery/FOUNDATION-V3-INTEGRATED-PLAN.md) §9–10.

### WP-009 correction follow-up executor evidence (base `9dbb19c`, reviewed source `d16c925`; READY FOR DIRECTOR REVIEW — WP-009 CORRECTION FOLLOW-UP ONLY; not accepted)

- **Scope**: the remaining original-finding-7 case only ([review](delivery/WP-009-CORRECTION-DIRECTOR-REVIEW.md)). MP-001 v0.2, implementation/evaluator/state/runtime identities, report `adviser.report.v2`, frozen and provisional schema baselines, Owner data and saved outputs unchanged.
- **Fix** (`observe/deep.py`): the stored professional record bytes were already re-hashed on every launch, but problems were added to the comparisons only when `start == 0`. New `_adv_merge_stored` merges them on every launch: a fresh launch behaves exactly as before; a resume records (and counts in `compared`) only problems not already in the saved mismatch list, so storage altered while paused is never dropped and repeated resumes never duplicate a diagnostic. If the bounded 20-entry list is already full the outcome is already MISMATCH; the extra count is disclosed. Each resume writes a `deep_resume_stored_recheck` diagnostic-log note (detected / newly recorded / unrecorded-list-full) and counters.
- **Version decision**: new adviser Deep launches are `observe.deep-reference` **v6** (scope sentence states the every-launch/resume re-hash). Saved v5 results keep their recorded version/scope untouched (a v5 result reached through a resume after storage changed while paused could have been a false MATCH; v6 distinguishes new results). An unfinished v5 validation resumed by this code gets the same merge (it can only add mismatches) and keeps its pinned v5 label. Legacy v1/v3 and the reconciliation validator are unchanged.
- **Fail-before / fixed-after** (DB, disposable PostgreSQL 18.6 port 55439; `src/` at `9dbb19c` is byte-identical to reviewed `d16c925`): new regressions starting from a CLEAN pause at a nonzero cursor — digest-only alteration in `adviser_journal` and in `adviser_evaluation_records`, last-row chain-only alteration in both tables, three repeated pause/resume cycles over altered storage (exactly one diagnostic) — **4 of 4 failing tests fail before** (resumed outcome `match`; the repeated test sees an empty saved list) and pass after; the clean pause/resume vs uninterrupted report-equality guard passes before and after. Focused fixed-after run (correction DB, adviser integration, assurance incl. byte tampering/cancel in every phase/terminal-lock ordering/stale-generation fencing/report, temporal Deep, wording, versions): **56 passed**. Details: [evidence](delivery/evidence/WP-009-CORRECTION-FOLLOWUP-EVIDENCE.json).
- **Checks**: disposable PostgreSQL 18.6 (Owner stack untouched): exact final full non-E2E suite with `ALGOTRADER_REQUIRE_DB=1` **599 passed, 0 failed** (30 min; 594 + 5 new); full E2E (Playwright) **18 passed**; web typecheck + build pass; `algotrader schema` matches (no contract change). Compose smoke: isolated CI on the exact final SHA (see executor report). No economic or long run.
- **Limits**: Deep stays optional, shares the method/reducer code and the canonical cache (not an independent method/economic/source check); it detects storage altered before or during the validation up to its last resume, not alterations made after completion; the `compared` counter still re-counts prefix record comparisons during the temporal re-fold on resume and a record-level mismatch in the re-folded prefix can be listed again after a resume (both pre-existing, unchanged and bounded by the 20-entry list; the outcome is unaffected).

### WP-009 correction executor evidence (base `03f2dda`; READY FOR DIRECTOR REVIEW — WP-009 CORRECTION ONLY; not accepted)

- **Scope**: Director findings 1–9 only; MP-001 v0.2 rules/register, thresholds, development/protected split, Owner pack/data unchanged. Identities versioned: implementation `adviser.core.v2`, evaluator `adviser.evaluator.v2`, core state `algotrader.adviser-state.v2`, runtime `algotrader.adviser-runtime.v2`, Deep `observe.deep-reference` v5 for adviser runs, report `adviser.report.v2`, `algotrader.adviser-evaluation.v1` r2 (additive optional `HypotheticalPath.resolved_at`, changelog). An unfinished run pinned to `adviser.core.v1` fails explicitly on resume (`INCOMPATIBLE_ADVISER_IDENTITY`, committed outputs preserved); Deep on such a run fails explicitly. Frozen baselines and observe r5 unchanged.
- **Fixes**: (1) ordinary protected-minute stop gaps fill at the adverse open (boundary time, funding at the boundary), LONG/SHORT/all guidance variants; both-level inside-open minutes stay AMBIGUOUS; HORIZON_ONLY unchanged. (2) first failing freshness instant = min(end, known_at)+allowance+1 µs; residual timer at hard−minimum+1 µs (equalities preserved). (3) C far-edge withdrawal on every newly admitted 15m close (no dispatch-time equality). (4) taped `connection` capability (CONNECTED→AWAITING_FRESH_BAR until a fresh bar, DISCONNECTED, STOPPED) → UNVERIFIED entry and no new call; usable-entry withdrawal/reopen alert once (Stop not alerted); API/UI/Copy presentation boundary for non-current sessions without rewriting history. (5) one owned startup (metadata + catch-up) with cancellation per history page and replayed minute, Stop read before each live batch, startup thread joined and owned loops closed on every exit. (6) window clamped to the committed checkpoint cursor with validation; `cutoff` on calls/call detail/journal; hypothetical paths filtered by `resolved_at`. (7) Deep v5 re-hashes stored record bytes (digest, sequence, link-by-link chain), compares regenerated digest+chain, missing/extra rows. (8) per-operation copy state (latest operation only writes/confirms; "Copying…"), cockpit copy uses the same hook. (9) durable condition-duration accumulator + staged room erosion in JSON/Markdown/Workbench.
- **Fail-before / fixed-after**: the 50 new correction regressions run against the reviewed commit `5d1f2e1` (worktree, UI rebuilt there): 46 of 55 fail (the 9 passing are deliberate preservation guards); on the final code 55/55 pass. The CI37275582552 repeated-copy race reproduces on the reviewed UI (stale "Copied" while the second copy is pending) and is fixed. Details and Director probe re-runs: [evidence](delivery/evidence/WP-009-CORRECTION-EVIDENCE.json).
- **Checks** (disposable PostgreSQL 18.6 on port 55439; Owner stack untouched): exact final full non-E2E suite with `ALGOTRADER_REQUIRE_DB=1` **594 passed, 0 failed** (29 min); exact final full E2E (Playwright) **18 passed** (incl. the CI-failing Workbench journey, new copy-race and non-current presentation journeys); web typecheck + build pass; `algotrader schema` matches (only `adviser-evaluation.v1` rewritten for r2; frozen and observe r5 unchanged). Director probes re-run on the final code give the expected values (see evidence). Partial reruns during development are not counted. CI on the exact final SHA: see the executor report.
- **Interpretations for review**: target open-gaps on ordinary minutes keep the conservative intrabar T/ambiguity rule (only the explicitly required protective stop gap was changed); a (re)connection counts as adequate only after a complete trade bar whose availability is at/after the reconnection; a further change between two unusable entry states (CLOSED↔UNVERIFIED) is journaled but not re-alerted; the API's current-session test is LIVE state + live lease + heartbeat ≤ 10 s + connected view; staged room derives T from the trigger side price and G (tick-rounded) instead of adding a semantic field; the copy-race E2E uses the shared hook through the Market cockpit (the Workbench report uses the same hook and its journey asserts the actual clipboard bytes).

### WP-009 Director review — changes required (2026-10-05)

Reviewed `5d1f2e1`; [review and interpretation disposition](delivery/WP-009-DIRECTOR-REVIEW.md), [independent probes](delivery/evidence/WP-009-DIRECTOR-PROBES.json). Nine findings: ordinary protective gap pricing; both-age/residual timer scheduling; delayed-receipt C withdrawal; live connection/session readiness and material entry alerts; startup Stop/fence/task cleanup; committed/cutoff-safe inspection; Deep actual stored-byte verification; repeated-copy acknowledgement race; required blocker-duration/staged-room diagnostics. Preserve architecture and unchanged MP-001; correction only active.

Director pure/offline suites:69 passed in37.24s (Python3.12.14, not a full project-runtime/DB/browser rerun). Exact-SHA CI37275582552 **failed**:544 non-E2E passed,12 E2E passed/1 failed (Copy MD still previous in-progress clipboard snapshot); web checks and Compose smoke passed. The executor's “all checks pass” is local reported evidence, not CI success. Owner Backtest A remains **inactive**; no economic run or new acquisition requested.

### WP-009 executor evidence (base `a840131`; READY FOR DIRECTOR REVIEW — WP-009 ONLY; not accepted)

- **Method release**: `src/algotrader/adviser/method/` byte-identical MP-001 rules + register (tests vs `delivery/`); identity = rules version + LF-normalized rules SHA-256 + register canonical SHA-256 (equals the R3 presets pin) + capability-profile SHA-256 + pins + implementation `adviser.core.v1` + build. Prose change ⇒ new identity (tested).
- **Contracts/formats**: new PROVISIONAL `algotrader.semantic.v2` r1 and `algotrader.adviser-evaluation.v1` r1 baselines (`schemas/`); `algotrader.observe.v1` r5 (additive optional `ObservationLaunch.run_type`, manifest `adviser` reference; changelog); internal `algotrader.adviser-state.v1`, `algotrader.adviser-runtime.v1`, `algotrader.adviser-evaluation-state.v1`, `algotrader.adviser-input-tape.v1`; engine `observe.stream.v3` for new adviser evaluations only; validator `observe.stream-reconciliation` v5 and Deep `observe.deep-reference` v4 for those runs only; additive migration 12. Frozen `semantic.v1`/`marketdata.v1` and `feed.v1`/`recorder.v1`/`temporal.v1`/`corpus-pack.v1` baselines byte-identical; existing observation reports byte-stable (adviser keys only appear for adviser runs).
- **Implemented**: professional fold (MP-001 §§3–9, A/B/C + exact SHORT reflection, landmarks with frozen zones/BROKEN, renewal latches/box tokens, atomic B cancellation/retirement, context withdrawal before coincident trigger, strict post-arm trigger minutes, target frozen at trigger, structural area vs admissible prices, slot/conflict/priority, entry/thesis lifecycles, certified contacts/straddling ambiguity, premise/STALLED/residual time, total MarketView table, typed calendar restriction/observed response/vintage policy, dislocation, live quotes); separate evaluator (§11); durable integration (same fenced checkpoint, sparse journal, professional finish, fallback-suffix journal verification without duplicates); live adviser worker (lease/fencing, first-completion WS candles, narrow ticker client, input tape, ≤96 h reconstruction, metadata/downtime resets, LIVE activation, alert dedup); API; Home cockpit; Workbench Adviser evaluation run type + result/call detail.
- **Decisions for Director review** (no rule invented beyond these readings): (1) B/C trigger minute with close ≥ K+tick but low ≤ V is *not a trigger* (attempt continues; A rejects as TRIGGER_CONTACT_AMBIGUOUS per its explicit text); (2) structural-area S15 = latest S15 at the trigger dispatch; (3) pivots/period landmarks unavailable for lack of S15 are created at the first usable S15 with known_at = creation; (4) phase evaluates EXPANSION/COMPRESSION before needing 1h context, else UNAVAILABLE; (5) a 15m INCOMPLETE/discontinuity resets windows, expires attempts/box, resets latches/tokens and makes an issued thesis UNASSESSABLE; (6) entry status: price reasons → CLOSED, quote-only reasons → UNVERIFIED; evaluator uses `entry_conditions_enabled` (non-price conditions) + its own open-price predicate; (7) freshness holds while age ≤ allowance; timers fire 1 µs after; (8) live: reconstructed spans issue no call, armed-before-activation attempts cannot issue live calls, a restart gap makes an ongoing thesis UNASSESSABLE (no alert); alerts for NEW_CALL/ENTRY_WITHDRAWN/ENTRY_REOPENED/TERMINAL only (UNVERIFIED displayed, not alerted; flapping in/out of the area alerts once per transition); (9) live availability = max(local receipt, processed clock), receipt kept in provenance; (10) warmup calls are cleared at evaluation start and never scored.
- **Checks** (disposable PostgreSQL 18.6 container on port 55439; Owner stack untouched): full non-E2E suite 538 passed + 1 failed (an old observe revision pin; updated to r5, `tests/test_observe.py` re-run 21 passed) — 539 non-E2E tests pass vs 469 at base, `ALGOTRADER_REQUIRE_DB=1`, DB suites ran; E2E (Playwright) 13 passed; isolated Compose smoke (project `wp009smoke`, separate image tag, port 18090, adviser worker healthy, `scripts/stack_smoke.py` OK; isolated project/volumes/image removed afterwards). Web typecheck/build pass. `algotrader schema` matches (observe r5 + two new baselines; frozen unchanged).
- **New tests**: `test_adviser_method.py` (identity/byte pins, exact measures, B4 geometry examples, B7 accounting/funding boundaries), `test_adviser_paths.py` (hand-expected A/B/C LONG + exact SHORT reflections; stop/stall/wick/progress/no-trigger/no-room/no-entry; B1 box ownership; view table; evaluator-disabled byte identity; direct restore at cursors 1/7/13/501/5000), `test_adviser_rules.py` (B2/B3/B5/B6, latches, tokens), `test_adviser_evaluator.py` (pre-open frontier, opening-price geometry, collision table, censoring, tail, windows), `test_adviser_causality.py` (future perturbation, windows, calendar vintage/restriction/response), `test_adviser_live.py` (ticker shape/invalid/stale/crossed/future/older/duplicate, pacing, activation, ask-priced call, 5 s expiry without input, restart gap, >96 h, metadata reset, tape reproduction), `test_adviser_integration.py` (DB: pure≡durable parity, cadence 7/5000 + STEP cadence-1 prefix + paced, crash/reclaim, corrupted-restore fallback, cancel, Deep v4 match + tamper), `test_adviser_live_db.py` (worker with mocked WS/REST/ticker: call, single alert set, stop, restart without repeated alerts), `tests/e2e/test_adviser_e2e.py` (Workbench and live journeys at 1440/1024/390 px). Existing E2E tests updated only for the deliberate UI wording/run-type changes; two observe tests updated for revision 5.
- **Bounded measurement** (`scripts/bench_adviser.py` → [evidence](delivery/evidence/WP-009-bench-adviser.json); synthetic, executor machine): 1 vs 2 synthetic days: 4,320 vs 8,640 events, 2.03 s vs 4.04 s (~2,100 events/s incl. temporal), restore state 9.8 vs 12.4 KB compressed, encode+decode ≈ 3 ms, peak RSS 81 vs 111 MB (harness keeps fixtures in memory). Not a month/year or economic measurement; no annual gate claimed.
- **Prepared Owner handoff (inactive until Director acceptance)**: see the executor report; it becomes READY FOR OWNER BACKTEST A only after acceptance.

### WP-008-R3 correction executor evidence (base `6aa982e`; Director review pending)

- **Finding 1 — contributor facts:** `pack.verified_manifest` parses request bounds, instrument snapshot and file sizes only from manifest bytes whose SHA-256 equals the manifest the accepted boundary verified (cold: private snapshot; warm: the manifest pinned by the cache receipt, cross-checked with the receipt). A manifest changed after verification fails the job (`…changed after verification…`), in cold, warm and pinned-rebuild paths; new facts are never combined with the old identity.
- **Finding 2 — artifact bytes and durability:** each attempt stages in `packs/.staging/<job_id>/g<generation>/`; files are fsynced, then the staging directory; actual bytes are re-hashed against their pins (manifest render hash, provenance pin, no unexpected entries) at staging, again under the publication row lock, and after the rename plus fsync of the published directory and of `packs/` — all before the receipt INSERT. A mismatch before the rename fails with nothing published; a mismatch after it moves the directory aside to `.invalid-*`, no receipt, no COMPLETED. Convergence also re-verifies existing bytes; a same-id directory with other bytes is quarantined, never overwritten.
- **Finding 3 — staging ownership:** the global `.tmp-*` sweep is removed. Cleanup (`pack.cleanup_abandoned_staging`) removes only this job's older, fenced-out generations and the staging of jobs whose row is terminal; another live job's staging and the current generation are never touched; no age sweep. Removals are recorded in the job's diagnostic log. A failed publication removes only the attempt's own staging.
- **Regressions** (`tests/test_pack_correction.py`, 11 tests): real cold mutation of tick/request/files after verification (3) through the real job/worker with a wrapper around the accepted source boundary; warm reuse mutation on a forced recomposition (warm path asserted), then unchanged sources reproduce the same pack id and original tick size; pinned rebuild rejects a mutated source; altered staged manifest before the lock and altered published manifest between rename and re-hash (2) → FAILED, no receipt, no published directory, no staging left, `.invalid-*` kept, later Prepare succeeds; provenance bytes checked at staging, publication and convergence, quarantine path; fsync order spy (staged files < staging dir < final dir < `packs/` < receipt); two concurrent jobs on two workers publishing while the other's staging is live, cancellation of one job while another's staging is live; reclaim removing only its own fenced-out `g1` and terminal leftovers. Falsification (scratch, not committed): with the old unverified manifest read restored, the request and file mutations completed and published a pack; the tick mutation failed only incidentally on a sibling instrument mismatch, not on verification.
- **Checks:** disposable PostgreSQL container (Owner stack untouched): 469 non-E2E passed (458 earlier + 11 new), 0 skipped; E2E 11/11; web typecheck/build; `algotrader schema` (seven baselines match; no contract change). Earlier composition/continuity/reuse/Deep/browser tests unchanged and passing. No local Compose smoke for this correction (CI compose-smoke covers it; result in the executor report).
- **Open limits:** Windows directory fsync is unavailable (no-op, power-loss durability unproven; POSIX path exercised in CI only); the R1B feed-cache age-based stale cleanup is unchanged and outside this correction; a crash between the rename and the receipt leaves a verified directory that the next Prepare converges on; real September preparation remains an Owner app action after acceptance (not requested here).

### WP-008-R3 executor evidence (base `1dac5ba`; Director review pending)

- **Implemented:** presets module (`src/algotrader/corpus/presets.py`, packaged `presets.json` byte-identical to the registered file; exact 96 h / 365 min windows; contiguous calendar-month builder; development/protected classification, contamination UNKNOWN, never certified); pack contracts/composition/publication (`corpus/pack_contracts.py`, `corpus/pack.py`); durable pack job in the corpus worker (`corpus/pack_job.py`; reuse → plan → sequential children → per-source caches → compose → fenced publish); pack API (`/api/corpus/presets`, `/selection`, `/pack-jobs`, `/packs`; no network on read) and diagnostic MD/JSON reports at every status; pack evaluations (`/api/evaluations` with `pack_id`, explicit acknowledgement for READY_WITH_LIMITATIONS) and an *Evaluation pack* report section separating feed consumption from source coverage; observe source kind `pack` with receipt-checked open, cache quarantine/rebuild from pinned sources, reconciliation v4 (`pack_receipt_and_pins`, `pack_coverage_reported`); Workbench step 1 *Prepare data* (default preset, local vs needed, estimate with basis, one Prepare, job progress/copy report, sources/coverage/capabilities disclosure, other presets and contiguous months), step 2 pack selection with acknowledgement, result fact *Data coverage*; earlier single-month workflow kept behind a disclosure.
- **Contract/format changes:** new `algotrader.corpus-pack.v1` r1 baseline (`schemas/algotrader.corpus-pack.v1.json`, includes presets models); `algotrader.observe.v1` r4 (additive `pack` source kind; changelog); reconciliation `observe.stream-reconciliation` v4 for pack runs only; additive migration 11. Frozen `semantic.v1`/`marketdata.v1` and `feed.v1`/`recorder.v1`/`temporal.v1` baselines unchanged. No `semantic.v2`.
- **Decisions to review:** the manifest identity excludes whether a slice was downloaded by this or an earlier preparation (operational history stays in job children) so identical inputs reproduce the same pack id across attempts; READY_WITH_LIMITATIONS is set by any missing/rejected bar minute of any of trade/mark/index (optional reference gaps are labelled optional and never veto the trade core); a same-id pack directory with other bytes is quarantined to `.invalid-*` and the verified staging published; capability probes were not executed (NOT_PROBED recorded).
- **Evidence:** `tests/test_pack.py` (19 tests: A registered windows/register hash/builder/leap/protected split/rejections/month+31-day split; B local month + boundary slices with a request spy proving no duplicate download, warm reuse with zero requests, larger package sliced offline, completed children kept after cancellation and reused after a crash/reclaim, API error → failed child with no package; C crash before lock/after rename/before commit converging to one trusted pack, cancel and stale generation at the publication boundary, replaced manifest/missing receipt refused then recovered by Prepare with quarantine, pack-cache manifest/partition tamper rebuilt from pinned sources, changed pinned source fails visibly; D equal content identity/event count/coverage/temporal chain for single, split and overlapping packagings with differing provenance-sensitive hashes, deterministic primary SourceRef, value conflict and rejected-vs-valid conflict fail, MISSING superseded by valid evidence, sparse funding, exact INVALID_ROW accounting, cross-source cutoff perturbation; E pack replay across source/month boundaries equals the single-source temporal records, STEP/pause/resume, corrupted temporal restore fallback, crash after commit, paced = max outputs, Deep v3 MATCH with terminal finish; F capability scope incl. EMPTY_UNKNOWN funding, metadata approximation, NONE_UNKNOWN calendar, optional reference gaps not a core veto, gap acknowledgement required, no adviser metric); `tests/e2e/test_pack_workbench.py` (prepare with no network on page open, ready with limitations, details, copy preparation report, reuse with zero requests, acknowledgement, pause/resume, completion, data-coverage fact, copy report, 390 px overflow); legacy single-month E2E updated for the disclosure.
- **Bounded engineering measurement** ([evidence](delivery/evidence/WP-008-R3-bench-pack/bench_pack.json), `scripts/bench_pack.py`, tiny synthetic fixtures, executor machine): 510 vs 1,590 requested minutes → 1,531 vs 4,773 events, pack cache added 98 KB vs 305 KB, 13 OKX requests each (two boundary children), preparation 1.3 s vs 2.4 s; paced replay transactions 10 vs 26 (checkpoints + 1 per generation), 0 delivery rows, 0 prefix-restore events, pause applied in 0.064 s / 0.079 s, compute RSS ≤ 94 MB, temporal checkpoint state 19 KB vs 44 KB (grows until sealed-record retention saturates). Not a historical month/year measurement or annual claim.
- **Checks:** disposable PostgreSQL 18.6 container (Owner stack untouched): 458 non-E2E passed, 0 skipped; E2E 11/11 (new pack flow + updated single-month flow); web typecheck/build; `algotrader schema` (seven baselines match; frozen ones unchanged); isolated Compose smoke (separate project, image tag, port and volumes; migration 11 applied; registered presets served from the packaged image; `stack_smoke.py` OK; isolated resources removed). Existing tests changed only for deliberate versions (observe r4) and the legacy month flow now behind a disclosure. CI result: see the executor report.
- **Open limits:** real September pack preparation, real boundary-slice availability and actual stored bytes are unmeasured (Owner app action after acceptance); capability probes NOT_PROBED; funding completeness, historical metadata effective dates, event calendar, incidents and quotes remain not covered; per-child restart from scratch (no byte resume); the Data page does not yet list packs (Workbench only); annual gates and Windows directory fsync unchanged.

### WP-008-R2 executor evidence (base `9169096`; accepted after correction `ddc1831`)

Implemented against [the temporal specification](delivery/WP-008-R2-CAUSAL-TEMPORAL-SPEC.md); original executor evidence below is retained. Current acceptance and corrected Deep version: [Director review](delivery/WP-008-R2-DIRECTOR-REVIEW.md).
- **New/changed formats:** contract `algotrader.temporal.v1` r1 (new baseline `schemas/algotrader.temporal.v1.json`); `algotrader.observe.v1` r3 (optional manifest `temporal`; changelog entry; r1/r2 readable); engine `observe.stream.v2` (v1 kept for existing runs; factual compatibility fingerprint now includes the engine format); temporal engine `temporal.engine.v1`, state `algotrader.temporal-state.v1`; validators `observe.stream-reconciliation` v3 and `observe.deep-reference` v2 (temporal runs only; v2/v1 and their claims unchanged for R1B/R1C runs); additive migration 10 (temporal columns; suspends pre-R2 unfinished lifecycle-3 runs read-only); lifecycle 4. `feed.v1`, `marketdata.v1`, `semantic.v1`, `recorder.v1` baselines byte-identical.
- **Clock/seal policies:** `temporal.clock.modeled-complete-prefix.v1`, `temporal.clock.recorded-replay-synthetic-barrier.v1` (named convention, not a live-decision reproduction), `temporal.clock.recorded-dispatch-tape.v1` (fixture/tape interface); `temporal.seal-no-revision.v1`; profile `temporal.utc-horizons.v1` with engineering demonstration dependencies only.
- **Evidence:** `tests/test_temporal.py` (21 pure: UTC anchors incl. leap/non-leap February and DST days, partial coverage, exact OHLC/Decimal volumes per family, slot-order independence, missing/rejected, late before/after seal, cutoff perturbation, modeled tie groups and pending-boundary restore, per-event restore equality, recorded equal-time receipts, tape replay = live-style, deadline ordering and no-event timers, finite clock end, monotonicity, differential vs the separate reference aggregator for both streamed policies, readiness/staleness/unavailable/capacity rejection, bounded state, contiguous continuation and discontinuity reset); `tests/test_temporal_integration.py` (12 DB: cadence 7/333/5000 range-by-range equality with the pure fold, STEP/pause/paced, crash after commit at 1/15/42 without duplicate dispatch, corrupt temporal restore fallback, reconciliation v3 tamper/scope, Deep v2 match + tamper detection + pause/resume re-fold, legacy `observe.stream.v1` run with validator v2 / Deep v1, migration-10 suspension, inspection view and copy report); Workbench E2E asserts the temporal disclosure.
- **Bounded synthetic month benchmark** (executor machine; [evidence](delivery/evidence/WP-008-R2-month-benchmark.md)): month application gates PASS — cached observation 43.8 s (R1C without temporal: 31.4 s), terminal 0.87 s, cold preparation 36.1 s; temporal restore state ~75 KB compressed per checkpoint; Deep v2 MATCH in 54.9 s, peak RSS 236 MB. Annual gates remain NOT_MEASURED/PENDING.
- **Checks:** final clean run on a disposable PostgreSQL 18.6 container (Owner stack untouched): 431 non-E2E passed, 0 skipped; E2E 10/10; web typecheck/build; `algotrader schema` (all six baselines match; frozen baselines unchanged); isolated Compose smoke (separate project, image tag, port 18080 and volumes; migration 10 applied; `stack_smoke.py` OK; isolated resources removed afterwards); documentation link check. Two existing tests were updated only for the deliberate version changes (observe r3, engine v2, reconciliation v3, `temporal.json`). The benchmark harness received one race fix (None progress). CI result to be read from the pushed commit.
- **Open limits:** live input ownership, wall-clock catch-up and real dispatch tapes are WP-009 dependencies (tape interface is fixture-only); multi-chunk runs do not exist in the app yet, so source continuation is implemented and tested at engine level only; dispatches are persisted as sequence + commitments + a bounded recent log (barriers are reproducible from input + pinned configuration), not as a per-dispatch table; Deep v2 compared only at committed boundaries (corrected by v3 below for completed runs) and re-folds the temporal prefix on resume; recorded closure allowance 120 s is an engineering default; production lookbacks/authority remain MP-001 decisions.

### WP-008-R2 correction executor evidence (base `35d73fc`; accepted at `ddc1831`)

- **Finding 1 corrected:** Deep validation for temporal runs is now `observe.deep-reference` **v3** (new launches; stored v2 results keep their recorded boundary-only claim; v1 for `observe.stream.v1` runs unchanged). At launch a completed run's published clock-end evidence is pinned (artifact generation, `temporal.json` SHA-256/size from the manifest, manifest `temporal` reference, `clock_end`). After the full committed prefix both the shadow temporal fold and the separate reference aggregator consume the pinned terminal clock command and 11 terminal comparisons run: published file vs manifest reference (aggregate chain, sealed/dispatch commitments, dispatch sequence, clock time), published aggregate chain vs reference and vs shadow, published sealed/dispatch commitments, dispatch sequence and clock time vs shadow / `clock_end`. Missing, unlisted or corrupt evidence ends FAILED with outcome `error` (never MATCH); inconsistent values are mismatches. Paused, cancelled, failed or partial targets keep exact committed-prefix scope (`terminal.compared = false`, no finish applied). The original run, its artifacts and saved diagnostic results are never modified; cancel/terminal serialization and progress hooks are unchanged.
- **Regressions:** pure — the exact 15-minute pending-final-tie case (0 sealed before finish, chains equal; engine finish seals 6 records; equal again only after the reference's finish) and a Monday-to-month-end fixture where the final 15m/1h/4h/day closures and the cut week/month exist only after the terminal command; DB — completed fixture run whose published chain differs from its last range yet Deep v3 MATCHes with 11 terminal comparisons, finished-output-only tamper (file and manifest made consistent, pre-finish records untouched) gives terminal mismatches, absent/corrupt/unlisted evidence never matches, paused and cancelled targets keep prefix-only scope; existing Deep tests updated to v3.
- **Checks:** disposable PostgreSQL 18.6 container (Owner stack untouched): 439 non-E2E passed, 0 skipped; E2E 10/10; web typecheck/build; `algotrader schema` (no contract change in this correction). A first full run failed 3 existing cancelled-Deep report tests because the new scope sentence contained the token MATCH; the scope was reworded and the full suites rerun green. Compose smoke is left to isolated CI (no Docker/packaging change); CI result in the executor report.

### WP-010 accepted evidence (base `e9c01b9`; implementation `f7ad4bc`)

- Chronology moved verbatim (heading levels only) from STATE.md and README.md to [delivery/DELIVERY-HISTORY.md](delivery/DELIVERY-HISTORY.md); STATE is reorganized as implementation / evidence / limits / next step; README is an operation guide (start, upgrade, data and report locations, normal Workbench path, limits); plan §9–10 and the SR-003 current pointer updated.
- UX/report wording: pause shows *Pause requested* until the worker parks the run (no "nothing is processed" promise before `paused`); replay status no longer claims knowledge "exactly as it would have been known" and states the modeled availability convention vs recorded receipt times; Deep validation is described as a reference re-execution with the shared reducer and canonical-cache scope, not a wholly independent method or source audit (UI, Workbench report text, Deep scope string for new validations, mismatch warning). Stored reports, validator ids/versions and the reconciliation scope string are unchanged.
- Checks: `tests/test_ux_wording.py` (3 tests; pause/availability assertions fail on the previous `runStory.ts`); 398 non-E2E passed and 10/10 E2E on a disposable PostgreSQL 18.6 container (Owner stack untouched); web typecheck/build; markdown link check of the changed documents (34 links, 0 problems). Compose smoke left to CI.

The next product objective is the first complete adviser path, not an isolated rule. Timing/cycle, news/event and derivatives roles need explicit bounded dispositions; missing optional context cannot become endless infrastructure work or silent neutral confirmation.

## Stable reference

**Product path:** available evidence → causal observable state → derived professional observations → integrated MarketView → scenarios → candidate plan → actionability → persistent call / NO_TRADE → reassessment.

**Architecture (SR-001, M3):** market evidence → causal availability feed → centrally owned observable market state → professional reasoning → MarketView / prediction / trade recommendation. The professional layer consumes causal observable state, not raw datasets. Mandatory distinctions: event vs availability vs retrieval time; deterministic processing order; traded/mark/index/funding roles; missing vs invalid vs stale vs unknown; market view vs trade decision; directional expectation vs actionability; NO_TRADE as a legitimate decision.

**Professional coverage decisions** (plan §3): structure/trend/location and movement/momentum are required core; participation/volume is included with limited non-voting authority; volatility is required context/scale; timing/cycles and news/events require explicit closure, not silent omission; derivatives/liquidity are factual context with limited interpretation.

**Contracts.** Frozen: `algotrader.semantic.v1` (synthetic DEMO shell), `algotrader.marketdata.v1`. Provisional: `algotrader.feed.v1`, `algotrader.recorder.v1`, `algotrader.observe.v1` (revision 4 since R3: source kind `pack`; revision 3 added the optional manifest `temporal` reference), `algotrader.temporal.v1` (revision 1, R2), `algotrader.corpus-pack.v1` (revision 1, R3; baseline also covers the presets file format). Operational: `algotrader.ops.v1`. Advisory `semantic.v2` is introduced only with an activated integrated specification (no `semantic.v2` during R1–R3).

**Market-data source:** public/read-only OKX `BTC-USDT-SWAP` as reference evidence, not an execution decision.

**Research retained, not governing:** RP-001 is closed as development evidence, not a production method ([review](research/first_trader/RP-001-DIRECTOR-REVIEW.md)). Its six real cutoffs cannot estimate frequency or profitability; frozen cases and labels stay byte-identical. Details are in the [history](delivery/DELIVERY-HISTORY.md).

**Knowledge baseline:** `source_notes/` and `knowledge/registry.yaml` (initial snapshot `3bf9de0d88fd97360bff7a6517bbb61544f5db68`) are provenance, not workflow instructions; preserve them unchanged.

**Repository:** force pushes are prohibited; executors do not pull (AGENTS.md). The earlier stale-parent history repair merge `ea88a97` is recorded in the [history](delivery/DELIVERY-HISTORY.md).

## WP-010 Director closure — 2026-10-03

ACCEPTED at `f7ad4bc8d067d3b5ab46945cd899da8d074f04d3`. Independently checked commit diff, current documents/history organization, pause/availability/reference wording and CI `37127341286`: checks (including E2E, web typecheck/build) and compose-smoke SUCCESS. Full local suites were reported by the executor, not rerun by the Director. Scope remains documentation and truthful presentation; no method or assurance criteria changed. The reconciliation v2 sentence “No independent reference replay was performed in this run” stays unchanged: it is a negative scope claim, and Deep's shared reducer/cache limits are explicit. The reported executor fetch --dry-run violated the standing no-sync rule; no update occurred, and the rule remains in AGENTS without a new approval flow. Next is a bounded Director R2 specification, not another general infrastructure pass.

## R2 activation — 2026-10-03

Director specification completed and implementation activated: `delivery/WP-008-R2-CAUSAL-TEMPORAL-SPEC.md`. Bounded factual aggregation/clock/readiness and restorable state only, no economic rules. Default horizon roles are conventions; MP-001 owns actual observation lookbacks and decision authority. No new Owner replay, acquisition or general hardening is assigned. Earlier specification-only pointers are historical.

## R2 initial Director review — historical, superseded by correction acceptance

**Correction required at `44ce68a`:** [one blocking finding](delivery/WP-008-R2-DIRECTOR-REVIEW.md). The Director reproduced a 15-minute modeled fixture where the pre-finish Deep chains match with zero sealed records, but the published clock-end finish produces six unexamined records. The active task extends the optional reference check to that terminal output, without changing the original evidence or partial-prefix semantics. CI 37135564664: compose-smoke, web and non-E2E steps succeeded; final checks/E2E were still pending at this review. No new Owner replay or next package is authorized.

## R2 correction accepted — 2026-10-03

ACCEPTED at `ddc1831b5015692e0b34969bc23390c2dff82a46`. Finding 1 closed: Deep v3 pins and compares completed clock-end output; unusable evidence fails, inconsistent output mismatches, partial targets retain prefix-only scope. Source/test review, independent fifteen-minute terminal-comparison probe and CI 37138450907 (checks including E2E and compose-smoke SUCCESS) support acceptance. Local full suites are executor evidence, not Director reruns. No new Owner run requested. task.md now assigns Director MP-001 specification only; R3/WP-009 and adviser implementation remain inactive.

## MP-001 v0.1 proposal — historical, superseded by v0.2 closure

Director wrote the complete first adviser proposal and parameter register before new economic outcomes: continuation after reaction, compression exit/retest and failed range exit; explicit volatility/structure phase, event-risk windows/response, distinct execution adequacy, persistent call/entry/thesis lifecycles, semantic.v2 design, R3 input inventory and preregistered evaluation assumptions. Source concepts and provisional numerical translations are distinguished; no edge/frequency guarantee is claimed. Its former PROPOSED status is superseded by the v0.2 closure below. No adviser code, data or schema was changed, no market outcome was inspected and no historical run was launched.

## MP-001 Director closure — 2026-10-03

Method design closed at `btc.context-action.v0.2`; B1–B8 resolved with explicit ownership/renewal, phase/context authority, frozen landmarks, admissible entry prices, terminal retirement, publication/residual-time, exit/funding accounting and composite capability identity. E1–E6 remain registered economic diagnostics, not tuned away. Original Astra attachment preserved unchanged. Independent document-level arithmetic/time/link checks only; no code, market outcomes, acquisition or new run. Cycle periodicity and comprehensive news interpretation remain limited, not declared solved. That specification-only pointer is superseded by the R3 activation below.

## R3 specification and activation — 2026-10-03

Director completed the bounded context/preset specification and registered logical windows before new economic results. September default requests96h warmup and365m tail; verified September sources reused. Contiguous multi-month packs preserve one causal/temporal state and cross-source ties. Missing funding/calendar/historical metadata proof stays limited, not silently neutral. New pack manifest/receipt and additive operational compatibility are authorized; no method, semantic.v2 or economic metrics. Executor implementation active under task.md, not accepted yet. No Owner download/run requested by this activation.

## R3 Director review — 2026-10-03

CORRECTION REQUIRED at33c2b83: contributor metadata reread outside verified-byte ownership, publication references intended hashes without checking actual artifacts and persisting the staging directory, and unconditional cleanup of other active attempts' staging. Three exact-code AST probes reproduced the isolated defects; full local suites were not rerun. Independently inspected CI37149503468: checks and compose-smoke SUCCESS. Executor458/11 tests remain evidence, not acceptance. Review/task activate only these corrections; WP-009 and Owner preparation handoff remain inactive.

## R3 correction accepted — 2026-10-03

ACCEPTED at09e23fd: verified contributor metadata, byte-checked durable publication and attempt-owned cleanup close findings1–3. Independent focused source/test review and exact-function probes; CI37152698917 checks/E2E and compose-smoke SUCCESS. Full469/11 local suites remain executor evidence. Owner September pack preparation authorized with report-only handoff, no replay/backtest. Director WP-009 specification next; no executor implementation.

## WP-009 specification and implementation activation — 2026-10-03

Director completed integrated contract/state/live/evaluation/UI/test specification from MP-001 v0.2. Owner prepared September pack without new replay; actual boundary rows and storage recorded, no economic outcome inspected. WP-009 executor implementation active: semantic.v2 and all A/B/C families, call lifecycle, separate evaluator, durable live/current-practicability and Home/Workbench. Current implementation still has no adviser until this work is delivered/reviewed. Owner economic handoff remains pending Director acceptance; no agent backtest or parameter search.

## WP-009 correction Director disposition — 2026-10-05

Reviewed `d16c925`: findings 1–6, 8 and 9 closed for this slice; one remaining original-finding-7 case in [the correction review](delivery/WP-009-CORRECTION-DIRECTOR-REVIEW.md). A clean paused Deep can discard a newly detected digest/chain inconsistency on resume. Exact-code offline probe reproduced it; 40 focused pure tests passed, one DB version test skipped (not locally verified); full DB/browser evidence is CI37289189340: 594 non-E2E and 18 E2E passed, checks and Compose smoke SUCCESS. Only the narrow resume fix/regressions are active; no method change or agent economic run. Owner launches substantial backtests in the web app after acceptance and returns Copy report for chat for Director analysis.

## WP-009 final acceptance and Owner handoff — 2026-10-05

ACCEPTED at `6f95273`: all original findings 1–9 closed; [follow-up acceptance](delivery/WP-009-CORRECTION-DIRECTOR-REVIEW.md). Independent source/regression review and exact merge-method probe; CI37300338202 exact-SHA SUCCESS (checks: 599 non-E2E, 18 E2E; Compose smoke SUCCESS). Full local suites remain executor evidence, not Director reruns. Deep v6 new launches, stricter resumed v5 verification, saved reports preserved. Economic performance remains unknown.

**Current next action:** [Owner Backtest A](delivery/WP-009-OWNER-BACKTEST-A.md): app Adviser evaluation / prepared btc-september-development-v1 pack / max / Copy report for chat. No new acquisition, agent economic run, method change or mandatory Deep validation. Earlier inactive handoffs are superseded by this acceptance. The Owner also takes over future CI waiting: executor local checks/commit/push, SHA/link and immediate summary; no polling or background CI shell (AGENTS.md).

## Owner Backtest A result — 2026-10-05

Owner app run `eval-20261005T120047-e6cc50` / `obs-20261005T120047-bc6947`, code6f95273: COMPLETED, 147,975/147,975, runtime reconciliation v5 PASS20/20, elapsed135.2s. Original [report](delivery/evidence/WP-009-OWNER-BACKTEST-A.json), [diagnosis/Astra brief](delivery/WP-009-OWNER-BACKTEST-A-DIAGNOSIS.md). All43,200 scored minutes assessable; births109, arms47, trigger evaluations38, **issued0**. Rejections18 no-room,14 reward/risk,6 opposing-area. Runtime workflow confirmed, method usefulness not accepted on this development month; no entered-path profitability evidence. Director diagnosis next, targeted Astra challenge; no Claude implementation, new Owner run or protected evidence authorized. Historical READY Owner handoff has been exercised and is superseded by this current result.

## Owner Backtest A Astra disposition — 2026-10-05

[Astra review](delivery/WP-009-OWNER-BACKTEST-A-ASTRA-REVIEW.md) preserved unchanged. [Director disposition](delivery/WP-009-OWNER-BACKTEST-A-DIRECTOR-DISPOSITION.md) accepts only one read-only existing-run causal dossier; independent static check confirms blocking-zone attribution loss without proving a missed valid call. Diagnose 38 triggers/109 candidate histories, net feasibility and upstream coverage before method revision. Read-only scoped Owner DB/API/cache access authorized; no product changes, replay, future outcomes or acquisition. Current task activates extraction only. September is the first development check, not the full evidence horizon: additional development months precede frozen/protected validation; no wider Owner run requested now.

## Owner Backtest A causal dossier — executor evidence (base `c5269f2`; READY FOR DIRECTOR REVIEW — DOSSIER ONLY; not accepted)

Read-only extraction for `eval-20261005T120047-e6cc50` / `obs-20261005T120047-bc6947`: [summary](delivery/evidence/WP-009-OWNER-BACKTEST-A-DOSSIER/SUMMARY.md), full [JSON](delivery/evidence/WP-009-OWNER-BACKTEST-A-DOSSIER/dossier.json), [trigger](delivery/evidence/WP-009-OWNER-BACKTEST-A-DOSSIER/triggers.csv)/[candidate](delivery/evidence/WP-009-OWNER-BACKTEST-A-DOSSIER/candidates.csv) CSVs and the one-off [script](delivery/evidence/WP-009-OWNER-BACKTEST-A-DOSSIER/extract_dossier.py).
- **Access**: one REPEATABLE READ READ ONLY psql transaction in the Owner `db` container (run rows + 6,972 journal rows; evaluation-record contents not read) and a byte copy of the pinned feed cache; no writes, service changes, replay, Deep, backtest or downloads. Product code, schemas and the original report are unchanged (report SHA-256 identical).
- **Verification**: journal digests/sequence/chain re-hashed = professional finish commitment; cache manifest = run pin, 30/30 partitions; aggregated 15m bars reproduce 896/896 journaled 15m pivots. All original counts reconcile exactly (births/arms/ends/reasons, 38 triggers, 18/14/6 blockers, limiting histogram, G/Q/K/margin quantiles, 26 staged rows). Per row: T/V DERIVED from side price and G/Q regenerate G/Q/margin/reason (32/32), match candidate invalidation rounding (32/32), 32 targets are reconstructed and all six inside-zone reasons are consistent; only three of those six have uniquely recoverable original zone attribution, DERIVED S15 regenerates the recorded structural area (32/32). Astra §8 LONG/SHORT incompatible/overshoot algebra self-tests pass.
- **Found**: all 32 geometric rejections are incompatible already at the minimum confirmation price (14 have no admissible price between V and T; 18 only beyond the threshold, gap 2.7–37.8 bps). None is overshoot or divergence. The arm/revise cutoff gives the same classes. Six inside-zone refusals: 3 uniquely the attempt's own impulse-B zone, 3 with several containing zones (original choice unrecoverable: F1 confirmed). Of the 26 A targets, 9 are the attempt's own impulse-B near edge. 45 spends verified on pinned bars, 11 with reaction conditions in the same bar (intrabar order unknown). MarketView: NO_SUPPORTED_PLAN 33,001 min (18,387 with UP/DOWN context), WATCH present in 1,725.
- **Missing**: blocking-zone identity for 3 ambiguous refusals, Q_A/latch transitions between records, box used/broken flags; S15/T/V/break flags are DERIVED (validated as above).
- **Checks**: extraction script run on the snapshot; no product-suite/Compose rerun (no product change, per disposition). CI on the pushed SHA: Owner-operated, PENDING / NOT CHECKED by the executor.


## Current Director disposition — dossier closure and MP-002 proposal, 2026-10-05

Dossier at 87948057 is sufficient diagnostic evidence for the observed 14 globally empty supplied geometries, 18 confirmation-incompatible geometries and six inside-zone refusals. [Astra independent arithmetic/cutoff review](delivery/WP-009-OWNER-BACKTEST-A-DOSSIER-ASTRA-REVIEW.md) supports that limited conclusion: it is not an independent journal/cache export, all-mode causal certification or proof of profitability. Earlier executor “38/38 zone identity” wording is qualified: 32 targets, six membership blocks, three uniquely attributed original blocking zones. CI for the dossier remains Owner-operated / not checked by this Director; no product release is inferred.

[MP-002 v0.1](delivery/MP-002-SCENARIO-CONFIRMATION-ENTRY-PROPOSAL.md) and its [parameter delta](delivery/MP-002-PARAMETER-DELTA.json) are FOR ASTRA REVIEW only. Proposed A immediate-versus-post-confirmation return entry, fixed reaction corridor and monotone pre-issue target cap; separate structural scenarios for A/B/C from economic eligibility. Preserve costs/ratio, B/C entry behavior and frozen v0.2 baseline. A's proposed hard deadline is anchored at confirmation (not delayed return issue) to avoid buying time; this is an explicit review decision. No code, schemas, numerical register, source data or saved results changed. Extraction closed; no further Owner run now. Planned Oct/Nov/Dec frozen baseline comparisons are future Owner app actions after engineering acceptance, never agent CLI work or protected tuning.


## Current Director action — MP-002 B1–B7 correction, 2026-10-05

The initial v0.1 proposal status above is historical. [Astra review](delivery/MP-002-ASTRA-REVIEW.md) required seven design corrections, adopted in [Director disposition](delivery/MP-002-DIRECTOR-DISPOSITION.md) and the same [proposal](delivery/MP-002-SCENARIO-CONFIRMATION-ENTRY-PROPOSAL.md)/[delta](delivery/MP-002-PARAMETER-DELTA.json), now v0.2. Separate structural discovery release/reset/zones from economic children; exhaustive mode routing; transient live-cost versus permanent geometric emptiness; causal cap activation; distinct contact/censorship domains; exact progress/hard/horizon-only clocks; primary RETURN-owner and corridor denominators. Bounded Decimal/tick/clock checks are specification checks, not product tests. Focused closure review pending; method design not closed, no executor implementation or Owner run. Product remains MP-001 v0.2.


## Current authority — MP-002 design closure; WP-011 active, 2026-10-05

[Astra CHIUDIBILE](delivery/MP-002-ASTRA-CLOSURE.md) on4b5ef95 closes B1–B7 without new market evidence. [Director disposition](delivery/MP-002-DIRECTOR-DISPOSITION.md) adopts method-design closure; [complete register](delivery/MP-002-PARAMETERS.json) consolidates reviewed categories while preserving trading numerical predicates. Earlier pending-review entries above are historical. Running product is still MP-001 v0.2 at6f95273; MP-002 profitability/practicality unvalidated.

[WP-011 specification](delivery/WP-011-MP-002-IMPLEMENTATION-SPEC.md) is the only active executor package: implement v0.3 plus selectable unchanged v0.2 baseline, durable/live/Workbench/paired reports and bounded engineering closure. No actual product code changed by this Director activation. Owner launches fixed October/November/December paired development evaluations only after Director engineering acceptance; no protected or current economic run authorized. CI waiting remains Owner-operated.


## WP-011 executor evidence (base `7bf0f3c`; READY FOR DIRECTOR REVIEW — WP-011 ONLY; not accepted)

- **Scope**: closed MP-002 v0.3 implemented beside the unchanged v0.2 baseline; method selected explicitly at launch (Workbench) and at live Start; stored results show their pinned method. v0.2 reducer/evaluator/runtime files are untouched and v0.2 outputs on 11 fixed fixtures reproduce the base commit byte for byte. Details: [evidence](delivery/evidence/WP-011-ENGINEERING-EVIDENCE.md) / [JSON](delivery/evidence/WP-011-ENGINEERING-EVIDENCE.json), [measurement](delivery/evidence/WP-011-bench-mp002.json).
- **Identities / contracts**: v0.3 `adviser.core.v3`, `adviser.evaluator.v3`, state v3, runtime v3, evaluation state v2, report v3, engine `observe.stream.v4`, reconciliation v6, Deep v7; semantic.v2 r2, adviser-evaluation.v1 r3, observe.v1 r6. No migration.
- **Checks** (disposable PostgreSQL 18.6, port 55439, Owner stack untouched): full non-E2E 657 passed + 2 failed on the deliberate observe revision pin (updated; `tests/test_observe.py` 21 passed); new suites mp002 paths/rules/db/versions/live green; full E2E 19 passed (incl. the new method/comparison journey); web typecheck/build; `algotrader schema` matches. Compose smoke and exact-SHA CI: Owner-operated, PENDING.
- **For Director decision**: (1) A anchor K ≥ frozen B ends the scenario at destination contact before confirmation (MP-002 §3 literal; reproducible test); (2) pre-existing v0.2 dislocation-baseline defect (veto never active), v0.2 kept unchanged, v0.3 applies the rule; (3) listed interpretations in the evidence file.
- **Owner handoff**: October→November→December paired v0.2/v0.3 development comparison prepared but INACTIVE until Director engineering acceptance. No economic run, acquisition or protected evaluation.


## WP-011 Director engineering review — 5 October 2026

Product reviewed: f1a8023763e820e41cbd6085be14b4ebabbcb0d3. **CORRECTION REQUIRED; no Owner development comparison activated.** [Review](delivery/WP-011-DIRECTOR-REVIEW.md), [offline synthetic probes](delivery/evidence/WP-011-DIRECTOR-PROBES.json).

F1: a B scenario alive at dispatch entry loses box-retirement ownership when the simultaneous V contact removes it before the opposite-edge 15m close is handled; the old box incorrectly births another episode. F2: hourly samples taken after a scenario's confirmation falsely record an unactivated antecedent. Both reproduced on full pure paths. The review records bounded correction checks, exact-SHA CI requirement, and no economic/research run.

A K>=B destination-before-confirmation is consistent with closed rules; no relaxation authorized. The acknowledged v0.2 dislocation bug remains frozen; v0.3 corrects it, so comparison must disclose this additional integrated difference. Remote CI is PENDING / NOT CHECKED by Director and Owner-operated. Earlier WP-011 delivery is evidence, not acceptance.


## WP-011 correction executor evidence (base `ed64d05`; READY FOR DIRECTOR REVIEW — WP-011 CORRECTION ONLY; not accepted)

- **F1** (`core3.py`): the opposite far-edge box retirement is derived from the B episodes alive at dispatch entry; protective call / V contact still runs first and keeps precedence; the old box retires once in that dispatch and births nothing; episodes dead before the dispatch are not resurrected. **F2** (`evaluator3.py`): an hourly sample whose principal is CONFIRMED in the core state at the cutoff records that activation; an ARMED principal is credited only by its own later CONFIRM. Comparison JSON/Markdown/Workbench card and the inactive Owner handoff text disclose the v0.2→v0.3 dislocation correction; report v3 adds the A destination-before-confirmation count/examples. No numerical/method/v0.2 change.
- **Found during the required restore checks:** records emitted during sealed ingestion (1h landmarks) carried the previous dispatch's dependency snapshot, absent from restorable state (pre-existing at f1a8023). v0.3 state now carries it (optional on decode); v0.2 has the same metadata-only defect and stays frozen (disclosed). For Director decision.
- **Fail-before → fixed-after:** Director probes F1/F2 false → true; `tests/test_mp002_correction.py` 13 failed/12 passed → 25 passed; new durable tests + paired comparison 3 failed → `test_mp002_db.py` 7/7.
- **Checks** (disposable PostgreSQL 18.3, port 55439; Owner stack untouched): pure MP-002 + adviser suites 189 passed (22 DB-skipped there, then run with a DB); DB suites 7 + 49 passed; E2E 19 passed; web typecheck/build; schema baselines match. Full local suite and compose smoke not rerun; exact-SHA CI Owner-operated, PENDING. Details: [evidence](delivery/evidence/WP-011-CORRECTION-EVIDENCE.md) / [JSON](delivery/evidence/WP-011-CORRECTION-EVIDENCE.json), [probe output](delivery/evidence/WP-011-CORRECTION-PROBES.json).
- Owner October/November/December comparison remains INACTIVE.


## WP-011 correction Director review — 6 October 2026

Reviewed product 9b05a3e4bd3767ea627fa821ceaea3a32da34460: F1/F2 closed (independent 25 pure tests and original probes pass). Dependency snapshot fix is within direct-restore scope, but F3 remains: optional deps decodes yet new encode adds a key absent in legacy bytes, so production unpack_runtime rejects exact old v3 blobs. [Review](delivery/WP-011-CORRECTION-DIRECTOR-REVIEW.md), [production-codec evidence](delivery/evidence/WP-011-CORRECTION-DIRECTOR-PROBE.json). Only bounded compatibility follow-up is active. No Owner economic comparison; exact-SHA CI remains PENDING / NOT CHECKED by Director and Owner-operated.


## WP-011 compatibility follow-up executor evidence (base `32233ec`; READY FOR DIRECTOR REVIEW — WP-011 COMPATIBILITY FOLLOW-UP ONLY; not accepted)

- **F3 fix** (`core3.py`): the v3 dependency snapshot is written only when known; a legacy state without it re-encodes to its exact verified bytes through the unchanged production `unpack_runtime` guard until a genuine dispatch recomputes it; absent and present-empty are distinct. New states keep the snapshot. No method/numerical/contract/v0.2/stored-output change.
- **Evidence**: legacy fixture encoded by the reviewed codec (worktree of ed64d05) at three cuts; Director probe legacy rejected → exact; `tests/test_mp002_state_compat.py` 7 failed/13 passed → 20 passed; DB legacy restore point (mid-run and after final commit) FAILED (`_UnsafeRecovery`) → completed with assurance passed and no fallback. Integrity failures (SHA, corrupt bytes, unknown key, malformed/non-canonical snapshot, incompatible state) still fail.
- **Legacy limitation**: records emitted during the first post-restore dispatch's sealed ingestion carry empty envelope dependencies (not invented). **For Director decision (not changed)**: Deep v7 on runs whose ranges were written by the pre-9b05a3e codec would report adviser state-hash mismatches (code reading).
- **Checks** (disposable PostgreSQL 18.3; Owner stack untouched): MP-002 pure 100 passed; DB 17 passed (`test_mp002_db`, live DB suites); schema baselines match. Full suite, E2E, compose smoke not rerun; exact-SHA CI Owner-operated, PENDING. [Evidence](delivery/evidence/WP-011-COMPAT-EVIDENCE.md) / [JSON](delivery/evidence/WP-011-COMPAT-EVIDENCE.json).
- Owner October/November/December comparison remains INACTIVE.


## Owner October comparison and read-only diagnosis — executor evidence (base `bd5d81c`; READY FOR DIRECTOR REVIEW — OCTOBER DIAGNOSIS ONLY; not accepted)

Owner runs on build `bd5d81c`, common pack `pack-30c0661f…` / cache `fc-de5aa4a9…`. Both runs COMPLETED; the comparison is COMPARABLE.

| Run | Evaluation / replay | Assurance | Result |
|---|---|---|---|
| v0.2 | `eval-20261006T173330-4e7c36` / `obs-20261006T173330-62d684` | reconciliation v5 PASS 20/20 | 1 A LONG call |
| v0.3 | `eval-20261006T175135-9ddf6d` / `obs-20261006T175135-e8267a` | reconciliation v6 PASS 21/21 | 0 calls; 6 A confirmations: 3 RETURN_WAIT, 2 NO_ECONOMIC_RETURN_REGION, 1 PRE_ENTRY_TARGET_CONTACT; 0 usable returns |

Director-authorized diagnosis: [summary](delivery/evidence/WP-011-OWNER-OCTOBER-DIAGNOSIS/SUMMARY.md), [JSON](delivery/evidence/WP-011-OWNER-OCTOBER-DIAGNOSIS/dossier.json), [confirmations](delivery/evidence/WP-011-OWNER-OCTOBER-DIAGNOSIS/confirmations.csv), [wait minutes](delivery/evidence/WP-011-OWNER-OCTOBER-DIAGNOSIS/wait_minutes.csv), [script](delivery/evidence/WP-011-OWNER-OCTOBER-DIAGNOSIS/extract_diagnosis.py).

- **Access.**
  - One REPEATABLE READ READ ONLY psql transaction (snapshot `540150:540150:`) and a byte copy of the pinned cache. The export stays outside Git.
  - No replay, Deep, backtest, download, sweep, product/parameter/schema change, or Owner-stack start/stop.
- **Verification.**
  - Both journals and both evaluation-record chains were re-hashed and equal their finish commitments.
  - The cache manifest equals the pin; 31/31 partitions verified.
  - The app's own report builders on the stored rows reproduce the Owner's counts exactly.
  - The extraction is byte-reproducible.
- **Q1 — the LONG.** Same birth/arm in both runs. At the 23:30 dispatch the 1m interval [23:29,23:30) has low 114329.5 ≤ armed V 114343.28.
  - v0.3 invalidates the scenario (MP-002 §3/§6: V contact is processed before newly complete revisions; `core3` order matches).
  - v0.2 checks V only on confirming minutes and re-anchors V lower at the 15m close (MP-001 §98), then issues at 23:34.
  - Dislocation and other entry gates are not involved.
  - Scope (STORED): 49/55 October v0.2 A revisions (29 attempts) went at or through the armed V; the only v0.2 call came from one of them.
- **Q2/Q3.**
  - In 5/6 confirmations T_confirm is the scenario's own impulse-B near edge, 0.45–20.4 bps from the close; every scenario later reached its destination (1–93 min).
  - The three waits each needed a 26–29 bps retracement toward R. Price never closed there, and never traded there intrabar.
  - Endings: setup deadline (1); destination/target-side contact (2).
  - The DERIVED price blockers equal the STORED blocker set in force in 64/64 sampled minutes.
- **Findings.**
  - Behaviour conforms to MP-002 and the build code. No implementation defect or counterexample was found.
  - For Director decision: the V-contact vs inherited re-anchoring interaction (explicit in the spec, measurable effect).
  - Code-reading notes:
    - the return gate samples only the latest minute of a dispatch;
    - the `corpus.pack.method` preset label reads v0.2 for both runs.
  - The counterfactual (what v0.3 would have issued without the rule) is NOT DEMONSTRABLE without an unauthorized replay.
- **Checks.** Documentation-only delivery: no product suite or Compose smoke rerun (per Director instruction). Counts, provenance and links were checked. CI on the pushed SHA is Owner-operated: PENDING / NOT CHECKED.
- November/December remain SUSPENDED. No implementation is activated.


## MP-003 focused closure correction — 6 October 2026

Astra identified one remaining contradiction in design v0.1: a birth-time B-contact terminal would override inherited pre-first-arm spend at B+z. Director adopts the requested preservation. MP-003 v0.2 §4 activates destination monitoring only at the first actually published arm, with immutable publication time/cursor and explicit prospective/straddling rules; ever_armed keeps it active in WATCH after anchor loss. §6 adds the three counterexamples. This corrects the design text, not product code. Closure remains pending; no implementation or economic run is active.


## MP-003 Director closure / WP-012 activation — 6 October 2026

[Astra closure](delivery/MP-003-ASTRA-CLOSURE.md) reports no remaining/new blocker on eb091648. Director accepts this method-design conclusion, preserves the reviewed MP-003 prose, and activates only [WP-012](delivery/WP-012-MP-003-IMPLEMENTATION-SPEC.md). [Full register](delivery/MP-003-PARAMETERS.json) inherits MP-002 with all 108 numerical values preserved; changed categorical policies name the closed delta. No product/schema/data/test/economic run occurred in this activation. CI waiting remains Owner-operated. No general UX cleanup, parameter search, protected access or next package.


## WP-012 executor evidence (base `68f26da`; READY FOR DIRECTOR REVIEW — WP-012 ONLY; not accepted)

[Evidence](delivery/evidence/WP-012-ENGINEERING-EVIDENCE.md) / [JSON](delivery/evidence/WP-012-ENGINEERING-EVIDENCE.json), [fixture table generator](delivery/evidence/WP-012-FIXTURE-TABLE.py), [bounded measurement](delivery/evidence/WP-012-bench-mp003.json).

- **Implemented.**
  - `btc.context-action.v0.4` / `mp003.rules.v0.4` is selectable in the Workbench (step 2, with its purpose) and at live Start. Absent selection is still v0.2.
  - `adviser/core4.py` subclasses the v0.3 fold and replaces only the A pre-confirmation domains:
    - local V contact → `ANCHOR_LOST` (same scenario, WATCH);
    - strictly deeper newly completed 15m reaction → prospective `REARM` at the actual dispatch time/cursor;
    - destination monitored from the immutable first-arm publication, also in WATCH;
    - straddling/simultaneous contacts are unassessable;
    - frozen after the first confirmation.
  - Everything after confirmation and the evaluator are v0.3; no numerical value changed.
- **Identities.**
  - `adviser.core.v4`, state/runtime v4, engine `observe.stream.v5`, report v4, reconciliation v7 (anchor-lineage checks), Deep v8; evaluator v3 reused.
  - The rules identity is a manifest of the MP-003 delta and the inherited MP-002 rules/disposition and MP-001 rules.
  - semantic.v2 r3 (`ScenarioStateV4`); observe.v1 r7 (method value only); adviser-evaluation.v1 unchanged (r3). No migration.
  - v0.3 status corrected to TECHNICALLY_ACCEPTED (identity and outputs unchanged).
- **Preservation.**
  - All 38 v0.2/v0.3 fixed-fixture outputs equal pins from the unchanged base.
  - B/C and post-confirmation A outputs equal v0.3 on 9 tapes (identifiers normalized).
  - Strict codecs: no cross-method decode or resume.
- **Checks** (disposable PostgreSQL 18.6, port 55439; Owner stack untouched):
  - MP-003 fixtures 46 (all 13 §6 rows, LONG and SHORT, equality/ties, delayed publication/backlog, straddling, old bar, late epoch);
  - versions/codec/parity 55; durable DB 11; live 5; browser journey 1;
  - final full non-E2E 824 passed + 2 failed on the deliberate observe.v1 revision pin (updated; `test_observe.py` 21 passed);
  - full E2E 20 passed;
  - web typecheck/build; schema baselines.
- **Reports and UI.**
  - Anchor diagnostics: owner level vs event level, evaluation window only.
  - Baseline/candidate comparison with the MP-003 limitation; v0.2/v0.3 comparison still readable.
  - Follow and live views distinguish observation, active anchor, confirmed WAIT and call.
- **For Director decision** (interpretations, evidence §6):
  - ever-armed WATCH needs fresh monitoring evidence;
  - late earlier-epoch contact → current anchor UNASSESSABLE;
  - the contact-containing 15m bar is an eligible replacement source;
  - live publication = dispatch tick after receipt.
- **Owner plan.** October/November/December v0.3 baseline vs v0.4 is prepared but INACTIVE until Director acceptance and exact-SHA green CI. October may reuse `eval-20261006T175135-9ddf6d`. No economic run by the executor.
- **CI.** Exact-SHA CI is Owner-operated: PENDING / NOT CHECKED.


## WP-012 Director review — 7 October 2026

Reviewed e434d4311a947f65f2fccf035d61e79d9108add2: CORRECTION REQUIRED. [Review](delivery/WP-012-DIRECTOR-REVIEW.md), [synthetic proof](delivery/evidence/WP-012-DIRECTOR-PROBES.json). F1: a minute straddling actual anchor supersession touches the old V but not the new V; core4 ignores the older overlapping domain, then confirms that new anchor. Reproduced on complete LONG/SHORT tapes (publication 04:00:30, contact interval [04:00,04:01), unexpected confirmation 04:14). Required anchor ambiguity/WATCH, not a new whole-scenario terminal. Director pure paths/versions: 101 selected tests pass after repairing missing docs in temporary snapshot; no DB/browser/Compose rerun. CI PENDING / NOT CHECKED, Owner-operated. Only bounded correction active; v0.4 and Owner economic plan not accepted/activated. No Owner data/stack touched.


## WP-012 correction F1 executor evidence (base `85ee150`; READY FOR DIRECTOR REVIEW — WP-012 CORRECTION ONLY; not accepted)

[Evidence](delivery/evidence/WP-012-CORRECTION-EVIDENCE.md) / [JSON](delivery/evidence/WP-012-CORRECTION-EVIDENCE.json).

- **Fix** (`core4._local_contact`). Every anchor domain that overlaps an interval is evaluated: superseded epochs only within their active domain; domains ended by a loss never again.
  - An interval straddling a supersession that reaches only the old V now makes the current anchor UNASSESSABLE (`SUPERSEDED_ANCHOR_CONTACT_TIME_AMBIGUOUS_EPOCH_n`): same owner WATCH, cutoff retained, later genuine replacement allowed.
  - MP-003, identities, formats and contracts are unchanged; closed domain entries now record SUPERSEDED/LOST.
- **Director probe.** Before: epoch 2 CONFIRM 04:14 (LONG/SHORT). After: ANCHOR_LOST UNASSESSABLE 04:01, no epoch-2 confirmation.
- **Tests.** `tests/test_mp003_correction.py`, 19 cases:
  - F1 regression and controls (neither V touched, new V reached, wholly-after old-V touch not resurrected, dead domain not re-tested), LONG/SHORT;
  - production pack/unpack around the supersession and the contact;
  - live restarts from persisted state at 3 points;
  - a durable LiveStore save/load restore.
- **Fail-before / fixed-after.** On `e434d43`: 6 failed / 6 passed (controls unchanged). After: all pass.
- **Relevant suites** with a disposable DB: 208 passed (MP-003 paths/versions/live/DB, MP-002 compatibility/versions/paths/rules incl. the 38 v0.2/v0.3 byte pins). Full suite, browser and Compose were not rerun (kernel-only change).
- **CI.** Exact-SHA CI is Owner-operated: PENDING / NOT CHECKED. The Owner plan stays INACTIVE.


## WP-012 correction Director closure — 7 October 2026

[Review](delivery/WP-012-CORRECTION-DIRECTOR-REVIEW.md): F1 CLOSED on e3a5afa6e355363cd2df93871c68ad8cb4de3626. Director original LONG/SHORT probes now lose epoch 2 at 04:01 and only later legitimately re-arm/confirm epoch 3. 18 independent correction tests pass; 1 DB test deliberately excluded. Genuine old-source four-element states round-trip exactly through current production unpack after supersession and loss. Legacy untagged domains remain conservatively uncertain; pre-correction v0.4 engineering Deep/hash mismatches are not relabelled or forced to match. Executor DB/208-suite results were examined, not rerun by Director. CI PENDING / NOT CHECKED, Owner-operated; no app/economic handoff yet. No product/schema/data change in this closure.

## WP-012 E2E stabilization executor evidence (base `2b8c327`; test-only; not accepted)

CI run 37587727298 (job 112681663191) on e3a5afa failed only `test_owner_runs_v04_sees_anchor_observation_and_compares_with_v03` (paused at clock 04:02, anchor 2 already active); 37589116092 on 2b8c327 was green with identical product code.
- **Cause (test timing, no product defect):** observation `progress.applied_events` is the committed checkpoint cursor; at speed > 0 the worker commits every `checkpoint_seconds` (2 s) of wall time, so at speed 100 it can trail the kernel by ~200 deliveries. The test switched to speed 1 when the *reported* cursor reached `CONTACT_DISPATCH - 120`, only 147 deliveries before the 04:00 rearm, so on a fast runner the kernel could already be past 04:00 before the speed change/pause applied. Documented PAUSE/STEP semantics behaved as specified.
- **Fix (`tests/e2e/test_mp003_e2e.py` only):** pause via the UI at reported cursor ≥ `CONTACT_DISPATCH - 450`, wait until the replay is parked (`status == paused`; committed cursor final), assert the parked cursor is before the 03:51 contact, then grant exactly `CONTACT_DISPATCH + 2 - parked` STEPs and wait for that exact committed cursor. The "Scenario under observation; waiting for a new completed reaction" assertion and all later assertions (STEP to anchor 2, completion, diagnostics, comparison, copy, layouts) are unchanged. No timeout/retry increase; MP-003, parameters and product code unchanged.
- **Checks:** the affected test passed 3/3 on Windows and 3/3 on Linux (uv python3.14-trixie container, WSL2 kernel), each against a disposable Postgres 18.6 (plus 2 earlier Windows development runs). Instrumented run: reported 4214 → parked 4237 (contact 5013, rearm 5040). Full suite and Compose smoke left to CI (test-only change). CI PENDING / NOT CHECKED, Owner-operated. Economic comparison remains INACTIVE.

## Owner Q4 v0.4 read-only diagnosis — executor evidence (base `c525941`; READY FOR DIRECTOR REVIEW — Q4 DIAGNOSIS ONLY; not accepted)

> Superseded in part by the correction below (091df18 erratum): the "single supported mechanism", the stop/delay/warmup exclusions, the −1.307 % total and the mixed-denominator distances in this entry are withdrawn.

[Summary](delivery/evidence/WP-012-OWNER-Q4-DIAGNOSIS/SUMMARY.md) · [dossier.json](delivery/evidence/WP-012-OWNER-Q4-DIAGNOSIS/dossier.json) · [calls.csv](delivery/evidence/WP-012-OWNER-Q4-DIAGNOSIS/calls.csv) · [confirmations.csv](delivery/evidence/WP-012-OWNER-Q4-DIAGNOSIS/confirmations.csv) · [extraction](delivery/evidence/WP-012-OWNER-Q4-DIAGNOSIS/extract_q4_diagnosis.py) · [export SQL](delivery/evidence/WP-012-OWNER-Q4-DIAGNOSIS/export.sql).
- **Scope (Owner assignment, 7 Oct).** Read-only cross-month diagnosis of the Owner v0.4 runs at c525941: eval-20261007T094006-67272e (Oct), eval-20261007T102821-ae14be (Nov), eval-20261007T105636-6d9276 (Dec). The v0.3 baselines (eval-20261006T175135-9ddf6d, eval-20261007T101912-087dd1, eval-20261007T105343-eb536a) were used for record comparison. No replay, backtest, Deep validation, counterfactual, download, or product/schema/method/data/Owner-stack change.
- **Evidence status.** October–December 2025 are now **EXPOSED DEVELOPMENT**. They are not intact verification for any future revision.
- **Provenance.**
  - One `REPEATABLE READ READ ONLY` psql transaction via `docker exec` (snapshot `704341:704341:`).
  - All six journal and evaluation-record chains equal their finish commitments.
  - The three pinned caches were byte-copied; manifests equal the pins and all partitions verified.
  - Product `compare.comparability` gives COMPARABLE for each month.
  - The extraction is byte-reproducible (two runs). Raw exports stay outside Git.
- **Reconciliation (product report builders).**
  - Owner figures reproduced exactly: 64 A confirmations (19/20/25), 46 WAITs, 10 calls (9 RETURN + 1 IMMEDIATE), 9 RETURN owners entered at PRIMARY 60 s.
  - PRIMARY: 2 target, 1 guidance time exit, 7 stop; price-net sum −1.307 %. Funding is not covered.
  - Derived WAIT price blockers equal the stored blocker changes in 963/963 sampled minutes; the only non-price blocker was BLOCKED_BY_ZONE, 4 minutes.
- **Findings (STORED/DERIVED).**
  - Selection: 0 rejections for slot/priority/execution.
  - Confirmations without a call:
    - 26 WAITs ended target-side before any return;
    - 6 expired without a return;
    - 3 hit a context restriction;
    - 2 ended on V contact during the WAIT;
    - 17 ended at confirmation (9 no economic region, 6 at opposing area, 2 target contact).
  - Scenario fate after confirmation: B reached in 43/64 overall, but only 2/9 after a usable return. V contact in 7/9 after a usable return versus 3/37 in WAITs without one.
  - 9/10 calls exist only through MP-003 anchor replacement. Scenario B-rate is equal with and without replacement (29/43 vs 14/21).
  - Stop distance does not separate winners from losers. On the 7 stopped calls HORIZON_ONLY sums −2.30 % against −2.63 % stopped.
  - The 0 s / 120 s sensitivities are nearly identical to PRIMARY.
  - First entry windows last 1–9 min (median 2.5).
- **Supported mechanism (single).** Return selection: the RETURN entry fires only after a deep post-confirmation retrace toward V, and in these records that retrace selects the failing scenarios.
  - Limits: n=9; a mechanical proximity-to-V component cannot be separated; the counterfactual is not authorized.
  - Counter-evidence: 2 RETURN targets; call 12-05 recovers at horizon; return depth does not separate outcomes.
  - No parameter or rule is proposed.
- **Warmup (96 h).**
  - 15m/1h dependencies are ready before each month starts.
  - 1h pivot memory (168 h) is truncated until day 4.
  - Previous-week levels are absent until 6 Oct / 10 Nov / 8 Dec.
  - Previous-month levels are never available inside an evaluated month.
  - Affected calls are 12-01 and 12-05 only. A descriptive price-range bound shows no missing pivot or weekly level could lie between their entry and target.
  - October's pre-warmup bound is UNAVAILABLE (September source cache not copied).
- **1 Jan 2026 tail.**
  - Both December runs admitted only 365 trade, 365 mark and 365 index 1m bars for 00:00–06:05; no funding.
  - Zero decision records in the tail; no December call path or scenario resolved there.
  - Only contribution: 3 Dec-31 view samples have 4 h endpoints in the tail (1 directional). January–August 2026 is otherwise untouched; there is no basis for declaring the protected months contaminated.
- **Checks.** Count reconciliation, chain/pin/hash provenance, two-run reproducibility and link check. No full suite, E2E or Compose (diagnostic-only delivery). CI PENDING / NOT CHECKED, Owner-operated.

## Owner Q4 diagnosis correction — executor evidence (base `091df18`; READY FOR DIRECTOR REVIEW — Q4 CORRECTION ONLY; not accepted)

Astra reviewed the dossier at 091df18 and this correction applies that review. Only the dossier, diagnostic script and documentation changed. No product, method, parameter, schema or stored-result change; no new DB extraction, acquisition, replay, Deep or economic run.
- **Inputs.** Artifacts were regenerated from the same session exports (snapshot sha256 `44c5dbc2…e094` and the three verified caches). The extraction stays byte-reproducible over two runs. The previous delivery is preserved in Git history, and an erratum heads the [SUMMARY](delivery/evidence/WP-012-OWNER-Q4-DIAGNOSIS/SUMMARY.md); `dossier.json → erratum_vs_091df18` lists the same corrections.
- **Corrections.**
  - **(1) 7/9 vs 3/37.** Now a descriptive association between groups defined by post-confirmation events with competing terminals. It is not a causal RETURN effect or evidence of general scenario quality.
  - **(2) Corridor vs economic restriction.** Corridor return (32/46 WAITs) is distinguished from the economic restriction (9/46). The economic share of the corridor ranges 0.00–1.00, median ≈ 0.37. The 31 Oct counterexample is kept: economic share 1.00, 9.3 bps of the close, target reached.
  - **(3) Sensitivities.** Denominators are reported: ENTRY_DELAY_120 covers 9 entered paths + 1 NO_ENTRY. HORIZON_ONLY is labelled a whole-exit-policy change. Both 23 Nov and 5 Dec have positive HORIZON_ONLY endpoints. The delay and stop exclusions are withdrawn.
  - **(4) Re-anchoring.** Anchor provenance is kept; re-anchoring is not declared harmless. The comparison group "no replacement after contact" may include revisions.
  - **(5) Warmup.** The exclusion is withdrawn: all 10 calls and all 64 confirmations lack previous-month levels. Price bounds are labelled non-reconstructive, and pivot memory completeness after `warmup_start+168h` is NOT_CERTIFIED. The tail conclusion is unchanged and separate.
  - **(6) Separate outcomes.** Destination B, call target, scenario, guidance and hypothetical path are kept distinct.
  - **(7) Totals.** Computed exactly, rounded only for presentation.
    - Exact sum of the 10 STORED PRIMARY price-net values: −0.0130817434351891232589748454948995…, ≈ −1.308 %. It is a normalized one-unit sum, not an account return.
    - The earlier −1.307 % summed per-path percentages already rounded to 3 decimals.
    - **Discrepancy with the supplied Owner total.** The supplied −0.01308174343518912325907484550 agrees with the records to 21 decimal places but differs by 1.0×10⁻²² (…258974… vs …259074…). It is not reproducible from the stored report values; this is reported, not forced.
  - **(8) Distances "from the close".** All now use the close as denominator, as the product's G/Q use the side price. Fields are renamed `*_bps_of_close`. 169 independent recomputations match.
- **Conclusion.** Diagnostic hypothesis on RETURN; causal mechanism not identified. The dossier authorizes no new rule or parameter.
- **Proposed next step (NOT activated).** An Owner-run continuous v0.4 September–December reference with adequate initial context, launched from the web app. January–August 2026 stays protected apart from the documented 1 Jan 00:00–06:05 tail.
- **Checks.** Exact totals, distance definitions, artifact consistency (no stale field names), two-run reproducibility and links. No full suite, E2E or Compose. CI PENDING / NOT CHECKED, Owner-operated.

## Q4 dossier closure — 7 October 2026

Director closure of [the Q4 dossier](delivery/evidence/WP-012-OWNER-Q4-DIAGNOSIS/SUMMARY.md) at `2d6fe9e`: "Accettato come evidenza descrittiva; associazione RETURN–terminali osservata; causalità non identificata; nessuna modifica metodologica autorizzata."

A non-blocking typo is corrected: `dossier.json → erratum_vs_091df18` and the script string now quote the authoritative total −0.0130817434351891232589748454948995…. The earlier figure was a Director transcription, and its comparison field is renamed `director_quoted_total_typo_superseded`. Only `dossier.json` was regenerated, from the existing local exports, with no Owner-DB read; the CSVs are byte-identical.

## WP-013 executor evidence (base `2d6fe9e`; READY FOR DIRECTOR REVIEW — WP-013 ONLY; not accepted)

[Protocol, registered before launch](delivery/WP-013-CONTINUOUS-REFERENCE-PROTOCOL.md) · [evidence](delivery/evidence/WP-013-ENGINEERING-EVIDENCE.md) · [presets registration](delivery/WP-013-PRESETS.json).
- **Preset.** `btc-2025-09-to-2025-12-continuous-init35d-v1` (identity `fabd1c55…2dbc`):
  - initialization 2025-07-28 → 2025-09-01, not evaluated;
  - evaluation 2025-09-01 → 2026-01-01;
  - tail to 2026-01-01 06:05.
  - The optional `Preset.initialization` field is omitted when absent, so the WP-008-R3 and month-builder presets keep byte-identical documents and identities. The 96 h fine warmup is unchanged.
  - Pack contract `algotrader.corpus-pack.v1` revision 2 (changelog). Fine-warmup manifests keep `schema_revision` 1, so a rebuild keeps its pack id.
- **Run.** One continuous run: the existing v0.4 kernel already has a single WARMUP→EVALUATION transition and no month logic, and it is unchanged.
  - The engine document gains an `initialization` pin only for explicit-initialization packs.
  - The method rules and values, the evaluator and stored results are unchanged; PRIMARY stays 60 s.
- **Report.** `adviser.report.v4` gains additive sections, only for explicit initialization and/or multi-month windows:
  - a context attestation at the evaluation start: coverage, readiness, previous day/week/month and pivot states; insufficient data and never-built kept apart from built-then-broken/expired/retired; pivot memory completeness NOT_CERTIFIED;
  - launch pins;
  - total plus calendar-month sections: calls attributed to their issue month and followed past the month end; confirmations, WAITs, coverage and samples on their own times and denominators; exact per-variant sums and reconciliation checks; censoring and funding stated.
  - The sections are carried by Copy report for chat and the Markdown/JSON exports.
- **Workbench.** The initialization is shown separately with a not-evaluated note. The fixed "4 days" lede is generalized, and the run-setup and report hints adapt.
- **Checks.** Run with a disposable PostgreSQL 18.6, never the Owner stack:
  - new pure tests 11 passed; new DB tests 4 passed (pure-fold equality, crash/restore inside an open call across a month boundary, API/Copy/export sections, fine-warmup shape unchanged);
  - new browser E2E 1 passed; existing pack-workbench and MP-003 journeys 2 passed;
  - pack/schema/corpus 55 passed; schema baselines match; web typecheck and build pass;
  - full non-E2E suite 860 passed (46 min, `ALGOTRADER_REQUIRE_DB=1`, no skips).
- **Owner handoff.** INACTIVE until the Director's technical review and green exact-SHA CI. The instructions and the reading criteria (registered before launch) are in the protocol. No real acquisition or Owner-DB extraction was performed. CI PENDING / NOT CHECKED, Owner-operated.

## WP-013 correction executor evidence (base `41790dd`; Astra review F1–F2 only; READY FOR DIRECTOR REVIEW — WP-013 CORRECTION ONLY; not accepted)

[Evidence](delivery/evidence/WP-013-CORRECTION-EVIDENCE.md). The method, kernel, evaluator, parameters, temporal protocol, stored records, schemas, registered protocol and UI are unchanged. The Owner launch stays INACTIVE.
- **F1.** The continuous-run Markdown (Copy report for chat = `.md` export) now shows, for TOTAL and each month, one row per variant (PRIMARY, ENTRY_DELAY_0, ENTRY_DELAY_120, HORIZON_ONLY):
  - expected pairs, available records and pairs without a terminal record;
  - CLOSED, CLOSED with price-net, NO_ENTRY, CENSORED, UNRESOLVED and AMBIGUOUS;
  - exits after the period end;
  - the sum with its population (`+x% over n closed`), or `none observed (0 closed)` instead of a bare 0.000%.
  - Monthly MarketView, samples, scenario transitions and D/N lines are added.
  - The JSON additions are additive (`by_status`, `sum_population`, `economic_result_observed`, …); earlier keys and values are kept.
- **F2.** Expected pairs = evaluable calls (issued in the window, HISTORICAL_MODELED) × the variants pinned in the run's evaluator identity. Missing terminal records are counted per variant and month of issue, and nothing is inferred for them.
  - `reconciliation` is declared as arithmetic of the available records, with checks for attribution and repeated records.
  - `outcome_completeness` is separate and uses the run's actual status: pending "outcome not yet recorded at checkpoint" for an unfinished run, explicit **REPORT INCOMPLETE** for a run declared completed. The run's saved status and assurance are unchanged; feed coverage is not finalization.
- **Fail-before / pass-after.** New pure regressions `tests/test_wp013_correction.py`: 7/7 fail on `41790dd`, 7/7 pass after. The extended DB test (API JSON/Markdown/export; deleting a HORIZON_ONLY terminal record from a completed run in the disposable DB) fails before and passes after.
- **Checks.** Disposable PostgreSQL 18.6 only, never the Owner stack. WP-013 pure + DB suites: 22 passed; related report/evaluation suites (`test_mp003_db`, `test_mp003_versions`, `test_mp002_db`, `test_evaluation`): 79 passed; WP-013 browser E2E (Copy = Markdown export): 1 passed. The full suite was not rerun.
- CI PENDING / NOT CHECKED, Owner-operated.

## WP-013 F2-R1 executor evidence (base `6f49ae7`; READY FOR DIRECTOR REVIEW — WP-013 F2-R1 ONLY; not accepted)

[Evidence](delivery/evidence/WP-013-CORRECTION-EVIDENCE.md#f2-r1--one-expected-population-for-path-records-base-6f49ae7-ready-for-director-review--wp-013-f2-r1-only). F1 is not reopened. The method, kernel, evaluator, parameters, stored data and assurance are unchanged. The Owner launch stays INACTIVE.
- **Fix.** One expected population (evaluable calls in the window × pinned evaluator variants). EVERY available path record is compared with it before deduplication: admitted, extraneous (`UNKNOWN_CALL`, `CALL_NOT_EVALUABLE`, `VARIANT_NOT_CONFIGURED`, `CALL_OUTSIDE_EVALUATION_WINDOW`) or duplicate.
  - Only admitted pairs enter counts, states and sums.
  - Extraneous or repeated records fail explicit reconciliation checks and are summarized in the copyable Markdown (`periods.path_records` in JSON).
  - COMPLETE can coexist with a failed reconciliation, which is shown next to it. A missing outcome is never extraneous. UNKNOWN is kept without a pinned evaluator.
- **Protocol.** Rule 1 records the Director decision on REPORT INCOMPLETE (blocks the economic reading; no retroactive status/assurance change; failed reconciliation is a distinct block).
- **Fail-before / pass-after.** The Astra counterexamples (alien call, PRIMARY-only pin with a HORIZON_ONLY record, LIVE call in the window) plus a call outside the window: 4/4 fail on `6f49ae7` (alien reconciliation passed; HORIZON_ONLY and LIVE records counted in the sums) and pass after. The extended DB test (inserted unknown-call record) also fails before and passes after.
- **Checks.** Disposable PostgreSQL 18.6, stopped afterwards: WP-013 pure + DB 26 passed; WP-013 E2E 1 passed. The full suite was not rerun. CI PENDING / NOT CHECKED, Owner-operated.

## Continuous v0.4 run — Director acceptance and read-only diagnosis (7 October 2026)

**Director decision, recorded verbatim:** “Prova continua accettata come evidenza descrittiva di sviluppo; risultato negativo; causa non identificata; nessuna modifica metodologica autorizzata.”
- **Run:** evaluation `eval-20261007T182934-3f41ad`, replay `obs-20261007T182934-f8c3d4`, build `97a2a8c`, pack `pack-1ae7d36c…`.
- **Recorded result:** COMPLETED, assurance PASSED 21/21. 89 A confirmations, 57 WAITs, 13 calls (12 RETURN, 11 RETURN entered PRIMARY), 52 terminal path records. PRIMARY exact price-net sum −0.01726699… over 12 CLOSED.
- **Executor diagnosis** ([dossier](delivery/evidence/WP-013-CONTINUOUS-V04-DIAGNOSIS/SUMMARY.md); READY FOR DIRECTOR REVIEW — CONTINUOUS V0.4 DIAGNOSIS ONLY; not accepted):
  - **Access.** The app report first, then one REPEATABLE READ READ ONLY extraction limited to this run. No cache copy, write, replay, Deep validation, backtest or counterfactual.
  - **Integrity.** The chains match the finish commitment, the pins are consistent, every count above reconciles, and two runs of the script give byte-identical output.
  - **Evidence definitions.** S1–S6 were registered before the outcome analysis from existing fields only, without thresholds. One erratum: same-dispatch context/phase observations are included, because they are journaled after the decision.
  - **Findings — records.** No predefined adverse structural record precedes any of the 13 issues. 11 RETURN calls are H2-consistent; #13 has one new obstacle (cap revision); the IMMEDIATE call is not applicable.
  - **Findings — outcomes.** 10 of 12 RETURN calls end on the frozen V, with the scenario invalidated in the same dispatch. The issue close sits 4.67–61.94 bps (median 12.7) from V, after an adverse return of 0.15–2.06 S15 into the R–K corridor.
  - **Not decidable from the records.** Whether that return was itself unrecorded deterioration, and causality. The WAITs without return are not controls.
- **Checks.** Dossier verifications only (reconciliation, chains, reproducibility). No product suites or Compose. CI PENDING / NOT CHECKED, Owner-operated.

### Continuous v0.4 diagnosis — Astra F1–F4 correction (base `e07bbe0`; READY FOR DIRECTOR REVIEW — CONTINUOUS V0.4 DIAGNOSIS CORRECTION ONLY; not accepted)

These are dossier and script corrections only, made from the existing local exports. There was no new extraction, acquisition, replay, Deep validation, backtest or method change.
- **F1 — observation limits.**
  - S1–S6 count published occurrences, not every state change. Categories persist; values are as of their publication. Each decision now reports the published category, its timestamp and the values as published.
  - S1, S2 and S3 are described as landmark break, opposite scenario transition and aggregate-view counterevidence, none automatically specific to the call.
  - The absence of S5/S6 at issue is expected from the gates; it is not an independent check of selection quality.
  - `classify()` is aligned to the definition: missing context/phase observations give INDETERMINATE, never H2.
- **F2 — wording.** All 12 RETURN calls reach the economic region with no directional H1 occurrence: 11 are in the H2 class and #13 is OBSTACLE_ONLY. The #13 cap 88564.3 → 88564.0 is a target constraint.
- **F3 — no conclusion about chance.** The chance-indistinguishability sentence is withdrawn and replaced: a small selected sample, no generalizable estimate, no causal identification, no equivalence-to-chance conclusion.
- **F4 — levels, prices and times.**
  - V structural (scenario) and V operational (tick-rounded guidance) are separated; every distance declares V_op and its reference price.
  - Terminal publication, contact bar and the UNAVAILABLE intrabar instant are distinguished.
  - #3 corrected: issued 00:52, contact bar 00:52–00:53, terminal published 00:53; the zero-delay path enters and stops in the 00:52 bar.
  - PRIMARY entry prices are modeled opens; the field is renamed `primary_entry_open_to_V_operational_bps`, values unchanged.
  - Reconciliation 12 = 10 + 2 and 10 = 9 + 1 is added.
- **Provenance.** The initial definitions came before joining outcomes. The cutoff was corrected afterwards (context/phase computed before, published after the decision; MarketView after selection excluded). Only the 4 context-withdrawn WAITs change.
- **Executor checks.**
  - The synthetic probe gives INDETERMINATE for missing observations; it failed on the `e07bbe0` script, which returned H2.
  - Classes, counts and exact sums are unchanged, and regeneration is byte-identical.
  - No product suites, E2E or Compose were run.
  - Astra's independent verification is separate.
- CI PENDING / NOT CHECKED, Owner-operated.

## MP-004 Director closure / WP-014 activation — 8 October 2026

Owner-relayed Director closure, recorded verbatim in [MP-004-DIRECTOR-CLOSURE.md](delivery/MP-004-DIRECTOR-CLOSURE.md): MP-004 v0.5 is closed methodologically; the closure approves candidate semantics, not economic effectiveness; both §8 joints are accepted (straddling local contact → UNASSESSABLE without renewal; first recovery observed late and no longer current → not issuable, no later bar searched). WP-014 is the only active package ([task](delivery/WP-014-MP-004-IMPLEMENTATION-SPEC.md)). No Owner run is activated.

## WP-014 executor evidence (base `776752e`; READY FOR DIRECTOR REVIEW — WP-014 ONLY; not accepted)

[Evidence](delivery/evidence/WP-014-ENGINEERING-EVIDENCE.md) · [v0.4 base-pin generator](delivery/evidence/WP-014-V04-BASE-PINS.py) · [inactive continuous plan](delivery/WP-014-CONTINUOUS-V04-V05-PLAN.md).
- **Implemented.**
  - `btc.context-action.v0.5` / `mp004.rules.v0.5` is selectable in the Workbench (label, status and purpose before Start; pin *MP-004 v0.5*) and at live Start. Absent selection is still v0.2.
  - `adviser/core5.py` subclasses the v0.4 fold and changes only the A RETURN child. The first usable return prepares one reference (H0/L0, bar, actual publication p0, cursor c0). WAIT_RESPONSE checks every later domain bar: contradiction, straddling ambiguity, then the first recovery is evaluated once. The outcome is ISSUE or RESPONSE_NOT_ISSUABLE with all blockers and one primary reason. IMMEDIATE, B/C, geometry, costs, deadlines, the evaluator and the post-issue lifecycle are inherited.
- **Identities.**
  - `adviser.core.v5`, state/runtime v5, engine `observe.stream.v6`, report `adviser.report.v5`, reconciliation v8 (response lineage), Deep v9; evaluator v3 reused.
  - The rules identity is a manifest of the MP-004 delta, its closure and every inherited text. The register is executor-derived (no numerical change; `mp004_policy`).
  - semantic.v2 r4 (`EntryAttemptV5.response`), observe.v1 r8 (method value only). adviser-evaluation.v1 is unchanged (r3). No migration.
- **Preservation.**
  - 53 v0.4 fixed-fixture outputs reproduce the unchanged base `776752e` byte for byte (pins computed in a disposable worktree); the 38 WP-012 v0.2/v0.3 pins still pass.
  - v0.4/v0.5 normalized parity on 33 tapes outside the RETURN child.
- **Durability.** Production pack/unpack at every response stage; DB crash/reclaim at 6 stages; STEP/paced; corrupted-restore fallback; fencing via the inherited path; cross-method resume refused.
- **App and reports.**
  - Follow/live views distinguish "return reference prepared — waiting for a local recovery (no call yet, no entry)" from an entry.
  - MP-004 §7 W/P/C/R/N/I/X/A with identities, ratios, N reasons and X causes, total and monthly (child → month its WAIT opened), in JSON and Copy report for chat.
  - Read-only v0.4/v0.5 comparison with the MP-004 limitation, the response row and a *Pinned release vs current package* fact.
- **For Director decision** (evidence §7):
  - dispatch-level precedence of a local break over an earlier recovery in the same dispatch;
  - corridor/economic emptiness evaluated at the first recovery during WAIT_RESPONSE;
  - "current bar" = latest complete minute, late recovery as its own primary class;
  - live asymmetry: the bar after the live reference publication always straddles p0;
  - monthly attribution;
  - executor-derived register;
  - §6 SHORT ratio erratum (1.935, not ≈ 2.08);
  - v0.4 status label left as recorded.
- **Checks** (disposable PostgreSQL 18.6, Owner stack untouched): new pure/DB/live/browser suites all pass, plus the v0.3/v0.4 regression set (counts in the evidence and executor report). Typecheck/build pass; schema baselines are rewritten only for observe.v1 r8 and semantic.v2 r4. The full suite and Compose smoke are left to CI.
- **Owner handoff.** The continuous v0.4/v0.5 Sep–Dec comparison (35-day initialization, baseline `eval-20261007T182934-3f41ad` reused only after the pin-compatibility check) is prepared but INACTIVE. CI is Owner-operated: PENDING / NOT CHECKED.

## WP-014 correction executor evidence (base `0526641`; Astra review F1–F3 and alignments only; READY FOR DIRECTOR REVIEW — WP-014 CORRECTION ONLY; not accepted)

[Evidence §9](delivery/evidence/WP-014-ENGINEERING-EVIDENCE.md#9-wp-014-correction-astra-review-of-0526641-f1f3-and-alignments-only) · [erratum](delivery/MP-004-ERRATUM-SECTION-6-RATIOS.md). MP-004, the methodological decisions and every identity/contract/schema are unchanged. The register is accepted only for the choices Astra verified (108 inherited values unchanged, `references_per_child = 1`).
- **F1.** The local sequence is consumed by its first ordered decisive event; inherited protections still cover the whole dispatch. Recovery → violation in one dispatch: late first recovery (C=0, R=1, N=1, I=0). Violation → recovery: C. Same bar: C. The earlier test that encoded the opposite precedence is corrected.
- **F2.** `EMPTY_RETURN_CORRIDOR` and `NO_ECONOMIC_RETURN_REGION` keep their v0.4 place during WAIT_RESPONSE: after the cap updates, before the local response (X), with no reopening. An unsuitable single price with a non-empty region is N. A live temporary cost block stays non-terminal until the recovery.
- **F3.** The earlier 20-owner RETURN convention is NOT_APPLICABLE to v0.5: the count is kept, there is no substitute criterion, and the completed verdict does not depend on it. This holds in JSON, Markdown, the Workbench metric and the comparison (the candidate never inherits the baseline criterion). v0.3/v0.4 are unchanged.
- **Alignments.**
  - The late first recovery is classified OTHER_GATES, with its own reason and late count.
  - Straddling is described only as start < p0 < end (start = p0 is in the domain).
  - The WAIT-open cohort is explained in the comparison (JSON, Markdown, Workbench).
  - Separate erratum: SHORT valid 1.934932545…, insufficient 0.971777….
- **Fail-before / pass-after.** 13 of 27 new regressions fail on `0526641` (the 14 guards pass); 27/27 pass after.
- **Checks.** See evidence §9–10. The full suite and Compose are left to CI. CI is Owner-operated: PENDING / NOT CHECKED. The continuous plan stays INACTIVE.

## Owner continuous v0.5 run — descriptive acceptance and four R→N paths diagnosis (9 October 2026)

**Director decision (as relayed in the Owner assignment).** The run result is accepted as descriptive development evidence and the task below is recorded. No verbatim decision text beyond the assignment was supplied. There is no method, threshold or parameter change and no next package.
- **Run.**
  - Evaluation `eval-20261009T155751-be8b2b`, replay `obs-20261009T155751-0f255b`, build `eab7d23`.
  - Method `btc.context-action.v0.5` / `mp004.rules.v0.5`, pack `pack-1ae7d36c…`, preset `btc-2025-09-to-2025-12-continuous-init35d-v1`.
- **Recorded result (app report).**
  - COMPLETED, coverage complete, assurance PASSED 21/21.
  - 89 A confirmations and 1 call (A IMMEDIATE, TIME_EXPIRED).
  - A RETURN response: W 57, P 12, C 6, R 4, N 4, I 0, X 2, A 0.
- **Executor diagnosis** ([summary](delivery/evidence/WP-014-OWNER-V05-RN-DIAGNOSIS/SUMMARY.md) · [paths.json](delivery/evidence/WP-014-OWNER-V05-RN-DIAGNOSIS/paths.json) · [script](delivery/evidence/WP-014-OWNER-V05-RN-DIAGNOSIS/extract_rn_paths.py)). READY FOR DIRECTOR REVIEW — FOUR R→N PATHS DIAGNOSIS ONLY; not accepted.
  - **Access.**
    - Only the app's read-only GET surfaces: report, journal pages and the bar window clamped before each recovery cursor.
    - The authorized DB extraction was not used. Raw exports stay outside Git.
    - No write, replay, Deep validation, acquisition or economic run.
  - **Integrity.** The stored corridor, E0, E1, G, Q, margin, blockers and primary reason are re-derived with the pinned formulas and register, and they are equal. The pinned-cache reference bars equal the stored H0/L0/close. Local verdicts reproduce `bars_checked`. Regeneration is byte-identical.
  - **Findings.**
    - In all four paths (1 LONG, 3 SHORT; cohorts Sep 1, Nov 1, Dec 2) E0 ∩ F was already empty at the preparation. The gaps are 0.4, 143.7, 22.9 and 2.6.
    - The reference bar's favourable extreme already lay beyond E0's near edge.
    - Check 2 is not applicable, because its precondition is false.
    - Check 3 found no restriction. There is no intermediate record of the child/scenario between the preparation sequence and the terminal sequence, endpoints excluded. The geometric fields of the two snapshots are identical. The cap history is unchanged after p0, and E0/E1 recomputed equal the stored values, so E1 = E0. This holds for the geometric quantities considered and does not imply a generally unchanged context. The #4 cap revision precedes the preparation.
    - For three paths F meets the corridor and the only blocker is reward/risk. For #2 F lies wholly outside the corridor, so both blockers apply and the corridor is primary (smaller code in the same class).
  - **Reconciliation.** R = N = 4, I = 0. Blocker incidence: RR 4, corridor 1. Primary: RR 3, corridor 1. This matches the report.
- **Checks.** Dossier verifications only (re-derivations, reconciliation, reproducibility). No product suites, E2E or Compose. CI PENDING / NOT CHECKED, Owner-operated.

### Four R→N paths diagnosis — Astra documentary correction (base `cb356f2`; READY FOR DIRECTOR REVIEW — FOUR R→N PATHS DIAGNOSIS CORRECTION ONLY; not accepted)

Only the dossier, the JSON labels and the script strings were corrected, from the existing local exports. There was no new extraction, acquisition, replay, Deep validation or economic run. Counts, classifications, sums and method are unchanged; outside the restructured preparation→recovery block, `paths.json` is identical.
- **Local domain.** The two intrabar overshoots without confirmation are #4 at 16:38 and 16:39. #1 at 18:16 is a valid RECOVERY with high = H0, because contrary equality is allowed.
- **Interval.** The "(p0, recovery]" statement is replaced by: no intermediate record of the child/scenario between the preparation sequence and the terminal sequence, endpoints excluded. That absence, the comparison of the two snapshots' geometric fields, and the cap-history check with the E0/E1 recomputation are now kept as separate facts. E1 = E0 is stated for the geometric quantities considered only, not as a generally unchanged context.
- **Checks.** Artifact consistency only (regeneration byte-identical, unchanged fields compared with `cb356f2`). No product suites, E2E or Compose. CI is Owner-operated: PENDING / NOT CHECKED.

## MP-005 closure and WP-015 executive authorization — 9 October 2026

- **Methodological closure** ([MP-005-DIRECTOR-CLOSURE.md](delivery/MP-005-DIRECTOR-CLOSURE.md)). It approves MP-005 for candidate v0.6 as a delta over MP-004. It certifies no economic effectiveness or predictive quality, and alone it authorized no work.
- **Executive authorization**, a separate act recorded verbatim in [WP-015](delivery/WP-015-MP-005-IMPLEMENTATION-SPEC.md). It covers implementation and synthetic engineering checks only. It does not authorize economic runs, acquisition, Owner extraction, real-data replay or an Owner launch.

## WP-015 executor evidence (base `3c6af11`; READY FOR DIRECTOR REVIEW — WP-015 ONLY; not accepted)

[Evidence](delivery/evidence/WP-015-ENGINEERING-EVIDENCE.md) · [v0.5 base-pin generator](delivery/evidence/WP-015-V05-BASE-PINS.py).
- **Implemented.**
  - `btc.context-action.v0.6` / `mp005.rules.v0.6` (`adviser/core6.py`), selectable in the Workbench and at live Start. The default is still v0.2.
  - Only addition: right after the MP-004 preparation of the single RETURN reference, in the same dispatch, the check F ∩ C0 (∩ A0 historically).
  - Historical: F ∩ C0 = ∅ → `INITIAL_RESPONSE_INCOMPATIBLE:CORRIDOR` (economics annotated); otherwise J0 = ∅ → `HISTORICAL_ECONOMICS`.
  - Live: the CORRIDOR test only, cost-independent; the MP-004 temporary cost restriction is unchanged.
  - A single tick is non-empty. Inherited protections come first with their own reasons.
  - The child ends (P and X), never the scenario. No renewal, reopening or later C/R.
- **Identities.**
  - `adviser.core.v6`, state/runtime v6, engine `observe.stream.v7`, report `adviser.report.v6`, reconciliation v9 (same-dispatch and recomputed-compatibility checks), Deep v10; evaluator v3 reused.
  - The rules manifest covers the MP-005 delta, its closure, the MP-004 rules/closure and every earlier inherited text.
  - The register is executor-derived: every MP-004 value is kept, and only `mp005_policy` (categorical) is added.
  - semantic.v2 r5 (values only; v0.6 emits the r4 shapes) and observe.v1 r9 (method value). No migration.
- **Preservation.**
  - 68 v0.5 fixed-fixture outputs reproduce the unchanged base `3c6af11` byte for byte (pins computed in a disposable worktree). The v0.4 and v0.2/v0.3 pins pass in their suites.
  - v0.5/v0.6 normalized parity on 75 tapes outside the new terminal.
- **Durability.** Production pack/unpack around the P→X dispatch; DB crash/reclaim at 5 stages; STEP; a v0.6 run refused under v0.5; a live restart does not reopen; live tape replay is identical.
- **App and reports.**
  - The `INITIAL_RESPONSE_INCOMPATIBLE` count is a subset of X (never added again): by base, direction and WAIT-open month, ratio over P, with the declared loss of C/R classifications, in JSON, Markdown and Copy report for chat. The 20-owner criterion is NOT_APPLICABLE.
  - The UI shows *entry attempt ended — scenario not invalidated*.
  - The read-only v0.5/v0.6 comparison carries the MP-005 limitation and the subset row.
- **Fixtures.** Every MP-005 §8/§9 row (LONG/SHORT) is checked literally through the pinned functions, and every behaviour on reachable engine tapes. There is a direct live CORRIDOR terminal with a preparable reference. **No counterexample to the actual predicates** was found.
- **Checks** (disposable PostgreSQL 18.6, Owner stack untouched):
  - new suites: paths 104, versions 83, report 14, live 10, DB 11;
  - E2E: v0.6 plus the v0.5 regression;
  - the regression set, typecheck/build and schemas pass (exact counts in the evidence);
  - the full suite and Compose smoke are left to CI.
- **Owner handoff.** None prepared: this delta needs technical acceptance first. CI is Owner-operated: PENDING / NOT CHECKED.


### WP-015 correction F1 (base `18f670a`; READY FOR DIRECTOR REVIEW — WP-015 CORRECTION ONLY; not accepted)

- The v0.5/v0.6 comparison limitation `V06_MP005_INITIAL_RESPONSE_INCOMPATIBILITY_DELTA` no longer claims that an ended child frees the slot or changes later selections/outcomes (WAIT_RESPONSE does not hold the slot; MP-005 neither ends a call nor releases the structural owner). It keeps the C/R loss and the statement that the new counts show no informational or economic improvement. JSON and Markdown/Copy carry the same constant.
- Kernel, method, register, identities and contracts unchanged. New targeted regression; fails on the base text.
- Checks: pure report/comparison tests only (48 + 6 passed). No full suite, E2E, DB or Compose. CI Owner-operated: PENDING / NOT CHECKED. [Evidence §8](delivery/evidence/WP-015-ENGINEERING-EVIDENCE.md).

## MarketView +1h vs persistence — feasibility check (base `b47b997`; READY FOR DIRECTOR REVIEW — FEASIBILITY ONLY; not accepted)

[Evidence](delivery/evidence/MARKETVIEW-PERSISTENCE-FEASIBILITY.md). The comparison result was not computed. Method v0.6 frozen; no product, schema or method change.
- **Access.** Repository code and the existing local GET exports of `eval-20261009T155751-be8b2b` only (hashes equal the R→N dossier inputs). No app GET call, DB access, price-cache copy, replay or network.
- **Finding.** Each hourly sample is a stored `view_sample` record with view, conditional flag, principal scenario, anchor, `outcome_1h/4h`, persistence (FLAT explicit) and activation flags. Those records sit only in `adviser_evaluation_records`: no GET surface or local export exposes them, and the report's persistence aggregate is unpaired. Activation time, owner and terminals can be derived through `scenario_id` from the local scenario journal. The stored flags alone mix already-active with newly activated cases.
- **Recommendation: B.** Possible with declared limits, after the Director authorizes a single read-only extraction of the run's 2928 `view_sample` rows (or a GET export, which is a scope change). No prospective data is missing.
- **Checks.** None beyond hash verification of the local exports; no suites. CI is Owner-operated: PENDING / NOT CHECKED.

## MarketView +1h vs persistence — descriptive tabulation (base `11a74b6`; Director descriptive closure at `ced7b2f`)

**Director (as relayed by the Owner):** descriptive closure of the tabulation at `ced7b2f`, with a correction of the chain wording only. Counts and conclusions are unchanged. The executor checks below are distinct from the Director's independent review.

[Summary](delivery/evidence/MARKETVIEW-PERSISTENCE-TABULATION/SUMMARY.md) · [tabulation.json](delivery/evidence/MARKETVIEW-PERSISTENCE-TABULATION/tabulation.json) · [samples.csv](delivery/evidence/MARKETVIEW-PERSISTENCE-TABULATION/samples.csv) · [script](delivery/evidence/MARKETVIEW-PERSISTENCE-TABULATION/tabulate_view_persistence.py). Run v0.5 only; no v0.6 equivalence. Method and product unchanged.
- **Access.**
  - One authorized REPEATABLE READ READ ONLY transaction on the run's `view_sample` rows, snapshot `965478:965478:`. The Owner started the DB container.
  - The local scenario journal and the report export were used for links and cross-checks. The raw export is outside Git.
- **Integrity.**
  - 2928/2928 rows on the hourly grid, unique, digests recomputed equal.
  - Executor chain checks: 2927 successful checks, made of 2926 links between extracted records and one check from the initial seed; one link is not verifiable. The full chain and the finish commitment are not verified here; the app's 21/21 assurance is reused by provenance only.
  - Report aggregates equal.
- **Result (descriptive).**
  - 158/2928 samples are directional. All have an endpoint and persistence, with no FLAT, so the paired set is all 158.
  - Paired cells: both 41, MarketView only 36, persistence only 45, neither 36. MarketView matches 77/158, persistence 86/158.
  - The samples come from 99 distinct scenarios (owner = scenario for A; no shared box for B/C), median 1 and max 6 samples per scenario.
  - Antecedent at +1h: already active 94, activated within +1h 38, not activated 26.
  - No significance test, no thresholds, no subgroup search. No economic or independent validation: Sep–Dec is exposed development.
- **Checks.** Integrity/reconciliation in the script and byte-identical regeneration; no product suites. CI is Owner-operated: PENDING / NOT CHECKED.
- **Documentary correction after closure.** Chain wording only, in SUMMARY, this STATE section, and the identical `chain_scope` string of the script and `tabulation.json`. No new extraction, data regeneration, product suite or Owner activity; counts and conclusions unchanged. CI is Owner-operated: PENDING / NOT CHECKED.

## RP-001 hourly directional persistence — protocol approved and registered (10 October 2026)

- **Registered texts.** [Protocol](delivery/RP-001-HOURLY-DIRECTIONAL-PERSISTENCE.md) and the separate [Director decision](delivery/RP-001-DIRECTOR-CLOSURE.md), both verbatim from the relayed authoritative text. The decision approves the protocol for methodological registration only. It adds one operational convention, a fixed bootstrap seed 0, which changes neither the hypothesis nor the reading criterion.
- **Status.**
  - Protocol approved and registered.
  - RP-001 execution: **INACTIVE**.
  - The verification window is not yet identified or authorized.
  - v0.6 stays frozen.
  - January–August 2026 stays protected.
- **Not authorized.** No exploratory computation, window selection or opening, acquisition, DB/Owner access or product change. The decision notes that the 2928 already-extracted samples suffice for the exploratory tabulation, without a new certification of prices or original availability.
- **Identifier note (unresolved, for the Director).** The identifier RP-001 is already used by the historical first-trader research ([research/RP-001-FIRST-TRADER-FORMALIZATION.md](research/RP-001-FIRST-TRADER-FORMALIZATION.md); "RP-001 findings" in FOUNDATION §3). The new files have distinct names and nothing was overwritten. References to the new protocol should name it in full ("RP-001 — Persistenza direzionale 1h → 1h").
- **Executor checks.** Documentary fidelity and links only. No product suites. CI is Owner-operated: PENDING / NOT CHECKED.
