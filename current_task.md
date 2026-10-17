# Incarico corrente — CAND-001, confronto aggiuntivo 2025 e consegna della macrofase

**Stato: ACCEPTED TECNICAMENTE** — Director, 17 ottobre 2026, review su4ff5046. Prova concreta Owner svolta con rilievi di comprensione/navigazione; chiusura e seguito da discutere conAstra. Nessun nuovo incarico di codice.
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

**Stato: DELIVERED** (Claude Code, 17 ottobre 2026). Non ACCEPTED: in attesa di review del Director. La prova d'uso di Gian non è stata svolta né registrata.

### Commit
- `078d9ed` — **supporto pre-esiti** (motore 1.0.2), pubblicato prima di qualunque acquisizione o esito 2025. Candidato 1.0.0 e config `aed2c4ef627617d73972778097bbab5fb702ab5064ce9e6eb68ded2170ce4edf` invariati; nessuna modifica del JSON.
  - `data.py`: piano degli input in tre insiemi: osservare 39 mesi dal 2022-10; riusare 7 mesi OBS, elencati in `reuseObsTradeMonths` della config; acquisire 5 trade + 12 funding + 12 mark.
  - Acquisizione senza rete per i file già verificati, con voci di manifest invariate; manifest separato `reuse-trade-obs.json`.
  - `load_trade` costruisce lo store dal 2022-10-01 in ogni fase.
  - `cli.py`: tolto il blocco incondizionato di ADDITIONAL_2025; statistiche del prefisso per ogni fase.
  - App: bundle 2025 etichettato «confronto aggiuntivo 2025 · già esposto, non validazione indipendente»; un anno uguale alla finestra non è duplicato.
- Commit docs di questa consegna: report, README, immagini, EXPOSURES, contesto funzionale, STATE, task.
- Cambiamento di comportamento dichiarato: anche per il DEV, `acquire` non richiede più il .CHECKSUM al fornitore per file locali già verificati contro il checksum registrato.

### Acquisizione e riuso (17 ottobre 2026, 08:35–08:36 UTC)
- Comando: `python3.12 -m cand001 acquire --phase additional2025`.
- Esito: trade 27 VERIFIED_LOCAL + 5 DOWNLOADED; funding 12 DOWNLOADED; mark 12 DOWNLOADED; 7 OBS riusati. **29 archivi nuovi, nessun trade riscaricato.**
- SHA256 dei 7 ZIP OBS identici prima e dopo; voci DEV dei manifest di acquisizione identiche prima e dopo.
- Controllo: 1.710.720 minuti validi su 1.710.720, nessuna anomalia; prefisso 1.185.120.
- Funding 2025: 1.095 eventi, 8 h, jitter ≤ 16 ms, certificato.
- Mark: 1.094 su 1.095. Manca il solo punto 2025-01-01 00:00, irrilevante perché la finestra parte FLAT.
- Manifest in `C:\Projects\algorithmic-trader-data\CAND-001\manifests\`: `acquisition-*.json`, `reuse-trade-obs.json`, `input-ADDITIONAL_2025.json`.

### Run
- `python3.12 -m cand001 run --phase additional2025` dal commit pulito `078d9ed`.
- Run `CAND-001-v1.0.0-e1.0.2-ADDITIONAL_2025-9324c5d179-aed2c4ef62`.
  - Input hash `9324c5d1795fc0a43eccf1c929f50773b1092b6c653f4627008249e0599731bb`.
  - Bundle 4,6 MB, SHA256 `7c6ff10e2051c2576c9fd6ee790a7952d22ee22937a3e69e8dde482abce3a721`.
  - Tempi: 22,9 s (controllo 18,7, backtest 2,8); picco 709 MB.
- Rieseguito offline subito dopo: bundle identico, nessuna sovrascrittura. Run DEV e1.0.0/e1.0.1 intatti.

### Risultati 2025 (dichiarati dall'esecutore)
- Copertura completa, nessuna operazione irrisolta, nessun costo mancante.
- 461 episodi, 31 call, 2 rifiuti al prezzo, 29 operazioni (13 LONG, 16 SHORT).
- Uscite: 22 stop, 3 target, 4 struttura.
- Netto −109,08 USDT su N0 = 1.000: riferimenti −62,54, slippage −17,41, fee −29,01, funding −0,12. Stress −178,71; drawdown −113,99.
- Mesi: 10 negativi, 1 positivo, 1 senza operazioni.
- Raccomandazione nel report:
  - non promuovere v1;
  - conservare l'evidenza negativa, senza varianti scelte sul 2025;
  - non scartare l'intera famiglia;
  - eventuale seguito solo con nuovo disegno preregistrato e dati non esposti con mandato specifico.

### Verifiche svolte (mirate)
- Python: `test_cand001_*.py` 45/45. I 9 nuovi test (`test_cand001_additional2025.py`) sul codice precedente danno 5 errori: piano, acquisizione e caricamento non esistevano. I 4 test sul confine e sulla partenza FLAT documentano proprietà già vere dell'osservatore e del motore.
- DEV ricalcolato in memoria con 1.0.2: bundle uguale a e1.0.1 salvo versione del motore e ID del run, input hash uguale. Nessun run scritto.
- Dati reali: osservazioni dello store 2025 e dello store DEV identiche sul tratto comune (26.336 barre 45m, 823 1D, 20.695 eventi). Alla prima barra 2025, A, SMA20 e SMA50 sono presenti.
- Riscontro separato **scritto da me** (stesso script del DEV, esteso alla cartella OBS): 31 call e 29 operazioni ricalcolate dai minuti grezzi, 0 differenze.
  - Perimetro: non cerca call mancanti fra le astensioni, non ricalcola le osservazioni e non rilegge i file funding.
  - Non è una verifica indipendente del Director.
- UI: `npx vitest run src/ui/backtest` 15/15, compreso il nuovo `Backtest2025.test.tsx`; `npx tsc -b` e `npm run build` riusciti. Nessuna suite generale.
- Browser (Chrome headless su mia `vite preview` 127.0.0.1:4173, poi chiusa; vite dell'Owner PID 10872 non toccato).
  - Bundle 2025 aperto in 0,11 s; titolo «confronto aggiuntivo 2025» con badge «2025 GIÀ ESPOSTO · NON VALIDAZIONE INDIPENDENTE»; una sola colonna 2025.
  - 12 mesi, novembre «nessuna operazione»; cinque pulsanti presenti, ciascuno apre l'episodio con seguito su richiesta. Registro 29 righe, 2 richieste non eseguite.
  - R1-C al momento d'ingresso (t+60s) e in 1D: prezzo «non corrente».
  - Il bundle DEV e1.0.1 si apre ancora come «backtest di sviluppo».
  - 0 errori di console, 0 richieste esterne.

### Per la prova di Gian
File: `C:\Projects\algorithmic-trader-data\CAND-001\runs\CAND-001-v1.0.0-e1.0.2-ADDITIONAL_2025-9324c5d179-aed2c4ef62\cand001-bundle.json`. Passi brevi nel README, sezione CAND-001:
1. «Backtest di sviluppo», poi «Apri backtest»;
2. «Prima operazione»;
3. «Mostra seguito modellato»;
4. «Primo caso negativo» e «Prima astensione».

### Limiti
- Il 2025 è già esposto, non è una validazione indipendente; 29 operazioni sono un campione piccolo.
- Esecuzione modellata, costi assunti, funding con proxy mark 1m.
- Le verifiche sui dati reali sono dell'esecutore.
- Difetto a 390 px invariato, fuori perimetro.
- I bundle /1 restano non apribili.
- Nessun dato 2026 letto o richiesto.

## Review finale del Director — 17 ottobre 2026

**ACCEPTED TECNICAMENTE su4ff5046a5f94dffc1a4bad7b339ffeb017b612ba.** Candidato1.0.0, motore1.0.2, schema cand001.bundle/2. Nessuna revisione metodologica scelta; nessun nuovo lavoro di codice assegnato. Macrofase in attesa della prova concreta di Gian e della comunicazione conclusiva adAstra, non dichiarata chiusa per implicazione.

### Verifiche indipendenti e loro limite
- Confronto Git: il supporto2025 è nel commit078d9ed03026e5126f20482037c21ffcc79cff43; dopo di esso il diff fino alla consegna è solo documentazione/immagini. Config, motore decisionale, ledger/gestione e metriche non modificati in questa fase.
- Lettura del piano input/riuso, caricamento dell'intero prefisso, selezione CLI e viste2025. Il riuso senza rete conserva il checksum del fornitore già registrato e ricontrolla l'hash locale: è una scelta coerente con riproducibilità e download dei soli mancanti, **non** una nuova verifica dell'eventuale revisione dell'archivio remoto.
- Nella copia isolata Director: **45test Python CAND,15test UI backtest e typecheck/build passati**. Comprendono prefisso, FLAT al confine, piano39mesi/29nuoviZIP, cache/riusoOBS, esclusione2026, regressioniR1 e apertura2025/DEV.
- Esaminate le due immagini2025 dell'esecutore a1366px. Non equivale a una prova browser autonoma.
- Riscontro reale indipendente circoscritto: scaricati in area di review soltanto i tre archivi pubblici di gennaio2025 (trade1m,mark1m,fundingRate), ciascuno confrontato col .CHECKSUM del fornitore. Sulla prima operazione LONG5gennaio, **dato il piano riportato** S0=97969/T=98760,9 e il momento d'ingresso, ricalcolati da CSV open d'ingresso, primo contatto stop, prezzi con frizioni, fee e funding. Coincidono: ingresso03:01UTC ref98200, fill98229,46; stop nel minuto08:03, chiusura contabile08:04, fill97939,6093; fee0,9985246244, funding−0,0999962057, netto−4,0492720609USDT (−4,05). Nessun2026 letto.
- Non verificati autonomamente dal Director: l'intera popolazione di segnali/astensioni, tutti i107trade DEV+2025, tutti gli archivi o la riproduzione byte per byte dei bundle reali. Tali evidenze restano dell'esecutore, con il perimetro dichiarato del suo script (non cerca call mancanti).
- I test sui casi di funding non certificato/HALT rimangono sintetici; nessun errore riproducibile nuovo individuato nel perimetro della review.

### Decisione e raccomandazione
Non promuovere v1 all'uso operativo o a una nuova fase live/paper volta a provarne la redditività. Conservare versione, risultati negativi e consultazione storica. DEV riportato:78trade,−210,59USDT;2025:29trade,−109,08USDT, entrambi negativi già ai prezzi di riferimento e peggiori con le frizioni assunte. Sono somme per nozionale fisso, non rendimento di conto. Il2025 è già esposto, non validazione indipendente.

La capacità implementata (osservazioni causali, candidato completo, percorso storico e UI) è distinta dall'utilità economica non dimostrata. Non scartare l'intera famiglia sulla base di questa sola versione; non modificare soglie dopo aver visto2025.

Precisazione alla raccomandazione dell'esecutore: “nessun uso” significa nessuna promozione operativa, non cancellazione di strumenti/evidenza o divieto di consultazione. Un futuro disegno **non può cancellare l'esposizione2025** dicendo di ripartire da zero. Può dichiarare ciò che ha imparato, ma il metodo e il protocollo del seguito spettano adAstra; nessun obbligo aggiunto di inventare tutto da zero o aprire subito dati nuovi/protetti. Nessuna nuova acquisizione, ottimizzazione o versione autorizzata da questa review.

### Prova concreta ancora da raccogliere
Gian apre il bundle2025 già consegnato, sceglie «Prima operazione», legge movimento/reazione/condizioni, poi «Mostra seguito modellato» e prova «Prima astensione». «Primo caso negativo» coincide qui con la prima operazione: non è un errore, è la regola cronologica.
Non deve verificare formule/pivot o decine di trade: deve solo dire se riesce a seguire perché il programma ha chiesto l'ingresso e come è finita. Riscontro non ancora ricevuto, nessuna accettazione d'uso inventata. Nessuna nuova macrofase UI automatica se resta una difficoltà di comprensione.

Dopo tale riscontro il Director comunica adAstra chiusura/evidenza/limiti/raccomandazione e chiede la direzione successiva.2026 resta protetto e i vecchi studiINACTIVE. Nessun ulteriore incaricoClaude pendente.


## Riscontro Owner e richiesta adAstra — 17 ottobre 2026, ore11:31 Europe/Rome

**Prova svolta con rilievi, non accettazione d'uso senza riserve.** Gian apprezza la base: il programma riconosce situazioni, decide se tentare un ingresso o astenersi e registra ciò che accade. Non giudica positivamente la redditività di v1. I risultati negativi, il congelamento e la review tecnica restano invariati.

Feedback integrale nei requisiti pertinenti di PRODUCT-CONTEXT.md v1.6 (§§13,24–26):
1. Non risultano chiari scopo dei pulsanti “prima…” e rapporto fra esempi e registro completo. La prima operazione è una vera entrata **della simulazione**, non un ordine reale né una fixture; gli esempi sono scorciatoie cronologiche, tutte le29operazioni2025 sono nel registro.
2. Si comprende circa movimento→attesa, ma non la differenza fra “ha chiesto un ingresso”, “ingresso modellato” e “uscita modellata”. Semplificare distinguendo proposta/tentativo, ordine simulato eseguito o rifiutato, posizione e motivo esatto di chiusura. Non rappresentare la richiesta condizionata di v1 come un limitorder permanente: è un tentativo unico al minuto successivo, con controllo del prezzo, che può non generare ingresso.
3. “Netto modellato”, “−40bp diN0”, “PnL ai prezzi di riferimento”, “slippage”, “funding storico”, “costi di stress”, “bp fee” sono incomprensibili senza traduzione. Importi/risultato in termini comuni e dettagli spiegati; icona “i” con popup hover accettata dall'Owner, consigliato anche focus/clic. Niente unità tecniche opache in primo piano.
4. Navigazione: passando da risultati a dettaglio l'Owner non trova come tornare; riseleziona “Backtest di sviluppo”. Richiede URL e Indietro/Avanti del browser oltre al ritorno interno evidente, come regola di tutta l'app. Nel codice attuale esiste “← Risultati”: assenza materiale non riprodotta, verificare visibilità/trovabilità; non negare il problema d'uso.
5. **Requisito nuovo esplicito:** Gian vuole avviare personalmente i backtest dallaUI e vedere avanzamento dettagliato, non soltanto percentuale. Non vuole aspettare al terminale o dipendere daClaude per lanciare il run. Oggi laUI apre solo risultati calcolati viaCLI; non fingere che l'importJSON soddisfi la richiesta.
6. **Destinazione:** app esclusivamente personale e locale perGian, nessuna pubblicazione del servizio. Personalizzazione informale appropriata. La repository pubblica non implica servizio web pubblico, dati pubblicati o multiutenza.

**Stato corrente:** nessuna implementazione assegnata aClaude su questo feedback. L'Owner chiede espressamente di portare tutto adAstra e ottenere direzione per risolverlo. Richiedere una disposizione completa su chiarezza/navigazione e minimo avvio/orchestrazione locale dei run, senza catena di specifiche parziali o infrastruttura sproporzionata. L'eventuale processo locale è motivato dall'avvio del motore, non da alimentare fixture. Non dedurre autorizzazione a nuovi dati,2026,strategia,ordini o cambio delle convenzioni.

Accettazione tecnica CAND conservata. Non rinviare il confronto conAstra in attesa di una provaOwner artificialmente positiva; il riscontro è questo. Astra deve qualificare chiusura della macrofase con limite funzionale dichiarato e il seguito. Nessun altro run/test/download richiesto per questa registrazione.
