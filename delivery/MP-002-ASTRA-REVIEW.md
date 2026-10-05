# MP-002 v0.1 — Review Astra per il Director

Data: 5 ottobre 2026. Repository: `C-Gian/algorithmic-trader`. Commit esaminato: `b46c29229c39d96d658f1ab6969ffdd88d907ded`.

**Verdetto: CORREZIONI METODOLOGICHE RICHIESTE prima della chiusura del design.** La direzione è difendibile; il testo attuale lascia biforcazioni che possono cambiare scenari, call e risultati. Non è un'autorizzazione a implementare o a lanciare valutazioni.

Fonti lette: FOUNDATION v3.1, STATE, AGENTS e task correnti; `MP-002-SCENARIO-CONFIRMATION-ENTRY-PROPOSAL.md`, `MP-002-PARAMETER-DELTA.json`; MP-001 v0.2, in particolare §§3,5–9,11; review Astra del dossier Owner Backtest A preservata nel repository. Nessun nuovo dato di mercato, estrazione, replay o backtest. I controesempi sono sintetici; i pochi controlli numerici sono algebra, non simulazioni del trader. Clean-room preservata.

## 1. Cosa approverei e cosa contesto

Approverei come direzione:

- scenario strutturale indipendente da costi, slot, call e valutatore;
- due modalità A distinte, immediata con area v0.2 oppure ritorno successivo nel corridoio R–K;
- V fisso, target pre-issue solo restringibile, nessuna retrodatazione dell'ingresso;
- un solo tentativo di prima emissione per conferma, senza retry di selezione;
- massimo temporale A dalla conferma, non dall'ingresso ritardato;
- confronto congelato ottobre–dicembre, Owner-operated, senza selezione sui risultati di settembre.

La mia precedente review suggeriva una direzione, non una dimostrazione che ogni sua traduzione fosse coerente. MP-002 aggiunge scelte sostanziali: ownership degli scenari persistenti, terminali che possono ritirare call, cap monotono e nuovo riferimento temporale. Vanno chiuse come regole, non lasciate al coding agent.

| Finding | Priorità | Decisione necessaria |
|---|---|---|
| B1. Ownership strutturale ancora potenzialmente dipendente dall'entry | Bloccante | Separare discovery/reset strutturali da occupazione e termine dell'entry |
| B2. Routing immediato/ritorno e precedenza dei gate | Bloccante | Tabella esaustiva, inclusi blocker simultanei |
| B3. Vuoto strutturale permanente versus costo live transitorio | Bloccante | Distinguere i due eventi e il loro lifecycle |
| B4. Nuovo cap e contatti nella barra che lo rende noto | Bloccante | Regola causale di attivazione, inclusi cap dietro il prezzo |
| B5. Contatti alla conferma, allo scenario e alla call | Bloccante | Un'unica precedenza esplicita, con domini temporali separati |
| B6. Orologi di progresso, hard deadline e valutatore | Bloccante | Formule precise e modifica esplicita della baseline horizon-only |
| B7. Denominatori e significato dei criteri di arresto | Bloccante per preregistrazione | Misurare separatamente dominio, routing RETURN, entry e costi |

Non serve un nuovo dossier per risolverli. Servono decisioni sul testo e sul delta; nessuna soglia vincente.

## 2. B1 — L'indipendenza deve includere la nascita degli scenari futuri

**Riferimenti: §§3–4,6,8; delta `scenario_ownership`.** Il documento richiede scenari identici al variare dei soli costi, ma mantiene qualification/renewal A e stabilisce che durante WAIT_PRICE l'owner pending rimane occupato. Non definisce cosa accada alla discovery dopo emissione immediata, rifiuto economico e attesa: in v0.2 termine del tentativo e reset false→true sono collegati.

**Controesempio.** Una conferma a t0 emette immediatamente con costi bassi; con costi alti entra in WAIT_PRICE. A t1 Q_A diventa falsa e a t2 torna vera mentre WAIT_PRICE è ancora vivo. Se la prima variante ha liberato il pending e la seconda no, soltanto la prima crea un nuovo scenario. Costi → durata dell'entry → latch → futuro MarketView. Tenere immutabili i campi dello scenario già nato non risolve questa dipendenza.

Lo stesso rischio riguarda le zone proprie: se la disponibilità di B come ostacolo dipende dal termine economico dell'attempt, un rifiuto cambia i target e potenzialmente altri oggetti futuri. B/C devono conservare budget e box secondo eventi strutturali, non secondo l'esito del loro gate.

**Correzione precisa.** Introdurre semanticamente due ownership:

1. owner di discovery/segmentazione strutturale, con nascita, occupazione, terminale e reset determinati esclusivamente dal percorso strutturale;
2. tentativo d'ingresso figlio, che può aspettare, emettere o terminare senza mutare il primo.

Per il perimetro minimo raccomando che A mantenga il blocco di discovery fino a un rilascio strutturale esplicito: invalidazione/destinazione/gap/contesto pre-conferma, oppure **scadenza originale del setup**. Anche se l'entry è già emessa o respinta. Da quel rilascio applicare il reset false→true previsto. Lo scenario confermato può sopravvivere come oggetto di lettura fino al proprio terminale; non occupa implicitamente un nuovo budget di ingresso. Questa è una modifica categoriale rispetto a v0.2 e va dichiarata, non chiamata renewal interamente invariato.

Fissare anche la vita delle zone owner: deve seguire l'owner strutturale e la regola di rottura/expiry, mai call o costi. Nessun cap di memoria deve scartare scenari in base a quante call sono state emesse. La durata massima e la cadenza di nascite consentono un limite deterministico; esplicitarlo nella successiva specifica di stato, senza un eviction economico nascosto.

**Esito atteso del controesempio:** entrambe le varianti hanno lo stesso rilascio, reset, nascite, zone e scenario-set; possono divergere solo negli oggetti d'ingresso e guidance. Verificare questa invarianza sull'intera sequenza, non solo sulla conferma iniziale. Se gli ID globali includono il profilo costi, confrontare lineage/contenuti strutturali normalizzati oppure usare ID strutturali separati: non pretendere simultaneamente hash di configurazioni differenti e identità byte-per-byte.

## 3. B2 — Rendere esaustivo il passaggio IMMEDIATE → RETURN

**Riferimenti: §§5–6 e transition inventory.** È chiaro il caso economico-pass con veto non economico: terminale. Non è altrettanto chiaro il caso economico-fail con calendario/quote/slot contemporanei. “Corridor/gates specified at confirmation permit waiting” e “only when immediate economic geometry fails” non costituiscono una tabella completa.

**Controesempio.** Il close è fuori dalla regione economica, il corridoio R–K è valido, ma c'è un blocco calendario. Una lettura termina per veto one-shot; un'altra entra in WAIT_PRICE e aspetta la fine del blocco, come §6 consente durante l'attesa. Le call future cambiano. Uno slot occupato pone lo stesso problema, ma WAIT_PRICE dichiara di non occuparlo.

**Correzione raccomandata, conservativa rispetto allo scopo dichiarato:**

| Stato alla conferma | Esito |
|---|---|
| Contatto/struttura/target invalidi o mancanti | Termine entry con ragione specifica |
| Quote necessarie assenti, dati richiesti insufficienti, calendario/dislocazione vietati, contesto vietato o tempo insufficiente | Termine entry, anche se fallisce anche la geometria economica |
| Gate non economici passano; geometria immediata passa | IMMEDIATE entra nella selezione normale; un perdente non si converte in RETURN |
| Gate non economici passano; geometria immediata fallisce; corridoio strutturale ed economico validi | WAIT_PRICE; non partecipa alla selezione, quindi slot/priority/conflict non lo consumano ora |
| Geometria immediata fallisce e corridoio non valido | Termine entry con distinzione geometrico/economico |

Durante WAIT_PRICE le nuove restrizioni temporanee possono mantenere l'attesa, come già proposto; la selezione si applica solo al primo evento davvero azionabile. Questa asimmetria è una convenzione dichiarata del test, non una necessità del trading. Evita che l'executor decida inconsapevolmente quale blocker vinca.

Specificare se “geometria immediata fallisce” includa EMPTY_STRUCTURAL_AREA e PRICE_OUTSIDE_STRUCTURAL_AREA, oltre ai due esiti economici del predicato. Raccomando includere soltanto le incompatibilità di prezzo/area con V/T validi; un errore/unavailable del calcolo non abilita una modalità alternativa. Storico: prezzo campione è il close dichiarato. Live: close strutturale e ask/bid di actionability non sono intercambiabili.

## 4. B3 — Un costo live più alto non è una rottura strutturale

**Riferimenti: §6.** Il testo dice sia che K corrente può restringere o ampliare la parte economica, sia che un corridoio economicamente vuoto termina permanentemente l'entry. Il transition inventory parla di “permanently empty corridor”, senza un criterio che distingua i casi.

**Controesempio numerico.** LONG T=100700, V=99700, R=99980, K_trigger=100049,9. Con costo 14 il massimo prezzo è 100014,5: il corridoio ha una parte utilizzabile. In WAIT_PRICE il costo sale temporaneamente a 20: il bound scende a circa 99954,6, sotto R. Poi torna a 14 prima della scadenza, senza contatti né cambiamenti strutturali. Il testo permette sia termine definitivo sia recupero della regione.

**Correzione:** il corridoio strutturale resta fisso salvo clipping monotono del target. La sua impossibilità geometrica è terminale. Una regione economica vuota per **K live corrente** durante un WAIT già ammesso è invece un blocker temporaneo, fino al normale termine strutturale/temporale. Non anticipare che tornerà utilizzabile e non emettere finché il predicato corrente non passa. Una nuova riduzione del target può chiudere definitivamente per geometria; se lascia geometria ma non economia live, applicare la stessa distinzione. Per il profilo storico K fisso il vuoto economico non si recupera e può terminare.

La decisione iniziale di non avviare RETURN senza regione economica/quote valide può restare one-shot. Esplicitare che la recuperabilità sopra riguarda solo un WAIT_PRICE già avviato. Esito atteso dell'esempio: attesa bloccata, poi nuovamente eleggibile; mai una call durante il vuoto economico.

## 5. B4 — Nuovi ostacoli: manca il momento da cui vale il nuovo cap

**Riferimenti: §6.** È corretta la monotonia T_confirm → T_current, ed è ragionevole non riallargare dopo retirement. Mancano però: definizione di “nuovo” rispetto alle zone già ignorate perché passate, trattamento di una zona che attraversa V, attivazione rispetto alla barra che pubblica il pivot.

**Controesempio.** A in WAIT con T=100700. Una nuova zona, nota per la prima volta alle 10:16, ha near edge 100100. La barra 10:15–10:16 ha high=100150 e close=100000, V non toccato. Se prima si aggiorna T e poi si usa l'intera barra contro T_current, si registra un contatto con un target che non era ancora in vigore durante quella barra. La conoscenza della zona è causale; attribuirle un precedente evento target non lo è.

**Correzione minima:** ogni revisione di cap ha effective publication/cursor. Valutare contatti storici della barra contro il cap che era in vigore nel suo intervallo, non contro un cap appena introdotto. Per l'intervallo che introduce/attraversa la revisione e tocca il nuovo cap, raccomando esclusione conservativa dell'ingresso e termine `CAP_ACTIVATION_CONTACT_AMBIGUOUS`, senza etichettarlo target raggiunto. Non è un trade outcome. Intervalli successivi possono certificare contatti solo per cap già attivi al loro inizio.

Se un nuovo cap viene pubblicato dietro o esattamente al prezzo attuale, chiudere l'entry come obiettivo pre-entry non più davanti, non attendere un fittizio “nuovo” attraversamento. Per una zona nuova che contiene V ma si estende sopra V nel LONG, definire: nessun clipping a V o sotto V può fabbricare rischio positivo; il campione nella zona è bloccato; se non resta corridoio fuori zona, non c'è entry. Non lasciare questa situazione affidata al solo controllo `near∈(V,T)`.

Identificare per ID le zone eleggibili alla conferma e quelle ammesse successivamente. “Wholly passed” non deve significare dimenticare arbitrariamente una zona ancora attiva solo perché in un campione il prezzo le è passato sopra: occorre adottare esattamente la distinzione MP-001 fra posizione corrente, rottura da close 15m e retirement.

**Esiti attesi:** nessun uso retroattivo del nuovo livello; nessuna riapertura se il cap è poi ritirato; nessun ingresso dentro una zona. Una volta emessa la call, il target outcome resta quello di issue; gli ostacoli nuovi possono restringere nuove entry, non riscrivere un esito passato.

## 6. B5 — Contatti e terminali: tre oggetti, tre confini temporali

MP-002 distingue correttamente scenario, entry e call, ma non completa tutte le collisioni.

**Caso 1: target nella barra di conferma.** Il testo vieta WAIT se la stessa barra ha toccato T_confirm. Non dice altrettanto chiaramente se IMMEDIATE possa emettere quando quella barra torna sotto T e la geometria corrente passa. I costi possono così determinare se un obiettivo già toccato blocchi o meno l'emissione.

Raccomando una regola comune A: un contatto della barra di conferma con il target conservativo appena selezionato esclude **entrambe** le modalità come `PRE_ENTRY_TARGET_CONTACT`, senza affermare l'ordine intrabar e senza contare un successo. Dichiarare questo delta rispetto a IMMEDIATE v0.2. Non basta dire che IMMEDIATE è interamente invariato.

**Caso 2: V nella barra di conferma.** §5 lo chiama rifiuto ambiguo; §3 può invalidare lo scenario per V già attivo dopo arm. Non c'è necessariamente contraddizione, ma servono esiti per oggetto: scenario ARMED con V già pubblicato prima dell'intero intervallo → invalidazione strutturale certa per contatto; nessuna conferma pulita/nessuna entry. Se l'intervallo straddla la pubblicazione di V, scenario UNASSESSABLE. L'ambiguità dell'ordine recupero/stop non rende incerto che un V già attivo sia stato toccato.

**Caso 3: scenario finisce nello stesso dispatch della possibile issue.** Se narrativa B o V vengono toccati, oppure scade il suo clock, il terminale strutturale deve precedere selezione ed emissione. Non si emette una call collegata a uno scenario già terminale, nemmeno se un target economico più lontano passa il rapporto.

**Correzione:** completare una collision table: timer/gap e terminali strutturali → contatti pre-entry secondo cap effettivo → nuovi cap con relativa ambiguità → gate/mode/selection → pubblicazione → futuro monitoring della call. Le coppie stop/destinazione simultanee sono UNASSESSABLE; un terminale d'entry non modifica lo scenario. Un terminale dello scenario che ritira guidance deve trasportare la ragione: se è perdita di copertura, il valutatore censura dal primo intervallo mancante, non esegue semplicemente un'uscita discrezionale tardiva chiamata SCENARIO_TERMINAL.

## 7. B6 — Approvo il termine massimo dalla conferma, ma non gli orologi impliciti

**Decisione esplicita:** ancorare il massimo A alla conferma è più coerente della concessione di quattro nuove ore al ritorno. La conferma identifica l'attivazione della tesi; un prezzo d'ingresso migliore non rinnova la previsione. Il periodo di attesa resta entro il vecchio setup expiry. È una convenzione prudente, non una durata scientificamente calibrata.

Raccomando queste formule, tutte riferite a pubblicazioni causali:

| Evento | Clock proposto |
|---|---|
| Termine attesa entry | Original setup expiry, senza proroga |
| Massimo scenario e call A | `t_confirmation + 4h` |
| Residuo per prima issue e successiva entry | `hard_deadline − now`; almeno 30m |
| Check progresso scenario | `t_confirmation + 2h`, dal close di conferma e S15 di conferma |
| Check progresso call | `t_issue + (hard_deadline − t_issue)/2`, dal riferimento di issue e S15 congelato a issue |
| Baseline horizon-only A | Richiesta uscita al medesimo `hard_deadline`, poi ritardo d'uscita dichiarato |

La scelta del check call al punto medio del **residuo** evita di lasciarlo a “metà del fixed hard horizon”, oggi interpretabile come confirmation+2h, issue+2h o metà del residuo. Scenario e call continuano ad avere riferimenti distinti; vince il primo terminale esplicito. Per l'entry IMMEDIATE gli orologi coincidono naturalmente. Non spostare il check scenario quando compare la call.

**Controesempio.** Conferma 10:00, setup expiry 12:00, issue RETURN 11:30. Hard deadline 14:00, durata residua 150 minuti, finestra comunicata iniziale [30,150]. Il check scenario è 12:00; quello call raccomandato 12:45. Non 13:30 e non un termine alle 15:30. Se a 12:00 fallisce il progresso dello scenario, la guidance viene ritirata allora anche se il trade ipotetico è giovane. Questo rischio di ritiro anticipato deve essere mostrato e contato, non nascosto dietro la durata indicativa di 30 minuti: un minimo residuo non garantisce di tenere la posizione almeno 30 minuti.

**Valutatore:** MP-001 ancora la baseline horizon-only a `original_issue + family_horizon`. §7 MP-002 dice valutatore invariato ma modifica la deadline A: ereditare letteralmente il vecchio clock darebbe 15:30 alla baseline e 14:00 al metodo. Correggere il registro/delta esplicitamente. La baseline resta un confronto condizionato sugli stessi ingressi, non una prova del vantaggio predittivo.

L'entry-delay resta da issue effettiva; WAIT non produce un path. Un eventuale termine prima dell'apertura ipotetica impedisce l'ingresso. La censura da gap deve restare distinta dal ritardo di uscita per STALLED o TIME_EXPIRED. Nessuna variazione del valutatore può cambiare gli output professionali.

## 8. B7 — Il confronto è valido come confronto di versioni, non come isolamento del RETURN

Conservo ordine ottobre, novembre, dicembre 2025 e v0.2→v0.3 per mese, stessi pack/profili, nessuna revisione opportunistica fra mesi, protetti non aperti. La nuova versione cambia però anche persistenza/scenari, ownership, terminali e clock: una differenza nel totale dei trade non è attribuibile automaticamente al solo ritorno. Non servono altre varianti: riportare funnel e cause per ciascuna modalità/owner nel confronto delle due versioni.

Tre correzioni della preregistrazione sono necessarie.

**1. Denominatore dei venti.** “20 distinct entered confirmation/owner structures” potrebbe essere soddisfatto da B/C o A IMMEDIATE mentre RETURN produce un solo ingresso. Specificare che la discussione dell'ipotesi RETURN richiede venti distinti **owner A con path RETURN entrato al ritardo principale**, non venti path di sensibilità né campioni orari. Continuare a riportare separatamente l'insieme integrato. Venti è una soglia di reporting, non indipendenza statistica: owner vicini nello stesso trend possono essere correlati.

**2. Maggioranza senza corridoio.** Definire tre insiemi: conferme strutturali A; conferme valutabili geometricamente; conferme instradate a RETURN. Il test >50% deve usare una metrica definita su ogni conferma geometricamente valutabile, non soltanto su chi entra in WAIT. Calcolare il corridoio e la sua intersezione economica al cutoff anche per una conferma IMMEDIATE, come diagnostica senza effetti decisionali. Distinguere no target, inside-zone, corridoio R–K vuoto, corridoio geometrico ma costo-incompatibile e dati non valutabili. Non trattare un campo non calcolato come vuoto.

Per questa prima verifica storica a K fisso, corridoio iniziale immutabile e cap soltanto restringibile, un'intersezione vuota all'inizio non può diventare non vuota in seguito. Quindi il criterio “mai non vuoto a qualsiasi assessment” può essere ridotto, per quel profilo, a un controllo al cutoff di conferma. Non estenderlo al live con K variabile. >50% resta un segnale diagnostico di incompatibilità del dominio selezionato, non una dimostrazione che bisogna passare a timeframe superiori.

**3. Zero e scarsità.** Zero ingressi RETURN su tre periodi valutabili respinge l'utilità osservata della variante nel dominio preregistrato; se non esiste alcuna conferma instradabile, non dimostra falsa la specifica ipotesi di un ritorno dopo conferma: il collo di bottiglia è a monte. Il risultato di prodotto resta negativo e richiede una decisione, non attesa indefinita. Con 1–19 owner entrati: INSUFFICIENT_EVIDENCE, ma anche mancata validazione di frequenza/praticabilità. Non procedere automaticamente ai protetti né estendere lo sviluppo mese per mese finché si raggiunge 20. Il Director chiude con una decisione motivata di mantenimento, revisione o rigetto del dominio, senza cambiare retroattivamente il test.

Resta accettabile non fissare un win rate o una soglia di profitto arbitraria. Però tre mesi con dati assessabili, chiamate inutilizzabili o perdite nette persistenti non possono essere presentati come successo perché sono stati superati venti ingressi. Rapporto finale: copertura, frequenza su tempo totale/assessabile, durata reale delle finestre, path a 60s, 0/120 come sensibilità, cost stress sugli stessi path, esiti ambigui/censurati, perdite e concentrazione per owner/regime. Le condizioni di avanzamento ai protetti richiedono disposizione distinta.

## 9. Ulteriori fixture sintetiche da incorporare nel design

Sono esiti attesi di specifica, non test eseguiti sul prodotto.

| Caso | Esito atteso dopo le correzioni |
|---|---|
| Costi diversi; una variante IMMEDIATE, una WAIT; poi Q_A false→true | Nascite/reset/zone/scenari identici; entry diverse |
| Scenario confermato, call respinta per slot | Scenario persiste, nessun nuovo tentativo su quello stesso confirmation ID |
| Close economicamente inadatto e calendario vietato alla conferma | Termine entry in entrambe le letture del gate; non WAIT secondo la tabella raccomandata |
| Close economicamente inadatto, nessun veto, slot occupato | WAIT possibile; lo slot viene controllato solo al primo ritorno azionabile |
| Corridoio R>K nel LONG | Vuoto strutturale, terminale; nessuna inversione degli estremi per renderlo utilizzabile |
| Corridoio con un solo tick, strettamente fra V/T | Consentito solo se il predicato esatto passa; nessuna larghezza minima inventata |
| K live rende temporaneamente vuoto un WAIT valido | Blocker economico, nessuna call; recupero ammesso prima dei terminali |
| Nuovo cap noto a fine barra, high della stessa barra oltre quel cap | Nessun target-hit retroattivo; esclusione/termine ambiguo esplicito |
| Nuova zona pubblicata sotto il prezzo corrente LONG | Cap non più davanti: niente issue su quella conoscenza; nessuna falsa attesa di contatto futuro |
| Target toccato nella barra di conferma, close di nuovo sotto | Nessuna A IMMEDIATE né RETURN; nessun successo ipotetico |
| Ritorno valido esattamente al setup expiry | Scadenza prima dell'emissione |
| Scenario terminale nello stesso dispatch del ritorno | Nessuna call |
| Issue 11:30 da conferma 10:00 | Hard 14:00, scenario check 12:00, call check 12:45; baseline hard 14:00 |
| Gap nel monitoring fa terminare lo scenario collegato a call entrata | Guidance unassessable; path censurato dal gap, non guarito con exit successivo |
| Call chiusa per prezzo, poi riaperta prima dei terminali | Stesso ID e un solo percorso first-entry per profilo, nessuna seconda operazione |
| Scenario dal warmup, conferma precedente al window start | Contesto/scenario dichiarato; nessun ritorno salvato come nuova call in finestra |
| Dieci RETURN call, tre delay per call | Dieci call/owner al massimo, non trenta evidenze indipendenti |

**Attenzione alle fixture SHORT:** “exact reflection with positive market prices must match decisions” è troppo forte se significa riflettere i prezzi rispetto a una costante. Le disuguaglianze strutturali si riflettono; G/Q dividono per il prezzo reale positivo. Per l'esempio LONG T=100700,V=99700 il bound è circa 100014,525; riflettendo attorno a 100000 si ottiene SHORT T=99300,V=100300, bound circa 99985,434, non 200000−100014,525. A ridosso del tick una riflessione arbitraria può cambiare il risultato economico. Costruire esempi LONG/SHORT con esiti calcolati dalle rispettive formule e uguali rapporti percentuali quando si pretende equivalenza; non imporre una falsa simmetria numerica. Il floor/ceil inward resta obbligatorio.

## 10. Limiti accettabili e delta da completare

Sono limiti accettabili, se espliciti: corridoio R–K non validato economicamente; ritorni soggetti a selezione avversa; conferma live senza quote consumata one-shot; nessun rinnovo per slot; B/C entry invariate; scenario WATCH ancora UNCERTAIN; impossibilità di garantire poche call ogni settimana. Non servono nuove fonti o dati per implementarli correttamente una volta chiuso il design. La loro utilità si verifica in seguito.

La copertura MarketView migliorata deve venire da scenari realmente persistenti e causalmente supportati. Non da UP/DOWN copiati dal contesto né dalla sola rinomina di WATCH. I campioni orari +1h/+4h conservano antecedenti e denominatori; costi e valutatore non selezionano i campioni da valutare.

Il JSON delta deve dichiarare, oltre alle voci già presenti: rilascio/reset dell'owner strutturale; vita delle zone proprie; routing con blocker simultanei; vuoto economico live recuperabile; effective time dei cap; contatto alla conferma per IMMEDIATE; origine/formula di entrambi i check progresso; origine della baseline horizon-only; propagazione della ragione di scenario terminale alla censura; denominatori RETURN e corridoio. Non basta modificare il prose lasciando un delta che promette invarianti più ampie di quelle reali.

**Prossimo passo unico:** il Director dispone su B1–B7 e chiude MP-002 con testo, delta e collisioni sintetiche coerenti. Nessun'altra estrazione; nessuna acquisizione; nessuna modifica al metodo runtime. Solo dopo questa chiusura può essere attivato separatamente un pacchetto implementativo. Questa review non attiva quel pacchetto né un Owner backtest.
