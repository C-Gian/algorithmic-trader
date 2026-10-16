"""Convenzioni congelate OBS-001/v1 e loro impronta.

L'hash è calcolato sul JSON canonico (chiavi ordinate, senza spazi, UTF-8), quindi non
dipende da fine riga o indentazione del file nel checkout.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "config" / "OBS-001-v1.json"
CONVENTIONS_ID = "OBS-001/v1"

MINUTE_MS = 60_000
DAY_MS = 86_400_000


def parse_utc(text: str) -> int:
    """ISO 8601 con suffisso Z -> millisecondi epoch UTC."""
    if not text.endswith("Z"):
        raise ValueError(f"atteso un istante UTC con suffisso Z: {text!r}")
    dt = datetime.fromisoformat(text[:-1] + "+00:00")
    return int(dt.timestamp() * 1000)


def iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def canonical_json(data: Any) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class Conventions:
    raw: dict
    hash: str
    input_start: int
    study_start: int
    end: int
    bar_ms: int
    day_ms: int

    @property
    def months(self) -> list[str]:
        return list(self.raw["source"]["months"])

    @property
    def study_months(self) -> list[str]:
        return list(self.raw["study"]["months"])

    def section(self, name: str) -> dict:
        return self.raw[name]


def load_conventions(path: Path | None = None) -> Conventions:
    data = json.loads((path or DEFAULT_CONFIG).read_text(encoding="utf-8"))
    if data.get("id") != CONVENTIONS_ID:
        raise ValueError(f"configurazione inattesa: {data.get('id')!r}, atteso {CONVENTIONS_ID}")
    periods = data["periods"]
    clock = data["clock"]
    conv = Conventions(
        raw=data,
        hash=sha256_bytes(canonical_json(data)),
        input_start=parse_utc(periods["inputStart"]),
        study_start=parse_utc(periods["studyStart"]),
        end=parse_utc(periods["end"]),
        bar_ms=clock["barMinutes"] * MINUTE_MS,
        day_ms=clock["dayMinutes"] * MINUTE_MS,
    )
    if conv.day_ms != DAY_MS or conv.day_ms % conv.bar_ms or conv.day_ms // conv.bar_ms != clock["barsPerDay"]:
        raise ValueError("griglia 45m/1D incoerente con la configurazione")
    for t in (conv.input_start, conv.study_start, conv.end):
        if t % DAY_MS:
            raise ValueError("i confini dei periodi devono essere mezzanotti UTC")
    return conv
