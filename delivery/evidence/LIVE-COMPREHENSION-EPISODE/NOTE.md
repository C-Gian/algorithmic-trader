# Live cockpit — synthetic comprehension episode (note for the Director)

Base `e582f3800d8cae25cb94b8bbccb5d5fc0fbed94d` (`main`). Evidence only: no product, method, API or persistence change. v0.6 and HDP-001 frozen; evaluations INACTIVE. Synthetic engineering inputs, not market data; no Owner data, live feed, order or economic replay.

## Episode identity

| | |
|---|---|
| Method | v0.6 (`btc.context-action.v0.6` / `adviser.core.v6`), live profile, mocked services |
| Tape | the existing MP-005 L1–L3 LONG tape of `tests/test_mp005_live.py` (`REF`, neutral, contrary-equality bar, `VALID`; wide quote at 04:05) |
| Continuity run | `live-20250828T0316-146680` (in-memory session; run id generated per execution) |
| Session (display) | `demo-synthetic-session` |
| Scenario | `AL-2025-09-01T03:15:00+00:00-d49a8b5618ff` (A LONG) |
| Call | `call-AL-2025-09-01T04:07:01+00:00-05a41e24819a` |

The three screenshots are successive views of **one** `LiveSession`, taken without a restart or any other input. Each view passes through the real `live_status` presentation boundary. The alerts shown are the session's own alertable material changes. The views are rendered by the built cockpit components. The only addition is the CSS label "Dimostrazione sintetica"; the screenshots carry no explanatory text. The generator checks the sequence: same run, same scenario and same call, the states below, one call and one revision recorded.

## States and recorded reasons

1. **[Expectation without a call](1-aspettativa-senza-call.png)** — 04:06:01.5 UTC.
   - MarketView UP, conditional, row `CONDITIONAL_SCENARIO`; no call.
   - Scenario A LONG `CONFIRMED`, child in `WAIT_RESPONSE`: return reference H0 100008 / L0 99990, published at 04:04:01. Blockers: none recorded ("waiting for a fresh minute").
2. **[Call available](2-call-disponibile.png)** — 04:07:01.5 UTC.
   - Call issued at 04:07:01 on the valid recovery from the same scenario; revision 0, entry `AVAILABLE`, thesis `ONGOING`.
   - Admissible 99900–100014.5, structural area 99900–100049.9, target 100700.0, stop guidance 99700.0, hard deadline 08:02:01.
   - Material change `NEW_CALL`, alertable.
3. **[Update to the same call](3-aggiornamento-stessa-call.png)** — 04:07:06 UTC.
   - Revision 1, published at 04:07:05.5: entry `UNVERIFIED`, reason `QUOTE_STALE`, thesis `ONGOING`.
   - Recorded guidance: "Thesis ongoing; current entry cannot be verified (no fresh quote). Do not treat as ready now."
   - Material change `ENTRY_UNVERIFIED`, alertable. The cockpit shows "Entry cannot be verified now (Quote stale)" and admissible "not verifiable".

## Compatibility and limits

- **Closure type.** The closure is the engine's withdrawal of usable entry through **`UNVERIFIED`** (no quote fresher than 5 s), not `CLOSED`. In this tape no `CLOSED` state occurs for this call. The synthetic feed sends one quote per minute, so availability alternates; the session's own course ends the call as `RETIRED` at 06:02. Producing a `CLOSED` state, for example price leaving the admissible range, would need a new tape minute, so it was not done. Whether `UNVERIFIED` fits the test's third moment is a Director decision.
- **Displayed context.** The cockpit shows the real product texts for a LIVE session, such as "Live: current public data and quotes are being assessed" and the fixture date 2025-09-01. Only the label marks the episode as synthetic.
- **Existing product wordings, unchanged.**
  - Moment 1 shows "Top reason: Conditional", the first word of the table-row text, because no blocker was recorded.
  - The `NEW_CALL` summary cites the structural area 99900–100049.9, while the admissible range is 99900–100014.5.
- **Reproduction.** `generate_episode.py` (disposable PostgreSQL, built UI). `episode.json` holds the recorded facts. Remote CI: PENDING / NOT CHECKED.
