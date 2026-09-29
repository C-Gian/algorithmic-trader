"""Deterministic synthetic BTC-perpetual bar stream (DEMO / SYNTHETIC).

The price path is a seeded integer random walk with scripted drift segments
so the demo chart looks coherent with the scripted dummy views. It is not
market data and carries no information about BTC.

Only integer arithmetic on ``random.Random`` is used, so the fixture is
bit-identical across platforms and Python builds.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from .contracts import DataQuality, InstrumentIdentity, MarketObservation

FIXTURE_ID = "synthetic-btc-perp-v1"
BAR_SECONDS = 60
TOTAL_BARS = 120
START_TIME = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
START_PRICE_TICKS = 600_000  # 60,000.0 in 0.1 ticks
TICK = Decimal("0.1")

# Bars with no data from the synthetic feed (exercises missing/stale state).
MISSING_BARS = frozenset({60, 61, 62})

# (first_bar, last_bar, drift in ticks per bar). Cosmetic only.
DRIFT_SEGMENTS = (
    (0, 9, 0),
    (10, 27, 300),
    (28, 39, 0),
    (40, 50, -350),
    (51, 79, 0),
    (80, 100, -250),
    (101, TOTAL_BARS - 1, 0),
)

SYNTHETIC_INSTRUMENT = InstrumentIdentity(
    instrument_id="SYNTH-BTC-USD-PERP",
    venue="SYNTHETIC",
    base_asset="BTC",
    quote_asset="USD",
    settlement_asset="USD",
    contract_multiplier=Decimal("1"),
    quantity_step=Decimal("0.001"),
    price_tick=TICK,
    synthetic=True,
)


@dataclass(frozen=True)
class Fixture:
    fixture_id: str
    seed: int
    instrument: InstrumentIdentity
    bars: tuple[MarketObservation, ...]

    @property
    def total_steps(self) -> int:
        return len(self.bars)

    def content_hash(self) -> str:
        payload = [b.model_dump(mode="json") for b in self.bars]
        blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(blob).hexdigest()

    def describe(self) -> dict:
        return {
            "fixture_id": self.fixture_id,
            "seed": self.seed,
            "bars": len(self.bars),
            "bar_seconds": BAR_SECONDS,
            "start_time": START_TIME.isoformat(),
            "missing_bars": sorted(MISSING_BARS),
            "content_sha256": self.content_hash(),
            "labels": ["DEMO", "SYNTHETIC"],
        }


def _drift(bar: int) -> int:
    for first, last, drift in DRIFT_SEGMENTS:
        if first <= bar <= last:
            return drift
    return 0


def _ticks(value: int) -> Decimal:
    return (Decimal(value) * TICK).quantize(TICK)


def build_fixture(fixture_id: str = FIXTURE_ID, seed: int = 20260929) -> Fixture:
    if fixture_id != FIXTURE_ID:
        raise ValueError(f"unknown fixture: {fixture_id}")
    rng = random.Random(seed)
    bars: list[MarketObservation] = []
    price = START_PRICE_TICKS
    for i in range(TOTAL_BARS):
        open_t = START_TIME + timedelta(seconds=BAR_SECONDS * i)
        close_t = open_t + timedelta(seconds=BAR_SECONDS)
        o = price
        c = o + _drift(i) + rng.randint(-150, 150)
        h = max(o, c) + rng.randint(0, 80)
        low = min(o, c) - rng.randint(0, 80)
        vol = rng.randint(50, 400)
        price = c
        obs_id = f"{fixture_id}:{i:04d}"
        if i in MISSING_BARS:
            bars.append(
                MarketObservation(
                    observation_id=obs_id,
                    instrument_id=SYNTHETIC_INSTRUMENT.instrument_id,
                    bar_index=i,
                    event_time=open_t,
                    available_time=close_t,
                    open=None,
                    high=None,
                    low=None,
                    close=None,
                    volume=None,
                    quality=DataQuality.MISSING,
                    source="SYNTHETIC",
                )
            )
            continue
        bars.append(
            MarketObservation(
                observation_id=obs_id,
                instrument_id=SYNTHETIC_INSTRUMENT.instrument_id,
                bar_index=i,
                event_time=open_t,
                available_time=close_t,
                open=_ticks(o),
                high=_ticks(h),
                low=_ticks(low),
                close=_ticks(c),
                volume=Decimal(vol),
                quality=DataQuality.OK,
                source="SYNTHETIC",
            )
        )
    return Fixture(fixture_id=fixture_id, seed=seed, instrument=SYNTHETIC_INSTRUMENT, bars=tuple(bars))
