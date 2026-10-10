# Live cockpit — historical alerts vs current availability (evidence)

Base `f62aa63` (`main`). Presentation-only correction of stored alerts in the cockpit's unread-alerts banner and *What changed* timeline, authorized by Astra (relayed by the Owner, 10 October 2026). No method, API, persistence, record rewrite, frontend availability inference or new alert expiry. Workbench, Owner data, real feed and economic replay untouched. v0.6 and HDP-001 frozen; evaluations INACTIVE. READY FOR DIRECTOR REVIEW — HISTORICAL ALERTS PRESENTATION ONLY.

## 1. Defect verified at the base

`test_live_continuity_e2e` run unchanged on the base build (disposable PostgreSQL), call `…5e9629dcc808`:
- **UNVERIFIED (r3, `QUOTE_STALE`), after reload.** The banner read "4 new changes" with, among others, `ENTRY REOPENED — Entry still valid now inside the admissible part of 100238.3–100245.7; stop 100226.5, target 100798.5, hard deadline …`, without a time. The timeline also listed `NEW_CALL` "New LONG call (A): entry available inside 100238.3–100245.7, …".
- **CLOSED (r4).** UNVERIFIED → CLOSED is recorded but not alerted, so the same stored alerts stayed listed. The extended test below fails on the base build at its first UNVERIFIED check (no historical-alert presentation exists).

The source is the guidance text frozen in each `material_change` (`core.py` / `core3.py` `_material`) and stored in `adviser_alerts.summary`. It is correct as history; only the presentation treated it as current.

## 2. Correction (frontend only)

`web/src/views/LiveCockpit.tsx`, `web/src/lib/format.ts`, `web/src/styles/adviser.css`. Each stored alert, in the banner (three newest unread) and in the timeline, is rendered by one shared component:
- **When.** `created_at`, the time the alert was recorded, in local time with an identifiable zone (e.g. `10/10/2026, 18:16:25 CEST`). A missing or unreadable value shows **"Orario non registrato"**; the page's own clock is never used (`fmtRecorded`).
- **What happened.** A past-tense Italian headline chosen only from the recorded `change_type`:
  - `NEW_CALL`: "Il sistema ha emesso una nuova call."
  - `ENTRY_REOPENED`: "Il sistema ha segnalato che l'ingresso era di nuovo disponibile."
  - `ENTRY_WITHDRAWN`: "Il sistema ha segnalato che l'ingresso non era più disponibile."
  - `ENTRY_UNVERIFIED`: "Il sistema ha segnalato che la disponibilità dell'ingresso non era confermabile."
  - `TERMINAL`: "Il sistema ha segnalato la conclusione della call."
  - any other type: a neutral "registered change" sentence with the type.
- **Original text.** Verbatim, collapsed under **"Testo registrato a quell'ora"**, followed by: "Fasce d'ingresso, livelli e scadenze in questo testo si riferiscono a quell'evento passato: non indicano un ingresso utilizzabile adesso."
- **Pointer to current state.** The banner (title "N avvisi registrati non ancora letti") and the timeline state that alerts are past events and that current availability is read in the main panel «Che cosa propone il sistema adesso», which keeps reading the authoritative backend state (unchanged).
- **Kept.** `dismiss` (acknowledgement) per alert in the timeline; banner selection (unread, newest three); non-alert timeline rows (call conclusions, session notes) unchanged.

## 3. Verification — `tests/e2e/test_live_continuity_e2e.py` (reused, extended)

Same in-process live worker, scripted WebSocket/REST/ticker fakes and E2E stack. The new helper `_check_historical_alerts` runs at four points: UNVERIFIED before reload, UNVERIFIED after reload, CLOSED before reload and CLOSED after a new reload (step 5). Each time, for both banner and timeline, it checks:
- the main panel's `data-state` equals the API `entry_status`;
- the pointer to the main panel is present;
- the rendered text contains no "Entry still valid now", no "entry available inside" and no admissible-band value;
- for every alert item, matched to the API alert by key:
  - the change type;
  - the time equals the browser's local rendering of the stored `created_at`;
  - the past-tense headline for that type;
  - the disclosure label;
  - the hidden original text equals the stored summary verbatim.

It then opens the ENTRY_REOPENED disclosure: the original "Entry still valid now …" is readable together with the past-event qualification, and the panel state is unchanged. Step 6 is presentation only: a routed response with `created_at` removed gives "Orario non registrato" on every alert. The earlier assertions (no AVAILABLE rendered after the reloads, no band, CLOSED `PRICE_OUTSIDE_STRUCTURAL_AREA` after resume) are kept.

**Fixture scope.** Method v0.2 is the cockpit default with this fixture. The banner, timeline and main panel it exercises are the components shared by every method version. The test does not certify v0.6 behaviour and was not extended to it.

## 4. Results

- Fail-before: the extended test on the base UI build: 1 failed, at the first UNVERIFIED check.
- Fixed-after: `test_live_continuity_e2e` 1 passed, run twice (31 s, 36 s).
- Regression (cockpit components touched): `test_live_presentation_e2e`, `test_live_proposal_e2e`, `test_live_call_history_e2e` 7 passed; shell smoke `test_shell_market_overview_is_default_honest_and_navigable` and `test_adviser_e2e` 3 passed.
- `npm run build` (includes `tsc` typecheck) passed.
- All on the disposable PostgreSQL 18.6 container `hist-alerts-pg-disposable` (127.0.0.1:55447), removed afterwards; the Owner stack was not touched. No non-E2E suite run (no Python product code changed). CI: Owner-operated, PENDING / NOT CHECKED.

Synthetic screenshots (fixture, not live market data): `continuity-1-available.png`, `continuity-2-unverified-after-reload.png`, `continuity-3-after-resume.png`, `continuity-4-closed-after-reload.png` (ENTRY_REOPENED original text opened), `alerts-banner-closed.png`, `alerts-timeline-closed.png`. Recorded facts: `e2e-live-continuity.json`. The earlier `LIVE-CONTINUITY/` evidence is left unchanged.

## 5. Limits

- `created_at` is the database time at which the alert was recorded, not the market clock of the change. In this fixture the two differ (2026 wall clock vs 2025 fixture market time), and the timeline's non-alert rows still show their own UTC times (pre-existing).
- Alerts recorded within the same second keep the API's order (pre-existing).
- The original texts stay in English (they are stored records).
- The transitional "Stopped / Loading…" before the first poll is out of scope and unchanged.
- No real live-session or phone-width check of the new rows.
