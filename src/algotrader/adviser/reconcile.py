"""Adviser runtime-integrity checks for terminal reconciliation (validator ``observe.stream-reconciliation`` v5,
``observe.stream.v3`` adviser evaluation runs only).

PASS means runtime integrity of the professional outputs — NOT profit, correct professional forecasts or an audit of
the original sources:

1. every committed range records the adviser state SHA-256 and commitments (professional sequence, factual cursor
   == range end, journal/evaluation sequence + chain); sequences never decrease;
2. the semantic journal and the evaluation records are recomputed from the stored record bytes (canonical digest,
   contiguous sequence, chained hash) and must equal every range commitment and the finish commitment;
3. the terminal adviser restore state verifies (SHA-256, exact round trip, cursor, journal sequence) and equals the
   last range's recorded adviser SHA-256;
4. completed runs: the professional clock-end finish is re-derived from the verified terminal temporal + adviser
   state (bounded: the tail timers only, no history replay) and must reproduce the committed finish commitment and
   the digests of the finish records;
5. lineage/immutability: unique call ids, contiguous revisions, one terminal per call, attempts born once and ended
   once, revisions never carry original geometry, only known semantic kinds.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from ..feed.ordering import canonical
from .contracts import KIND_CONTRACTS, KIND_CONTRACTS_V3, KIND_CONTRACTS_V4, KIND_CONTRACTS_V5
from .core import INITIAL_JOURNAL
from .evaluator import INITIAL_RECORDS

SCOPE = (" Version 5 (adviser evaluation runs, engine observe.stream.v3) additionally verifies the professional "
         "outputs' runtime integrity: adviser state SHA-256 and commitments at every committed range; the semantic.v2 "
         "journal and adviser-evaluation.v1 records recomputed from their stored bytes (digest, contiguous sequence, "
         "chain) against every range and the finish; the terminal adviser restore state; for completed runs the "
         "professional clock-end finish re-derived from that verified state (tail timers only); and call/attempt "
         "lineage, revision contiguity and immutability. PASS is runtime integrity, not profit, forecast quality or an "
         "independent audit of the original sources; it shares the method implementation.")
SCOPE_V6 = (" Version 6 (WP-011 MP-002 v0.3 adviser runs, engine observe.stream.v4) additionally binds the pinned "
            "method release (packaged MP-002 rules/register identity, runtime format and engine format must match the "
            "engine document; another release fails) and checks v0.3 lineage: every structural scenario born once and "
            "terminal at most once, contiguous scenario transitions, every child entry attempt linked to a born "
            "scenario with at most one ISSUE and at most one terminal, and every v0.3 call linked to exactly one "
            "issuing entry attempt and its scenario. PASS remains runtime integrity, not profit or forecast quality.")
SCOPE_V7 = (" Version 7 (WP-012 MP-003 v0.4 adviser runs, engine observe.stream.v5) applies the version-6 binding and "
            "lineage checks to the pinned v0.4 release (MP-003 rules manifest: delta plus inherited MP-002 rules/"
            "disposition and MP-001 rules, register, runtime and engine format) and additionally checks the "
            "pre-confirmation A anchor lineage: anchor epochs contiguous from 1, first ARM once, REVISE only from an "
            "active anchor, ANCHOR_LOST only from ARMED, REARM only after a loss, every anchor publication equal to "
            "its own dispatch time, an immutable destination-monitoring origin equal to the first arm publication, "
            "no anchor transition after the first confirmation and a confirmation strictly after its anchor's "
            "publication. PASS remains runtime integrity, not profit or forecast quality.")
SCOPE_V8 = (" Version 8 (WP-014 MP-004 v0.5 adviser runs, engine observe.stream.v6) applies the version-7 binding, "
            "lineage and anchor checks to the pinned v0.5 release (MP-004 rules manifest: delta and Director closure "
            "plus the inherited MP-003 disposition, MP-002 rules/disposition and MP-001 rules, register, runtime and "
            "engine format) and additionally checks the A RETURN response lineage from the stored entry-attempt "
            "records: at most one reference per child, prepared only from WAIT_RETURN and published at its own "
            "dispatch time and cursor; the reference never changes afterwards; no record after a child's ending; "
            "every RETURN call issued by a child holding a pre-existing reference, decided by a complete bar starting "
            "at/after that publication in a strictly later dispatch; never a RETURN_USABLE record; and each closing "
            "record's response outcome consistent with its transition/reason. PASS remains runtime integrity, not "
            "profit or forecast quality.")


def _chain(rows: list[dict], initial: str) -> tuple[list[str], str | None]:
    problems: list[str] = []
    h = initial
    expect = 1
    for r in rows:
        if r["seq"] != expect:
            problems.append(f"sequence gap: expected {expect}, found {r['seq']}")
            break
        digest = hashlib.sha256(canonical(r["record"])).hexdigest()
        if digest != r["digest"]:
            problems.append(f"seq {r['seq']} stored digest differs from its record bytes")
            break
        h = hashlib.sha256(bytes.fromhex(h) + bytes.fromhex(digest)).hexdigest()
        if h != r["chain"]:
            problems.append(f"seq {r['seq']} stored chain differs from the recomputed chain")
            break
        r["_chain"] = h
        expect += 1
    return problems, (h if not problems else None)


def checks(check, *, status: str, ranges: list[dict], terminal: dict | None, cursor: int, engine: dict,
           journal: list[dict], records: list[dict], finish: dict | None, temporal_restore) -> dict[str, Any]:
    """Run the v5 adviser checks; returns the adviser summary (adviser.json body)."""
    from .engine import AdviserStateError, unpack_runtime

    summary: dict[str, Any] = {"identity": engine["adviser"]["identity"], "journal_records": len(journal),
                               "evaluation_records": len(records)}
    method = engine["adviser"].get("method")
    v3 = method in ("v0.3", "v0.4", "v0.5")  # MP-002 scenario lineage (v0.4/v0.5 inherit it)
    kinds = (KIND_CONTRACTS_V5 if method == "v0.5" else KIND_CONTRACTS_V4 if method == "v0.4" else
             KIND_CONTRACTS_V3 if v3 else KIND_CONTRACTS)
    if v3:
        summary["method"] = method
    if v3:
        from .engine import config_from_engine, release

        try:
            rel = release(engine)
            config_from_engine(engine)
            ok = engine.get("format") == rel.engine_format
            check("adviser_method_binding", ok,
                  f"pinned release {rel.key} ({rel.model} / {rel.rules_version}, rules {rel.rules_sha256()[:12]}, "
                  f"register {rel.register_sha256()[:12]}, runtime {rel.runtime_format}, engine {rel.engine_format})"
                  if ok else f"engine format {engine.get('format')} differs from the release's {rel.engine_format}")
        except AdviserStateError as exc:
            check("adviser_method_binding", False, str(exc))
    # 1. ranges
    problems, prev = [], {"journal_seq": 0, "evaluation_seq": 0, "professional_seq": 0}
    for r in ranges:
        c = r.get("adviser_commitment")
        if not r.get("adviser_sha256") or not c:
            problems.append(f"range {r['range_seq']} has no adviser state/commitment")
            continue
        if c["factual_cursor"] != r["to_cursor"]:
            problems.append(f"range {r['range_seq']} adviser cursor {c['factual_cursor']} != {r['to_cursor']}")
        for k in prev:
            if (c.get(k) or 0) < prev[k]:
                problems.append(f"range {r['range_seq']} {k} decreases")
            prev[k] = c.get(k) or 0
    check("adviser_ranges_recorded", not problems, "; ".join(problems[:5]) or
          f"{len(ranges)} ranges record adviser state + commitments (journal {prev['journal_seq']}, evaluation "
          f"{prev['evaluation_seq']}, professional sequence {prev['professional_seq']})")
    # 2. chains
    jp, jchain = _chain(journal, INITIAL_JOURNAL)
    ep, echain = _chain(records, INITIAL_RECORDS)
    by_j = {r["seq"]: r["_chain"] for r in journal if "_chain" in r}
    by_e = {r["seq"]: r["_chain"] for r in records if "_chain" in r}
    for r in ranges:
        c = r.get("adviser_commitment") or {}
        js, es = c.get("journal_seq") or 0, c.get("evaluation_seq") or 0
        if js and by_j.get(js) != c.get("journal_chain"):
            jp.append(f"range {r['range_seq']} journal chain differs from the recomputed chain at seq {js}")
        if not js and c.get("journal_chain") not in (None, INITIAL_JOURNAL):
            jp.append(f"range {r['range_seq']} records a chain without journal records")
        if es and by_e.get(es) != c.get("evaluation_chain"):
            ep.append(f"range {r['range_seq']} evaluation chain differs at seq {es}")
    end_c = (finish or {}).get("commitment") or (ranges[-1].get("adviser_commitment") if ranges else {}) or {}
    if journal and end_c.get("journal_seq") != journal[-1]["seq"]:
        jp.append(f"stored journal ends at seq {journal[-1]['seq']} but the final commitment records "
                  f"{end_c.get('journal_seq')}")
    if journal and end_c.get("journal_chain") != jchain:
        jp.append("final journal chain differs from the recomputed chain")
    if records and end_c.get("evaluation_seq") != records[-1]["seq"]:
        ep.append("evaluation records do not end at the final committed sequence")
    if records and end_c.get("evaluation_chain") != echain:
        ep.append("final evaluation chain differs from the recomputed chain")
    check("adviser_journal_chain", not jp, "; ".join(jp[:5]) or
          f"{len(journal)} semantic.v2 records recomputed from stored bytes; chain {str(jchain)[:16]} equals every "
          "range and the final commitment")
    check("adviser_evaluation_chain", not ep, "; ".join(ep[:5]) or
          f"{len(records)} adviser-evaluation.v1 records recomputed; chain {str(echain)[:16]} equals the commitments")
    summary["journal_chain"], summary["evaluation_chain"] = jchain, echain
    # 3. terminal adviser state
    rt = None
    try:
        if terminal is None or terminal.get("adviser_blob") is None:
            raise AdviserStateError("no terminal adviser restore state")
        rt = unpack_runtime(bytes(terminal["adviser_blob"]), terminal["adviser_sha256"], engine)
        if rt.admitted != cursor:
            raise AdviserStateError(f"terminal adviser cursor {rt.admitted} != committed {cursor}")
        last = ranges[-1] if ranges else None
        if last is not None and last.get("adviser_sha256") != terminal["adviser_sha256"]:
            raise AdviserStateError("terminal adviser state differs from the last range's recorded SHA-256")
        lc = (last or {}).get("adviser_commitment") or {}
        if rt.core.journal_seq != (lc.get("journal_seq") or 0):
            raise AdviserStateError("terminal adviser journal sequence differs from the last range")
        check("adviser_terminal_state_verified", True,
              f"terminal adviser state (cursor {cursor}, professional sequence {rt.core.seq}, journal "
              f"{rt.core.journal_seq}) verified and equal to the last committed range")
    except AdviserStateError as exc:
        rt = None
        check("adviser_terminal_state_verified", False, str(exc))
    # 4. finish
    if status == "completed":
        if finish is None:
            check("adviser_finish_rederived", False, "no committed professional finish for a completed adviser run")
        elif rt is None or temporal_restore is None:
            check("adviser_finish_rederived", False, "the finish cannot be re-derived without a verified terminal state")
        else:
            try:
                clock_end = datetime.fromisoformat(str(engine["adviser"]["clock_end"]).replace("Z", "+00:00"))
                rt.attach(temporal_restore)
                temporal_restore.finish(clock_end)
                rt.finish(clock_end)
                j2, r2 = rt.take()
                from .engine import pack_runtime

                sha = pack_runtime(rt)[1]
                got = {**rt.commitment(), "temporal_commitment": temporal_restore.commitment(),
                       "temporal_clock": temporal_restore.clock.isoformat(), "adviser_sha256": sha}
                stored_j = {r["seq"]: r["digest"] for r in journal}
                stored_e = {r["seq"]: r["digest"] for r in records}
                bad = [e["seq"] for e in j2 if stored_j.get(e["seq"]) != e["digest"]]
                bad += [r["seq"] for r in r2 if stored_e.get(r["seq"]) != r["digest"]]
                ok = got == json.loads(json.dumps(finish["commitment"])) and not bad and sha == finish["adviser_sha256"]
                check("adviser_finish_rederived", ok,
                      (f"clock-end finish re-derived from the verified terminal state: {len(j2)} journal and {len(r2)} "
                       f"evaluation record(s), commitment equal") if ok else
                      f"re-derived finish differs (records {bad[:5]}, commitment equal: {got == finish['commitment']})")
                summary["finish"] = {"clock_end": clock_end.isoformat(), "journal_records": len(j2),
                                     "evaluation_records": len(r2)}
                summary["inspection"] = rt.core.inspect()
            except Exception as exc:  # noqa: BLE001 - any failure is a failed integrity check, never a pass
                check("adviser_finish_rederived", False, f"{type(exc).__name__}: {exc}")
    elif rt is not None:
        summary["inspection"] = rt.core.inspect()
    # 5. lineage / immutability
    lp: list[str] = []
    calls: dict[str, dict] = {}
    revs: dict[str, list[int]] = {}
    terminals: dict[str, int] = {}
    births: dict[str, int] = {}
    ends: dict[str, int] = {}
    for e in journal:
        k, rec = e["kind"], e["record"]
        if k not in kinds:
            lp.append(f"unknown journal kind {k}")
            continue
        if k == "call":
            if rec["call_id"] in calls:
                lp.append(f"duplicate call id {rec['call_id']}")
            calls[rec["call_id"]] = rec
        elif k == "call_revision":
            cid = rec["call_id"]
            if cid not in calls:
                lp.append(f"revision of unknown call {cid}")
            revs.setdefault(cid, []).append(rec["revision"])
            if rec["thesis_status"] != "ONGOING":
                terminals[cid] = terminals.get(cid, 0) + 1
            elif terminals.get(cid):
                lp.append(f"call {cid} revised after its terminal status")
            for forbidden in ("invalidation", "target", "structural_area", "issued_at", "hard_deadline"):
                if forbidden in rec:
                    lp.append(f"revision of {cid} carries original geometry field {forbidden}")
        elif k == "candidate":
            aid = rec["attempt_id"]
            if rec["transition"] == "BIRTH":
                births[aid] = births.get(aid, 0) + 1
            elif rec["transition"] in ("EXPIRE", "WITHDRAW", "REJECT", "ISSUE", "CLEARED"):
                ends[aid] = ends.get(aid, 0) + 1
    for cid, rs in revs.items():
        if rs != list(range(1, len(rs) + 1)):
            lp.append(f"call {cid} revisions are not contiguous from 1")
    lp += [f"call {c} has {n} terminal revisions" for c, n in terminals.items() if n > 1]
    lp += [f"attempt {a} born {n} times" for a, n in births.items() if n > 1]
    lp += [f"attempt {a} ended {n} times" for a, n in ends.items() if n > 1]
    lp += [f"attempt {a} ended without a birth" for a in ends if a not in births]
    if v3:
        lp += _v3_lineage(journal, calls)
    if method in ("v0.4", "v0.5"):
        lp += _v4_anchor_lineage(journal)
    if method == "v0.5":
        lp += _v5_response_lineage(journal)
    check("adviser_lineage_immutability", not lp, "; ".join(lp[:5]) or
          f"{len(calls)} unique call(s), contiguous revisions, one terminal each; {len(births)} attempt(s) born once "
          "and ended at most once; revisions never restate original geometry")
    summary["calls"] = len(calls)
    return summary


def _v4_anchor_lineage(journal: list[dict]) -> list[str]:
    """MP-003 pre-confirmation A anchor lineage from the stored scenario records (WP-012 §4/§5)."""
    lp: list[str] = []
    state: dict[str, dict] = {}
    anchor_moves = ("ARM", "REVISE", "REARM", "ANCHOR_LOST")
    for e in journal:
        if e["kind"] != "scenario" or e["record"]["family"] != "A":
            continue
        rec = e["record"]
        sid, tr, at = rec["scenario_id"], rec["transition"], rec["env"]["clock_time"]
        st = state.setdefault(sid, {"epoch": 0, "status": "WATCH", "origin": None, "confirmed": False, "pub": None})
        if tr in anchor_moves and st["confirmed"]:
            lp.append(f"scenario {sid} anchor transition {tr} after its first confirmation")
        if tr in ("ARM", "REVISE", "REARM"):
            want = {"ARM": ("WATCH", 0), "REVISE": ("ARMED", None), "REARM": ("WATCH", None)}[tr]
            if st["status"] != want[0] or (want[1] is not None and st["epoch"] != want[1])                     or (tr == "REARM" and st["epoch"] == 0):
                lp.append(f"scenario {sid} {tr} from status {st['status']} epoch {st['epoch']}")
            if rec["anchor_epoch"] != st["epoch"] + 1:
                lp.append(f"scenario {sid} {tr} epoch {rec['anchor_epoch']} is not {st['epoch'] + 1}")
            if _iso_z(rec["anchor_published_at"]) != at:
                lp.append(f"scenario {sid} {tr} published at {rec['anchor_published_at']} not its dispatch {at}")
            if tr == "ARM":
                st["origin"] = (rec["destination_monitoring_from"], rec["destination_monitoring_cursor"])
                if _iso_z(rec["destination_monitoring_from"]) != at:
                    lp.append(f"scenario {sid} destination monitoring origin differs from its first arm")
            st.update(epoch=rec["anchor_epoch"] or 0, status="ARMED", pub=at)
        elif tr == "ANCHOR_LOST":
            if st["status"] != "ARMED" or rec["anchor_epoch"] != st["epoch"]:
                lp.append(f"scenario {sid} ANCHOR_LOST without an active anchor epoch {st['epoch']}")
            st["status"] = "WATCH"
        elif tr == "CONFIRM":
            if st["status"] != "ARMED" or not st["pub"] or not at > st["pub"]:
                lp.append(f"scenario {sid} CONFIRM not strictly after its active anchor publication")
            if rec["anchor_status"] != "FROZEN_AT_CONFIRMATION":
                lp.append(f"scenario {sid} CONFIRM does not freeze its anchor")
            st.update(status="CONFIRMED", confirmed=True)
        if st["origin"] is not None and tr != "ARM" and                 (rec["destination_monitoring_from"], rec["destination_monitoring_cursor"]) != st["origin"]:
            lp.append(f"scenario {sid} destination monitoring origin changed at {tr}")
    return lp


_OUTCOME = {"ISSUE": ("ISSUED",), "RESPONSE_NOT_ISSUABLE": ("NOT_ISSUABLE",),
            "LOCAL_RESPONSE_CONTRADICTED": ("CONTRADICTED",), "LOCAL_CONTACT_TIME_AMBIGUOUS": ("UNASSESSABLE",)}
_REF_KEYS = ("reference_bar", "reference_start", "reference_end", "H0", "L0", "reference_close", "published_at",
             "published_cursor")


def _v5_response_lineage(journal: list[dict]) -> list[str]:
    """MP-004 A RETURN response lineage from the stored entry-attempt records (WP-014)."""
    lp: list[str] = []
    st: dict[str, dict] = {}
    for e in journal:
        if e["kind"] != "entry_attempt":
            continue
        rec = e["record"]
        eid, tr, env = rec["entry_attempt_id"], rec["transition"], rec["env"]
        x = st.setdefault(eid, {"wait": False, "ref": None, "ref_seq": None, "ended": False})
        resp = rec.get("response") or {}
        if x["ended"]:
            lp.append(f"entry attempt {eid} {tr} after its ending")
            continue
        if tr == "RETURN_USABLE":
            lp.append(f"entry attempt {eid} has a RETURN_USABLE record (v0.5 prepares a reference instead)")
        if tr == "WAIT_OPEN":
            x["wait"] = True
        elif tr == "RESPONSE_REFERENCE":
            if not x["wait"] or x["ref"] is not None:
                lp.append(f"entry attempt {eid} reference not prepared once from WAIT_RETURN")
            if (_iso_z(resp.get("published_at")) != _iso_z(env["clock_time"])
                    or str(resp.get("published_cursor")) != str(env["factual_cursor"])
                    or resp.get("phase") != "WAIT_RESPONSE"):
                lp.append(f"entry attempt {eid} reference publication differs from its own dispatch time/cursor")
            x["ref"] = {k: resp.get(k) for k in _REF_KEYS}
            x["ref_seq"] = env["professional_seq"]
        elif x["ref"] is not None and {k: resp.get(k) for k in _REF_KEYS} != x["ref"]:
            lp.append(f"entry attempt {eid} reference changed at {tr}")
        if tr not in ("ISSUE", "TERMINAL", "REJECT", "CLEARED") or rec["state"] not in ("TERMINAL", "ISSUED",
                                                                                          "CLEARED"):
            continue
        x["ended"] = True
        reason = str(rec["reason"] or "").split(":")[0].split(",")[0]
        if tr == "ISSUE" and rec.get("mode") == "RETURN" and x["ref"] is None:
            lp.append(f"entry attempt {eid} issued a RETURN call without a pre-existing reference")
        if x["ref"] is None:
            if reason in ("RESPONSE_NOT_ISSUABLE", "LOCAL_RESPONSE_CONTRADICTED", "LOCAL_CONTACT_TIME_AMBIGUOUS"):
                lp.append(f"entry attempt {eid} ended {reason} without a reference")
            continue
        key = "ISSUE" if tr == "ISSUE" else reason
        if resp.get("outcome") not in _OUTCOME.get(key, ("ENDED_BY_PRIORITY_CAUSE", "CLEARED")):
            lp.append(f"entry attempt {eid} closing outcome {resp.get('outcome')} inconsistent with {key}")
        if key in ("ISSUE", "RESPONSE_NOT_ISSUABLE", "LOCAL_RESPONSE_CONTRADICTED"):
            bar = resp.get("response_bar") or resp.get("decisive_bar")
            p0 = x["ref"]["published_at"]
            try:
                start = datetime.fromisoformat(str(bar).rsplit("@", 1)[1].replace("Z", "+00:00"))
                ok = start >= datetime.fromisoformat(str(p0).replace("Z", "+00:00"))
            except (IndexError, ValueError):
                ok = False
            if not ok or env["professional_seq"] <= (x["ref_seq"] or 0):
                lp.append(f"entry attempt {eid} decided by {bar} not wholly after its reference publication {p0} "
                          "in a later dispatch")
    return lp


def _iso_z(x) -> str | None:
    return None if x is None else str(x).replace("+00:00", "Z")


def _v3_lineage(journal: list[dict], calls: dict[str, dict]) -> list[str]:
    lp: list[str] = []
    born: dict[str, int] = {}
    terminal: dict[str, int] = {}
    entry_issue: dict[str, int] = {}
    entry_terminal: dict[str, int] = {}
    issued_call: dict[str, str] = {}
    for e in journal:
        rec = e["record"]
        if e["kind"] == "scenario":
            sid = rec["scenario_id"]
            if rec["transition"] == "BIRTH":
                born[sid] = born.get(sid, 0) + 1
            elif sid not in born:
                lp.append(f"scenario {sid} {rec['transition']} without a birth")
            if sid in terminal:
                lp.append(f"scenario {sid} transition {rec['transition']} after its terminal")
            if rec["transition"] == "TERMINAL":
                terminal[sid] = terminal.get(sid, 0) + 1
        elif e["kind"] == "entry_attempt":
            sid, eid = rec["scenario_id"], rec["entry_attempt_id"]
            if sid not in born:
                lp.append(f"entry attempt {eid} without a born scenario")
            if rec["transition"] == "ISSUE":
                entry_issue[eid] = entry_issue.get(eid, 0) + 1
                issued_call[rec["call_id"]] = eid
            if rec["state"] == "TERMINAL" or rec["transition"] == "CLEARED":
                entry_terminal[eid] = entry_terminal.get(eid, 0) + 1
    lp += [f"scenario {s} born {n} times" for s, n in born.items() if n > 1]
    lp += [f"scenario {s} has {n} terminal records" for s, n in terminal.items() if n > 1]
    lp += [f"entry attempt {a} issued {n} calls" for a, n in entry_issue.items() if n > 1]
    lp += [f"entry attempt {a} ended {n} times" for a, n in entry_terminal.items() if n > 1]
    for cid, rec in calls.items():
        if issued_call.get(cid) != rec.get("attempt_id"):
            lp.append(f"call {cid} is not linked to exactly one issuing entry attempt")
        if rec.get("scenario_id") is None or rec.get("scenario_id") not in born:
            lp.append(f"call {cid} has no born scenario")
    return lp
