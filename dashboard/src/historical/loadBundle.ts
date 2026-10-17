/**
 * Import del bundle OBS-001 (o del pacchetto di caso OBS-002) scelto dall'utente: validazione del contratto effettivamente usato
 * da provider e viste, con errori leggibili. Un file incompleto o incoerente viene rifiutato
 * prima di sostituire lo studio aperto; nessun ripiego silenzioso sulle fixture.
 * Piccolo validatore dello schema locale: non ricalcola il motore e non verifica firme.
 */
import { BUNDLE_KIND, BUNDLE_SCHEMA, CASE_KIND, CASE_SCHEMA, type StudyBundle } from '../contract/historical';

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

/** Misura numerica: valore finito oppure null con motivo. */
function numMeasure(x: unknown, where: string): void {
  measure(x, where);
  if (!isNumOrNull((x as Obj).v)) fail(`${where}: valore non numerico.`);
}

/** Misura con valore in un insieme chiuso, oppure null con motivo. */
function enumMeasure(x: unknown, allowed: string[], where: string): void {
  measure(x, where);
  const v = (x as Obj).v;
  if (v !== null && !allowed.includes(v as string)) fail(`${where}: valore «${String(v)}» non riconosciuto.`);
}

const LEVEL_KINDS = ['PIVOT_HIGH', 'PIVOT_LOW', 'DAY_HIGH', 'DAY_LOW'];

function pivotRef(x: unknown, where: string): void {
  if (!isObj(x) || (x.kind !== 'HIGH' && x.kind !== 'LOW') || !isNum(x.price) || !isInt(x.candidateOpen) || !isInt(x.eventTime) || !isInt(x.availableAt)) {
    fail(`${where}: riferimento al pivot incompleto.`);
  }
}

/** Campi annidati del record letti dalle viste (famiglie, grafico, osservazioni). */
function validateRecord(r: Obj, w: string): void {
  const ref = obj(r, 'inputRef', w);
  if (!Array.isArray(ref.minutes) || ref.minutes.length !== 2 || !ref.minutes.every(isInt) || !['valid', 'missing', 'invalid'].every((k) => isInt(ref[k]))) {
    fail(`${w}: riferimento agli input incompleto.`);
  }
  const seg = r.segment;
  if (r.status === 'COMPLETE' ? !(isObj(seg) && isInt(seg.id) && isInt(seg.bars)) : seg !== null) fail(`${w}: segmento incoerente con lo stato.`);
  const vol = obj(r, 'vol', w);
  for (const k of ['tr', 'A', 'AoverC']) numMeasure(vol[k], `${w}, vol.${k}`);
  const avg = obj(r, 'avg', w);
  for (const k of ['sma20', 'sma50', 'dist', 'slope', 'pos']) numMeasure(avg[k], `${w}, avg.${k}`);
  enumMeasure(avg.cross, ['UP', 'DOWN', 'NONE'], `${w}, avg.cross`);
  const volu = obj(r, 'volu', w);
  for (const k of ['median', 'ratio']) numMeasure(volu[k], `${w}, volu.${k}`);
  for (const k of ['base', 'quote', 'trades', 'takerBase', 'takerQuote']) if (!isNumOrNull(volu[k])) fail(`${w}: volume «${k}» non valido.`);
  const piv = obj(r, 'piv', w);
  measure(piv.check, `${w}, piv.check`);
  const check = (piv.check as Obj).v;
  if (check !== null && !(isObj(check) && isInt(check.candidateOpen) && isStr(check.high) && isStr(check.low))) fail(`${w}: controllo del pivot incompleto.`);
  enumMeasure(piv.structure, ['UP', 'DOWN', 'MIXED'], `${w}, piv.structure`);
  for (const k of ['highs', 'lows']) arr(piv, k, w).forEach((p, j) => pivotRef(p, `${w}, piv.${k}[${j}]`));
  const fib = obj(r, 'fib', w);
  if (!isInt(fib.version)) fail(`${w}: versione Fibonacci assente.`);
  measure(fib.anchors, `${w}, fib.anchors`);
  const anchors = (fib.anchors as Obj).v;
  if (anchors !== null) {
    if (!isObj(anchors)) return fail(`${w}: ancore Fibonacci non valide.`);
    pivotRef(anchors.P0, `${w}, fib P0`);
    pivotRef(anchors.P1, `${w}, fib P1`);
    if (!isNum(fib.u) || !isNum(fib.r)) fail(`${w}: u o r di Fibonacci assenti.`);
    for (const k of ['retracements', 'projections']) {
      arr(fib, k, w).forEach((l, j) => {
        if (!isObj(l) || !isNum(l.ratio) || !isNum(l.price)) fail(`${w}: livello Fibonacci ${k}[${j}] incompleto.`);
        numMeasure((l as Obj).dist, `${w}, fib ${k}[${j}].dist`);
      });
    }
  }
  arr(r, 'lvl', w).forEach((lv, j) => {
    const lw = `${w}, livello ${j + 1}`;
    if (!isObj(lv) || !LEVEL_KINDS.includes(lv.kind as string)) return fail(`${lw}: tipo non riconosciuto.`);
    if (lv.price === null) {
      if (!isStr(lv.reason)) fail(`${lw}: livello assente senza motivo.`);
    } else if (!isNum(lv.price) || !isStr(lv.id) || !isInt(lv.availableAt)) {
      fail(`${lw}: prezzo, identità o disponibilità non validi.`);
    } else {
      numMeasure(lv.dist, `${lw}, distanza`);
    }
  });
  arr(r, 'crossings', w).forEach((c, j) => {
    if (!isObj(c) || !isStr(c.levelKind) || (c.direction !== 'UP' && c.direction !== 'DOWN') || !isNum(c.price)) fail(`${w}: attraversamento ${j + 1} incompleto.`);
  });
}

/** Campi richiesti dalla descrizione di ciascun tipo di evento (revisioni e marcatori dei pivot). */
function validateEvent(e: Obj, w: string): void {
  switch (e.type) {
    case 'PIVOT_CONFIRMED':
    case 'PIVOT_REJECTED':
      if ((e.kind !== 'HIGH' && e.kind !== 'LOW') || !isInt(e.candidateOpen) || !isNum(e.price)) fail(`${w}: dati del pivot incompleti.`);
      break;
    case 'PIVOT_DUAL_AMBIGUOUS':
      if (!isInt(e.candidateOpen)) fail(`${w}: candela ambigua senza orario.`);
      break;
    case 'FIB_SEQUENCE': {
      if (!isInt(e.version) || !['APPEND', 'REPLACE', 'KEEP'].includes(e.action as string)) fail(`${w}: versione o azione Fibonacci non valide.`);
      const after = e.after ?? e.ignored;
      if (!isObj(after) || !isNum(after.price)) fail(`${w}: pivot della sequenza Fibonacci assente.`);
      if (!(e.before === null || e.before === undefined || (isObj(e.before) && isNum(e.before.price)))) fail(`${w}: pivot sostituito non valido.`);
      break;
    }
    case 'LEVEL_CROSS':
      if ((e.direction !== 'UP' && e.direction !== 'DOWN') || !isStr(e.levelKind) || !isNum(e.price)) fail(`${w}: attraversamento incompleto.`);
      break;
    case 'SMA_CROSS':
      if (e.direction !== 'UP' && e.direction !== 'DOWN') fail(`${w}: direzione dell’incrocio non valida.`);
      break;
    case 'SEGMENT_RESET':
      if (!isInt(e.missing)) fail(`${w}: azzeramento senza conteggio dei minuti mancanti.`);
      break;
    default:
      fail(`${w}: tipo di evento «${String(e.type)}» non riconosciuto.`);
  }
}

const FLAGS = ['ORIGIN_INCOMPLETE', 'A_UNAVAILABLE', 'RIGHT_CENSORED', 'GAP'];
const STAT_FIELDS = ['mean', 'min', 'max', 'p10', 'p25', 'p50', 'p75', 'p90'];

/** Gruppo del riepilogo: conteggi, motivi (letti con Object.entries) e statistiche per misura. */
function validateGroup(g: Obj, w: string, withStats: boolean): void {
  for (const k of ['n', 'originValid', 'aValid', 'futureComplete', 'measuresAvailable', 'measuresMissing']) if (!isInt(g[k])) fail(`${w}: conteggio «${k}» assente o non valido.`);
  const flags = obj(g, 'missingFlags', w);
  for (const k of FLAGS) if (!isInt(flags[k])) fail(`${w}: motivo mancante «${k}» assente o non valido.`);
  if (!withStats) return;
  const stats = obj(g, 'stats', w);
  for (const m of MEASURES) {
    const st = obj(stats, m, w);
    if (!isInt(st.n) || !STAT_FIELDS.every((k) => isNumOrNull(st[k]))) fail(`${w}: statistiche di «${m}» incomplete.`);
  }
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
      validateRecord(r, w);
    });

    let prev = -Infinity;
    arr(events, scale, `Eventi ${scale}`).forEach((e, i) => {
      const w = `Eventi ${scale}, evento ${i + 1}`;
      if (!isObj(e) || !isStr(e.id) || !isStr(e.type) || !isInt(e.eventTime) || !isInt(e.availableAt)) return fail(`${w}: campi obbligatori assenti.`);
      if (e.scale !== scale) fail(`${w}: scala diversa da ${scale}.`);
      if ((e.availableAt as number) < prev || (e.eventTime as number) > (e.availableAt as number)) fail(`${w}: ordine temporale non valido.`);
      prev = e.availableAt as number;
      validateEvent(e, w);
    });
  }
}

function validateStudy(data: Obj, periods: { studyStart: number; end: number }, kind: string): void {
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
  if (kind === CASE_KIND) return validateCase(data, retro, origins);
  const summary = obj(retro, 'summary', 'Riepilogo');
  const periodsList = arr(summary, 'periods', 'Riepilogo');
  const tables = obj(summary, 'tables', 'Riepilogo');
  if (periodsList.length === 0) fail('Riepilogo: nessun periodo.');
  for (const p of periodsList) {
    const w = `Riepilogo, periodo ${String(p)}`;
    const t = obj(tables, String(p), 'Riepilogo');
    const cov = obj(t, 'coverage', w);
    validateGroup(cov, `${w}, copertura`, false);
    const avail = obj(cov, 'availabilityAtOrigin', `${w}, copertura`);
    for (const scale of SCALES) {
      for (const [key, cell] of Object.entries(obj(avail, scale, `${w}, disponibilità`))) {
        if (!isObj(cell) || !isInt(cell.available) || !isInt(cell.missing) || !isObj(cell.reasons)) fail(`${w}: disponibilità di «${key}» (${scale}) incompleta.`);
      }
    }
    const s45 = obj(t, 's45', w);
    const matrix = obj(t, 'matrix', w);
    for (const s of ['UP', 'DOWN', 'MIXED', 'UNAVAILABLE']) {
      validateGroup(obj(s45, s, w), `${w}, gruppo s45 ${s}`, true);
      const row = obj(matrix, s, w);
      if (!['UP', 'DOWN', 'MIXED', 'UNAVAILABLE'].every((d) => isInt(row[d]))) fail(`${w}: matrice incompleta.`);
    }
    const rel = obj(t, 'relation', w);
    for (const side of ['UP', 'DOWN']) {
      const r = obj(rel, side, w);
      for (const k of ['CONCORDANT', 'OPPOSITE', 'MIXED', 'UNAVAILABLE']) {
        validateGroup(obj(r, k, w), `${w}, relazione ${side}/${k}`, true);
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

const CLASSES = ['F_ONLY', 'A_ONLY', 'F_BEFORE_A', 'A_BEFORE_F', 'BOTH_UNORDERED', 'NEITHER'];
const OUTCOME_FLAGS = ['RIGHT_CENSORED', 'GAP', 'MISSING_A', 'ZERO_A'];
const MINUTE = 60_000;
const DAY = 86_400_000;

type Contact = { minute: number; atOpen: boolean; interval: [number, number] } | null;

/** Contatto tipizzato, all'apertura di un minuto della finestra [t, t+24h), intervallo coerente con atOpen. */
function contact(x: unknown, t: number, end: number, where: string): Contact {
  if (x === null) return null;
  if (!isObj(x) || !isInt(x.minute) || typeof x.atOpen !== 'boolean' || !Array.isArray(x.interval) || x.interval.length !== 2 || !x.interval.every(isInt)) {
    return fail(`${where}: contatto non valido.`);
  }
  const m = x.minute as number;
  if (m % MINUTE !== 0) fail(`${where}: il contatto non è all'apertura di un minuto.`);
  if (m < t || m >= end) fail(`${where}: contatto fuori dalla finestra 24h del caso.`);
  const [a, b] = x.interval as number[];
  if (a !== m || b !== (x.atOpen ? m : m + MINUTE)) fail(`${where}: intervallo del contatto incoerente con minuto e apertura.`);
  return x as Contact;
}

/** Classe implicata dai primi contatti (stessa regola del calcolo: nello stesso minuto ordina solo l'apertura). */
function classOf(f: Contact, a: Contact): string {
  if (f === null && a === null) return 'NEITHER';
  if (a === null) return 'F_ONLY';
  if (f === null) return 'A_ONLY';
  if (f.minute !== a.minute) return f.minute < a.minute ? 'F_BEFORE_A' : 'A_BEFORE_F';
  if (f.atOpen && a.atOpen) return 'INVALID';
  if (f.atOpen) return 'F_BEFORE_A';
  return a.atOpen ? 'A_BEFORE_F' : 'BOTH_UNORDERED';
}

/**
 * Esito OBS-002 del caso: coerenza dei campi letti dal blocco a posteriori, non ricalcolo del percorso.
 * Completo: misure finite, escursioni non negative, A positiva, riferimenti = C ± A nel verso, contatti
 * coerenti con la classe, nessun flag. Incompleto: flag riconosciuti, nessuna classe, misura o contatto
 * completo inventato; il prefisso parziale resta separato. Orizzonte t+24h; censura coerente col confine.
 */
function validateObs002Outcome(o: Obj, c: Obj, end: number): void {
  const w = 'Esito OBS-002';
  const t = c.t as number;
  if (o.t !== t || typeof o.complete !== 'boolean' || !Array.isArray(o.flags)) fail(`${w}: istante o completezza non validi.`);
  if (o.horizonEnd !== t + DAY) fail(`${w}: orizzonte diverso da t + 24h.`);
  const flags = o.flags as unknown[];
  for (const f of flags) if (!OUTCOME_FLAGS.includes(f as string)) fail(`${w}: flag non riconosciuto «${String(f)}».`);
  if (new Set(flags).size !== flags.length) fail(`${w}: flag ripetuti.`);
  if (o.complete !== (flags.length === 0)) fail(`${w}: flag incoerenti con la completezza dell'esito.`);
  if (flags.includes('RIGHT_CENSORED') !== (o.horizonEnd as number) > end) fail(`${w}: flag di censura incoerente con il confine dei dati autorizzati.`);
  if (!isNum(o.C)) fail(`${w}: C all'origine non valido.`);
  const d = c.side === 'LONG' ? 1 : -1;
  const aMissing = flags.includes('MISSING_A');
  const aZero = flags.includes('ZERO_A');
  if (aMissing ? o.A !== null : aZero ? o.A !== 0 : !(isNum(o.A) && (o.A as number) > 0)) fail(`${w}: A all'origine incoerente con il suo stato.`);
  if (aMissing || aZero) {
    if (o.markers !== null) fail(`${w}: riferimenti ±A presenti senza A valida.`);
  } else {
    const mk = o.markers;
    const C = o.C as number;
    const A = o.A as number;
    const tol = 1e-9 * Math.max(1, Math.abs(C));
    if (!isObj(mk) || !isNum(mk.F) || !isNum(mk.A) || Math.abs((mk.F as number) - (C + d * A)) > tol || Math.abs((mk.A as number) - (C - d * A)) > tol) {
      fail(`${w}: riferimenti F/A diversi da C ± A nel verso del caso.`);
    }
  }
  const cf = contact(o.contactF, t, o.horizonEnd as number, `${w}, contatto F`);
  const ca = contact(o.contactA, t, o.horizonEnd as number, `${w}, contatto A`);
  if (o.complete) {
    for (const k of ['final', 'favourable', 'adverse']) if (!isNum(o[k])) fail(`${w}: «${k}» mancante o non finito in un esito completo.`);
    if ((o.favourable as number) < 0 || (o.adverse as number) < 0) fail(`${w}: escursioni favorevole e contraria devono essere non negative.`);
    if (!CLASSES.includes(o.class as string)) fail(`${w}: esito completo senza classe di contatto riconosciuta (${String(o.class)}).`);
    if (classOf(cf, ca) !== o.class) fail(`${w}: contatti incoerenti con la classe ${String(o.class)}.`);
    if (!(o.partial === null || o.partial === undefined)) fail(`${w}: prefisso parziale in un esito completo.`);
  } else {
    if (o.class !== null) fail(`${w}: esito incompleto con una classe di contatto.`);
    for (const k of ['final', 'favourable', 'adverse']) if (o[k] !== null) fail(`${w}: misure complete presenti in un esito incompleto («${k}»).`);
    if (cf !== null || ca !== null) fail(`${w}: contatti dell'esito completo presenti in un esito incompleto (stanno nel prefisso parziale).`);
    if (!(o.partial === null || o.partial === undefined || (isObj(o.partial) && isStr(o.partial.label)))) fail(`${w}: prefisso parziale non etichettato.`);
  }
}

/**
 * Pacchetto OBS-002 di un caso: identità dello studio, caso causale all'interno delle origini ed esito
 * a posteriori dello stesso istante. La tabulazione OBS-001 deve essere assente (summary null), non inventata.
 */
function validateCase(data: Obj, retro: Obj, origins: unknown[]): void {
  const study = obj(data, 'study', 'Studio OBS-002');
  if (!isStr(study.id) || !study.id.startsWith('OBS-002/') || !isStr(study.hash) || !isStr(study.label)) fail('Studio OBS-002: identità assente o non riconosciuta.');
  if (retro.summary !== null) fail('Pacchetto OBS-002: la tabulazione OBS-001 non deve essere presente (summary atteso null).');
  const c = obj(data, 'case', 'Caso OBS-002');
  if (!isStr(c.attemptId) || !isInt(c.t) || (c.side !== 'LONG' && c.side !== 'SHORT') || !isStr(c.profile) || !isInt(c.ordinal)) fail('Caso OBS-002: identità del tentativo incompleta.');
  if (!origins.includes(c.t)) fail('Caso OBS-002: l’istante del caso non è fra le origini del pacchetto.');
  if (!Array.isArray(c.categories) || !c.categories.every(isStr)) fail('Caso OBS-002: categorie non valide.');
  obj(c, 'causal', 'Caso OBS-002');
  const o2 = obj(retro, 'obs002', 'Esito OBS-002');
  if (o2.attemptId !== c.attemptId) fail('Esito OBS-002: riferito a un altro tentativo.');
  validateObs002Outcome(obj(o2, 'outcome', 'Esito OBS-002'), c, (data.periods as Obj).end as number);
}

export function parseBundle(text: string): StudyBundle {
  let data: unknown;
  try {
    data = JSON.parse(text);
  } catch {
    return fail('Il file non è un JSON valido. Scegli il file obs001-bundle.json prodotto dal comando «process».');
  }
  if (!isObj(data)) return fail('Formato inatteso: il contenuto non è un oggetto JSON.');
  if (data.kind !== BUNDLE_KIND && data.kind !== CASE_KIND) return fail(`Non è un bundle OBS-001 né un pacchetto di caso OBS-002 (kind=${String(data.kind)}).`);
  const expected = data.kind === CASE_KIND ? CASE_SCHEMA : BUNDLE_SCHEMA;
  if (data.schema !== expected) return fail(`Versione di schema non supportata: ${String(data.schema)} (attesa ${expected}).`);
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
  validateStudy(data, p, data.kind as string);
  return data as unknown as StudyBundle;
}
