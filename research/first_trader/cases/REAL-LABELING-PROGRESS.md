# RP-001 real-case labeling — record

Status: **COMPLETE — six real grid labels frozen one at a time, then outcomes exported and revealed.** Frozen labels were not edited after their freeze commits.

## Acquisition (per SELECTION-PROTOCOL.md §1)

- `uv run algotrader data fetch-okx --start 2026-09-25T00:00Z --end 2026-09-30T00:00Z --root var/data` → dataset `okx-btc-usdt-swap-1m-20260925T0000-20260930T0000-3305612c15aa`, quality CLEAN (7,200 rows per bar family, 15 funding rows, 218 raw pages); `data verify` OK. Stored outside Git (`var/data`). The acquisition was run by the executor with the accepted WP-003 read-only workflow; the Director may treat this as a process point to confirm.
- Prefixes exported with `tools/export_case_excerpt.py prefix --m5-hours 24` (Amendment A1).

## Freeze sequence (Amendment A1)

| Case | Cutoff (UTC) | Freeze commit | Frozen public label |
|---|---|---|---|
| REAL-G01 | 2026-09-28T04:00 | `a43dc45` | NOT_DIRECTIONAL → NO_TRADE `NO_SUPPORTED_SETUP` |
| REAL-G02 | 2026-09-28T12:00 | `53bf65b` | DOWN, NO_IMPULSE (stair-step) → NO_TRADE `NO_SUPPORTED_SETUP` |
| REAL-G03 | 2026-09-28T20:00 | `544e206` | NOT_DIRECTIONAL → NO_TRADE `NO_SUPPORTED_SETUP` |
| REAL-G04 | 2026-09-29T04:00 | `85ae86f` | NOT_DIRECTIONAL → NO_TRADE `NO_SUPPORTED_SETUP` |
| REAL-G05 | 2026-09-29T12:00 | `972d6a2` | UP, IMPULSE_DEVELOPING → NO_TRADE `NO_SUPPORTED_SETUP` |
| REAL-G06 | 2026-09-29T20:00 | `0047ea6` | UP, NO_IMPULSE (progress fails) → NO_TRADE `NO_SUPPORTED_SETUP` |

Each commit contained only that case's prefix and label, and was pushed before the next prefix was opened. The `outcome` command was first run after `0047ea6` was on `origin/main`.

## Reveal summary (`outcomes/REAL-Gxx.reveal.yaml`; 240 VALID 1m bars each)

| Case | Verdict | What the forward application showed |
|---|---|---|
| G01 | SUPPORTS | Context stayed NOT_DIRECTIONAL while price fell 662 USDT; DOWN context arrived 6 h later (confirmation lag). |
| G02 | SUPPORTS | DOWN context lost at 13:00 (1h close above H2); rest of horizon NOT_DIRECTIONAL. |
| G03 | SUPPORTS | No new 1h swing; uninformative. |
| G04 | EXPOSES_AMBIGUITY | Context UP at 07:00; impulse 82933.0→84169.9 (1236.9) confirmed 07:45; reaction CONTROLLED (D 0.165/0.195) → first real WATCHING; blocked by P-GEOM (G 89.7 vs Rd 209.9, then 110.7 vs 131.0). Never ARMED. |
| G05 | SUPPORTS | WATCHING at 12:05 blocked by P-GEOM (G 9.0 vs Rd 193.4); at 12:10 ρ = 1.118 (n_R = 3) → OPPOSING_INITIATIVE (sticky). No later qualifying impulse. |
| G06 | SUPPORTS | NO_IMPULSE to the horizon end; 1h LOW 82850.8 confirmed only at 00:00 (new long epoch). |

No real case reached ARMED, a trigger, a LONG/SHORT or a scenario activation. No hit rate, return or profitability is computed or implied (six cutoffs over five days are not a performance sample).

## Findings for Director review (no rule was changed after any reveal)

1. **Geometry floor binds for shallow controlled reactions (G04, G05).** The nearest eligible target is usually the impulse extreme's own zone, so G = (B − z) − (K + e) is small while Rd includes the anchor bar's range. DC-17 (G ≥ 1.0 × Rd) therefore rejects most shallow pullbacks by construction.
2. **DC-31 progress reference after a deep counter-move (G06).** In an UP-labelled context, every new 5m high is compared with the epoch high-water mark; after a ~2% decline the method is blind to long setups until a new 1h swing LOW restarts the epoch (10.5 h here). DC-31's recorded alternative (latest confirmed same-direction 5m swing) is the obvious candidate for a predeclared contrast.
3. **Context label lag (G01, G06).** Confirmed-swing context arrives late and survives deep retracements that have not yet produced a confirmed swing; UP with 93% of the 1h leg retraced is correct under the rule but of doubtful information value.
4. **Stair-step trends are never impulses (G02).** Single-leg impulse definition excludes persistent multi-leg trends.
5. **Definition gap — which 5m swing series feed the zone set (G04).** Zones are created from "confirmed 5m swings", but 5m swings exist only inside long/short epochs with different S5. Not decisive in G04 (any extra nearer zone only lowers G).
6. **Boundary wording** — "confirmed before the arming known-at" when the zone of B becomes known at the same instant (G04); and C14 #5 displays single-direction OPPOSING_INITIATIVE as `SCENARIOS_CONTESTED` (G05).
7. **Frequency signal.** 3 of 6 cutoffs NOT_DIRECTIONAL; 0 of 6 armed; together with RP-001D's cost finding (VIABLE needs ≈ 64 bps of room) this suggests the candidate, as frozen, would issue very rarely on BTC 1h/5m/1m. This is a coverage observation, not an evidence claim, and it must not be "fixed" by tuning on these cases.

## Record-keeping notes

- Frozen labels `REAL-G02`, `REAL-G03` and `REAL-G05` are not strictly valid YAML: under `h1_series_continued_from_REAL-Gxx` a list item is followed by mapping keys. The content is unambiguous to a human reader; the files were **left byte-identical** to preserve the freeze. `REAL-G06` (fixed before its freeze) and all reveal files parse.
- REAL-G05's 5m swing HIGH 83318.0 is recorded at 05:20; the 05:25 bar has an equal high, which DC-06 keeps at the earliest time (05:20). Consistent.
