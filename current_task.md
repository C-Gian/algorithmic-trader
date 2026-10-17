# OBS-002 — Prosecuzione ed esaurimento del tentativo di ripresa

**Stato: DELIVERED** (Claude Code, 17 ottobre 2026; in attesa di review del Director, non accettato). Incarico READY del Director, 17 ottobre 2026; esecutore Claude Code. Base main **9d5df7d3dc8aed9feda44b624e36dddd461f8590** più il commit di questo incarico. Checkout sincronizzato da Gian, nessun pull/fetch. Leggere AGENTS, STATE, PRODUCT-CONTEXT §31 e questo task; definizioni osservatore OBS-001/v1 e config/OBS-002-v1.json. Nessun nuovo cantiere preparatorio UI.

## 1. Domanda, responsabilità e confini
Astra accetta il ciclo CAND-001 senza v2 e autorizza una sola analisi esplorativa: dopo movimento e arretramento, quali differenze già osservabili al primo tentativo di ripresa aiutano a distinguere prosecuzione da esaurimento? Le informazioni possono contare insieme anche quando presenti in esiti opposti. Nessun requisito di efficacia autonoma di ciascuna famiglia. Il Director non ha escluso ogni possibile modifica futura di CAND-001.

Solo Binance Vision BTCUSDT perpetual USDⓈ-M trade1m già conservato: input [2022-10-01,2025-01-01), origini DEV [2023-01-01,2025-01-01) UTC. Nessun download/rete per dati, funding/mark o costi necessari, 2025/2026 o vecchio stack. V1, config, ledger e risultati CAND-001 immutabili; non eseguire CAND-001 o varianti. Il caricamento dei file deve limitare esplicitamente i mesi a ottobre2022–dicembre2024, verificando hash/provenienza già conservati. Nessuna nuova fonte.

Claude implementa le convenzioni sotto e produce evidenze, non sceglie indicatori, soglie, gruppi o ipotesi operative. Director interpreta il confronto e chiude con al massimo una ipotesi concreta, con controesempi e verifica successiva necessaria, oppure nessuna distinzione interpretabile e limite preciso. Un'ipotesi sarà scoperta su DEV già esposto, non efficacia; nessuna sua implementazione autorizzata ora. Microstep/review/correzioni ordinari autonomi, ad Astra alla chiusura o conflitto sostanziale.

## 2. Popolazione causale, più ampia della ricetta v1
Riutilizzare osservatore OBS-001/v1 invariato, aggregati 45m/1D UTC, pivot stretti2+2 e sequenza alternata APPEND/REPLACE. Non usare estremi individuati guardando il futuro. È una definizione osservativa nostra, non una definizione ottimale di movimento.

**Movimento/versione.** A ciascun evento FIB_SEQUENCE APPEND/REPLACE disponibile a t0 con due ancore opposte P0/P1: d=+1 per LOW→HIGH, −1 per HIGH→LOW; L=d*(P1.price−P0.price)>0 e ancore nello stesso segmento. Registrare anche eventi esclusi per ancore mancanti, segmenti diversi o L<=0, con motivo. KEEP non crea versioni. Le ancore e i tempi di disponibilità della versione restano congelati.

Tenere al massimo una versione attiva per ciascun verso: un nuovo movimento/versione dello stesso verso ritira la precedente a t0; un movimento del verso opposto può coesistere, non la ritira. Elaborare prima gli aggiornamenti disponibili a una chiusura, poi i tentativi di quella chiusura. Reset del segmento ritira entrambi i contesti. Nessuna scadenza di 9h o posizione che occupi l'osservatore. Alla fine DEV contesti senza seguito terminano amministrativamente, non come fallimenti.

**Collegamento dei tentativi.** groupId=(verso,P0.candidateOpen), entro il segmento; versionId include inoltre P1.candidateOpen e availableAt. REPLACE di P1 con stesso P0 mantiene groupId, storico versioni e contatore dei tentativi. Nuova gamba con P0 diverso crea nuovo gruppo. Conservare gli intervalli di attività e motivi di ritiro; non prolungare una vecchia versione dopo il ritiro, non contare due versioni dello stesso verso alla stessa chiusura. Gruppi distinti possono comunque avere futuri sovrapposti: non sono certificati indipendenti.

**Arretramento e primo tentativo.** Per la versione attiva, dalla barra successiva alla candela di P1 alla barra k appena chiusa:
- deve esistere almeno una chiusura contro d: d*(Cj−Cj−1)<0;
- Rext=min(low) per LONG, max(high) per SHORT; profondità=d*(P1.price−Rext)/L. Registrare la profondità senza imporre 1/4–3/4, nemmeno il limite 1;
- tentativo a chiusura t>=t0: LONG Ck>Hk−1 e Ck>Ok; SHORT Ck<Lk−1 e Ck<Ok. La barra precedente e tutte le barre usate devono essere complete nello stesso segmento;
- il primo tentativo del gruppo richiede quella reazione già osservata. Un ulteriore tentativo richiede almeno una nuova chiusura contro d strettamente dopo il tentativo precedente e un nuovo trigger; chiusure consecutive di ripresa senza nuovo arretramento sono continuazione dello stesso tentativo, non nuove righe. Per REPLACE sono richiesti sia arretramento dopo il nuovo P1 sia riarmo dopo l'ultimo tentativo del gruppo, se esiste.

Inizializzare contesti, versioni e contatori anche nel prefisso dal2022-10-01, senza includerne le origini nella popolazione DEV. Il contatore non si azzera a gennaio o a cambio mese. Un tentativo DEV di gruppo già osservato nell'inizializzazione mantiene ordinal>1 e lo dichiara. La popolazione principale per la domanda sul primo tentativo comprende ordinal=1 con t in DEV. Tutti i successivi tentativi DEV restano nel registro e nel riepilogo secondario dipendente; nessuna scelta del tentativo poi migliore. Conteggiare gruppi/versioni senza alcun tentativo e gruppi iniziati prima DEV.

**Vincoli v1 rimossi, intenzionalmente:** nessuna struttura richiesta nel verso, soglia3A, limite32barre della gamba, profondità1/4–3/4, scadenza12barre, esclusione se P1 ritoccato, rapporto1,5, guard d'ingresso, ritardo60s, stop/target, costi, consumo/occupazione per posizione. Rimangono causalità e qualità delle barre. Il trigger di una barra è solo un localizzatore comune del tentativo, non una call o un ordine. Sono ammesse origine già oltre P1, struttura contraria/mista e volume/medie/Fibonacci mancanti. La selezione non dipende da A positiva: se manca A si conserva l'origine con esiti normalizzati mancanti. Questa popolazione non è una replica di tutti gli episodi v1 e non è un backtest senza protezioni.

## 3. Snapshot congiunto all'origine
Un record per tentativo con ID/verso/group/version/ordinal, ancore e availableAt, t,Ct, arretramento e trigger; tutte le misure hanno valore o motivo mancante. Snapshot e storia delle versioni append-only, indipendenti dal seguito. Ultimo 1D concluso entro t, mai giorno in formazione. Sei famiglie nello stesso record:
- struttura45m e1D, ultimi pivot disponibili;
- tutti i livelli esistenti pivot/day con prezzo, ruolo geometrico e d*(livello−Ct)/At; indicare il più vicino davanti e dietro (strict >0/<0, a parità kind poi id), livello esattamente a Ct distinto. Non chiamarli ostacoli certi o supporti efficaci;
- SMA20/50, d*dist, d*slope lag4, d*pos, incrocio osservato;
- volume relativo alla mediana20 precedente e valore base, nessun gruppo di volume ottimizzato;
- At e At/Ct; L/At, distanza direzionale residua a P1/At e al Rext/At;
- Fibonacci **effettivo dell'osservatore a t**, versione/ancore/u/r/livelli e distanze, verso delle ancore concorde/opposto al movimento studiato. Le ancore correnti possono essere diverse da quelle del contesto attivo: mostrarlo, non riscriverle per farle coincidere. Profondità del movimento e r Fibonacci non sono sinonimi se ancore diverse.

**Unica rappresentazione di confronto fissata:** quattro profili congiunti usando struttura45m, ordine SMA20/50 e pendenza SMA20 già definiti. CONCORDANT se struttura nel verso d e d*(SMA20−SMA50)>0 e d*slope>0; OPPOSITE se struttura opposta e entrambe le altre quantità<0; DISCORDANT ogni altra combinazione pienamente disponibile, inclusi MIXED e zeri; UNAVAILABLE se uno dei tre input manca. Sono contesti descrittivi, non punteggi, classificatore predittivo o regole operative.

Leggere **il profilo completo delle sei famiglie insieme** entro questi quattro contesti, per ciascun verso. Livelli, volume, volatilità e Fibonacci restano coordinate continue/categoriali del medesimo record e della medesima tabella, non quattro rassegne separate, filtri impliciti o altre coppie/triple da esplorare. Per ciascun contesto mostrare anche distribuzioni delle coordinate, disponibilità e pochi esempi completi; non dedurre una combinazione dalla sola differenza delle mediane marginali. Nessun sottogruppo aggiuntivo per livello, ratio Fibonacci, volume o giornaliero. Nessuna regressione, clustering, fitting o scansione soglie.

## 4. Unico seguito 24h, senza operazioni economiche
Orizzonte H=32barre45m=1440minuti. Motivo: ciclo di un giorno a scala45m, già consultabile con il seguito24h nell'app; non scelto per esiti o durate di CAND. Unico riferimento Ct a t e normalizzatore At=A45m(t) congelato, non R0 o rischio di un trade. Nessuna fill/fee/funding/saldo né t+60s.

Futuro esattamente minuti negoziati [t,t+H): variazione finale d*(Cend−Ct)/At, massimo avanzamento favorevole e massimo movimento contrario non negativi usando high/low1m e origine0. Registrare istanti/minuti dei primi estremi, senza attribuire un prezzo eseguibile al massimo. Definizioni LONG: favorevole=max(0,maxHigh−Ct)/At, contrario=max(0,Ct−minLow)/At; SHORT simmetriche.

Per descrivere **ordine e mancata risoluzione**, un solo riferimento simmetrico ±At dal Ct, registrato ora: una unità della volatilità già definita, non un target/stop né la barriera2A dei vecchi studi. È un adattamento descrittivo nostro, non successo operativo. Registrare primo contatto favorevole F e contrario A, a risoluzione1m, e una delle sei classi F_ONLY, A_ONLY, F_BEFORE_A, A_BEFORE_F, BOTH_UNORDERED, NEITHER. Non basta un F_ONLY a chiamare il caso prosecuzione stabile: leggere insieme variazione finale ed escursioni. Nessun altro livello/orizzonte provato.

Se entrambi i primi contatti sono nello stesso minuto: se l'open è già sul/oltre uno dei due riferimenti, quello è noto prima dell'altro, altrimenti BOTH_UNORDERED; non presumere ordine stop-first. Timestamp di open esatto, contatto intraminuto come intervallo [u,u+60s), non secondo inventato. Uguaglianza è contatto. Le distribuzioni comprendono questi casi con classe propria, mai scelta favorevole.

Fine DEV senza H completo: RIGHT_CENSORED, non usare2025. Minuto mancante/invalido: GAP, non inventare prezzi. At mancante/zero: MISSING_A/ZERO_A. Tutte le origini restano; esiti completi e classe aH null se orizzonte/input/normalizzatore incompleti. Conservare separatamente eventuale prefisso noto fino a prima lacuna/fine, con contatti già noti e copertura, senza presentarlo come esito completo. NEITHER è finestra completa senza contatti, non costo/dato mancante; BOTH_UNORDERED è ordine non ricostruibile, non esclusione.

## 5. Tabelle complete, senza ricerca di gruppi
Un report docs/research/OBS-002-results.md con riferimento alla preregistrazione config/task e licenza/provenienza dei derivati. Raw e output estesi fuoriGit. Registro completo di contesti/versioni/tentativi con snapshot ed esiti separati, non solo esempi.

Riconciliare flusso: versioni per motivo, gruppi, senza tentativi, prime origini DEV, ripetizioni, origini per verso, esclusioni qualitative e mancanze per motivo. Somme di tutti i profili/esiti/missing devono ricostruire la popolazione. Dichiarare gruppi distinti, numero tentativi per gruppo e sovrapposizione degli intervalli24h: niente numerosità trattate come prove indipendenti.

Tabella principale: entro LONG e SHORT, quattro profili congiunti §3. Per ciascuno n tentativi/n gruppi, complete/missing e classi di contatto §4; final/favorevole/contrario P10/P50/P90 (metodo lineare h=(n−1)q); profilo simultaneo di livelli, SMA, volume, A/C e Fibonacci con disponibilità. Schema tabella unico, nessuna graduatoria dei migliori indicatori o scelta di cut-off. Nessuna significatività o attribuzione causale. Non dichiarare utile un elemento da una sola media; non escluderlo perché compare in casi contrari.

DEV,2023,2024 e mesi: copertura, numerosità, classi ed esiti del medesimo disegno; nessun mese scelto. Mese dell'origine; gruppi possono attraversare mesi, i distinti per mese non si sommano. Popolazione principale ordinal1 separata da riepilogo secondario di tutti i tentativi dipendenti (stesse misure, non un nuovo studio); casi n=0 e distribuzioni non calcolabili espliciti. Non cambiare profili o orizzonte se gruppi piccoli o conclusioni poco leggibili.

## 6. Pochi percorsi, scelta fissata prima dell'estrazione
Sulla popolazione principale: primo cronologico per ciascun verso/profilo (massimo8); inoltre primo CONCORDANT con final<=0 e primo OPPOSITE con final>0 complessivi (categorie retrospettive dichiarate, esiti completi); primo RIGHT_CENSORED; primo tentativo ripetuto ordinal>1; primo BOTH_UNORDERED completo. Massimo13, deduplicazione per attemptId con categorie conservate. Ordinamento t poi attemptId. Categoria vuota dichiarata, nessuna sostituzione con un caso bello. Pubblicare regola prima degli esiti, elenco/ID/hash effettivi dopo estrazione, senza fingere selezione per esito ex ante.

Timeline con dati disponibili a t e seguito separato; casi contrari espliciti, non solo riusciti. Non chiedere a Gian di cercare centinaia di date, verificare pivot o formule.

**Consultazione con strumenti esistenti:** usare l'ambiente Studio storico, grafico45m/1D, osservazioni e seguito24h già costruiti. Esportare supporto visuale con prezzi/snapshot reali per i casi e tempi precisi. Nessuna call/operazione CAND fittizia, nessun ordine/saldo mescolato. Se il formato OBS-001 impone tabelle della vecchia domanda, non fabbricarle per riempirlo: ammesso il solo adattamento tecnico del lettore/metadata per un pacchetto osservativo di consultazione OBS-002 e per disabilitare la vecchia tabulazione non pertinente con spiegazione. Riutilizzare componenti e selettore temporale esistenti, niente nuovo ambiente/esploratore, filtri, motore UI o pagina di confronto. I risultati dello studio restano nel report. Il pacchetto si identifica come OBS-002, non come originale OBS-001 o backtest CAND. I file OBS-001 precedenti continuano ad aprirsi.

Scegliere il contenitore proporzionato (un bundle o pacchetti per casi) e documentare l'apertura più semplice. Test import/compatibilità e una prova visiva sui casi reali solo se il lettore cambia; nessun restyling. Il riepilogo originale OBS non viene ricalcolato come analisi collaterale.

## 7. Sequenza e controlli
1. Trascrizione eseguibile delle convenzioni di questo task/config, codice e pochi test sintetici; pubblicare prima di estrarre esiti reali OBS-002. Config e gruppi immutabili dopo gli esiti, salvo bug documentato con confronto d'impatto.
2. Calcolo causale delle osservazioni sugli input esistenti e costruzione della popolazione/snapshot, senza usare esiti per includere righe. Conservare hash di identità/config/popolazione prima del passaggio agli esiti.
3. Seguito24h e tabelle prefissate, elenco esempi deterministico e supporto di consultazione. Una estrazione reale ripetibile; seconda verifica hash output deterministici senza eseguire CAND. Provenienza/commit/orari separati dagli output numerici se impediscono riproducibilità.
4. Report e consegna, poi review/interpretazione Director; niente ipotesi implementata da Claude.

Controlli discriminanti: simmetria LONG/SHORT; pivots disponibili a t, trigger a t0 non retroattivo; arretramento e riarmo, REPLACE stesso gruppo e nuovo P0, coesistenza dei due versi, reset/lacuna, ordinale nell'inizializzazione; assenza del guard CAND e inclusione di casi struttura opposta/profondità>3/4/rapporto basso; dati futuri alterati non cambiano popolazione o snapshot fino al cutoff; ultimo minuto incluso e primo escluso nell'H24; contatti stesso minuto con/senza open che ordina, NEITHER, censura, missingA/zeroA; conteggi/gruppi riconciliati e categorie vuote; eventuale reader compatibile. Nessuna suite generale/CI per abitudine, nessun backtest economico per il collaudo del viewer.

Non aggiungere nuovi requisiti di inclusione per agevolare il codice. Se un vincolo necessario non è definito qui, completare i passi indipendenti e segnalare il punto esatto al Director, non scegliere silenziosamente un gruppo. Bug correggibili autonomamente, con provenienza e impatto; nessun aggiustamento per migliorare il risultato.

## 8. Consegna e chiusura
Commit/push main pertinenti autorizzati; niente forcepush/pull/fetch o chiusura processi altrui. Aggiornare STATE e spazio consegna, passare DELIVERED. Report distinguendo implementato, evidenza e limiti; comando riproducibile, hash completi e percorso output fuoriGit. Non incollare il registro completo in chat.

Il Director sceglierà al massimo una ipotesi concreta «in questa situazione, questa combinazione potrebbe motivare attesa/ingresso/rinuncia», con spiegazione, svantaggi/controesempi e verifica futura necessaria; oppure nessuna distinzione interpretabile, specificando cosa non è riconoscibile. Non è sufficiente ripetere saldi o scegliere il profilo col seguito migliore. Una scoperta esplorativa non è evidenza di efficacia o v2: nessuna sua implementazione senza decisione successiva Astra. Chiusura ad Astra al termine, senza nuova autorizzazione ordinaria per estrazione, viewer pertinente o review.

## Spazio dell'esecutore
**Avanzamento 1 — convenzioni eseguibili e test pubblicati prima di ogni esito reale.** Checkout verificato su `6f1743d` senza pull/fetch. Pacchetto `src/obs002/` (config, dati con mesi espliciti 2022-10…2024-12 verificati sul manifest CAND-001, popolazione causale e snapshot, seguito 24h, tabelle, esempi, pacchetti di consultazione) e 15 test sintetici in `tests/test_obs002.py`. Nessun dato reale OBS-002 ancora elaborato.

**Consegna OBS-002 — Claude Code, 17 ottobre 2026.** Commit:
- `36f6153`: convenzioni eseguibili e 15 test sintetici, prima di ogni dato reale;
- `118f706`: hash di popolazione e identità registrati prima degli esiti;
- `7cad393`: riscontro con il seguito OBS-001, tabelle e lettore dei casi;
- commit di questa consegna: report, schermate, stato.

File:
- nuovi: `src/obs002/*`, `tests/obs002_helpers.py`, `tests/test_obs002.py`, `docs/research/OBS-002-results.md`, `docs/research/OBS-002-screens/`, fixture sintetica e `Obs002Case.test.tsx`;
- modificati, adattamento tecnico del lettore storico: `dashboard/src/contract/historical.ts`, `historical/loadBundle.ts`, `historical/study.ts`, `ui/historical/{HistHeader,HistoricalEnvironment,OpenStudy,OutcomeCard,StudySummaryView}.tsx`;
- CAND-001, osservatore OBS-001 e config invariati.

Comportamento:
- `python3.12 -m obs002 population` poi `outcomes` sui soli 27 ZIP 2022-10…2024-12 verificati;
- popolazione causale con 4.372 primi tentativi DEV e 2.210 ripetuti dipendenti;
- tabella unica verso × profilo, periodi e mesi, 10 esempi (vuote solo le 2 categorie UNAVAILABLE);
- un pacchetto di consultazione per caso, aperto dallo Studio storico.

Output in `C:/Projects/algorithmic-trader-data/OBS-002/runs/OBS-002-v1.0.0-e1.0.0-3b76888642-b11bad4557/`.

Controlli effettivi:
- hash della popolazione riverificato prima degli esiti;
- riconciliazioni di tutte le partizioni;
- riscontro di tutti i 6.582 esiti con il seguito OBS-001 esistente;
- due esecuzioni con output identici byte per byte, l'ultima da commit pulito;
- 15 test Python, 24 test del lettore (4 nuovi), typecheck e build;
- prova visiva su 2 pacchetti reali. Nessuna suite generale o CI.

Limiti: elenco in report §8; punti tecnici da confermare in §7. Da sapere per leggere la popolazione: circa il 40% dei primi tentativi ha un arretramento oltre P0, conseguenza della coesistenza dei versi preregistrata. Nessuna ipotesi decisionale formulata o implementata.
