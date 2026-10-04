"""DB/worker helpers for adviser integration tests: hand fixtures served through the offline OKX fake, prepared as a
real receipt-pinned evaluation pack, then evaluated by the durable observation worker (engine observe.stream.v3).
Tiny synthetic engineering inputs only — never market evidence or an economic evaluation."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from adviser_fixtures import DAY1, DAY2
from okx_fake import FakeOkx
from pack_fixtures import connect, corpus_worker, drain

from algotrader.adviser.harness import Minute
from algotrader.corpus import pack as pk
from algotrader.corpus import pack_job as pj
from algotrader.corpus import presets as ps
from algotrader.marketdata.contracts import Family
from algotrader.observe.worker import ObservationWorker

MIN = timedelta(minutes=1)
WARMUP_H = 24
EV_START = DAY2
EV_END = DAY2 + timedelta(hours=6)
TAIL_M = 365


def iso(t: datetime) -> str:
    return t.isoformat().replace("+00:00", "Z")


def presets_doc(ev_start=EV_START, ev_end=EV_END) -> dict:
    w = ev_start - timedelta(hours=WARMUP_H)
    t = ev_end + timedelta(minutes=TAIL_M)
    return {
        "schema_version": "algotrader.corpus-presets.v1", "version": 1, "method": "btc.context-action.v0.2",
        "rules_version": "mp001.rules.v0.2", "source": "okx", "instrument": "BTC-USDT-SWAP",
        "availability": "MODELED_ZERO_EXTRA_DELAY", "fine_warmup_hours": WARMUP_H, "outcome_tail_minutes": TAIL_M,
        "window_convention": "UTC_HALF_OPEN_WHOLE_MINUTES", "acquisition_max_span_days": 31,
        "acquisition_split": "UTC_MONTH_AND_MAX_SPAN",
        "target": {"start": "2025-08-01T00:00:00Z", "end": "2025-10-01T00:00:00Z"},
        "development": {"start": "2025-08-01T00:00:00Z", "end": "2025-10-01T00:00:00Z"},
        "protected_provisional": {"start": "2026-01-01T00:00:00Z", "end": "2026-09-01T00:00:00Z",
                                  "contamination": "UNKNOWN_REQUIRES_DIRECTOR_INVENTORY_BEFORE_ECONOMIC_USE"},
        "capability_profile": {"execution": "HISTORICAL_BASE", "calendar": "NONE_UNKNOWN",
                               "incident_tape": "NOT_COVERED", "dislocation": "ENABLE_WHERE_SUPPORTED",
                               "funding_outcomes": "AUTHORITATIVE_IF_COVERED_ELSE_PRICE_NET_ONLY",
                               "metadata": "PINNED_RETRIEVAL_SNAPSHOT_ASSUMED_FOR_WINDOW"},
        "boundaries": {"warmup": "UNSCORED_FACTUAL_DERIVED_INITIALIZATION",
                       "internal_month": "CONTINUE_NO_FINISH_NO_RESET",
                       "clock_end": "FULL_COVERAGE_END_PLUS_DECLARED_CLOSURE_ALLOWANCE"},
        "presets": [{"preset_id": "adviser-fixture-v1", "label": "Adviser fixture", "default": True,
                     "warmup": {"start": iso(w), "end": iso(ev_start)},
                     "evaluation": {"start": iso(ev_start), "end": iso(ev_end)},
                     "tail": {"start": iso(ev_end), "end": iso(t)},
                     "evidence_class": "DEVELOPMENT", "adviser_implemented": False, "automatic_prepare": False}],
        "fixture": True,
    }


def write_presets(tmp_path: Path, monkeypatch, **kw) -> Path:
    p = tmp_path / "presets.json"
    p.write_text(json.dumps(presets_doc(**kw)), encoding="utf-8")
    monkeypatch.setenv("ALGOTRADER_CORPUS_PRESETS", str(p))
    return p


def fake_from(minutes: list[Minute], start: datetime = DAY1) -> FakeOkx:
    f = FakeOkx()
    trade, mark, index = [], [], []
    for i, m in enumerate(minutes):
        ms = str(int((start + i * MIN).timestamp() * 1000))
        if not m.gap:
            trade.append([ms, str(m.o), str(m.h), str(m.lo), str(m.c), "100", "1", str(m.c), "1"])
        mk = m.mark if m.mark is not None else m.c
        ix = m.index if m.index is not None else m.c
        mark.append([ms, str(mk), str(mk), str(mk), str(mk), "1"])
        index.append([ms, str(ix), str(ix), str(ix), str(ix), "1"])
    f.rows = {Family.TRADE_CANDLES: trade, Family.MARK_CANDLES: mark, Family.INDEX_CANDLES: index, Family.FUNDING: []}
    return f


def prepare_pack(database_url: str, root: Path, f: FakeOkx) -> dict:
    with connect(database_url) as c:
        P = ps.load_presets()
        jid = pj.create_pack_job(c, P, P.default)
    drain(corpus_worker(database_url, root, f))
    with connect(database_url) as c:
        job = c.execute("SELECT * FROM corpus_pack_jobs WHERE job_id = %s", (jid,)).fetchone()
        assert job["status"] == "completed", job["error"]
        rec = pk.pack_receipt(c, job["pack_id"])
    return {"pack_id": job["pack_id"], "manifest_sha256": rec["manifest_sha256"]}


def worker(database_url: str, root: Path, art: Path, wid: str = "observe:adv", **kw) -> ObservationWorker:
    kw.setdefault("checkpoint_events", 5000)
    return ObservationWorker(database_url, root, art, worker_id=wid, isolate=False, sleep=lambda s: None,
                             lease_seconds=5, poll_interval=0.01, **kw)


def run_all(w: ObservationWorker) -> None:
    while w.run_once():
        pass


def replay(database_url: str, rid: str) -> dict:
    with connect(database_url) as c:
        return c.execute("SELECT * FROM observation_replays WHERE replay_id = %s", (rid,)).fetchone()


def journal(database_url: str, rid: str) -> list[dict]:
    with connect(database_url) as c:
        return c.execute("SELECT * FROM adviser_journal WHERE run_id = %s ORDER BY seq", (rid,)).fetchall()


def records(database_url: str, rid: str) -> list[dict]:
    with connect(database_url) as c:
        return c.execute("SELECT * FROM adviser_evaluation_records WHERE run_id = %s ORDER BY seq", (rid,)).fetchall()


_ = UTC
