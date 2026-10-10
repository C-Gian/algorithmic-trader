# Live cockpit — updates of one call (synthetic comprehension episode; note for the Director)

Base `2159ef6c2b25d6b0a5d2e4776981653101869b76`. Evidence only: no product, UI, method, API or persistence change. Synthetic engineering inputs, not market data; no Owner data, live feed, order or economic replay. v0.6 and HDP-001 frozen; studies INACTIVE.

## Identity

| | |
|---|---|
| Method | v0.6 (`btc.context-action.v0.6` / `adviser.core.v6`), live profile, mocked services |
| Run (continuity epoch) | `live-20250828T0316-62d8c8`; the suffix is generated on each execution |
| Session (display) | `demo-synthetic-session` |
| Scenario | `AL-2025-09-01T03:15:00+00:00-d49a8b5618ff` (A LONG) |
| Call | `call-AL-2025-09-01T04:07:01+00:00-05a41e24819a`, RETURN entry |
| Call record | Issued 2025-09-01T04:07:01Z. Structural area 99900–100049.9, admissible 99900–100014.5, target 100700.0, stop 99700.0, hard deadline 08:02:01Z. |

**Inputs and what was adapted.**
- Tape: the existing MP-005 L1–L3 LONG tape of `tests/test_mp005_live.py`.
- Minimal adaptation:
  - three later minutes (closes 100100 and 100300, then a high of 100720);
  - the last close re-quoted every 4 s between minute closes. The existing feed quotes once a minute, so the 5 s freshness rule would otherwise interleave `QUOTE_STALE` revisions.
- No rule or engine change.

**How the views were produced.** The three screenshots are successive views of **one** session, run and call. Each passes through the real `live_status` boundary and is rendered by the current cockpit components. For the history card, the session's journal is inserted as produced into the disposable database and served by the real `GET /api/adviser/runs/{run}/calls/{call}`. The only addition is the "Dimostrazione sintetica" label.

## Recorded sequence (UTC)

| Rev | Published | entry_status | Reasons | thesis_status | Recorded guidance |
|---|---|---|---|---|---|
| r0 (call) | 04:07:01 | AVAILABLE | — | ONGOING | "Entry still valid now inside the admissible part of 99900–100049.9; stop 99700.0, target 100700.0, hard deadline 2025-09-01T08:02:01+00:00." |
| r1 | 04:08:00.5 | CLOSED | PRICE_OUTSIDE_STRUCTURAL_AREA, REWARD_RISK_BELOW_MINIMUM | ONGOING | "Thesis ongoing but new entry is closed now (…). If following this call: hold with stop 99700.0, target 100700.0." |
| r2 | 04:10:00.5 | CLOSED | AT_OPPOSING_AREA, NO_ROOM_AFTER_COSTS, PRICE_OUTSIDE_STRUCTURAL_AREA | ONGOING | the same form, with these reasons |
| r3 | 04:10:01 | CLOSED | THESIS_TERMINAL | TARGET_REACHED | "Target reached: the call's guidance is complete." (terminal reason `CERTIFIED_TARGET_CONTACT:…obs@2025-09-01T04:09:00Z`) |

Alertable material changes: `NEW_CALL` 04:07:01, `ENTRY_WITHDRAWN` 04:08:00.5, `TERMINAL` 04:10:01. No `QUOTE_STALE` revision occurs. The generator asserts:
- the same run and call in all three views;
- the second view is CLOSED with ONGOING thesis, not UNVERIFIED;
- the call has left the current view at the third moment, with `TARGET_REACHED` among the recent calls.

## What each view shows

Times in the interface are local time (CEST); the codes and UTC times are in the details.

**[1](1-ingresso-disponibile.png) — 04:07:01.5, r0.**
- *Visible in the panel:* "Ingresso disponibile secondo il sistema"; LONG and its sentence; the admissible band 99900 – 100014.5; target, stop, deadline, horizon 30–180 min; thesis "ancora valida".
- *Banner:* one recorded event, "Il sistema ha emesso una nuova call."
- *Only in Approfondimenti:* the system text (the English guidance above), the code AVAILABLE, the structural area, the issue price 100012, the minutes left, revision r0, and the link to the history.

**[2](2-ingresso-chiuso-tesi-aperta.png) — 04:08:01.5, r1.**
- *Visible:* "Ingresso non più disponibile"; the reason "prezzo fuori dall'area d'ingresso; rapporto rendimento/rischio sotto il minimo"; target, stop, deadline, horizon; thesis "ancora valida". No admissible band.
- *Banner:* two recorded events, the newest "Il sistema ha segnalato che l'ingresso non era più disponibile."
- *Only in Approfondimenti:* the system text, including "If following this call: hold with stop …, target …"; the codes `CLOSED · PRICE_OUTSIDE_STRUCTURAL_AREA, REWARD_RISK_BELOW_MINIMUM`; the structural area; and "Ultima fascia calcolata (non utilizzabile ora)".

**[3](3-conclusione-storico-della-call.png) — 04:10:01.5, after r3. History opened with the existing "history" button in *What changed*.**
- *Main panel (current state):* "In attesa — nessun ingresso proposto"; expected direction Rialzo (conditional), with the same A LONG scenario still confirmed (destination 100900, invalidation 99700.0); "Ultima indicazione: LONG A, conclusa — target raggiunto (06:10:01 CEST)".
- *Banner (past events):* the call's conclusion, the entry no longer available, and the new call.
- *History card:* it states "Terminal — Target reached. No entry is available from this call now; earlier revisions are history only". It then shows the call record at issue and r1–r3 with UTC times, "Entry closed at this revision", entry and thesis codes, reasons, terminal reason, "Admissible then", and the recorded guidance verbatim (English).
- *Timeline:* an extra row, "04:10:01 LONG A Target reached · Certified target contact".

## Observed, not changed

- The timeline's call-conclusion row shows a UTC time without a zone ("04:10:01"), next to the alert rows in local time with a zone.
- The recorded system texts stay in English.

## Regenerate

Disposable PostgreSQL and a built UI (`cd web && npm run build`):

```text
ALGOTRADER_TEST_DATABASE_URL=postgresql://<user>:<pw>@127.0.0.1:<port>/postgres \
  uv run python delivery/evidence/LIVE-CALL-UPDATES-EPISODE/generate_episode.py
```

Since the second correction below, it writes the `*-prospettive.png` files and `episode-prospettive.json`; the `*-dopo-correzione` files of the first correction stay as recorded at `a0d6029`. The screenshots and `episode.json` of the guided test above are kept as recorded at `3b10e1a`. The run id suffix changes; the states, times and call id do not. Remote CI: PENDING / NOT CHECKED.

## Correction after the guided test (base `3b10e1a`)

**Guided test with Gian.** This is a guided test of one synthetic episode, not a general usability validation and not evidence of the method's effectiveness.
- At **CLOSED + ONGOING** he understood that there was no new entry, but inferred "I keep holding" from the thesis without opening the details.
- At **TARGET_REACHED** with the scenario still bullish, he read the expected direction as a reason to keep the earlier operation.

**Change.** Live cockpit main panel only: `web/src/views/LiveProposal.tsx`, plus two CSS rules. No method, API, persistence or Workbench change.
- **Two groups.**
  - "Disponibilità di un nuovo ingresso": the headline state; the admissible band, or the recorded reason, or the UNVERIFIED consequence, all unchanged.
  - "Aggiornamento della call già emessa": direction, the call's target, stop, deadline, horizon and thesis.
- **Call still present.** The system text recorded for the call is shown in the panel verbatim, attributed: "Testo del sistema per questa call, alla valutazione del <local time> — originale, non tradotto".
  - Nothing is derived from `thesis_status`.
  - A missing text is declared as missing.
  - In a non-current session the saved text is not shown as current.
- **Concluded call.** A separate "Aggiornamento della call già emessa" block, placed before "Lettura attuale del mercato", shows:
  - the conclusion and time, and the recorded reason (`CERTIFIED_TARGET_CONTACT` → "contatto certificato con il target operativo della call");
  - for TARGET_REACHED, the call's **operational target** (100700.0), shown apart from the scenario's destination (100900, "non è un target operativo");
  - the closing text recorded at the conclusion, verbatim, with its time;
  - "La lettura attuale del mercato qui sotto è una valutazione nuova: non estende la call conclusa."

  The target and closing text are read from the existing read-only `GET /api/adviser/runs/{run}/calls/{call}`. When it is unavailable, both are declared not available and never rebuilt.
- **Kept.** The details, the technical codes and the call history.

**Screenshots** (same episode and states; run id `live-20250828T0316-a9c168`; [facts](episode-dopo-correzione.json)):
- [1](1-ingresso-disponibile-dopo-correzione.png) AVAILABLE r0;
- [2](2-ingresso-chiuso-tesi-aperta-dopo-correzione.png) CLOSED r1 with the thesis ONGOING;
- [3](3-conclusione-storico-della-call-dopo-correzione.png) TARGET_REACHED, with the history opened.

**Checks.**
- The generator asserts, per moment:
  - the panel shows the recorded text verbatim;
  - no hold/exit wording appears ("mantieni", "mantenere", "esci", "uscire", "chiudi la posizione");
  - for moment 3, the concluded block's target is 100700.0, its closing text is the recorded r3 guidance, its terminal is `TARGET_REACHED`, and the scenario destination stays labelled "(non è un target operativo)".
- `tests/e2e/test_live_proposal_e2e.py` was extended:
  - CLOSED shows the recorded text with no hold/exit wording, and an empty text is declared;
  - a concluded call whose history is not stored declares its text and target as not available;
  - a non-current session never shows the saved text as current;
  - AVAILABLE and UNVERIFIED keep their existing assertions.
- Cockpit E2E (proposal, presentation, call history, continuity, adviser): 10 passed on a disposable PostgreSQL, removed. Build and typecheck passed.

**Limits for the Director.**
- **English, untranslated.** The recorded texts stay in English and untranslated. A translation of "If following this call: hold with stop …" would be an interpretation, so the original is shown and attributed. That recorded text itself contains "hold"; the panel adds no hold or exit wording of its own.
- **Time shown with the text.** It is the view's evaluation time. The revision's publication time is in the call history.
- **Concluded block.** It shows the latest concluded call of the run in `recent_calls`, whatever its age.
- **Not changed.** The timeline's conclusion row still shows a UTC time without a zone.

## Second correction — two perspectives and plain-Italian guidance (base `a0d6029`)

**Guided test, again.** Gian still read mainly "Ingresso non più disponibile". With a LONG already open, he read the bullish expectation as a reason to keep it, without understanding the guidance. This is a guided test only, not a general usability or effectiveness validation.

**Change.** Main panel only (`web/src/views/LiveProposal.tsx`). No method, API, persistence, Workbench, layout or palette change.
- **Two hypothetical perspectives, equally legible.** Each has the same section-title and headline styles. A line states "Due prospettive ipotetiche: l'app non sa se hai aperto un'operazione."
  - *"Se non hai ancora aperto un'operazione"* shows the authoritative availability, as before. CLOSED now reads **"Ingresso non disponibile adesso"**, no longer "non più".
  - *"Se hai già aperto un'operazione su questa call"* shows, in plain Italian, only what a **recognised** recorded system text says.
- **Presentation translation (`readGuidance`).** It recognises exactly the texts the engine writes (`core.py` `_entry_guidance` / `_terminal_guidance`) and takes the values from the text itself.
  - CLOSED, "If following this call: hold with stop X, target Y." → "Il sistema indica di mantenere l'operazione con stop 99.700 e target 100.700."
  - AVAILABLE and UNVERIFIED entry texts → their content, plus "Non contiene un'indicazione specifica per chi ha già aperto."
  - TARGET_REACHED → "Target della call raggiunto: l'indicazione è conclusa."
  - The INVALIDATED, TIME_EXPIRED, UNASSESSABLE and RETIRED texts → "per chi segue questa call il sistema indica l'uscita", because those texts say "exit guidance if following this call".
  - Any other text: "Testo del sistema non riconosciuto: nessuna indicazione operativa è mostrata." A missing text: "Il sistema non ha registrato un testo…".
  - Nothing is derived from ONGOING, the expected direction or the levels.
  - The original stays in Approfondimenti ("Testo del sistema"); for a concluded call it is in a collapsed "Testo originale registrato".
- **Concluded call.**
  - The follower perspective states the recognised conclusion and the recorded reason.
  - For TARGET_REACHED, the call's target is shown as "100700.0 — raggiunto".
  - "La successiva aspettativa (rialzo) non prolunga questa call: è una valutazione nuova del mercato." This comes before "Lettura attuale del mercato".
  - No close order appears unless the recorded text gives one.

**Screenshots** (same episode, run `live-20250828T0316-60b093`, [facts](episode-prospettive.json)):
- [1](1-ingresso-disponibile-prospettive.png);
- [2](2-ingresso-chiuso-tesi-aperta-prospettive.png): CLOSED with the recorded hold text;
- [3](3-conclusione-storico-della-call-prospettive.png): TARGET_REACHED, with the history opened.

**Checks.**
- The generator asserts, per moment:
  - the original is in the details;
  - the follower text equals the expected translation of the recorded text;
  - none of "mantieni", "esci", "uscire", "uscita" or "chiudi la posizione" appears ("mantenere" appears only in moment 2, where the recorded text says "hold");
  - for moment 3, the concluded guidance, the collapsed original, "100700.0 — raggiunto", and the separation from the current "rialzo".
- `tests/e2e/test_live_proposal_e2e.py`:
  - CLOSED with the explicit hold text → HOLD with Italian numbers;
  - ONGOING with an unrecognised text → UNKNOWN, with no hold/exit wording;
  - a missing text → MISSING;
  - AVAILABLE entry text → ENTRY_VALID, with the band unchanged;
  - UNVERIFIED → ENTRY_UNVERIFIED;
  - a terminated call with no stored history → MISSING, target not available, "non prolunga questa call", no hold/close wording;
  - a non-current session → NOT_CURRENT.
- Cockpit E2E (proposal, presentation, call history, continuity, adviser): **10 passed** on a disposable PostgreSQL, removed. Build and typecheck passed.

**Limits for the Director.**
- Only the engine's current texts are recognised. A future wording change shows "non riconosciuto" until the mapping is updated; it never shows an invented instruction.
- The time beside the follower text is the view's evaluation time; the revision time is in the history.
- The "uscita" wording for the INVALIDATED, TIME_EXPIRED, UNASSESSABLE and RETIRED texts is recognised but was not exercised by this episode, only by the code mapping.
- The timeline's conclusion row still shows a UTC time without a zone.
