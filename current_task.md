# Incarico corrente — UI-001

**Stato: DELIVERED — consegna dell'esecutore in attesa di review del Director (vedi «Spazio dell'esecutore»).**

Macro-obiettivo autorizzato: dashboard fedele al Figma approvato, con stati simulati coerenti e fornitore dati separato. Disposizione Astra trasmessa dall'Owner il 16 ottobre 2026.
Responsabile del task/review: Director. Esecutore: Claude Code.
Base minima: commit che contiene questo READY e docs/ui/FIGMA-REFERENCE.md; Gian sincronizza il checkout al commit completo comunicato dal Director. Nessun pull dell'esecutore.
Macrofase autorizzata: non chiedere nuova approvazione ad Astra per avvio o correzioni ordinarie.

## 1. Design disponibile e verifica iniziale obbligatoria

Figma: https://www.figma.com/design/ys2HFfjS2OdaLLTsfhPp9A/Untitled?node-id=2-9260
File key ys2HFfjS2OdaLLTsfhPp9A. Dashboard 2:9260.
Leggere [riferimento Figma](docs/ui/FIGMA-REFERENCE.md): mappa nodi, anteprime, stile, interazioni e correzioni semantiche definite dal Director. Non è un nuovo design da inventare.

Il Director ha letto il progetto tramite l'integrazione Figma, con metadata, screenshot e contesti completi dei sottoalberi; accesso riuscito qui. Quello di Claude non è ancora verificato e va accertato prima del codice UI.

Fase A, nello stesso task:
1. Verificare identità repo/branch/base e modifiche locali secondo AGENTS.
2. Verificare quali strumenti Figma sono effettivamente disponibili; leggere dashboard e componenti del file fornito con contesto e screenshot. Non basta aprire l'URL o vedere il titolo.
3. Registrare nella consegna metodo, nodi letti e risultato. Se l'accesso funziona, proseguire direttamente con l'implementazione: non attendere un nuovo permesso.
4. Se impossibile ottenere il contesto completo, segnare BLOCKED con errore/capacità mancante. Non ridisegnare da una sola immagine, non installare integrazioni e non modificare il Figma. La documentazione locale è supporto, non prova dell'accesso al progetto completo.

Fase B: dashboard e simulazioni secondo il resto del mandato. Nessuna delega della strategia all'esecutore.

## 2. Risultato concreto e soluzione proporzionata

Dashboard locale frontend, avviabile su Windows dal PC dell'Owner. Scelta del Director: React e TypeScript con Vite, CSS coerente con Figma. Una singola app frontend, nessun backend/DB/autenticazione/container necessario. Se il progetto Figma include già sorgenti riutilizzabili, ispezionarli prima di ricreare i componenti; adeguare l'impalcatura solo se necessario e documentare la ragione.

Versioni, requisiti Node e comandi saranno verificati e fissati nel lockfile durante l'esecuzione. La scelta di una libreria grafica deve soddisfare candele, serie e livelli richiesti dal progetto, funzionamento locale e licenza compatibile; niente CDN o dati remoti a runtime. Non scegliere infrastrutture per una futura API ancora inesistente.

Banner persistente in tutti gli stati: **SIMULAZIONE LOCALE — nessun collegamento exchange**.
Il marchio Binance può comparire soltanto come riferimento del design, mai come prova di collegamento. Dicitura “Demo connessa” vietata se induce a credere a una sessione vera. Stato di connessione nel simulatore esplicitamente etichettato “feed simulato”.

## 3. Contratto minimo di presentazione definito dal Director

Contratto versionato in TypeScript, indipendente dal rendering e non equivalente a uno schema DB. ID stabili e timestamp ISO UTC; fuso leggibile nell'interfaccia. Quantità/importi con unità esplicite; arrotondare soltanto in visualizzazione. Distinguere zero noto da valore mancante. Per valori mancanti: null più motivo, ad esempio NOT_APPLICABLE, NOT_PROVIDED, STALE o UNAVAILABLE. Liste vuote note non equivalgono a caricamento o errore.

| Modello | Informazioni e significato |
|---|---|
| Context | scenarioId, simulated=true, clock simulato, strumento/base/quotazione, productLabel illustrativa, environment=LOCAL_SIMULATION, modalità CALL_ONLY/CALL_AND_EXECUTION, bot RUNNING/STOPPED, feed simulato OK/DISCONNECTED, observedAt/receivedAt/freshness e spiegazione |
| Chart | timeframe 45m/1D, candele OHLCV esplicite per ciascuna scala, serie già preparate con nome/unità/parametri illustrativi, livelli con origine OBSERVATION/ORIGINAL_PLAN/CURRENT_PLAN/POSITION e validità; nessuna elaborazione indicatori nei componenti |
| Observation | famiglia STRUCTURE/LEVELS/MOVING_AVERAGES/VOLUME/VOLATILITY/FIBONACCI, disponibilità, scala e tempo, valore se presente, testo semplice, spiegazione e limiti; nessun voto o probabilità inventati |
| Expectation | descrizione e direzione UP/DOWN/UNCERTAIN, alternative/controindicazioni, updatedAt; può esistere anche senza call |
| Call | id, direzione LONG/SHORT, stato PROPOSED/AVAILABLE/ACTIVE/EXPIRED/WITHDRAWN/COMPLETED, condizioni e validità; non rappresenta ordine né posizione |
| Plan | callId, versione, piano originario immutabile e corrente, ingresso/condizioni, target anche multipli se visibili, stop/invalidazione, scadenza, ragione; cambi con prima/dopo/orario; null quando non esiste un piano |
| Order | id, callId opzionale, scopo ENTRY/PROTECTION/EXIT, side BUY/SELL, quantità richiesta/eseguita, tipo illustrativo, stato REQUESTED/ACCEPTED/PARTIALLY_FILLED/FILLED/CANCELLED/REJECTED, prezzo/trigger se pertinente; accettato non significa eseguito |
| Fill | id, orderId, timestamp, side, quantità/prezzo e commissione con valuta; unica fonte degli eseguiti simulati |
| Position | id, LONG/SHORT, quantità residua, prezzo medio di ingresso, riferimento di valutazione e tempo, protezioni effettivamente simulate, titolarità gestione BOT/MANUAL; null quando nessun eseguito ha aperto esposizione |
| Account/results | valuta, saldo iniziale, saldo contabile simulato, equity, P&L realizzato lordo, costi effettivamente addebitati, P&L realizzato netto, P&L non realizzato lordo e costi di uscita non inclusi; margine/disponibile null se non simulati |
| History | id evento, tipo, timestamp, collegamenti a call/ordine/posizione/piano, testo, cambi prima/dopo; eventi passati non presentati come call corrente |

ACTIVE indica call seguita dopo l'ingresso; non permette un secondo ingresso. La scadenza della call non chiude da sola la posizione. Freschezza e disponibilità sono qualificabili anche per posizione/protezioni/valutazione: lastKnown con orario è distinto da current; P&L attuale null durante disconnessione. Il provider espone scadenze e transizioni già predeterminate, senza decisioni dal mercato.

Si può affinare la forma dei tipi per aderire al Figma senza fondere i significati. Parametri di medie, percentuali, capitale, leva e Spot/futures nelle fixture sono esempi esplicitamente etichettati, non decisioni operative. Nessun calcolo o regola di DESIGN-001 si attiva per popolare questi modelli.

Provider separato: caricamento scenario, snapshot e comandi simulati. I componenti consumano snapshot e inviano intenzioni; il provider gestisce le sole transizioni predeterminate. Niente deduzione di direzione, segnali o gestione dai prezzi. Formattazione e calcoli grafici geometrici consentiti; contabilità in una funzione del dominio simulato testabile, non duplicata nei widget.

## 4. Scenari piccoli e coerenti

Un percorso LONG e una variante SHORT speculare, con checkpoint riutilizzati; non dieci simulatori indipendenti. Poche decine di candele per scala, già preparate per visualizzazione; niente mesi di minuti, warmup analitico o motore di mercato. Entrambe le scale devono riflettere lo stesso percorso nei periodi sovrapposti. Un breve contesto giornaliero sintetico può precedere il segmento intraday senza fingere copertura intraday assente.

Checkpoint: attesa con aspettativa ma nessuna call; opportunità senza posizione; ordine accettato ancora non eseguito; eseguito e posizione LONG; protezione aggiornata; uscita parziale; chiusura; variante posizione SHORT. Dati non aggiornati e disconnessione sono alterazioni controllate degli stessi checkpoint, preservando ultimo valore noto e relativo orario. Includere anche ordine rifiutato senza fill/fee, posizione manuale e bot fermo come nella tavola Figma; riutilizzare lo stesso percorso, senza una nuova contabilità per ogni scheda.

Esempio contabile vincolante per il percorso LONG, tutti valori fittizi in USDT:
- saldo iniziale 10.000; ingresso 0,01 BTC a 60.000; fee ingresso 0,60;
- valutazione a 61.000: non realizzato lordo +10; saldo 9.999,40; equity 10.009,40;
- protezione simulata aggiornata da 59.000 a 60.200 con evento prima/dopo; nessun P&L realizzato dall'aggiornamento;
- parziale 0,004 a 61.000, fee 0,244: lordo realizzato +4; costi cumulati 0,844; realizzato netto cumulato +3,156; saldo 10.003,156; residuo 0,006 con non realizzato +6; equity 10.009,156;
- chiusura residuo a 60.500, fee 0,363: lordo totale +7; costi totali 1,207; netto +5,793; saldo/equity 10.005,793; nessuna posizione residua.
La fee è una cifra di fixture, non tariffa exchange. Equity=saldo+non realizzato lordo. Nessuna detrazione del nozionale dal saldo in questo esempio di contratto lineare illustrativo; margine e leva non modellati e non esposti con numeri inventati. Il prezzo di valutazione non implica liquidabilità a quel prezzo.

SHORT: ingresso 0,01 a 60.000, fee 0,60, valutazione 59.000: non realizzato lordo +10, saldo 9.999,40, equity 10.009,40. Direzione ordine di ingresso SELL e chiusura BUY; protezione sopra il prezzo, nessuna posizione LONG contemporanea. Nessuna necessità di replicare tutte le parziali.

Ordine pendente: nessuna posizione, nessun P&L e nessuna fee di esecuzione. Una call senza ordine non occupa capitale. Quantità e costi di uscita si riconciliano con fill, storia e quantità residua. Funding esplicitamente non applicato nell'esempio breve; non rappresentare un campo mancante come zero noto. Grafico, tempi e livelli devono contenere e rendere plausibili gli eseguiti illustrativi.

Selezione checkpoint e reset riproducibili; orologio deterministico. Nessuna persistenza indispensabile: ricarica/reset torna allo scenario iniziale dichiarato. Se si sceglie persistenza UI, separarla dagli eventi contabili per evitare duplicazioni.

## 5. Interazioni e conseguenze

- Scelta scenario in un controllo chiaramente di simulazione, integrato senza alterare il design principale.
- Timeframe, strumenti del grafico, dettagli osservazioni, cronologia e viste effettivamente previste dal Figma funzionanti.
- Sezioni fuori perimetro dichiarate “Non disponibile in questa versione”; evitare pagine apparentemente reali con bottoni inerti non spiegati.
- CALL_ONLY non invia ordini simulati nuovi né gestisce attivamente la posizione.
- Passaggio a CALL_ONLY con posizione BOT richiede conferma: indica quantità, protezioni rimaste e rilascio della gestione; annulla lascia tutto invariato. Nessuna protezione esistente rimossa.
- Ritorno a CALL_AND_EXECUTION con posizione MANUAL richiede conferma esplicita di presa in gestione. Nessun ingresso duplicato.
- Stop totale ferma analisi/azioni simulate del bot e annulla ingressi pendenti; mantiene posizione e protezioni. Conferma con elenco delle conseguenze se c'è esposizione/ordine. Non equivale a chiusura.
- Chiudi posizione separato: conferma quantità e contesto; prima REQUESTED, poi fill di chiusura predeterminato con esito distinto. Disabilitato/spiegato se nessuna posizione. Funziona anche con bot fermo come comando esplicito Owner.
- Passaggio a CALL_ONLY annulla eventuali ingressi pendenti, dichiarandolo prima della conferma; gli ordini protettivi sono preservati.
- Feed STALE/DISCONNECTED: mostra ultimo dato e orario, non trasforma attesa in mercato aggiornato; blocca nuovi ingressi. Tentativo di chiusura senza feed può produrre richiesta simulata in attesa di conferma, mai una chiusura certa inventata; checkpoint di ripristino completa o annulla coerentemente l'azione.
- Comandi duplicati o click rapidi non duplicano eseguiti. Reimpostare scenario azzera il ramo precedente, etichettato reset della simulazione.
Le transizioni sono convenzioni di questa UI simulata: non approvano un protocollo exchange reale.

## 6. Verifiche e consegna

Percorso di prova Owner da documentare: avvio → posizione LONG e dettagli → stop totale senza chiusura → ripresa con conferma → gestione manuale/ritorno automatico → parziale → chiusura → reset → attesa/ordine pendente/rifiutato/SHORT → dati vecchi e ripristino. Ogni azione è simulata. Il selettore scenario è esplicitamente distinto dai comandi ordinari.

Criteri: fedeltà al riferimento Figma identificato; avvio locale documentato; scenari riproducibili; riconciliazione contabile; distinzioni call/ordine/posizione; dati mancanti/stale chiari; componenti sostituibili tramite provider senza riscrittura.

Controlli mirati su contabilità LONG/SHORT, pendente senza posizione, stop distinto da chiusura, conferme/annullamenti, doppio comando e disconnessione. Build/typecheck del solo frontend; prova visiva dei principali checkpoint con confronto al Figma. Nessuna suite Python/CI ereditata, nessun polling CI.

Consegna di Claude: commit, file, avvio su Windows con prerequisiti verificati, controlli eseguiti, immagini dei principali stati, differenze residue dal design e funzionalità realmente interattive/simulate/non costruite. Director effettua review e distingue verifiche proprie da quelle dichiarate; Gian prova il percorso concreto, senza chiamarlo validazione di trading.

Pubblicazione esecutore AUTORIZZATA: commit e push dei soli file pertinenti su main nel checkout della nuova repository assegnato dall'Owner, dopo le verifiche mirate. Nessun force push. Non sovrascrivere modifiche locali o concorrenti; in quel caso isolare la divergenza. Aggiornare README con avvio Windows, STATE con stato effettivo e lo spazio consegna del task passando a DELIVERED, mai ACCEPTED. Nessun pull dell'esecutore: Gian sincronizza il checkout al commit READY indicato.

## 7. Esclusioni ed escalation

Nessun backend, database, autenticazione, exchange API/chiavi, rete prezzi, acquisizione, backtest, motore osservazioni, strategia, ordini esterni o apertura protetta. Nessun riuso vecchia app. DESIGN-001 archiviato NON APPROVATO.

Director risolve dettagli ordinari, fedeltà UI e correzioni. Astra solo a fine macrofase o conflitto sostanziale; non richiedere approvazione per ogni commit. Owner solo per materiale Figma e preferenze indispensabili.

## Spazio dell'esecutore

Consegna Claude Code, 16 ottobre 2026. Base 96846887, checkout pulito su `main`. Il commit della consegna è quello che aggiorna questo file (vedi `git log`).

**Gate Figma — superato.** Il plugin Figma MCP era installato ma non autorizzato. L'Owner ha completato l'OAuth nel browser durante la sessione: nessuna installazione nuova, Figma non modificato. Account con piano Starter e seat View. Metodo: `create_session`, poi `get_design_context` con screenshot su 2:9260 (risposta sparsa, solo metadata) e quindi sui sottoalberi 2:9261, 2:9302, 2:9347, 2:9549, 2:9595, 2:9641, 3:154, 3:210, 3:267, 3:342, 3:416, 3:473, 2:9828, 2:9953, 2:10283, 3:2. Tutti hanno restituito codice di riferimento completo e screenshot. Per 2:9953 l'output è stato troncato dopo l'ultima scheda; il testo delle otto schede è comunque completo. Le 52 icone statiche sono state scaricate dagli asset Figma in `dashboard/src/assets/icons` e sono servite in locale.

**Cosa è stato costruito** (`dashboard/`, React 18 + TypeScript + Vite 6, CSS proprio, nessuna libreria grafica):
- Contratto versionato in `src/contract/` (Context, Chart, Observation, Expectation, Call, Plan, Order, Fill, Position, Account/results, History). Usa `Maybe` con motivo e ultimi valori noti con orario.
- Provider separato in `src/sim/`:
  - eventi predeterminati e comandi con idempotenza per `requestId`;
  - contabilità in un'unica funzione (`accounting.ts`);
  - percorso LONG con i checkpoint 1, 2, 3, 3b (rifiuto), 4, 5, 5b (manuale), 5c (bot fermo), 6 (parziale), 7 (chiusa);
  - variante SHORT speculare con i checkpoint S1 (proposta in Solo call) e S2 (posizione);
  - alterazioni del feed (non aggiornato o disconnesso) su qualunque checkpoint;
  - reset al checkpoint iniziale «5».
- UI fedele ai nodi letti, con le correzioni di FIGMA-REFERENCE: etichette corrette, banner fisso, feed simulato, contratto lineare d'esempio, nessuna operazione del mockup senza eseguiti.
  - Grafico SVG disegnato dai dati: 45m/1D, zoom, overlay. Le scale coincidono nei periodi sovrapposti.
  - Dettagli dei segnali in un dialogo; sei conferme (stop, start, manuale, ripresa con spunta obbligatoria, parziale, chiusura).
  - Storico e Conto portano alle sezioni della dashboard; Ricerca/Backtest e Impostazioni mostrano «Non disponibile in questa versione».

**Riconciliazione:** il percorso Owner, partendo da «5», arriva a saldo/equity 10.005,793, realizzato lordo +7, costi 1,207 e netto +5,793. SHORT: +10 non realizzato, saldo 9.999,40, equity 10.009,40.

**Controlli eseguiti dall'esecutore:**
- 28 test Vitest: contabilità LONG/SHORT; ordine pendente e ordine rifiutato senza posizione né costi; stop distinto dalla chiusura; conferme e annullamenti; doppio comando; disconnessione e ripristino; coincidenza 45m/1D; dialoghi via Testing Library.
- `npm ci`, typecheck e build superati.
- Percorso Owner ripetuto nel browser headless (Chrome locale) senza errori in console.
- Screenshot in `docs/ui/app-screenshots/`: 1680 e 1366 px, attesa, pendente, rifiutato, manuale, bot fermo, chiusa, SHORT, dati vecchi, disconnessione, tutti i dialoghi, 1D.

Nessuna suite Python o CI eseguita.

**Scelte tecniche rilevanti (convenzioni della UI simulata):**
- Un'uscita richiesta viene eseguita alla chiusura della candela 45m successiva dello scenario. Commissione di fixture: 0,1% del nozionale. Parziale fissa a 0,004 BTC.
- I rami creati dai comandi dell'Owner non ripetono le azioni automatiche del bot già scritte nello scenario.
- Le osservazioni sono gruppi datati (12:30, 13:15, 16:15) e non vengono ricalcolate a ogni tick.
- Le «medie» sono curve illustrative ricavate da punti di ancoraggio, non calcolate dai prezzi.
- Con feed non aggiornato una chiusura resta REQUESTED e il ripristino la completa; la richiesta può essere ritirata.

**Differenze residue dal design:**
- Mancano alcune varianti d'icona che non esistono nel Figma, quindi gli stati corrispondenti sono senza icona: «Solo call» attivo, «Call + esecuzione» inattivo, badge disconnesso e bot fermo.
- Pannello di simulazione aggiunto nella sidebar.
- «Timeline e notifiche» al posto di «Timeline & Telegram».
- Metriche del conto rinominate per il modello lineare.
- Il pulsante 45m non ha il simbolo «⌄»: non esiste un menu.

**Limiti:** nessuna persistenza; nessun dato dopo le 17:45 CEST dello scenario (le uscite successive usano l'ultimo prezzo un minuto dopo). La prova Owner e la review del Director non sono ancora avvenute.

## Review del Director

Progetto Figma letto dal Director il 16 ottobre con metadata, screenshot e contesti dei sottoalberi. Riferimento visivo e correzioni documentati. Nessun codice implementato o test applicativo eseguito dal Director; nessuna fedeltà dell'app ancora dimostrata. Accesso diretto dell'esecutore ancora da attestare nella fase A.
