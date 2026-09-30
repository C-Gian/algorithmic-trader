"""Semantic contract baseline: the checked-in JSON Schema must match the code.

If a test here fails you changed a public contract. Revert the accidental
change; for an intentional breaking change bump ``contracts.SCHEMA_VERSION``
and run ``uv run algotrader schema --write`` to add a new baseline file. The
existing baseline file is frozen and must not be edited.
"""

from __future__ import annotations

import json

import pytest

from algotrader import contracts as c
from algotrader import schema
from algotrader.engine import Engine
from algotrader.synthetic import build_fixture


def checked_in() -> dict:
    path = schema.baseline_path()
    assert path.is_file(), f"missing baseline {path}; run `uv run algotrader schema --write`"
    return json.loads(path.read_text(encoding="utf-8"))


def test_version_is_product_level():
    assert c.SCHEMA_VERSION == "algotrader.semantic.v1"
    assert "wp0" not in c.SCHEMA_VERSION


def test_checked_in_baseline_matches_contracts():
    current = schema.baseline()
    stored = checked_in()
    assert stored["schema_version"] == c.SCHEMA_VERSION
    drifted = sorted(
        name for name in set(current["$defs"]) | set(stored["$defs"])
        if current["$defs"].get(name) != stored["$defs"].get(name)
    )
    assert not drifted, (
        f"semantic contract drift in {drifted}: revert, or bump SCHEMA_VERSION and write a new baseline"
    )
    assert current == stored


def test_baseline_rendering_is_deterministic():
    assert schema.render(schema.baseline()) == schema.render(schema.baseline())
    assert schema.baseline_path().read_text(encoding="utf-8") == schema.render(schema.baseline())


def test_baseline_covers_every_journal_kind_and_public_record():
    stored = checked_in()
    assert set(stored["journal_event_kinds"]) == set(c.EVENT_KIND_CONTRACTS)
    for name in ("Run", "RunConfig", "ReplayControl", "RunManifest", "MarketView", "Decision", "Fill"):
        assert stored["public_contracts"][name] == f"#/$defs/{name}"
    # speed is operational control, never a pinned semantic input
    assert "speed" not in stored["$defs"]["RunConfig"]["properties"]
    assert "speed" in stored["$defs"]["ReplayControl"]["properties"]
    assert "schema_version" in stored["$defs"]["RunManifest"]["required"]


def test_engine_payloads_fit_the_baseline_shape():
    """Journal payloads use exactly the properties the baseline declares."""
    defs = checked_in()["$defs"]
    kinds = checked_in()["journal_event_kinds"]
    _, events = Engine(build_fixture()).run_all()
    for ev in events:
        d = defs[kinds[ev.kind].split("/")[-1]]
        assert set(ev.payload) <= set(d["properties"]), ev.kind
        assert set(d.get("required", [])) <= set(ev.payload), ev.kind


def test_frozen_baseline_cannot_be_overwritten(tmp_path, monkeypatch):
    frozen = tmp_path / f"{c.SCHEMA_VERSION}.json"
    frozen.write_text('{"tampered": true}\n', encoding="utf-8")
    with pytest.raises(SystemExit, match="frozen baseline"):
        schema.write_baseline(tmp_path)
    assert frozen.read_text(encoding="utf-8") == '{"tampered": true}\n'
    other = tmp_path / "fresh"
    assert schema.write_baseline(other).read_text(encoding="utf-8") == schema.render(schema.baseline())
