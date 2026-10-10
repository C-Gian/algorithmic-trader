---
title: "Analisi Evoluta — corpus tecnico e di ricerca per Astra"
language: it
version: "1.0"
compiled_on: "2026-10-10"
source_primary: "Jacopo Marini, Guida pratica per comprendere l'Analisi Evoluta, ©2023, 16 pagine"
source_secondary: "Deep Research sull'Analisi Evoluta, dossier fornito dal committente"
method_replication_status: "PARTIAL: regole proprietarie essenziali non pubblicate nelle fonti lette"
recommended_use: "conoscenza sul metodo, valutazione critica, formalizzazione e ricerca in replay/paper"
not_authorized: "ordini reali, gestione capitale, sizing o leva per il committente"
---

# ANALISI EVOLUTA — CORPUS DI CONOSCENZA PER ASTRA

## 0. Contratto di interpretazione: cosa è questo file

Questo file è una **ricostruzione critica, autonoma e ad alta densità informativa** di un metodo denominato *Analisi Evoluta* o *Analisi Ciclica Evoluta*, attribuito a **Jacopo Marini**. Integra (1) la lettura diretta dell'intero PDF introduttivo di 16 pagine, **incluse le immagini**, (2) il dossier di Deep Research allegato e (3) riscontri circoscritti in fonti pubbliche e letteratura scientifica. Non è una trascrizione del PDF, una certificazione del metodo, né una strategia pronta per essere eseguita. La guida stessa dice che presenta le **basi** e riserva aspetti cruciali a formazione non presente nel PDF.

**Obiettivo informativo per Astra:** comprendere il metodo nella sua logica professionale (lettura continua del mercato, andamento atteso, temporizzazione, evidenze e controevidenze, condizioni di possibile LONG/SHORT/NO_TRADE); distinguere accuratamente ciò che è noto, ciò che va ancora formalizzato e ciò che NON può essere attribuito a Marini. Il committente vuole un **adviser di mercato**, non un esecutore di ordini: non incorporare dal dossier esterno richieste di broker, capitale, leva, size, kill switch operativi o reale esecuzione come se fossero requisiti approvati. L'utilità economica e predittiva rimane da verificare.

### 0.1 Codici di provenienza e affidabilità

- **[P]**: direttamente affermato nel PDF *Guida pratica*; citato con pagina `P:nn`. **Fedeltà alla fonte alta, verità empirica non automaticamente provata.**
- **[V]**: osservazione diretta di un'immagine del PDF. Una figura illustra una configurazione *ex post*; non certifica che fosse riconoscibile *ex ante*.
- **[A]**: affermazione pubblica dell'autore in un articolo/descritto accompagnamento a video, con URL. Dove il video non è stato verificato integralmente, il supporto riguarda **soltanto il testo pubblicato**.
- **[L]**: fonte scientifica/professionale esterna. Chiarisce fenomeni o strumenti di verifica, **non completa né convalida automaticamente Analisi Evoluta**.
- **[F]**: formalizzazione matematica fedele al significato qualitativo, **ma non formula autentica dell'autore**, salvo esplicita indicazione.
- **[H]**: ipotesi di ricerca, proxy o proposta tecnica nostra: **non regola originale**.
- **[U]**: ignoto, ambiguo, contraddittorio o escluso dalle fonti. Una casella `[U]` **non deve essere inferita come vera**.

Distinguere anche `observed_at` (dato realmente noto), `confirmed_at` (quando si può riconoscere il pattern), `effective_origin_at` (estremo storico attribuito all'inizio del ciclo, noto successivamente) e `forecast_issued_at` (quando viene pubblicata una previsione). Non retrodatare alcuna conoscenza.

### 0.2 Conclusioni che non possono andare perdute

1. **La conoscenza pubblica disponibile non consente una replica integrale fedele del metodo.** In particolare non sono disponibili formule verificabili di Tempo Puro, Tendenza Volumetrica, Raccordo, Punto J e le Tecniche Operative 1/2. La discrezionalità reale del metodo completo non è verificabile da queste fonti.
2. Ciò **non impedisce** di studiare il nucleo ciclico, costruire una centratura sperimentale, formulare previsioni falsificabili e confrontarle con alternative concrete: ogni parte introdotta per colmare un vuoto resta etichettata `[H]`.
3. Le condizioni del metodo **interagiscono**: tempo e struttura dei sottocicli, swing, volume, ciclo indice/inverso e vincoli non sono una votazione di indicatori. Il PDF non specifica comunque la funzione completa che li combina.
4. Il mercato può essere interpretato anche quando il trade è **NO_TRADE**: una previsione direzionale e la decisione di operare sono oggetti diversi. Non confondere `market_view=BEARISH` con `decision=SHORT`.
5. **Nessuna evidenza rigorosa di redditività integrale** è documentata nella guida o stabilita nel dossier. Esempi grafici e dichiarazioni di performance dell'autore non sono backtest indipendenti.

## 1. Identità, genealogia e vocabolario essenziale

**[P:4,8,9,10,14,15]** L'Analisi Evoluta è presentata come sviluppo della tradizione dell'analisi ciclica di **J. M. Hurst** e dell'ingegner **Giuseppe Migliorino**, con richiami a **W. D. Gann**, cui l'autore dichiara di aggiungere analisi dei volumi, candele giapponesi, vari indicatori e concetti nuovi. L'autore definisce il proprio metodo statistico-matematico e non discrezionale, ma la guida non contiene la specificazione completa per verificarne tale caratteristica.

La genealogia è **storica, non equivalenza metodologica**:

- **Hurst**: lettura del prezzo per oscillazioni/periodicità su più scale, gerarchie cicliche, interazione cicli/trend. La scala di gradi del PDF richiama questa famiglia, ma l'Analisi Evoluta rifiuta una rigidità ritenuta superata. **Non importare indiscriminatamente** la struttura nominale, le medie mobili/FLD o le regole di Hurst come se fossero di Marini. [P:8,15; L]
- **Migliorino**: tradizione ciclica italiana e *Lingua di Bayer*, che Marini associa al proprio *Raccordo* ma dichiara aggiornato. **Non equiparare** ogni lingua classica al Raccordo originale del PDF. [P:10-11; L]
- **Gann**: dichiarata fonte d'ispirazione; **nessun angolo, ventaglio, quadrato, divisione del tempo o specifica formula ganniana è prescritta dal PDF**. [P:14]
- **Volumi e HFT**: l'autore sostiene che le pressioni di acquisto/vendita e gli HFT siano centrali per i movimenti dei cicli; è **una tesi del metodo**, non una legge scientifica dimostrata. [P:9-10; L]

**Lessico:**

| Termine | Significato utile | Fonte e limiti |
|---|---|---|
| `T` o `T (Tracy)` | Ciclo base settimanale, durata indicativa 6–11 giorni | [P:4,9]; non definito come settimana di calendario |
| `T-3` | Ciclo detto *giornaliero* | [P:4-6,9]; per i mercati azionari è un intervallo di barre, non necessariamente 24 ore |
| `T+2` | Mensile | [P:4,9] |
| `T+5` | Annuale | [P:4,9] |
| `lato indice` | Segmentazione del prezzo minimo → massimo → minimo | [P:4]; vale anche per BTC/altro asset, non solo indice bursatile |
| `lato inverso` / suffisso `i` | Segmentazione massimo → minimo → massimo | [P:13]; `T+2i` = mensile inverso |
| `centratura` | Attribuzione degli estremi osservati ai cicli e gradi | [P:12-14]; algoritmo non specificato |
| `swing di pertinenza` | Estremo di prezzo da superare come conferma pertinente al grado | [P:6,10]; metodo di selezione ignoto |
| `Tempo Puro` | Conferma temporale oltre la sola conta tradizionale dei cicli | [P:8,10]; formula ignota |
| `vincolo` | Informazione direzionale implicata dalla violazione anticipata di un estremo | [P:12]; propagazione/durata esatta ignote |
| `Raccordo` | Falsa partenza con breve salita e rapida discesa, collegata a un sottociclo e volume | [P:10-11]; almeno due tipi, formula non pubblicata |
| `reciprocità` | Possibile coincidenza tra minimo indice e massimo inverso e viceversa | [P:12-14]; non sempre rispettata |
| `Cambio di Ritmo` | Fenomeno associato al venir meno della reciprocità | [P:14]; regola ignota |
| `Ciclo Motore` | Struttura possibile dopo cambio ritmo/inversione | [P:14]; regola ignota |
| `Punto J` | Controllo della centratura ciclica | [P:14; V:13]; definizione matematica ignota |
| `Tecniche operative 1 e 2` | Procedure di trading citate | [P:14]; contenuto ignoto |

## 2. Fondamento geometrico: che cosa è un ciclo

### 2.1 Lato indice

**[P:4]** Un ciclo lato indice inizia in un minimo, raggiunge un massimo e termina su un minimo successivo. Esistono durata **minima**, **media** e **massima**; non un unico periodo deterministico. Il termine `indice` indica qui la lettura convenzionale di un grafico dei prezzi, anche quando l'asset è BTC, oro o altra attività.

La rappresentazione `[F]` di un ciclo **già identificato** è:

```text
indice G:  L0 (origine) -> H (massimo interno) -> L1 (chiusura)
            t0                  tH                t1
D = t1 - t0, con t0 < tH < t1 nei casi non degeneri
```

La sequenza **non** significa che al tempo `t0` un osservatore sapesse già che quel minimo fosse origine. Spesso `t0` diventa certo solo in `t_confirm > t0`. Il massimo `H` può essere provvisorio finché il ciclo non chiude.

### 2.2 Lato inverso

**[P:13]** Un ciclo inverso parte da un massimo, sviluppa un minimo e chiude sul massimo successivo:

```text
inverso Gi: H0 (origine) -> L (minimo interno) -> H1 (chiusura)
             t0                  tL                  t1
```

Non assumere che `inverse` significhi applicare matematicamente il reciproco `1/prezzo` o invertire il segno dei rendimenti. Il PDF descrive **un diverso modo di delimitare le onde sullo stesso grafico del prezzo**, massimo→massimo. Un eventuale uso di `-prezzo` per implementare un algoritmo simmetrico è soltanto una tecnica `[H]`: va verificato che preservi la semantica originaria.

### 2.3 Gerarchia di gradi

**[P:4,8,9]** Gradi piccoli e grandi sono annidati approssimativamente secondo durate in rapporto 1:2 tra gradi successivi, non rigidamente. Schema dichiarato:

```text
T-6  = 1/8 giornaliero
T-5  = 1/4 giornaliero
T-4  = 1/2 giornaliero
T-3  = giornaliero
T-2  = 2 giorni
T-1  = circa 4 giorni
T    = settimanale / Tracy
T+1  = bisettimanale
T+2  = mensile
T+3  = trimestrale
T+4  = semestrale
T+5  = annuale
```

Il PDF menziona T-3, T, T+2 e T+5 come riferimenti principali, precisando che altri gradi potrebbero non essere sempre identificabili sul grafico. Non richiedere una centratura perfetta di **tutti** i gradi come dogma originale. La scomposizione in 3 o 4 parti **non è obbligatoria**: un ciclo può contenere fino a **6 sottocicli**; l'esempio del PDF è un `T+2` che si compone di sei `T` singoli. [P:8]

Un ciclo più grande e i suoi figli forniscono contesto reciproco, ma dalle fonti non derivano né una regola unica per ripartire 6 sotto-onde né una proprietà matematica rigorosa di nesting senza sovrapposizioni. [U]

## 3. Durate ORIGINALI della tabella, limiti ed eccezioni

### 3.1 Tabella p. 9 — S&P 500, Nasdaq, DAX

**[P:9; V:9]** Numeri verificati direttamente sulla **tabella grafica** del PDF, non ricostruiti per raddoppio:

| Grado | Descrizione | Min | Media | Max | Unità nella tabella |
|---|---|---:|---:|---:|---|
| T-6 | 1/8 giornaliero | 3 | 4 | 5 | barre di 15 min |
| T-5 | 1/4 giornaliero | 6 | 8 | 10 | barre di 15 min |
| T-4 | 1/2 giornaliero | 12 | 16 | 20 | barre di 15 min |
| T-3 | giornaliero | 21 | 32 | 44 | barre di 15 min |
| T-2 | 2 giorni | 44 | 64 | 84 | barre di 15 min |
| T-1 | circa 4 giorni | **NON DATO** | **NON DATO** | **NON DATO** | tabella mostra puntini |
| T / Tracy | settimanale | 6 | 8 | 11 | **giorni** |
| T+1 | bisettimanale | 12 | 16 | 21 | giorni |
| T+2 | mensile | 24 | 32 | 43 | giorni |
| T+3 | trimestrale | 48 | 64 | 84 | giorni |
| T+4 | semestrale | 96 | 128 | 168 | giorni |
| T+5 | annuale | 192 | 256 | 336 | giorni |

**Avvertenza fondamentale:** questa tabella mescola una **sezione in barre da 15 minuti** e una **sezione in giorni**. Il punto di separazione è T / Tracy. Non convertirle tra loro usando arbitrariamente `1 giorno = 24 ore`, `1 giorno = una sessione`, `1 T = 8 sessioni` oppure valori moderni di CFD/futures. La convenzione di `giorno` (calendario, contrattazione, sedute, sessione) **non è risolta** nel documento; la convenzione temporale condiziona tutte le date di scadenza e gli start/end. [U]

**Lettura dei colori della tabella** [V:9]: giallo = minimo, verde = media, rosso = massimo. I valori sono **durate suggerite**, non probabilità, target di prezzo o limiti fisici universali.

### 3.2 Eccezione FTSE MIB

**[P:9]** Minimo `T-3=24 barre da 15 min`, anziché 21; minimo `T-2=48 barre da 15 min`, anziché 44. Durante fasi di forte discesa/crash l'autore ammette accorciamento anche dei minimi e cita `23` barre per il MIB. Non è specificata una funzione regime→durata né se gli altri punti di minima/media/massima cambino. **Non applicare automaticamente** 24/32/44 o 48/64/84 come tabella completa MIB approvata: sono noti soltanto gli aggiustamenti espliciti. [U]

### 3.3 Bitcoin ed Ethereum

**[P:4,9]** La guida specifica che, per BTC e ETH, le barre di riferimento **non sono 15 minuti ma 45 minuti**, e che il minimo del `T-3` è **24 barre in media**. L'espressione qualifica il numero: non trattarlo come limite immutabile o perfettamente certo. In minuti `24 × 45 = 1080 min = 18 h` di candele consecutive, **solo se** il mercato è trattato 24/7, senza buchi e con la corretta ancora delle barre. Il PDF **non fornisce una tabella completa** T-6…T+5 specifica crypto, non stabilisce l'anchor di aggregazione dei 45m, non definisce exchange, simbolo, mercato spot/perpetual/futures né il volume da utilizzare. [U]

La pagina 4 attribuisce al T settimanale `6–11 giorni` anche su BTC/ETH, ma non consente di dedurre da quel numero gli estremi di tutti i gradi inferiori sulle barre crypto. **Non importare ciecamente** i valori in barre da 15m previsti per indici sul medesimo numero di barre da 45m. [U]

### 3.4 Variabilità temporale e regime

**[P:9]** L'autore osserva che in salita i cicli tendono mediamente ad allungarsi, in discesa/crash ad accorciarsi; segnala durate T settimanali americane recentemente più brevi e dice di sorvegliare nel tempo la stabilità dei valori. Questa è una **generalizzazione qualitativa da verificare**, non una formula di correzione basata su ATR, trend o volatilità.

`D_g` può dunque essere studiata come una variabile condizionale `[H]`:

```text
Durata osservata ~ f(asset, grado, segmento temporale, sessione, regime)
```

MA: stimare `f()` non è riprodurre il Tempo Puro originale.

### 3.5 Esempio quantitativo neutro, senza dare falsa precisione

Se un `T-3` indice S&P parte a `t0` e ha già **14 barre da 15 minuti** trascorse, è **prima** delle 21 barre minime della tabella. Se raggiunge 32 barre è vicino al valore medio. Se raggiunge 45 barre è *oltre* il massimo tabellare di 44. **Non si può però inferire automaticamente** che a 44 barre debba chiudere, né riposizionare un pivot retroattivamente per far rientrare la statistica. La fonte non fornisce una regola di trattamento per gli overrun. [F/U]

## 4. Come parte un ciclo: tre elementi e una lacuna cruciale

### 4.1 Enunciato originale

**[P:6]** Per il `T` lato indice il PDF elenca tre condizioni: violazione dello swing di **massimo** pertinente, un tempo espresso nell'esempio come `T-2 rialzista`, e volumi. Generalizza: per far nascere un ciclo di grado `G`, servirebbe un sottociclo `G-2` rialzista o laterale/neutro **oppure** un *Tempo Puro equivalente*; lo swing è una conferma, che può però non verificarsi con Tendenza Volumetrica molto forte, anche rialzista o ribassista. Per un `T-3`, l'esempio pratico è `T-5` laterale-rialzista. La fonte insiste sul successivo esame dei volumi per anticipare la qualità rialzista/neutra/ribassista del ciclo, salvo vincoli già intervenuti.

**[P:10]** La pagina 10 presenta la concomitanza di (1) violazione swing pertinente, (2) conferma volumetrica, (3) tempo trascorso **sopra un minimo** (o **sotto un massimo** per il lato inverso), come *Tempo Puro*. Mancando quest'ultimo, l'autore segnala rischio di Raccordo.

### 4.2 Relazioni logiche sicure e NON sicure

**Sicuro:** i tre domini **prezzo/swing**, **struttura-tempo** e **volume** svolgono un ruolo centrale e il grado `G-2` è rilevante nell'avvio di `G`. Il tempo puro può sostituire una conferma strutturale in alcune circostanze; una forte tendenza volumetrica può rendere lo swing non manifesto. [P:6,10]

**Non noto** `[U]`:

- quale specifico swing debba essere violato e se valgano high/close, tick/soglia, tolleranza o conferma su chiusura;
- se il sottociclo `G-2` debba **essere completato** e classificato o sia sufficiente una condizione in tempo reale;
- l'ordine delle conferme e se una successiva conferma possa retrodatare l'origine;
- la formula e il tempo di persistenza del *Tempo Puro* sopra il minimo/sotto il massimo;
- quali misure di volume, soglie e direzioni siano necessarie;
- la precedenza fra swing assente e forte tendenza volumetrica;
- se le tre condizioni siano `AND`, `OR` condizionato, una macchina a stati o una valutazione più ampia;
- cosa significhi esattamente 'lo swing può non verificarsi' in scenari ribassisti.

**Conclusione progettuale:** non codificare `start = swing AND lower2 AND volume` come *la* regola autentica. È una **versione investigativa [H]** e può produrre comportamenti diversi dal metodo proprietario.

### 4.3 Lato inverso

Il PDF dà una simmetria parziale: il Tempo Puro si valuta **sotto un massimo** e il ciclo inverso parte da un massimo. [P:10,13] Per simmetria geometrica, uno swing di **minimo** sarebbe candidato naturale `[F]`, ma **non esiste nel PDF una specifica completa identica** della condizione d'avvio `Gi`, quindi non trattare ogni operatore speculare come fonte originale. [U]

## 5. Come termina un ciclo

**[P:6]** La presenza di un sottociclo di **tre gradi inferiori ribassista** è descritta come condizione **necessaria e sufficiente** alla chiusura di un ciclo. Esempio: il `T-3` chiude tramite un `T-6` ribassista. Non sostituire questo rapporto con `G-2`: due gradi inferiori per l'avvio, tre per la chiusura. Questa asimmetria è un elemento strutturale fondamentale.

**[U] Il testo non spiega** se il ciclo di `G-3` debba aver già completato il suo minimo finale, se il segnale di chiusura arrivi alla sua partenza, alla conferma della classificazione ribassista o al suo completamento; non indica quale minimo del grado superiore sia selezionato come chiusura, come evitare più chiusure candidate, cosa fare quando il ciclo `G-3` è ribassista ma il `G` supera la durata massima, e come trattare raccordi e sottocicli incompleti.

**Disciplina causale:** `end_effective_at` (minimo terminale riconosciuto a posteriori) **non equivale** a `end_recognized_at` (momento in cui la chiusura è inferibile da informazioni già arrivate). Per un'eventuale previsione va pubblicato il **secondo**. [F]

## 6. Forma: rialzista, ribassista, neutra

**[P:6-8; V:7-8]** Le forme spiegate nel PDF sono:

- **Rialzista:** minimo iniziale, massimo di solito nella **seconda parte**, minimo terminale **più alto** del minimo iniziale.
- **Ribassista:** minimo iniziale, massimo **solitamente nella prima parte**, minimo terminale **più basso** di quello iniziale.
- **Neutra:** minimo iniziale, massimo in **zona centrale** e minimo terminale ottenuto con **ritracciamento di Fibonacci 75–99%** secondo l'autore.

Termini come *di solito* e *zona centrale* non sono parametri soglia. Il volume è indicato come utile per anticipare il carattere del ciclo **prima** che esso finisca; la forma finale, invece, può essere accertata compiutamente **soltanto quando l'estremo terminale è noto**. [P/F]

### 6.1 Descrittori quantitativi proposti [F/H]

Dati `L0` origine, `H` massimo e `L1` termine:

```text
cycle_end_return = (L1 - L0)/L0
peak_location = (tH - t0)/(t1 - t0)
retracement_from_peak = (H - L1)/(H - L0)   solo se H > L0
```

Questi descrittori servono **a non perdere l'informazione** del PDF; non sono formule confermate dell'autore. Non utilizzare `peak_location` quando `t1` non è noto; in streaming un eventuale `peak_location_so_far` è una diversa variabile. Non assumere `0.5` come confine rigoroso fra prima e seconda parte quando il testo usa avverbi qualitativi. [H]

### 6.2 Il problema di sovrapposizione della classe neutra

Esempio puramente didattico `[H]`: `L0=100`, `H=110`, `L1=101.2`. Il ritracciamento definito sopra è `(110-101.2)/(110-100)=0.88`, cioè 88%, quindi rientrerebbe nel segmento 75–99%. Ma `L1 > L0`, condizione del ciclo rialzista! La fonte non definisce la precedenza né una classe esclusiva. Anche un massimo al centro potrebbe non risolvere ogni caso. Astra **non deve forzare** una classificazione mutuamente esclusiva come fatto dell'autore: mantenere i descrittori separati e `CLASS_AMBIGUOUS` quando necessario. [U]

## 7. Vincoli, significato predittivo e gestione dell'età

**[P:12]** Se un ciclo **lato indice** rompe il minimo iniziale **PRIMA della durata minima**, il PDF considera la violazione un **vincolo** capace di orientare aspettative e operatività short, con riferimento a durate minima/media/massima. La fonte non quantifica **per quanto tempo esatto** sia valida la previsione, a quali cicli il vincolo si trasferisca, quando decada e quali condizioni la invalidino. Neanche una probabilità empirica è pubblicata.

Formalizzazione **dell'evento osservabile**, non della sua conseguenza probabilistica `[F]`:

```text
INDEX_CONSTRAINT_EVENT(G, t) =
  cycle_origin_is_established(G)
  AND elapsed_valid_bars(G, t) < documented_min_bars(G)
  AND current_low(t) < origin_low(G)
```

Questa definizione presuppone un modo causale di identificare l'origine e una durata minima *applicabile al mercato specifico*. Non assumere che basti una singola rottura per autorizzare `SHORT`: il legame con timing, volumi, cicli superiori, possibili falsi segnali e costi va ancora stabilito. [U/H]

**Esempio numerico** `[F]`: per un `T-3` su S&P della tabella 15m, la soglia è **21** barre; se il minimo originario viene infranto alla barra 14 il vincolo anticipato è osservabile, **a condizione che l'origine fosse conoscibile allora**. Su BTC la guida cita **24 barre da 45m** per il minimo T-3: non applicare la soglia 21 dell'S&P; 24×45m=18 ore in mercato 24/7, ma vanno confermati ancoraggio, integrità dati e convenzione.

**Lato inverso:** una rottura anticipata del massimo d'origine è la possibile versione speculare `[F]` per uno schema `HIGH->LOW->HIGH`; non è enunciata nel PDF con un algoritmo e una previsione completa. La logica dei vincoli inversi è comunque evocata come doppio controllo [P:13].

## 8. Tempo Puro: centrale, ma non definito computazionalmente

**[P:8,10,12]** L'Analisi Evoluta dichiara di superare l'assunzione di 3–4 sottocicli fissi introducendo il Tempo Puro. Il tempo **sopra il minimo** lato indice o **sotto il massimo** lato inverso è una conferma che può far riconoscere l'inizio, impedendo di confondere una falsa partenza con un ciclo genuino. Il testo rimanda implicitamente a regole non divulgate per equivalenza con il sottociclo `G-2`.

**Non basta** leggere `time_since_low` o `age_bars`: il documento non chiarisce se le barre debbano restare interamente sopra il livello, se si azzeri il conteggio in caso di shadow wick, come si aggancino i timeframe, come venga determinato l'estremo, quando la condizione sia soddisfatta, né come si combinino durata massima e volume. Qualsiasi funzione del tipo `elapsed >= N` è un'ipotesi nuova, non il Tempo Puro originale. [U]

```text
AUTHENTIC_PURE_TIME_RULE = NOT_AVAILABLE
PERMISSIBLE_RESEARCH_OBJECT = {candidate_extreme, elapsed_time, price_persistence}
PERMISSIBLE_ACTION = record features / compare hypotheses, NOT claim original rule
```

Una fonte pubblica dell'autore, datata 24/10/2022, presenta il *Tempo Puro* come diverso dalle vecchie onde di Hurst senza pubblicarne nel testo una formula. [A; bibliografia A-04] Non si deduca dal titolo o dalla descrizione del video una definizione che non è stata verificata.

## 9. Raccordo / «Lingua di Bayer»: descrizione, appartenenza e conteggi incerti

### 9.1 Descrizione effettivamente dichiarata

**[P:10-11; V:11]** Per Marini il *Raccordo* è una **finta di partenza rialzista** seguita da discesa repentina: la sequenza sembra dare avvio a un normale ciclo, ma il movimento scende/si interrompe **prima della durata minima** del ciclo che l'operatore si attendeva. Il fenomeno viene assimilato storicamente alla *Lingua di Bayer* di Migliorino, ma la guida precisa che le denominazioni e la logica sono state evolute.

Dettagli IMPORTANTI da preservare:

- la fonte parla di un **sottociclo di tre gradi inferiori** rispetto al ciclo dopo il quale il Raccordo si manifesta;
- ipotizza che il **ciclo successivo** alla finta possa essere di tre gradi superiori; l'autore dice che questa relazione è oggetto di verifica perché non sempre è stata osservata;
- il Raccordo può **unirsi** al ciclo superiore precedente per completarne o estenderne il tempo, oppure **staccarsene**: sono citate **due tipologie**, ma le loro definizioni formali non sono pubblicate;
- viene detto che il Raccordo è calcolato attraverso una **formula collegata ai volumi**, non inclusa;
- la pagina 10 esplicita che ci sono **due definizioni di Raccordo** e che questa guida offre solo quella meno matematica. Non inventare la seconda definizione.

La regola generica `apparente breakout + immediato reversal` è insufficiente per distinguere Raccordo da ordinary failed breakout, whipsaw o ciclo fisiologicamente corto. Occorrono appartenenza strutturale, tempo, volumi e regole esatte. [U]

### 9.2 Esempio BTC di p. 11 (da non «correggere» arbitrariamente)

La pagina illustra su TradingView un grafico BTC apparentemente in barre **45m**: fra due cicli `T-1` di circa quattro giorni un **Raccordo T-4** di **12 barre**. L'autore confronta le 12 barre con **24 barre minime** del giornaliero atteso; aggiunge che non può essere parte del **precedente sesto T-3**, altrimenti il T-3 conterebbe **46 barre** contro un massimo menzionato di **44**. Il disegno evidenzia una salita iniziale, una discesa e un segmento rosso ribassista. [P:11; V:11]

**Tensione numerica e terminologica `[U]`:** in tabella S&P `T-4` ha minimo **12 barre da 15m**, `T-3` ha minimo **21** e massimo **44**; per crypto il testo dice 24 barre **45m** come minimo T-3, ma **non riporta** il suo massimo. L'esempio usa `T-4=12`, `T-3 minimo=24`, `T-3 massimo=44`, apparentemente trasferendo alcuni numeri nel contesto BTC. **Non sappiamo** se il massimo 44 venga applicato intenzionalmente al BTC, sia un'approssimazione locale, una convenzione omessa o un'incongruenza. Non dichiarare né `T-4 BTC minimo=12` universale né `T-3 BTC massimo=44` regola generale senza una fonte ulteriore. L'espressione `6'T-3` è l'etichetta dell'esempio, non prova che ogni T-1 contenga sei T-3.

**Interpretazione operativa ammissibile:** l'autore usa un *controllo di compatibilità della centratura*: per scegliere a quale ciclo appartiene un movimento breve, considera la durata del ciclo precedente e scarta un'assegnazione che lo porterebbe oltre il massimo ammesso. **Interpretazione NON ammessa:** dato un grafico con 12 barre, è sempre un Raccordo o autorizza short. [P/F]

### 9.3 Stato di riconoscimento e formalizzazione sperimentale

```text
RACCORDO_STATUS = DEFINITION_PARTIAL
AUTHENTIC_VOLUME_FORMULA = UNKNOWN
AUTHENTIC_TYPE_A/B = UNKNOWN
CANDIDATE_CHARACTERISTICS = apparent_start, reversal, sub-minimum duration,
                            disputed prior/next-cycle affiliation
```

Per ricerca `[H]`, si può costruire una classe `FALSE_START_CANDIDATE` solo **dopo** che la falsa partenza sia osservabile; si dovrà valutare se i dati disponibili *prima* della discesa fossero sufficienti a distinguerla da un autentico nuovo ciclo. Contrapporre `candidate_at` a `recognized_false_at` per non attribuire preveggenza.

## 10. Inverso, reciprocità, Cambio di Ritmo e Ciclo Motore

### 10.1 A cosa serve il lato inverso

**[P:12-14; V:13-14]** L'autore descrive i cicli inversi come **doppio controllo** della centratura dell'indice in termini soprattutto di tempo e vincoli. Un minimo origine del ciclo indice può coincidere con un massimo del ciclo inverso; la relazione speculare può valere per il massimo indice e il minimo inverso. La corrispondenza **non è garantita** sui mercati moderni e crypto, secondo la fonte.

L'illustrazione p.13 mostra un grafico Nasdaq con archi e annotazioni `T+2i`, altre etichette di grado e una scritta **«PUNTO J»** vicino a un estremo nella zona inferiore del grafico. La sua posizione visiva non fornisce l'algoritmo con cui il livello viene calcolato. La p.14 mostra un grafico dell'oro con vertici massimi/minimi collegati da frecce/segmenti gialli: illustra l'alternanza, **non** la probabilità che continui nel futuro.

### 10.2 Attenzione al significato statistico di «doppio controllo»

**[F/H]** Se indice e inverso sono **due segmentazioni della medesima serie di prezzo**, non sono due campioni indipendenti. Confrontarli può rivelare incoerenze e vincoli reciproci, ma **non raddoppia automaticamente la fiducia statistica**. Per stimare la loro utilità aggiuntiva serve una comparazione in cui la sola centratura lato indice viene confrontata con indice+inverso su dati non visti. Questa osservazione evita il falso conteggio di evidenze fortemente correlate.

La distanza temporale normalizzata tra estremi potenzialmente reciproci può essere una metrica `[H]`:

```text
alignment_distance = abs(t_index_origin_low - t_inverse_origin_high)
normalized_distance = alignment_distance / reference_duration_for_degree
```

L'esatta tolleranza di coincidenza, la definizione degli estremi associabili, lo sfasamento consentito, il riferimento di durata e il trattamento dei casi uno-a-molti **non sono nel PDF**.

### 10.3 Cambio di Ritmo e Ciclo Motore

**[P:14]** La rottura di reciprocità è associata dall'autore a un **Cambio di Ritmo**, che viene descritto come prodromico a un'inversione del trend in corso e alla **possibile** formazione di un *Ciclo Motore*. La regola di diagnosi, i gradi coinvolti, l'anticipo rispetto al turning point, i tempi e la distinzione tra inversione vera e fluttuazione non sono divulgati. Non equiparare `missing correspondence` a `sell now` o `buy now`.

```text
RHYTHM_CHANGE_CLAIM = author's qualitative association
MOTOR_CYCLE_CLAIM = possible subsequent structure
RHYTHM_CHANGE_DETECTOR = UNKNOWN
MOTOR_CYCLE_DETECTOR = UNKNOWN
PREDICTIVE_PERFORMANCE = UNKNOWN
```

## 11. Punto J e Tecniche Operative 1/2: riscontri esterni circoscritti

**[P:14; V:13]** Il Punto J serve a **controllare la centratura ciclica**; le Tecniche Operative 1 e 2 servono a operare. Nessun calcolo, ingresso, target, stop, livello di attenzione, regola di invalidazione o ordine di priorità è spiegato nel PDF.

**[A]** Ulteriori descrizioni pubbliche di Jacopo Marini su Investing.com precisano tre aspetti, **senza colmare la formula**:

- 20/02/2023, articolo/video di introduzione: il *Punto J* è un **«livello di attenzione»** per controllare se la centratura principale è corretta, potenzialmente su indici, crypto e altri asset. [A-01]
- 10/03/2023, articolo/video: l'autore parla di **distanza dal Punto J** per valutare se un'ipotesi di ritorno ai massimi di S&P 500 rimanga coerente. Ciò suggerisce che almeno in alcuni casi il concetto coinvolga un livello rispetto a cui misurare distanza del prezzo; **non dimostra formula, segno o soglia**. [A-02]
- 07/03/2023, articolo/video: l'autore riferisce che il Punto J avrebbe funzionato su DAX/MIB; è una **dichiarazione dell'autore**, non una validazione autonoma. [A-03]

**[A]** Esempi di logica operativa dichiarata pubblicamente, non norme universali:

- 18/01/2022, commento a una videoanalisi Bitcoin: l'autore riferisce che dopo la **violazione di uno swing prima delle 24 barre minime T-3** avrebbe assunto una prospettiva/operazione short, riportandone poi esito positivo. È una **singola narrazione retrospettiva**, utile a comprendere il nesso pratico swing+vincolo, non a verificare rendimento o replicare il setup completo. [A-05]
- 27/09/2022, testo su DAX/MIB: l'autore dichiara di essere **rimasto flat** in assenza di violazione swing per lo short contemplato. È un esempio della **possibilità di avere una tesi di discesa senza eseguire un trade**, non la prova che ogni swing sia sempre obbligatorio. [A-06]
- 03/03/2023, testo dell'autore su Bitcoin: invita alla prudenza perché le alternative erano numerose e suggerisce di operare solo con vincoli T-3; esemplifica il valore di `WAIT/NO_TRADE` sotto incertezza, **senza costituire una regola generalizzabile**. [A-07]

**[U]** Le pubblicazioni sono accompagnamenti testuali a video; il corpus **non pretende** di aver analizzato integralmente quei video né trascrive o ricostruisce istruzioni che potrebbero apparire al loro interno. L'unica estensione autentica attualmente sicura per Punto J è *controllo centratura / livello di attenzione / distanza dal livello*: nient'altro.

## 12. Volumi: che cosa dice il metodo e che cosa sappiamo dai mercati

### 12.1 Tesi originale vs verificabilità

**[P:6,9-11]** Secondo Marini il ruolo del volume è sostanziale: la lettura della pressione d'acquisto/vendita serve per valutare carattere e conferme del ciclo, può supplire a una conferma di swing in forte tendenza e dovrebbe aiutare a distinguere un Raccordo da una partenza valida. La guida collega questa esigenza alla presenza di HFT; attribuisce grande ruolo ai capitali che muovono mercati e strumenti.

**Non segue**, dalla formulazione, che: (a) tutte le oscillazioni T-6...T+5 siano causate da HFT, (b) sia osservabile il volume proprietario impiegato, (c) un indicatore generico come OBV/RSI/volume profile equivalga al suo calcolo, (d) più volume significhi sempre rialzo, (e) volume elevato implichi un trade. Tali implicazioni **non sono documentate**. [U/L]

### 12.2 Tipi di dati di mercato: distinguere prima di calcolare

| Oggetto | Significato misurabile | Limite per Analisi Evoluta |
|---|---|---|
| `trade_volume` | quantità effettivamente negoziata, aggregata in barra | non separa da sé lato aggressore, causa o intenzione |
| `quote_volume/notional` | controvalore, es. USDT scambiati | non coincide numericamente con volume in BTC |
| `trade_count` | numero di esecuzioni | diverso da volume; dipende da frammentazione |
| `taker_buy_volume` | quantità eseguita da compratori aggressivi | disponibile solo con labeling attendibile |
| `taker_sell_volume` | quantità eseguita da venditori aggressivi | stessa avvertenza |
| `delta` | volume aggressivo buy meno sell | flusso eseguito, NON nuove posizioni nette universali |
| `CVD` | somma cumulata dei delta | dipende dall'inizio finestra/sessione e dalla qualità dei trade |
| `order_book_depth` | liquidità visibile ai livelli | cancellazioni/spoofing e hidden liquidity la rendono incompleta |
| `order_flow_imbalance` | flusso/variazioni della domanda-offerta al book | non coincide automaticamente con il delta dei trade |
| `open_interest` | contratti derivati aperti | aumento può derivare da nuove posizioni long **e** short; non dà direzione da solo |
| `funding`, `basis`, `liquidations` | contesto derivati crypto | non compare come regola nella guida; solo contesto esterno `[H]` |
| `tick_volume` | numero di variazioni/tick in un feed | **proxy**, non volume negoziato nativo |

**[F]** Su un feed che classifica correttamente il lato aggressore di ogni trade `j`:

```text
signed_trade_quantity_j = +quantity_j se aggressor=BUY
                        = -quantity_j se aggressor=SELL
delta_bar = Σ_j signed_trade_quantity_j
cvd_t = cvd_(t-1) + delta_bar_t
```

Il CVD è sempre riferito a una **venue e convenzione di aggregazione**; riavviarlo ogni giorno o cumulandolo dall'inizio del dataset produce grafici diversi. `Zscore(volume)`, delta normalizzato, CVD, OFI, spread, depth e altre trasformazioni sono `[H]` **strumenti professionali da valutare**, non formule attribuibili a Marini.

Una definizione puramente esplorativa di *volume anomalo*, se servisse, è `z_t=(V_t-mean_past_N(V))/std_past_N(V)`; `N`, soglie, normalizzazione per ora del giorno e volume di riferimento richiedono predefinizione e prova. **Mai calibrare sulla sessione futura.**

### 12.3 Volume su un indice: specificare il mercato reale

S&P 500, Nasdaq 100, DAX e FTSE MIB sono **indici calcolati**, non order book negoziabili dell'indice stesso. Per volume/order flow è necessario scegliere un mercato di osservazione: future pertinente (es. futures azionari), ETF, somma componenti, dati del vendor o altro proxy. Due feed entrambi etichettati «S&P 500 volume» non sono necessariamente la stessa misura. Per un CFD il broker può fornire un proxy diverso dal volume di un future regolamentato. [L]

Per BTC/ETH è necessario fissare almeno `venue`, `instrument_type` (spot/perpetual/future), `symbol`, `contract_unit`, `trade_count`, `base_volume/quote_volume`, semantica di `taker`, fuso/ancora barre, calendario e qualità del feed. Nel crypto una coppia di venue può divergere in liquidità, volume e aggressor delta; non presumere un'unica «pressione BTC» direttamente osservabile. [L]

### 12.4 Contesto scientifico pertinente, senza appropriazioni

- **Blume, Easley & O'Hara (1994)**: un modello mostra che il volume può portare informazioni non deducibili dal solo prezzo. Questo motiva un test di valore **incrementale** del volume; **non valida una formula ciclica specifica**. [L-03]
- **Campbell, Grossman & Wang (1993)**: relazione tra volume e autocorrelazione dei rendimenti giornalieri nel loro campione. **Non** implica che un picco di volume predica sempre la continuazione. [L-04]
- **Conrad, Hameed & Niden (1994)**: attività di trading connessa ai pattern successivi dei rendimenti individuali, secondo asset e orizzonte. **Non** determina direzione universale o fasi T. [L-05]
- **Aquilina, Budish & O'Neill (2022)**: la concorrenza ultra-rapida e le *latency races* sono misurabili in particolari mercati; il loro contributo al volume/costi non dimostra che HFT generino i cicli nominali del PDF. [L-06]

**Test decisivo `[H]`:** confrontare previsione `[prezzo + tempo + cicli]` con `[prezzo + tempo + cicli + volume]` su periodi fuori campione. Il contributo del volume è dimostrato **solo** se migliora in modo affidabile la qualità predittiva/decisionale **dopo** aver considerato costi, complessità e tentativi multipli.

## 13. Prezzo, tempo e informazione disponibili realmente: principi di causalità

### 13.1 Causalità del riconoscimento

La figura di un ciclo può mostrare l'arco che parte da un minimo che nessun operatore poteva sapere fosse definitivo sul momento. Bisogna separare:

```text
origin_event_at       = timestamp del minimo/massimo attribuito a origine
candidate_observed_at = primo timestamp in cui è nato il sospetto
confirmation_at       = timestamp in cui una REGOLA ESPLICITA permette conferma
forecast_issued_at    = timestamp in cui la tesi viene registrata
first_actionable_at   = primo momento successivo, con prezzi realisticamente osservabili
```

Vincolo di qualità `[H]`:

```text
forecast_issued_at >= data_available_at
if setup depends on confirmed cycle:
    forecast_issued_at >= confirmation_at
```

Un test che registra LONG al minimo storico di origine e calcola profitto da quel minimo **mentre la conferma arriva dopo** è invalido per look-ahead. Anche un pivot con `k` barre a destra è riconoscibile **solo dopo** quelle barre; non si può usare il timestamp del centro pivot come timestamp della decisione.

### 13.2 Informazioni temporali diverse

- `event_time`: timestamp dell'evento sulla venue, in UTC.
- `receive_time`: quando il sistema riceve il dato, possibilmente con latenza.
- `bar_open` e `bar_close`: estremi temporali della candela; una barra non chiusa ha high, low e volume ancora mutevoli.
- `data_cutoff_at`: ultimo dato che ha contribuito alla previsione.
- `session_id/market_calendar`: necessario per mercati a orario limitato e giornalieri.

**[H]** Le decisioni bar-based vanno giudicate sulla **barra conclusa** e non su high/low finale di una barra ancora in formazione. Se si usano tick o eventi intrabar, rendere esplicito l'ordine temporale, la copertura e la validità dei dati.

### 13.3 Ragioni per cui si sbaglia una centratura pur «seguendo il PDF»

1. Un estremo scelto ex post viene attribuito all'inizio in anticipo rispetto alla conoscenza reale.
2. Si usa la banda di barre da 15m di S&P su barre da 45m di BTC senza giustificazione.
3. Si confonde un giorno di calendario con una sessione.
4. Si riconoscono come confermati un `G-2` o `G-3` ancora non identificabili causalmente.
5. Si sceglie retrospettivamente un segnale swing più conveniente fra più candidati.
6. Si «ripara» la centratura per rispettare la tabella dei massimi dopo aver visto il futuro.
7. Si considerano indice e inverso prove indipendenti pur essendo trasformazioni dello stesso prezzo.
8. Si usa volume spot di una venue con prezzo perpetual di un'altra senza misura del disallineamento.
9. Si presume che la mancanza di Tempo Puro significhi sempre Raccordo anziché soltanto *rischio di Raccordo*.
10. Si attribuisce a Marini una formula inventata per completare le lacune.

## 14. Registro visivo del PDF, completo pagina per pagina

Le figure sono state interpretate dal documento originale. Le descrizioni seguenti sono **parafrasi dell'informazione grafica**: non contengono coordinate numeriche fittizie né timestamp di trade inventati.

| Pagina | Contenuto e lettura corretta | Cosa NON prova |
|---|---|---|
| 1 | Copertina con candele e presentazione della guida | nessuna regola di entrata |
| 2 | Presentazione gruppo Premium, video, discussione, disciplina della pazienza | nessuna formula |
| 3 | Schermata canali Discord Europa/USA/crypto/commodity e invito abbonamento | nessuna evidenza tecnica |
| 4 | Definizione, gerarchia e scala temporale narrate | non conferma numeri della tabella successiva per ogni venue |
| 5 | DAX: archi arancioni associati a molte onde T-3 lato indice, da minimo a minimo con massimo interno | niente prova di rilevabilità ex ante dei minimi |
| 6 | Regole testuali di avvio/chiusura e ruolo swing-volume | non fornisce le formule mancanti |
| 7 | S&P 500: figura superiore con cicli rialzisti; inferiore con cicli ribassisti; archi evidenziano andamento e collocazione del massimo | gli archi non sono previsioni datate |
| 8 | S&P 500: figura di ciclo neutro, distinta narrativamente con ritracciamento 75–99%; testo sui sei sottocicli e Tempo Puro | la formula dei ritracciamenti resta incerta |
| 9 | Tabella giallo/verde/rosso di min/media/max; 15m per gradi brevi, giorni per lunghi; varianti MIB e crypto | non fornisce l'intera tabella BTC né T-1 |
| 10 | Definizione dei tre fattori, pressione volumetrica, Tempo Puro e tipologie di Raccordo | non fornisce formula volumetrica né logica completa |
| 11 | BTC TradingView 45m: piccola falsa partenza, inversione, frecce/arco e riquadro ribasso; Raccordo T-4 fra T-1 | non è prova predittiva, né statistica sul tasso dei raccordi |
| 12 | Testo sui vincoli, T-3, reciprocità non sempre valida | non fornisce la scadenza esatta del vincolo |
| 13 | Nasdaq: archi inversi T+2i di massimo a massimo; più gradi e un'etichetta *PUNTO J* sul grafico | non rivela il calcolo di Punto J |
| 14 | Oro futures: alternanza di swing massimi/minimi evidenziati in giallo; testo su rottura reciprocità | non certifica il Cambio di Ritmo prima del reversal |
| 15 | Conclusioni dell'autore e avvertenze educative/rischi; cenno alla futura parte 2 | non è audit di risultati |
| 16 | Copyright | nessuna regola metodologica |

**Nota critica sulle immagini:** se una figura dispone contemporaneamente di linee/archetti, indicatori in pannelli separati, etichette temporali e una scelta del minimo come origine, non possiamo dedurre quale componente abbia causato l'annotazione. Il PDF non fornisce dataset originali, timestamp delle analisi prima della candela futura, impostazioni complete degli indicatori e criteri di conferma. Per una replica non bisogna «allenarsi sul disegno finale» come se fosse un segnale.

## 15. Formalizzazione che Astra può **valutare**, senza spacciarla per originale

L'applicazione del nucleo documentato richiede definizioni di mercato, dati, regole causali e comportamento in caso d'incertezza. Questa sezione è una **specifica candidata di ricerca** `[H]`, non le Tecniche Operative 1/2 di Jacopo Marini. Nessuna delle scelte implementative seguenti è automaticamente approvata per il progetto.

### 15.1 Scomporre il problema correttamente

```text
Market data / provenance
  -> observed price, volume, time, data-quality state
  -> cycle-centering hypotheses (index + inverse + grades)
  -> cycle evidence and contradictions
  -> market view + predictions + invalidation
  -> trade-opportunity assessment (LONG / SHORT / NO_TRADE)
  -> immutable forecast, replay and verification
```

Non inserirvi come dipendenza obbligatoria un *broker execution engine*: il compito del trader del progetto è **leggere il mercato e consigliare**; size, leva, ordini e reale esecuzione appartengono all'umano e a un'eventuale decisione progettuale futura esplicita. Il dossier di ricerca includeva un'architettura di broker e sizing come esercizio generale: **non trasferirla automaticamente** nei requisiti del prodotto.

### 15.2 Oggetto `CycleHypothesis` [H]

Un grado può avere più centrature candidate senza falsamente imporre un pivot «certo»:

```yaml
CycleHypothesis:
  instrument: string
  data_source: string
  degree: "T-6|T-5|T-4|T-3|T-2|T-1|T|T+1|T+2|T+3|T+4|T+5"
  side: "INDEX|INVERSE"
  state: "SEARCH|ORIGIN_CANDIDATE|START_PROVISIONAL|START_CONFIRMED|MATURING|CLOSING_CANDIDATE|CLOSED_CONFIRMED|INVALID|UNRESOLVED"
  origin_effective_at: timestamp_or_null
  origin_first_observed_at: timestamp_or_null
  origin_price: number_or_null
  start_confirmed_at: timestamp_or_null
  last_assessed_at: timestamp
  age_in_eligible_bars: integer_or_null
  elapsed_wall_time: duration_or_null
  duration_basis: "15m_sessions|45m_continuous|days_UNDEFINED|other_explicit"
  min_duration: number_or_null
  mean_duration: number_or_null
  max_duration: number_or_null
  extreme_so_far: number_or_null
  lower_minus_2_observation: "BULL|NEUTRAL|BEAR|AMBIGUOUS|UNKNOWN"
  lower_minus_3_observation: "BULL|NEUTRAL|BEAR|AMBIGUOUS|UNKNOWN"
  swing: "TRIGGERED|NOT_TRIGGERED|UNKNOWN|NOT_APPLICABLE"
  pure_time: "UNKNOWN_PROPRIETARY|RESEARCH_PROXY|DOCUMENTED_CONFIRMED"
  volume: "AVAILABLE_NOT_AUTHENTIC|MISSING|RESEARCH_PROXY|DOCUMENTED_CONFIRMED"
  constraint: "TRIGGERED|NOT_TRIGGERED|UNKNOWN"
  inverse_alignment: "CONSISTENT|DIVERGENT|UNRESOLVED"
  form_descriptors: {peak_location: null, retracement: null, terminal_return: null}
  hypotheses_and_contradictions: []
  confidence_basis: "descriptive; statistical calibration required"
  origin_and_rule_provenance: []
```

Gli stati `START_CONFIRMED` e `DOCUMENTED_CONFIRMED` **non possono essere assegnati nel nome dell'Analisi Evoluta originale** se sono assenti le regole proprietarie. Si può chiamare `EXPERIMENTAL_RULE_CONFIRMED` per risultati di una definizione autonoma, tracciandone versione, evidenze e parametri. Evitare di riempire `confidence=90%` senza calibration set.

### 15.3 Macchina a stati in stream [H]

```text
all'arrivo di un dato validato al tempo t:
  1) valida feed, ordine cronologico, chiusura barre e sessione;
  2) aggiorna osservazioni di prezzo/volume e gradi disponibili;
  3) registra eventuali nuovi estremi candidati, SENZA retrodatare conferme;
  4) per ogni grado/side conserva più centrature concorrenti se necessario;
  5) per ogni ipotesi calcola età nel calendario appropriato;
  6) osserva struttura G-2 (possibile avvio) e G-3 (possibile fine);
  7) valuta swing, tempo, volume SOLO con regole esplicite e tracciate;
  8) osserva vincoli temporali e coerenza della coppia indice/inverso;
  9) classifica forma/fase come PROVVISORIA finché non confermata;
 10) registra revisioni e motivazioni, mantenendo le previsioni precedenti;
 11) produce una market view anche quando nessun trade è giustificato;
 12) pubblica forecast/decision basati SOLO su osservazioni disponibili entro t.
```

Un candidato non deve essere cancellato silenziosamente quando fallisce: conservarne origini, data di falsificazione e impatto sulla previsione. Non usare all'indietro la centratura «vincitrice» per ricalcolare previsioni passate.

### 15.4 Swing: possibili rappresentazioni esterne, non authentic AE [H]

| Famiglia | Definizione causale indicativa | Distorsione/limite |
|---|---|---|
| massimo rolling precedente | `close_t > max(high_{t-N},...,high_{t-1})` | non è necessariamente swing *di pertinenza* |
| pivot locale con conferma a destra | massimo bar `i` riconosciuto solo in `i+k` | ritardo obbligatorio, problema dei pareggi |
| reversal di ampiezza rispetto ad ATR | pivot confermato dopo variazione `q*ATR` | parametri e ATR adattivo non attribuiti a Marini |
| struttura multi-grado | swing scelto dalla centratura dei figli | pericolo di circolarità: il figlio va prima definito causalmente |

La scelta tra queste famiglie richiede una **domanda verificabile** e un test preregistrato. Non trasformare la matrice in 500 combinazioni ottimizzate sul PnL.

### 15.5 Tempo Puro e volume: interfacce intenzionalmente incomplete [H/U]

```python
# PSEUDOCODICE DI CONTRATTO, NON ALGORITMO DEL METODO

def authentic_swing_of_relevance(market, degree, as_of):
    raise NotImplementedError("[U] formula/pertinenza non disponibile")

def authentic_pure_time(market, degree, side, as_of):
    raise NotImplementedError("[U] durata/criterio non disponibile")

def authentic_volume_confirmation(market, degree, side, as_of):
    raise NotImplementedError("[U] feature e soglie non pubblicate")

def authentic_raccordo(market, degree, side, as_of):
    raise NotImplementedError("[U] formula volumetrica e due tipologie ignote")

def authentic_point_j(market, degree, side, as_of):
    raise NotImplementedError("[U] calcolo e regole ignoti")
```

La funzione `research_proxy_*` eventualmente sviluppata deve chiamarsi **diversamente**, essere versionata e accompagnata dall'avvertenza `NOT_AUTHENTIC_ANALISI_EVOLUTA`.

## 16. Cosa il trader deve capire e poter prevedere

### 16.1 Separare comprensione del mercato e scelta di un'operazione

**Market view**: qual è la lettura ciclica ora, quali gradi sembrano iniziare/maturare/chiudere, quali estremi e vincoli sono osservabili, quale direzione/ampiezza/tempo dei movimenti appare plausibile, quali scenari alternativi, quanto reggono dati e indicatori, che cosa falsificherebbe la lettura.

**Trade decision**: dato ciò che si prevede, **esiste un'occasione realmente attraente e verificabile** da segnalare LONG o SHORT? NO_TRADE può dipendere da tesi poco robusta, movimento residuo piccolo, timing già sfavorevole, costo/volatilità/liquidità, conflitto tra gradi, incertezza su Raccordo, vicinanza a vincoli contrari oppure regole originali mancanti.

Non bisogna chiedere al motore «se il ciclo è rialzista allora LONG»: un ciclo può essere nominalmente rialzista ma già vicino al suo massimo o alla chiusura; l'azione corrente può quindi essere NO_TRADE, addirittura la preparazione condizionale a una correzione. Analogamente un vincolo ribassista non equivale a uno short immediato a qualunque prezzo.

### 16.2 Forma desiderabile di un bollettino di mercato [H]

```yaml
as_of: "timestamp UTC reale"
instrument: "nome e venue espliciti"
data_quality: "CLEAN|PARTIAL|STALE|GAP|UNVERIFIED"
method_basis: "AE-documentato|AE-ispirato-sperimentale|non determinabile"
market_view:
  dominant_direction: "UP|DOWN|SIDEWAYS|MIXED|UNCERTAIN"
  dominant_cycle_grade: "grado o UNKNOWN"
  cycle_phase: "early|middle|late|candidate_closing|uncertain"
  lower_cycle_evidence: []
  higher_cycle_evidence: []
  inverse_reciprocity_evidence: []
  volume_evidence: "misure, fonte, eventuale NON-AUTHENTIC"
  constraints: []
  active_hypotheses: []
  conflicting_evidence: []
forecast:
  horizon: "intervallo esplicito, con convenzione temporale"
  direction: "UP|DOWN|SIDEWAYS|UNCERTAIN"
  price_scenario: "range condizionale o UNKNOWN"
  target_basis: "regola esplicita o UNKNOWN"
  conditions: []
  invalidation_price_or_event: "valore se giustificato, altrimenti UNKNOWN"
  alternative_scenarios: []
  uncertainty: "calibrata empiricamente oppure qualitativa motivata"
decision:
  action: "LONG|SHORT|NO_TRADE"
  rationale: []
  trigger_to_reassess: []
  no_trade_does_not_erase_forecast: true
provenance:
  latest_data_cutoff: timestamp
  original_vs_experimental_rules: []
  model_and_data_versions: []
```

**Target**: la guida non fornisce la formula per proiettare un prezzo-obiettivo. Astra può prevedere *un orizzonte temporale di fase* se le durate sono applicabili; **non può inferire automaticamente un target numerico**, né una stop distance, dalle sole bande cicliche. Un target quantitativo necessita una regola **esplicitamente esterna `[H]`**, documentata e con prestazioni testate. Non generare target con falsa precisione perché l'utente desidera che ci siano.

### 16.3 Esempi di ragionamento corretti

**Esempio A — previsione DOWN, decisione NO_TRADE `[H]`.** Il motore vede una centratura che suggerisce conclusione imminente di un grado superiore e pressione verso il basso. Tuttavia il minimo è già vicino, un grado inferiore ha avviato un recupero, la tendenza volumetrica non è interpretabile con formula originale e uno short ora avrebbe scarso margine. Pubblicazione: `VIEW=DOWN_BIASED`, `FORECAST=possible terminal downswing`, `DECISION=NO_TRADE`, con condizioni che cambierebbero la valutazione. Non dire `NO_TRADE perché non capisco nulla`.

**Esempio B — evento vincolo `[P/F]`.** Un T-3 su crypto ha origine confermata e rompe il minimo originario prima del limite illustrativo 24×45m. Si registra `bearish_constraint_observed`, si alza il peso della prosecuzione ribassista come **tesi del metodo**, ma restano sconosciute la durata probabilistica residua, lo swing pertinente, la formula volume e l'occasione operativa. Non promuovere automaticamente `SHORT` alla notizia del vincolo.

**Esempio C — interpretazione biforcata `[H]`.** Un `G-2` sembra laterale/rialzista ma lo swing pertinente non è definibile con certezza e l'inverso sembra sfasato. In assenza di Tempo Puro verificabile, registrare `NEW_CYCLE_POSSIBLE` e `RACCORDO_RISK_UNQUANTIFIED`, non `NEW_CYCLE_CONFIRMED`. Si possono descrivere scenari condizionali di rialzo o falsa partenza, senza inventare probabilità.

**Esempio D — Punto J `[A/U]`.** Su un grafico un autore indica un Punto J come soglia di attenzione. Senza la formula non si può ricalcolare il suo livello su altri dati: `PUNTO_J=UNKNOWN`; mai fare finta di averlo derivato da Fibonacci, ATR o pivot standard.

### 16.4 Da conoscenza a traduzione tecnica: livello di verità dichiarato

Una prima implementazione può essere **AE-INSPIRED RESEARCH ENGINE**, cioè un sistema che apprende dal PDF a mantenere ipotesi cicliche e valuta, sperimentalmente, sottocicli/vincoli/volumi. Non deve chiamarsi **replica del metodo di Marini** se non si dispone di regole complete con conferma dell'autore o evidenza equivalente documentale. Sottolineare questa differenza anche nei report di replay e nella UX.

## 17. Dati minimi e igiene quantitativa

**[H/L]** Per studiare il contenuto della guida, almeno OHLCV con timestamp corretti, mercato identificato, calendario di negoziazione, barre chiuse, metadata di provenienza e data quality. Se si prova a capire il ruolo del volume aggressivo occorre accesso ai **singoli trade con labeling verificabile**, non semplicemente supporre che la candela verde indichi taker buy. Per OFI/imbalance servono messaggi/order book idonei, non un volume a barre.

**Principi non negoziabili di buona ricerca:**

1. Normalizzare internamente timestamp in UTC; conservare timezone originale, sessione e aggancio delle candele; includere DST sui mercati tradizionali.
2. Dichiarare **esattamente** quali contratti/venue generano prezzo e volume, inclusi roll futures e cambi di simbolo.
3. Non interpolare volume mancante come volume reale zero. Marcare gap, dati corrotti, disconnessioni e allineamento prezzo-volume.
4. Per crypto 45m, conservare anchor (es. una convenzione UTC fissata **solo dopo verifica**), senza assumere equivalenza fra provider.
5. Per future distinguere prezzo spot/indice continuo/back-adjusted/contratto reale; un prezzo *back-adjusted* non è un prezzo eseguibile.
6. Non utilizzare nel segnale rolling mean o normalization calcolate sui dati successivi; distinguere valori provvisori e consolidati.
7. Registrare tutte le decisioni ex ante con snapshot immutabili e data cut-off; lasciare visibile una tesi anche quando poi viene invalidata.
8. Testare il comportamento in mercati con volatilità, liquidità, frequenza e sessioni differenti; un risultato S&P 500 15m non si trasferisce automaticamente a BTC 45m.
9. Distinguere studi *osservazionali* (quanto la forma riconosciuta rispetta le tabelle) da studi *predittivi* (che cosa era possibile sapere prima dell'esito) e da simulazioni economiche con costi.
10. Sulle granularità alte considerare microstructure noise, bid-ask bounce, incompletezza book e timestamp venue, evitando di scambiare rumore per ciclo.

### 17.1 Dataset requisiti specifici per la guida

| Studio | Requisiti | Qualità del risultato |
|---|---|---|
| geometria cicli | OHLC, calendari, gradi, annotazioni causali | distribuzioni età/forma; no edge implicito |
| start G/G-2 | OHLC, criteri swing/proxy, timeline conferme | lead/lag e precisione ex ante |
| end G/G-3 | OHLC e timeline di classificazione figli | capacità di prevedere chiusura, non arco ex post |
| vincoli | origine confermata, minima per asset, low/high intrabar affidabili | esiti condizionali per orizzonte |
| volume incrementale | trade volume valido o signed trades; stessa venue | prestazioni aggiuntive rispetto a prezzo+tempo |
| reciprocità | doppia centratura *causale* stesso dato | valore aggiunto al modello base, senza doppio conteggio |
| raccordi | annotazioni di false start, estremi e decisioni disponibili allora | precision/recall e timing; formula AE non riprodotta |
| utilità operativa | previsioni, target/invalidazioni, costi/proxy eseguibilità | valore economico potenziale, **non trade live** |

## 18. Protocollo per falsificare il metodo senza trasformarlo in una «caccia agli indicatori»

### 18.1 Problema vero

Il progetto non deve cercare centinaia di segnali da backtestare a caso: **la domanda** è se l'insieme di osservazioni professionali descritto dall'Analisi Evoluta possa essere tradotto in una lettura **anticipatoria, ripetibile e utile**. La ricerca verifica se l'interpretazione sia corretta e se il contesto composto migliori rispetto a alternative realistiche.

### 18.2 Formalizzare PRIMA del test

Per ogni ipotesi fissare `market`, `venue`, `degree`, `calendar`, `input data`, `as-of logic`, `definition of event`, `forecast horizon`, `target event/return`, `comparison`, `cost assumptions`, `max candidate variants`, `train/validation/test`, `failure interpretation`. Una previsione di ciclo rialzista non è la stessa cosa che prevedere il segno del prossimo singolo bar; scegliere un orizzonte coerente **prima** di misurare l'accuratezza.

### 18.3 Confronti scientifici minimi utili [H]

| Confronto | Domanda | Avvertenza |
|---|---|---|
| centratore vs pivot di riferimento | la gerarchia riconosce struttura senza ricostruzioni retroattive? | verifica causale, non bellezza grafica |
| modello prezzo vs prezzo+tempo | le bande min/med/max contengono informazioni aggiuntive? | niente scelta posteriori di origini |
| prezzo+tempo vs +struttura G-2/G-3 | la logica multi-grado migliora la previsione? | lag e classificazione figli contabilizzati |
| prezzo+tempo+gradi vs +volume | il volume aggiunge informazione predittiva? | stessa finestra OOS e costo dato |
| indice solo vs indice+inverso | lo schema inverso corregge davvero errori di centratura? | non presumere indipendenza |
| vincolo prima del minimo vs controllo adatto | la rottura anticipata predice continuazione meglio di una normale rottura? | confrontare anche rotture senza età ciclica |
| raccordo proxy vs breakout failed ordinario | il concetto di Raccordo ha vantaggio classificatorio/pratico? | senza formula originale studiamo **solo proxy** |

**Baseline importanti:** trend/momentum prezzo, breakout semplice, movimento non condizionato, distribuzione dei rendimenti nel regime comparabile, centratura alternativa causale. Le differenze vanno valutate a uguale momento di informazione e simile frequenza/selezione; non «battere» una baseline volutamente scadente.

### 18.4 Metriche separate per osservazione, previsione, decisione

**Centratura**: durata empirica, coverage bande `Dmin≤D≤Dmax`, frequenza overrun e undercut, ritardo conferma, revisioni della centratura, consistenza tra gradi, accordo indipendente delle annotazioni esperte.

**Previsione**: direzione/ampiezza/tempo `predicted_at` contro futuro effettivo, Brier/calibrazione se si producono probabilità, log-loss ove appropriata, MAE per target quantitativi, precision/recall per turning events, probabilità condizionate vs base rate, distribuzione di errori secondo regime e orizzonte.

**Decisione**: opportunità selezionate, frequenza NO_TRADE, falso positivo delle occasioni, rendimento potenziale netto al trade simulato solo se l'eseguibilità è definita, adverse/favorable excursion e costi. `NO_TRADE` non va valutato come «previsione mancata» se il sistema ha pubblicato una previsione: valutare separatamente entrambe.

### 18.5 Controlli contro le illusioni statistiche

- **Leakage:** stop immediato dell'interpretazione se un feature usa informazione futura. Analizzare timestamp **di conferma**, non solo l'evento visivo.
- **Data snooping:** registrare quante varianti sono state provate; un risultato di una su mille non è prova senza correzione.
- **Out-of-sample:** dati successivi mai usati per rifare parametri; ripetizione in diversi regimi.
- **Ablation:** misurare il contributo reale di ogni famiglia di osservazioni; il pacchetto completo non deve essere accettato se una baseline semplice spiega tutto.
- **Parameter sensitivity:** preferire regioni ampie di prestazione coerente, non un unico picco numerico.
- **Cost/latency stress:** spread, commissioni, slippage, funding e ritardo di pubblicazione possono annullare l'utilità di una tesi corretta.
- **Selection/reporting:** conservare fallimenti, episodi indecisi, timestamp assenti e tutte le ipotesi scartate; non riportare soltanto i grafici che «funzionavano».
- **Performance del metodo di Marini:** articoli/video e recensioni sono **affermazioni non confrontabili con un audit di previsioni timestampate ed esiti indipendenti**.

**Letteratura**: Brock, Lakonishok & LeBaron (1992) documentano risultati di regole tecniche in un campione storico specifico; Sullivan, Timmermann & White (1999) mostrano i rischi del *data snooping*; Bailey e López de Prado studiano il *Deflated Sharpe Ratio* (2014). Queste fonti motivano il controllo scientifico, **non la scelta di una strategia specifica**. [L-07,L-08,L-09]

### 18.6 Ipotesi di ricerca — registro con confidenza e blocchi

| ID | Proposizione ispirata alla guida | Definizione/trasferibilità | Stato |
|---|---|---|---|
| AE-H01 | i cicli T tendono a durate comprese nelle bande indicate | tabella applicabile solo a mercati/unità dichiarate | [P] enunciata, efficacia non testata |
| AE-H02 | la forma ciclica ha potere descrittivo e anticipatorio | classificazione rialzista/neutra/ribassista | [P] forma, [U] riconoscimento ex ante |
| AE-H03 | `G-2` rialzista/neutro facilita start di `G` | struttura figlio, latenza classificazione | [P] schema; [U] regola causale |
| AE-H04 | `G-3` ribassista chiude `G` | relazione necessaria/sufficiente | [P] enunciato; [U] timing esatto |
| AE-H05 | swing di pertinenza conferma start | quale estremo/superamento | [P] enunciato; [U] formula |
| AE-H06 | Tempo Puro sopra minimo/sotto massimo dà conferma | regola proprietaria | **[U] BLOCKER** |
| AE-H07 | volume aggiunge capacità di distinguere fase/forme | quale feed, variabile, trasformazione | [P] tesi; [L] motivo generale; [U] formula |
| AE-H08 | rottura precoce dell'origine crea vincolo direzionale | minima corretta, base rate, orizzonte | [P] testabile dopo centratura |
| AE-H09 | la reciprocità migliora controllo centratura | indice e inverso sullo stesso prezzo | [P] funzione; [U] tolleranza |
| AE-H10 | rottura reciprocità anticipa cambio di ritmo | criterio, orizzonte, trade | [P] tesi; **[U] BLOCKER** |
| AE-H11 | raccordi segnalano falsi start | due forme e formula volume non note | [P] descrizione; **[U] BLOCKER** |
| AE-H12 | il Punto J aiuta controllo/livelli | livello di attenzione, distanza | [P,A] funzione; **[U] BLOCKER** |
| AE-H13 | Tecniche 1/2 producono ingressi/trade | nessun dettaglio pubblicato | **[U] BLOCKER** |
| AE-H14 | bull tende ad allungare cicli, crash accorcia | condizionalità di regime | [P] tesi, formula [U] |
| AE-H15 | un'implementazione semplificata conserva valore | differenza tra replica e motore ispirato | **[H] domanda di prodotto/ricerca** |

## 19. Lacune prioritarie: domande che davvero servono alla replica

Per chi possiede altre fonti autentiche (guida successiva, manuali, lezioni pubblicamente accessibili o appunti autorizzati) le domande sono **specifiche**. Non dedurne la risposta dai titoli.

| Priorità | Domanda al titolare del metodo / evidenza da recuperare | Impatto |
|---|---|---|
| BLOCCANTE | Qual è la formula esatta del **Tempo Puro**, inclusi reset, unità, barre non concluse e sostituzione `G-2`? | nessuno start autentico completo |
| BLOCCANTE | Come si determina *lo swing di pertinenza* nei vari gradi, e qual è il trigger verificabile? | nessuna conferma prezzo fedele |
| BLOCCANTE | Quali indicatori/serie, lookback, normalizzazioni e soglie definiscono la **Tendenza Volumetrica**? | componente centrale non replicabile |
| BLOCCANTE | Qual è la **formula volumetrica del Raccordo** e quali sono esattamente le sue due tipologie? | impossibile distinguere false partenze in modo autentico |
| BLOCCANTE | Che cosa sono esattamente **Tecnica Operativa 1 e 2**: condizioni di mercato, ingresso, target, uscita e invalidazione? | impossibile replicare trading autentico |
| BLOCCANTE | Come si determina il **Punto J**, come cambia con l'età e che significa la sua distanza? | doppio controllo incompleto |
| ALTA | Qual è la condizione algoritmica di **Cambio di Ritmo** e di **Ciclo Motore**? | cambio regime/inversione indisponibili |
| ALTA | `G-2` per lo start / `G-3` per la fine devono essere **chiusi**, riconosciuti, in corso o soltanto confermati? | grave rischio look-ahead |
| ALTA | Come classificare **neutro** rispetto a **rialzista**, definendo ritracciamento e precedenza? | contraddizione classificatoria |
| ALTA | Come si attribuisce un Raccordo al ciclo precedente: si unisce, estende o resta staccato? | centratura fragile |
| ALTA | Come si spiegano le **12/24/44/46 barre BTC** dell'esempio p.11 e le sue unità? | tabelle crypto non complete |
| ALTA | Qual è il calendario per giorni di T/T+ e sessioni 15m/45m, inclusi overnight, DST, exchange e anchor? | età temporali non affidabili |
| ALTA | Quale feed è usato per i volumi degli indici e di BTC/ETH? Quale strumento ha prodotto i grafici? | potenziale cambio di significato delle feature |
| ALTA | Quanto è forte un vincolo? Come deriva la scadenza minima/media/massima di una discesa? | non si ricava timing operativo |
| MEDIA | Cosa succede dopo durata massima, con cicli senza swing visibile, o con più origini alternative? | logica recovery non definita |
| MEDIA | Quali tolleranze temporal-prezzo definiscono la reciprocità fra gradi? | doppio controllo non deterministico |
| MEDIA | Sono disponibili **previsioni originali timestampate prima degli esiti** e un archivio completo, incluse quelle sbagliate? | impossibile misurare edge autentico |

**Non presentare** le domande su leva/sizing/capitale come blocchi per la *lettura* del mercato: nella configurazione del progetto sono responsabilità esterne al trader analitico. Le lacune **realmente bloccanti** per l'obiettivo di produrre consigli LONG/SHORT fedeli sono la formalizzazione di start/finish/falsi start/Punto J e le **Tecniche Operative** originali; le altre sono importanti per qualità e validazione.

## 20. Verifica dei riferimenti storici e delle affermazioni forti

### 20.1 Hurst, Migliorino, Gann: che cosa è trasferibile

**Hurst [L-01]**: il libro del 1970 documenta una tradizione di modello ciclico, filtri e strumenti di analisi temporale. Questa genealogia può aiutare a capire i concetti *wave*, *nominal cycles*, *valid trend lines* e *componenti multiple*, ma il PDF dichiara di essersi **allontanato dalle onde fisse**; inserire direttamente formule di Hurst come Tempo Puro o Raccordo Evoluta sarebbe errato.

**Migliorino [L-02]**: il libro del 2006 *Il trading con le Lingue di Bayer* fornisce il nesso lessicale; l'indice mostrato dal **catalogo ufficiale Borsari** comprende voci su difesa dalle lingue, stop spazio-temporali, rotture e anche **«I volumi nelle Lingue di Ba...»** (titolo troncato nella scheda web). Pertanto **non è corretto generalizzare** che Migliorino non parlasse mai di volumi. La p.11 della guida Marini sostiene che la propria formula volumetrica per le finte è assente dagli scritti precedenti; tale formula può ben essere nuova **senza** che i predecessori ignorassero totalmente il volume. Questa lettura evita una falsa genealogia. Non avendo letto integralmente il libro Migliorino in questa consegna, non attribuirgli una formula specifica o un capitolo oltre la voce verificabile del catalogo.

**Gann [P:14]**: solo citazione quale tradizione di partenza; **nessun elemento operativo specifico** trasferibile in modo fedele dalla sola guida. Ogni connessione più precisa richiederebbe una fonte primaria del metodo che la stabilisca.

### 20.2 I mercati non provano la causalità per decreto

L'affermazione `[P:10]` che «i volumi, soprattutto da HFT, fanno muovere i cicli» va trattata come **ipotesi esplicativa dell'autore**, non come conclusione empirica generale. La ricerca sull'HFT [L-06,L-10] documenta impatti sulla formazione dei prezzi, concorrenza e liquidità **in specifici campioni**. Il livello di prova è diverso da dimostrare (a) una periodicità ricorrente in tutti gli asset, (b) gradi T numericamente stabili o (c) un algoritmo originale per prevedere minimi.

### 20.3 Ciclicità non implica edge economico

La comparsa di pattern riconoscibili su un grafico **non basta** a prevedere il futuro. Finestre sovrapposte, serial correlation, selection bias, periodi senza eventi e scelta retrospettiva degli estremi possono creare apparente periodicità. Gli strumenti multi-scala (wavelet, filtri, decomposizioni) sono confronti utili ma **non una prova matematica** dell'esistenza di un clock deterministico di mercato. La validità delle durate della p.9 è una domanda empirica per mercato, periodo e algoritmo di identificazione.

## 21. Bibliografia verificabile e natura dell'evidenza

Questi riferimenti sono **link esterni stabili** o titoli identificati con date; non sostituiscono il corpus allegato. **Non usare numeri di citazione interni alla Deep Research come URL:** quei marcatori non sono portabili in un Markdown esportato. Le referenze `[A-..]` e `[L-..]` qui sotto sono la chiave bibliografica di questo file.

### 21.1 Fonte primaria del metodo

- **[P-01]** Jacopo Marini, *Guida pratica per comprendere l'Analisi Evoluta e conoscere il gruppo Premium dei trader*, copyright ©2023, **16 pagine**, PDF consegnato dall'utente, nome file `Analisi Evoluta.pdf`. **Fonte diretta determinante** per gerarchia, tabelle, forma, vincoli, avvio/chiusura, tempo, volume, raccordo, inverso e terminologia. Cita nel testo `[P:pagina]`.
- **[DR-01]** *Deep Research sull'“Analisi Evoluta”: fondamenti, evidenza, formalizzazione quantitativa e architettura per Astra*, report ricevuto dal committente, `deep-research-report.md`. **Fonte secondaria di approfondimento**: molte sue formule/proposte sono esplicitamente sperimentali, non di Marini; il report include anche aspetti di broker/sizing/live che **non** rientrano automaticamente nello scopo del progetto.

### 21.2 Ulteriori fonti primarie PUBBLICHE dell'autore

- **[A-01]** Jacopo Marini, 20/02/2023, *S&P500 — Introduciamo il «Punto J»*, Investing.com: https://it.investing.com/analysis/sp500--analisi-evoluta-del-180223--introduciamo-il-punto-j-200460297 — dal **testo associato** risulta la definizione *livello di attenzione per la centratura*, non l'algoritmo.
- **[A-02]** Jacopo Marini, 10/03/2023, *S&P500 — L'importanza del Punto J*, Investing.com: https://it.investing.com/analysis/sp500--analisi-evoluta-del-90323--limportanza-del-punto-j-dellevoluta-200460788 — menziona **distanza dal livello**; non formula.
- **[A-03]** Jacopo Marini, 07/03/2023, *DAX e MIB — Il Punto J ha funzionato bene*, Investing.com: https://it.investing.com/analysis/dax-e-mib--analisi-evoluta-di-mart-70323--il-punto-j-ha-funzionato-bene-200460703 — resoconto auto-dichiarato, non studio.
- **[A-04]** Jacopo Marini, 24/10/2022, *Bitcoin — Rialzo arrivato nel tempo dato*, Investing.com: https://it.investing.com/analysis/bitcoin--analisi-evoluta-di-lun-2410--rialzo-arrivato-nel-tempo-dato-perfect-200457733 — nel testo afferma che Tempo Puro è diverso dalla ciclica classica; niente formula verificata.
- **[A-05]** Jacopo Marini, 18/01/2022, *Bitcoin — Night Session del 17/01/2022*, Investing.com: https://it.investing.com/analysis/bitcoin--night-session-del-17012022--altro-gain-da-short-e-6660-200450735 — rapporto ex post di swing infranto prima di 24 barre e short, non protocollo esaustivo.
- **[A-06]** Jacopo Marini, archivio pubblico, 27/09/2022, *DAX e MIB — Pronti per la discesa?*: https://it.investing.com/members/contributors/200667220/opinion/35 — descrizione nell'archivio: aspettativa short, mancata violazione swing, scelta flat; **pagina di archivio**, non prova integrale del video.
- **[A-07]** Jacopo Marini, archivio pubblico, 03/03/2023, *Bitcoin — La prudenza paga!*: https://it.investing.com/members/contributors/200667220/opinion/13 — descrizione nell'archivio sull'incertezza e vincoli T-3; **pagina di archivio**, non prova integrale del video.
- **[A-08]** Pagine pubbliche di collegamento dell'autore: https://www.analisievoluta.com/youtube/ ; https://www.evolutaprevisioni.com/ — contengono presentazioni, rinvii a contenuti e anche claim promozionali; **non** sono documentazione tecnica completa né audit di risultati. L'esistenza di centinaia/migliaia di contenuti non autorizza a inferire regole non esaminate.

### 21.3 Ascendenze e letteratura esterna: SOLO contesto/validazione

- **[L-01]** J. M. Hurst, *The Profit Magic of Stock Transaction Timing*, Prentice-Hall, 1970. Catalogo: https://books.google.com/books/about/The_profit_magic_of_stock_transaction_ti.html?hl=en&id=62cPAQAAMAAJ — precedente storico per cicli; non manuale Evoluta.
- **[L-02]** Giuseppe Migliorino, *Il trading con le Lingue di Bayer*, Borsari, 2006. Editore/catalogo: https://www.borsari.it/prodotto/il-trading-con-le-lingue-di-bayer/ — tradizione lingua/raccordo; la voce dell'indice sul volume è rilevante per non travisare la genealogia.
- **[L-03]** L. Blume, D. Easley, M. O'Hara (1994), *Market Statistics and Technical Analysis: The Role of Volume*, *Journal of Finance* 49(1), 153–181. DOI: https://doi.org/10.1111/j.1540-6261.1994.tb04424.x — plausibilità teorica di valore informativo del volume.
- **[L-04]** J. Y. Campbell, S. J. Grossman, J. Wang (1993), *Trading Volume and Serial Correlation in Stock Returns*, *Quarterly Journal of Economics* 108(4), 905–939. DOI: https://doi.org/10.2307/2118454 — pattern volume e rendimenti, non periodicità AE.
- **[L-05]** J. S. Conrad, A. Hameed, C. Niden (1994), *Volume and Autocovariances in Short-Horizon Individual Security Returns*, *Journal of Finance* 49(4), 1305–1329. DOI: https://doi.org/10.1111/j.1540-6261.1994.tb02455.x — valore predittivo potenzialmente condizionale dell'attività di trading.
- **[L-06]** M. Aquilina, E. Budish, P. O'Neill (2022), *Quantifying the High-Frequency Trading “Arms Race”*, *Quarterly Journal of Economics* 137(1), 493–564. DOI: https://doi.org/10.1093/qje/qjab032 ; sintesi BIS: https://www.bis.org/publications/working-paper-955-quantifying-high-frequency-trading-arms-race — HFT, latenza e struttura di mercato in specifici campioni.
- **[L-07]** W. Brock, J. Lakonishok, B. LeBaron (1992), *Simple Technical Trading Rules and the Stochastic Properties of Stock Returns*, *Journal of Finance* 47(5), 1731–1764. DOI: https://doi.org/10.1111/j.1540-6261.1992.tb04681.x — evidenza storica su regole tecniche, **non** su Analisi Evoluta.
- **[L-08]** R. Sullivan, A. Timmermann, H. White (1999), *Data-Snooping, Technical Trading Rule Performance, and the Bootstrap*, *Journal of Finance* 54(5), 1647–1691. DOI: https://doi.org/10.1111/0022-1082.00163 — necessità di controllare selezione e numero di strategie tentate.
- **[L-09]** D. H. Bailey, M. López de Prado (2014), *The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality*, *Journal of Portfolio Management* 40(5), 94–107. Versione SSRN: https://doi.org/10.2139/ssrn.2460551 — solo se si conduce una valutazione economica con molte prove.
- **[L-10]** J. Brogaard, T. Hendershott, R. Riordan (2014), *High-Frequency Trading and Price Discovery*, *Review of Financial Studies* 27(8), 2267–2306. DOI: https://doi.org/10.1093/rfs/hhu032 — microstruttura HFT, non una spiegazione del clock T.

**Ulteriori famiglie citate nella Deep Research (senza attribuzione di regole Evoluta):** trasformate wavelet e decomposizione tempo-frequenza; misure di microstructure noise; probability of backtest overfitting, robustezza walk-forward; order flow e microprice; impatto di sessioni diverse. Sono **metodi alternativi/controlli scientifici**, non ingredienti obbligatori del prodotto e non sostituti della guida originale.

## 22. Scheda operativa di conoscenza COMPATTA — da poter riutilizzare isolatamente

> Questo blocco riassume ad alta densità la conoscenza del file. **In caso di ambiguità prevalgono le sezioni precedenti e le pagine del PDF, non la scorciatoia.**

```yaml
AE_KNOWLEDGE_V1:
  status: PARTIAL_PUBLIC_SPEC
  faithful_original_replica_possible_now: false
  primary: "Marini ©2023, Guida 16pp"
  research_basis: "Deep Research allegata + riscontri pubblici e letteratura"
  role: "lettura mercato e consulenza trade, NON esecuzione/capitale"
  epistemic_tags: [P, V, A, L, F, H, U]

  ontology:
    index: "min -> max -> min"
    inverse: "max -> min -> max"
    hierarchy: ["T-6", "T-5", "T-4", "T-3", "T-2", "T-1", "T", "T+1", "T+2", "T+3", "T+4", "T+5"]
    approx_degree_ratio: 2
    maximum_subcycles_mentioned: 6
    fixed_3_or_4_subcycles_required: false

  durations_original:
    applicable_instrument_context: "S&P500 NASDAQ DAX"
    bars_15m:
      T-6: [3, 4, 5]
      T-5: [6, 8, 10]
      T-4: [12, 16, 20]
      T-3: [21, 32, 44]
      T-2: [44, 64, 84]
      T-1: UNKNOWN
    days_calendar_basis: UNKNOWN
    days:
      T: [6, 8, 11]
      T+1: [12, 16, 21]
      T+2: [24, 32, 43]
      T+3: [48, 64, 84]
      T+4: [96, 128, 168]
      T+5: [192, 256, 336]
    MIB:
      T-3_min_15m: 24
      T-2_min_15m: 48
      min_can_shorten_to_23_in_decline: "mentioned, degree/context not fully resolved"
    BTC_ETH:
      nominal_bar: "45m"
      T-3_min_bar_approx: 24
      all_other_bands: UNKNOWN
      source_venue_and_anchor: UNKNOWN
    regime_claim: "ascents elongate, declines/crashes shorten; not formalized"

  cycle_rules_claimed:
    start_G: "G-2 bullish/neutral or equivalent Pure Time; swing of pertinent high; volumes; unclear AND/OR and volume exception"
    finish_G: "G-3 bearish is described necessary and sufficient; detection timestamp unspecified"
    bull: "terminal low above origin; peak usually later"
    bear: "terminal low below origin; peak usually earlier"
    neutral: "peak centrally; 75-99% retracement; precise ratio and precedence UNKNOWN"
    bearish_constraint: "index origin low violated before documented minimum age; forecast duration UNKNOWN"
    inverse_recursion: "max-to-max controls index timing/constraints"
    reciprocity: "index low might align with inverse high; breakdown can occur"
    rhythm_change: "associated with lost reciprocity; rule UNKNOWN"
    motor_cycle: "possible after rhythm change; rule UNKNOWN"
    raccordo: "false start up then swift down before expected min; three-degree-lower relation; two types; proprietary volume formula UNKNOWN"
    point_j: "centratura attention level, distance used publicly; formula UNKNOWN"
    operational_techniques_1_2: UNKNOWN

  verified_non_claims:
    price_target_formula: UNKNOWN
    stop_and_entry_original_formulas: UNKNOWN
    volume_original_definition: UNKNOWN
    pure_time_formula: UNKNOWN
    swing_of_relevance_formula: UNKNOWN
    original_method_integral_OOS_evidence: NOT_ESTABLISHED
    HFT_causes_cycles: UNPROVEN_GENERAL_CLAIM
    index_inverse_independent_confirmation: FALSE_ASSUMPTION
    six_subcycles_always: FALSE_ASSUMPTION

  guardrails:
    - "Never invent a proprietary rule or claim experimental proxy is authentic"
    - "Never use hindsight pivots as if known at origin"
    - "Always use market-specific calendars and units"
    - "Always separate market view from trade action"
    - "NO_TRADE can coexist with directional forecast"
    - "Targets require independent documented projection rules"
    - "Do not add sizing, leverage, broker execution or real-money authority"
    - "Keep alternatives, contradictory evidence, and unknowns visible"
    - "Evaluate incremental validity out-of-sample versus sensible baselines"
```

## 23. Consegna ad Astra: come leggere e usare questa conoscenza

1. **Conserva la distinzione fra tradizione professionale, metodo specifico e contributo originale non divulgato.** Non fare «Analisi Evoluta» semplicemente sommando swing+RSI+MACD+volume perché la guida cita generici indicatori.
2. **Considera il corpus come conoscenza da studiare e una descrizione di vincoli epistemici**, non come un mandato a sviluppare subito una nuova strategia. Chiedi di recuperare fonti autentiche o proponi una formalizzazione sperimentale solo dopo un'esplicita scelta di ricerca.
3. **Mantieni la struttura causale multi-grado**, la distinzione `G-2` per partenza/`G-3` per chiusura e la differenza tra durata 15m, 45m e giorni.
4. **Quando valuti un segnale**, indica sempre `quale fonte`, `quale regola esatta`, `quale mercato`, `quando era conoscibile`, `cosa conferma`, `cosa lo contraddice`, `come potrebbe essere falsificato`.
5. **Se vuoi consigliare una posizione LONG/SHORT sulla base del metodo specifico, riconosci il blocco attuale**: non possediamo le Tecniche Operative né il calcolo degli elementi proprietari che renderebbero la decisione fedele. Le eventuali prove restano **AE-inspired research** e non consiglio autenticato dell'autore.
6. **La priorità del committente è una market view continua, comprensibile e utilizzabile per le sue scelte manuali**, non una piattaforma che prenda decisioni di leva, quantità o esegua ordini; eventuale integrazione progettuale passa da approvazione esplicita.
7. **Nessuna performance o capacità predittiva futura è certificata** da questo corpus. Per renderla tale servono definizioni, previsioni ex ante, riferimenti di confronto, dati validati e risultati fuori campione.

---

**Esito conoscitivo finale:** l'Analisi Evoluta pubblicamente descritta contiene un nucleo sostanziale, riconoscibile e formalizzabile **in parte**: cicli di entrambi i lati, gradi, alcune durate, geometrie, regola qualitativa `G-2/G-3`, swing, volume, Tempo Puro, vincoli, reciprocità e Raccordo. La sua **procedura operativa completa** resta **non ricostruibile fedelmente** con le fonti disponibili. Questa non è una perdita d'informazione causata dalla condensazione: è una lacuna nelle fonti primarie. Astra deve conservare fedelmente **sia ciò che sappiamo sia ciò che non sappiamo**, senza trasformare il secondo gruppo in certezze inventate.
