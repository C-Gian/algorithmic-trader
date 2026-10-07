# WP-012 correction — Director technical closure
Date: 2026-10-07 Europe/Rome.
Reviewed product: e3a5afa6e355363cd2df93871c68ad8cb4de3626.
Decision: F1 CLOSED; no remaining blocking finding in the reviewed correction scope. RELEASE / OWNER COMPARISON WAITING FOR EXACT-SHA CI.
CI: PENDING / NOT CHECKED by Director, Owner-operated. This document does not activate an economic run.

## What was independently checked
Compared the full correction diff with [original review](WP-012-DIRECTOR-REVIEW.md): only core4.py, new correction tests and executor evidence/STATE changed. Method/register/identity/public schemas, core v0.2/v0.3 and evaluation policy are untouched. Reviewed domain overlap, loss-versus-supersession bookkeeping, canonical codec and the relevant live persistence tests.

Ran the original Director complete synthetic LONG/SHORT tape: epoch 2 now loses its anchor UNASSESSABLE at 04:01 with SUPERSEDED_ANCHOR_CONTACT_TIME_AMBIGUOUS_EPOCH_1, same scenario WATCH. It never confirms. A valid later complete reaction publishes epoch 3 at 04:15:30 and confirms at 04:17. This is allowed replacement, not a retroactive rescue. [After output](evidence/WP-012-CORRECTION-DIRECTOR-PROBES.json).

Independently ran:
`PYTHONPATH=src:tests ../wp009-probe-venv/bin/python -m pytest tests/test_mp003_correction.py -m 'not db' -q`
Result: 18 passed, 1 DB case deliberately deselected. These cover LONG/SHORT full-tape regression, neither/new/old-only controls, dead-domain non-retest, production pack/unpack at four cuts and six persisted-live restart paths. No Director database/container/browser/Compose run. Executor's 208 DB-required relevant-suite results and durable LiveStore case are evidence examined, not independently rerun.

Generated genuine four-element legacy histories using the original e434d43 core4 source loaded in an isolated module, with the current unchanged method/config pins. Production pack/unpack on current code accepts canonical old bytes exactly after supersession (ARMED) and after loss (WATCH). Both output snapshots have only four-element domain entries. [Compatibility results](evidence/WP-012-CORRECTION-DIRECTOR-COMPAT.json), [reproduction script](evidence/WP-012-CORRECTION-DIRECTOR-COMPAT-PROBE.py). The preliminary harness attempts rejected mismatched evaluation configuration and undrained outputs; correcting those harness inputs, without altering any product guard, produced the two passing results. This was codec verification, not historical economic evaluation.

## Closure and limits
- F1 closed: every actually overlapping active domain is considered; old-V-only straddling contact is ambiguous, not clean. An old level entirely outside its active domain cannot invalidate a new anchor.
- The fifth history element is added only when a domain closes; SUPERSEDED is eligible only within its interval, LOST is not retested. The current release's direct canonical round trip remains exact; no reader inserts new fields into old bytes.
- Old pre-correction engineering histories did not record how their domains closed. Treating an untagged closed domain conservatively as superseded is an acknowledged information limitation, not proof that every old domain was superseded. Such states can conservatively block on late input. No old v0.4 engineering run is an accepted economic baseline or is relabelled/repaired.
- Likewise, reference replay with current code need not reproduce pre-correction v0.4 engineering state hashes/outputs whose history shape or behavior differs. Preserve honest mismatches; never force MATCH or rewrite old evidence. Fresh accepted v0.4 runs must use the corrected release. The Owner has not been authorized to run v0.4 before this closure.
- Keeping implementation/state-format identifiers is acceptable for this unaccepted engineering correction: rules unchanged, old exact decoding preserved, build included in behavior identity. Existing v0.2/v0.3 identities/output compatibility are unaffected.
- LiveStore is a suitable durable path for the subminute-publication regression. Historical MODELED pack runs do not demonstrate that particular subminute case; their restore/cadence suite is executor-reported passing. Recorded/delayed tapes are still covered by the pure temporal/runtime probe. Do not generalize minute-boundary publication to all possible source policies.
- No parameters, economic results or usefulness claims have changed. More calls remain neither promised nor accepted as improvement.

## Current boundary
Technical findings are closed; full WP-012 release acceptance awaits Owner notification and verification that checks and compose-smoke succeeded on e3a5afa6e355363cd2df93871c68ad8cb4de3626. No executor implementation/correction task remains active while waiting. Do not poll/wait in a shell.

After that CI gate, the Director will explicitly activate only the registered Owner app development comparison. October uses the existing matching v0.3 baseline eval-20261006T175135-9ddf6d; candidate is a fresh v0.4 run on the same October pack. November/December remain later frozen development follow-up; protected periods unauthorized. No app upgrade or economic launch is requested by this document.
