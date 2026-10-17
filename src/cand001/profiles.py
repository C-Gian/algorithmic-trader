"""Profili fissi dei backtest avviabili (registro APP-001, separato dalla configurazione del candidato).

Ogni profilo è una finestra valutata del candidato congelato: le due fasi registrate (DEV,
ADDITIONAL_2025) prendono la finestra da config/CAND-001-v1.json; il profilo di collaudo
APP_CHECK_2025_01 dichiara la propria finestra, che deve stare dentro la fase indicata. Nessun
parametro economico o di strategia: solo identità, nome e periodo. Il 2026 resta escluso.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from obs001.conventions import REPO_ROOT, iso, parse_utc

from .config import Candidate

REGISTRY_PATH = REPO_ROOT / "config" / "APP-001-profiles.json"
REGISTRY_ID = "APP-001/profiles"
PROTECTED_FROM = parse_utc("2026-01-01T00:00:00Z")
KINDS = ("PRODUCT_CHECK", "DEVELOPMENT", "ADDITIONAL_COMPARISON")


class ProfileError(ValueError):
    """Registro dei profili non coerente con il candidato o con i confini autorizzati."""


@dataclass(frozen=True)
class Profile:
    id: str
    label: str
    kind: str
    window: tuple[int, int]
    phase: str  # fase registrata del candidato che contiene la finestra
    description: str
    registry: str

    def ref(self) -> dict:
        """Identità del profilo nel bundle e nei manifest (deterministica, senza date di esecuzione)."""
        return {"id": self.id, "label": self.label, "kind": self.kind, "registry": self.registry,
                "window": {"start": self.window[0], "end": self.window[1]}, "withinPhase": self.phase}


def _month_aligned(t: int) -> bool:
    d = datetime.fromtimestamp(t / 1000, UTC)
    return d.day == 1 and d.hour == 0 and d.minute == 0 and d.second == 0 and d.microsecond == 0


def load_profiles(cand: Candidate, path: Path | None = None) -> dict[str, Profile]:
    raw = json.loads((path or REGISTRY_PATH).read_text(encoding="utf-8"))
    if raw.get("id") != REGISTRY_ID or not isinstance(raw.get("version"), int):
        raise ProfileError("registro dei profili non riconosciuto")
    if raw.get("candidate") != cand.raw["id"] or raw.get("configHash") != cand.hash:
        raise ProfileError("il registro dei profili non corrisponde al candidato congelato (id o hash della configurazione)")
    registry = f"{REGISTRY_ID}/v{raw['version']}"
    out: dict[str, Profile] = {}
    for p in raw["profiles"]:
        pid = p["id"]
        if pid in out or p.get("kind") not in KINDS:
            raise ProfileError(f"profilo {pid}: identità o tipo non validi")
        if "phase" in p:
            phase = p["phase"]
            window = cand.window(phase)
            if "window" in p:
                raise ProfileError(f"profilo {pid}: una fase registrata non può ridefinire la finestra")
        else:
            phase = p["withinPhase"]
            window = (parse_utc(p["window"]["start"]), parse_utc(p["window"]["end"]))
        lo, hi = cand.window(phase)
        start, end = window
        if not (lo <= start < end <= hi):
            raise ProfileError(f"profilo {pid}: finestra fuori dalla fase {phase}")
        if start < cand.input_start or end > PROTECTED_FROM:
            raise ProfileError(f"profilo {pid}: finestra fuori dai confini autorizzati (nessun dato 2026)")
        if not (_month_aligned(start) and _month_aligned(end)):
            raise ProfileError(f"profilo {pid}: la finestra deve iniziare e finire a inizio mese UTC")
        out[pid] = Profile(pid, p["label"], p["kind"], window, phase, p.get("description", ""), registry)
    return out


def describe(profile: Profile) -> dict:
    """Testo di presentazione: periodo valutato e prefisso osservativo, distinti."""
    return {**profile.ref(), "description": profile.description, "windowIso": [iso(profile.window[0]), iso(profile.window[1])]}
