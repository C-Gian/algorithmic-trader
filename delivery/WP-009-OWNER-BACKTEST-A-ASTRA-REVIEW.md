# Owner Backtest A — Review mirata Astra

Data: 5 ottobre 2026  
Destinatario: Project & Research Director  
Base: `26d521e9f2da0a53e970e6ab860810ca71887dff`  
Run: `eval-20261005T120047-e6cc50` / `obs-20261005T120047-bc6947`  
Metodo: `btc.context-action.v0.2`, `mp001.rules.v0.2`  
Stato: **ADVISORY — nessuna modifica o nuova esecuzione autorizzata**

## 1. Verdetto e unico prossimo passo

**La diagnosi del Director identifica correttamente il punto finale di blocco, ma non identifica ancora la causa progettuale da correggere.** È confermata l'incompatibilità, nei trigger osservati, fra geometria disponibile e gate economico dichiarato. Non è ancora dimostrato che il problema principale sia la conferma tardiva, un eccesso di piccoli pivot, il target dell'impulso, oppure un errore nella selezione degli oggetti.

La spiegazione “target locali + recupero prima dell'ingresso” è plausibile soprattutto per A, ma non va promossa automaticamente a revisione. B ha un solo trigger e rischio molto piccolo; C ha soltanto cinque trigger e una destinazione diversa. Spiegare tutte le famiglie con l'anchor-high di A sarebbe scorretto.

**Unico prossimo passo raccomandato: un dossier causale, in sola lettura, sui record già committati della run.** Deve unire i 38 trigger alle loro geometrie e zone, e includere una sintesi circoscritta dell'attrito precedente all'arm. Il perimetro e il criterio di arresto sono in §6. Nessun nuovo replay, backtest, Deep, acquisizione o modifica di parametri. Non raccomando ancora una versione comportamentale v0.3: mancano proprio i dati che distinguerebbero revisioni opposte.

La correzione del difetto diagnostico individuato sotto non è un secondo pacchetto da attivare adesso: il dossier deve prima rendere esplicita la perdita, recuperando quanto recuperabile dagli altri record senza riscrivere il report originale.

## 2. Evidenza verificata e cosa prova

Ho letto Foundation, STATE/task, AGENTS, MP-001 v0.2 e registro, disposizione accettata, brief/diagnosi e JSON originale. Ho ispezionato le parti pertinenti di `adviser/core.py`, `geometry.py`, `report.py`. I tre file risultano identici fra il commit della review e `6f95273b54674081fe6b3896a84d62a015384fe5`, codice dichiarato dalla run. La review del codice è statica: nessun motore o test economico è stato eseguito.

| Fatto | Interpretazione consentita |
|---|---|
| 147.975 eventi, 135,2 s, runtime PASS 20/20 | Il workflow ha completato la run e riconciliato i suoi artefatti. Non certifica correttezza economica né ogni predicato della strategia. |
| 43.200 minuti assessabili, zero unavailable nel mese | Warmup/readiness del nucleo non spiegano l'assenza di call. Non significa disponibilità completa di news, funding o quote. |
| A: 85 nascite, 38 arm, 32 trigger respinti | Dei trigger A, 26 hanno G/Q; gli altri sei sono AT_OPPOSING_AREA. Quest'attribuzione deriva dal funnel per famiglia, non dall'istogramma dei landmark. |
| B: 12 nascite, 3 arm, 1 trigger; C: 12 nascite, 6 arm, 5 trigger | Le due famiglie complementari hanno già forte attrito prima del gate geometrico. Non sono economicamente valutate in modo rappresentativo. |
| 18 NO_ROOM_AFTER_COSTS, 14 REWARD_RISK_BELOW_MINIMUM, 6 AT_OPPOSING_AREA | Tutti i 38 trigger terminano prima di una call. I primi due motivi sono rami ordinati dello stesso controllo, non due cause indipendenti. |
| Nessuno scarto per slot, priority o conflitto; nessun veto comune registrato nel periodo | Queste restrizioni non sono una spiegazione del risultato osservato. I 15 minuti di priority competition descrivono coesistenza, non scarti effettivi. |
| 45 A spesi per nuovo high prima della reazione | Attrito reale della regola d'episodio: 45/85 nascite A, circa 52,9%. Non equivale a 45 occasioni redditizie perse. |
| 1.113 minuti con scenario armed; 33.001 NO_SUPPORTED_PLAN; 9.086 BALANCED_RANGE | Scenario armed nel 2,58% del mese; nessun piano prospettico supportato nel 76,39%. La seconda lacuna non viene curata automaticamente correggendo il target. |
| 18 campioni orari direzionali su 720; 702 astensioni | Copertura direzionale 2,5%. Gli 8/18 e 9/18 matching-sign a 1h/4h non stimano una qualità generale e non sono confrontabili direttamente con persistence su 720. |
| Una call nel warmup, esclusa da settembre | Il percorso di emissione è raggiungibile almeno in quella run. Non prova utilità nel mese e non va recuperata come risultato favorevole. |

Zero call è un insuccesso di utilità per questo mese di sviluppo, non evidenza di break-even o di prudenza eccellente. Con zero ingressi non esiste una stima di profitto, win rate o bontà delle uscite. Non servono altri mesi per riconoscere il problema; servono dati congiunti per scegliere la correzione.

## 3. Findings: implementazione, metodo e ipotesi

### F1 — Difetto diagnostico confermato: la zona bloccante viene persa

**Codice:** `core._resolve_target`, `_select_and_issue`, `_actionability`; `report.build`.

Quando il trigger è dentro una zona opposta, `_resolve_target` restituisce il suo `info` insieme ad AT_OPPOSING_AREA. `_select_and_issue` aggiunge il blocker ma lascia `geom=None`; `_actionability` recupera `limiting_landmark` soltanto da `geom`. Il riferimento si perde. `report.build` conta poi il valore nullo come NONE.

**Conseguenza:** i sette NONE dell'istogramma non significano sette casi senza ostacolo. I sei AT_OPPOSING_AREA sono necessariamente fra questi null; la distribuzione dei tipi di ostacolo su tutti i 38 casi non è completa. Per il restante NONE non si può scegliere fra midpoint/projection o altro senza il join.

**Controesempio minimo:** trigger 100 dentro zona [99,101]. Il motore respinge proprio per quella zona ma il report la classifica NONE. La call resta correttamente respinta secondo il metodo: il bug riguarda attribuzione/audit, non dimostra emissioni mancate per un errore di trading.

**Correzione minima futura, soggetta al Director:** preservare separatamente il riferimento alla zona bloccante anche senza geometria. Per questa run non inventarlo né modificare l'originale: ricostruire l'insieme delle zone al cutoff dai loro record, distinguendo zona specifica recuperabile da attribuzione non recuperabile. Se più zone contengono il prezzo, riportarle tutte; non supporre una scelta univoca senza l'ordine originario.

### F2 — Nessun bug aritmetico dimostrato nel gate centrale

`geometry.predicate` implementa G>K, Q>0 e (G−K)/(Q+K)≥1,2; il margine è G−1,2Q−2,2K. La formula e i rami LONG/SHORT sono compatibili con MP-001. I round-trip 14 bps sono l'assunzione nominale prevista; la piccola differenza dalla contabilità esatta per-leg è già dichiarata dal metodo e non spiega, da sola, i margini negativi riportati.

Gli errori possibili nella scelta del riferimento, nel cutoff o nel target non vengono esclusi dal runtime PASS. Però **non ho trovato, nelle funzioni centrali lette, una prova di un bug numerico che spieghi le zero call**. Non va dichiarato “il codice è corretto in tutto”, né va assegnato un bugfix economico ipotetico.

I 18 e 14 scarti non sono due popolazioni causalmente indipendenti: il codice restituisce prima NO_ROOM se G≤K, e soltanto dopo verifica il rapporto. Ridurre uno scarto a zero può semplicemente farlo ricomparire nel ramo successivo.

### F3 — Conflitto di scala osservato; attribuzione causale ancora aperta

Con K=14 e r=1,2:

`G ≥ 1,2 Q + 30,8 bps`.

Nei 32 record con geometria, **27 hanno G<30,8 bps**, conteggio sulle righe già esportate, arrotondate a 0,01 bps e non a ridosso della soglia. Quindi, a quel prezzo e con quel target, nemmeno portare Q arbitrariamente vicino a zero basterebbe. Non è una raccomandazione di stringere lo stop: mostra che “rischio troppo largo” non può essere la spiegazione unica. Negli altri cinque casi il margine effettivo è comunque negativo.

B è il controesempio più netto a una spiegazione solo basata sullo stop: G≈17,62 e Q≈1,22 bps, ma il gate fallisce. Per C il migliore margine resta circa −32,24 bps. Per A il migliore è circa −7,69 bps. Non combino mediane di casi differenti e non deduco una soglia vincente.

Questo dimostra una incompatibilità dei **casi prodotti** con il filtro dichiarato; non un'impossibilità matematica universale del modello. Né dimostra che i costi siano empiricamente corretti: sono ancora scenari, e cambiarli per emettere call altererebbe il metodo.

### F4 — L'erosione di A non prova un ingresso precedente praticabile

Il Director riconosce già il limite, ma deve mantenerlo nella decisione. `report.staged_room` misura la distanza dal prezzo dell'estremo di reazione al target ricostruito al trigger. Non misura uno stato decisionale noto al tempo della reazione, una quote disponibile, una conferma o il rapporto netto con il rischio di allora.

**Controesempio:** low di reazione 100, high della stessa barra 105, target 106. Avere sei punti di spazio dal low non permette di entrare a 100 dopo aver saputo che quella barra è la reazione completata. Una successiva conferma oltre 105 può lasciare un solo punto. Sono prezzi di natura diversa, non due ingressi equivalenti fra cui scegliere ex post.

Inoltre **24/26 target prima di B non dimostrano 24 cap dovuti a piccoli pivot**. Lo stesso target dell'impulso è la near edge B−z per LONG: sta prima di B per costruzione anche quando nessun pivot intermedio lo limita. Per SHORT vale il riflesso. Il conteggio non separa haircut della zona, altri landmark e perdita dovuta al recupero.

**Correzione diagnostica minima:** distinguere distanza totale fino al target economico, sconto dovuto alla zona, eventuale cap intermedio e distanza consumata fra soglia minima di conferma e close effettivo. Il tempo arm→trigger e la disponibilità causale dei target devono essere nello stesso record.

### F5 — Copertura della MarketView: limite dichiarato, ma tensione reale col prodotto

In `compute_view`, senza call la direzione attesa UP/DOWN appare praticamente solo con un candidato ARMED. Il contesto 1h UP/DOWN senza arm ricade in UNCERTAIN/NO_SUPPORTED_PLAN. Quando un trigger fallisce per geometria, l'episodio termina e può sparire anche lo scenario prospettico.

Questo corrisponde alla tabella MP-001 v0.2: **non è un bug di implementazione**. Ma il progetto voleva un'opinione continua separata dall'operabilità. Qui la separazione dei dati è presente, mentre la persistenza dell'aspettativa resta fortemente legata alla maturità di un setup e al suo esito economico.

**Controesempio:** due stati hanno struttura e direzione identiche; cambia soltanto un'assunzione di costo che fa respingere il trigger. È ragionevole cambiare actionability; non è automaticamente giustificato eliminare la tesi direzionale. D'altro canto mostrare UP copiando il contesto passato non costituirebbe una soluzione scientifica.

La scelta successiva deve distinguere “non ho un trade”, “non ho ancora una conferma” e “non sostengo una previsione”. Non raccomando ora nuove frecce forzate o un motore separato: il dossier deve prima mostrare durata di WATCH, ARMED e dei contesti/phase dentro NO_SUPPORTED_PLAN. La bassa copertura è un problema autonomo da portare alla disposizione, non una ragione per ignorare il gate economico.

### F6 — Spesa pre-reazione e reset: attrito del metodo, non 45 bug dimostrati

`_a_close` controlla un high oltre B+z mentre l'episodio è WATCH prima di completare la valutazione della reazione; `_a_births` richiede poi il reset dichiarato terminal→false→true. Non conserva semplicemente un'idea in attesa lungo tutta la continuazione. B/C dipendono a loro volta dallo stesso box qualificato da compressione e dai suoi budget di tentativi.

**Controesempio:** un impulso continua ancora un tratto, supera B, poi reagisce. La vecchia idea di ritorno a B è effettivamente obsoleta; tenere B sarebbe sbagliato. Ma se la qualification rimane vera, il latch può impedire la nascita di un nuovo episodio per la nuova struttura. È una scelta di segmentazione del trend, non necessariamente “nessuna opportunità nel mercato”.

Una barra può inoltre contenere sia nuovo high sia reazione qualificante: l'ordine intrabar non è noto, mentre la precedenza del codice la spende. Non classifico questo automaticamente come bug, perché “prima di una reazione riconosciuta” ammette tale lettura conservativa. Il Director deve chiarire il significato nel caso concreto, senza inventare l'ordine OHLC.

Servono durata fino al termine, stato della qualification/reset e numero di casi con entrambe le condizioni nella barra terminale. Il solo conteggio 45 non dice quanto tempo di copertura sia perso né se la mancata rinascita sia dominante.

## 4. Compatibilità integrata delle tre famiglie

| Famiglia | Tensione da verificare | Cosa non fare |
|---|---|---|
| A — reazione/continuazione | Conferma oltre high della barra di reazione, stop sotto il suo low, target prima di una destinazione già vicina. Può richiedere di percorrere buona parte della gamba prima di ammettere l'ingresso. Zona propria e pivots possono ridurre ulteriormente lo spazio. | Non entrare retroattivamente al low; non togliere automaticamente il pivot; non estendere B a una proiezione solo per far passare il rapporto. |
| B — breakout/retest | Richiede compressione, uscita completa, retest e ulteriore conferma; il target può essere cap o proiezione. Il singolo trigger non consente di attribuire il fallimento al retest o alla scala di tutte le B. | Non estrapolare da n=1; non trattare breakout senza retest come lo stesso comportamento “meno filtrato”. |
| C — failed exit | Reclaim con close già rientrato, ulteriore conferma, rischio fino all'estremo fallito, target al midpoint o prima. Il percorso da estremo a centro può essere in gran parte consumato prima del trigger. Dominio limitato ai box da compressione. | Non convertire ogni range in box qualificato né spostare il target all'altro bordo senza una nuova tesi. |

Gli orizzonti attesi di 30–180, 30–240 e 15–90 minuti sono etichette/politiche; non rendono ampia una geometria locale. Attendere ore non aumenta il target immutabile. Allungare il deadline non risolve G/Q negativi all'ingresso.

Né è dimostrato che ogni pivot eleggibile sia economicamente una destinazione terminale: il metodo stesso dichiara di non inferirne significatività dalla mera eleggibilità, ma gli assegna comunque un potere di cap. È una **ipotesi economica forte**, non un fatto della fonte. Occorre distinguere in un'eventuale revisione destinazione della tesi e ostacolo intermedio, con una condizione osservabile di accettazione/superamento. Non basta ribattezzare “intermedio” qualsiasi livello scomodo.

Anche la politica first-trigger-consumes-attempt ha un effetto distinto: un close che supera molto la soglia può essere respinto definitivamente pur esistendo, in teoria, prezzi inferiori economicamente ammissibili. Un successivo ingresso su ritorno sarebbe una diversa regola causale, con ownership/invalidazione/lifetime propri; non una call retroattiva da aggiungere a settembre.

## 5. Spiegazioni concorrenti e grado di fiducia

| Spiegazione | Giudizio attuale |
|---|---|
| Geometria netta dei trigger incompatibile con K14/r1,2 | **Alta, confermata** per i 32 casi calcolati. I sei inside-zone sono esclusioni distinte. |
| Conferma di A consuma spazio economicamente necessario | **Media-alta come meccanismo**, non ancora quantificata causalmente. Il dato R→trigger non è prova sufficiente. |
| Cap indiscriminato di piccoli pivot è la causa principale | **Media come ipotesi**, non dimostrata. Mancano join e set di zone; i NONE sono diagnosticamente difettosi. |
| Stop eccessivamente larghi spiegano tutto | **Contraddetta come causa unica** dai 27 G sotto il floor e dal caso B a basso Q. |
| Errore aritmetico/simmetria LONG–SHORT nel gate | **Non supportata** dalla lettura mirata. Non è una certificazione dell'intero codice. |
| Oggetti sbagliati, non ancora noti o già ritirati influenzano T | **Possibile ma non dimostrata**; serve il join causale per i casi, non un rerun generale. |
| Segmentazione/reset e dipendenze condivise limitano gli scenari | **Alta sull'esistenza dell'attrito**, media sulla sua importanza relativa. La MarketView sparse è anche conseguenza diretta della tabella. |
| Calendario/funding/quote mancanti causano zero call | **Non supportata** nel profilo dichiarato: i moduli mancanti non erano gate di emissione. Aggiungerli non è la correzione di questo risultato. |

## 6. Un solo dossier, minimo sufficiente e criterio di arresto

Proposta al Director: richiedere una **estrazione read-only una tantum**, non nuove funzionalità di analytics. Identità run/commit/hashes e originali restano invariati. Nessuna lettura di esiti successivi per classificare “occasioni buone”.

### A. Una riga congiunta per ciascuno dei 38 trigger

- attempt/owner/famiglia/direzione; nascita, arm e ultima revisione, trigger publication/cursor, deadline;
- scala e zona congelate, A/B/R o L/U/M; soglia di conferma K-trigger distinta dal costo Kcost; V, T, prezzo effettivamente valutato, structural area e admissible bounds;
- G/Q/Kcost/margine e blocker originali; zona limitante/bloccante con tipo, source IDs, extrema time, known_at, stato e retirement;
- insieme delle zone opposte **già note** all'ultimo arm/revise e al trigger, incluse zone proprie, e motivo di esclusione di quelle pertinenti. Ricavarlo dalle versioni dei record, non dallo stato finale;
- per i sei AT_OPPOSING_AREA: prezzo/soglia/stop da record collegati e tutte le zone contenenti il prezzo al cutoff; se il preciso oggetto restituito non è recuperabile, dichiararlo.

Il journal contiene candidate, actionability, landmark e MarketView: questo è un join di fatti già pubblicati. Dove T/V non sono direttamente in actionability, recuperarli dai record originali; una derivazione algebrica da p/G/Q deve essere marcata DERIVED e verificata contro tick/stop del candidato. Non ricostruire una falsa decisione storica usando solo valori arrotondati del riepilogo. Se manca un campo indispensabile, dichiarare precisamente quale: nessun replay professionale sostitutivo.

### B. Due controlli analitici per distinguere le cause

Con geometria e set di livelli del **medesimo cutoff**, confrontare la soglia minima di conferma con il prezzo estremo economicamente ammissibile già definito in MP-001:

- LONG: conferma richiede almeno `K-trigger + tick`; adeguatezza impone `p ≤ (T+1,2V)/(2,2(1+Kcost/10000))`.
- SHORT: conferma richiede al massimo `K-trigger − tick`; adeguatezza impone `p ≥ (T+1,2V)/(2,2(1−Kcost/10000))`.

Se gli insiemi non si intersecano, quella geometria non può passare al prezzo di conferma nemmeno senza overshoot. Se si intersecano ma il close effettivo è oltre il limite, il caso segnala overshoot/tempo di conferma, non necessariamente target inadeguato già alla nascita. Intersecare poi con la fascia strutturale del trigger. Un prezzo teoricamente ammissibile non è una prova di ingresso eseguito o disponibile.

Fare il controllo al trigger per tutti i 32 casi; al cutoff arm/revise soltanto usando target allora noti e stop allora vigente. Se target/stop cambiano tra i due cutoff, attribuire separatamente il cambiamento. Non usare T-trigger nel passato come se fosse già noto. Nessuna variante di costi/soglie o ricerca del “prezzo vincente”.

### C. Copertura a monte senza un secondo studio

Per i 109 candidati: breve ledger di nascita→arm/revise→termine, età e motivo, distinguendo tentativi legati allo stesso owner. Per i 45 A spesi aggiungere la barra terminale già salvata e le condizioni high/reazione; riportare reset/qualification successivi solo se disponibili in record, senza simulare nuovi episodi.

Dal journal MarketView già emesso: una tabella di durata `NO_SUPPORTED_PLAN × observed_context × phase`, con WATCH presente/assente quando ricavabile. Per B/C riportare numero/durata degli owner box e consumo dei tentativi: 24 nascite B/C non sono necessariamente 24 strutture indipendenti. Non richiedo una scansione di tutti i “trade che si sarebbero potuti fare”.

**Output e stop:** un allegato tabellare completo, un breve responso per famiglia, massimo cinque timeline illustrative selezionate senza outcome: A con margine meno negativo, A con maggiore erosione riportata, primo AT_OPPOSING_AREA, unico B, C con maggior G. Gli elenchi completi evitano che gli esempi diventino cherry-picking. Terminare quando ogni scarto è riconciliato e classificato come errore di regola/oggetto, incompatibilità già alla conferma minima, overshoot, o dato insufficiente. Non estendere l'analisi a nuovi periodi.

Questa estrazione è necessaria perché un anticipo dell'entry, una diversa segmentazione dell'impulso e una diversa gerarchia delle destinazioni risolvono problemi diversi e possono peggiorarsi a vicenda. La sola mediana di G non sceglie fra essi.

## 7. Decisioni Director dopo il dossier, non modifiche attuali

Il Director deve decidere esplicitamente:

1. Se esista una divergenza codice–MP-001 da correggere mantenendo il metodo, oppure una regola implementata fedelmente ma economicamente incompatibile nel dominio prodotto.
2. Se il target rappresenti la destinazione della tesi o il primo ostacolo indistintamente. Un'eventuale distinzione deve usare tipo/location/comportamento osservabile ex ante, non il fatto che il prezzo poi lo abbia superato.
3. Se la conferma minima lasci una regione di ingresso praticabile. Nessuna proposta valida può omettere il costo della conferma o supporre un ingresso al minimo già riconosciuto.
4. Se una tesi direzionale debba persistere quando fallisce soltanto actionability e quando una nuova struttura possa creare un nuovo episodio senza sliding reset. Questo riguarda la copertura, non autorizza UP/DOWN costanti.

Se si sceglierà una revisione, dovrà essere **una proposta coerente e versionata**, con osservabili/eligibilità, destinazione e ostacoli, trigger/entry, invalidazione, orizzonte atteso e hard deadline, ownership/reset/expiry. Nessuno di questi campi va lasciato a Claude. Per ora non esiste evidenza sufficiente per riempirli scegliendo una variante superiore; non invento quella precisione.

## 8. Piccoli casi attesi e successiva validazione Owner

Casi ingegneristici da specificare per il prossimo intervento eventualmente autorizzato; non eseguiti in questa review:

- **Zona senza geometria:** prezzo dentro una zona; scarto AT_OPPOSING_AREA con provenance preservata, mai NONE inteso come assenza di ostacolo.
- **Conferma incompatibile:** LONG T=100700, V=99700, Kcost=14, r=1,2; massimo prezzo ammissibile circa 100014,525. Con soglia minima di conferma 100050 nessun prezzo confermato passa. Dimostrazione geometrica, non market outcome.
- **Overshoot distinto:** stessi T/V/costi, soglia 100000 ma close 100100. La soglia teorica è compatibile, il prezzo effettivo no; nessun ingresso retrodatato a 100000. Specchio SHORT.
- **Near edge propria:** unico riferimento B con target B−z. Room da B negativo non viene etichettato come prova di un pivot intermedio.
- **Cutoff:** pivot pubblicato dopo arm ma prima del trigger; appartiene solo al secondo set. Appendere dati futuri non cambia nessuno dei due.
- **High e reazione nella stessa barra:** conservare l'ambiguità dell'ordine e rendere esplicita la precedenza decisa, senza considerare automaticamente il caso un trade perso.

La futura sequenza di validazione, **non un nuovo run richiesto ora**, è: disposizione mirata → eventuale correzione/revisione e fixture → Owner-run sullo stesso settembre con baseline conservata. Confrontare non solo call ma domini, funnel, margini, finestre davvero utilizzabili, entry differite, costi e qualità dei risultati. Una call ottenuta peggiorando coerenza/causalità non è successo; zero call non si chiude con “attendere”.

Solo dopo una versione coerente e un comportamento utilizzabile in sviluppo: freeze di regole/profilo/criteri, verifica contaminazione e valutazione Owner sui periodi protetti Jan–Aug 2026 secondo il piano già dichiarato. Ogni risultato che influenza una revisione diventa sviluppo. Nessuna selezione del mese più favorevole, soglia di win rate promessa o gara fra segnali isolati.

## 9. Riferimenti e limiti

Riferimenti al commit della review:

- `delivery/WP-009-OWNER-BACKTEST-A-DIAGNOSIS.md` e `delivery/evidence/WP-009-OWNER-BACKTEST-A.json` — fonte dei risultati Owner; non nuova riproduzione.
- `delivery/MP-001-INTEGRATED-METHOD-PROPOSAL.md`, §§3, 5–8, 11; registro e disposizione v0.2 — norme del metodo.
- `src/algotrader/adviser/core.py`: `_a_births`, `_a_close`, `_box_birth`, `_bc_geometry`, `_context_withdrawals`, `_triggers`, `_resolve_target`, `_select_and_issue`, `_actionability`, `compute_view`, emissione candidate/landmark/view.
- `src/algotrader/adviser/geometry.py`: `predicate`, `structural_area`, `admissible_bounds`.
- `src/algotrader/adviser/report.py`: `staged_room`, `build` — significato dei contatori e perdita di attribuzione.

I record dettagliati della run non sono contenuti nel JSON di riepilogo: non affermo di averli letti. Nessun nuovo dato storico, outcome, backtest, acquisizione, parametro o codice del prodotto è stato introdotto. Nessuna fonte professionale aggiuntiva è necessaria per risolvere le discrepanze qui individuate: prima va chiuso il nesso causale fra le regole già adottate e gli scarti già prodotti. Repository remoto e baseline originali restano invariati.
