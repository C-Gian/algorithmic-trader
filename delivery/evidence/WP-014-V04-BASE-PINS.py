"""WP-014: v0.4 fixed-fixture output pins computed on the UNCHANGED base 776752e (engineering evidence, synthetic).

Run from a detached worktree of 776752e with that worktree's ``src`` and ``tests`` first on the import path (the
WP-014 fixture module ``tests/adviser5_fixtures.py`` is pure data and is copied in). For every fixture the v0.4 fold
records (journal sequence, journal chain, evaluation sequence, evaluation chain, calls); the WP-014 code must
reproduce every pin byte for byte (``tests/test_mp004_versions.py``).

    PYTHONPATH=<worktree>/src:<worktree>/tests python WP-014-V04-BASE-PINS.py <out.json>
"""

from __future__ import annotations

import json
import sys

import adviser3_fixtures as f3
import adviser4_fixtures as f4
import adviser5_fixtures as f5
from adviser_fixtures import DAY1, DAY2, a_fixture, box_fixture, mirror

import algotrader
from algotrader.adviser.harness import run_pure

FIX = {
    "a_rally": lambda: a_fixture(), "a_stop": lambda: a_fixture(after_issue="stop"),
    "a_stall": lambda: a_fixture(after_issue="stall"), "a_progress": lambda: a_fixture(after_issue="progress"),
    "a_fade": lambda: a_fixture(after_arm="fade"), "a_short": lambda: mirror(a_fixture()),
    "box_b": lambda: box_fixture("B"), "box_c": lambda: box_fixture("C"), "box_b_return": lambda: box_fixture("B_RETURN"),
    "box_b_opposite": lambda: box_fixture("B_OPPOSITE"), "box_c_short": lambda: mirror(box_fixture("C")),
    "a3_return_long": f3.a3_return_long, "a3_return_short": lambda: f3.mirror(f3.a3_return_long()),
    "a3_cap_then_return": f3.a3_cap_then_return, "a3_cap_activation_contact": f3.a3_cap_activation_contact,
    "a3_cap_not_ahead": f3.a3_cap_not_ahead, "a3_expiry_at_return": f3.a3_expiry_at_return,
    "a3_stall_after_return": f3.a3_stall_after_return, "a3_outside_then": f3.a3_outside_then,
}
for name in ("contact_then_rearm", "contact_at_equality", "replacement_tie", "supersede_tie",
             "wick_through_a_plus_z_then_rebound", "close_at_a_plus_z", "never_armed", "arm_source_touches_b",
             "arm_then_lost_then_b", "local_and_destination_same_minute", "monitoring_gap_after_loss",
             "deadline_with_candidate_replacement", "a3_wait_v_contact_then_rebound", "a3_issued_then_v_contact"):
    FIX[f"mp003_{name}"] = getattr(f4, name)
for name in ("valid", "equality", "favourable_equality_only", "intermediate_violation_then_valid",
             "violation_and_recovery_same_bar", "v_and_recovery_same_bar", "economics_insufficient",
             "outside_corridor", "deadline_at_recovery", "gap_before_valid"):
    FIX[f"mp004_{name}"] = getattr(f5, name)
    FIX[f"mp004_{name}_short"] = (lambda n: lambda: f5.mirror(getattr(f5, n)()))(name)


def main(out: str) -> None:
    print("algotrader from", algotrader.__file__, file=sys.stderr)
    pins = {}
    for name, fn in FIX.items():
        res = run_pure(DAY1, fn(), eval_start=DAY2, method="v0.4")
        core, ev = res.runtime.core, res.runtime.ev
        pins[f"v0.4:{name}"] = [core.journal_seq, core.journal_chain, ev.record_seq, ev.record_chain, len(res.calls())]
        print(name, pins[f"v0.4:{name}"][:1], file=sys.stderr)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(pins, f, indent=1, sort_keys=True)
        f.write("\n")


if __name__ == "__main__":
    main(sys.argv[1])
