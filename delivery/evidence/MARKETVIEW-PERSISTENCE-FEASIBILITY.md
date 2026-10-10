# MarketView +1h vs last-hour persistence — feasibility check (no result computed)

Base `b47b997`. Run `eval-20261009T155751-be8b2b` (replay `obs-20261009T155751-0f255b`, `btc.context-action.v0.5`, evaluator `adviser.evaluator.v3`). Method v0.6 frozen. No identity with v0.6 MarketView is assumed. READY FOR DIRECTOR REVIEW — FEASIBILITY ONLY; not accepted.

**Access actually used:**
- repository code (`adviser/evaluator.py`, `evaluator3.py`, `evaluation_contracts.py`, `report.py`, `report_periods.py`, `runtime.py`, `adviser/api.py`, `evaluation/api.py`, `db.py`);
- the existing local GET exports of the R→N diagnosis, outside Git. Their SHA-256 equal `WP-014-OWNER-V05-RN-DIAGNOSIS/paths.json` `input_sha256`.

No app GET call, DB access, price-cache copy, replay or network.

## Where the samples are

`EvaluatorV3.after_dispatch` takes one sample per UTC hour after every dispatch update at that hour. Each sample is persisted as one `view_sample` record (`ViewSample`, public contract), with seq/digest/chain, in `adviser_evaluation_records`. **No GET surface returns `kind='view_sample'` rows.** Of that table, `/api/adviser/runs/*/calls` exposes only `path` rows; `/journal` reads `adviser_journal`. The local exports hold only report aggregates. The report's persistence aggregate is unpaired: 1434/2928, over all samples, not restricted to UP/DOWN views.

## Field → source → availability

| Field | Source | Status |
|---|---|---|
| sample time = causal cutoff | `view_sample.sample_time` (after all dispatch updates at h) | STORED (DB only) |
| sample identity | `record_id = sample-<time>`, seq, digest, chain | STORED (DB only) |
| feed cursor of the sample | not recorded | ABSENT (non-blocking: the time is the cutoff) |
| MarketView label | `view` UP/DOWN/BALANCED/UNCERTAIN/UNAVAILABLE (no-dispatch hour → UNAVAILABLE) | STORED (DB only) |
| conditional flag, principal scenario | `conditional`, `scenario_id` | STORED (DB only) |
| alternatives/levels of the view | not in the sample; only in the journal's `market_view` records | ABSENT from sample (not needed) |
| anchor price | `anchor_price` = last complete 1m close known at h | STORED (DB only) |
| +1h endpoint, sign, availability | `outcome_1h` UP/DOWN/FLAT, `return_1h`; `None` = endpoint minute missing | STORED (DB only) |
| persistence sign | `persistence` = sign(last complete 1h close − previous contiguous 1h close) at h; FLAT explicit; `None` = unassessable | STORED (DB only) |
| antecedent activated by +1h / +4h | `antecedent_activated_1h/4h` (bool; `None` without scenario) | STORED (DB only), limited |
| activation time, and already-active vs activated after the cutoff | CONFIRM `env.published_at` / `confirmed_at` by `scenario_id` in the local scenario journal (2003 records, 571 BIRTH = 571 TERMINAL, 138 CONFIRM, last page partial) | DERIVABLE once per-sample `scenario_id` is available |
| owner, repeated samples | `owner_id` (BIRTH/OWNER_RELEASE) by `scenario_id`; repeats visible through equal `scenario_id` | DERIVABLE (same condition) |
| scenario terminals | TERMINAL `terminal_state`/time in the local scenario journal, used only as later outcomes | DERIVABLE (same condition) |
| expected population | 2928 = 122 days × 24; by_view U93/D65/B655/UNC2115; directional 158; unavailable view 0; endpoint unavailable 0 (report) | STORED (aggregates, local) |

## Blocking gap (only one)

The 2928 per-sample `view_sample` records of this run are reachable only by DB or by a new GET/export. Neither is authorized in this assignment, so this check did not use them. Every field the comparison needs is already in those records. No prospective data is missing.

## Non-blocking limits to declare in the tabulation

- **Activation flag.**
  - The stored flag puts "already CONFIRMED at the cutoff" and "confirmed in (h, h+1h]" in the same class. It also puts confirmation after +4h in the same class as never confirmed.
  - CONFIRM records alone can mistime an attempt: the minute is processed before the same dispatch's journal (`runtime.py` 157–162). So a CONFIRM published exactly at h+4h is missed by the 4h flag.
  - The join with the scenario journal separates all these cases. The +1h flag has no boundary loss, because the sample is still pending at h+1h.
- **FLAT cells.** FLAT outcomes and FLAT persistence must stay as their own cells. The existing aggregates count a FLAT outcome as a non-match and drop FLAT persistence.
- **Scope.** v0.5 run only. A statement about v0.6 would need its own run.

## Feasibility

- **Full reconciliation, including abstentions and missing endpoints:** yes, once the records are available. Use seq/chain, with the report aggregates as checks.
- **Pairing view and persistence on the same sample:** yes; both fields are on one record.
- **Repeated samples of the same owner visible:** yes, through `scenario_id` and the local journal.
- **Activation within +1h vs later:** yes, with the join; the stored flag alone is not enough.

**Recommendation: B.** The tabulation is possible with explicit limits, after the Director authorizes one access path:
- a single REPEATABLE READ READ ONLY extraction of `adviser_evaluation_records` with `run_id = 'obs-20261009T155751-0f255b' AND kind = 'view_sample'` (2928 rows expected);
- or a product GET/export, which is a scope change.
