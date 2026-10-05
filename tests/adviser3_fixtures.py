"""Hand-designed synthetic paths for the MP-002 v0.3 fixtures (engineering inputs, NOT market data).

The base A LONG path reproduces the MP-002 §9 numbers exactly (tick 0.1, historical K_cost 14 bps, r 1.2):

* day 1 + day 2 to 02:00: 15m bars alternating 97000->99000->97000 (every TR 2000, 1h context BALANCED, no strict
  pivot);
* impulse 02:00-03:30: six bars of +650 (the last o 100250 h 100900 l 100250 c 100700): Q_A true at 03:30
  (ER6 1, displacement 1.85 S15) -> A birth, impulse A 97000, B 100900, S15 2000, z 200 (14 of the last 20 TRs are
  2000);
* reaction: bar [03:30,03:45) o 100700 h 100700 l 100000 c 100049.9 -> ARM at 03:45 (K 100700, V 99800); bar
  [03:45,04:00) o 100049.9 h 100049.9 l 99900 c 99950 -> REVISE at 04:00: R 99900, K_trigger 100049.9, V 99700;
* confirmation minute [04:00,04:01): o 99950 h 100050 l 99950 c 100050 -> CONFIRM at 04:01. T = own impulse-B zone
  near edge 100900-200 = 100700; immediate at 100050 fails REWARD_RISK_BELOW_MINIMUM (G 64.97, Q 34.98: ratio 1.04);
  corridor [99900, 100049.9]; economic upper bound (100700+1.2*99700)/(2.2*1.0014) = 100014.525... -> inward 100014.5:
  WAIT_PRICE.

``post`` lists the explicit minute OHLC after the confirmation minute (from 04:01); the tail drifts flat. ``mirror``
(about 100000) gives the positive-price SHORT fixture whose economics must be computed separately.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from algotrader.adviser.harness import Minute

D = Decimal
MIN = timedelta(minutes=1)
DAY1 = datetime(2025, 8, 31, tzinfo=UTC)
DAY2 = DAY1 + timedelta(days=1)
LOW, HIGH = D(97000), D(99000)


def T(h: int, m: int = 0) -> datetime:
    return DAY2 + timedelta(hours=h, minutes=m)


def bar15(o, h, lo, c, order: str = "HL") -> list[Minute]:
    """15 minutes whose aggregate is exactly (o, h, lo, c): o -> first extreme (5 min) -> second (5) -> c (5)."""
    o, h, lo, c = D(str(o)), D(str(h)), D(str(lo)), D(str(c))
    pts = [h, lo] if order == "HL" else [lo, h]
    path: list[Decimal] = []
    cur = o
    for target in pts + [c]:
        step = (target - cur) / 5
        for i in range(5):
            cur = cur + step if i < 4 else target
            path.append(cur)
    out, prev = [], o
    for x in path:
        out.append(Minute(prev, max(prev, x), min(prev, x), x))
        prev = x
    return out


def minute(o, h, lo, c) -> Minute:
    return Minute(D(str(o)), D(str(h)), D(str(lo)), D(str(c)))


def oscillation(n_bars: int) -> list[Minute]:
    out: list[Minute] = []
    for i in range(n_bars):
        if i % 2 == 0:
            out += bar15(LOW, HIGH, LOW, HIGH, order="LH")
        else:
            out += bar15(HIGH, HIGH, LOW, LOW)
    return out


def a3_base() -> list[Minute]:
    """Up to and including the confirmation minute [04:00,04:01) of day 2."""
    ms = oscillation(26 * 4)  # day 1 + day 2 00:00-02:00 (ends at 97000 after a down bar)
    x = LOW
    for k in range(5):
        ms += bar15(x, x + 650, x, x + 650, order="LH")
        x += 650
    ms += bar15(x, D(100900), x, D(100700), order="LH")          # [03:15,03:30): B 100900, close 100700
    ms += bar15(D(100700), D(100700), D(100000), D("100049.9"))  # [03:30,03:45): ARM at 03:45
    ms += bar15(D("100049.9"), D("100049.9"), D(99900), D(99950))  # [03:45,04:00): REVISE at 04:00
    ms.append(minute(99950, 100050, 99950, 100050))              # [04:00,04:01): CONFIRM at 04:01
    return ms


def flat(n: int, price, amp=D(5)) -> list[Minute]:
    out, p = [], D(str(price))
    for i in range(n):
        q = p + amp if i % 2 == 0 else p - amp
        out.append(minute(p, max(p, q), min(p, q), q))
        p = q
    return out


def walk(start, end, n: int) -> list[Minute]:
    """n minutes moving linearly from ``start`` to ``end`` (closes at the exact grid)."""
    s, e = D(str(start)), D(str(end))
    out, p = [], s
    for i in range(n):
        q = s + (e - s) * (i + 1) / n
        out.append(minute(p, max(p, q), min(p, q), q))
        p = q
    return out


def a3(post: list[Minute], tail: int = 420, tail_price=None) -> list[Minute]:
    ms = a3_base() + post
    last = ms[-1].c if tail_price is None else D(str(tail_price))
    return ms + flat(tail, last)


def a3_return_long(tail: int = 420) -> list[Minute]:
    """WAIT then RETURN: [04:01,04:02) o 100050 h 100050 l 99990 c 100000 is the first usable return (MP-002 §9 row
    2): issue at 04:02; the primary 60 s entry opens at 04:03 (o 100010); a rally reaches the cap/target 100700
    (call TARGET_REACHED) and later the narrative destination 100900 (scenario DESTINATION_REACHED)."""
    post = [minute(100050, 100050, 99990, 100000), minute(100000, 100010, 100000, 100010)]
    post += walk(100010, 100690, 34) + walk(100690, 100720, 1) + walk(100720, 100880, 8) + walk(100880, 100910, 1)
    return a3(post, tail=tail)


def mirror(minutes: list[Minute], pivot=D(100000)) -> list[Minute]:
    f = lambda x: 2 * pivot - x  # noqa: E731
    return [Minute(f(m.o), f(m.lo), f(m.h), f(m.c), gap=m.gap, vol=m.vol,
                   mark=None if m.mark is None else f(m.mark), index=None if m.index is None else f(m.index))
            for m in minutes]


# -- variants ---------------------------------------------------------------------------------------------------

def a3_spike_base(spike=100600) -> list[Minute]:
    """a3_base with a day-1 12:00 spike to ``spike`` (15m/1h pivot highs and the previous-day high, z 200): for
    spike 100600 every such zone is [100400, 100800] -> T = 100400 at confirmation (nearer than the own B zone)."""
    ms = a3_base()
    i = 48 * 15  # bar [12:00,12:15) of day 1 (an up bar)
    ms[i:i + 15] = bar15(LOW, D(spike), LOW, HIGH, order="LH")
    return ms


def a3_outside_then(post_close=100080) -> list[Minute]:
    """Row 3: the next minute only wicks to 100000 and closes 100080 (outside the corridor), then stays there."""
    return a3([minute(100050, 100080, 100000, 100080)], tail_price=post_close)


def a3_cap_then_return() -> list[Minute]:
    """Prices stay above the corridor (100060 +/- 5) while a new 15m pivot high 100560 (bar [04:15,04:30)) is
    confirmed at 05:00 with S15 650 / z 65: the cap drops to floor(100560-65) = 100495. The minute [05:00,05:01) closes
    99910 inside the corridor and passes against the new cap (G 58.55, Q 21.02, ratio 1.272): RETURN issue at 05:01
    with target 100495."""
    post = walk(100050, 100150, 14)                                     # rest of [04:00,04:15): high 100150
    post += walk(100150, 100560, 5) + walk(100560, 100060, 10)          # [04:15,04:30): pivot high 100560
    post += flat(30, 100060)                                            # [04:30,05:00): above the corridor
    post.append(minute(100060, 100060, 99910, 99910))                   # [05:00,05:01): usable return
    return a3(post)


def a3_cap_activation_contact() -> list[Minute]:
    """As a3_cap_then_return, but the minute [04:59,05:00) ending at the cap activation wicks to 100500 >= the new cap
    100495 (still below T_confirm 100700): CAP_ACTIVATION_CONTACT_AMBIGUOUS (never a retroactive target hit)."""
    post = walk(100050, 100150, 14) + walk(100150, 100560, 5) + walk(100560, 100060, 10) + flat(29, 100060)
    post += [minute(100060, 100500, 100060, 100060)]
    post.append(minute(100060, 100060, 99910, 99910))
    return a3(post)


def a3_cap_not_ahead() -> list[Minute]:
    """A new 15m pivot high 100300 (z 65 -> near edge 100235) confirmed at 05:00 while the close is 100240:
    CAP_NOT_AHEAD_NOW."""
    post = walk(100050, 100150, 14) + walk(100150, 100300, 5) + walk(100300, 100200, 10)
    post += walk(100200, 100250, 15) + walk(100250, 100240, 15)
    return a3(post)


def a3_expiry_at_return() -> list[Minute]:
    """Prices stay above the corridor until [05:29,05:30) closes 100000: the WAIT expires at 05:30 (original setup
    deadline) before that return is evaluated - expiry before issue, no call or path."""
    post = flat(88, 100070) + [minute(100070, 100070, 100000, 100000)]
    return a3(post)


def a3_stall_after_return() -> list[Minute]:
    """Stay above the corridor until 05:00, return at [05:00,05:01) close 100000 (issue 05:01), then flat at 100000:
    the scenario progress check at 06:01 (confirmation + 2h) finds max favorable close displacement below 0.5*S15 ->
    scenario STALLED retires the young call (call progress would only be at 06:31)."""
    post = flat(59, 100070) + [minute(100070, 100070, 100000, 100000)]
    return a3(post, tail_price=100000)


# -- stepping harness (dispatch-level injection between dispatches) -------------------------------------------------

class Stepper:
    """Pure kernel order (temporal barriers -> professional barriers -> admission) with a pause after the dispatch
    at a chosen time, so a dispatch-level fixture can inspect or (explicitly, white-box) alter state."""

    def __init__(self, minutes: list[Minute], *, method="v0.3", params=None, profile=None, events=None,
                 eval_start=DAY2, evaluator=True, start=DAY1) -> None:
        from algotrader.adviser.harness import build_events, make_runtime, temporal_for

        evs, cov = build_events(start, minutes)
        self.events = events if events is not None else evs
        self.rt = make_runtime(eval_start=eval_start, method=method, params=params, profile=profile,
                               evaluator=evaluator)
        self.temporal = temporal_for(cov)
        self.rt.attach(self.temporal)
        self.i = 0
        self.end = start + len(minutes) * MIN
        self.journal: list[dict] = []
        self.records: list[dict] = []

    @property
    def core(self):
        return self.rt.core

    def _drain(self) -> None:
        j, r = self.rt.take()
        self.journal += j
        self.records += r

    def run_until(self, t: datetime) -> None:
        """Process events until the dispatch at ``t`` has run (the first event available after t is admitted)."""
        while self.i < len(self.events):
            e = self.events[self.i]
            self.temporal.on_event(e, self.i)
            self.rt.before_admit(e)
            self.rt.admit(e, self.i)
            self.i += 1
            if e.available_time > t:
                break
        self._drain()

    def finish(self) -> None:
        while self.i < len(self.events):
            e = self.events[self.i]
            self.temporal.on_event(e, self.i)
            self.rt.before_admit(e)
            self.rt.admit(e, self.i)
            self.i += 1
        self.temporal.finish(self.end)
        self.rt.finish(self.end)
        self._drain()

    def kinds(self, kind: str) -> list[dict]:
        return [e["record"] for e in self.journal if e["kind"] == kind]


def delayed_events(minutes: list[Minute], delays: dict[int, int], start=DAY1):
    """Canonical events where trade minute i is RECEIVED ``delays[i]`` seconds after its close (availability =
    receipt); every other event keeps modeled close availability."""
    from algotrader.adviser.harness import build_events, trade_bar
    from algotrader.feed.ordering import order_events

    evs, _ = build_events(start, minutes)
    out = []
    for e in evs:
        if e.channel.family.value == "trade_bar_1m" and e.kind.value == "bar_observation":
            i = int((e.event_time - start) / MIN)
            if i in delays:
                m = minutes[i]
                e = trade_bar(e.event_time, m.o, m.h, m.lo, m.c, m.vol,
                              received=e.event_time + MIN + timedelta(seconds=delays[i]))
        out.append(e)
    return list(order_events(out))


def index_of(t: datetime, start=DAY1) -> int:
    return int((t - start) / MIN)
