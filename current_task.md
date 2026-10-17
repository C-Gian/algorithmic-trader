# APP-001 — Backtest autonomo locale, comprensione e navigazione

**Stato: READY.** Director, 17 ottobre 2026. Esecutore: Claude Code.
Base: **ebd48027ce9828fbb80eddc478036b5d1ceed930**, più il commit di questo incarico. Gian sincronizza il checkout; nessun pull/fetch dell'esecutore, neppure dry-run.

## 1. Mandato e stato precedente

Astra autorizza l'intera macrofase: Gian deve aprire l'app, avviare personalmente un backtest consentito, seguirne avanzamento reale e annullamento, riaprire i risultati, trovare tutte le operazioni e capire decisioni/esiti/costi. Director gestisce specifica, incarichi, review e correzioni ordinarie; Claude completa il percorso senza fermarsi a un motore sintetico o a un prototipo.

Leggere AGENTS.md, STATE.md, PRODUCT-CONTEXT.md §§13–15,24–27,31 e **questo incarico completo**. Per le regole usare CAND-001-v1.md e config/CAND-001-v1.json; non riaprire tutto l'archivio.

Stato CAND-001 da mantenere distinto:
- implementazione accettata tecnicamente a4ff5046, review b9f54cc e limiti dichiarati;
- uso Owner: base apprezzata, comprensione/autonomia insufficienti, feedback ebd4802;
- candidato1.0.0 negativo in DEV e2025, **non promosso** all'operatività;
- efficacia generale della famiglia non risolta.
APP-001 non corregge la strategia. Config SHA256 canonico **aed2c4ef627617d73972778097bbab5fb702ab5064ce9e6eb68ded2170ce4edf**, osservazioni, segnali, gestione, precedenze e costi invariati. Nessuna scelta di parametri sugli esiti dei collaudi. Vecchi studi INACTIVE,2026protetto.

## 2. Architettura scelta dal Director

Conservare l'unico frontend React/TypeScript e il motore Python esistenti. Aggiungere **un piccolo servizio Python locale con libreria standard**, HTTP su127.0.0.1:8765, e un solo worker di calcolo in background nello stesso processo (thread dedicato). Non creare un backend generale, DB, code di job, account, hosting, cloud o streaming exchange.
Il frontend interroga il servizio tramite /api e proxy Vite; anche Vite resta su127.0.0.1:5173. Porta occupata: errore leggibile, nessuna terminazione automatica del processo che la usa.

**Un solo comando per l'avvio normale:** npm run dev dalla cartella dashboard avvia servizio e Vite tramite piccolo launcher Node senza nuove dipendenze se non necessarie. Individuare Python3.12 già usato sul PC (override opzionale di percorso all'avvio documentato). Se Python/dati mancano: messaggio concreto e istruzione breve; non installazioni/download automatici. Il terminale può rimanere aperto, ma Gian non deve usarlo per avviare o seguire il singolo backtest. README con un percorso Windows reale, niente script manuali multipli. Fermare il launcher deve arrestare i propri processi, mai un vite o Python dell'Owner.

Il servizio chiama **lo stesso percorso applicativo** usato dal comando diretto: caricamento/verifica→aggregati/osservazioni→run_window→summary/bundle/salvataggio. Il browser non calcola segnali né conti; non simulare avanzamento con timer. Non usare acquire/all né http_get nel percorso UI. Nessuna accettazione di comandi shell, argomenti arbitrari o percorsi di filesystem ricevuti dal browser. Solo ID di profili/job/risultati registrati sotto la cartella dati configurata. Modifiche HTTP accettate solo dal frontend locale previsto (controllo Host/Origin; nessun CORS permissivo). Sono confini del servizio locale, non login o nuove schermate di sicurezza.

Cartella dati predefinita: C:\Projects\algorithmic-trader-data\CAND-001 con riuso della sorella OBS-001. Configurazione di percorso eventuale solo locale all'avvio. Stato delle esecuzioni e piccoli manifest in una sottocartella jobs/ fuoriGit; artefatti deterministici restano nei runs/ esistenti. Identificativo di una **esecuzione** distinto da quello del **risultato**: due ricalcoli identici possono riferirsi allo stesso bundle senza perdere data/stato/provenienza di ciascun avvio. Date/UUID/progresso non entrano nel contenuto deterministico del bundle.

Se una scelta tecnica reversibile è necessaria, risolverla autonomamente e documentarla. Escalare soltanto un impedimento sostanziale, non chiedere altra autorizzazione ordinaria.

## 3. Profili consentiti e dati offline

Nessun editor di strategia, selettore libero di date o parametri economici. Tre profili fissi, presentati con nomi comprensibili:
1. **Prova di gennaio2025** — ID APP_CHECK_2025_01, valutazione[2025-01-01,2025-02-01)UTC. Profilo di collaudo del prodotto, non nuovo studio o sottogruppo scelto per redditività.
2. **Sviluppo2023–2024** — finestra DEV registrata[2023-01-01,2025-01-01).
3. **Confronto2025** — ADDITIONAL_2025[2025-01-01,2026-01-01), già esposto, non validazione indipendente.

Sempre stesso candidato1.0.0, baseline5bp fee/3bp slippage per lato e stress registrato separato, funding storico con mark1mproxy, N0=1000USDT, nessuna leva/reinvestimento. Tutte le finestre iniziano FLAT senza episodio/ordine ereditato, ma osservazioni con **prefisso dal2022-10-01**; ultima apertura e chiusura forzata come protocollo. Il profilo di collaudo richiede solo dati fino a fine gennaio2025: non leggere il resto del2025 per completarlo. Non modificare il JSON candidato per aggiungere un profilo applicativo: registro di profili separato e versionato nel codice/config dell'app. Adeguare il contratto di esecuzione/bundle/validatore alla distinta identità del profilo di collaudo: gennaio non va etichettato come l'intero confronto2025. Conservare compatibilità con i risultati schema/2 già consegnati, inferendo il vecchio profilo dalla fase/finestra quando non è registrato esplicitamente; non inventare una data d'avvio o job storico.

Usare esclusivamente file già verificati, manifest e checksum registrati. Riusare OBS dove previsto; nessun ricontrollo online o download implicito. API rifiuta profili non previsti, alterazioni di periodo/strategia e qualsiasi2026 anche se il frontend viene aggirato. Mancante/corrotto/non certificabile: fermarsi con errore leggibile e rapporto qualità, non acquisire o inventare. Policy R1 funding/HALT/null invariate.

Prima dell'avvio laUI espone profilo, periodo UTC, candidato/versione, dimensione convenzionale e dati richiesti; non confondere prefisso osservativo e periodo con operazioni. L'avvio parte da un clic esplicito diGian. Un risultato già presente non sostituisce di nascosto un nuovo calcolo: “Apri risultato” e “Avvia” sono azioni diverse.

## 4. Contratto del processo e concorrenza

Una gestione piccola con snapshot dello stato su disco e API locale è sufficiente. Interfaccia indicativa:
- GET profili/disponibilità, elenco esecuzioni e risultati, stato del singolojob;
- POST avvio con profileId e chiave univoca della richiesta;
- POST annullamento del job;
- GET bundle e manifest del risultato noto.
Percorsi/nome endpoint sono dettagli tecnici. Non usare GET per avviare/annullare. Risposte di errore distinguono servizio assente, risorsa non disponibile, dati mancanti e conflitto con esecuzione attiva.

Regole:
- massimo **un worker reale**; niente coda. Controllo atomico lato servizio, non soltanto pulsante disabilitato. Due tab/clic simultanei non lanciano due calcoli;
- ripetere la medesima chiave d'avvio (retry dopo risposta persa) restituisce lo stessojob, anche dopo che è terminato. Un nuovo ricalcolo richiede un nuovo avvio esplicito;
- se esiste un altrojob attivo, restituirlo con messaggio/link “C'è già un backtest in corso”, senza crearne uno;
- prenotare e registrare iljob prima di eseguirlo; stato coerente anche se l'avvio fallisce;
- chiusura tab/ricaricamento/interruzione della connessione HTTP non annullano il worker. La pagina ritrova stato e risultati dal servizio;
- all'arresto/riavvio del servizio, i job non conclusi non diventano completi. Contrassegnarli interrotti con causa. Non serve ripresa del calcolo dal punto raggiunto; l'eventuale rilancio è un nuovojob esplicito;
- garantire con un controllo minimo di istanza/lock compatibile Windows che non convivano due servizi/worker sulla stessa cartella dati, anche durante arresto/riavvio. Nessuna uccisione di processi estranei o basata sul solo nome;
- errore o dati incompleti lasciano diagnostica e fatti noti; mai eliminare raw, run precedenti o risultati validi.

Stati riconoscibili: preparazione/in corso, annullamento richiesto, completato con risultato completo, terminato con risultato incompleto, annullato, interrotto, errore. Usare macchina a stati esplicita con un solo esito terminale perjob. Un run con UNRESOLVED_DATA_GAP non è “completo” solo perché il worker ha finito; i valori mancanti e il motivo restano evidenti.

**Annullamento cooperativo:** pulsante “Annulla backtest”, nessuna chiusura scheda come surrogato. Passare segnale di annullamento ai loop di parsing/calcolo/salvataggio, con controlli abbastanza frequenti da terminare normalmente entro5secondi sul PC dopo la richiesta. Nessuna attesa di tutto il mese/anno se un loop è lungo. Prima “Annullamento richiesto”, poi esito effettivo; non fingere cancellato mentre continua. È accettabile spiegare un limite misurato di una breve operazione indivisibile, non rinviare indefinitamente.
Corsa con completamento: se il risultato completo è già stato pubblicato, annullamento troppo tardi restituisce quello stato; non cancellarlo. Risultati/parziali in scrittura non devono comparire come validi: staging e pubblicazione atomica. Conservare manifest/stato/progresso di un annullato; non occorre costruire un bundle parziale economicamente valutato per ogni annullamento. LaUI non gli attribuisce netto finale o percentuale100%.

## 5. Avanzamento veritiero

Aggiungere callback/eventi opzionali, separati dal dato osservativo/decisionale, ai punti effettivi del percorso comune. In assenza di callback, comportamento diretto invariato.
Fasi:
- controllo file, checksum e copertura: tipo/file o mesi controllati/attesi;
- inizializzazione: aggregati e osservazioni sul prefisso, scala e quantità realmente elaborate;
- simulazione: dataUTC raggiunta, chiusure45m valutate/attese, tentativi d'ingresso, operazioni concluse ed eventuale posizione aperta fino a quel punto;
- riepilogo e salvataggio;
- esito finale o blocco/errore.

Distingui il prefisso dalle operazioni simulate. Conteggi non ancora disponibili sono “non ancora calcolati”, non zero derivato dal risultato finale. Non mostrare in anticipo totale trade/esiti del bundle già presente. I contatori derivano dallo stato corrente del motore, non da una distribuzione stimata delle78/29operazioni note.

Aggiornare snapshot al cambio fase e durante i loop, tipicamente ogni0,5–1secondo o per blocchi equivalenti; non ogni candela e non log illimitati. Può bastare polling dellaUI ogni circa1secondo finché iljob è attivo, poi fermarlo. Questo polling applicativo è richiesto dal prodotto e distinto dal pollingCI vietato. Conservare ultimo aggiornamento e tempo trascorso reali; se il servizio non risponde mostrare stato non aggiornato, senza presumere completamento/annullamento.
Percentuale solo se denominatore reale noto, riferita alla fase; per lavoro non quantificabile usare stato in corso con spiegazione. Niente ETA o percentuale globale inventati, sleep per rendere visibile la progressione, animazioni di candele o scanner artificiale. Una fase rapida può essere già conclusa; la cronologia sintetica deve mostrarlo.

## 6. Percorso UI principale e risultati salvati

L'ambiente si chiama chiaramente **Backtest** (eventuale vecchio nome come migrazione non doppio ambiente).
Ingresso normale:
- **Nuovo backtest**: i3profili, cosa sarà calcolato, disponibilità dati, Avvia;
- **Risultati salvati**: risultati precedenti riconosciuti dalla cartella runs e nuove esecuzioni, con profilo/periodo/versione/data/stato. Consultare non ricalcola;
- pagina deljob attivo con progresso e annullamento; al termine “Apri risultati”, senza aprire risultati finali prima che esistano;
- pagina risultati con **“Tutte le operazioni (n)”** ben visibile e accesso al registro; ogni riga apre il dettaglio;
- esempi sotto “Esempi dal registro”: primi cronologici e motivazione della selezione, categorie assenti dichiarate. Non sono l'intero risultato. Per2025 prima operazione e primo negativo coincidono: spiegarlo senza inventarne un altro.

Caricare vecchi run schema/2 DEV e2025 senza dover scegliere un JSON; catalogo derivato da cartelle/manifest, nessun DB. Scansione e lettura proporzionate, non ricaricare tutte le decine diMB a ogni tick. Non attribuire a un run preesistente una nuova esecuzione live. Cartella/run mancante o formato/manifest invalido: riga spiegata/non apribile, nessun crash o sostituzione silenziosa di un risultato valido. Vecchio schema/1 resta conservato e non supportato: dirlo, nessuna migrazione richiesta.
ImportJSON può restare in “Apri un file esterno” come opzione secondaria; i validatori e la protezioneR1 non si indeboliscono. Nessuna acquisizione automatica per riempire catalogo.
Risultati incompleti/interruzioni distinguibili dai completi, con periodo realmente coperto e fatti noti. Nessuna fixture mescolata al backtest reale.

## 7. Linguaggio: specifica semantica da applicare

Banner persistente nell'ambiente:
**“Simulazione su prezzi storici. Nessuna operazione reale.”**
Precisare il candidato di sviluppo non promosso, senza sommergere ogni titolo di “modellato”. Nessuna dicitura Binance demo connessa.

Nel dettaglio seguire la sequenza reale:
- “Il bot ha riconosciuto una salita/discesa…” e “Ha aspettato una reazione…”;
- “Ha deciso di tentare un acquisto/una vendita”: condizioni espresse con prezzo massimo/minimo, momento del tentativo e rischio/ragione. **Non è ancora entrato.** Per v1 tentativo unico all'apertura prevista, con controllo sul prezzo: non un ordine permanente in attesa che il mercato lo tocchi;
- richiesta rifiutata/annullata: “L'acquisto/la vendita non è stato/a eseguito/a: [motivo concreto]”, nessuna posizione o costo di esecuzione inventato;
- fill: “La posizione simulata è stata aperta a [prezzo]”; LONG significa puntare su una salita, SHORT su una discesa. Non raccontareSHORT come vendita diBTC posseduti;
- aggiornamento protezione: nuovo limite di protezione, prima/dopo, momento efficace e ragione; non “stop alzato” perSHORT se il prezzo scende;
- chiusura: “La posizione è stata chiusa perché…” con motivo vero: limite di perdita raggiunto, obiettivo raggiunto, cambiamento di direzione rilevato dalle regole, limite24ore, fine del periodo; irrisolto = esito non calcolabile, non chiusura;
- per contatto intraminuto, distinguere intervallo del contatto e orario contabile se consultati nei dettagli, non inventare istante esatto.

Prima si vedono le informazioni disponibili alla decisione; **“Mostra cosa è successo dopo”** rende esplicito il passaggio retrospettivo. Entrata/uscita/costi futuri non sono informazioni note prima. Restano linea temporale e scala45m/1D, con prezzo corrente/ultimo noto corretti secondoR1.

Riepilogo e scheda operazione:
- voce principale **“Risultato dopo i costi”**, unitàUSDT spiegata (“unità usata in questa simulazione; non euro”);
- **“Dimensione di ogni operazione:1000USDT”**, convenzione fissa, non capitale del conto né perdita massima. Rischio fino allo stop distinto; saldo personale inesistente;
- guadagno/perdita dal solo movimento dei prezzi, **effetto del prezzo di esecuzione**, **commissioni**, **pagamento periodico del contratto** (funding, anche ricevuto) riconciliati con il totale;
- spiegare “slippage”: differenza avversa assunta fra prezzo del grafico/riferimento e quello usato per eseguire. È già nei prezzi di ingresso/uscita: non sottrarlo di nuovo;
- commissioni sui due eseguiti; ordine non eseguito non paga fee; dato mancante resta mancante;
- scenario con costi più alti in sezione secondaria distinta: **stesse operazioni ricalcolate con costi più severi**, non un altro percorso né totale da sommare;
- bp,N0,PnL,formulaR0,profit factor e unità analoghe in dettagli espandibili e spiegati. Nessun “−40bp diN0” opaco nel riepilogo. Per un singolo trade1000USDT,−40bp corrisponde circa a−4USDT/−0,40% della dimensione convenzionale, non rendimento del conto; non estendere questa lettura a un capitale cumulato inesistente.

Icone “i” o controlli equivalenti con spiegazioni in italiano semplice, leggibili a hover, **clic e tastiera**, chiudibili senza perdere il contesto. I dettagli tecnici non sono eliminati o sostituiti da valori “più belli”. Ogni operazione mostra ingresso/uscita se disponibili, motivo, durata e risultato/costi. Esiti negativi e astensioni non nascosti.
Applicare gli stessi termini ai componenti condivisi pertinenti senza riscrivere tutti i pannelli osservativi o fare un restyling generale.

## 8. Navigazione comune agli ambienti esistenti

Soluzione proporzionata scelta: **router condiviso con URL a frammento (#/...)**, History/Indietro/Avanti del browser, senza introdurre un secondofrontend o dipendenze di routing se superflue. I percorsi identificano ambiente/vista e dove pertinentejob,risultato,operazione. Indicativamente:
- #/backtest/new, #/backtest/saved, #/backtest/jobs/<jobId>;
- #/backtest/results/<resultId>, relativo registro e dettaglio episodio;
- #/simulation/... e #/historical/... per le viste esistenti.
Nomi definitivi delle rotte sono dettaglio tecnico; coerenza e ID stabili sono obbligatori. Un ID è identificatore opaco validato, mai percorso/file da aprire a piacere.

Usare questa navigazione anche per shell, menu, link di ritorno e apertura righe: non mantenere route e useState che si contraddicono. Il selettore d'ambiente non è il pulsanteindietro.
- ritorno interno ben visibile **“Torna alle operazioni”** se provenienza registro, **“Torna ai risultati”** se provenienza esempi; ritorno alregistro comunque accessibile dal dettaglio;
- preservare filtri esistenti, ordinamento e posizione scorrimento dove pertinente, anche con Indietro/Avanti; non aggiungere filtri nuovi solo per dimostrare questa proprietà;
- ricaricamento sujob/runsalvato recupera vista dal servizio, senza nuovaPOST o annullamento;
- link a ID inesistente/cancellato: messaggio e via d'uscita, nessun grafico vuoto presentato come risultato;
- per uno studio OBS o fileesterno caricato solo in memoria, è accettato che refresh/linkdiretto chieda di riaprirlo con messaggio chiaro e conservi, quando possibile, momento/scala richiesti. Non promettere persistenza non costruita e non lasciare pagina rotta. Nessuna obbligazione di salvare ogni JSON importato in IndexedDB;
- la simulazione fixture può ripartire dal suo stato iniziale al refresh, dichiarandolo; non presentare una posizione locale come ripristinata se non lo è;
- inizializzazione non fa navigazioni che annullano la cronologia e non genera calcoli al semplice mount.
Il problema Owner di “←Risultati” non trovato va verificato sul layout principale desktop: presenza nel codice non basta. Esistenti limiti telefono dichiarati non richiedono una versione mobile dedicata.

## 9. Controlli e confronto richiesti

Scegliere test mirati del diff e delle dipendenze effettivamente toccate:
- API/manager: duePOST contemporanee e due tab, retry con stessa chiave anche a job concluso, uno attivo, profilo/periodo non ammesso, dati mancanti e nessun tentativo di download;
- avanzamento dal motore reale: fasi/cursore/conteggi monotonici dove hanno senso, null prima di disponibilità, nessun totale finale anticipato;
- annullamento durante controllo e durante simulazione, completamento concorrente, errore e servizio riavviato conjob interrotto, nessun falso successo e nessun risultato completo da file parziale;
- ripresa della solaUI dopo refresh/chiusuratab: stessojob senza altro avvio;
- collegamenti registrorisultatidettaglio, Indietro/Avanti e refresh negli ambienti pertinenti, conservazione scroll/filtri ove presenti, file importato non più disponibile spiegato;
- lettura di risultati/costi e tooltip da mouse/clic/tastiera, stato non eseguito senza posizione, motivi diversi d'uscita, preservazione R1 su ultimo prezzo e file/percorsi incompleti;
- typecheck/build e breve prova browser sui dati reali, almeno desktop1366px; chiudere solo i propri processi.

**Confronto reale proporzionato obbligatorio:** eseguire il profilo fisso gennaio2025 una volta tramiteUI e una volta direttamente tramite medesimo percorso del motore/CLIoffline. Verificare stesso inputhash/confighash/versione/profilo, stesse decisioni/richieste/trade/costi/risultati e **bundle deterministico identico**; jobID/date/progresso separati dai risultati. Documentare comando diretto e hash. Il confronto è collaudo software, non nuova ottimizzazione o verifica indipendente della strategia.
Per l'instrumentazione di parsing/aggregazione/osservatore esistente, pochi casi sintetici e prefisso/futuri diversi devono dimostrare che callback/progresso/cancel non cambiano i risultati completi. Patch motore ammessa per il plumbing, non convenzioni nuove.

Non rieseguire automaticamente l'intero DEV/2025 a ogni testo/layout. Riutilizzare evidenze complete precedenti per regole immutate. Nessuna suite generale o pollingCI. Un fullrun ulteriore solo se un difetto trasversale lo giustifica esplicitamente. Fixture controllate possono coprire errori/annullamento; niente pause artificiali nel percorso produttivo.

## 10. Consegna completa e provaOwner

Non fermarsi al servizio API o alla sostituzione di etichette: consegnare un percorso completo e avviabile.
- commit/push dei file pertinenti su main autorizzati, noforcepush, pull/fetch, reset/stash o dati pesantiGit;
- aggiornare README con **un comando** d'avvio e pochi clic: Backtest→Nuovo→Prova gennaio2025→Avvia→progressione→Apri risultati→Tutte le operazioni→dettaglio→ritorno→Risultati salvati;
- documentare stato/versioni/input/profili e cartelle dei nuovijob, confrontoUI/diretto e controlli realmente eseguiti;
- screenshot principali con risultato, progresso reale e registro/dettaglio, attribuzione pertinente per i dati derivati;
- dichiarare cosa funziona e limiti: locale personale, noexchange, nessuna efficacia nuova; mancanti/annullati/interrotti non completi,importsoloRAM spiegato;
- aggiornare STATE e consegna di questo task, passareDELIVERED,nonACCEPTED. Non inventare la prova positivaOwner.

Il Director revisiona e guida una sola prova concreta proporzionata diGian: distinguere nuovo/salvato,avviare/capireprogresso,trovaretutteoperazioni,capiretentativo/eseguito/chiusura/costi,tornare/ripristinare. Gian non verifica formule. Correzioni ordinarie autonome fino a risultato utilizzabile; adAstra solo chiusura o conflitto sostanziale.
Questa è l'ultima preparazione richiesta prima del prossimo ciclo sull'algoritmo: **nessuna piattaforma generale o nuova strategia dentroAPP-001**.

## Spazio dell'esecutore

Da compilare: implementazione, versioni/profili, controlli, confronto realeUI/diretto, avvio e prova pratica, limiti, commit e consegna.
