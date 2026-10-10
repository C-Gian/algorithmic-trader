"""A v0.6 operational evaluation — moving-block bootstrap of the observed balance (offline study tool).

Not product code: it reads one ledger produced by ``scripts/a_v06_study_ledger.py`` (v2) and never recomputes a
decision, outcome or cost. It runs only when the ledger is attested and its balance is COMPLETE (every included PRIMARY
path determinable); otherwise it writes the refusal and its reason and computes nothing.

Frozen procedure (design §6, as stated in the assignment of 10 October 2026):
  grid       the complete UTC hourly grid of the evaluation window, in time order, never compressed to hours with calls;
             each hour holds the ledger's attested value (0 only for an attested null economic contribution)
  blocks     moving blocks of L = 168 hours; k = ceil(N / L); lengths L for blocks 0..k-2, N - L(k-1) for block k-1
             (truncated last block); no circular wrap
  draws      one random.Random(0); one randrange(N - L + 1) per block, in the order resample b = 0..B-1, then block
             j = 0..k-1; block j covers the grid hours s .. s + length_j - 1
  statistic  the sum of the resampled hourly values (exact Decimal), B = 10,000 resamples
  interval   95% percentile interval, Hyndman-Fan type 7 on the sorted statistics, p = 0.025 / 0.975, h = (B - 1) p
The interval is reported separately from the observed balance. No verdict of effectiveness or promotion is produced.

Usage (only under the separate executive assignment; the study is INACTIVE):
  uv run python scripts/a_v06_study_bootstrap.py --ledger <ledger dir> --out <new dir> --assignment "<ref>"
Synthetic executions run only through tests or with explicit synthetic configurations and are labelled as such.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, localcontext
from pathlib import Path

BOOTSTRAP_ID = "a-v06.study-bootstrap.v1"
REQUIRED_LEDGER = "a-v06.study-ledger.v2"
STUDY_WINDOW = ("2027-01-25T00:00:00Z", "2027-07-26T00:00:00Z")
HOUR = timedelta(hours=1)
VALUED = ("NO_CALL_ZERO", "DETERMINED")


@dataclass(frozen=True)
class Config:
    block_hours: int = 168
    resamples: int = 10000
    seed: int = 0
    p_lo: str = "0.025"
    p_hi: str = "0.975"


FROZEN = Config()
PROCEDURE = ("one random.Random(seed); for resample b = 0..B-1, for block j = 0..k-1: s = randrange(N - L + 1); block "
             "j covers grid hours s .. s + length_j - 1; lengths L except the last, truncated to N - L(k-1); no wrap; "
             "statistic = exact sum of the resampled hourly values")
PERCENTILES = "Hyndman-Fan type 7 (linear between order statistics, h = (B - 1) p), p = 0.025 / 0.975"


def _dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(UTC)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def block_lengths(n: int, L: int) -> list[int]:
    k = math.ceil(n / L)
    return [L] * (k - 1) + [n - L * (k - 1)]


def type7(sorted_x: list[Decimal], p: Decimal) -> Decimal:
    h = (len(sorted_x) - 1) * p
    lo = int(h)  # floor for h >= 0
    hi = min(lo + 1, len(sorted_x) - 1)
    return sorted_x[lo] + (h - lo) * (sorted_x[hi] - sorted_x[lo])


def resample_sums(values: list[Decimal], cfg: Config) -> tuple[list[Decimal], list[int]]:
    n, L = len(values), cfg.block_hours
    if n < L:
        raise ValueError(f"the grid has {n} hours, fewer than one block of {L}")
    pre = [Decimal(0)]
    with localcontext() as ctx:
        ctx.prec = 400
        for v in values:
            pre.append(pre[-1] + v)
        lengths = block_lengths(n, L)
        rng = random.Random(cfg.seed)
        out = []
        for _ in range(cfg.resamples):
            total = Decimal(0)
            for ln in lengths:
                s = rng.randrange(n - L + 1)
                total += pre[s + ln] - pre[s]
            out.append(+total)
    return out, lengths


def _refuse(doc: dict, out: Path, status: str, reason: str) -> dict:
    doc.update({"status": status, "reason": reason, "interval_95": None})
    (out / "bootstrap.json").write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return doc


def run(ledger_dir: Path, out: Path, cfg: Config = FROZEN, mode: str = "SYNTHETIC",
        assignment: str | None = None) -> dict:
    if mode not in ("SYNTHETIC", "STUDY"):
        raise ValueError("mode must be SYNTHETIC or STUDY")
    if mode == "STUDY" and (cfg != FROZEN or not assignment):
        raise SystemExit("a STUDY bootstrap runs only the frozen configuration and needs --assignment")
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"{out} exists and is not empty; earlier outputs are never overwritten")
    raw = (ledger_dir / "ledger.json").read_bytes()
    led = json.loads(raw)
    out.mkdir(parents=True, exist_ok=True)
    doc = {
        "tool": BOOTSTRAP_ID, "tool_sha256_lf": _sha(Path(__file__).read_bytes().replace(b"\r\n", b"\n")),
        "mode": mode, "assignment": assignment,
        "label": ("SYNTHETIC EXECUTION — engineering check of the study bootstrap; not the A v0.6 evaluation"
                  if mode == "SYNTHETIC" else "A v0.6 OPERATIONAL EVALUATION — bootstrap of the ledger below"),
        "config": {**asdict(cfg), "frozen": cfg == FROZEN, "sha256": _sha(json.dumps(asdict(cfg), sort_keys=True)
                                                                         .encode())},
        "procedure": PROCEDURE, "percentile_convention": PERCENTILES,
        "input": {"ledger_json_sha256": _sha(raw),
                  "hours_csv_sha256": _sha((ledger_dir / "hours.csv").read_bytes())
                  if (ledger_dir / "hours.csv").is_file() else None,
                  "ledger_tool": led.get("ledger_tool"), "ledger_script_sha256_lf": led.get("ledger_script_sha256_lf"),
                  "ledger_mode": led.get("mode"), "evaluation_id": led.get("evaluation_id"),
                  "replay_id": led.get("replay_id"), "build": led.get("build"),
                  "identity_sha256": led.get("identity_sha256"), "window": (led.get("windows") or {}).get("evaluation")},
        "reading": "no automatic verdict of effectiveness or promotion (design §7)",
    }
    if led.get("ledger_tool") != REQUIRED_LEDGER:
        return _refuse(doc, out, "REFUSED_LEDGER_VERSION", f"needs {REQUIRED_LEDGER}, got {led.get('ledger_tool')}")
    if mode == "STUDY" and (led.get("mode") != "STUDY" or tuple(doc["input"]["window"] or ()) != STUDY_WINDOW):
        return _refuse(doc, out, "REFUSED_NOT_THE_STUDY_LEDGER", "a STUDY bootstrap needs the STUDY ledger of the "
                       "registered window [2027-01-25T00:00Z, 2027-07-26T00:00Z)")
    att, bal = led.get("attestation") or {}, led.get("balance") or {}
    if not att.get("attested") or bal.get("status") == "NOT_ATTESTED_IDENTITY_OR_COMPLETENESS":
        return _refuse(doc, out, "NOT_COMPUTED_NOT_ATTESTED", "identity or completeness not attested by the ledger")
    if bal.get("status") != "COMPLETE":
        return _refuse(doc, out, "NOT_COMPUTED_UNDETERMINED_PATHS",
                       "at least one included PRIMARY path has no determinable result: no complete balance, no "
                       "primary bootstrap (a partial subtotal, if any, stays in the ledger as PARTIAL)")
    hours = led["hours"]
    es, ee = (_dt(x) for x in led["windows"]["evaluation"])
    grid, t = [], es  # every UTC hour starting inside the window, as the ledger builds it
    while t < ee:
        grid.append(t)
        t += HOUR
    if [_dt(h["hour"]) for h in hours] != grid:
        return _refuse(doc, out, "REFUSED_GRID", "the hourly series is not the complete UTC grid of the window")
    if any(h["status"] not in VALUED or h["value"] is None for h in hours):
        return _refuse(doc, out, "REFUSED_UNVALUED_HOUR", "an hour has no attested value")
    values = [Decimal(h["value"]) for h in hours]
    with localcontext() as ctx:
        ctx.prec = 400
        observed = +sum(values, Decimal(0))
    if observed != Decimal(bal["observed_balance"]):
        return _refuse(doc, out, "REFUSED_INCONSISTENT_LEDGER", "the hourly values do not sum to the observed balance")
    try:
        stats, lengths = resample_sums(values, cfg)
    except ValueError as exc:
        return _refuse(doc, out, "REFUSED_GRID_SHORTER_THAN_A_BLOCK", str(exc))
    srt = sorted(stats)
    with localcontext() as ctx:
        ctx.prec = 400
        lo, hi = type7(srt, Decimal(cfg.p_lo)), type7(srt, Decimal(cfg.p_hi))
    vec = json.dumps([str(x) for x in stats]).encode()
    doc.update({
        "status": "COMPUTED", "grid_hours": len(values), "zero_hours": sum(1 for v in values if v == 0),
        "blocks_per_resample": len(lengths), "block_lengths": lengths, "start_range": [0, len(values) - cfg.block_hours],
        "observed_balance": str(observed), "interval_95": [str(lo), str(hi)],
        "resampled_statistics_sha256": _sha(vec), "resampled_statistics_count": len(stats),
        "note": "the interval represents uncertainty conditional on the observed history; it is reported separately "
                "from the observed balance and is not a verdict (design §6-§7)"})
    (out / "resampled_statistics.json").write_bytes(vec)  # exactly the hashed bytes
    (out / "bootstrap.json").write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return doc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="A v0.6 study bootstrap (offline; frozen configuration only)")
    ap.add_argument("--ledger", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--assignment", required=True)
    a = ap.parse_args(argv)
    doc = run(a.ledger, a.out, FROZEN, mode="STUDY", assignment=a.assignment)
    print(json.dumps({"status": doc["status"], "out": str(a.out)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
