"""Registered evaluation presets (``algotrader.corpus-presets.v1``; checked-in ``presets.json`` next to this module).

The packaged ``presets.json`` is a byte-identical copy of the Director-registered
``delivery/WP-008-R3-PRESETS.json`` (a regression test pins the equality). It declares logical windows only:
warmup (unscored factual/derived initialization), evaluation (contiguous calendar months, the only scored portion
for a later adviser) and outcome tail, all UTC half-open whole minutes. It contains no market bytes, paths, secrets
or timestamps of preparation, so its identity hash is reproducible on any machine.

WP-013 adds one OPTIONAL preset field, ``initialization``. Absent (every earlier preset), the warmup is exactly the
file's ``fine_warmup_hours`` before the evaluation start, as before. ``REGISTERED_EXPLICIT_INITIALIZATION`` declares
an explicitly registered, longer unscored initialization window (at least the fine warmup, ending at the evaluation
start); it is context only and is never evaluated. An absent field is not serialized, so the documents and identity
hashes of the earlier presets are byte-for-byte unchanged and the file-level warmup is not modified globally.

``ALGOTRADER_CORPUS_PRESETS`` may point at another file; it exists only so deterministic tests can use tiny
``"fixture": true`` windows that match offline fixtures. Fixture files may use non-calendar evaluation windows;
registered files may not.

Registered study windows (``study_presets.json``, ``algotrader.study-presets.v1``) are the only exception to the
calendar-month / logical-target rules: a preset that equals, field for field, a study preset registered there (window,
initialization and tail taken from the study's pinned authoritative design) is accepted outside the target and
without month alignment. It must still use an explicit initialization and the file's tail, may not overlap the
development or protected periods, and is classified ``REGISTERED_STUDY_WINDOW``. Nothing else widens the date range:
the month builder and every other preset keep the earlier checks. ``ALGOTRADER_STUDY_PRESETS`` may point at another
file only so that tests can use tiny synthetic study windows.

No call, outcome or adviser metric is defined or computed here.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from ..feed.ordering import canonical

PRESETS_FILE = Path(__file__).with_name("presets.json")
STUDY_PRESETS_FILE = Path(__file__).with_name("study_presets.json")
STUDY_EVIDENCE_CLASS = "REGISTERED_STUDY_WINDOW"
PRESETS_SCHEMA_VERSION = "algotrader.corpus-presets.v1"
# Canonical-JSON SHA-256 of delivery/MP-001-PARAMETERS.json (the method register these presets serve as input
# requirements; it is NOT implemented here). Pinned by a regression test against the delivery file.
MP001_REGISTER_SHA256 = "e2e2dd8ef0501e239c3e4f07dc17732e72fdbbaab3a10471a521bfd2a2d60bae"


class PresetError(ValueError):
    """An invalid, discontiguous or out-of-target preset/selection."""


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def _aligned(t: datetime, what: str) -> None:
    if t.utcoffset() != timedelta(0) or t.second or t.microsecond:
        raise PresetError(f"{what}: {t.isoformat()} is not a whole UTC minute")


def _month_start(t: datetime) -> bool:
    return t.day == 1 and t.hour == 0 and t.minute == 0


def add_months(t: datetime, n: int) -> datetime:
    m = t.month - 1 + n
    return t.replace(year=t.year + m // 12, month=m % 12 + 1)


class Window(_Model):
    start: datetime
    end: datetime

    @model_validator(mode="after")
    def _check(self) -> Window:
        _aligned(self.start, "window start")
        _aligned(self.end, "window end")
        if self.end <= self.start:
            raise PresetError("window end must be after its start")
        return self

    @property
    def minutes(self) -> int:
        return int((self.end - self.start) / timedelta(minutes=1))


class Protected(_Model):
    start: datetime
    end: datetime
    contamination: str


INITIALIZATION_EXPLICIT = "REGISTERED_EXPLICIT_INITIALIZATION"
INITIALIZATION_NOTE = ("Registered initialization window: market context only. Calls, outcomes and diagnostics "
                       "inside it are never evaluated; it builds the method's existing dependencies (scales and "
                       "landmarks) before the evaluation starts.")


class Preset(_Model):
    preset_id: str
    label: str
    default: bool
    warmup: Window
    evaluation: Window
    tail: Window
    evidence_class: str
    adviser_implemented: Literal[False]
    automatic_prepare: Literal[False]
    initialization: Literal["REGISTERED_EXPLICIT_INITIALIZATION"] | None = None  # WP-013; absent = fine warmup


class StudySource(_Model):
    path: str
    sha256_lf: str


class StudyPreset(_Model):
    """One registered study window: its authoritative sources, the run it admits and its exact preset."""

    study_id: str
    label: str
    sources: tuple[StudySource, ...]
    run_type: Literal["adviser_evaluation"]
    method: str
    preset: Preset


class StudyPresetsFile(_Model):
    schema_version: Literal["algotrader.study-presets.v1"]
    version: int
    studies: tuple[StudyPreset, ...]
    fixture: bool = False  # test-only files use tiny synthetic windows


class PresetsFile(_Model):
    schema_version: Literal["algotrader.corpus-presets.v1"]
    version: int
    method: str
    rules_version: str
    source: Literal["okx"]
    instrument: str
    availability: str
    fine_warmup_hours: int
    outcome_tail_minutes: int
    window_convention: Literal["UTC_HALF_OPEN_WHOLE_MINUTES"]
    acquisition_max_span_days: int
    acquisition_split: str
    target: Window
    development: Window
    protected_provisional: Protected
    capability_profile: dict[str, str]
    boundaries: dict[str, str]
    presets: tuple[Preset, ...]
    fixture: bool = False  # test-only files may use non-calendar evaluation windows

    @model_validator(mode="after")
    def _check(self) -> PresetsFile:
        ids = [p.preset_id for p in self.presets]
        if len(set(ids)) != len(ids):
            raise PresetError("duplicate preset_id")
        if sum(1 for p in self.presets if p.default) != 1:
            raise PresetError("exactly one preset must be the default")
        for p in self.presets:
            check_windows(self, p)
        return self

    def preset(self, preset_id: str) -> Preset | None:
        return next((p for p in self.presets if p.preset_id == preset_id), None)

    @property
    def default(self) -> Preset:
        return next(p for p in self.presets if p.default)


def study_presets_path() -> Path:
    override = os.environ.get("ALGOTRADER_STUDY_PRESETS")
    return Path(override) if override else STUDY_PRESETS_FILE


@lru_cache(maxsize=4)
def _load_studies(path: str, mtime: float) -> StudyPresetsFile:
    return StudyPresetsFile.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


def load_study_presets(path: Path | None = None) -> StudyPresetsFile:
    p = path or study_presets_path()
    return _load_studies(str(p), p.stat().st_mtime)


def registered_study(p: Preset) -> StudyPreset | None:
    """The registered study whose preset equals ``p`` field for field (None for every other preset)."""
    doc = preset_doc(p)
    return next((s for s in load_study_presets().studies if preset_doc(s.preset) == doc), None)


def check_windows(f: PresetsFile, p: Preset) -> None:
    """Exact warmup/tail arithmetic around a contiguous evaluation window inside the logical target (or a registered
    study window: see the module note)."""
    w, e, t = p.warmup, p.evaluation, p.tail
    if p.initialization is None:
        if w.end != e.start or w.start != e.start - timedelta(hours=f.fine_warmup_hours):
            raise PresetError(f"{p.preset_id}: warmup must be exactly {f.fine_warmup_hours}h ending at evaluation "
                              "start")
    elif w.end != e.start or w.start > e.start - timedelta(hours=f.fine_warmup_hours):
        raise PresetError(f"{p.preset_id}: a registered initialization must end at the evaluation start and last at "
                          f"least the fine warmup ({f.fine_warmup_hours}h)")
    if t.start != e.end or t.end != e.end + timedelta(minutes=f.outcome_tail_minutes):
        raise PresetError(f"{p.preset_id}: tail must be exactly {f.outcome_tail_minutes}m starting at evaluation end")
    if registered_study(p) is not None:
        if p.initialization is None or p.evidence_class != STUDY_EVIDENCE_CLASS:
            raise PresetError(f"{p.preset_id}: a registered study window needs an explicit initialization and the "
                              f"{STUDY_EVIDENCE_CLASS} class")
        for name, win in (("development", f.development), ("protected", f.protected_provisional)):
            if max(w.start, win.start) < min(t.end, win.end):
                raise PresetError(f"{p.preset_id}: a registered study window may not overlap the {name} period")
        return
    if not f.fixture and not (_month_start(e.start) and _month_start(e.end)):
        raise PresetError(f"{p.preset_id}: evaluation must be whole contiguous calendar months")
    if not (f.target.start <= e.start < e.end <= f.target.end):
        raise PresetError(f"{p.preset_id}: evaluation is outside the logical target "
                          f"[{f.target.start.isoformat()}, {f.target.end.isoformat()})")


def presets_path() -> Path:
    override = os.environ.get("ALGOTRADER_CORPUS_PRESETS")
    return Path(override) if override else PRESETS_FILE


@lru_cache(maxsize=4)
def _load(path: str, mtime: float) -> PresetsFile:
    return PresetsFile.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


def load_presets(path: Path | None = None) -> PresetsFile:
    p = path or presets_path()
    return _load(str(p), p.stat().st_mtime)


def policy_doc(f: PresetsFile) -> dict:
    """File-level policies a preset's identity depends on (no other preset, no fixture flag)."""
    d = json.loads(f.model_dump_json())
    d.pop("presets")
    d.pop("fixture", None)
    return d


def preset_doc(p: Preset) -> dict:
    """Serialized preset; the optional ``initialization`` is omitted when absent so earlier documents/identities are
    unchanged."""
    d = json.loads(p.model_dump_json())
    if d.get("initialization") is None:
        d.pop("initialization", None)
    return d


def initialization_doc(p: Preset) -> dict | None:
    """The explicit initialization of a WP-013 preset (None for the fine-warmup presets)."""
    if p.initialization is None:
        return None
    return {"policy": p.initialization, "start": p.warmup.start.isoformat(), "end": p.warmup.end.isoformat(),
            "hours": p.warmup.minutes // 60, "minutes": p.warmup.minutes, "evaluated": False,
            "note": INITIALIZATION_NOTE}


def preset_sha256(f: PresetsFile, p: Preset) -> str:
    """Identity of one preset under its declared policies (machine/path/time independent)."""
    return hashlib.sha256(canonical({"preset": preset_doc(p), "policies": policy_doc(f)})).hexdigest()


def capability_profile_sha256(f: PresetsFile) -> str:
    return hashlib.sha256(canonical(f.capability_profile)).hexdigest()


def requested(p: Preset) -> Window:
    """Full requested coverage: warmup start .. tail end."""
    return Window(start=p.warmup.start, end=p.tail.end)


def windows_doc(p: Preset) -> dict:
    out = {
        "warmup": {"start": p.warmup.start.isoformat(), "end": p.warmup.end.isoformat(), "scored": False,
                   "minutes": p.warmup.minutes},
        "evaluation": {"start": p.evaluation.start.isoformat(), "end": p.evaluation.end.isoformat(), "scored": True,
                       "minutes": p.evaluation.minutes},
        "tail": {"start": p.tail.start.isoformat(), "end": p.tail.end.isoformat(), "scored": False,
                 "minutes": p.tail.minutes},
        "requested": {"start": p.warmup.start.isoformat(), "end": p.tail.end.isoformat()},
        "convention": "UTC half-open [start, end), whole minutes; only the evaluation window is ever scored",
    }
    init = initialization_doc(p)
    if init is not None:  # additive key only for an explicit initialization (earlier documents unchanged)
        out["initialization"] = init
    return out


def classify(f: PresetsFile, p: Preset) -> dict:
    """Development / provisional-protected portions of the evaluation window, reported separately."""
    study = registered_study(p)
    if study is not None:  # never labelled DEVELOPMENT by default: it lies outside both periods (check_windows)
        return {"label": STUDY_EVIDENCE_CLASS, "portions": [], "study_id": study.study_id, "method": study.method,
                "run_type": study.run_type,
                "note": ("Registered prospective study window outside the development and protected periods; data "
                         "preparation and integrity checks never certify uncontaminated evidence."),
                "certified_uncontaminated": False}
    e = p.evaluation
    portions = []
    for cls, w in (("DEVELOPMENT", f.development), ("PROTECTED_PROVISIONAL", f.protected_provisional)):
        lo, hi = max(e.start, w.start), min(e.end, w.end)
        if lo < hi:
            portions.append({"class": cls, "start": lo.isoformat(), "end": hi.isoformat(),
                             "contamination": (f.protected_provisional.contamination if cls == "PROTECTED_PROVISIONAL"
                                               else "DEVELOPMENT_EVIDENCE_ONLY")})
    classes = {x["class"] for x in portions}
    label = ("MIXED_DEVELOPMENT_AND_PROTECTED" if len(classes) > 1 else
             "PROTECTED_PROVISIONAL" if classes == {"PROTECTED_PROVISIONAL"} else "DEVELOPMENT")
    note = ("Contamination is UNKNOWN for protected portions: data preparation and integrity checks never certify "
            "uncontaminated economic evidence; the Director inventories revealed outcomes before any economic use."
            if "PROTECTED_PROVISIONAL" in classes else "Development evidence only.")
    # never "wholly protected / clean" before the Director's contamination inventory
    return {"label": label, "portions": portions, "note": note, "certified_uncontaminated": False}


def months_preset(f: PresetsFile, months: list[str]) -> Preset:
    """General contiguous-month builder: first month start - warmup .. last month end + tail.

    ``months`` are ``YYYY-MM`` strings; they must be chronological, contiguous and inside the logical target.
    """
    if not months:
        raise PresetError("select at least one month")
    try:
        starts = [datetime.fromisoformat(f"{m}-01T00:00:00+00:00") for m in months]
    except ValueError:
        raise PresetError("months must be YYYY-MM") from None
    for a, b in zip(starts, starts[1:]):
        if add_months(a, 1) != b:
            raise PresetError("months must be chronological and contiguous (no gaps, no repeats)")
    first, end = starts[0], add_months(starts[-1], 1)
    label_cls = "DEVELOPMENT"
    p = Preset(
        preset_id=f"btc-months-{months[0]}-to-{months[-1]}-v1",
        label=f"{first:%B %Y}" + ("" if len(months) == 1 else f" – {starts[-1]:%B %Y}") + " — selected months",
        default=False,
        warmup=Window(start=first - timedelta(hours=f.fine_warmup_hours), end=first),
        evaluation=Window(start=first, end=end),
        tail=Window(start=end, end=end + timedelta(minutes=f.outcome_tail_minutes)),
        evidence_class=label_cls, adviser_implemented=False, automatic_prepare=False)
    check_windows(f, p)
    cls = classify(f, p)["label"]
    return p.model_copy(update={"evidence_class": cls})


def resolve(f: PresetsFile, preset_id: str | None = None, months: list[str] | None = None) -> Preset:
    if months:
        return months_preset(f, months)
    p = f.preset(preset_id) if preset_id else f.default
    if p is None and preset_id:
        p = next((s.preset for s in load_study_presets().studies if s.preset.preset_id == preset_id), None)
    if p is None:
        raise PresetError(f"unknown preset {preset_id!r}")
    return p
