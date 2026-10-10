# Live entry availability — technical continuity check (evidence)

Base `09951a72d7c75d4747b9f3c750643f047cbc1449` (`main`). Verification only: no method, API, persistence or UI change. Synthetic offline fakes, disposable PostgreSQL; no real feed, Owner data or economic replay. v0.6 and HDP-001 frozen; evaluations INACTIVE. READY FOR DIRECTOR REVIEW — LIVE CONTINUITY CHECK ONLY.

## Expected behaviour (frozen rules and code)

- **Quote freshness.** A live call's side price is the measured public quote. A quote older than `fresh_quote` (MP-001 `live_quote_seconds` = 5 s, `delivery/MP-001-PARAMETERS.json:150`) makes `AdviserCore._quote_state` return STALE, and `_side_price` returns the blocker `QUOTE_STALE` (`src/algotrader/adviser/core.py:1001`, `:1542`). The entry-status rule then gives **UNVERIFIED**, because only quote or connection reasons remain (`UNVERIFIED_REASONS`, `core.py:56`; `core.py:1795–1820`; same rule in `core3.py:1470–1490`, inherited by v0.4–v0.6). The result is a `call_revision`, plus an `ENTRY_UNVERIFIED` material change that is alertable when the previous state was AVAILABLE. The thesis is not judged by it.
- **Detection.** The worker's `_live_loop` calls `sess.tick(now)` every tick, even with no input (`live.py:924`), so the timer fires without new data. The view is saved with the journal every `save_seconds` (`live.py:952`).
- **API.** `live_status` serves the saved view, and `present()` (`api.py:30`) masks a saved AVAILABLE only when the session is not current. A stale quote inside a current session is served as recorded: UNVERIFIED with `QUOTE_STALE`.
- **Longer silence.** With no complete 1m bar for more than `trade_1m_seconds` = 120 s, the call ends UNASSESSABLE (`core.py:1773`).
- **Disconnect.** A taped disconnect gives `CANDLE_CONNECTION_LOST`, and later `…AWAITING_FRESH_BAR`.
- **Resumption.** It re-evaluates the frozen rule; AVAILABLE is never implied.

## Existing coverage reviewed (reused, not re-run)

| Layer | Test | Covers |
|---|---|---|
| service (in-memory) | `test_adviser_live.py::test_quote_expiry_after_five_seconds_without_new_input_marks_entry_unverified` | AVAILABLE → UNVERIFIED `QUOTE_STALE` after 5 s without input; one alert |
| service | `test_adviser_correction_live.py` (disconnect, reconnect + fresh bar, silent socket > 120 s, Owner stop) | connection reasons, reopening only per rule, UNASSESSABLE |
| API presentation | `test_adviser_correction_live.py::test_non_current_sessions_never_present_a_usable_entry`, `test_live_presentation_e2e.py` | a non-current session never presents a usable entry (fabricated rows) |
| worker + API + cockpit | `test_adviser_e2e.py::test_owner_starts_the_live_adviser…` | a call is shown and a withdrawal alert appears; **no** controlled interruption, reload or resume, and no cockpit assertion during unavailability |

**Missing coverage:** the full path through the real worker, the served API state and the real cockpit across an interruption, a reload and a resume. I added one synthetic E2E in the existing framework.

## Check added and run

`tests/e2e/test_live_continuity_e2e.py`. It reuses the same in-process live worker and scripted WebSocket, REST and ticker fakes as `test_adviser_e2e` (`test_adviser_live_db`), the E2E `Stack`, and the built cockpit. Method v0.2, the cockpit default with this fixture; the quote rule is shared by every version.

1. **AVAILABLE.** The API serves call `…5e9629dcc808` r2 AVAILABLE, admissible 100238.3–100245.7. The cockpit shows AVAILABLE, the band in the panel and the band in the chart.
2. **Interrupted updates.** The scripted candle pushes and ticker quotes stop; the fake quote source offers a quote only with a push. The socket stays open and the worker keeps heartbeating; only the worker clock advances, to 8 s after the last quote.
   - The backend detects it through the freshness timer: same call at r3, **UNVERIFIED**, `["QUOTE_STALE"]`, thesis ONGOING.
   - The session stays LIVE and current, and no `NOT_CURRENT` mask is applied.
   - The cockpit shows UNVERIFIED with the QUOTE consequence; no admissible row, no chart band, no "Ingresso disponibile" headline.
3. **Reload during the interruption.** The panel states rendered after the reload (sampled every 25 ms) were `NO_VIEW → UNVERIFIED`; **AVAILABLE never appeared**. No band, and the API was still UNVERIFIED.
4. **Resumption.** The next scripted minute arrives, with its quote at 05:23:00.5. The backend establishes r4 **CLOSED**, `PRICE_OUTSIDE_STRUCTURAL_AREA`; it does not return to AVAILABLE. The cockpit equals the backend state: CLOSED, reason "prezzo fuori dall'area d'ingresso", no band.

**Result:** 1 passed (28 s), run twice. Recorded facts are in `e2e-live-continuity.json`; screenshots are `continuity-1-available.png`, `continuity-2-unverified-after-reload.png` and `continuity-3-after-resume.png`. `npm run build` passed. No other suite was re-run, since no product code changed.

## Findings (reported, not corrected)

1. **Reproducible: obsolete AVAILABLE wording outside the main panel.**
   - **What.** While the call is UNVERIFIED, including after the reload, the cockpit's "N new changes" banner shows up to three unacknowledged alerts without timestamps (`LiveCockpit.tsx:208–210`). The *What changed* timeline does the same, with times.
   - **Which text.** Both still show the earlier `ENTRY_REOPENED` summary "Entry still valid now inside the admissible part of 100238.3–100245.7; stop …, target …". The `NEW_CALL` summary "entry available inside …" also stays.
   - **Source.** The summary is the guidance text frozen at that revision (`core.py` `_material`).
   - **Effect.** The main panel is correct, but an old present-tense AVAILABLE sentence with a range remains on screen until it is dismissed. The banner lists the newest alert first. The recorded `alerts_banner` field in `e2e-live-continuity.json` reproduces it.
2. **Minor, transient.** After a reload and before the first poll answers, the cockpit renders its defaults: the panel shows NO_VIEW "Nessuna valutazione in corso" (observed). From the code, the state badge reads "Stopped" (`state = st?.state ?? "STOPPED"`), with the message "Loading…". AVAILABLE is never shown.

## Limits

- **Clock.** The time is fake (`FakeClock`); only the 5 s rule was exercised.
- **Not exercised in this E2E.** Socket disconnect, a silent feed beyond 120 s, worker death (heartbeat/lease → UNRESPONSIVE mask) and a stopped session. These are covered at service and presentation level by the tests listed above.
- **Production latency (from code settings, not measured).** The CLI worker runs with tick 1 s and save 2 s, and the cockpit polls every 1.5 s. After the last quote, the cockpit can keep showing the authoritative AVAILABLE for about 5 s plus up to ~3.5 s of save and poll delay before UNVERIFIED appears.
- **Timeline timestamps.** The alert `created_at` uses the database wall clock, so it differs from the fixture's market clock.
- **CI.** Remote CI: PENDING / NOT CHECKED.
