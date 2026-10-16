# Incarico corrente

**Stato: DRAFT — proposta del Director per review di Astra; nessuna esecuzione autorizzata.**

ID: DESIGN-001. Data: 16 ottobre 2026.
Macrofase: primo disegno di studio e primo risultato tecnico visibile.
Responsabile del disegno e della review: Director. Orchestratore: Astra.
Base documentale verificata: `16d8461d7db66e4ba9a2ebe96ada68935641040c`.
Mandato: messaggio di inizializzazione di Astra trasmesso dall'Owner il 16 ottobre.
Questo file raccoglie una proposta unica. Non modifica le decisioni funzionali e non è un ordine per Claude.

## 1. Risultato e confini

Costruire conoscenza su come struttura, livelli, andamento, partecipazione e ampiezza delle oscillazioni si combinano prima/durante/dopo sviluppi BTC. Il primo incremento proposto è un esploratore temporale su esempi sintetici che renda controllabile la disponibilità delle osservazioni; dopo distinta autorizzazione potrà essere alimentato da storico di sviluppo.

Non cerchiamo la migliore combinazione di indicatori. Non approviamo ancora ingressi, gestione della posizione o strategia. La lettura continua resta distinta dalla decisione operativa.

Decisioni già chiuse: BTC LONG/SHORT; 45m e 1D; una posizione; nessun aumento; parziali ammesse; demo prima del reale; PC e strumenti gratuiti; Fibonacci incluso; ciclicità e order book rinviati. Fonte funzionale unica: `docs/functional/PRODUCT-CONTEXT.md`.

Non occorrono adesso risposte dell'Owner su capitale/leva/rischio: non simuliamo il suo conto. Quelle scelte diventano necessarie prima di un candidato esecutivo e della sua valutazione economica.

## 2. Provenienza del ragionamento

Consultati integralmente: PRODUCT-CONTEXT, AGENTS, STATE, current_task, README, SOURCES, EXPOSURES alla base indicata. Verificato il riferimento main prima della proposta.

Fonti esterne primarie già indicizzate, riaperte il 16 ottobre:
- Adam H. Grimes, Fundamental Trading Patterns: https://www.adamhgrimes.com/fundamental-trading-patterns/
- Adam H. Grimes, One step ahead: https://www.adamhgrimes.com/one-step-ahead/
- Carol Osler, pagina/abstract di Support for Resistance (2000): https://www.newyorkfed.org/research/epr/00v06n2/0007osle.html
- Carol Osler, pagina/abstract di Currency Orders and Exchange-Rate Dynamics (2001): https://www.newyorkfed.org/research/staff_reports/sr125.html

Non sono stati letti integralmente i PDF di Osler in questo incarico. Gli abstract riguardano cambi valutari, non BTC: motivano una domanda sui livelli, non dimostrano una risposta per questo progetto. Grimes illustra strutture di continuazione e fallimento e la relazione fra movimento e reazione; non fornisce queste formule BTC o soglie universali.

Consultate le sezioni 1–14 del dossier secondario LIB-004, Systematic Trading, nell'archivio al commit b8f8e2d4b9eb531dcab4e609a037c02024087414:
https://github.com/C-Gian/algorithmic-trader-archive/blob/b8f8e2d4b9eb531dcab4e609a037c02024087414/source_notes/LIB-004-SYSTEMATIC-TRADING.md
Non riletto il libro originale. Considerati soltanto i riassunti bibliografici su previsione distinta da posizione, semplicità, idee prima della ricerca estesa, costi e separazione temporale. Escluse interpretazioni del vecchio Director, vecchi vincoli e parametri. Nessuna regola EWMAC, scala di forecast o architettura Carver adottata.

Tutte le convenzioni numeriche seguenti sono **proposte nuove del Director per rendere misurabile lo studio**, non regole estratte dalle fonti, ottimizzate sui prezzi o approvate dall'Owner. Astra può modificarle prima del congelamento. Un esito negativo resta pubblicabile; non cerchiamo poi un'altra soglia nello stesso studio per ribaltarlo.

## 3. Strumento e dati: fattibilità documentale

Proposta: Binance USDⓈ-M BTCUSDT perpetual lineare, quotato e regolato in USDT. Identità precisa da verificare nei metadati prima dell'acquisizione autorizzata; nessun sostituto automatico se non disponibile. Distinguiamo mercato di produzione per la ricerca e ambiente demo per collaudo futuro.

Documentazione ufficiale consultata il 16 ottobre:
1. Archivio pubblico Binance: https://github.com/binance/binance-public-data
2. General Info USDⓈ-M: https://developers.binance.com/en/docs/products/derivatives-trading-usds-futures/general-info
3. Market Data REST: https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data
4. Trade REST: https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/trade

Il repository ufficiale descrive archivi daily/monthly, campi delle klines futures e checksum; segnala possibili correzioni successive dei file. La documentazione REST descrive klines, mark-price klines, exchangeInfo e fundingRate storico paginabile. General Info indica demo-fapi.binance.com e demo-fstream.binance.com e dice che la maggior parte degli endpoint è disponibile in testnet. Trade REST documenta ordini condizionali, trigger su CONTRACT_PRICE/MARK_PRICE, closePosition e reduceOnly con incompatibilità specifiche.

Conclusione circoscritta: esiste una via documentata per dati pubblici e API demo. Non verificati: completezza di BTCUSDT nelle date proposte, possibilità di scarico dall'ambiente Owner, accessibilità della demo dal suo account/paese, commissioni demo, corrispondenza dei riempimenti e del funding al mercato reale. Nessun conto o endpoint di mercato interrogato.

Piano dati futuro:
- klines CONTRACT_PRICE 1m con OHLC, volume base, volume quote, numero scambi e campi taker originali; niente ricostruzione di order flow dal solo volume;
- aggregazione locale a 45m e 1D; niente dipendenza da una barra 45m nativa;
- mark 1m e funding storico quando serviranno costi/protezioni; non requisiti del primo esploratore sintetico;
- provenienza: URL, strumento, tipo di prezzo, intervallo, unità temporale, estremi, data acquisizione, checksum del fornitore se presente e hash locale;
- nessun riuso di prezzi OKX o del dataset Owner; nessuna riqualificazione di spot come futures;
- costo di accesso pubblico non equivale a licenza di ridistribuzione: mantenere i dati fuori dal repository pubblico e verificare i termini pertinenti prima di eventuale distribuzione.

Copertura e qualità saranno un gate dell'acquisizione futura: unicità, ordinamento, passo, conteggio, OHLC coerenti, volumi non negativi, unità temporale verificata, buchi e duplicati dichiarati. Una checksum corretta verifica il file, non che non manchino minuti. Non colmare buchi con candele inventate.

## 4. Finestre proposte, non aperte

Intervalli UTC con inizio incluso e fine esclusa:

| Uso | Intervallo proposto | Trattamento |
|---|---|---|
| Warmup sviluppo | 2022-10-01 → 2023-01-01 | Solo inizializzazione, nessun esito valutato |
| Sviluppo | 2023-01-01 → 2026-01-01 | Circa tre anni; contiene periodi già esposti, nessuna etichetta di novità |
| Warmup verifica | 2025-10-01 → 2026-01-02 | Calcolo fisso dello stato; include accesso protetto da autorizzare espressamente |
| Verifica distinta proposta | 2026-01-02 → 2026-09-01 | Resta protetta fino a distinto mandato dopo congelamento del candidato |

Il registro EXPOSURES non certifica che 2023/2024 siano mai stati visti: sono sviluppo per scelta, non holdout incontaminato. Anche cambiare exchange non azzera la conoscenza del periodo.

La verifica proposta utilizza parte di gennaio–agosto 2026 oggi protetta. **Non è richiesta né concessa la sua apertura ora.** Astra deve approvare la riserva, poi il mandato specifico di apertura deve identificare warmup, input, orizzonti e accessi. Se emergono ulteriori esposizioni materiali, il periodo viene riclassificato e si ridisegna la verifica prima dell'accesso. Non si sostituisce silenziosamente con dati futuri.

Per tutti gli orizzonti a 72 ore l'ultimo istante origine ammesso è strettamente prima della fine meno 72 ore. Gli altri istanti restano nel conteggio di copertura come censurati, non fallimenti. Nessun tail oltre il periodo: sviluppo con origini < 29 dicembre 2025 00:00; verifica con origini < 29 agosto 2026 00:00. Il primo gennaio protetto non viene letto per completare sviluppo.

Le finestre future HDP-001 e A rimangono INACTIVE, senza modifiche. Questa proposta non autorizza acquisizioni neppure sullo sviluppo.

## 5. Tempo e disponibilità

Clock logico di analisi: chiusure 45m, 32 al giorno. Origine UTC 00:00; barre [00:00,00:45), [00:45,01:30), ecc.; giornata [00:00,00:00 successiva). Un'osservazione a t usa solo barre terminate entro t. A mezzanotte si chiudono e calcolano entrambe le scale prima di creare lo snapshot.

OHLC: primo open, massimo high, minimo low, ultimo close; volumi e conteggi sommati. Una barra aggregata richiede tutti i minuti attesi; altrimenti è INCOMPLETE. Il giornaliero corrente resta escluso dalle osservazioni definitive. Un gap rende non disponibili le finestre che lo attraversano; si azzerano anche sequenze pivot e ancore correnti, conservandone la storia, e si ricostruisce il warmup completo necessario, senza forward-fill. Nessun segnale equivale a zero se non calcolabile.

Ogni oggetto conserva almeno event_time, available_at, identità, versione e input. Il tempo logico assume la disponibilità alla chiusura per lo studio; non dimostra latenza live zero. Un futuro replay esecutivo deve separare disponibilità e azione.

## 6. Dizionario iniziale contenuto

Per ciascuna scala si calcolano le osservazioni seguenti. Niente punteggio o votazione.

**Volatilità / unità di confronto.** TR=max(H-L,abs(H-Cprecedente),abs(L-Cprecedente)); A è media aritmetica degli ultimi 20 TR completi. Servono 21 chiusure consecutive. A=0 o dati mancanti rendono indisponibili i rapporti. A/prezzo descrive l'ampiezza relativa; non è una probabilità o uno stop.

**Medie.** SMA20 e SMA50 delle chiusure, distanza (SMA20-SMA50)/A, pendenza (SMA20[t]-SMA20[t-4])/A e posizione (C-SMA20)/A. Un incrocio esiste quando il segno della distanza passa da <=0 a >0 o da >=0 a <0; zero mantenuto non è un nuovo incrocio. Le medie descrivono persistenza e allontanamento: non rappresentano conferme indipendenti della stessa struttura. Numeri scelti come due velocità leggibili, senza ricerca del periodo vincente.

**Struttura.** Pivot high a i se H_i supera strettamente i due high precedenti e i due successivi; pivot low speculare. Disponibile solo alla chiusura i+2. Parità non genera pivot; barra simultaneamente pivot high e low registrata ambigua ed esclusa dalla sequenza di swing. Conservare anche gli scarti. Confronto degli ultimi due high confermati e degli ultimi due low: entrambi crescenti, entrambi decrescenti, misti o insufficienti; parità = misti. Non chiamare questi stati certezza di trend futuro.

**Livelli.** Livelli base: ultimo high e low confermati, high/low del giorno precedente. Ogni livello mantiene origine e data di disponibilità. Distanza firmata (C-Livello)/A. Fascia descrittiva di prossimità +/-0,25A; usa A disponibile allo snapshot, senza alterare il livello. Attraversamento a chiusura rilevato rispetto a un livello già disponibile nello snapshot precedente. Salvataggio del livello e A di allora: successivi pivot non riscrivono l'evento. Livelli superati restano nella storia, non vengono rilanciati automaticamente come nuovi.

**Volume.** Rapporto fra volume base della barra appena chiusa e mediana delle 20 precedenti della stessa scala; mediana zero = indisponibile. Volume quote e numero scambi restano osservazioni descrittive di controllo. Non usare volume di mark/index né confondere acquisti aggressivi con flusso netto di tutti gli operatori. Nessuna etichetta automatica “volume alto = acquisto”. La normalizzazione iniziale non corregge stagionalità intraday: limite da mostrare nelle tabelle per fascia oraria, senza fit supplementare.

**Fibonacci.** Sequenza alternata di pivot confermati: se arriva lo stesso tipo sostituire il terminale solo con un estremo strettamente più esteso; altrimenti conservare il precedente. All'arrivo di un tipo opposto appendere. Ogni sostituzione crea una versione, senza cancellare la precedente. Ancore = ultimi due estremi opposti della sequenza, solo quando entrambi disponibili. Indicando in ordine temporale P0,P1, progressione u=(C-P0)/(P1-P0), ritracciamento r=1-u. Riferimenti r=0,382; 0,5; 0,618; 0,786 e proiezioni u=1,272; 1,618. Il 50% è una convenzione di ritracciamento, non un rapporto Fibonacci. Nessuna attrazione del prezzo presunta. Ancore identiche o assenti = indisponibile; ancore superate non si spostano con un estremo futuro non confermato. Registrare ancore, disponibilità, r continuo e distanze dai riferimenti. Questi livelli sono un linguaggio descrittivo, non take profit automatici.

Warmup per snapshot pienamente analizzabile: almeno 54 barre complete per scala (SMA50 e pendenza; ulteriori osservazioni restano parziali se mancano pivot). Non inventare due pivot per dichiarare pronto lo stato. I giorni proposti di warmup non garantiscono che esistano tutti i pattern.

## 7. Unità di studio e movimenti

Popolazione di base: **tutte** le chiusure 45m del periodo, anche senza pattern, movimento o indicatori disponibili. Registrare eleggibilità e motivo di esclusione prima di leggere gli esiti. Per misurare gli esiti bastano C_t e A45m_t validi e la copertura futura richiesta: l'assenza di pivot, livelli, medie giornaliere o Fibonacci non esclude la riga dalla popolazione base. Ogni relazione dichiara separatamente i propri input mancanti. Gli esiti non sono input del motore delle osservazioni.

Per ogni origine t eleggibile, prezzo base p=C_t e scala a=A45m_t congelata:
- orizzonte principale 32 barre = 24h;
- orizzonti secondari prefissati 4 e 96 barre = 3h e 72h, riportati separatamente, mai scelti dopo per il risultato migliore;
- variazione finale (C[t+h]-p)/a, massima escursione verso alto e basso rispetto a p, tempi del primo contatto con p+2a e p-2a, percorso delle chiusure;
- etichetta retrospettiva: solo barriera alta raggiunta, solo bassa, entrambe, nessuna; aggiungere separatamente segno e ampiezza della variazione finale;
- se entrambe nella stessa barra 1m, ordine UNKNOWN; se in minuti distinti, ordine osservabile a risoluzione minuto, senza fingere precisione tick;
- sottoclasse quieta se l'intero percorso resta fra p-a e p+a (inclusi bordi); “nessuna barriera 2a” non significa da sola mercato fermo;
- gap nel futuro = esito incompleto, mai “nessun movimento”.

Le barriere 2a delimitano un movimento in unità della volatilità preesistente; non sono target/stop o criteri economici. Non sostituiamo a con volatilità futura.

Prima/durante/fine: per ogni origine si rendono visibili le 32 barre precedenti, gli snapshot successivi nel percorso e il punto finale a h. Eventuali estremi e primo contatto sono marcatori retrospettivi nella vista degli esiti, mai “ingresso/uscita ideali”. Le origini temporali sono fisse: non si cerca dopo il minimo perfetto da cui far partire ogni episodio. Il metodo non pretende di ricostruire tutta la durata naturale dei trend.

Per limitare doppio conteggio:
- tutti gli snapshot servono a copertura e descrizione;
- confronto principale a 24h sulla coorte prefissata di origini UTC 00:00 (finestre adiacenti non sovrapposte);
- tutte le altre fasi orarie come descrizione separata, per controllare dipendenza dall'orario;
- risultati 72h e istanti ravvicinati esplicitamente sovrapposti; niente test binomiale che assuma indipendenza;
- riassunti mensili, numerosità, concentrazione temporale e dispersione; nessuna significatività convenzionale o certificazione con poche occorrenze. Una futura inferenza formale richiede un mandato proprio.

## 8. Tre relazioni di contesto, senza ricerca combinatoria

Si fissano tre domande, con esiti principali a 24h. Nessuna soglia viene aggiustata in base ai risultati.

R1 — Struttura/medie: a parità di struttura 45m crescente o decrescente, cosa cambia quando la struttura 1D concorda, contrasta o è mista/insufficiente? Distinguere poi distanza delle medie concorde/contraria e i valori continui di pendenza. Confronto con la sola struttura 45m e con distribuzione incondizionata della stessa direzione; SMA non diventa un secondo voto indipendente.

R2 — Livello/partecipazione/ampiezza: dopo una chiusura oltre un livello precedentemente noto, il prezzo mantiene il lato superato oppure rientra? Un episodio si apre solo al primo attraversamento di ciascuna coppia livello/direzione; nessun nuovo episodio per quella coppia per 32 barre. Livello e a congelati. Rientro = prima chiusura di nuovo dal lato originario entro 32 barre, non stop simulato. Confrontare presenza o assenza del rientro, escursioni, volume relativo <=1 o >1 e TR/A <=1 o >1, entro il contesto strutturale. Soglie 1 indicano la rispettiva misura di riferimento, non qualità. Risultati grezzi, non spiegazione causale di stop hunting.

R3 — Ritracciamento/contesto: per ancore disponibili, classe di r: <0; [0,0,382); [0,382,0,618]; (0,618,1]; >1. Stratificare per concordanza della struttura giornaliera con P1-P0; mostrare anche r continuo. Confrontare le escursioni successive nella direzione della gamba e opposta e gli esiti a 24h. Niente scelta ex post della coppia di ancore “giusta”. L'intervallo centrale non dimostra un effetto Fibonacci: confrontare descrittivamente fasce adiacenti e trattare eventuali differenze come ipotesi di sviluppo, non come prova della specificità dei rapporti.

Per ogni domanda: conteggio di tutti i casi, esiti mancanti, contesti senza successivo movimento, movimenti senza il contesto, distribuzioni e mesi. “Falso allarme” significa qui che una condizione descrittiva non è seguita dall'esito ipotizzato, non una call perdente. Prima di parlare di precisione predittiva servirà una regola che emetta realmente un'aspettativa a t.

Le classi sono tassonomia iniziale, non un modello finale. Niente test automatico delle sei famiglie in tutte le combinazioni e niente ranking per P&L.

## 9. Costi ed esecuzione: modello iniziale proposto

Questo studio osservativo **non produce trade né un saldo**. Prepara un modello per il candidato successivo.

Proposta di modello semplificato per futuri trade lineari:
- entry/exit market, nessun maker fill presunto; quantità fissa per ogni segmento salvo parziali esplicitamente definite;
- fee f=5 punti base per lato come ASSUNZIONE DI STUDIO, non tariffa Binance verificata;
- scostamento avverso s=2 punti base per lato; stress prefissato f=10 e s=10 per lato;
- price_buy=prezzo_riferimento*(1+s), price_sell=prezzo_riferimento*(1-s);
- fee su ogni nozionale effettivamente eseguito, incluse parziali;
- funding a ogni timestamp storico effettivo attraversato, posizione in essere appena prima del timestamp: cashflow=-d*q*mark*rate, d=+1 long/-1 short; non assumere sempre intervallo di otto ore;
- P&L=sum(d*q_segmento*(Puscita-Pingresso))-fee+cashflow_funding. Rapporti normalizzati al nozionale d'ingresso, mai chiamati rendimento del capitale.

La decisione calcolata alla chiusura non si esegue retroattivamente a quella chiusura. Proposta prudenziale: prima apertura 1m con timestamp >= t+1 minuto, poi scostamento avverso; nel frattempo non esiste posizione simulata. Trigger di stop/target su CONTRACT_PRICE nel modello iniziale, esplicito e distinto da un'eventuale futura scelta MARK_PRICE.

Se un ordine protettivo già attivo è oltrepassato all'apertura, prezzo riferimento = apertura avversa, non lo stop teorico. Se stop e target sono toccati nello stesso minuto e l'ordine è ignoto: risultato con stop prima più conteggio delle ambiguità; confronto con estremo favorevole solo come intervallo di sensibilità, mai risultato prescelto. Gap durante posizione = segmento non valutabile e blocco del risultato aggregato completo, non uscita inventata.

Non modella coda ordini, impatto dipendente dalla quantità, liquidazioni o margine. Prima di una prova economica servono capitale, leva, quantità, compatibilità con minimi/tick e politica completa di gestione. Una prova a nozionale normalizzato non li sostituisce. Funding o fee mancanti impediscono l'etichetta “netto completo”; nessun costo ignoto assunto zero.

Lo scenario di costo mostra se un movimento è piccolo rispetto alla frizione ipotizzata. Non prova che la strategia guadagni, che la dimensione sia eseguibile o che la demo abbia questi prezzi.

## 10. Primo incremento tecnico proposto a Claude

**Nessuna esecuzione ora.** Dopo review Astra: incarico separatamente reso READY, limitato a esempi sintetici e nessuna rete.

Risultato: motore di osservazioni e report HTML locale interattivo, alimentato da fixture deterministiche create per controllare i casi; nessuna architettura applicativa definitiva scelta. Proposta proporzionata: Python per trasformazioni e JSON; HTML/JS senza dipendenze remote per una vista utilizzabile. Eventuali nuove dipendenze richiedono una ragione concreta. Non importare il vecchio frontend.

Contratti:
- ingresso: barre 1m sintetiche, identità SYNTHETIC non Binance, metadati di completezza;
- aggregati e snapshot secondo sezioni 5–6;
- stream delle osservazioni separato dagli esiti futuri della sezione 7;
- identificatori stabili, eventi di disponibilità, ancore versionate, null con ragione;
- nessuna previsione, ordine, conto, probabilità o P&L costruiti per riempire campi.

Gian vedrà un solo grafico, scelta 45m/1D, cursore temporale, avanti di una barra, osservazioni spiegate e motivi dei dati mancanti. Le porzioni future e le etichette degli esiti non sono visibili in modalità temporale. Comando distinto “mostra il seguito” passa a vista retrospettiva esplicitamente etichettata; tornare al passato ricostruisce gli snapshot originali. Grafico e pannelli devono fermarsi allo stesso cutoff. Esempi visibili: pivot non ancora confermato, nuovo livello noto, ancore aggiornate, movimento che fallisce, fase quieta e gap.

Non pretendiamo una simulazione cieca sicura: un HTML locale può contenere gli esiti e l'Owner può leggerne il sorgente. È uno strumento sullo sviluppo/sintetico, **mai un mezzo per aprire un periodo protetto**. La separazione dei risultati di verifica richiederà un controllo di accesso/processo prima del suo mandato.

Fixture: almeno 70 giorni di minuti sintetici, anche inizializzazione, percorso controllato per creare esempi crescenti/decrescenti, reazione, superamento e rientro, quiete; casi indipendenti con high uguali, dual pivot, denominatore zero, gap e cambio giorno. Nessun prezzo reale copiato o generato fingendo che sia una storia di BTC.

Prima incrementale: solo calcolo/report e test causali; le tabelle aggregate di R1–R3 e qualsiasi acquisizione reale saranno un task successivo dopo autorizzazione dati. Non ricreare ora una piattaforma completa o un simulatore exchange.

## 11. Criteri di accettazione futuri

Verifiche mirate, niente CI/suite generale:
1. Lo stesso prefisso di dati produce gli stessi snapshot anche cambiando il futuro; esiti separati.
2. Pivot visibile a i+2, mai prima; sostituzione ancore conserva versioni.
3. 45 minuti esatti e confine UTC giornaliero; nessun giornaliero futuro usato.
4. Gap, parità e volatilità zero producono i casi espliciti sopra; nessuno zero sostituisce un dato assente.
5. Fixture nota riconcilia OHLC/volumi e rapporti con pochi calcoli manuali.
6. Prova visiva del report: cutoff, toggle seguito e 45m/1D concordano; nessun campo si presenta come call corrente.
7. Nessuna chiamata a rete, chiave, acquisizione, backtest, ordine, riuso strategia o accesso Owner.

Consegna futura: file pertinenti, comandi di generazione/apertura, controlli effettivamente eseguiti, screenshot/report sintetico, limiti e commit. Commit/push dell'esecutore verranno autorizzati esplicitamente nel READY; non sono autorizzati da questa bozza. Il Director distingue review statica, verifiche rieseguite e dichiarazioni di Claude.

## 12. Che cosa impareremo e come decidere il seguito

Primo incremento sintetico: possiamo verificare che il programma descriva ciò che è conoscibile, senza riscrivere il passato, e rendere comprensibile la lettura a Gian. Nessuna evidenza finanziaria.

Studio sviluppo successivo: distribuzioni e casi contrari delle tre relazioni; eventuali ipotesi condizionate abbastanza precise da diventare un candidato. I risultati possono essere insufficienti o contrari. Non si promuove un'osservazione per qualche grafico favorevole.

Prima della verifica separata: candidato completo congelato con lettura, condizioni di ingresso, stop, target, validità, gestione, parziali, astensione, capitale/rischio Owner e costi. Dati, software, versioni e criteri di giudizio fissati prima di aprire gli esiti. Il presente disegno non finge di aver già definito quel candidato.

Confronti economici da specificare allora: liquidità/inattività come riferimento zero e strategia semplice di controllo realmente eseguibile con costi ed esposizione comparabili; buy-and-hold eventualmente contestuale, non automaticamente un confronto a rischio uguale. Nessuna soglia numerica di successo o win rate introdotta ora.

## 13. Decisione richiesta ad Astra e pubblicazione

Raccomandazione del Director:
- approvare questo disegno come primo studio delimitato, con eventuali correzioni in una review unica;
- approvare soltanto il primo incremento sintetico per il prossimo READY;
- valutare BTCUSDT perpetual e finestre come proposte, senza accesso account o apertura protetta;
- mantenere acquisizione e studio storico per un mandato esplicito successivo.

Astra deve decidere se il disegno è sufficientemente concreto e metodologicamente coerente; eventuali cambi strutturali rientrano nel suo ruolo. L'Owner conserva autorizzazioni a dati/conti e rischio personale.

Pubblicazione corrente: solo Director, documentazione current_task e STATE su main, senza modifica del documento funzionale perché non sono state approvate nuove decisioni di prodotto.

## Spazio dell'esecutore

Non attivo. Non avviare il DRAFT.

## Review del Director

Preparazione documentale propria: lettura dei documenti indicati, controllo di coerenza di formule/date/limiti e consultazione delle fonti con qualificazione sopra. Nessun test del codice, dataset o funzionamento demo eseguito. Non esiste consegna Claude da accettare.
