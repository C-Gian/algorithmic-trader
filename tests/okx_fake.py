"""Offline stand-in for the OKX public REST API.

Serves the captured fixture rows (tests/fixtures/okx, see PROVENANCE.json)
through the *same* ``OkxPublicClient`` and parsers used for live access. It
emulates the verified OKX paging semantics: ``after``/``before`` are
exclusive bounds, results are newest first, at most ``limit`` rows.

Scenario variants (gaps, duplicates, out-of-order pages, invalid values,
errors) are produced by mutating the served rows and are labelled "derived"
in the tests that use them.
"""

from __future__ import annotations

import copy
import json
import urllib.parse
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from algotrader.marketdata.contracts import Family
from algotrader.marketdata.okx import ENDPOINTS, OkxPublicClient

FIXTURES = Path(__file__).parent / "fixtures" / "okx"
FIXTURE_START = datetime(2026, 9, 30, 7, 50, tzinfo=UTC)
CONFIRMED_END = datetime(2026, 9, 30, 8, 9, tzinfo=UTC)  # bars 07:50..08:08 are confirm=1
FIXTURE_END = datetime(2026, 9, 30, 8, 10, tzinfo=UTC)  # the 08:09 bar is confirm=0 (captured live)
NOW = datetime(2026, 9, 30, 9, 0, tzinfo=UTC)

PATH_FAMILY = {v: k for k, v in ENDPOINTS.items()}
SOURCE_IDS = {Family.TRADE_CANDLES: "BTC-USDT-SWAP", Family.MARK_CANDLES: "BTC-USDT-SWAP",
              Family.INDEX_CANDLES: "BTC-USDT", Family.FUNDING: "BTC-USDT-SWAP"}


def fixture_bytes(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def fixture_data(name: str) -> list[Any]:
    return json.loads(fixture_bytes(name))["data"]


def row_key(row: Any) -> int:
    return int(row["fundingTime"]) if isinstance(row, dict) else int(row[0])


def envelope(data: list[Any], code: str = "0", msg: str = "") -> bytes:
    return json.dumps({"code": code, "data": data, "msg": msg}, separators=(",", ":")).encode()


class FakeOkx:
    def __init__(self) -> None:
        self.instrument_body = fixture_bytes("instrument.json")
        self.rows: dict[Family, list[Any]] = {
            f: fixture_data(f"{f.value}.json") for f in SOURCE_IDS
        }
        self.calls: list[tuple[str, dict[str, str], dict[str, str]]] = []
        self.queued: list[tuple[int, bytes]] = []  # responses returned before normal service
        self.page_hook: Callable[[Family, list[Any]], list[Any]] | None = None

    def mutate(self, family: Family, fn: Callable[[list[Any]], list[Any]]) -> FakeOkx:
        self.rows[family] = fn(copy.deepcopy(self.rows[family]))
        return self

    def __call__(self, url: str, headers: dict[str, str], timeout: float) -> tuple[int, bytes]:
        parts = urllib.parse.urlsplit(url)
        params = dict(urllib.parse.parse_qsl(parts.query))
        self.calls.append((parts.path, params, headers))
        if self.queued:
            return self.queued.pop(0)
        family = PATH_FAMILY[parts.path]
        if family == Family.INSTRUMENT:
            return 200, self.instrument_body
        if params.get("instId") != SOURCE_IDS[family]:
            return 200, envelope([], "51001", "Instrument ID, Instrument ID code, or Spread ID doesn't exist.")
        after = int(params.get("after", 2**62))
        before = int(params.get("before", -1))
        limit = int(params.get("limit", 100))
        rows = [r for r in self.rows[family] if before < row_key(r) < after]
        rows.sort(key=row_key, reverse=True)
        page = rows[:limit]
        if self.page_hook:
            page = self.page_hook(family, page)
        return 200, envelope(page)


class FixedClock:
    def __init__(self, now: datetime = NOW) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


def client(fake: FakeOkx, **kw) -> OkxPublicClient:
    kw.setdefault("clock", FixedClock())
    return OkxPublicClient(transport=fake, sleep=lambda s: None, min_interval=0, **kw)
