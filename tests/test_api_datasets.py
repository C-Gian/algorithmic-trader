"""Read-only dataset inspection API over a fixture-derived dataset (no DB, no network)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from okx_fake import CONFIRMED_END, FIXTURE_END, FIXTURE_START, FakeOkx, client

from algotrader.api import create_app
from algotrader.marketdata.dataset import acquire


@pytest.fixture
def data_root(tmp_path):
    root = tmp_path / "data"
    acquire(client(FakeOkx()), root, FIXTURE_START, CONFIRMED_END)
    acquire(client(FakeOkx()), root, FIXTURE_START, FIXTURE_END)
    return root


@pytest.fixture
def api(data_root, tmp_path):
    app = create_app("postgresql://unused", tmp_path / "artifacts", web_dist=tmp_path / "no-ui", data_root=data_root)
    return TestClient(app)


def test_list_datasets_summarizes_coverage_quality_and_provenance(api, data_root):
    body = api.get("/api/datasets").json()
    assert body["schema_version"] == "algotrader.marketdata.v1" and body["data_root"] == str(data_root)
    by_end = {d["requested"]["end"]: d for d in body["datasets"]}
    clean, degraded = by_end["2026-09-30T08:09:00+00:00"], by_end["2026-09-30T08:10:00+00:00"]
    assert (clean["source"], clean["inst_id"], clean["base_url"]) == ("okx", "BTC-USDT-SWAP", "https://www.okx.com")
    assert clean["quality_status"] == "clean" and degraded["quality_status"] == "degraded"
    fams = {f["family"]: f for f in degraded["families"]}
    assert fams["trade_candles_1m"]["rows"] == 19 and fams["trade_candles_1m"]["gaps"] == 1
    assert fams["trade_candles_1m"]["missing_rows"] == 1 and fams["funding_rates"]["rows"] == 1
    assert clean["retrieved_at"].startswith("2026-09-30T09:00")


def test_dataset_detail_verify_and_files(api):
    ds = api.get("/api/datasets").json()["datasets"][0]["dataset_id"]
    detail = api.get(f"/api/datasets/{ds}").json()
    assert detail["manifest"]["dataset_id"] == ds and detail["quality"]["dataset_id"] == ds
    assert detail["manifest"]["instrument"]["ct_val"] == "0.01"
    assert api.get(f"/api/datasets/{ds}/verify").json() == {"dataset_id": ds, "ok": True, "problems": []}
    names = [f["name"] for f in detail["manifest"]["files"]]
    for name in ("manifest.json", "quality.json", "request_log.jsonl", "raw/instrument/0000.json"):
        r = api.get(f"/api/datasets/{ds}/files/{name}")
        assert r.status_code == 200 and (name == "manifest.json" or name in names)
    assert api.get(f"/api/datasets/{ds}/files/../../secret").status_code == 404
    assert api.get("/api/datasets/nope").status_code == 404
    assert api.get("/api/datasets/..%2F..").status_code == 404


def test_empty_data_root(tmp_path):
    app = create_app("postgresql://unused", tmp_path / "a", web_dist=tmp_path / "no-ui", data_root=tmp_path / "none")
    assert TestClient(app).get("/api/datasets").json()["datasets"] == []
