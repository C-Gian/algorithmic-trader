"""Checked-in JSON Schema baseline for the public semantic contracts.

The baseline for ``SCHEMA_VERSION`` lives at ``schemas/<SCHEMA_VERSION>.json``
and is generated deterministically from the Pydantic contracts. A regression
test compares the generated schema with the checked-in file, so accidental
contract drift fails CI.

A published baseline is frozen. An intentional breaking change bumps
``SCHEMA_VERSION`` (e.g. ``algotrader.semantic.v2``) and writes a new file;
the old file stays unchanged so older run manifests remain interpretable.
``write_baseline`` refuses to overwrite an existing baseline with different
content.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic.json_schema import models_json_schema

from . import contracts as c

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas"

# Public contracts exchanged between engine, worker, API and artifacts. The
# journal payload contracts are included through EVENT_KIND_CONTRACTS.
RECORD_CONTRACTS: tuple[type[c.Contract], ...] = (
    c.InstrumentIdentity,
    c.RunConfig,
    c.ReplayControl,
    c.Run,
    c.RunManifest,
    c.ArtifactRef,
)


def public_contracts() -> list[type[c.Contract]]:
    models = list(dict.fromkeys([*c.EVENT_KIND_CONTRACTS.values(), *RECORD_CONTRACTS]))
    return sorted(models, key=lambda m: m.__name__)


def baseline() -> dict[str, Any]:
    models = public_contracts()
    refs, schema = models_json_schema(
        [(m, "serialization") for m in models], ref_template="#/$defs/{model}"
    )
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": f"Algorithmic Trader semantic contracts ({c.SCHEMA_VERSION})",
        "schema_version": c.SCHEMA_VERSION,
        "journal_event_kinds": {
            kind: refs[(m, "serialization")]["$ref"] for kind, m in sorted(c.EVENT_KIND_CONTRACTS.items())
        },
        "public_contracts": {m.__name__: refs[(m, "serialization")]["$ref"] for m in models},
        "$defs": schema["$defs"],
    }


def render(doc: dict[str, Any]) -> str:
    return json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def baseline_path(version: str = c.SCHEMA_VERSION, schema_dir: Path = SCHEMA_DIR) -> Path:
    return schema_dir / f"{version}.json"


def write_baseline(schema_dir: Path = SCHEMA_DIR) -> Path:
    path = baseline_path(schema_dir=schema_dir)
    text = render(baseline())
    if path.exists() and path.read_text(encoding="utf-8") != text:
        raise SystemExit(
            f"{path.name} is a frozen baseline and differs from the current contracts. "
            "Revert the accidental change, or bump contracts.SCHEMA_VERSION for an intentional "
            "breaking change and write a new baseline."
        )
    schema_dir.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))
    return path
