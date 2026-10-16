"""Costruttori sintetici per i test OBS-001 (prezzi inventati, non BTC)."""

from __future__ import annotations

import random

from obs001.aggregate import COMPLETE, Bar
from obs001.conventions import MINUTE_MS, load_conventions
from obs001.minutes import MinuteStore

CONV = load_conventions()
BAR = CONV.bar_ms


def bar(i: int, o: float, h: float, l: float, c: float, v: float = 1.0, start: int | None = None, width: int = BAR) -> Bar:
    s = (CONV.input_start if start is None else start) + i * width
    return Bar(s, s + width, COMPLETE, width // MINUTE_MS, 0, 0, o=o, h=h, l=l, c=c, v=v, q=v * c, trades=1, tb=0.0, tq=0.0)


def linear_bars(n: int = 51) -> list[Bar]:
    """Esempio prefissato del task: C_i=100+i, O=C, H=C+1, L=C-1, V=i per i=1..n."""
    return [bar(i - 1, 100 + i, 101 + i, 99 + i, 100 + i, v=float(i)) for i in range(1, n + 1)]


def hl_bars(highs: list[float], lows: list[float]) -> list[Bar]:
    out = []
    for i, (h, l) in enumerate(zip(highs, lows)):
        mid = (h + l) / 2
        out.append(bar(i, mid, h, l, mid))
    return out


def fill_random_walk(store: MinuteStore, start: int, end: int, seed: int = 7, price: float = 100.0) -> None:
    rng = random.Random(seed)
    for t in range(start, end, MINUTE_MS):
        o = price
        c = max(1.0, o + rng.uniform(-0.5, 0.5))
        h = max(o, c) + rng.uniform(0, 0.3)
        l = max(0.5, min(o, c) - rng.uniform(0, 0.3))
        store.set_minute(store.index(t), (o, h, l, c, rng.uniform(0, 5), 0.0, rng.randint(0, 9), 0.0, 0.0))
        price = c


def full_store(seed: int = 7) -> MinuteStore:
    store = MinuteStore(CONV.input_start, CONV.end)
    fill_random_walk(store, CONV.input_start, CONV.end, seed)
    return store
