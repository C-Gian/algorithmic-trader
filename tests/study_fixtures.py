"""Synthetic fixtures for the A v0.6 study path (engineering inputs, NOT market data, never the real study window).

A tiny registered *study* window is served through ``ALGOTRADER_STUDY_PRESETS`` next to a fixture presets file whose
logical target and development/protected periods exclude it, so the study exemption (outside the target, not on
calendar months) is exercised exactly as for the real registered window. The tape is the MP-005 v0.6 reachable A LONG
path ``adviser6_fixtures.compatible_then(REF_ONE... )`` style: confirmation published 04:01 on DAY2, reference
prepared 04:02, recovery issued 04:03 (call A LONG RETURN), then a flat tail: the call ends at its hard deadline
(confirmation + 4 h = 08:01), inside the study tail.

Study windows (DAY1 = 2025-08-31, a Sunday; the evaluation crosses the Aug/Sep month boundary):
  initialization [DAY1 00:00, DAY1 22:00)  (explicit; the fixture file's fine warmup is 2 h)
  evaluation     [DAY1 22:00, DAY2 04:30)
  tail           [DAY2 04:30, DAY2 10:35)  (365 min, the registered outcome tail)
"""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

import adviser6_fixtures as fx
from adviser3_fixtures import DAY1, DAY2

MIN = timedelta(minutes=1)
INIT_START = DAY1
EV_START = DAY1 + timedelta(hours=22)
EV_END = DAY2 + timedelta(hours=4, minutes=30)
TAIL_END = EV_END + timedelta(minutes=365)
STUDY_PRESET_ID = "study-fixture-v1"


def iso(t) -> str:
    return t.isoformat().replace("+00:00", "Z")


def study_preset(ev_start=EV_START, ev_end=EV_END, init_start=INIT_START, preset_id=STUDY_PRESET_ID) -> dict:
    return {"preset_id": preset_id, "label": "Study fixture", "default": False,
            "warmup": {"start": iso(init_start), "end": iso(ev_start)},
            "evaluation": {"start": iso(ev_start), "end": iso(ev_end)},
            "tail": {"start": iso(ev_end), "end": iso(ev_end + timedelta(minutes=365))},
            "evidence_class": "REGISTERED_STUDY_WINDOW", "adviser_implemented": False, "automatic_prepare": False,
            "initialization": "REGISTERED_EXPLICIT_INITIALIZATION"}


def base_presets_doc() -> dict:
    """Fixture presets file: target/development/protected all before the study window (so it is outside them)."""
    return {
        "schema_version": "algotrader.corpus-presets.v1", "version": 1, "method": "btc.context-action.v0.2",
        "rules_version": "mp001.rules.v0.2", "source": "okx", "instrument": "BTC-USDT-SWAP",
        "availability": "MODELED_ZERO_EXTRA_DELAY", "fine_warmup_hours": 2, "outcome_tail_minutes": 365,
        "window_convention": "UTC_HALF_OPEN_WHOLE_MINUTES", "acquisition_max_span_days": 31,
        "acquisition_split": "UTC_MONTH_AND_MAX_SPAN",
        "target": {"start": "2025-06-01T00:00:00Z", "end": "2025-08-01T00:00:00Z"},
        "development": {"start": "2025-06-01T00:00:00Z", "end": "2025-07-01T00:00:00Z"},
        "protected_provisional": {"start": "2025-07-01T00:00:00Z", "end": "2025-08-01T00:00:00Z",
                                  "contamination": "UNKNOWN_REQUIRES_DIRECTOR_INVENTORY_BEFORE_ECONOMIC_USE"},
        "capability_profile": {"execution": "HISTORICAL_BASE", "calendar": "NONE_UNKNOWN",
                               "incident_tape": "NOT_COVERED", "dislocation": "ENABLE_WHERE_SUPPORTED",
                               "funding_outcomes": "AUTHORITATIVE_IF_COVERED_ELSE_PRICE_NET_ONLY",
                               "metadata": "PINNED_RETRIEVAL_SNAPSHOT_ASSUMED_FOR_WINDOW"},
        "boundaries": {"warmup": "UNSCORED_FACTUAL_DERIVED_INITIALIZATION",
                       "internal_month": "CONTINUE_NO_FINISH_NO_RESET",
                       "clock_end": "FULL_COVERAGE_END_PLUS_DECLARED_CLOSURE_ALLOWANCE"},
        "presets": [{"preset_id": "dev-fixture-v1", "label": "Development fixture", "default": True,
                     "warmup": {"start": "2025-06-10T00:00:00Z", "end": "2025-06-10T02:00:00Z"},
                     "evaluation": {"start": "2025-06-10T02:00:00Z", "end": "2025-06-10T04:00:00Z"},
                     "tail": {"start": "2025-06-10T04:00:00Z", "end": "2025-06-10T10:05:00Z"},
                     "evidence_class": "DEVELOPMENT", "adviser_implemented": False, "automatic_prepare": False}],
        "fixture": True,
    }


def study_doc(preset: dict | None = None, method: str = "v0.6") -> dict:
    return {"schema_version": "algotrader.study-presets.v1", "version": 1, "fixture": True,
            "studies": [{"study_id": "STUDY-FIXTURE", "label": "Study fixture",
                         "sources": [{"path": "tests/study_fixtures.py", "sha256_lf": "fixture"}],
                         "run_type": "adviser_evaluation", "method": method, "preset": preset or study_preset()}]}


def write_files(tmp_path: Path, monkeypatch, preset: dict | None = None) -> None:
    b, s = tmp_path / "presets.json", tmp_path / "study_presets.json"
    b.write_text(json.dumps(base_presets_doc()), encoding="utf-8")
    s.write_text(json.dumps(study_doc(preset)), encoding="utf-8")
    monkeypatch.setenv("ALGOTRADER_CORPUS_PRESETS", str(b))
    monkeypatch.setenv("ALGOTRADER_STUDY_PRESETS", str(s))


def tape(n_minutes: int | None = None) -> list:
    """The v0.6 A LONG call path, padded flat so the data cover the study tail end."""
    ms = fx.a3([fx.REF_ONE, fx.ONE_EDGE], tail_price=100000)
    need = n_minutes or int((TAIL_END - DAY1) / MIN)
    return (ms + fx.flat(max(0, need - len(ms)), ms[-1].c))[:need]
