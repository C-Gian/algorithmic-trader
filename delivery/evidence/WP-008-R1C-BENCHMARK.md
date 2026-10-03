# WP-008-R1C structural benchmark — executor evidence (gate inventory corrected; Director review pending)

Synthetic infrastructure evidence only: deterministic generated OKX-shaped data served through the accepted offline
acquisition path (no network), plus a captured recorder edge fixture. **Not** a historical month/year evaluation, a
strategy test, or an Owner-hardware speedup claim.

- Script: `scripts/bench_observe.py` (reproduce: `uv run python scripts/bench_observe.py --admin-url <disposable PostgreSQL> --out var/benchmarks/r1c --budget-minutes 60`)
- Machine: Windows 10 19045, Python 3.14.7, Intel Core (Family 6 Model 158), 8 logical CPUs, 32 GiB RAM, local disk (type not recorded); no container limits; disposable PostgreSQL 18.6 container on the same host. Build: base `d2ee918` + R1C working tree.
- Full report: `WP-008-R1C-benchmark.json` (clean run, ~22 min wall). First run: `WP-008-R1C-benchmark-run1-traced.json` (see *Year tier, first run*).

## Gates (clean run) — corrected inventory (R1C correction, evaluator v2)

The original table labelled all six rows as release gates PASS. That was wrong for the three year rows: they are
component measurements, not application gates. The stored raw measurements are unchanged and were not rerun.
`WP-008-R1C-benchmark-gates-v2.{json,md}` re-evaluates them with the corrected evaluator
(`uv run python scripts/bench_observe.py --evaluate-only delivery/evidence/WP-008-R1C-benchmark.json --out
delivery/evidence/WP-008-R1C-benchmark-gates-v2`). Both raw JSON files keep their original v1 `gate_evaluation` as
historical record.

**Month application gates** (measured end to end: durable launch, compute process, DB checkpoints, actual reconciliation and report)

| Gate | Measured | Limit | Result | How measured |
|---|---|---|---|---|
| Month cached observation | 31.4 s | 120 s | PASS | warm job, launch → terminal, wall incl. compute-process spawn; run completed/passed |
| Month terminal validation/report | 0.84 s | 10 s | PASS | FINALIZING + VALIDATING + GENERATING_REPORT active |
| Month cold preparation | 36.8 s | 120 s | PASS | PREPARING_SOURCE + VERIFYING_SOURCE + BUILDING_FEED active |

**Annual component comparisons** (not gates)

| Component | Measured | Annual limit | Not included |
|---|---|---|---|
| Kernel replay + checkpoint-cadence snapshot/encode | 326 s | 900 s | DB checkpoint transactions, durable job, process spawn |
| SHA-256 of all 316 partitions + consumed-input commitment re-hash | 6.8 s | 30 s | full reconciliation path (ranges/state/receipt), report generation |
| Cache build (bounded external sorts) | 157 s | 900 s | source snapshot and verification; the ~2 × 157 s cold estimate is not a measurement |

**Annual application gates.** Year cached observation, year terminal validation/report and year cold preparation are
all **NOT_MEASURED / PENDING**. No end-to-end year application run was measured, so annual readiness is not claimed.
The proposed Owner handoff is month-only (September), for Director review.

## Month tier (30 days, 129,690 events, 2-day long gap + periodic missing slots, shuffled Parquet rows)

| Run | Wall | Replay | Rate | Terminal | Txns / checkpoints | Delivery rows | Peak RSS |
|---|---|---|---|---|---|---|---|
| Cold (snapshot 0.01 s, verify 18.7 s, build 18.1 s; 14 sort spill runs) | 68.7 s | 30.3 s | 4,286 ev/s | 0.80 s | 27 / 26 | 0 | 139 MB |
| Warm (receipt-pinned cache reused, 0 verifications/builds) | 31.4 s | 29.7 s | 4,371 ev/s | 0.84 s | 27 / 26 | 0 | 102 MB |
| Paused at ~50 % (pause applied 0.23 s), resumed | 16.1 s after resume | — | 4,382 ev/s | 0.84 s | 13 / 13 after resume | 0 | 101 MB |
| Deep validation of the warm run | 28.6 s | 27.8 s | 4,667 ev/s | — | — | — | 101 MB |

Resume restored the checkpoint directly: INITIALIZING 0.08 s, prefix-restore events 0, suffix events 0, 63,543 events applied after resume. Deep validation: MATCH, 84 comparisons, 129,690/129,690 events covered. Cache read 8.9 MB in 26 partitions; restorable state 33 KB per checkpoint; max control gap 0.27 s.

## Other tiers

- **Many partitions** (same month, 500-event partitions, inline worker): 260 partitions read; COMPLETED/passed; wall 69.3 s, cold prep 36.7 s, replay 31.6 s; peak RSS 178 MB (inline: includes the benchmark driver).
- **Recording** (captured recorder session with 60 repeated completions per push): COMPLETED/passed; dedup collapses the input to 5 delivered events; 1.2 s wall. This is a dedup edge fixture, not a volume test.
- **Pilot** (2 days): cold 5.6 s, warm 3.1 s, Deep MATCH.

## Year tier (component level, fresh process)

365 days, 1,576,800 events (incl. a 1-week gap and periodic quality slots), 316 partitions, 100 MB cache, 196 KB manifest (metadata growth ≈ 620 B per partition). Replay rate per decile: 4,686 → 4,850 ev/s (flat; no per-event growth). Python heap (separate traced pass over 300,000 events): plateau 10.0–10.7 MB, peak 21.5 MB. Peak RSS 89 MB after build, 95 MB after replay. External sorts: 84 runs each, one merge pass, ≤16 open runs, ≤20,000 buffered records.

Not covered at year scale: DB checkpoint transactions (month: 1 per ~5,000 events, included in the month job timings), process spawn, source snapshot/verification (month: verification ≈ build time, so a year cold preparation is extrapolated at roughly 2 × 157 s, not measured).

### Year tier, first run (retained)

The first run measured year replay 984 s (FAIL) and cache build 588 s because `tracemalloc` was active during the timed passes. Profiling the same cache untraced showed ~5,000 ev/s with no cursor-dependent slowdown (bounded reducer history). The script was corrected to time untraced and measure heap in a separate bounded pass; no product code was changed for this. Month tiers in both runs agree within ~6 %.

## Limits

Single local machine; the Owner's Docker host, disk and CPU limits will differ. Generated bars are denser/cleaner than real evidence apart from the injected gaps. These numbers do not predict the Owner's September result; the Owner's new Market replay report (with worker host facts) is the comparison point.
