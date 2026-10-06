"""Regenerates the WP-012 fixture -> expected -> actual table (pure, synthetic; no market data).

usage: uv run python delivery/evidence/WP-012-FIXTURE-TABLE.py > table.json
The hand expectations are the ones asserted in tests/test_mp003_paths.py; ``actual`` is the A scenario transition
sequence (time, transition, reason head, anchor epoch/status) of the v0.4 run, LONG; the reflected SHORT run must give
the same sequence."""

from __future__ import annotations

import json
import sys
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))

import adviser4_fixtures as fx  # noqa: E402
from adviser3_fixtures import Stepper  # noqa: E402
from adviser4_fixtures import D, T, bar15, minute, walk  # noqa: E402

from algotrader.adviser.harness import run_pure  # noqa: E402

ROWS = [
    ("1 never armed: B contact no terminal; spend only > B+z (equality kept)", "never_armed", {},
     "BIRTH 03:30; no terminal at 03:45 (high 100950 >= B) or 04:00 (high = B+z); SPENT at 04:15 (101100.1)"),
    ("2 first arm source bar touched B: no retroactive destination", "arm_source_touches_b", {},
     "ARM 03:45 (K 100950); DESTINATION_REACHED 03:51 from the later minute [03:50,03:51) high = B"),
    ("2 delayed publication: B contact admitted before the arm is ignored", "_delayed_b", {"allowance": 300},
     "BIRTH 03:35, ARM published 03:50 (actual dispatch); destination from [03:50,03:51) at 03:51"),
    ("2/12 straddling first-arm origin with B contact", "_straddle_b", {"allowance": 30, "delay": 30},
     "ARM 03:45:30; [03:45,03:46) reaches B -> UNASSESSABLE FIRST_ARM_DESTINATION_CONTACT_TIME_AMBIGUOUS"),
    ("3 anchor lost, destination still monitored in WATCH", "arm_then_lost_then_b", {},
     "ANCHOR_LOST 03:51; DESTINATION_REACHED 04:21 (origin stays 03:45)"),
    ("4-5 contact -> same owner WATCH -> deeper complete reaction re-arms -> fresh confirmation", "contact_then_rearm",
     {}, "ARM 03:45 e1; ANCHOR_LOST 03:51 e1; REARM 04:00 e2 (R 99790 K 100300 V 99590); CONFIRM 04:09 e2"),
    ("4 equality: low exactly V is contact", "contact_at_equality", {}, "ANCHOR_LOST 03:51; REARM 04:00 (R 99800)"),
    ("tie: replacement needs a strictly deeper R", "replacement_tie", {},
     "no REARM at 04:15 (low = lost R); REARM 04:30 (R 99999.9)"),
    ("tie: supersession keeps the inherited inclusive tie", "supersede_tie", {}, "REVISE 04:00 e2 (R 100000)"),
    ("6 contact + seal in one dispatch; no retroactive confirmation", "_one_dispatch", {"delay58": 60},
     "ANCHOR_LOST and REARM both at 04:00 (same cursor, loss first); CONFIRM 04:01 from [04:00,04:01)"),
    ("6 delayed publication: admitted recoveries never confirm", "contact_same_bar_backlog", {"allowance": 300},
     "ANCHOR_LOST 03:59; REARM 04:05; CONFIRM 04:06 from [04:05,04:06) (04:00-04:04 closes >= K+tick ignored)"),
    ("old bar rejection", "_old_bar", {"allowance": 300},
     "ANCHOR_LOST 04:03; bar [03:45,04:00) sealed 04:05 not used; REARM 04:20 from [04:00,04:15)"),
    ("late interval in an earlier epoch domain", "_late_epoch", {"allowance": 300, "delay404": 30},
     "REVISE 04:05 e2; ANCHOR_LOST 04:05:30 e2 UNASSESSABLE (LATE_CONTACT_WITH_EARLIER_ANCHOR_EPOCH_1)"),
    ("12 straddling local contact", "_straddle_local", {"allowance": 30, "delay": 30},
     "ANCHOR_LOST 03:46 UNASSESSABLE (scenario WATCH, not terminal); REARM 04:00:30; CONFIRM 04:08"),
    ("7 complete 15m close <= A+z withdraws, no replacement", "close_at_a_plus_z", {},
     "ANCHOR_LOST 03:51; WITHDRAWN CLOSE_AT_OR_BEYOND_A_PLUS_ZONE 04:00"),
    ("11/7 wick through A+z is not the close predicate; no eligible reaction", "wick_through_a_plus_z_then_rebound",
     {}, "ANCHOR_LOST 03:51; WATCH until EXPIRED ORIGINAL_SETUP_DEADLINE 05:30; no call"),
    ("8 original deadline before a candidate replacement", "deadline_with_candidate_replacement", {},
     "ANCHOR_LOST 03:51; EXPIRED 05:30 (the [05:15,05:30) deeper bar never re-arms)"),
    ("9 confirmed WAIT, V contact then rebound", "a3_wait_v_contact_then_rebound", {},
     "CONFIRM 04:01; scenario INVALIDATED V_CONTACT 04:02; no ANCHOR_LOST/REARM; no call"),
    ("10 issued call, V contact", "a3_issued_then_v_contact", {},
     "RETURN call 04:02; call INVALIDATED; revisions/paths equal v0.3"),
    ("12 local + destination same minute", "local_and_destination_same_minute", {},
     "UNASSESSABLE DESTINATION_AND_LOCAL_ANCHOR_CONTACT_SAME_INTERVAL 03:51"),
    ("12 required gap after loss", "monitoring_gap_after_loss", {}, "ANCHOR_LOST 03:51; UNASSESSABLE gap 03:56"),
]


def _tape(name):
    pre_b = fx.birth_base() + bar15(D(100700), D(100950), D(100000), D("100049.9"), order="HL")
    if name == "_delayed_b":
        return fx.tail(pre_b + [minute("100049.9", 100950, 100040, 100100)] + walk(100100, 100800, 4)
                       + [minute(100800, 100900, 100800, 100850)] + walk(100850, 100600, 9))
    if name == "_straddle_b":
        return fx.tail(pre_b + [minute("100049.9", 100950, 100040, 100100)] + walk(100100, 100600, 13))
    if name == "_straddle_local":
        return fx.tail(fx.arm_base() + [minute("100049.9", "100049.9", 99790, 99900)] + walk(99900, 100300, 6)
                       + walk(100300, 99950, 7) + walk(99950, 100350, 10))
    if name == "_one_dispatch":
        return fx.contact_same_bar_backlog()
    if name in ("_old_bar", "_late_epoch"):
        low, n = (99700, 2) if name == "_old_bar" else (99750, 4)
        return fx.tail(fx.arm_base() + walk("100049.9", 99850, 7) + walk(99850, 100100, 8) + walk(100100, 100000, n)
                       + [minute(100000, 100000, low, 99900)] + walk(99900, 100200, 12))
    return getattr(fx, name)()


def actual(name, opts, side):
    ms = _tape(name)
    if side == "S":
        ms = fx.mirror(ms)
    delays = {}
    for key, at in (("delay", T(3, 44)), ("delay58", T(3, 58)), ("delay404", T(4, 4))):
        if opts.get(key):
            delays[fx.index_of(at)] = opts[key]
    if delays or opts.get("allowance"):
        st = Stepper(ms, events=fx.delayed_events(ms, delays), method="v0.4",
                     allowance=timedelta(seconds=opts.get("allowance", 0)))
        st.finish()
        journal = st.journal
    else:
        journal = run_pure(fx.DAY1, ms, eval_start=fx.DAY2, method="v0.4").journal
    calls = [e for e in journal if e["kind"] == "call"]
    recs = [e["record"] for e in journal if e["kind"] == "scenario" and e["record"]["scenario_id"][:2] in ("AL", "AS")]
    sid = next(r["scenario_id"] for r in recs if r["transition"] == "BIRTH"
               and r["env"]["clock_time"][:15] == "2025-09-01T03:3")
    seq = []
    for r in recs:
        if r["scenario_id"] != sid:
            continue
        head = (r["reason"] or "").split(":")[0]
        seq.append(" ".join(x for x in (r["env"]["clock_time"][11:19], r["transition"], head,
                                         f"e{r['anchor_epoch']}" if r["anchor_epoch"] else "", r["anchor_status"]) if x))
    return {"transitions": seq, "calls": len(calls)}


def main():
    out = []
    for row, name, opts, expected in ROWS:
        a_l, a_s = actual(name, opts, "L"), actual(name, opts, "S")
        out.append({"row": row, "tape": name, "options": opts, "expected": expected, "actual_long": a_l,
                    "actual_short_same_sequence": a_s["transitions"] == a_l["transitions"],
                    "test": "tests/test_mp003_paths.py"})
    json.dump(out, sys.stdout, indent=1)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
