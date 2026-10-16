# Algorithmic Trader — prodotto, decisioni e contesto completo

Versione documentale: 1.0 — 16 ottobre 2026. Responsabile della sintesi: Astra.

Questo è il documento funzionale centrale del **nuovo** progetto di Gian. È scritto per poter essere consegnato da solo a una nuova chat: spiega obiettivo, organizzazione, requisiti, ragioni delle scelte, limiti e questioni ancora aperte. Non è una specifica matematica dell'algoritmo, una dichiarazione di efficacia o un'autorizzazione a operare con denaro reale.

La sintesi deriva dalle decisioni e preferenze espresse nella conversazione con Gian e dalle consegne del progetto precedente. I risultati storici qui ricordati sono evidenze riportate dal progetto precedente, non ricalcoli effettuati per questo documento. Le risposte brevi come «sì» prive della domanda originale non vengono trasformate in dettagli tecnici presunti.

## 1. Il progetto in parole semplici

Vogliamo costruire un assistente che osservi Bitcoin continuamente e ragioni su quello che sta succedendo. Deve usare più strumenti di analisi in relazione al contesto, spiegare quali sviluppi considera plausibili e riconoscere quando esiste un'operazione sensata. Quando è abilitata l'esecuzione, deve anche aprire e gestire l'operazione sul conto collegato secondo regole stabilite.

Non basta dire «il prezzo potrebbe salire». Bisogna distinguere se conviene entrare, a quali condizioni, dove la lettura perde significato, quale destinazione si considera e per quanto tempo. Dopo l'ingresso il lavoro continua: nuove informazioni possono giustificare attesa, protezione del guadagno, revisione dell'obiettivo, uscita parziale o chiusura.

L'immagine di riferimento dell'Owner è un **trader esperto digitale**. È un obiettivo funzionale, non una capacità già ottenuta. Non promettiamo di prevedere tutto, evitare ogni perdita o riconoscere sempre una normale oscillazione rispetto a un'inversione. Cerchiamo decisioni motivate e utili nel complesso, verificandone i risultati al netto dei costi.

Il progetto può durare anni. Gian accetta studio e sviluppo progressivi, ma vuole che ogni macrofase avvicini al prodotto: non una sequenza indefinita di dossier, piccoli esperimenti scollegati e rifiniture grafiche.

## 2. Che cosa esiste oggi e che cosa no

La repository nuova è `C-Gian/algorithmic-trader`. La precedente è `C-Gian/algorithmic-trader-archive`.

Al momento di questa registrazione, nella nuova repository esistono soltanto documentazione e tre piccole utilità tecniche recuperate e riviste: calcolo di intervalli temporali, arrotondamento a passi espliciti e impronte dei file. Hanno test isolati. **Non esistono ancora un nuovo algoritmo, un'app funzionante, un collegamento al conto o un esecutore di ordini.**

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

La durata di tre anni è una proposta di scala, non una finestra già autorizzata. Fonte, date, strumento, copertura e separazione fra sviluppo e verifica devono ancora essere stabiliti. Anche il termine «movimento rilevante» va definito: gli esempi di 500, 1.000 o 5.000 dollari non sono soglie approvate.

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

Binance è la preferenza iniziale per l'esecuzione perché Gian conosce la demo. Il prodotto preciso, il contratto che permette LONG/SHORT e la fonte coerente per lo storico sono decisioni ancora da chiudere. TradingView è un possibile riferimento visivo, non automaticamente una fonte autorizzata per tutti i dati o il gestore della posizione.

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

## 25. Linguaggio, colori e aggiornamenti

Lingua principale: italiano semplice. Dire «il mercato osservato è in equilibrio» non equivale a prevedere lateralità. Dire «nessun ingresso» non equivale a dire che non esiste un'analisi.

Verde e rosso identificano direzione/movimento; disponibilità, attenzione, errori e conclusione richiedono etichette e simboli distinti. Il colore da solo non comunica lo stato. I dettagli del vecchio cockpit non sono vincoli di layout del nuovo.

Gli aggiornamenti devono spiegare i passaggi importanti, non generare un messaggio a ogni variazione minima. Se un target o uno stop cambiano, devono essere leggibili prima, dopo, orario e ragione. Se i dati diventano vecchi, lo stato non può restare presentato come attuale senza avviso.

Telegram è il canale iniziale concordato per le notifiche. Portata esatta degli avvisi e collegamento saranno definiti nel relativo incarico. Comandi di trading via chat non sono approvati implicitamente. WhatsApp non è una dipendenza necessaria.

## 26. Budget e funzionamento pratico

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

Questa è la direzione del lavoro, non l'autorizzazione ad avviare tutte le fasi.

1. **Fondazione funzionale e organizzativa:** rendere esplicite decisioni, limiti e ruoli. È lo scopo di questa registrazione.
2. **Disegno della ricerca e del primo percorso operativo:** Director e Astra chiudono definizioni osservabili, contributi dei segnali, dati, divisione sviluppo/verifica e modello di costo proporzionato. Gian decide i vincoli personali necessari. Nessun incarico aperto a Claude per “trovare la strategia migliore”.
3. **Studio e prima traduzione eseguibile:** raccogliere conoscenza nel perimetro autorizzato, formulare un candidato completo e implementarlo con esempi discriminanti. Non ottimizzare combinazioni senza limite.
4. **Percorso integrato visibile nell'app:** analisi, call, aggiornamenti, storia e conto simulato devono avere significati coerenti. Gian prova incrementi utili; il design Figma serve a questa esperienza.
5. **Verifica storica separata e demo:** valutare strategia, costi, gestione e collegamento nei rispettivi ambienti. La demo non sostituisce lo storico e lo storico non prova la gestione reale degli ordini.
6. **Eventuale reale:** decisione separata dell'Owner sulla base delle evidenze, con capitale e limiti espliciti. Nessuna promozione automatica.

Non fissiamo qui una durata fittizia o una promessa di successo. Ogni macrofase deve finire con un risultato utilizzabile, un'incertezza ridotta o un blocco preciso, non soltanto con un altro elenco di possibili studi.

## 32. Decisioni ancora da chiudere prima di programmare le parti relative

| Decisione aperta | Perché serve | Responsabilità |
|---|---|---|
| Strumento Binance preciso e fattibilità demo | LONG/SHORT, costi e protezioni dipendono dal prodotto | Director verifica fatti; Astra decide conflitti; Owner approva accessi |
| Date e fonte del nuovo storico | Evitare dati inadeguati o periodi già esposti chiamati nuovi | Director propone nel perimetro; Astra/Owner autorizzano |
| Definizione dei movimenti studiati | Separare studio retrospettivo da trade realmente riconoscibile | Astra/Director |
| Regole concrete dei segnali e delle combinazioni | Le famiglie non sono ancora un algoritmo | Astra/Director |
| Origine e disponibilità delle barre 45m/1D | Evitare disallineamenti e informazioni future | Director, prima dell'incarico tecnico |
| Entry, uscita, revisione target/stop e orizzonti | Un candidato deve includere tutta la gestione | Astra/Director con vincoli dell'Owner |
| Capitale, leva, rischio e limiti personali | Sono decisioni dell'Owner, non valori da inventare | Gian, assistito da Astra/Director |
| Ordini pendenti, passaggio manuale/automatico e ripresa | Evitare responsabilità e stati operativi ambigui | Director specifica; Astra sui conflitti strutturali |
| Modello dei costi ed esecuzioni ambigue | Rendere interpretabile il risultato netto | Astra/Director |
| Criteri di avanzamento alla demo e al reale | Un saldo isolato non è un'autorizzazione | Astra/Director; reale solo Owner |
| Stack applicativo, test budget e installazione | Evitare di importare complessità precedente senza bisogno | Director nel mandato architetturale |

Non occorre rivolgere subito tutte queste domande a Gian. Quelle tecniche e metodologiche spettano al team; quelle su preferenze, denaro e autorizzazioni personali vanno poste all'Owner quando diventano necessarie, in linguaggio semplice. Nessuna esecuzione deve precedere le scelte indispensabili per interpretarla.

## 33. Istruzioni per una nuova chat che riceve solo questo documento

Considera questo testo la memoria funzionale del nuovo progetto, datata 16 ottobre 2026, non una prova dello stato attuale del codice. Prima di agire sulla repository consulta lo stato corrente e l'incarico attivo. Non riattivare vecchi metodi, studi o autorizzazioni.

Parla a Gian in modo semplice. Ricorda che vuole partecipare alla strategia, che accetta un progetto lungo, che non pretende infallibilità e che vuole vedere progressi concreti. Non ridurre il progetto a tre pattern, a una somma di indicatori o a un grafico descrittivo. Non promettere un trader professionale già ottenuto.

Mantieni i ruoli: Astra direzione, Director ragionamento e gestione operativa, Claude esecuzione tecnica. Non chiedere ad Astra ogni microdecisione e non delegare all'esecutore la scelta del metodo. Non creare un nuovo documento per ogni dubbio se basta chiudere una decisione nella macrofase corrente.

Il primo lavoro dopo questa registrazione deve essere un incarico completo deciso dal team, non l'avvio spontaneo di backtest, acquisizioni o trading. Se il testo non contiene una soglia o una regola, non significa che sia lecito inventarla.

## 34. Storia delle revisioni

| Versione | Data | Variazione |
|---|---|---|
| 1.0 | 2026-10-16 | Prima sintesi funzionale autonoma del nuovo progetto; separazione da archivio, decisioni aperte esplicite, organizzazione dei ruoli e del task unico |

Per approfondire senza cambiare l'autorità di questo documento: indice delle fonti `docs/references/SOURCES.md`, memoria delle esposizioni `docs/research/EXPOSURES.md`, provenienza del recupero `docs/provenance/RECOVERY.md`. Non serve leggerli per comprendere l'obiettivo e il modo di lavorare descritti qui.
