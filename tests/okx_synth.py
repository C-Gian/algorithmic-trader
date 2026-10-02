"""Deterministic synthetic OKX rows for bounded engineering fixtures (derived, NOT market data).

Served through the same offline ``FakeOkx`` transport and accepted acquisition path, so the resulting
datasets are ordinary verified ``marketdata.v1`` packages. Prices are a deterministic saw-tooth; they are
used only to exercise structure (sizes, partitions, checkpoints, memory), never as market evidence.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from okx_fake import FakeOkx

from algotrader.marketdata.contracts import Family

MIN = timedelta(minutes=1)


def synthetic_fake(start: datetime, end: datetime, gap_every: int | None = 97) -> FakeOkx:
    fake = FakeOkx()
    trade, mark, index, funding = [], [], [], []
    t, i = start, 0
    while t < end:
        ms = int(t.timestamp() * 1000)
        if not (gap_every and i % gap_every == gap_every - 1):  # periodic missing slots (quality events)
            p = 80000 + (i * 37 % 1000) / 10
            o, h, lo, c = p, p + 5, p - 5, p + 1
            trade.append([str(ms), f"{o:.1f}", f"{h:.1f}", f"{lo:.1f}", f"{c:.1f}", "100", "1", "80000.5", "1"])
            mark.append([str(ms), f"{o:.1f}", f"{h:.1f}", f"{lo:.1f}", f"{c:.1f}", "1"])
            index.append([str(ms), f"{o + 40:.1f}", f"{h + 40:.1f}", f"{lo + 40:.1f}", f"{c + 40:.1f}", "1"])
        if ms % (8 * 3600 * 1000) == 0:
            funding.append({"formulaType": "withRate", "fundingRate": "0.0001", "fundingTime": str(ms),
                            "instId": "BTC-USDT-SWAP", "instType": "SWAP", "method": "current_period",
                            "realizedRate": "0.0001"})
        t += MIN
        i += 1
    fake.rows = {Family.TRADE_CANDLES: trade, Family.MARK_CANDLES: mark, Family.INDEX_CANDLES: index,
                 Family.FUNDING: funding}
    return fake
