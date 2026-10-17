/**
 * Import del bundle di backtest CAND-001: validazione dei campi effettivamente letti dalle viste
 * (risultati, mesi, esempi, operazioni, episodi, finestre), con errori localizzati. Un file
 * incoerente non sostituisce il backtest aperto. Formato separato dal bundle osservativo OBS-001.
 */
import { BACKTEST_KIND, BACKTEST_SCHEMA, type BacktestBundle } from '../contract/backtest';

export class BacktestBundleError extends Error {}

type Obj = Record<string, unknown>;

const fail = (msg: string): never => {
  throw new BacktestBundleError(msg);
};
const isObj = (x: unknown): x is Obj => typeof x === 'object' && x !== null && !Array.isArray(x);
const isInt = (x: unknown): x is number => Number.isInteger(x);
const isNum = (x: unknown): x is number => typeof x === 'number' && Number.isFinite(x);
const isNumOrNull = (x: unknown) => x === null || isNum(x);
const isStr = (x: unknown): x is string => typeof x === 'string' && x.length > 0;
const SIDES = ['LONG', 'SHORT'];
const CATEGORIES = [
  'FIRST_CALL', 'FIRST_TRADE', 'FIRST_NEGATIVE_TRADE', 'FIRST_POSITIVE_TRADE', 'FIRST_PROTECTION_UPDATE',
  'FIRST_ABSTAIN_REACTION_INVALIDATED', 'FIRST_ABSTAIN_REWARD_RISK', 'FIRST_ABSTAIN_MISSING_DATA',
];
const EXITS = ['STOP', 'TARGET', 'EXIT_STRUCTURE', 'TIME_EXIT', 'END_OF_SEGMENT'];

function obj(p: Obj, k: string, w: string): Obj {
  return isObj(p[k]) ? (p[k] as Obj) : fail(`${w}: campo «${k}» assente o non valido.`);
}
function arr(p: Obj, k: string, w: string): unknown[] {
  return Array.isArray(p[k]) ? (p[k] as unknown[]) : fail(`${w}: elenco «${k}» assente o non valido.`);
}
function nums(p: Obj, keys: string[], w: string, nullable = false): void {
  for (const k of keys) if (!(nullable ? isNumOrNull(p[k]) : isNum(p[k]))) fail(`${w}: valore «${k}» assente o non numerico.`);
}
function measure(x: unknown, w: string): void {
  if (!isObj(x) || !('v' in x) || !('r' in x) || (x.v === null && !isStr(x.r))) fail(`${w}: misura non nel formato {v, r}.`);
}
function pivot(x: unknown, w: string): void {
  if (!isObj(x) || (x.kind !== 'HIGH' && x.kind !== 'LOW') || !isNum(x.price) || !isInt(x.candidateOpen) || !isInt(x.availableAt)) fail(`${w}: pivot incompleto.`);
}
function stats(x: unknown, w: string): void {
  if (!isObj(x) || !isInt(x.n)) return fail(`${w}: statistiche incomplete.`);
  nums(x, ['mean', 'p10', 'p25', 'p50', 'p75', 'p90'], w, true);
}

function period(t: unknown, w: string): void {
  if (!isObj(t)) return fail(`${w}: tabella assente.`);
  for (const k of ['start', 'end', 'closes', 'evaluatedCloses', 'notEvaluatedCloses', 'validCloses', 'legs', 'episodes', 'calls']) if (!isInt(t[k])) fail(`${w}: conteggio «${k}» non valido.`);
  if ((t.validCloses as number) > (t.evaluatedCloses as number) || (t.evaluatedCloses as number) + (t.notEvaluatedCloses as number) !== t.closes) fail(`${w}: chiusure valutate, teoriche e valide incoerenti.`);
  const cov = obj(t, 'coverage', w);
  if (typeof cov.complete !== 'boolean' || typeof cov.evaluated !== 'boolean' || !isInt(cov.evaluatedUntil) || !(cov.haltedAt === null || isInt(cov.haltedAt)) || !isInt(cov.unresolvedTrades)) {
    fail(`${w}: copertura del periodo incompleta.`);
  }
  const req = obj(t, 'requests', w);
  for (const k of ['FILLED', 'REJECTED_PRICE', 'CANCELLED_NO_QUOTE']) if (!isInt(req[k])) fail(`${w}: richieste «${k}» non valide.`);
  for (const k of ['legsByOutcome', 'episodesByTermination']) for (const [kk, v] of Object.entries(obj(t, k, w))) if (!isInt(v)) fail(`${w}: «${k}.${kk}» non valido.`);
  const dd = obj(t, 'drawdown', w);
  if (!isNumOrNull(dd.maxDrawdown) || typeof dd.missing !== 'boolean') fail(`${w}: drawdown non valido.`);
  if ('partialMaxDrawdown' in dd && (!isInt(dd.partialUntil) || !isNumOrNull(dd.partialMaxDrawdown))) fail(`${w}: drawdown parziale non valido.`);
  const tr = obj(t, 'trades', w);
  for (const k of ['n', 'closed', 'unresolved', 'long', 'short', 'maxLosingStreak', 'protectionUpdates', 'tradesWithProtectionUpdate', 'bothTouched', 'gapExits', 'fundingAmbiguousTrades', 'fundingMissingTrades']) {
    if (!isInt(tr[k])) fail(`${w}: operazioni «${k}» non valido.`);
  }
  nums(tr, ['pricePnLRef', 'slippage', 'fees', 'funding', 'net', 'netBps', 'stressNet', 'positiveShare', 'payoff', 'profitFactor'], `${w}, operazioni`, true);
  if (!isNum(tr.exposureShare)) fail(`${w}: esposizione non valida.`);
  const cs = obj(tr, 'closedSubset', w);
  if (!isInt(cs.trades) || !isNumOrNull(cs.net) || !isStr(cs.label)) fail(`${w}: parte nota delle operazioni incompleta.`);
  if ((tr.unresolved as number) > 0 && tr.net !== null) fail(`${w}: netto completo presente nonostante operazioni irrisolte.`);
  const ex = obj(tr, 'exits', w);
  for (const r of EXITS) if (!isInt(ex[r])) fail(`${w}: uscite «${r}» non valide.`);
  const pt = obj(tr, 'perTrade', w);
  for (const k of ['net', 'durationMin', 'riskInitialOverN0']) stats(pt[k], `${w}, ${k}`);
  nums(obj(tr, 'concentration', w), ['top5AbsShare', 'best5PositiveShare', 'worst5NegativeShare'], `${w}, concentrazione`, true);
}

function trade(t: unknown, w: string): void {
  if (!isObj(t) || !isStr(t.id) || !isStr(t.episodeId) || !SIDES.includes(t.side as string) || (t.d !== 1 && t.d !== -1)) return fail(`${w}: identità incompleta.`);
  for (const k of ['callTime', 'entryTime']) if (!isInt(t[k])) fail(`${w}: tempo «${k}» non valido.`);
  nums(t, ['Eref', 'E', 'q', 'N0', 'S0', 'T', 'R0', 'G0', 'feeEntry', 'riskInitial'], w);
  if (t.status !== undefined || t.exit === null) {
    // Percorso irrisolto: fatti noti fino alla lacuna, nessun risultato completo.
    if (t.status !== 'UNRESOLVED_DATA_GAP' || t.exit !== null) fail(`${w}: stato dell'operazione non riconosciuto.`);
    if (!isObj(t.gap) || !isInt(t.gap.at) || !isStr(t.gap.reason)) fail(`${w}: operazione irrisolta senza momento della lacuna.`);
    if (!isNum(t.durationUntilGapMin)) fail(`${w}: durata fino alla lacuna assente.`);
    for (const k of ['pricePnL', 'pricePnLRef', 'slippageCost', 'feeExit', 'net', 'netBps', 'durationMin']) if (t[k] !== null) fail(`${w}: operazione irrisolta con «${k}» valorizzato.`);
  } else {
    nums(t, ['pricePnL', 'pricePnLRef', 'slippageCost', 'feeExit', 'durationMin'], w);
    nums(t, ['net', 'netBps'], w, true);
    const ex = obj(t, 'exit', w);
    if (!EXITS.includes(ex.reason as string) || !isInt(ex.minute) || !isInt(ex.accountingTime)) fail(`${w}: uscita incompleta.`);
    nums(ex, ['Xref', 'X'], `${w}, uscita`);
  }
  arr(t, 'stops', w).forEach((s, i) => {
    if (!isObj(s) || !isInt(s.decidedAt) || !isInt(s.effectiveAt)) return fail(`${w}: aggiornamento protezione ${i + 1} incompleto.`);
    nums(s, ['from', 'to', 'pivot'], `${w}, protezione ${i + 1}`);
  });
  const f = obj(t, 'funding', w);
  if (!isNumOrNull(f.total) || typeof f.missing !== 'boolean') fail(`${w}: funding incompleto.`);
  arr(f, 'events', w).forEach((e, i) => {
    if (!isObj(e) || !isInt(e.tau) || !isNum(e.rate) || !isNumOrNull(e.cashflow) || typeof e.counted !== 'boolean') fail(`${w}: evento di funding ${i + 1} incompleto.`);
  });
  if (!(t.netRange === null || (Array.isArray(t.netRange) && t.netRange.length === 2 && t.netRange.every(isNum)))) fail(`${w}: intervallo del netto non valido.`);
  nums(obj(t, 'stress', w), ['fee', 'slippage'], `${w}, stress`);
  if (!isNumOrNull((t.stress as Obj).net)) fail(`${w}: netto stress non valido.`);
}

function episode(e: unknown, w: string): void {
  if (!isObj(e) || !isStr(e.id) || !isStr(e.legId) || !SIDES.includes(e.side as string) || (e.d !== 1 && e.d !== -1)) return fail(`${w}: identità incompleta.`);
  pivot(e.P0, `${w}, P0`);
  pivot(e.P1, `${w}, P1`);
  nums(e, ['A0', 'L'], w);
  if (!isInt(e.t0) || !isStr(e.status)) fail(`${w}: tempo o stato non validi.`);
  arr(e, 'states', w).forEach((s, i) => {
    if (!isObj(s) || !isInt(s.t) || !isStr(s.state)) fail(`${w}: stato ${i + 1} incompleto.`);
  });
  if (e.plan !== null) nums(obj(e, 'plan', w), ['S0', 'T', 'Estar', 'risk', 'gain', 'Ck', 'Rext', 'depth'], `${w}, piano`);
  if (e.plan !== null && !isNumOrNull((e.plan as Obj).ratio)) fail(`${w}: rapporto del piano non valido.`);
  if (e.call !== null) {
    const c = obj(e, 'call', w);
    if (!isInt(c.t) || !isInt(c.executeAt) || !isStr(c.expectation)) fail(`${w}: call incompleta.`);
    nums(c, ['S0', 'T', 'Estar', 'entryBound'], `${w}, call`);
  }
  if (e.termination !== null && !(isObj(e.termination) && isInt(e.termination.t) && isStr(e.termination.code))) fail(`${w}: conclusione incompleta.`);
  const ctx = obj(e, 'context0', w);
  for (const k of ['A', 'structure45m', 'structure1D', 'sma20', 'sma50', 'volumeRatio']) measure(ctx[k], `${w}, contesto ${k}`);
  if (!(e.tradeId === null || isStr(e.tradeId))) fail(`${w}: riferimento all'operazione non valido.`);
}

function window_(x: unknown, w: string): void {
  if (!isObj(x)) return fail(`${w}: finestra assente.`);
  for (const scale of ['bars45', 'bars1d']) {
    const b = obj(x, scale, w);
    const n = arr(b, 'open', `${w}, ${scale}`).length;
    if (n === 0) fail(`${w}: ${scale} vuoto.`);
    for (const col of ['status', 'o', 'h', 'l', 'c', 'v']) if (arr(b, col, `${w}, ${scale}`).length !== n) fail(`${w}: colonna ${scale}.${col} non allineata.`);
    if (!(b.open as unknown[]).every(isInt)) fail(`${w}: aperture ${scale} non valide.`);
  }
  const n45 = ((x.bars45 as Obj).open as unknown[]).length;
  for (const k of ['sma20', 'sma50']) if (arr(x, k, w).length !== n45 || !(x[k] as unknown[]).every(isNumOrNull)) fail(`${w}: serie ${k} non allineata.`);
  arr(x, 'pivots', w).forEach((p, i) => pivot(p, `${w}, pivot ${i + 1}`));
  for (const [t, s] of Object.entries(obj(x, 'snapshots', w))) {
    if (!isObj(s) || String(s.t) !== t) return fail(`${w}: fotografia ${t} non valida.`);
    for (const k of ['A', 'structure45m', 'structure1D', 'sma20', 'sma50', 'volumeRatio']) measure(s[k], `${w}, fotografia ${t}.${k}`);
    if (!isObj(s.fib) || !isInt(s.fib.version)) fail(`${w}: fotografia ${t}: Fibonacci incompleto.`);
  }
}

export function parseBacktest(text: string): BacktestBundle {
  let data: unknown;
  try {
    data = JSON.parse(text);
  } catch {
    return fail('Il file non è un JSON valido. Scegli il file cand001-bundle.json prodotto dal comando «run».');
  }
  if (!isObj(data)) return fail('Formato inatteso: il contenuto non è un oggetto JSON.');
  if (data.kind !== BACKTEST_KIND) {
    return fail(data.kind === 'OBS001_BUNDLE' ? 'Questo è un bundle dello studio osservativo OBS-001: aprilo nell’ambiente «Studio storico».' : `Non è un bundle di backtest CAND-001 (kind=${String(data.kind)}).`);
  }
  if (data.schema !== BACKTEST_SCHEMA) return fail(`Versione di schema non supportata: ${String(data.schema)} (attesa ${BACKTEST_SCHEMA}).`);
  const cand = obj(data, 'candidate', 'Candidato');
  if (!isStr(cand.id) || !cand.id.startsWith('CAND-001/') || !isStr(cand.version) || !isStr(cand.hash)) fail('Candidato assente o non riconosciuto.');
  const run = obj(data, 'run', 'Identità del run');
  if (!isStr(run.runId) || !isStr(run.engineVersion)) fail('Identità del run incompleta.');
  const win = obj(data, 'window', 'Finestra');
  if (!isInt(win.start) || !isInt(win.end) || !isInt(win.inputStart) || !((win.inputStart as number) <= (win.start as number) && (win.start as number) < (win.end as number))) fail('Finestra valutata non valida.');
  const src = obj(data, 'source', 'Fonte');
  if (!isStr(src.attribution) || !isStr(src.symbol)) fail('Fonte dei dati non dichiarata.');
  if (!isStr(data.economicsLabel) || !isNum(data.notionalUSDT) || !isStr(data.phase)) fail('Etichetta economica, nozionale o fase assenti.');
  const q = obj(data, 'quality', 'Qualità degli input');
  const totals = obj(obj(q, 'trade', 'Qualità degli input'), 'totals', 'Qualità degli input');
  for (const k of ['expected', 'valid', 'missing', 'invalid']) if (!isInt(totals[k])) fail(`Qualità degli input: conteggio «${k}» non valido.`);
  const fs = obj(obj(q, 'funding', 'Qualità degli input'), 'series', 'Qualità del funding');
  if (!isInt(fs.events) || !Array.isArray(fs.anomalies)) fail('Qualità del funding incompleta.');
  const mk = obj(q, 'mark', 'Qualità degli input');
  if (!isInt(mk.pointsNeeded) || !isInt(mk.pointsAvailable)) fail('Qualità del mark incompleta.');

  const summary = obj(data, 'summary', 'Risultati');
  const periods = arr(summary, 'periods', 'Risultati');
  if (periods.length === 0) fail('Risultati: nessun periodo.');
  const tables = obj(summary, 'tables', 'Risultati');
  for (const p of periods) period(tables[String(p)], `Risultati, periodo ${String(p)}`);
  const months = obj(summary, 'months', 'Risultati');
  const halted = summary.halted;
  if (!(halted === null || (isObj(halted) && isInt(halted.at) && isStr(halted.reason)))) fail('Risultati: interruzione della finestra non valida.');
  const rec = obj(summary, 'reconciliation', 'Riconciliazione');
  if (typeof rec.knownPartReconciled !== 'boolean' || typeof rec.windowComplete !== 'boolean' || !isInt(rec.closedTrades) || !isInt(rec.unresolvedTrades) || !isNumOrNull(rec.knownPartNet) || !isInt(rec.evaluatedCloses) || !isInt(rec.notEvaluatedCloses)) {
    fail('Riconciliazione incompleta.');
  }
  if ((halted === null) !== (rec.windowComplete === true)) fail('Riconciliazione incoerente con l’interruzione della finestra.');
  for (const [m, t] of Object.entries(months)) {
    period(t, `Risultati, mese ${m}`);
    const cf = obj(t as Obj, 'cashflowByTimestamp', `Risultati, mese ${m}`);
    if (!isNumOrNull(cf.net)) fail(`Risultati, mese ${m}: cashflow non valido.`);
  }

  const trades = arr(data, 'trades', 'Operazioni');
  trades.forEach((t, i) => trade(t, `Operazioni, ${i + 1}ª`));
  const episodes = arr(data, 'episodes', 'Episodi');
  episodes.forEach((e, i) => episode(e, `Episodi, ${i + 1}°`));
  const epIds = new Set(episodes.map((e) => (e as Obj).id));
  const trIds = new Set(trades.map((t) => (t as Obj).id));
  for (const t of trades) if (!epIds.has((t as Obj).episodeId)) fail(`Operazione ${String((t as Obj).id)}: episodio non presente.`);
  arr(data, 'requests', 'Richieste').forEach((r, i) => {
    if (!isObj(r) || !isStr(r.episodeId) || !isInt(r.executeAt) || !isStr(r.outcome) || !SIDES.includes(r.side as string)) fail(`Richieste, ${i + 1}ª: incompleta.`);
  });
  const legs = arr(data, 'exampleLegs', 'Gambe d’esempio');
  legs.forEach((lg, i) => {
    if (!isObj(lg) || !isStr(lg.id) || !isInt(lg.t) || !isStr(lg.outcome)) return fail(`Gambe d’esempio, ${i + 1}ª: incompleta.`);
    pivot(lg.P0, `Gamba ${String(lg.id)}, P0`);
    pivot(lg.P1, `Gamba ${String(lg.id)}, P1`);
  });
  const windows = obj(data, 'windows', 'Finestre degli episodi');
  for (const [id, w] of Object.entries(windows)) window_(w, `Finestra ${id}`);
  const legIds = new Set(legs.map((l) => (l as Obj).id));
  const examples = obj(summary, 'examples', 'Esempi');
  for (const side of SIDES) {
    const cats = obj(examples, side, 'Esempi');
    for (const c of CATEGORIES) {
      const ref = cats[c];
      if (ref === null) continue;
      const w = `Esempi ${side}/${c}`;
      if (!isObj(ref) || !isStr(ref.id) || !isInt(ref.t)) return fail(`${w}: riferimento incompleto.`);
      const target = ref.kind === 'trade' ? ref.episodeId : ref.id;
      if (ref.kind === 'trade' && !trIds.has(ref.id)) fail(`${w}: operazione non presente.`);
      if (ref.kind === 'leg' ? !legIds.has(ref.id) : !epIds.has(target)) fail(`${w}: episodio o gamba non presente.`);
      if (!windows[String(target)]) fail(`${w}: finestra del grafico assente.`);
    }
  }
  return data as unknown as BacktestBundle;
}
