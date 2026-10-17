# CAND-001/v1 — movimento, reazione, tentativo di ripresa

**Versione iniziale completa: 1.0.0. Registrazione ex ante del Director, 17 ottobre 2026.**
Mandato Astra: primo candidato completo e ciclo storico di sviluppo. Nessun esito economico di questo candidato è stato esaminato per scegliere queste regole. Non è una conclusione di OBS-001, una strategia validata o un'autorizzazione reale.

## 1. Ipotesi, provenienza e responsabilità

Ipotesi verificabile: dopo una gamba direzionale abbastanza ampia, una reazione contenuta e una chiusura che tenta di riprendere il movimento possono offrire un ingresso con invalidazione identificabile e spazio verso il precedente estremo. La versione può fallire per la selezione, l'ingresso, la gestione o le frizioni; non la si promuove perché riconosce una figura sul grafico.

Fonti primarie rilette dal Director il17ottobre:
- Adam Grimes, Fundamental Trading Patterns: https://www.adamhgrimes.com/fundamental-trading-patterns/ — alternanza gamba/reazione e ingresso al tentativo di ripresa.
- Adam Grimes, One step ahead: https://www.adamhgrimes.com/one-step-ahead/ — importanza della reazione successiva a un movimento e gestione del rischio.

Sono motivazioni qualitative. **Tutte le formule, soglie, durate, precedenze e gestione qui sotto sono adattamenti nostri**, non regole numeriche attribuite a Grimes, parametri ottimali o dati recuperati da A/RETURN/E/a2x del vecchio progetto. Si sceglie una sola implementazione simmetrica LONG/SHORT, non una ricerca di combinazioni.

Leggere insieme current_task.md per dati, sequenza operativa, verifiche e pubblicazione. Questo file è la specifica versionata del candidato, non un secondo incarico. config/CAND-001-v1.json deve trascriverne le convenzioni prima di qualunque backtest economico.

## 2. Dati, clock e sei famiglie

Stesso strumento di OBS-001: Binance Vision, BTCUSDT perpetual USDⓈ-M, prezzo negoziato1m. Decisioni alle chiusure45m UTC; osservazioni45m/1D calcolate esattamente dalle definizioni OBS-001/v1, senza cambiare SMA, TR, pivot o disponibilità. Giorno corrente non chiuso escluso. Esecuzione modellata sui minuti futuri, modulo separato dagli input della decisione.

| Famiglia | Ruolo iniziale | Uso |
|---|---|---|
| Struttura/pivot45m | Decisionale | Contesto direzionale, gamba confermata e invalidazione per struttura opposta |
| Livelli | Decisionale | Estremo di reazione per stop; estremo della gamba per obiettivo; pivot successivi per protezione |
| Volatilità | Decisionale | A45m per riconoscere ampiezza della gamba e buffer dello stop |
| Medie SMA20/50 | Contestuale | Valori e distanze registrati/spiegati; nessun requisito d'ingresso o voto |
| Volume relativo | Contestuale | Registrato a t; nessun filtro o modifica di quantità |
| Fibonacci | Contestuale | Ancore/rapporti osservativi mostrati; nessun rapporto Fibonacci usato come conferma obbligatoria |

Struttura giornaliera solo contestuale, anche se contraria/mista/indisponibile. Non bloccare il candidato per SMA50, volume o Fibonacci giornaliero mancanti. Per identificare la gamba si riusa la sequenza alternata di pivot di OBS-001 come struttura geometrica; ciò non attribuisce potere predittivo ai rapporti Fibonacci. I livelli del piano sono identificati separatamente dai livelli osservati.

Parametri fissati:
- soglia ampiezza gamba: 3*A0;
- durata massima gamba:32barre45m (24h), minima una barra;
- reazione: almeno2barre chiuse dopo la candela estrema, almeno una chiusura contro il movimento; profondità tra1/4 e3/4 della gamba, bordi inclusi;
- scadenza setup:12barre45m (9h) dalla chiusura della candela estrema;
- buffer stop:0,10*A0;
- rapporto spazio/rischio minimo:1,5 lordo, sia su prezzo indicativo sia su ingresso effettivamente modellato;
- ritardo azioni discrezionali:60secondi dopo la chiusura45m;
- durata massima posizione:24h dall'ingresso modellato;
- una posizione e un solo ingresso per episodio, nessun incremento/parziale.

Motivazione:3A distingue una gamba da pochi TR ordinari; quarti della gamba delimitano una reazione apprezzabile che ne conservi una parte;9h limita l'attesa,24h limita il trade.1,5 richiede spazio superiore alla distanza di invalidazione. Sono convenzioni leggibili, non stime di probabilità o profitto atteso. Nessuna efficacia desunta dal loro valore.

## 3. Oggetti e stati

Oggetti distinti: ObservationSnapshot, Episode, Expectation, Call, EntryRequest, Fill, Position, PlanVersion, ManagementEvent e Cashflow. Una call non è un eseguito né una posizione. Tutti hanno ID, candidateVersion, event_time, available_at, riferimenti input e motivi. Storia append-only, niente correzioni retroattive per includere pivot futuri.

Stati episodio: IDLE → WATCH_REACTION → CALL_REQUESTED → OPEN → CLOSED. Cancellazioni/astensioni terminano come EXPIRED/INVALIDATED/REJECTED/SKIPPED_BUSY, con codice e fatti. Non emettere call mentre si è solo in osservazione. Le decisioni NO_NEW_SETUP/WAIT_REACTION/WAIT_RESUMPTION/ABSTAIN sono reali stati del candidato, non testo fittizio della dashboard.

Un ID gamba dipende dai due pivot P0/P1 e dai loro tempi/identità, non dal risultato futuro o dal numero globale di righe. Ogni gamba viene considerata una volta quando diventa disponibile. Un REPLACE di P1 è una nuova gamba con identità della nuova candidata. Un KEEP non crea una nuova gamba. Le gambe divenute note mentre episodio/ordine/posizione occupano il candidato sono registrate SKIPPED_BUSY e non recuperate dopo.

## 4. Riconoscimento del movimento

A chiusura t0, soltanto se IDLE e senza posizione/richiesta:
1. La sequenza alternata di pivot45m ha appena APPEND o REPLACE e rende disponibili due estremi opposti P0,P1, in ordine temporale.
2. P0 è LOW e P1 HIGH per LONG (d=+1); P0 HIGH e P1 LOW per SHORT (d=-1). L=d*(P1.price-P0.price)>0.
3. Struttura45m a t0 è UP per LONG o DOWN per SHORT, dagli ultimi due high e due low confermati non ambigui.
4. Da P0.candidateOpen a P1.candidateOpen passano da1a32barre45m incluse; tutte le barre fino a t0 nel segmento sono complete.
5. A0=A45m(t0)>0 e L>=3*A0.

Se fallisce un requisito, registrare astensione con motivo, consumare quella gamba; non riesaminarla più tardi con volatilità o struttura diverse. A0,P0,P1,L restano congelati nell'episodio. Nessun futuro high/low non confermato modifica la gamba.

P1 è noto due barre dopo la propria candela: si possono leggere ora le due barre di reazione già chiuse, ma **non emettere retroattivamente una call** in quelle barre. Il primo trigger ammissibile è una chiusura45m strettamente successiva a t0.

## 5. Reazione, contraddizioni e tentativo di ripresa

Sia i la candela di P1 e k la candela chiusa corrente. La reazione comprende le barre i+1..k, mai l'interno della candela di P1 (ordine intrabar ignoto).
- LONG: Rext=min(low delle barre di reazione), profondità=(P1.price-Rext)/L.
- SHORT: Rext=max(high delle barre di reazione), profondità=(Rext-P1.price)/L.
- Contare almeno una chiusura contro movimento: d*(C_j-C_(j-1))<0 per j>i.
- k-i>=2. La creazione a t0 può già soddisfarlo, ma il trigger aspetta almeno la chiusura seguente.

Prima di verificare un trigger, le seguenti contraddizioni terminano l'episodio:
1. input richiesto incompleto/gap o nuova segmentazione;
2. struttura45m disponibile opposta al verso; MIXED non è di per sé invalidazione;
3. profondità>3/4 o d*(C_k-P0.price)<=0;
4. obiettivo già raggiunto dopo P1: LONG qualsiasi high nelle barre i+1..k >=P1.price, SHORT qualsiasi low<=P1.price. Il movimento fino al vecchio estremo è già avvenuto, non si entra dopo;
5. k-i>12: scadenza. Alla barra12 il trigger è ancora ammissibile.

Se non invalidato e profondità<1/4 o manca una chiusura contraria: WAIT_REACTION. Se reazione compatibile ma manca ripresa: WAIT_RESUMPTION.
Trigger a t>t0:
- LONG: C_k>H_(k-1) e C_k>O_k;
- SHORT: C_k<L_(k-1) e C_k<O_k.
Tutte le condizioni sono valutate dopo la chiusura della barra k; contraddizioni hanno precedenza sul trigger.

Il trigger genera il piano:
- LONG S0=Rext-0,10*A0; T=P1.price.
- SHORT S0=Rext+0,10*A0; T=P1.price.
- E*=C_k*(1+d*s), s baseline della sezione9.
- rischio r*=d*(E*-S0)>0; spazio g*=d*(T-E*)>0; g*/r*>=1,5.
- S0,T ed E* devono essere positivi e finiti.
Se fallisce, ABSTAIN_REWARD_RISK e episodio consumato. Nessun inseguimento o secondo tentativo della stessa gamba.

Se passa: Expectation esplicita “tentativo di ritorno all'estremo P1 prima dell'invalidazione della reazione, entro24h dall'eventuale ingresso”; Call con verso, fatti/reazione, limiti, piano, validità e condizione di prezzo. Non è probabilità numerica. Richiesta d'ingresso creata a t, tentativo unico all'apertura1m t+60s.

## 6. Ingresso e astensione al momento dell'esecuzione

Non entrare alla chiusura che ha prodotto il segnale né all'apertura1m simultanea t. La richiesta attende60s. Non è un vero ordine inviato all'exchange.

A u=t+60s usare solo l'open negoziato1m di u come quotazione disponibile per il tentativo:
- E=O_u*(1+d*s).
- R0=d*(E-S0)>0 e G0=d*(T-E)>0 e G0/R0>=1,5.
La call indica già il vincolo: per LONG E<=(T+1,5*S0)/2,5 e S0<E<T; per SHORT E>=(T+1,5*S0)/2,5 e T<E<S0. È un ingresso condizionato alla quotazione modellata, non una fill garantita di un market order irrevocabile. Nessuna lettura di high/low del minuto per scegliere se entrare.

Se minuto mancante/invalido, vincolo fallito, confine valutazione imminente o posizione già presente: richiesta REJECTED/CANCELLED con motivo, nessuna fill/costo, episodio consumato. Non rimandare al prossimo prezzo favorevole.

R0 è rischio geometrico iniziale: non include costi, slippage d'uscita o gap e non è un tetto garantito alla perdita.

Al fill: q=N0/E BTC, **N0=1.000USDT di nozionale normalizzato fisso per operazione**. Quantità continua per confronto, niente reinvestimento, aumento, leva o margine modellati. Non è capitale dell'Owner, non certifica eseguibilità su tick/lot/minimi reali. Tutta la posizione q viene chiusa una volta sola. EntryRequest accettata non equivale a Fill.

## 7. Gestione dinamica e conclusione

S0 e T sono attivi nel modello dall'ingresso. Target T fisso: il test riguarda un ritorno al precedente estremo, non un target che si allontana. Nessun take-profit rialzato, uscita parziale o recupero perdite.

A ogni chiusura45m t con posizione ancora aperta:
1. Se struttura45m è diventata opposta al trade: richiesta EXIT_STRUCTURE a t+60s. Nessuna inversione automatica.
2. Altrimenti, per un nuovo pivot protettivo confermato ora (LOW per LONG, HIGH per SHORT), con **candidateOpen>=entryTime**: proposta Snew=pivot.price-d*0,10*A0. La candidata deve iniziare dopo l'ingresso per evitare un estremo formato prima del trade.
3. Accettare la proposta solo se d*(Snew-Scurrent)>0, d*(C_t-Snew)>0, d*(T-Snew)>0 e prezzo positivo. Se non è migliorativa/compatibile, scartare con motivo, non applicarla in una barra futura.
4. Snew efficace a t+60s. Fino ad allora resta S precedente. Per LONG lo stop non diminuisce mai, per SHORT non aumenta mai. A0 non cambia; un aumento di volatilità non allarga il rischio.
5. Non rimuovere stop o target per una fase MIXED, per una perdita recente o per ritardare l'uscita.

Uscite:
- STOP o TARGET secondo sezione8;
- EXIT_STRUCTURE modellata alla prima apertura prevista con ritardo60s;
- TIME_EXIT all'apertura esatta entryTime+24h (scadenza predefinita all'ingresso, non un nuovo segnale da ritardare);
- END_OF_SEGMENT nella prima apertura dell'ultimo minuto autorizzato della finestra valutata, come sezione10;
- DATA_GAP: percorso irrisolto, trattamento sezione11, non prezzo inventato.

Stop aggiornato conserva vecchia/nuova versione, decisione t, effective_at e motivo/pivot. Una call scaduta o un nuovo segnale opposto non crea una seconda posizione. Chiuso il trade, episodio consumato; nessun reingresso sulla stessa gamba. Non creare una nuova opportunità nella stessa chiusura45m che termina/annulla un episodio: riprendere da chiusura successiva e solo per nuova gamba resa disponibile allora.

## 8. Precedenze e minuti di esecuzione

Una barra1m rappresenta [u,u+60s); il suo open è riferimento a u. Posizioni e comandi sono processati cronologicamente. Le decisioni45m usano soltanto minuti terminati; l'osservatore non riceve esiti economici o funding futuro.

All'apertura u, su posizione preesistente:
1. addebitare/accreditare funding con timestamp esattamente u alla quantità detenuta prima di u;
2. gap oltre stop già attivo: STOP al riferimento O_u (anche se peggiore dello stop); altrimenti gap oltre target: TARGET al riferimento O_u;
3. se ancora aperta, eseguire uscita discrezionale/scadenza/fine segmento già dovuta a O_u;
4. se ancora aperta, attivare stop aggiornato in scadenza. Se O_u viola il nuovo stop, uscita al riferimento O_u; vecchio stop aveva precedenza;
5. se flat e nessuna uscita/richiesta confliggente, tentativo ingresso in scadenza con guard della sezione6.

Intraminuto:
- LONG stop se low<=S, target se high>=T; SHORT stop se high>=S, target se low<=T.
- Solo stop: riferimento S; solo target: riferimento T.
- Entrambi: **STOP_FIRST baseline**, flag BOTH_TOUCHED_SAME_MINUTE e valorizzazione alternativa TARGET_FIRST sullo stesso trade/istante come intervallo di sensibilità, non risultato prescelto.
- Tutte le uscite sono modellate taker con slippage avverso, anche il target. Non si presume un limit maker perfettamente eseguito.
- Fill intrabar identificata con intervallo temporale [u,u+60s), senza fingere secondo/tick del contatto; il modello contabile la conclude a u+60s. Funding con timestamp interno al minuto è processato prima di tale conclusione, con ambiguità dichiarata se pertinente.
- Entrata a open e uscita nello stesso minuto possibili; addebitare entrambe le fee.
- Eventi funding con timestamp non allineato ai minuti mantengono il timestamp originale, non arrotondato silenziosamente.

A chiusura u+60s: consolidare eventuale uscita intrabar, poi, se confine45m, pubblicare osservazioni e gestione/richieste per il futuro. Non aggiornare lo stop usando un pivot prima della sua available_at. Un trigger stop/target dentro la barra appena terminata precede qualsiasi nuova decisione costruita dalla sua chiusura.

## 9. Prezzi, fee, slippage e funding: convenzioni economiche

Fonti ufficiali consultate17ottobre:
- Fee: https://www.binance.com/en/support/faq/detail/360033544231
- Funding: https://www.binance.com/en/support/faq/detail/360033525031
- REST: https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data

Verificato documentalmente: fee sul nozionale eseguito, market taker; la FAQ propone esempi di fee e rimanda ai tariffari. Funding sul valore mark*quantità e tasso storico, con segno distinto LONG/SHORT; intervallo non garantito sempre8h. Non verificati: commissione personale/storica del conto Owner e slippage realmente eseguibile. Nessun account consultato.

**Decisioni autonome Director per questa versione**, non attivazione automatica di DESIGN-001:
- baseline f=0,0005 (5puntibase per lato), scelto come tariffa illustrativa taker senza sconti/BNB/VIP; **ASSUNZIONE DI STUDIO**, non certificazione delle tariffe2023–2025;
- s=0,0003 (3puntibase avversi per eseguito), haircut semplice senza order book, anch'esso assunzione;
- BUY fill=reference*(1+s); SELL fill=reference*(1-s);
- fee=f*q*prezzo_fill su ogni lato;
- stress f=0,001 e s=0,001, scenario unico di frizione più severa, non griglia da ottimizzare.

Stress: valorizzazione economica sugli **stessi trade, quantità, tempi, riferimenti e gestione baseline**, applicando f/s maggiori. Non riqualificare ingressi col nuovo s, non alterare R0 o stop/target e non selezionare le operazioni rimaste migliori. È repricing del ledger, non un secondo percorso strategico eseguibile; indicarlo. Alternative stop/target idem intervallo di prezzi sullo stesso ledger, non selezione di traiettoria favorevole.

Lordo modellato pricePnL=d*q*(X-E), già comprensivo dell'effetto slippage nei prezzi. Esporre separatamente pricePnL senza slippage sui reference e differenza avversa; non sottrarre lo slippage due volte. Netto=pricePnL-feeIngresso-feeUscita+sommaFunding.

**Funding prescelto e fisso perv1:** tassi storici dall'archivio Binance Vision fundingRate e mark dalla chiusura della barra mark1m immediatamente precedente il minuto che contiene il timestamp funding. È una **approssimazione mark1m dichiarata**, non mark esatto di addebito e non sostituzione con prezzo negoziato. Nessun tasso futuro è input della decisione.
- Per evento raw a tau, u=floor(tau/60s)*60s; M=close della mark1m [u-60s,u), completa. Se manca, il cashflow è MISSING, non zero. Il timestamp raw può avere millisecondi di scarto (osservato 2023-01-01T08:00:00.008Z).
- Cashflow=-d*q*M*fundingRate. Il tasso CSV è frazione decimale (0,0001=0,01%), non un valore da dividere nuovamente per100.
- Baseline detenzione: entryTime<tau<=exitAccountingTime. Funding esattamente all'entryTime è prima dell'ingresso; esattamente all'uscita è prima della chiusura.
- La documentazione segnala scarti nell'addebito e la risoluzione1m non risolve tutti i contatti: se ingresso o uscita sono entro60s da tau, oppure tau cade nel minuto di uscita intrabar, flag FUNDING_BOUNDARY_AMBIGUITY. Per quei cashflow mostrare intervallo includendo/escludendo il contributo, senza scegliere il lato favorevole. Non inventare timing al millisecondo.
- Nessun tasso mancante=0, nessun calendario8h generato per riempire buchi, nessuna mark inventata. Netto completo modellato solo se tutti i cashflow pertinenti sono valutabili; altrimenti lordo/fee/costi noti e netto MISSING. Riportare anche l'intervallo delle ambiguità separatamente.
- Non modella margine, liquidazioni, size impact, code ordini o disponibilità di un conto. Etichetta: “netto modellato con fee/slippage assunti e funding storico valorizzato con mark1m”.

## 10. Finestre e separazione delle fasi

Input trade: [2022-10-01,2026-01-01) UTC. Inizializzazione [2022-10-01,2023-01-01), non genera trade.
**DEV:** [2023-01-01,2025-01-01), unico percorso continuo2023–2024. Non resettare a ogni mese/anno.
**ADDITIONAL_2025:** [2025-01-01,2026-01-01), confronto aggiuntivo già esposto, eseguito solo dopo decisione Director sul congelamento post-diagnosi DEV. Mai chiamarlo validazione indipendente o holdout.

Ogni finestra valutata inizia FLAT senza episodio/ordine, ma con osservazioni inizializzate da tutto il prefisso disponibile. Nessun episodio nato prima dell'inizio viene emesso retroattivamente; si attendono nuove gambe confermate nella finestra.
All'ultima apertura1m u=end-60s: cancellare ingressi/aggiornamenti pendenti e chiudere eventuale posizione a O_u con costi. Stop/target in gap alla stessa apertura hanno precedenza come sopra. Nessun nuovo ingresso con execute_at>=u. Le chiusure forzate sono contate e spiegate. Non scaricare un minuto dopo end; nessuna posizione irrisolta per convenzione di fine campione.
Per chiarezza,2025 non continua una posizione2024: sono due finestre di valutazione separate; il cumulato2023–2024 è continuo, il totale di entrambe è solo somma normalizzata dichiarata. Il riferimento iniziale non è un conto con reinvestimento.

Prima di esiti DEV: commit del candidato/config, checksum/hash e test sintetici; nessuna ricerca automatica parametri. Dopo DEV: diagnosi e checkpoint Director. La disposizione Astra autorizza al più una revisione metodologica motivata in questa famiglia; la strategia non viene scelta da Claude.
Dopo eventualev2 o decisione di mantenerev1: congelare versione/i e confrontoDEV PRIMA di elaborare esiti2025. Nessuna iterazione su2025; bug documentati correggibili con patch e confronto d'impatto. Una diversa famiglia/nuovi segnali richiedono Astra. Non anticipare un backtest2025 “solo per vedere”.

## 11. Dati mancanti e risultati non completi

Riutilizzare le policy OBS-001 per barre/finestre/osservazioni; nessun riempimento prezzi. Quando FLAT, un gap annulla episodio/richieste, resetta segmenti e si attende disponibilità effettiva dei soli input necessari.
Minuto richiesto per entry assente: CANCELLED_NO_QUOTE, nessun fill.
Minuto negoziato assente mentre una posizione esiste, anche in latenza di un'uscita: stop/target potrebbero essere stati raggiunti. Segnare trade UNRESOLVED_DATA_GAP e interrompere l'esecuzione di QUELLA finestra valutata: le decisioni successive sono NOT_EVALUATED_AFTER_GAP, non finti trade o rientri flat. Nessuna liquidazione inventata al primo prezzo dopo il gap. Report parziale con numero/tempo interruzione e nessun netto completo della finestra. Altra finestra riparte separatamente come previsto, previa diagnosi.
Funding/mark mancanti non influenzano la scelta del candidato (non sono segnali): si può completare il percorso dei prezzi, ma cashflow e netto restano indisponibili per i trade/aggregati interessati. Non sommare solo i trade completi chiamando il risultato totale.
Conservare tutti i rifiuti e stati dei tempi non valutabili; dati assenti delle famiglie contestuali non diventano zero né bloccano indebitamente l'episodio.

## 12. Output, metriche, esempi e diagnosi

Ledger immutabile completo per versione/finestra: snapshot alla decisione, episodio/gamba, call e condizione, ordine modellato, ingresso/uscita (tempo o intervallo), quantità/N0, piano originario e successive protezioni, eventi concorrenti/ambigui, ragioni di astensione/uscita, prezzo reference/fill, fee, funding con origine/markproxy, lordo/netto/stress e missing flags.

Tabelle per anno e mese, anche vuoti, più DEVtotale e ADDITIONAL2025 distinto:
- popolazione barre/tempi validi, episodi riconosciuti, call, richieste rifiutate/annullate, trade, direzioni e motivi;
- PnL reference, slippage attribuito, fee e funding separati, netto modellato e stress; unità USDT per N0=1000 e puntibase=Nettopertrade/N0*10000. Cumulato = somma di questi valori, non rendimento composto del conto;
- media/mediana/P10/P25/P75/P90 dei risultati per trade, durata, rischio iniziale q*R0/N0 e rapporto netto/(q*R0); nessuna divisione per0;
- quota trade netti positivi dichiarata come descrizione secondaria, payoff medio e profit factor se denominatori presenti; niente soglia di successo o promozione fissata ex post;
- esposizione temporale e numero di operazioni per mese; sequenza massima di perdite;
- percorso PnL cumulato realizzato e a chiusure1m con non realizzato, fee/funding già applicati, senza stimare costi di uscita non avvenuti. Drawdown picco-minimo su queste chiusure, in USDT/N0 e bps, denominato risoluzione1m, non drawdown tick esatto. In minuto di uscita intrabar usare il risultato della fill e non extrema/close successivi per creare un'esposizione inesistente;
- concentrazione top5 trade per |netto| / somma|netto|; contributi positivi dei5migliori / sommaPnLpositivo e negativi dei5peggiori / somma|PnLnegativo|, null se denominatore0; distribuzione mensile/annuale e LONG/SHORT;
- conteggio stop/target/time/structure/end, aggiornamenti protezione, conflitti intrabar, funding ai confini e dati mancanti. Intervalli di sensibilità non sono nuove osservazioni indipendenti.
Assegnare le operazioni al mese/anno d'ingresso per distribuzioni per-trade; cashflow e curva seguono invece il loro timestamp effettivo. Riconciliare trade che attraversano fine mese/anno, non azzerare posizioni a quei confini. Riferimento inattività =0, senza sostenere rischio equivalente con buy-and-hold.

Regola esempi registrata prima degli esiti, per ciascuna finestra e ciascun verso:
- prima call cronologica e primo trade cronologico;
- primo trade chiuso con netto<0, primo con netto>0 (categorie a posteriori dichiarate);
- primo trade con aggiornamento della protezione;
- prima astensione per reazione invalidata, prima per rapporto spazio/rischio e prima per dato mancante, se esistono.
Tie: timestamp poi ID. Nessuna scelta del grafico più bello o più estremo. Categoria vuota dichiarata. I link aprono direttamente il momento pertinente, le informazioni allora disponibili e la sequenza successiva modellata; l'Owner non deve cercare date/pivot o rivedere migliaia di origini.

Diagnosi DEV deve separare: bug, decisione non fedele al disegno, scelta coerente ma poco utile, costo/assunzione sensibile, informazione insufficiente. Documentare dove il metodo fallisce e quanto dipende da pochi trade/mesi o dall'intrabar. Una revisione non è obbligatoria e non può essere una griglia di soglie. Nessuna pretesa di significatività o causalità; dati2023–2024 destinati alle iterazioni, non certificati mai visti.

## 13. Esempi sintetici discriminanti

- LONG: P0=100, P1=112, A0=2, durata10barre, strutturaUP. Reazione Rext=106, profondità0,5; barra di ripresa con C=108>Hprev107,5 e C>O, high<112. S0=105,8, T=112. E*=108*(1+0,0003)=108,0324: R0=2,2324, G0=3,9676, rapporto>1,5. Fill solo al futuro open previsto che rispetti il guard; non alla barra pivot o al close108.
- SHORT speculare: P0=112, P1=100, reazione106, S0=106,2, triggerC104<prevLow104,5 e C<O; T100, E*=103,9688. Non copiare BUY/SELL del LONG.
- Contabilità con fill già fissate (slippage non applicato di nuovo): E100, X102, q10, f0,0005, LONG, un funding positivo0,0001 con M101 → lordo20, fee1,01, funding-0,101, netto18,889. SHORT E100/X98,q10: lordo20, fee0,99, funding+0,101, netto19,111.
- Uno stop proposto ma non ancora efficace non sostituisce quello attivo nel minuto di latenza. Un gap oltre stop riempie a open avverso, non a stop ideale. Entrambi i livelli nello stesso minuto producono stop-first e flag, non il trade migliore.
Questi sono numeri di controllo sintetici, non livelli reali BTC o tariffe verificate.


## 14. Checkpoint DEV — Director, 17 ottobre 2026, prima degli esiti2025

Decisione registrata: **mantenere candidato1.0.0, nessuna revisione metodologica** in questa macrofase. Config canonica invariata SHA256 `aed2c4ef627617d73972778097bbab5fb702ab5064ce9e6eb68ded2170ce4edf`; osservatore OBS-001/v1 invariato. La perdita DEV riportata non giustifica una modifica unica sufficientemente motivata; nessuna ricerca di parametri o variante scelta sugli esiti.

**R1 accettato tecnicamente sulla base3ae7b7529f26f7aef94c9de207ce41df342590d1**, motore1.0.1/schema cand001.bundle/2. Review Director:36test Python CAND,14test UI Backtest/BacktestR1 e typecheck/build passati; lettura delle patch funding, HALT/aggregati/UI e prezzo. Il confronto reale offline di Claude dichiara decisioni,87richieste,78trade e numeri DEV invariati. Questo confronto e il riscontro separato dell'esecutore non sono un ricalcolo autonomo del Director dei75archivi o78trade reali; nessuna prova positiva Owner registrata. Incarico/consegna R1 conservati in current_task.md alla base3ae7b75.

Il checkpoint della sezione10 è ora soddisfatto: **procedere con ADDITIONAL_2025**, già autorizzato daAstra. Ammessa patch tecnica del supporto prima del primo esito2025:caricamento dell'intero prefisso dal2022-10-01, riuso dei file verificati, finestra2025 che riparte FLAT senza episodi ereditati, output e consultazione separati. Nessuna modifica del JSON candidato, delle regole o dei costi; versionare il motore senza creare una revisione metodologica. Pubblicare tale supporto prima degli esiti.

2025 è confronto aggiuntivo già esposto, non validazione indipendente; nessuna iterazione metodologica dopo la sua lettura. Bug documentati correggibili con confronto d'impatto. Nessun dato2026 o tail. Report conserva DEV negativo e2025 distinto; la chiusura non richiede esito favorevole. Dettagli esecutivi nel task corrente.
