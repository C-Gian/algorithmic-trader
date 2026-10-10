# Live call history in the live cockpit — engineering evidence

Base `6710474bcab32ea4be8a96d258594d7a1b79ec3f` (`main`). READY FOR DIRECTOR REVIEW — LIVE CALL HISTORY ONLY; not accepted. Product change only; v0.6 and HDP-001 frozen, studies INACTIVE.

## Preliminary compatibility check

- `src/algotrader/adviser/live.py`: `LiveStore.save` writes the core journal (`call`, `call_revision`, `material_change`, …) with `_outputs` into `adviser_journal` under `run_id = epoch.run_id`, in the same fenced transaction as the session view. The view exposes the same `run_id` (`LiveSession.view`). A continuity run can span several sessions: a restart within 96 h resumes the same run, and the restart-gap terminal is written by the later session.
- `src/algotrader/adviser/api.py` `call_detail` (`GET /api/adviser/runs/{run_id}/calls/{call_id}`) is generic over the run id. It filters `run_id` plus `subject/record_id = call_id` and returns `revisions` in `seq` order. It only reads `adviser_journal` and `adviser_evaluation_records`; the latter are absent for live runs, so no evaluator data is required.
- Record identity is therefore **continuity run + call id**. The journal carries no session id, so the session is shown as context: the session that showed the call when the history was opened.
- **Compatible.** No new event, persistence, migration, API or method change was needed.

## Chosen path

- `web/src/views/AdviserResult.tsx`: the existing *Guidance revisions* list is extracted as `RevisionList`. The historical call detail renders the same markup as before. `detail` mode adds the stored revision values with full UTC times.
- `web/src/views/LiveCallHistory.tsx` (new) is a read-only *Call history* card keyed by run + call:
  - **Identity.** The card is remounted per identity, every response is dropped after a selection change, and only data loaded for exactly that key are rendered. A response whose call or revisions belong to another call is an error and nothing from it is shown.
  - **Content.** The call record at issue, then the revisions in recorded order. Status is CURRENT (from the live view), NOT CURRENT, TERMINAL (no entry available now; earlier revisions are history only), or not the call shown / another continuity run. No-revision, partial (missing revision numbers, or live view newer than loaded), missing (404) and load-error states are distinct. A notice appears when the live session changed since opening.
  - **Refresh.** Reloads happen only when the cockpit's existing poll shows a new revision or terminal of that call, or on the manual Reload; there is no timer of its own.
  - **Limits.** No hypothetical path, no computed differences and no reconstructed reasons; the card states that it implies no Owner entry.
- `web/src/views/LiveCockpit.tsx`: *Show this call's recorded history (rN)* in the call panel and *history* on terminated calls in *What changed*. The selection is fixed to the run, call and session at opening.
- `web/src/adviser.ts`: optional stored fields typed (`changed`, `current_admissible_bounds`, `entry_status`/`thesis_status` at issue). `web/src/styles/adviser.css`: 5 lines for the detailed revision rows.

## Checks actually run

All on the disposable PostgreSQL 18.6 container `livehist-pg-disposable` (127.0.0.1:55446), removed afterwards. The Owner stack was not touched. No live feed, Owner data or network.

| Check | Result |
|---|---|
| `npm run build` (tsc typecheck + vite build) | pass |
| `tests/test_live_call_history_db.py`: synthetic journal across two runs and three calls; plus a real live-worker journal (offline OKX fake) across a stop and a restart in the same run | 2 passed |
| `tests/e2e/test_live_call_history_e2e.py` (Playwright, built UI, synthetic route-mocked payloads) | 2 passed |
| Regression: `test_adviser_e2e` (historical call detail / *Guidance revisions*), `test_live_presentation_e2e` (4 cockpit presentation cases), `test_ui_smoke::test_shell_market_overview_is_default_honest_and_navigable` | 7 passed |

The DB tests check:
- identity isolation, including the same call id in another run;
- recorded order and stored values, including the terminal and its reason;
- no-revision and 404 cases, and no hypothetical paths;
- the cockpit `run_id` equals the journal `run_id`;
- the history of a real call across sessions;
- an unchanged checksum of all seven `adviser_*` tables across every read.

The E2E test checks:
- identity, order, UTC times and stored values;
- exactly one refetch on a new revision and none over three unchanged polls;
- not-current and terminal states;
- a held response released after a call switch, never shown;
- session change and run change;
- no-revision, partial, missing, error and foreign-response states;
- GET-only requests;
- at 390 px, the panel adds no horizontal overflow.

## Correction — revision labels (base `3a8f783`)

Director finding: past revisions in the live card used the present-tense labels "Entry valid now" / "Entry closed now", so the terminal screen still showed "Entry valid now" on an earlier revision.
- **Fix.** `RevisionList` in `detail` mode (live history only) now labels the recorded state at that revision: "Entry available at this revision", "Entry closed at this revision", "Entry not verifiable at this revision". Current availability stays only in the status banner.
- **Unchanged.** The historical call detail keeps its labels and markup. No method, API or persistence change.
- **Checks.** `npm run build` passed. `test_live_call_history_e2e` 2 passed: after the terminal, the old AVAILABLE revision remains readable as "Entry available at this revision" with no "now" in the revision list. Regression `test_adviser_e2e` (historical panel) 2 passed. Both ran on a fresh disposable PostgreSQL, removed afterwards. Screenshots regenerated; the terminal one shows the corrected labels.

## Synthetic screenshots

[current](live-history-1-current.png) · [terminal](live-history-2-terminal.png) · [other run / session changed](live-history-3-other-run.png) · [partial](live-history-4-partial.png) · [error](live-history-5-error.png) · [phone](live-history-6-phone.png).

## Residual limits

- Material-change summaries and candidate/scenario records are not shown in the live card; the revisions carry the guidance and reasons.
- The partial check sees only revision-number gaps and a live view newer than the loaded records.
- Pre-existing, not caused by this change: at 390 px the cockpit's v0.6 method badge in the top bar already overflows horizontally. It is left as is because restyling was not authorized.
- The *history* entry point on terminated calls in *What changed* uses the same handler as the call-panel button but is not clicked in the E2E test.
- No runtime check against a real live session or Owner data. Comprehensibility is not attested by these checks.
- Remote CI: PENDING / NOT CHECKED.
