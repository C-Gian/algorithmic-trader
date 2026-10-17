# Incarico corrente — CAND-001, confronto aggiuntivo 2025 e consegna della macrofase

**Stato: READY.** Director, 17 ottobre 2026.
Esecutore: Claude Code. Base tecnica accettata: **3ae7b7529f26f7aef94c9de207ce41df342590d1**, più il commit di questo incarico.
Checkout sincronizzato da Gian; nessun pull/fetch dell'esecutore, neppure dry-run.

## 1. Chiusura R1 e checkpoint del Director

**CAND-001/R1 ACCEPTED TECNICAMENTE** su 3ae7b75. Incarico e consegna R1 conservati nella storia di questo file a quel commit. Review Director:
- lettura delle modifiche a qualità funding, gate prima del ledger, operazione irrisolta, metriche/copertura, contratto/validatore, risultati e prezzo nella vista episodio;
- nella copia isolata: **36 test Python CAND, 14 test UI Backtest/BacktestR1 e typecheck/build riusciti**;
- i tre difetti riprodotti nella review precedente sono risolti nei controlli pertinenti: funding non certificato blocca il run economico, percorso irrisolto conserva fatti noti senza netto/uscita inventati e si apre nell'app, prezzo precedente separato dal corrente;
- config canonica verificata invariata: aed2c4ef627617d73972778097bbab5fb702ab5064ce9e6eb68ded2170ce4edf;
- il confronto reale DEV e1.0.0/e1.0.1, eseguito da Claude, dichiara invariati 814 episodi, 87 richieste, 78 trade e tutti i numeri comuni. Il Director ha verificato codice/test/report, **non ricalcolato autonomamente i75archivi o i78trade reali**, né effettuato browser su quel bundle;
- compatibilità dichiarata: schema /2, app non apre i vecchi bundle /1. Vecchio run conservato come evidenza; nessuna migrazione richiesta ora;
- difetto a390px dichiarato, fuori dal perimetro desktop di questa fase; nessun restyling richiesto;
- esecuzione delle suite complete da parte di Claude oltre incarico annotata come deviazione di processo. Non ripeterla: controlli mirati soltanto.

Nessuna prova positiva d'uso Gian registrata per CAND-001; la chiusura è tecnica. OBS-001 resta tecnicamente chiuso con il suo limite di comprensione.

**Decisione metodologica definitiva prima del 2025:** mantenere **candidato1.0.0**, nessuna revisione metodologica in questa macrofase. Specifica vincolante **docs/research/CAND-001-v1.md**, convenzioni OBS-001/v1 intatte. Il risultato DEV negativo non identifica una modifica unica abbastanza motivata: nessun cambio di soglie, famiglie, filtri, target, stop, ritardi, costi o gruppi.

La base accettata del motore è1.0.1; si ammette ora una patch tecnica per completare il supporto della finestra2025 e il prefisso previsto, non una nuova variante del candidato. Registrare patch/versione e commit prima del primo esito economico2025. Il parametro requiresDirectorCheckpoint della config può restare invariato: **il checkpoint è soddisfatto da questa disposizione**, non da una modifica del candidato/config. Rimuovere il blocco CLI incondizionato nella sola fase ora autorizzata. Nessun sistema di autorizzazioni aggiuntivo necessario.

## 2. Obiettivo completo, già autorizzato da Astra

Completare **ADDITIONAL_2025** con la v1 congelata: acquisizione dei soli input mancanti, controlli, elaborazione riproducibile, confronto separato con DEV2023–2024 e consultazione nella stessa app. Consegnare report finale e raccomandazione anche negativa.

Non fermarsi dopo predisposizione sintetica, download o solo JSON per chiedere permessi ordinari. Questo task autorizza l'intero seguito operativo. Solo blocchi precisi o conflitti sostanziali vanno riportati; nessuna sostituzione di fonte, strumento o periodo.

**2025 è confronto aggiuntivo già esposto, NON validazione indipendente/holdout.** Nessuna iterazione metodologica sui suoi esiti. Correggere solo bug documentati con impatto e riesecuzione; non introdurre una v2 o selezionare mesi favorevoli. L'unica revisione facoltativa su DEV non è stata scelta e non si riapre dopo aver visto2025.

## 3. Dati, prefisso e finestre

Fonte invariata: archivio pubblico Binance Vision, BTCUSDT perpetual USDⓈ-M, klines negoziate1m; fundingRate storico e markPriceKlines1m solo per costi, secondo protocollo. Nessun account, chiave, stackOwner o altro strumento.

Confini UTC:
- **input osservativo totale [2022-10-01,2026-01-01)**;
- DEV già valutato [2023-01-01,2025-01-01), percorso continuo2023–2024 conservato;
- nuova finestra **ADDITIONAL_2025 [2025-01-01,2026-01-01)**;
- all'inizio2025: FLAT, nessun episodio/ordine ereditato, osservazioni inizializzate da **tutto il prefisso dal2022-10-01**, nessun reset degli indicatori a gennaio2025. Attendere nuove gambe disponibili nella finestra;
- ultima apertura1m2025: regola di fine segmento del protocollo, nessun dato2026 per chiudere operazioni o completare esiti.

Correggere phase_months/load_trade che oggi, in ADDITIONAL_2025, partono dal2025: distinguere **file da caricare per osservare**, **file da scaricare** e **finestra che genera decisioni/operazioni**. Non rifare DEV per calcolare il prefisso: riusare prezzi e calcolare osservazioni, ma non generare o usare i suoi trade come stato2025.

Riutilizzo effettivo:
-27archivi trade ottobre2022–dicembre2024 già CAND;
-7archivi trade giugno–dicembre2025 già verificati da OBS, localizzati dal manifest OBS in C:\Projects\algorithmic-trader-data\OBS-001. Riuso con SHA256/provenienza, senza modificarli; lettura diretta o copia locale verificata entrambe ammesse. Non riscaricarli solo perché si trovano in un'altra cartella;
- solo5archivi trade gennaio–maggio2025 mancanti e12funding+12mark2025 se davvero non presenti. Attesi **29ZIP nuovi**, non39trade nuovi;
- totale osservativo39mesi trade,1.710.720minuti teorici. Finestra2025:365giorni,525.600minuti,11.680origini45m teoriche. Qualità reale da verificare, non presumere;
- nessun bisogno di mark/funding per tutto il warmup precedente: la finestra parte senza posizione. Un mark precedente al confine iniziale mancante non diventa prezzo negoziato o zero; applicare le dipendenze effettive.

Manifest separati con file riusati/nuovi, checksum fornitore, hash locale, unità temporali, identità fonte e strumento, eventuali anomalie. Non inventare prezzi, tassi o calendari. Se il funding non è certificabile, dichiarare il blocco; non disabilitare R1-A per proseguire. Se un costo pertinente manca o un percorso diventa irrisolto, mantenere le distinzioni R1. File raw/bundle pesanti sempre fuoriGit. Nessun tail2026.

## 4. Implementazione e controlli prima degli esiti

Riutilizzare motore/osservatore/provider e dashboard esistenti. Nessun backend, database, piattaforma parallela o nuovo restyling.
Prima del primo backtest economico2025:
1. predisporre caricamento con prefisso intero, riuso OBS, selezione fase CLI e output separato;
2. pochi controlli sintetici discriminanti: osservazioni al confine2025 coincidono con un calcolo sul medesimo prefisso continuo; finestra nuova parte FLAT senza episodio/ordine precedente; le decisioni prima della fine non usano dati successivi; nessun minuto2026 letto o richiesto;5+12+12file nuovi a cache prevista, non riscaricamento dei7OBS;
3. conservare test funding/irrisolti/prezzo pertinenti se i loro percorsi cambiano;
4. registrare commit/versione motore/hash candidato e pubblicare il supporto prima degli esiti. Nessuna modifica del JSON candidato per fare sparire il checkpoint.

Dopo questo commit: acquisire input, elaborare ADDITIONAL_2025 e ripetere offline per verificare output identico. Conservare run DEV e precedenti; nessuna sovrascrittura. Hash input/output e comandi reali Windows nel manifest/README. Il run non include data di esecuzione o commit variabili nel contenuto deterministico.

Non rilanciare suite complete per abitudine. I test mirati del percorso modificato, typecheck/build e breve prova browser del bundle reale sono sufficienti. Ulteriori controlli solo per difetti o rischi identificati. Nessun pollingCI, processoOwner terminato o nuovo servizio permanente.

## 5. Report finale e diagnosi

Aggiornare **docs/research/CAND-001-results.md**, conservando DEV e diagnosi negativa. Aggiungere2025 separato:
- copertura reale, costi verificabili/assunzioni invariati, conti e tempi di esecuzione;
-2023,2024,DEV e2025 distinti, tutti i mesi anche senza operazioni; nessuna selezione dei mesi migliori;
- episodi/call/rifiuti/trade, LONG/SHORT e motivi d'astensione/uscita;
- lordo ai riferimenti, slippage, fee, funding, netto/stress modellati per N0=1000USDT, non rendimento personale/composto;
- distribuzioni per trade, rischio iniziale, durata/esposizione, drawdown alla risoluzione1m, sequenze di perdite e concentrazione secondo protocollo;
- ambiguità, dati mancanti, percorsi non valutati e differenza fra completo e parziale; costi mancanti non sono zero;
- confronto descrittivo con DEV, casi contrari, limiti e raccomandazione motivata sul seguito. Non promuovere automaticamente v1 se2025 fosse positivo, non scartare l'intera famiglia se negativo. Nessun test di significatività o conclusione causale aggiunto.

Conservare la distinzione diagnosi: bug, difformità, scelta coerente poco utile, costo/assunzione sensibile, informazione insufficiente. Nessuna nuova suddivisione o ricerca di parametri/combinazioni per migliorare2025. Le categorie di esempi già fissate si applicano anche a2025, con primi cronologici per verso e categorie vuote dichiarate.

La frase “zero differenze” di uno script separato dell'esecutore deve precisare autore e perimetro; non equivale a verifica indipendente Director. Documentare capacità implementata, risultati ottenuti, limiti ancora aperti.

## 6. Risultato nell'app e prova Gian

Stesso ambiente «Backtest di sviluppo», distinguendo chiaramente2025 “confronto aggiuntivo già esposto” e DEV. Sono ammessi bundle separati e selettore file esistente: **nessun nuovo esploratore o import multiplo obbligatorio**. Tabelle report affiancate bastano per il confronto dei periodi; se si mostra un totale, solo somma normalizzata esplicita e mai saldo del conto.

Nel bundle2025 devono aprirsi risultati, mesi, registro e gli esempi previsti, con informazioni note allora separate dal seguito modellato. Anche eventuale assenza di categorie deve essere comprensibile. Banner senza collegamentoexchange; nessuna call/posizione/saldo delle fixture mescolata allo storico. R1-A/B/C preservate. Vecchi bundle /1 restano conservati ma non apribili, come dichiarato; nessuna migrazione in questo task.

Istruzioni Owner brevi con percorso esatto del nuovo file:
1. aprire «Backtest di sviluppo» e il bundle2025;
2. «Prima operazione» oppure categoria assente spiegata; leggere movimento, reazione e condizioni d'ingresso;
3. «Mostra seguito modellato»: ingresso, protezione, uscita, costi;
4. «Primo caso negativo» e «Prima astensione», se presenti.

Gian deve poter seguire decisione/esito senza scegliere date a caso né verificare formule/pivot. La prova d'uso sarà raccolta dal Director dopo la review: **non registrarla come fatta o positiva in anticipo**, né presentarla come validazione del trading. Non lasciare il lavoro incompleto perché la provaOwner non è ancora avvenuta.

## 7. Consegna e chiusura

Completare tutti i passaggi sopra e passare DELIVERED, non ACCEPTED:
- commit pre-esiti del supporto2025, versione motore, confighash invariato;
- file nuovi/riusati e copertura reale, manifest/run/hash e comando per rifare offline;
- report DEV/confronto2025 e raccomandazione, anche negativa;
- app avviabile, bundle e percorso di prova concreto;
- test mirati, build, prova browser e limiti dichiarati;
- eventuali bug corretti, impatto e riesecuzione documentati, nessuna iterazione metodologica;
- aggiornare STATE, EXPOSURES con esposizione effettiva2025 e consegna di questo task; aggiornare contesto funzionale solo per capacità davvero mutate.

Commit/push pertinenti su main autorizzati, niente force push, pull/fetch, reset/stash o sovrascrittura di lavoro concorrente. Non pubblicare raw/bundle.
La macrofase si chiude dopo review Director, prova concreta Gian e comunicazione adAstra con evidenza/limiti/raccomandazione. Non occorre un risultato favorevole.

Esclusioni ferme:2026protetto, studi vecchiINACTIVE, conto/chiavi/ordini esterni, stackOwner, leva/reinvestimento, nuova famiglia/segnali o ottimizzazione, restyling o suite generali.

## Spazio dell'esecutore

Da compilare: avanzamento, acquisizione/riuso, run, risultati, prove, limiti e consegna.
