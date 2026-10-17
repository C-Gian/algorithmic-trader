# Incarico corrente — CAND-001 primo candidato e ciclo storico di sviluppo

**Stato: DELIVERED — fase DEV completata (backtest 2023–2024, diagnosi, app); macrofase non chiusa: checkpoint del Director prima del 2025. Non ACCEPTED.**
Macrofase intera autorizzata da Astra il17ottobre2026: primo candidato completo e primo backtest riproducibile, più eventuale unica revisione motivata e confronto2025 già esposto. Il checkpoint Director dopo la diagnosi DEV governa la scelta metodologica prima degli esiti2025; non richiede una nuova autorizzazione ordinaria di Gian/Astra.
Responsabile disegno/diagnosi/review: Director. Esecutore: Claude Code.
Base codice: bf3280ec8c034a775c925d0b5f38223eeade9c53 più questo READY. Sincronizzazione checkout a cura di Gian; nessun pull/fetch dell'esecutore.

## 1. Chiusura OBS-001 e priorità

OBS-001 **ACCEPTED TECNICAMENTE**, review finale conservata nella storia del task al commit ebf81f2e972609607572dcdf26dfcb0f64132403. R1-A corretto e verificato indipendentemente:20test storici e build passati; R1-B giàPASS. Calcoli/tabelle reali verificati nella review precedente.
Il limite di comprensione Owner resta registrato; non inventare una prova positiva. Nessuna ulteriore estensione dell'esploratore. Il cursore consulta episodi già elaborati automaticamente; non chiedere a Gian verifiche di formule, conferma pivot o migliaia di origini.

Il prossimo risultato è una decisione davvero prodotta dal candidato, con esecuzione modellata, gestione, costi e risultato storico visibili. Niente nuova macrofase di UI o generica ricerca sulle sei famiglie.

## 2. Specifica unica vincolante prima del codice

Leggere integralmente **docs/research/CAND-001-v1.md**: contiene una versione iniziale completa, simmetrica LONG/SHORT, movimento→reazione→ripresa, ruoli delle sei famiglie, ingresso/astensione, target/stop, gestione dinamica, precedenze, confini e convenzioni economiche. Claude implementa quel disegno; non sceglie strategia/soglie o nuovi filtri.

Prima di esaminare esiti economici:
1. Trascrivere in config/CAND-001-v1.json parametri, versioni, fonti, finestre, fee/slippage/funding, precedenze, esempi e classificazioni del protocollo, senza modificarli.
2. Canonicalizzare JSON, calcolare SHA256, registrare data e commit della specifica. Versione candidato1.0.0, versione motore/schema distinte.
3. Implementare e verificare con pochi esempi sintetici discriminanti, poi **commit/push di codice/config/test prima del primo run economico**. Non occorre una risposta del Director per passare da sintetico a DEV: il mandato è già completo.
4. Nessun risultato di OBS-001 promuove un requisito giornaliero o un parametro; nessun riuso di A/RETURN/E/a2x o codice strategico del vecchio progetto.

Scelte tecniche ordinarie dell'esecutore consentite e motivate. Contraddizione sostanziale della specifica: isolare il punto e chiedere Director prima di cambiare metodo. Correzione di bug documentata non è ottimizzazione.

## 3. Pipeline minima e dati autorizzati

Riutilizzare acquisizione, parsing/qualità, aggregati e osservatore OBS-001, isolando il nuovo motore decisionale e il ledger di esecuzione/costi. Python già presente, stdlib dove basta; React/TypeScript/provider/UI esistenti. Nessun database, backend permanente, autenticazione, Docker, streaming o secondo frontend. Non aggiornare dipendenze per abitudine.

Non cambiare config/OBS-001-v1.json o i risultati esistenti per ampliare i periodi. Il nuovo protocollo parametrizza gli stessi calcoli e disponibilità osservativi con nuovi confini; rifattorizzazione piccola ammessa con regressioni pertinenti. Tenere dati economici/esiti separati dagli input delle decisioni.

Cartella nuova dati: directory sorella autorizzata C:\Projects\algorithmic-trader-data\CAND-001 (adattare al checkout o --data-dir). **Riutilizzare in lettura** i sette ZIP verificati in ..\algorithmic-trader-data\OBS-001\raw con relativi manifest/checksum; non riscaricarli né modificare runOBS-001. Nessuna scansione di altre directory/vecchio stack. Codice/config/report piccoli in Git; raw, mark, funding e bundle pesanti fuori Git.

### 3.1 Prezzo negoziato

Fonte/strumento invariati: Binance Vision futures/um/monthly/klines/BTCUSDT/1m/BTCUSDT-1m-YYYY-MM.zip e .CHECKSUM.
- input complessivo autorizzato [2022-10-01,2026-01-01) UTC;
- inizializzazione [2022-10-01,2023-01-01);
- DEV [2023-01-01,2025-01-01);
- ADDITIONAL_2025 [2025-01-01,2026-01-01), solo dopo checkpoint Director.
39mesi trade in tutto,7già verificati e riutilizzabili, quindi al massimo32ZIP trade nuovi. Nessun tail2026. Conteggio teorico input totale1.710.720minuti, non una certificazione di copertura. DEV ha23.392chiusure45m,2025 ne ha 11.680, comprese indisponibilità/astensioni.

Fase corrente: scaricare solo i27mesi trade ottobre2022–dicembre2024 mancanti, controllare ed elaborare DEV. I5mesi mancanti gennaio–maggio2025 saranno scaricati nella fase aggiuntiva, riusando gli altri7;2025 non va elaborato economicamente in anticipo. Non selezionare mesi favorevoli né sostituire fonte/strumento.

Cache già verificata: verificare hash locale contro manifest/checksum conservato; non è obbligatorio richiamare REST/riscaricare il file per ogni run. Per file nuovi/incompleti, checksum fornitore e ZIP, timeout/tentativi limitati e versioni precedenti conservate come OBS. Metadati pubblici d'identità già acquisiti e verificati sul PC Owner possono essere riutilizzati con provenienza; non inventare un nuovo ok se un endpoint risponde451. Non aggirare restrizioni o entrare in account.

Stessi controlli essenziali OBS-001 su schema/tempi/ms, OHLC, volumi, ordine, duplicati e buchi. Nessun forward-fill. Le barre incomplete propagano indisponibilità per misura; record osservativi immutabili e pivot confermati i+2. Non attivare un warmup globale54barre.

### 3.2 Funding e mark strettamente necessari ai costi

Nuovi dati pubblici autorizzati da Astra per la valutazione economica, stessi simbolo e confini:
- **fundingRate** mensile: https://data.binance.vision/data/futures/um/monthly/fundingRate/BTCUSDT/BTCUSDT-fundingRate-YYYY-MM.zip e .CHECKSUM;
- **markPriceKlines1m** mensile: https://data.binance.vision/data/futures/um/monthly/markPriceKlines/BTCUSDT/1m/BTCUSDT-1m-YYYY-MM.zip e .CHECKSUM.
Per DEV servono solo2023–2024; costi inizializzazione2022 non necessari perché non si apre posizione.2025 solo nella fase aggiuntiva. Nessun index/orderbook/aggTrades o scansione altri simboli.

Fattibilità verificata dal Director prima di esiti economici:
- archivio funding gennaio2023 raggiunto e ZIP ispezionato: intestazione calc_time,funding_interval_hours,last_funding_rate; primo timestamp1672531200000, successivo1672560000008. Tassi anche negativi validi. SHA256 del file nell'ispezione:05e3df32f28d0d50f4c5a280adee9368b4a66fc68c6ddca1b3277087ac0d19f5.
- checksum mark gennaio2023 HTTP200:18abe5d64d97bf153d1d8f7f9b39f51c37454add602b6af8d51f267dd0f19094.
Non sono pin eterni o verifica della copertura degli altri mesi. Confrontare i file reali coi checksum della versione scaricata, registrare variazioni.

Conservare tasso e timestamp raw, unità ms, funding_interval_hours finito positivo e schema effettivo. Non generare rate a intervalli8h per riempire buchi. Controllare unicità/ordine e intervalli rispetto alla durata dichiarata, tollerando soltanto jitter entro risoluzione1m per il controllo della distanza (timestamp raw invariato); scarti maggiori o cambi non interpretabili = copertura non certificata, non rate0. Metadati correnti di fundingInfo non sostituiscono il calendario storico.

Mark è prezzo diverso dal negoziato: parsing/identità separati; nessun volume mark usato come volume delle osservazioni. Serve soltanto il close completo del minuto precedente il minuto del settlement come **approssimazione predefinita**, secondo protocollo, mai prezzo spot/negoziato di ripiego. Si possono conservare in memoria solo i punti mark necessari ai settlement dopo validazione dei file; non creare un secondo motore di segnali mark.

Manifest distinti raw trade/funding/mark: fonte, URL, tipo, periodo, unità, acquisito_alle, hash locale/fornitore, righe/copertura/anomalie, file/cache usati. Funding o mark mancanti non valgono zero. Valutazione parziale chiaramente denominata; nessun netto completo nascondendo percorsi/costi irrisolti. Se uno schema o la fonte impediscono il lavoro, errore preciso al Director, nessuna sostituzione silenziosa.

Termini/attribuzione come OBS-001: copia locale con hash/data, uso personale di ricerca non produttiva, niente redistribuzione raw/bundle. I piccoli report aggregati e screenshot derivati eventualmente pubblicati riportano fonte Binance Vision e CC BY-NC-SA4.0 per quei soli derivati, senza cambiare licenza del codice. Nessun conto o chiave.

## 4. Esecuzione, costi e casi limite già decisi

Applicare integralmente il protocollo versionato; qui soltanto i punti da non interpretare liberamente:
- una posizione, nozionale N0=1000USDT per trade, nessun reinvestimento/leva/incremento/parziale;
- call a close45m, tentativo condizionato a open1m60s dopo, mai ingresso retroattivo;
- S0/T derivati dalla reazione/gamba, rapporto minimo1,5 controllato sia alla call sia sulla quotazione d'ingresso;
- protezione migliorata solo da pivot protettivo confermato dopo l'ingresso, efficace dopo60s, mai allargata; uscita su struttura opposta, stop/target,24h o fine finestra;
- fee baseline5bps/lato, slippage3bps avversi: assunzioni esplicite; stress unico10bps/10bps sullo stesso ledger;
- target eseguito come taker modellato, non maker perfetto; gap prezzoopen, entrambi nella stessa1m stop-first e sensibilità separata;
- funding storico con mark1mproxy, timestamp raw e ambiguità ai confini registrate; costi mancanti→netto mancante;
- DEV continuo2023–2024, resetflat all'inizio della finestra aggiuntiva2025; mai reset mensile per nascondere posizioni/perdite;
- confine end: chiusura modellata a open dell'ultimo minuto, nessuna lettura dopoend;
- gap durante esposizione può rendere il percorso irrisolto: interrompere quella finestra come specificato, non ripartire dopo il buco facendo finta di essere flat.

Non usare fee/slippage economici del DESIGN-001 per implicazione. Le decisioni di questo incarico sono quelle del protocollo e della config preregistrata.

## 5. Output riproducibile e app: stesso prodotto, un percorso concreto

Separare versione candidato, versione motore, schema e manifest di esecuzione. Run hash basato su input/config/software; timestamp/commit variabili nei manifest, non negli snapshot causali. Conservare tutti i run, incluse perdite/bugversioni; nessuna sovrascrittura con stesso ID e contenuto diverso. Comandi CLI espliciti acquire/check/run/report, default DEV; all --phase dev o equivalente riproduce il percorso autorizzato. Nessuna esecuzione economica2025 nel default.

Non inserire milioni di minuti nel DOM. Elaborazione batch e bundle/indici proporzionati, caricamento per anno o finestra se necessario, senza DB/server permanentemente attivo. Quantificare durata/memoria/dimensioni, ottimizzare solo colli di bottiglia reali. Nessun ricalcolo completo a ogni clic. Conservare hash/manifest/config per ripetere offline senza rete.

Nella stessa dashboard:
- ambiente esplicito **BACKTEST DI SVILUPPO — esecuzioni modellate, nessun collegamento exchange**; non chiamarlo Binance demo connessa;
- import del bundle candidato con discriminante/schema separato dal bundle osservativo e dalla simulazione; riusare shell/grafico/provider e componenti pertinenti. Import errato mantiene studio valido e spiega il problema. Non indebolire le correzioni R1 per un nuovo formato;
- all'apertura una pagina risultati leggibile con versione, finestra e qualità, netto modellato/costi, frequenza, rischio/percorso e concentrazione.2023/2024 distinti e mesi consultabili, celle vuote/mancanti esplicite; nessun unico saldo personale o rendimento capitale;
- pulsanti **“Prima decisione”, “Prima operazione”, “Primo caso negativo”, “Prima astensione”, “Prima protezione aggiornata”** dalle regole del protocollo. Categoria assente dichiarata, niente esempi fittizi aggiunti;
- un clic apre direttamente un episodio con spiegazione semplice: “ha riconosciuto questo movimento”, “ha atteso questa reazione”, “ha richiesto un ingresso a queste condizioni”, oppure “si è astenuto perché…”. Non chiedere a Gian di scegliere una data a caso;
- distinguere sempre informazioni disponibili alla decisione da ingresso/gestione/uscita/costi modellati successivi. Modalità causale mostra solo eventi available_at<=t; seguito del trade e risultato sono consultazione a posteriori esplicitamente etichettata, non previsione già nota;
- grafico45m/1D, origini del piano e stop originario/corrente, eventi di aggiornamento e fill modellati distinguibili. Call/ordine/posizione non fusi. Nessun dato di saldo/posizione delle fixture dentro il backtest;
- il cursore è facoltativo per ispezionare il tempo: una frase spiega “Il programma ha già elaborato tutti gli episodi; qui consulti un momento”.45m/1D cambia scala grafica, non avvia una nuova prova o un nuovo algoritmo;
- comandi simulati Start/Stop/chiusura manuale non modificano i risultati congelati del backtest. Modalità fixture può restare isolata; nessun nuovo restyling o gateFigma.

README: pochi comandi Windows reali, file da aprire e primo esempio da cliccare. L'Owner non verifica formule/pivot/ritardi; prova solo di riuscire a seguire decisione, posizione modellata, costi e motivo d'uscita/astensione.

## 6. Controlli discriminanti e scelta delle verifiche

Scegliere pochi esempi sintetici compatti che coprano:
- causale gamba conosciuta solo a i+2, nessuna call retroattiva sulle barre di conferma, struttura45m richiesta/daily solo contesto;
- LONG e SHORT, soglia ampiezza, quarti della reazione, incompatibilità e scadenza; priorità invalidazione sul trigger e consumo gamba, busy senza reingresso;
- trigger→ordine condizionato→fill futura oppure rifiuto per gap/rapporto, nessuna fee su ordine non eseguito;
- protezione monotona, pivot post-ingresso,60sdi latenza con vecchio stop attivo, struttura opposta e scadenza;
- gapoltrestop, stop+targetstessa1m, entry+exitstesso minuto, confini temporali e nessun prezzo dopo2024/2025;
- fee/slippage/funding LONG/SHORT, markproxy al tempo corretto, funding mancante e ambiguità vicino ingresso/uscita, nessuna doppia sottrazione slippage; esempi numerici del protocollo;
- stesso prefisso con due futuri diversi dà identiche decisioni, richieste e protezioni già disponibili (esiti futuri separati);
- conto delle opportunità/call/rifiuti/fill e ledger riconciliato; mesi/anni e curve non azzerati, quantili/costi/null coerenti;
- import/contratto candidato e uno o pochi percorsi integrati UI, esempio negativo/astensione e visibilità causale/retrospettiva.

Controlli solo del codice toccato. Riusando aggregazione/osservazioni intatte non rilanciare tuttoOBS-001; se le parametrizzi, rieseguire le regressioni pertinenti di disponibilità/causalità/aggregazione. Typecheck/build frontend e breve prova browser del bundle reale. Nessuna suite generale, pollingCI o infrastruttura test aggiuntiva.

Nel test difensivo di errore UI uno stderr atteso non è fallimento; documentarlo senza tacitare errori veri. Chiudere solo processi propri, non devserverOwner.

## 7. Sequenza e checkpoint metodologico

A. Implementare versione1 completa e registrarne config/hash/commit prima degli esiti. Sintetici e controlli mirati.
B. Acquisire/validare solo nuovi file strettamente necessari a DEV, riusando quelli disponibili se pertinenti; fare il backtest2023–2024 e report annuale/mensile/ledger. Integrare esempi e risultati nella dashboard esistente. Non fermarsi al solo motore o al JSON.
C. Consegnare **DEV + diagnosi** classificata secondo protocollo: bug, difformità, scelta coerente poco utile, frizione/assunzione o insufficienza. Consegnare versione negativa senza cambiare soglie per migliorarla.
D. **Checkpoint Director prima del2025.** Il Director decide di mantenerev1 oppure registra una sola revisione metodologica motivata entro la famiglia e un confronto sullo stesso DEV. Questa decisione è del Director, non dell'esecutore. Non serve approvazione strategica nuova se resta nel mandato; l'Owner trasmette la consegna.
E. Dopo registrazione del congelamento, fase aggiuntiva2025 con dati autorizzati e nessuna iterazione sui suoi esiti; stessa app e report separato. Bug documentati ancora correggibili. La faseE è già autorizzata dalla macrofase, ma l'esecutore non anticipa il checkpoint né presume di poter scegliere la revisione.

Stato prima consegna: DELIVERED con **faseDEV completata, macrofase non ancora chiusa**; current_task resta unico e sarà aggiornato dal Director al checkpoint. Non descrivere il checkpoint come mancanza di autorizzazione all'acquisizione2025 o come blocco tecnico, né chiedere un nuovo permesso ad Astra.

## 8. Consegna, pubblicazione e chiusura

Pubblicazione ordinaria su main autorizzata per file pertinenti, incluso commit pre-esiti e consegna. Nessun pull/fetch, reset/stash, force push o sovrascrittura di lavoro concorrente. Verificare repo/branch/base e modifiche locali prima di agire; checkout sincronizzato da Gian al commit comunicato.

Consegna DEV:
- commit pre-esiti, candidate/config/version/hash, manifest input/output e comandi riproducibili;
- copertura reale, file nuovi/riusati, fonti/assunzioni economiche, tempi/memoria/dimensioni;
- ledger e report completo **docs/research/CAND-001-results.md** con2023,2024 e mesi, base/stress, concentrazione/astensioni/ambiguità, casi contrari e diagnosi; riferimenti ai dati pesanti locali;
- istruzioni pratiche per aprire il risultato e un esempio direttamente nell'app; controlli realmente svolti e limiti;
- eventuali bug corretti con patch e confronto d'impatto, nessuna modifica metodologica implicita;
- aggiornareSTATE e spazio consegna del task, passareDELIVERED, maiACCEPTED.2025 ancora non eseguito economicamente.

Chiusura macrofase dopo eventuale revisione, confronto2025, review Director, prova concreta di Gian sul nuovo risultato e raccomandazione ad Astra, anche negativa. Nessuna promessa di profitto. Nessuna approvazione per denaro reale.

## 9. Esclusioni ed escalation

2026protetto, studi precedentiINACTIVE, niente famiglia diversa/nuovi segnali/ricerca automatica parametri, conto collegato/chiavi, ordini esterni, stackOwner, infrastrutturaL2, nuova piattaforma o restyling. Nessuna validazione indipendente attribuita al2025 già esposto.
Solo conflitti sostanziali ad Astra; dettagli tecnici al Director/esecutore nel mandato.

## Spazio dell'esecutore

### Preregistrazione prima di dati economici ed esiti (Claude Code, 17 ottobre 2026)

**Stato allora: IN_PROGRESS.**
- **Base e ambiente.** Base `0d48828` su `main`, checkout pulito, nessun pull o fetch. Python 3.12.14 già presente via `uv`; i test passano anche su 3.11.16.
- **Configurazione.** `config/CAND-001-v1.json` trascrive `docs/research/CAND-001-v1.md` (commit `0d4882848d014f8137153848171243674759370d`, 17 ottobre 2026), senza modifiche: parametri, finestre, fonti, fee/slippage/funding, precedenze, regole degli esempi e classi di diagnosi. Candidato 1.0.0, motore `cand001` 1.0.0, schema bundle `cand001.bundle/1`.
- **Hash.** SHA256 canonico (JSON con chiavi ordinate, indipendente dai fine riga): `aed2c4ef627617d73972778097bbab5fb702ab5064ce9e6eb68ded2170ce4edf`. Convenzioni osservative OBS-001/v1 invariate (`3c4eb884…2387`), verificate al caricamento.
- **Codice.**
  - `src/cand001/`: config, decision (motore decisionale), execution (ledger e costi), backtest (orchestrazione), metrics, data (acquisizione e controlli trade/funding/mark), bundle, cli.
  - Osservatore, aggregazione e parsing sono riusati da `obs001` senza modifiche, solo con nuovi confini di input.
- **Test sintetici.** 28 (`tests/test_cand001_*.py`):
  - esempi LONG e SHORT del protocollo con S0, T, E*, rischio, spazio e vincolo d'ingresso;
  - nessuna call retroattiva e 1D solo come contesto;
  - soglia 3A, struttura, durata, occupazione;
  - quarti della reazione e bordi, contraddizioni prima del trigger, scadenza alla barra 12, astensione per rapporto;
  - protezione solo dopo l'ingresso e monotona, uscita per struttura;
  - fill a open+60s con vincolo, rifiuti senza costi, gap oltre lo stop, stop-first con alternativa, ingresso e uscita nello stesso minuto, latenza dello stop aggiornato, 24h, fine finestra, gap di dati;
  - esempi contabili 18,889 e 19,111, mark mancante, ambiguità ai confini, slippage non doppio, stress;
  - catena completa: stesso prefisso e futuri diversi danno decisioni, richieste e protezioni identiche; riconciliazione; nessun minuto dopo la fine.
- **Sequenza.** Nessun download e nessun backtest reale prima del commit che contiene questa nota.

Questa preregistrazione è nel commit `8146336`, pubblicato prima del primo download.

### Consegna DEV (Claude Code, 17 ottobre 2026) — DELIVERED, fase DEV completata, macrofase non chiusa

**Commit**
- `8146336`: preregistrazione di config, motore e 28 test.
- `c597a5e`: ambiente app «Backtest di sviluppo», fixture sintetica, 8 test UI, correzione della misura di memoria.
- Il commit della consegna aggiorna questo file, STATE, README e il report.

Tutti su `main`, senza pull, fetch o force push. **Il 2025 non è stato scaricato né elaborato economicamente.** La CLI rifiuta `--phase additional2025` finché il Director non registra il congelamento.

**Riproduzione**
- PowerShell: `$env:PYTHONPATH="src"; python3.12 -m cand001 all` (fase predefinita DEV); offline basta `run`.
- Dati in `C:\Projects\algorithmic-trader-data\CAND-001\` (raw/trade, raw/funding, raw/mark, manifests con copie datate, runs).
- Run `CAND-001-v1.0.0-e1.0.0-DEV-adaa94c502-aed2c4ef62`: input hash `adaa94c502…`, bundle 9,1 MB, SHA256 `53d5fdcfbfe1c4ef…`.
- Rieseguito da `c597a5e`: bundle identico byte per byte. Il commit sta solo nel manifest del run.
- Tempi: 22,3 s totali (controllo 18,4 s, backtest 1,9 s); picco di memoria 532 MB.

**Dati**
- **Nuovi**, scaricati il 17 ottobre alle 07:29–07:31 UTC con checksum del fornitore tutti verificati: 27 ZIP trade (da ottobre 2022 a dicembre 2024), 24 funding e 24 mark (2023–2024).
- **Trade:** 1.185.120 minuti validi su 1.185.120, nessuna anomalia.
- **Funding:** 2.193 eventi a 8 h, jitter massimo 29 ms, nessuna anomalia di serie.
- **Mark:** 2.189 punti su 2.193. Manca un giorno nel febbraio 2023 (funding del 24–25 febbraio) e 2 minuti nell'agosto 2024; il punto del 1° gennaio 2023 alle 00:00 cadrebbe nel 2022, non acquisito e non necessario. Nessuna operazione è toccata.
- **Riusati:** identità dello strumento e termini, dalla verifica OBS-001 con provenienza. I 7 ZIP OBS del 2025 non sono stati letti in DEV.
- **Hash Director:** gennaio 2023 funding (`05e3df32…`) e mark (`18abe5d6…`) coincidono.

**Risultato DEV** (operazioni da 1.000 USDT di nozionale, somme; report completo in `docs/research/CAND-001-results.md`)

| | 2023 | 2024 | 2023–2024 |
|---|---:|---:|---:|
| Operazioni (LONG/SHORT) | 41 (19/22) | 37 (11/26) | 78 (30/48) |
| PnL ai prezzi di riferimento | −49,79 | −35,65 | −85,44 |
| Slippage / fee / funding | −24,57 / −40,95 / −0,57 | −22,23 / −37,06 / +0,23 | −46,80 / −78,01 / −0,34 |
| **Netto modellato** | **−115,87** | **−94,72** | **−210,59** (−2.106 bp di N0) |
| Netto stress 10+10 bp | −214,15 | −183,65 | −397,80 |
| Quota netti positivi / profit factor | 24,4% / 0,42 | 24,3% / 0,54 | 24,4% / 0,48 |
| Drawdown massimo (1m) / sequenza di perdite | −136,90 / 12 | −103,50 / 10 | −216,79 / 12 |

- Uscite: 56 stop, 17 target, 4 struttura, 1 a 24 h.
- Protezioni aggiornate: 31 su 23 operazioni.
- Nessun contatto stop+target nello stesso minuto, nessun gap, nessun funding ambiguo o mancante.
- Mesi: 15 negativi, 8 positivi, 1 senza operazioni.
- Concentrazione: i 5 trade maggiori pesano il 14,7% della somma dei |netti|.

**Diagnosi** (classi del protocollo; dettagli nel report)
- **Bug:** nessuno. Il riscontro indipendente dai minuti grezzi (87 call e 78 operazioni: A0, ampiezza, profondità, trigger, S0, ingresso, percorso d'uscita con le precedenze, netto) dà zero differenze.
- **Non fedele al disegno:** nessuna. Due interpretazioni tecniche da confermare: le contraddizioni sono valutate anche a t0, senza trigger; un'uscita esattamente su una chiusura 45m occupa quella chiusura.
- **Coerente ma poco utile (principale):** il lordo ai prezzi di riferimento è già negativo. Il target viene raggiunto nel 22% dei casi, contro circa il 33% necessario con spazio/rischio mediano 2,05. Gli stop avevano un'escursione favorevole mediana di 0,38R. Le astensioni per spazio/rischio sono 271 su 814 episodi (mediana 0,68).
- **Costi e assunzioni sensibili:** fee e slippage valgono in mediana circa il 28% del rischio iniziale (stop vicino, 0,57% di N0 in mediana) e fanno 124,81 dei 210,59 persi. Lo stress quasi raddoppia la perdita.
- **Informazione insufficiente:** 78 operazioni in 24 mesi, 2% del tempo in posizione. LONG e SHORT sono entrambi negativi, profilo simile nei due anni.

Nessuna soglia è stata cambiata. La decisione v1 / unica revisione spetta al Director.

**App.** Ambiente «Backtest di sviluppo» nella stessa dashboard, con banner «BACKTEST DI SVILUPPO — esecuzioni modellate, nessun collegamento exchange».
- Import con contratto e validatore separati da OBS-001 e dalla simulazione: tutti i campi annidati letti dalle viste sono controllati, e un file errato lascia aperto il backtest valido.
- Pagina risultati: versione, finestra, qualità, netto con costi separati, 2023/2024/DEV, mesi, frequenza, rischio e percorso, concentrazione.
- Cinque pulsanti: «Prima decisione», «Prima operazione», «Primo caso negativo», «Prima astensione», «Prima protezione aggiornata». Sul reale sono tutti presenti; una categoria assente è dichiarata e disattivata.
- Vista episodio: frasi «Ha riconosciuto questo movimento / Ha atteso questa reazione / Ha chiesto un ingresso a queste condizioni / Si è astenuto», più i momenti dell'episodio.
  - Il grafico 45m/1D mostra solo candele, linee di piano e pivot noti al momento.
  - «Mostra seguito modellato» aggiunge ingresso, stop aggiornato, uscita e la scheda del risultato «A POSTERIORI».
- Registro operazioni: 78 righe apribili.
- Nessun saldo personale; i comandi della simulazione non toccano i risultati.

**Verifiche dell'esecutore**
- **Python:** 28 test sintetici CAND (anche su 3.11.16) più riscontro e diagnosi indipendenti sul run reale. I test OBS-001 non sono stati rilanciati, perché l'osservatore è riusato senza modifiche.
- **Frontend:** 44 test UI, typecheck e build. Gli 8 nuovi riguardano import, risultati, esempi causali e a posteriori, astensione, registro e separazione dalla simulazione; le regressioni R1 e della barra superiore sono incluse perché ho toccato shell e `TopBar`.
- **Browser:** Chrome headless sulla build con il bundle reale. Apertura in 0,15 s, i cinque esempi aperti, uscita assente prima del seguito e presente dopo, 78 righe nel registro, 1D, nessun errore e nessuna richiesta esterna.
- **Immagini:** 3 in `docs/research/CAND-001-screens/` (CC BY-NC-SA 4.0 per i soli derivati).

**Limiti**
- Esecuzione modellata, senza order book, margine o liquidazioni. Fee e slippage sono assunzioni; il funding usa il proxy mark 1m.
- Risoluzione 1m.
- Campione DEV già usato per la diagnosi.
- Ho chiuso solo il mio `vite preview` (PID 20512); il `vite` di sviluppo PID 10872 non è mio ed è rimasto acceso.

**Prova di Gian** (dopo la review): seguire il paragrafo «Backtest di sviluppo CAND-001» del README.
1. Aprire il file del run.
2. Premere «Prima operazione», leggere le tre frasi e poi «Mostra seguito modellato».
3. Ripetere con «Primo caso negativo» e «Prima astensione».

Non serve verificare formule o pivot.

## Review del Director

Specifica completa prima degli esiti. Fonti primarie consultate; archivio fundinggennaio2023 e checksum markgennaio2023 verificati come fattibilità/campi, nessun backtest economico del candidato svolto. Review tecnica e diagnosi reale dopo la consegnaDEV.
