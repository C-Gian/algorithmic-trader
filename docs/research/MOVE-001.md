# MOVE-001/v1 — Ciclo di vita del movimento di riferimento

**Proposta completa del Director, 17 ottobre 2026. Solo design, consegnato ad Astra. Non attivata nel codice, nei dati o nel prodotto.**
Base di lettura:505801131efd9f2cd6b9f8e92363c077c8b0bca9. Mandato Astra: definire quale situazione si riconosce mentre accade, senza estrazione, esclusione dei1728casi o modifica CAND-001. Non è una strategia, un segnale di esecuzione o una regola validata.

## 1. Significato e fonti

La lettura proposta è specifica: **arretramento di un impulso che ha superato in chiusura un estremo precedente, partendo da un nuovo pivot nel verso della struttura**. Non basta una coppia qualsiasi di estremi alternati. Il riferimento riguarda quella sequenza locale a45m, non tutto il trend di BTC o il giornaliero.

Fonti già indicizzate, rilette il17ottobre2026:
- Adam Grimes,[Fundamental Trading Patterns](https://www.adamhgrimes.com/fundamental-trading-patterns/): alternanza fra gambe nel verso e arretramenti; una ripresa può fallire e precedere un arretramento complesso.
- Adam Grimes,[One step ahead](https://www.adamhgrimes.com/one-step-ahead/): la reazione successiva contribuisce alla lettura del movimento.

Sono motivazioni qualitative. **Tripla di pivot, rottura in chiusura, regole di sospensione/perdita, identità e precedenze sotto sono convenzioni nostre.** Le fonti non forniscono questa formula, non ne dimostrano efficacia e non attribuiamo loro un obbligo di comprare o vendere. Non importati vecchi modelli o dossier del progetto precedente.

Definizioni riutilizzate: OBS-001/v1, barre45m UTC complete; pivot stretti2+2, doppio pivot ambiguo non accettato, sequenza alternata APPEND/REPLACE/KEEP e availableAt; struttura45m UP/DOWN/MIXED dagli ultimi due high e low confermati. Nessuna nuova media, indicatore, rapporto Fibonacci o parametro di ampiezza/tempo.

## 2. P0 pertinente: base di una rottura osservata

### 2.1 Formazione del riferimento LONG
Alla chiusura tb devono essere già disponibili, in quest'ordine nella sequenza alternata accettata, tre pivot:
1. Q, un LOW precedente;
2. B, il successivo HIGH;
3. P0, il successivo LOW, con **Q.price<P0.price<B.price**.

P0 è un minimo crescente, non il primo minuto di una finestra. B è un massimo formato e confermato prima, non un massimo futuro o una resistenza presumibilmente efficace.

La nascita richiede un **nuovo attraversamento in chiusura di B**, con tutti i pivot noti entro tb: Cprecedente<=B e Ctb>B. P0 deve risultare non ancora testato: dopo la propria candela candidata, fino alla barra di rottura inclusa, tutti i low devono essere>P0. Barre complete nello stesso segmento; Q/B/P0 con identità e tempi distinti, nessuna ambiguità nella loro sequenza. Una rottura avvenuta prima che la tripla fosse disponibile non è retrodatata: occorre un nuovo attraversamento osservabile con ancore già note.

**Perché P0 conta:** è l'ultimo minimo crescente da cui il prezzo ha effettuato quella rottura. La tesi locale è che la successiva reazione conservi come base quel minimo. Una chiusura che torna a P0 o sotto non conserva la base dichiarata per questo impulso. Non conclude che P0 fosse supporto economicamente efficace, che l'intero trend sia invertito o che ogni ritorno sotto P0 sia destinato a proseguire.

Una coppia LOW→HIGH isolata resta geometria disponibile, ma non è ancora questa lettura. La distinzione è motivata dal ruolo del pivot nella sequenza osservata, non dal39,52% o da un nuovo seguito favorevole.

### 2.2 SHORT speculare
Sequenza Q HIGH, B LOW, P0 HIGH, con **Q.price>P0.price>B.price**; Cprecedente>=B e Ctb<B; dopo la candela candidata di P0 tutti gli high<P0. P0 è il massimo decrescente da cui è stato rotto in chiusura il minimo B.

In notazione comune d=+1 LONG/−1 SHORT: d*(P0−Q)>0, d*(B−P0)>0; d*(Cprecedente−B)<=0<d*(Ctb−B). Nessun requisito economico e nessuna soglia in unitàA.

### 2.3 Estremo finale P1 e disponibilità
A tb è nota la base P0 e la rottura, **non ancora l'estremo finale dell'impulso**. Il massimo/minimo in formazione può essere descritto come tale, ma non chiamato pivot confermato.

P1 è il primo pivot accettato nel verso finale dopo la rottura: HIGH per LONG, LOW per SHORT, candidato dalla barra della rottura in poi e oltre B nel verso d. Diventa noto soltanto alla chiusura della seconda barra a destra. Non anticipiamo il ruolo di P1 alla sua candela candidata.

Fino ad allora la specifica lettura di arretramento ha giudizio INDETERMINATO, motivo FORMAZIONE_NON_CONCLUSA; la rottura resta un fatto noto. Se P0 viene perso nel frattempo si conclude la tesi prima che esista un P1 utilizzabile. Quando P1 diventa noto, se non vi sono sospensioni/perdite, si può descrivere la reazione già osservata senza collocare decisioni nel passato. La disponibilità di ogni nuovo fatto, non il successivo risultato, determina la lettura.

P0,P1 e B sono congelati nella specifica lettura. Non spostiamo P0 sul minimo successivo per salvare la tesi, né P1 sull'estremo più favorevole per riscrivere l'impulso.

## 3. Tre giudizi, distinti dalla direzione futura

| Giudizio al momento | Significato | Che cosa non implica |
|---|---|---|
| UTILIZZABILE | Ancore conoscibili e continuità osservata; la reazione può ancora essere letta rispetto alla base di quell'impulso | Entrata, probabilità favorevole o trend globale confermato |
| NON_SOSTIENE_PIU_LA_TESI | Chiusura sulla/oltre la base nel verso contrario; il riferimento non conserva la proprietà dichiarata | Inversione certa o operazione opposta |
| INDETERMINATO | Estremo finale non ancora conoscibile, base testata e recuperata, struttura contraddittoria o continuità ignota | Perdita/guadagno pari a zero, conferma della tesi o permesso di prolungarla a piacere |

Ogni giudizio conserva il motivo. FORMAZIONE_NON_CONCLUSA è una attesa informativa risolvibile con P1 confermato; le sospensioni per TEST_ORIGINE, STRUTTURA_OPPOSTA o DATI_INCOMPLETI **non** si risolvono col semplice ritorno del prezzo o del colore della struttura. Richiedono una nuova lettura con nuova evidenza (§6).

L'archiviazione di una lettura è un fatto separato dal giudizio: può avvenire perché il vecchio estremo è stato raggiunto, perché la base è persa, perché subentra una nuova lettura o perché termina la copertura dei dati. Non creiamo un quarto giudizio chiamando ogni archiviazione fallimento.

## 4. Una semantica causale a chiusure45m

Tutte le classificazioni avvengono **dopo la chiusura di una barra completa**; contatti intrabar diventano fatti disponibili a quella chiusura. Non c'è una simulazione di comandi intrabar. Il prezzo della candela di P0 è escluso dai test della base, altrimenti ogni origine risulterebbe testata per definizione.

| Fatto disponibile | Trattamento della stessa lettura |
|---|---|
| LONG low>P0, C>P0; SHORT high<P0, C<P0; nessun conflitto | Mantiene UTILIZZABILE quando P1 è noto; le normali oscillazioni interne e MIXED non bastano a invalidare |
| LONG low<=P0 ma C>P0; SHORT high>=P0 ma C<P0 | INDETERMINATO/TEST_ORIGINE: base penetrata o toccata e recuperata entro la barra; non decidiamo se sia un falso superamento o la premessa della perdita |
| LONG C<=P0; SHORT C>=P0 | NON_SOSTIENE_PIU_LA_TESI/ORIGINE_IN_CHIUSURA, conclusione definitiva della specifica lettura |
| Struttura45m confermata opposta al verso, prima della conclusione geometrica e senza perdita della base | INDETERMINATO/STRUTTURA_OPPOSTA: organizzazione locale contraria, che può ancora essere parte di una reazione complessa; nessuna inversione automatica |
| P1 non ancora confermato | INDETERMINATO/FORMAZIONE_NON_CONCLUSA, senza estremo futuro spacciato per noto |
| Barra mancante/incompleta o segmento interrotto | INDETERMINATO/DATI_INCOMPLETI; non sappiamo quale estremo sia stato raggiunto nel tratto mancante. Non ricucire il vecchio riferimento come se fosse continuo |

**Perché contatto e chiusura diversi su P0:** la chiusura oltre la base è la convenzione scelta per concludere la conservazione di quella base a scala45m. Un semplice contatto è un test che non distingue da solo rifiuto e accettazione oltre il livello, quindi sospende. Non attribuiamo una qualità speciale all'esatto prezzo P0; non aggiungiamo tolleranze, bufferA o un numero ottimizzato di chiusure. Questa scelta può sospendere anche riprese poi favorevoli e può riconoscere tardi una perdita rapida: sono svantaggi accettati del disegno, da non nascondere.

### 4.1 Priorità, senza inventare l'ordine intrabar
1. Una lettura già conclusa/archiviata non si riscrive. Il futuro si registra in eventuale nuova lettura.
2. Dati incompleti o continuità interrotta: non assegnare una perdita/completamento di mercato nel tratto ignoto; sospendere e richiedere nuovo riferimento nel segmento noto.
3. Su barra completa, C sulla/oltre P0 nel verso contrario conclude la proprietà di conservazione della base. Se la stessa barra ha toccato anche P1, registrare entrambi i fatti e ordine non ricostruibile dalle sole barre45m: **non** attribuire quale fosse arrivato prima o un esito di trading. Il giudizio riguarda la base non conservata a quella chiusura.
4. C dalla parte conservata, ma test di P0 nella barra, oppure sospensione già aperta: INDETERMINATO. Anche un recupero fino a P1 non ripristina una lettura già sospesa come se non fosse stata testata.
5. Se la lettura era UTILIZZABILE, senza test di P0/sospensione e con P1 noto, il contatto favorevole di P1 completa geometricamente il ritorno all'estremo (§5). Archiviare con l'ultimo giudizio UTILIZZABILE e motivo ESTREMO_RAGGIUNTO: non è NON_SOSTIENE_PIU_LA_TESI.
6. Senza tale completamento, nuova struttura opposta sospende; altrimenti P1 non disponibile mantiene l'attesa informativa, P1 confermato rende UTILIZZABILE se tutte le condizioni restano soddisfatte.

Se entrambe le frontiere sono state toccate nella stessa barra e C è tornata nell'intervallo, vale INDETERMINATO/TEST_ORIGINE con flag DOPPIO_TEST_ORDINE_IGNOTO, non un completamento scelto per primo. Queste precedenze qualificano una lettura a chiusura: non sono precedenze di stop/target.

## 5. Estremi nuovi e conclusione favorevole della lettura

Per una lettura utilizzabile, LONG high>=P1 o SHORT low<=P1 testimonia che il prezzo ha rivisitato l'estremo. Basta il contatto per questo **fatto geometrico**, perché la proposizione è «è tornato a quel prezzo», non «ha accettato una rottura duratura». La sospensione/perdita di P0 ha le priorità di§4.1. Il contatto può essere seguito da un rifiuto del livello; non dimostra una tendenza destinata a continuare.

A quel punto la lettura di arretramento *in attesa del ritorno a P1* è completata e archiviata, senza calcolo di rendimento o prezzo di uscita. Un'eventuale estensione oltre P1 appartiene ai fatti successivi; un nuovo P1 confermato non modifica il vecchio. Durante la formazione iniziale, invece, estremi ancora non confermati restano provvisori e non generano versioni storiche retroattive.

Un nuovo minimo/massimo interno alla reazione può modificare la geometria descritta, ma non P0. Un pivot opposto da solo può descrivere la reazione: non è automaticamente un nuovo riferimento nel verso opposto. KEEP e REPLACE dell'osservatore restano eventi osservativi; non sono da soli comandi di sostituzione del riferimento semantico.

## 6. Recupero e nuovo movimento

Una vecchia lettura NON_SOSTIENE_PIU_LA_TESI resta tale dopo C tornata dalla parte di P0. Una lettura sospesa per test/conflitto resta INDETERMINATA dopo quel semplice recupero. La vecchia classificazione è ciò che era sostenibile allora, non un'etichetta da correggere in base a come va a finire.

Per una nuova lettura serve di nuovo **l'intera evidenza di§2**: tripla alternata confermata, pivot di base nel verso, nuovo attraversamento in chiusura di un estremo precedente già noto, continuità e base non ancora testata. Dopo sospensione/perdita, il nuovo P0 deve avere candela candidata strettamente successiva alla prima barra che ha generato quel test/conflitto; dopo un gap tutte le ancore sono nel nuovo segmento. Il nuovo attraversamento deve avvenire quando le ancore sono già disponibili. Un recupero in due candele senza questa struttura non basta.

La nuova lettura ha identità propria (pivot di base, livello rotto, istante di rottura e verso), eventuale legame genealogico con la precedente e proprio P1 conoscibile solo più tardi. Può avere lo stesso verso o quello opposto; nessuna direzione privilegiata e nessuna operazione implicita. Non richiediamo che il nuovo prezzo P0 sia sopra/sotto il vecchio per salvare l'episodio: conta la nuova sequenza causale.

Un solo riferimento principale alla volta. Finché una lettura resta utilizzabile, le sotto-gambe osservate restano contesto; non manteniamo due tesi direzionali principali concorrenti come in OBS-002. Se la vecchia è sospesa/conclusa, si può adottare un nuovo riferimento solo su nuova evidenza completa, archiviando il precedente con il suo ultimo giudizio e motivo. Alla stessa chiusura sono possibili archiviazione e nascita di una nuova lettura se la nuova rottura avviene proprio allora e le condizioni sono già note: mai recuperare una rottura vecchia come se fosse appena avvenuta.

Dopo completamento favorevole di P1, una nuova lettura richiede nuovo pivot di base (candela dopo il vecchio P0) e nuova rottura; il solo allungamento dello stesso estremo non crea una nuova unità. Questi requisiti sono convenzioni conservative e possono non rappresentare alcune continuazioni reali. Non è dimostrato che la loro selettività migliori le decisioni.

## 7. Tempo, dati e limiti d'ambito

La scala della lettura è45m: conferme2+2 e chiusure determinano quando si sa qualcosa. Registrare età in barre e fasi, senza una scadenza9h/24h o un decadimento scelti dai risultati. H24 di OBS-002 è un orizzonte di misura, non la durata naturale del movimento. Un percorso interno può restare non risolto a lungo; l'età non lo trasforma automaticamente in perdita o conferma.

Fine copertura: archiviazione amministrativa con giudizio/limite noto, non evento di mercato. L'indeterminatezza può persistere finché non arriva evidenza nuova: questo design non garantisce una classificazione immediata di ogni barra. A,SMA,volume o Fibonacci mancanti non bloccano automaticamente la semantica, che dipende qui da prezzi/pivot/struttura richiesti. Il giornaliero resta un contesto diverso; non viene imposto come conferma.

## 8. Verifica manuale causale — prezzi inventati, nessun dato storico

### 8.1 Prefisso comune e specchio SHORT
Barre e tempi sono simbolici45m. Tutti i pivot descritti sono stretti2+2 con i vicini coerenti. Non sono dati BTC.

| Evento noto | LONG | SHORT, specchio p→220−p | Giudizio sulla lettura |
|---|---|---|---|
| Tripla già confermata prima di tb | Q LOW100, B HIGH110, P0 LOW104 | Q HIGH120, B LOW110, P0 HIGH116 | Nessuna lettura nata senza rottura |
| tb, Cprev109→C111, low105; specchio Cprev111→C109, high115 | Nuova rottura110 dalla base104 | Nuova rottura110 dalla base116 | INDETERMINATO, estremo finale non noto |
| tb+1: HIGH116, low110, C115 | Possibile P1, ancora candidato | LOW104, high110, C105 | INDETERMINATO, non usare il futuro per chiamarlo pivot |
| tb+2: H115,5 L110 C112 | Un solo vicino destro | H110 L104,5 C108 | INDETERMINATO |
| tb+3: H114 L109 C111 | HIGH116 confermato con2barre a destra | H111 L106 C109; LOW104 confermato | UTILIZZABILE; P1 ora noto |

Q/B/P0 hanno candidateOpen ordinati e distinti (per esempio−8/−5/−3barre prima di tb); conferme rispettivamente2barre dopo la propria chiusura, quindi disponibili prima di tb. Nessuna barra successiva alla candidata P0 e precedente a tb lo ha testato.

### A. Arretramento e ripresa
Da tb+3, struttura UP/MIXED nel LONG, DOWN/MIXED nello SHORT; nessuna struttura opposta confermata.

| Passo | LONG H/L/C | SHORT H/L/C | Affermazione disponibile allora |
|---|---|---|---|
| 4 | 113/108/110 | 112/107/110 | Base intatta, UTILIZZABILE; non sappiamo se riprenderà |
| 5 | 115/109/114 | 111/105/106 | Nuovo tentativo nel verso, riferimento ancora UTILIZZABILE; nessuna entrata implicita |
| 6 | 116,4/113/115,7 | 107/103,6/104,3 | P1 rivisitato, base non testata: ritorno geometrico completato e lettura archiviata; non profitto né prosecuzione garantita |

### B. Attraversamento dell'origine e seguito contrario

| Passo | LONG H/L/C | SHORT H/L/C | Giudizio e motivo |
|---|---|---|---|
| 4 | 109/103/103,5 | 117/111/116,5 | NON_SOSTIENE_PIU_LA_TESI: chiusura oltre la base104/116 |
| 5 | 104/100/101 | 120/116/119 | Vecchio giudizio invariato; ora osserviamo ulteriore movimento contrario, non lo avevamo previsto né ordinato |

### C. Stesso attraversamento, poi recupero
Passo4 identico aB. Il recupero successivo non cambia la classificazione di quel passo.

| Momento | Evidenza LONG disponibile | Evidenza SHORT speculare | Che cosa si può dire |
|---|---|---|---|
| 4 | H109 L103 C103,5 | H117 L111 C116,5 | Vecchio riferimento NON_SOSTIENE_PIU_LA_TESI |
| 5 | C108, ritorno sopra104 | C112, ritorno sotto116 | Vecchio giudizio invariato; recupero non è nuova struttura |
| 6 | LOW103 del passo4 ora confermato | HIGH117 del passo4 ora confermato | Un solo pivot nuovo non basta |
| 9 | HIGH113 del passo7 ora confermato | LOW107 del passo7 ora confermato | Si conosce un nuovo livello, non una nuova rottura |
| 11 | LOW107 del passo9 ora confermato; è>103 | HIGH113 del passo9 ora confermato; è<117 | Nuova tripla nota:103→113→107, oppure117→107→113 |
| 12 | Cprev112,2→C114 rompe113; base107 non testata dopo la candidata | Cprev107,8→C106 rompe107; base113 non testata | Nasce nuova identità, INDETERMINATO/FORMAZIONE_NON_CONCLUSA; il vecchio riferimento rimane perso |
| 15 | HIGH117 del passo13 confermato | LOW103 del passo13 confermato | Nuovo P1 noto, nuova lettura UTILIZZABILE se nessuna altra contraddizione |

Coerenza dei vicini per questa sequenza: dopo il LOW103, low ai passi5/6=103,6/105; HIGH113 al passo7 ha high nei passi5/6=109/110 e8/9=112,5/112; LOW107 al passo9 ha low nei passi7/8=108/109 e10/11=108/109. P1 al passo13 ha HIGH117 e high ai14/15=116,5/115. SHORT ottenuto dallo specchio, non da una scelta diversa di regole.

### D. Percorso ancora ambiguo

| Passo | LONG H/L/C | SHORT H/L/C | Giudizio disponibile |
|---|---|---|---|
| 4 | 117/103,8/112 | 116,2/103/108 | Test di P0 e P1 nella stessa barra, C nell'intervallo: INDETERMINATO, ordine ignoto. Non scegliamo il contatto favorevole per primo |
| 5 | 115/109/113 | 111/105/107 | Prezzo recuperato ma nessuna nuova tripla/rottura: ancora INDETERMINATO |
| 6 | 114/110/112 | 110/106/108 | Il futuro non ha ancora risolto la lettura; non le assegniamo un esito inventato |

Anche senza test di P0, due high e due low confermati decrescenti interni alla vecchia gamba LONG (per esempio high114→112 e low108→106, tutti>P0=104) sono STRUTTURA_OPPOSTA: sospensione, non perdita della base né SHORT automatico. Specchio SHORT: high112→114 e low106→108, con high<P0=116; stessa conclusione. MIXED da solo non basta.

## 9. Review interna del Director e limiti residui

Controllati manualmente: simmetria p→220−p, ordine di conoscibilità2+2, rottura con ancore già disponibili, assenza di nuovi pivot dedotti prima della conferma; stesso prefisso B/C con uguale giudizio prima dei futuri diversi; nessuna resurrezione del vecchio riferimento, contatto/chiusura distinti, doppio test non ordinato, nuova identità distinta, completamento geometrico distinto da perdita e da esecuzione. I numeri dei casiC consentono effettivamente i pivot stretti indicati. Nessun test di rendimento, nuova estrazione o suite.

È **review interna dello stesso Director autore della proposta**, non verifica indipendente di Claude/Astra. La lettura del codice OBS-001 conferma soltanto che i fatti richiesti sono rappresentabili con eventi/availableAt esistenti; il codice attuale non implementa questo ciclo.

Limiti dichiarati: scelta della scala, ritardo dei pivot, definizione conservativa di base protetta, sospensione non reversibile del vecchio riferimento per un semplice recupero, assenza di scadenza temporale. Possono produrre attese e riferimenti non risolti o perdere alcune continuazioni; non sono qualità validate. Non sappiamo se le distinzioni aiutino a decidere. Non riqualifichiamo la popolazione OBS-002: quella domanda futura richiederebbe autorizzazione e registrazione separate.

## 10. Consegna

Una sola proposta completa, pronta per valutazione semantica Astra. Nessun cambiamento a CAND-001, OBS-002, osservatore, config, UI, dataset o esiti; nessuna esclusione dei1728casi, uso2025 o2026, acquisizione o incarico implementativo. Il passo successivo è una decisione sulla proposta, non un nuovo studio già attivo.
