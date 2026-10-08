# MP-004 — v0.5 candidata: RETURN seguito da recupero locale

Stato: specifica per chiusura metodologica del Director. Le scelte B sono approvate come ipotesi candidata; efficacia, implementazione e nuove prove non sono approvate. Base semantica: v0.4 al commit `776752e10b4153900647004cab305a0a6a29e0c6`. Nessun pacchetto esecutivo attivato.

**Scopo.** Per il solo child RETURN dello scenario A, sostituire l'emissione al ritorno con l'attesa di un recupero locale successivo. Recuperare l'estremo favorevole di una barra di ritorno prima di perderne quello contrario è evidenza locale coerente con una ripresa; non prova esaurimento della pressione avversa, validità dell'intera tesi o qualità economica della continuazione. Nessuna regola deriva dalla separazione dei nove stop dai due target.

## 1. Preparazione e predicati

Durante il WAIT attuale, la prima barra completa 1m che sarebbe un RETURN utilizzabile secondo le condizioni esistenti prepara il riferimento: corridoio, economia, gate non di selezione, dominio post-conferma e assenza di contatti proibiti. Slot, conflitto e priorità non scelgono ancora una call. Una barra bloccata non prepara; resta il WAIT esistente fino al suo termine. Non basta entrare geometricamente nel corridoio.

Congelare una sola volta `H0`, `L0`, identificativo e intervallo della barra, timestamp di effettiva pubblicazione del riferimento `p0` e cursore fattuale `c0`. Nessuna sostituzione, nuovo tentativo o rinnovo. Questi estremi non sono pivot certificati, anchor, V o stop.

Per una successiva barra completa `b`, con tick dello strumento `δ`:

| Direzione | Contraddizione locale | Ripresa, soltanto in assenza di contraddizioni precedenti |
|---|---|---|
| LONG | `low(b) < L0` | `close(b) >= H0 + δ` e `low(b) >= L0` |
| SHORT | `high(b) > H0` | `close(b) <= L0 - δ` e `high(b) <= H0` |

L'uguaglianza sull'estremo contrario è ammessa. Il solo massimo/minimo favorevole oltre soglia non conferma: serve la chiusura. Il riferimento non conferma sé stesso. Ogni barra intermedia nel dominio attivo viene controllata, anche se non può produrre ingresso. Prima violazione contraria: child terminato; una successiva ripresa non lo riapre. Violazione e chiusura favorevole nella stessa barra: contraddizione, nessuna emissione, nessuna sequenza intrabar presunta.

## 2. Stati e precedenze

| Stato | Evento | Transizione |
|---|---|---|
| WAIT_RETURN | Primo RETURN utilizzabile | WAIT_RESPONSE; un riferimento preparato |
| WAIT_RESPONSE | Barra integra senza ripresa né violazione | Resta WAIT_RESPONSE |
| WAIT_RESPONSE | Violazione contraria | TERMINAL: LOCAL_RESPONSE_CONTRADICTED |
| WAIT_RESPONSE | Prima ripresa causale valida | RESPONSE_OBSERVED; valutazione unica nella stessa dispatch |
| RESPONSE_OBSERVED | Tutti i gate e selezione superati | ISSUED; child consumato |
| RESPONSE_OBSERVED | Economia, gate o selezione impediscono la call | TERMINAL: RESPONSE_NOT_ISSUABLE, con motivi; child consumato |
| Qualsiasi attesa | Termine esistente o monitoraggio non valutabile | TERMINAL/CLEARED/UNASSESSABLE secondo causa |

RESPONSE_OBSERVED è un evento transitorio, mai una conferma conservata. Dopo la dispatch restano emissione o termine. La contraddizione locale termina soltanto questo child: non invalida automaticamente lo scenario A.

Ordine di decisione: confini della finestra e protezioni esistenti; scadenze, copertura e terminalità dello scenario; contatti con V/B/target/cap secondo i rispettivi domini; nuovi cap e loro controlli; contraddizione locale o ambiguità locale; ripresa; economia e altri gate; selezione; eventuale ISSUE. Si preserva l'ordine interno delle protezioni v0.4. In collisione la causa prioritaria determina l'esito; le altre condizioni osservate possono essere annotate senza contare due termini.

Non contare come ripresa decisionale una mera chiusura oltre soglia quando una causa prioritaria ha già terminato il child. Una falsa ripresa dopo ISSUE resta possibile: si applica il lifecycle attuale, senza stop locale aggiuntivo.

## 3. Disponibilità causale e dati

`p0` è il momento in cui il riferimento viene realmente pubblicato, non la fine nominale della sua barra. Il dominio locale inizia a `p0`. Una barra può confermare solo se inizia a/oltre `p0`, è completa, diventa disponibile dopo il cursore `c0` ed è ammessa in una dispatch successiva. Stesso timestamp non sostituisce l'ordine fattuale. Nessuna barra già disponibile nella dispatch di preparazione può confermare il riferimento appena creato.

Distinguere sempre intervallo di mercato, ammissione fattuale e pubblicazione professionale. Usare il normale ordinamento/sealing e le protezioni di freschezza esistenti; non aggiungere una tolleranza numerica ai ritardi. In una dispatch con più barre, tutte concorrono ai controlli di sicurezza. La prima ripresa ordinata nel dominio consuma la possibilità: non si cerca una barra successiva più conveniente. Se essa non è la barra corrente utilizzabile secondo la semantica esistente, annotare ripresa tardivamente osservata e valutazione non emettibile; non emettere sul vecchio prezzo né sostituirlo con una successiva chiusura.

Una barra con fine `<= p0` non fornisce risposta locale. Una barra con `start < p0 < end` non può confermare: se supera l'estremo contrario, non è noto se lo abbia fatto prima o dopo l'attivazione; esito locale UNASSESSABLE, motivo LOCAL_CONTACT_TIME_AMBIGUOUS, senza rinnovo. Se non lo supera, può escludere quella violazione nell'intervallo, ma non confermare. L'uguaglianza contraria non genera ambiguità.

L'esclusione dal dominio locale non esclude i controlli rispetto a V, target e cap già attivi: un contatto precedente o tardivamente pubblicato non viene ignorato. Una barra tutta successiva a un livello attivo con contatto invalidante produce l'esito esistente; una barra a cavallo della sua attivazione segue la protezione di ambiguità esistente.

Barre parziali non preparano e non confermano. Assenza di barre, gap, stale o ordine non risolto non equivalgono ad assenza di violazione. Finché manca copertura verificabile non si emette; alle condizioni esistenti di perdita copertura si termina UNASSESSABLE, senza riparazione retroattiva o riapertura. Eventuali informazioni giunte dopo ISSUE seguono le protezioni/assurance esistenti, senza riscrivere la conoscenza disponibile all'emissione.

## 4. Geometria, prezzo e selezione

R/K/V dello scenario, V operativa arrotondata, target, costi, corridoio e scadenze restano quelli esistenti. V strutturale e V operativa restano distinte. Le revisioni del cap continuano a restringere soltanto quanto già consentito; il riferimento non si sposta. Un cap nuovo non genera un nuovo tentativo né prolunga la vita del child.

La ripresa può esistere fuori dal corridoio o dalla regione economica: in quel caso non è emettibile e consuma il child. Al momento della prima ripresa si ricontrollano geometria e cap correnti, contesto, copertura, freshness, gate, tempo residuo e scadenze originali; poi slot/conflitto/priorità esistenti. Scadenza a uguaglianza precede ISSUE. Un veto di contesto che già termina il WAIT continua a farlo anche prima della ripresa; un blocco temporaneo non terminale resta tale fino alla prima ripresa, dove impedisce definitivamente questo ingresso.

Storico: prezzo della valutazione = chiusura della barra di ripresa corrente e utilizzabile, con costi storici fissati. Live: evidenza di ripresa dalla chiusura completa, ma valutazione economica sul prezzo side corrente e valido, ask LONG/bid SHORT, con envelope e freshness già previsti. Anche close e side price rispettano i gate di corridoio/zone già richiesti. Quote assente o stale alla ripresa: child consumato, nessuna attesa di quote migliori.

ISSUE è pubblicazione della call, non fill. L'ingresso storico successivo usa il valutatore pinnato e la sua prima opportunità ammissibile: non si assegna un fill alla chiusura di conferma né a un contatto precedente. Restano possibili NO_ENTRY e tutti gli esiti già previsti. IMMEDIATE, famiglie B/C e comportamento post-emissione invariati.

## 5. Confine della finestra

All'inizio della finestra valutata si applica il clearing esistente dei child pendenti del warmup anche a WAIT_RESPONSE, eliminando riferimento e possibilità d'ingresso; gli scenari strutturali restano contesto warmup senza rigenerare il child. Le call warmup seguono il trattamento esistente. Alla fine della finestra le attese terminano; il tail gestisce soltanto quanto autorizzato dal lifecycle esistente. Nessun reset a ottobre, novembre o dicembre all'interno di una finestra continua.

## 6. Fixture manuali deterministiche

Fixture semantiche, non backtest eseguiti. Tempo UTC. Ogni riga riparte dal riferimento, salvo sequenza esplicita. Tick 0,1; costi storici 14 bps; rapporto minimo 1,2. LONG: R=1000, K=1020, V operativa=990, T/cap=1050, corridoio [1000;1020]. SHORT: R=1040, K=1020, V operativa=1050, T/cap=990, corridoio [1020;1040]. Geometria già validamente confermata, nessuna zona bloccante, copertura completa, gate superati e scadenze lontane salvo override.

Riferimento `[10:00;10:01)`, pubblicato 10:01, cursore 100: LONG `(low,high,close)=(1002;1008;1004)`; SHORT `(1032;1038;1036)`. Preparazione una sola volta. Le tuple seguenti sono sempre `(low,high,close)`; barre consecutive complete, pubblicazione alla fine e cursore crescente salvo override.

| Caso | LONG | SHORT | Esito |
|---|---|---|---|
| Valido, barra 10:01–10:02 | (1003;1010;1009) | (1030;1037;1031) | Prima ripresa, economia ammessa, ISSUE 10:02 |
| Uguaglianza contraria e soglia favorevole esatta | (1002;1008,1;1008,1) | (1031,9;1038;1031,9) | Ripresa valida |
| Solo uguaglianza favorevole | (1002;1008;1008) | (1032;1038;1032) | Nessuna ripresa; attesa |
| Violazione intermedia; poi barra valida | (1001,9;1007;1005), poi caso valido | (1033;1038,1;1035), poi caso valido | Termine sulla prima barra, seconda inutilizzabile |
| Violazione e recupero stessa barra | (1001,9;1010;1009) | (1030;1038,1;1031) | Contraddizione, zero riprese decisionali/ISSUE |
| V e recupero stessa barra | (990;1010;1009) | (1030;1050;1031) | Protezione V prioritaria; nessun ordine intrabar |
| Economia insufficiente, corridoio rispettato | (1003;1019;1019) | (1021;1037;1021) | Ripresa osservata; rapporto circa 0,97/0,98 < 1,2; consumato |
| Fuori corridoio | (1003;1021;1021) | (1019;1037;1019) | Ripresa osservata, non emettibile, consumato |
| Selezione negata | Caso valido, slot occupato | Caso valido, candidato prioritario stesso verso | Non emettibile: SLOT_OCCUPIED / PRIORITY |
| Conflitto selezione | Caso valido e candidato SHORT azionabile | Caso valido e candidato LONG azionabile | CONFLICTED, consumato |
| Scadenza esattamente 10:02 | Caso valido | Caso valido | Scadenza prima della ripresa decisionale/ISSUE |
| Nuovo cap prima della ripresa | Cap a 1012, attivo 10:01:30; barra valida non lo tocca | Cap a 1028, attivo 10:01:30; barra valida non lo tocca | Ripresa; economia insufficiente col nuovo cap; nessun reset |
| Contatto cap attivato dentro barra | Nuovo cap 1009,5 a 10:01:30, barra valida | Nuovo cap 1030,5 a 10:01:30, barra valida | CAP_ACTIVATION_CONTACT_AMBIGUOUS prioritario |
| Riferimento pubblicato tardi | p0=10:02; recupero in [10:01;10:02) | Speculare | Recupero precedente non utilizzabile; solo barre iniziate da 10:02 possono confermare |
| Ripresa ricevuta con barra successiva | Prima barra valida più barra successiva ammesse insieme; solo la seconda è corrente | Speculare | Se le protezioni dati non hanno già terminato: prima ripresa tardiva, N=1, I=0; niente sostituzione |
| Quote live non valida alla ripresa | Barra valida, ask stale | Barra valida, bid assente | R=1, N=1, I=0; nessuna attesa della quote |
| Barra a cavallo di p0 | p0=10:01:30; [10:01;10:02) con low=1001,9 | Stesso p0, high=1038,1 | LOCAL_CONTACT_TIME_AMBIGUOUS, non emissione |
| Dato incompleto/gap | Manca barra intermedia prima di quella valida | Speculare | Nessuna emissione attraverso il buco; protezioni copertura esistenti |
| Warmup/finestra | Riferimento warmup, ripresa dopo eval_start | Speculare | Child CLEARED; nessun riuso del riferimento |

Per il percorso valido i rapporti netti sono circa 1,94 LONG e 2,08 SHORT: esiste spazio economico con geometria invariata. Per distinguere ISSUE/fill, si può fissare nella fixture PRIMARY una prima barra d'ingresso ammessa alle 10:03 con open 1009/1031, senza contatti invalidanti antecedenti. Questa costruzione dimostra possibilità, non frequenza né efficacia. Dopo tale ingresso, una successiva barra che raggiunge V dimostra una falsa ripresa possibile senza contraddire la specifica.

## 7. Conteggi e riconciliazione

Unità = child RETURN univoco, separato per direzione e per warmup/evaluation; nessun conteggio ripetuto per barra. `W` = child instradati al WAIT_RETURN nella finestra; `P` = riferimenti preparati; `C` = risposte terminate per contraddizione locale prima di ripresa; `R` = prime riprese decisionali osservate; `N` = valutazioni della prima ripresa non emettibili; `I` = call emesse. `X` = altri termini dopo preparazione (scadenza, scenario, contatti, cap, copertura/ambiguità, clearing); `A` = attese ancora aperte al cutoff del rendiconto.

Identità: `P = C + R + X + A`; `R = N + I`. Per completare il flusso, `W = P + termini prima del riferimento + WAIT_RETURN ancora aperti`. Conteggi sul medesimo perimetro temporale; i clearing warmup si espongono a parte, non diventano riferimenti evaluation.

Rapporti minimi: P/W, C/P, R/P, N/R, I/R e I/P; denominatore zero = non definito. Esporre sempre conteggi assoluti e X/A: C/P non misura deterioramento reale e R/P non misura qualità della continuazione. Per N registrare tutti i blocker, con un motivo primario deterministico per riconciliare (economia/geometria, altri gate, selezione; dentro classe codice ordinato); le incidenze multi-motivo non si sommano. X usa la causa prioritaria del lifecycle. Ambiguità e copertura non contano come contraddizioni provate. Esiti e ingressi successivi appartengono al report economico distinto, non a questi denominatori. Nessuna quota di frequenza o profitto.

## 8. Chiusura richiesta e limiti

Nessuna nuova soglia numerica è necessaria. Il recupero 1m e il tick sono le scelte candidate approvate; non implicano superiorità informativa. La specifica è falsificabile semanticamente: una call senza riferimento unico preesistente, con violazione intermedia, con conferma retroattiva, dopo prima ripresa respinta o ottenuta cambiando geometria è non conforme. Uno stop successivo non è di per sé una violazione semantica.

Due raccordi sono espliciti nella presente proposta di chiusura: contatto locale a cavallo della pubblicazione → UNASSESSABLE senza rinnovo; prima ripresa tardivamente osservata ma non più corrente → non emettibile senza cercare recuperi successivi. Non sono tolleranze già implementate né evidenza di efficacia. Richiedono l'accettazione del Director insieme a MP-004; se si vuole invece attendere ulteriori barre in questi casi, occorre riaprire precisamente la decisione su primo tentativo/causalità, non introdurre un fallback implicito.

Nessun conflitto geometrico assoluto emerge dalle fixture. Resta non identificato se questo recupero locale sia informativamente utile. C resta alternativa distinta qualora B sia respinta; non è fallback automatico durante l'esecuzione. Fonti controllate in sola lettura: snapshot v0.4 di `core3.py` (finestre, WAIT, cap, selezione) e `core.py` (prezzi side). Nessuna implementazione, acquisizione, estrazione, replay, Deep, backtest o verifica CI è stata eseguita per questa specifica.
