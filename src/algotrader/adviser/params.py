"""Typed, exact view of the packaged MP-001 parameter register (no value is defined here).

Every number comes from ``method/MP-001-PARAMETERS.json`` (parsed with Decimal, never binary floats). The only
constants stated in this module are the few the normative rules PROSE states without a register key; each names its
MP-001 section so a reviewer can check it (``PROSE``).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from functools import lru_cache

from .identity import REGISTER_FILE

# Rules-prose constants without a register key (MP-001 v0.2 text is normative; JSON does not replace it).
PROSE = {
    "b_attempt_lifetime_minutes": 60,  # §6 B: attempt deadline = min(box expiry, break publication + 1h)
    "c_attempt_lifetime_minutes": 30,  # §6 C: attempt expires min(box expiry, reclaim publication + 30m) (= register)
    "a_withdraw_close_at_or_below_A_plus_z": True,  # §6 A: close <= A+z withdraws before trigger
    "dislocation_bps_unit": 10000,  # §7: b = 10000*(trade-ref)/ref
}


def _dec(x) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


@dataclass(frozen=True)
class Params:
    raw: dict
    median_tr: int
    ctx_transitions: int
    ctx_disp: Decimal
    ctx_eff: Decimal
    ph_short: int
    ph_prev: int
    ph_cr_max: Decimal
    ph_comp_er_max: Decimal
    ph_exp_er_min: Decimal
    ph_exp_disp: Decimal
    ph_rot_er8_max: Decimal
    ph_exp_transitions: int
    ph_reaction_transitions: int
    pivot_left: int
    pivot_right: int
    zone_frac: Decimal
    zone_min_ticks: int
    max_pivots: int
    pivot_age_15m: timedelta
    pivot_age_1h: timedelta
    period_age: dict[str, timedelta]
    a_transitions: int
    a_er_min: Decimal
    a_disp: Decimal
    a_reaction_min: Decimal
    a_reaction_max_bars: int
    a_hard: timedelta
    a_expected: tuple[int, int]
    a_source_bars: int
    a_lifetime: timedelta
    box_prior: int
    box_er_max: Decimal
    box_width: tuple[Decimal, Decimal]
    box_touch: int
    box_lifetime: timedelta
    b_retest_bars: int
    b_hard: timedelta
    b_expected: tuple[int, int]
    b_lifetime: timedelta
    c_lifetime: timedelta
    c_hard: timedelta
    c_expected: tuple[int, int]
    area_scale: Decimal
    rr_min: Decimal
    trigger_ticks: int
    residual_min: dict[str, int]
    fresh_1m: timedelta
    fresh_15m: timedelta
    fresh_1h: timedelta
    fresh_4h: timedelta
    fresh_day: timedelta
    fresh_week: timedelta
    fresh_month: timedelta
    fresh_quote: timedelta
    ev_pre: timedelta
    ev_post_min: timedelta
    fee_bps: Decimal
    allowance_bps: Decimal
    stress_allowance_bps: Decimal
    hist_k_bps: Decimal
    live_fee_bps: Decimal
    live_slip_bps: Decimal
    progress_fraction: Decimal
    progress_min_scale: Decimal
    eval_primary_delay: int
    eval_delay_sens: tuple[int, ...]
    eval_exit_delay: int
    eval_tail_minutes: int
    ready_15m: int
    ready_1h: int
    vol_bars: int
    disl_min_bps: Decimal
    disl_mult: Decimal
    disl_prior: int
    retention: dict[str, int]

    def hard(self, family: str) -> timedelta:
        return {"A": self.a_hard, "B": self.b_hard, "C": self.c_hard}[family]

    def expected(self, family: str) -> tuple[int, int]:
        return {"A": self.a_expected, "B": self.b_expected, "C": self.c_expected}[family]


@lru_cache(maxsize=1)
def load() -> Params:
    r = json.loads(REGISTER_FILE.read_text(encoding="utf-8"), parse_float=Decimal)
    sc, tac, ph, lv = r["scale"], r["tactical"], r["phase"], r["levels"]
    co, cr, fe, en, fr = r["continuation"], r["compression_retest"], r["failed_exit"], r["entry"], r["freshness"]
    ev, ex, pr, eva, rd = r["events"], r["execution"], r["progress"], r["evaluation"], r["readiness"]
    if co["setup_lifetime_minutes"] != 120 or fe["setup_lifetime_minutes"] != PROSE["c_attempt_lifetime_minutes"]:
        raise RuntimeError("register lifetimes disagree with the rules prose")
    return Params(
        raw=r, median_tr=int(sc["median_tr_bars"]), ctx_transitions=int(tac["transitions"]),
        ctx_disp=_dec(tac["direction_displacement_scale"]), ctx_eff=_dec(tac["efficiency_min"]),
        ph_short=int(ph["short_tr_count"]), ph_prev=int(ph["preceding_tr_count"]),
        ph_cr_max=_dec(ph["compression_ratio_max"]), ph_comp_er_max=_dec(ph["compression_er6_max"]),
        ph_exp_er_min=_dec(ph["expansion_er6_min"]), ph_exp_disp=_dec(ph["expansion_displacement_scale"]),
        ph_rot_er8_max=_dec(ph["rotation_er8_max"]), ph_exp_transitions=int(ph["expansion_displacement_transitions"]),
        ph_reaction_transitions=int(ph["reaction_close_transitions"]),
        pivot_left=int(lv["pivot_left"]), pivot_right=int(lv["pivot_right"]), zone_frac=_dec(lv["zone_halfwidth_scale"]),
        zone_min_ticks=int(lv["zone_min_ticks"]), max_pivots=int(lv["max_pivots_per_horizon"]),
        pivot_age_15m=timedelta(hours=int(lv["age_15m_hours"])), pivot_age_1h=timedelta(hours=int(lv["age_1h_hours"])),
        period_age={"1d": timedelta(seconds=int(fr["trade_day_seconds"])),
                    "1w": timedelta(seconds=int(fr["trade_week_seconds"])),
                    "1mo": timedelta(seconds=int(fr["trade_month_seconds"]))},
        a_transitions=int(co["impulse_transitions"]), a_er_min=_dec(co["impulse_er_min"]),
        a_disp=_dec(co["impulse_displacement_scale"]), a_reaction_min=_dec(co["reaction_min_scale"]),
        a_reaction_max_bars=int(co["reaction_max_15m_bars"]), a_hard=timedelta(hours=int(co["hard_thesis_hours"])),
        a_expected=(int(co["expected_minutes"][0]), int(co["expected_minutes"][1])),
        a_source_bars=int(co["source_bars"]), a_lifetime=timedelta(minutes=int(co["setup_lifetime_minutes"])),
        box_prior=int(cr["box_prior_bars"]), box_er_max=_dec(cr["box_er_max"]),
        box_width=(_dec(cr["box_width_scale"][0]), _dec(cr["box_width_scale"][1])),
        box_touch=int(cr["edge_touch_count"]), box_lifetime=timedelta(hours=int(cr["box_lifetime_hours"])),
        b_retest_bars=int(cr["retest_max_15m_bars"]), b_hard=timedelta(hours=int(cr["hard_thesis_hours"])),
        b_expected=(int(cr["expected_minutes"][0]), int(cr["expected_minutes"][1])),
        b_lifetime=timedelta(minutes=PROSE["b_attempt_lifetime_minutes"]),
        c_lifetime=timedelta(minutes=int(fe["setup_lifetime_minutes"])), c_hard=timedelta(hours=int(fe["hard_thesis_hours"])),
        c_expected=(int(fe["expected_minutes"][0]), int(fe["expected_minutes"][1])),
        area_scale=_dec(en["area_each_side_scale"]), rr_min=_dec(en["net_reward_risk_min"]),
        trigger_ticks=int(en["trigger_offset_ticks"]),
        residual_min={k: int(v) for k, v in en["residual_minimum_minutes"].items()},
        fresh_1m=timedelta(seconds=int(fr["trade_1m_seconds"])), fresh_15m=timedelta(seconds=int(fr["trade_15m_seconds"])),
        fresh_1h=timedelta(seconds=int(fr["trade_1h_seconds"])), fresh_4h=timedelta(seconds=int(fr["trade_4h_seconds"])),
        fresh_day=timedelta(seconds=int(fr["trade_day_seconds"])), fresh_week=timedelta(seconds=int(fr["trade_week_seconds"])),
        fresh_month=timedelta(seconds=int(fr["trade_month_seconds"])),
        fresh_quote=timedelta(seconds=int(fr["live_quote_seconds"])),
        ev_pre=timedelta(minutes=int(ev["pre_minutes"])), ev_post_min=timedelta(minutes=int(ev["post_minimum_minutes"])),
        fee_bps=_dec(ex["base_fee_bps_per_leg"]), allowance_bps=_dec(ex["base_allowance_bps_per_leg"]),
        stress_allowance_bps=_dec(ex["stress_allowance_bps_per_leg"]),
        hist_k_bps=_dec(ex["historical_adequacy_nominal_roundtrip_bps"]),
        live_fee_bps=_dec(ex["live_fee_bps_per_leg"]), live_slip_bps=_dec(ex["live_slippage_bps_per_leg"]),
        progress_fraction=_dec(pr["at_fraction_of_hard_horizon"]), progress_min_scale=_dec(pr["minimum_favorable_scale"]),
        eval_primary_delay=int(eva["primary_delay_seconds"]),
        eval_delay_sens=tuple(int(x) for x in eva["sensitivity_delay_seconds"]),
        eval_exit_delay=int(eva["exit_delay_seconds"]), eval_tail_minutes=int(eva["outcome_tail_minutes"]),
        ready_15m=int(rd["trade_15m_required_bars"]), ready_1h=int(rd["trade_1h_required_bars"]),
        vol_bars=int(r["participation"]["previous_base_volume_bars"]),
        disl_min_bps=_dec(r["dislocation"]["min_abs_bps"]), disl_mult=_dec(r["dislocation"]["median_multiplier"]),
        disl_prior=int(r["dislocation"]["prior_contiguous_matched_slots"]),
        retention={k: int(v) for k, v in r["retention"].items() if isinstance(v, int) and not isinstance(v, bool)},
    )
