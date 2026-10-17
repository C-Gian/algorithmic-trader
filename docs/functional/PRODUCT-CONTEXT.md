# Algorithmic Trader — prodotto, decisioni e contesto completo

Versione documentale: 1.9 — 17 ottobre 2026. Responsabile della sintesi: Astra; aggiornamento Director sui requisiti espliciti dell'Owner.

Questo è il documento funzionale centrale del **nuovo** progetto di Gian. È scritto per poter essere consegnato da solo a una nuova chat: spiega obiettivo, organizzazione, requisiti, ragioni delle scelte, limiti e questioni ancora aperte. Non è una specifica matematica dell'algoritmo, una dichiarazione di efficacia o un'autorizzazione a operare con denaro reale.

La sintesi deriva dalle decisioni e preferenze espresse nella conversazione con Gian e dalle consegne del progetto precedente. I risultati storici qui ricordati sono evidenze riportate dal progetto precedente, non ricalcoli effettuati per questo documento. Le risposte brevi come «sì» prive della domanda originale non vengono trasformate in dettagli tecnici presunti.

## 1. Il progetto in parole semplici

Vogliamo costruire un assistente che osservi Bitcoin continuamente e ragioni su quello che sta succedendo. Deve usare più strumenti di analisi in relazione al contesto, spiegare quali sviluppi considera plausibili e riconoscere quando esiste un'operazione sensata. Quando è abilitata l'esecuzione, deve anche aprire e gestire l'operazione sul conto collegato secondo regole stabilite.

Non basta dire «il prezzo potrebbe salire». Bisogna distinguere se conviene entrare, a quali condizioni, dove la lettura perde significato, quale destinazione si considera e per quanto tempo. Dopo l'ingresso il lavoro continua: nuove informazioni possono giustificare attesa, protezione del guadagno, revisione dell'obiettivo, uscita parziale o chiusura.

L'immagine di riferimento dell'Owner è un **trader esperto digitale**. È un obiettivo funzionale, non una capacità già ottenuta. Non promettiamo di prevedere tutto, evitare ogni perdita o riconoscere sempre una normale oscillazione rispetto a un'inversione. Cerchiamo decisioni motivate e utili nel complesso, verificandone i risultati al netto dei costi.

Il progetto può durare anni. Gian accetta studio e sviluppo progressivi, ma vuole che ogni macrofase avvicini al prodotto: non una sequenza indefinita di dossier, piccoli esperimenti scollegati e rifiniture grafiche.

## 2. Che cosa esiste oggi e che cosa no

La repository nuova è `C-Gian/algorithmic-trader`. La precedente è `C-Gian/algorithmic-trader-archive`.

Aggiornamento 16 ottobre: oltre alle tre utilità tecniche recuperate (intervalli temporali, arrotondamento e impronte), esiste la dashboard locale React/TypeScript con provider simulato separato e scenari deterministici. La macrofase UI, comprese correzioni e navigazione superiore richiesta dall'Owner, è conclusa con review Director e riscontro positivo di Gian. È stato poi consegnato OBS-001: motore osservativo causale e primo studio storico integrato nella stessa dashboard; calcoli e tabelle verificati dal Director, ora chiuso tecnicamente dopo le correzioni R1. Il limite di comprensione Owner è conservato, senza dichiarare una prova positiva o riaprire una macrofase UI. Esiste ora anche il primo candidato decisionale CAND-001, con esecuzioni storiche modellate e consultazione nella stessa app: fase DEV2023–2024 consegnata con risultato riportato negativo, correzioni R1 accettate tecnicamente dal Director a3ae7b75. Il Director mantiene la versione iniziale senza revisione metodologica. Il confronto aggiuntivo2025 su dati già esposti è stato elaborato con la stessa versione e si consulta nella stessa app con un bundle separato: risultato riportato negativo, consegna accettata tecnicamente dal Director a4ff5046. Verificati codice, test pertinenti, build e, sui CSV pubblici, esecuzione/costi della prima operazione2025; non è un ricalcolo autonomo dell'intero ledger. V1 non promossa all'uso operativo; evidenza negativa conservata senza varianti scelte sul2025. Prova concreta Owner svolta il17ottobre con feedback articolato: apprezza il percorso decisione/astensione/registro, ma linguaggio economico e stati dell'operazione risultano insufficientemente comprensibili e segnala difficoltà di ritorno dai dettagli. Non è un'accettazione d'uso senza riserve. Astra ha ora autorizzato APP-001 per comprensione, navigazione e avvio manuale dei backtest dallaUI con avanzamento reale; l'implementazione e le correzioni APP-001/R1 sono accettate tecnicamente dal Director sulla consegna ec19f22 (codice 3dd3f66): servizio locale, avvio/progresso/annullamento dalla UI, risultati salvati, costi mancanti dichiarati, avanzamento fermo alla lacuna, ritorni al registro e spiegazioni dei costi. La review comprende controlli mirati indipendenti. Dopo la richiesta di prova, il 17 ottobre Gian riferisce «ok, ora mi sembra molto meglio!»: riscontro positivo sul miglioramento d'uso, senza verbale di ogni passo. Il Director chiude APP-001 con questo limite e torna ad Astra per il ciclo metodologico; non apre ulteriori preparazioni UI. Non cambia la specifica della strategia o il perimetro dati. **Non esistono una strategia validata, un collegamento al conto o un esecutore di ordini reali.** Stato e incarico correnti precisano le verifiche e l'avanzamento.

Il vecchio motore non viene importato implicitamente. Il nuovo progetto non è una v0.8 e non eredita le soglie, gli scenari A/B/C, i profili di costo, le scadenze o la struttura delle prove precedenti. Il nuovo nome della repository non rende però sconosciuti i dati già studiati.

I requisiti delle sezioni seguenti descrivono il prodotto da costruire. Non sono una lista di funzionalità già implementate. Il file `STATE.md` della repository registra il progresso effettivo; `current_task.md` contiene l'unico incarico esecutivo corrente.

## 3. Che cosa è deciso, rinviato o ancora aperto

| Ambito | Decisione o stato |
|---|---|
| Obiettivo | Analisi continua, opportunità motivate e gestione dinamica; futura esecuzione automatica |
| Mercato iniziale | BTC; supporto LONG e SHORT |
| Posizioni | Una sola posizione BTC alla volta; niente aumento della posizione già aperta; uscite parziali ammesse |
| Grafici di analisi | Candele di 45 minuti e di un giorno, scelta dell'Owner; non sono durate obbligatorie delle operazioni |
| Durata delle operazioni | Variabile secondo la situazione; orientamento intraday/fino a pochi giorni, non investimento di lungo periodo; limite esatto da fissare |
| Modi d'uso | Solo call oppure call + esecuzione; Stop totale separato; chiusura posizione separata |
| Primo ambiente operativo | Demo con fondi virtuali; Binance è la preferenza iniziale dell'Owner, fattibilità del prodotto specifico da verificare |
| Denaro reale | Non autorizzato da questa documentazione |
| Budget | Prima fase gratuita sul PC dell'Owner; eventuale server economico in seguito, con approvazione |
| Ricerca | Studio dei segnali nel contesto storico BTC, prima/durante/fine dei movimenti; controlli anche su falsi allarmi e assenze |
| Fibonacci | Incluso fra gli strumenti da studiare; scelta causale degli estremi da definire |
| Ciclica classica ed Evoluta | Rinviate per la prima fase; non dichiarate inutili |
| Order book e alta frequenza | Fuori dalla prima fase |
| Strategia durante una prova | Fissa; il bot applica le regole, non le riscrive autonomamente |
| Successo | Risultato netto centrale, insieme a rischio sostenuto, completezza e solidità della valutazione |
| Capitale, leva e limiti numerici | Da discutere con Gian prima dell'esecuzione; nessun numero implicito |

Le regole tecniche che permettono di rispettare queste decisioni vanno specificate prima della relativa implementazione. Un campo aperto non autorizza Claude a riempirlo scegliendo una strategia.

## 4. Le persone e il modo di lavorare

**Gian è l'Owner.** Stabilisce obiettivi, preferenze, budget e autorizzazioni importanti. Vuole partecipare alla definizione della strategia e capire le decisioni in italiano semplice. Non deve conoscere finanza, statistica o dettagli tecnici per seguire la conversazione. Trasmettere un messaggio del Director non equivale ad approvare implicitamente ogni scelta contenuta nel messaggio.

**Astra è l'orchestratore.** Decide la direzione strategica e metodologica, i confini delle macrofasi, le scelte architetturali importanti e risolve conflitti sostanziali. Fornisce al Director una sub-roadmap eseguibile e criteri di chiusura. Interviene alla conclusione delle macrofasi, per problemi importanti o consulti mirati. Il suo costo rende inappropriato coinvolgerla in ogni correzione ordinaria.

**Il Director/ricercatore è la chat operativa principale.** Traduce la direzione in incarichi completi, svolge ragionamento teorico e analisi, guida Gian e Claude, decide i dettagli ordinari entro il perimetro approvato, verifica i risultati e porta la macrofase a chiusura. Non chiede ad Astra conferma per ogni commit. Escala quando serve una decisione che modifica obiettivo, metodo, rischio, dati autorizzati o architettura sostanziale.

**Claude Code è l'esecutore tecnico.** Implementa ciò che è stato definito, legge il codice necessario, risolve problemi di programmazione, svolge le verifiche pertinenti e riporta ciò che ha realmente fatto. Può e deve ragionare tecnicamente. Non riceve il compito aperto di scegliere la strategia di trading, interpretare autonomamente una bibliografia per inventare regole o decidere quali risultati finanziari siano soddisfacenti.

Il flusso normale è: Astra imposta una macrofase; il Director la gestisce autonomamente; Astra o Director scrive `current_task.md`; Gian chiede a Claude di leggerlo ed eseguirlo; il Director revisiona la consegna e procede con i passi già compresi nella macrofase. Alla fine comunica una sintesi ad Astra. Un task non deve costringere l'esecutore a completare il disegno metodologico per poter programmare.

## 5. Perché abbiamo ricominciato

Il lavoro precedente ha prodotto un motore deterministico, verifiche tecniche e una notevole quantità di conoscenza. Non ha dimostrato l'efficacia dell'adviser desiderato. La complessità dei documenti e la sovrapposizione di versioni rendevano inoltre facile recuperare istruzioni obsolete.

Gian ha chiesto un nuovo progetto per separare chiaramente le nuove decisioni. Ha anche chiesto di correggere tre problemi organizzativi: troppe escalation ad Astra, troppo ragionamento strategico delegato all'esecutore e troppa attività preparatoria rispetto allo sviluppo e all'uso concreto dell'app.

La ripartenza conserva le lezioni, non trasferisce automaticamente il vecchio metodo. Non cancella i fallimenti e non considera inutile ogni componente precedente. Il riuso deve essere esplicito, piccolo, revisionato e privo di dipendenze nascoste dalla vecchia strategia.

## 6. Le lezioni delle evidenze precedenti

Questa sezione è memoria del progetto, non un nuovo studio. I numeri servono a capire perché non dobbiamo presentare il vecchio motore come validato.

- Nel continuo v0.4 settembre–dicembre 2025 risultavano 13 call e 12 ingressi PRIMARY, con somma normalizzata circa −1,727%; funding non coperto.
- v0.5 produceva nello stesso confronto una sola call IMMEDIATE e nessun RETURN emesso. Eliminare operazioni non dimostrava superiorità economica.
- In quattro percorsi RETURN analizzati, il recupero locale richiesto era già incompatibile con la regione ammessa. v0.6 rendeva esplicita questa incompatibilità prima, senza dimostrare migliore capacità predittiva.
- La tabulazione MarketView a +1h, su 158 campioni direzionali esposti, riportava 77 corrispondenze contro 86 della persistenza. Non misurava l'intero adviser.
- Lo studio E sul carattere della reazione trovava confronti scarsi e concentrati: non sosteneva l'ipotesi, ma non dimostrava assenza generale di informazione. La variante a2x aggiungeva quattro successori e una conferma senza nuove call nel periodo studiato; non veniva promossa.
- Lo studio delle revisioni distingueva 28 prime conferme sulla prima formulazione e 61 su formulazioni successive. Una nuova formulazione non rende retroattivamente corretta quella abbandonata.
- La correzione v0.7 risolveva una contraddizione della promessa: un trigger già a destinazione o oltre non poteva promettere una successiva continuazione verso quella stessa destinazione. Era una correzione semantica, non una prova di guadagno.
- Il confronto direzionale con barriere speculari riportava +4,49 punti percentuali su 89 coppie in settembre–dicembre e +1,14 su 88 coppie in gennaio–aprile. I risultati descrittivi non autorizzavano promozione o conclusioni sull'utilità economica.
- La politica completa v0.7 riportava gennaio–aprile 2025: 4 call, 3 ingressi, 1 NO_ENTRY, somma normalizzata +9,64 punti base; settembre–dicembre: 1 call, 1 ingresso, +10,09 punti base. Erano risultati PRICE_NET_ONLY, non rendimento del capitale dell'Owner. Lo stress rendeva negativo il primo periodo. Opportunità troppo poche per un giudizio economico solido.
- I contributi su Evoluta e prezzo–volume lasciavano lacune di traducibilità nei materiali consultati. Non dimostravano che cicli o volume fossero inutili.

Le lezioni trasversali sono: correttezza del programma, coerenza della spiegazione, capacità di anticipare e risultato economico sono cose differenti. Avere poche call non prova inutilità; avere qualche guadagno non prova efficacia. Aggiungere una regola perché produce più call non è un miglioramento dimostrato.

## 7. Le domande a cui deve rispondere il bot

1. **Che cosa sta mostrando il mercato?** Movimento, contesto e strutture effettivamente osservati.
2. **Che cosa potrebbe succedere?** Aspettativa condizionata e alternative, senza inventare certezze.
3. **C'è un'operazione sensata adesso?** Prezzo, percorso, protezione, costi e tempo possono rendere non conveniente una direzione plausibile.
4. **Che cosa deve accadere prima di agire?** Condizioni ancora mancanti, solo se realmente definite dalle regole.
5. **Che cosa cambia durante l'operazione?** Nuove informazioni, ragione per mantenere o aggiornare il piano.
6. **Che cosa abbiamo davvero fatto e ottenuto?** Ordini, eseguiti, posizione, costi e risultato, separati dalle previsioni.

Se una condizione futura non è definita, il prodotto deve dirlo. Non deve inventare un livello da superare solo per riempire la schermata.

## 8. Segnali, contesto e decisione composta

Gli strumenti discussi per la prima fase sono struttura del prezzo e andamento del mercato, supporti/resistenze, medie mobili e relativi incroci, volumi, volatilità e Fibonacci. Sono famiglie da rendere precise e studiare, non una strategia già pronta né un elenco di indicatori da sommare.

Una media mobile può raccontare in parte lo stesso movimento già descritto da altre misure. Tre segnali concordi non sono automaticamente tre conferme indipendenti. Viceversa, un segnale poco utile da solo può diventare informativo in una particolare situazione. Non richiediamo indipendenza statistica fra tutti gli strumenti e non pretendiamo che ognuno guadagni autonomamente.

Il lavoro deve chiarire cosa osserva ogni strumento, quando lo si può conoscere, quale informazione aggiunge, dove è ridondante e come contribuisce alla decisione complessiva. Non sono approvati un punteggio a voti, pesi numerici, soglie, lunghezze delle medie o probabilità percentuali mostrate come se fossero già misurate.

La menzione del golden cross, per esempio, non approva automaticamente una regola di ingresso su un incrocio specifico. La presenza di Fibonacci nel progetto non approva una scelta arbitraria degli estremi dopo aver visto il seguito.

## 9. Fibonacci e ciclicità

Fibonacci entra nella ricerca iniziale. Occorre stabilire quali minimi e massimi siano riconoscibili in quel momento, come scegliere fra alternative e quando aggiornare la lettura. Si può rivedere un'interpretazione quando arrivano informazioni nuove, conservando quella precedente e il momento della revisione. Non si può ricalcolare il passato come se la scelta migliore fosse sempre stata nota.

La ciclicità classica e l'Analisi Evoluta interessano Gian e possono essere considerate in futuro. Nei materiali già esaminati non risultava sufficientemente ricostruita la procedura causale per scegliere e confermare l'origine di un ciclo e gestire origini concorrenti. Questo è un limite delle conoscenze disponibili, non una dichiarazione sull'assenza di un metodo dell'autore.

Per la prima fase sono rinviate. Non sostituiamo le lacune con regole nostre chiamandole Evoluta. Non riapriamo automaticamente una ricerca indefinita di video o libri. Un futuro recupero richiederà conoscenza nuova e pertinente.

## 10. Scala temporale e durata

Gian ha scelto di ragionare su grafici a **45 minuti e un giorno**. Una candela di 45 minuti riassume ciò che è successo in quei 45 minuti: non impone che il trade duri 45 minuti. Il grafico giornaliero serve a un contesto più ampio; il suo ruolo esatto sarà definito nella strategia.

Per ordini, stop e gestione può servire osservare prezzi più frequentemente. Questo non autorizza una strategia ad alta frequenza o venti operazioni al minuto. Una candela giornaliera ancora aperta non può essere usata come se la sua chiusura futura fosse già nota.

La durata desiderata è flessibile, orientata al trading e non all'holding. Occorre ancora definire l'orizzonte delle letture, la validità dell'ingresso e un limite temporale operativo. Sono tre concetti distinti. Le convenzioni di fuso, origine delle barre di 45 minuti e chiusura giornaliera devono essere esplicite; non si ereditano dalla vecchia repository.

## 11. Come vogliamo imparare dallo storico

L'Owner propone di studiare una storia BTC ampia, indicativamente tre anni, osservando movimenti rilevanti e segnali prima, durante e alla fine. L'obiettivo è costruire conoscenza prima di scegliere un insieme definitivo di regole.

Aggiornamento 17 ottobre: Astra autorizza per CAND-001 sviluppo 2023–2025 sulla stessa fonte/strumento, con inizializzazione da ottobre 2022. 2023–2024 per le iterazioni iniziali, 2025 confronto aggiuntivo già esposto, non validazione indipendente. Copertura/varietà effettive vanno misurate; tre anni non le garantiscono. Nessuna apertura 2026. Anche il termine «movimento rilevante» va definito: gli esempi di 500, 1.000 o 5.000 dollari non sono soglie approvate.

Un movimento identificato guardando il seguito è utile per studiare il mercato, ma non coincide con un trade che si sarebbe potuto aprire e chiudere in tempo reale. Il mercato non riparte ogni volta da una situazione neutra: movimenti si sovrappongono, contengono reazioni e possono continuare per molto tempo. Il criterio per delimitare gli eventi non deve produrre un ingresso perfetto con il senno di poi.

Studiare il prima serve a cercare informazioni anticipatrici. Studiare il durante serve a capire mantenimento, rischi e aggiornamenti. Studiare la fine serve a capire esaurimento e uscita. In tutti e tre i casi bisogna distinguere ciò che allora era osservabile da ciò che abbiamo riconosciuto dopo.

## 12. Ripetizioni, eccezioni e combinazioni

Si possono studiare prima strumenti singoli e poi relazioni fra strumenti. Non è approvata una ricerca automatica di tutte le coppie, triple e combinazioni fino a N. Il numero di combinazioni cresce e si può trovare una spiegazione convincente solo perché si è provato abbastanza.

La selezione delle combinazioni deve avere una motivazione: strumenti che descrivono aspetti differenti della stessa situazione o un contrasto concreto da comprendere. Non si cambia una regola a ogni eccezione. Si conserva la storia delle scelte, compresi tentativi senza sostegno.

Non basta cercare i segnali prima dei grandi movimenti. Per capire se avrebbero aiutato, dobbiamo anche sapere quante volte erano presenti senza il movimento e quante occasioni non erano riconosciute. Questo non richiede che le regole finali siano già pronte: durante l'esplorazione possiamo confrontare osservazioni e situazioni, distinguendo le ipotesi provvisorie.

Le occorrenze vicine possono appartenere allo stesso episodio. Non vanno presentate come molte prove indipendenti solo perché abbiamo molte candele o revisioni.

## 13. Sviluppo, simulazione e verifica separata

Scorrere le candele una alla volta è necessario per simulare il presente: il programma deve utilizzare soltanto informazioni disponibili a quel momento. Questo controllo non cancella però il fatto che chi ha progettato le regole potrebbe aver già studiato il seguito di quei prezzi.

Possiamo tornare sui dati di sviluppo per imparare e correggere. Quelle esecuzioni misurano il comportamento sul materiale usato per costruire il candidato. Per una verifica distinta occorre fermare regole e convenzioni prima di osservare il risultato di un altro periodo. Se poi cambiamo le regole usando quel risultato, anche quel periodo entra nella conoscenza di sviluppo.

Tre anni possono contenere situazioni diverse, ma non garantiscono che una relazione continui in ogni mercato futuro. Non chiediamo infallibilità: chiediamo che il giudizio non confonda apprendimento sugli esempi con verifica separata.

La strategia non si riscrive durante una run. A fine prova Astra o Director analizza il risultato e propone eventuali modifiche motivate, registrate come versione distinta. Le regole possono prevedere comportamenti diversi secondo il contesto: applicarli non è apprendimento autonomo della strategia.

**Requisito esplicito Owner del17ottobre2026: eseguire il backtest dallaUI.** Gian vuole premere personalmente “Avvia backtest” e seguirne l'esecuzione nella webapp, senza attendere il terminale o dipendere da un run lanciato dall'agente. Occorre distinguere avvio di un nuovo calcolo da apertura di risultati già calcolati; la barra percentuale da sola non basta. Mostrare fase in corso, periodo/avanzamento temporale realmente elaborato, conteggi pertinenti ed errori/blocchi leggibili, con aggiornamenti veritieri anche se il run è rapido. L'importJSON attuale è consultazione, non avvio; non spacciarlo per requisito realizzato. Astra ha autorizzato l'orchestrazione locale minima; il Director ne specifica il percorso inAPP-001. Nessuna estensione a nuovi dati, algoritmi, ottimizzazioni, ordini o apertura dei dati protetti.

## 14. Quando una lettura diventa una call

Una call è una proposta operativa identificabile, con una ragione e condizioni. Deve essere distinguibile da una semplice osservazione o da una direzione ancora incerta.

Il piano deve permettere di comprendere direzione, condizione/fascia di ingresso, protezione iniziale, destinazione o obiettivo, validità temporale, ragioni principali, controevidenze e vincoli economici. Le condizioni operative precise saranno definite prima di implementare il motore.

«Ingresso disponibile» non significa «entra a qualsiasi prezzo». Se il prezzo cambia prima dell'esecuzione, il piano va ricontrollato. Una destinazione narrativa non è automaticamente un target eseguibile. Un target modificato non sostituisce nella storia quello originario.

Il bot può attendere senza essere guasto. D'altra parte, un sistema che non propone mai niente non ha automaticamente raggiunto l'obiettivo dell'Owner. Frequenza e motivi delle astensioni servono a leggere il comportamento, non diventano una quota di trade da raggiungere.

## 15. Call, ordine e posizione sono differenti

Una call può non produrre un ordine, un ordine può essere rifiutato e un ordine accettato può non essere ancora eseguito. Una posizione esiste quando risulta effettivamente aperta sull'exchange, non quando la pagina mostra una proposta.

Il prodotto deve distinguere almeno: proposta, attesa, richiesta di ordine, ordine accettato/non eseguito, esecuzione parziale o completa, posizione aperta, richiesta di chiusura e posizione chiusa. Non sono necessariamente nomi tecnici definitivi, ma significati che non possono essere fusi.

Il conto collegato è la fonte dello stato operativo effettivo. Dopo un problema di connessione il bot deve riconciliare quanto è accaduto: un ordine potrebbe essere stato eseguito mentre il PC non riceveva dati. Un retry non deve aprire una seconda posizione.

Gian non fa trading manuale ordinario e non richiede un gestore universale di portafogli. Il progetto può essere pensato per un conto/ambito dedicato al bot. Un'incoerenza o una posizione inattesa deve comunque essere gestita esplicitamente, senza assumere che il conto sia vuoto.

## 16. Gestione della posizione durante il trade

Il bot deve continuare a osservare la situazione che motivava il trade. Nuove informazioni possono giustificare mantenere il piano, stringere la protezione, ridurre o aumentare il target, chiudere parzialmente o uscire. Le condizioni per farlo sono parte della strategia da studiare, non una libertà del programma di improvvisare.

Una normale oscillazione non deve attivare meccanicamente l'uscita soltanto perché una candela è contraria. Allo stesso tempo, non possiamo garantire di riconoscere sempre oscillazione e inversione. Un cambio di lettura può derivare da errore iniziale, nuova informazione o reazione eccessiva: la storia deve permettere di distinguerli quando possibile.

Sono approvate uscite parziali e nessun aumento della posizione già aperta. Non sono approvati mediare una perdita, aggiungere esposizione per recuperare o spostare uno stop lontano per evitare di registrare una perdita. I dettagli di protezione, quantità, uscite parziali e gestione del residuo richiedono una specifica prima dell'esecuzione.

La comparsa di una lettura opposta non deve creare due posizioni contemporanee né un ribaltamento automatico non definito. La chiusura della posizione corrente e l'eventuale nuovo ingresso sono decisioni distinte. La politica esatta del passaggio e dei tempi di attesa resta da fissare.

## 17. Esempi che chiariscono il risultato

Questi numeri sono esempi dell'Owner, non parametri.

| Percorso | Come leggerlo |
|---|---|
| Entrata 9.000, target 10.000, salita a 9.500 e poi stop in perdita | La posizione ha avuto un tratto favorevole, ma il trade effettivo è una perdita netta. Non si conta come vittoria perché la direzione era stata corretta per un po'. |
| Stesso inizio, uscita decisa a 9.500 | Si misura il risultato effettivamente ottenuto, al netto dei costi. Non aver raggiunto 10.000 non impedisce un guadagno. La ragione dell'uscita deve essere disponibile in quel momento. |
| Salita a 9.500 e lunga stabilizzazione con posizione ancora aperta | C'è un risultato non ancora realizzato. Non lo confondiamo con denaro già incassato; intervengono le regole di gestione e scadenza definite prima. |
| Entrata 10.000, salita a 12.000, caduta a 8.000, poi salita a 15.000 | Se lo stop aveva chiuso prima, il recupero successivo non cancella la perdita. Non possiamo allargare retroattivamente lo stop per ottenere un trade vincente. |

Per valutare la gestione dinamica conserviamo piano iniziale, aggiornamenti, ragioni, orari e azioni effettive. Guardare solo l'ultimo target nasconderebbe promesse cambiate lungo il percorso.

## 18. Modi d'uso e comandi dell'Owner

**Solo call.** Il bot continua ad analizzare e aggiornare le indicazioni, ma non deve aprire o gestire automaticamente ordini per conto dell'Owner. Se si passa a questa modalità con una posizione gestita dal bot, serve una conferma chiara del passaggio di responsabilità: non si deve dare l'impressione che il bot continui a proteggerla attivamente. La posizione e le protezioni già presenti restano visibili.

**Call + esecuzione.** Il bot può eseguire e gestire secondo strategia e limiti autorizzati. Il ritorno a questa modalità non può ignorare lo stato effettivo del conto. Il recupero della gestione di una posizione già aperta richiede verifica e chiarezza per l'Owner; i dettagli della conferma vanno precisati nel contratto operativo.

**Chiudi posizione.** È un comando separato, pertinente solo quando esiste una posizione aperta, anche se la call narrativa risulta conclusa. La richiesta non viene mostrata come chiusura completata prima della conferma dell'exchange.

**Stop totale.** Ferma l'attività del bot. Non equivale automaticamente a chiudere la posizione. L'interfaccia deve chiarire che cosa resta aperto e protetto e che cosa non verrà più monitorato. Una chiusura del processo dal terminale non garantisce che siano state completate operazioni di cancellazione o salvataggio.

Prima dell'implementazione occorre chiudere il trattamento degli ordini pendenti nei cambi di modalità, la conferma di presa/rilascio della gestione e l'arresto con ordini in corso. Non è autorizzato cancellare silenziosamente protezioni esistenti o lasciare nuovi ingressi pendenti senza dichiararlo. Il requisito di sicurezza è deciso; il protocollo tecnico non è ancora scritto.

## 19. Interruzioni, ripresa e protezioni

Gian preferisce che dopo un'interruzione tecnica il bot possa riprendere. Questo non significa ignorare uno Stop volontario o riattivare una modalità che l'Owner aveva disabilitato.

La ripresa deve verificare posizione, ordini, dati e stato salvato prima di agire. Nessun ingresso duplicato, nessuna call storica dichiarata corrente per il solo fatto di essere stata ricaricata. Se non sappiamo se la posizione è protetta o se un ordine è stato eseguito, il prodotto deve mostrare il problema e applicare il comportamento conservativo che verrà specificato.

L'obiettivo è mantenere le protezioni sull'exchange dove il prodotto scelto lo consente, perché il PC può spegnersi. Questo requisito va verificato sulle funzionalità reali dell'exchange prima della costruzione. Uno stop non garantisce comunque il prezzo esatto di uscita in ogni condizione di mercato.

## 20. Capitale, costi e significato di convenienza

Gian vuole scegliere capitale, leva, rischio massimo, guadagno minimo desiderato e altri limiti quando il progetto arriverà alla definizione esecutiva. Non sono già fissati. La quantità di denaro rischiata non può essere inferita da vecchi profili o dagli esempi della conversazione.

Non cerchiamo operazioni con un guadagno teorico minuscolo che sparisce nei costi. Ma non basta fissare una differenza assoluta in dollari: contano prezzo di ingresso, quantità, protezione, percorso, durata e costi. La regola di convenienza deve essere definita prima delle prove della strategia, senza adattarla al saldo desiderato.

Il risultato netto deve includere ciò che realmente si paga o si assume di pagare: commissioni di entrata e uscita, effetto del prezzo di esecuzione rispetto al prezzo osservato, eventuale funding e altri costi propri dello strumento. Costi mancanti non valgono zero per comodità.

All'inizio non serve ricostruire un exchange completo o un order book storico perfetto. Serve un modello semplice, esplicito e sufficientemente prudente per la domanda studiata, con limiti dichiarati. Se quei limiti impediscono una conclusione, non li nascondiamo dietro un saldo preciso.

## 21. Storico locale, demo e reale

**Storico locale:** fa scorrere più rapidamente dati già raccolti e simula decisioni, entrate, gestione e uscite. Serve sia allo sviluppo sia a verifiche separate, secondo quali dati si usano. Non è limitato al solo “training”.

**Demo dell'exchange:** usa fondi virtuali e il tempo corrente. Serve a provare collegamento, ordini, protezioni, gestione, aggiornamenti e continuità. Non fa scorrere tre anni a velocità accelerata. Non è un conto reale e non dimostra da sola redditività o qualità identica delle esecuzioni.

**Reale:** espone denaro vero e richiede una decisione successiva esplicita. Non è attivato dal desiderio di automatizzare il prodotto.

Per la demo Binance devono essere verificati prodotto disponibile, accesso API, tipi di ordine, commissioni simulate, funding, riempimenti e differenze dal reale. La conversazione non certifica che tutto sia già supportato. Non presentiamo condizioni commerciali o disponibilità geografiche come accertate.

## 22. Dati e provenienza

Binance è la preferenza iniziale per l'esecuzione perché Gian conosce la demo. Il prodotto e il conto operativi che permettono LONG/SHORT restano decisioni da chiudere. Per OBS-001 e CAND-001 è autorizzata Binance Vision BTCUSDT perpetual USDⓈ-M, prezzo negoziato 1m e intervalli circoscritti in §31; CAND ammette inoltre funding/mark necessari ai costi. Non equivale a scelta operativa di conto, leva o accessibilità reale. TradingView è un possibile riferimento visivo, non automaticamente una fonte autorizzata per tutti i dati o il gestore della posizione.

I vecchi dati OKX restano dati OKX. Non vengono rinominati Binance e non provano le stesse condizioni di esecuzione. Dove possibile vogliamo studiare dati pertinenti alla sede e allo strumento da usare, dichiarando eventuali differenze.

I dati devono avere identità, origine, tempi e copertura verificabili. Barre incomplete, minuti mancanti, ritardi o valori non disponibili devono restare riconoscibili. Gli orari interni saranno confrontabili; l'interfaccia li presenta in modo locale leggibile con il fuso identificabile.

Se una sola candela contiene sia target sia stop e non sappiamo l'ordine dei contatti, non scegliamo quello favorevole. La convenzione per casi ambigui deve essere fissata prima della prova. Anche gli indicatori che confermano un massimo o minimo usando barre successive diventano disponibili solo al momento della conferma, non all'ora retroattiva dell'estremo.

## 23. Come giudicheremo il candidato

Il risultato economico netto è centrale: partire con un capitale e arrivare a un valore maggiore, dopo costi e tenendo distinti eventuali versamenti, è il risultato cercato. Il confronto deve però usare regole coerenti su capitale, esposizione, posizioni ancora aperte e termine della prova.

Un saldo positivo dice che quella prova ha guadagnato nel modello utilizzato. Per decidere se affidarsi al sistema occorre capire anche quanta perdita temporanea è stata sopportata, quanto è concentrato il risultato e quanta informazione abbiamo. Non basta una sola operazione fortunata e non serve vincere il 100% delle volte.

La percentuale di trade vincenti è secondaria: molte piccole vittorie possono essere cancellate da poche grandi perdite. La gestione dinamica viene giudicata sulle azioni realmente previste ed eseguite/simulate, non sul miglior prezzo raggiunto dal mercato.

Non fissiamo qui una soglia arbitraria di promozione, una quota di call o un numero di indicatori concordi. Il disegno di valutazione deve essere pronto prima dell'esecuzione e deve consentire anche la conclusione «informazione insufficiente».

## 24. L'app desiderata

L'Owner immagina una stazione di comando leggibile: grafico principale a sinistra, call/decisione a destra e riquadri dei segnali sotto. L'aspetto può essere ricco ma non deve diventare un muro di numeri o termini incomprensibili.

La dashboard deve distinguere ambiente demo/reale, modalità solo call/esecuzione, bot attivo/fermo, stato dei collegamenti e freschezza dei dati. I comandi principali devono essere riconoscibili. Il cambio di modalità deve avere evidenza visiva senza confondersi con LONG/SHORT.

Il grafico mostra candele, scelta 45m/giornaliero, volumi e strumenti pertinenti attivabili; livelli del piano e della posizione devono essere distinguibili. Non è approvata una seconda copia del grafico per ogni spiegazione.

Il riquadro decisionale mostra: attesa o opportunità, direzione, ingresso e condizioni, target, stop/invalidazione, validità, motivi e aggiornamento più recente. Quando esiste una posizione, mostra la situazione effettiva e le azioni del bot. Quando non c'è una call non deve riempire i campi con livelli immaginari.

Le schede dei segnali spiegano cosa viene osservato, che significato ha secondo la versione corrente e se il dato è disponibile. I dettagli tecnici sono consultabili progressivamente. Una scheda non deve inventare una probabilità numerica o diventare un voto automatico.

Conto, ordini, eseguiti, operazioni concluse, costi e risultati hanno viste consultabili. Il risultato della posizione ancora aperta deve essere distinto da quello realizzato. Le notifiche storiche sono eventi passati: non devono dire “entra adesso” quando la disponibilità è terminata.

Gian ha proposto Figma AI per il design e successiva implementazione con Claude. I valori di un mockup sono esempi, non parametri approvati. Il design non deve precedere il chiarimento del significato dei campi o diventare una lunga rifinitura scollegata dall'algoritmo.

Aggiornamento Owner del 16 ottobre 2026 dopo il primo avvio locale: eliminare la barra di navigazione sinistra e spostare le destinazioni in una barra superiore per recuperare larghezza nel contenuto principale. Questa modifica è autorizzata rispetto al layout Figma; schede, stile e semantica operativa restano il riferimento. I controlli degli scenari locali devono restare accessibili e chiaramente separati dai comandi operativi, senza occupare una colonna laterale permanente.

Riscontro Owner del17ottobre2026 su OBS-001: lo scopo di apertura JSON, data/ora, avanzamento, scale e pivot non era comprensibile dalle sole istruzioni. Non trattare la prova come accettata. Il cursore serve a ispezionare informazioni note a un momento passato; lo studio elabora già automaticamente tutte le origini. L'Owner chiede di discutere con Astra la sufficienza di pochi mesi e il passo verso il metodo decisionale. Lo studio attuale copre4mesi settembre–dicembre2025, preceduti da3mesi di inizializzazione; quella richiesta non autorizzava da sola un'estensione. Astra l'ha poi autorizzata esplicitamente per CAND-001 come registrato in §31.

**Riscontro Owner CAND-001 del17ottobre2026.** Gian comprende circa il riconoscimento di un movimento e l'attesa di una reazione, ma perde il significato fra proposta d'ingresso, ordine e posizione. Chiede frasi dirette e informali: che cosa ha deciso il programma, se ha soltanto tentato di entrare, se l'acquisto/vendita è stato effettivamente eseguito nella simulazione e come si è chiusa l'operazione. La qualificazione simulata deve essere chiara, senza ripetere “modellato” come spiegazione di ogni campo. Il motivo d'uscita deve essere esplicito: stoploss, obiettivo raggiunto, decisione per cambiamento osservato, limite di tempo, fine del periodo o percorso irrisolto, secondo l'evento vero. Nessuna “uscita” generica che richieda deduzioni.

I pulsanti “Prima operazione”, “Primo caso negativo”, “Prima astensione” ecc. sono scorciatoie cronologiche a esempi prodotti dal candidato, non gli unici casi disponibili. Spiegare questa funzione e rendere riconoscibile il registro di tutte le operazioni e il passaggio elenco→dettaglio. Non confondere “prima operazione” con nuovo ordine o avvio di un backtest.

**Navigazione: requisito trasversale per tutta l'app.** Ogni passaggio elenco/risultati→dettaglio deve permettere di tornare in modo evidente, conservando lo studio/run e il contesto pertinente. L'Owner richiede navigazione coerente con URL e Indietro/Avanti del browser, oltre al ritorno interno visibile: non deve dover riselezionare l'ambiente per ritrovare l'elenco. Non introdurre sistematicamente altri dettagli senza questa possibilità.
Segnalazione attuale: l'Owner non trova il ritorno dai cinque pulsanti. In EpisodeView il Director ha letto un controllo “← Risultati”: l'assenza materiale del controllo non è riprodotta; visibilità/accessibilità/usabilità vanno verificate. La mancanza di percorso URL/cronologia è distinta. Non liquidare il problema perché un pulsante esiste nel codice.

## 25. Linguaggio, colori e aggiornamenti

Lingua principale: italiano semplice. Dire «il mercato osservato è in equilibrio» non equivale a prevedere lateralità. Dire «nessun ingresso» non equivale a dire che non esiste un'analisi.

**Requisito esplicito Owner del17ottobre2026:** app personale, destinatario senza conoscenze di trading, linguaggio semplice/diretto anche informale. Non presupporre conoscenza di “modellato”, “PnL”, “slippage”, “funding”, “stress”, “bp”, “N0” o “fee”. I dati tecnici restano tracciabili, ma l'interfaccia deve tradurli e dare priorità a importi e significato concreto.

Per risultati e costi: risultato simulato dopo i costi; guadagno/perdita dal solo movimento del prezzo; commissioni; differenza fra prezzo di riferimento e prezzo usato per l'esecuzione; pagamento periodico del contratto (anche a favore, non sempre costo); scenario con costi più alti sugli stessi trade. Le descrizioni esatte devono rispettare il calcolo e non sommare due volte lo scostamento di esecuzione. Il nozionale1000USDT è il valore convenzionale della singola operazione, non capitale personale o rischio fino allo stop.

L'Owner accetta una classica icona “i” con popup esplicativo all'hover per le voci tecniche; il Director propone la stessa spiegazione anche a focus/clic, per non renderla dipendente dal solo mouse. Numeri come “−40bp diN0” non devono restare in primo piano senza traduzione: spiegare scala/unità con esempio riferito all'operazione, oppure spostarli nei dettagli. Le somme su più operazioni non diventano una percentuale di rendimento di un conto.

Verde e rosso identificano direzione/movimento; disponibilità, attenzione, errori e conclusione richiedono etichette e simboli distinti. Il colore da solo non comunica lo stato. I dettagli del vecchio cockpit non sono vincoli di layout del nuovo.

Gli aggiornamenti devono spiegare i passaggi importanti, non generare un messaggio a ogni variazione minima. Se un target o uno stop cambiano, devono essere leggibili prima, dopo, orario e ragione. Se i dati diventano vecchi, lo stato non può restare presentato come attuale senza avviso.

Telegram è il canale iniziale concordato per le notifiche. Portata esatta degli avvisi e collegamento saranno definiti nel relativo incarico. Comandi di trading via chat non sono approvati implicitamente. WhatsApp non è una dipendenza necessaria.

## 26. Budget e funzionamento pratico

**Destinazione esplicita Owner del17ottobre2026:** questa webapp è locale, personale ed esclusiva diGian, non destinata alla pubblicazione o ad altri utenti. È corretto personalizzare lessico e flussi sul suo modo di capire e lavorare; non progettare hosting pubblico, multiutenza o autenticazione per questo incremento. Il fatto che il codice sia in una repository pubblica non equivale alla pubblicazione del servizio web, dei dati locali o del conto.

La prima fase deve funzionare sul PC dell'Owner usando strumenti e dati gratuiti dove adeguati. Gian paga già gli abbonamenti AI e non vuole aggiungere automaticamente servizi a pagamento. Può lasciare acceso il PC; un server economico potrà essere valutato in seguito.

Nessun requisito deve presupporre un servizio LLM a pagamento chiamato continuamente dal bot. Usare AI per progettare e sviluppare non significa che il motore debba fare richieste a un modello a ogni candela. L'architettura di esecuzione verrà scelta esplicitamente.

Quando il PC è spento, il software locale non continua a monitorare o mandare notifiche. Le protezioni eventualmente presenti sull'exchange sono un meccanismo diverso. Non promettiamo disponibilità continua solo perché il programma prevede una ripresa.

Credenziali e chiavi non devono finire in Git, report o screenshot. La futura configurazione dovrà separare demo e reale e usare solo i permessi necessari. La repository pubblica non deve contenere libri acquistati o dati del conto per comodità di consultazione.

## 27. Verifiche utili senza trasformare il progetto in una suite infinita

Test sintetici: verificano esempi e comportamenti del programma. Prove integrate: controllano che motore, salvataggio, collegamento e app lavorino insieme. Prove d'uso: verificano se Gian capisce e riesce a usare una funzione. Studi storici: valutano comportamenti ed esiti su mercato passato. Demo: verifica il funzionamento corrente con fondi virtuali. Nessuna di queste sostituisce tutte le altre.

Gian ha segnalato il costo di suite e CI molto lunghe. Non è approvato rieseguire l'intero prodotto per ogni documento o cambio di versione. Si scelgono controlli proporzionati al rischio e al diff, con un motivo chiaro per estenderli. Un problema già verificato non richiede ripetizioni rituali.

Le prove sull'app devono ricomparire quando c'è una funzionalità concreta da vedere, senza costringere l'Owner a cicli continui di usabilità. Non bisogna attendere un algoritmo “perfetto” per verificare l'integrazione, ma neppure confondere una schermata bella con una strategia valida.

Ogni consegna distingue ciò che Claude dichiara di aver eseguito da ciò che il Director ha verificato o rieseguito. Una review statica non viene presentata come prova live. Nessun polling della CI è autorizzato automaticamente.

## 28. Fonti e archivio

Libri, dossier, paper e professionisti sono aiuti. Non sono la legge del prodotto e non garantiscono una formula pronta per BTC. Non dobbiamo richiedere che ogni componente abbia una conseguenza operativa autonoma se il ragionamento è composto; dobbiamo però sapere quali raccordi stiamo introducendo noi.

I dossier restano nell'archivio o in una biblioteca esterna al codice. La nuova repository contiene un indice di collegamenti, non l'intera vecchia `source_notes` e non la vecchia cartella `delivery`. Non serve una terza repository obbligatoria.

Una fonte va qualificata: originale letto, riassunto secondario, trascrizione non verificata, interpretazione nostra, regola adattata. Non presentare la presenza di un riferimento bibliografico come prova empirica della nuova strategia. Nuovi acquisti o ricerche estese richiedono una lacuna precisa; non sono il prossimo passo automatico.

## 29. Dati già esposti e studi congelati

Gennaio–aprile 2025 e settembre–dicembre 2025 sono periodi già esposti a studi e sviluppo. Per il primo erano dichiarati input dal 27 novembre 2024 al 1 maggio 2025 06:05 UTC; per il secondo dal 28 luglio 2025 al 1 gennaio 2026 06:05 UTC. Anche parte di settembre/ottobre 2026 è stata vista; il registro non certifica assenza di altre esposizioni.

Gennaio–agosto 2026 resta protetto, salvo il tail del 1 gennaio fino alle 06:05 già autorizzato. Non aprire periodi perché la nuova repository è vuota.

Gli studi precedenti HDP-001, con finestra dal 2 novembre 2026 al 25 gennaio 2027, e A v0.6, dal 25 gennaio al 26 luglio 2027, restano INACTIVE e separati. Le finestre sono intervalli con inizio incluso e fine esclusa. La migrazione non li attiva, modifica o cancella. La nuova ricerca non eredita l'autorizzazione ad acquisire, elaborare o consultare dati di quegli studi.

Gli accessi e le copie autorizzati nel vecchio progetto non sono permessi generici di entrare nello stack Owner. Qualsiasi futuro uso di dati deve identificare cosa serve e dove si trova.

## 30. Organizzazione documentale e incarichi

Questo documento svolge il ruolo di foundation funzionale. Non manteniamo una seconda foundation con le stesse decisioni riscritte diversamente. Le modifiche sostanziali devono aggiornare questo testo e la sua breve storia delle revisioni.

`README.md` è la porta d'ingresso. `AGENTS.md` stabilisce come lavorare. `CLAUDE.md` rimanda a quelle istruzioni. `STATE.md` fotografa il progresso corrente. `current_task.md` contiene un solo incarico, completo e delimitato. Le fonti, la provenienza e le esposizioni hanno documenti separati perché non sono requisiti del prodotto.

Astra o Director deve scrivere nel task obiettivo, perimetro, decisioni già chiuse, comportamento atteso, controlli necessari e criteri di accettazione. Se manca una scelta metodologica, il task non è pronto per l'esecutore. Claude registra consegna e problemi senza modificare autonomamente l'obiettivo o dichiararsi accettato.

Il prompt ordinario può essere semplicemente: «Leggi AGENTS.md e current_task.md. Esegui l'incarico attivo entro il perimetro indicato e consegna i risultati». Non deve essere ogni volta un secondo documento di progetto.

## 31. Macropercorso del nuovo progetto

**Macrofase UI conclusa il 16 ottobre 2026. Mandato UI storico:** Gian sceglie di costruire prima la dashboard approvata in Figma, alimentata da modelli di presentazione e pochi scenari deterministici simulati, e collegare successivamente l'algoritmo. Astra autorizza al Director questa macrofase completa: specifica, incarichi a Claude, implementazione, review, correzioni e prova Owner. Link al progetto e accesso effettivo dell'esecutore devono essere verificati; nessun restyling autonomo. Nessun backend, database, autenticazione o connettore costruito soltanto per alimentare questa UI.

L'app deve mostrare “SIMULAZIONE LOCALE — nessun collegamento exchange”. Call, ordini, eseguiti e posizione restano distinti; parametri, importi e prodotto nel mockup sono esempi. Il fornitore di dati simulati è separato dai componenti, che non deducono segnali o decisioni. Le sezioni non costruite sono dichiarate. I comandi possono produrre solo transizioni locali simulate e coerenti con i requisiti funzionali. Chiusura macrofase: dashboard avviabile sul PC, fedele al Figma, stati navigabili/coerenti, controlli comprensibili e dati sostituibili senza riscrivere la presentazione.

**Mandato OBS-001 di Astra del 16 ottobre, ora concluso tecnicamente:** osservazioni calcolate e primo studio storico nell'app. Autorizzata l'intera macrofase: specifica ex ante, calcoli sintetici discriminanti, acquisizione pubblica circoscritta, elaborazione reale, integrazione nella dashboard esistente, prima tabulazione e prova Owner. Il Director gestisce autonomamente incarichi, review e correzioni ordinarie; torna ad Astra alla conclusione o per conflitto sostanziale. Non fermarsi al solo motore sintetico.

DESIGN-001 è **approvato parzialmente per le definizioni osservative §§5–6**, come versione iniziale non ottimizzata: aggregati45m/1D UTC, TR/media20TR, SMA20/50, pivot2+2 confermati, livelli, volume relativo e Fibonacci con disponibilità/versioni. Warmup per misura e dipendenze effettive, mai blocco globale54barre. Etichette UI coerenti coi calcoli. Esclusi modello economico, barriere2A, prossimità come decisione, R2/R3 e verifica protetta. Dettagli eseguibili nel task OBS-001.

Unica fonte candidata per questo studio: Binance Vision BTCUSDT perpetual USDⓈ-M, prezzo negoziato1m; inizializzazione [2025-06-01,2025-09-01), studio [2025-09-01,2026-01-01) UTC. Nessun dato successivo per completare esiti. Download pubblico gratuito e metadati consentiti, file locali fuori Git, controlli di provenienza/copertura; nessun account/chiave/vecchio stack. Buchi e duplicati non producono prezzi inventati; nessun sostituto spot/OKX. Non approva prodotto operativo, conto, leva o accessibilità reale.

Domanda descrittiva unica: tutte le chiusure45m, confronto entro la medesima struttura crescente/decrescente fra giornaliero concorde, contrario, misto o indisponibile; anche riepilogo della sola struttura45m. Esiti24h: variazione finale ed escursioni alto/basso normalizzate con volatilità all'origine. Popolazione completa, stati misti/assenti e censure finali conservati, numerosità/distribuzioni mensili, niente successo trade, significatività, causalità o ricerca di combinazioni favorevoli. Finestre sovrapposte non indipendenti.

Stessa dashboard e provider separato, selezione temporale e avanzamento sincronizzati45m/1D; distinguere informazioni a t dal seguito retrospettivo. Nello storico nessuna call, posizione o saldo fittizi; la simulazione resta ambiente separato. Pipeline locale batch senza servizi permanenti/DB/live non necessari.

**Chiusura tecnica OBS-001:** motore osservativo e tabelle reali verificati, correzioni R1 concluse; limite di comprensione Owner registrato. Nessuna ulteriore estensione dell'esploratore. Le esclusioni del mandato OBS non autorizzavano strategia o valutazione economica: il mandato successivo sotto le autorizza separatamente per CAND-001, senza denaro reale.

**Mandato CAND-001 di Astra del 17 ottobre — primo candidato completo e ciclo storico di sviluppo, implementazione ora accettata tecnicamente con i limiti dichiarati.** Famiglia scelta: movimento direzionale → reazione → tentativo di ripresa. Il Director definisce una versione completa prima degli esiti: contesto, reazione/contraddizioni, trigger/astensione, ingresso modellato, stop/target/validità, gestione dinamica, precedenze e dati mancanti. Claude implementa, non sceglie strategia. Ruoli delle sei famiglie espliciti, nessun voto/sestina obbligatoria e nessuna concordanza giornaliera obbligata dal solo OBS-001. Nessun riuso di vecchi A/RETURN/E/a2x.

Storico autorizzato: stessa fonte Binance Vision BTCUSDT perpetual USDⓈ-M, inizializzazione [2022-10-01,2023-01-01), sviluppo [2023-01-01,2026-01-01) UTC. Riutilizzare file verificati, acquisire solo mancanti. 2023–2024 per iterazioni iniziali; 2025 confronto aggiuntivo già esposto. 2026 protetto e vecchi studi INACTIVE. Dati pubblici funding/mark strettamente necessari ai costi ammessi entro gli stessi confini, nessun account/stack Owner.

Prima valutazione con nozionale normalizzato fisso, senza leva/reinvestimento: risultati di operazioni ipotetiche, non rendimento del conto personale. Capitale e leva dell'Owner non sono prerequisiti di questo studio. Fee/slippage/funding/ritardo/intrabar/confini registrati prima del calcolo; costi mancanti non zero e percorsi irrisolti non nascosti in un saldo completo. Il modello economico DESIGN-001 non è approvato automaticamente: riferimento completo docs/research/CAND-001-v1.md.

Sequenza: specifica registrata → implementazione → controlli discriminanti → backtest DEV 2023–2024 → diagnosi Director. Bug si correggono; revisione metodologica richiede motivazione/versione/confronto sullo stesso DEV. Al più un ciclo di revisione nella famiglia, non obbligatorio, senza nuova approvazione Astra. Cambi di famiglia/nuovi segnali/ricerca automatica parametri richiedono decisione strutturale. Congelamento dopo diagnosi prima di 2025; nessuna iterazione sui suoi esiti salvo bug documentati.

Nella stessa app Gian vede decisione reale del candidato, informazioni note allora, ingresso/gestione/uscita modellati, costi/risultato e astensioni/casi contrari scelti con regola cronologica prefissata. Accesso diretto agli episodi, non verifica manuale di migliaia di origini. Nessun nuovo restyling, piattaforma o conto/ordine esterno. Report separati per anno/mese con frequenza, rischio/percorso e concentrazione; non un unico saldo. Chiusura con evidenza riproducibile e raccomandazione anche negativa, non promessa di profitto o soli test verdi.

**Mandato APP-001 di Astra del17ottobre2026 — Gian autonomo nel lanciare, seguire e capire un backtest.** Non è restyling: capacità d'uso necessaria al prodotto. Director gestisce l'intera macrofase, incarichi aClaude scritti prima dell'esecuzione, review/correzioni ordinarie autonome; adAstra alla chiusura o conflitto sostanziale.

CAND-001 resta distinto in quattro giudizi: implementazione accettata tecnicamente entro review/limiti; usoOwner apprezzato ma non sufficientemente comprensibile/autonomo; strategiav1 storicamente negativa e non promossa; efficacia generale della famiglia non risolta. Non inventare una provaOwner positiva né bocciare il software per la perdita del candidato.

Percorso principale: **Nuovo backtest→calcolo**, **Risultati salvati→consultazione**, **Tutte le operazioni→dettaglio**, esempi cronologici chiaramente subordinati al registro. ImportJSON secondario. Orchestrazione autorizzata solo locale personale, massimo un backtest attivo, dati già presenti e finestre autorizzate, niente download/exchange/ordini/editorstrategia/ricerca parametri. Versione,input,periodo e profilo conservati a ogni esecuzione.

Avanzamento reale per controllo dati,inizializzazione,storico con data/conteggi,riepilogo/salvataggio; frequenza sufficiente per distinguere lavoro,attesa ed errore,nessuna percentuale/ETA inventata. Chiudere/ricaricare la pagina non avvia duplicati né cancella il processo; stato ritrovabile. Annullamento esplicito e incompletezza dichiarata; dopo spegnimento può risultare interrotto e richiedere nuovo avvio,senza ripresa complessa.

Banner persistente **“Simulazione su prezzi storici. Nessuna operazione reale.”** Linguaggio diretto su tentativo,non eseguito,posizione aperta e motivo di chiusura.1000USDT è dimensione convenzionale di ogni trade,non capitale né perdita massima. Costi tradotti e riconciliati senza doppio conteggio; dettagli/formule espandibili,aiuti anche clic/tastiera,stress separato. Navigazione condivisa conURL,Indietro/Avanti,ritorno evidente,registro con contesto conservato e ricaricamento gestito o spiegato in tutti gli ambienti.

Scelte tecniche Director perAPP-001: stesso frontend con piccolo servizioPython locale e un worker,statojob sufile fuoriGit,nessun DB/hosting/multiutenza. Un comando npm run dev avvia frontend e servizio;3profili fissi:DEV2023–2024,confronto2025 e **prova gennaio2025[2025-01-01,2025-02-01)** per collaudoUI/diretto,non nuovo studio. Prefisso osservativo sempre dal2022-10-01,FLAT all'inizio della finestra. Routercomune a frammentoURL(#/...),non secondaapp. Dettagli e comportamenti limite in current_task.md.

Controlli mirati:duplicati,progresso,annullamento,errori,riapertura,navigazione,risultati. Confrontare una breve esecuzione realeUI col medesimo percorso diretto,riusando verifiche complete per regole immutate;non ripetere tutta la storia a ogni testo/layout. Chiusura quandoGian distingue nuovo/salvato,avvia e segue,trova tutte le operazioni,capisce entrata/nonentrata/uscita/costi e torna/riapre. Gian non verifica formule.

DuranteAPP-001 v1 e convenzioni restano congelate; collaudi non selezionano regole più favorevoli. Questa è l'ultima preparazione richiesta prima del prossimo ciclo metodologico,non una piattaforma generale. Alla chiusura si torna adAstra per diagnosi della politica completa,eventuale revisione e confronto;nessuna nuova strategia/segnale/combinazione autorizzata ora,2026protetto e nessun reale.

**Mandato Astra — ciclo metodologico CAND-001, 17 ottobre 2026.** APP-001 chiuso e accettato nei limiti della review e del riscontro Owner. Nessun ulteriore lavoro preparatorio sull'interfaccia. Director gestisce autonomamente diagnosi della politica completa v1, scelta di al massimo un problema decisionale, eventuale unica v2 e confronto sull'intero DEV [2023-01-01,2025-01-01), con input già disponibili e inizializzazione dal 2022-10-01. Il 2025 non è ricalcolato né usato per scegliere la revisione; 2026 protetto. V1 rimane negativa e non promossa.

Diagnosi integrata di ingresso, percorso/gestione, destinazione/tempo e costi; tutti i trade e conteggi delle astensioni, esempi positivi/negativi e astensioni selezionati con regola dichiarata prima dei nuovi percorsi dettagliati. Nessuna uscita al massimo dedotta dal futuro. Un problema modificabile richiede informazione disponibile allora, coerenza con la famiglia, correzione precisa e svantaggi/controesempi. Claude estrae evidenze e implementa la decisione specificata, non sceglie strategia.

Prima del calcolo di eventuale v2: problema, nuova decisione/input, motivo, situazioni peggiorabili e risultato che indebolirebbe la spiegazione. Stessi dati/costi/dimensionamento/esecuzione, confronto completo anche di operazioni aggiunte/eliminate/spostate, netto, drawdown e concentrazione. Nessuna ricerca automatica, griglia di soglie, nuova famiglia/segnale o modello di rischio/esecuzione. Eventuali deroghe sostanziali ad Astra. Microstep e review ordinari senza nuove autorizzazioni. Chiusura con v2 confrontata anche se peggiore, oppure nessuna revisione giustificata e limite informativo preciso. Risultato consultabile nella stessa app con soli adattamenti indispensabili, nessun sistema generale di confronto o restyling. D1 consegnato a3b27b5d e accettato dal Director: diagnosi integrata e 13 esempi cronologici, 9 test mirati indipendenti; estrazione reale e riconciliazioni restano evidenza dell'esecutore. Il Director chiude il ciclo senza revisione giustificata: non individuata una condizione contemporanea motivata per cambiare ingresso, mantenimento o uscita. Massimi futuri e medie descrittive non definiscono una decisione alternativa. Nessuna v2 o ricerca di valori; v1 negativa e non promossa, famiglia irrisolta. Decisione completa e limiti in CAND-001-diagnosis.md §9; casi consultabili nel DEV già salvato, nessun nuovo lavoro UI. Si torna ad Astra alla chiusura, nessuna nuova attività autorizzata implicitamente.

**Mandato corrente Astra — OBS-002, 17 ottobre 2026.** Accolta la chiusura CAND-001 senza v2, senza escludere la famiglia o il contributo congiunto di caratteristiche presenti in entrambi gli esiti. Nuova domanda osservativa: dopo movimento/arretramento, quali differenze note al primo tentativo aiutano a distinguere prosecuzione da esaurimento? Solo DEV2023–2024, osservatore già definito e input locali dal2022-10-01, nessun download/2025/2026 o modifica CAND.

Il Director fissa prima dell'estrazione popolazione più ampia delle operazioni v1, rimuovendo i vincoli di struttura/ampiezza/profondità/rapporto/costi e occupazione del candidato. Contesti causali da pivot confermati; prime riprese e ripetizioni collegate per movimento, senza indipendenza presunta. Unico seguito24h, variazione finale ed escursioni/ordine dei contatti descrittivi, valori mancanti/censure conservati; nessun profitto potenziale o massimo trasformato in uscita. Sei famiglie nello stesso snapshot con disponibilità e versioni. Unica rappresentazione semplice di contesti congiunti struttura/SMA, altre coordinate lette insieme senza griglie di coppie/triple, voti o soglie ricercate. Convenzioni eseguibili in config/OBS-002-v1.json e task unico.

Una sola analisi con popolazione completa e pochi esempi cronologici, inclusi contrari, consultabili col grafico storico e seguito esistenti. Nessun nuovo esploratore, classificatore complesso, rassegna di indicatori o preparazione UI. Solo adattamenti tecnici indispensabili al pacchetto di consultazione, senza chiamarlo vecchio OBS-001 o backtest. Conclusione Director: al massimo una ipotesi decisionale concreta, combinazione motivata con controesempi e verifica successiva necessaria, oppure nessuna distinzione interpretabile con limite preciso. Esplorazione su DEV già esposto, non efficacia; non produce automaticamente v2. Implementazione dell'ipotesi richiede decisione successiva Astra. Microstep ordinari autonomi, ad Astra alla chiusura o per conflitti sostanziali.

1. **Fondazione funzionale e organizzativa:** rendere esplicite decisioni, limiti e ruoli. È lo scopo di questa registrazione.
2. **Dashboard Figma con dati simulati:** realizzare e provare la UI approvata, con modelli distinti e provider sostituibile, entro la macrofase autorizzata sopra.
3. **Disegno della ricerca e del primo percorso operativo:** Director e Astra chiudono definizioni osservabili, contributi dei segnali, dati, divisione sviluppo/verifica e modello di costo proporzionato. Gian decide i vincoli personali necessari. Nessun incarico aperto a Claude per “trovare la strategia migliore”.
4. **Studio e prima traduzione eseguibile:** raccogliere conoscenza nel perimetro autorizzato, formulare un candidato completo e implementarlo con esempi discriminanti. Non ottimizzare combinazioni senza limite.
5. **Percorso integrato visibile nell'app:** analisi, call, aggiornamenti, storia e conto simulato devono avere significati coerenti. Gian prova incrementi utili; il design Figma serve a questa esperienza.
6. **Verifica storica separata e demo:** valutare strategia, costi, gestione e collegamento nei rispettivi ambienti. La demo non sostituisce lo storico e lo storico non prova la gestione reale degli ordini.
7. **Eventuale reale:** decisione separata dell'Owner sulla base delle evidenze, con capitale e limiti espliciti. Nessuna promozione automatica.

Non fissiamo qui una durata fittizia o una promessa di successo. Ogni macrofase deve finire con un risultato utilizzabile, un'incertezza ridotta o un blocco preciso, non soltanto con un altro elenco di possibili studi.

## 32. Decisioni ancora da chiudere prima di programmare le parti relative

| Decisione aperta | Perché serve | Responsabilità |
|---|---|---|
| Strumento Binance preciso e fattibilità demo | LONG/SHORT, costi e protezioni dipendono dal prodotto | Director verifica fatti; Astra decide conflitti; Owner approva accessi |
| Dati per ulteriori prove | CAND-001 ha fonte e finestre autorizzate in §31; nessuna apertura ulteriore implicita | Director propone nel perimetro; Astra/Owner autorizzano |
| Definizione dei movimenti studiati | Separare studio retrospettivo da trade realmente riconoscibile | Astra/Director |
| Regole concrete dei segnali e delle combinazioni | Le famiglie non sono ancora un algoritmo | Astra/Director |
| Origine e disponibilità delle barre 45m/1D | Evitare disallineamenti e informazioni future | Director, prima dell'incarico tecnico |
| Entry, uscita, revisione target/stop e orizzonti | Un candidato deve includere tutta la gestione | Astra/Director con vincoli dell'Owner |
| Capitale, leva, rischio e limiti personali | Sono decisioni dell'Owner, non valori da inventare | Gian, assistito da Astra/Director |
| Ordini pendenti, passaggio manuale/automatico e ripresa | Evitare responsabilità e stati operativi ambigui | Director specifica; Astra sui conflitti strutturali |
| Modello dei costi per prove successive | CAND-001 ha convenzioni registrate; eventuali modelli ulteriori da decidere | Astra/Director |
| Criteri di avanzamento alla demo e al reale | Un saldo isolato non è un'autorizzazione | Astra/Director; reale solo Owner |
| Stack applicativo, test budget e installazione | Evitare di importare complessità precedente senza bisogno | Director nel mandato architetturale |

Non occorre rivolgere subito tutte queste domande a Gian. Quelle tecniche e metodologiche spettano al team; quelle su preferenze, denaro e autorizzazioni personali vanno poste all'Owner quando diventano necessarie, in linguaggio semplice. Nessuna esecuzione deve precedere le scelte indispensabili per interpretarla.

## 33. Istruzioni per una nuova chat che riceve solo questo documento

Considera questo testo la memoria funzionale del nuovo progetto, aggiornata al 17 ottobre 2026, non una prova dello stato attuale del codice. Prima di agire sulla repository consulta lo stato corrente e l'incarico attivo. Non riattivare vecchi metodi, studi o autorizzazioni.

Parla a Gian in modo semplice. Ricorda che vuole partecipare alla strategia, che accetta un progetto lungo, che non pretende infallibilità e che vuole vedere progressi concreti. Non ridurre il progetto a tre pattern, a una somma di indicatori o a un grafico descrittivo. Non promettere un trader professionale già ottenuto.

Mantieni i ruoli: Astra direzione, Director ragionamento e gestione operativa, Claude esecuzione tecnica. Non chiedere ad Astra ogni microdecisione e non delegare all'esecutore la scelta del metodo. Non creare un nuovo documento per ogni dubbio se basta chiudere una decisione nella macrofase corrente.

Il lavoro corrente segue OBS-002 della sezione31 e il task unico. APP-001 e il ciclo CAND-001/D1 sono chiusi. Il Director ha fissato lo studio osservativo più ampio sul solo DEV2023–2024; Claude implementa le convenzioni e raccoglie evidenze, il Director interpreta e può formulare una sola ipotesi futura. Nessuna v2, nuovo indicatore, uso2025 o apertura2026, né preparazione UI o ricerca automatica. Non scartare una caratteristica perché compare in casi contrari: valutarne il collegamento motivato alle altre informazioni.

## 34. Storia delle revisioni

| Versione | Data | Variazione |
|---|---|---|
| 1.9 | 2026-10-17 | Astra accoglie D1 senza v2 e autorizza OBS-002: riprese anche fuori dalle operazioni v1, sei famiglie congiunte, unico seguito24h sul DEV, nessuna nuova strategia/esploratore; chiusura con una ipotesi esplorativa o limite preciso |
| 1.8 | 2026-10-17 | APP-001 chiuso; Astra autorizza diagnosi integrata v1 ed eventuale unica revisione/confronto sul solo DEV 2023–2024. Nessun uso 2025, nessun 2026; prima estrazione D1, scelta metodologica Director |
| 1.7 | 2026-10-17 | Astra autorizzaAPP-001: avvio backtest dallaUI,processo locale minimo,stato/progresso/annullamento reali,risultati leggibili e navigazione condivisa. V1 congelata,dati già disponibili,nessun2026/reale;ultima preparazione prima del ciclo metodologico |
| 1.6 | 2026-10-17 | Prova Owner CAND con rilievi: linguaggio/stati/costi comprensibili e aiuti contestuali, navigazione URL/Indietro trasversale, avvio manuale backtest e avanzamento dettagliato dallaUI, uso esclusivamente personale locale. Richiesto confrontoAstra, nessuna nuova esecuzione/metodologia avviata |
| 1.5 | 2026-10-17 | OBS-001 chiuso tecnicamente con limite di comprensione conservato; Astra autorizza candidato completo movimento/reazione/ripresa, sviluppo 2023–2024, confronto 2025, costi modellati e unica revisione motivata |
| 1.4 | 2026-10-17 | Motore/studio OBS-001 consegnati e calcoli verificati; accettazione finale pendente. Riscontro Owner su comprensibilità/scopo e richiesta confronto Astra su durata dati e sviluppo decisionale |
| 1.3 | 2026-10-16 | UI conclusa; Astra autorizza motore osservativo, acquisizione pubblica giugno–dicembre2025, studio descrittivo24h e stessa app; DESIGN-001 approvato solo §§5–6 con warmup per misura, limiti operativi invariati |
| 1.2 | 2026-10-16 | Richiesta Owner: navigazione superiore al posto della sidebar; spazio recuperato per il contenuto, controlli simulati distinti |
| 1.1 | 2026-10-16 | Disposizione Astra: priorità alla UI Figma con provider/scenari simulati; DESIGN-001 non approvato; limiti invariati sui dati e sull'operatività |
| 1.0 | 2026-10-16 | Prima sintesi funzionale autonoma del nuovo progetto; separazione da archivio, decisioni aperte esplicite, organizzazione dei ruoli e del task unico |

Per approfondire senza cambiare l'autorità di questo documento: indice delle fonti `docs/references/SOURCES.md`, memoria delle esposizioni `docs/research/EXPOSURES.md`, provenienza del recupero `docs/provenance/RECOVERY.md`. Non serve leggerli per comprendere l'obiettivo e il modo di lavorare descritti qui.
