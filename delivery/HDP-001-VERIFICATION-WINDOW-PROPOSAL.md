# HDP-001 — Verification window proposal (documentary only)

Base `7b5aaf2`. Protocol: [HDP-001](HDP-001-HOURLY-DIRECTIONAL-PERSISTENCE.md) · [Director decision](HDP-001-DIRECTOR-CLOSURE.md). PROPOSAL FOR DIRECTOR DECISION. It opens no window and activates nothing.

**Sources.** Repository documentation only: STATE, README, FOUNDATION, delivery/research specifications and dossiers, parameter registers, presets and corpus plan. No prices, results or statistics of any new period; no DB, acquisition, replay or product change.

## 1. Documented exposures

| Period (UTC) | Exposure / use | Source |
|---|---|---|
| 2025-07-28 → 2025-09-01 | Initialization context of the continuous v0.4/v0.5 runs, never scored. Scenario-journal records from this span are in the R→N diagnosis exports. Also the 96 h warmups (from 08-28) of the monthly presets. | WP-013 protocol, WP-014 plan, R→N dossier |
| 2025-09-01 → 2026-01-01 | Development, fully exposed: Backtest A (Sep), redesign-exposed October, Nov/Dec follow-up, continuous v0.4/v0.5 runs, diagnoses, MarketView tabulation. It is the HDP-001 exploration phase (protocol §7). | STATE, MP-003 disposition, WP-013/014 |
| 2026-01-01 00:00 → 06:05 | Outcome tail of the monthly-December and continuous runs: 365 trade/mark/index 1m bars admitted. 4 h endpoints of the Dec-31 samples fall here, and the extracted `view_sample` records hold the 1 h/4 h returns of the Dec-31 20:00–23:00 samples. | STATE (Q4 diagnosis), tabulation |
| 2026-01-01 06:05 → 2026-09-01 | **Protected** (Director). "Otherwise untouched; no basis for declaring contamination" (Q4 diagnosis). Parameter registers carry `contamination_check_required: true`. | STATE, MP-00x parameters, Backtest A disposition |
| 2026-09-25 → 2026-09-30 | Historical first-trader research RP-001: fetched window and six labelled real cutoffs (Sep 28–29), declared development. | research/first_trader/cases |
| Live operation (from at least the WP-009 handoff, 2026-10-05) | The live cockpit/adviser and recorder sessions run while the Owner's app runs, with ≤96 h startup reconstruction. Session dates are not consolidated anywhere. | STATE, README |

## 2. Is any past period documented as not examined?

**No.** Nothing in the repository affirmatively documents a past period as not examined:
- Sep 1–24 2026 merely has no recorded use.
- Jan–Aug 2026 is protected, not certified unexamined.

## 3. Gaps that prevent certification

1. **No exposure register.** Protocol §7 requires identifying the window through the exposure register. No consolidated register exists; exposures are scattered across STATE and dossiers (table above).
2. **Contamination inventory not documented as done.** The Jan–Aug 2026 inventory is required by the Backtest A disposition and the parameter registers, and it is not documented as performed.
3. **Protected status.** Jan–Aug 2026 is reserved by the Director and stays protected. Opening any part of it for HDP-001 would expose it for later protected checks, which is a Director decision outside this task.
4. **Unregistered or unknown exposure.**
   - Live/recorder session dates (Sep–Oct 2026) are not registered.
   - Any pre-clean-room exposure is not documented in the repository.
   - The literature reaches into 2026: `source_notes/LIB-010` monthly time-series-momentum data through May 2026. This is literature, which protocol §7 excludes, but it is declared here.
5. **Data availability.**
   - Packs documented as prepared: the September pack (`pack-427d5f5d…`) and the continuous Sep–Dec preset pack `pack-1ae7d36c…` (initialization 2025-07-28 → tail 2026-01-01 06:05, per the WP-014 plan).
   - The Jan–Aug 2026 months appear only as planned chunks in `corpus/plan.json`; no acquisition is documented.
   - Sep 2026 lies outside the corpus target.
   - Any past window would therefore need a new, separately authorized acquisition.

## 4. Candidate window (future, after the definitive freeze)

**[2026-11-02T00:00:00Z, 2027-01-25T00:00:00Z)**: 12 weeks, Monday 00:00 to Monday 00:00, **2016 hourly cutoffs**.

**Validity conditions, fixed now:**
- **Before the start**, all of the following must be committed:
  - the HDP-001 exploration on Sep–Dec 2025 is computed;
  - the constant reference is frozen;
  - the Director authorizes this window;
  - HDP-001 and v0.6 are unchanged.
- **If any condition is missing at the start,** the window is void and a new one is proposed. It is never shifted or shortened after its start.
- **During the window:**
  - no HDP-001 computation or outcome consultation;
  - no interim look and no early stop;
  - the Owner's ordinary live use of the app is general real-time market exposure, declared and not a project decision.
- **Boundary:**
  - per §2, the cutoff 2027-01-24T23:00 (endpoint = end) is BOUNDARY_NOT_SCORED;
  - history before the start (from 2026-11-01T22:00 for the first C_(t-1)) may build the first prediction only.
- **Data:**
  - same instrument and price role as the exploration: OKX BTC-USDT-SWAP trade 1m, historical and modeled-available;
  - fetched only after the end, under a separate authorization;
  - the live recorder is not a substitute.

**Why this duration.**
- The protocol floor is two non-overlapping 168 h blocks (336 h). Twelve weeks gives 12 non-overlapping blocks, so the moving-block bootstrap draws from many distinct weeks rather than a handful.
- It is the same order as the exploration (2928 h, about 17 weeks), while concluding about three months from now.
- It is a calendar choice made with no exploration or verification result, and no power calculation (which would need results).
- It is not optimized and does not guarantee a conclusive interval.
- The holiday weeks inside it are declared and are no reason to move it.

**Why not a past window.**
- Jan 1 06:05 → Aug 31 2026: gaps 1–3 and 5 in §3.
- Sep 1–24 2026 (576 h, 3.4 weeks): gaps 1, 4 and 5 in §3, and too short for more than three weekly blocks.

## 5. Director clarifications (recorded 2026-10-10, with the exploration authorization)

- Failing to certify non-exposure does not show that the protected periods are contaminated.
- Any live use observed must be declared. If it influences research decisions, it is relevant exposure.
- The candidate window stays [2026-11-02T00:00Z, 2027-01-25T00:00Z). It is not acquired or activated; the final freeze follows the review of the exploration and comes before the start.

HDP-001 execution stays INACTIVE; this proposal does not authorize opening the window. v0.6 stays frozen; January–August 2026 stays protected.
