"""Generator of tests/fixtures/mp002_legacy_v3_states.json.gz (WP-011 compatibility follow-up).

Run with the REVIEWED v0.3 codec (src/ identical at f1a8023 and ed64d05), e.g. from a git worktree of ed64d05:
    git worktree add <tmp> ed64d05 && cd <tmp>
    PYTHONPATH=src:tests python <repo>/delivery/evidence/WP-011-COMPAT-LEGACY-FIXTURE-GEN.py <repo>/tests/fixtures/mp002_legacy_v3_states.json.gz
Pure v0.3 fold of adviser3_fixtures.a3_stall_after_return (eval DAY2 -> DAY2+12h); the canonical encoded runtime state
(outputs drained) just before the first event available at/after each cut time (inside_0400: one event later,
between the first 04:00 event and the 04:00 sealed-ingestion landmarks). Synthetic engineering input only.
"""
import gzip
import hashlib
import json
import sys
from datetime import timedelta

import adviser3_fixtures as fx
from adviser3_fixtures import DAY1, DAY2, T

import algotrader
from algotrader.adviser.harness import build_events, make_runtime, temporal_for
from algotrader.feed.ordering import canonical

EVAL_END = DAY2 + timedelta(hours=12)
mins = fx.a3_stall_after_return()
events, cov = build_events(DAY1, mins)
cuts = {min(i for i, e in enumerate(events) if e.available_time >= t) + k: name
        for name, t, k in (("before_0400", T(4), 0), ("inside_0400", T(4), 1), ("before_0500", T(5), 0))}
rt = make_runtime(eval_start=DAY2, eval_end=EVAL_END, method="v0.3")
temporal = temporal_for(cov)
rt.attach(temporal)
states = {}
for i, e in enumerate(events):
    if i in cuts:
        rt.take()
        raw = canonical(rt.encode())
        assert "deps" not in json.loads(raw)["core"]["v3"], "not the reviewed (legacy) codec"
        states[cuts[i]] = {"event_index": i, "sha256": hashlib.sha256(raw).hexdigest(), "state": raw.decode()}
    temporal.on_event(e, i)
    rt.before_admit(e)
    rt.admit(e, i)
doc = {"provenance": "Encoded by the reviewed v0.3 codec (src identical at f1a8023/ed64d05); see "
                     "delivery/evidence/WP-011-COMPAT-LEGACY-FIXTURE-GEN.py. Synthetic, not market data.",
       "eval_start": DAY2.isoformat(), "eval_end": EVAL_END.isoformat(), "states": states}
open(sys.argv[1], "wb").write(gzip.compress(json.dumps(doc, sort_keys=True, indent=1).encode(), 9, mtime=0))
print(algotrader.__file__, {k: (v["event_index"], v["sha256"][:16]) for k, v in states.items()})
