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

The market-data records (``algotrader.marketdata.v1``) have their own,
independently versioned baseline file written by the same mechanism.

The causal feed contracts (``algotrader.feed.v1``) are PROVISIONAL during M3:
their baseline carries a revision number and may be rewritten only when the
revision is bumped (with a changelog entry), never silently.
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


def marketdata_baseline() -> dict[str, Any]:
    """Separate baseline for the market-data records (``algotrader.marketdata.v1``)."""
    from .marketdata import contracts as md

    models = sorted(md.RECORD_CONTRACTS, key=lambda m: m.__name__)
    refs, schema = models_json_schema(
        [(m, "serialization") for m in models], ref_template="#/$defs/{model}"
    )
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": f"Algorithmic Trader market-data contracts ({md.MARKETDATA_SCHEMA_VERSION})",
        "schema_version": md.MARKETDATA_SCHEMA_VERSION,
        "availability_policy": {"id": md.AVAILABILITY_POLICY_ID, "text": md.AVAILABILITY_POLICY_TEXT},
        "public_contracts": {m.__name__: refs[(m, "serialization")]["$ref"] for m in models},
        "$defs": schema["$defs"],
    }


def feed_baseline() -> dict[str, Any]:
    """PROVISIONAL baseline for the causal feed/observable state (``algotrader.feed.v1``)."""
    from .feed import contracts as fd

    models = sorted(fd.PUBLIC_CONTRACTS, key=lambda m: m.__name__)
    refs, schema = models_json_schema(
        [(m, "serialization") for m in models], ref_template="#/$defs/{model}"
    )
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": f"Algorithmic Trader causal feed contracts ({fd.FEED_SCHEMA_VERSION}, {fd.FEED_CONTRACT_STATUS})",
        "schema_version": fd.FEED_SCHEMA_VERSION,
        "status": fd.FEED_CONTRACT_STATUS,
        "revision": fd.FEED_SCHEMA_REVISION,
        "changelog": [{"revision": r, "date": d, "note": n} for r, d, n in fd.FEED_CHANGELOG],
        "ordering_policy": {"id": fd.ORDERING_POLICY_ID, "text": fd.ORDERING_POLICY_TEXT},
        "public_contracts": {m.__name__: refs[(m, "serialization")]["$ref"] for m in models},
        "$defs": schema["$defs"],
    }


def recorder_baseline() -> dict[str, Any]:
    """PROVISIONAL baseline for public recorder sessions (``algotrader.recorder.v1``)."""
    from .recorder import contracts as rc

    models = sorted(rc.PUBLIC_CONTRACTS, key=lambda m: m.__name__)
    refs, schema = models_json_schema(
        [(m, "serialization") for m in models], ref_template="#/$defs/{model}"
    )
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": f"Algorithmic Trader public recorder contracts ({rc.RECORDER_SCHEMA_VERSION}, "
                 f"{rc.RECORDER_CONTRACT_STATUS})",
        "schema_version": rc.RECORDER_SCHEMA_VERSION,
        "status": rc.RECORDER_CONTRACT_STATUS,
        "revision": rc.RECORDER_SCHEMA_REVISION,
        "changelog": [{"revision": r, "date": d, "note": n} for r, d, n in rc.RECORDER_CHANGELOG],
        "clock_source": rc.CLOCK_SOURCE,
        "receipt_point": rc.RECEIPT_POINT,
        "public_contracts": {m.__name__: refs[(m, "serialization")]["$ref"] for m in models},
        "$defs": schema["$defs"],
    }


def observe_baseline() -> dict[str, Any]:
    """PROVISIONAL baseline for real-market observation replay (``algotrader.observe.v1``)."""
    from .observe import contracts as oc

    models = sorted(oc.PUBLIC_CONTRACTS, key=lambda m: m.__name__)
    refs, schema = models_json_schema(
        [(m, "serialization") for m in models], ref_template="#/$defs/{model}"
    )
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": f"Algorithmic Trader observation-replay contracts ({oc.OBSERVE_SCHEMA_VERSION}, "
                 f"{oc.OBSERVE_CONTRACT_STATUS})",
        "schema_version": oc.OBSERVE_SCHEMA_VERSION,
        "status": oc.OBSERVE_CONTRACT_STATUS,
        "revision": oc.OBSERVE_SCHEMA_REVISION,
        "changelog": [{"revision": r, "date": d, "note": n} for r, d, n in oc.OBSERVE_CHANGELOG],
        "clock_policy": oc.CLOCK_POLICY,
        "labels": list(oc.LABELS),
        "public_contracts": {m.__name__: refs[(m, "serialization")]["$ref"] for m in models},
        "$defs": schema["$defs"],
    }


def temporal_baseline() -> dict[str, Any]:
    """PROVISIONAL baseline for the causal temporal substrate (``algotrader.temporal.v1``)."""
    from .temporal import contracts as tc

    models = sorted(tc.PUBLIC_CONTRACTS, key=lambda m: m.__name__)
    refs, schema = models_json_schema(
        [(m, "serialization") for m in models], ref_template="#/$defs/{model}"
    )
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": f"Algorithmic Trader causal temporal substrate contracts ({tc.TEMPORAL_SCHEMA_VERSION}, "
                 f"{tc.TEMPORAL_CONTRACT_STATUS})",
        "schema_version": tc.TEMPORAL_SCHEMA_VERSION,
        "status": tc.TEMPORAL_CONTRACT_STATUS,
        "revision": tc.TEMPORAL_SCHEMA_REVISION,
        "changelog": [{"revision": r, "date": d, "note": n} for r, d, n in tc.TEMPORAL_CHANGELOG],
        "profile_id": tc.PROFILE_ID,
        "seal_policy": {"id": tc.SEAL_POLICY_ID, "text": tc.SEAL_POLICY_TEXT},
        "clock_policies": {k.value: v for k, v in sorted(tc.CLOCK_POLICY_TEXT.items())},
        "horizon_roles": {h.value: tc.HORIZON_ROLE[h] for h in tc.HORIZON_ORDER},
        "readiness_precedence": [x.value for x in tc.READINESS_PRECEDENCE],
        "public_contracts": {m.__name__: refs[(m, "serialization")]["$ref"] for m in models},
        "$defs": schema["$defs"],
    }


def pack_baseline() -> dict[str, Any]:
    """PROVISIONAL baseline for evaluation packs (``algotrader.corpus-pack.v1``) and the presets file format."""
    from .corpus import pack_contracts as pc
    from .corpus import presets as pr

    models = sorted([*pc.PUBLIC_CONTRACTS, pr.PresetsFile, pr.Preset, pr.Window, pr.Protected],
                    key=lambda m: m.__name__)
    refs, schema = models_json_schema(
        [(m, "serialization") for m in models], ref_template="#/$defs/{model}"
    )
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": f"Algorithmic Trader evaluation pack contracts ({pc.PACK_SCHEMA_VERSION}, {pc.PACK_CONTRACT_STATUS})",
        "schema_version": pc.PACK_SCHEMA_VERSION,
        "status": pc.PACK_CONTRACT_STATUS,
        "revision": pc.PACK_SCHEMA_REVISION,
        "changelog": [{"revision": r, "date": d, "note": n} for r, d, n in pc.PACK_CHANGELOG],
        "presets_schema_version": pr.PRESETS_SCHEMA_VERSION,
        "composition_policy": {"id": pc.COMPOSITION_POLICY, "text": pc.COMPOSITION_POLICY_TEXT},
        "slice_policy": pc.SLICE_POLICY,
        "metadata_policy": pc.METADATA_POLICY,
        "public_contracts": {m.__name__: refs[(m, "serialization")]["$ref"] for m in models},
        "$defs": schema["$defs"],
    }


def baselines() -> dict[str, Any]:
    """Every current contract baseline, keyed by schema version."""
    from .feed.contracts import FEED_SCHEMA_VERSION
    from .marketdata.contracts import MARKETDATA_SCHEMA_VERSION
    from .observe.contracts import OBSERVE_SCHEMA_VERSION
    from .recorder.contracts import RECORDER_SCHEMA_VERSION
    from .corpus.pack_contracts import PACK_SCHEMA_VERSION
    from .temporal.contracts import TEMPORAL_SCHEMA_VERSION

    return {
        c.SCHEMA_VERSION: baseline,
        MARKETDATA_SCHEMA_VERSION: marketdata_baseline,
        FEED_SCHEMA_VERSION: feed_baseline,
        RECORDER_SCHEMA_VERSION: recorder_baseline,
        OBSERVE_SCHEMA_VERSION: observe_baseline,
        TEMPORAL_SCHEMA_VERSION: temporal_baseline,
        PACK_SCHEMA_VERSION: pack_baseline,
    }


def _provisional_revision(text: str) -> int | None:
    try:
        doc = json.loads(text)
    except ValueError:
        return None
    return doc.get("revision") if doc.get("status") == "PROVISIONAL" else None


def render(doc: dict[str, Any]) -> str:
    return json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def baseline_path(version: str = c.SCHEMA_VERSION, schema_dir: Path = SCHEMA_DIR) -> Path:
    return schema_dir / f"{version}.json"


def write_baseline(schema_dir: Path = SCHEMA_DIR, version: str = c.SCHEMA_VERSION) -> Path:
    path = baseline_path(version, schema_dir)
    text = render(baselines()[version]())
    if path.exists() and path.read_text(encoding="utf-8") != text:
        # A PROVISIONAL baseline may be rewritten only with a revision bump (and changelog entry).
        old_rev, new_rev = _provisional_revision(path.read_text(encoding="utf-8")), _provisional_revision(text)
        if old_rev is not None and new_rev is not None and new_rev > old_rev:
            path.write_bytes(text.encode("utf-8"))
            return path
        if old_rev is not None:
            raise SystemExit(
                f"{path.name} is a PROVISIONAL baseline at revision {old_rev}; a contract change requires "
                "bumping its revision, adding a changelog entry and Director approval."
            )
        raise SystemExit(
            f"{path.name} is a frozen baseline and differs from the current contracts. "
            "Revert the accidental change, or bump the schema version for an intentional "
            "breaking change and write a new baseline."
        )
    schema_dir.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))
    return path
