"""Local live adviser (WP-009 §5): Owner Start/Stop, durable session with lease/fencing, bounded startup catch-up,
first-completion live candles, narrow public quotes, explicit input tape, journal and once-only alerts.

Layers (each testable without the network):

* ``LiveDriver`` — the SAME sequential professional fold as historical runs (temporal engine + adviser runtime), driven
  by explicit commands: ``admit`` (one factual event), ``advance`` (clock barrier), ``quote``, ``origin``. Commands are
  recorded in the adviser input tape (``algotrader.adviser-input-tape.v1``); replaying the tape reproduces the same
  semantic outputs. Live/recorded execution uses ``temporal.clock.recorded-dispatch-tape.v1``.
* ``LiveSession`` — epochs and continuity: reuse a compatible persisted state, identify the downtime, reconstruct at
  most 96 h of missing same-instrument history (RECONSTRUCTED origin, modeled close availability; never measured
  receipt), abandon continuity explicitly beyond that (old ongoing guidance becomes UNASSESSABLE), reset on instrument
  metadata incompatibility, then activate LIVE only after connected current receipts and a fresh complete trade-bar
  dispatch. Reconstructed calls are never promoted; new calls need post-activation arm/trigger.
* ``LiveStore`` — fenced persistence: restorable state, journal, tape batches, alert dedup by change id, session view.
* ``LiveAdviserWorker`` — claims the single active session, owns its public WebSocket candle subscription and quote
  poller explicitly (no unmanaged watchers), heartbeats the lease, honours Stop/Reassess.

While the app is stopped nothing is monitored and no alert is promised. No order, account, size or leverage exists.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import socket
import time
import uuid
import zlib
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from .. import db
from ..feed.adapter import make_event
from ..feed.contracts import (
    AvailabilityBasis,
    AvailabilityPolicy,
    ChannelCoverage,
    ChannelRef,
    EventKind,
    Family,
    FeedEvent,
    IndexBarPayload,
    MarkBarPayload,
    QualityReason,
    SlotQualityPayload,
    SourceRef,
    TradeBarPayload,
)
from ..feed.ordering import canonical, modeled_availability
from ..temporal import engine as te
from ..temporal.contracts import ClockPolicy
from . import contracts as sc
from .core import AdviserConfig, AdviserCore, Quote
from .harness import mp001_dependencies, method_ref
from .identity import composite_identity, live_profile
from .params import load
from .runtime import AdviserRuntime

log = logging.getLogger("algotrader.adviser.live")
TAPE_FORMAT = "algotrader.adviser-input-tape.v1"
JOURNAL_FORMAT = "algotrader.adviser-journal.v1"
STATE_KEY = "live:okx:BTC-USDT-SWAP"
MIN = timedelta(minutes=1)
EPS = timedelta(microseconds=1)
MAX_RECONSTRUCTION = timedelta(hours=96)
FAR_FUTURE = timedelta(days=3650)
RECORDED_ALLOWANCE = timedelta(seconds=120)
OWNED_TASK_GRACE_SECONDS = 15.0  # socket receive wait (5 s) + one paced quote request (bounded timeout)
LIVE_POLICY = AvailabilityPolicy(
    policy_id="feed.live-admitted.v1(first-completed-local-receipt)", basis=AvailabilityBasis.RECORDED,
    base_policy_id="live adviser local receipt of the first completed (confirm=1) public push",
    bar_delay=timedelta(0), funding_delay=timedelta(0), measured=True,
    note=("RECORDED live availability: the local receipt time of the first completed push, admitted in receipt order; "
          "the receipt time is kept in SourceRef.retrieved_at. Not the exchange publication time."))
RECON_POLICY = modeled_availability()  # reconstructed catch-up: modeled close availability, NEVER measured receipt
ALERT_TYPES = frozenset({"NEW_CALL", "ENTRY_WITHDRAWN", "ENTRY_UNVERIFIED", "ENTRY_REOPENED", "TERMINAL"})
INST, IDX = "BTC-USDT-SWAP", "BTC-USDT"
TRADE = ChannelRef(source="okx", family=Family.TRADE_BAR_1M, series_id=INST)
MARK = ChannelRef(source="okx", family=Family.MARK_BAR_1M, series_id=INST)
INDEX = ChannelRef(source="okx", family=Family.INDEX_BAR_1M, series_id=IDX)
CHANNELS = {"trade": TRADE, "mark": MARK, "index": INDEX}


def _iso(t: datetime | None) -> str | None:
    return None if t is None else t.isoformat()


def floor_minute(t: datetime) -> datetime:
    return t.replace(second=0, microsecond=0)


# ---------------------------------------------------------------------------------------------------------------
# events
# ---------------------------------------------------------------------------------------------------------------


def candle_event(family: Family, start: datetime, o, h, lo, c, available: datetime, policy: AvailabilityPolicy,
                 source_ref: str, vol: tuple[str, str, str] = ("0", "0", "0"), received: datetime | None = None
                 ) -> FeedEvent:
    """One complete 1m bar event (trade/mark/index) with explicit availability policy and provenance."""
    ch = {Family.TRADE_BAR_1M: TRADE, Family.MARK_BAR_1M: MARK, Family.INDEX_BAR_1M: INDEX}[family]
    D = Decimal
    if family == Family.TRADE_BAR_1M:
        p = TradeBarPayload(open=D(str(o)), high=D(str(h)), low=D(str(lo)), close=D(str(c)),
                            volume_contracts=D(vol[0]), volume_base=D(vol[1]), volume_base_ccy="BTC",
                            volume_quote=D(vol[2]), volume_quote_ccy="USDT")
    elif family == Family.MARK_BAR_1M:
        p = MarkBarPayload(open=D(str(o)), high=D(str(h)), low=D(str(lo)), close=D(str(c)))
    else:
        p = IndexBarPayload(index_id=IDX, open=D(str(o)), high=D(str(h)), low=D(str(lo)), close=D(str(c)))
    src = SourceRef(dataset_id="live-adviser", artifact=source_ref, row_index=None, raw_page_ref=None,
                    retrieved_at=received or available, source_availability_policy=policy.base_policy_id)
    return make_event(ch, EventKind.BAR_OBSERVATION, start, start + MIN, available - policy.bar_delay, policy, src, p)


def missing_event(family: Family, start: datetime, available: datetime, policy: AvailabilityPolicy) -> FeedEvent:
    ch = {Family.TRADE_BAR_1M: TRADE, Family.MARK_BAR_1M: MARK, Family.INDEX_BAR_1M: INDEX}[family]
    src = SourceRef(dataset_id="live-adviser", artifact="gap", row_index=None, raw_page_ref=None, retrieved_at=available,
                    source_availability_policy=policy.base_policy_id)
    return make_event(ch, EventKind.SLOT_QUALITY, start, start + MIN, available, policy, src,
                      SlotQualityPayload(reason=QualityReason.MISSING, detail="no completed bar obtained"))


# ---------------------------------------------------------------------------------------------------------------
# driver (same fold, explicit tape)
# ---------------------------------------------------------------------------------------------------------------


@dataclass
class Epoch:
    run_id: str
    started: datetime
    cov_from: datetime
    compat: dict


def new_epoch(start: datetime, compat: dict) -> Epoch:
    return Epoch(run_id=f"live-{start:%Y%m%dT%H%M}-{uuid.uuid4().hex[:6]}", started=start,
                 cov_from=floor_minute(start), compat=compat)


def live_config(compat: dict, build: str | None, method: str = "v0.2") -> AdviserConfig:
    from . import methods

    rel = methods.get(method)
    profile = live_profile()
    return AdviserConfig(instrument=INST, tick=Decimal(compat["tick_sz"]), profile=profile,
                         method=method_ref(profile, build) if rel.key == "v0.2" else rel.method_ref(profile, build),
                         clock_policy=ClockPolicy.RECORDED_DISPATCH_TAPE.value,
                         params=load() if rel.key == "v0.2" else rel.params(), eval_start=None, eval_end=None,
                         origin=sc.Origin.RECONSTRUCTED.value, channel_ids={k: v.channel_id for k, v in CHANNELS.items()})


def _rt_classes(cfg: AdviserConfig):
    """(runtime class, core class) of the method pinned in a live configuration."""
    if cfg.method.model == "btc.context-action.v0.3":
        from .core3 import AdviserCoreV3
        from .runtime3 import AdviserRuntimeV3

        return AdviserRuntimeV3, AdviserCoreV3
    return AdviserRuntime, AdviserCore


def new_live_runtime(cfg: AdviserConfig) -> AdviserRuntime:
    rt_cls, core_cls = _rt_classes(cfg)
    return rt_cls(core_cls(cfg), None)


def new_temporal(cov_from: datetime) -> te.TemporalEngine:
    cov = tuple(ChannelCoverage(channel=ch, covered_from=cov_from, covered_until=cov_from + FAR_FUTURE,
                                expected_cadence=MIN) for ch in CHANNELS.values())
    profile = te.default_profile(ClockPolicy.RECORDED_DISPATCH_TAPE, RECORDED_ALLOWANCE,
                                 dependencies=mp001_dependencies())
    return te.TemporalEngine(profile, cov, basis=AvailabilityBasis.RECORDED, availability_policy_id=LIVE_POLICY.policy_id,
                             content_identity="live", context={"live": True})


class LiveDriver:
    def __init__(self, temporal: te.TemporalEngine, runtime: AdviserRuntime, tape_seq: int = 0) -> None:
        self.temporal = temporal
        self.rt = runtime
        runtime.attach(temporal)
        self.cursor = runtime.admitted
        if temporal.cursor != self.cursor:
            raise ValueError(f"temporal cursor {temporal.cursor} != adviser cursor {self.cursor}")
        self.tape: list[dict] = []
        self.tape_seq = tape_seq
        self.slots: dict[str, datetime] = {}  # last admitted slot per family (first-completion dedup)

    def _cmd(self, doc: dict) -> None:
        self.tape_seq += 1
        self.tape.append({"seq": self.tape_seq, **doc})

    def admit(self, e: FeedEvent) -> bool:
        """Admit one factual event in receipt order (first completion per channel/slot wins; later dups dropped)."""
        fam = e.channel.family.value
        last = self.slots.get(fam)
        if last is not None and e.event_time <= last:
            return False
        clock = self.temporal.clock
        if clock is not None and e.available_time < clock:
            raise ValueError(f"{e.event_id} available {e.available_time} before the processed clock {clock}")
        # every barrier strictly before this receipt runs first (sealing follows receipt time even in a burst of
        # pushes); evidence received at the same instant joins the same barrier
        if clock is None or e.available_time - EPS > clock:
            self.advance(e.available_time - EPS)
        self.rt.before_admit(e)
        self.temporal.admit(e, self.cursor)
        self.rt.admit(e, self.cursor)
        self._cmd({"cmd": "admit", "cursor": self.cursor, "event": e.model_dump(mode="json")})
        self.cursor += 1
        self.slots[fam] = e.event_time
        return True

    def advance(self, t: datetime, record_noop: bool = False) -> int:
        """Clock barrier at t: temporal barriers (sealing/readiness) then professional barriers <= t."""
        if self.temporal.clock is not None and t < self.temporal.clock:
            t = self.temporal.clock
        before = (self.temporal.dispatch_seq, self.rt.dispatches)
        self.temporal.advance_to(t)
        n = self.rt.advance(t, inclusive=True)
        if record_noop or (self.temporal.dispatch_seq, self.rt.dispatches) != before:
            self._cmd({"cmd": "advance", "time": _iso(t)})
        return n

    def quote(self, q: Quote, at: datetime) -> None:
        self.rt.quote(q, at)
        self._cmd({"cmd": "quote", "at": _iso(at), "quote": q.encode()})

    def origin(self, origin: str, at: datetime) -> None:
        self.rt.origin(origin, at)
        self._cmd({"cmd": "origin", "at": _iso(at), "origin": origin})

    def connection(self, state: str, at: datetime) -> None:
        self.rt.connection(state, at)
        self._cmd({"cmd": "connection", "at": _iso(at), "state": state})

    def restart(self, at: datetime, reason: str) -> None:
        self.rt.capability_restart(at, reason)
        self._cmd({"cmd": "restart", "at": _iso(at), "reason": reason})

    def take(self) -> tuple[list[dict], list[dict], list[dict]]:
        j, _ = self.rt.take()
        t, self.tape = self.tape, []
        return j, [], t

    def encode(self) -> tuple[bytes, str, bytes, str]:
        traw = canonical(self.temporal.encode())
        araw = canonical({**self.rt.encode(), "driver": {"cursor": self.cursor, "tape_seq": self.tape_seq,
                                                         "slots": {k: _iso(v) for k, v in sorted(self.slots.items())}}})
        return (zlib.compress(traw, 6), hashlib.sha256(traw).hexdigest(), zlib.compress(araw, 6),
                hashlib.sha256(araw).hexdigest())

    @classmethod
    def decode(cls, tblob: bytes, tsha: str, ablob: bytes, asha: str, cfg: AdviserConfig) -> LiveDriver:
        temporal = te.unpack(tblob, tsha)
        araw = zlib.decompress(ablob)
        if hashlib.sha256(araw).hexdigest() != asha:
            raise ValueError("live adviser state SHA-256 mismatch")
        doc = json.loads(araw)
        drv_doc = doc.pop("driver")
        rt = _rt_classes(cfg)[0].decode(doc, cfg, None)
        d = cls(temporal, rt, drv_doc["tape_seq"])
        d.slots = {k: datetime.fromisoformat(v) for k, v in drv_doc["slots"].items()}
        return d


def replay_tape(commands: list[dict], cfg: AdviserConfig, cov_from: datetime) -> LiveDriver:
    """Reproduce a live/recorded session from its input tape (same commands -> same semantic outputs)."""
    d = LiveDriver(new_temporal(cov_from), new_live_runtime(cfg))
    for c in commands:
        k = c["cmd"]
        if k == "admit":
            e = FeedEvent.model_validate(c["event"])
            d.admit(e)
        elif k == "advance":
            d.advance(datetime.fromisoformat(c["time"]))
        elif k == "quote":
            d.quote(Quote.decode(c["quote"]), datetime.fromisoformat(c["at"]))
        elif k == "origin":
            d.origin(c["origin"], datetime.fromisoformat(c["at"]))
        elif k == "restart":
            d.restart(datetime.fromisoformat(c["at"]), c["reason"])
        elif k == "connection":
            d.connection(c["state"], datetime.fromisoformat(c["at"]))
    return d


# ---------------------------------------------------------------------------------------------------------------
# session (epochs, catch-up, activation, alerts)
# ---------------------------------------------------------------------------------------------------------------


class CatchUpCancelled(Exception):
    """Stop observed between bounded catch-up units (history pages / replayed minutes)."""


HistoryFetcher = Callable[[Family, datetime, datetime], list[tuple[datetime, Decimal, Decimal, Decimal, Decimal, tuple]]]


@dataclass
class LiveSession:
    """Owner session over one continuity epoch. ``fetch_history(family, start, end)`` returns complete bars
    [(start, o, h, l, c, (vol_contracts, vol_base, vol_quote))] for [start, end) from the public archive."""

    compat: dict
    build: str | None
    clock: Callable[[], datetime]
    epoch: Epoch | None = None
    driver: LiveDriver | None = None
    status: str = "STARTING"  # STARTING / RECONSTRUCTING / WARMING_UP / LIVE / DISCONNECTED / STOPPED
    connected: bool = False
    live_since: datetime | None = None
    last_receipt: datetime | None = None
    notes: list[dict] = field(default_factory=list)
    recent_1m: deque = field(default_factory=lambda: deque(maxlen=240))
    abandoned: list[dict] = field(default_factory=list)  # (epoch run id, journal, tape) of a closed old epoch
    activation_pending: bool = True
    progress: dict = field(default_factory=dict)
    cancel_requested: bool = False
    method: str = "v0.2"  # selected at Start; a session never converts an existing lineage to another method

    def note(self, event: str, **kw: Any) -> None:
        self.notes.append({"at": _iso(self.clock()), "event": event, **kw})

    # -- start / continuity ---------------------------------------------------------------------------------------

    def start(self, persisted: dict | None, fetch_history: HistoryFetcher) -> None:
        now = self.clock()
        cfg = live_config(self.compat, self.build, self.method)
        reset_reason = None
        if persisted is not None:
            if persisted["compat"] != self.compat:
                reset_reason = "INSTRUMENT_METADATA_CHANGED"
            elif persisted.get("method", "v0.2") != self.method:
                reset_reason = f"METHOD_CHANGED:{persisted.get('method', 'v0.2')}->{self.method}"
            else:
                try:
                    drv = LiveDriver.decode(bytes(persisted["temporal_blob"]), persisted["temporal_sha256"],
                                            bytes(persisted["adviser_blob"]), persisted["adviser_sha256"], cfg)
                except Exception as exc:  # noqa: BLE001 - an unusable state is an explicit reset, never silent
                    drv, reset_reason = None, f"STATE_UNUSABLE:{type(exc).__name__}"
                if drv is not None:
                    last = drv.temporal.clock or persisted.get("clock")
                    downtime = now - last if last else None
                    self.epoch = Epoch(persisted["run_id"], persisted["epoch_started"], persisted["cov_from"],
                                       persisted["compat"])
                    if downtime is not None and downtime > MAX_RECONSTRUCTION:
                        reset_reason = "DOWNTIME_BEYOND_96H"
                        drv.origin(sc.Origin.RECONSTRUCTED.value, last)
                        drv.restart(last, "CONTINUITY_ABANDONED_DOWNTIME_BEYOND_96H")
                        drv.advance(last)
                        j, _, tape = drv.take()
                        self.abandoned.append({"run_id": self.epoch.run_id, "journal": j, "tape": tape,
                                               "driver": drv})
                    else:
                        self.driver = drv
                        self.note("resumed", downtime_seconds=downtime.total_seconds() if downtime else None,
                                  run_id=self.epoch.run_id)
        if self.driver is None:
            if reset_reason:
                self.note("continuity_reset", reason=reset_reason)
            self.epoch = new_epoch(now - MAX_RECONSTRUCTION, self.compat)
            self.driver = LiveDriver(new_temporal(self.epoch.cov_from), new_live_runtime(cfg))
        at = self.driver.temporal.clock or self.epoch.cov_from
        self.driver.origin(sc.Origin.RECONSTRUCTED.value, at)  # nothing during catch-up is alertable
        # no candle subscription is confirmed yet: entry cannot be verified until a (re)connection AND a fresh bar
        self.driver.connection("DISCONNECTED", at)
        if persisted is not None and not reset_reason:
            # a restart gap overlapping an ongoing thesis makes it UNASSESSABLE; old alerts never replay as new
            self.driver.restart(at, "RESTART_GAP_OVERLAPS_THESIS")
        self.reconstruct(fetch_history, now)

    def reconstruct(self, fetch_history: HistoryFetcher, now: datetime) -> None:
        """Bounded catch-up of complete minutes [last processed, now) (<= 96 h), RECONSTRUCTED, modeled close
        availability; gaps the archive cannot fill stay explicit MISSING minutes."""
        self.status = "RECONSTRUCTING"
        d = self.driver
        start = d.slots.get("trade_bar_1m")
        start = (start + MIN) if start is not None else self.epoch.cov_from
        end = floor_minute(now)
        if end - start > MAX_RECONSTRUCTION:
            start = end - MAX_RECONSTRUCTION
        if start >= end:
            self.status = "WARMING_UP"
            return
        bars: dict[Family, dict[datetime, tuple]] = {}
        self.progress = {"phase": "CATCH_UP_ACQUIRE", "start": _iso(start), "end": _iso(end),
                         "minutes": int((end - start) / MIN), "families_done": 0}
        for fam in (Family.TRADE_BAR_1M, Family.MARK_BAR_1M, Family.INDEX_BAR_1M):
            if self._cancelled("CATCH_UP_ACQUIRE"):
                return
            try:
                bars[fam] = {b[0]: b for b in fetch_history(fam, start, end)}
            except CatchUpCancelled:
                self._cancelled("CATCH_UP_ACQUIRE")
                return
            except Exception as exc:  # noqa: BLE001 - no fabricated history; the gap stays visible
                self.note("catch_up_failed", family=fam.value, detail=str(exc))
                bars[fam] = {}
            self.progress["families_done"] += 1
        self.progress["phase"] = "CATCH_UP_REPLAY"
        t = start
        n = 0
        while t < end:
            if self._cancelled("CATCH_UP_REPLAY"):  # one bounded unit (one minute) at a time
                return
            close = t + MIN
            # modeled close availability, never before the already processed clock (a restart can resume a little
            # after the close of a minute that had not been received yet)
            avail = max(close, d.temporal.clock or close)
            for fam in (Family.TRADE_BAR_1M, Family.MARK_BAR_1M, Family.INDEX_BAR_1M):
                if d.slots.get(fam.value) is not None and d.slots[fam.value] >= t:
                    continue  # already admitted live before the stop
                b = bars[fam].get(t)
                e = (candle_event(fam, t, *b[1:5], avail, RECON_POLICY, "rest-history", vol=b[5]) if b else
                     missing_event(fam, t, avail, RECON_POLICY))
                d.admit(e)
                if fam == Family.TRADE_BAR_1M and b:
                    self.recent_1m.append({"t": _iso(t), "o": str(b[1]), "h": str(b[2]), "l": str(b[3]), "c": str(b[4])})
            d.advance(avail)
            t = close
            n += 1
            self.progress["replayed_minutes"] = n
        self.progress["phase"] = "DONE"
        self.note("reconstructed", minutes=n, start=_iso(start), end=_iso(end))
        self.status = "WARMING_UP"

    def _cancelled(self, phase: str) -> bool:
        if not self.cancel_requested:
            return False
        self.progress = {**self.progress, "phase": "CANCELLED", "cancelled_in": phase}
        self.note("catch_up_cancelled", phase=phase, replayed_minutes=self.progress.get("replayed_minutes", 0))
        self.status = "STOPPING"
        return True

    # -- live inputs ---------------------------------------------------------------------------------------------

    def on_live_bar(self, fam: Family, start: datetime, ohlc: tuple, vol: tuple, received: datetime) -> bool:
        """A first completed (confirm=1) public push. Bars already covered by the catch-up are dropped."""
        d = self.driver
        avail = max(received, d.temporal.clock or received)
        e = candle_event(fam, start, *ohlc, avail, LIVE_POLICY, "ws-first-completion", vol=vol, received=received)
        if not d.admit(e):
            return False
        self.last_receipt = received
        if fam == Family.TRADE_BAR_1M:
            self.recent_1m.append({"t": _iso(start), "o": str(ohlc[0]), "h": str(ohlc[1]), "l": str(ohlc[2]),
                                   "c": str(ohlc[3])})
            if self.activation_pending and self.connected and received - (start + MIN) <= RECORDED_ALLOWANCE:
                # a fresh, currently received complete trade bar: activate LIVE at its receipt (post-activation
                # arm/trigger rules apply to new calls; reconstructed calls are never promoted)
                d.origin(sc.Origin.LIVE.value, avail)
                self.activation_pending = False
                self.live_since = avail
                self.status = "LIVE"
                self.note("live_activated", at=_iso(avail))
        return True

    def _at(self, at: datetime) -> datetime:
        # inputs from the WebSocket and the quote poller can be queued slightly out of timestamp order: a command is
        # dispatched no earlier than the processed clock (its own source/receipt times still govern freshness)
        known = [x for x in (self.driver.temporal.clock, self.driver.rt.core.clock) if x is not None]
        return max([at, *known])

    def on_quote(self, q: Quote, at: datetime) -> None:
        self.driver.quote(q, self._at(at))

    def on_connection(self, state: str, at: datetime) -> None:
        """Taped candle-session adequacy (CONNECTED / DISCONNECTED / STOPPED). Reconnection alone is not proof of
        fresh usable input: the core waits for a fresh complete trade bar received after it."""
        self.driver.connection(state, self._at(at))
        self.connected = state == "CONNECTED"
        self.note({"CONNECTED": "ws_connected", "DISCONNECTED": "ws_disconnected", "STOPPED": "stopped"}[state])
        if not self.connected and self.status == "LIVE":
            self.status = "DISCONNECTED"

    def tick(self, now: datetime) -> None:
        self.driver.advance(now)
        if self.status == "LIVE" and not self.connected:
            self.status = "DISCONNECTED"
        elif self.status == "DISCONNECTED" and self.connected and not self.activation_pending:
            self.status = "LIVE"

    def disconnected(self) -> None:
        self.on_connection("DISCONNECTED", self.clock())

    def view(self) -> dict:
        core = self.driver.rt.core
        t = core.clock
        insp = core.inspect()
        return {"status": self.status, "connected": self.connected, "live_since": _iso(self.live_since),
                "method": self.method,
                **({"scenarios": insp.get("scenarios", [])} if self.method != "v0.2" else {}),
                "last_receipt": _iso(self.last_receipt), "run_id": self.epoch.run_id if self.epoch else None,
                "clock": _iso(t), "origin": core.origin, "market_view": insp["view"], "call": insp["call"],
                "lenses": insp["lenses"], "recent_calls": insp["recent_calls"], "attempts": insp["attempts"],
                "box": insp["box"], "readiness": insp["readiness"],
                "levels": (insp["view"] or {}).get("levels"),
                "chart": {"minutes": list(self.recent_1m),
                          "m15": [b.encode()[:7] for b in list(core.m15)[-96:]]},
                "notes": self.notes[-20:], "counters": {k: insp["counters"].get(k) for k in
                                                         ("dispatches", "view_changes", "quotes_admitted",
                                                          "quotes_not_newer")}}


def alerts_from(journal: list[dict], run_id: str) -> list[dict]:
    """Alert candidates: committed LIVE material changes of the alertable types, keyed by change id (dedup)."""
    out = []
    for e in journal:
        if e["kind"] != "material_change":
            continue
        r = e["record"]
        if not r["alertable"] or r["change_type"] not in ALERT_TYPES:
            continue
        out.append({"alert_key": f"{run_id}:{r['change_id']}", "run_id": run_id, "journal_seq": e["seq"],
                    "change_type": r["change_type"], "subject_id": r["subject_id"], "summary": r["summary"]})
    return out


# ---------------------------------------------------------------------------------------------------------------
# persistence
# ---------------------------------------------------------------------------------------------------------------


class LiveStore:
    def __init__(self, conn: psycopg.Connection, session_id: str, worker_id: str, generation: int) -> None:
        self.conn, self.sid, self.wid, self.gen = conn, session_id, worker_id, generation

    @property
    def fence(self) -> tuple[str, tuple]:
        return ("session_id = %s AND lease_owner = %s AND lease_generation = %s AND status = 'running'",
                (self.sid, self.wid, self.gen))

    def load_state(self) -> dict | None:
        row = self.conn.execute("SELECT * FROM adviser_live_state WHERE state_key = %s", (STATE_KEY,)).fetchone()
        if row is None:
            return None
        meta = row["compat"]
        return {**row, "compat": meta["compat"], "run_id": meta["run_id"], "method": meta.get("method", "v0.2"),
                "epoch_started": datetime.fromisoformat(meta["epoch_started"]),
                "cov_from": datetime.fromisoformat(meta["cov_from"])}

    def save(self, sess: LiveSession, extra: list[dict] | None = None) -> list[dict]:
        """One fenced transaction: state + journal + tape + alerts (+ outputs of an abandoned epoch) + view."""
        d = sess.driver
        journal, _, tape = d.take()
        tblob, tsha, ablob, asha = d.encode()
        cond, args = self.fence
        new_alerts = []
        with self.conn.transaction():
            if self.conn.execute(f"SELECT 1 FROM adviser_live_sessions WHERE {cond} FOR UPDATE", args).fetchone() is None:
                raise PermissionError("live session lease lost (fenced)")
            for old in sess.abandoned:
                self._outputs(old["run_id"], old["journal"], old["tape"])
            sess.abandoned = []
            self._outputs(sess.epoch.run_id, journal, tape)
            meta = {"compat": sess.compat, "run_id": sess.epoch.run_id, "epoch_started": _iso(sess.epoch.started),
                    "cov_from": _iso(sess.epoch.cov_from)}
            if sess.method != "v0.2":  # v0.2 state meta stays byte-identical to WP-009
                meta["method"] = sess.method
            self.conn.execute(
                """INSERT INTO adviser_live_state (state_key, session_id, generation, compat, clock, temporal_blob,
                       temporal_sha256, adviser_blob, adviser_sha256, tape_seq, journal_seq, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
                   ON CONFLICT (state_key) DO UPDATE SET session_id = excluded.session_id,
                       generation = excluded.generation, compat = excluded.compat, clock = excluded.clock,
                       temporal_blob = excluded.temporal_blob, temporal_sha256 = excluded.temporal_sha256,
                       adviser_blob = excluded.adviser_blob, adviser_sha256 = excluded.adviser_sha256,
                       tape_seq = excluded.tape_seq, journal_seq = excluded.journal_seq, updated_at = now()""",
                (STATE_KEY, self.sid, self.gen, Jsonb(meta), d.temporal.clock, tblob, tsha, ablob, asha, d.tape_seq,
                 d.rt.core.journal_seq))
            for a in alerts_from(journal, sess.epoch.run_id):
                got = self.conn.execute(
                    """INSERT INTO adviser_alerts (alert_key, run_id, session_id, journal_seq, change_type, subject_id,
                           summary) VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (alert_key) DO NOTHING
                       RETURNING alert_key""",
                    (a["alert_key"], a["run_id"], self.sid, a["journal_seq"], a["change_type"], a["subject_id"],
                     a["summary"])).fetchone()
                if got:
                    new_alerts.append(a)
            self.conn.execute(
                f"""UPDATE adviser_live_sessions SET view = %s, view_seq = view_seq + 1, phase = %s,
                        identity = coalesce(identity, %s), diagnostic_log = %s, heartbeat_at = now()
                    WHERE {cond}""",
                (Jsonb(json.loads(json.dumps(sess.view(), default=str))), sess.status,
                 Jsonb(_session_identity(sess)), Jsonb(sess.notes[-50:]), *args))
        return new_alerts

    def _outputs(self, run_id: str, journal: list[dict], tape: list[dict]) -> None:
        if journal:
            with self.conn.cursor() as cur:
                cur.executemany(
                    """INSERT INTO adviser_journal (run_id, seq, kind, record_id, clock_time, professional_seq,
                           factual_cursor, origin, subject, digest, chain, record, generation)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    [(run_id, e["seq"], e["kind"], e["record_id"], e["clock_time"], e["professional_seq"],
                      e["factual_cursor"], e["origin"], e["subject"], e["digest"], e["chain"], Jsonb(e["record"]),
                      self.gen) for e in journal])
        if tape:
            self.conn.execute(
                """INSERT INTO adviser_input_tape (run_id, seq, session_id, generation, command)
                   VALUES (%s, %s, %s, %s, %s)""",
                (run_id, tape[0]["seq"], self.sid, self.gen,
                 Jsonb({"format": TAPE_FORMAT, "from": tape[0]["seq"], "to": tape[-1]["seq"], "commands": tape})))


# ---------------------------------------------------------------------------------------------------------------
# session control (API side)
# ---------------------------------------------------------------------------------------------------------------


class LiveControlError(Exception):
    pass


def _session_identity(sess) -> dict:
    pins = {"state_key": STATE_KEY, "run_id": sess.epoch.run_id}
    if sess.method == "v0.2":
        return composite_identity(live_profile(), pins, sess.build)
    from . import methods

    return {**methods.get(sess.method).composite_identity(live_profile(), pins, sess.build), "method": sess.method}


def start_session(conn: psycopg.Connection, rest_base_url: str = "https://www.okx.com",
                  method: str | None = None) -> str:
    """Queue a live session. The method is selected explicitly before Start (absent = the v0.2 default) and pinned in
    the session configuration; it never changes for a running session."""
    from . import methods

    try:
        rel = methods.get(method)
    except methods.UnknownMethod as exc:
        raise LiveControlError(str(exc)) from None
    sid = f"live-session-{datetime.now(UTC):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:6]}"
    cfg = {"rest_base_url": rest_base_url, "inst_id": INST}
    if method is not None:
        cfg["method"] = rel.key
    try:
        with conn.transaction():
            conn.execute("INSERT INTO adviser_live_sessions (session_id, status, config, phase) VALUES (%s, 'queued', "
                         "%s, 'QUEUED')", (sid, Jsonb(cfg)))
    except psycopg.errors.UniqueViolation:
        raise LiveControlError("a live adviser session is already queued or running") from None
    return sid


def stop_session(conn: psycopg.Connection, session_id: str) -> None:
    with conn.transaction():
        row = conn.execute("SELECT status FROM adviser_live_sessions WHERE session_id = %s FOR UPDATE",
                           (session_id,)).fetchone()
        if row is None:
            raise LookupError(session_id)
        if row["status"] == "queued":
            conn.execute("UPDATE adviser_live_sessions SET status = 'stopped', stopped_at = now(), phase = 'STOPPED' "
                         "WHERE session_id = %s", (session_id,))
        elif row["status"] == "running":
            conn.execute("UPDATE adviser_live_sessions SET stop_requested = true WHERE session_id = %s", (session_id,))


def request_reassess(conn: psycopg.Connection, session_id: str) -> None:
    conn.execute("UPDATE adviser_live_sessions SET reassess_requested = reassess_requested + 1 WHERE session_id = %s "
                 "AND status = 'running'", (session_id,))


# ---------------------------------------------------------------------------------------------------------------
# public market access (REST history, instrument, WebSocket candles)
# ---------------------------------------------------------------------------------------------------------------


def instrument_compat(client) -> dict:
    """Pinned instrument definition (effective live metadata); a change resets continuity explicitly."""
    from ..marketdata.okx import parse_instrument

    inst = parse_instrument(client.instrument(INST), INST, "live-instrument")
    return {"inst_id": inst.inst_id, "index_id": inst.index_id, "tick_sz": str(inst.tick_sz),
            "ct_val": str(inst.ct_val), "ct_mult": str(inst.ct_mult), "lot_sz": str(inst.lot_sz),
            "settle_ccy": inst.settle_ccy}


def history_fetcher(client, cancelled: Callable[[], bool] = lambda: False) -> HistoryFetcher:
    """Complete minutes for [start, end) through the accepted read-only history endpoints (paged, newest first).
    ``cancelled`` is checked before every page request (bounded unit): an observed Stop raises CatchUpCancelled."""
    from ..marketdata.contracts import Family as MdFamily
    from ..marketdata.okx import dt_to_ms, ms_to_dt

    md = {Family.TRADE_BAR_1M: MdFamily.TRADE_CANDLES, Family.MARK_BAR_1M: MdFamily.MARK_CANDLES,
          Family.INDEX_BAR_1M: MdFamily.INDEX_CANDLES}
    src = {Family.TRADE_BAR_1M: INST, Family.MARK_BAR_1M: INST, Family.INDEX_BAR_1M: IDX}

    def fetch(fam: Family, start: datetime, end: datetime):
        out = {}
        after = dt_to_ms(end)
        before = dt_to_ms(start) - 1
        while True:
            if cancelled():
                raise CatchUpCancelled(fam.value)
            page = client.history_page(md[fam], src[fam], after, before, 100)
            rows = page.data
            if not rows:
                break
            for r in rows:
                if str(r[-1]) != "1":
                    continue  # unconfirmed bar: never complete evidence
                t = ms_to_dt(r[0])
                if start <= t < end:
                    vol = (str(r[5]), str(r[6]), str(r[7])) if fam == Family.TRADE_BAR_1M else ("0", "0", "0")
                    out[t] = (t, Decimal(r[1]), Decimal(r[2]), Decimal(r[3]), Decimal(r[4]), vol)
            oldest = min(int(r[0]) for r in rows)
            if oldest <= before + 1 or len(rows) < 100:
                break
            after = oldest
        return [out[k] for k in sorted(out)]

    return fetch


WS_CHANNELS = (("candle1m", INST, Family.TRADE_BAR_1M), ("mark-price-candle1m", INST, Family.MARK_BAR_1M),
               ("index-candle1m", IDX, Family.INDEX_BAR_1M))


def parse_ws_candle(text: str) -> list[tuple[Family, datetime, tuple, tuple]]:
    """Completed (confirm=1) candle pushes only; forming pushes never become observations."""
    try:
        doc = json.loads(text)
    except ValueError:
        return []
    arg = doc.get("arg") or {}
    fam = next((f for ch, inst, f in WS_CHANNELS if arg.get("channel") == ch and arg.get("instId") == inst), None)
    if fam is None or not isinstance(doc.get("data"), list):
        return []
    out = []
    for r in doc["data"]:
        if not isinstance(r, list) or len(r) < 6 or str(r[-1]) != "1":
            continue
        try:
            t = datetime.fromtimestamp(int(r[0]) / 1000, tz=UTC)
            ohlc = tuple(Decimal(str(x)) for x in r[1:5])
        except (ValueError, ArithmeticError):
            continue
        if not (ohlc[2] <= min(ohlc[0], ohlc[3]) and ohlc[1] >= max(ohlc[0], ohlc[3]) and ohlc[2] > 0):
            continue  # invalid OHLC never becomes valid state
        vol = (str(r[5]), str(r[6]), str(r[7])) if fam == Family.TRADE_BAR_1M and len(r) >= 9 else ("0", "0", "0")
        out.append((fam, t, ohlc, vol))
    return out


# ---------------------------------------------------------------------------------------------------------------
# worker
# ---------------------------------------------------------------------------------------------------------------


class LiveAdviserWorker:
    """Supervised worker owning the single live session (lease + generation fencing, explicit subscriptions)."""

    PREFIX = "adviser:"

    def __init__(self, url: str | None = None, worker_id: str | None = None, lease_seconds: float = 20.0,
                 poll_interval: float = 1.0, *, rest_client_factory=None, quote_client_factory=None,
                 ws_connect=None, ws_url: str = "wss://ws.okx.com:8443/ws/v5/business",
                 clock: Callable[[], datetime] = lambda: datetime.now(UTC), tick_seconds: float = 1.0,
                 save_seconds: float = 2.0, max_ticks: int | None = None, build: str | None = None) -> None:
        self.url = url or db.database_url()
        self.worker_id = worker_id or f"{self.PREFIX}{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:6]}"
        self.lease_seconds, self.poll_interval = lease_seconds, poll_interval
        self.rest_client_factory = rest_client_factory
        self.quote_client_factory = quote_client_factory
        self.ws_connect = ws_connect
        self.ws_url = ws_url
        self.clock = clock
        self.tick_seconds, self.save_seconds = tick_seconds, save_seconds
        self.max_ticks = max_ticks
        self.build = build

    def claim(self, conn) -> tuple[dict, int] | None:
        with conn.transaction():
            row = conn.execute(
                """SELECT * FROM adviser_live_sessions WHERE status = 'queued'
                      OR (status = 'running' AND lease_expires_at < now())
                   ORDER BY created_at LIMIT 1 FOR UPDATE SKIP LOCKED""").fetchone()
            if row is None:
                return None
            gen = row["lease_generation"] + 1
            conn.execute(
                """UPDATE adviser_live_sessions SET status = 'running', lease_owner = %s, lease_generation = %s,
                       lease_expires_at = now() + make_interval(secs => %s), heartbeat_at = now(),
                       attempt = attempt + 1, started_at = coalesce(started_at, now()), phase = 'STARTING'
                   WHERE session_id = %s""", (self.worker_id, gen, self.lease_seconds, row["session_id"]))
        return row, gen

    def beat(self, current: str | None) -> None:
        with db.connection(self.url, autocommit=True) as conn:
            conn.execute(
                """INSERT INTO workers (worker_id, host, pid, current_run) VALUES (%s, %s, %s, %s)
                   ON CONFLICT (worker_id) DO UPDATE SET heartbeat_at = now(), current_run = excluded.current_run""",
                (self.worker_id, socket.gethostname(), os.getpid(), current))

    def run_forever(self, should_stop: Callable[[], bool] = lambda: False) -> None:
        log.info("live adviser worker %s started", self.worker_id)
        while not should_stop():
            try:
                self.beat(None)
                if not self.run_once():
                    time.sleep(self.poll_interval)
            except psycopg.OperationalError as exc:
                log.warning("live adviser worker loop error: %s", exc)
                time.sleep(self.poll_interval)

    def run_once(self) -> bool:
        with db.connection(self.url, autocommit=True) as conn:
            got = self.claim(conn)
            if got is None:
                return False
            row, gen = got
            store = LiveStore(conn, row["session_id"], self.worker_id, gen)
            try:
                asyncio.run(self._session(conn, row, store))
            except PermissionError:
                log.warning("%s: lease lost; session continues under another owner", row["session_id"])
            except Exception as exc:  # noqa: BLE001 - visible failure, never silent
                log.exception("live session failed")
                conn.execute("UPDATE adviser_live_sessions SET status = 'failed', error = %s, stopped_at = now(), "
                             "lease_owner = NULL WHERE session_id = %s AND lease_generation = %s",
                             (f"{type(exc).__name__}: {exc}", row["session_id"], gen))
        return True

    def _clients(self, row):
        from ..marketdata.okx import OkxPublicClient
        from .quotes import QuoteClient

        base = (row["config"] or {}).get("rest_base_url", "https://www.okx.com")
        rest = self.rest_client_factory(base) if self.rest_client_factory else OkxPublicClient(base)
        quotes = self.quote_client_factory(base) if self.quote_client_factory else QuoteClient(base, INST)
        return rest, quotes

    async def _session(self, conn, row, store: LiveStore) -> None:
        """All database access happens on this event-loop thread; network fetches and the bounded startup (instrument
        metadata, catch-up) run in ONE owned worker thread that never touches the connection. The session owns every
        task it starts: on any exit (Stop, startup failure, lease/fence loss) the startup thread is signalled and
        joined (it checks cancellation between history pages and replayed minutes) and the socket/quote tasks are
        cancelled and awaited. A heartbeat renews the lease and publishes progress while startup work runs. After an
        observed Stop the session never enters LIVE nor publishes new alerts."""
        from ..marketdata.okx_authority import validate_okx_ws_url

        validate_okx_ws_url(self.ws_url, ("/ws/v5/business",))
        rest, quotes = self._clients(row)
        sess = LiveSession(compat={}, build=self.build, clock=self.clock,
                           method=(row["config"] or {}).get("method") or "v0.2")
        queue: asyncio.Queue = asyncio.Queue()
        stop = asyncio.Event()
        owned: list[asyncio.Task] = []
        start_task: asyncio.Task | None = None
        stopped_by_owner = False
        persisted: dict | None = None

        def startup() -> None:
            sess.compat = instrument_compat(rest)  # metadata acquisition belongs to the owned startup
            if sess.cancel_requested:
                sess.note("start_cancelled", phase="METADATA")
                return
            sess.start(persisted, history_fetcher(rest, lambda: sess.cancel_requested))

        try:
            persisted = store.load_state()
            owned.append(asyncio.create_task(self._ws_loop(queue, stop)))
            start_task = asyncio.create_task(asyncio.to_thread(startup))
            while not start_task.done():
                await asyncio.wait({start_task}, timeout=self.save_seconds)
                ctl = self._heartbeat(conn, store, sess, quotes)  # fence loss raises PermissionError
                if ctl["stop_requested"]:
                    sess.cancel_requested = True
            start_task.result()
            if sess.cancel_requested:
                stopped_by_owner = True  # Stop observed during startup: never enter LIVE
            else:
                store.save(sess)
                owned.append(asyncio.create_task(self._quote_loop(quotes, queue, stop)))
                stopped_by_owner = await self._live_loop(conn, row, store, sess, queue, quotes)
        finally:
            stop.set()
            if start_task is not None and not start_task.done():
                sess.cancel_requested = True  # cooperative: the thread returns at its next bounded unit
                await asyncio.wait({start_task})
            if owned:  # owned loops observe ``stop`` at their next bounded unit (one poll / a 5 s receive wait)
                _, late = await asyncio.wait(owned, timeout=OWNED_TASK_GRACE_SECONDS)
                for tk in late:
                    tk.cancel()
                await asyncio.gather(*owned, return_exceptions=True)
        if sess.driver is not None:
            sess.on_connection("STOPPED", self.clock())  # entry not verifiable while stopped; never alerted
        sess.status = "STOPPED"
        if sess.driver is not None and sess.epoch is not None:
            store.save(sess)
        conn.execute("UPDATE adviser_live_sessions SET status = 'stopped', stopped_at = now(), phase = 'STOPPED', "
                     "lease_owner = NULL, lease_expires_at = NULL, progress = %s WHERE session_id = %s "
                     "AND lease_generation = %s", (Jsonb(sess.progress), store.sid, store.gen))
        if stopped_by_owner:
            log.info("%s: stopped by the Owner", store.sid)

    async def _live_loop(self, conn, row, store: LiveStore, sess: LiveSession, queue: asyncio.Queue, quotes) -> bool:
        """Live ticks until Stop (True) or the bounded test tick budget (False). Stop is read BEFORE a batch is
        processed, so nothing received after an observed Stop becomes advice or an alert."""
        ticks, last_save, reassess_seen = 0, time.monotonic(), row["reassess_requested"]
        while True:
            await asyncio.sleep(self.tick_seconds)
            ctl = conn.execute("SELECT stop_requested, reassess_requested FROM adviser_live_sessions "
                               "WHERE session_id = %s", (store.sid,)).fetchone()
            if ctl["stop_requested"]:
                return True
            now = self.clock()
            batch = []
            while not queue.empty():
                batch.append(queue.get_nowait())
            batch.sort(key=lambda x: x[2])  # receipt order across the WebSocket and quote loops (stable)
            for kind, payload, received in batch:
                if kind == "bar":
                    sess.on_live_bar(payload[0], payload[1], payload[2], payload[3], received)
                elif kind == "quote":
                    sess.on_quote(payload, received)
                elif kind == "conn":
                    sess.on_connection(payload, received)
            sess.tick(now)
            ticks += 1
            if ctl["reassess_requested"] != reassess_seen:
                reassess_seen = ctl["reassess_requested"]
                sess.driver.advance(now, record_noop=True)  # current assessment only; never rewrites history
                sess.note("manual_reassess")
            if time.monotonic() - last_save >= self.save_seconds:
                store.save(sess)
                self._heartbeat(conn, store, sess, quotes)
                last_save = time.monotonic()
            if self.max_ticks is not None and ticks >= self.max_ticks:
                return False

    def _heartbeat(self, conn, store: LiveStore, sess: LiveSession, quotes) -> dict:
        stats = getattr(quotes, "stats", None)
        conn.execute("""INSERT INTO workers (worker_id, host, pid, current_run) VALUES (%s, %s, %s, %s)
                        ON CONFLICT (worker_id) DO UPDATE SET heartbeat_at = now(), current_run = excluded.current_run""",
                     (self.worker_id, socket.gethostname(), os.getpid(), store.sid))
        row = conn.execute(
            """UPDATE adviser_live_sessions SET lease_expires_at = now() + make_interval(secs => %s),
                   heartbeat_at = now(), progress = %s, connection = %s, phase = %s
               WHERE session_id = %s AND lease_owner = %s AND lease_generation = %s AND status = 'running'
               RETURNING stop_requested, reassess_requested""",
            (self.lease_seconds, Jsonb(sess.progress), Jsonb({"connected": sess.connected,
                                                              "last_receipt": _iso(sess.last_receipt),
                                                              "quotes": stats.doc() if stats else None}),
             sess.status, store.sid, self.worker_id, store.gen)).fetchone()
        if row is None:
            raise PermissionError("live session lease lost (fenced)")
        return row

    async def _quote_loop(self, quotes, queue: asyncio.Queue, stop: asyncio.Event) -> None:
        while not stop.is_set():
            q = await asyncio.to_thread(quotes.poll)  # sequential: never overlapping requests; paced <= 1/s
            if q is not None:
                queue.put_nowait(("quote", q, q.received_at))

    async def _ws_loop(self, queue: asyncio.Queue, stop: asyncio.Event) -> None:
        """Owned candle subscription. Connection changes are queued with their local receipt time and taped by the
        session loop in receipt order (never mutated from here)."""
        from ..recorder.okx_live import websockets_connect

        connect = self.ws_connect or websockets_connect
        backoff = 1.0
        up = False
        while not stop.is_set():
            try:
                ws = await connect(self.ws_url)
            except Exception:  # noqa: BLE001 - visible disconnection, retried with bounded backoff
                if up:
                    queue.put_nowait(("conn", "DISCONNECTED", self.clock()))
                    up = False
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30.0)
                continue
            backoff = 1.0
            try:
                await ws.send(json.dumps({"op": "subscribe", "args": [{"channel": ch, "instId": inst}
                                                                      for ch, inst, _ in WS_CHANNELS]}))
                queue.put_nowait(("conn", "CONNECTED", self.clock()))
                up = True
                last_ping = time.monotonic()
                while not stop.is_set():
                    try:
                        text = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    except TimeoutError:
                        if time.monotonic() - last_ping > 20:
                            await ws.send("ping")
                            last_ping = time.monotonic()
                        continue
                    received = self.clock()  # local receipt immediately after the read returns
                    for fam, t, ohlc, vol in parse_ws_candle(text):
                        queue.put_nowait(("bar", (fam, t, ohlc, vol), received))
            except Exception:  # noqa: BLE001 - visible as a taped disconnection
                pass
            finally:
                if up:
                    queue.put_nowait(("conn", "DISCONNECTED", self.clock()))
                    up = False
                try:
                    await ws.close()
                except Exception:  # noqa: BLE001
                    pass
