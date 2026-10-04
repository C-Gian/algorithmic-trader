"""Hand-designed synthetic minute paths for the adviser fixtures (engineering inputs, NOT market data).

Each fixture is built from explicit piecewise-linear minute closes so every 15m/1h aggregate, scale, zone, trigger
and target can be recomputed by hand in the tests. ``mirror`` reflects a LONG fixture about a pivot price
(P -> 2*pivot - P, high <-> low) to obtain the SHORT fixture; MP-001 defines SHORT as exactly that reflection.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from algotrader.adviser.harness import Minute

D = Decimal
MIN = timedelta(minutes=1)
DAY1 = datetime(2025, 8, 31, tzinfo=UTC)  # Sunday: day 1 completes at 2025-09-01 00:00 (previous-day landmark)
DAY2 = DAY1 + timedelta(days=1)
P0 = D(100000)


class Path:
    """Minute closes with optional per-minute wicks; minute open = previous close."""

    def __init__(self, start_price: Decimal = P0) -> None:
        self.closes: list[Decimal] = []
        self.wick_hi: list[Decimal] = []
        self.wick_lo: list[Decimal] = []
        self.gaps: set[int] = set()
        self.last = start_price
        self.first_open = start_price

    def __len__(self) -> int:
        return len(self.closes)

    def step(self, n: int, delta, wick_hi=0, wick_lo=0) -> "Path":
        for _ in range(n):
            self.last = self.last + D(str(delta))
            self.closes.append(self.last)
            self.wick_hi.append(D(str(wick_hi)))
            self.wick_lo.append(D(str(wick_lo)))
        return self

    def to(self, price, n: int) -> "Path":
        """Linear move to ``price`` over n minutes (exact decimal steps)."""
        price = D(str(price))
        delta = (price - self.last) / n
        for i in range(n):
            self.last = self.last + delta if i < n - 1 else price
            self.closes.append(self.last)
            self.wick_hi.append(D(0))
            self.wick_lo.append(D(0))
        return self

    def wick(self, idx: int, hi=0, lo=0) -> "Path":
        self.wick_hi[idx] = D(str(hi))
        self.wick_lo[idx] = D(str(lo))
        return self

    def oscillate(self, hours: int, amp=60) -> "Path":
        for h in range(hours):
            self.step(60, D(amp) / 60 if h % 2 == 0 else -D(amp) / 60)
        return self

    def minutes(self) -> list[Minute]:
        out = []
        o = self.first_open
        for i, c in enumerate(self.closes):
            h = max(o, c) + self.wick_hi[i]
            lo = min(o, c) - self.wick_lo[i]
            out.append(Minute(o, h, lo, c, gap=i in self.gaps))
            o = c
        return out


def mirror(minutes: list[Minute], pivot: Decimal = P0) -> list[Minute]:
    out = []
    for m in minutes:
        f = lambda x: 2 * pivot - x  # noqa: E731
        out.append(Minute(f(m.o), f(m.lo), f(m.h), f(m.c), gap=m.gap,
                          mark=None if m.mark is None else f(m.mark), index=None if m.index is None else f(m.index),
                          vol=m.vol))
    return out


def agg(minutes: list[Minute], start: int, n: int) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    seg = minutes[start:start + n]
    return seg[0].o, max(m.h for m in seg), min(m.lo for m in seg), seg[-1].c


def bars15(p: Path, closes) -> Path:
    """Append 15m bars, each a linear 15-minute move to the given close (offsets from P0)."""
    for c in closes:
        p.to(P0 + D(str(c)), 15)
    return p


def box_warmup(p: Path) -> Path:
    """~26h of a 6-bar 15m oscillation 0..1800 (TR 600, balanced 1h context), ending at the bottom (P0)."""
    for _ in range(18):
        bars15(p, [600, 1200, 1800, 1200, 600, 0])
    return p


def box_fixture(kind: str) -> list[Minute]:
    """Compression box [P0, P0+1800] born after small (TR 200) bars; then:
    B: break close 1900, retest (low 1780, close 1850), trigger 1860, rally;
    C: failed exit (low -70, close 100), trigger 110, drift;
    B_RETURN: break close 1900, then a bar wicking below L-z that closes back inside at 100 (B_LONG cancelled, box
    kept, C_LONG born from the same frozen edges);
    B_OPPOSITE: break close 1900, then a close at -100 < L-z (B_LONG cancelled AND box retired atomically)."""
    p = Path()
    box_warmup(p)
    bars15(p, [600, 800, 600, 800, 600])  # up-leg then small bars: compression (CR ~ 1/3), ER6 low
    if kind == "B":
        p.to(P0 + 1900, 15)                      # break: close 1900 > U + z (1860)
        p.to(P0 + 1780, 10).to(P0 + 1850, 5)     # retest: low 1780 in [1740, 1860], close 1850 > U
        p.to(P0 + 1860, 1)                       # trigger minute: close 1860 >= K + tick, low > V (1720)
        p.step(240, 10)                          # post-issue rally
    elif kind == "C":
        p.to(P0 - 70, 10).to(P0 + 100, 5)        # failed exit: low -70 < L - z, close 100 in (L+z, M)
        p.to(P0 + 110, 1)                        # trigger minute: close 110 >= K + tick, low > V (-130)
        p.step(120, 5)                           # post-issue drift toward the midpoint
    elif kind == "B_RETURN":
        p.to(P0 + 1900, 15)                      # break: B_LONG attempt born
        p.to(P0 + 1500, 15)                      # returns inside: close 1500 < U - z cancels B_LONG; box kept
        p.to(P0 - 70, 10).to(P0 + 100, 5)        # failed exit below L - z with high 1500 < U + z: C_LONG born
        p.to(P0 + 110, 1)
        p.step(60, 5)
    elif kind == "B_OPPOSITE":
        p.to(P0 + 1900, 15)
        p.to(P0 - 100, 15)                       # close -100 < L - z during the existing B_LONG attempt
    for i in range(400):
        p.step(1, D(5) if i % 2 == 0 else D(-5))
    return p.minutes()


def a_fixture(spike=800, after_arm: str = "trigger", after_issue: str = "rally") -> list[Minute]:
    """A_LONG continuation: balanced warmup with a day-1 spike high (P0+spike), a 4h trend, reaction, trigger.

    after_arm: "trigger" (rally to P0+242 at [05:20,05:21)) | "fade" (no trigger: drift down, episode deadline).
    after_issue: "rally" (+3/min through the target) | "stop" (falls through V=P0+226.5) | "stall" (flat at the
    reference: half-horizon STALLED) | "progress" (closes reach +9 = 0.6*S15, then back to the reference: not stalled)
    | "wick" (only an intrabar high reaches +9, closes stay below +7.5: STALLED)."""
    p = Path()
    p.oscillate(2)                                 # day1 00:00-02:00
    p.to(P0 + spike, 30).to(P0, 30)                # 02:00-03:00 spike: 1h pivot high / previous-day high
    p.oscillate(21)                                # 03:00-24:00 -> P0+60
    p.step(60, -1)                                 # day2 00:00-01:00 -> P0
    p.step(240, 1)                                 # 01:00-05:00 trend -> P0+240 (context UP from 05:00)
    p.step(12, -1).step(1, 1).step(2, D("0.5"))   # 05:00-05:15 reaction: low P0+228, close P0+230
    if after_arm == "fade":
        for i in range(800):
            p.step(1, D("0.5") if i % 2 == 0 else D("-0.5"))
        return p.minutes()
    p.step(6, 2)                                   # 05:15-05:21: trigger minute [05:20,05:21) close P0+242
    if after_issue == "rally":
        p.step(188, 3)
    elif after_issue == "stop":
        p.step(10, -2)                             # 242 -> 222: the minute reaching 226 touches V=226.5
    elif after_issue in ("stall", "progress", "wick"):
        if after_issue == "progress":
            p.step(9, 1).step(9, -1)               # a close at +9 then back to the reference
        for i in range(400):
            p.step(1, D("0.5") if i % 2 == 0 else D("-0.5"))
            if after_issue == "wick" and i == 30:
                p.wick(len(p) - 1, hi=9)            # intrabar high only
    for i in range(500):
        p.step(1, D("0.5") if i % 2 == 0 else D("-0.5"))
    return p.minutes()
