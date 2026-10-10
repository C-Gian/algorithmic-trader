# Live cockpit — clarity of the operational state (evidence)

Base `1c346ff31104a2d2f31376f1beb1817798312c01` (`main`). READY FOR DIRECTOR REVIEW — COCKPIT CLARITY ONLY; not accepted. Live cockpit only; the Workbench is untouched. No method, API or persistence change. v0.6 and HDP-001 frozen; evaluations INACTIVE.

## Preliminary check: fields, authoritative states, components

- **Entry availability.** It comes only from `view.call.entry_status` (AVAILABLE / CLOSED / UNVERIFIED), set by the core (`core.py` / `core3.py`):
  - AVAILABLE when no reason is recorded;
  - UNVERIFIED when only quote or connection reasons are present;
  - CLOSED otherwise.
  
  The API `present()` already turns a saved AVAILABLE into UNVERIFIED for a non-current session, with `presentation: NOT_CURRENT`, no admissible range and the reason `SESSION_NOT_CURRENT:<state>`.
- **Thesis validity.** It comes from `call.thesis_status`. A terminated call leaves `view.call` at once (`core.py`, `self.call = None`) and appears only in `view.recent_calls`.
- **Without a call.** The panel reads the following fields:
  - `market_view` for the expected direction, the conditional flag, the table row and the horizon;
  - `market_view.principal` for the scenario, trigger, invalidation and destination;
  - for v0.3+, the matching `view.scenarios[]` row for waiting, observing or entry-ended.
- All required data exist, so no backend change was needed. The previous `DirectionPanel` and `CallPanel` are replaced by one `ProposalPanel`. The technical scenario cards are moved unchanged into its "Approfondimenti" section.

## Field → meaning shown (main panel, Italian)

| Backend field | Shown as |
|---|---|
| no `view` | "Nessuna valutazione in corso"; Direzione attesa: Non disponibile |
| `view.call` = null | **"In attesa — nessun ingresso proposto"** |
| `call.entry_status` AVAILABLE (and not `NOT_CURRENT`, thesis ONGOING) | **"Ingresso disponibile secondo il sistema"**; "Fascia d'ingresso ammessa ora" = `admissible_bounds`, shown only in this state; the chart band too |
| `call.entry_status` CLOSED | **"Ingresso non più disponibile"**; "Motivo" = `entry_reasons` in plain Italian |
| `call.entry_status` UNVERIFIED (incl. `NOT_CURRENT`) | **"Non è possibile confermare la disponibilità dell'ingresso"**; "Motivo"; for a non-current session, also the badge "Sessione non corrente" |
| `call.thesis_status` ≠ ONGOING | "Indicazione conclusa — ingresso non disponibile" (defensive; the core normally removes the call) |
| unknown `entry_status` | "Stato dell'ingresso non riconosciuto (…): non considerarlo disponibile" |
| `recent_calls` (no call) | "Ultima indicazione: LONG A, conclusa — target raggiunto (time)" |
| `market_view.expected_direction` / `conditional` / `table_row` | Direzione attesa (Rialzo / Ribasso / Equilibrio / Incerta / Non disponibile), "(condizionale)", row in Italian |
| scenario state | Condizione ancora necessaria: an Italian phrase per recorded state (innesco oltre `trigger_level`; corridoio `corridor`; ripresa locale; osservazione; tentativo concluso); exact rules only in the details |
| `destination` / `conditional_target` | Destinazione dello scenario (non è un target operativo) |
| `invalidation_level` | Invalidazione dello scenario (livello strutturale, non è uno stop) |
| `market_view.horizon_minutes` / `call.expected_minutes` | Orizzonte atteso (scenario/call), kept apart from the deadline |
| `call.direction` | LONG/SHORT plus "Indicazione di acquisto/vendita: il sistema si aspetta un rialzo/ribasso" |
| `call.target` / `call.stop` | Target operativo / Stop indicato (published values) |
| `call.hard_deadline` | Scadenza dell'indicazione, local time with time zone; no countdown |
| `call.thesis_status` | Tesi: ancora valida / conclusa — … |
| `view.clock` | Ultimo aggiornamento, local time with time zone (e.g. "01/09/2025, 06:07:01 CEST") |

**Approfondimenti (collapsed)** holds:
- the reading codes, the 1h context and the phase;
- the system's reasons and counter-evidence;
- the system's guidance text and the raw codes;
- the structural area and the last computed band, labelled history / not usable now;
- family, precise UTC times, remaining minutes and revision;
- the live call history link and the scenario cards.

A fixed note says the indication is the system's, not an operation of the user, which the app does not know. Missing data read "non indicata"; nothing is reconstructed. The chart's admissible band is now drawn only while AVAILABLE.

## Synthetic screenshots

Each screenshot carries the label "Dimostrazione sintetica" and shows real engine states over existing fixtures, with no rule changed. Generator: `generate_states.py`; recorded facts: `states.json`. Browser time zone: Europe/Rome.

| File | State | Source |
|---|---|---|
| [1-in-attesa](1-in-attesa.png) | WAITING: A LONG confirmed, waiting for a local recovery | v0.6 MP-005 L1–L3 tape, 04:06:01.5 UTC |
| [2-ingresso-disponibile](2-ingresso-disponibile.png) (+ [telefono](2-ingresso-disponibile-telefono.png)) | AVAILABLE, r0 | same session, 04:07:01.5 |
| [3-ingresso-non-piu-disponibile](3-ingresso-non-piu-disponibile.png) | CLOSED, `PRICE_OUTSIDE_STRUCTURAL_AREA`, r4 | v0.2 WP-009 live fixture, 05:23:01.5 |
| [4-disponibilita-non-confermabile](4-disponibilita-non-confermabile.png) | UNVERIFIED, `QUOTE_STALE`, r1 | v0.6 session, 04:07:06 |
| [5-call-conclusa](5-call-conclusa.png) | call terminated TARGET_REACHED (in `recent_calls`) | v0.2 fixture, 08:27:01.5 |
| [6-sessione-non-corrente](6-sessione-non-corrente.png) | saved AVAILABLE in a STOPPED session → UNVERIFIED / NOT_CURRENT | v0.6 view 2 through the real `live_status` |
| [7-approfondimenti-chiusa](7-approfondimenti-chiusa.png) | CLOSED with the details open | v0.2 fixture, as 3 |

## Checks actually run

All on the disposable PostgreSQL `livehist-pg-disposable`, removed afterwards; the Owner stack was not touched. 12 passed in the final run on the final build.

| Check | Result |
|---|---|
| `npm run build` (typecheck + build) | passed |
| New `tests/e2e/test_live_proposal_e2e.py` (synthetic payloads; non-current through the real `live_status`) | 1 passed |
| `test_live_presentation_e2e` (4 cases; assertions moved to the Italian texts, same protections) | 4 passed |
| Live call history: `test_live_call_history_e2e` (entry point now inside Approfondimenti) and `test_live_call_history_db` | 2 + 2 passed |
| `test_ui_smoke::test_shell_market_overview_is_default_honest_and_navigable` (texts updated) | passed |
| `test_adviser_e2e` (real live worker: call, withdrawal, target, 390 px overflow) | 2 passed |

The new state test covers each state, the admissible band only in AVAILABLE (panel and chart), the scenario levels never named entry, target or stop, the local time with time zone, the unknown status, the defensive terminal state and `recent_calls`.

## Limits

- **Language.** System free texts stay in English inside Approfondimenti: guidance, reasons, rules. The rest of the cockpit (top bar, notices, timeline, lenses, history card) is unchanged and in English.
- **Condition phrases.**
  - They are fixed Italian sentences per recorded scenario state. The exact WAIT_RESPONSE rule is shown only in the details.
  - "Serve l'innesco: una chiusura oltre K" mirrors the existing UI wording ("needs a later close beyond K").
- **Real-engine notes.**
  - In the v0.2 fixture, CLOSED (price) alternates with UNVERIFIED (stale quote) within each minute, because a stale quote suppresses the price check.
  - In the fixtures the CLOSED call later reaches its target.
- No check against a real live session or Owner data. Comprehensibility is not attested. Remote CI: PENDING / NOT CHECKED.
