# Live cockpit — SECOND desktop visual PROPOSAL (to show Gian; not implemented)

Base `4a918dcc5032e900eb1935ba8d9f1839c5d8aee3`. **Proposal only: no product change is active.**
- The first proposal ([COCKPIT-VISUAL-PROPOSAL](../COCKPIT-VISUAL-PROPOSAL/PROPOSAL.md)) was not approved and is not implemented.
- The images were rendered from a temporary local draft, [`draft-ui.patch`](draft-ui.patch), which applies cleanly to the base. The product files (`web/src`) were restored, and the original UI rebuilt, right after the screenshots.
- Unchanged: semantics, the approved operational texts (two perspectives, plain-Italian reading of recognised guidance), method, API, persistence and Workbench. No new endpoint, field or data transformation.
- Synthetic engineering inputs only. v0.6 and HDP-001 frozen; studies INACTIVE. After Gian's choice, the implementation follows in the same step.

**Owner feedback addressed.**
1. The colours looked essentially unchanged.
2. Chart on the left, decision panel on the right.
3. Smaller chart, wider panel.
4. Candles.
5. Possibly a second useful chart.

**Viewport.** 1440 × 1000 desktop (Chromium, Europe/Rome). Each image is the cockpit area (1104 px next to the app sidebar), labelled "PROPOSTA VISIVA 2 — Dimostrazione sintetica (non implementata)". State 5 is also shown at 1024 and 390 px.

## Images

| # | State | Image |
|---|---|---|
| 1 | Waiting, no call | [1-attesa-senza-call.png](1-attesa-senza-call.png) |
| 2 | LONG available | [2-long-disponibile.png](2-long-disponibile.png) |
| 3 | SHORT available | [3-short-disponibile.png](3-short-disponibile.png) |
| 4 | UNVERIFIED (no fresh quote) | [4-non-verificabile.png](4-non-verificabile.png) |
| 5 | Entry CLOSED, thesis ONGOING | [5-ingresso-chiuso-tesi-aperta.png](5-ingresso-chiuso-tesi-aperta.png) · [1024](5-ingresso-chiuso-tesi-aperta-1024.png) · [390](5-ingresso-chiuso-tesi-aperta-390.png) |
| 6 | Call concluded (TARGET_REACHED), new expectation | [6-call-conclusa-nuova-aspettativa.png](6-call-conclusa-nuova-aspettativa.png) |

## First vs second proposal

| | First (not approved) | Second |
|---|---|---|
| Arrangement | Decision area at full width above a full-width chart | **Chart left (≈ 5/12), decision panel right (≈ 7/12)** |
| Chart | Close-price line, 720 × 260, full width | **1-minute candles**, ≈ 440 px wide, same levels and bands, with time ticks and a legend |
| Perspectives | Two side-by-side cards of equal height (empty space under the shorter one) | **Two full-width rows** (title \| content), each as tall as its own content |
| Market reading | Dashed column inside the decision area | Dashed block **under the chart**: a market assessment, kept away from the call |
| State colours | Soft 12 % tints: blue/amber/grey looked almost alike on the dark panel | **Filled blocks**: solid blue for available, solid amber for not verifiable, grey surface for waiting/closed/concluded. The direction chip is solid green or red. |
| Technical badges | LIVE, READY and LIVE QUOTED still green; Stop button and error red | Blue with a cpu icon (READY, LIVE QUOTED, Dati LIVE, Origine: call live), "Sessione" label; Stop neutral; errors amber |
| Alerts, timeline | Blue notice; new items in champagne | Neutral notice (history); new items marked "● nuovo" in bold; past calls show ▲/▼ with their direction |
| Lower area | Lenses + What changed, then Technical details | What changed (left) + lenses (right), then Technical details |

## Layout

**Top to bottom.**
1. The top bar (session) and the unread-alerts notice, as today.
2. The **main area**:
   - Left column, the market: the chart card, then "Lettura attuale del mercato".
   - Right column, the decision panel "Che cosa propone il sistema adesso":
     1. a call strip with the direction chip, "Call A · family", purpose and issue time, and the operational levels shown once (target, stop, deadline, horizon, thesis);
     2. the line "Due prospettive ipotetiche…";
     3. row 1, "Se non hai ancora aperto un'operazione": the filled state block, then the band, reason or UNVERIFIED consequence;
     4. row 2, "Se hai già aperto un'operazione su questa call": the plain-Italian reading of the recognised guidance, or of the concluded call;
     5. the non-order note, then Approfondimenti (collapsed).
3. **Below:** What changed, the lenses, then Technical details (collapsed).

**The four meanings stay apart.**
- Call identity: the strip.
- New entry: row 1.
- Update of the issued call: row 2.
- Market reading: under the chart, with "È una valutazione del mercato, non la call: non dice se entrare."

**Widths.**
- **1440:** two columns, as above.
- **1100 px and below (1024 image):** the decision panel comes first, at full width. Below it, the chart and the market reading sit side by side, so the chart keeps its desktop size instead of being scaled up.
- **760 px and below (390 image):** everything is stacked. The rows put the title above the content, and the levels use two columns. The decision panel comes before the chart.

## Colour map (whole cockpit shown)

Every state keeps its icon and its words; no state is conveyed by colour alone.

| Meaning | Where | Colour | Symbol + text |
|---|---|---|---|
| LONG / rising | Direction chip, timeline, market reading, scenario badge | green `--pos`; the chip is filled | ▲ LONG, "Rialzo" |
| SHORT / falling | same | red `--neg`; the chip is filled | ▼ SHORT, "Ribasso" |
| New entry available | Row 1 | **filled blue** `--info`, dark ink | ✓ "Ingresso disponibile secondo il sistema" |
| Admissible band (only while available) | Chart | blue tint with a blue edge | label "fascia ammessa ora" |
| Ready technical state | Session badge, lens READY / LIVE QUOTED / HISTORICAL BASE, "Dati LIVE", "Origine: call live", readiness READY in Technical details | blue outline badge on a soft tint | cpu icon or dot + the technical word; "Sessione" label in the bar |
| Not verifiable / attention | Row 1 UNVERIFIED, consequence box, unknown entry status | **filled amber** `--warn`, dark ink | ⚠ "Non è possibile confermare…" + consequence |
| Technical problem | "Sessione non corrente", Disconnected, Not responding, Failed, Stale, Unavailable, action error notice | amber (dashed chip for session not current) | cpu / alert + words |
| Waiting | Row 1, no-call strip, session starting / catching up, scenario "waiting" | grey surface `--surface-3`, text `--text-2` | clock "In attesa — nessun ingresso proposto" |
| Entry not available now | Row 1 | grey surface | ⏸ "Ingresso non disponibile adesso" |
| Concluded call | Strip | grey dashed chip | ■ "Conclusa — target raggiunto" |
| History | Alerts notice, timeline | neutral; new items in bold with "● nuovo" | pulse icon, recorded time |
| Session stopped / method | Bar | neutral | words |
| Actions | Start | champagne `--brand` (identity colour, not a state) | label |
| Actions | Stop, Reassess, Copy | neutral secondary | label |
| Limited / not covered / unknown coverage | Lens badges | `--pending`, dashed | words |

**Changed from the product.**
- LIVE, READY and LIVE QUOTED were green; they are now blue with cpu.
- "Stop live adviser" was red; it is now neutral.
- Error notices, Not responding and Failed were red; they are now amber.
- The alerts notice was blue; it is now neutral.
- New timeline items were champagne; they are now bold with "● nuovo".
- The scenario "waiting" badge was blue; it is now grey with a clock.
- The method badge was blue; it is now neutral.
- CLOSED was red; it is now grey with ⏸.
- AVAILABLE was green; it is now filled blue with ✓.

### Chart: what each mark means

The chart's existing meanings change **explicitly** here, and are written in the legend under the chart:

| Mark | Product today | Proposal |
|---|---|---|
| Price | brass close-price line | 1-minute candles. **Hollow green** = close above open; **filled red** = close below. This is that minute's move, never the call's direction. |
| Target, stop | green / red solid lines | Light (text colour) solid lines, with labels "target …" and "stop …". Green and red now belong to the candles only. |
| Support, resistance | green / red dashed | Grey dashed lines, with labels "supporto …" and "resistenza …" |
| Box | pending dashed | pending dotted, "box min/max …" |
| Structural area | brass tint | unchanged |
| Admissible band | green tint, only while AVAILABLE and current | blue tint with a blue edge and the label "fascia ammessa ora". The drawing rule is unchanged. |
| Coincident levels | overprinted ("target/resistance 100,700") | one label: "target 100,700 / = resistenza" |
| Times | none in the chart (only "as of" in the header) | three ticks (first, middle, last minute), in local time, plus the legend line "Asse orizzontale: ora locale dei minuti completi". The header keeps "as of … UTC". |

**How the three things are told apart.**
- **Direction** of the call is never drawn in the chart. It is the filled chip in the panel.
- **Levels** are told apart by line style plus label.
- **Entry state** is shown only by whether the blue band exists, and the band is labelled.

### Contrast

WCAG ratios on the actual backgrounds, with soft tints composited. Script: [contrast.py](contrast.py); values: [contrast.json](contrast.json).

**Text** (4.5:1 required):

| Element | Ratio |
|---|---|
| Ink on filled blue | 8.48 |
| Ink on filled amber | 8.48 |
| Grey state | 8.07 |
| LONG chip | 8.88 |
| SHORT chip | 6.91 |
| Concluded chip | 6.87 |
| Technical blue badges | 6.22 / 6.63 |
| Amber "session not current" chip | 6.38 |
| Timeline ▲ green / ▼ red | 8.56 / 6.43 |
| Market reading Rialzo / Ribasso | 9.18 / 6.89 |
| Secondary notes | 4.70 |
| Chart legend and ticks | 4.94 |
| Band label | 8.13 |

**Chart marks** (3:1 required):

| Mark | Ratio |
|---|---|
| Green candles | 8.56 |
| Red candles | 6.43 |
| Target/stop lines | 15.33 |
| Support/resistance | 7.22 |
| Box | 7.10 |
| Band edge | 8.13 |
| Candles over the band / area tints | 5.63 / 5.38 |

All 26 pairs pass.

## Candles: availability findings

1. **The existing candle component cannot be reused as is.**
   - `MarketChart` (`web/src/views/replay/MarketChart.tsx`, used by Backtest and Market Replay) draws OHLC candles, but it takes `TradedBar[]`: `seq`, `event_time`, `available_time`, `kind`, `quality_reason` and optional `open/high/low/close`.
   - The cockpit receives `view.chart.minutes` as `{t, o, h, l, c}`. Feeding `MarketChart` would need a data mapping that invents `seq`, `available_time` and `kind`, which the assignment excludes.
   - `MarketChart` also has **no level or band overlays**: no target, stop, structural area, admissible band, support/resistance or box. Reusing it would lose the cockpit's levels.
2. **The cockpit already has the OHLC data.** The live view sends `chart.minutes` with `o/h/l/c` (`src/algotrader/adviser/live.py`, `recent_1m`, at most 240 complete minutes). The cockpit's own `PriceChart` already reads `h/l` for its scale.
3. **What the proposal does.** It reuses **the cockpit's existing `PriceChart`** with its existing scale, levels, bands and the AVAILABLE-only band rule, and draws a candle (wick + body) per minute from those same fields.
   - No new chart engine, endpoint or field.
   - No change to the data, only to how existing values are drawn.
   - The candle look reuses the replay chart's convention: wick + body, green/red.
   - If the Director reads "reuse an existing component" strictly (that is, `MarketChart` only), the exact limit is point 1, and the candles stay out of the proposal.

## Possible second chart (not implemented)

- **Candidate: 15-minute context.** The live view already sends `chart.m15`: the last 96 complete 15-minute bars, about 24 hours, encoded as `[start, end, o, h, lo, c, vol]` from `measures.Bar.encode()[:7]`. Nothing in the web app shows it today.
- **The distinct question it answers:** "where is the price in the context of the last day?" The 1-minute chart covers at most 4 hours. This matters because the method's 15m/1h context gates calls.
- **No existing component can show it without a transformation.**
  - `MarketChart` needs `TradedBar[]`.
  - The Workbench `MiniChart` (`AdviserResult.tsx`) needs `{t, c, h, l}` plus a historical call. It also answers a different question (price around one recorded call).
  - `PriceChart` takes the whole `LiveView`, not a series.
- **What it would take:** a presentation-only adapter from the array to `{t, o, h, l, c}`. That is a data transformation, so it would need a separate decision.
- **The main proposal works without it.**

## Information shown and existing fields

Same fields as the first proposal: `view.call.*` (direction, family, family_text, issued_at, target, stop, hard_deadline, expected_minutes, thesis_status, entry_status, entry_reasons, admissible_bounds, guidance, presentation, origin), `view.recent_calls[]`, the read-only `GET /api/adviser/runs/{run}/calls/{call}` for a concluded call, `view.market_view`, `view.scenarios[]`, `view.levels`, `view.chart.minutes` (o/h/l/c/t), `view.lenses`, `view.clock`, `view.origin`, `view.stale_session`.

## States and fixtures

The states are real in-memory v0.6 live sessions with mocked services, over the existing MP-005 synthetic tapes, served through the real `live_status` boundary.
- Generator: [generate_proposal.py](generate_proposal.py), the same state logic as the first proposal. It asserts each state.
- Facts: [proposal-states.json](proposal-states.json).

They are **three independent sessions**, shown as separate states and not as one sequence:
- **States 1, 2 and 4:** one LONG session (`live-20250828T0316-ed1b76`), at 04:06:01.5, 04:07:01.5, and 04:07:06 (QUOTE_STALE).
- **State 3:** the mirrored SHORT tape (`…-6a870f`), 04:07:01.5.
- **States 5 and 6:** the LIVE-CALL-UPDATES episode (`…-6b0d56`). State 5 is CLOSED r1 at 04:08:01.5; state 6 is TARGET_REACHED at 04:10:01.5, with the expectation still UP.

The run ids differ from the first proposal because each run creates new ids; the tapes and moments are the same.

## Limits

- The tapes are synthetic step series: most minutes are flat (open = close), so many candles look like ticks. Real data would show ordinary candles.
- The chart labels use the existing `fmtNum` format ("99,700"), while the panel uses the Italian format ("99.700"). This is pre-existing and not changed.
- At 1440 px, when the decision panel is shorter than the left column (state 1), some empty space remains under the panel. There are no equal-height cards.
- At 390 px the long method badge in the top bar is cut. This is pre-existing.
- Lens and timeline texts stay as the system writes them, mostly in English. The recorded texts stay in English in the details.
- The draft keeps the existing test ids, with three differences:
  - `live-call-direction` is now on the strip's chip;
  - `live-direction` marks only the market reading;
  - it adds `live-call-identity`, `live-market-reading` and `live-chart-legend`. The E2E suite was **not** run against the draft; it is not a product change. The implementation step will update and run it.

## Regenerate

1. `git apply delivery/evidence/COCKPIT-VISUAL-PROPOSAL-2/draft-ui.patch`
2. `cd web && npm run build`
3. Run the generator with a disposable PostgreSQL:
   ```text
   ALGOTRADER_TEST_DATABASE_URL=… uv run python delivery/evidence/COCKPIT-VISUAL-PROPOSAL-2/generate_proposal.py
   ```
4. Check contrast: `uv run python delivery/evidence/COCKPIT-VISUAL-PROPOSAL-2/contrast.py`
5. Restore the product: `git checkout -- web/src`, then rebuild.
