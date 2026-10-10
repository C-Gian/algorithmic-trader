# Live cockpit — desktop visual PROPOSAL (to show Gian; not implemented)

Base `8759c855450fe2edb0b35f86db111b7daa82b69d`. **Proposal only: no product change is active.**
- The images were rendered from a temporary local draft, [`draft-ui.patch`](draft-ui.patch), which applies cleanly to the base. The product files were restored right after the screenshots.
- The draft is evidence, not an implementation. After Gian's agreement, the implementation follows in the same step.
- Unchanged: semantics, the approved operational texts (two perspectives, plain-Italian guidance), method, API, persistence and Workbench.
- Synthetic engineering inputs only. v0.6 and HDP-001 frozen; studies INACTIVE.

**Viewport.** 1440 × 1000 desktop (Chromium, Europe/Rome). Each image is the cockpit area (1104 px wide next to the app sidebar), and each is labelled "PROPOSTA VISIVA — Dimostrazione sintetica (non implementata)". State 5 is also shown at 1024 and 390 px for width compatibility.

## Images

| # | State | Image |
|---|---|---|
| 1 | Waiting, no call | [1-attesa-senza-call.png](1-attesa-senza-call.png) |
| 2 | LONG available | [2-long-disponibile.png](2-long-disponibile.png) |
| 3 | SHORT available | [3-short-disponibile.png](3-short-disponibile.png) |
| 4 | UNVERIFIED | [4-non-verificabile.png](4-non-verificabile.png) |
| 5 | Entry CLOSED, thesis ONGOING | [5-ingresso-chiuso-tesi-aperta.png](5-ingresso-chiuso-tesi-aperta.png) · [1024](5-ingresso-chiuso-tesi-aperta-1024.png) · [390](5-ingresso-chiuso-tesi-aperta-390.png) |
| 6 | Call concluded (TARGET_REACHED), new expectation | [6-call-conclusa-nuova-aspettativa.png](6-call-conclusa-nuova-aspettativa.png) |

## Layout

1. **Decision area at full width**, above the chart. The call is no longer a narrow column beside the technical cards.
2. **Call strip** (left, top). It holds the direction chip (▲ LONG / ▼ SHORT), "Call A · family", the issue time, and the call's operational levels, shown once: target, stop, deadline, horizon, thesis. A concluded call keeps a grey dashed chip and "■ Conclusa — target raggiunto".
3. **Two equal cards**, one per approved perspective, each with the same title size and the same headline size:
   - "Se non hai ancora aperto un'operazione": the authoritative availability, with its symbol, plus the band, reason or UNVERIFIED consequence;
   - "Se hai già aperto un'operazione su questa call": the plain-Italian reading of the recognised guidance, or of the concluded call.
4. **"Lettura attuale del mercato"** (right, dashed frame, no fill). It shows the expected direction, the table row and the scenario levels, labelled as non-operational, with "È una valutazione del mercato, non la call."
5. **Progressive detail.** Approfondimenti stays collapsed under the decision area. Below it come the chart at full width, then lenses and "What changed" side by side, then Technical details.
6. **Widths.**
   - Below 1100 px, the market reading moves under the cards.
   - Below 760 px, the cards stack and the levels use two columns.

**No duplication.** The levels appear only in the call strip. The direction of the call (chip) and the market expectation (arrow plus word) are labelled as different things.

## Colour map

Every colour comes from the existing tokens and is paired with a symbol and a text. The panel is never coloured by LONG/SHORT.

| Meaning | Colour (token) | Symbol | Text |
|---|---|---|---|
| LONG / rising direction | green `--pos` | ▲ | LONG, "Rialzo" |
| SHORT / falling direction | red `--neg` | ▼ | SHORT, "Ribasso" |
| New entry available | blue `--info` | ✓ (check) | "Ingresso disponibile secondo il sistema" |
| New entry not available now | grey `--neutral` | ⏸ (pause) | "Ingresso non disponibile adesso" |
| Not verifiable / attention | amber `--warn` | ⚠ (alert) | "Non è possibile confermare…" plus the consequence |
| Waiting | grey `--neutral` | clock | "In attesa — nessun ingresso proposto" |
| Concluded call | grey `--neutral`, dashed chip | ■ (stop) | "Conclusa — target raggiunto" |
| Technical problem (session not current) | amber, dashed outline | cpu | "Sessione non corrente: disponibilità non verificabile" |

**What the map achieves.**
- An available SHORT shows red only in its direction chip; the availability itself is blue with ✓, so it does not look like an error.
- A concluded LONG has a grey dashed chip and ■, never green or ✓.
- TARGET_REACHED is grey "Conclusa", never green or "profit".

**Contrast** (WCAG, computed on the token values and their actual backgrounds):

| Colour | Background | Ratio |
|---|---|---|
| blue | its soft background | 6.63 |
| amber | its soft background | 6.73 |
| grey | its soft background | 6.19 |
| green | strip / card | 7.51 / 8.56 |
| red | strip / card | 5.64 / 6.43 |
| main text | strip | 13.46 |
| secondary notes | panel | 4.70 |

All pass AA for normal text.

## Shown information and existing fields

All values come from the existing live view, through `live_status`, or from the read-only call route. No new field is used.

| Shown | Field |
|---|---|
| Direction chip, Call family, issue time | `view.call.direction`, `family`, `family_text`, `issued_at` |
| Target, stop, deadline, horizon, thesis | `call.target`, `stop`, `hard_deadline`, `expected_minutes`, `thesis_status` |
| Availability headline and symbol | `call.entry_status` (masked by the API when not current), through `proposalState` |
| Band / reason / UNVERIFIED consequence | `call.admissible_bounds` (AVAILABLE only), `entry_reasons` |
| Follower reading | `call.guidance` through the approved `readGuidance`; the original stays in Approfondimenti |
| Concluded call | `view.recent_calls[]` (`terminal`, `reason`, `terminal_at`); target and closing text from `GET /api/adviser/runs/{run}/calls/{call}` |
| Market reading | `view.market_view` (`expected_direction`, `conditional`, `table_row`, `principal`, `horizon_minutes`), `view.scenarios[]` |
| Session not current | `call.presentation`, `view.stale_session` |

## States and fixtures

The states come from real in-memory v0.6 live sessions with mocked services, over the existing MP-005 tapes, and are served through the real `live_status`. Facts: [proposal-states.json](proposal-states.json); generator: [generate_proposal.py](generate_proposal.py).
- **States 1, 2 and 4** come from one LONG session (`…-06b29f`), at 04:06:01.5, 04:07:01.5 and 04:07:06 (QUOTE_STALE).
- **State 3** is the mirrored SHORT tape (`…-0b6592`), 04:07:01.5, call `call-AS-…-bf29ac4566ec`.
- **States 5 and 6** come from the LIVE-CALL-UPDATES episode (`…-44125a`): CLOSED r1 at 04:08:01.5, and TARGET_REACHED at 04:10:01.5 with the expectation still UP.

They are three independent sessions, shown as separate states and not as one sequence.

**Limits.**
- The tapes are synthetic and short. The chart and lens cards are the existing components, unchanged.
- The existing chart labels overlap when target and resistance coincide ("target/resistance 100,700"). This is pre-existing and not addressed by the proposal.
- At 390 px the long method badge in the top bar is cut. This is a pre-existing, known limit outside the decision area.
- The recorded system texts stay in English in the details.

**Regenerate.**
1. `git apply delivery/evidence/COCKPIT-VISUAL-PROPOSAL/draft-ui.patch`
2. `cd web && npm run build`
3. Run the generator with a disposable PostgreSQL:
   ```text
   ALGOTRADER_TEST_DATABASE_URL=… uv run python delivery/evidence/COCKPIT-VISUAL-PROPOSAL/generate_proposal.py
   ```
4. `git checkout -- web/src`
