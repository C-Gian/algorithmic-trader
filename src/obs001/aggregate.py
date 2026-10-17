"""Barre 45m (32 al giorno, ancorate a 00:00 UTC) e 1D [00:00, 00:00) UTC dagli stessi minuti.

Una barra è COMPLETE solo se tutti i minuti attesi sono VALID; altrimenti INCOMPLETE con i
conteggi, senza OHLC definitivo ricavato da una copertura parziale.
"""

from __future__ import annotations

from dataclasses import dataclass

from .conventions import MINUTE_MS
from .minutes import INVALID, MISSING, VALID, MinuteStore

COMPLETE, INCOMPLETE = "COMPLETE", "INCOMPLETE"


@dataclass(frozen=True)
class Bar:
    start: int
    end: int
    status: str
    valid: int
    missing: int
    invalid: int
    o: float | None = None
    h: float | None = None
    l: float | None = None
    c: float | None = None
    v: float | None = None
    q: float | None = None
    trades: int | None = None
    tb: float | None = None
    tq: float | None = None

    @property
    def complete(self) -> bool:
        return self.status == COMPLETE


TICK_BARS = 1_000


def aggregate(store: MinuteStore, width_ms: int, start: int | None = None, end: int | None = None, tick=None) -> list[Bar]:
    """tick(done, total) facoltativo ogni TICK_BARS barre: solo avanzamento/annullamento."""
    start = store.start if start is None else start
    end = store.end if end is None else end
    if width_ms % MINUTE_MS or (end - start) % width_ms:
        raise ValueError("ampiezza o intervallo non allineati")
    per_bar = width_ms // MINUTE_MS
    bars: list[Bar] = []
    total = (end - start) // width_ms
    for b_start in range(start, end, width_ms):
        if tick is not None and len(bars) % TICK_BARS == 0:
            tick(len(bars), total)
        i0 = store.index(b_start)
        seg = store.status[i0:i0 + per_bar]
        valid, missing, invalid = seg.count(VALID), seg.count(MISSING), seg.count(INVALID)
        if valid != per_bar:
            bars.append(Bar(b_start, b_start + width_ms, INCOMPLETE, valid, missing, invalid))
            continue
        i1 = i0 + per_bar
        bars.append(
            Bar(
                b_start, b_start + width_ms, COMPLETE, valid, missing, invalid,
                o=store.o[i0], h=max(store.h[i0:i1]), l=min(store.l[i0:i1]), c=store.c[i1 - 1],
                v=sum(store.v[i0:i1]), q=sum(store.q[i0:i1]), trades=sum(store.trades[i0:i1]),
                tb=sum(store.tb[i0:i1]), tq=sum(store.tq[i0:i1]),
            )
        )
    return bars
