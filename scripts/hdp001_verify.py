"""HDP-001 verification executor (offline). Not product code; never run automatically.

Applies the frozen HDP-001 protocol to locally stored, already verified ``marketdata.v1`` datasets of OKX
BTC-USDT-SWAP. It downloads nothing, opens no service or database, and never updates the reference, the study status
or the exposure register: it only writes a NEW output directory.

Authoritative sources (pinned by SHA-256 below; a VERIFICATION run refuses to start if any differs):
  delivery/HDP-001-HOURLY-DIRECTIONAL-PERSISTENCE.md   protocol
  delivery/HDP-001-DIRECTOR-CLOSURE.md                 registration, seed 0
  delivery/HDP-001-EXPLORATION-CLOSURE.md              constant UP, window, conventions, boundary
  delivery/HDP-001-A-V06-REFERENCES-DECISION.md        completeness, UNAVAILABLE vs not evaluable, fixed UP
Operational index: delivery/HDP-001-VERIFICATION-REFERENCES.md (bootstrap draw procedure registered there first).

Construction (decision §1):
  H(e) = trade 1h bar [e-1h, e), built by the existing ``temporal.v1`` engine from the dataset's causal feed (modeled
  availability, zero delay; seal-no-revision). C_e = its close only when its status is COMPLETE: all 60 minutes present
  and valid. The last minute's close alone never certifies an hour; nothing is interpolated or substituted.
  prediction(t) = sign(C_t - C_(t-1h)) if H(t-1h) and H(t) are COMPLETE, else PREDICTION_UNAVAILABLE (FLAT = abstention)
  outcome(t)    = sign(C_(t+1h) - C_t) if t+1h < window end and H(t), H(t+1h) are COMPLETE, else OUTCOME_UNAVAILABLE;
                  the cutoff with t+1h = end is BOUNDARY_NOT_SCORED and H(end) is never loaded or read.
  Constant reference: UP, fixed by the exploration closure; never recomputed.

Integrity: an identified gap (an INCOMPLETE hour with its recorded reasons) becomes UNAVAILABLE with grid and masks kept;
any check that cannot attest identity, instrument, price role, timestamps/grid, bar validity or aggregate construction
makes the result NOT_EVALUABLE (no computation). No minimum coverage percentage exists.

Usage (only under a separate executive assignment, after 2027-01-25):
  uv run python scripts/hdp001_verify.py --assignment "<assignment reference>" --out <new_dir> <dataset_dir> [...]
Synthetic executions run only through tests (``run(..., mode="SYNTHETIC")``) and are labelled as such.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import platform
import random
import statistics
import sys
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

from algotrader import version
from algotrader.feed.adapter import build_feed
from algotrader.feed.contracts import EventKind, Family
from algotrader.feed.ordering import FeedError, canonical, modeled_availability
from algotrader.marketdata import dataset as md
from algotrader.temporal import engine as te
from algotrader.temporal.contracts import AggregateStatus, Horizon

EXECUTOR_ID = "hdp001.verify.v1"
ROOT = Path(__file__).resolve().parents[1]
HOUR = timedelta(hours=1)
MINUTE = timedelta(minutes=1)
DIRECTIONAL = ("UP", "DOWN")
FLAGS = ("BOUNDARY_NOT_SCORED", "PREDICTION_UNAVAILABLE", "PREDICTION_FLAT", "OUTCOME_UNAVAILABLE")
AUTHORITATIVE = {
    "delivery/HDP-001-HOURLY-DIRECTIONAL-PERSISTENCE.md": "7fb2f545a92436fac3fe32a05c23d700ef26a6771f8e7970a74060f1f581f6d1",
    "delivery/HDP-001-DIRECTOR-CLOSURE.md": "195a11ccc876bf641db58053391b88ce0835f0b79486795ca43b18464e0203e1",
    "delivery/HDP-001-EXPLORATION-CLOSURE.md": "b8c33cd32a887b38b9525b0f966c6cd9754cb25934df8492083846a201597d0e",
    "delivery/HDP-001-A-V06-REFERENCES-DECISION.md": "7b91a1b3e667965dba19cb8771285fd39c4f662d7c7c06882feae2795c77ffb8",
}
OPERATIONAL_INDEX = "delivery/HDP-001-VERIFICATION-REFERENCES.md"
EXTERNAL_PROVENANCE = (
    "authenticity of the raw OKX responses: hashes prove the stored bytes are unchanged since acquisition, not that "
    "they are genuine exchange data; the acquisition's own record (dataset retrieval times, base URL, operator) must "
    "be accepted separately",
    "agreement of OKX history-candle prices with the traded market (no independent price source is compared)",
    "that no dataset was produced or altered before its hashes were first recorded",
)


@dataclass(frozen=True)
class StudyConfig:
    window_start: datetime
    window_end: datetime
    block_hours: int = 168
    resamples: int = 10000
    seed: int = 0
    reference: str = "UP"
    instrument: str = "BTC-USDT-SWAP"
    price_role: str = "trade"
    p_lo: float = 0.025
    p_hi: float = 0.975

    def doc(self) -> dict:
        d = asdict(self)
        d["window_start"], d["window_end"] = iso(self.window_start), iso(self.window_end)
        return d

    def sha256(self) -> str:
        return hashlib.sha256(canonical(self.doc())).hexdigest()


FROZEN = StudyConfig(datetime(2026, 11, 2, tzinfo=UTC), datetime(2027, 1, 25, tzinfo=UTC))


def iso(t: datetime | None) -> str | None:
    return None if t is None else t.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha_lf(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def sign(d: Decimal) -> str:
    return "UP" if d > 0 else "DOWN" if d < 0 else "FLAT"


# -- grid and required input ---------------------------------------------------------------------------------------

def grid(cfg: StudyConfig) -> list[datetime]:
    out, t = [], cfg.window_start
    while t < cfg.window_end:
        out.append(t)
        t += HOUR
    return out


def required_minutes(cfg: StudyConfig) -> tuple[datetime, datetime]:
    """Trade 1m range read: H(start-1h) .. H(end-1h), i.e. [start-2h, end-1h). H(end) is never needed."""
    return cfg.window_start - 2 * HOUR, cfg.window_end - HOUR


def block_lengths(n: int, L: int) -> list[int]:
    k = math.ceil(n / L)
    return [L] * (k - 1) + [n - L * (k - 1)]


# -- integrity bookkeeping -----------------------------------------------------------------------------------------

@dataclass
class Checks:
    items: list[dict] = field(default_factory=list)

    def add(self, check_id: str, ok: bool, detail: str, scope: str = "INTERNAL_CONSISTENCY") -> bool:
        self.items.append({"id": check_id, "passed": bool(ok), "scope": scope, "detail": detail})
        return bool(ok)

    @property
    def passed(self) -> bool:
        return all(c["passed"] for c in self.items)


@dataclass(frozen=True)
class HourBar:
    end: datetime
    status: str  # COMPLETE | INCOMPLETE
    close: Decimal | None  # only when COMPLETE
    known_at: datetime
    valid: int
    expected: int
    reasons: dict


# -- input: datasets -> causal feed -> temporal.v1 1h trade aggregates ---------------------------------------------

def load_hours(paths: list[Path], cfg: StudyConfig, checks: Checks) -> tuple[dict[datetime, HourBar] | None, list[dict]]:
    """Hourly trade bars of the required range, or None when the input cannot be attested (NOT_EVALUABLE)."""
    lo, hi = required_minutes(cfg)
    inputs: list[dict] = []
    manifests = []
    for p in paths:
        try:
            problems = md.verify(p)
        except Exception as exc:  # unreadable artifacts are a failed attestation, not a crash
            problems = [f"verification raised {type(exc).__name__}: {exc}"]
        ok = checks.add("C1_DATASET_VERIFY", not problems, f"{p.name}: " + ("; ".join(problems) or
                        "manifest, file hashes/sizes, row counts, raw pages and dataset_id recomputed"))
        if not ok:
            inputs.append({"path": p.name, "verify_problems": problems})
            continue
        m = md.load_manifest(p)
        manifests.append((p, m))
        inputs.append({"dataset_id": m.dataset_id, "manifest_sha256": md.sha256_file(p / "manifest.json"),
                       "request": [iso(m.request.start), iso(m.request.end)], "base_url": m.request.base_url,
                       "inst_id": m.instrument.inst_id, "inst_type": m.instrument.inst_type,
                       "retrieval": [iso(m.retrieval_started_at), iso(m.retrieval_finished_at)],
                       "quality_status": str(m.quality_status), "acquisition_code_version": m.code_version})
    if not checks.passed:
        return None, inputs
    for p, m in manifests:
        checks.add("C2_INSTRUMENT", m.instrument.source == "okx" and m.instrument.inst_id == cfg.instrument
                   and m.request.inst_id == cfg.instrument and m.instrument.inst_type == "SWAP",
                   f"{m.dataset_id}: source {m.instrument.source}, instrument {m.request.inst_id}/{m.instrument.inst_id} "
                   f"{m.instrument.inst_type}")
    spans = sorted((m.request.start, m.request.end, m.dataset_id) for _, m in manifests)
    aligned = all(s.minute == 0 and e.minute == 0 and s.second == 0 and e.second == 0 for s, e, _ in spans)
    checks.add("C3_HOUR_ALIGNED", aligned, "every dataset starts and ends on a whole UTC hour")
    contiguous = bool(spans) and all(spans[i][1] == spans[i + 1][0] for i in range(len(spans) - 1))
    checks.add("C3_CONTIGUOUS", contiguous, "datasets are contiguous, without overlap or hole: "
               + ", ".join(f"[{iso(s)}, {iso(e)})" for s, e, _ in spans))
    exact = bool(spans) and spans[0][0] == lo and spans[-1][1] == hi
    checks.add("C3_REQUIRED_RANGE", exact, f"union equals the required trade 1m range [{iso(lo)}, {iso(hi)})")
    if not checks.passed:
        return None, inputs

    hours: dict[datetime, HourBar] = {}
    docs = {d["dataset_id"]: d for d in inputs if "dataset_id" in d}
    for p, m in sorted(manifests, key=lambda x: x[1].request.start):
        doc = docs[m.dataset_id]
        try:
            hours.update(_dataset_hours(p, m, doc, cfg, checks))
        except (FeedError, te.TemporalError, ValueError) as exc:
            checks.add("C4_FEED_AND_AGGREGATION", False, f"{m.dataset_id}: {type(exc).__name__}: {exc}")
    if not checks.passed:
        return None, inputs
    want = [lo + HOUR * (i + 1) for i in range(int((hi - lo) / HOUR))]
    checks.add("C9_GRID", sorted(hours) == want and len(grid(cfg)) == int((cfg.window_end - cfg.window_start) / HOUR),
               f"{len(want)} hourly bars ending {iso(want[0])} .. {iso(want[-1])} for {len(grid(cfg))} cutoffs")
    return (hours if checks.passed else None), inputs


def _dataset_hours(p: Path, m, doc: dict, cfg: StudyConfig, checks: Checks) -> dict[datetime, HourBar]:
    hours: dict[datetime, HourBar] = {}
    policy_id = modeled_availability().policy_id
    feed = build_feed(p)  # re-verifies the dataset; modeled availability with zero delay
    fm = feed.manifest
    doc.update({"feed_content_identity": fm.content_identity, "ordered_event_hash": fm.ordered_event_hash,
                "availability_policy_id": fm.availability_policy.policy_id})
    checks.add("C4_AVAILABILITY", fm.availability_policy.policy_id == policy_id,
               f"{m.dataset_id}: availability {fm.availability_policy.policy_id} (expected {policy_id})")
    trade = [c.channel for c in fm.coverage if c.channel.family == Family.TRADE_BAR_1M]
    if not checks.add("C4_PRICE_ROLE", len(trade) == 1 and trade[0].series_id == cfg.instrument,
                      f"{m.dataset_id}: one trade_bar_1m channel for {cfg.instrument}; mark/index/funding unused"):
        return hours
    cid = trade[0].channel_id
    profile = te.profile_for_feed(fm)
    eng = te.for_feed(fm, profile)
    sealed: list = []
    eng.sealed_listeners.append(lambda r, cid=cid: sealed.append(r)
                                if r.channel_id == cid and r.horizon == Horizon.H1 else None)
    for i, e in enumerate(feed.events):
        eng.on_event(e, i)
    eng.finish()
    doc["temporal_profile_fingerprint"] = eng.fingerprint
    c = eng.counters
    checks.add("C5_TEMPORAL_COUNTERS", c["late_excluded"] == 0 and c["misaligned_excluded"] == 0
               and c["outside_coverage_excluded"] == 0,
               f"{m.dataset_id}: late {c['late_excluded']}, misaligned {c['misaligned_excluded']}, "
               f"outside coverage {c['outside_coverage_excluded']}")
    # independent recount from the trade events themselves (not from the aggregator)
    slots: dict[datetime, list] = {}
    valid_per_hour: dict[datetime, int] = {}
    for e in feed.events:
        if e.channel.channel_id == cid:
            slots.setdefault(e.event_time, []).append(e)
            if e.kind == EventKind.BAR_OBSERVATION:
                h0 = e.event_time.replace(minute=0, second=0, microsecond=0)
                valid_per_hour[h0] = valid_per_hour.get(h0, 0) + 1
    dup = [s for s, es in slots.items() if len(es) != 1]
    checks.add("C6_ONE_EVENT_PER_MINUTE", not dup and set(slots) == {
        m.request.start + i * MINUTE for i in range(int((m.request.end - m.request.start) / MINUTE))},
        f"{m.dataset_id}: exactly one trade observation or quality event per minute slot ({len(dup)} duplicated)")
    expected_starts = [m.request.start + i * HOUR for i in range(int((m.request.end - m.request.start) / HOUR))]
    checks.add("C7_ONE_RECORD_PER_HOUR", [r.interval_start for r in sealed] == expected_starts,
               f"{m.dataset_id}: one sealed 1h trade record per hour, in order ({len(sealed)} sealed, "
               f"{len(expected_starts)} expected)")
    bad = []
    for r in sealed:
        s, e = r.interval_start, r.interval_end
        n_valid = valid_per_hour.get(s, 0)
        last = slots.get(e - MINUTE, [None])[0]
        if r.status == AggregateStatus.COMPLETE:
            ok = (e - s == HOUR and r.counts.expected == r.counts.valid == 60 and n_valid == 60
                  and last is not None and last.kind == EventKind.BAR_OBSERVATION
                  and r.values.close == last.payload.close and r.known_at == e)
            hours[e] = HourBar(e, "COMPLETE", r.values.close, r.known_at, r.counts.valid, r.counts.expected,
                               dict(r.counts.reasons))
        elif r.status == AggregateStatus.INCOMPLETE:
            ok = e - s == HOUR and r.counts.valid == n_valid < 60 and r.values is None
            hours[e] = HourBar(e, "INCOMPLETE", None, r.known_at, r.counts.valid, r.counts.expected,
                               dict(r.counts.reasons))
        else:  # OUTSIDE_COVERAGE inside an attested range cannot be explained
            ok = False
        if not ok:
            bad.append(iso(s))
    checks.add("C8_AGGREGATE_CONSTRUCTION", not bad,
               f"{m.dataset_id}: COMPLETE iff 60 valid minutes (independent recount), close = last minute's close, "
               f"known at the hour end; INCOMPLETE with its reasons" + (f"; inconsistent: {bad[:5]}" if bad else ""))
    return hours


# -- samples ---------------------------------------------------------------------------------------------------------

def build_register(hours: dict[datetime, HourBar], cfg: StudyConfig) -> list[dict]:
    reg = []
    for t in grid(cfg):
        boundary = not (t + HOUR < cfg.window_end)
        prev, cur = hours.get(t - HOUR), hours.get(t)
        complete = lambda b: b is not None and b.status == "COMPLETE"  # noqa: E731
        pred = sign(cur.close - prev.close) if complete(prev) and complete(cur) else None
        flags = []
        if boundary:
            flags.append("BOUNDARY_NOT_SCORED")
        if pred is None:
            flags.append("PREDICTION_UNAVAILABLE")
        elif pred == "FLAT":
            flags.append("PREDICTION_FLAT")
        outcome, nxt = None, None
        if not boundary:  # the boundary endpoint H(end) is never looked up
            nxt = hours.get(t + HOUR)
            outcome = sign(nxt.close - cur.close) if complete(cur) and complete(nxt) else None
            if outcome is None:
                flags.append("OUTCOME_UNAVAILABLE")
        paired = (not boundary) and outcome is not None and pred in DIRECTIONAL
        reg.append({"t": t, "prediction": pred, "outcome": outcome, "flags": flags, "paired": paired,
                    "persistence_correct": paired and pred == outcome,
                    "constant_correct": paired and cfg.reference == outcome,
                    "bars": {"prev": prev.status if prev else "ABSENT", "cur": cur.status if cur else "ABSENT",
                             "next": "NOT_READ" if boundary else (nxt.status if nxt else "ABSENT")}})
    return reg


# -- computation ---------------------------------------------------------------------------------------------------

def type7(sorted_x: list[float], p: float) -> float:
    h = (len(sorted_x) - 1) * p
    lo = math.floor(h)
    hi = min(lo + 1, len(sorted_x) - 1)
    return sorted_x[lo] + (h - lo) * (sorted_x[hi] - sorted_x[lo])


def paired_table(reg: list[dict]) -> dict:
    P = [x for x in reg if x["paired"]]
    cells = {"BOTH": sum(1 for x in P if x["persistence_correct"] and x["constant_correct"]),
             "PERSISTENCE_ONLY": sum(1 for x in P if x["persistence_correct"] and not x["constant_correct"]),
             "CONSTANT_ONLY": sum(1 for x in P if x["constant_correct"] and not x["persistence_correct"]),
             "NEITHER": sum(1 for x in P if not x["persistence_correct"] and not x["constant_correct"])}
    n = len(P)
    hp, hc = cells["BOTH"] + cells["PERSISTENCE_ONLY"], cells["BOTH"] + cells["CONSTANT_ONLY"]
    out = {"n": n, "cells": cells, "persistence_hits": hp, "constant_hits": hc,
           "outcome_flat_in_paired": sum(1 for x in P if x["outcome"] == "FLAT")}
    if n:
        d = Fraction(hp - hc, n)
        out.update({"accuracy_persistence": f"{hp}/{n}", "accuracy_constant": f"{hc}/{n}",
                    "accuracy_persistence_decimal": float(Fraction(hp, n)),
                    "accuracy_constant_decimal": float(Fraction(hc, n)),
                    "delta_exact": f"{d.numerator}/{d.denominator}", "delta_decimal": float(d)})
    return out


def bootstrap(reg: list[dict], cfg: StudyConfig) -> dict:
    """The registered draw procedure (delivery/HDP-001-VERIFICATION-REFERENCES.md §2)."""
    N, L, B = len(reg), cfg.block_hours, cfg.resamples
    base = {"block_hours": L, "resamples": B, "seed": cfg.seed, "grid_hours": N, "circular": False,
            "generator": "random.Random(seed); one randrange(N-L+1) per block, resample 0..B-1 then block 0..k-1",
            "percentile_convention": f"Hyndman-Fan type 7, p = {cfg.p_lo} / {cfg.p_hi}",
            "reference": cfg.reference}
    if N < 2 * L:
        return {**base, "status": "INCONCLUSIVE_DURATION", "interval_95": None,
                "note": "fewer than two non-overlapping blocks; blocks are never shortened (protocol §5)"}
    d_pre, e_pre = [0], [0]
    for x in reg:
        d_pre.append(d_pre[-1] + int(x["persistence_correct"]) - int(x["constant_correct"]))
        e_pre.append(e_pre[-1] + int(x["paired"]))
    lengths = block_lengths(N, L)
    rng = random.Random(cfg.seed)
    deltas: list[float] = []
    zero = 0
    for _ in range(B):
        dsum = esum = 0
        for ln in lengths:
            s = rng.randrange(N - L + 1)
            dsum += d_pre[s + ln] - d_pre[s]
            esum += e_pre[s + ln] - e_pre[s]
        if esum == 0:
            zero += 1
            continue
        deltas.append(dsum / esum)
    out = {**base, "blocks_per_resample": len(lengths), "block_lengths": lengths, "start_range": [0, N - L],
           "zero_denominator_resamples": zero,
           "deltas_sha256": hashlib.sha256(json.dumps(deltas).encode()).hexdigest()}
    if zero:
        return {**out, "status": "INCONCLUSIVE_ZERO_DENOMINATOR", "interval_95": None}
    srt = sorted(deltas)
    lo, hi = type7(srt, cfg.p_lo), type7(srt, cfg.p_hi)
    q = statistics.quantiles(deltas, n=40, method="inclusive") if len(deltas) > 1 else [lo, hi]
    return {**out, "status": "COMPUTED", "interval_95": [lo, hi],
            "cross_check_statistics_quantiles_inclusive": {"values": [q[0], q[-1]],
                                                            "max_abs_difference": max(abs(q[0] - lo), abs(q[-1] - hi))}}


def absences(reg: list[dict], hours: dict[datetime, HourBar], cfg: StudyConfig) -> dict:
    """Where the unavailable hours fall (descriptive only; no threshold)."""
    weekly = []
    for b, ln in enumerate(block_lengths(len(reg), cfg.block_hours)):
        part = reg[b * cfg.block_hours: b * cfg.block_hours + ln]
        weekly.append({"block": b, "from": iso(part[0]["t"]), "hours": len(part),
                       "paired": sum(1 for x in part if x["paired"]),
                       **{f.lower(): sum(1 for x in part if f in x["flags"]) for f in FLAGS}})
    runs, cur = [], None
    for x in reg:
        unav = "PREDICTION_UNAVAILABLE" in x["flags"] or "OUTCOME_UNAVAILABLE" in x["flags"]
        if unav and cur is None:
            cur = {"first_cutoff": iso(x["t"]), "last_cutoff": iso(x["t"]), "hours": 1}
        elif unav:
            cur["last_cutoff"], cur["hours"] = iso(x["t"]), cur["hours"] + 1
        elif cur is not None:
            runs.append(cur)
            cur = None
    if cur is not None:
        runs.append(cur)
    incomplete = [{"hour": [iso(h.end - HOUR), iso(h.end)], "valid_minutes": h.valid, "expected": h.expected,
                   "reasons": h.reasons} for h in sorted(hours.values(), key=lambda h: h.end) if h.status != "COMPLETE"]
    return {"per_block": weekly, "unavailable_runs": runs, "incomplete_hourly_bars": incomplete,
            "note": "descriptive; reduced or concentrated coverage limits the conclusion (decision §1); no threshold"}


def section6(interval: list[float] | None) -> str | None:
    if interval is None:
        return None
    lo, hi = interval
    return ("INTERVAL_ENTIRELY_ABOVE_ZERO" if lo > 0 else "INTERVAL_ENTIRELY_BELOW_ZERO" if hi < 0
            else "INTERVAL_INCLUDES_OR_TOUCHES_ZERO")


# -- run -------------------------------------------------------------------------------------------------------------

def source_hashes() -> list[dict]:
    out = [{"path": p, "expected_sha256_lf": h, "sha256_lf": sha_lf(ROOT / p) if (ROOT / p).is_file() else None}
           for p, h in AUTHORITATIVE.items()]
    for d in out:
        d["match"] = d["sha256_lf"] == d["expected_sha256_lf"]
    idx = ROOT / OPERATIONAL_INDEX
    out.append({"path": OPERATIONAL_INDEX, "role": "operational index (not authoritative)",
                "sha256_lf": sha_lf(idx) if idx.is_file() else None})
    return out


def run(paths: list[Path], out: Path, cfg: StudyConfig = FROZEN, mode: str = "SYNTHETIC",
        assignment: str | None = None) -> dict:
    if mode not in ("SYNTHETIC", "VERIFICATION"):
        raise ValueError("mode must be SYNTHETIC or VERIFICATION")
    sources = source_hashes()
    if mode == "VERIFICATION":
        if cfg != FROZEN:
            raise SystemExit("VERIFICATION runs only the frozen HDP-001 configuration")
        if not assignment:
            raise SystemExit("VERIFICATION needs --assignment: the separate executive assignment that authorizes it")
        if not all(s["match"] for s in sources if "expected_sha256_lf" in s):
            raise SystemExit(f"authoritative source changed; refusing to run: {sources}")
    explo = (ROOT / "delivery" / "evidence" / "HDP-001-EXPLORATION").resolve()
    if out.resolve() == explo or explo in out.resolve().parents:
        raise SystemExit("the exploration directory is never written")
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"{out} exists and is not empty; earlier outputs are never overwritten")

    checks = Checks()
    hours, inputs = load_hours([Path(p) for p in paths], cfg, checks)
    doc: dict = {
        "mode": mode,
        "label": ("SYNTHETIC EXECUTION — engineering check of the executor; not the HDP-001 verification, no study "
                  "reading" if mode == "SYNTHETIC" else "HDP-001 VERIFICATION — real input under the assignment below"),
        "assignment": assignment,
        "executor": {"id": EXECUTOR_ID, "script": "scripts/hdp001_verify.py", "script_sha256_lf": sha_lf(Path(__file__)),
                     "code_version": version.code_version(), "python": platform.python_version()},
        "sources": sources, "config": {**cfg.doc(), "sha256": cfg.sha256(), "frozen": cfg == FROZEN},
        "inputs": {"datasets": inputs, "required_trade_1m": [iso(x) for x in required_minutes(cfg)]},
        "reference": {"value": cfg.reference, "source": "frozen by HDP-001-EXPLORATION-CLOSURE; never recomputed"},
        "integrity": {"checks": checks.items, "external_provenance_not_attested": list(EXTERNAL_PROVENANCE)},
    }
    out.mkdir(parents=True, exist_ok=True)
    if hours is None:
        doc.update({"status": "NOT_EVALUABLE", "integrity": {**doc["integrity"], "status": "NOT_ATTESTED"},
                    "reason": "input identity or construction could not be attested; nothing is computed"})
        (out / "results.json").write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        return doc
    doc["integrity"]["status"] = "ATTESTED_INTERNALLY"
    reg = build_register(hours, cfg)
    flag_counts = {f: sum(1 for x in reg if f in x["flags"]) for f in FLAGS}
    usable = [x for x in reg if "BOUNDARY_NOT_SCORED" not in x["flags"] and x["outcome"] is not None]
    pt = paired_table(reg)
    doc["population"] = {
        "planned_cutoffs": len(reg), "with_directional_prediction": sum(1 for x in reg if x["prediction"] in DIRECTIONAL),
        "flags_recorded_separately_even_if_concurrent": flag_counts, "paired": pt["n"],
        "usable_outcomes_descriptive": {s: sum(1 for x in usable if x["outcome"] == s) for s in ("UP", "DOWN", "FLAT")},
        "reconciliation": {"planned = paired + excluded": len(reg) == pt["n"] + sum(1 for x in reg if not x["paired"]),
                           "excluded": sum(1 for x in reg if not x["paired"])}}
    doc["paired"] = pt
    boot = bootstrap(reg, cfg)
    doc["bootstrap"] = boot
    doc["absences"] = absences(reg, hours, cfg)
    status = "INCONCLUSIVE_NO_PAIRED_HOURS" if pt["n"] == 0 else boot["status"]
    doc["status"] = status
    doc["reading"] = (None if mode == "SYNTHETIC" else {
        "section6_interval": section6(boot.get("interval_95")) if status == "COMPUTED" else "INCONCLUSIVE",
        "limits": "coverage and concentration of absences (see absences) limit the conclusion; the reading is the "
                  "Director's (decision §1). No profitability, target or randomness claim (protocol §6)."})
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["cutoff", "prediction", "outcome_scored", "flags", "paired", "persistence_correct", "constant_correct",
                "bar_prev", "bar_cur", "bar_next"])
    for x in reg:
        w.writerow([iso(x["t"]), x["prediction"] or "", x["outcome"] or "", "|".join(x["flags"]), x["paired"],
                    x["persistence_correct"], x["constant_correct"], x["bars"]["prev"], x["bars"]["cur"],
                    x["bars"]["next"]])
    data = buf.getvalue().encode()
    (out / "hours.csv").write_bytes(data)
    doc["outputs"] = {"hours_csv_sha256": hashlib.sha256(data).hexdigest()}
    (out / "results.json").write_text(json.dumps(doc, indent=1, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return doc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="HDP-001 verification executor (offline; frozen configuration only)")
    ap.add_argument("--assignment", required=True, help="reference of the executive assignment authorizing the run")
    ap.add_argument("--out", required=True, type=Path, help="new, empty output directory")
    ap.add_argument("datasets", nargs="+", type=Path, help="verified marketdata.v1 dataset directories")
    a = ap.parse_args(argv)
    doc = run(a.datasets, a.out, FROZEN, mode="VERIFICATION", assignment=a.assignment)
    print(json.dumps({"status": doc["status"], "out": str(a.out)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
