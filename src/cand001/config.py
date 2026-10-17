"""Configurazione congelata CAND-001/v1 e convenzioni osservative OBS-001/v1 con nuovi confini."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path

from obs001.conventions import REPO_ROOT, Conventions, canonical_json, iso, load_conventions, parse_utc, sha256_bytes

CONFIG_PATH = REPO_ROOT / "config" / "CAND-001-v1.json"
CANDIDATE_ID = "CAND-001/v1"


@dataclass(frozen=True)
class Candidate:
    raw: dict
    hash: str

    @property
    def p(self) -> dict:
        return self.raw["parameters"]

    @property
    def econ(self) -> dict:
        return self.raw["economics"]

    def window(self, phase: str) -> tuple[int, int]:
        w = self.raw["windows"][phase]
        return parse_utc(w["start"]), parse_utc(w["end"])

    @property
    def input_start(self) -> int:
        return parse_utc(self.raw["windows"]["inputStart"])


def load_candidate(path: Path | None = None) -> Candidate:
    data = json.loads((path or CONFIG_PATH).read_text(encoding="utf-8"))
    if data.get("id") != CANDIDATE_ID:
        raise ValueError(f"configurazione inattesa: {data.get('id')!r}")
    obs = load_conventions()
    if data["observations"]["conventionsHash"] != obs.hash:
        raise ValueError("le convenzioni osservative non coincidono con OBS-001/v1 registrate")
    return Candidate(raw=data, hash=sha256_bytes(canonical_json(data)))


def observation_conventions(input_start: int, end: int) -> Conventions:
    """OBS-001/v1 con confini di input diversi: definizioni e parametri osservativi identici.
    Le sezioni di studio OBS (origini/esiti) non sono usate da CAND-001."""
    base = load_conventions()
    raw = copy.deepcopy(base.raw)
    raw["periods"] = {"inputStart": iso(input_start), "studyStart": iso(input_start), "end": iso(end)}
    return Conventions(raw=raw, hash=base.hash, input_start=input_start, study_start=input_start, end=end,
                       bar_ms=base.bar_ms, day_ms=base.day_ms)


def months_between(start: int, end: int) -> list[str]:
    """Mesi YYYY-MM che intersecano [start, end)."""
    from datetime import UTC, datetime

    out = []
    d = datetime.fromtimestamp(start / 1000, UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    while int(d.timestamp() * 1000) < end:
        out.append(d.strftime("%Y-%m"))
        d = d.replace(year=d.year + 1, month=1) if d.month == 12 else d.replace(month=d.month + 1)
    return out
