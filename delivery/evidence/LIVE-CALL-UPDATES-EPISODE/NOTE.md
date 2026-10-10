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

It rewrites the three PNG files and `episode.json` in this folder. The run id suffix changes; the states, times and call id do not. Remote CI: PENDING / NOT CHECKED.
