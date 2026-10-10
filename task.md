# Current task — Input provisioning for HDP-001 and A v0.6 (technical path; no real data)
Date: 2026-10-10. Status: **CLOSED by the orchestrator's disposition** ([HDP-001 §8.1](delivery/HDP-001-VERIFICATION-REFERENCES.md) · [A v0.6 §10.1](delivery/A-V06-OPERATIONAL-EVALUATION-REFERENCES.md)).
- The preparatory cycle is closed within the documented limits.
- Future source availability is not attested; the risk is accepted.
- Funding not covered: PRICE_NET_ONLY, already admitted, so no funding decision is required.
- Pre-execution conditions and a separate authorization remain. Studies INACTIVE. Remote CI is Owner-operated: PENDING / NOT CHECKED.

## Assignment (relayed by the Owner, 10 October 2026; expected base `9854f16`)

Complete the technical input path of both studies without acquiring real data.
- **Sources.** Official documentation for history, retention, paging and limits (URL, section, date); documented vs guaranteed availability. Report series that need prior collection or post-window recovery that is not documented.
- **Coverage.** Exact intervals from the registered documents, with no margins.
- **Path.** Reuse acquisition, `marketdata.v1`, pack composition, verification and reading. Document parts, order, identity, provenance, gaps, duplicates, overlaps, conflicts, delivery to the executors and immutable identities. Completeness is verified on content.
- **Tests.** Synthetic: boundaries, gaps, conflicting overlaps, duplicates, identity and coverage delivery.
- **Excluded.** Market-data requests, Owner data, credentials, acquisition, changes to windows, semantics, population or profiles, and to the `be44370` behaviour.

## Previous task — A v0.6 statistical completion (offline bootstrap)
Date: 2026-10-10. Status: DELIVERED — READY FOR DIRECTOR REVIEW — A V0.6 BOOTSTRAP TOOLING ONLY ([references §9](delivery/A-V06-OPERATIONAL-EVALUATION-REFERENCES.md)). **Decision registered; statistical implementation delivered, awaiting the Director's final review; studies INACTIVE.** The orchestrator decision, missing at delivery (`e52f237`), was then relayed and registered verbatim: [decision](delivery/A-V06-STATISTICAL-CONVENTIONS-DECISION.md). Remote CI is Owner-operated: PENDING / NOT CHECKED.

### Statistical completion assignment (relayed by the Owner, 10 October 2026; expected base `b2ebf20`)

Register the orchestrator decision verbatim in a separate `delivery/` document (text not received) and complete the offline bootstrap with synthetic evidence only.
- **Bootstrap.** The full UTC hourly grid; 168 h moving blocks; 10,000 resamples; one `random.Random(0)`; one `randrange(N-L+1)` per block, in resample -> block order; no wrap; truncated last block. The statistic is the sum of the resampled hourly values, with the registered 95% percentile convention. Zeros are only attested null contributions.
- **Protections.**
  - Not attested: no balance, no bootstrap, no reconciled subtotal.
  - Undetermined included path: no balance, no bootstrap, an explicitly partial subtotal only.
  - Attested and determinable: balance and bootstrap, with the interval separate and no verdict.

  The owner journal stays descriptive.
- **Identities.** Full SHAs of `b47b997` and `be44370` and the tool versions, with product and tool identities kept separate.
- **Excluded.** `src/`, method, preset, evaluator, acquisition, Owner data, real evaluation, CI. The design term 2027-01-25T00:00Z is unchanged.

## Previous task — A v0.6 continuous evaluation, technical preparation
Date: 2026-10-10. Status: DELIVERED — READY FOR DIRECTOR REVIEW — A V0.6 STUDY PATH ONLY. **Technically ready** on synthetic evidence only; the **study is not launchable** ([references §8.6](delivery/A-V06-OPERATIONAL-EVALUATION-REFERENCES.md)). Studies INACTIVE. Remote CI is Owner-operated: PENDING / NOT CHECKED.

**Review correction (base `2018634`).** The ledger gives no complete balance or hourly series without attested identity and completeness. It is a ledger-only change ([references §8.8](delivery/A-V06-OPERATIONAL-EVALUATION-REFERENCES.md)): method, preset, population and economic criteria are unchanged, and the bootstrap is not implemented.

### Study path assignment (relayed by the Owner, 10 October 2026; expected base `77420cd`)

Make the full A v0.6 preparation, execution and reporting path technically executable, proven only with isolated synthetic data.
- **Sources.** The design, the orchestrator decision, the references decision, the operational references and `identities-b47b997.json`. Authoritative sources prevail. `b47b997` is the frozen behaviour reference. Pinned documents are not modified.
- **First step.** Reconstruct the existing path and locate the impediments; choose the minimal adaptation of existing tools. No new engine or parallel infrastructure.
- **Window and continuity.** [2027-01-25, 2027-07-26), with the registered initialization and tail. One continuous run, no monthly reset. Technical partitions keep state, order and identity. The tail only completes included paths. No indiscriminate date access; no protected periods.
- **Method and population.** The ordinary v0.6 policy, unchanged. Primary = every A call issued in the window. These are kept apart:
  - pre-existing owners and owners born in the window;
  - non-confirmation and non-issue;
  - included calls and post-boundary issues;
  - NO_ENTRY and undetermined entered paths.

  No imputation and no invented balance.
- **Reporting.** PRIMARY results, price_net or total_net (only with certified funding), per-call results, UTC issue-hour attribution. Hours without a call are 0; undetermined hours are not automatically 0. No HDP-001 conventions. Open statistical conventions go to the Director.
- **Identity and equivalence.** Register the reference, the build, the method, parameters, profile and evaluator, and the synthetic inputs. Map the relevant diff, compare reference and build on the same inputs where applicable, and verify the window extension separately. No general equivalence from a few fixtures.
- **Excluded.** Real feed, Owner data, acquisition, real cache, economic replay, the Owner stack, real evaluations, CI polling. HDP-001 and v0.6 frozen.

## Previous task — HDP-001 verification executor, technical preparation
Date: 2026-10-10. Status: DELIVERED — READY FOR DIRECTOR REVIEW — HDP-001 EXECUTOR ONLY. The executor is prepared only to the extent shown by synthetic tests ([references §7](delivery/HDP-001-VERIFICATION-REFERENCES.md)). **HDP-001 INACTIVE.** Remote CI is Owner-operated: PENDING / NOT CHECKED.

### HDP-001 executor assignment (relayed by the Owner, 10 October 2026; expected base `d5a666b`)

Implement and document an offline HDP-001 verification executor, ready to apply the frozen protocol, verified only with isolated synthetic fixtures.
- **Sources.** The protocol, the Director decision, the exploration closure and the references decision. The operational references are an index only. The temporal semantics and the exploration script are reused, not modified.
- **Scope.** Existing formats and tools. Explicit offline path: no download, service, Owner DB or UI, and no adviser change.
- **Samples.** The frozen window, 2016 cutoffs, the last one BOUNDARY_NOT_SCORED. Complete hours only, with no interpolation. UP fixed. No MarketView, scenario or call selection. FLAT and unavailability per the protocol, with grid and masks kept.
- **Integrity.** Concrete checks; UNAVAILABLE vs NOT_EVALUABLE; no coverage percentage; internal vs external provenance declared.
- **Computation.** Paired cells, accuracies, Delta; the registered bootstrap; duration and zero denominators per the protocol; no A v0.6 convention.
- **Output.** Identities and hashes, coverage, masks, absence distribution, synthetic vs real distinguished, no overwrite, no automatic update of the reference, status or register.
- **Tests.** Few discriminating synthetic cases with hand-derived expectations. The existing framework, no product suites, DB or E2E.
- **Excluded.** Acquiring or consulting verification data or protected periods; running the real study. v0.6 frozen; A technical preparation not activated.

## Previous task — Closure of the study references (documentary only)
Date: 2026-10-10. Status: **Riferimenti registrati; preparazione esecutiva ancora incompleta; studi INACTIVE.** [Decision (verbatim)](delivery/HDP-001-A-V06-REFERENCES-DECISION.md) · [HDP-001 references](delivery/HDP-001-VERIFICATION-REFERENCES.md) · [A v0.6 references](delivery/A-V06-OPERATIONAL-EVALUATION-REFERENCES.md) · [exposure register](delivery/STUDY-EXPOSURE-REGISTER.md). Remote CI is Owner-operated: PENDING / NOT CHECKED.

### Study references closure assignment (relayed by the Owner, 10 October 2026)

Base `aff2a3d`.
- Register the authoritative decision verbatim in a separate addendum linked to the pinned HDP-001 and A v0.6 documents. Do not edit the pinned texts or replace the decision with a summary.
- Update the two operational addenda, separating what is resolved from residual dependencies.
- Designate and create `delivery/STUDY-EXPOSURE-REGISTER.md` with a minimal structure. Columns: study, period, consultation date, material, subject, use in decisions, source. Documented exposures only; gaps stay explicit; never "no exposure" from missing information.
- **Checks.** Text fidelity, links, state coherence; identities recomputed with the existing functions; pinned hashes unchanged; no re-run of the exploration.
- **Operational points.** Close only those already determined by the designs. List the missing computation conventions without completing them.
- **Excluded.** Acquisition, Owner extraction, implementation, running the studies, CI polling, pull/fetch. v0.6 and HDP-001 frozen; protected periods unchanged.

## Previous task — Complete the references of the two frozen studies (documentary only)
Date: 2026-10-10. Status: DELIVERED at `aff2a3d` (superseded by the closure above).

### Study references authorization (Astra, relayed by the Owner, 10 October 2026)

Make the artifacts, rules and residual dependencies of HDP-001 and of the A v0.6 operational evaluation identifiable. Documentary preparation only.
- **HDP-001 (first priority).** Protocol and decisions, exploratory closure and constant UP, frozen window, script and conventions (168 h blocks, 10,000 resamples, `random.Random(0)`, type 7, masks, boundary), verifiable identities of reusable artifacts. Keep the exploratory script distinct from verification instructions; do not modify it.
- **A v0.6.** From the design and closure, identify method, parameters, implementation, evaluator and profile through existing identities and functions. Verify `b47b997` and record full SHAs and hashes. Later UI changes do not make the newest commit the study build. Identities that depend on future data or a non-existent pack are declared for later registration; no invented hashes, no new identity system.
- **Per study.** Separate what is fixed and verified now, future data/hashes, and checks/authorizations still needed. An executor must understand what to use without the chats.
- **Mode.** Update existing documents and STATE/task only as needed; no general dossier or duplicated specifications. Authoritative text stays recognizable; operational additions are separate and labelled; pinned documents are not rewritten. Report any missing convention or conflict touching method, window, population, outcome or frozen reference; do not resolve it implicitly.
- **Excluded.** Acquisition, Owner extraction, running the studies, opening protected periods, CI polling, pull/fetch. v0.6 and HDP-001 frozen.

## Previous task — Historical alerts vs current availability (live cockpit banner and timeline only)
Date: 2026-10-10. Status: DELIVERED — READY FOR DIRECTOR REVIEW — HISTORICAL ALERTS PRESENTATION ONLY ([evidence](delivery/evidence/LIVE-HISTORICAL-ALERTS/NOTE.md)). Remote CI is Owner-operated: PENDING / NOT CHECKED. No further package is activated.

### Historical alerts authorization (Astra, relayed by the Owner, 10 October 2026)

Presentation correction of historical alerts in the banner and timeline only. First verify the defect reported at `f62aa63`: during UNVERIFIED and CLOSED, earlier guidance such as "Entry still valid now" and "entry available inside …" remains. Then correct it.
- Each alert is a recorded event with local date, time and an identifiable time zone. The main message is a past-tense description based on the recorded type.
- The original text stays in the details, labelled "Testo registrato a quell'ora". Any entry band is qualified as relative to the historical event, never as usable now.
- Current availability is read in the main panel, which keeps reading the authoritative state. A missing time shows "Orario non registrato", never the load time.
- No record rewrite, frontend availability inference or new alert expiry. Existing dismiss/acknowledgement commands are kept.
- **Verification.** Reuse `test_live_continuity_e2e`: banner and timeline during UNVERIFIED and CLOSED, before and after reload. The original text stays consultable, and the current panel equals the backend. The v0.2 fixture is allowed, documented as crossing the shared components; do not extend the test to certify v0.6.
- **Excluded.** The transitional "Stopped / Loading…", method, API, persistence, Workbench, Owner data, real feed, economic replay and CI polling. v0.6 and HDP-001 frozen; evaluations INACTIVE.

## Previous task — Cockpit: clarity of the operational state (live cockpit only)
Date: 2026-10-10. Status: DELIVERED — READY FOR DIRECTOR REVIEW — COCKPIT CLARITY ONLY ([evidence](delivery/evidence/LIVE-PROPOSAL-CLARITY/NOTE.md)). Remote CI is Owner-operated: PENDING / NOT CHECKED. No Owner launch is prepared and no further package is activated.

### Cockpit clarity authorization (Astra, relayed by the Owner, 10 October 2026)

Live cockpit only; Workbench excluded. The main panel must answer "Che cosa propone il sistema adesso?":
- **States.** "In attesa — nessun ingresso proposto" / "Ingresso disponibile secondo il sistema" / "Ingresso non più disponibile" / "Non è possibile confermare la disponibilità dell'ingresso". Terminal and non-current keep the existing protections.
- **Source.** Only the backend's authoritative state; no availability inferred from direction, quotes or levels.
- **Without a call.** Direction, the needed condition, the scenario destination and the structural invalidation, never called entry, target or stop.
- **With a call.** Plain LONG/SHORT, the admissible band only when available, the published target and stop, conditions, deadline and the reason for unavailability. Past levels are history only.
- **Kept distinct.** Narrative destination vs operational target, horizon vs deadline, entry availability vs thesis validity, the system's indication vs the user's unknown operation.
- **Presentation.** Grouped, readable on phones, simple Italian, details collapsed, local time with time zone; no probabilities, promises or countdowns; absences declared.
- **Checks.** Fields and states verified first, including CLOSED, UNVERIFIED, terminal and not current, without changing rules.
- **Excluded.** Method, API or persistence changes; Owner data, live feed or economic replay. v0.6 and HDP-001 frozen; evaluations INACTIVE.

## Previous task — Live call history in the live cockpit (product, read-only consultation)
Date: 2026-10-10. Status: DELIVERED — READY FOR DIRECTOR REVIEW — LIVE CALL HISTORY ONLY ([evidence](delivery/evidence/LIVE-CALL-HISTORY/SUMMARY.md)), with the revision-label correction at `e582f38`; synthetic comprehension episode at `1c346ff` ([note](delivery/evidence/LIVE-COMPREHENSION-EPISODE/NOTE.md)).

### Live call history authorization (relayed by the Owner, 10 October 2026)

After the read-only adviser user-path survey at `6710474` (the Owner's visual review was closed as not assessable from the available material, with no interface finding), the Director authorized making the already-recorded history of a single call consultable from the live cockpit:
- identity = session/run + call, never mixing records; reuse of *Guidance revisions* where compatible; minimal presentation adaptation and reading of existing records only;
- revisions in recorded order, explicit UTC times, stored values/changes/reasons only; current vs earlier revisions, no-revision/partial/missing/error, available/not-current/terminal kept distinct; no stale data under a new call/session, including out-of-order responses;
- no reconstructed motivations, no implied Owner entry, no hypothetical economic path in live; read-only, no dedicated continuous polling;
- stop at the boundary if new events, persistence or method semantics were needed. A minimal read-API adaptation was allowed but was not needed.

Not authorized: general restyling, new infrastructure, kernel/rule/parameter/selection/evaluator/method-identity changes, persistence or migrations, live feed, Owner data or stack changes, acquisition or economic replay. v0.6 and HDP-001 stay frozen; studies stay INACTIVE.

## Previous task — WP-015: MP-005 implementation / candidate v0.6
Date: 2026-10-09. Status: DELIVERED — READY FOR DIRECTOR REVIEW — WP-015 ONLY ([evidence](delivery/evidence/WP-015-ENGINEERING-EVIDENCE.md)). Remote CI is Owner-operated: PENDING / NOT CHECKED.

## Preceding record and studies (not active packages; execution INACTIVE)

The read-only four R→N paths diagnosis of `eval-20261009T155751-be8b2b` was delivered at `cb356f2`, with Astra documentary corrections at `3c6af11`; see the STATE.

**HDP-001 — not an active package.** The [protocol](delivery/HDP-001-HOURLY-DIRECTIONAL-PERSISTENCE.md) and its [registration decision](delivery/HDP-001-DIRECTOR-CLOSURE.md) are approved and registered (bootstrap seed 0).
- **Exploration closed.** The Director accepted the [exploration](delivery/evidence/HDP-001-EXPLORATION/SUMMARY.md) at `cf18dbd`, on Astra's independent review ([closure and freeze](delivery/HDP-001-EXPLORATION-CLOSURE.md)). It promotes no signal and shows no economic effectiveness.
- **Verification frozen.**
  - Constant reference UP.
  - Window [2026-11-02T00:00Z, 2027-01-25T00:00Z) ([note](delivery/HDP-001-VERIFICATION-WINDOW-PROPOSAL.md)).
  - Protocol and conventions: 168 h blocks, 10,000 resamples, `random.Random(0)`, type-7 percentiles.
  - Boundary: the last cutoff is kept, and the endpoint equal to the end is not scored.
  - No adaptation, extension, opportunistic stop or interim consultation. Any exposure that influences research decisions must be declared.
- **Execution INACTIVE.** Acquisition and computation after the end need a separate executive assignment.
- v0.6 stays frozen, and January–August 2026 stays protected.

**A v0.6 operational evaluation — not an active package.** The [design](delivery/A-V06-OPERATIONAL-EVALUATION-DESIGN.md) and the [orchestrator decision](delivery/A-V06-OPERATIONAL-EVALUATION-CLOSURE.md) are approved (Astra, relayed by the Owner) and registered verbatim.
- Window [2027-01-25T00:00Z, 2027-07-26T00:00Z) fixed. The pre-start freeze of method, implementation and profile identities (technical reference `b47b997`) is still to be completed and verified.
- **Execution INACTIVE.** No future pack is acquired or certified by the registration. Acquisition, access and execution need a separate assignment.
- v0.6 and HDP-001 unchanged; January–August 2026 stays protected.

## WP-015 authority

- [MP-005 specification](delivery/MP-005-V06-INITIAL-RESPONSE-INCOMPATIBILITY.md) and [Director methodological closure](delivery/MP-005-DIRECTOR-CLOSURE.md): separate documents, registered from the relayed authoritative text.
- **Executive authorization**, recorded verbatim and separately in [WP-015-MP-005-IMPLEMENTATION-SPEC.md](delivery/WP-015-MP-005-IMPLEMENTATION-SPEC.md). The closure alone did not activate work. The authorization covers implementation and synthetic engineering checks only, not economic runs.

## WP-015 assignment (summary; the verbatim text is authoritative)

1. **Registration.** Register spec, closure and authorization separately. Prepare the task, register and v0.6 identities. Keep every inherited numerical value and show only the new categorical elements. Preserve v0.2–v0.5 specifications, identities, outputs and checkpoints.
2. **Scoped implementation.** Only the MP-005 check after the valid preparation of the single RETURN reference:
   - historical: F ∩ corridor ∩ economic region;
   - live: F ∩ corridor only, cost-independent;
   - a single admissible tick is non-empty;
   - inherited protections first;
   - `INITIAL_RESPONSE_INCOMPATIBLE` ends the child, not the scenario;
   - P and X in the same dispatch, never C/R/N/I/A;
   - no renewal, reopening or later local classification.
   
   Reuse the existing formulas. No tolerances, live minimum costs, thresholds or new interpretations.
3. **Integration.**
   - v0.6 selectable in the Workbench and live.
   - Distinct identities and persisted state, with production restore.
   - The reason, diagnostic bases and count identities in JSON, Markdown, Copy report and export.
   - The new count is a subset of X with denominator P, never summed again.
   - WAIT-open cohorts kept, and the C/R loss explained.
   - No 20-RETURN threshold for v0.6.
   - UI: an ended attempt is distinct from an invalidated scenario.
   - Assurance, reconciliation and Deep extended only where needed.
4. **Checks.**
   - Every MP-005 fixture, LONG and SHORT, plus direct live CORRIDOR coverage with a preparable reference.
   - Single tick and edges; precedence; same dispatch.
   - Checkpoint/restore and crash; live temporary cost restriction.
   - Parity with v0.5; previous pins.
   - Reports and copy text; a minimal browser path.
   - Typecheck, build and schemas, on an isolated database.
   - Report counterexamples; never correct silently.
5. **Limits.** No acquisition, Owner extraction, real-data replay or economic backtest/comparison; no automatic Owner launch; no Owner-stack change.
6. **Delivery.** Compact evidence; update STATE and task; commit and push. No CI polling or waiting.
