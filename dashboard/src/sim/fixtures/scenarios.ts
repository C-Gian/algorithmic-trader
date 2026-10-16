/**
 * Scenari predeterminati della simulazione locale: un percorso LONG e la variante SHORT
 * speculare. Testi, livelli e cifre sono esempi fittizi e non costituiscono strategia,
 * parametri approvati o scelta di prodotto. Le commissioni seguono la cifra di fixture
 * del task (0,1% del nozionale).
 */
import type { Call, Expectation, ObservationFamily, PlanLevels } from '../../contract/types';
import type { CheckpointDef, ObservationDef, ObservationSetDef, ScenarioDef, ScenarioMarket, SimEvent } from '../engine';
import { toIso, usdt, utc } from '../engine';
import {
  DAILY_SYNTHETIC_LONG,
  DAY_OCT14_BEFORE_INTRADAY_LONG,
  INTRADAY_LONG,
  MA_FAST_1D_ANCHORS,
  MA_FAST_45M_ANCHORS,
  MA_SLOW_1D_ANCHORS,
  MA_SLOW_45M_ANCHORS,
  interpolateAnchors,
  mirrorOhlcv,
  mirrorPrice,
} from './market';

const T = (hhmmss: string) => utc(`2026-10-15T${hhmmss}Z`);

/* ------------------------------------------------------------- Testi fissi */

const FAMILY_NOTES: Record<ObservationFamily, { explanation: string; limits: string }> = {
  STRUCTURE: {
    explanation: 'Confronta minimi e massimi delle ultime candele 45m per descrivere la forma del movimento.',
    limits: 'Descrive il passato recente; non stima la probabilità che il movimento continui. Valori d’esempio della simulazione.',
  },
  LEVELS: {
    explanation: 'Livelli dove il prezzo ha rallentato o invertito in passato, sul 45m e sul giornaliero.',
    limits: 'I livelli sono zone, non prezzi esatti, e possono essere superati senza preavviso. Valori d’esempio.',
  },
  MOVING_AVERAGES: {
    explanation: 'Due curve che smussano il prezzo su orizzonti diversi (etichette “EMA 20/50” d’esempio).',
    limits: 'In questa simulazione le curve sono illustrative e non calcolate dai prezzi; i parametri non sono approvati.',
  },
  VOLUME: {
    explanation: 'Confronta il volume dell’ultima candela 45m con un valore di riferimento.',
    limits: 'Il riferimento è un valore d’esempio; più volume non garantisce la continuità del movimento.',
  },
  VOLATILITY: {
    explanation: 'Indica l’escursione tipica delle candele (etichetta “ATR 14” d’esempio).',
    limits: 'Valore statico della simulazione, non calcolato dai prezzi.',
  },
  FIBONACCI: {
    explanation: 'Livelli di ritracciamento fra un minimo e un massimo recenti.',
    limits: 'La scelta degli estremi non è ancora definita dal progetto: qui sono valori d’esempio, non un segnale autonomo.',
  },
};

function obs(
  family: ObservationFamily,
  id: string,
  title: string,
  rest: Omit<ObservationDef, 'id' | 'family' | 'title' | 'explanation' | 'limits'>,
): ObservationDef {
  return { id, family, title, ...FAMILY_NOTES[family], ...rest };
}

/* ------------------------------------------------------------------ LONG */

const longMarket: ScenarioMarket = {
  intraday: INTRADAY_LONG,
  dailySynthetic: DAILY_SYNTHETIC_LONG,
  oct14BeforeIntraday: DAY_OCT14_BEFORE_INTRADAY_LONG,
  maFast45: interpolateAnchors(MA_FAST_45M_ANCHORS, INTRADAY_LONG.length),
  maSlow45: interpolateAnchors(MA_SLOW_45M_ANCHORS, INTRADAY_LONG.length),
  maFast1D: interpolateAnchors(MA_FAST_1D_ANCHORS, 40),
  maSlow1D: interpolateAnchors(MA_SLOW_1D_ANCHORS, 40),
};

const longSets: ObservationSetDef[] = [
  {
    id: 'obs-long-1',
    observedAt: T('10:30:00'),
    reading: 'Medie 20/50 (curve illustrative, parametri d’esempio): 59.760 · 59.740 USDT. Prezzo tra 59.600 e 60.000.',
    levels: [
      { id: 'res', kind: 'RESISTANCE', price: 60000, label: 'RESISTENZA · 60.000' },
      { id: 'sup', kind: 'SUPPORT', price: 59600, label: 'SUPPORTO · 59.600' },
    ],
    fibonacci: [
      { ratio: '38,2%', price: 59714 },
      { ratio: '50%', price: 59625 },
      { ratio: '61,8%', price: 59537 },
    ],
    observations: [
      obs('STRUCTURE', 'structure', 'Struttura / trend', {
        value: { display: 'Laterale', caption: 'Struttura · 45m' },
        badge: { text: 'Da confermare', tone: 'warning' },
        observes: 'Minimi crescenti (59.250 → 59.420 → 59.600) sotto un tetto a 60.000 mai superato.',
        means: 'La struttura migliora, ma finché 60.000 tiene il mercato resta laterale.',
        context: 'Ultimi minimi: 59.250 → 59.420 → 59.600 USDT',
        mini: { kind: 'CLOSES' },
      }),
      obs('LEVELS', 'levels', 'Supporti / resistenze', {
        value: { display: '60.000', caption: 'USDT · resistenza intraday' },
        badge: { text: 'Attenzione', tone: 'warning' },
        observes: 'Il prezzo è 180 USDT sotto la resistenza a 60.000, toccata più volte.',
        means: 'Senza una chiusura sopra 60.000 manca una conferma; non è un invito a comprare.',
        context: 'Supporto 59.600 · Resistenze 60.000 / 61.400 USDT',
        mini: { kind: 'CLOSES_WITH_LEVELS', levels: [60000, 59600] },
      }),
      obs('MOVING_AVERAGES', 'averages', 'Medie mobili', {
        value: { display: '20 ≈ 50', caption: 'Medie esponenziali · 45m · esempio' },
        badge: { text: 'Intrecciate', tone: 'accent' },
        observes: 'EMA 20 a 59.760 ed EMA 50 a 59.740 USDT: quasi sovrapposte.',
        means: 'Nessuna tendenza dominante sul 45 minuti.',
        context: 'Prezzo 59.820 · EMA 20: 59.760 · EMA 50: 59.740',
        mini: { kind: 'MOVING_AVERAGES' },
      }),
      obs('VOLUME', 'volume', 'Volumi', {
        value: { display: '−8,0%', caption: 'rispetto al riferimento di 20 candele' },
        badge: { text: 'Partecipazione debole', tone: 'accent' },
        observes: '102,4 BTC scambiati contro un riferimento di 111,3 BTC.',
        means: 'I volumi non accompagnano ancora un movimento.',
        context: 'Volume candela: 102,4 BTC · Riferimento 20: 111,3 BTC',
        mini: { kind: 'VOLUMES', highlightLast: 4 },
      }),
      obs('VOLATILITY', 'volatility', 'Volatilità', {
        value: { display: '240,00', caption: 'USDT · ATR 14 · esempio' },
        badge: { text: 'Escursioni normali', tone: 'accent' },
        observes: 'L’escursione media resta intorno a 240 USDT.',
        means: 'Oscillazioni ordinarie: nessun segno di accelerazione.',
        context: 'ATR 14: 240 USDT · Riferimento 20 periodi: 235 USDT',
        mini: { kind: 'STATIC_LINE', values: [228, 236, 231, 244, 238, 241, 236, 243, 239, 242, 240, 240] },
      }),
      obs('FIBONACCI', 'fibonacci', 'Fibonacci', {
        value: { display: '59.537–59.714', caption: 'USDT · ritracciamento 61,8–38,2%' },
        badge: { text: 'Zona di riferimento', tone: 'accent' },
        observes: 'Il prezzo resta sopra il ritracciamento del 38,2%.',
        means: 'Questa zona è un riferimento, non un segnale autonomo.',
        context: 'Swing 59.250 → 60.000 · 50%: 59.625 USDT',
        mini: { kind: 'CLOSES_WITH_FIB' },
      }),
    ],
  },
  {
    id: 'obs-long-2',
    observedAt: T('11:15:00'),
    reading: 'Medie 20/50 (curve illustrative, parametri d’esempio): 59.880 · 59.790 USDT. Chiusura sopra 60.000 con volume in aumento.',
    levels: [
      { id: 'sup', kind: 'SUPPORT', price: 60000, label: 'SUPPORTO · 60.000' },
      { id: 'res', kind: 'RESISTANCE', price: 61400, label: 'RESISTENZA 1D · 61.400' },
    ],
    fibonacci: [
      { ratio: '38,2%', price: 59862 },
      { ratio: '50%', price: 59745 },
      { ratio: '61,8%', price: 59628 },
    ],
    observations: [
      obs('STRUCTURE', 'structure', 'Struttura / trend', {
        value: { display: 'Rottura 60.000', caption: 'Struttura · 45m' },
        badge: { text: '↗ Rialzista', tone: 'positive' },
        observes: 'Chiusura a 60.180 sopra il tetto di 60.000; minimi crescenti confermati.',
        means: 'Il rialzo resta ordinato finché 60.000 tiene come supporto.',
        context: 'Ultimi minimi: 59.250 → 59.420 → 59.600 USDT',
        mini: { kind: 'CLOSES' },
      }),
      obs('LEVELS', 'levels', 'Supporti / resistenze', {
        value: { display: '60.000', caption: 'USDT · da resistenza a supporto' },
        badge: { text: 'Attenzione', tone: 'warning' },
        observes: 'Il prezzo è 180 USDT sopra il livello appena superato a 60.000.',
        means: 'Un ritorno su 60.000 è il punto di verifica; sotto 59.000 la lettura cade.',
        context: 'Supporto 60.000 · Resistenze 61.400 / 62.000 USDT',
        mini: { kind: 'CLOSES_WITH_LEVELS', levels: [60000] },
      }),
      obs('MOVING_AVERAGES', 'averages', 'Medie mobili', {
        value: { display: '20 > 50', caption: 'Medie esponenziali · 45m · esempio' },
        badge: { text: '↗ Concordi', tone: 'positive' },
        observes: 'EMA 20 a 59.880, sopra EMA 50 a 59.790 USDT.',
        means: 'Il prezzo recente è più forte della tendenza di fondo.',
        context: 'Prezzo 60.180 · EMA 20: 59.880 · EMA 50: 59.790',
        mini: { kind: 'MOVING_AVERAGES' },
      }),
      obs('VOLUME', 'volume', 'Volumi', {
        value: { display: '+51,0%', caption: 'rispetto al riferimento di 20 candele' },
        badge: { text: 'Partecipazione', tone: 'accent' },
        observes: '168,1 BTC scambiati contro un riferimento di 111,3 BTC.',
        means: 'Più partecipazione sulla rottura, ma non garantisce continuità.',
        context: 'Volume candela: 168,1 BTC · Riferimento 20: 111,3 BTC',
        mini: { kind: 'VOLUMES', highlightLast: 4 },
      }),
      obs('VOLATILITY', 'volatility', 'Volatilità', {
        value: { display: '265,00', caption: 'USDT · ATR 14 · esempio' },
        badge: { text: 'Escursioni in aumento', tone: 'warning' },
        observes: 'L’escursione media è salita da 240 a 265 USDT.',
        means: 'Oscillazioni più ampie: evitare decisioni basate su piccoli scatti.',
        context: 'ATR 14: 265 USDT · Riferimento 20 periodi: 240 USDT',
        mini: { kind: 'STATIC_LINE', values: [236, 243, 239, 242, 240, 240, 246, 251, 255, 259, 262, 265] },
      }),
      obs('FIBONACCI', 'fibonacci', 'Fibonacci', {
        value: { display: '59.628–59.862', caption: 'USDT · ritracciamento 61,8–38,2%' },
        badge: { text: 'Zona di riferimento', tone: 'accent' },
        observes: 'Il prezzo è sopra l’intera zona di ritracciamento.',
        means: 'Questa zona è un riferimento, non un segnale autonomo.',
        context: 'Swing 59.250 → 60.240 · 50%: 59.745 USDT',
        mini: { kind: 'CLOSES_WITH_FIB' },
      }),
    ],
  },
  {
    id: 'obs-long-3',
    observedAt: T('14:15:00'),
    reading: 'Medie 20/50 (curve illustrative, parametri d’esempio): 60.780 · 60.310 USDT.',
    levels: [
      { id: 'sup', kind: 'SUPPORT', price: 60400, label: 'SUPPORTO · 60.400' },
      { id: 'res', kind: 'RESISTANCE', price: 61400, label: 'RESISTENZA 1D · 61.400' },
    ],
    fibonacci: [
      { ratio: '38,2%', price: 60695 },
      { ratio: '50%', price: 60555 },
      { ratio: '61,8%', price: 60415 },
    ],
    observations: [
      obs('STRUCTURE', 'structure', 'Struttura / trend', {
        value: { display: 'Minimi crescenti', caption: 'Struttura · 45m' },
        badge: { text: '↗ Rialzista', tone: 'positive' },
        observes: 'Nuovo minimo crescente a 60.400, sopra l’ingresso; prezzo 61.000 USDT.',
        means: 'Il rialzo resta ordinato finché 60.400 tiene.',
        context: 'Ultimi minimi: 59.600 → 59.960 → 60.400 USDT',
        mini: { kind: 'CLOSES' },
      }),
      obs('LEVELS', 'levels', 'Supporti / resistenze', {
        value: { display: '61.400', caption: 'USDT · prossima resistenza (1D)' },
        badge: { text: 'Attenzione', tone: 'warning' },
        observes: 'Il prezzo è a 400 USDT dalla resistenza giornaliera a 61.400.',
        means: 'Il movimento può rallentare; non è un invito ad aumentare la posizione.',
        context: 'Supporto 60.400 · Resistenze 61.400 / 62.000 USDT',
        mini: { kind: 'CLOSES_WITH_LEVELS', levels: [60400] },
      }),
      obs('MOVING_AVERAGES', 'averages', 'Medie mobili', {
        value: { display: '20 > 50', caption: 'Medie esponenziali · 45m · esempio' },
        badge: { text: '↗ Concordi', tone: 'positive' },
        observes: 'EMA 20 a 60.780, sopra EMA 50 a 60.310 USDT.',
        means: 'Il prezzo recente è più forte della tendenza di fondo.',
        context: 'Prezzo 61.000 · EMA 20: 60.780 · EMA 50: 60.310',
        mini: { kind: 'MOVING_AVERAGES' },
      }),
      obs('VOLUME', 'volume', 'Volumi', {
        value: { display: '+6,0%', caption: 'rispetto al riferimento di 20 candele' },
        badge: { text: 'Partecipazione normale', tone: 'accent' },
        observes: '118,0 BTC scambiati contro un riferimento di 111,3 BTC.',
        means: 'Partecipazione nella norma: nessuna accelerazione dei volumi.',
        context: 'Volume candela: 118,0 BTC · Riferimento 20: 111,3 BTC',
        mini: { kind: 'VOLUMES', highlightLast: 4 },
      }),
      obs('VOLATILITY', 'volatility', 'Volatilità', {
        value: { display: '300,00', caption: 'USDT · ATR 14 · esempio' },
        badge: { text: 'Escursioni ampie', tone: 'warning' },
        observes: 'L’escursione media è salita da 265 a 300 USDT.',
        means: 'Oscillazioni più ampie: evitare decisioni basate su piccoli scatti.',
        context: 'ATR 14: 300 USDT · Riferimento 20 periodi: 250 USDT',
        mini: { kind: 'STATIC_LINE', values: [265, 270, 268, 276, 281, 279, 286, 290, 288, 294, 297, 300] },
      }),
      obs('FIBONACCI', 'fibonacci', 'Fibonacci', {
        value: { display: '60.415–60.695', caption: 'USDT · ritracciamento 61,8–38,2%' },
        badge: { text: 'Zona di supporto', tone: 'accent' },
        observes: 'Il prezzo resta sopra il ritracciamento del 38,2%.',
        means: 'Questa zona è un riferimento, non un segnale autonomo.',
        context: 'Swing 59.960 → 61.150 · 50%: 60.555 USDT',
        mini: { kind: 'CLOSES_WITH_FIB' },
      }),
    ],
  },
];

const expectation = (id: string, at: number, e: Omit<Expectation, 'id' | 'updatedAt'>): Expectation => ({ id, updatedAt: toIso(at), ...e });

const longPlan: PlanLevels = {
  setAt: toIso(T('11:15:00')),
  entryZone: { low: usdt(59950), high: usdt(60050) },
  entryCondition: 'Ingresso solo con un ritorno nella fascia 59.950–60.050 USDT, entro la validità della call.',
  stop: usdt(59000),
  targets: [usdt(62000)],
  invalidation: 'Chiusura 45m sotto 59.000 USDT: la lettura rialzista decade.',
};

const longCall: Call = {
  id: 'call-long-015',
  displayId: 'BTC-015',
  direction: 'LONG',
  status: 'AVAILABLE',
  createdAt: toIso(T('11:15:00')),
  rationale: 'Il prezzo ha superato 60.000 e resta sopra le medie.',
  explanation: 'I minimi stanno salendo e i volumi accompagnano la rottura. La call attende un ritorno su 60.000, senza inseguire il prezzo.',
  contraindication: {
    title: 'Controindicazione: resistenza giornaliera',
    text: 'A 61.400 USDT i venditori hanno già frenato il prezzo l’8 ottobre. Un ritorno sotto 59.000 invalida la lettura.',
  },
  conditions: ['Ingresso solo nella fascia 59.950–60.050 USDT', 'Una sola posizione BTC; nessun aumento di quantità'],
  validity: {
    from: toIso(T('11:15:00')),
    entryUntil: toIso(T('12:45:00')),
    note: 'Alla scadenza: nessun nuovo ingresso; la posizione resta protetta da stop e target fino all’uscita.',
  },
  expectedDuration: '2–6 ore dall’ingresso',
};

const longEvents: SimEvent[] = [
  {
    kind: 'OBSERVATIONS',
    id: 'l-obs-1',
    at: T('10:30:00'),
    setId: 'obs-long-1',
    summary: 'Prezzo 59.820 tra 59.600 e 60.000. Trend e volumi non allineati: nessuna call.',
    expectation: expectation('exp-long-1', T('10:30:00'), {
      direction: 'UNCERTAIN',
      description: 'Laterale tra 59.600 e 60.000. Una chiusura sopra 60.000 renderebbe plausibile un rialzo.',
      alternatives: ['Chiusura sotto 59.600: la sequenza di minimi crescenti si interrompe.'],
      contraindications: ['Volumi sotto il valore di riferimento.'],
    }),
  },
  {
    kind: 'OBSERVATIONS',
    id: 'l-obs-2',
    at: T('11:15:00'),
    setId: 'obs-long-2',
    summary: 'Chiusura 45m a 60.180 sopra 60.000 con volume in aumento.',
    expectation: expectation('exp-long-2', T('11:15:00'), {
      direction: 'UP',
      description: 'Rialzo plausibile dopo il superamento di 60.000.',
      alternatives: ['Ritorno stabile sotto 60.000 e nuova fase laterale.'],
      contraindications: ['Resistenza giornaliera a 61.400.'],
    }),
  },
  { kind: 'CALL_CREATED', id: 'l-call', at: T('11:15:00'), call: longCall, plan: { original: longPlan, expiresAt: T('19:30:00'), reason: 'Superamento di 60.000 con volume; piano illustrativo dello scenario.' } },
  {
    kind: 'ORDER_CREATED',
    id: 'l-entry-order',
    at: T('11:20:00'),
    origin: 'BOT',
    order: { id: 'ord-entry-015', purpose: 'ENTRY', side: 'BUY', type: 'LIMIT', qty: 0.01, limitPrice: 60000 },
    outcome: 'ACCEPTED',
  },
  { kind: 'FILL', id: 'l-entry-fill', at: T('12:31:00'), orderId: 'ord-entry-015', price: 60000 },
  { kind: 'PROTECTIONS_PLACED', id: 'l-protections', at: T('12:31:05'), stopOrderId: 'ord-stop-015', targetOrderId: 'ord-target-015' },
  {
    kind: 'OBSERVATIONS',
    id: 'l-obs-3',
    at: T('14:15:00'),
    setId: 'obs-long-3',
    summary: 'Nuovo minimo crescente a 60.400; prezzo 61.000.',
    expectation: expectation('exp-long-3', T('14:15:00'), {
      direction: 'UP',
      description: 'Rialzo ordinato: nuovo minimo crescente a 60.400.',
      alternatives: ['Rallentamento sotto la resistenza giornaliera a 61.400.'],
      contraindications: ['Escursioni più ampie della media.'],
    }),
  },
  {
    kind: 'PLAN_CHANGE',
    id: 'l-stop-move',
    at: T('14:15:00'),
    field: 'STOP',
    after: 60200,
    reason: 'Nuovo minimo crescente a 60.400 sopra l’ingresso: stop portato sotto quel minimo. Target invariato.',
  },
  {
    kind: 'ORDER_CREATED',
    id: 'l-partial-order',
    at: T('14:59:00'),
    origin: 'OWNER',
    order: { id: 'ord-exit-partial-015', purpose: 'EXIT', side: 'SELL', type: 'MARKET', qty: 0.004 },
    outcome: 'REQUESTED',
  },
  { kind: 'FILL', id: 'l-partial-fill', at: T('15:00:00'), orderId: 'ord-exit-partial-015', price: 61000 },
  {
    kind: 'ORDER_CREATED',
    id: 'l-close-order',
    at: T('15:44:00'),
    origin: 'OWNER',
    order: { id: 'ord-exit-close-015', purpose: 'EXIT', side: 'SELL', type: 'MARKET', qty: 0.006 },
    outcome: 'REQUESTED',
  },
  { kind: 'FILL', id: 'l-close-fill', at: T('15:45:00'), orderId: 'ord-exit-close-015', price: 60500 },
  {
    kind: 'OBSERVATIONS',
    id: 'l-obs-4',
    at: T('15:45:00'),
    setId: 'obs-long-3',
    summary: 'Posizione chiusa. Nessuna nuova call: si attende una nuova struttura.',
    expectation: expectation('exp-long-4', T('15:45:00'), {
      direction: 'UNCERTAIN',
      description: 'Dopo la chiusura, attesa di una nuova struttura prima di qualsiasi call.',
      alternatives: ['Ripresa del rialzo sopra 61.150.', 'Ritorno verso il supporto a 60.400.'],
      contraindications: [],
    }),
  },
];

const longCheckpoints: CheckpointDef[] = [
  { id: 'long-1-waiting', label: '1 · Attesa, nessuna call', description: 'Aspettativa senza call operativa.', at: T('10:30:00'), initialMode: 'CALL_AND_EXECUTION' },
  { id: 'long-2-opportunity', label: '2 · Opportunità senza posizione', description: 'Call disponibile, nessun ordine.', at: T('11:15:00'), initialMode: 'CALL_AND_EXECUTION' },
  { id: 'long-3-pending', label: '3 · Ordine accettato, non eseguito', description: 'Ordine d’ingresso in attesa: nessuna posizione, nessun P&L.', at: T('12:00:00'), initialMode: 'CALL_AND_EXECUTION' },
  {
    id: 'long-3r-rejected',
    label: '3b · Ordine rifiutato',
    description: 'Rifiuto simulato: nessun eseguito, nessuna commissione.',
    at: T('12:00:00'),
    initialMode: 'CALL_AND_EXECUTION',
    exclude: ['l-entry-order'],
    extra: [
      {
        kind: 'ORDER_CREATED',
        id: 'l-entry-order-rejected',
        at: T('11:20:02'),
        origin: 'BOT',
        order: { id: 'ord-entry-015r', purpose: 'ENTRY', side: 'BUY', type: 'LIMIT', qty: 0.01, limitPrice: 60000 },
        outcome: 'REJECTED',
        rejection: { code: 'SIM-E104', message: 'Rifiuto predeterminato del simulatore: prezzo fuori dalla fascia del piano all’invio' },
      },
    ],
  },
  { id: 'long-4-open', label: '4 · Posizione LONG aperta', description: 'Eseguito 0,01 BTC a 60.000; valutazione 61.000.', at: T('13:30:00'), initialMode: 'CALL_AND_EXECUTION' },
  { id: 'long-5-protection', label: '5 · Protezione aggiornata', description: 'Stop da 59.000 a 60.200 con evento prima/dopo.', at: T('14:15:00'), initialMode: 'CALL_AND_EXECUTION' },
  {
    id: 'long-5m-manual',
    label: '5b · Gestione manuale',
    description: 'Stessa posizione, gestione passata all’Owner.',
    at: T('14:20:00'),
    initialMode: 'CALL_AND_EXECUTION',
    extra: [{ kind: 'MODE', id: 'l-manual', at: T('14:18:00'), origin: 'OWNER', mode: 'CALL_ONLY' }],
  },
  {
    id: 'long-5s-stopped',
    label: '5c · Bot fermo, posizione aperta',
    description: 'Stop totale: posizione e protezioni invariate.',
    at: T('14:20:00'),
    initialMode: 'CALL_AND_EXECUTION',
    extra: [{ kind: 'BOT', id: 'l-stopped', at: T('14:18:00'), origin: 'OWNER', status: 'STOPPED', reason: 'Stop totale richiesto dall’Owner' }],
  },
  { id: 'long-6-partial', label: '6 · Uscita parziale', description: '0,004 BTC a 61.000; residuo 0,006.', at: T('15:00:00'), initialMode: 'CALL_AND_EXECUTION' },
  { id: 'long-7-closed', label: '7 · Chiusa, call conclusa', description: 'Residuo chiuso a 60.500; nessuna posizione.', at: T('15:45:00'), initialMode: 'CALL_AND_EXECUTION' },
];

export const LONG_SCENARIO: ScenarioDef = {
  id: 'long',
  label: 'Percorso LONG',
  direction: 'LONG',
  startsAt: T('10:00:00'),
  market: longMarket,
  observationSets: longSets,
  events: longEvents,
  checkpoints: longCheckpoints,
};

/* ----------------------------------------------------------------- SHORT */

const shortMarket: ScenarioMarket = {
  intraday: INTRADAY_LONG.map(mirrorOhlcv),
  dailySynthetic: DAILY_SYNTHETIC_LONG.map(mirrorOhlcv),
  oct14BeforeIntraday: {
    open: mirrorPrice(DAY_OCT14_BEFORE_INTRADAY_LONG.open),
    high: mirrorPrice(DAY_OCT14_BEFORE_INTRADAY_LONG.low),
    low: mirrorPrice(DAY_OCT14_BEFORE_INTRADAY_LONG.high),
    volume: DAY_OCT14_BEFORE_INTRADAY_LONG.volume,
  },
  maFast45: longMarket.maFast45.map(mirrorPrice),
  maSlow45: longMarket.maSlow45.map(mirrorPrice),
  maFast1D: longMarket.maFast1D.map(mirrorPrice),
  maSlow1D: longMarket.maSlow1D.map(mirrorPrice),
};

const shortSets: ObservationSetDef[] = [
  {
    id: 'obs-short-2',
    observedAt: T('11:15:00'),
    reading: 'Medie 20/50 (curve illustrative, parametri d’esempio): 60.120 · 60.210 USDT. Chiusura sotto 60.000 con volume in aumento.',
    levels: [
      { id: 'res', kind: 'RESISTANCE', price: 60000, label: 'RESISTENZA · 60.000' },
      { id: 'sup', kind: 'SUPPORT', price: 58600, label: 'SUPPORTO 1D · 58.600' },
    ],
    fibonacci: [
      { ratio: '38,2%', price: 60138 },
      { ratio: '50%', price: 60255 },
      { ratio: '61,8%', price: 60372 },
    ],
    observations: [
      obs('STRUCTURE', 'structure', 'Struttura / trend', {
        value: { display: 'Rottura 60.000', caption: 'Struttura · 45m' },
        badge: { text: '↘ Ribassista', tone: 'negative' },
        observes: 'Chiusura a 59.820 sotto il pavimento di 60.000; massimi decrescenti confermati.',
        means: 'Il ribasso resta ordinato finché 60.000 tiene come resistenza.',
        context: 'Ultimi massimi: 60.750 → 60.580 → 60.400 USDT',
        mini: { kind: 'CLOSES' },
      }),
      obs('LEVELS', 'levels', 'Supporti / resistenze', {
        value: { display: '60.000', caption: 'USDT · da supporto a resistenza' },
        badge: { text: 'Attenzione', tone: 'warning' },
        observes: 'Il prezzo è 180 USDT sotto il livello appena rotto a 60.000.',
        means: 'Un ritorno su 60.000 è il punto di verifica; sopra 61.000 la lettura cade.',
        context: 'Resistenza 60.000 · Supporti 58.600 / 58.000 USDT',
        mini: { kind: 'CLOSES_WITH_LEVELS', levels: [60000] },
      }),
      obs('MOVING_AVERAGES', 'averages', 'Medie mobili', {
        value: { display: '20 < 50', caption: 'Medie esponenziali · 45m · esempio' },
        badge: { text: '↘ Concordi', tone: 'negative' },
        observes: 'EMA 20 a 60.120, sotto EMA 50 a 60.210 USDT.',
        means: 'Il prezzo recente è più debole della tendenza di fondo.',
        context: 'Prezzo 59.820 · EMA 20: 60.120 · EMA 50: 60.210',
        mini: { kind: 'MOVING_AVERAGES' },
      }),
      obs('VOLUME', 'volume', 'Volumi', {
        value: { display: '+51,0%', caption: 'rispetto al riferimento di 20 candele' },
        badge: { text: 'Partecipazione', tone: 'accent' },
        observes: '168,1 BTC scambiati contro un riferimento di 111,3 BTC.',
        means: 'Più partecipazione sulla rottura al ribasso, ma non garantisce continuità.',
        context: 'Volume candela: 168,1 BTC · Riferimento 20: 111,3 BTC',
        mini: { kind: 'VOLUMES', highlightLast: 4 },
      }),
      obs('VOLATILITY', 'volatility', 'Volatilità', {
        value: { display: '265,00', caption: 'USDT · ATR 14 · esempio' },
        badge: { text: 'Escursioni in aumento', tone: 'warning' },
        observes: 'L’escursione media è salita da 240 a 265 USDT.',
        means: 'Oscillazioni più ampie: evitare decisioni basate su piccoli scatti.',
        context: 'ATR 14: 265 USDT · Riferimento 20 periodi: 240 USDT',
        mini: { kind: 'STATIC_LINE', values: [236, 243, 239, 242, 240, 240, 246, 251, 255, 259, 262, 265] },
      }),
      obs('FIBONACCI', 'fibonacci', 'Fibonacci', {
        value: { display: '60.138–60.372', caption: 'USDT · ritracciamento 38,2–61,8%' },
        badge: { text: 'Zona di riferimento', tone: 'accent' },
        observes: 'Il prezzo è sotto l’intera zona di ritracciamento.',
        means: 'Questa zona è un riferimento, non un segnale autonomo.',
        context: 'Swing 60.750 → 59.760 · 50%: 60.255 USDT',
        mini: { kind: 'CLOSES_WITH_FIB' },
      }),
    ],
  },
];

const shortPlan: PlanLevels = {
  setAt: toIso(T('11:15:00')),
  entryZone: { low: usdt(59950), high: usdt(60050) },
  entryCondition: 'Ingresso solo con un ritorno nella fascia 59.950–60.050 USDT, entro la validità della call.',
  stop: usdt(61000),
  targets: [usdt(58000)],
  invalidation: 'Chiusura 45m sopra 61.000 USDT: la lettura ribassista decade.',
};

const shortCall: Call = {
  id: 'call-short-021',
  displayId: 'BTC-021',
  direction: 'SHORT',
  status: 'AVAILABLE',
  createdAt: toIso(T('11:15:00')),
  rationale: 'Il prezzo ha rotto 60.000 al ribasso e resta sotto le medie.',
  explanation: 'I massimi stanno scendendo e i volumi accompagnano la rottura. La call attende un ritorno su 60.000, senza inseguire il prezzo.',
  contraindication: {
    title: 'Controindicazione: supporto giornaliero',
    text: 'A 58.600 USDT i compratori hanno già frenato il prezzo. Un ritorno sopra 61.000 invalida la lettura.',
  },
  conditions: ['Ingresso solo nella fascia 59.950–60.050 USDT', 'Una sola posizione BTC; nessun aumento di quantità'],
  validity: {
    from: toIso(T('11:15:00')),
    entryUntil: toIso(T('12:45:00')),
    note: 'Alla scadenza: nessun nuovo ingresso; la posizione resta protetta da stop e target fino all’uscita.',
  },
  expectedDuration: '2–6 ore dall’ingresso',
};

const shortEvents: SimEvent[] = [
  {
    kind: 'OBSERVATIONS',
    id: 's-obs-2',
    at: T('11:15:00'),
    setId: 'obs-short-2',
    summary: 'Chiusura 45m a 59.820 sotto 60.000 con volume in aumento.',
    expectation: expectation('exp-short-2', T('11:15:00'), {
      direction: 'DOWN',
      description: 'Ribasso plausibile dopo la rottura di 60.000.',
      alternatives: ['Ritorno stabile sopra 60.000 e nuova fase laterale.'],
      contraindications: ['Supporto giornaliero a 58.600.'],
    }),
  },
  { kind: 'CALL_CREATED', id: 's-call', at: T('11:15:00'), call: shortCall, plan: { original: shortPlan, expiresAt: T('19:30:00'), reason: 'Rottura di 60.000 al ribasso con volume; piano illustrativo dello scenario.' } },
  {
    kind: 'ORDER_CREATED',
    id: 's-entry-order',
    at: T('11:20:00'),
    origin: 'BOT',
    order: { id: 'ord-entry-021', purpose: 'ENTRY', side: 'SELL', type: 'LIMIT', qty: 0.01, limitPrice: 60000 },
    outcome: 'ACCEPTED',
  },
  { kind: 'FILL', id: 's-entry-fill', at: T('12:31:00'), orderId: 'ord-entry-021', price: 60000 },
  { kind: 'PROTECTIONS_PLACED', id: 's-protections', at: T('12:31:05'), stopOrderId: 'ord-stop-021', targetOrderId: 'ord-target-021' },
];

const shortCheckpoints: CheckpointDef[] = [
  {
    id: 'short-2-proposal',
    label: 'S1 · Proposta SHORT senza ordine',
    description: 'Solo call: lettura ribassista, nessun ordine.',
    at: T('11:15:00'),
    initialMode: 'CALL_ONLY',
    exclude: ['s-call'],
    extra: [{ kind: 'CALL_CREATED', id: 's-call-proposed', at: T('11:15:00'), call: { ...shortCall, status: 'PROPOSED' }, plan: { original: shortPlan, expiresAt: T('19:30:00'), reason: 'Rottura di 60.000 al ribasso con volume; piano illustrativo dello scenario.' } }],
  },
  { id: 'short-4-open', label: 'S2 · Posizione SHORT aperta', description: 'Eseguito SELL 0,01 BTC a 60.000; valutazione 59.000.', at: T('13:30:00'), initialMode: 'CALL_AND_EXECUTION' },
];

export const SHORT_SCENARIO: ScenarioDef = {
  id: 'short',
  label: 'Variante SHORT speculare',
  direction: 'SHORT',
  startsAt: T('10:00:00'),
  market: shortMarket,
  observationSets: shortSets,
  events: shortEvents,
  checkpoints: shortCheckpoints,
};

export const SCENARIOS: readonly ScenarioDef[] = [LONG_SCENARIO, SHORT_SCENARIO];
export const INITIAL_CHECKPOINT_ID = 'long-5-protection';
