"""Pure, database-free adviser execution over an in-memory canonical feed (tests, references, bounded benchmarks).

It applies exactly the kernel's order — factual event -> temporal clock policy (barriers strictly before the event,
then admission) -> professional barriers strictly before the event -> admission into the runtime — and finishes at
a finite clock end. Synthetic fixtures built here are engineering inputs, never market evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from ..feed.adapter import make_event
from ..feed.contracts import (
    AvailabilityBasis,
    ChannelCoverage,
    ChannelRef,
    EventKind,
    Family,
    FeedEvent,
    FundingPayload,
    IndexBarPayload,
    MarkBarPayload,
    QualityReason,
    SlotQualityPayload,
    SourceRef,
    TradeBarPayload,
)
from ..feed.ordering import modeled_availability, order_events
from ..temporal import engine as te
from ..temporal.contracts import ClockPolicy, Dependency, Horizon
from . import contracts as sc
from .core import AdviserConfig, AdviserCore
from .evaluator import Evaluator
from .identity import (
    IMPLEMENTATION_ID,
    MODEL_ID,
    RULES_VERSION,
    CapabilityProfile,
    historical_profile,
    register_sha256,
    rules_sha256,
)
from .params import load
from .runtime import AdviserRuntime

MIN = timedelta(minutes=1)
INST, IDX = "BTC-USDT-SWAP", "BTC-USDT"
TRADE = ChannelRef(source="okx", family=Family.TRADE_BAR_1M, series_id=INST)
MARK = ChannelRef(source="okx", family=Family.MARK_BAR_1M, series_id=INST)
INDEX = ChannelRef(source="okx", family=Family.INDEX_BAR_1M, series_id=IDX)
FUNDING = ChannelRef(source="okx", family=Family.FUNDING_SETTLEMENT, series_id=INST)
SRC = SourceRef(dataset_id="synthetic-fixture", artifact="fixture", row_index=None, raw_page_ref=None,
                retrieved_at=None, source_availability_policy="fixture")
MODELED = modeled_availability()


def mp001_dependencies() -> tuple[Dependency, ...]:
    """MP-001 named core dependencies exposed through the temporal readiness query (inspection); the professional
    core applies BOTH event-end and known-at age itself."""
    p = load()
    return (
        Dependency(name="mp001.trade.15m", family=Family.TRADE_BAR_1M, horizon=Horizon.M15,
                   required_complete=p.ready_15m, freshness_allowance=p.fresh_15m, optional=False),
        Dependency(name="mp001.trade.1h", family=Family.TRADE_BAR_1M, horizon=Horizon.H1,
                   required_complete=p.ready_1h, freshness_allowance=p.fresh_1h, optional=False),
        Dependency(name="mp001.trade.4h", family=Family.TRADE_BAR_1M, horizon=Horizon.H4, required_complete=1,
                   freshness_allowance=p.fresh_4h),
        Dependency(name="mp001.trade.1d", family=Family.TRADE_BAR_1M, horizon=Horizon.D1, required_complete=1,
                   freshness_allowance=p.fresh_day),
        Dependency(name="mp001.trade.1w", family=Family.TRADE_BAR_1M, horizon=Horizon.W1, required_complete=1,
                   freshness_allowance=p.fresh_week),
        Dependency(name="mp001.trade.1mo", family=Family.TRADE_BAR_1M, horizon=Horizon.MO1, required_complete=1,
                   freshness_allowance=p.fresh_month),
    )


def method_ref(profile: CapabilityProfile, build: str | None = None) -> sc.MethodRef:
    return sc.MethodRef(model=MODEL_ID, rules_version=RULES_VERSION, rules_sha256=rules_sha256(),
                        register_sha256=register_sha256(), profile_sha256=profile.sha256(),
                        implementation=IMPLEMENTATION_ID, build=build)


def D(x: Any) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


def trade_bar(t: datetime, o, h, lo, c, vol="1", policy=MODELED, received: datetime | None = None) -> FeedEvent:
    p = TradeBarPayload(open=D(o), high=D(h), low=D(lo), close=D(c), volume_contracts=D(vol) * 100,
                        volume_base=D(vol), volume_base_ccy="BTC", volume_quote=D(vol) * D(c), volume_quote_ccy="USDT")
    return make_event(TRADE, EventKind.BAR_OBSERVATION, t, t + MIN, received or t + MIN, policy, SRC, p)


def ref_bar(ch: ChannelRef, t: datetime, o, h, lo, c, policy=MODELED, received: datetime | None = None) -> FeedEvent:
    if ch.family == Family.MARK_BAR_1M:
        p = MarkBarPayload(open=D(o), high=D(h), low=D(lo), close=D(c))
    else:
        p = IndexBarPayload(index_id=IDX, open=D(o), high=D(h), low=D(lo), close=D(c))
    return make_event(ch, EventKind.BAR_OBSERVATION, t, t + MIN, received or t + MIN, policy, SRC, p)


def missing(ch: ChannelRef, t: datetime, policy=MODELED) -> FeedEvent:
    p = SlotQualityPayload(reason=QualityReason.MISSING, detail="fixture gap")
    return make_event(ch, EventKind.SLOT_QUALITY, t, t + MIN, t + MIN, policy, SRC, p)


def funding(t: datetime, rate) -> FeedEvent:
    p = FundingPayload(funding_rate=D(rate), realized_rate=None, method=None, formula_type=None)
    return make_event(FUNDING, EventKind.FUNDING_OBSERVATION, t, None, t, MODELED, SRC, p)


@dataclass
class Minute:
    """One synthetic minute: OHLC (trade) and optional mark/index closes; ``gap`` makes the trade slot MISSING."""

    o: Decimal
    h: Decimal
    lo: Decimal
    c: Decimal
    gap: bool = False
    mark: Decimal | None = None
    index: Decimal | None = None
    vol: Decimal = Decimal(1)


@dataclass
class PureResult:
    runtime: AdviserRuntime
    journal: list[dict] = field(default_factory=list)
    records: list[dict] = field(default_factory=list)
    temporal: Any = None

    def kinds(self, kind: str) -> list[dict]:
        return [e for e in self.journal if e["kind"] == kind]

    def calls(self) -> list[dict]:
        return [e["record"] for e in self.kinds("call")]

    def revisions(self, call_id: str | None = None) -> list[dict]:
        return [e["record"] for e in self.kinds("call_revision") if call_id is None or e["record"]["call_id"] == call_id]

    def candidates(self, prefix: str | None = None) -> list[dict]:
        """Candidate records whose attempt id starts with ``prefix`` (e.g. "A", "BL", "CS")."""
        return [e["record"] for e in self.kinds("candidate") if prefix is None
                or e["record"]["attempt_id"].startswith(prefix)]

    def scenarios(self, prefix: str | None = None) -> list[dict]:
        """v0.3/v0.4/v0.5 structural scenario records whose scenario id starts with ``prefix``."""
        return [e["record"] for e in self.kinds("scenario") if prefix is None
                or e["record"]["scenario_id"].startswith(prefix)]

    def entries(self, prefix: str | None = None) -> list[dict]:
        """v0.3/v0.4/v0.5 child entry-attempt records."""
        return [e["record"] for e in self.kinds("entry_attempt") if prefix is None
                or e["record"]["scenario_id"].startswith(prefix)]

    def paths(self, variant: str | None = None) -> list[dict]:
        return [r["record"] for r in self.records if r["kind"] == "path"
                and (variant is None or r["record"]["variant"] == variant)]

    def samples(self) -> list[dict]:
        return [r["record"] for r in self.records if r["kind"] == "view_sample"]


def build_events(start: datetime, minutes: list[Minute], *, with_refs: bool = True,
                 funding_events: tuple[tuple[datetime, Any], ...] = ()) -> tuple[list[FeedEvent], list[ChannelCoverage]]:
    events: list[FeedEvent] = []
    for i, m in enumerate(minutes):
        t = start + i * MIN
        if m.gap:
            events.append(missing(TRADE, t))
        else:
            events.append(trade_bar(t, m.o, m.h, m.lo, m.c, m.vol))
        if with_refs:
            mk = m.mark if m.mark is not None else m.c
            ix = m.index if m.index is not None else m.c
            events.append(ref_bar(MARK, t, mk, mk, mk, mk))
            events.append(ref_bar(INDEX, t, ix, ix, ix, ix))
    for t, rate in funding_events:
        events.append(funding(t, rate))
    end = start + len(minutes) * MIN
    cov = [ChannelCoverage(channel=TRADE, covered_from=start, covered_until=end, expected_cadence=MIN)]
    if with_refs:
        cov += [ChannelCoverage(channel=MARK, covered_from=start, covered_until=end, expected_cadence=MIN),
                ChannelCoverage(channel=INDEX, covered_from=start, covered_until=end, expected_cadence=MIN)]
    if funding_events:
        cov.append(ChannelCoverage(channel=FUNDING, covered_from=start, covered_until=end, expected_cadence=None))
    return list(order_events(events)), cov


def make_runtime(*, tick=Decimal("0.1"), eval_start=None, eval_end=None, evaluator: bool = True,
                 profile: CapabilityProfile | None = None, origin: str = sc.Origin.HISTORICAL_MODELED.value,
                 clock_policy: str = ClockPolicy.MODELED_COMPLETE_PREFIX.value, sample_views: bool = True,
                 funding_mode: str | None = None, method: str = "v0.2", params=None) -> AdviserRuntime:
    """``method`` selects the packaged release (v0.2 baseline / v0.3 MP-002 / v0.4 MP-003 / v0.5 MP-004); ``params`` overrides the typed register
    for engineering fixtures only (e.g. a different cost envelope to test cost invariance)."""
    from . import methods

    rel = methods.get(method)
    profile = profile or historical_profile()
    p = params or rel.params()
    cfg = AdviserConfig(instrument=INST, tick=D(tick), profile=profile,
                        method=method_ref(profile) if rel.key == "v0.2" else rel.method_ref(profile, None),
                        clock_policy=clock_policy, params=p, eval_start=eval_start, eval_end=eval_end, origin=origin,
                        channel_ids={"trade": TRADE.channel_id, "mark": MARK.channel_id, "index": INDEX.channel_id})
    ev = None
    if rel.key == "v0.2":
        if evaluator:
            ev = Evaluator(p, D(tick), eval_start=eval_start, eval_end=eval_end,
                           funding_mode=funding_mode or profile.funding_outcomes.value, sample_views=sample_views)
        return AdviserRuntime(AdviserCore(cfg), ev)
    from .evaluator3 import EvaluatorV3
    from .runtime3 import AdviserRuntimeV3
    from .runtime4 import AdviserRuntimeV4
    from .runtime5 import AdviserRuntimeV5

    if evaluator:
        ev = EvaluatorV3(p, D(tick), eval_start=eval_start, eval_end=eval_end,
                         funding_mode=funding_mode or profile.funding_outcomes.value, sample_views=sample_views)
    rt_cls = {"v0.4": AdviserRuntimeV4, "v0.5": AdviserRuntimeV5}.get(rel.key, AdviserRuntimeV3)
    return rt_cls(rt_cls.CORE_CLS(cfg), ev)


def temporal_for(coverage: list[ChannelCoverage], clock_policy=ClockPolicy.MODELED_COMPLETE_PREFIX,
                 allowance=timedelta(0)) -> te.TemporalEngine:
    profile = te.default_profile(clock_policy, allowance, dependencies=mp001_dependencies())
    return te.TemporalEngine(profile, tuple(coverage), basis=AvailabilityBasis.MODELED,
                             availability_policy_id=MODELED.policy_id, content_identity="synthetic")


def run_pure(start: datetime, minutes: list[Minute], *, eval_start: datetime | None = None,
             eval_end: datetime | None = None, evaluator: bool = True, tick=Decimal("0.1"),
             with_refs: bool = True, funding_events=(), funding_mode: str | None = None,
             runtime: AdviserRuntime | None = None, sample_views: bool = True,
             stop_after: int | None = None, method: str = "v0.2", params=None) -> PureResult:
    events, cov = build_events(start, minutes, with_refs=with_refs, funding_events=funding_events)
    rt = runtime or make_runtime(tick=tick, eval_start=eval_start if eval_start is not None else start,
                                 eval_end=eval_end, evaluator=evaluator, sample_views=sample_views,
                                 funding_mode=funding_mode, method=method, params=params)
    temporal = temporal_for(cov)
    rt.attach(temporal)
    res = PureResult(rt, temporal=temporal)
    for i, e in enumerate(events):
        if stop_after is not None and i >= stop_after:
            return _drain(res)
        temporal.on_event(e, i)
        rt.before_admit(e)
        rt.admit(e, i)
    end = start + len(minutes) * MIN
    temporal.finish(end)
    rt.finish(end)
    return _drain(res)


def _drain(res: PureResult) -> PureResult:
    j, r = res.runtime.take()
    res.journal += j
    res.records += r
    return res
