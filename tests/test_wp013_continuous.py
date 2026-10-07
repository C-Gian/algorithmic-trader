"""WP-013 (pure): the registered continuous September-December preset with an explicit 35-day initialization, the
compatibility of the earlier fine-warmup presets, the launch pin of the initialization, the context attestation at
the evaluation start and the whole-run/monthly report sections. Synthetic engineering inputs only - no market data,
no economic evaluation."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import adviser3_fixtures as f3
import pytest

from algotrader.adviser import engine as en
from algotrader.adviser import report_periods as rp
from algotrader.adviser.harness import run_pure
from algotrader.corpus import pack as pk
from algotrader.corpus import presets as ps

ROOT = Path(__file__).resolve().parents[1]
NEW_ID = "btc-2025-09-to-2025-12-continuous-init35d-v1"


def T(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


# ---------------------------------------------------------------------------------------------------------------------
# presets: one new registered preset, earlier identities unchanged, no global warmup change
# ---------------------------------------------------------------------------------------------------------------------

def test_registered_file_is_the_wp013_registration_and_keeps_every_earlier_preset_identity():
    assert (ROOT / "src/algotrader/corpus/presets.json").read_text(encoding="utf-8") == \
        (ROOT / "delivery/WP-013-PRESETS.json").read_text(encoding="utf-8")
    new = ps.load_presets(ps.PRESETS_FILE)
    old = ps.load_presets(ROOT / "delivery/WP-008-R3-PRESETS.json")
    assert new.fine_warmup_hours == old.fine_warmup_hours == 96 and new.default == old.default
    assert ps.policy_doc(new) == ps.policy_doc(old)  # file-level policies (and so every identity) unchanged
    for p in old.presets:
        q = new.preset(p.preset_id)
        assert q is not None and q.initialization is None
        assert ps.preset_doc(q) == ps.preset_doc(p) and "initialization" not in ps.preset_doc(q)
        assert ps.preset_sha256(new, q) == ps.preset_sha256(old, p)
        assert ps.windows_doc(q) == ps.windows_doc(p) and "initialization" not in ps.windows_doc(q)
        assert pk.manifest_revision(q) == 1  # a rebuilt fine-warmup pack keeps its manifest revision and id
    # the month builder still uses exactly the 96 h fine warmup
    for m in ("2025-09", "2025-10", "2025-11", "2025-12"):
        b = ps.months_preset(new, [m])
        assert b.initialization is None and b.warmup.minutes == 96 * 60
        assert ps.preset_sha256(new, b) == ps.preset_sha256(old, ps.months_preset(old, [m]))


def test_continuous_preset_windows_are_exact_half_open_utc():
    f = ps.load_presets(ps.PRESETS_FILE)
    p = f.preset(NEW_ID)
    assert p.initialization == ps.INITIALIZATION_EXPLICIT and not p.default
    assert (p.warmup.start, p.warmup.end) == (T("2025-07-28T00:00Z"), T("2025-09-01T00:00Z"))
    assert (p.evaluation.start, p.evaluation.end) == (T("2025-09-01T00:00Z"), T("2026-01-01T00:00Z"))
    assert (p.tail.start, p.tail.end) == (T("2026-01-01T00:00Z"), T("2026-01-01T06:05Z"))
    assert p.warmup.minutes == 35 * 1440 and p.tail.minutes == 365
    assert p.evaluation.minutes == (30 + 31 + 30 + 31) * 1440
    w = ps.windows_doc(p)
    assert (w["warmup"]["scored"], w["evaluation"]["scored"], w["tail"]["scored"]) == (False, True, False)
    assert w["initialization"]["hours"] == 840 and w["initialization"]["evaluated"] is False
    assert w["requested"] == {"start": "2025-07-28T00:00:00+00:00", "end": "2026-01-01T06:05:00+00:00"}
    assert ps.classify(f, p)["label"] == "DEVELOPMENT" and ps.preset_doc(p)["initialization"] == ps.INITIALIZATION_EXPLICIT
    assert pk.manifest_revision(p) == 2
    # acquisition requests split at UTC months (the initialization reaches back to 28 July)
    s = pk.split_requests(p.warmup.start, p.tail.end)
    assert s[0] == (T("2025-07-28T00:00Z"), T("2025-08-01T00:00Z")) and s[-1] == (T("2026-01-01T00:00Z"),
                                                                                 T("2026-01-01T06:05Z"))


def test_explicit_initialization_must_end_at_evaluation_start_and_cover_the_fine_warmup():
    f = ps.load_presets(ps.PRESETS_FILE)
    p = f.preset(NEW_ID)
    bad_short = p.model_copy(update={"warmup": ps.Window(start=T("2025-08-30T00:00Z"), end=T("2025-09-01T00:00Z"))})
    bad_gap = p.model_copy(update={"warmup": ps.Window(start=T("2025-07-28T00:00Z"), end=T("2025-08-31T00:00Z"))})
    for bad in (bad_short, bad_gap):
        with pytest.raises(ps.PresetError):
            ps.check_windows(f, bad)
    ps.check_windows(f, p.model_copy(update={"warmup": ps.Window(start=T("2025-08-28T00:00Z"),
                                                                 end=T("2025-09-01T00:00Z"))}))  # = fine warmup ok
    # without the field the exact fine-warmup rule is unchanged
    with pytest.raises(ps.PresetError):
        ps.check_windows(f, p.model_copy(update={"initialization": None}))
    with pytest.raises(ValueError):  # only the registered literal is accepted
        ps.Preset.model_validate({**ps.preset_doc(p), "initialization": "LONGER"})


def test_engine_pins_the_initialization_only_for_an_explicit_preset():
    f = ps.load_presets(ps.PRESETS_FILE)
    cov = [{"family": "trade_bar_1m", "window": "warmup", "valid": 50400, "expected_slots": 50400, "missing": 0,
            "rejected": 0},
           {"family": "trade_bar_1m", "window": "evaluation", "valid": 1, "expected_slots": 1, "missing": 0,
            "rejected": 0}]
    for p, want in ((f.preset(NEW_ID), True), (f.default, False)):
        pack = {"preset": ps.preset_doc(p), "preset_sha256": ps.preset_sha256(f, p), "windows": ps.windows_doc(p),
                "coverage": cov}
        pin = en.initialization_pin(pack)
        if not want:
            assert pin is None
            continue
        assert pin["hours"] == 840 and pin["evaluated"] is False and pin["preset_id"] == NEW_ID
        assert pin["coverage"] == cov[:1] and pin["continuity"].startswith("ONE_RUN_ONE_EVALUATION_START")


# ---------------------------------------------------------------------------------------------------------------------
# one continuous run across a month boundary (pure kernel): a call issued in August resolves in September
# ---------------------------------------------------------------------------------------------------------------------

SHIFT = timedelta(minutes=270)  # moves the a3 RETURN fixture so its call is issued 31 Aug 23:32 and ends 1 Sep 00:08


def month_crossing_run(**kw):
    st = f3.DAY1 - SHIFT
    es, ee = st + timedelta(hours=24), st + timedelta(hours=30)
    return st, es, ee, run_pure(st, f3.a3_return_long(), eval_start=es, eval_end=ee, method="v0.4", **kw)


def test_single_evaluation_start_transition_and_no_monthly_reset_in_the_kernel():
    st, es, ee, r = month_crossing_run()
    calls = r.calls()
    assert [c["issued_at"] for c in calls] == ["2025-08-31T23:32:00Z"]
    term = [x for x in r.revisions() if x["thesis_status"] != "ONGOING"]
    assert [(x["env"]["clock_time"], x["thesis_status"]) for x in term] == [("2025-09-01T00:08:00Z", "TARGET_REACHED")]
    # nothing is cleared, retired or restarted at the month boundary
    boundary = [e for e in r.journal if e["clock_time"][:16] in ("2025-09-01T00:00", "2025-09-01T00:01")]
    for e in boundary:
        assert "EVALUATION_START" not in json.dumps(e["record"]) and "CLEARED" not in json.dumps(e["record"])
    cleared = [e for e in r.journal if "EVALUATION_START_CLEARS" in json.dumps(e["record"])]
    assert all(e["clock_time"][:19] == es.isoformat()[:19] for e in cleared)
    # the structural owner born in August keeps its lineage into September (no restart, no second birth)
    sid = calls[0]["scenario_id"]
    tr = [(e["clock_time"][:10], e["record"]["transition"]) for e in r.journal
          if e["kind"] == "scenario" and e["record"]["scenario_id"] == sid]
    assert tr[0] == ("2025-08-31", "BIRTH") and tr[-1] == ("2025-09-01", "TERMINAL")
    assert sum(1 for _, x in tr if x == "BIRTH") == 1
    # the PRIMARY hypothetical path entered in August and exited in September
    p = r.paths("PRIMARY")[0]
    assert p["entry"]["time_end"].startswith("2025-08-31") and p["exit"]["time_end"].startswith("2025-09-01")


# ---------------------------------------------------------------------------------------------------------------------
# context attestation at the evaluation start (synthetic journals)
# ---------------------------------------------------------------------------------------------------------------------

ES = T("2025-09-01T00:00Z")


def lm(at, typ, period, status="ACTIVE", reason=None, lid=None):
    h = {"PREV_1D": "1d", "PREV_1W": "1w", "PREV_1MO": "1mo"}.get(typ.rsplit("_", 1)[0])
    rec = {"landmark_id": lid or f"lm-{typ}-{period}", "landmark_type": typ, "status": status, "status_reason": reason,
           "price": "100", "source_ids": [f"okx/BTC-USDT-SWAP/trade_bar_1m/{h or '1h'}/{period}"],
           "extremum_time": None if h else period}
    return {"kind": "landmark", "clock_time": at, "record": rec}


def readiness(at, cat):
    return {"kind": "observation", "clock_time": at, "record": {"name": "readiness", "category": cat}}


def engine_doc(init_start="2025-07-28T00:00:00+00:00", missing=0):
    return {"adviser": {"method": "v0.4", "eval_start": ES.isoformat(), "eval_end": "2026-01-01T00:00:00+00:00",
                        "warmup_start": init_start,
                        "initialization": {"policy": ps.INITIALIZATION_EXPLICIT, "preset_id": NEW_ID,
                                           "start": init_start, "end": ES.isoformat(), "hours": 840, "evaluated": False,
                                           "coverage": [{"family": "trade_bar_1m", "window": "warmup", "valid":
                                                         50400 - missing, "expected_slots": 50400, "missing": missing,
                                                         "rejected": 0}]}}}


def full_journal():
    j = [readiness("2025-07-28T00:01:00+00:00", "trade.15m:WARMING_UP/trade.1h:WARMING_UP/trade.1m:READY"),
         readiness("2025-07-28T21:00:00+00:00", "trade.15m:READY/trade.1h:READY/trade.1m:READY")]
    j += [lm("2025-08-01T00:00:00+00:00", f"PREV_1MO_{s}", "2025-07-01T00:00:00+00:00") for s in ("HIGH", "LOW")]
    j += [lm("2025-08-25T00:00:00+00:00", "PREV_1W_HIGH", "2025-08-18T00:00:00+00:00"),
          lm("2025-08-25T00:00:00+00:00", "PREV_1W_LOW", "2025-08-18T00:00:00+00:00")]
    j += [lm("2025-08-31T00:00:00+00:00", "PREV_1D_HIGH", "2025-08-30T00:00:00+00:00"),
          lm("2025-08-31T00:00:00+00:00", "PREV_1D_LOW", "2025-08-30T00:00:00+00:00"),
          lm("2025-08-31T10:00:00+00:00", "PIVOT_HIGH_1H", "2025-08-31T05:00:00+00:00"),
          lm("2025-08-30T10:00:00+00:00", "PIVOT_LOW_1H", "2025-08-30T04:00:00+00:00", "BROKEN",
             "15M_CLOSE_BEYOND_FAR_EDGE:x", lid="lm-pl1h")]
    # at the evaluation start itself: the August month, the last week and day are published, the July month and the
    # 18 Aug week retire; one previous-day high was broken by a later close
    j += [lm("2025-09-01T00:00:00+00:00", f"PREV_1MO_{s}", "2025-08-01T00:00:00+00:00") for s in ("HIGH", "LOW")]
    j += [lm("2025-09-01T00:00:00+00:00", f"PREV_1MO_{s}", "2025-07-01T00:00:00+00:00", "RETIRED",
             "NEXT_PERIOD_COMPLETED") for s in ("HIGH", "LOW")]
    j += [lm("2025-09-01T00:00:00+00:00", f"PREV_1W_{s}", "2025-08-25T00:00:00+00:00") for s in ("HIGH",)]
    j += [lm("2025-08-31T00:00:00+00:00", "PREV_1W_LOW", "2025-08-25T00:00:00+00:00", lid="w-low-late")]
    j += [lm("2025-09-01T00:00:00+00:00", "PREV_1D_HIGH", "2025-08-31T00:00:00+00:00"),
          lm("2025-09-01T00:00:00+00:00", "PREV_1D_LOW", "2025-08-31T00:00:00+00:00", "BROKEN",
             "15M_CLOSE_BEYOND_FAR_EDGE:y")]
    j += [lm("2025-09-01T00:15:00+00:00", "PREV_1D_HIGH", "2025-08-31T00:00:00+00:00", "BROKEN", "after-start")]
    return sorted(j, key=lambda e: e["clock_time"])


def test_attestation_with_complete_initialization_reports_built_broken_and_retired_levels():
    ic = rp.initial_context(engine_doc(), full_journal())
    assert ic["initialization_trade_complete"] is True
    assert ic["readiness"]["at_evaluation_start"] == {"trade.15m": "READY", "trade.1h": "READY", "trade.1m": "READY"}
    rp_ = ic["required_periods"]
    assert rp_["previous_month"] == {"start": "2025-08-01T00:00:00+00:00", "end": "2025-09-01T00:00:00+00:00",
                                     "inside_initialization": True, "data": "COVERED"}
    assert rp_["previous_week"]["start"] == "2025-08-25T00:00:00+00:00"  # 1 Sep 2025 is a Monday
    assert rp_["previous_day"]["start"] == "2025-08-31T00:00:00+00:00"
    assert rp_["pivot_1h_memory"]["start"] == "2025-08-25T00:00:00+00:00" and rp_["pivot_1h_memory"]["data"] == "COVERED"
    L = ic["landmarks"]
    assert L["PREV_1MO_HIGH"]["state"] == "BUILT_ACTIVE" and L["PREV_1MO_HIGH"]["covers_required_period"]
    assert L["PREV_1MO_HIGH"]["ever_built"] == 2  # July (retired at the start) and August
    assert L["PREV_1W_HIGH"]["state"] == "BUILT_ACTIVE"
    assert L["PREV_1D_LOW"]["state"] == "BUILT_THEN_BROKEN" and L["PREV_1D_LOW"]["status_reason"].startswith("15M")
    assert L["PREV_1D_HIGH"]["state"] == "BUILT_ACTIVE"  # the break after the start is not counted
    assert L["PIVOTS_1H"]["ever_built"] == 2 and L["PIVOTS_1H"]["active_at_start"] == 1
    assert L["PIVOTS_1H"]["memory_completeness"] == "NOT_CERTIFIED" and L["PIVOTS_1H"]["state"] == "BUILT"
    assert L["PIVOTS_15M"]["state"] == "NEVER_BUILT"


def test_attestation_keeps_insufficient_data_apart_from_never_built_and_never_certifies():
    # a 96 h initialization: previous month/week and the 1h pivot memory start before it
    short = rp.initial_context(engine_doc("2025-08-28T00:00:00+00:00"), [
        lm("2025-08-29T00:00:00+00:00", "PREV_1D_HIGH", "2025-08-28T00:00:00+00:00", "RETIRED", "AGE")])
    rq = short["required_periods"]
    assert rq["previous_month"]["data"] == rq["previous_week"]["data"] == rq["pivot_1h_memory"]["data"] == \
        "INSUFFICIENT_BEFORE_INITIALIZATION"
    assert rq["previous_day"]["data"] == "COVERED"
    L = short["landmarks"]
    assert L["PREV_1MO_HIGH"]["state"] == L["PREV_1W_LOW"]["state"] == "NOT_BUILT_DATA_INSUFFICIENT"
    assert L["PREV_1D_HIGH"]["state"] == "BUILT_THEN_RETIRED_FOR_ANOTHER_PERIOD"  # a retired older day, not 31 Aug
    assert L["PREV_1D_LOW"]["state"] == "NOT_BUILT_WITH_COVERED_PERIOD_UNEXPLAINED_NOT_CERTIFIED"
    assert L["PIVOTS_1H"]["state"] == "NEVER_BUILT" and short["readiness"]["at_evaluation_start"] == \
        "NO_READINESS_OBSERVATION_BEFORE_START"
    # missing initialization minutes: covered periods cannot be located, so nothing is called covered
    gaps = rp.initial_context(engine_doc(missing=3), [])
    assert gaps["initialization_trade_complete"] is False
    assert {v["data"] for v in gaps["required_periods"].values()} == {
        "INITIALIZATION_TRADE_COVERAGE_INCOMPLETE_UNLOCATED"}
    assert gaps["landmarks"]["PREV_1MO_LOW"]["state"] == "NOT_BUILT_DATA_INSUFFICIENT"
    # no explicit initialization: no attestation (earlier runs/reports unchanged)
    eng = engine_doc()
    del eng["adviser"]["initialization"]
    assert rp.initial_context(eng, full_journal()) is None


# ---------------------------------------------------------------------------------------------------------------------
# whole-run total and monthly sections (synthetic records)
# ---------------------------------------------------------------------------------------------------------------------

def env(t):
    return {"published_at": t, "clock_time": t}


def scen(t, tr, sid="AL-x"):
    return {"kind": "scenario", "clock_time": t,
            "record": {"env": env(t), "family": "A", "direction": "LONG", "transition": tr, "scenario_id": sid}}


def ent(t, tr, eid, reason=None, in_d="true", in_n="false", fam="A"):
    return {"kind": "entry_attempt", "clock_time": t,
            "record": {"env": env(t), "family": fam, "transition": tr, "entry_attempt_id": eid, "reason": reason,
                       "diagnostic": {"in_D": in_d, "in_N": in_n} if tr in ("WAIT_OPEN", "ISSUE", "TERMINAL")
                       and reason != "later" else {}, "state": "X", "blockers": []}}


def call(t, cid, mode="RETURN"):
    return {"kind": "call", "clock_time": t,
            "record": {"env": env(t), "call_id": cid, "issued_at": t, "family": "A", "entry_mode": mode}}


def rev(t, cid, status):
    return {"kind": "call_revision", "clock_time": t,
            "record": {"env": env(t), "call_id": cid, "thesis_status": status}}


def view(t, row):
    return {"kind": "market_view", "clock_time": t, "record": {"table_row": row}}


def path(cid, variant, net, exit_t, status="CLOSED"):
    return {"kind": "path", "record": {"call_id": cid, "variant": variant, "status": status, "price_net": net,
                                       "exit_class": "STOP" if net and Decimal(net) < 0 else "TARGET",
                                       "exit": {"time_end": exit_t} if exit_t else None}}


def sample(t, v="UP", o="UP"):
    return {"kind": "view_sample", "record": {"sample_time": t, "view": v, "outcome_1h": o, "outcome_4h": o}}


def periods_fixture():
    j = [view("2025-09-01T00:00:00+00:00", "NO_QUALIFIED_STRUCTURE"),
         view("2025-09-20T00:00:00+00:00", "REQUIRED_CONTEXT_UNAVAILABLE"),
         view("2025-09-20T01:00:00+00:00", "BALANCED_RANGE")]
    # September: a WAIT opened 30 Sep that ends (issue) 30 Sep; its call resolves on 1 October
    j += [scen("2025-09-30T23:00:00+00:00", "CONFIRM", "AL-1"),
          ent("2025-09-30T23:00:00+00:00", "WAIT_OPEN", "AL-1#entry"),
          ent("2025-09-30T23:30:00+00:00", "ISSUE", "AL-1#entry", reason="call-1"),
          call("2025-09-30T23:30:00+00:00", "call-1"),
          rev("2025-10-01T00:10:00+00:00", "call-1", "INVALIDATED")]
    # September: a WAIT that ends in October without a call; an IMMEDIATE call in October still open at the end
    j += [ent("2025-09-15T10:00:00+00:00", "WAIT_OPEN", "AL-2#entry"),
          ent("2025-10-01T00:30:00+00:00", "TERMINAL", "AL-2#entry", reason="ORIGINAL_SETUP_DEADLINE", in_d=None),
          ent("2025-10-05T10:00:00+00:00", "ISSUE", "AL-3#entry", reason="call-3"),
          call("2025-10-05T10:00:00+00:00", "call-3", "IMMEDIATE"),
          ent("2025-10-06T10:00:00+00:00", "TERMINAL", "AL-4#entry", reason="NO_ECONOMIC_RETURN_REGION")]
    j.sort(key=lambda e: e["clock_time"])
    recs = [path("call-1", "PRIMARY", "-0.0040000000000000000000000000001", "2025-10-01T00:10:00Z"),
            path("call-1", "HORIZON_ONLY", "0.0010", "2025-10-01T04:00:00Z"),
            path("call-1", "ENTRY_DELAY_120", None, None, "NO_ENTRY"),
            path("call-3", "PRIMARY", "0.0025000000000000000000000000003", "2025-10-05T12:00:00Z"),
            path("call-3", "HORIZON_ONLY", None, None, "CENSORED"),
            sample("2025-09-30T23:00:00Z"), sample("2025-10-01T01:00:00Z", "DOWN", "UP")]
    eng = {"adviser": {"eval_start": "2025-09-01T00:00:00+00:00", "eval_end": "2025-10-07T00:00:00+00:00"}}
    base = {"funnel": {"issued": 2, "a_confirmations": 4, "waiting": {"opened": 2}}}
    return eng, j, recs, base


def test_monthly_sections_attribute_calls_to_issue_month_and_reconcile_exactly():
    eng, j, recs, base = periods_fixture()
    pr = rp.periods(engine=eng, journal=j, records=recs, base=base)
    sep, octo = pr["months"]["2025-09"], pr["months"]["2025-10"]
    assert (sep["start"], sep["end"], octo["end"]) == ("2025-09-01T00:00:00+00:00", "2025-10-01T00:00:00+00:00",
                                                       "2025-10-07T00:00:00+00:00")
    assert sep["calls"]["call_ids"] == ["call-1"] and octo["calls"]["call_ids"] == ["call-3"]
    assert sep["calls"]["resolved_after_period_end"] == 1 and sep["calls"]["guidance_outcome"] == {"INVALIDATED": 1}
    assert octo["calls"]["ongoing_at_last_commit"] == 1
    assert sep["hypothetical"]["PRIMARY"]["exits_after_period_end"] == 1
    assert sep["hypothetical"]["ENTRY_DELAY_120"]["status"] == {"NO_ENTRY": 1}
    assert octo["hypothetical"]["HORIZON_ONLY"]["censored_or_unresolved"] == 1
    assert sep["waits"] == {"opened": 2, "observed_usable_return": 0, "endings": {
        "ISSUE": 1, "TERMINAL:ORIGINAL_SETUP_DEADLINE": 1}, "ended_after_period_end": 1}
    assert octo["waits"]["opened"] == 0 and (sep["a_confirmations"], octo["a_confirmations"]) == (2, 2)
    assert octo["a_routing"] == {"IMMEDIATE_ISSUED": 1, "TERMINAL:NO_ECONOMIC_RETURN_REGION": 1}
    # coverage uses minutes: the unavailable hour is in September only; samples by sample time
    assert sep["coverage"]["unavailable_minutes"] == 60 and octo["coverage"]["unavailable_minutes"] == 0
    assert (sep["market_view_samples"]["samples"], octo["market_view_samples"]["samples"]) == (1, 1)
    total = pr["total"]
    assert total["calls"]["issued"] == 2 and total["coverage"]["minutes"] == 36 * 1440
    assert Decimal(total["hypothetical"]["PRIMARY"]["sum_price_net_normalized"]) == \
        Decimal("-0.0014999999999999999999999999998")  # exact, beyond the 28-digit default context
    assert pr["reconciliation"]["all_passed"], pr["reconciliation"]["checks"]
    md = "\n".join(rp.render_markdown({"periods": pr}))
    assert "| TOTAL |" in md and "| 2025-09 |" in md and "not an account return" in md
    assert "Reconciliation total vs months: PASS" in md


def test_monthly_sections_detect_a_mismatch_and_skip_single_month_windows():
    eng, j, recs, base = periods_fixture()
    bad = rp.periods(engine=eng, journal=j, records=recs, base={**base, "funnel": {**base["funnel"], "issued": 3}})
    assert not bad["reconciliation"]["all_passed"] and not bad["reconciliation"]["checks"]["calls_equal_report_total"]
    one = {"adviser": {"eval_start": "2025-09-01T00:00:00+00:00", "eval_end": "2025-10-01T00:00:00+00:00"}}
    assert rp.periods(engine=one, journal=j, records=recs, base=base) is None and not rp.is_multi_month(one)


def test_launch_pins_name_method_build_costs_clock_and_primary_60s():
    f = ps.load_presets(ps.PRESETS_FILE)
    assert f is not None
    adv = {"method": "v0.4", "build": "abc+image", "format": "algotrader.adviser-runtime.v4", "tick": "0.1",
           "clock_policy": "temporal.clock.modeled-complete-prefix.v1", "profile": {"execution": "HISTORICAL_BASE"},
           "channels": {}, "eval_start": "2025-09-01T00:00:00+00:00", "eval_end": "2026-01-01T00:00:00+00:00",
           "warmup_start": "2025-07-28T00:00:00+00:00", "tail_end": "2026-01-01T06:05:00+00:00",
           "clock_end": "2026-01-01T06:05:00Z",
           "identity": {"model": "btc.context-action.v0.4", "rules_version": "mp003.rules.v0.4", "rules_sha256": "r",
                        "register_sha256": "g", "implementation": "adviser.core.v4", "identity_sha256": "i",
                        "capability_profile_sha256": "p", "pins": {"pack_id": "pack-x"}},
           "evaluator": {"format": "algotrader.adviser-evaluation.v1", "sha256": "e", "profiles": {
               "PRIMARY": {"fee_per_leg": "0.0005", "allowance_per_leg": "0.0002", "entry_delay_seconds": 60,
                           "exit_delay_seconds": 60, "exit_mode": "GUIDANCE", "funding": "PRICE_NET_ONLY",
                           "adequacy_envelope_bps": "14"}}}}
    lp = rp.launch_pins({"adviser": adv})
    assert lp["primary_is_60s"] and lp["build"] == "abc+image" and lp["rules_version"] == "mp003.rules.v0.4"
    assert lp["costs"]["PRIMARY"]["fee_per_leg"] == "0.0005" and lp["pack_id"] == "pack-x"
    md = "\n".join(rp.render_markdown({"launch_pins": lp}))
    assert "PRIMARY entry delay 60 s" in md and "build `abc+image`" in md


def test_month_bounds_are_calendar_months_clipped_to_the_window():
    b = rp.month_bounds(T("2025-09-01T00:00Z"), T("2026-01-01T00:00Z"))
    assert [m for m, _, _ in b] == ["2025-09", "2025-10", "2025-11", "2025-12"]
    assert sum(int((hi - lo).total_seconds() // 60) for _, lo, hi in b) == 122 * 1440
    assert rp.month_bounds(T("2025-09-15T12:00Z"), T("2025-10-01T00:00Z")) == [
        ("2025-09", T("2025-09-15T12:00Z"), T("2025-10-01T00:00Z"))]
    assert UTC is not None
