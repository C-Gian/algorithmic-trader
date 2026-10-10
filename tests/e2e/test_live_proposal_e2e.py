"""Cockpit clarity (E2E, synthetic payloads only): the main panel answers "Che cosa propone il sistema adesso?" from the
authoritative backend state alone — no view, waiting without a call (scenario levels never named entry/target/stop),
AVAILABLE (admissible band only then), CLOSED, UNVERIFIED, a terminal thesis, a terminated call in recent_calls, a
non-current session through the REAL ``live_status`` boundary, and an unknown status never shown as available."""

from __future__ import annotations

import json
import re
import sys

import pytest
from playwright.sync_api import expect

from test_live_call_history_e2e import call_view, live
from test_ui_smoke import ROOT, browser, evidence_dir, stack  # noqa: F401

pytestmark = [pytest.mark.e2e, pytest.mark.db]
sys.path.insert(0, str(ROOT / "tests"))
from test_adviser_correction_live import _Conn, _row  # noqa: E402

from algotrader.adviser import api as adv_api  # noqa: E402

LOCAL = re.compile(r"\d{2}/\d{2}/\d{4}, \d{2}:\d{2}:\d{2} \S+")


def waiting_view() -> dict:
    st = live("live-R1", "S1", None)
    mv = st["view"]["market_view"]
    mv.update(table_row="CONDITIONAL_SCENARIO", principal={
        "scenario_id": "AL-1", "family": "A", "direction": "LONG", "antecedent": "A LONG confirmed",
        "trigger_level": None, "invalidation_level": "99700.0", "conditional_target": "100900", "alternative": "",
        "expires_at": None, "candidate_domain": "", "status": "CONFIRMED", "destination": "100900"})
    st["view"]["scenarios"] = [{
        "scenario_id": "AL-1", "family": "A", "family_text": "x", "direction": "LONG", "status": "CONFIRMED",
        "antecedent": "a", "trigger_level": None, "invalidation_level": "99700.0", "destination": "100900",
        "destination_type": "LANDMARK", "original_expiry": "2026-10-10T12:00:00Z", "confirmed_at": None,
        "confirmed_deadline": None, "progress_check_at": None, "owner": None, "discovery_owner": None,
        "entry_state": "WAIT", "call_id": None,
        "waiting": {"text": "t", "corridor": ["99900", "100049.9"], "stop_V": "99700.0", "target_now": "100700.0",
                    "target_at_confirmation": "100700.0", "wait_until": "2026-10-10T10:30:00Z",
                    "hard_deadline": "2026-10-10T12:00:00Z", "remaining_wait_minutes": None, "blockers": [],
                    "caps": [], "phase": "WAIT_RESPONSE",
                    "response": {"reference_bar": "b", "H0": "100008", "L0": "99990", "published_at": "2026-10-10T09:04:01Z",
                                 "recovery_close": "100008.1", "recovery_rule": "RULE-R", "contradiction_rule": "RULE-C",
                                 "bars_checked": 0}}}]
    return st


def armed_v02_view() -> dict:
    st = live("live-R1", "S1", None)
    st["view"]["market_view"].update(table_row="ARMED_SCENARIO", expected_direction="DOWN", principal={
        "scenario_id": "att-1", "family": "A", "direction": "SHORT", "antecedent": "A SHORT armed",
        "trigger_level": "99500", "invalidation_level": "100300", "conditional_target": "98800", "alternative": "",
        "expires_at": None, "candidate_domain": ""})
    st["view"].pop("scenarios")
    return st


def with_call(**kw) -> dict:
    c = call_view("c1", 3, entry=kw.pop("entry", "AVAILABLE"))
    c.update(kw)
    return live("live-R1", "S1", c)


def not_current() -> dict:
    st = adv_api.live_status(_Conn(_row(status="stopped")))
    v = st["view"]
    base = live("live-R1", "S1", None)["view"]
    v.update({k: base[k] for k in ("origin", "run_id", "clock", "recent_calls", "attempts", "levels", "chart", "notes",
                                   "counters", "market_view", "lenses", "readiness", "box")})
    v["call"].update({"thesis_status": "ONGOING", "expected_minutes": [30, 180], "duration_window": [30, 180],
                      "progress_check_at": "2026-10-10T09:30:00Z", "premise": "p", "limiting_landmark": None,
                      "revision": 1, "hard_deadline": "2026-10-10T12:00:00Z", "issue_reference": "100"})
    return json.loads(json.dumps(st, default=str))


def no_view() -> dict:
    st = live("live-R1", "S1", None)
    st.update(session=None, state="STOPPED", running=False, current=False, view=None)
    return st


def test_main_panel_states_follow_only_the_authoritative_backend_state(stack, browser, evidence_dir):  # noqa: F811
    ctx = browser.new_context(viewport={"width": 1280, "height": 1000}, timezone_id="Europe/Rome")
    page = ctx.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    cur = {"body": no_view()}
    page.route("**/api/adviser/live", lambda r: r.fulfill(status=200, body=json.dumps(cur["body"]),
                                                          headers={"content-type": "application/json"}))
    panel = page.get_by_test_id("live-call")

    def show(body: dict, state: str) -> None:
        cur["body"] = body
        expect(panel).to_have_attribute("data-state", state, timeout=10_000)

    page.goto(f"{stack.base}/#market")
    expect(panel).to_have_attribute("data-state", "NO_VIEW", timeout=15_000)
    expect(page.get_by_test_id("live-no-view")).to_have_text("Nessuna valutazione in corso")
    expect(page.get_by_test_id("live-expected")).to_have_text("Non disponibile")

    # waiting without a call: expectation, condition, scenario destination/invalidation — never entry/target/stop
    show(waiting_view(), "WAITING")
    expect(page.get_by_test_id("live-no-trade")).to_have_text("In attesa — nessun ingresso proposto")
    expect(page.get_by_test_id("live-expected")).to_have_text("Rialzo")
    expect(page.get_by_test_id("live-direction")).to_contain_text("(condizionale)")
    expect(page.get_by_test_id("live-condition")).to_contain_text("ripresa locale")
    levels = page.get_by_test_id("live-scenario-levels")
    expect(levels).to_contain_text("100900")
    expect(levels).to_contain_text("non è un target operativo")
    expect(levels).to_contain_text("99700.0")
    expect(levels).to_contain_text("non è uno stop")
    for word in ("Target operativo", "Stop indicato", "Fascia d'ingresso"):
        expect(panel).not_to_contain_text(word)
    expect(page.get_by_test_id("live-updated")).to_have_text(LOCAL)
    expect(page.get_by_test_id("live-proposal-details")).to_contain_text("RULE-R")  # exact rule kept in the details

    show(armed_v02_view(), "WAITING")
    expect(page.get_by_test_id("live-condition")).to_have_text("Serve l'innesco: una chiusura oltre 99500.")
    expect(page.get_by_test_id("live-expected")).to_have_text("Ribasso")

    # AVAILABLE: the admissible band appears only now (panel and chart)
    show(with_call(), "AVAILABLE")
    expect(page.get_by_test_id("live-entry")).to_have_text("Ingresso disponibile secondo il sistema")
    expect(page.get_by_test_id("live-admissible")).to_have_text("96 – 99")
    expect(page.get_by_test_id("live-target")).to_have_text("120")
    expect(page.get_by_test_id("live-stop-guidance")).to_have_text("90")
    expect(page.get_by_test_id("live-deadline")).to_have_text(LOCAL)
    expect(page.get_by_test_id("live-thesis")).to_have_text("ancora valida")
    expect(page.get_by_test_id("live-direction")).to_contain_text("Indicazione di acquisto")
    expect(page.locator(".band-admissible")).to_have_count(1)
    expect(page.get_by_test_id("live-entry-consequence")).to_have_count(0)
    expect(page.get_by_test_id("live-call-levels-note")).to_have_count(0)
    shot = page.get_by_test_id("live-call")
    shot.screenshot(path=str(evidence_dir / "proposal-test-available.png"))

    # CLOSED: no usable band; the recorded reason in plain Italian; last band kept only as history in the details
    show(with_call(entry="CLOSED", entry_reasons=["PRICE_OUTSIDE_STRUCTURAL_AREA"]), "CLOSED")
    expect(page.get_by_test_id("live-entry")).to_have_text("Ingresso non disponibile adesso")
    expect(page.get_by_test_id("live-admissible")).to_have_count(0)
    expect(page.get_by_test_id("live-entry-reasons")).to_have_text("prezzo fuori dall'area d'ingresso")
    expect(page.locator(".band-admissible")).to_have_count(0)
    expect(page.get_by_test_id("live-call-technical")).to_contain_text("non utilizzabile ora")
    expect(page.get_by_test_id("live-entry-consequence")).to_have_count(0)  # CLOSED unchanged
    expect(page.get_by_test_id("live-call-levels-note")).to_have_count(0)
    # two hypothetical perspectives of equal standing; the follower side shows only what a RECOGNISED system text says
    expect(page.get_by_test_id("live-perspectives-note")).to_contain_text("l'app non sa se hai aperto")
    expect(page.get_by_test_id("live-new-entry-title")).to_have_text("Se non hai ancora aperto un'operazione")
    expect(page.get_by_test_id("live-section-following")).to_have_text("Se hai già aperto un'operazione su questa call")
    follow = page.get_by_test_id("live-call-guidance")
    # thesis ONGOING with an unrecognised text: nothing is derived (no hold/exit), the limit is declared
    expect(follow).to_have_attribute("data-kind", "UNKNOWN")
    expect(follow).to_contain_text("nessuna indicazione operativa")
    expect(page.get_by_test_id("live-guidance")).to_have_text("guidance now c1")  # the original stays in the details
    for word in ("mantenere", "mantieni", "uscita", "esci", "chiudi"):
        expect(panel).not_to_contain_text(word)
    # CLOSED with the engine's explicit hold text: translated with the values of that text
    show(with_call(entry="CLOSED", entry_reasons=["PRICE_OUTSIDE_STRUCTURAL_AREA"], guidance=(
        "Thesis ongoing but new entry is closed now (PRICE_OUTSIDE_STRUCTURAL_AREA). If following this call: hold with "
        "stop 99700.0, target 100700.0.")), "CLOSED")
    expect(follow).to_have_attribute("data-kind", "HOLD")
    expect(follow).to_have_text("Il sistema indica di mantenere l'operazione con stop 99.700 e target 100.700.")
    expect(page.get_by_test_id("live-entry")).to_have_text("Ingresso non disponibile adesso")  # not "lost for good"
    expect(page.get_by_test_id("live-call-guidance-basis")).to_contain_text("l'originale è negli approfondimenti")
    # a missing text: declared, never rebuilt from the thesis or the levels
    show(with_call(entry="CLOSED", entry_reasons=["PRICE_OUTSIDE_STRUCTURAL_AREA"], guidance=""), "CLOSED")
    expect(follow).to_have_attribute("data-kind", "MISSING")
    for word in ("mantenere", "uscita"):
        expect(panel).not_to_contain_text(word)
    # AVAILABLE with the engine's entry text: about the entry only, nothing for someone already in
    show(with_call(guidance="Entry still valid now inside the admissible part of 96–99; stop 90, target 120, hard "
                            "deadline 2026-10-10T12:00:00+00:00."), "AVAILABLE")
    expect(follow).to_have_attribute("data-kind", "ENTRY_VALID")
    expect(follow).to_contain_text("Non contiene un'indicazione specifica per chi ha già aperto")
    expect(page.get_by_test_id("live-admissible")).to_have_text("96 – 99")
    for word in ("mantenere", "uscita"):
        expect(panel).not_to_contain_text(word)

    # UNVERIFIED
    show(with_call(entry="UNVERIFIED", entry_reasons=["QUOTE_STALE"], admissible_bounds=None, guidance=(
        "Thesis ongoing; current entry cannot be verified (no fresh quote). Do not treat as ready now.")), "UNVERIFIED")
    expect(page.get_by_test_id("live-entry")).to_have_text("Non è possibile confermare la disponibilità dell'ingresso")
    expect(page.get_by_test_id("live-call-guidance")).to_have_attribute("data-kind", "ENTRY_UNVERIFIED")
    expect(page.get_by_test_id("live-entry-reasons")).to_have_text("quotazione non aggiornata")
    expect(page.get_by_test_id("live-admissible")).to_have_count(0)
    # the practical consequence: no usable entry now, wait for the system to confirm it again; levels belong to the call
    cons = page.get_by_test_id("live-entry-consequence")
    expect(cons).to_have_attribute("data-kind", "QUOTE")
    expect(cons).to_contain_text("Ingresso non verificabile — attendi una quotazione aggiornata.")
    expect(cons).to_contain_text("non presenta un ingresso utilizzabile")
    expect(cons).to_contain_text("confermi di nuovo la disponibilità")
    expect(page.get_by_test_id("live-call-levels-note")).to_contain_text(
        "target e stop da soli non sono una proposta d'ingresso attuale")
    expect(page.get_by_test_id("live-thesis")).to_have_text("ancora valida")  # thesis kept apart from entry

    show(with_call(entry="UNVERIFIED", entry_reasons=["CANDLE_CONNECTION_LOST"], admissible_bounds=None), "UNVERIFIED")
    expect(cons).to_have_attribute("data-kind", "CONNECTION")
    expect(cons).not_to_contain_text("quotazione")

    show(with_call(entry="UNVERIFIED", entry_reasons=["SOMETHING_NEW"], admissible_bounds=None), "UNVERIFIED")
    expect(cons).to_have_attribute("data-kind", "OTHER")
    expect(cons).to_contain_text("Ingresso non verificabile.")
    expect(cons).not_to_contain_text("quotazione")
    expect(cons).not_to_contain_text("attendi")

    # a terminal thesis still in the view (defensive) and a terminated call in recent_calls
    show(with_call(entry="CLOSED", entry_reasons=["THESIS_TERMINAL"], thesis_status="INVALIDATED"), "TERMINAL")
    expect(page.get_by_test_id("live-entry")).to_have_text("Indicazione conclusa — ingresso non disponibile")
    expect(page.get_by_test_id("live-admissible")).to_have_count(0)
    expect(page.get_by_test_id("live-thesis")).to_have_text("conclusa — invalidata")
    done = live("live-R1", "S1", None, recent=[{"call_id": "c1", "family": "A", "direction": "LONG",
                                               "issued_at": "2026-10-10T09:00:00Z", "terminal": "TARGET_REACHED",
                                               "reason": "R", "terminal_at": "2026-10-10T09:40:00Z", "origin": "LIVE"}])
    show(done, "WAITING")
    expect(page.get_by_test_id("live-last-terminal")).to_contain_text("conclusa — target raggiunto")
    expect(page.get_by_test_id("live-entry")).to_have_count(0)
    concluded = page.get_by_test_id("live-call-concluded")
    expect(concluded).to_have_attribute("data-terminal", "TARGET_REACHED")
    expect(concluded.get_by_test_id("live-section-following")).to_have_text("Se hai già aperto un'operazione su questa call")
    expect(page.get_by_test_id("live-concluded-reason")).to_have_text("motivo registrato: R")
    # the call's history is not stored here: its closing text and target are declared missing, never rebuilt
    expect(page.get_by_test_id("live-concluded-guidance")).to_have_attribute("data-kind", "MISSING")
    expect(page.get_by_test_id("live-concluded-target")).to_have_text("non disponibile")
    expect(page.get_by_test_id("live-concluded-separation")).to_contain_text("non prolunga questa call")
    for word in ("mantenere", "chiudi"):
        expect(panel).not_to_contain_text(word)  # the conclusion is never turned into a hold/close order
    expect(panel).to_contain_text("Lettura attuale del mercato")

    # a non-current session through the real presentation boundary (saved entry was AVAILABLE)
    show(not_current(), "UNVERIFIED")
    expect(page.get_by_test_id("live-call-not-current")).to_be_visible()
    expect(page.get_by_test_id("live-admissible")).to_have_count(0)
    expect(page.get_by_test_id("live-entry-reasons")).to_contain_text("sessione non corrente")
    expect(page.locator(".band-admissible")).to_have_count(0)
    cons = page.get_by_test_id("live-entry-consequence")
    expect(cons).to_have_attribute("data-kind", "NOT_CURRENT")
    expect(cons).to_contain_text("la sessione live non è corrente")
    expect(cons).not_to_contain_text("quotazione")  # never promises that waiting for a quote is enough
    expect(page.get_by_test_id("live-call-guidance")).to_have_attribute("data-kind", "NOT_CURRENT")
    expect(page.get_by_test_id("live-call-guidance")).to_contain_text("non è presentato come indicazione attuale")

    # an unrecognised status is never presented as available
    show(with_call(entry="SOMETHING_NEW"), "UNKNOWN")
    expect(page.get_by_test_id("live-entry")).to_contain_text("non considerarlo disponibile")
    expect(page.get_by_test_id("live-admissible")).to_have_count(0)
    assert not errors, errors
    ctx.close()
