# Ottobre Owner — decisione metodologica Astra

6 ottobre 2026 · `C-Gian/algorithmic-trader` · commit `e33c4c3c63d89d4f2535a89173a68803dd3f5583`.

**Decisione: chiarire prima il significato dell'invalidazione A pre-conferma; mantenere sospesi novembre/dicembre durante questa sola decisione di design. Nessuna implementazione o nuova estrazione richiesta.** Non ripristinare v0.2 per recuperare il LONG e non modificare target, costi o soglie sulla base di ottobre.

## 1. Giudizio e responsabilità della precedente chiusura

Il dossier identifica una conseguenza metodologica reale: MP-002 ha trasformato il limite locale della reazione armata in un'invalidazione dell'intero scenario prima della conferma. La regola è esplicita, quindi non è una deviazione nascosta dell'executor. Ma è una restrizione sostanziale rispetto al re-anchoring di MP-001, non una semplice garanzia di ordinamento causale.

**La mia precedente chiusura CHIUDIBILE non ha riconosciuto adeguatamente questa conseguenza.** Avevo verificato la coerenza di “contatto prima della revisione”; non avevo contestato abbastanza quale oggetto quel contatto dovesse invalidare. La disposizione del Director e l'implementazione hanno adottato proprio quella semantica. Non attribuisco ora al codice un errore che appartiene anche alla review del design.

La distinzione è importante: registrare un contatto con il vecchio V prima di pubblicare un nuovo V è necessario per la causalità. Far morire per quel contatto anche l'intero scenario di continuazione è una scelta economica e interpretativa aggiuntiva.

## 2. Cosa dimostrano le evidenze

Ho letto SUMMARY, dossier.json e confirmations.csv, confrontandoli con MP-002, la disposition e le regole MP-001 pertinenti. La lettura mirata di `core.py::_a_close` e `core3.py::_scen_intervals`/ordine di dispatch corrobora il meccanismo dichiarato. Ho ricalcolato le sei regioni economiche dai numeri del dossier con algebra separata dagli helper di prodotto; ho controllato le 64 righe campionate delle attese rispetto alle regioni riportate. Non ho eseguito il motore né riestratto DB/cache.

| Evidenza | Conclusione consentita | Conclusione non consentita |
|---|---|---|
| Il 26 ottobre, prima divergenza alle 23:30: low 114329,5 contro V armato 114343,28 | v0.3 termina lo scenario prima della revisione; v0.2 pubblica un nuovo anchor | Eliminare quella regola garantirebbe la stessa call in v0.3 |
| 49/55 revisioni v0.2, su 29 attempt, oltrepassano il precedente V | La restrizione incide su una parte ampia del processo di revisione osservato | 49 occasioni, 29 trade mancati o 29 errori di v0.3 |
| 30 terminali A pre-conferma per V in v0.3; due revisioni A | La maturazione delle reazioni è molto diversa | Corrispondenza uno-a-uno con tutti i 29 attempt v0.2 |
| Sei conferme; tre WAIT, due vuoti economici, un contatto pre-entry | Il routing osservato è compatibile con le regole dichiarate | Sei opportunità utilizzabili |
| Nessuna delle tre WAIT raggiunge il proprio intervallo ammissibile | Non c'è un ingresso RETURN perso per un semplice filtro nascosto in quei percorsi | RETURN non possa mai funzionare in altri contesti |
| Un solo LONG v0.2, path PRIMARY positivo circa +0,10% price-net, uscita per scadenza | È un primo output operativo concreto e un caso da comprendere | Target raggiunto, edge dimostrato o superiorità del metodo |

Runtime assurance e input comparabili rendono la diagnosi utilizzabile; non certificano le ipotesi economiche. La riproduzione dei report con gli stessi builder è una riconciliazione, non una prova indipendente del metodo. Le garanzie di hash/export restano evidenza dell'executor.

## 3. Il LONG del 26 ottobre: cambiano soprattutto la reazione e la conferma

L'episodio nasce alle 23:00 con A=112835, B=115759,3 e z=19,92. Alle 23:15 entrambe le versioni hanno R=114363,2, K=114940,6, V=114343,28. Non esiste ancora una call.

Alle 23:30 v0.2 riconosce la nuova barra 15m e aggiorna:

- R a 114329,5;
- K a 114540,5;
- V a 114309,58.

Alle 23:34 il close 114599,9 supera il **nuovo** K, ma rimane sotto il precedente 114940,6. La revisione cambia quindi il punto da cui si considera completato il recupero; non sposta soltanto uno stop di pochi dollari. Al trigger v0.2 il target 115739,3 lascia circa 99,4 bps e il rischio è circa 25,3 bps, compatibili con il gate dichiarato.

v0.3 termina prima, per il contatto col vecchio V. La sequenza spiega la divergenza concreta senza usare il profitto successivo come criterio. Non autorizza a dedurre la call controfattuale: v0.3 conserva altre differenze di owner, destinazioni, contatti, target, selezione e tempo. Togliere un terminale può cambiare anche il percorso successivo del suo stato.

## 4. Problema di design: tre significati da separare

### Prima della conferma: reazione ancora in formazione

MP-001 consente di aggiornare R/K/V su una nuova reazione completa e pulita, dentro l'impulso e senza estendere la scadenza. Questa costruzione rappresenta una reazione che può ancora approfondirsi prima di recuperare.

Con V=R−z nel LONG, MP-002 invece ammette solo una nuova R che non abbia già toccato quel V. In termini intuitivi, il nuovo approfondimento deve restare entro il piccolo buffer della reazione precedente. Ripetuti piccoli aggiornamenti possono ancora avvenire; un approfondimento più ampio prima del successivo aggiornamento termina tutto. Questo introduce una sensibilità alla traiettoria e alla cadenza delle revisioni, non una prova automatica che l'impulso originario sia fallito.

La regola è coerente se la tesi voluta è: **“quel preciso minimo di reazione deve tenere da ora”**. È più restrittiva della tesi: **“l'impulso resta valido mentre una reazione si completa dentro i suoi limiti”**. Per la famiglia A come inizialmente descritta, considero la seconda interpretazione più coerente.

### Dopo conferma, prima dell'ingresso RETURN

Qui la situazione cambia: il metodo ha già dichiarato che il recupero si è confermato e ha congelato R/K/V. Un ritorno oltre quel V nega proprio la struttura confermata sulla quale l'attesa è basata. **Non raccomando di riaprire il re-anchoring durante WAIT_PRICE**, anche se non è ancora stata emessa una call.

### Dopo l'emissione

V è anche protezione e guidance pubblicata. Non si sposta per assorbire un contatto; restano i terminali, le ambiguità e le regole del valutatore. L'assenza di ordini automatici non rende facoltativa l'immutabilità della raccomandazione storica.

### Direzione raccomandata, ancora da disporre

Prima della conferma distinguere **fallimento dell'anchor locale** da **fallimento dello scenario/owner strutturale**:

1. Il contatto con il V locale viene sempre registrato e rende inutilizzabile quel vecchio armamento. Non è cancellato da una revisione successiva.
2. Lo scenario può restare in osservazione solo se i limiti strutturali originari, il contesto, la copertura e la scadenza lo consentono. Nessuna nuova freccia incondizionata derivata dalla sola sopravvivenza dell'owner.
3. Un nuovo anchor può essere riconosciuto soltanto da una successiva pubblicazione causale di barra 15m completa che soddisfi le condizioni di reazione. Nel dispatch che contiene il contatto e la barra 15m: prima si chiude l'anchor vecchio, poi eventualmente si pubblica quello nuovo.
4. Il nuovo anchor richiede un minuto di conferma interamente successivo alla propria pubblicazione. Non può usare il recupero precedente, né l'open della barra con cui viene riconosciuto.
5. A/B dell'impulso, z congelato, deadline originale e budget strutturale non si spostano per consentire altri tentativi. Le revisioni sono entro un singolo episodio temporalmente limitato; non sono nuove call né rinnovi dopo un'entry respinta.
6. Dalla prima conferma valida in poi, nessuna revisione di R/K/V: conservare la disciplina MP-002 di WAIT e call.

È una direzione semantica, non l'autorizzazione a sostituire oggi una condizione nel codice. La nota di design deve nominare esattamente i limiti dello scenario già presenti in MP-001, distinguendo quelli da close e quelli da contatto: non convertire implicitamente A+z in uno stop 1m né introdurre tolleranze ricavate dal minimo del 26 ottobre.

## 5. Controesempi che la decisione deve risolvere

Numeri sintetici, senza claim di redditività.

| Caso | Esito richiesto nella direzione raccomandata |
|---|---|
| Impulso A=100, B=120, z=1; reazione R=112, K=116, V=111. Prima della conferma compare low=110,5, mentre il limite strutturale originario resta rispettato | Il vecchio anchor è fallito; non necessariamente tutto lo scenario. Un nuovo anchor da barra completa può diventare eleggibile solo prospetticamente |
| Il low tocca 110,5 e nella stessa barra recupera oltre il nuovo K, calcolabile soltanto a fine barra | Nessuna conferma retroattiva. Serve un minuto valido dopo la nuova pubblicazione |
| Reazioni scendono progressivamente; una barra completa chiude a 100,5, violando il limite originario close≤A+z=101 | Scenario terminale; un successivo rimbalzo non lo salva aggiornando A o V |
| Le reazioni restano entro i limiti, ma arriva la scadenza originale | Termine dell'episodio. Ogni nuova R non compra altre due ore |
| R/K/V sono già stati confermati; durante WAIT il prezzo tocca V e poi rimbalza | Termine dell'opportunità confermata; nessun nuovo anchor per salvarla |
| Esiste già una call e il prezzo tocca V | Regole di protezione/ambiguità e valutazione della call; nessun allargamento dello stop |

Il controesempio opposto è quindi preso sul serio: consentire revisioni illimitate, muovendo anche impulso, durata o condizioni già confermate, manterrebbe artificialmente viva una tesi fallita. **Riconoscere una reazione ancora in formazione non significa concedere revisioni dopo qualunque invalidazione.**

## 6. Target, conferma e RETURN: algebra coerente, dominio molto selettivo

I sei bound verificati sono 116030,5; 123561,2; 124514,2 SHORT; 107800,8; 111457,9; 107422,0 SHORT. Le intersezioni riproducono tre regioni non vuote e tre vuote. Il quarto caso termina prima per contatto target ma appartiene comunque a N: **N/D=3/6=0,5**, non maggiore di 0,5. Non reinterpretare la soglia preregistrata.

Nelle tre WAIT la conferma arriva quando il prezzo ha già recuperato buona parte della distanza alla destinazione. Con stop ancora riferito alla reazione e costi/rapporto invariati, la parte utilizzabile del corridoio è quella vicina a R. Il metodo richiede quindi una **seconda visita profonda verso la reazione, dopo il recupero confermato e prima del completamento verso B**. Questa è una configurazione più specifica della generica continuazione dopo reazione.

Le distanze richieste, circa 26–29 bps dal close di conferma, non sono un errore aritmetico. Ma nemmeno una ragione per presumere che quel ritorno fosse probabile. Nei dati consegnati:

- 1 ottobre: 41 campioni, zero close ammissibili e nessun contatto intrabar con la regione; scadenza del setup;
- 6 ottobre: un campione, nessun ritorno; destinazione raggiunta nel minuto seguente;
- 30 ottobre: 22 campioni, nessun ritorno ammissibile; contatto del cap, poi della destinazione.

Cinque target sono il bordo della **B propria**, non piccoli pivot esterni che si potrebbero semplicemente eliminare. Anche il sesto pivot è allo stesso livello centrale della destinazione B, con la propria zona. Allontanare il target oltre B significherebbe cambiare da ritorno alla destinazione originaria a prosecuzione oltre quell'estremo: serve un'altra tesi, non una correzione geometrica per far passare il rapporto.

Il successivo contatto della destinazione in tutti e sei i casi mostra perché lettura e azione devono restare distinte. Non è “sei trade vincenti”, non valida tutta la MarketView e non misura il valore delle previsioni che non sono mai arrivate alla conferma. Sono sei casi condizionati a quella selezione, con tempi e room differenti.

**Giudizio:** RETURN è internamente coerente come opportunità stretta e facoltativa; questi dati ne mostrano la mancata attivazione, non la falsificazione generale. Non va presentato come soluzione già dimostrata al costo della conferma. Non cambierei ora corridoio, target, stop, costi o durate; il problema semantico a monte va deciso prima.

## 7. Classificazione dei problemi e limiti della prova

| Categoria | Giudizio |
|---|---|
| Difetto di implementazione responsabile dei casi esaminati | Non dimostrato. Ordine V-contact→revisione e routing sono conformi al testo adottato |
| Problema di design | Equiparazione del V locale pre-conferma all'invalidazione dell'intero scenario; restrizione del re-anchoring non adeguatamente riconosciuta nella chiusura |
| Ipotesi economica aperta | Utilità della continuazione selezionata, frequenza dei ritorni validi, selezione avversa, praticabilità dopo ritardo e costi |
| Insufficienza delle evidenze | Controfattuale v0.3 senza questa regola; redditività generale; esiti di novembre/dicembre; qualità complessiva MarketView |

I 29 attempt non sono un campione di perdite causate dalla restrizione: 28 non emisero call nemmeno in v0.2. Il dato rende la scelta strutturalmente importante, senza provarne il segno economico. Nemmeno 49/55 revisioni sono 49 owner indipendenti.

La nota sul sampling dell'ultimo minuto di dispatch multipli non spiega queste tre attese: qui i campioni sono consecutivi e neppure gli estremi raggiungono le regioni. Resta un confine ingegneristico da verificare se emerge una discrepanza concreta; non è un motivo per riaprire ora un audit generale o un'altra estrazione.

Una piccola imprecisione del dossier non cambia il giudizio: nel caso SHORT del 30 ottobre il campo DERIVED riporta distanza target di 29,64 bps, mentre T=106794,6 e close=107111,1 danno 29,55 bps, coerenti con G e CSV. Il target è il pivot con la propria zona, non va ricostruito usando automaticamente z dell'owner B. Ho usato T/V espliciti nei controlli.

## 8. Minimo prossimo passo e destino del confronto congelato

**Un solo passo documentale del Director:** una breve decisione sul significato di V prima della conferma, con distinzione scenario/anchor confermato/call e gli esiti dei sei controesempi sopra. Raccomando la separazione proposta in §4. Non serve nuova ricerca, una nuova estrazione o una tolleranza numerica.

Continuare subito novembre/dicembre aggiungerebbe risultati prima di aver deciso se il metodo rappresenta il processo desiderato. La questione è risolvibile senza quei risultati; vale la pena mantenerli non ancora osservati durante questa breve decisione. Non è una richiesta di sospensione indefinita.

Se il Director **conferma la semantica rigida**, la deve descrivere come reazione armata che deve tenere fin dal primo arm. Si potrà allora riprendere il confronto fisso invariato con autorizzazione separata: sapremo precisamente quale ipotesi stiamo valutando.

Se il Director **adotta la separazione raccomandata**, sarà una nuova versione metodologica, non un bugfix di v0.3. Il confronto preregistrato ottobre–dicembre della vecchia versione resta parziale/sospeso; ottobre e le run originali si preservano. Prima di ulteriori risultati occorre dichiarare il nuovo piano e la contaminazione: non sostituire v0.3 a metà serie continuando a chiamarla verifica immutata. Questa review non assegna né implementazione né un nuovo backtest.

Il primo LONG è un progresso concreto dell'applicazione: ora abbiamo anche una raccomandazione e un percorso ipotetico da ispezionare. Il progresso metodologico consiste nel capire perché sia comparsa, e decidere quale processo vogliamo rappresentare anche quando lo stesso processo produrrà una perdita.
