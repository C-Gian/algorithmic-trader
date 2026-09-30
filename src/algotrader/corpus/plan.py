"""Checked-in logical corpus plan (``plan.json`` next to this module).

The plan declares *logical coverage only*: the Foundation target interval and its
monthly chunks. It contains no market bytes. Local preparation state (which
immutable dataset a chunk is bound to) lives in PostgreSQL, see ``state.py``.

``ALGOTRADER_CORPUS_PLAN`` may point at another plan file; it exists only so
deterministic tests can use a tiny chunk that matches offline fixtures. The
application default is the checked-in plan.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict, model_validator

from ..marketdata.contracts import HISTORICAL_FAMILIES, Family
from ..marketdata.dataset import MAX_SPAN

PLAN_FILE = Path(__file__).with_name("plan.json")


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Interval(_Model):
    start: datetime
    end: datetime
    note: str | None = None


class Chunk(_Model):
    chunk_id: str
    label: str
    start: datetime  # inclusive, UTC
    end: datetime  # exclusive, UTC
    preparable: bool  # only enabled chunks can be prepared from the app
    note: str


class CorpusPlan(_Model):
    plan_id: str
    plan_version: int
    description: str
    source: str
    inst_id: str
    bar: str
    families: tuple[Family, ...]
    target: Interval
    chunk_rule: str
    chunks: tuple[Chunk, ...]

    @model_validator(mode="after")
    def _check(self) -> CorpusPlan:
        if self.source != "okx":
            raise ValueError("the corpus source must be the accepted public OKX source")
        if set(self.families) != {Family.INSTRUMENT, *HISTORICAL_FAMILIES}:
            raise ValueError("a corpus chunk is a full marketdata.v1 dataset (instrument + four families)")
        ids = [c.chunk_id for c in self.chunks]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate chunk_id")
        prev_end = None
        for c in self.chunks:
            for t in (c.start, c.end):
                if t.utcoffset() != timedelta(0) or t.second or t.microsecond:
                    raise ValueError(f"{c.chunk_id}: bounds must be whole UTC minutes")
            if not self.target.start <= c.start < c.end <= self.target.end:
                raise ValueError(f"{c.chunk_id}: outside the corpus target")
            if c.end - c.start > MAX_SPAN:
                raise ValueError(f"{c.chunk_id}: exceeds the bounded acquisition span ({MAX_SPAN.days} days)")
            if prev_end is not None and c.start < prev_end:
                raise ValueError(f"{c.chunk_id}: chunks overlap or are not chronological")
            prev_end = c.end
        return self

    def chunk(self, chunk_id: str) -> Chunk | None:
        return next((c for c in self.chunks if c.chunk_id == chunk_id), None)


def plan_path() -> Path:
    override = os.environ.get("ALGOTRADER_CORPUS_PLAN")
    return Path(override) if override else PLAN_FILE


@lru_cache(maxsize=4)
def _load(path: str, mtime: float) -> CorpusPlan:
    return CorpusPlan.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


def load_plan(path: Path | None = None) -> CorpusPlan:
    p = path or plan_path()
    return _load(str(p), p.stat().st_mtime)
