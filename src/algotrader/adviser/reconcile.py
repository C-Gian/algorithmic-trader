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
from .contracts import KIND_CONTRACTS
from .core import INITIAL_JOURNAL
from .evaluator import INITIAL_RECORDS

SCOPE = (" Version 5 (adviser evaluation runs, engine observe.stream.v3) additionally verifies the professional "
         "outputs' runtime integrity: adviser state SHA-256 and commitments at every committed range; the semantic.v2 "
         "journal and adviser-evaluation.v1 records recomputed from their stored bytes (digest, contiguous sequence, "
         "chain) against every range and the finish; the terminal adviser restore state; for completed runs the "
         "professional clock-end finish re-derived from that verified state (tail timers only); and call/attempt "
         "lineage, revision contiguity and immutability. PASS is runtime integrity, not profit, forecast quality or an "
         "independent audit of the original sources; it shares the method implementation.")


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
        if k not in KIND_CONTRACTS:
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
    check("adviser_lineage_immutability", not lp, "; ".join(lp[:5]) or
          f"{len(calls)} unique call(s), contiguous revisions, one terminal each; {len(births)} attempt(s) born once "
          "and ended at most once; revisions never restate original geometry")
    summary["calls"] = len(calls)
    return summary
