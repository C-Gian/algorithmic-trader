# MP-001 — Review metodologica Astra

Data: 3 ottobre 2026  
Destinatario: Project & Research Director  
Base esaminata: `C-Gian/algorithmic-trader@cd8665ab17464f164437b9857c23aefb5342be10`  
Oggetto: proposta `btc.context-action.v0.1`, non ancora metodo accettato  
Stato: **ADVISORY — REVISIONE MIRATA NECESSARIA PRIMA DELLA CHIUSURA MP-001**

## 1. Giudizio e perimetro

**Conservare l'impianto integrato e le tre famiglie; non approvare la specifica invariata.** Non occorre un nuovo programma di ricerca né un'altra architettura generale. Occorre chiudere alcune regole che oggi consentono a due implementazioni diligenti di produrre call diverse, e rendere esplicita la portata effettiva delle capacità professionali promesse.

A/B/C costituiscono un primo playbook ragionevole: continuazione dopo reazione, uscita da compressione con retest, fallimento dell'uscita con ritorno verso il centro. Non sono tre prove indipendenti né coprono ogni regime. La loro complementarità dipende da episodi, transizioni e geometrie; non dal numero di indicatori. Non propongo di aggiungere una quarta famiglia.

I problemi principali sono: ownership e rinnovo degli episodi; conflitto fra box e failure test; MarketView/scenari non completamente definiti; entry area più ampia dell'area economicamente ammissibile; lifecycle incompleto dopo exit guidance; contatti OHLC a cavallo della pubblicazione; convenzioni di valutazione ancora mancanti. Questi sono problemi risolvibili prima di vedere altri risultati.

**Non è dimostrato** che le soglie siano buone, che il metodo generi poche o molte call, che il target più vicino sia utile o che la traduzione abbia un vantaggio economico. La review non trae queste conclusioni. Anche “molto prudente” non equivale a “professionalmente corretto”.

Letti integralmente FOUNDATION.md, STATE.md, task.md, AGENTS.md e i tre documenti MP-001 richiesti; inoltre RP-001-DIRECTOR-REVIEW.md e la specifica temporale R2. Verificati i registri delle fonti e i passaggi pertinenti dei dossier LIB-005/LIB-008; effettuato un controllo primario mirato su M01 e M03, senza ricerca di risultati. Non ho riesaminato i casi storici né aperto nuovi outcome, eseguito backtest, cercato parametri o modificato codice. Le prescrizioni dei vecchi dossier non sono state adottate. Questa review non modifica Foundation, non chiude MP-001 e non autorizza R3/WP-009.

Classificazione:

- **B — Bloccante di specifica:** va risolto prima di implementare il comportamento interessato; non implica abbandonare il progetto.
- **E — Ipotesi economica/prodotto:** definibile ora, da valutare successivamente sul processo completo; non va “risolta” cercando soglie vincenti.
- **O — Miglioramento facoltativo:** non deve ritardare la prima integrazione.

Tutti i controesempi numerici e temporali qui sotto sono sintetici.

## 2. Copertura dei ruoli Foundation

“Implementato nella proposta” indica una regola descritta, non codice già esistente o efficacia verificata.

| Ruolo | Trattamento effettivo | Disposizione |
|---|---|---|
| Struttura, trend, livelli/location | Implementato nel nucleo 15m/1h; contesto più ampio limitato. Pivots, estremi e box danno location e invalidazione. | Conservare; chiudere semantica dei livelli e MarketView. Non chiamare tutti gli orizzonti “integrati” se alcuni sono solo descrittivi. |
| Momentum | Implementato tramite displacement, efficienza e reazione. | Non contarli come conferme indipendenti: sono trasformazioni dello stesso percorso. |
| Partecipazione | Significativamente limitata: rapporto di volume descrittivo, nessuna autorità sulla call. | Accettabile se dichiarato. Non attribuire “conferma dei volumi” a un dato che non modifica il ragionamento. |
| Volatilità | Implementata come scala, compressione/espansione, zone e geometria. | Ruolo sostanziale, ma le molte dipendenze dalla stessa scala vanno rese visibili. |
| Timing e ciclica | Implementazione parziale significativa: fase osservabile contrazione/movimento e transizioni. | Non è analisi di periodicità, turning dates o cicli lunghi. Non dichiarare definitivamente soddisfatto tutto l'interesse dell'Owner per la ciclica. |
| News, eventi economici/politici e risposta | Calendario e restrizioni implementati; risposta descritta ma non interamente formalizzata. Interpretazione contenuti e politica non programmata assenti, dichiaratamente. | Accettare un modulo di rischio-evento limitato, non un analista macro/news completo. Formalizzare la piccola parte di risposta che si intende esporre. |
| Derivati | Significativamente limitati: basi di prezzo e funding; nessuna lettura di positioning. | Corretto non dedurre OI/liquidazioni dai prezzi. Dislocation non equivale a segnale direzionale. |
| Liquidità ed execution context | Quote/spread per praticabilità, costi ipotetici; profondità e impatto non modellati. | Correggere prezzo lato operazione e contabilizzazione spread. Non promettere eseguibilità per una size ignota. |

Le esclusioni sono prevalentemente oneste. Il rischio di **assenza mascherata** si concentra nelle etichette “MarketView integrato”, “risposta alle notizie” e “ciclica implementata”: i nomi sono più ampi di alcune regole operative. Si corregge specificando le decisioni realmente prodotte, non aggiungendo automaticamente nuovi feed.

## 3. Findings bloccanti e correzioni minime

### B1 — Box, tentativi e rinnovo degli episodi non hanno una semantica unica

**Riferimenti:** proposta §§6A–C, 8–9.

B dice che un ritorno profondo attraverso L distrugge il box; C richiede un box vivo e una barra che scenda sotto L−z e rientri sopra L+z. Non è chiaro se la distruzione valga soltanto durante un tentativo B già iniziato, se dipenda dal low o dal close, e se C possa usare lo stesso box in quel dispatch. Non affermo che C sia necessariamente impossibile: affermo che una lettura plausibile la elimina.

**Controesempio:** box [100,110], z=0,2, midpoint 105; barra low 99,5, close 101. Soddisfa il failure test LONG di C, ma “through L destroys the box” può distruggere il suo prerequisito prima della valutazione. Un executor può emettere C, un altro ritirarla.

Anche il rinnovo non è completo. A nasce al “primo” qualificante, ma non è definito primo rispetto a quale reset. Un impulso resta qualificante per cinque barre; il primo episodio viene speso da un nuovo high prima della reazione. Crearne uno a ogni barra ricostruisce gli ancoraggi; aspettare un nuovo attraversamento false→true può escludere la reazione successiva. B/C possono ricreare, alla scadenza, un box quasi identico dai medesimi dati e consumare nuovi tentativi pur senza nuova informazione.

**Correzione minima:** separare oggetto box, tentativo di breakout B e tentativo di failure C. Specificare invalidazione per close/low e ordine di elaborazione; una penetrazione rientrata non deve distruggere automaticamente il riferimento che C deve leggere. Dichiarare per famiglia l'evento di nascita, consumo, cancellazione e rinnovo, inclusi i tentativi respinti dai gate. Un nuovo ID deve richiedere nuova evidenza strutturale nominata, non soltanto scadenza o nuovo hash di una finestra scorrevole. Non reintrodurre un massimo storico globale. Rendere esplicito che B richiede entrambi i conteggi di touch: “if both edge conditions fail” è ambiguo rispetto al requisito precedente.

### B2 — Fase, contesto e scenario non compongono ancora una funzione totale

**Riferimenti:** §§4–6, 10.

La fase REACTION viene indicata come licenza per A, ma A richiede una reazione geometrica e assenza di espansione opposta, non necessariamente phase=REACTION. C viene associata a ROTATION, ma la regola effettiva ammette BALANCED e qualunque fase non EXPANSION. Manca una decisione su quale definizione prevalga. Mancano inoltre le transizioni dei candidati quando il contesto 1h cambia dopo l'arm.

**Controesempio:** contesto BALANCED, fase TRANSITION, failure C geometricamente valido. La tabella delle fasi suggerisce nessun C, il predicato §6C lo permette. Oppure un B LONG è armed con 1h BALANCED; al close orario 1h diventa DOWN e nello stesso dispatch arriva il trigger. Non è detto se cancellare, mantenere o soltanto annotare il conflitto.

Il MarketView è incompleto anche senza candidati: BALANCED 1h e EXPANSION 15m non rientrano chiaramente nei casi UP/DOWN, BALANCED “in rotation/compression”, UNCERTAIN per scenario contrario armed. Inoltre un contesto 1h BALANCED può avere un breakout B LONG valido: la direzione attesa della call e quella del pannello principale devono essere spiegabili insieme. Le descrizioni direzionali 4h/day e l'invalidazione della view sono nominate, non definite interamente.

**Correzione minima:** usare i predicati di famiglia come autorità; la fase condivisa li descrive e abilita solo dove il metodo lo dichiara espressamente, senza un secondo veto implicito. A ogni dispatch applicare prima aggiornamento contesto e invalidazioni, poi arm/trigger/selezione. Specificare se ciascun requisito 1h vale alla nascita, all'arm e/o al trigger; raccomando riverifica al trigger, con motivo di ritiro esplicito. Definire una tabella totale di MarketView con priorità, scenario principale e alternativa. Tenere distinti **contesto osservato** e **aspettativa condizionale**: l'etichetta 1h UP non è da sola una previsione professionale a 1–4h. Per 4h/day scegliere una descrizione deterministica semplice o limitarli esplicitamente a location; niente formule lasciate all'executor.

### B3 — Il set dei livelli può produrre target diversi a parità di evidenza

**Riferimenti:** §§3, 6, 8.

La zona usa una S15 “frozen” senza precisare per ogni landmark se congelata alla sua nascita o all'episodio che la consulta. “Opposing” e retirement dei period levels non hanno regole complete; non è esplicito quando congelare il target rispetto alle revisioni pre-issue e ai nuovi pivot confermati.

**Controesempio:** un massimo 100 nasce con S15=10; quando nasce il candidato S15=20. La near edge può essere 99 oppure 98. Un close precedente a 101,5 ha superato la far edge della prima zona ma non della seconda: cambiano eleggibilità, target e call. Nessuno dei due executor deve inventare la risposta.

**Correzione minima:** attribuire a ciascun oggetto ownership della scala/zone, known_at e regola di retirement. Raccomando zone del landmark immutabili dalla sua creazione, zone del setup dalla creazione dell'episodio; selezione fra oggetti eleggibili al trigger, congelata all'issue. Definire gestione delle zone che contengono già il prezzo, delle sovrapposizioni e del caso C senza landmark prima del midpoint. Una zona attraversata non diventa automaticamente supporto/resistenza opposta. La scelta del target più vicino resta una convenzione economica, non viene corretta scegliendo quello più redditizio.

### B4 — L'entry area pubblicata non coincide necessariamente con l'ingresso valido

**Riferimenti:** §§7–8, 11.

La fascia ±0,25 S15 è un contenitore geometrico. Il gate reward/risk viene valutato su un prezzo p, ma §11 accetta un open dentro la fascia con entry precedentemente consentita: non richiede esplicitamente di ricalcolare la stessa adeguatezza su quell'open. Live usa il midpoint, mentre un ingresso immediato LONG si confronta con ask e SHORT con bid.

**Controesempio:** LONG, V=99.700, T=100.700, trigger=100.000, S15=400: fascia [99.900,100.100]. Con K=14 bps, a 100.000 il rapporto è (70−14)/(30+14)=1,27; a 100.100 è circa (59,94−14)/(39,96+14)=0,85. L'open differito può dunque essere dentro la fascia e già inammissibile. Analogamente midpoint 100.090 con ask 100.110 non rende utilizzabile un limite superiore 100.100.

**Correzione minima:** mantenere la fascia strutturale immutabile, ma derivare e mostrare l'**insieme corrente dei prezzi ammissibili**, intersezione con geometria, costi e condizioni temporali. Live verificare il lato pertinente della quote e la sua freschezza; storico verificare l'open ipotetico con gli altri prerequisiti noti prima dell'open. Non usare high/low/close successivi per concedere quell'ingresso. Dichiarare se lo spread è già incorporato nel prezzo lato quote o aggiunto all'envelope: non addebitarlo due volte. La liquidità osservata resta indicativa senza size/impact, che rimangono fuori dal trader.

### B5 — Exit guidance, progresso e tesi attiva possono creare blocchi artificiali

**Riferimenti:** §§8–9.

Gli stati terminali non includono esplicitamente il ritiro della tesi per early-exit. Premise failure e STALLED producono EXIT_GUIDANCE, ma non è definito se la tesi continui a occupare l'unico posto attivo. STALLED oscilla fra “compare last fresh close” e “if no displacement occurred”: massimo favorevole intrabar, massimo dei close e ultimo close sono tre regole diverse. Non è chiaro se STALLED imponga uscita o una nuova valutazione non specificata.

**Controesempio:** B perde la premessa dopo 30 minuti senza toccare V; viene emessa exit guidance. Un C opposto diventa valido, ma il B potrebbe restare ONGOING fino alla scadenza a sei ore e sopprimerlo. Oppure il prezzo raggiunge +0,6 S15, torna a zero al checkpoint: con MFE non è stalled, con ultimo close sì.

**Correzione minima:** rendere terminale il ritiro esplicito della raccomandazione, con motivo THESIS_FAILED/STALLED secondo una regola scelta dal Director. L'eventuale uscita ipotetica ancora in attesa non occupa lo slot delle raccomandazioni. Una chiusura temporanea dell'entry per prezzo/evento resta invece non terminale. Per il checkpoint raccomando, come semplice traduzione del testo, il massimo displacement favorevole dei close completi post-issue rispetto al riferimento iniziale, non gli estremi intrabar; registrare se la mancata progressione termina la guidance. Nessuna delle alternative è già economicamente validata.

Raccomando mantenere inizialmente una sola raccomandazione attiva, ma registrare tutti i candidati soppressi da questo limite. È una scelta di coerenza editoriale del consiglio, non gestione di una posizione umana. Non consentire riapertura dopo ritiro definitivo solo perché il prezzo torna nella fascia.

### B6 — Tempo ancora disponibile e contatti a cavallo dell'issue

**Riferimenti:** §§6, 9, 11; R2 §5.

Una call può restare entry-available quasi fino alla scadenza pur esponendo una durata minima molto più lunga del tempo residuo. In recorded/live un minuto pubblicato dopo l'issue può inoltre comprendere estremi anteriori all'issue. L'esclusione della sola barra di detection non risolve tutti i casi.

**Controesempi:** B a 5h59m dall'issue è di nuovo dentro fascia e adeguato, ma promette 30m–4h con un solo minuto residuo. Separatamente, issue alle 10:00:30; la barra [10:00,10:01) tocca T alle 10:00:05 e poi chiude sotto T. Leggerne il massimo come successo della call inventa un contatto successivo alla pubblicazione.

**Correzione minima:** distinguere orizzonte originario della tesi, tempo residuo e durata prevista per un ingresso ora. Definire un requisito di tempo residuo per nuovi ingressi; riutilizzare il limite inferiore della durata attesa di famiglia è una convenzione iniziale semplice, da registrare e valutare, non una legge. Non spostare il deadline per riaprire l'entry.

Per i contatti post-issue certificati usare barre con start non anteriore alla pubblicazione. Un estremo nella barra che attraversa la pubblicazione è temporalmente ambiguo senza osservazioni più fini; dichiararlo, senza assegnarlo arbitrariamente al prima o al dopo. Quote effettivamente osservate dopo l'issue possono aggiornare la praticabilità corrente, non ricostruire tutto il percorso. Applicare la stessa distinzione all'arm ritardato: un close successivo può confermare il trigger, ma l'intero low della barra non è necessariamente post-arm. Esplicitare la conservatività scelta. Conservare l'ordine R2, inclusa scadenza prima di nuova pubblicazione a pari tempo/cursor.

### B7 — La valutazione non è ancora preregistrata fino all'ultima convenzione

**Riferimenti:** §11 e MP-001-PARAMETERS.json.

Il “registered exit delay” non è nel registro; l'ordinamento fra protective stop/target, exit guidance e uscita differita non è completo. Non è definito il trattamento di possibili contatti precedenti a un gap, né la convenzione completa di notional per funding/costi. Sei ore di tail coprono il deadline massimo ma non necessariamente delay d'uscita e allineamento al minuto.

**Controesempio:** exit guidance alle 12:00:30, uscita ipotetica alle 12:02, stop toccato alle 12:01:20. Chi usa il primo messaggio esce al successivo open; chi lascia attiva la protezione fino al fill esce allo stop. Oppure call B appena prima della fine della finestra: deadline a +6h e fill a +6h2m, fuori dal tail. Un risultato diverso non può dipendere da un default nascosto.

**Correzione minima:** registrare delay d'uscita, arrotondamento al minuto, stato pending-exit e tabella di collisioni. Raccomando che target/stop ipotetici restino attivi sino all'uscita modellata; un contatto osservabile prima di essa prevale. Se l'ordine intrabar non è inferibile, mantenere bounds/AMBIGUOUS. Dopo un gap non classificare come primo contatto certo quello successivo senza sapere cosa è accaduto nel tratto mancante.

Registrare una convenzione normalizzata di esposizione, per esempio quantità sintetica costante equivalente a una unità di notional all'ingresso, senza introdurre size umana; specificare valore di riferimento al settlement, fee su entry/exit e confini temporali dei flussi. Se mancano rate, tempi o prezzi necessari, mantenere PRICE_NET_ONLY. Estendere il tail dell'allowance tecnica necessaria a delay/allineamento oppure dichiarare anticipatamente la censura attesa. La baseline deve usare gli stessi confini di osservabilità.

Chiarire inoltre che i profili di costo alternativi applicati alle stesse call misurano sensibilità dell'esecuzione; se cambiano il gate di emissione, diventano versioni distinte del metodo e non un semplice ricalcolo del P&L.

### B8 — Identità della configurazione e modalità di evidenza incomplete

**Riferimenti:** §§7, 10–12 e registro JSON.

Dislocation 25 bps / multiplo 3 / 60 slot, alcuni lookback, le nuove decisioni di lifecycle e l'exit delay non sono tutti nel registro. Il registro non deve essere considerato l'identità completa del comportamento se la prosa aggiunge regole. Il calendario ricostruito e il gate dislocation solo live possono inoltre cambiare la selezione delle call pur usando lo stesso nome di modello.

**Controesempio:** due run hanno stesso JSON ma una usa 25 bps e l'altra 50; cambiano call senza cambiamento del config hash. Un calendario retrospettivo elimina call prima di un evento rischedulato senza prova che quel nuovo orario fosse noto allora. Oppure una dislocation blocca live una call che il replay concede con gli stessi prezzi di riferimento.

**Correzione minima:** identità composta da versione delle regole, registro completo dei parametri comportamentali e profilo di capacità/evidenza. Il calendario strict-as-known ammette versioni soltanto dalla disponibilità dimostrata; dove ignota, coverage UNKNOWN. La ricostruzione resta un ramo dichiarato di sensitivity/reconstruction, non prova causale primaria. La politica di dislocation deve essere applicata dove esistono gli stessi input oppure identificata come differenza del profilo live: nessuna pretesa di call-identità fra capacità diverse. I cambi di coverage devono essere eventi visibili, non un passaggio silenzioso a un metodo diverso.

## 4. Ipotesi economiche e limiti del playbook: non sono bug

| ID | Ipotesi / controesempio sintetico | Disposizione minima |
|---|---|---|
| E1 | **Target vicino + costi possono sterilizzare il metodo.** Con soglia 1,2 e costo K, serve G ≥ 1,2Q + 2,2K. A K=14 bps il solo termine costi è 30,8 bps; se Q=20 servono G≥54,8 bps. Un setup con 40 bps fino al target e 20 di rischio fallisce pur avendo rapporto lordo 2. | Non eliminare costi né allontanare T per farlo passare. Registrare distribuzioni di G, Q, K e margine dal gate per famiglia, inclusi scarti. I 14/20 bps sono scenari dichiarati, non misure verificate. |
| E2 | **A resta sensibile alla geometria della reazione.** Una reazione poco profonda offre poco ritorno verso B; usare l'high dell'intera barra del minimo come K può attendere quasi tutto il recupero. | Conservare come traduzione iniziale, ma non dichiarare risolto il problema RP-001 della geometry floor. Misurare dove si perde spazio nella sequenza impulso→reazione→trigger→delay, senza torneo di trigger. |
| E3 | **B e C condividono un dominio ristretto.** Un range ampio e regolare privo di recente compressione non genera il box e quindi non può produrre C. Un breakout senza retest non produce B. | Accettare questa copertura iniziale, rinominando C come failure test di box qualificato da compressione; non chiamarlo metodo generale per mercati laterali. Mostrare tempo di dominio supportato e non supportato. |
| E4 | **Nearest-level cap attribuisce autorità forte a ogni ostacolo eleggibile.** Un piccolo pivot 15m poco sopra l'entry può eliminare una continuazione nonostante una destinazione maggiore lontana. | La fonte non prova che ogni pivot sia una barriera economica. Tenere la convenzione per una prima versione coerente, ma tracciare fonte/età/tipo del livello che limita la call. Non introdurre subito uno score di “forza”. |
| E5 | **Priorità A>B>C e una sola call possono mascherare complementarità.** A occupa lo slot mentre un successivo B con tesi distinta non viene pubblicato. | Conservare come convenzione iniziale soltanto con motivi SLOT_OCCUPIED/PRIORITY, durata del blocco e candidati soppressi. Nessun ranking di famiglie da pochi risultati; correggere prima B5. |
| E6 | **Calendario ±15m e checkpoint a metà vita non provano fine del rischio o decadenza dell'idea.** Dopo una barra post-evento completa il mercato può ancora essere disordinato; una call può svilupparsi lentamente senza essere errata. | Chiamarli politiche iniziali, non soglie professionali universali. Event unblock richiede comunque nuovo scenario e quote utilizzabili; i timer non sostituiscono il contenuto informativo. Valutarli nell'intero processo. |

La frequenza non si inferisce dalle formule né da sei casi RP-001. Serve successivamente una valutazione Owner sull'app con denominatori temporali: periodo totale, periodo coperto, tempo leggibile, dominio supportato, tempo con entry utilizzabile e lunghezza dei periodi senza call. Il requisito “qualche opportunità a settimana” rimane un obiettivo di utilità da verificare, non una quota da generare.

## 5. Ciclica, news e derivati: giudizio sulle fonti e sulle decisioni

### Ciclica

M03 descrive alternanza contrazione/espansione e un possibile confronto fra misure di volatilità su durate differenti; mette in guardia dal forzare periodicità esatte. Questo sostiene il **concetto** adottato, non i parametri 4/20, ER6, la classificazione esaustiva delle fasi o una previsione del prossimo minimo. M01 sostiene le categorie di pullback, breakout e failure test, non queste specifiche sequenze numeriche BTC.

La ciclica non è fittizia: influenza la creazione del box e la lettura della reazione. Tuttavia phase age non influenza ancora una decisione esplicita e non deve apparire come stima del tempo mancante a una svolta. La review ammette questa prima implementazione limitata; non conclude che altre metodologie cicliche siano inutili. Se il Director vuole assegnare in seguito autorità predittiva a un metodo ciclico ulteriore, la lacuna precisa è: osservabile causale di fase, regola di revisione, evento futuro previsto, decisione modificata rispetto alla fase già presente. Nessuna di queste richiede ora un censimento di scuole o cinque anni di minuti.

### Eventi e notizie

Il calendario è un modulo utile di restrizione temporale. Non è equivalente a comprendere sorpresa, aspettative, tono, contenuto politico e reazione relativa alle attese. Per la prima versione è accettabile **non avere una direzione macro**.

La promessa di misurare la risposta va però resa piccola e concreta: riferire ogni EventContext alla finestra e al riferimento prezzo noti, mostrare displacement/range rispetto alla scala pre-evento e l'eventuale reclaim di livelli già esistenti; evitare etichette causali come “sale grazie alla notizia”. Il suo effetto iniziale può limitarsi a sblocco dopo nuova valutazione e descrizione dello scenario, senza un nuovo voto. Se tale record non viene specificato, dichiarare “calendario/rischio-evento soltanto”, non “interpretazione della risposta implementata”.

I calendari ufficiali citati sono fonti identificate, non dimostrazione dei loro vintages storici. Anche Employment Situation necessita di una fonte ufficiale e provenance esplicita propria. La disponibilità di as-known calendar per il periodo scelto è una verifica mirata dei dati, non una ragione per bloccare il nucleo price-led. Gli incidenti venue/BTC richiedono tassonomia e regola di risoluzione se attivati; in assenza di tape restano capacità non coperta.

### Derivati e liquidità

Mark, index e funding hanno ruoli distinti e corretti in linea di principio. Non serve OI per giustificare una tesi che non usa OI. Non serve un order book annuale per valutare un metodo di barre con esecuzione storica dichiaratamente modellata.

La dislocation è un limite di qualità/praticabilità, non prova di arbitraggio, liquidazioni o direzione. È necessario stabilire segno, denominatore e finestre contigue della misura; la sua soglia resta convenzione. Funding passato non rivela automaticamente crowded positioning; funding futuro realizzato può entrare soltanto nell'outcome. Una quote misura uno spread e prezzi visibili, non garantisce riempimento, impatto o slippage per il capitale dell'Owner.

LIB-005 offre esempi e principi professionali selezionati, non un algoritmo BTC riproducibile. LIB-008 avverte della ridondanza di famiglie di filtri, non dimostra che tutte le trasformazioni non lineari siano equivalenti. EXT-003 riguarda livelli pubblicati su FX con condizioni diverse: non convalida un cap universale su ogni pivot BTC. Questi limiti impediscono promesse d'autorità; non impediscono una traduzione dichiarata e valutabile.

## 6. Dipendenze minime e complessità da evitare

| Capacità | Dati realmente necessari | Cosa non deve diventare gate generale |
|---|---|---|
| Nucleo A/B/C e MarketView | Trade 1m causali, metadata/versione tick, aggregati completi 15m/1h, stato continuo fra chunk; volume tipizzato per la scheda partecipazione. | Quote storiche annuali, OI, sentiment, libro ordini, funding noto futuro. |
| Contesto più ampio | Stesso strumento; 4h/day quando disponibili; precedenti estremi week/month con provenance. | Tutti gli orizzonti READY, sei mesi di warmup fine o splice spot/perpetual. |
| Actionability live | Bid/ask misurati e freschi, stato connessione, modello fee/slippage dichiarato, evidence freshness e timer. | Account, capitale, leva, size, routing ordini. |
| Calendario causale | Record tipizzati versionati, prova di disponibilità e coverage. | Archivio news completo prima del primo metodo. |
| Diagnostica dislocation | Slot contemporanei trade/mark/index e storia sufficiente alla baseline scelta. | Bloccare tutto quando una diagnostica opzionale è assente. |
| Outcome comprensivo di funding | Tempi/rate effettivi e valore richiesto dalla convenzione normalizzata. | Confondere missing con cashflow zero o usare outcome futuri per selezionare call. |
| Intermittenza locale | Checkpoint professionale, catch-up dichiarato, gap e rivalutazione presente. | H24, collezione quotidiana lunga o VPS. |

La base di 96h è un envelope iniziale ragionevole per questa proposta, non un teorema né requisito per i contesti opzionali. Le dipendenze effettive devono essere calcolate da barre/ancore e non da un generico numero di ore. Per la scale 1m di §4 non trovo un utilizzatore decisionale: rimuovere il warmup di 21 minuti come gate autonomo, oppure nominare la regola che lo usa. Non togliere il monitoraggio 1m necessario al lifecycle.

**O1 — Ridurre stato inutilizzato.** Controesempio: si acquisiscono sei mesi di 1m solo per riempire sei monthly records quando il metodo usa soltanto il precedente estremo. Correzione: inventario per campo realmente letto; retention opzionale non diventa requisito di acquisizione. Nessuna necessità ora di un nuovo servizio context o di una DSL.

**O2 — Evitare ramificazioni equivalenti.** In A, con dati continui e V sopra A, il protective stop verrà normalmente toccato prima di un close sotto A. Quel premise-failure può essere un controllo esplicativo ma non è una seconda protezione indipendente. Correzione: descriverne la subordinazione senza aggiungere un secondo motore di uscita.

**O3 — Non moltiplicare documenti.** Correggere proposta e registro, poi una disposizione Director con finding→decisione→evidenza di chiusura. Niente nuovi framework di governance o tanti registri sovrapposti. La distinzione semantic.v2 advisory / evaluation resta sufficiente.

## 7. Separazione guidance, esecuzione ipotetica e valutazione

Conservare tre identità distinte:

1. **Call e revisioni:** ciò che il metodo ha consigliato con l'evidenza allora disponibile. Entry valida ora, tesi, stop/target, limiti e scadenza. Nessuna posizione umana inferita.
2. **Percorso ipotetico:** se/quando una persona convenzionale avrebbe potuto entrare secondo delay, prezzo ammissibile e disponibilità; poi uscita modellata. NO_ENTRY non diventa un trade vincente perché T viene raggiunto dopo.
3. **Valutazione:** prezzo lordo/netto, funding quando misurabile, successo target, perdita, uscita temporale, ambiguità/censura e copertura. Un expiry positivo non è automaticamente target success; una call senza ingresso non è una perdita d'esecuzione.

Le revisioni non riscrivono la geometria originaria, ma possono ritirare l'attuale raccomandazione. Il motore di valutazione non governa la disponibilità futura di call. In particolare una posizione sintetica ancora in attesa di uscita non rappresenta la posizione dell'Owner.

Il confronto horizon-only è utile **condizionato alle call selezionate e agli stessi ingressi**; non dimostra qualità della selezione direzionale né superiorità rispetto al non operare. La persistence forecast oraria è un riferimento distinto: non è un benchmark P&L matched. Definire separatamente il campionamento della MarketView del metodo, inclusi BALANCED/UNCERTAIN/UNAVAILABLE e astensioni, prima di attribuirle un'accuratezza.

Conservare development/protected e contaminazione esplicita. La specifica di un metodo con parametri prima dei risultati non equivale a validazione. Dopo una modifica ispirata dai risultati protetti, quel periodo diventa development. Nessuna necessità di vedere l'intero anno prima di implementare il processo coerente; nessuna autorizzazione a vederlo con questa review.

## 8. Lezioni RP-001: cosa è corretto e cosa resta aperto

| Lezione del Director review RP-001 | MP-001 |
|---|---|
| Ritardo dei pivot come contesto obbligatorio | Migliorato: il contesto 1h usa il percorso, non attende due pivot. Rimane la normale latenza di un metodo su close, da dichiarare. |
| Bias sul singolo impulso | Migliorato: percorso a sei transizioni; non prova però copertura di ogni staircase. |
| Blocco da high-water d'epoca | Rimosso nominalmente; B1 deve impedire che un reset indefinito ne ricrei l'effetto o l'opposto spam. |
| Floor geometrico e costi dominanti | Non risolto per definizione: E1/E2/E4 restano ipotesi del metodo completo. |
| Ownership della target-zone | Ancora incompleta: B3. |
| Wording non corrispondente agli stati | B2/B5 sono da chiudere prima della UI reale. |
| Sei cutoff insufficienti per frequency/edge | Invariato: non uso quei risultati per scegliere parametri o famiglie. |

## 9. Chiusura proposta al Director

**Disposizione raccomandata: REVISE, mantenendo il metodo integrato.** Le correzioni bloccanti sono semantiche e causali; non richiedono nuovi outcome. Le ipotesi E non devono diventare ulteriori gate di ricerca prima del codice.

Ordine di chiusura MP-001, senza attivare pacchetti esecutivi:

1. Decidere B1–B3: episodi/box, contesto e scenari, ownership dei livelli. Rendere il modello deterministico per ogni stato supportato.
2. Decidere B4–B6: prezzo ammissibile, lifecycle completo, tempo residuo e confini post-pubblicazione.
3. Decidere B7–B8: percorso ipotetico e collisioni, tail, identità/versioni e modalità di evidenza. Aggiornare il registro senza ricerca di soglie.
4. Correggere le dichiarazioni di copertura professionale e l'inventario minimo dei dati. Pubblicare la disposizione Director e soltanto poi valutare l'attivazione separata di R3/WP-009.

Criteri di chiusura documentale e futura accettazione ingegneristica mirata:

- Il box del controesempio C ha una sola interpretazione; nessun ordine interno dei callback elimina arbitrariamente la famiglia.
- Gli episodi persistentemente qualificanti, consumati e rinnovati hanno ID/transizioni attesi; nessuno sliding reset nascosto e nessun high-water globale.
- Tutte le combinazioni supportate di contesto/fase danno una MarketView determinata; i cambi 1h fra arm e trigger sono risolti.
- Due implementazioni scelgono lo stesso landmark, la stessa zona e lo stesso target al medesimo cutoff.
- Un prezzo dentro la fascia ma fuori dalla geometria ammissibile non genera live ready-now né ingresso ipotetico.
- Exit guidance terminale libera la raccomandazione senza attendere un fill sintetico; chiusura temporanea dell'entry conserva il corretto ID.
- Nessun estremo precedente alla pubblicazione diventa un esito della call; i minuti straddling restano espliciti.
- Collisioni stop/target/exit, delay, gap, funding, deadline e tail hanno esiti attesi e ambiguità preservate.
- Restore, fast/paced/STEP e checkpoint cadence preservano lo stesso percorso sul medesimo command tape, senza promettere equivalenza fra disponibilità modellata e ricevute live non registrate.
- Il report mostra funnel completo, ragioni sovrapposte di scarto, slot occupato, durata entry e tempi senza opportunità. Zero call porta a una diagnosi del processo, non a “aspettare altri segnali”.

Non propongo come condizione di chiusura win rate, minimo di call su fixture sintetiche o performance di un singolo segnale. Fixture positive provano raggiungibilità e correttezza, non frequenza reale. Quest'ultima e l'utilità economica appartengono alla successiva valutazione integrata, lanciata dall'Owner nell'app.

## 10. Riferimenti verificati e limiti della review

I riferimenti interni sono al commit indicato, non al main mobile:

- [FOUNDATION.md](https://github.com/C-Gian/algorithmic-trader/blob/cd8665ab17464f164437b9857c23aefb5342be10/FOUNDATION.md), STATE.md, task.md, AGENTS.md.
- [MP-001 proposta](https://github.com/C-Gian/algorithmic-trader/blob/cd8665ab17464f164437b9857c23aefb5342be10/delivery/MP-001-INTEGRATED-METHOD-PROPOSAL.md), MP-001-PARAMETERS.json e MP-001-REVIEW-BRIEF.md.
- [RP-001 Director review](https://github.com/C-Gian/algorithmic-trader/blob/cd8665ab17464f164437b9857c23aefb5342be10/research/first_trader/RP-001-DIRECTOR-REVIEW.md), limitatamente alle lezioni esplicite e senza riaprire outcome.
- [R2 temporal specification](https://github.com/C-Gian/algorithmic-trader/blob/cd8665ab17464f164437b9857c23aefb5342be10/delivery/WP-008-R2-CAUSAL-TEMPORAL-SPEC.md).
- knowledge/registry.yaml, knowledge/external_registry.yaml e passaggi pertinenti dei dossier LIB-005/LIB-008: provenance e limiti, non autorità sulle regole.
- Controllo primario mirato del 3 ottobre 2026: Adam H. Grimes, [Fundamental Trading Patterns](https://www.adamhgrimes.com/fundamental-trading-patterns/) e [Cycles, Cycles Everywhere](https://www.adamhgrimes.com/cycles-cycles-everywhere/). Usati soltanto per verificare categorie professionali e portata del concetto di ciclo; nessuna soglia o evidenza di edge BTC deriva da queste pagine.

Non sono stati verificati nuovi endpoint/coverage di mercato, tariffe effettive, disponibilità storica dei calendari o performance del metodo. Il report è una review metodologica e dei contratti dichiarati, non una nuova certificazione del codice R2 o una validazione economica.
