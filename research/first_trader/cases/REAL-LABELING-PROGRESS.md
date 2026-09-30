# RP-001 real-case labeling — progress record (work in progress)

Status: **IN PROGRESS — no real grid label is frozen yet; no outcome has been exported or viewed.**

## Acquisition (done, per SELECTION-PROTOCOL.md)

- `uv run algotrader data fetch-okx --start 2026-09-25T00:00Z --end 2026-09-30T00:00Z --root var/data` → dataset `okx-btc-usdt-swap-1m-20260925T0000-20260930T0000-3305612c15aa`, quality CLEAN (7,200 rows per bar family, 15 funding rows, 218 raw pages); `data verify` OK. Stored outside Git (`var/data`).
- The six prefixes were exported locally with `tools/export_case_excerpt.py prefix --m5-hours 24` (24 h of 5m bars, a superset of the protocol's 12 h). **Not committed yet.** Only REAL-G01's prefix has been viewed. The outcome command has not been run.

## Protocol amendment A1 (made before any prefix was viewed)

Every later prefix contains the earlier cutoffs' 4-hour outcome windows. So labels must be frozen **one case at a time in chronological order**: G01 is labeled, committed and pushed before G02's prefix is opened, and so on. After all six freezes, the outcome exports and reveals follow.

## REAL-G01 working derivation so far (1h structure; cutoff 2026-09-28T04:00Z)

- S1h warm-up (bars 1–24, 09-25 00:00–23:00): median TR 382.4 → θ = 764.8.
- INIT from bar 25. Swing **LOW 83,748.8** (extremum 09-26T00:00), confirmed by bar 50 (09-27T01:00; high 84,535.0 ≥ 84,513.6), known 09-27T02:00. Mode UP.
- θ for the up-leg: S1h at bar 50 (TR bars 27–50) = 181.95 → θ = 363.9.
- Bar 62 (09-27T13:00): high 85,137.5 extends the high, and its low 84,590.0 also reaches 85,088.0 − 363.9 → **AMBIGUOUS_PATH** (DC-07: treated as an extension).
- Swing **HIGH 85,137.5** (09-27T13:00, flagged AMBIGUOUS_PATH), confirmed by bar 63 (low 84,382.6 ≤ 84,773.6), known 09-27T15:00. Mode DOWN, running low 84,382.6.
- θ for the down-leg: S1h at bar 63 (TR bars 40–63) = 208.4 → θ = 416.8. **Continue DC from bar 64.**

## Remaining

1. Finish G01: 1h DC through bar 76; context rule (≥ 2 confirmed highs and ≥ 2 confirmed lows needed; only 1 + 1 so far → likely UNKNOWN unless more swings confirm); if assessable and directional, run the 5m epoch per DC-30/31. Write `prefixes/REAL-G01.label.yaml`, commit and push (freeze).
2. Repeat for G02 → G06 in order, one freeze commit each.
3. Run the `outcome` exports; write `outcomes/REAL-Gxx.reveal.yaml` per protocol §5; update `CASE-REGISTER.yaml`.
4. Final checks (the scratch check script: YAML/JSON parse, OHLC sanity, links, DC references) and the RP-001 completion report.
