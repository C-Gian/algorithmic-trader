# MOVE-001/v1 — Ciclo di vita del movimento di riferimento

**Candidata semantica sperimentale approvata da Astra, 17 ottobre 2026. Contratto 1.0.1 completo per implementazione isolata e applicazione descrittiva DEV; non strategia approvata né efficacia dimostrata. Implementazione e macrofase descrittiva chiuse dal Director dopo R1 su2cdda77: esiti, verifiche e limiti in MOVE-001-results.md §11. Nessuna nuova strategia autorizzata.**
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
| 6 | 114/110/112 | 110/106/108 | Questa lettura non viene riattivata per scelta del metodo; attendiamo una nuova struttura |

Anche senza test di P0, due high e due low confermati decrescenti interni alla vecchia gamba LONG (per esempio high114→112 e low108→106, tutti>P0=104) sono STRUTTURA_OPPOSTA: sospensione, non perdita della base né SHORT automatico. Specchio SHORT: high112→114 e low106→108, con high<P0=116; stessa conclusione. MIXED da solo non basta.

## 9. Review interna del Director e limiti residui

Controllati manualmente: simmetria p→220−p, ordine di conoscibilità2+2, rottura con ancore già disponibili, assenza di nuovi pivot dedotti prima della conferma; stesso prefisso B/C con uguale giudizio prima dei futuri diversi; nessuna resurrezione del vecchio riferimento, contatto/chiusura distinti, doppio test non ordinato, nuova identità distinta, completamento geometrico distinto da perdita e da esecuzione. I numeri dei casiC consentono effettivamente i pivot stretti indicati. Nessun test di rendimento, nuova estrazione o suite.

È **review interna dello stesso Director autore della proposta**, non verifica indipendente di Claude/Astra. La lettura del codice OBS-001 conferma soltanto che i fatti richiesti sono rappresentabili con eventi/availableAt esistenti; il codice attuale non implementa questo ciclo.

Limiti dichiarati: scelta della scala, ritardo dei pivot, definizione conservativa di base protetta, sospensione non reversibile del vecchio riferimento per un semplice recupero, assenza di scadenza temporale. Possono produrre attese e riferimenti non risolti o perdere alcune continuazioni; non sono qualità validate. Non sappiamo se le distinzioni aiutino a decidere. Non riqualifichiamo la popolazione OBS-002: quella domanda futura richiederebbe autorizzazione e registrazione separate.

## 10. Consegna di design e autorizzazione successiva

Il commit 03510afe conserva la proposta originale di solo design. Astra l'ha approvata come candidata sperimentale e autorizza ora il perimetro dei §§11–12. Nessun risultato precedente viene riscritto; CAND-001 resta invariata. Le precisazioni seguenti sono chiuse dal Director prima dell'incarico implementativo.

## 11. Precisazioni approvate e contratto implementativo — versione 1.0.1

Astra approva la candidata semantica del commit 03510afed13732c2fc46b5bb4e95626986c95ca0 e autorizza implementazione isolata e una applicazione descrittiva DEV. Questa sezione completa le precedenze dei §§2–7 e prevale nei punti prima non espliciti. Non introduce una strategia. La versione 1.0.1 identifica queste precisazioni, non una variante scelta da esiti.

### 11.1 Popolazione e significato dei giudizi

È una popolazione nuova e più specifica: minimo crescente/massimo decrescente seguito dalla rottura del precedente estremo. Non ripara OBS-002, non rappresenta ogni impulso o pullback, non elimina retroattivamente i 1728 casi e non prevede un vantaggio economico.

Distinguere attesa informativa FORMAZIONE_NON_CONCLUSA da sospensioni metodologiche TEST_ORIGINE e STRUTTURA_OPPOSTA. Queste ultime restano tali per scelta conservativa: **questa lettura non viene riattivata; attendiamo una nuova struttura**. Non affermare che tutta l'informazione successiva sia inconoscibile. Conservare primo motivo, istante di sospensione e fatti successivi, senza cancellare i motivi precedenti. Una chiusura successiva oltre P0 può ancora concludere per perdita della base una lettura sospesa.

### 11.2 Unico riferimento e strutture candidate

Alla nascita la formazione occupa subito l'unico posto principale. Una lettura INDETERMINATA soltanto perché P1 non è ancora noto non è sostituibile come una lettura sospesa per test/conflitto.

Ad ogni chiusura completa considerare la tripla degli ultimi tre pivot della sequenza alternata accettata allora, con i vincoli §2. Ogni tripla qualificata viene considerata al suo primo attraversamento valido con ancore già note; identificazione tramite verso, segmento e ID/versioni causali Q/B/P0. Considerarla una volta sola anche se non adottata. Una nuova versione di pivot è una nuova tripla soltanto dal proprio availableAt. Non recuperare in seguito candidati rifiutati, né trasformare il successivo riattraversamento della stessa tripla in nuova nascita.

Registrare tutte le strutture qualificate, prima del filtro del posto principale: ADOTTATA, NON_ADOTTATA_OCCUPATO_FORMAZIONE, NON_ADOTTATA_OCCUPATO_UTILIZZABILE o NON_ADOTTATA_FRESCHEZZA. I primi due rifiuti valgono anche se il candidato ha verso opposto. Nel caso sospeso, una nuova tripla può subentrare soltanto con P0 candidato strettamente successivo alla prima barra di test/conflitto; altrimenti NON_ADOTTATA_FRESCHEZZA. Dopo perdita usare la barra della perdita; dopo completamento geometrico basta P0 candidato successivo al vecchio P0, come §6. Conservare il vincolo anche se il posto è stato liberato; il primo riferimento del segmento non ha un predecessore da soddisfare.

La sostituzione archivia il vecchio riferimento col suo ultimo giudizio e motivo SOSTITUITO_DA_NUOVA_STRUTTURA; la nuova identità conserva il legame. Perdita e completamento liberano il posto nella stessa chiusura: un candidato di quella chiusura può essere adottato se soddisfa i vincoli, senza riusare una rottura precedente.

Distinguere questi rifiuti da triple non qualificate (geometria, base già testata, assenza di nuovo attraversamento, dati non continui). Non contarle come strutture nuove bloccate dal posto. Nessuna selezione fra più triple storiche per trovare quella più favorevole.

### 11.3 Ordine della chiusura e struttura opposta alla nascita

Ordine deterministico per ogni chiusura:
1. Accertare continuità/completamento della barra; se manca, applicare §11.5.
2. Pubblicare soltanto gli eventi dell'osservatore disponibili entro quella chiusura.
3. Valutare il vecchio riferimento con le priorità §4.1, inclusa l'eventuale prima disponibilità di P1. Una sospensione preesistente non scompare.
4. Considerare la nuova tripla e il suo attraversamento, registrando adozione/rifiuto §11.2.
5. Per il riferimento appena nato valutare la struttura45m già disponibile nella stessa chiusura. Se opposta, conservare la nascita ma attribuire subito INDETERMINATO/STRUTTURA_OPPOSTA_ALLA_NASCITA, sospensione persistente. Non attendere un successivo cambiamento di struttura. MIXED/non disponibile non bastano a sospendere. La formazione resta distinta come attributo P1 non disponibile.

La base di un candidato deve essere intatta dalla barra dopo P0 fino alla barra di nascita inclusa: perciò un candidato con test/perdita nella propria barra di nascita non nasce affatto. Non attribuire al neonato contatti della sua base precedenti alla nascita come eventi successivi. La sospensione per struttura può invece esistere già alla nascita: non equivale a errore del candidato o inversione.

Su una lettura non sospesa, il completamento geometrico precede la nuova struttura opposta sulla stessa barra, come §4.1. Perdita/test della base prevalgono sul completamento; conservare entrambi i fatti se i due estremi sono toccati, senza inventarne l'ordine intrabar.

### 11.4 Pubblicazione e formazione di P1

P1 è il primo pivot accettato qualificato §2.3: evento APPEND o REPLACE, mai un KEEP non accettato. Si fissa il valore/versione disponibile allora e non si riscrive dopo una successiva revisione dell'osservatore. Gli ID/versioni sorgente restano nella provenienza.

Gli eventi pubblicati alla chiusura sono già conoscibili per valutare la struttura e per nascita/sospensione. La candela candidata del pivot non può essere usata come contatto successivo del proprio P1. Alla pubblicazione di P1 si può descrivere la reazione osservata dalla barra successiva alla sua candidata fino alla pubblicazione inclusa, ma il giudizio cambia solo alla pubblicazione. Per un pivot stretto 2+2 nessuna delle due barre a destra può rivisitare P1; il primo nuovo contatto geometrico è quindi possibile dalla barra successiva alla pubblicazione. Non completare automaticamente il riferimento perché la candela che definisce P1 lo ha raggiunto per costruzione.

P1 pubblicato dopo una sospensione per test/struttura può essere registrato come fatto conoscibile, se la lettura è ancora principale, ma non la rende UTILIZZABILE. Dopo archiviazione non aggiornare la vecchia lettura. Contare separatamente disponibilità di P1 e passaggi effettivi a UTILIZZABILE. Una perdita durante formazione resta una perdita con P1 mancante, non uno zero o un endpoint inventato.

### 11.5 Dati interrotti, ripartenza e fine copertura

Un minuto mancante/invalido rende incompleta la relativa barra45m. Al primo confine previsto in cui la continuità non è verificabile, archiviare l'eventuale principale con INDETERMINATO/DATI_INCOMPLETI e motivo CONTINUITA_INTERROTTA; non attribuire perdita della base, contatto di P1 o inversione nel tratto ignoto. Conservare ultimo istante completo e primo confine di lacuna, non un timestamp di mercato inventato.

Ripartire l'osservatore in un nuovo segmento alla prima sequenza di barre complete dopo il tratto incompleto. Nessuna aggregazione o pivot può attraversare la lacuna; Q/B/P0/P1 devono appartenere al proprio segmento. Per il nuovo segmento non trasportare il prezzo precedente alla lacuna come chiusura precedente per l'attraversamento. Il primo eventuale riferimento deve qualificarsi interamente con nuove ancore e nuovo attraversamento. Non basta osservare dopo la lacuna un prezzo sotto P0 per dire che la vecchia base fu persa durante il tratto ignoto.

L'assenza di un indicatore dipendente da warmup non è un gap dei prezzi e non blocca il ciclo. Un input illeggibile o una provenienza non verificabile è invece errore operativo dichiarato: non sostituirlo con dati fittizi.

Fine copertura al 2025-01-01 escluso: registrare amministrativamente riferimenti ancora aperti e durate censurate, conservando l'ultimo giudizio. Nessuna perdita/completamento presunta, nessuna lettura 2025 per risolverli. Non introdurre scadenze temporali.

## 12. Applicazione descrittiva preregistrata

### 12.1 Input, percorso e riproducibilità

Solo barre negoziate 1m BTCUSDT perpetual USDⓈ-M pubbliche già verificate: prefisso [2022-10-01,2023-01-01), DEV [2023-01-01,2025-01-01). Riutilizzare i 27 file locali e i controlli di provenienza/copertura. Nessun download, funding/mark, dato2025/2026 o nuovo indicatore. Aggregazione45m e osservatore OBS-001 invariati; wrapper per segmenti se necessario, senza alterare gli studi precedenti.

Processare il prefisso per inizializzare anche il ciclo: non azzerare un riferimento il 1° gennaio 2023. Riportare stock iniziale e letture nate nel prefisso separate dalle nascite DEV, ma contare gli eventi DEV su entrambi. Identificare versione semantica/motore, config, commit, hash degli input e output e comando. Dati e output fuori Git, sotto MOVE-001.

Prima di qualsiasi applicazione reale pubblicare implementazione, test discriminanti e config che traduca questo contratto. Nessuna lettura esplorativa dei percorsi reali prima di quel gate. Congelare anche schema dei conteggi e selezione casi; non scegliere metriche dopo i risultati. Un'esecuzione descrittiva completa; una ripetizione per verificare identità dei risultati è ammessa e non è una seconda variante. Correzioni di bug documentate, versionate, con confronto degli effetti; non cambiare metodo per migliorare i conteggi.

### 12.2 Conteggi e durate fissati

Totale DEV, separati per anno e verso; riepilogo mensile di nascite, passaggi, archiviazioni e stock finale. Contare:
- chiusure previste/complete/incomplete; chiusure con principale assente, in formazione senza sospensione, sospeso (distinguendo con/senza P1), utilizzabile;
- strutture qualificate e tutti gli esiti adozione/rifiuto §11.2, inclusi verso e motivo del riferimento occupante;
- nascite, prime disponibilità P1, primo passaggio a UTILIZZABILE; sospensioni iniziali per test/struttura, distinguendo struttura opposta alla nascita e successiva; fatti ulteriori separati, senza ricontare una nascita;
- perdite della base (anche in formazione/sospensione), completamenti geometrici, sostituzioni e interruzioni; letture aperte a fine copertura con motivo e stato;
- durata nascita→P1, nascita→utilizzabile, permanenza nelle condizioni sopra, nascita→archiviazione o fine copertura. Unità barre45m e tempo UTC, conteggi disponibili/censurati separati, minimo/mediana/p90/massimo, quantile lineare standard dichiarato in config. Nessuna durata mancante pari a zero.

Riconciliare per ogni periodo stock iniziale + nascite − archiviazioni = stock finale; strutture qualificate = adottate + rifiutate; chiusure complete = somma delle condizioni di occupazione mutuamente esclusive. Le durate dei riferimenti che attraversano confini mensili non vanno falsamente concluse al confine. Segnalare concentrazione temporale e lunghe occupazioni descrittivamente, senza soglia di successo o parametro nuovo.

### 12.3 Esempi e consultazione

Selezione fissata prima dell'elaborazione: primo cronologico per (1) nascita LONG, (2) nascita SHORT, (3) passaggio a UTILIZZABILE dopo P1, (4) test dell'origine, (5) perdita della base, (6) struttura opposta alla nascita, (7) struttura opposta successiva, (8) completamento geometrico, (9) sostituzione dopo sospensione, (10) struttura non adottata per formazione occupante, (11) struttura non adottata per riferimento utilizzabile, (12) continuità interrotta. Inoltre primo per data di nascita fra i riferimenti ancora aperti a fine copertura. Ordinare per availableAt dell'evento, poi ID stabile; deduplicare lo stesso riferimento mantenendo le categorie. Categoria vuota dichiarata, non sostituita con un caso più interessante. Al massimo13 riferimenti, non selezionati per andamento futuro.

Usare importazione e consultazione storica esistenti con un adattatore minimo e tipo MOVE001_CASE esplicito, senza fingere che siano casi OBS-002 o risultati CAND. Grafico, ancore e timeline sincronizzati al momento scelto; “noto allora” non contiene revisioni/sostituzioni future. Segnalare chiaramente «Rappresentazione sperimentale del movimento — nessuna decisione operativa». Nessun esito24h calcolato soltanto per adattarsi al lettore: disabilitare/nascondere quel comando per questi casi. Nessun nuovo esploratore, restyling o servizio. I pacchetti storici esistenti devono restare leggibili.

### 12.4 Verifica e conclusione

Controlli sintetici discriminanti su LONG/SHORT speculari, pivot2+2 e loro versioni, formazione che occupa, struttura opposta alla nascita e successiva, test vs chiusura, collisioni, sostituzione/freschezza, candidati ignorati senza recupero, interruzione/ripartenza, fine copertura e invarianza dello stesso prefisso con futuri diversi. Controlli mirati del lettore se toccato; niente suite generale o polling CI.

Report unico con conteggi completi, limiti, esempi e giudizio: il ciclo rappresenta sequenze concretamente consultabili oppure resta prevalentemente in formazione/sospensione/blocco? Nessuna percentuale minima, resa economica o attribuzione di efficacia. Distinguere esecuzione verificata dall'autore e successiva review indipendente Director. L'esecutore consegna risultati e limiti; il Director conclude se la rappresentazione permette una prossima domanda decisionale e dove perde informazione. Non modificare automaticamente il metodo.
