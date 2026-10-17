# Incarico corrente — CAND-001/R1, correzioni prima del confronto 2025

**Stato: DELIVERED** (Claude Code, 17 ottobre 2026; assegnato READY dal Director lo stesso giorno). Consegna nello «Spazio dell'esecutore».
Esecutore: Claude Code. Base: `ee7282f84ebade3a7daaebb15c06532da24df79e` più il commit di questo incarico. Gian sincronizza il checkout; nessun pull/fetch dell'esecutore, neppure dry-run.

La macrofase Astra resta autorizzata interamente. Questo è il seguito della review DEV, non una richiesta di nuovo permesso ordinario. Consegna DEV e incarico originario sono conservati nella storia di questo file a ee7282f. Specifica vincolante: **docs/research/CAND-001-v1.md**. OBS-001 resta chiuso tecnicamente; limite di comprensione Owner conservato.

## 1. Review indipendente del Director su ee7282f

**Esito: correzioni richieste, non ACCEPTED.** Nessuna prova d'uso positiva Owner registrata per CAND-001.

Controllato:
- lettura di protocollo, config, decisioni, ledger, acquisizione, metriche, bundle e viste app;
- confronto Git: config, decision.py, execution.py, backtest.py, metrics.py, data.py e i 28 test non sono cambiati dal commit preregistrato 81463360d57f58aadb4bad478bbfa18c5bdd522a; successivamente aggiunta la UI, modifica CLI limitata alla misura memoria;
- nella copia isolata del Director: **28 test Python CAND superati, 8 test Backtest.test.tsx superati, typecheck/build riusciti**;
- riproduzioni sintetiche aggiuntive dei tre difetti sotto.

Non svolto dal Director in questa review: download/ricalcolo autonomo dei 75 archivi DEV, riproduzione indipendente dei 78 trade reali, browser sui dati reali. I valori −210,59 / −85,44 e il riscontro delle 87 call / 78 operazioni restano evidenza dell'esecutore. Una verifica separata scritta dallo stesso esecutore è utile, ma non va presentata come review indipendente del Director. I test verdi non provano assenza di bug.

Le due interpretazioni segnalate sono confermate come coerenti: contraddizioni controllate già a t0 senza permettere il trigger; uscita esattamente sulla chiusura 45m occupa quella chiusura, senza nuova gamba alla stessa chiusura.

## 2. Decisione metodologica del checkpoint DEV

**Mantenere CAND-001 candidato 1.0.0, senza revisione metodologica in questa macrofase.** Config SHA256 canonico:
`aed2c4ef627617d73972778097bbab5fb702ab5064ce9e6eb68ded2170ce4edf`.

La diagnosi consegnata indica debolezza già ai prezzi di riferimento, costi sensibili e poche operazioni. Non identifica una modifica unica con una ragione abbastanza specifica da giustificare un nuovo candidato. La sola perdita non motiva cambiare profondità, target, stop o filtri per migliorare il risultato. Si conserva la v1 negativa; non si cercano parametri alternativi. Il confronto 2025 servirà a completare l'evidenza prevista, non a scegliere una variante.

Sono congelati disegno e convenzioni metodologiche, **non approvata l'implementazione difettosa**. R1 è una patch tecnica, non la revisione metodologica concessa da Astra. Nessuna v2 o nuova famiglia in questo incarico.

**2025 ancora non elaborabile in R1.** Dopo accettazione delle correzioni il Director registrerà la base tecnica e il seguito operativo 2025 già autorizzato. Non chiedere un altro permesso ad Astra/Gian; non sbloccare la CLI o anticipare download/calcoli 2025 in questo task. Il 2026 rimane protetto.

## 3. R1-A — funding assente non equivale a costo zero

Difetto riprodotto:
- `check_funding_series([], start, end)` restituisce `certified=True`;
- serie sintetica con eventi alle 00:00 e 16:00, intervallo dichiarato 8h: viene segnalato INTERVAL_MISMATCH, ma `load_costs` restituisce normalmente i dati;
- un trade fra 04:00 e 12:00 attraversa il tratto sospetto delle 08:00. `Ledger.funding_for` produce `events=[]; total=0; missing=False`. Quindi un evento assente viene trattato come assenza di costi.

Comportamento richiesto:
- la qualità del funding deve influire realmente sull'ammissibilità del risultato economico, non essere una nota ignorata;
- soluzione proporzionata scelta dal Director: **bloccare il run economico prima del ledger** quando la serie funding è vuota, contiene righe corrotte/non finite, duplicati/conflitti, eventi fuori mese, incongruenze degli intervalli o copertura non verificabile. Dare errore preciso con fonte/intervallo/motivo e conservare il rapporto qualità;
- controllare anche i confini della copertura, non soltanto le coppie interne. Usare gli intervalli dichiarati e la tolleranza registrata; non inventare un calendario di addebiti, tassi o prezzi. Un intervallo che non si riesce a certificare si dichiara tale e blocca il netto completo;
- non cambiare trattamento dei singoli mark mancanti: restano MISSING per i cashflow pertinenti, come nel protocollo. Non bloccare indiscriminatamente per mark non necessari ai trade;
- un input valido dà gli stessi funding, decisioni e risultati di prima. Nessun nuovo costo o parametro.

Verifiche mirate: serie valida, vuota, buco interno, copertura iniziale/finale insufficiente, riga corrotta/duplicata; almeno un caso attraverso il percorso di caricamento usato dal comando run, provando che non venga prodotto un netto completo. Riutilizzare pochi esempi; niente suite generale.

## 4. R1-B — finestra interrotta, aggregati e app coerenti

Difetto riprodotto:
1. ingresso LONG sintetico a 100 con S0=98 e T=110;
2. minuto successivo mancante;
3. ledger correttamente HALT con un trade UNRESOLVED_DATA_GAP;
4. `trade_stats` restituisce `n=1, closed=0, unresolved=1, net=0.0, stressNet=0.0, netMissing=0`.
Con trade già chiusi il totale esclude il trade irrisolto. `reconcile` può dichiarare riconciliata la sola parte chiusa.
In più il validatore ammette `exit=null`, ma l'apertura del suo episodio dereferenzia `tr.exit.accountingTime` e va in errore. Riprodotto con un bundle sintetico accettato dal validatore.

Comportamento richiesto:
- per ogni aggregato che include un trade irrisolto, netto completo/netBps/stress sono **mancanti**, non zero o somma dei soli chiusi. Contare e mostrare gli irrisolti;
- per la finestra interrotta, nessun risultato completo o drawdown dell'intero periodo. Eventuali valori del prefisso noto devono avere nome e copertura esplicitamente parziali. Le distribuzioni dei soli trade conclusi possono restare, dichiarando il sottoinsieme;
- conservare quanto era già noto: ingresso, fee di ingresso, protezioni, cashflow valutabili e momento della lacuna; non inventare uscita o risultato;
- rendere coerenti ledger, riepilogo, riconciliazione, bundle, contratto/validatore e UI. Un bundle legittimo prodotto dal motore con percorso irrisolto deve aprirsi: avviso di finestra interrotta, registro consultabile e episodio senza crash, stato “percorso irrisolto”, nessuna uscita fittizia;
- dopo HALT distinguere dati presenti da decisioni realmente valutate. Non chiamare “chiusure valutate” tutti i tempi teorici successivi;
- un periodo successivo non valutato non è un mese a risultato zero. Un periodo precedente completamente valutato può conservare i suoi risultati;
- la riconciliazione distingue conti della parte nota e completezza della finestra. Non basta un flag generale verde mentre manca un trade.

Verifiche: gap sulla prima posizione e gap dopo una posizione già conclusa, aggregati/curve coerenti; bundle realmente generato con HALT caricato e aperto tramite l'app, inclusi registro e seguito modellato. Non basta modificare a mano la sola intestazione del JSON.

## 5. R1-C — ultimo prezzo noto nella nuova vista backtest

Difetto riprodotto con fixture del motore:
- aprire un episodio con call in orario non coincidente con mezzanotte, passare a 1D;
- ultima candela completa termina prima del cursore;
- EpisodeView passa comunque `lastPriceCurrent=true`: il grafico espone il titolo “Prezzo corrente della scala”.
Il precedente R1-B osservativo aveva già chiarito il comportamento; va rispettato anche qui.

Comportamento richiesto:
- se alla scala selezionata manca una candela completa che termina al momento consultato, nessun prezzo corrente;
- eventuale ultimo prezzo noto della stessa scala separato, con orario e dicitura “non corrente”; nessun prezzo futuro o valore zero sostitutivo;
- tratto senza candele complete: messaggio di indisponibilità. Preservare modalità causale/retrospettiva e simulazione;
- coprire anche il momento di ingresso a t+60s rispetto alla griglia 45m. Passare 45m/1D cambia scala, non disponibilità dei prezzi.

Verifica UI mirata del giorno incompleto, momento t+60s e tratto senza candele complete. Riutilizzare il comportamento/componenti pertinenti già esistenti, senza restyling.

## 6. Diagnosi e limiti da correggere nel report

Non cambiare le tabelle per ragioni narrative.
- “Bug: nessuno” diventa dichiarazione della consegna iniziale, seguita dai difetti della review e dal loro impatto verificato. Nessuna frase “la perdita viene sicuramente dal metodo e non dal programma”.
- Il 33% derivato dal rapporto mediano 2,05 è solo un esempio teorico per trade identici con due sole uscite. **Non è il pareggio effettivo di questo ledger**: rischi/rapporti diversi, quantità normalizzate, protezioni e altre uscite lo impediscono. Togliere il confronto 22% contro 33% come dimostrazione del fallimento; conservare target17/78 e PnL ai riferimenti come descrizioni distinte.
- Distinguere concentrazione osservata dalla frase assoluta “la perdita non dipende da casi sfortunati”. Nessuna conclusione causale o certezza sulla famiglia generale.
- Resta valida la raccomandazione Director: nessuna modifica metodologica selezionata, evidenza negativa da conservare.

## 7. Verifiche, versione e consegna

Nessun nuovo download. Usare i file DEV già verificati. Config candidato e osservatore invariati; aggiornare versione motore patch per il comportamento tecnico corretto, con nota d'impatto. Non sovrascrivere il vecchio run.

Prima dimostrare le regressioni su ee7282f, poi passaggio delle correzioni. Eseguire i test CAND pertinenti, test UI backtest/R1 toccati e typecheck/build. Nessuna suite generale, polling CI o servizi aggiuntivi. Prova browser proporzionata dei nuovi casi e del bundle DEV reale; chiudere solo processi propri.

Rieseguire DEV **offline una volta** con la patch, perché cambia la gestione della qualità e degli aggregati. Confrontare contenuti numerici/decisioni/richieste/trade con il run precedente, escludendo le sole differenze dichiarate di versione/schema/qualità. Atteso: nessun cambiamento dei 78 trade o dei loro importi se davvero non toccati da dati mancanti. Se cambia qualcosa, identificare il bug e quantificare, senza modificare convenzioni.

Pubblicare commit/push su main solo di file pertinenti; nessun force push, pull, fetch, reset/stash o dati pesanti in Git. Aggiornare report, README se necessario, STATE e consegna di questo task; passare DELIVERED, mai ACCEPTED. Indicare controlli realmente svolti e file locale preciso da aprire. Non registrare una prova positiva Owner non avvenuta.

## 8. Seguito già deciso, fuori da R1

Dopo review tecnica: mantenimento v1, congelamento della base tecnica corretta, confronto ADDITIONAL_2025 senza iterazioni sui suoi esiti. Nel predisporlo occorrerà correggere la predisposizione attuale di `phase_months/load_trade`: oggi ADDITIONAL_2025 legge solo gennaio–dicembre2025. Il protocollo richiede osservazioni inizializzate da **tutto il prefisso dal 2022-10-01**, pur partendo FLAT senza episodi al 2025-01-01. Non confondere confine dei trade valutati e prefisso osservativo. Riutilizzare DEV e i sette archivi OBS del2025, solo mancanti da acquisire; nessun tail2026. Questa nota fissa il requisito, non autorizza l'esecuzione anticipata in R1.

## Spazio dell'esecutore

**Stato: DELIVERED** (Claude Code, 17 ottobre 2026). Non ACCEPTED: in attesa di review del Director. Nessuna prova d'uso Owner svolta o registrata.

### Patch (motore 1.0.1, schema bundle `cand001.bundle/2`; candidato 1.0.0 e config `aed2c4ef…ce4edf` invariati)
- Commit `0a46892`: R1-A, R1-B, R1-C con test e fixture.
  - Python: `data.py` (`check_funding_series`, `FundingNotCertified`, filtro alla finestra), `cli.py` (blocco prima del ledger, manifest di qualità scritto comunque), `execution.py` (trade irrisolto conservato), `metrics.py` (copertura, parte nota, drawdown parziale, riconciliazione separata), `bundle.py`, `fixture.py`.
  - App: contratto, validatore, risultati, registro, episodio.
- Commit `605544b`: correzione trovata nella mia prova browser. Nei periodi interrotti le chiusure valide erano contate anche dopo l'interruzione (639 su 581 valutate). Inoltre, con irrisolte, le statistiche per operazione sono marcate «solo concluse». Nessun effetto su finestre complete.
- Commit docs (questo): report, README, STATE, consegna.
- Cambiamento dichiarato del contratto: il flag `reconciliation.reconciled` è sostituito da `knownPartReconciled` e `windowComplete`. Per questo `tests/test_cand001_backtest.py` è aggiornato su quel solo punto. Il bundle e1.0.0 (schema /1) non si apre più nell'app.

### Riproduzioni prima / dopo
Prima, sul codice identico a `ee7282f` (script separato, dati sintetici):
- serie funding vuota risultava `certified=True`;
- un buco interno era segnalato come `INTERVAL_MISMATCH` senza blocco: il trade aperto nel buco riceveva `events=[]`, `total=0`, `missing=False`;
- con lacuna a posizione aperta: `net=0.0`, `stressNet=0.0`, `netMissing=0`, trade assente dal ledger.

I nuovi test `tests/test_cand001_r1.py` (8) sul codice vecchio non passano: 4 fallimenti e 6 errori. Dopo la patch: verdi.

R1-C: con la logica vecchia ripristinata temporaneamente, 2 dei test UI R1 falliscono (prezzo corrente in 1D e a t+60s); con la patch passano.

### Verifiche svolte
- Python: test CAND 36/36 (`test_cand001_*.py`). Ho eseguito anche l'intera discover `tests` (80/80): era più del richiesto, nessun effetto.
- UI: `Backtest.test.tsx` 8/8 e nuovo `BacktestR1.test.tsx` 6/6. Coprono: bundle HALT dal selettore, mese «non valutato», registro ed episodio irrisolto senza uscita fittizia, 1D con giorno incompleto, momento t+60s, tratto senza candele complete. Ho eseguito anche l'intera suite vitest (84/84): anche questo più del richiesto.
- `npx tsc -b` e `npm run build`: riusciti.
- Fixture `synthetic-backtest.json` e `synthetic-backtest-halt.json` rigenerate dal motore; la rigenerazione dà file identici byte per byte.
- Browser (Chrome headless su mia `vite preview` 127.0.0.1:4173, poi chiusa; il vite dell'Owner PID 10872 non è stato toccato).
  - Bundle DEV reale e1.0.1: aperto in 0,15 s; nessun avviso di interruzione; copertura «completa».
  - Primo episodio SHORT alla call 03:45: in 45m prezzo corrente presente; in 1D nessun prezzo corrente e avviso «Ultimo noto della stessa scala: 16.537,60 USDT, chiusura alle 01 gen 2023, 00:00 UTC (non corrente)».
  - Momento d'ingresso 03:46: avviso anche in 45m, ultimo noto 16.529,40 alle 03:45.
  - Fixture HALT: avviso con parte nota +81,70 su 2 operazioni concluse, 1 irrisolta, 581 chiusure valutate e 59 non valutate. Netto, stress e drawdown «n.d.»; drawdown parziale −2,94 fino all'interruzione. Registro con «percorso irrisolto». L'episodio si apre anche col seguito: passo «Percorso irrisolto», nessuna «Uscita modellata», fee solo d'ingresso.
  - Nessun errore in console, nessuna richiesta esterna.

### Run DEV offline e confronto
- Nessun download. `python3.12 -m cand001 run` dal commit pulito `0a46892`: run `CAND-001-v1.0.0-e1.0.1-DEV-adaa94c502-aed2c4ef62`, bundle SHA256 `b141150237e94a807817adea2d9fb6810f6eabc220d7db5ea3602d8b79b4944a`, 22,3 s, picco 533 MB. Serie funding certificata (2.193 eventi, 0 anomalie); mark 2.189/2.193 come prima.
- Dopo `605544b` il run è stato rieseguito una seconda volta solo per verificare che la correzione non toccasse il DEV: bundle identico, nessuna sovrascrittura. È stato aggiunto il solo manifest del secondo run.
- Il vecchio run e1.0.0 (`53d5fdcf…`) è intatto.
- Il manifest corrente `manifests/input-dev.json` della cartella dati è stato riscritto dal controllo (ogni run lo fa); i run conservano ciascuno il proprio `input-manifest.json`.
- Confronto con e1.0.0 (script separato):
  - candidato, convenzioni, finestra, fonte, nozionale e input hash: uguali;
  - 814 episodi, 87 richieste e 360 finestre: identici;
  - 78 trade con zero campi diversi;
  - terminazioni identiche;
  - sintesi: tutti i valori comuni uguali; unica differenza, la rimozione dichiarata di `reconciled`.
- Netto −210,59, riferimenti −85,44, stress −397,80, drawdown −216,79: invariati.

### Report
`docs/research/CAND-001-results.md`:
- nuova sezione «Correzioni R1» con difetti, prima/dopo, impatto e confronto;
- «Bug» riscritto come dichiarazione della consegna iniziale seguita dai difetti della review;
- tolto il confronto 22% contro 33%; target 17/78 e PnL ai riferimenti restano come descrizioni distinte;
- concentrazione descritta senza frasi assolute;
- tabelle sostituite con il `results.md` del nuovo run: solo righe aggiunte (copertura, chiusure valutate/teoriche, irrisolte, parte nota), nessun numero cambiato.

README: percorso del nuovo bundle.

### Limiti
- Funding non certificato e percorso irrisolto sono provati solo su dati sintetici: il DEV reale non li contiene.
- A 390 px l'intestazione dell'episodio sporge di 256 px. Il difetto c'era già prima di R1; non è corretto, perché l'incarico esclude il restyling. Le altre viste del backtest non sporgono.
- §8 (prefisso 2022-10-01 per ADDITIONAL_2025) non toccato; nessuna elaborazione 2025.

### File da aprire
`C:\Projects\algorithmic-trader-data\CAND-001\runs\CAND-001-v1.0.0-e1.0.1-DEV-adaa94c502-aed2c4ef62\cand001-bundle.json` nell'app, ambiente «Backtest di sviluppo», pulsante «Apri backtest».
