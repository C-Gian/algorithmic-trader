import { CallView, LiveView, reasonText, ScenarioState, ScenarioView } from "../adviser";
import { fmtLocal, fmtTime, humanize } from "../lib/format";
import { Icon } from "../ui/Icon";
import { Badge, cx, Tone } from "../ui/primitives";

// Live cockpit main panel: "Che cosa propone il sistema adesso?". It shows only the authoritative backend state of the
// committed live view: entry availability is call.entry_status (already masked by the API for a non-current session),
// thesis validity is call.thesis_status, a terminated call has left view.call for view.recent_calls. Nothing is inferred
// from direction, quotes or levels. Scenario levels are never called entry, operational target or stop.

const EXPECTED_IT: Record<string, string> = {
  UP: "Rialzo", DOWN: "Ribasso", BALANCED: "Equilibrio", UNCERTAIN: "Incerta", UNAVAILABLE: "Non disponibile",
};

const ROW_IT: Record<string, string> = {
  REQUIRED_CONTEXT_UNAVAILABLE: "Il contesto 15m/1h necessario non è ancora pronto",
  OPPOSING_SCENARIOS: "Gli scenari indicano direzioni opposte",
  ONGOING_CALL: "Segue la call in corso finché la sua premessa regge",
  ARMED_SCENARIO: "Condizionale: una call solo se avviene l'innesco",
  BALANCED_RANGE: "Mercato in equilibrio (range)",
  NO_SUPPORTED_PLAN: "Nessun piano supportato nelle condizioni attuali",
  CONDITIONAL_SCENARIO: "Condizionale: uno scenario supportato in una direzione",
  WATCH_ONLY: "Solo ipotesi in osservazione: né previsione né call",
  NO_QUALIFIED_STRUCTURE: "Nessuna struttura qualificata nelle condizioni attuali",
};

const THESIS_IT: Record<string, string> = {
  ONGOING: "ancora valida", TARGET_REACHED: "conclusa — target raggiunto", INVALIDATED: "conclusa — invalidata",
  TIME_EXPIRED: "conclusa — scaduta", UNASSESSABLE: "conclusa — non valutabile", RETIRED: "conclusa — ritirata",
};

/** Plain Italian for recorded entry reason codes; an unknown code is shown as recorded, never reinterpreted. */
const REASON_IT: Record<string, string> = {
  TOO_LATE: "tempo residuo insufficiente prima della scadenza",
  PRICE_OUTSIDE_STRUCTURAL_AREA: "prezzo fuori dall'area d'ingresso",
  NO_ROOM_AFTER_COSTS: "spazio verso il target insufficiente dopo i costi",
  AT_OR_BEYOND_INVALIDATION: "prezzo al livello di invalidazione o oltre",
  REWARD_RISK_BELOW_MINIMUM: "rapporto rendimento/rischio sotto il minimo",
  AT_OPPOSING_AREA: "prezzo in un'area contraria",
  QUOTE_STALE: "quotazione non aggiornata",
  QUOTE_UNAVAILABLE: "quotazione non disponibile",
  QUOTE_CLOCK_UNCERTAIN: "orario della quotazione incerto",
  CANDLE_CONNECTION_LOST: "connessione ai dati di mercato interrotta",
  CANDLE_CONNECTION_AWAITING_FRESH_BAR: "in attesa di dati nuovi dopo la riconnessione",
  LIVE_SESSION_STOPPED: "sessione live fermata",
  SESSION_NOT_CURRENT: "sessione non corrente",
  RECONSTRUCTED_REQUIRES_FRESH_CALL: "indicazione ricostruita: serve una nuova valutazione live",
  RECONSTRUCTED_CATCH_UP: "recupero dello storico in corso",
  TRADE_15M_NOT_READY: "contesto a 15 minuti non pronto",
  TRADE_1H_NOT_READY: "contesto a 1 ora non pronto",
  TRADE_1M_STALE: "dati a 1 minuto non aggiornati",
  THESIS_TERMINAL: "indicazione conclusa",
};

export function reasonIt(code: string): string {
  return REASON_IT[code.split(":")[0]] ?? `motivo registrato: ${code}`;
}

function Arrow({ d }: { d: string | undefined }) {
  if (d === "UP") return <span className="dir-arrow up" aria-hidden>▲</span>;
  if (d === "DOWN") return <span className="dir-arrow down" aria-hidden>▼</span>;
  return <span className="dir-arrow flat" aria-hidden>◆</span>;
}

/** The single authoritative state of the panel (from the backend fields only). */
export function proposalState(v: LiveView | null): { key: string; text: string; tone: Tone } {
  if (!v) return { key: "NO_VIEW", text: "Nessuna valutazione in corso", tone: "neutral" };
  const c = v.call;
  if (!c) return { key: "WAITING", text: "In attesa — nessun ingresso proposto", tone: "neutral" };
  if (c.thesis_status !== "ONGOING") {
    return { key: "TERMINAL", text: "Indicazione conclusa — ingresso non disponibile", tone: "neutral" };
  }
  if (c.entry_status === "AVAILABLE" && c.presentation !== "NOT_CURRENT") {
    return { key: "AVAILABLE", text: "Ingresso disponibile secondo il sistema", tone: "pos" };
  }
  if (c.entry_status === "CLOSED") return { key: "CLOSED", text: "Ingresso non più disponibile", tone: "neg" };
  if (c.entry_status === "UNVERIFIED" || c.entry_status === "AVAILABLE") {
    return { key: "UNVERIFIED", text: "Non è possibile confermare la disponibilità dell'ingresso", tone: "warn" };
  }
  return { key: "UNKNOWN", text: `Stato dell'ingresso non riconosciuto (${c.entry_status}): non considerarlo disponibile`, tone: "warn" };
}

/** What the principal scenario still needs, from its recorded state; null when the system states nothing. */
function condition(p: ScenarioView, s: ScenarioState | undefined): string | null {
  if (s?.entry_ended) return "Il tentativo d'ingresso di questo scenario si è concluso senza call; lo scenario non è invalidato.";
  if (s?.observing) return "Scenario in osservazione: serve una nuova reazione completa del prezzo.";
  if (s?.waiting?.phase === "WAIT_RESPONSE") {
    return "Scenario confermato: serve una ripresa locale del prezzo (regola esatta negli approfondimenti).";
  }
  if (s?.waiting) {
    return s.waiting.corridor
      ? `Scenario confermato: serve un ritorno del prezzo nel corridoio ${s.waiting.corridor[0]} – ${s.waiting.corridor[1]}.`
      : "Scenario confermato: nessun corridoio di ritorno residuo.";
  }
  const status = s?.status ?? p.status ?? "ARMED";
  const k = s?.trigger_level ?? p.trigger_level;
  if (status === "ARMED" && k) return `Serve l'innesco: una chiusura oltre ${k}.`;
  if (status === "WATCH") return "Si osserva una possibile reazione: nessun innesco ancora definito.";
  return null;
}

function ScenarioCards({ v }: { v: LiveView }) {
  const mv = v.market_view;
  return (
    <>
      {mv?.principal && (
        <div className="call-scenario" data-testid="live-scenario">
          <Badge tone={mv.principal.direction === "LONG" ? "pos" : "neg"}>{mv.principal.direction} {mv.principal.family}{" "}
            {(mv.principal.status ?? "ARMED").toLowerCase()}</Badge>
          <span className="small-text">{mv.principal.antecedent}</span>
        </div>
      )}
      {(v.scenarios ?? []).filter((s) => s.entry_ended).map((s) => (
        <div className="call-waiting" key={`${s.scenario_id}-ended`} data-testid="live-entry-ended">
          <Badge tone="neutral">{s.direction} {s.family} confirmed — entry attempt ended</Badge>
          <p className="small-text">{s.entry_ended!.text} This is not a call and not an invalidation of the scenario.</p>
          <dl className="call-geo">
            <dt>Why</dt><dd>{s.entry_ended!.base === "CORRIDOR" ? "no confirming close could be inside the usable corridor"
              : "no confirming close could be inside the historical economic region"}</dd>
            <dt>Ended at</dt><dd className="mono">{fmtTime(s.entry_ended!.at)}</dd>
            <dt>Scenario</dt><dd>still {s.status.toLowerCase()} · invalid at {s.invalidation_level ?? "—"}</dd>
          </dl>
        </div>
      ))}
      {(v.scenarios ?? []).filter((s) => s.observing).map((s) => (
        <div className="call-waiting" key={s.scenario_id} data-testid="live-observing">
          <Badge tone="neutral">{s.direction} {s.family} — scenario under observation</Badge>
          <p className="small-text">{s.observing!.text} The previous reaction anchor
            {s.observing!.lost_anchor?.V ? ` (stop ${s.observing!.lost_anchor.V})` : ""} was touched before confirmation.
            This is not a call and not an entry: nothing to do now.</p>
          <dl className="call-geo">
            <dt>Narrative destination</dt><dd className="mono">{s.destination ?? "—"}</dd>
            <dt>Observation ends</dt><dd className="mono">{fmtTime(s.observing!.original_expiry)} (original deadline)</dd>
          </dl>
        </div>
      ))}
      {(v.scenarios ?? []).filter((s) => s.waiting).map((s) => (
        <div className="call-waiting" key={s.scenario_id} data-testid="live-waiting">
          <Badge tone="info">{s.direction} {s.family} confirmed — {s.waiting!.phase === "WAIT_RESPONSE"
            ? "waiting for a local recovery" : "waiting for a usable price"}</Badge>
          <p className="small-text">{s.waiting!.text} This is not a call: do not treat it as “enter now”.</p>
          {s.waiting!.response && (
            <dl className="kv-grid small-text" data-testid="live-waiting-response">
              <dt>Return reference</dt><dd className="mono">H0 {s.waiting!.response.H0} · L0 {s.waiting!.response.L0} · published {fmtTime(s.waiting!.response.published_at)}</dd>
              <dt>Call possible only if</dt><dd>{s.waiting!.response.recovery_rule}</dd>
              <dt>Ends this attempt</dt><dd>{s.waiting!.response.contradiction_rule}</dd>
            </dl>
          )}
          <dl className="call-geo">
            <dt>Usable return corridor</dt><dd className="mono">{s.waiting!.corridor ? `${s.waiting!.corridor[0]} – ${s.waiting!.corridor[1]}` : "none left"}</dd>
            <dt>Target now</dt><dd className="mono">{s.waiting!.target_now} <span className="muted">(at confirmation {s.waiting!.target_at_confirmation})</span></dd>
            <dt>Stop guidance if issued</dt><dd className="mono">{s.waiting!.stop_V}</dd>
            <dt>Waits until</dt><dd className="mono">{fmtTime(s.waiting!.wait_until)} · hard deadline {fmtTime(s.waiting!.hard_deadline)}</dd>
            <dt>Blockers now</dt><dd>{s.waiting!.blockers.length ? s.waiting!.blockers.map(reasonText).join(", ") : "none (waiting for a fresh minute)"}</dd>
          </dl>
        </div>
      ))}
    </>
  );
}

function CallFacts({ c, available }: { c: CallView; available: boolean }) {
  const reasons = c.entry_reasons.length ? c.entry_reasons.map(reasonIt).join("; ") : "nessun motivo registrato";
  return (
    <dl className="call-geo proposal-facts">
      {available ? (
        <><dt>Fascia d'ingresso ammessa ora</dt>
          <dd className="mono" data-testid="live-admissible">{c.admissible_bounds ? `${c.admissible_bounds[0]} – ${c.admissible_bounds[1]}` : "non indicata dal sistema"}</dd></>
      ) : (
        <><dt>Motivo</dt><dd data-testid="live-entry-reasons">{reasons}</dd></>
      )}
      <dt>Target operativo</dt><dd className="mono" data-testid="live-target">{c.target}</dd>
      <dt>Stop indicato</dt><dd className="mono" data-testid="live-stop-guidance">{c.stop}</dd>
      <dt>Scadenza dell'indicazione</dt><dd data-testid="live-deadline">{fmtLocal(c.hard_deadline)}</dd>
      <dt>Orizzonte atteso</dt><dd>{c.expected_minutes ? `${c.expected_minutes[0]}–${c.expected_minutes[1]} min` : "non indicato"}</dd>
      <dt>Tesi</dt><dd data-testid="live-thesis">{THESIS_IT[c.thesis_status] ?? c.thesis_status}</dd>
    </dl>
  );
}

export function ProposalPanel({ v, onHistory }: { v: LiveView | null; onHistory: (callId: string) => void }) {
  const st = proposalState(v);
  const mv = v?.market_view ?? null;
  const c = v?.call ?? null;
  const available = st.key === "AVAILABLE";
  const d = mv?.expected_direction ?? "UNAVAILABLE";
  const p = mv?.principal ?? null;
  const ps = p ? (v?.scenarios ?? []).find((s) => s.scenario_id === p.scenario_id) : undefined;
  const lastTerminal = [...(v?.recent_calls ?? [])].sort((a, b) => (a.terminal_at < b.terminal_at ? 1 : -1))[0];
  const tone = c ? (c.direction === "LONG" ? "is-long" : "is-short") : "is-none";
  return (
    <section className={cx("call-panel proposal", tone)} data-testid="live-call" data-state={st.key}>
      <div className="eyebrow">Che cosa propone il sistema adesso</div>
      <div className={cx("proposal-state", `tone-${st.tone}`)} data-testid={c ? "live-entry" : v ? "live-no-trade" : "live-no-view"}>
        {st.text}
      </div>
      <div className="proposal-badges">
        {c?.presentation === "NOT_CURRENT" || (v?.stale_session && !c)
          ? <Badge tone="warn" testid="live-call-not-current">Sessione non corrente: disponibilità non verificabile</Badge>
          : c && <Badge tone={c.origin === "LIVE" ? "pos" : "pending"}>{c.origin === "LIVE" ? "Call live" : "Ricostruita — non operativa"}</Badge>}
      </div>
      {!v && <p className="proposal-note">Avvia l'adviser live per valutare il mercato. Da fermo non viene monitorato nulla.</p>}
      {v && <div className="proposal-updated" data-testid="live-updated">Ultimo aggiornamento: {fmtLocal(v.clock)}</div>}

      {!c && (
        <div className="proposal-dir" data-testid="live-direction">
          <Arrow d={d} />
          <span>Direzione attesa: <b data-testid="live-expected">{EXPECTED_IT[d] ?? d}</b>{mv?.conditional ? " (condizionale)" : ""}</span>
        </div>
      )}
      {v && !c && (
        <>
          {mv && <div className="proposal-sub">{ROW_IT[mv.table_row] ?? humanize(mv.table_row)}</div>}
          {p ? (
            <dl className="call-geo proposal-facts" data-testid="live-scenario-levels">
              <dt>Scenario</dt><dd>{p.direction} {p.family}</dd>
              <dt>Condizione ancora necessaria</dt><dd data-testid="live-condition">{condition(p, ps) ?? "non indicata dal sistema"}</dd>
              <dt>Destinazione dello scenario</dt>
              <dd><span className="mono">{ps?.destination ?? p.destination ?? p.conditional_target ?? "non indicata"}</span> <span className="muted">(non è un target operativo)</span></dd>
              <dt>Invalidazione dello scenario</dt>
              <dd><span className="mono">{ps?.invalidation_level ?? p.invalidation_level ?? "non indicata"}</span> <span className="muted">(livello strutturale, non è uno stop)</span></dd>
              <dt>Orizzonte atteso</dt><dd>{mv?.horizon_minutes ? `${mv.horizon_minutes[0]}–${mv.horizon_minutes[1]} min` : "non indicato"}</dd>
            </dl>
          ) : <p className="proposal-note">Nessuno scenario principale in questo momento.</p>}
          {lastTerminal && (
            <p className="proposal-note" data-testid="live-last-terminal">Ultima indicazione: {lastTerminal.direction} {lastTerminal.family},{" "}
              {THESIS_IT[lastTerminal.terminal] ?? lastTerminal.terminal} ({fmtLocal(lastTerminal.terminal_at)}).</p>
          )}
        </>
      )}

      {c && (
        <>
          <div className="proposal-dir" data-testid="live-direction">
            <span className="call-dir" data-testid="live-call-direction">{c.direction}</span>
            <span>{c.direction === "LONG" ? "Indicazione di acquisto: il sistema si aspetta un rialzo del prezzo."
              : "Indicazione di vendita: il sistema si aspetta un ribasso del prezzo."}</span>
          </div>
          <CallFacts c={c} available={available} />
        </>
      )}

      {v && (
        <p className="proposal-note">È l'indicazione del sistema, non una tua operazione: l'app non sa se hai aperto posizioni.
          Lo stop è un'indicazione, non un ordine.</p>
      )}

      {v && (
        <details className="more proposal-more" data-testid="live-proposal-details">
          <summary><Icon name="chevron" size={14} className="summary-chevron" /> Approfondimenti
            <span className="summary-hint">motivazioni, dettagli tecnici e cronologia</span></summary>
          <div className="more-body stack-sm">
            {mv && (
              <dl className="call-geo">
                <dt>Lettura</dt><dd className="mono">{d}{mv.conditional ? " · conditional" : ""} · {mv.table_row}</dd>
                <dt>Contesto 1h osservato</dt><dd className="mono">{mv.observed_context}</dd>
                <dt>Fase</dt><dd className="mono">{mv.phase}</dd>
                <dt>Valutazione (UTC)</dt><dd className="mono">{fmtTime(v.clock)}</dd>
              </dl>
            )}
            {(mv?.reasons.length ?? 0) > 0 && (
              <div><div className="adv-section-title">Motivazioni (testo del sistema)</div>
                <ul className="dir-reasons">{mv!.reasons.map((r) => <li key={r}>{r}</li>)}</ul></div>
            )}
            {(mv?.counterevidence.length ?? 0) > 0 && (
              <div><div className="adv-section-title">Controevidenze (testo del sistema)</div>
                <ul className="dir-counter">{mv!.counterevidence.map((r) => <li key={r}>{r}</li>)}</ul></div>
            )}
            {c && (
              <dl className="call-geo" data-testid="live-call-technical">
                <dt>Testo del sistema</dt><dd data-testid="live-guidance">{c.guidance}</dd>
                <dt>Codici registrati</dt><dd className="mono">{c.entry_status}{c.entry_reasons.length ? ` · ${c.entry_reasons.join(", ")}` : ""}</dd>
                <dt>Area strutturale (storico)</dt><dd className="mono">{c.structural_area[0]} – {c.structural_area[1]}</dd>
                {!available && c.admissible_bounds && (
                  <><dt>Ultima fascia calcolata (non utilizzabile ora)</dt><dd className="mono">{c.admissible_bounds[0]} – {c.admissible_bounds[1]}</dd></>
                )}
                <dt>Famiglia</dt><dd>{c.family} · {c.family_text} · target {humanize(c.target_type)}</dd>
                <dt>Emessa (UTC)</dt><dd className="mono">{fmtTime(c.issued_at)} a {c.issue_reference}</dd>
                <dt>Scadenza (UTC)</dt><dd className="mono">{fmtTime(c.hard_deadline)}</dd>
                <dt>Minuti residui alla valutazione</dt><dd className="mono">{c.remaining_minutes}</dd>
                <dt>Revisione</dt><dd className="mono">r{c.revision}</dd>
              </dl>
            )}
            {c && v.run_id && (
              <button type="button" className="link-btn" onClick={() => onHistory(c.call_id)} data-testid="live-call-history-open">
                Show this call's recorded history (revision r{c.revision})</button>
            )}
            <ScenarioCards v={v} />
            <p className="muted small-text">Lettura qualitativa, non una probabilità.</p>
          </div>
        </details>
      )}
    </section>
  );
}
