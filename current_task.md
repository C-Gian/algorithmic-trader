# APP-001/R1 — Completezza, progresso, ritorno e costi iniziali

**Stato: DELIVERED** (Claude Code, 17 ottobre 2026; in attesa di review Director, non accettato). Incarico del Director, 17 ottobre 2026. Esecutore: Claude Code.
Base: **11e028407261907a0206f2b484f0445f8c712ea0** più il commit di questo incarico; checkout sincronizzato daGian. Nessun pull/fetch, neppure dry-run.

La macrofase APP-001 resta aperta e autorizzata interamente daAstra. Requisiti e disegno originari conservati nella storia di current_task.md al commit7f94d4e; consegna a11e0284 e docs/research/APP-001-delivery.md. R1 corregge difetti nel perimetro già assegnato, non apre una nuova macrofase.
Leggere AGENTS.md, STATE.md, sezioni pertinenti di PRODUCT-CONTEXT.md e questo incarico. CAND-001/v1,config aed2c4ef627617d73972778097bbab5fb702ab5064ce9e6eb68ded2170ce4edf, regole/gestione/costi e finestre rimangono invariati. Nessun download o2026,nessuna nuova strategia,servizio generale o restyling.

## 1. Review Director su11e0284 — correzioni richieste, non ACCEPTED

Verifiche indipendenti in copia isolata:
- lettura servizio/lock/job,percorso comune,catalogo,launcher,router e viste pertinenti;
- **18test servizio,45test CAND,30test OBS passati**: diff tocca percorso comune e callback nei loro moduli, motivo della selezione;
- **38test UI** (backtest e router),typecheck/build passati;
- esaminate immagini dell'esecutore «Nuovo backtest» e «Dettaglio seguito» a1366px;
- riprodotti in più i difetti R1-A/B/C sotto, con dati sintetici e UI controllata. R1-D riscontrato nel codice e nell'immagine della prima pagina.

Non svolti dal Director in questa review: nuovo backtest reale, confronto autonomo byte-per-byteUI/CLI sui datiOwner, browser autonomoWindows. L'equivalenza gennaioUI/diretto,3trade−18,68 e i tempi di annullamento reali restano evidenza dell'esecutore, non verifica indipendente Director. Nessuna prova positivaOwner diAPP-001 ancora registrata.

Il lavoro principale esiste: orchestration locale, profili fissi, stato/progresso e navigazione sono stati implementati. Non rifarlo; correggere i punti precisi sotto. I test verdi non coprono ancora tali casi.

Deviazioni/limiti della consegna:
- ricalcoloDEV involontario per tentare annullamento annotato come collaudo extra, non evidenza nuova o modifica metodologica. Non ripeterlo;
- annullamento durante simulazione provato sinteticamente ma non sul mercato reale perché fase troppo rapida: limite accettabile se dichiarato, non richiede un altro fullrun;
- suite frontend completa motivata dal router trasversale, non una nuova regola per ogni patch;
- job di prova reali già salvati restano; nessuna pulizia automatica o rimozione per “abbellire” il catalogo;
- provenienza mancante dei primi run dichiarata; successivo fix non rende retroattivamente completo il manifest vecchio.

## 2. R1-A — costo pertinente mancante, risultato non completo

**Riproduzione indipendente sul percorso reale del servizio**, usando archivi sintetici coerenti di app001_helpers, nessun prezzo reale:
1. un primo run individua un trade con durata>1minuto;
2. serie funding sintetica regolare8h posizionata in modo che un evento cada durante il trade; controllo della serie certificato;
3. si elimina soltanto il minuto mark precedente quell'evento e si aggiornano correttamente ZIP/hash/manifest sintetici;
4. avvio da JobManager con pipeline reale: almeno un trade ha net=None e il netto complessivo èNone, come dovuto;
5. **job.state=COMPLETED, job.result.complete=True e Catalog.complete=True**.

Causa: pipeline usa solo reconciliation.windowComplete, che segnala il percorso dei prezzi, non l'esistenza di tutti i costi/netto. LaUI JobPage lo traduce in “completato · risultato completo”.

Comportamento richiesto:
- distinguere **copertura del percorso dei prezzi** da **completezza economica** del risultato. Non cambiare i prezzi,il funding o il netto per rendere vero un flag;
- se manca un costo pertinente al netto baseline, il risultato pubblicato è INCOMPLETE con motivo concreto, nonCOMPLETED. Conservare le operazioni, i componenti noti e i valori mancanti;
- propagare la distinzione in output del percorso comune,manifest,job,catalogo e viste(saved/job/risultati). LaUI può dire “Storico elaborato, ma risultato dopo i costi non calcolabile: manca…”; non attribuire necessariamente una lacuna ai prezzi quando manca soltanto un costo;
- preservare significato delle riconciliazioni/flag di copertura già esistenti; aggiungere la qualificazione economica dove serve, senza presentare la parte nota come un totale;
- gestire anche vecchi risultati supportati/2 e/3 con windowComplete=True ma nettoNone, conservando compatibilità e dichiarando la completezza economica mancante senza inventare la causa se non documentata;
- zero operazioni con dati validi e netto0 resta un risultato completo: zero non è un costo mancante;
- un mark mancante non pertinente a nessuna posizione non deve bloccare o rendere parziale un risultato valido. Nessuna forzatura indiscriminata su tutti i mark mancanti.

Verifica mirata: file sintetici con evento regolare durante una posizione e singolo mark mancante→pipeline/job/catalogo/UI incompleti; caso valido e zero-trade completi; regressione funding non certificato ancora blocca prima del ledger. Nuovo test che fallisca su11e0284, non soltanto un runner finto che restituisce complete=False.

## 3. R1-B — progresso dopo HALT non è lavoro valutato

Riproduzione indipendente con stesso esempio sintetico di CAND/R1:
- trend_store daT0−10giorni aT0+20giorni,seme7; finestra(T0,T0+20giorni);
- si toglie il minuto5minuti dopo l'ingresso della prima operazione;
- HALT corretto a1673190360000,riepilogo **245chiusure valutate/395non valutate**;
- tick finale di run_window invece **t=1674259200000, closes=640,closesTotal=640**,pur conservando haltedAt.

JobPage chiama closes “chiusure45m valutate” e mostra data raggiunta a fine finestra. Quindi il progresso contraddice il riepilogo e accredita lavoro dopo la lacuna.

Comportamento richiesto:
- dopoHALT, avanzamento del periodo realmente valutato fermo al punto effettivo,contatori di valutazione e data coerenti col riepilogo;
- se il programma percorre tempi successivi per registrare NOT_EVALUATED_AFTER_GAP, non contarli come valutati: eventuale scansione amministrativa ha nome separato, oppure nessun contatore aggiuntivo;
- evento finale e snapshotpersistito deljob non promuovono la copertura al100% del periodo. Fine del processo di riepilogo non equivale a fine della valutazione storica;
- UI espone l'interruzione e la copertura effettiva, non solo un piccolo avviso accanto a640/640;
- preservare decisioni,registrazioni NOT_EVALUATED e risultati del motore: correggere osservabilità,non metodo.

Test: evento/progresso finale del motore e job su dati sintetici congap coincidono con i conteggi del report; UI con snapshotreale/fixture derivata mostra245e395,non640valutate. Caso completo invariato. Non serve nuovo runDEV.

## 4. R1-C — ritorno interno conserva il posto nel registro

Riproduzione indipendente UI:
- aprire registro di un risultato salvato,scorrere a640px;
- aprire dettaglio di una riga;
- premere **“← Torna alle operazioni”**;
- torna il registro,ma window.scrollTo riceve0 invece del precedente640.
Il test esistente copre Indietro/Avanti del browser,non il ritorno interno. Link chiama navigate come nuova navigazione e perde lo scroll salvato.

Comportamento richiesto:
- il ritorno interno al registro recupera la posizione precedente,come il browserIndietro; conservare eventuali filtri/ordinamento esistenti;
- risolvere come comportamento comune del router/link di ritorno,non con timeout o numeri fissi nella singola pagina. Non fare ogni navigazione un ripristino: aprire una pagina nuova può partire dall'alto;
- “Torna ai risultati” dalla scorciatoia segue lo stesso principio ove un contesto esiste;
- link aperto direttamente senza provenienza rimane utilizzabile con ritorno ragionevole. Indietro/Avanti e URL non regrediscono; nessun salto al risultato sbagliato.

TestUI del vero clic sul ritorno interno e confronto640→dettaglio→640,più precedente regressioneBrowserBack. Nessuna nuova infrastruttura di navigazione o filtri appositi.

## 5. R1-D — riga costi della schermata iniziale ancora opaca

Nella scheda “Nuovo backtest”,rigaCosti,si legge ancora in primo piano:
“commissioni5bp e prezzo di esecuzione3bp per lato … scenario a parte con10+10bp”
senza un aiuto associato. Anche “prezzi mark” compare fra dati richiesti senza spiegazione. Riscontrato nel codice NewBacktestPage e screenshotapp-01.

È il gergo esatto segnalato dall'Owner e contrario alla specificaAPP-001§7. Non rinviare al futuro la comprensione della pagina da cui deve avviare autonomamente il test.

Correzione editoriale circoscritta:
- nomi semplici,ipotesi esposte senza richiedere conoscenza dibp; valore percentuale comprensibile o dettaglio espandibile con spiegazione;
- aiuto “i” al costo/scostamento e ai “prezzi mark” (prezzo di riferimento del contratto usato per i pagamenti periodici),riusando il componente già costruito;
- spiegare che le commissioni si applicano sia all'apertura sia alla chiusura; lo scostamento è già incluso nei prezzi usati,non da sottrarre ancora;
- scenario con costi più alti secondario,non parametri da impostare;
- valori identici:5bp=0,05%,3bp=0,03%; nessuna modifica economica. Esempi inUSDT solo qualificati come esempi sulla dimensione1000,non costi esatti di tutte le uscite;
- tooltip da clic/tastiera oltrehover,come già richiesto. Niente restyling del resto della dashboard.

Un controllo UI pertinente per presenza della spiegazione accessibile è sufficiente; non rilanciare lo storico per testi.

## 6. Verifiche e consegna

Prima riprodurre su11e0284,poi verificare le correzioni. Controlli mirati nei moduli toccati,più regressioni servizio/UI pertinenti e typecheck/build. Niente suite generale per abitudine; non ripetere CAND/OBS interi se il diff non li richiede.
Il confronto reale gennaioUI/diretto già documentato è riutilizzabile per regole immutate. **Nessun nuovo download e nessun nuovo fullrunDEV/2025.** Se un cambiamento al percorso numerico impone un controllo reale ulteriore,documentare il motivo e limitarsi al profilo breve; non farlo per una nuova etichetta o flag.

Conservare i dati/risultati precedenti. Schema e versioni: patch pertinente dichiarata,compatibilità/2 e/3; nessun bisogno di una nuova migrazione solo per qualificare completezza. Config candidato/parametri invariati.
Aggiornare APP-001-delivery.md con sezione R1,impatto numerico e controlli effettivi; immagini delle viste realmente cambiate solo dove servono. Per i casi sintetici indicarlo esplicitamente,non mostrarli come risultato reale.
Aggiornare STATE e spazio consegna di questo task,passareDELIVERED,maiACCEPTED. Commit/push su main pertinenti autorizzati,no forcepush,pull/fetch,reset/stash o datiGit. Nessuna pulizia dei jobOwner o chiusura processi estranei.

La macrofase continua fino a percorso usabile: reviewDirector,poi prova concretaGian suNuovo→Avvia→progresso→registro→spiegazioni→ritorno→risultati salvati. Non registrare tale prova prima che avvenga. AdAstra solo conclusione o conflitto sostanziale;non serve una nuova autorizzazione ordinaria.

## Spazio dell'esecutore

Consegna Claude Code, 17 ottobre 2026. Il dettaglio è in [docs/research/APP-001-delivery.md §6](docs/research/APP-001-delivery.md).

**Commit:** 3dd3f66 per le correzioni e i test, più un commit di documentazione. Motore 1.0.3 e schema /3 invariati; servizio 1.0.1.

**Riproduzioni prima della correzione** (ogni nuovo test è stato eseguito anche sul codice 11e0284, dove fallisce):
- **R1-A**, archivi sintetici: mark mancante sotto un pagamento durante la posizione → COMPLETED e catalogo completo.
- **R1-B**, esempio CAND/R1: ultimo tick 640/640 contro 245/395 del riepilogo.
- **R1-C**: «Torna alle operazioni» → `scrollTo(0)` invece di 640.
- **R1-D**: «bp» e «prezzi mark» senza spiegazione.

**Correzioni:**
- **R1-A**: completezza economica distinta dalla copertura dei prezzi, con motivo, in pipeline, manifest, job, catalogo e viste. Nessun valore cambiato. I vecchi /2 e /3 con netto mancante non risultano completi; la causa, se non registrata, è dichiarata tale.
- **R1-B**: il progresso si ferma all'HALT (chiusure valutate, non valutate, data) e la pagina del job mostra l'interruzione.
- **R1-C**: navigazione `return` del router per i ritorni interni.
- **R1-D**: costi in percentuali semplici con «i» per commissione, prezzo di esecuzione, pagamenti periodici e prezzi mark; scenario con costi più alti solo come confronto.
- Difetto extra: il servizio legge il corpo delle POST prima di rifiutarle, correggendo un fallimento intermittente su Windows.

**Controlli:**
- servizio: 24 test, 5 volte OK;
- CAND backtest/R1: 12 test OK;
- UI: 79 test OK;
- typecheck e build OK.

**Impatto numerico nullo.** Il profilo breve rieseguito da comando diretto dà lo stesso bundle `982ad3a6…` con `economic.complete=true`; i risultati reali nel catalogo restano completi con gli stessi netti. Nessun download e nessun ricalcolo DEV o 2025.

**Immagini:** app-01 aggiornata e app-12 (spiegazione della commissione).

**Limiti:**
- R1-A e R1-B sono verificati solo su dati sintetici;
- l'annullamento durante la simulazione resta solo sintetico;
- i manifest già salvati non vengono riscritti.

Prova Owner non svolta né dichiarata.
