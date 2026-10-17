/**
 * Import del bundle OBS-001 scelto dall'utente: validazione del contratto effettivamente usato
 * da provider e viste, con errori leggibili. Un file incompleto o incoerente viene rifiutato
 * prima di sostituire lo studio aperto; nessun ripiego silenzioso sulle fixture.
 * Piccolo validatore dello schema locale: non ricalcola il motore e non verifica firme.
 */
import { BUNDLE_KIND, BUNDLE_SCHEMA, type StudyBundle } from '../contract/historical';

export class BundleError extends Error {}

type Obj = Record<string, unknown>;

const STEP: Record<string, number> = { '45m': 45 * 60_000, '1D': 86_400_000 };
const SCALES = ['45m', '1D'] as const;
const BAR_COLUMNS = ['open', 'status', 'o', 'h', 'l', 'c', 'v', 'q', 'trades', 'valid', 'missing', 'invalid'] as const;
const STATES = ['UP', 'DOWN', 'MIXED', 'UNAVAILABLE'];
const RELATIONS = ['CONCORDANT', 'OPPOSITE', 'MIXED', 'UNAVAILABLE', 'NOT_APPLICABLE'];
const MEASURES = ['final', 'up', 'down'];

const fail = (msg: string): never => {
  throw new BundleError(msg);
};

const isObj = (x: unknown): x is Obj => typeof x === 'object' && x !== null && !Array.isArray(x);
const isInt = (x: unknown): x is number => Number.isInteger(x);
const isNum = (x: unknown): x is number => typeof x === 'number' && Number.isFinite(x);
const isNumOrNull = (x: unknown) => x === null || isNum(x);
const isStr = (x: unknown): x is string => typeof x === 'string' && x.length > 0;

function obj(parent: Obj, key: string, where: string): Obj {
  const v = parent[key];
  return isObj(v) ? v : fail(`${where}: campo «${key}» assente o non valido.`);
}

function arr(parent: Obj, key: string, where: string): unknown[] {
  const v = parent[key];
  return Array.isArray(v) ? v : fail(`${where}: elenco «${key}» assente o non valido.`);
}

function str(parent: Obj, key: string, where: string): string {
  const v = parent[key];
  return isStr(v) ? v : fail(`${where}: testo «${key}» assente o non valido.`);
}

/** Misura {v, r}: valore oppure null con motivo. */
function measure(x: unknown, where: string): void {
  if (!isObj(x) || !('v' in x) || !('r' in x) || (x.v === null && !isStr(x.r))) fail(`${where}: misura non nel formato {v, r}.`);
}

function counts(x: unknown, where: string): void {
  if (!isObj(x) || !['expected', 'valid', 'missing', 'invalid'].every((k) => isInt(x[k]))) fail(`${where}: conteggi dei minuti non validi.`);
}

function validateRun(data: Obj): void {
  const run = obj(data, 'run', 'Identità del run');
  str(run, 'runId', 'Identità del run');
  str(run, 'engineVersion', 'Identità del run');
  if (!(run.inputHash === null || isStr(run.inputHash))) fail('Identità del run: «inputHash» non valido.');
  if (run.synthetic !== undefined && typeof run.synthetic !== 'boolean') fail('Identità del run: «synthetic» non valido.');
}

function validateQuality(data: Obj): void {
  const q = obj(data, 'inputQuality', 'Qualità degli input');
  const totals = obj(q, 'totals', 'Qualità degli input');
  for (const k of ['input', 'initialization', 'study']) counts(totals[k], `Qualità degli input (${k})`);
  arr(q, 'files', 'Qualità degli input').forEach((f, i) => {
    if (!isObj(f) || !isStr(f.month) || !isStr(f.file) || !isStr(f.sha256) || !isInt(f.rows)) fail(`Qualità degli input: file ${i + 1} incompleto.`);
    counts((f as Obj).coverage, `Qualità degli input (file ${i + 1})`);
  });
}

function validateBars(data: Obj, periods: { inputStart: number; end: number }): void {
  const bars = obj(data, 'bars', 'Barre');
  const observations = obj(data, 'observations', 'Osservazioni');
  const events = obj(data, 'events', 'Eventi');
  for (const scale of SCALES) {
    const where = `Barre ${scale}`;
    const b = obj(bars, scale, 'Barre');
    const open = arr(b, 'open', where);
    const n = open.length;
    const step = STEP[scale];
    if (n < 2 || n * step !== periods.end - periods.inputStart) fail(`${where}: la griglia non copre i periodi dichiarati.`);
    for (const col of BAR_COLUMNS) if (arr(b, col, where).length !== n) fail(`${where}: colonna «${col}» non allineata.`);
    const status = b.status as unknown[];
    open.forEach((t, i) => {
      if (t !== periods.inputStart + i * step) fail(`${where}: apertura ${i + 1} fuori dalla griglia UTC.`);
      if (status[i] !== 'COMPLETE' && status[i] !== 'INCOMPLETE') fail(`${where}: stato della barra ${i + 1} non valido.`);
      const ohlc = ['o', 'h', 'l', 'c', 'v'].map((k) => (b[k] as unknown[])[i]);
      if (status[i] === 'COMPLETE' ? !ohlc.every(isNum) : !ohlc.every((x) => x === null)) fail(`${where}: valori della barra ${i + 1} incoerenti con il suo stato.`);
    });

    const recs = arr(observations, scale, `Osservazioni ${scale}`);
    if (recs.length !== n) fail(`Osservazioni ${scale}: ${recs.length} record per ${n} barre.`);
    recs.forEach((r, i) => {
      const w = `Osservazioni ${scale}, record ${i + 1}`;
      if (!isObj(r)) return fail(`${w}: non è un oggetto.`);
      if (r.open !== open[i] || r.end !== (open[i] as number) + step || r.availableAt !== r.end) fail(`${w}: tempi non allineati alla barra.`);
      if (r.status !== status[i]) fail(`${w}: stato diverso da quello della barra.`);
      if (!isNumOrNull(r.C) || (r.status === 'COMPLETE') !== isNum(r.C)) fail(`${w}: chiusura C incoerente.`);
      const vol = obj(r, 'vol', w);
      const avg = obj(r, 'avg', w);
      const volu = obj(r, 'volu', w);
      const piv = obj(r, 'piv', w);
      const fib = obj(r, 'fib', w);
      obj(r, 'inputRef', w);
      for (const k of ['tr', 'A', 'AoverC']) measure(vol[k], `${w}, vol.${k}`);
      for (const k of ['sma20', 'sma50', 'dist', 'slope', 'pos', 'cross']) measure(avg[k], `${w}, avg.${k}`);
      for (const k of ['median', 'ratio']) measure(volu[k], `${w}, volu.${k}`);
      for (const k of ['check', 'structure']) measure(piv[k], `${w}, piv.${k}`);
      if (!Array.isArray(piv.highs) || !Array.isArray(piv.lows)) fail(`${w}: pivot di struttura assenti.`);
      if (!isInt(fib.version)) fail(`${w}: versione Fibonacci assente.`);
      measure(fib.anchors, `${w}, fib.anchors`);
      if (!Array.isArray(r.lvl) || !Array.isArray(r.crossings)) fail(`${w}: livelli o attraversamenti assenti.`);
    });

    let prev = -Infinity;
    arr(events, scale, `Eventi ${scale}`).forEach((e, i) => {
      const w = `Eventi ${scale}, evento ${i + 1}`;
      if (!isObj(e) || !isStr(e.id) || !isStr(e.type) || !isInt(e.eventTime) || !isInt(e.availableAt)) return fail(`${w}: campi obbligatori assenti.`);
      if (e.scale !== scale) fail(`${w}: scala diversa da ${scale}.`);
      if ((e.availableAt as number) < prev || (e.eventTime as number) > (e.availableAt as number)) fail(`${w}: ordine temporale non valido.`);
      prev = e.availableAt as number;
    });
  }
}

function validateStudy(data: Obj, periods: { studyStart: number; end: number }): void {
  const origins = arr(data, 'origins', 'Origini');
  if (origins.length === 0) fail('Nessuna origine di studio nel bundle.');
  origins.forEach((t, i) => {
    if (t !== periods.studyStart + i * STEP['45m'] || (t as number) >= periods.end) fail(`Origini: la ${i + 1}ª non è sulla griglia 45m dello studio.`);
  });
  const retro = obj(data, 'retrospective', 'Sezione retrospettiva');
  const rows = arr(retro, 'rows', 'Sezione retrospettiva');
  if (rows.length !== origins.length) fail('Sezione retrospettiva: righe non allineate alle origini.');
  rows.forEach((r, i) => {
    const w = `Sezione retrospettiva, riga ${i + 1}`;
    if (!isObj(r) || r.t !== origins[i] || !isInt(r.horizonEnd) || !isStr(r.month)) return fail(`${w}: origine o orizzonte non validi.`);
    if (!STATES.includes(r.s45 as string) || !STATES.includes(r.s1d as string) || !RELATIONS.includes(r.dailyRelation as string)) fail(`${w}: gruppo non riconosciuto.`);
    if (!Array.isArray(r.futureFlags) || !isStr(r.originStatus) || !isStr(r.aStatus) || !isStr(r.futureStatus)) fail(`${w}: stato degli esiti assente.`);
    for (const k of ['p', 'a', 'close24h', 'maxHigh', 'minLow', ...MEASURES]) if (!isNumOrNull(r[k])) fail(`${w}: valore «${k}» non valido.`);
    for (const k of ['futureMinutesExpected', 'futureMinutesInRange', 'futureMinutesValid', 'futureMinutesContiguous']) if (!isInt(r[k])) fail(`${w}: conteggio «${k}» non valido.`);
  });
  const summary = obj(retro, 'summary', 'Riepilogo');
  const periodsList = arr(summary, 'periods', 'Riepilogo');
  const tables = obj(summary, 'tables', 'Riepilogo');
  if (periodsList.length === 0) fail('Riepilogo: nessun periodo.');
  for (const p of periodsList) {
    const w = `Riepilogo, periodo ${String(p)}`;
    const t = obj(tables, String(p), 'Riepilogo');
    const cov = obj(t, 'coverage', w);
    if (!isInt(cov.n) || !isObj(cov.missingFlags) || !isObj(cov.availabilityAtOrigin)) fail(`${w}: copertura incompleta.`);
    const s45 = obj(t, 's45', w);
    const matrix = obj(t, 'matrix', w);
    for (const s of ['UP', 'DOWN', 'MIXED', 'UNAVAILABLE']) {
      const g = obj(s45, s, w);
      if (!isInt(g.n) || !isObj(g.stats) || !MEASURES.every((m) => isObj((g.stats as Obj)[m]))) fail(`${w}: gruppo s45 ${s} incompleto.`);
      const row = obj(matrix, s, w);
      if (!['UP', 'DOWN', 'MIXED', 'UNAVAILABLE'].every((d) => isInt(row[d]))) fail(`${w}: matrice incompleta.`);
    }
    const rel = obj(t, 'relation', w);
    for (const side of ['UP', 'DOWN']) {
      const r = obj(rel, side, w);
      for (const k of ['CONCORDANT', 'OPPOSITE', 'MIXED', 'UNAVAILABLE']) {
        const g = obj(r, k, w);
        if (!isInt(g.n) || !isObj(g.stats)) fail(`${w}: relazione ${side}/${k} incompleta.`);
      }
    }
  }
  const examples = obj(summary, 'examples', 'Riepilogo');
  for (const side of ['UP', 'DOWN']) {
    const e = obj(examples, side, 'Riepilogo, esempi');
    for (const k of ['first', 'contrary']) {
      if (!(e[k] === null || origins.includes(e[k]))) fail(`Riepilogo, esempi ${side}: origine «${k}» non presente nello studio.`);
    }
  }
  obj(summary, 'checks', 'Riepilogo');
}

export function parseBundle(text: string): StudyBundle {
  let data: unknown;
  try {
    data = JSON.parse(text);
  } catch {
    return fail('Il file non è un JSON valido. Scegli il file obs001-bundle.json prodotto dal comando «process».');
  }
  if (!isObj(data)) return fail('Formato inatteso: il contenuto non è un oggetto JSON.');
  if (data.kind !== BUNDLE_KIND) return fail(`Non è un bundle OBS-001 (kind=${String(data.kind)}).`);
  if (data.schema !== BUNDLE_SCHEMA) return fail(`Versione di schema non supportata: ${String(data.schema)} (attesa ${BUNDLE_SCHEMA}).`);
  str(data, 'engineVersion', 'Bundle');
  const conv = obj(data, 'conventions', 'Convenzioni');
  if (!isStr(conv.id) || !conv.id.startsWith('OBS-001/') || !isStr(conv.hash)) fail('Convenzioni assenti o non riconosciute nel bundle.');
  const source = obj(data, 'source', 'Fonte');
  for (const k of ['name', 'attribution', 'symbol']) str(source, k, 'Fonte dei dati');
  const periods = obj(data, 'periods', 'Periodi');
  const { inputStart, studyStart, end } = periods;
  if (!isInt(inputStart) || !isInt(studyStart) || !isInt(end) || !(inputStart < studyStart && studyStart < end)) fail('Periodi del bundle mancanti o non validi.');
  const p = { inputStart: inputStart as number, studyStart: studyStart as number, end: end as number };
  validateRun(data);
  validateQuality(data);
  validateBars(data, p);
  validateStudy(data, p);
  return data as unknown as StudyBundle;
}
