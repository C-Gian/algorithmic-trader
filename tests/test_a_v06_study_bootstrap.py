"""A v0.6 study bootstrap (scripts/a_v06_study_bootstrap.py) on SYNTHETIC ledgers only (pure, no DB).

Expected statistics are recomputed here independently: plain slicing of the hourly list (no prefix sums), the test's
own random.Random(0), and exact Fraction arithmetic for the type-7 percentiles. Synthetic engineering inputs only."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import random
import sys
from datetime import UTC, datetime, timedelta
from fractions import Fraction
from pathlib import Path

import pytest
import study_fixtures as sf
import test_a_v06_study as tl  # reuses the ledger helpers (pure folds of the study tape)

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("a_v06_study_bootstrap", ROOT / "scripts" / "a_v06_study_bootstrap.py")
bs = importlib.util.module_from_spec(_spec)
sys.modules["a_v06_study_bootstrap"] = bs
_spec.loader.exec_module(bs)

W = datetime(2026, 8, 3, tzinfo=UTC)
H = timedelta(hours=1)
SERIES = [1, 0, -2, 3, 0, 0, 5]  # hourly values, zeros in place (hours without an A call)
SMALL = bs.Config(block_hours=3, resamples=6)


def iso(t):
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def ledger_dir(tmp_path: Path, values, status="COMPLETE", attested=True, mode="SYNTHETIC", start=W, name="led") -> Path:
    hours = [{"hour": iso(start + i * H), "value": str(v) if v is not None else None,
              "status": "DETERMINED" if v else "NO_CALL_ZERO"} for i, v in enumerate(values)]
    total = str(sum(v for v in values if v is not None))
    doc = {"ledger_tool": "a-v06.study-ledger.v2", "mode": mode, "evaluation_id": "eval-s", "replay_id": "obs-s",
           "build": "synthetic", "identity_sha256": "synthetic",
           "windows": {"evaluation": [iso(start), iso(start + len(values) * H)]},
           "attestation": {"attested": attested},
           "balance": {"status": status, "observed_balance": total if status == "COMPLETE" else None},
           "hours": hours}
    d = tmp_path / name
    d.mkdir()
    (d / "ledger.json").write_text(json.dumps(doc), encoding="utf-8")
    return d


def expected(values, L, B, seed=0, order="resample_then_block"):
    """Independent recomputation: explicit slices, own generator."""
    n = len(values)
    k = -(-n // L)
    lengths = [L] * (k - 1) + [n - L * (k - 1)]
    rng = random.Random(seed)
    if order == "resample_then_block":
        starts = [[rng.randrange(n - L + 1) for _ in lengths] for _ in range(B)]
    else:  # the other order, used only to show the tool's order is discriminated
        cols = [[rng.randrange(n - L + 1) for _ in range(B)] for _ in lengths]
        starts = [[cols[j][b] for j in range(len(lengths))] for b in range(B)]
    return lengths, [sum(sum(values[s:s + ln]) for s, ln in zip(row, lengths)) for row in starts]


def frac_type7(xs, p: Fraction) -> Fraction:
    xs = sorted(Fraction(x) for x in xs)
    h = (len(xs) - 1) * p
    lo = int(h)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (h - lo) * (xs[hi] - xs[lo])


def stats_of(out: Path) -> list[int]:
    return [int(x) for x in json.loads((out / "resampled_statistics.json").read_bytes())]


def test_resampled_sums_order_truncation_zeros_and_percentiles(tmp_path):
    doc = bs.run(ledger_dir(tmp_path, SERIES), tmp_path / "out", SMALL)
    lengths, want = expected(SERIES, 3, 6)
    assert doc["status"] == "COMPUTED" and doc["block_lengths"] == lengths == [3, 3, 1]  # truncated last block
    assert doc["start_range"] == [0, 4] and doc["grid_hours"] == 7 and doc["zero_hours"] == 3
    got = stats_of(tmp_path / "out")
    assert got == want
    _, other_order = expected(SERIES, 3, 6, order="block_then_resample")
    assert got != other_order  # resample -> block order, not the transposed one
    nonzero = [v for v in SERIES if v != 0]  # a grid compressed to hours with a value would differ
    assert got != expected(nonzero, 3, 6)[1]
    lo, hi = frac_type7(want, Fraction(25, 1000)), frac_type7(want, Fraction(975, 1000))
    assert [Fraction(x) for x in doc["interval_95"]] == [lo, hi]
    assert doc["observed_balance"] == "7" and doc["label"].startswith("SYNTHETIC EXECUTION")
    assert doc["resampled_statistics_sha256"] == hashlib.sha256((tmp_path / "out" / "resampled_statistics.json")
                                                                .read_bytes()).hexdigest()
    again = bs.run(ledger_dir(tmp_path, SERIES, name="led2"), tmp_path / "out2", SMALL)
    assert again["resampled_statistics_sha256"] == doc["resampled_statistics_sha256"]  # reproducible
    with pytest.raises(SystemExit):
        bs.run(ledger_dir(tmp_path, SERIES, name="led3"), tmp_path / "out", SMALL)  # never overwritten


@pytest.mark.parametrize("case,status", [("undetermined", "NOT_COMPUTED_UNDETERMINED_PATHS"),
                                         ("not_attested", "NOT_COMPUTED_NOT_ATTESTED")])
def test_no_primary_bootstrap_without_a_complete_attested_balance(tmp_path, case, status):
    d = (ledger_dir(tmp_path, [1, None, 2, 0], status="INCOMPLETE_UNDETERMINED_PATHS") if case == "undetermined"
         else ledger_dir(tmp_path, SERIES, status="NOT_ATTESTED_IDENTITY_OR_COMPLETENESS", attested=False))
    doc = bs.run(d, tmp_path / "out", SMALL)
    assert doc["status"] == status and doc["interval_95"] is None and "observed_balance" not in doc
    assert not (tmp_path / "out" / "resampled_statistics.json").exists()


def test_frozen_configuration_on_a_full_synthetic_window(tmp_path):
    assert (bs.FROZEN.block_hours, bs.FROZEN.resamples, bs.FROZEN.seed, bs.FROZEN.p_lo, bs.FROZEN.p_hi) == (
        168, 10000, 0, "0.025", "0.975")
    start = datetime(2027, 1, 25, tzinfo=UTC)
    n = int((datetime(2027, 7, 26, tzinfo=UTC) - start) / H)
    values = [(i * 37) % 11 - 5 if i % 9 == 0 else 0 for i in range(n)]  # sparse calls, zeros elsewhere
    doc = bs.run(ledger_dir(tmp_path, values, start=start), tmp_path / "out", bs.FROZEN)  # SYNTHETIC mode
    assert doc["status"] == "COMPUTED" and doc["config"]["frozen"] and n == doc["grid_hours"] == 4368
    assert doc["blocks_per_resample"] == 26 and doc["block_lengths"] == [168] * 26 and doc["start_range"] == [0, 4200]
    assert stats_of(tmp_path / "out") == expected(values, 168, 10000)[1]  # independent recomputation
    with pytest.raises(SystemExit):
        bs.run(ledger_dir(tmp_path, values, start=start, name="b"), tmp_path / "o2", SMALL, mode="STUDY",
               assignment="x")  # STUDY runs only the frozen configuration
    with pytest.raises(SystemExit):
        bs.run(ledger_dir(tmp_path, values, start=start, name="c"), tmp_path / "o3", bs.FROZEN, mode="STUDY")
    refused = bs.run(ledger_dir(tmp_path, values, start=start, name="d"), tmp_path / "o4", bs.FROZEN, mode="STUDY",
                     assignment="x")
    assert refused["status"] == "REFUSED_NOT_THE_STUDY_LEDGER"  # a synthetic ledger is never the study ledger


def test_pure_fold_ledger_through_the_bootstrap(tmp_path, monkeypatch):
    led = tl._ledger_of(monkeypatch, sf.EV_START, sf.EV_END)
    d = tmp_path / "led"
    d.mkdir()
    (d / "ledger.json").write_text(json.dumps({**led, "ledger_tool": "a-v06.study-ledger.v2"}), encoding="utf-8")
    doc = bs.run(d, tmp_path / "out", SMALL)
    assert doc["status"] == "COMPUTED" and doc["observed_balance"] == "-0.0014" and doc["grid_hours"] == 7
