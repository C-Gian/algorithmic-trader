# R1C benchmark gate re-evaluation

> Stored raw measurements from `WP-008-R1C-benchmark.json` (build `d2ee918e03cf9388d9c017060b528413ca10b378`) re-evaluated with the corrected gate inventory. No new measurement was taken; the stored report is unchanged.

_Gate evaluator v2_

### Month application gates (measured end to end)

| Gate | Measured s | Limit s | Run | Result |
|---|---|---|---|---|
| month cached observation | 31.381 | 120.0 | completed/passed | PASS |
| month terminal validation/report | 0.837 | 10.0 | completed/passed | PASS |
| month cold preparation | 36.81 | 120.0 | completed/passed | PASS |

### Annual component comparisons (NOT gates)

| Component | Measured s | Annual limit s | Omits | Result |
|---|---|---|---|---|
| year kernel replay + checkpoint-cadence encoding | 326.31 | 900.0 | no durable job, DB checkpoint transactions or compute-process spawn | COMPONENT_WITHIN_LIMIT |
| year consumed-input re-hash | 6.79 | 30.0 | no actual terminal reconciliation path (ranges/state/receipt checks) and no report generation | COMPONENT_WITHIN_LIMIT |
| year feed-cache build | 157.36 | 900.0 | no source snapshot and no source verification (month: verification ~ build time; a ~2x estimate is not a measurement) | COMPONENT_WITHIN_LIMIT |

### Annual application gates

| Gate | Limit s | Result | Status |
|---|---|---|---|
| year cached observation | 900.0 | NOT_MEASURED | PENDING - no end-to-end year application run was measured; annual readiness is not claimed (component comparisons are not substitutes) |
| year terminal validation/report | 30.0 | NOT_MEASURED | PENDING - no end-to-end year application run was measured; annual readiness is not claimed (component comparisons are not substitutes) |
| year cold preparation | 900.0 | NOT_MEASURED | PENDING - no end-to-end year application run was measured; annual readiness is not claimed (component comparisons are not substitutes) |
