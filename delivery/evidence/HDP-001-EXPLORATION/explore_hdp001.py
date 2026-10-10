"""HDP-001 exploration (protocol delivery/HDP-001-HOURLY-DIRECTIONAL-PERSISTENCE.md; decision HDP-001-DIRECTOR-CLOSURE.md).

Not product code. Offline only. Input: exclusively
delivery/evidence/MARKETVIEW-PERSISTENCE-TABULATION/samples.csv (2928 hourly samples, run eval-20261009T155751-be8b2b).

Field mapping (fixed before computing):
  prediction(t) = s_persistence  = sign(C_t - C_(t-1)), last complete contiguous 1h closes known at the cutoff t
  outcome(t)    = s_outcome_1h   = sign(close of the 1m bar ending exactly at t+1h - anchor(t)); missing -> unavailable
  No MarketView field is read. Every hourly cutoff of the phase is a unit.

Phase [2025-09-01T00:00Z, 2026-01-01T00:00Z): an outcome is usable only if its endpoint t+1h < end; the cutoff whose
endpoint equals the end is BOUNDARY_NOT_SCORED and its stored outcome is never read for scoring or for the reference.

Constant reference (§4): UP/DOWN outcome counts over all usable hours, not conditioned on the prediction; more UP -> UP,
more DOWN -> DOWN, tie -> UP; no directional outcome -> insufficient exploration, stop.

Paired comparison (§5): hours with prediction UP/DOWN and outcome available (FLAT outcomes included and wrong for both).

Bootstrap (§5 + decision), fixed here before any result was computed:
  - grid = all 2928 phase cutoffs in time order (unavailability/boundary masks kept; evaluable hours not compressed);
  - moving blocks of L = 168 consecutive grid hours, start s uniform on {0, ..., N-L} (entirely inside the phase, no
    circular wrap); k = ceil(N/L) blocks concatenated, the last one truncated so that the resample has exactly N hours;
  - B = 10000 resamples; generator: Python stdlib random.Random(0) (Mersenne Twister MT19937), starts drawn with
    randrange(N-L+1) in order resample 0..B-1, block 0..k-1; the reference stays fixed;
  - statistic per resample: Delta* = (persistence hits - constant hits) / paired count over the resampled hours; a zero
    paired count makes the result inconclusive (counted, never skipped);
  - 95% percentile interval: Hyndman-Fan type 7 (linear interpolation between order statistics, h = (B-1)p), p = 0.025
    and 0.975, on the B values of Delta*; cross-checked against statistics.quantiles(n=40, method="inclusive").

Usage: uv run python explore_hdp001.py <samples.csv> <out_dir>
Writes <out_dir>/results.json and <out_dir>/hours.csv. The protocol's §6 reading categories apply to the verification
only (Director decision); none is assigned here.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import random
import statistics
import sys
from datetime import datetime, timedelta, timezone
from fractions import Fraction
from pathlib import Path

PHASE_START = datetime(2025, 9, 1, tzinfo=timezone.utc)
PHASE_END = datetime(2026, 1, 1, tzinfo=timezone.utc)
L, B, SEED, P_LO, P_HI = 168, 10000, 0, 0.025, 0.975
DIRECTIONAL = ("UP", "DOWN")


def dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def type7(sorted_x: list[float], p: float) -> float:
    h = (len(sorted_x) - 1) * p
    lo = math.floor(h)
    hi = min(lo + 1, len(sorted_x) - 1)
    return sorted_x[lo] + (h - lo) * (sorted_x[hi] - sorted_x[lo])


def main(src: Path, out: Path) -> None:
    raw = src.read_bytes()
    lf = raw.replace(b"\r\n", b"\n")
    rows = list(csv.DictReader(lf.decode("utf-8").splitlines()))

    # -- grid and integrity --------------------------------------------------------------------------------------------
    grid = []
    t = PHASE_START
    while t < PHASE_END:
        grid.append(t)
        t += timedelta(hours=1)
    by_time = {dt(r["s_sample_time"]): r for r in rows}
    integrity = {
        "rows": len(rows), "expected_cutoffs": len(grid), "unique_times": len(by_time) == len(rows),
        "times_equal_phase_grid": sorted(by_time) == grid,
    }
    if not (integrity["unique_times"] and integrity["times_equal_phase_grid"]):
        raise SystemExit(f"integrity failure: {integrity}")
    # stored-value identity: outcome(t) equals the next cutoff's prediction (both sign(C_(t+1) - C_t))
    same = diff = 0
    for i in range(len(grid) - 1):
        o, p_next = by_time[grid[i]]["s_outcome_1h"], by_time[grid[i + 1]]["s_persistence"]
        if o and p_next:
            same, diff = same + (o == p_next), diff + (o != p_next)
    integrity["outcome_t_equals_prediction_t_plus_1h"] = {"equal": same, "different": diff}

    # -- per-hour register ---------------------------------------------------------------------------------------------
    reg = []
    for t in grid:
        r = by_time[t]
        pred = r["s_persistence"] or None
        boundary = not (t + timedelta(hours=1) < PHASE_END)
        out_raw = None if boundary else (r["s_outcome_1h"] or None)  # boundary outcome is never read
        flags = []
        if boundary:
            flags.append("BOUNDARY_NOT_SCORED")
        if pred is None:
            flags.append("PREDICTION_UNAVAILABLE")
        elif pred == "FLAT":
            flags.append("PREDICTION_FLAT")
        if not boundary and out_raw is None:
            flags.append("OUTCOME_UNAVAILABLE")
        reg.append({"t": t, "prediction": pred, "outcome": out_raw, "flags": flags,
                    "usable_outcome": (not boundary) and out_raw is not None,
                    "paired": (not boundary) and out_raw is not None and pred in DIRECTIONAL})

    # -- constant reference (§4) -------------------------------------------------------------------------------------
    up = sum(1 for x in reg if x["usable_outcome"] and x["outcome"] == "UP")
    down = sum(1 for x in reg if x["usable_outcome"] and x["outcome"] == "DOWN")
    flat_out = sum(1 for x in reg if x["usable_outcome"] and x["outcome"] == "FLAT")
    if up + down == 0:
        raise SystemExit("insufficient exploration: no directional outcome (protocol §4) - stop")
    ref = "UP" if up >= down else "DOWN"
    ref_rule = "more UP" if up > down else "more DOWN" if down > up else "tie -> UP (administrative convention)"

    # -- paired comparison (§5) --------------------------------------------------------------------------------------
    for x in reg:
        x["persistence_correct"] = x["paired"] and x["prediction"] == x["outcome"]
        x["constant_correct"] = x["paired"] and ref == x["outcome"]
    P = [x for x in reg if x["paired"]]
    n = len(P)
    cells = {"BOTH": sum(1 for x in P if x["persistence_correct"] and x["constant_correct"]),
             "PERSISTENCE_ONLY": sum(1 for x in P if x["persistence_correct"] and not x["constant_correct"]),
             "CONSTANT_ONLY": sum(1 for x in P if x["constant_correct"] and not x["persistence_correct"]),
             "NEITHER": sum(1 for x in P if not x["persistence_correct"] and not x["constant_correct"])}
    hp, hc = cells["BOTH"] + cells["PERSISTENCE_ONLY"], cells["BOTH"] + cells["CONSTANT_ONLY"]
    delta = Fraction(hp - hc, n)

    flag_counts = {}
    for f in ("BOUNDARY_NOT_SCORED", "PREDICTION_UNAVAILABLE", "PREDICTION_FLAT", "OUTCOME_UNAVAILABLE"):
        flag_counts[f] = sum(1 for x in reg if f in x["flags"])
    population = {
        "planned_cutoffs": len(reg),
        "with_directional_prediction": sum(1 for x in reg if x["prediction"] in DIRECTIONAL),
        "prediction_flat": flag_counts["PREDICTION_FLAT"], "prediction_unavailable": flag_counts["PREDICTION_UNAVAILABLE"],
        "boundary_not_scored": flag_counts["BOUNDARY_NOT_SCORED"], "outcome_unavailable": flag_counts["OUTCOME_UNAVAILABLE"],
        "usable_outcomes": up + down + flat_out, "paired": n,
        "paired_outcome_flat": sum(1 for x in P if x["outcome"] == "FLAT"),
        "flags_recorded_separately_even_if_concurrent": flag_counts,
        "reconciliation": {
            "planned = paired + hours excluded (any flag)":
                len(reg) == n + sum(1 for x in reg if not x["paired"]),
            "hours excluded": sum(1 for x in reg if not x["paired"]),
            "excluded hours with exactly one flag": sum(1 for x in reg if not x["paired"] and len(x["flags"]) == 1),
        },
    }

    # -- moving-block bootstrap (§5) ---------------------------------------------------------------------------------
    N = len(reg)
    if N < 2 * L:
        raise SystemExit("inconclusive: fewer than two non-overlapping weekly blocks (protocol §5)")
    d_pre, e_pre = [0], [0]
    for x in reg:
        d_pre.append(d_pre[-1] + (int(x["persistence_correct"]) - int(x["constant_correct"])))
        e_pre.append(e_pre[-1] + int(x["paired"]))
    k = math.ceil(N / L)
    lengths = [L] * (k - 1) + [N - L * (k - 1)]
    rng = random.Random(SEED)
    deltas, zero_den = [], 0
    for _ in range(B):
        dsum = esum = 0
        for ln in lengths:
            s = rng.randrange(N - L + 1)
            dsum += d_pre[s + ln] - d_pre[s]
            esum += e_pre[s + ln] - e_pre[s]
        if esum == 0:
            zero_den += 1
            continue
        deltas.append(dsum / esum)
    srt = sorted(deltas)
    lo, hi = type7(srt, P_LO), type7(srt, P_HI)
    q = statistics.quantiles(deltas, n=40, method="inclusive") if deltas else []
    boot = {
        "block_hours": L, "resamples": B, "seed": SEED, "blocks_per_resample": k, "block_lengths": lengths,
        "start_range": [0, N - L], "circular": False, "zero_denominator_resamples": zero_den,
        "generator": "Python stdlib random.Random(seed) - Mersenne Twister MT19937; randrange(N-L+1) per block",
        "percentile_convention": "Hyndman-Fan type 7 (linear), p = 0.025 / 0.975",
        "interval_95": [lo, hi] if zero_den == 0 else None,
        "cross_check_statistics_quantiles_inclusive": {"values": [q[0], q[-1]],
                                                        "max_abs_difference": max(abs(q[0] - lo), abs(q[-1] - hi))}
        if q else None,
        "deltas_sha256": hashlib.sha256(json.dumps(deltas).encode()).hexdigest(),
        "status": "COMPUTED" if zero_den == 0 else "INCONCLUSIVE_ZERO_DENOMINATOR",
    }

    doc = {
        "protocol": "HDP-001 (delivery/HDP-001-HOURLY-DIRECTIONAL-PERSISTENCE.md), exploration phase only",
        "phase": ["2025-09-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        "input": {"path": "delivery/evidence/MARKETVIEW-PERSISTENCE-TABULATION/samples.csv",
                  "sha256_raw": hashlib.sha256(raw).hexdigest(), "sha256_lf_normalized": hashlib.sha256(lf).hexdigest(),
                  "fields_read": ["s_sample_time", "s_persistence", "s_outcome_1h"]},
        "environment": {"python": platform.python_version(), "implementation": platform.python_implementation(),
                        "libraries": "standard library only (csv, random, statistics, fractions, hashlib, json)"},
        "integrity": integrity, "population": population,
        "constant_reference": {"usable_outcomes_up": up, "usable_outcomes_down": down, "usable_outcomes_flat": flat_out,
                               "reference": ref, "rule_applied": ref_rule,
                               "note": "exploratory performance of the reference is measured on the sample used to choose it"},
        "paired": {"n": n, "cells": cells, "persistence_hits": hp, "constant_hits": hc,
                   "accuracy_persistence": f"{hp}/{n}", "accuracy_constant": f"{hc}/{n}",
                   "accuracy_persistence_decimal": float(Fraction(hp, n)), "accuracy_constant_decimal": float(Fraction(hc, n)),
                   "delta_exact": f"{delta.numerator}/{delta.denominator}", "delta_decimal": float(delta)},
        "bootstrap": boot,
        "reading": ("exploration on already exposed development data; the protocol's §6 categories apply to the "
                    "verification only and none is assigned; no signal promotion, profitability or target conclusion"),
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    with open(out / "hours.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["cutoff", "prediction", "outcome_scored", "flags", "paired", "persistence_correct", "constant_correct"])
        for x in reg:
            w.writerow([x["t"].strftime("%Y-%m-%dT%H:%M:%SZ"), x["prediction"] or "", x["outcome"] or "",
                        "|".join(x["flags"]), x["paired"], x["persistence_correct"], x["constant_correct"]])


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
