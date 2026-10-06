# Owner October 2025 comparison — read-only diagnosis

Date: 2026-10-06. Scope: the Director's bounded diagnosis of the paired October comparison. It covers three questions: the disappeared v0.2 LONG, the six v0.3 A confirmations and the three RETURN waits. This is executor evidence, **not Director acceptance**. No replay, backtest, Deep validation, download, sweep, parameter change, product-code change or Owner-stack action was performed.

| | v0.2 (`btc.context-action.v0.2`) | v0.3 (`btc.context-action.v0.3`) |
|---|---|---|
| Evaluation / run | `eval-20261006T173330-4e7c36` / `obs-20261006T173330-62d684` | `eval-20261006T175135-9ddf6d` / `obs-20261006T175135-e8267a` |
| Build | `bd5d81c…+image` | `bd5d81c…+image` |
| Status / assurance | COMPLETED; reconciliation v5 PASS 20/20 | COMPLETED; reconciliation v6 PASS 21/21 |
| Pack / cache | `pack-30c0661f…` / `fc-de5aa4a9…` (common) | same |

Files:
- [dossier.json](dossier.json): provenance, report reconciliation, all three questions and the rule scope;
- [confirmations.csv](confirmations.csv): the 6 confirmations;
- [wait_minutes.csv](wait_minutes.csv): 67 rows, one per minute of the three waits;
- [extract_diagnosis.py](extract_diagnosis.py): the one-off extraction. It reads only the local export and uses the product's pure `geometry` functions and report builders on stored rows.

Labels:
- **STORED** = a committed journal or evaluation field.
- **DERIVED** = exact Decimal arithmetic on STORED fields, or on pinned 1m trade bars no later than the row's stated cutoff.

## Provenance and reconciliation

- **DB.** One `REPEATABLE READ READ ONLY` psql transaction in the Owner `db` container (`transaction_read_only=on`, snapshot `540150:540150:`). It selected only the two evaluation, replay, checkpoint and finish rows (adviser blob excluded), both journals (7,094 + 7,213 rows) and both evaluation-record sets (748 + 744). The export and a byte copy of the pinned cache stay outside Git, in the session scratchpad.
- **Journals and evaluation records.** Every digest and chain was re-hashed. Both runs equal their finish commitments.
- **Cache.** Manifest SHA-256 `ad75110b…1716` equals the pin of both runs. All 31 partitions verified; 50,765 trade minutes.
- **Report counts.** They were rebuilt with the app's own builders (`report.build` for v0.2, `report3.build` for v0.3, selected from each run's stored engine descriptor exactly as `evaluation/api.py` does). They reproduce the Owner's comparison:
  - v0.2: 1 issued call;
  - v0.3: 0 issued; 6 A confirmations, D=6, N=3 (N/D 0.5000);
  - v0.3 routing: RETURN_WAIT 3, NO_ECONOMIC_RETURN_REGION 2, PRE_ENTRY_TARGET_CONTACT 1;
  - v0.3 waits: 3 opened, 0 usable returns, 1 cap revision; endings ORIGINAL_SETUP_DEADLINE 1, PRE_ENTRY_TARGET_CONTACT 1, SCENARIO_TERMINAL 1.
- The extraction is byte-reproducible (two runs, identical hashes).

## 1. Why the 26 October A LONG disappeared

The episode is the same structural object in both runs:
- birth at 23:00 with identical impulse A 112835, impulse B 115759.3, S15 199.2 and z 19.92 (v0.2 attempt `…-c846b443f534`, v0.3 scenario `…-3ae176455221`);
- arm at 23:15 with identical R 114363.2, K 114940.6 and V 114343.28 = R − z (STORED).

| Dispatch (UTC) | Pinned 1m evidence (DERIVED) | v0.2 (STORED) | v0.3 (STORED) |
|---|---|---|---|
| 23:16–23:29 | 14 minutes starting 23:15–23:28: lows > V 114343.28, closes < K+tick 114940.7 | ARMED | ARMED |
| **23:30** | minute [23:29,23:30): **low 114329.5 ≤ V 114343.28**, the first V contact after arm. The 15m bar [23:15,23:30) closes: low 114329.5, high 114540.5 | `REVISE LOWER_CLEAN_REACTION_REANCHOR`: R 114329.5, K 114540.5, V 114309.58 | `TERMINAL INVALIDATED V_CONTACT:…obs@23:29`; entry attempt `SCENARIO_TERMINAL:INVALIDATED:V_CONTACT`; discovery owner released |
| 23:34 | minute [23:33,23:34): close 114599.9 ≥ 114540.6, low 114533.2 > V 114309.58 | trigger → `ISSUE` A LONG: target 115739.3 (own impulse-B near edge), stop 114309.5, gain 99.4 bps, risk 25.3 bps, margin +38.2 bps, no blockers | nothing (scenario already terminal) |

**Decisive divergence.** It is the 1m interval [23:29,23:30), admitted at the 23:30 dispatch together with the 15m close.

- **v0.3.** The minute is tested against the V active at its start, *before* newly complete revisions. This follows MP-002 §3 ("after arm, contact with frozen current V in an eligible complete 1m interval invalidates the scenario") and §6 collision order (2) before revisions: "a later revision cannot erase a contact with the V active for an earlier admitted interval. Newly complete derived revisions are applied only after such contact processing."
  - Code: `core3.dispatch` calls `_scen_intervals` → `V_CONTACT` before `_a_close` → `REVISE`.
- **v0.2.** MP-001 §98 lets "a lower clean R>A+z … revise anchor/K/V" before trigger. v0.2 checks V only on a confirming minute or an arm-straddling bar (`core._triggers`). The 23:29 contact is therefore not an event, and the 15m close re-anchors V below the contact.

**Not dislocation.**
- v0.3's last stored dislocation observation before the episode is `TRADE_INDEX:NORMAL/TRADE_MARK:NORMAL` (10 Oct 21:55). Observations are published only on category change.
- The scenario ended for V contact before any entry gate was evaluated. No dislocation, calendar, context or economic gate takes part in the divergence.

**Afterwards.** The next v0.3 A LONG birth was at 01:30 on 27 Oct. It was spent before reaction, as was v0.2's attempt born at the same boundary. For the record (STORED), the v0.2 call stayed ongoing to its hard deadline. PRIMARY path: GUIDANCE_TIME_EXPIRED, entry 114623.4, exit 114899.7, price_net ≈ +0.10%.

**Scope of this rule difference in October (STORED counts, [dossier](dossier.json) `q1_rule_scope`).**
- v0.2 made 55 A revisions in the window. 49 of them (29 distinct attempts) set the new reaction at or through the V armed before it. On that path every minute is wholly after arm, so a 1m V contact necessarily came first.
- Those 29 v0.2 attempts ended:

  | End | Attempts |
  |---|---:|
  | Context/adverse-expansion withdrawal | 14 |
  | Rejected: REWARD_RISK_BELOW_MINIMUM | 10 |
  | Rejected: NO_ROOM_AFTER_COSTS | 2 |
  | Rejected: AT_OPPOSING_AREA | 1 |
  | Withdrawn: close at/beyond A+z | 1 |
  | **Issued (the 26 Oct call)** | **1** |

- v0.3 records 30 A pre-confirmation V-contact terminals and only 2 A revisions.
- The only v0.2 call of October came through exactly the path that MP-002 closes.

## 2. The six v0.3 A confirmations

STORED unless noted. Prices are in USDT. T_confirm is the conservative target at the confirmation close.

| # | Confirmed (UTC) | Dir | R / K_trigger / V | Close | T_confirm (source) | G / Q / margin (bps) | I0 · corridor · fixed-K economics | Routing | Final reason |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 10-01 10:18 | LONG | 115906.5 / 116314.8 / 115883.2 | 116333 | 116564.7 (own impulse B 116588 − z) | 19.92 / 38.66 / −57.28 | 116279.6..116386.4 · 115906.5..116314.8 · 115906.5..116030.5 | WAIT (RR below min) | ORIGINAL_SETUP_DEADLINE 11:00 |
| 2 | 10-06 02:48 | LONG | 123414.7 / 123880.4 / 123385.0 | 123900.1 | 124153.4 (own B 124183.1 − z) | 20.44 / 41.57 / −60.24 | 123815.8..123984.4 · 123414.7..123880.4 · 123414.7..123561.2 | WAIT (RR) | SCENARIO_TERMINAL: DESTINATION_REACHED 02:50 |
| 3 | 10-07 03:24 | SHORT | 124509.8 / 124186.2 / 124532.9 | 124184.1 | 124108.1 (own B 124085 + z) | 6.12 / 28.09 / −58.38 | 124126.6..124241.6 · 124186.2..124509.8 · **empty** | TERMINAL | NO_ECONOMIC_RETURN_REGION |
| 4 | 10-19 14:19 | LONG | 107833 / 108119.9 / 107799.5 | 108129.6 | 108134.5 (own B 108168 − z) | 0.45 / 30.53 / −66.98 | 108045.9..108134.4 · 107833..108119.9 · **empty** | TERMINAL | PRE_ENTRY_TARGET_CONTACT |
| 5 | 10-25 08:52 | LONG | 111500 / 111643.9 / 111486.9 | 111649.8 | 111766.5 (own B 111779.6 − z) | 10.45 / 14.59 / −37.86 | 111614.5..111685.1 · 111500..111643.9 · **empty** | TERMINAL | NO_ECONOMIC_RETURN_REGION |
| 6 | 10-30 18:36 | SHORT | 107624 / 107129.9 / 107669.1 | 107111.1 | 106794.6 (15m pivot low 106747.3 + z; same price as its impulse B) | 29.55 / 52.10 / −63.77 | 106992.9..107229.3 · 107129.9..107624 · 107422.0..107624 | WAIT (RR) | PRE_ENTRY_TARGET_CONTACT 18:59 |

DERIVED checks. All six rows reproduce exactly:
- predicate at the confirmation close and stored fixed-K economics, from the product's `geometry` functions;
- fixed-K bounds:
  - #3: SHORT lower bound 124514.2 > corridor top 124509.8, so empty;
  - #4: LONG upper bound 107800.8 < corridor bottom 107833, so empty;
  - #5: 111457.9 < 111500, so empty;
- #4's confirmation minute [14:18,14:19): high 108167.9 ≥ T 108134.5. MP-002 §5 routing puts the target contact before the economic test, so PRE_ENTRY_TARGET_CONTACT is the recorded reason, with NO_ROOM_AFTER_COSTS also listed.

Context (STORED):
- In every case the scenario's own narrative destination was later contacted. Delay after confirmation: 93, 2, 2, 1, 9 and 24 min.
- In 5/6 cases T_confirm is the scenario's own impulse-B near edge. In those 5 cases the confirmation close sat 0.45–20.4 bps short of it (#6: 29.6 bps to its pivot-zone target).
- v0.2 rejected the attempt born at the same boundary in all six cases at its trigger (REWARD_RISK_BELOW_MINIMUM 3, NO_ROOM_AFTER_COSTS 3).
- No case was routed IMMEDIATE.

## 3. The three RETURN waits, minute by minute

The full table is [wait_minutes.csv](wait_minutes.csv) (cutoff = each wait's terminal dispatch). BLOCKERS records are journaled only when the blocker set changes. Every sampled minute was therefore reconstructed. The DERIVED price blockers (corridor membership plus the product predicate at the close against the cap active at that dispatch) **equal the STORED blocker set in force in 64/64 sampled minutes**. No zone, TOO_LATE, context, calendar, dislocation or data blocker was ever active in any wait.

**Wait 1 — LONG, 1 Oct, confirmed 10:18, setup expiry 11:00.**
- Required: a minute close in 115906.5..116030.5, i.e. back near the reaction low R. The confirmation close was 116333; the region edge was −26.0 bps from it.
- Observed: 41 return samples. 40 closes were inside the structural corridor but **0 inside the economic region**. Best close 116168.5 (11.9 bps above the edge); lowest low 116145, so the region was never touched even intrabar.
- 10:45 cap revision (STORED): a newly eligible 15m pivot-high zone (near edge 116478.705) lowered the cap 116564.7 → 116478.7. The economic edge fell to 115991.4. The interval [10:44,10:45) did not touch the new cap, so there was no activation ambiguity.
- Close: 11:00 `ORIGINAL_SETUP_DEADLINE`. The expiry check precedes return gates, so the minute [10:59,11:00) is not sampled. There was no V, cap or destination contact during the wait. The scenario itself reached destination 116588 at 11:51, after the wait was closed.
- **Price was never admissible; the wait expired.**

**Wait 2 — LONG, 6 Oct, confirmed 02:48.**
- Required: a close in 123414.7..123561.2 (−27.4 bps from 123900.1).
- Observed: one sample. Minute [02:48,02:49) closed at 124076.8, above the corridor: CLOSE_OUTSIDE_RETURN_CORRIDOR plus NO_ROOM_AFTER_COSTS.
- Minute [02:49,02:50) reached high 124195.6. That is at or beyond both the entry cap 124153.4 and the scenario destination 124183.1.
- Per MP-002 §6 order, scenario contacts (step 2) precede the child's cap contacts. The scenario ended DESTINATION_REACHED and the wait ended `SCENARIO_TERMINAL:DESTINATION_REACHED`.
- **Price moved straight away to the target side; it never became admissible.**

**Wait 3 — SHORT, 30 Oct, confirmed 18:36.**
- Required: a close in 107422.0..107624, i.e. a bounce of +29.0 bps from 107111.1.
- Observed: 22 samples. 3 closes were inside the corridor (18:47, 18:48, 18:51) but below the region, so only REWARD_RISK_BELOW_MINIMUM applied. The other samples were outside the corridor (blocked by CLOSE_OUTSIDE plus RR or NO_ROOM). Best close 107151.3 (25.3 bps short); highest high 107192, so the region was never touched intrabar.
- Minute [18:58,18:59): low 106793.1 ≤ cap 106794.6. Result: `PRE_ENTRY_TARGET_CONTACT`. The scenario destination 106747.3 was touched in the next minute, so the scenario ended DESTINATION_REACHED at 19:00.
- **Price was never admissible; target-side contact ended the wait.**

No wait ended for V contact, a cost change, slot/priority or selection. In all three cases the economic region was the part of the corridor nearest R: the bottom 30% (#1), 31% (#2) and top 41% (#3). Each required a deep retracement back toward the reaction extreme. Price instead stayed near, or ran past, the conservative target.

## Conformity, defects and limits

**Conformant to MP-002 and the build code (as observed).**
- Pre-confirmation V-contact invalidation and its precedence over revisions (§3, §6).
- Exhaustive routing at confirmation, including target contact before economics (§5).
- Fixed-K historical NO_ECONOMIC_RETURN_REGION at confirmation and under a cap (§6).
- Causal cap activation with first-eligibility zone IDs, a monotone cap and the start-of-interval contact test (§6).
- Scenario-before-child contact order (§6).
- Expiry before return gates at the setup deadline (§5).
- Blocker emission only on change (§8: no per-minute snapshots).

**Implementation defect.** None found in these cases. No counterexample.

**For Director decision — design consequence, not a defect.**
- MP-002 B1 keeps "pre-confirmation revisions … MP-001", while §3/§6 make every revision whose new low reaches the armed V impossible, because the contact is processed first. The text is explicit, so the code is conformant.
- The consequence is measurable: 49/55 October v0.2 revisions were of that kind, and the sole v0.2 October call depended on one.
- No change is proposed here.

**Code-reading notes, not exercised as differences here.**
- (a) `_waits` uses only the latest admitted minute of a dispatch as the return sample. In these records consecutive minutes produced consecutive samples. Behaviour for a dispatch admitting several minutes was not examined.
- (b) The evaluation's `corpus.pack.method` shows `btc.context-action.v0.2` for both runs. It is the preset-file label copied at pack preparation. Each run's engine, launch and every journal record carry its actual method (v0.3 for the second run).

**Not recorded / not demonstrable.**
- Whether v0.3 would have issued on 26 Oct, or on any of the 29 v0.2 through-V paths, without the V-contact rule. That needs a counterfactual replay, which is not authorized.
- Per-minute wait samples, which are reconstructed (DERIVED, validated 64/64 against stored blocker changes).
- Intrabar order inside the [02:49] and [18:58] minutes. It does not matter here: both contacts are on the target side.
- Any economic outcome of v0.3, which issued no call.
- Whether a target-side move after a wait would have been profitable is not claimed.

## Plain-language answers for the Director

- **Why the LONG disappeared.** The episode was the same in both versions until 23:29. In the minute starting 23:29 price dipped 13.8 USDT (about 1.2 bps) below the armed stop level V. In v0.3 that dip ends the scenario immediately: MP-002 deliberately treats a touch of V after arm as invalidation. In v0.2 the dip was ignored. At the 15m close v0.2 simply moved the reaction low, trigger and stop lower, and five minutes later price confirmed against the new, lower trigger. It was not dislocation, cost or any entry gate.
- **Why the three waits produced no entry.** In all three the usable price was a deep pull-back toward the reaction extreme: 26–29 bps away from the confirmation close. Price never closed there, and never even traded there intrabar.
  - Instead, one wait timed out at the original setup deadline while price hovered 12–15 bps above the region.
  - The other two ended because price ran to the target side (the scenario destination, and the conservative target cap) within 2 and 23 minutes.
  - No hidden blocker, data problem or bug intervened. The stored blocker sets match the arithmetic minute by minute.
- **What remains to verify.**
  - The Director's view on the intended interaction between the new V-contact invalidation and the inherited MP-001 re-anchoring (a design question).
  - The recurring geometry in which the conservative target is the scenario's own impulse-B edge, only a few bps beyond confirmation (5/6 cases).
  - Whether the multi-minute-dispatch return sampling matters anywhere.
  - All of these are October development observations. November and December remain suspended; no numerical change is proposed.

READY FOR DIRECTOR REVIEW — OCTOBER DIAGNOSIS ONLY
