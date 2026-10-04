"""Dispatch-level rig for the professional core (pure): explicit sealed 15m/1h records and minute bars at exact
barriers, so ordering rules can be asserted one dispatch at a time. Synthetic engineering inputs only."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from algotrader.adviser import contracts as sc
from algotrader.adviser.core import AdviserConfig, AdviserCore, Quote
from algotrader.adviser.harness import INDEX, MARK, TRADE, method_ref, ref_bar, trade_bar
from algotrader.adviser.identity import CapabilityProfile, historical_profile
from algotrader.adviser.params import load

D = Decimal
MIN = timedelta(minutes=1)
T0 = datetime(2025, 9, 1, tzinfo=UTC)


def rec(h: str, start: datetime, o, hi, lo, c, status: str = "COMPLETE", vol="1") -> dict:
    span = {"15m": timedelta(minutes=15), "1h": timedelta(hours=1), "4h": timedelta(hours=4),
            "1d": timedelta(days=1)}[h]
    end = start + span
    return {"channel": {"source": "okx", "family": "trade_bar_1m", "series_id": "BTC-USDT-SWAP"},
            "channel_id": TRADE.channel_id, "horizon": h, "status": status,
            "values": None if status != "COMPLETE" else {"open": str(o), "high": str(hi), "low": str(lo),
                                                         "close": str(c), "volume_base": str(vol)},
            "interval_start": start.isoformat(), "interval_end": end.isoformat(), "known_at": end.isoformat(),
            "record_id": f"{TRADE.channel_id}/{h}/{start.isoformat()}", "sealed_at": end.isoformat()}


class Rig:
    def __init__(self, profile: CapabilityProfile | None = None, eval_start=None, tick="0.1",
                 origin=sc.Origin.HISTORICAL_MODELED.value) -> None:
        profile = profile or historical_profile()
        self.cfg = AdviserConfig(instrument="BTC-USDT-SWAP", tick=D(tick), profile=profile, method=method_ref(profile),
                                 clock_policy="rig", params=load(), eval_start=eval_start, eval_end=None,
                                 origin=origin, channel_ids={"trade": TRADE.channel_id, "mark": MARK.channel_id,
                                                             "index": INDEX.channel_id})
        self.core = AdviserCore(self.cfg)
        self.t = T0
        self.cursor = 0
        self.journal: list[dict] = []
        self.m15: list[tuple] = []  # (start, o, h, l, c)

    # -- inputs ------------------------------------------------------------------------------------------------
    def _bar(self, start: datetime, o, h, lo, c, refs: bool = True) -> None:
        self.core.admit_event(trade_bar(start, o, h, lo, c), self.cursor)
        self.cursor += 1
        if refs:
            for ch in (MARK, INDEX):
                self.core.admit_event(ref_bar(ch, start, c, c, c, c), self.cursor)
                self.cursor += 1

    def dispatch(self, t: datetime) -> list[dict]:
        self.t = t
        out = self.core.dispatch(t)
        self.journal += out
        self.core.journal = []
        return out

    def minute(self, o, h, lo, c, at: datetime | None = None) -> list[dict]:
        """One complete 1m bar ending at the next minute (or ``at``) and its dispatch."""
        end = at or (self.t + MIN)
        self._bar(end - MIN, o, h, lo, c)
        return self.dispatch(end)

    def close15(self, o, h, lo, c, *, h1: tuple | None = None, extra: list[dict] | None = None,
                minute: tuple | None = None) -> list[dict]:
        """A complete 15m bar ending at the next 15m boundary, its last 1m bar (default o=h=l=c=close) and, at whole
        hours, the 1h record (``h1`` overrides the aggregate of the last four 15m bars)."""
        end = (self.t.replace(minute=self.t.minute - self.t.minute % 15, second=0) + timedelta(minutes=15))
        start = end - timedelta(minutes=15)
        self.m15.append((start, D(str(o)), D(str(h)), D(str(lo)), D(str(c))))
        m = minute or (c, c, c, c)
        self._bar(end - MIN, *m)
        self.core.admit_sealed(rec("15m", start, o, h, lo, c))
        if end.minute == 0:
            if h1 is None and len(self.m15) >= 4:
                last4 = self.m15[-4:]
                if last4[0][0] == end - timedelta(hours=1):
                    h1 = (last4[0][1], max(x[2] for x in last4), min(x[3] for x in last4), last4[-1][4])
            if h1 is not None:
                self.core.admit_sealed(rec("1h", end - timedelta(hours=1), *h1))
        for r in extra or []:
            self.core.admit_sealed(r)
        return self.dispatch(end)

    def quote(self, bid, ask, source_ts: datetime | None = None, received: datetime | None = None) -> None:
        self.core.admit_quote(Quote(D(str(bid)), D(str(ask)), source_ts or self.t, received or self.t,
                                    "BTC-USDT-SWAP", "q" * 64))

    # -- helpers -----------------------------------------------------------------------------------------------
    def seed_h1(self, bars: list[tuple]) -> None:
        """Pre-fill the 1h window with complete contiguous bars ending at the rig clock (derived context)."""
        start = self.t - len(bars) * timedelta(hours=1)
        for i, (o, h, lo, c) in enumerate(bars):
            self.core.admit_sealed(rec("1h", start + i * timedelta(hours=1), o, h, lo, c))

    def kinds(self, kind: str) -> list[dict]:
        return [e["record"] for e in self.journal if e["kind"] == kind]

    def candidates(self, aid_prefix: str = "") -> list[dict]:
        return [r for r in self.kinds("candidate") if r["attempt_id"].startswith(aid_prefix)]


def trend_h1(n: int, start=100000, step=60, rng=60) -> list[tuple]:
    """n contiguous 1h bars rising by ``step`` (TR = ``rng`` when |step| <= rng)."""
    out, p = [], D(start)
    for _ in range(n):
        o, c = p, p + step
        out.append((o, max(o, c) + (rng - abs(step)) / 2 if rng > abs(step) else max(o, c),
                    min(o, c) - (rng - abs(step)) / 2 if rng > abs(step) else min(o, c), c))
        p = c
    return out


def flat_h1(n: int, start=100000, rng=60) -> list[tuple]:
    """n balanced 1h bars alternating +/- half range (context BALANCED, S1h = rng)."""
    out, p = [], D(start)
    for i in range(n):
        c = p + (D(rng) if i % 2 == 0 else -D(rng))
        out.append((p, max(p, c), min(p, c), c))
        p = c
    return out
