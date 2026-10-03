"""Tiny deterministic evaluation-pack fixtures (offline): a fixture presets file, one shared synthetic OKX fake whose
values depend only on the market timestamp (so overlapping acquisitions agree), workers and helpers."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg
import psycopg.rows
from okx_fake import client
from okx_synth import synthetic_fake

from algotrader.corpus.job import CorpusWorker
from algotrader.marketdata import dataset as md

MIN = timedelta(minutes=1)
# fixture windows: 2 h warmup, 6 h evaluation (crossing a UTC month boundary), 30 min tail
EV_START = datetime(2026, 8, 31, 21, 0, tzinfo=UTC)
EV_END = datetime(2026, 9, 1, 3, 0, tzinfo=UTC)
WARMUP_H, TAIL_M = 2, 30
REQ_START, REQ_END = EV_START - timedelta(hours=WARMUP_H), EV_END + timedelta(minutes=TAIL_M)
FAKE_START, FAKE_END = REQ_START - timedelta(hours=2), REQ_END + timedelta(hours=2)


def presets_doc(ev_start: datetime = EV_START, ev_end: datetime = EV_END, extra: list | None = None) -> dict:
    iso = lambda t: t.isoformat().replace("+00:00", "Z")  # noqa: E731
    w = ev_start - timedelta(hours=WARMUP_H)
    t = ev_end + timedelta(minutes=TAIL_M)
    return {
        "schema_version": "algotrader.corpus-presets.v1", "version": 1, "method": "btc.context-action.v0.2",
        "rules_version": "mp001.rules.v0.2", "source": "okx", "instrument": "BTC-USDT-SWAP",
        "availability": "MODELED_ZERO_EXTRA_DELAY", "fine_warmup_hours": WARMUP_H, "outcome_tail_minutes": TAIL_M,
        "window_convention": "UTC_HALF_OPEN_WHOLE_MINUTES", "acquisition_max_span_days": 31,
        "acquisition_split": "UTC_MONTH_AND_MAX_SPAN",
        "target": {"start": "2026-08-01T00:00:00Z", "end": "2026-10-01T00:00:00Z"},
        "development": {"start": "2026-08-01T00:00:00Z", "end": "2026-09-01T00:00:00Z"},
        "protected_provisional": {"start": "2026-09-01T00:00:00Z", "end": "2026-10-01T00:00:00Z",
                                  "contamination": "UNKNOWN_REQUIRES_DIRECTOR_INVENTORY_BEFORE_ECONOMIC_USE"},
        "capability_profile": {"execution": "HISTORICAL_BASE", "calendar": "NONE_UNKNOWN",
                               "incident_tape": "NOT_COVERED", "dislocation": "ENABLE_WHERE_SUPPORTED",
                               "funding_outcomes": "AUTHORITATIVE_IF_COVERED_ELSE_PRICE_NET_ONLY",
                               "metadata": "PINNED_RETRIEVAL_SNAPSHOT_ASSUMED_FOR_WINDOW"},
        "boundaries": {"warmup": "UNSCORED_FACTUAL_DERIVED_INITIALIZATION", "internal_month":
                       "CONTINUE_NO_FINISH_NO_RESET", "clock_end": "FULL_COVERAGE_END_PLUS_DECLARED_CLOSURE_ALLOWANCE"},
        "presets": [{"preset_id": "tiny-v1", "label": "Tiny fixture", "default": True,
                     "warmup": {"start": iso(w), "end": iso(ev_start)},
                     "evaluation": {"start": iso(ev_start), "end": iso(ev_end)},
                     "tail": {"start": iso(ev_end), "end": iso(t)},
                     "evidence_class": "DEVELOPMENT", "adviser_implemented": False, "automatic_prepare": False},
                    *(extra or [])],
        "fixture": True,
    }


def write_presets(tmp_path: Path, monkeypatch, **kw) -> Path:
    p = tmp_path / "presets.json"
    p.write_text(json.dumps(presets_doc(**kw)), encoding="utf-8")
    monkeypatch.setenv("ALGOTRADER_CORPUS_PRESETS", str(p))
    return p


def fake(gap_every=None, gaps=()):
    return synthetic_fake(FAKE_START, FAKE_END, gap_every=gap_every, gaps=gaps)


def acquire(root: Path, f, start: datetime, end: datetime) -> str:
    return md.acquire(client(f), root, start, end).manifest.dataset_id


def corpus_worker(database_url: str, root: Path, f, **kw) -> CorpusWorker:
    kw.setdefault("worker_id", "corpus:packtest")
    return CorpusWorker(database_url, root, lease_seconds=5, poll_interval=0.01, heartbeat_interval=0.05,
                        sleep=lambda s: None, client_factory=lambda base: client(f), **kw)


def drain(w) -> None:
    while w.run_once():
        pass


def connect(url: str):
    return psycopg.connect(url, autocommit=True, row_factory=psycopg.rows.dict_row)
