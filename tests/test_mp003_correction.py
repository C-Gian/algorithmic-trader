"""WP-012 correction F1 (Director review): an interval straddling a supersession that reaches the OLD active V but
not the new V cannot certify a clean continuation of the new anchor.

Tape (the Director probe): first ARM published 03:45:30 (R 100000, V1 99800); the complete [03:45,04:00) clean reaction
supersedes it at the actual publication 04:00:30 (30 s closure allowance; the minute [03:59,04:00) received 30 s late):
R2 99850, V2 99650. The newly admitted complete minute [04:00,04:01) spans that publication; no finer order is known.
Fail-before (e434d43): low 99750 (old V touched, new V not) was ignored and epoch 2 confirmed at 04:14.
Fixed-after: ANCHOR_LOST UNASSESSABLE (SUPERSEDED_ANCHOR_CONTACT_TIME_AMBIGUOUS_EPOCH_1), same owner WATCH, contact
interval end retained; a later genuine deeper replacement is allowed. LONG and positive-price mirrored SHORT."""

from __future__ import annotations

import json
import zlib
from datetime import timedelta

import adviser4_fixtures as fx
import pytest
from adviser3_fixtures import DAY2, Stepper
from test_mp003_paths import _late_tape, flip, main_records

from algotrader.adviser import engine, methods
from algotrader.adviser.harness import build_events, make_runtime, temporal_for
from algotrader.feed.ordering import canonical
from algotrader.temporal import engine as te

D = fx.D
ALLOWANCE = timedelta(seconds=30)


def tape(low_0400=99750, low_0401=None):
    ms = _late_tape(99900)
    ms[fx.index_of(fx.T(4, 0))] = fx.minute(100100, 100100, low_0400, 99950)
    if low_0401 is not None:
        ms[fx.index_of(fx.T(4, 1))] = fx.minute(99950, 99950, low_0401, 99950)
    return ms


def _side(ms, side):
    return ms if side == "L" else fx.mirror(ms)


def _events(ms):
    return fx.delayed_events(ms, {fx.index_of(fx.T(3, 59)): 30})


def run(ms):
    st = Stepper(ms, events=_events(ms), method="v0.4", allowance=ALLOWANCE)
    st.finish()
    return st


def rows(st):
    return [(r["env"]["clock_time"][11:19], r["transition"], r["anchor_epoch"], r["anchor_status"],
             (r["reason"] or "").split(":")[0] or None) for r in main_records(st.journal)]


HEAD = [("03:30:30", "BIRTH", None, "NONE", "FALSE_AT_OR_AFTER_RELEASE_TO_TRUE"),
        ("03:45:30", "ARM", 1, "ACTIVE", None),
        ("04:00:30", "REVISE", 2, "ACTIVE", "LOWER_CLEAN_REACTION_REANCHOR")]


@pytest.mark.parametrize("side", ["L", "S"])
def test_straddling_supersession_old_v_only_contact_makes_the_new_anchor_unassessable(side):
    st = run(_side(tape(), side))
    got = rows(st)
    assert got[:6] == HEAD + [
        ("04:01:00", "ANCHOR_LOST", 2, "UNASSESSABLE", "SUPERSEDED_ANCHOR_CONTACT_TIME_AMBIGUOUS_EPOCH_1"),
        ("04:15:30", "REARM", 3, "ACTIVE", "NEW_COMPLETE_STRICTLY_DEEPER_CLEAN_REACTION"),
        ("04:17:00", "CONFIRM", 3, "FROZEN_AT_CONFIRMATION", "okx/BTC-USDT-SWAP/trade_bar_1m#obs@2025-09-01T04")]
    assert not [r for r in got if r[1] == "CONFIRM" and r[2] == 2]  # never a confirmation using epoch 2
    recs = main_records(st.journal)
    lost, rearm = recs[3], recs[4]
    assert lost["status"] == "WATCH" and lost["discovery_owner"] == "OCCUPIED"  # same structural owner
    prev = lost["previous_anchor"]
    assert (prev["epoch"], prev["status"], flip(prev["V"], side)) == ("2", "UNASSESSABLE", D("99650"))
    assert prev["interval"].endswith("@2025-09-01T04:00:00Z")
    assert prev["interval_end"] == "2025-09-01T04:01:00+00:00"  # the replacement cutoff is retained
    # the later replacement comes from a bar ending after that cutoff and is published prospectively
    assert rearm["anchor_source"].endswith("/15m/2025-09-01T04:00:00+00:00")
    assert rearm["anchor_published_at"] == rearm["env"]["clock_time"] == "2025-09-01T04:15:30Z"
    assert {r["original_expiry"] for r in recs} == {recs[0]["original_expiry"]}  # original deadline unchanged


@pytest.mark.parametrize("side", ["L", "S"])
def test_control_neither_active_domain_v_touched_keeps_the_new_anchor(side):
    got = rows(run(_side(tape(low_0400=99850), side)))
    assert not [r for r in got if r[1] == "ANCHOR_LOST"]
    assert got[:4] == HEAD + [("04:14:00", "CONFIRM", 2, "FROZEN_AT_CONFIRMATION",
                                "okx/BTC-USDT-SWAP/trade_bar_1m#obs@2025-09-01T04")]


@pytest.mark.parametrize("side", ["L", "S"])
def test_control_new_v_reached_in_the_straddling_interval_is_the_existing_ambiguity(side):
    got = rows(run(_side(tape(low_0400=99600), side)))
    assert got[3] == ("04:01:00", "ANCHOR_LOST", 2, "UNASSESSABLE", "ANCHOR_CONTACT_TIME_AMBIGUOUS")


@pytest.mark.parametrize("side", ["L", "S"])
def test_control_wholly_after_supersession_touching_only_the_old_v_never_resurrects_it(side):
    """[04:00,04:01) clean (low 99900); [04:01,04:02) - wholly after the 04:00:30 publication - reaches 99750, below
    the superseded V1 99800 but above the active V2 99650: the inactive level is not a contact."""
    got = rows(run(_side(tape(low_0400=99900, low_0401=99750), side)))
    assert not [r for r in got if r[1] == "ANCHOR_LOST"]
    assert [r[1:3] for r in got[3:4]] == [("CONFIRM", 2)]


@pytest.mark.parametrize("side", ["L", "S"])
def test_control_dead_lost_domain_is_never_retested(side):
    """A domain that ended by a LOSS is never re-tested: after the 04:01 loss and the 04:15:30 REARM, the next minutes
    stay above the replacement's V; the old V1/V2 levels (both dead) never create another loss."""
    got = rows(run(_side(tape(), side)))
    assert [r[1] for r in got].count("ANCHOR_LOST") == 1


# -- production pack/unpack immediately before/after the supersession and the contact ------------------------------------

def _engine_doc(rt, end):
    cfg, rel = rt.core.cfg, methods.get("v0.4")
    return {"format": rel.engine_format, "adviser": {
        "method": rel.key, "format": rel.runtime_format,
        "identity": rel.composite_identity(cfg.profile, {"instrument": cfg.instrument}, None),
        "profile": cfg.profile.model_dump(mode="json"), "tick": str(cfg.tick), "clock_policy": cfg.clock_policy,
        "eval_start": DAY2.isoformat(), "eval_end": end.isoformat(), "origin": cfg.origin, "channels": cfg.channel_ids,
        "evaluator": rt.ev.identity(), "build": None}}


def _fold(ms, cuts=()):
    evs = _events(ms)
    _, cov = build_events(fx.DAY1, ms)
    end = fx.DAY1 + len(ms) * timedelta(minutes=1)
    rt = make_runtime(eval_start=DAY2, eval_end=end, method="v0.4")
    temporal = temporal_for(cov, allowance=ALLOWANCE)
    rt.attach(temporal)
    eng, cuts, journal, kinds = _engine_doc(rt, end), sorted(cuts), [], []
    for i, e in enumerate(evs):
        while cuts and e.available_time > cuts[0]:
            journal += rt.take()[0]
            blob, sha = engine.pack_runtime(rt)
            kinds.append(json.loads(zlib.decompress(blob))["core"]["format"])
            temporal = te.unpack(*te.pack(temporal))
            rt = engine.unpack_runtime(blob, sha, eng)
            assert canonical(rt.encode()) == zlib.decompress(blob)  # exact round trip (canonical + hash guards)
            rt.attach(temporal)
            cuts.pop(0)
        temporal.on_event(e, i)
        rt.before_admit(e)
        rt.admit(e, i)
    temporal.finish(end)
    rt.finish(end)
    return journal + rt.take()[0], kinds


CUTS = (fx.T(4, 0, ) + timedelta(seconds=15), fx.T(4, 0) + timedelta(seconds=45),
        fx.T(4, 1) + timedelta(seconds=15), fx.T(4, 15) + timedelta(seconds=45))


@pytest.mark.parametrize("side", ["L", "S"])
def test_production_pack_unpack_around_the_supersession_and_the_contact_gives_identical_outputs(side):
    ms = _side(tape(), side)
    base, _ = _fold(ms)
    restored, fmts = _fold(ms, CUTS)
    assert [e["digest"] for e in restored] == [e["digest"] for e in base]
    assert set(fmts) == {"algotrader.adviser-state.v4"}
    assert any(r["transition"] == "ANCHOR_LOST" for r in (e["record"] for e in base if e["kind"] == "scenario"))


# -- live path (recorded receipts: every supersession is published at a tick inside the next minute) ----------------------
# Live minute rhythm (test_mp003_live): quote at close+0.5 s, bars received at close+1 s, dispatch tick at close+1.5 s.
# The 04:00 supersession is published at 04:00:01.5, so [04:00,04:01) straddles it; its low reaches only the old V.

def _live_feed(sess, clock, ms, start, end):
    from algotrader.adviser.core import Quote
    from algotrader.feed.contracts import Family

    t = start
    while t < end:
        m = ms[int((t - fx.DAY1) / timedelta(minutes=1))]
        close = t + timedelta(minutes=1)
        clock.t = close + timedelta(milliseconds=500)
        sess.on_quote(Quote(m.c, m.c, clock.t, clock.t, "BTC-USDT-SWAP", "q" * 64), clock.t)
        clock.t = close + timedelta(seconds=1)
        for fam in (Family.TRADE_BAR_1M, Family.MARK_BAR_1M, Family.INDEX_BAR_1M):
            ohlc = (m.o, m.h, m.lo, m.c) if fam == Family.TRADE_BAR_1M else (m.c, m.c, m.c, m.c)
            sess.on_live_bar(fam, t, ohlc, ("100", "1", str(m.c)), clock.t)
        clock.t = close + timedelta(milliseconds=1500)
        sess.tick(clock.t)
        t = close


LIVE_START, LIVE_END = fx.T(3, 46), fx.T(4, 30)


def _live_session(ms, persisted=None, clock=None):
    from test_adviser_live import COMPAT, Clock, fetcher

    from algotrader.adviser import live as lv

    clock = clock or Clock(LIVE_START + timedelta(seconds=30))
    sess = lv.LiveSession(compat=COMPAT, build="test", clock=clock, method="v0.4")
    sess.start(persisted, fetcher(ms))
    sess.on_connection("CONNECTED", clock.t)
    return sess, clock


def _structural(journal):
    return [(r["scenario_id"], r["env"]["clock_time"], r["transition"], r["anchor_epoch"], r["anchor_status"],
             r["reason"], r["trigger_level"], r["invalidation_level"], json.dumps(r["previous_anchor"], sort_keys=True))
            for r in (e["record"] for e in journal if e["kind"] == "scenario")]


def _live_uninterrupted(ms):
    sess, clock = _live_session(ms)
    _live_feed(sess, clock, ms, LIVE_START, LIVE_END)
    return sess.driver.take()[0]


@pytest.mark.parametrize("side", ["L", "S"])
@pytest.mark.parametrize("cut", [fx.T(3, 59), fx.T(4, 0), fx.T(4, 1)],
                         ids=["before_supersession", "after_supersession_before_contact", "after_contact"])
def test_live_restart_from_persisted_state_around_supersession_and_contact_gives_the_same_lineage(side, cut):
    from test_adviser_live import _persisted

    ms = _side(tape(), side)
    want = _live_uninterrupted(ms)
    lost = [x for x in _structural(want) if x[2] == "ANCHOR_LOST"]
    assert lost and lost[0][5].startswith("SUPERSEDED_ANCHOR_CONTACT_TIME_AMBIGUOUS_EPOCH_1")
    a, clock = _live_session(ms)
    _live_feed(a, clock, ms, LIVE_START, cut)
    first = a.driver.take()[0]
    p = {**_persisted(a), "method": "v0.4"}
    b, _ = _live_session(ms, persisted=p, clock=clock)  # production LiveDriver decode of the persisted blobs
    assert b.epoch.run_id == a.epoch.run_id  # lineage continues (no reset)
    _live_feed(b, clock, ms, cut, LIVE_END)
    assert _structural(first + b.driver.take()[0]) == _structural(want)


@pytest.mark.db
def test_durable_live_store_save_and_restore_between_supersession_and_contact(database_url):
    """One isolated durable case: the live session state is saved through the production LiveStore after every minute
    (cadence 1 minute) into the disposable database, the process 'restarts' from LiveStore.load_state() between the
    04:00:01.5 supersession and the straddling contact minute, and the stored journal reproduces the uninterrupted
    structural lineage (ANCHOR_LOST UNASSESSABLE at 04:01:01, no epoch-2 confirmation)."""
    from pack_fixtures import connect

    from algotrader.adviser import live as lv

    ms = tape()
    want = _live_uninterrupted(ms)
    with connect(database_url) as c:
        c.execute("DELETE FROM adviser_live_sessions")
        c.execute("DELETE FROM adviser_live_state")
        sid = lv.start_session(c, "http://x", "v0.4")
        c.execute("UPDATE adviser_live_sessions SET status = 'running', lease_owner = 'w', lease_generation = 1 "
                  "WHERE session_id = %s", (sid,))
        store = lv.LiveStore(c, sid, "w", 1)
        a, clock = _live_session(ms)
        t = LIVE_START
        while t < fx.T(4, 1):  # through the minute ending 04:00 (supersession published), saved every minute
            _live_feed(a, clock, ms, t, t + timedelta(minutes=1))
            store.save(a)
            t += timedelta(minutes=1)
        persisted = store.load_state()
        assert persisted["method"] == "v0.4"
        b, _ = _live_session(ms, persisted={**persisted, "temporal_blob": bytes(persisted["temporal_blob"]),
                                            "adviser_blob": bytes(persisted["adviser_blob"])}, clock=clock)
        assert b.epoch.run_id == a.epoch.run_id
        while t < LIVE_END:
            _live_feed(b, clock, ms, t, t + timedelta(minutes=1))
            store.save(b)
            t += timedelta(minutes=1)
        rows = c.execute("SELECT kind, record FROM adviser_journal WHERE run_id = %s ORDER BY seq",
                         (a.epoch.run_id,)).fetchall()
    got = _structural([{"kind": r["kind"], "record": r["record"]} for r in rows])
    assert got == _structural(want)
    assert not [x for x in got if x[2] == "CONFIRM" and x[3] == 2]
