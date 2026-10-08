# WP-014 — Continuous v0.4 / v0.5 comparison, September–December 2025: prepared plan

Date: 2026-10-08. Status: **PREPARED — INACTIVE.** It becomes READY FOR OWNER BACKTEST only after the Director's technical acceptance of WP-014 and green CI on the exact pushed SHA. The executor launches nothing; the Owner alone starts the candidate from the app.

Authority: [WP-014](WP-014-MP-004-IMPLEMENTATION-SPEC.md), [MP-004](MP-004-V05-RETURN-RESPONSE.md) and its [closure](MP-004-DIRECTOR-CLOSURE.md); windows and pins of the [WP-013 protocol](WP-013-CONTINUOUS-REFERENCE-PROTOCOL.md). This plan authorizes no method change and adds no reading criterion: the reading criteria of the v0.5 comparison are Director-owned and are not registered here.

## 1. Inputs (unchanged, already available)

| Item | Value |
|---|---|
| Preset | `btc-2025-09-to-2025-12-continuous-init35d-v1` (identity `fabd1c55…2dbc`) |
| Windows | initialization 2025-07-28 → 2025-09-01 (35 days, not evaluated); evaluation 2025-09-01 → 2026-01-01; tail to 2026-01-01 06:05 |
| Pack | `pack-1ae7d36c20adbde0a468a7e0f6d8750a9951aa8e`, already prepared on the Owner's machine: **no acquisition, no re-preparation** |
| Baseline | v0.4 run `eval-20261007T182934-3f41ad` (replay `obs-20261007T182934-f8c3d4`, build `97a2a8c`), Director-accepted as descriptive development evidence on 7 October 2026 |
| Candidate | v0.5 (`btc.context-action.v0.5` / `mp004.rules.v0.5`, implementation `adviser.core.v5`), PRIMARY 60 s, same profile and evaluator v3 |

## 2. Baseline reuse — pin compatibility check (before any reading)

The v0.4 baseline is reused **only if** every check below holds; otherwise the Director decides (a fresh v0.4 run on the same pack is the only alternative, and it is also Owner-launched).
1. **Same inputs.** The read-only comparison (Workbench step 3, *Compare two adviser runs*, A = the v0.4 baseline, B = the v0.5 run) reports **COMPARABLE**: same pack id and manifest, feed content identity, availability and clock policy, tick and channels, evaluation window and clock end, capability profile and evaluator terms (delays, costs, funding treatment).
2. **Same v0.4 release.** The comparison's *Pinned release vs current package* row shows **MATCHES_CURRENT_PACKAGE** for A: the baseline's model, rules version, rules/register hashes and implementation equal the v0.4 release packaged at the accepted WP-014 SHA. WP-014 changes no v0.4 identity or output (53 fixed v0.4 fixtures reproduce the base `776752e` byte for byte); a build-commit difference alone is not a pin difference.
3. **Both runs clean.** Both runs COMPLETED with runtime assurance PASSED, total/monthly reconciliation passed and no REPORT INCOMPLETE (WP-013 rule 1 applies to both).

## 3. Owner action (only after activation)

1. Workbench → step 2 *Check data and engine*: data = the September–December continuous pack; run type *Adviser evaluation*; method **Candidate v0.5 — RETURN waits for a local recovery** (the pin badge shows *MP-004 v0.5*); speed max (0); Start.
2. When COMPLETED: **Copy report for chat** (total and monthly MP-004 §7 table, identities, cross-checks, launch pins).
3. Step 3 *Compare two adviser runs*: A = `eval-20261007T182934-3f41ad` (v0.4), B = the new v0.5 run → **Copy comparison for chat**. Check the release-pin row and COMPARABLE first (§2).
4. Paste both copies to the Director chat. Nothing else (no Deep validation, no other preset, no protected month).

**Expected time.** The v0.4 continuous run on the same pack is the reference; v0.5 changes only the A RETURN child and adds bounded per-wait state, so a comparable duration is expected. This is an estimate from the unchanged plumbing, not a measured v0.5 real-month time.

## 4. What the comparison can and cannot say

- It is an **integrated version comparison** on identical inputs: v0.5 differs from v0.4 only in the A RETURN child, but a RETURN call issued later or not at all changes slot use, so later selections and outcomes can differ downstream; differences are not per-call attributions.
- §7 counts (W, P, C, R, N, I, X, A and their ratios) describe the response mechanism; C/P does not measure real deterioration and R/P does not measure continuation quality. Fewer stops or fewer calls are not improvement by themselves.
- Sep–Dec 2025 is exposed development data (the v0.4 diagnosis motivated MP-004); January–August 2026 stays protected except the documented tail.
