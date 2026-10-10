"""HDP-001 verification executor (scripts/hdp001_verify.py) on SYNTHETIC inputs only (pure, offline; no DB, no network).

Hand-expected sequence (directions d_e = sign(C_e - C_(e-1)) of the hourly closes C ending at e):
  closes C_-1..C_7 = 100, 99, 98, 97, 98, 99, 98, 98, 98  ->  d_0..d_7 = D, D, D, U, U, D, F, F
  cutoff t_i: prediction d_i, outcome d_(i+1) (t_7 is the boundary: outcome never read)
  t0 D/D persistence only | t1 D/D persistence only | t2 D/U constant only | t3 U/U both | t4 U/D neither
  t5 D/F neither (FLAT outcome, paired) | t6 F/F PREDICTION_FLAT, excluded | t7 BOUNDARY_NOT_SCORED + PREDICTION_FLAT
  cells: both 1, persistence only 2, constant only 1, neither 2; n = 6; hits 3 vs 2; Delta = 1/6
  usable outcomes are majority DOWN (UP 2, DOWN 3, FLAT 2) and the reference stays UP (a re-estimated DOWN would give
  constant hits 3 and Delta 0).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import random
import statistics
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from okx_fake import FakeOkx, client

from algotrader.marketdata import dataset as md
from algotrader.marketdata.contracts import Family

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("hdp001_verify", ROOT / "scripts" / "hdp001_verify.py")
hv = importlib.util.module_from_spec(_spec)
sys.modules["hdp001_verify"] = hv  # dataclasses resolve annotations through sys.modules
_spec.loader.exec_module(hv)

H = timedelta(hours=1)
MIN = timedelta(minutes=1)
W = datetime(2026, 8, 3, 2, tzinfo=UTC)  # synthetic window start (Monday); 8 cutoffs W .. W+7h
CFG = hv.StudyConfig(W, W + 8 * H, block_hours=3, resamples=5)
CLOSES = [100, 99, 98, 97, 98, 99, 98, 98, 98]  # C_-1 .. C_7, bar ending at W + (i-1)h
HOUR_CLOSE = {W + (i - 1) * H: Decimal(c) for i, c in enumerate(CLOSES)}


def hours_from(closes: dict[datetime, Decimal], incomplete=()) -> dict:
    return {e: hv.HourBar(e, "INCOMPLETE" if e in incomplete else "COMPLETE", None if e in incomplete else c, e,
                          59 if e in incomplete else 60, 60, {"MISSING": 1} if e in incomplete else {})
            for e, c in closes.items()}


def cells_of(reg):
    out = []
    for x in reg:
        if not x["paired"]:
            out.append(None)
        elif x["persistence_correct"] and x["constant_correct"]:
            out.append("BOTH")
        elif x["persistence_correct"]:
            out.append("P")
        elif x["constant_correct"]:
            out.append("C")
        else:
            out.append("N")
    return out


# -- samples and paired table (pure) ---------------------------------------------------------------------------------

def test_four_cells_flat_cases_boundary_and_fixed_up_reference():
    reg = hv.build_register(hours_from(HOUR_CLOSE), CFG)
    assert [x["t"] for x in reg] == [W + i * H for i in range(8)]
    assert [x["prediction"] for x in reg] == ["DOWN", "DOWN", "DOWN", "UP", "UP", "DOWN", "FLAT", "FLAT"]
    assert [x["outcome"] for x in reg] == ["DOWN", "DOWN", "UP", "UP", "DOWN", "FLAT", "FLAT", None]
    assert cells_of(reg) == ["P", "P", "C", "BOTH", "N", "N", None, None]
    assert reg[6]["flags"] == ["PREDICTION_FLAT"]  # prediction FLAT and outcome FLAT: abstention, not paired
    assert reg[7]["flags"] == ["BOUNDARY_NOT_SCORED", "PREDICTION_FLAT"] and reg[7]["bars"]["next"] == "NOT_READ"
    pt = hv.paired_table(reg)
    assert pt["cells"] == {"BOTH": 1, "PERSISTENCE_ONLY": 2, "CONSTANT_ONLY": 1, "NEITHER": 2}
    assert (pt["n"], pt["persistence_hits"], pt["constant_hits"]) == (6, 3, 2)
    assert (pt["accuracy_persistence"], pt["accuracy_constant"], pt["delta_exact"]) == ("3/6", "2/6", "1/6")
    assert pt["outcome_flat_in_paired"] == 1
    assert CFG.reference == "UP" and sum(1 for x in reg if x["constant_correct"]) == 2  # UP kept despite DOWN majority


def test_boundary_endpoint_is_never_read_and_first_prediction_uses_prior_history():
    poisoned = {**HOUR_CLOSE, CFG.window_end: Decimal(1)}  # H(end) must never matter
    assert hv.build_register(hours_from(poisoned), CFG) == hv.build_register(hours_from(HOUR_CLOSE), CFG)
    no_history = {e: c for e, c in HOUR_CLOSE.items() if e != W - H}
    first = hv.build_register(hours_from(no_history), CFG)[0]
    assert first["prediction"] is None and first["flags"] == ["PREDICTION_UNAVAILABLE"] and first["outcome"] == "DOWN"


def test_incomplete_hour_masks_exactly_its_dependent_cutoffs_and_keeps_the_grid():
    reg = hv.build_register(hours_from(HOUR_CLOSE, incomplete={W + 3 * H}), CFG)  # bar ending at t3
    assert len(reg) == 8
    assert [x["flags"] for x in reg] == [[], [], ["OUTCOME_UNAVAILABLE"], ["PREDICTION_UNAVAILABLE", "OUTCOME_UNAVAILABLE"],
                                         ["PREDICTION_UNAVAILABLE"], [], ["PREDICTION_FLAT"],
                                         ["BOUNDARY_NOT_SCORED", "PREDICTION_FLAT"]]
    assert cells_of(reg) == ["P", "P", None, None, None, "N", None, None]
    pt = hv.paired_table(reg)
    assert (pt["n"], pt["persistence_hits"], pt["constant_hits"], pt["delta_exact"]) == (3, 2, 0, "2/3")


# -- bootstrap (pure; expected values recomputed here independently) -----------------------------------------------

def _expected_deltas(d, e, L, B, seed):
    n = len(d)
    k = -(-n // L)
    lengths = [L] * (k - 1) + [n - L * (k - 1)]
    rng = random.Random(seed)
    out = []
    for _ in range(B):
        num = den = 0
        for ln in lengths:
            s = rng.randrange(n - L + 1)
            num += sum(d[s:s + ln])
            den += sum(e[s:s + ln])
        out.append(num / den)
    return lengths, out


def test_bootstrap_follows_the_registered_draw_procedure_with_masks_kept():
    reg = hv.build_register(hours_from(HOUR_CLOSE), CFG)
    # per hour (persistence - constant) and paired, written by hand from the cells above; t6/t7 masked (0, 0)
    d = [1, 1, -1, 0, 0, 0, 0, 0]
    e = [1, 1, 1, 1, 1, 1, 0, 0]
    lengths, deltas = _expected_deltas(d, e, 3, 5, 0)
    b = hv.bootstrap(reg, CFG)
    assert (b["status"], b["block_lengths"], b["start_range"], b["zero_denominator_resamples"]) == (
        "COMPUTED", [3, 3, 2], [0, 5], 0) and lengths == [3, 3, 2]
    assert b["deltas_sha256"] == hashlib.sha256(json.dumps(deltas).encode()).hexdigest()
    q = statistics.quantiles(deltas, n=40, method="inclusive")
    assert b["interval_95"] == pytest.approx([q[0], q[-1]], abs=1e-15)
    assert hv.bootstrap(reg, CFG) == b  # reproducible


def test_bootstrap_insufficient_duration_and_zero_denominators_stay_inconclusive():
    reg = hv.build_register(hours_from(HOUR_CLOSE), CFG)
    short = hv.bootstrap(reg, hv.StudyConfig(W, W + 8 * H, block_hours=5, resamples=5))  # 8 < 2 x 5
    assert short["status"] == "INCONCLUSIVE_DURATION" and short["interval_95"] is None and "deltas_sha256" not in short
    flat = {e: Decimal(100) for e in HOUR_CLOSE}  # every prediction FLAT: no paired hour anywhere
    z = hv.bootstrap(hv.build_register(hours_from(flat), CFG), CFG)
    assert z["status"] == "INCONCLUSIVE_ZERO_DENOMINATOR" and z["zero_denominator_resamples"] == 5
    assert z["interval_95"] is None and z["block_lengths"] == [3, 3, 2]


def test_frozen_configuration_arithmetic():
    g = hv.grid(hv.FROZEN)
    assert len(g) == 2016 and g[0] == datetime(2026, 11, 2, tzinfo=UTC) and g[-1] == datetime(2027, 1, 24, 23, tzinfo=UTC)
    assert hv.required_minutes(hv.FROZEN) == (datetime(2026, 11, 1, 22, tzinfo=UTC), datetime(2027, 1, 24, 23, tzinfo=UTC))
    assert hv.block_lengths(2016, 168) == [168] * 12
    assert (hv.FROZEN.block_hours, hv.FROZEN.resamples, hv.FROZEN.seed, hv.FROZEN.reference) == (168, 10000, 0, "UP")
    # synthetic hourly closes on the frozen grid (structure only): 2017 bars ending 2026-11-01T23:00 .. 2027-01-24T23:00
    closes = {datetime(2026, 11, 1, 23, tzinfo=UTC) + i * H: Decimal(100 + (i * 7) % 5) for i in range(2017)}
    reg = hv.build_register(hours_from(closes), hv.FROZEN)
    assert len(reg) == 2016 and reg[-1]["flags"][0] == "BOUNDARY_NOT_SCORED" and reg[-1]["bars"]["next"] == "NOT_READ"
    assert reg[-2]["flags"] in ([], ["PREDICTION_FLAT"]) and reg[-2]["outcome"] is not None
    b = hv.bootstrap(reg, hv.FROZEN)
    assert (b["blocks_per_resample"], b["start_range"], b["resamples"]) == (12, [0, 1848], 10000)
    assert hv.bootstrap(reg, hv.FROZEN)["deltas_sha256"] == b["deltas_sha256"]


# -- full offline path through verified marketdata.v1 datasets -------------------------------------------------------

def _fake(lo: datetime, hi: datetime, drop_trade=()) -> FakeOkx:
    fake = FakeOkx()
    trade, mark, index, funding = [], [], [], []
    t = lo
    while t < hi:
        price = HOUR_CLOSE.get(t + MIN, Decimal(100))  # the last minute of each hour carries its close
        ms, p = int(t.timestamp() * 1000), f"{price:.1f}"
        if t not in drop_trade:
            trade.append([str(ms), p, p, p, p, "100", "1", "80000.5", "1"])
        mark.append([str(ms), p, p, p, p, "1"])
        index.append([str(ms), p, p, p, p, "1"])
        if ms % (8 * 3600 * 1000) == 0:
            funding.append({"formulaType": "withRate", "fundingRate": "0.0001", "fundingTime": str(ms),
                            "instId": "BTC-USDT-SWAP", "instType": "SWAP", "method": "current_period",
                            "realizedRate": "0.0001"})
        t += MIN
    fake.rows = {Family.TRADE_CANDLES: trade, Family.MARK_CANDLES: mark, Family.INDEX_CANDLES: index,
                 Family.FUNDING: funding}
    return fake


def _dataset(root: Path, lo: datetime, hi: datetime, **kw) -> Path:
    r = md.acquire(client(_fake(W - 2 * H, W + 7 * H, **kw)), root, lo, hi)
    return md.dataset_path(root, r.manifest.dataset_id)


LO, HI = W - 2 * H, W + 7 * H  # required trade 1m range of CFG


def test_synthetic_run_end_to_end_with_an_internal_minute_missing(tmp_path):
    missing = W + 2 * H + 30 * MIN  # inside [t3 - 1h, t3); the hour's last minute (its close) is present
    ds = _dataset(tmp_path / "data", LO, HI, drop_trade=(missing,))
    out = tmp_path / "out"
    doc = hv.run([ds], out, CFG, mode="SYNTHETIC")
    assert doc["mode"] == "SYNTHETIC" and doc["label"].startswith("SYNTHETIC EXECUTION") and doc["reading"] is None
    assert doc["integrity"]["status"] == "ATTESTED_INTERNALLY" and all(c["passed"] for c in doc["integrity"]["checks"])
    assert doc["status"] == "COMPUTED"
    assert doc["population"]["planned_cutoffs"] == 8
    assert doc["population"]["flags_recorded_separately_even_if_concurrent"] == {
        "BOUNDARY_NOT_SCORED": 1, "PREDICTION_UNAVAILABLE": 2, "PREDICTION_FLAT": 2, "OUTCOME_UNAVAILABLE": 2}
    assert doc["paired"]["cells"] == {"BOTH": 0, "PERSISTENCE_ONLY": 2, "CONSTANT_ONLY": 0, "NEITHER": 1}
    assert doc["paired"]["delta_exact"] == "2/3"
    inc = doc["absences"]["incomplete_hourly_bars"]
    assert len(inc) == 1 and inc[0]["hour"] == [hv.iso(W + 2 * H), hv.iso(W + 3 * H)] and inc[0]["valid_minutes"] == 59
    assert doc["absences"]["unavailable_runs"] == [{"first_cutoff": hv.iso(W + 2 * H), "last_cutoff": hv.iso(W + 4 * H),
                                                    "hours": 3}]
    rows = (out / "hours.csv").read_text(encoding="utf-8").splitlines()
    assert len(rows) == 9 and rows[4].startswith(f"{hv.iso(W + 3 * H)},,,PREDICTION_UNAVAILABLE|OUTCOME_UNAVAILABLE")
    assert doc["outputs"]["hours_csv_sha256"] == hashlib.sha256((out / "hours.csv").read_bytes()).hexdigest()
    ins = doc["inputs"]["datasets"][0]
    assert ins["inst_id"] == "BTC-USDT-SWAP" and ins["feed_content_identity"] and ins["manifest_sha256"]
    assert doc["config"]["frozen"] is False and doc["reference"]["value"] == "UP"
    assert all(s["match"] for s in doc["sources"] if "expected_sha256_lf" in s)
    with pytest.raises(SystemExit):  # earlier outputs are never overwritten
        hv.run([ds], out, CFG, mode="SYNTHETIC")


def test_complete_dataset_reproduces_the_hand_expected_cells(tmp_path):
    doc = hv.run([_dataset(tmp_path / "data", LO, HI)], tmp_path / "out", CFG, mode="SYNTHETIC")
    assert doc["status"] == "COMPUTED" and doc["paired"]["delta_exact"] == "1/6"
    assert doc["paired"]["cells"] == {"BOTH": 1, "PERSISTENCE_ONLY": 2, "CONSTANT_ONLY": 1, "NEITHER": 2}
    assert doc["population"]["usable_outcomes_descriptive"] == {"UP": 2, "DOWN": 3, "FLAT": 2}
    assert doc["absences"]["incomplete_hourly_bars"] == [] and doc["absences"]["unavailable_runs"] == []


def test_two_contiguous_hour_aligned_datasets_equal_one(tmp_path):
    one = hv.run([_dataset(tmp_path / "a", LO, HI)], tmp_path / "o1", CFG, mode="SYNTHETIC")
    two = hv.run([_dataset(tmp_path / "b", W + 3 * H, HI), _dataset(tmp_path / "b", LO, W + 3 * H)], tmp_path / "o2",
                 CFG, mode="SYNTHETIC")  # given out of order on purpose
    assert two["status"] == "COMPUTED" and len(two["inputs"]["datasets"]) == 2
    assert (two["paired"], two["bootstrap"], two["absences"]) == (one["paired"], one["bootstrap"], one["absences"])
    assert two["outputs"]["hours_csv_sha256"] == one["outputs"]["hours_csv_sha256"]


@pytest.mark.parametrize("case", ["tampered", "corrupt", "missing_first_hour", "overlap", "not_hour_aligned"])
def test_inputs_that_cannot_be_attested_are_not_evaluable(tmp_path, case):
    root = tmp_path / "data"
    if case in ("tampered", "corrupt"):  # one byte changed mid-file (hash) / footer destroyed (unreadable Parquet)
        ds = _dataset(root, LO, HI)
        f = ds / "trade_candles_1m.parquet"
        b = bytearray(f.read_bytes())
        b[len(b) // 2 if case == "tampered" else len(b) - 1] ^= 0xFF
        f.write_bytes(bytes(b))
        paths, failing = [ds], "C1_DATASET_VERIFY"
    elif case == "missing_first_hour":
        paths, failing = [_dataset(root, LO + H, HI)], "C3_REQUIRED_RANGE"
    elif case == "overlap":
        paths, failing = [_dataset(root, LO, W + 3 * H), _dataset(root, W + 2 * H, HI)], "C3_CONTIGUOUS"
    else:
        paths, failing = [_dataset(root, LO, W + 30 * MIN), _dataset(root, W + 30 * MIN, HI)], "C3_HOUR_ALIGNED"
    out = tmp_path / "out"
    doc = hv.run(paths, out, CFG, mode="SYNTHETIC")
    assert doc["status"] == "NOT_EVALUABLE" and doc["integrity"]["status"] == "NOT_ATTESTED"
    assert any(c["id"] == failing and not c["passed"] for c in doc["integrity"]["checks"])
    assert "paired" not in doc and not (out / "hours.csv").exists()


def test_verification_mode_guards(tmp_path):
    with pytest.raises(SystemExit):
        hv.run([], tmp_path / "a", CFG, mode="VERIFICATION", assignment="x")  # only the frozen configuration
    with pytest.raises(SystemExit):
        hv.run([], tmp_path / "b", hv.FROZEN, mode="VERIFICATION")  # an assignment reference is required
    with pytest.raises(SystemExit):
        hv.run([], ROOT / "delivery" / "evidence" / "HDP-001-EXPLORATION", CFG)  # never written
