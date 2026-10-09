"""WP-015: v0.5 fixed-fixture output pins computed on the UNCHANGED base 3c6af11 (engineering evidence, synthetic).

Run from a detached worktree of 3c6af11 with that worktree's ``src`` and ``tests`` first on the import path (the
WP-015 fixture module ``tests/adviser6_fixtures.py`` is pure data and is copied in). For every fixture the v0.5 fold
records (journal sequence, journal chain, evaluation sequence, evaluation chain, calls); the WP-015 code must
reproduce every pin byte for byte (``tests/test_mp005_versions.py``): the v0.6 code leaves v0.5 untouched.

    PYTHONPATH=<worktree>/src:<worktree>/tests python WP-015-V05-BASE-PINS.py <out.json>
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import adviser5_fixtures as f5
import adviser6_fixtures as f6

import algotrader
from algotrader.adviser.harness import run_pure

_spec = importlib.util.spec_from_file_location("wp014_pins", Path(__file__).with_name("WP-014-V04-BASE-PINS.py"))
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

FIX = dict(_mod.FIX)  # the 53 WP-014 fixtures (v0.2/v0.3 tapes, MP-003 tapes, MP-004 tapes)
for name in ("two_valid", "recovery_then_violation", "blocked_first", "new_cap_before_recovery",
             "cap_contact_in_activation_bar"):
    FIX[f"mp004_{name}"] = getattr(f5, name)
for name in ("h1_economics", "h2_corridor", "h3_single_tick", "h4_deadline_collision", "h5_persistence"):
    FIX[f"mp005_{name}"] = getattr(f6, name)
    FIX[f"mp005_{name}_short"] = (lambda n: lambda: f6.mirror(getattr(f6, n)()))(name)


def main(out: str) -> None:
    print("algotrader from", algotrader.__file__, file=sys.stderr)
    pins = {}
    for name, fn in FIX.items():
        res = run_pure(f6.DAY1, fn(), eval_start=f6.DAY2, method="v0.5")
        core, ev = res.runtime.core, res.runtime.ev
        pins[f"v0.5:{name}"] = [core.journal_seq, core.journal_chain, ev.record_seq, ev.record_chain, len(res.calls())]
        print(name, pins[f"v0.5:{name}"][:1], file=sys.stderr)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(pins, f, indent=1, sort_keys=True)
        f.write("\n")


if __name__ == "__main__":
    main(sys.argv[1])
