# WP-008-R2 synthetic month benchmark (engineering smoke, temporal substrate enabled)

> Executor-run bounded engineering measurement with the unchanged `scripts/bench_observe.py --tiers month` (only fix: a None-progress race in its pause/restore helper). Same synthetic 30-day dataset generator as R1C; runs use engine `observe.stream.v2` with the causal temporal substrate. Not a historical month/year evaluation, not an Owner-hardware claim, not an annual gate. The embedded title below is the script's unchanged R1C template.

Comparison with the stored R1C evidence (`delivery/evidence/WP-008-R1C-benchmark-gates-v2.md`, same executor machine): month cached observation 31.4 s (R1C, no temporal state) -> 43.8 s here; terminal validation/report 0.84 s -> 0.87 s; cold preparation 36.8 s -> 36.1 s (preparation is unchanged by R2). Temporal restore state measured in a first run of this tier with the same code path: ~75 KB compressed per checkpoint (factual state ~33 KB); 2,879 dispatches over the month. Deep validation v2 (shadow temporal fold + separate reference aggregator): MATCH, 164 comparisons, 54.9 s, peak RSS 236 MB (a first run before the reference's compact per-minute storage peaked at 930 MB).

---

# R1C synthetic engineering benchmark

> Deterministic generated evidence through the offline acquisition path. Not a historical month/year evaluation, strategy test or Owner-hardware claim.

- Build `91690966919bc34fbb709a5f82da7a02521bf653` (dirty=True) · Windows-10-10.0.19045-SP0 · Python 3.14.7
- CPU Intel64 Family 6 Model 158 Stepping 9, GenuineIntel · 8 logical · RAM 32.0 GiB · storage free 379.1 GiB
- local machine, no container CPU/memory limits applied by the benchmark · budget 20.0 min

## Gates

_Gate evaluator v2_

### Month application gates (measured end to end)

| Gate | Measured s | Limit s | Run | Result |
|---|---|---|---|---|
| month cached observation | 43.812 | 120.0 | completed/passed | PASS |
| month terminal validation/report | 0.873 | 10.0 | completed/passed | PASS |
| month cold preparation | 36.13 | 120.0 | completed/passed | PASS |

### Annual component comparisons (NOT gates)

| Component | Measured s | Annual limit s | Omits | Result |
|---|---|---|---|---|

### Annual application gates

| Gate | Limit s | Result | Status |
|---|---|---|---|
| year cached observation | 900.0 | NOT_MEASURED | PENDING - no end-to-end year application run was measured; annual readiness is not claimed (component comparisons are not substitutes) |
| year terminal validation/report | 30.0 | NOT_MEASURED | PENDING - no end-to-end year application run was measured; annual readiness is not claimed (component comparisons are not substitutes) |
| year cold preparation | 900.0 | NOT_MEASURED | PENDING - no end-to-end year application run was measured; annual readiness is not claimed (component comparisons are not substitutes) |

## month

```json
{
 "synthetic_acquisition_s": 10.57,
 "cold": {
  "replay_id": "obs-20261003T152747-b45ad4",
  "status": "completed",
  "assurance": "passed",
  "events": 129690,
  "cursor": 129690,
  "wall_including_process_spawn_s": 80.237,
  "phase_active_s": {
   "QUEUED": 0.0,
   "PREPARING_SOURCE": 0.011,
   "VERIFYING_SOURCE": 18.103,
   "BUILDING_FEED": 18.016,
   "INITIALIZING": 0.012,
   "REPLAYING": 42.372,
   "FINALIZING": 0.021,
   "VALIDATING": 0.736,
   "GENERATING_REPORT": 0.069
  },
  "phase_wall_s": {
   "QUEUED": 0.068,
   "PREPARING_SOURCE": 0.016,
   "VERIFYING_SOURCE": 18.107,
   "BUILDING_FEED": 18.019,
   "INITIALIZING": 0.015,
   "REPLAYING": 42.375,
   "FINALIZING": 0.024,
   "VALIDATING": 0.739,
   "GENERATING_REPORT": 0.072
  },
  "preparation_active_s": 36.13,
  "terminal_report_active_s": 0.826,
  "replay_events_per_s": 3060.7,
  "counters": {
   "source_verifications": 1,
   "feed_builds": 1,
   "cache_reused": false,
   "cache_build_events": 129690,
   "sort_spill_runs": 14,
   "events_applied": 129690,
   "snapshots_built": 27,
   "state_encodes": 27,
   "transactions_committed": 27,
   "checkpoints_committed": 26,
   "delivery_rows_written": 0,
   "restore_suffix_events": 0,
   "prefix_restore_events": 0,
   "cache_bytes_read": 8919597,
   "cache_partitions_read": 26,
   "checkpoint_state_bytes": 33390,
   "output_bytes": null,
   "max_control_gap_seconds": 0.268,
   "max_rss_bytes": 140881920,
   "max_rss_source": "Windows PeakWorkingSetSize (process lifetime peak)",
   "cpu_seconds": 65.766
  },
  "ranges": 26,
  "delivery_rows": 0
 },
 "warm": {
  "replay_id": "obs-20261003T152908-bfdede",
  "status": "completed",
  "assurance": "passed",
  "events": 129690,
  "cursor": 129690,
  "wall_including_process_spawn_s": 43.812,
  "phase_active_s": {
   "QUEUED": 0.0,
   "PREPARING_SOURCE": 0.073,
   "INITIALIZING": 0.011,
   "REPLAYING": 42.043,
   "FINALIZING": 0.02,
   "VALIDATING": 0.775,
   "GENERATING_REPORT": 0.078
  },
  "phase_wall_s": {
   "QUEUED": 0.042,
   "PREPARING_SOURCE": 0.077,
   "INITIALIZING": 0.013,
   "REPLAYING": 42.046,
   "FINALIZING": 0.024,
   "VALIDATING": 0.778,
   "GENERATING_REPORT": 0.082
  },
  "preparation_active_s": 0.073,
  "terminal_report_active_s": 0.873,
  "replay_events_per_s": 3084.7,
  "counters": {
   "source_verifications": 0,
   "feed_builds": 0,
   "cache_reused": true,
   "cache_build_events": null,
   "sort_spill_runs": null,
   "events_applied": 129690,
   "snapshots_built": 27,
   "state_encodes": 27,
   "transactions_committed": 27,
   "checkpoints_committed": 26,
   "delivery_rows_written": 0,
   "restore_suffix_events": 0,
   "prefix_restore_events": 0,
   "cache_bytes_read": 8919597,
   "cache_partitions_read": 26,
   "checkpoint_state_bytes": 33390,
   "output_bytes": null,
   "max_control_gap_seconds": 0.258,
   "max_rss_bytes": 107933696,
   "max_rss_source": "Windows PeakWorkingSetSize (process lifetime peak)",
   "cpu_seconds": 42.609
  },
  "ranges": 26,
  "delivery_rows": 0
 },
 "pause_restore": {
  "replay_id": "obs-20261003T152952-76443f",
  "status": "completed",
  "assurance": "passed",
  "events": 129690,
  "cursor": 129690,
  "wall_including_process_spawn_s": 22.884,
  "phase_active_s": {
   "QUEUED": 0.0,
   "PREPARING_SOURCE": 0.089,
   "INITIALIZING": 0.099,
   "REPLAYING": 42.355,
   "FINALIZING": 0.022,
   "VALIDATING": 1.048,
   "GENERATING_REPORT": 0.077
  },
  "phase_wall_s": {
   "QUEUED": 0.024,
   "PREPARING_SOURCE": 0.106,
   "INITIALIZING": 0.106,
   "REPLAYING": 42.363,
   "FINALIZING": 0.025,
   "VALIDATING": 1.052,
   "GENERATING_REPORT": 0.08
  },
  "preparation_active_s": 0.089,
  "terminal_report_active_s": 1.147,
  "replay_events_per_s": 3062.0,
  "counters": {
   "source_verifications": 0,
   "feed_builds": 0,
   "cache_reused": true,
   "cache_build_events": null,
   "sort_spill_runs": null,
   "events_applied": 63081,
   "snapshots_built": 14,
   "state_encodes": 13,
   "transactions_committed": 13,
   "checkpoints_committed": 13,
   "delivery_rows_written": 0,
   "restore_suffix_events": 0,
   "prefix_restore_events": 0,
   "cache_bytes_read": 4572256,
   "cache_partitions_read": 13,
   "checkpoint_state_bytes": 33390,
   "output_bytes": null,
   "max_control_gap_seconds": 0.26,
   "max_rss_bytes": 107999232,
   "max_rss_source": "Windows PeakWorkingSetSize (process lifetime peak)",
   "cpu_seconds": 21.5
  },
  "ranges": 27,
  "delivery_rows": 0,
  "pause_applied_s": 0.371,
  "restore": {
   "prefix_restore_events": 0,
   "restore_suffix_events": 0,
   "events_applied_after_resume": 63081,
   "initializing_active_s": 0.099
  }
 },
 "deep": {
  "validation_id": "deep-20261003T153037-f34ec2",
  "status": "completed",
  "outcome": "match",
  "compared": 164,
  "covered": 129690,
  "wall_including_process_spawn_s": 54.948,
  "phase_active_s": {
   "QUEUED": 0,
   "PREPARING_SOURCE": 0.01,
   "VALIDATING": 54.11,
   "GENERATING_REPORT": 0.031
  },
  "events_per_s": 2396.8,
  "max_rss_bytes": 235704320
 }
}
```
