"""Catalogo dei risultati salvati (cartelle runs/ e loro run-manifest) e disponibilità dei dati dei profili.

Nessun DB: il catalogo si ricava dalle cartelle, leggendo solo i piccoli manifest (in cache per
data/dimensione). Un risultato è apribile solo con run-manifest leggibile, schema supportato e bundle
della dimensione dichiarata; all'apertura lo SHA256 del bundle deve coincidere col manifest. Un
risultato vecchio senza profilo registrato riceve il profilo dedotto dalla fase, dichiarato come tale;
nessuna data d'avvio o job viene inventato. Gli ID sono nomi di cartella validati, mai percorsi.
"""

from __future__ import annotations

import hashlib
import json
import re
import threading
from pathlib import Path

from cand001.config import Candidate
from cand001.data import obs_dir
from cand001.pipeline import BUNDLE_FILE, RUN_MANIFEST, input_plan
from cand001.profiles import Profile

RESULT_ID = re.compile(r"^CAND-001-[A-Za-z0-9._-]{1,150}$")
SUPPORTED = ("cand001.bundle/2", "cand001.bundle/3")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class Catalog:
    def __init__(self, cand: Candidate, profiles: dict[str, Profile], data_dir: Path):
        self.cand, self.profiles, self.data_dir = cand, profiles, data_dir
        self.runs = data_dir / "runs"
        self._lock = threading.Lock()
        self._entries: dict[str, tuple[tuple, dict]] = {}
        self._verified: dict[str, tuple] = {}

    # ------------------------------------------------------------- elenco

    def _profile_of(self, manifest: dict) -> dict | None:
        if isinstance(manifest.get("profile"), dict):
            p = manifest["profile"]
            known = self.profiles.get(p.get("id"))
            return {**p, "label": known.label if known else p.get("label"), "inferred": False}
        phase = manifest.get("phase")
        if phase in self.profiles and phase in ("DEV", "ADDITIONAL_2025"):
            return {**self.profiles[phase].ref(), "inferred": True}
        return None

    def _entry(self, folder: Path) -> dict:
        rid = folder.name
        base = {"resultId": rid, "status": "NOT_OPENABLE", "reason": None, "profile": None, "window": None, "schema": None,
                "engineVersion": None, "candidate": None, "startedAt": None, "finishedAt": None, "complete": None, "trades": None,
                "net": None, "halted": None, "inputHash": None, "bundleBytes": None, "via": None, "jobId": None}
        mpath = folder / RUN_MANIFEST
        try:
            manifest = json.loads(mpath.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {**base, "reason": "manifest del run assente: pubblicazione incompleta o cartella non prodotta dal motore"}
        except (OSError, ValueError):
            return {**base, "reason": "manifest del run non leggibile"}
        if not isinstance(manifest, dict) or manifest.get("kind") != "CAND001_RUN":
            return {**base, "reason": "manifest del run non riconosciuto"}
        profile = self._profile_of(manifest)
        out = {**base, "schema": manifest.get("schema"), "engineVersion": manifest.get("engineVersion"), "candidate": manifest.get("candidate"),
               "startedAt": manifest.get("startedAt"), "finishedAt": manifest.get("finishedAt"), "profile": profile,
               "window": profile["window"] if profile else None, "inputHash": manifest.get("inputHash"),
               "trades": (manifest.get("counts") or {}).get("trades"), "halted": manifest.get("halted"),
               "via": (manifest.get("execution") or {}).get("via", "DIRECT"), "jobId": (manifest.get("execution") or {}).get("jobId")}
        rec = manifest.get("reconciliation") or {}
        out["complete"] = rec.get("windowComplete")
        out["net"] = rec.get("net")
        if manifest.get("schema") not in SUPPORTED:
            return {**out, "status": "UNSUPPORTED_SCHEMA",
                    "reason": f"schema {manifest.get('schema')} conservato ma non supportato dall'app (nessuna migrazione)"}
        if profile is None:
            return {**out, "reason": "profilo non riconosciuto per questo run"}
        bundle = (manifest.get("outputs") or {}).get("bundle") or {}
        path = folder / BUNDLE_FILE
        if bundle.get("file") != BUNDLE_FILE or not path.exists():
            return {**out, "reason": "file del bundle assente"}
        size = path.stat().st_size
        if size != bundle.get("bytes"):
            return {**out, "reason": "dimensione del bundle diversa da quella registrata nel manifest"}
        return {**out, "status": "OK", "bundleBytes": size}

    def list(self) -> list[dict]:
        if not self.runs.exists():
            return []
        out = []
        with self._lock:
            seen = set()
            for folder in sorted(self.runs.iterdir()):
                if not folder.is_dir() or not RESULT_ID.match(folder.name):
                    continue
                seen.add(folder.name)
                key = tuple((p.stat().st_mtime_ns, p.stat().st_size) if p.exists() else None for p in (folder / RUN_MANIFEST, folder / BUNDLE_FILE))
                cached = self._entries.get(folder.name)
                if cached is None or cached[0] != key:
                    cached = (key, self._entry(folder))
                    self._entries[folder.name] = cached
                out.append(cached[1])
            for gone in set(self._entries) - seen:
                del self._entries[gone]
        out.sort(key=lambda e: e["finishedAt"] or "", reverse=True)
        return out

    def get(self, result_id: str) -> dict | None:
        if not RESULT_ID.match(result_id or ""):
            return None
        return next((e for e in self.list() if e["resultId"] == result_id), None)

    def manifest(self, result_id: str) -> dict | None:
        entry = self.get(result_id)
        if entry is None:
            return None
        try:
            return json.loads((self.runs / entry["resultId"] / RUN_MANIFEST).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def bundle(self, result_id: str) -> tuple[dict | None, bytes | None, str | None]:
        """(voce, contenuto, motivo del rifiuto). Il contenuto è restituito solo se lo SHA256 coincide."""
        entry = self.get(result_id)
        if entry is None:
            return None, None, "NOT_FOUND"
        if entry["status"] != "OK":
            return entry, None, entry["reason"]
        folder = self.runs / entry["resultId"]
        path = folder / BUNDLE_FILE
        manifest = self.manifest(result_id) or {}
        expected = ((manifest.get("outputs") or {}).get("bundle") or {}).get("sha256")
        body = path.read_bytes()
        key = (path.stat().st_mtime_ns, len(body))
        if self._verified.get(entry["resultId"]) != key:
            if hashlib.sha256(body).hexdigest() != expected:
                return entry, None, "SHA256 del bundle diverso da quello registrato nel manifest: risultato non aperto"
            self._verified[entry["resultId"]] = key
        return entry, body, None

    # ------------------------------------------------------------- disponibilità dati

    def availability(self, profile: Profile) -> dict:
        """Controllo rapido: ogni file richiesto è registrato nel manifest d'acquisizione ed esiste con la
        dimensione registrata. Lo SHA256 completo si verifica nella fase di controllo del backtest."""
        plan = input_plan(self.cand, profile)
        missing = []
        manifests = {}
        for kind in ("trade", "funding", "mark"):
            try:
                manifests[kind] = json.loads((self.data_dir / "manifests" / f"acquisition-{kind}.json").read_text(encoding="utf-8"))
            except (OSError, ValueError):
                manifests[kind] = None
        try:
            obs = json.loads((obs_dir(self.data_dir) / "manifests" / "acquisition.json").read_text(encoding="utf-8")) if plan["reuseObs"] else None
        except (OSError, ValueError):
            obs = None
        for kind in ("trade", "funding", "mark"):
            for month in plan[kind]:
                reuse = kind == "trade" and month in plan["reuseObs"]
                man = obs if reuse else manifests[kind]
                folder = obs_dir(self.data_dir) / "raw" if reuse else self.data_dir / "raw" / kind
                if man is None:
                    missing.append({"kind": kind, "month": month, "reason": "manifest d'acquisizione assente"})
                    continue
                f = next((x for x in man.get("files", []) if x.get("month") == month), None)
                if f is None:
                    missing.append({"kind": kind, "month": month, "reason": "file non registrato"})
                    continue
                path = folder / f["file"]
                if not path.exists():
                    missing.append({"kind": kind, "month": month, "reason": "file assente sul disco"})
                elif f.get("size") is not None and path.stat().st_size != f["size"]:
                    missing.append({"kind": kind, "month": month, "reason": "dimensione diversa da quella registrata"})
        return {"available": not missing, "missing": missing,
                "files": {k: len(plan[k]) for k in ("trade", "funding", "mark")}, "reuseObs": len(plan["reuseObs"]),
                "tradeMonths": [plan["trade"][0], plan["trade"][-1]], "costMonths": [plan["funding"][0], plan["funding"][-1]]}
