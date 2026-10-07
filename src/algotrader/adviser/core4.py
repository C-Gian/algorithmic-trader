"""MP-003 ``btc.context-action.v0.4`` professional fold (implementation ``adviser.core.v4``; state
``algotrader.adviser-state.v4``).

It is the accepted MP-002 v0.3 fold (``core3.AdviserCoreV3``) with ONLY the A pre-confirmation anchor, discovery-owner
and destination domains replaced (MP-003 §§2–4). B/C, qualification/renewal, landmarks/targets, confirmed clocks, the
child entry attempt (IMMEDIATE / RETURN WAIT_PRICE, caps, economics), selection, issued-call protection and the
evaluator are inherited unchanged.

A structural scenario (owner, impulse A/B, birth S15/z, sources, original deadline) carries at most one ACTIVE local
reaction anchor (epoch, source 15m bar, R/K/V, actual publication time and admitted cursor):

* **Local contact.** Before confirmation, a newly admitted complete interval wholly after the active anchor's actual
  publication with LONG low <= V (SHORT high >= V) INVALIDATES that anchor only; an interval straddling the
  publication whose extremum can reach V - the current V, or a superseded V active in the interval's earlier part
  (WP-012 F1) - makes it UNASSESSABLE. The same scenario returns to WATCH (``ANCHOR_LOST``)
  with owner, latch, zones, child budget, birth geometry and original deadline unchanged. A late-admitted interval
  lying in an EARLIER epoch's domain that reaches that epoch's V makes the current anchor UNASSESSABLE (the newer
  anchor was published without that evidence). A dead anchor is never tested again (no inflated counts).
* **Replacement** (``REARM``): only from a 15m bar that completes in the current dispatch, whose market end is at/after
  the lost anchor's contact-interval end, with a clean reaction strictly deeper than the lost R (R > A+z,
  R < B - 0.25 birth S15, allowed 1h context, no opposite EXPANSION); K = that bar's high, V = R - birth z (SHORT
  reflects). It is published at the actual dispatch time/cursor after contacts, structural terminals and the 15m close
  predicates of that dispatch; no interval admitted at or before that publication can confirm it.
* **Supersession** (``REVISE``): without contact, the inherited lower-clean-R revision publishes a new epoch.
* **Destination**: inactive before the first published arm (inherited spend > B+z and the A+z close withdrawal apply);
  from the immutable first-arm publication time/cursor onward a certified complete-interval contact with frozen B ends
  the scenario DESTINATION_REACHED, in WATCH as well as ARMED; an interval straddling that origin which can reach B is
  UNASSESSABLE; a destination and a local-anchor contact in the same interval are UNASSESSABLE (no replacement).
* **Monitoring**: an ever-armed unconfirmed scenario needs complete fresh 1m/15m trade evidence like an armed one
  (missing minute / staleness -> UNASSESSABLE coverage loss).
* After the FIRST confirmation R/K/V are frozen forever (``FROZEN_AT_CONFIRMATION``); every later rule is v0.3.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from . import contracts as sc
from .core import MINUTE, _d, _dt, _iso, _s, dname, tbar
from .core3 import AdviserCoreV3, Scen
from .measures import Bar

STATE_FORMAT = "algotrader.adviser-state.v4"
ANCHOR_HISTORY = 16  # bounded anchor-domain history per scenario (older epochs live in the journal only)


@dataclass
class Scen4(Scen):
    """Scenario with the MP-003 local-anchor state (A only; B/C keep the defaults)."""

    epoch: int = 0  # local anchor epoch under this scenario (0: never armed)
    anchor_status: str = "NONE"  # NONE / ACTIVE / INVALIDATED / UNASSESSABLE / FROZEN_AT_CONFIRMATION
    anchor_pub_at: datetime | None = None  # actual publication of the active (or last) anchor
    anchor_cursor: int | None = None  # admitted factual cursor at that publication
    ever_armed: bool = False
    first_arm_at: datetime | None = None  # immutable destination-monitoring origin (A)
    first_arm_cursor: int | None = None
    prev_anchor: dict | None = None  # last lost / superseded epoch (record-facing, market prices)
    lost_r_t: Decimal | None = None  # lost anchor R (transformed) while WATCH after a loss
    lost_cutoff: datetime | None = None  # end of the latest invalidating / ambiguous interval
    losses: int = 0
    rearms: int = 0

    _DT = Scen._DT + ("anchor_pub_at", "first_arm_at", "lost_cutoff")
    _DEC = Scen._DEC + ("lost_r_t",)


class AdviserCoreV4(AdviserCoreV3):
    SCEN_CLS = Scen4
    STATE_FMT = STATE_FORMAT
    KINDS = sc.KIND_CONTRACTS_V4

    def __init__(self, config) -> None:
        super().__init__(config)
        self.counters["v4"] = {"anchor_losses": {}, "owners_losing_anchor": 0, "replacements": 0,
                               "supersessions": 0, "confirmations_after_replacement": 0,
                               "terminals_without_replacement": 0}

    # ----------------------------------------------------------------------------------------------------------
    # monitoring domains
    # ----------------------------------------------------------------------------------------------------------

    def _monitored(self, s: Scen4) -> bool:
        return super()._monitored(s) or (s.family == "A" and s.ever_armed)

    def _scen_interval(self, s: Scen4, m: Any, t: datetime) -> None:
        if s.family != "A" or s.status not in ("WATCH", "ARMED"):
            super()._scen_interval(s, m, t)  # B/C and confirmed A: v0.3 unchanged
            return
        if not s.ever_armed:
            return  # before the first published arm: no destination/local monitoring (spend/withdrawal at 15m)
        first = s.first_arm_at
        if isinstance(m, tuple):
            if m[1] + MINUTE > first:
                self._scen_end(s, "UNASSESSABLE", f"REQUIRED_MONITORING_GAP:{m[2]}", t, coverage_from=m[1])
            return
        if m.end <= first:
            return  # wholly before the destination-monitoring origin
        _, h_t, l_t, _ = tbar(m, s.d)
        hit_d = h_t >= s.dest_t
        if m.start < first and hit_d:
            self._scen_end(s, "UNASSESSABLE", f"FIRST_ARM_DESTINATION_CONTACT_TIME_AMBIGUOUS:{m.rid}", t)
            return
        local = self._local_contact(s, m, l_t) if s.status == "ARMED" else None
        if hit_d and local is not None:
            self._scen_end(s, "UNASSESSABLE", f"DESTINATION_AND_LOCAL_ANCHOR_CONTACT_SAME_INTERVAL:{m.rid}", t)
            return
        if hit_d:
            self._scen_end(s, "DESTINATION_REACHED", f"DESTINATION_CONTACT:{m.rid}", t)
            return
        if local is not None:
            self._anchor_lost(s, local[0], local[1], m, t)

    def _local_contact(self, s: Scen4, m: Bar, l_t: Decimal) -> tuple[str, str] | None:
        """The local-anchor verdict of one interval against EVERY anchor domain it overlaps (WP-012 F1).

        A domain is [publication, end) of one epoch: the current one is open; a superseded one ended at the actual
        publication of its successor. Domains that ended by a loss belong to anchors already dead (their contact was
        processed then): they are never re-tested. Only domains actually overlapping the interval are tested, so an
        old V is never applied outside its own active time (no resurrection of an inactive level), and no intrabar
        order is inferred:
        * only the current domain, interval wholly after its publication, V reached -> certified contact;
        * the interval straddles the current publication and reaches the current V or a superseded V active in its
          earlier part -> the current anchor is UNASSESSABLE (a touch of the old V cannot be certified to have
          happened after the supersession, and the new anchor's source bar ended before this interval);
        * the interval ends at/before the current publication (late admission) and reaches a superseded V active
          during it -> UNASSESSABLE (the newer anchor was published without that evidence)."""
        pub = s.anchor_pub_at
        touched: list[int] = []
        for since, v, epoch, end, *how in s.v_hist:
            if epoch != s.epoch and (how and how[0] == "LOST"):
                continue
            if not (_dt(since) < m.end and (end is None or _dt(end) > m.start)):
                continue  # this epoch's active domain does not overlap the interval
            if l_t <= Decimal(v):
                touched.append(epoch)
        if not touched:
            return None
        if m.start >= pub:  # wholly inside the current domain (no earlier domain can overlap it)
            return "INVALIDATED", f"V_CONTACT:{m.rid}"
        if m.end <= pub:
            return "UNASSESSABLE", f"LATE_CONTACT_WITH_EARLIER_ANCHOR_EPOCH_{min(touched)}:{m.rid}"
        if s.epoch in touched:
            return "UNASSESSABLE", f"ANCHOR_CONTACT_TIME_AMBIGUOUS:{m.rid}"
        return "UNASSESSABLE", f"SUPERSEDED_ANCHOR_CONTACT_TIME_AMBIGUOUS_EPOCH_{min(touched)}:{m.rid}"

    # ----------------------------------------------------------------------------------------------------------
    # anchor publication / loss
    # ----------------------------------------------------------------------------------------------------------

    def _anchor_summary(self, s: Scen4, status: str, reason: str | None, interval: Bar | None) -> dict:
        d = s.d
        return {"epoch": str(s.epoch), "status": status, "reason": reason, "source": s.anchor,
                "R": _s(s.r_t * d if s.r_t is not None else None), "K": _s(s.k_t * d if s.k_t is not None else None),
                "V": _s(s.v_t * d if s.v_t is not None else None), "published_at": _iso(s.anchor_pub_at),
                "published_cursor": None if s.anchor_cursor is None else str(s.anchor_cursor),
                "interval": interval.rid if interval is not None else None,
                "interval_end": _iso(interval.end) if interval is not None else None}

    def _close_domain(self, s: Scen4, t: datetime, how: str) -> None:
        """End the current anchor's active domain at ``t``; ``how`` is SUPERSEDED (a later domain may still have to
        consider it for overlapping intervals) or LOST (dead anchor: never re-tested)."""
        if s.v_hist and s.v_hist[-1][3] is None:
            s.v_hist[-1][3] = _iso(t)
            s.v_hist[-1][4:] = [how]

    def _anchor_lost(self, s: Scen4, status: str, reason: str, m: Bar, t: datetime) -> None:
        s.prev_anchor = self._anchor_summary(s, status, reason, m)
        s.lost_r_t, s.lost_cutoff = s.r_t, m.end
        self._close_domain(s, t, "LOST")
        s.status, s.anchor_status = "WATCH", status
        s.k_t = s.v_t = s.r_t = s.anchor = s.anchor_h_t = s.arm_at = s.arm_seq = None
        if self.window == "EVALUATION":
            v4 = self.counters["v4"]
            v4["anchor_losses"][status] = v4["anchor_losses"].get(status, 0) + 1
            if s.losses == 0:
                v4["owners_losing_anchor"] += 1
        s.losses += 1
        self._emit_scen(s, "ANCHOR_LOST", reason, t)
        self._touch()

    def _publish_anchor(self, s: Scen4, transition: str, r_t: Decimal, k_t: Decimal, rid: str, t: datetime) -> None:
        if transition == "REVISE":
            s.prev_anchor = self._anchor_summary(s, "SUPERSEDED", "LOWER_CLEAN_REACTION_REANCHOR", None)
            self._close_domain(s, t, "SUPERSEDED")
        s.epoch += 1
        s.r_t, s.anchor, s.anchor_h_t = r_t, rid, k_t
        s.k_t, s.v_t = k_t, r_t - s.z
        s.status, s.arm_at, s.arm_seq = "ARMED", t, self.seq
        s.anchor_pub_at, s.anchor_cursor, s.anchor_status = t, self.cursor, "ACTIVE"
        s.v_hist = (s.v_hist + [[_iso(t), str(s.v_t), s.epoch, None]])[-ANCHOR_HISTORY:]
        reason = None
        if not s.ever_armed:
            s.ever_armed, s.first_arm_at, s.first_arm_cursor = True, t, self.cursor
            self.counters["armed"]["A"] += 1
        elif transition == "REARM":
            s.lost_r_t = s.lost_cutoff = None
            s.rearms += 1
            reason = "NEW_COMPLETE_STRICTLY_DEEPER_CLEAN_REACTION"
            if self.window == "EVALUATION":
                self.counters["v4"]["replacements"] += 1
        else:
            reason = "LOWER_CLEAN_REACTION_REANCHOR"
            if self.window == "EVALUATION":
                self.counters["v4"]["supersessions"] += 1
        self._emit_scen(s, transition, reason, t)

    # ----------------------------------------------------------------------------------------------------------
    # 15m close processing (A pre-confirmation reaction rules; MP-003 §§3-4)
    # ----------------------------------------------------------------------------------------------------------

    def _a_close(self, b: Bar, t: datetime) -> None:
        p = self.p
        for s in sorted([x for x in self.scen.values() if x.family == "A"], key=lambda x: x.sid):
            if s.born_at >= t:
                continue
            o_t, h_t, l_t, c_t = tbar(b, s.d)
            if self._owner_active(s) and c_t > s.b_t + s.z:
                s.b_broken = True  # the impulse destination zone is BROKEN by a close beyond its far edge
            if s.status == "CONFIRMED":
                continue  # no post-confirmation anchor revision
            s.bars_seen += 1
            if s.prev_close_t is not None and c_t < s.prev_close_t:
                s.lower_close = True
            s.prev_close_t = c_t
            if s.status == "WATCH" and not s.ever_armed and h_t > s.b_t + s.z:
                self._scen_end(s, "EXPIRED", "SPENT_HIGH_BEYOND_B_BEFORE_REACTION", t)
                continue
            if c_t <= s.a_t + s.z:
                self._scen_end(s, "WITHDRAWN", "CLOSE_AT_OR_BEYOND_A_PLUS_ZONE", t)
                continue
            if s.status == "WATCH" and not s.ever_armed:
                if s.r_t is None or l_t <= s.r_t:
                    s.r_t, s.anchor, s.anchor_h_t = l_t, b.rid, h_t
                reaction = (s.lower_close and s.r_t < s.b_t - p.a_reaction_min * s.s15 and s.r_t > s.a_t + s.z)
                if reaction:
                    if self._a_context_ok(s, t):
                        self._publish_anchor(s, "ARM", s.r_t, s.anchor_h_t, s.anchor, t)
                elif s.bars_seen >= p.a_reaction_max_bars:
                    self._scen_end(s, "EXPIRED", "NO_QUALIFYING_REACTION_WITHIN_8_BARS", t)
            elif s.status == "WATCH":  # ever armed: the local anchor was lost; only a prospective replacement
                if (s.lost_cutoff is not None and b.end >= s.lost_cutoff and l_t < s.lost_r_t
                        and l_t > s.a_t + s.z and l_t < s.b_t - p.a_reaction_min * s.s15 and s.lower_close
                        and self._a_context_ok(s, t)):
                    self._publish_anchor(s, "REARM", l_t, h_t, b.rid, t)
            elif l_t <= s.r_t and l_t > s.a_t + s.z:
                self._publish_anchor(s, "REVISE", l_t, h_t, b.rid, t)

    # ----------------------------------------------------------------------------------------------------------
    # confirmation / terminals bookkeeping
    # ----------------------------------------------------------------------------------------------------------

    def _confirm(self, s: Scen4, m: Bar, t: datetime) -> None:
        if s.family == "A":
            s.anchor_status = "FROZEN_AT_CONFIRMATION"
            if s.rearms and self.window == "EVALUATION":
                self.counters["v4"]["confirmations_after_replacement"] += 1
        super()._confirm(s, m, t)

    def _scen_end(self, s: Scen4, state: str, reason: str, t: datetime, coverage_from: datetime | None = None) -> None:
        if (s.sid in self.scen and s.family == "A" and s.ever_armed and s.status == "WATCH"
                and self.window == "EVALUATION"):
            self.counters["v4"]["terminals_without_replacement"] += 1
        super()._scen_end(s, state, reason, t, coverage_from=coverage_from)

    # ----------------------------------------------------------------------------------------------------------
    # records / views
    # ----------------------------------------------------------------------------------------------------------

    def _scen_extra(self, s: Scen4) -> dict:
        if s.family != "A":
            return {"anchor_epoch": None, "anchor_status": None, "anchor_source": None, "anchor_published_at": None,
                    "anchor_published_cursor": None, "previous_anchor": None, "ever_armed": None,
                    "destination_monitoring_from": None, "destination_monitoring_cursor": None}
        return {"anchor_epoch": s.epoch or None, "anchor_status": s.anchor_status,
                "anchor_source": s.anchor if s.status != "WATCH" else None,
                "anchor_published_at": s.anchor_pub_at, "anchor_published_cursor": s.anchor_cursor,
                "previous_anchor": s.prev_anchor, "ever_armed": s.ever_armed,
                "destination_monitoring_from": s.first_arm_at, "destination_monitoring_cursor": s.first_arm_cursor}

    def _antecedent(self, s: Scen4) -> str:
        if s.family == "A" and s.status == "WATCH" and s.ever_armed:
            lost = s.prev_anchor or {}
            return (f"scenario under observation; waiting for a new completed reaction strictly beyond the lost "
                    f"anchor R {lost.get('R')} (anchor {lost.get('epoch')} {str(lost.get('status')).lower()}); "
                    f"continuation toward {s.dest_t * s.d} is not confirmed and this is not an entry")
        return super()._antecedent(s)

    def scenarios_view(self, t: datetime | None) -> list[dict]:
        rows = super().scenarios_view(t)
        for row in rows:
            s = self.scen.get(row["scenario_id"])
            if s is None or s.family != "A":
                continue
            row["anchor"] = {"epoch": s.epoch or None, "status": s.anchor_status,
                             "published_at": _iso(s.anchor_pub_at), "ever_armed": s.ever_armed,
                             "destination_monitoring_from": _iso(s.first_arm_at), "previous": s.prev_anchor,
                             "replacements": s.rearms, "losses": s.losses}
            if s.status == "WATCH" and s.ever_armed:
                row["observing"] = {"text": "Scenario under observation; waiting for a new completed reaction "
                                            "(no anchor, no entry, no call).",
                                    "lost_anchor": s.prev_anchor, "original_expiry": _iso(s.setup_deadline)}
        return rows

    def inspect(self) -> dict:
        out = super().inspect()
        out["method_semantics"] = ("MP-003 v0.4: structural scenarios + local A reaction anchors before confirmation "
                                   "+ child entry attempts")
        out["anchors"] = {s.sid: {"epoch": s.epoch, "status": s.anchor_status, "direction": dname(s.d),
                                  "published_at": _iso(s.anchor_pub_at), "ever_armed": s.ever_armed,
                                  "destination_monitoring_from": _iso(s.first_arm_at)}
                          for s in sorted(self.scen.values(), key=lambda x: x.sid) if s.family == "A"}
        return out


_ = (_d,)
