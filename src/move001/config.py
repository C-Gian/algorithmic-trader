"""Convenzioni MOVE-001/v1 (config/MOVE-001-v1.json) e osservatore OBS-001/v1 con i confini MOVE-001."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path

from obs001.conventions import REPO_ROOT, Conventions, canonical_json, iso, load_conventions, parse_utc, sha256_bytes

CONFIG_PATH = REPO_ROOT / "config" / "MOVE-001-v1.json"
STUDY_ID = "MOVE-001/v1"
# Mesi trade letti, elencati esplicitamente: nessun mese 2025 o successivo.
MONTHS = [f"2022-{m:02d}" for m in (10, 11, 12)] + [f"{y}-{m:02d}" for y in (2023, 2024) for m in range(1, 13)]


@dataclass(frozen=True)
class Study:
    raw: dict
    hash: str
    input_start: int
    study_start: int
    end: int


def load_study(path: Path | None = None) -> Study:
    data = json.loads((path or CONFIG_PATH).read_text(encoding="utf-8"))
    if data.get("id") != STUDY_ID or data.get("version") != "1.0.1":
        raise ValueError(f"configurazione inattesa: {data.get('id')!r} {data.get('version')!r}")
    if data["observationDefinitions"]["hash"] != load_conventions().hash:
        raise ValueError("le definizioni osservative non coincidono con OBS-001/v1 registrate")
    p = data["periods"]
    study = Study(raw=data, hash=sha256_bytes(canonical_json(data)), input_start=parse_utc(p["inputStart"]),
                  study_start=parse_utc(p["studyStart"]), end=parse_utc(p["end"]))
    if (iso(study.input_start), iso(study.study_start), iso(study.end)) != ("2022-10-01T00:00:00Z", "2023-01-01T00:00:00Z", "2025-01-01T00:00:00Z"):
        raise ValueError("confini diversi da quelli autorizzati")
    return study


def observation_conventions(study: Study) -> Conventions:
    """OBS-001/v1 con i confini di input MOVE-001: definizioni e parametri osservativi identici."""
    base = load_conventions()
    raw = copy.deepcopy(base.raw)
    raw["periods"] = {"inputStart": iso(study.input_start), "studyStart": iso(study.study_start), "end": iso(study.end)}
    return Conventions(raw=raw, hash=base.hash, input_start=study.input_start, study_start=study.study_start, end=study.end,
                       bar_ms=base.bar_ms, day_ms=base.day_ms)
