# Owner Backtest A — review indipendente del dossier e proposta al Director

Data: 5 ottobre 2026. Baseline esaminata: `87948057d25a045f93249f59b2b79c0f2bc15041`, repository `C-Gian/algorithmic-trader`.

**Stato: proposta strategica, non disposizione e non autorizzazione a modificare il progetto.** Nessun backtest, replay, acquisizione di dati di mercato o implementazione. Clean-room preservata. Capitale, quantità, leva ed esecuzione restano decisioni umane.

## 1. Decisione raccomandata

La diagnosi centrale regge: **le 32 geometrie respinte sono incompatibili già con la conferma minima richiesta**, non soltanto con il prezzo che ha infine superato quella soglia. Quattordici non ammettono neppure un prezzo economicamente valido fra stop e target; le altre diciotto hanno spazio teorico soltanto dal lato del prezzo che la conferma ha già oltrepassato. Le sei esclusioni dentro una zona restano una classe distinta.

Questo chiude l'incertezza principale della review precedente. Non dimostra che anticipare l'ingresso, ignorare i pivot o attendere più a lungo produrrebbe un metodo utile. Non dimostra neppure l'impossibilità universale di MP-001: riguarda gli oggetti effettivamente prodotti in questa run.

**Non richiedo un altro giro di estrazione.** Propongo un solo prossimo passo: una revisione metodologica documentale circoscritta, per approvazione del Director, che separi scenario, conferma e ingresso e specifichi, inizialmente per A, un ingresso su ritorno successivo alla conferma. Conservare costi, rapporto minimo, destinazioni conservative e invalidazione strutturale. B/C restano operativamente invariati; la semantica MarketView viene disaccoppiata dall'esito del gate economico per tutte le famiglie. Non attivare ancora implementazione o run.

Non propongo una ricerca fra molte varianti di trigger. La proposta sotto è una singola ipotesi da chiudere semanticamente e poi poter respingere su altri periodi di sviluppo.

## 2. Che cosa ho verificato e che cosa non è una prova indipendente

Ho confrontato FOUNDATION, STATE, AGENTS e task correnti, MP-001 v0.2 e registro, la precedente review Astra e la disposizione del Director, i tre file richiesti del dossier e le funzioni pertinenti del codice, inclusi selezione dei target e prezzi, geometria e caricamento dei parametri.

Ho inoltre eseguito esclusivamente controlli aritmetici statici sui numeri già presenti in `dossier.json`, con frazioni razionali e formule separate dal codice del progetto: nessun import del motore, nessuna lettura di nuovi percorsi storici, nessuna simulazione di decisioni o risultati.

| Controllo indipendente sui dati forniti | Risultato |
|---|---|
| G, Q e margine dalle 32 coppie T/V e dal prezzo | Coerenti; scarti di precisione inferiori a 5×10⁻⁴⁹ bps per G/Q e 9×10⁻²⁷ bps per il margine |
| Arrotondamento di V dal candidato e limite economico inward al tick 0,1 | Coerenti nei 32 casi |
| Classificazione algebrica | 14 senza prezzo ammissibile, 18 incompatibili con conferma, zero overshoot |
| Selezione target dal set di zone fornito, al prezzo effettivo e alla conferma minima | 64 controlli coerenti; un target cambia fra i due prezzi |
| Prezzo al centro e near/far edge delle zone; creazione non successiva ai due cutoff dichiarati | Nessuna incoerenza rilevata nei set forniti |
| Zone contenenti i sei prezzi bloccati | Cardinalità 2, 1, 4, 1, 1, 2: tre attribuzioni uniche, tre ambigue |
| Hash canonico del registro letto | Coincide con `identity.register_sha256`: `e2e2dd8e…d60bae` |

Questi controlli verificano la coerenza interna e l'algebra dei record consegnati. **Non certificano indipendentemente la completezza del journal o del cache esportato.** I 6.972 record originali e il cache locale non sono stati riestratti da me. Il loro hash-chain e i 896 pivot riprodotti sono evidenza riportata dall'executor. Lo script importa inoltre `geometry`, `params`, funzioni di precisione e quantili dal prodotto: rigenerare una risposta con gli stessi helper non esclude un errore condiviso. Per questo ho rifatto separatamente i calcoli decisivi.

La differenza fra hash del file del registro (`f7fce…`) e hash canonico dell'identità non è di per sé una discrepanza: sono rappresentazioni diverse. Il controllo canonico chiude questo dubbio per i parametri esaminati, non certifica l'intera immagine runtime.

## 3. Audit causale e limiti dello script

### Cutoff: sostanzialmente adeguati a questa run, non certificazione universale

`Index` ricostruisce le ultime versioni dei landmark anteriori alla sequenza limite; non legge semplicemente lo stato finale. Le zone proprie provengono da owner già nati e non terminati al cutoff. I due set arm/trigger sono distinti e la ricostruzione usa barre complete con fine non successiva al tempo considerato. Questo è il disegno corretto per evitare di portare un pivot pubblicato dopo l'arm nel passato.

Due limiti vanno esplicitati:

- Il cache viene indicizzato per event time e l'aggregazione ricostruisce il known-at dalla fine della barra; non conserva autonomamente tutta la semantica di ammissione, late exclusion e cursor dei costituenti. Quindici elementi non costituiscono, in generale, una dimostrazione di quindici slot contigui ammessi. Qui il profilo dichiarato è `modeled-complete-prefix`, con ritardo bar zero: rende ragionevole il cutoff usato. Non trasferire questa estrazione al live o a profili con latenze senza modificarne il ragionamento.
- `dispatch_cutoff_seq` è ricavato dalla prima actionability dello stesso clock time. È coerente con un unico dispatch del prefix modellato e impedisce che le terminazioni prodotte durante la selezione cancellino retroattivamente le zone proprie. Un timestamp da solo non identifica però universalmente un dispatch. Due batch ammessi allo stesso clock sarebbero un controesempio.

**Correzione minima del giudizio:** “nessuna contaminazione futura individuata nei cutoff di questa run modellata”, non “causalità dimostrata per ogni modalità”. Non serve acquisire altri dati per scegliere la direzione metodologica qui proposta.

### Zone: ricostruzione utile, attribuzione non sempre recuperabile

La ricostruzione separa landmark, impulso B e box, usa la creazione invece dell'extremum time e applica la rottura per close oltre far edge. Il confronto indipendente conferma la selezione numerica dai set forniti; non prova che non manchi un oggetto nell'esportazione.

La frase di SUMMARY secondo cui target e zona limitante coincidono “38/38” è troppo forte. Per tre rifiuti inside-zone non è recuperabile quale oggetto il runtime abbia restituito. È verificato il **motivo di blocco**, non l'identità originaria della zona. Esempio: il primo rifiuto è dentro sia il pivot 15m sia la zona B propria. Nessuna delle due va arbitrariamente eletta causa unica.

La correzione minima è distinguere 32 target ricostruiti, sei blocchi coerenti con appartenenza, tre sole attribuzioni inside-zone univoche. F1 della review precedente resta un difetto di audit del prodotto, non una prova di call soppresse erroneamente.

### Arrotondamenti: non spiegano il risultato

Con direzione d=+1 LONG e d=−1 SHORT, il target si arrotonda verso il prezzo e lo stop lontano dal prezzo. Il floor nello spazio trasformato riproduce correttamente il ceil reale per SHORT. I bound economici sono arrotondati verso l'interno; un prezzo uguale a V non è ammissibile perché Q deve essere positivo.

T/V vengono anche invertiti da p/G/Q con quantizzazione al tick: sarebbe fragile usando i valori del riepilogo arrotondati a due decimali. Nel dossier ci sono invece sufficienti cifre; il target selezionato dalle zone e lo stop del candidato costituiscono controlli ulteriori. Non vedo un errore di tick capace di trasformare i rifiuti osservati in pass.

Lo script non arresta necessariamente tutta l'elaborazione per ogni possibile mismatch di provenienza e carica i parametri dal package corrente. Sono limiti della sua riutilizzabilità come validatore, non errori osservati che ribaltino questo dossier. Non propongo di trasformare un'estrazione una tantum in una nuova piattaforma di audit.

## 4. Incompatibilità, overshoot e dominio della dimostrazione

Siano c il costo round-trip nominale in bps e r il rapporto netto minimo. Il gate richiede:

`G − c ≥ r(Q + c)`, con `Q > 0` e `G > c`.

Per LONG il prezzo massimo è `(T+rV)/[(1+r)(1+c/10000)]`; per SHORT il minimo è `(T+rV)/[(1+r)(1−c/10000)]`. Con c=14 e r=1,2: `G ≥ 1,2Q + 30,8`.

| Famiglia | Nessun prezzo fra V/T | Conferma minima incompatibile | Inside-zone |
|---|---:|---:|---:|
| A | 10 | 16 | 6 |
| B | 1 | 0 | 0 |
| C | 3 | 2 | 0 |

Tre precisazioni impediscono di sovrainterpretare la tabella.

**Primo:** il target è funzione anche del prezzo. `feasibility()` tiene fisso quello scelto al prezzo effettivo; separatamente lo script ricalcola quello alla soglia minima. Per A del 30 settembre 19:45 il target a conferma minima è 114488,3 invece di 114766,4: è più vicino e non salva il caso. La classificazione resiste, ma il calcolo a target fisso non sarebbe in generale un teorema su tutti i prezzi possibili o su futuri target. “Nessun prezzo” significa con quella coppia T/V e quei costi, non “nessun trade nel mercato”.

**Secondo:** `feasibility()` non interseca la regione con la fascia strutturale. Non altera i 32 verdetti negativi: restringere un insieme già incompatibile con la conferma non lo rende compatibile. Però “18 regioni economiche non vuote” non equivale a 18 ingressi strutturalmente utilizzabili. Solo **due** righe hanno `admissible_bounds` non nulli entro la fascia registrata al trigger. Esempio A LONG dell'8 settembre: fascia 112320,9–112444,7, parte economicamente ammissibile 112320,9–112343,5, conferma minima 112374,0. Un nuovo ingresso su ritorno richiede una nuova semantica causale; non era una call disponibile secondo v0.2.

**Terzo:** zero overshoot esclude l'overshoot come spiegazione sufficiente di questi 32 rifiuti. Non assolve il costo della conferma: recuperare fino all'high dell'intera barra di reazione può avere già consumato il percorso. Né esclude effetti di latenza o riempimento in un metodo futuro.

Non è giustificato concludere che tutti i pivot siano troppo severi. In A, nove target sono la near edge della B propria, quindici un altro landmark prima di B e due oltre B. Lo stesso obiettivo della tesi è talvolta troppo vicino. Il caso B, con Q circa 1,2 bps e span T−V circa 18,8 bps, confuta “basta stringere lo stop”. B ha un solo trigger: non basta per ridisegnare tutta la famiglia.

## 5. Direzione metodologica circoscritta: conferma separata dal prezzo d'ingresso

La scelta che raccomando di specificare è **conferma della continuazione, poi ingresso soltanto a un prezzo ancora valido, eventualmente su un successivo ritorno nella reazione**. Non una previsione retroattiva al minimo e non un abbassamento del requisito di conferma.

Il primo perimetro operativo è A, mantenendo la lettura integrata e B/C esistenti. A dispone del campione diagnostico maggiore e di un conflitto esplicito fra recupero dell'anchor e spazio residuo. Cambiare simultaneamente tutte le famiglie, i pivot e la scala impedirebbe di capire quale ipotesi stiamo verificando.

### Specifica proposta da chiudere nella revisione, non da implementare ora

1. **Struttura e scenario.** Alla reazione riconosciuta causalmente associare owner, A/B/R, anchor, invalidazione, destinazione e scadenza. Distinguere il target economico conservativo dalla destinazione narrativa B, mostrando eventuale ostacolo intermedio. Non basta chiamare un pivot “intermedio” per poterlo ignorare.
2. **Conferma.** Conservare inizialmente la conferma v0.2 oltre l'anchor su minuto successivo ammissibile. Essa conferma un evento della struttura; non obbliga ad acquistare proprio quel close. Se il prezzo corrente passa tutti i gate, l'ingresso immediato resta possibile.
3. **Ritorno successivo.** Se l'unico ostacolo è il prezzo non economico e il target non è già stato raggiunto, consentire uno stato di attesa prima dell'ingresso, senza emettere una call “entra ora”. La regione candidata deve essere strutturale: per LONG il tratto della reazione fra R e K dell'anchor, riflesso per SHORT, intersecato con prezzi strettamente validi rispetto a V, target, costi e zone. Non un allargamento arbitrario della fascia centrata sul close di trigger. R è un livello già noto: nessun fill al suo precedente estremo.
4. **Nuova osservazione utilizzabile.** L'ingresso può essere indicato soltanto su un successivo campione causale effettivamente nella regione, con tutte le condizioni ancora valide. La conferma è una condizione storica ancora in vigore, non il vincolo che ogni prezzo futuro debba restare oltre K: proprio questa è la nuova ipotesi economica. Una candela di ingresso che tocca l'invalidazione resta ambigua/non utilizzabile secondo le garanzie correnti.
5. **Target e rischio.** Congelare il target conservativo alla conferma per questo tentativo; un nuovo ostacolo può restringere o bloccare, mai allontanarlo per salvare il rapporto. Conservare V strutturale e costo 14/r1,2, senza stringere lo stop su richiesta del gate. Se la regione è vuota, questo tentativo non è economicamente adatto: nessun ritorno lo “ripara”.
6. **Ownership e durata.** Un solo tentativo d'ingresso per conferma, nessuna serie illimitata di retry. Attesa limitata dalla scadenza originale del setup, senza proroga al ritorno. Invalidation, contesto vietato, gap, scadenza o obiettivo già raggiunto chiudono l'attesa. Dopo ingresso conservare le regole esplicite di reassessment/hard horizon; nessuna durata estesa per recuperare spazio.
7. **Call persistente.** L'Owner vede prima “tesi confermata, attendo prezzo utilizzabile”, poi LONG/SHORT attiva finché la regione e i gate consentono ancora un nuovo ingresso. “Ingresso chiuso” deve restare distinto da “tesi invalidata” e dall'eventuale guidance per chi fosse già entrato. Non riaprire automaticamente un secondo trade dopo la chiusura del tentativo.

Questa proposta **non salva i 14 casi globalmente vuoti**, non garantisce che i diciotto restanti abbiano un ritorno valido e non promette chiamate in settembre. Nei sei inside-zone una destinazione già raggiunta non diventa un nuovo obiettivo: si chiude l'opportunità, pur potendo continuare la lettura del mercato.

Il rischio specifico è la selezione avversa: il ritorno a un prezzo migliore può essere il primo segnale che la continuazione sta fallendo. Va verificato, non occultato chiamandolo semplicemente “miglior entry”. Un'altra possibilità è che i ritorni siano troppo rari o rapidi per l'Owner: in quel caso la direzione proposta fallisce come prodotto anche se produce alcune call.

### Alternative considerate

| Alternativa | Giudizio |
|---|---|
| Anticipare la conferma con un nuovo pattern 1m | Plausibile, ma introduce una nuova tesi di microstruttura e maggiore esposizione a falsi recuperi. Il dossier non identifica quale pattern; non è la prima variante raccomandata. |
| Target più lontano / ignorare pivot | Richiederebbe una regola ex ante di significatività e accettazione degli ostacoli. Non giustificato dal solo fallimento del rapporto. |
| Spostare il metodo su strutture più ampie | Alternativa seria se il dominio locale resta sistematicamente incompatibile con costi e tempi umani. È un cambio di dominio da motivare, non la prima correzione automatica. |
| Ridurre costi, r o buffer dello stop | Nessuna evidenza nuova lo giustifica. Vietato usarli come manopole per ottenere chiamate. |
| Correggere solo il bug di attribuzione | Necessario per audit futuro, insufficiente per utilità economica e MarketView. |

## 6. MarketView: correggere la dipendenza, senza inventare frecce

33.001 minuti su 43.200 sono NO_SUPPORTED_PLAN, circa il 76,4%; 18.387 di questi hanno contesto osservato UP/DOWN. WATCH è presente soltanto in 1.725 minuti del totale NO_SUPPORTED_PLAN. Questi numeri non misurano errore predittivo e non autorizzano a copiare la direzione passata nella previsione.

La tensione di prodotto è però dimostrata dalla regola: una geometria respinta termina il candidato e può cancellare anche lo scenario. Un cambio di costo può quindi modificare indirettamente ciò che il sistema sostiene sul mercato. **La lettura va mantenuta da evidenza strutturale, non dal fatto di poter entrare.**

La revisione deve rendere distinti:

- osservazione: contesto, fase, posizione rispetto ai livelli e limiti delle fonti;
- scenario condizionale: antecedente, destinazione, evidenza a favore/contraria, invalidazione e orizzonte;
- ingresso: non pronto, attesa prezzo, utilizzabile, chiuso;
- guidance già emessa e sua gestione.

Uno scenario strutturalmente supportato può persistere dopo un rifiuto economico fino al proprio evento terminale. Un WATCH non è automaticamente una previsione UP/DOWN: può esporre “se si conferma il recupero, ritorno verso B; altrimenti scenario non attivato”. Dove manca una tesi sostenibile, UNCERTAIN resta corretto, con ragione concreta. Serve anche lo stato “nessuna struttura qualificata”, senza fingere che sia indisponibilità dei dati.

Il nuovo principio deve valere anche per B/C, senza cambiarne ora le entry. Il test semantico è netto: a parità di evidenza strutturale, cambiare soltanto un costo può cambiare actionability, non riscrivere lo scenario. La sua valutazione a orizzonte fisso resta separata dal rendimento dei trade ipotetici.

Non attribuisco tutta la scarsa copertura al latch A. Nei 45 spent ci sono 11 barre con entrambe le condizioni; OHLC non ne rivela l'ordine. La distanza alla nascita successiva non misura il tempo perso *a causa* del latch, perché non abbiamo Q_A a ogni close. Il dato mancante sarebbe precisamente quella sequenza con transizioni del latch; **non è decisivo per la proposta corrente e non ne richiedo l'estrazione**. Conservare per ora la segmentazione, riportandone il limite; la persistenza dello scenario non autorizza nuovi tentativi sullo stesso owner.

## 7. Criteri falsificabili per la verifica successiva

Il prossimo deliverable del Director è una sola proposta versionata con transizioni, regioni e fixture sintetiche, distinguendo ciò che cambia da v0.2. Il dettaglio numerico non deve essere inventato dall'executor. Questa review non attiva quel lavoro nel repository.

Dopo eventuale approvazione e implementazione separatamente autorizzata, la verifica economica dovrà usare **altri periodi di sviluppo**, non selezionare una variante sulle call di settembre. Ottobre–dicembre 2025 sono nel development dichiarato: verificarne prima la contaminazione e fissare l'ordine dei periodi prima di leggere risultati. Settembre resta evidenza diagnostica conosciuta e possibile regressione tecnica, non criterio di scelta della variante. Nessun accesso anticipato ai periodi protetti.

Registrare prima della verifica queste condizioni:

1. **Causalità:** nessun ingresso retrodatato alla reazione o alla conferma; aggiungere futuro non cambia output precedenti. Target e zone appartengono al cutoff, LONG/SHORT e tick sono simmetrici. Una violazione respinge l'implementazione indipendentemente dai risultati.
2. **Coerenza:** ogni call ha intersezione strutturale/economica non vuota, invalidazione indipendente dal rapporto, destinazione non spostata per passare, finestra e scadenza esplicite. I casi senza spazio restano esclusi.
3. **Meccanismo:** contare per owner le conferme con regione strutturale valida, quelle con ritorno osservato prima di invalidazione/target/deadline, e quelle realmente ancora utilizzabili al ritardo umano dichiarato. Una regione algebrica senza ritorno non è un'opportunità e non entra nel win rate.
4. **Utilità Owner:** mantenere il ritardo principale già dichiarato di 60 secondi e le sensibilità 0/120, senza scegliere a posteriori la più favorevole. Finestre solo istantanee o sistematicamente scadute prima dell'entry rendono il risultato inutilizzabile per il prodotto.
5. **Qualità economica:** valutare l'intero percorso ipotetico dopo l'emissione, costi base/stress, ambiguità e non-fill; riportare numerosità per strutture indipendenti, distribuzione degli esiti e perdite, non solo win rate. Più call non è accettazione.
6. **MarketView:** confrontare copertura di osservazione/scenari/aspettativa e ragioni di UNCERTAIN, indipendentemente dalla copertura di entry. Le previsioni condizionali si valutano con i loro antecedenti; una nuova etichetta non vale come aumento di accuratezza.
7. **Arresto:** se i periodi di sviluppo preregistrati restano privi di ingressi utilizzabili, o la maggioranza degli owner diagnosticati non dispone mai di un corridoio coerente, non concludere “aspettare altri segnali”. Respingere questa ipotesi di ingresso e decidere esplicitamente se il dominio strutturale locale vada sostituito. Non avviare una sequenza di riduzioni di soglie. Una base di casi troppo esigua resta non validata, non PASS.

Non impongo un numero di call o un win rate inventato da questo dossier. Il Director deve fissare prima dei risultati l'eventuale soglia di utilità di prodotto; i fallimenti logici e l'assenza persistente di ingressi utilizzabili sono già criteri negativi chiari.

## 8. Disposizione proposta in una frase

**Accettare il dossier come evidenza sufficiente dell'incompatibilità osservata, con i limiti probatori sopra; chiudere l'estrazione; sottoporre a decisione una sola revisione che separi scenario, conferma e ingresso e provi in A il ritorno post-conferma entro struttura/costi invariati, preservando B/C e separando MarketView da actionability; nessuna modifica o nuova run è autorizzata da questa review.**

Riferimenti al commit indicato: `delivery/evidence/WP-009-OWNER-BACKTEST-A-DOSSIER/{SUMMARY.md,dossier.json,extract_dossier.py}`; `delivery/WP-009-OWNER-BACKTEST-A-ASTRA-REVIEW.md`; `delivery/WP-009-OWNER-BACKTEST-A-DIRECTOR-DISPOSITION.md`; `delivery/MP-001-INTEGRATED-METHOD-PROPOSAL.md` §§3,5–9; `delivery/MP-001-PARAMETERS.json`; `src/algotrader/adviser/{core.py,geometry.py,params.py}`. Le categorie professionali sono il contesto del metodo; né le fonti né questo dossier dimostrano un edge BTC della nuova ipotesi.
