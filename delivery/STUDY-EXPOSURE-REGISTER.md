# Study exposure register

Common register of the exposures of the frozen studies (HDP-001, A v0.6 operational evaluation). It was designated by the [decision on the study references](HDP-001-A-V06-REFERENCES-DECISION.md) and created 10 October 2026 on base `aff2a3d`.

## How entries are kept

- **What qualifies.** Only exposures documented in the repository (or declared later with a source) are recorded. Each row cites its source.
- **Unknown values.** A field that is not documented says "not documented". Absence of information is never recorded as "no exposure".
- **Append only.** Rows are added, never edited to change history. A correction is a new row that refers to the earlier one.
- **No new data.** This register is built from documents only.
- **Dates.** "Consultation date" is the date of the documented record (usually its commit), unless a more precise date is documented.
- **Subject.** Who consulted the material: Owner, executor, Director, or Astra.

## Documented exposures

| # | Study | Period concerned (UTC) | Consultation date | Material consulted | Subject | Use in decisions | Source of the declaration |
|---|---|---|---|---|---|---|---|
| 1 | A v0.6 (method lineage v0.2–v0.6) | 2025-08-28 → 2025-10-01 06:05 (warmup, September, tail) | 2026-10-05 (`26d521e`, `8794805`) | Owner Backtest A on the September pack: report and dossier | Owner (app run), executor (dossier), Director (review) | Cited as evidence by the MP-002 proposal (v0.3 lineage, inherited by v0.6) | STATE; `evidence/WP-009-OWNER-BACKTEST-A*` |
| 2 | A v0.6 (method lineage) | October 2025 | 2026-10-06 (`e33c4c3`) | Owner October run diagnosis | Owner, executor, Director | Development evidence; the window proposal calls October "redesign-exposed" | STATE; `evidence/WP-011-OWNER-OCTOBER-DIAGNOSIS` |
| 3 | A v0.6 (method lineage) | October–December 2025 | 2026-10-07 (`091df18`) | Owner Q4 v0.4 runs and read-only diagnosis | Owner, executor, Director | Development evidence (Q4 dossier closure) | STATE; `evidence/WP-012-OWNER-Q4-DIAGNOSIS` |
| 4 | A v0.6 (method lineage) | 2025-07-28 → 2026-01-01 06:05 (35-day initialization, Sep–Dec, tail) | 2026-10-07 (`e07bbe0`) | Continuous v0.4 run and diagnosis | Owner, executor, Director, Astra (F1–F4 review) | Development evidence preceding MP-004 (v0.5); a direct citation in MP-004 is not documented | STATE; `evidence/WP-013-CONTINUOUS-V04-DIAGNOSIS` |
| 5 | A v0.6 (method lineage) | 2025-07-28 → 2026-01-01 06:05 | 2026-10-09 (`cb356f2`) | Continuous v0.5 run `eval-20261009T155751-be8b2b` and the four R→N paths diagnosis | Owner, executor, Director, Astra (documentary correction) | Development evidence preceding MP-005 (v0.6); MP-005 approves "coerenza del comportamento e della diagnosi" without citing the run by id | STATE; `evidence/WP-014-OWNER-V05-RN-DIAGNOSIS` |
| 6 | HDP-001 | 2025-09-01 → 2026-01-01; the 1 h/4 h returns of the Dec-31 20:00–23:00 samples reach 2026-01-01 03:00 | 2026-10-10 (`ced7b2f`) | One read-only extraction of the 2928 `view_sample` rows of run v0.5; MarketView +1h vs persistence tabulation | executor (extraction, tabulation), Owner (started the DB container), Director (descriptive closure) | Diagnostics seen before the HDP-001 hypothesis was chosen (protocol §7 declares this chronology) | STATE; `evidence/MARKETVIEW-PERSISTENCE-TABULATION`; [window proposal](HDP-001-VERIFICATION-WINDOW-PROPOSAL.md) §1 |
| 7 | HDP-001 | 2025-09-01 → 2026-01-01 (endpoint of the last scored cutoff 2025-12-31T23:00 excluded) | 2026-10-10 (`cf18dbd`) | HDP-001 exploration on `samples.csv` (persistence and +1h outcome fields) | executor (computation), Astra (independent review), Director (acceptance) | Constant reference UP chosen and frozen; verification frozen | [exploration closure](HDP-001-EXPLORATION-CLOSURE.md); `evidence/HDP-001-EXPLORATION` |
| 8 | Project (relevance to these studies not assessed) | 2026-09-25 → 2026-09-30 | 2026-09-30 (`852ee08`…`a43dc45`) | Historical first-trader research RP-001: fetched window and six labelled real cutoffs | executor, Director | Declared development evidence (FOUNDATION §3) | [window proposal](HDP-001-VERIFICATION-WINDOW-PROPOSAL.md) §1; `research/first_trader` |
| 9 | HDP-001 — **correction of row 7** (period description only; every other field of row 7 unchanged) | 2025-09-01 → 2026-01-01. Last scored cutoff 2025-12-31T22:00Z, its endpoint 2025-12-31T23:00Z included; cutoff 2025-12-31T23:00Z BOUNDARY_NOT_SCORED, its endpoint 2026-01-01T00:00Z excluded. Replaces row 7's "endpoint of the last scored cutoff 2025-12-31T23:00 excluded" | as row 7 | as row 7 | as row 7 | as row 7 | Correction relayed by the Owner, 10 October 2026; consistent with the exploration [SUMMARY](evidence/HDP-001-EXPLORATION/SUMMARY.md) (BOUNDARY_NOT_SCORED 2025-12-31T23:00) |

## Known gaps (not declarations of absence)

- **Live operation.** The live cockpit/adviser and recorder sessions run whenever the Owner's app runs, at least from 2026-10-05, with up to 96 h startup reconstruction. Session dates and what was looked at are not consolidated anywhere. The window proposal's Director clarifications state that live use must be declared, and is relevant exposure if it influences research decisions.
- **January–August 2026.** This period is protected. Apart from the outcome tail to 2026-01-01 06:05 (rows 4–6), the repository documents no consultation. It is not certified unexamined, and the contamination inventory required by the parameter registers is not documented as done.
- **Study windows.**
  - HDP-001: [2026-11-02T00:00Z, 2027-01-25T00:00Z).
  - A v0.6: initialization from 2026-12-21T00:00Z; window [2027-01-25T00:00Z, 2027-07-26T00:00Z); tail to 06:05Z.

  No consultation is documented as of this creation, and none could yet have occurred for these future periods. Later live use during them must be declared here.
- **Pre-clean-room exposure** is not documented in the repository.
- **Literature.** `source_notes/LIB-010` reaches May 2026. Protocol §7 excludes literature from "not examined by the project", but the window proposal declares it.
- **Rows 1–5.** They record the dates of the evidence commits. Exact per-consultation dates, and every viewer of each report, are not documented.
