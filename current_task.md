# Incarico corrente — UI-001

**Stato: DRAFT — specifica in preparazione; link Figma ricevuto; contenuto e accesso effettivo di Claude ancora da verificare.**

Macro-obiettivo autorizzato: dashboard fedele al Figma approvato, con stati simulati coerenti e fornitore dati separato. Disposizione Astra trasmessa dall'Owner il 16 ottobre 2026.
Responsabile: Director. Esecutore futuro: Claude Code.
Base precedente: 671d8d5176c19af13ec7b1cfe755867577724aa5; usare la successiva registrazione documentale contenente questo task.
La macrofase è autorizzata; il DRAFT indica contenuto Figma e accessi ancora da verificare, non una richiesta di nuova approvazione ad Astra. È consentita una verifica di sola lettura a Claude sul link indicato: identificare strumenti disponibili, leggere il nodo e riferire pagine/frame, asset e limite concreto se bloccato. Non installare integrazioni, modificare il design o iniziare codice in questa verifica.

## 1. Materiale necessario e verifica accesso

- Link Figma fornito dall'Owner il 16 ottobre 2026: https://www.figma.com/design/ys2HFfjS2OdaLLTsfhPp9A/Untitled?node-id=0-1
- File key: ys2HFfjS2OdaLLTsfhPp9A. Nodo richiesto: 0:1. Il link identifica un file design; non prova quali frame contenga o che il nodo sia la dashboard approvata.
- Verifica Director: il lettore web non ha accesso al contenuto. Integrazione Figma individuata ma non installata/collegata al momento del controllo; proposta all'Owner. Nessun contenuto Figma letto e nessuna fedeltà verificata.
- Pagina/frame/versione approvata: da identificare nel progetto; chiedere ulteriori preferenze solo se ci sono alternative sostanziali.
- Accesso effettivo di Claude: NON VERIFICATO. Una connessione disponibile al Director non prova quella dell'esecutore.
- Il Director non ha visionato lo screenshot citato da Astra in questa chat. Non inventare layout, componenti, font, asset o interazioni dal solo riferimento allo screenshot.
- Prima di implementare verificare che Claude possa leggere layout, componenti, asset e stati tramite strumenti effettivamente disponibili nel suo ambiente; se il link è soltanto un sito pubblicato e non il file sorgente Figma, dichiarare la differenza.
- Se accesso diretto impossibile, raccogliere esportazione del progetto/codice disponibile e riferimenti dei frame approvati. Non dichiarare equivalenza o fedeltà al Figma completo sulla base di una sola immagine.
- Design approvato vincolante: niente restyling autonomo. Eventuali incompatibilità funzionali si isolano al Director prima di implementare quel punto.

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
| Call | id, direzione LONG/SHORT, stato PROPOSED/AVAILABLE/EXPIRED/WITHDRAWN/COMPLETED, condizioni e validità; non rappresenta ordine né posizione |
| Plan | callId, versione, piano originario immutabile e corrente, ingresso/condizioni, target anche multipli se visibili, stop/invalidazione, scadenza, ragione; cambi con prima/dopo/orario; null quando non esiste un piano |
| Order | id, callId opzionale, scopo ENTRY/PROTECTION/EXIT, side BUY/SELL, quantità richiesta/eseguita, tipo illustrativo, stato REQUESTED/ACCEPTED/PARTIALLY_FILLED/FILLED/CANCELLED/REJECTED, prezzo/trigger se pertinente; accettato non significa eseguito |
| Fill | id, orderId, timestamp, side, quantità/prezzo e commissione con valuta; unica fonte degli eseguiti simulati |
| Position | id, LONG/SHORT, quantità residua, prezzo medio di ingresso, riferimento di valutazione e tempo, protezioni effettivamente simulate, titolarità gestione BOT/MANUAL; null quando nessun eseguito ha aperto esposizione |
| Account/results | valuta, saldo iniziale, saldo contabile simulato, equity, P&L realizzato lordo, costi effettivamente addebitati, P&L realizzato netto, P&L non realizzato lordo e costi di uscita non inclusi; margine/disponibile null se non simulati |
| History | id evento, tipo, timestamp, collegamenti a call/ordine/posizione/piano, testo, cambi prima/dopo; eventi passati non presentati come call corrente |

Si può affinare la forma dei tipi per aderire al Figma senza fondere i significati. Parametri di medie, percentuali, capitale, leva e Spot/futures nelle fixture sono esempi esplicitamente etichettati, non decisioni operative. Nessun calcolo o regola di DESIGN-001 si attiva per popolare questi modelli.

Provider separato: caricamento scenario, snapshot e comandi simulati. I componenti consumano snapshot e inviano intenzioni; il provider gestisce le sole transizioni predeterminate. Niente deduzione di direzione, segnali o gestione dai prezzi. Formattazione e calcoli grafici geometrici consentiti; contabilità in una funzione del dominio simulato testabile, non duplicata nei widget.

## 4. Scenari piccoli e coerenti

Un percorso LONG e una variante SHORT speculare, con checkpoint riutilizzati; non dieci simulatori indipendenti. Poche decine di candele per scala, già preparate per visualizzazione; niente mesi di minuti, warmup analitico o motore di mercato. Entrambe le scale devono riflettere lo stesso percorso nei periodi sovrapposti. Un breve contesto giornaliero sintetico può precedere il segmento intraday senza fingere copertura intraday assente.

Checkpoint: attesa con aspettativa ma nessuna call; opportunità senza posizione; ordine accettato ancora non eseguito; eseguito e posizione LONG; protezione aggiornata; uscita parziale; chiusura; variante posizione SHORT. Dati non aggiornati e disconnessione sono alterazioni controllate degli stessi checkpoint, preservando ultimo valore noto e relativo orario.

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

## 6. Verifiche e consegna future

Criteri: fedeltà al riferimento Figma identificato; avvio locale documentato; scenari riproducibili; riconciliazione contabile; distinzioni call/ordine/posizione; dati mancanti/stale chiari; componenti sostituibili tramite provider senza riscrittura.

Controlli mirati su contabilità LONG/SHORT, pendente senza posizione, stop distinto da chiusura, conferme/annullamenti, doppio comando e disconnessione. Build/typecheck del solo frontend; prova visiva dei principali checkpoint con confronto al Figma. Nessuna suite Python/CI ereditata, nessun polling CI.

Consegna di Claude: commit, file, avvio su Windows con prerequisiti verificati, controlli eseguiti, immagini dei principali stati, differenze residue dal design e funzionalità realmente interattive/simulate/non costruite. Director effettua review e distingue verifiche proprie da quelle dichiarate; Gian prova il percorso concreto, senza chiamarlo validazione di trading.

Pubblicazione esecutore: da attivare esplicitamente passando questo task a READY. Nel DRAFT non implementare o pubblicare codice. Nessun pull dell'esecutore: Gian sincronizza il checkout al commit READY indicato.

## 7. Esclusioni ed escalation

Nessun backend, database, autenticazione, exchange API/chiavi, rete prezzi, acquisizione, backtest, motore osservazioni, strategia, ordini esterni o apertura protetta. Nessun riuso vecchia app. DESIGN-001 archiviato NON APPROVATO.

Director risolve dettagli ordinari, fedeltà UI e correzioni. Astra solo a fine macrofase o conflitto sostanziale; non richiedere approvazione per ogni commit. Owner solo per materiale Figma e preferenze indispensabili.

## Spazio dell'esecutore

Implementazione non attiva: accesso Figma da verificare, task DRAFT. La sola verifica di lettura descritta sopra è consentita; non dichiarare accesso dal semplice riconoscimento dell'URL.

## Review del Director

Disposizione recepita e specifica iniziale registrata. Nessun codice implementato o test applicativo eseguito; nessuna fedeltà visiva dichiarata prima di vedere il progetto.
