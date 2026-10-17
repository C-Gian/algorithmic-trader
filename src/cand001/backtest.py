"""Percorso continuo di una finestra valutata: decisioni alle chiusure 45m, ledger sui minuti.

Ordine a ogni chiusura t: il ledger processa i minuti [cursore, t) (fill, stop/target, uscite dovute),
le sue notifiche aggiornano lo stato del motore, poi il motore decide a t con le sole informazioni
disponibili a t. La finestra parte FLAT; le osservazioni usano tutto il prefisso di input.
"""

from __future__ import annotations

from obs001.aggregate import aggregate
from obs001.minutes import MinuteStore
from obs001.observe import observe

from .config import Candidate, observation_conventions
from .decision import DecisionEngine, PositionView
from .execution import Ledger


def observe_store(store: MinuteStore) -> dict:
    conv = observation_conventions(store.start, store.end)
    bars45 = aggregate(store, conv.bar_ms)
    bars1d = aggregate(store, conv.day_ms)
    observed = observe(bars45, bars1d, conv)
    return {"conv": conv, "bars45": bars45, "bars1d": bars1d, "observed": observed}


def run_window(cand: Candidate, store: MinuteStore, window: tuple[int, int], funding: list[dict], mark: dict[int, float],
               obs: dict | None = None) -> dict:
    start, end = window
    if store.start > start or store.end != end:
        raise ValueError("lo store deve coprire il prefisso e terminare esattamente alla fine della finestra")
    obs = obs or observe_store(store)
    conv = obs["conv"]
    engine = DecisionEngine(cand, obs["bars45"], obs["observed"]["45m"], obs["observed"]["1D"], obs["observed"]["events"]["45m"],
                            store.start, conv.bar_ms, conv.day_ms, window)
    ledger = Ledger(cand, store, window, funding, mark)

    def dispatch() -> None:
        for kind, ep_id, at, outcome, facts in ledger.notices:
            if kind == "ENTRY":
                engine.entry_outcome(ep_id, at, outcome, **facts)
            elif kind == "CLOSE":
                engine.position_closed(ep_id, at, outcome, **facts)
            elif kind == "HALT":
                engine.halt(at)
        ledger.notices.clear()

    for t in range(start, end, conv.bar_ms):
        ledger.advance(t)
        dispatch()
        pos = ledger.position
        view = None if pos is None else PositionView(pos.episode_id, pos.d, pos.entry_time, pos.stop, pos.t, pos.a0)
        actions = engine.on_close(t, view, ledger.pending_entry is not None)
        ledger.accept(actions)
    ledger.advance(end)
    dispatch()
    return {"obs": obs, "engine": engine, "ledger": ledger, "window": window}
