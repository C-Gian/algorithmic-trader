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


# ---------------------------------------------------------------------------
# Market-data baseline (algotrader.marketdata.v1): separate from semantic v1
# ---------------------------------------------------------------------------


def test_marketdata_baseline_is_separate_and_matches_contracts():
    from algotrader.marketdata import contracts as md

    assert md.MARKETDATA_SCHEMA_VERSION == "algotrader.marketdata.v1" != c.SCHEMA_VERSION
    path = schema.baseline_path(md.MARKETDATA_SCHEMA_VERSION)
    assert path.is_file(), "run `uv run algotrader schema --write`"
    stored = json.loads(path.read_text(encoding="utf-8"))
    current = schema.marketdata_baseline()
    drifted = sorted(n for n in set(current["$defs"]) | set(stored["$defs"])
                     if current["$defs"].get(n) != stored["$defs"].get(n))
    assert not drifted, f"market-data contract drift in {drifted}: bump the market-data schema version"
    assert current == stored
    for name in ("InstrumentSnapshot", "TradeCandle1m", "MarkCandle1m", "IndexCandle1m", "FundingRateEvent",
                 "RawPageRef", "DatasetManifest", "QualityReport"):
        assert name in stored["public_contracts"]
    assert stored["availability_policy"]["id"] == md.AVAILABILITY_POLICY_ID
    # market-data records never leak into the frozen trader baseline
    assert not set(stored["public_contracts"]) & set(checked_in()["public_contracts"])


def test_marketdata_decimals_serialize_as_strings():
    defs = schema.marketdata_baseline()["$defs"]
    for field in ("open", "high", "low", "close", "volume_contracts", "volume_base", "volume_quote"):
        assert defs["TradeCandle1m"]["properties"][field]["type"] == "string"
    assert defs["FundingRateEvent"]["properties"]["funding_rate"]["type"] == "string"


def test_frozen_marketdata_baseline_cannot_be_overwritten(tmp_path):
    from algotrader.marketdata.contracts import MARKETDATA_SCHEMA_VERSION

    (tmp_path / f"{MARKETDATA_SCHEMA_VERSION}.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="frozen baseline"):
        schema.write_baseline(tmp_path, MARKETDATA_SCHEMA_VERSION)


def test_semantic_v1_baseline_file_is_unchanged_by_marketdata():
    import hashlib

    # sha256 of schemas/algotrader.semantic.v1.json as accepted with WP-002 (LF line endings)
    text = schema.baseline_path().read_text(encoding="utf-8")
    assert hashlib.sha256(text.encode()).hexdigest() == SEMANTIC_V1_SHA256


SEMANTIC_V1_SHA256 = "7e212b948ef0d756628b9db2da4b923aace3d8d25532dc48d58b8b10ce4e0c09"
