# MP-005 — v0.6: incompatibilità iniziale del riferimento RETURN

**Stato:** chiuso metodologicamente dal Director.  
**Natura:** delta rispetto a MP-004 / v0.5. La specifica pinnata MP-004 resta invariata.  
**Ambito:** soltanto il child A RETURN, nel momento in cui prepara il riferimento locale.

L’approvazione riguarda la coerenza del comportamento e della diagnosi. Non approva efficacia economica, implementazione o nuove prove.

## 1. Scopo e regole ereditate

MP-005 termina il child quando la conferma richiesta dal riferimento appena preparato è già incompatibile con la regione utilizzabile e le evoluzioni ammesse non possono rimuovere tale incompatibilità.

La terminazione riguarda la **praticabilità di questa modalità d’ingresso**. Non invalida automaticamente lo scenario A e non misura la qualità informativa della risposta locale.

Restano invariati tutti i valori e le regole ereditati, inclusi:

- un solo riferimento, nessuna sostituzione o rinnovo;
- prima ripresa come unica valutazione d’ingresso;
- uguaglianza ammessa sull’estremo contrario; superamento invalidante;
- geometria, anchor, V, target, cap, corridoio, costi, scadenze e protezioni;
- IMMEDIATE, scenari B/C e comportamento dopo l’emissione;
- separazione fra emissione e successivo ingresso modellato;
- clearing iniziale e continuità fra mesi.

Gli estremi del riferimento non diventano stop o anchor dello scenario.

## 2. Momento del controllo e domini

Il controllo si esegue **soltanto dopo che un RETURN utilizzabile secondo MP-004 ha preparato il riferimento**. Non anticipa né allenta i requisiti della preparazione.

Sono disponibili causalmente:

- barra completa di riferimento, con estremi \(H_0,L_0\);
- intervallo della barra, pubblicazione effettiva \(p_0\) e cursore \(c_0\);
- tick \(\tau\) dell’instrument pin;
- corridoio effettivo e cap aggiornati secondo le precedenze esistenti;
- profilo di esecuzione applicabile.

Sulla griglia dei prezzi ammessi dal tick:

\[
F_{\mathrm{LONG}}=\{p:p\ge H_0+\tau\}
\]

\[
F_{\mathrm{SHORT}}=\{p:p\le L_0-\tau\}.
\]

F descrive il dominio della **chiusura confermante**. Non incorpora le altre condizioni necessarie della risposta: assenza di violazioni contrarie precedenti, dominio temporale valido, barra corrente e gate esistenti.

Siano:

- \(C_0\): corridoio effettivo alla preparazione;
- \(A_0\): regione economicamente ammessa dal profilo applicabile;
- \(J_0=F\cap C_0\cap A_0\).

Il corridoio conserva gli arrotondamenti esistenti verso l’interno. I bordi sono inclusivi quando soddisfano i predicati ereditati. **Un solo prezzo ammesso sulla griglia costituisce un’intersezione non vuota.**

## 3. Condizioni del nuovo terminale

### 3.1 Incompatibilità col corridoio — storico e live

Se:

\[
F\cap C_0=\varnothing,
\]

il child termina con:

- motivo: `INITIAL_RESPONSE_INCOMPATIBLE`;
- base primaria: `CORRIDOR`.

Questa prova è indipendente dai costi.

Nel live resta rilevante perché MP-004 richiede che anche la **chiusura della barra confermante** appartenga al corridoio, oltre ai controlli sul prezzo side corrente. Una quotazione favorevole successiva non può sanare una chiusura confermante fuori corridoio.

### 3.2 Incompatibilità economica — soltanto storico

Nel profilo storico fisso registrato, se:

\[
F\cap C_0\ne\varnothing,\qquad J_0=\varnothing,
\]

il child termina con:

- motivo: `INITIAL_RESPONSE_INCOMPATIBLE`;
- base primaria: `HISTORICAL_ECONOMICS`.

Si conservano:

- costo storico di adeguatezza: **14 bps**;
- rapporto netto minimo: **1.2**;
- formule, V operativa e arrotondamenti ereditati.

Se concorrono incompatibilità col corridoio ed economica, entrambe possono essere annotate; la base primaria resta `CORRIDOR`. Si registra una sola terminazione.

### 3.3 Limite live

Nel live, se \(F\cap C_0\ne\varnothing\), **MP-005 non introduce una terminazione per incompatibilità economica**, anche quando i costi correnti rendono \(J_0\) vuoto.

Non si introduce un costo minimo futuro o una nuova soglia. Restano i costi registrati:

\[
K_{\mathrm{live}}
=2\cdot5+2\cdot2+
\frac{10000(\mathrm{ask}-\mathrm{bid})}{2\,\mathrm{midpoint}}
\quad\text{bps}.
\]

Durante WAIT_RESPONSE, una restrizione economica temporanea segue MP-004. Alla prima ripresa, qualsiasi impedimento ancora presente consuma il child secondo le regole esistenti.

L’intersezione live fra F e la regione economica corrente non va interpretata come identità fra chiusura confermante e prezzo d’esecuzione: quest’ultimo resta ask per LONG, bid per SHORT.

## 4. Perché l’incompatibilità certificata è irreversibile

Per il child restano congelati riferimento, anchor, corridoio strutturale, V operativa e target alla conferma. Il tick e i parametri seguono i pin esistenti.

Il cap può soltanto restringersi:

- LONG: scendere;
- SHORT: salire.

Di conseguenza:

- il corridoio effettivo futuro non può ampliare quello iniziale;
- nello storico, a costo fisso, la regione economica futura non può ampliare quella iniziale;
- F resta invariato.

Pertanto l’intersezione certificata vuota non può diventare non vuota attraverso le evoluzioni ammesse.

Contesto, scadenze e altre protezioni possono terminare o bloccare il child, ma non ampliano questi insiemi. MP-005 non autorizza modifiche agli invarianti per recuperare opportunità.

## 5. Precedenze, transizioni e persistenza

Ordine logico:

1. Applicare le protezioni ereditate e gli aggiornamenti causali previsti.
2. Verificare che il RETURN sia utilizzabile secondo MP-004.
3. Preparare e registrare l’unico riferimento.
4. Applicare il controllo MP-005.
5. Se incompatibile, registrare immediatamente il terminale; altrimenti proseguire in WAIT_RESPONSE secondo MP-004.

Una protezione ereditata che termina il child prima della preparazione conserva il proprio motivo. Non viene sostituita da `INITIAL_RESPONSE_INCOMPATIBLE`.

La preparazione e l’eventuale nuovo terminale appartengono alla **stessa dispatch**, con ordine documentato. Al termine della dispatch non deve esistere un’attesa attiva per quel child.

Il terminale è durevole:

- restore, pausa/STEP e ripartenza non riaprono il child;
- nessuna sostituzione del riferimento;
- nessuna successiva classificazione locale C/R;
- nessuna emissione successiva attribuibile al child terminato.

Lo scenario strutturale conserva il proprio ciclo di vita indipendente.

## 6. Reporting

Il riferimento preparato incrementa **P**. Il nuovo terminale incrementa **X**, con motivo e base distinti.

Non incrementa **C, R, N, I o A**.

Restano valide:

\[
P=C+R+X+A,\qquad R=N+I
\]

\[
W=P+\text{terminazioni prima del riferimento}
+\text{WAIT\_RETURN ancora aperti}.
\]

Il conteggio `INITIAL_RESPONSE_INCOMPATIBLE` è un sottoinsieme di X. Un eventuale rapporto usa P come denominatore; denominatore zero significa non definito.

**A è lo stock delle attese aperte al cutoff**, non un conteggio cumulativo delle preparazioni. Il passaggio P→X nella stessa dispatch non produce un’attesa aperta al checkpoint.

L’attribuzione mensile segue la coorte del mese di apertura WAIT, senza reset mensili.

**Perdita informativa dichiarata:** i child terminati alla preparazione non ricevono più le successive classificazioni C/R che avrebbero potuto produrre sotto MP-004. Non si ricostruiscono classificazioni controfattuali. Cambiamenti di C/P e R/P fra versioni non dimostrano miglioramento della risposta locale.

## 7. Convenzioni comuni alle fixture

Le fixture sono manuali e astratte. I prezzi e i tick sono input sintetici, non nuovi parametri del metodo né dati Owner.

Ogni fixture LONG e SHORT è indipendente. Salvo il caso di collisione:

- il child è già in WAIT_RETURN, senza riferimento;
- scenario e contesto sono ammissibili;
- dati e dipendenze sono completi e disponibili;
- nessuna zona o contatto ereditato blocca la preparazione;
- scadenze e tempo residuo consentono gli eventi descritti;
- alla ripresa, selezione libera e nessun altro gate bloccante.

Tutti i tempi sono UTC nella stessa giornata sintetica.

| Barra | Intervallo | Pubblicazione e ammissione | Ordine |
|---|---|---|---|
| B0, riferimento | [10:00, 10:01) | 10:01 | \(c_0\) |
| B1 | [10:01, 10:02) | 10:02 | \(c_1>c_0\) |
| B2 | [10:02, 10:03) | 10:03 | \(c_2>c_1\) |

Ogni barra viene ammessa completa, prima della propria dispatch. Non vi sono ritardi o barre a cavallo di \(p_0\). B1 inizia esattamente a \(p_0\), quindi appartiene al dominio successivo.

I contatori sono mostrati nell’ordine:

\[
(P,X,C,R,N,I,A).
\]

“I=1” significa call emessa; non afferma che il successivo ingresso modellato sia avvenuto.

## 8. Fixture storiche LONG/SHORT

Profilo fisso: **14 bps**, rapporto minimo **1.2**, tick sintetico **1**.

| Direzione | R | K trigger | V strutturale/operativa | Target e cap | Corridoio | Regione economica nel corridoio |
|---|---:|---:|---:|---:|---|---|
| LONG | 95 | 110 | 90 / 90 | 120 | [95,110] | [95,103] |
| SHORT | 105 | 90 | 110 / 110 | 80 | [90,105] | [97,105] |

Non vi sono revisioni del cap.

### H1 — Intersezione vuota per economia storica

| Direzione | B0: O/H/L/C | Estremo contrario | F | Risultato a 10:01 |
|---|---|---:|---|---|
| LONG | 100/103/99/100 | L0=99 | p≥104 | `HISTORICAL_ECONOMICS` |
| SHORT | 100/101/97/100 | H0=101 | p≤96 | `HISTORICAL_ECONOMICS` |

La chiusura 100 rende il RETURN utilizzabile. Il corridoio incontra F, la regione economica no.

Transizione: WAIT_RETURN → riferimento preparato → TERMINAL nella stessa dispatch.

Contatori: **(1,1,0,0,0,0,0)**.

Barre successive:

- LONG B1: **100/104/99/104**;
- SHORT B1: **100/101/96/96**.

Pur soddisfacendo aritmeticamente il predicato locale, non generano R o N: il child è già terminato.

### H2 — Intersezione vuota per corridoio

| Direzione | B0: O/H/L/C | Estremo contrario | F | Risultato a 10:01 |
|---|---|---:|---|---|
| LONG | 100/110/99/100 | L0=99 | p≥111 | `CORRIDOR` |
| SHORT | 100/101/90/100 | H0=101 | p≤89 | `CORRIDOR` |

Il riferimento nasce da un RETURN utilizzabile. Concorre anche l’incompatibilità economica storica, ma la base primaria è `CORRIDOR`.

Contatori: **(1,1,0,0,0,0,0)**.

B1 LONG **100/111/99/111**, B1 SHORT **100/101/89/89**: nessuna successiva classificazione del child.

### H3 — Un solo tick ammesso e uguaglianze

| Direzione | B0: O/H/L/C | F | Intersezione | B1: O/H/L/C |
|---|---|---|---|---|
| LONG | 100/102/99/100 | p≥103 | {103} | 100/103/99/103 |
| SHORT | 100/101/98/100 | p≤97 | {97} | 100/101/97/97 |

A 10:01: WAIT_RESPONSE, contatori **(1,0,0,0,0,0,1)**.

A 10:02:

- chiusura esattamente alla soglia favorevole;
- LONG low=L0=99;
- SHORT high=H0=101;
- prezzo storico sul bordo ammesso della regione economica.

Le uguaglianze sono valide. Con i gate comuni soddisfatti: prima ripresa → unica valutazione → emissione.

Contatori: **(1,0,0,1,0,1,0)**.

### H4 — Collisione con protezione ereditata

Usare B0 e geometria di H1, ma con **setup deadline alle 10:01**.

La scadenza precede la preparazione. Il terminale resta `ORIGINAL_SETUP_DEADLINE`.

Contatori: **(0,0,0,0,0,0,0)**; incrementa la categoria delle terminazioni prima del riferimento nell’identità W.

B1 come H1: nessuna preparazione tardiva e nessuna riapertura.

### H5 — Persistenza e perdita delle classificazioni

Usare H1. Dopo il terminale delle 10:01, effettuare un checkpoint e un restore logico prima dell’ammissione di B1.

Ammettere:

- LONG B1 **100/101/98/100**, B2 **100/104/99/104**;
- SHORT B1 **100/102/99/100**, B2 **100/101/96/96**.

B1 supera l’estremo contrario originario; B2 soddisfa la soglia favorevole. Nessuna delle due produce C o R per il child già terminato.

Dopo entrambe le dispatch: **(1,1,0,0,0,0,0)**. Lo scenario resta soggetto soltanto alle proprie regole.

## 9. Fixture live LONG/SHORT

Tick sintetico **0.01**. Fee **5 bps per lato**, slippage **2 bps per lato**, half-spread secondo formula registrata; rapporto minimo **1.2**.

| Direzione | R | K trigger | V strutturale/operativa | Target e cap | Corridoio |
|---|---:|---:|---:|---:|---|
| LONG | 100.00 | 100.20 | 99.80 / 99.80 | 100.70 | [100.00,100.20] |
| SHORT | 100.00 | 99.80 | 100.20 / 100.20 | 99.30 | [99.80,100.00] |

In ogni dispatch viene ammessa la barra completa, poi la quotazione indicata, infine eseguita la decisione. La quotazione è fresca, disponibile alla decisione e conforme alle condizioni ereditate.

### L1 — Preparazione utilizzabile

B0, entrambe le direzioni: **100.00/100.01/99.99/100.00**.

Alle 10:01, bid/ask **99.99/100.01**:

- midpoint=100;
- half-spread=1 bps;
- costo live=15 bps;
- LONG valuta ask=100.01;
- SHORT valuta bid=99.99.

Entrambi i prezzi soddisfano l’economia e appartengono al rispettivo corridoio; anche la chiusura 100.00 appartiene al corridoio. La preparazione è quindi utilizzabile secondo MP-004.

- LONG: L0=99.99, F≥100.02;
- SHORT: H0=100.01, F≤99.98.

F incontra entrambi i corridoi. Nessun terminale MP-005.

Contatori: **(1,0,0,0,0,0,1)**.

### L2 — Restrizione temporanea durante WAIT_RESPONSE

B1, entrambe le direzioni: **100.00/100.01/99.99/100.00**.

Alle 10:02, bid/ask **99.80/100.20**:

- midpoint=100;
- half-spread=20 bps;
- costo live=34 bps.

La regione economica corrente nel corridoio è vuota in entrambe le direzioni. I prezzi side restano sui rispettivi bordi del corridoio.

B1 non conferma e non contraddice: LONG low=L0, SHORT high=H0. La restrizione economica non genera il nuovo terminale.

Contatori invariati: **(1,0,0,0,0,0,1)**.

### L3 — Costi ripristinati e prima ripresa

Alle 10:03:

| Direzione | B2: O/H/L/C | Bid/ask | Prezzo valutato |
|---|---|---|---:|
| LONG | 100.00/100.04/100.00/100.03 | 100.02/100.04 | ask=100.04 |
| SHORT | 100.00/100.00/99.96/99.97 | 99.96/99.98 | bid=99.96 |

Il costo torna vicino a 15 bps secondo la formula esatta, senza sostituzione con un valore arrotondato. I rapporti netti sono superiori a 1.2.

Le chiusure confermano F, gli estremi contrari non sono violati e prezzi side e chiusure restano nei corridoi.

Con i gate comuni soddisfatti: prima ripresa → unica valutazione → emissione.

Contatori: **(1,0,0,1,0,1,0)**.

La fixture mostra una preparazione valida seguita da una restrizione temporanea. Non introduce una preparazione con economia già inammissibile.

## 10. Esito della verifica semantica

Le fixture non introducono contraddizioni con il delta ratificato. In particolare:

- il live prepara il riferimento prima della restrizione temporanea;
- l’uguaglianza e il singolo tick non vengono scambiati per insieme vuoto;
- le protezioni ereditate conservano precedenza;
- i terminali iniziali restano P→X, senza successive classificazioni C/R;
- praticabilità geometrica e valore informativo della risposta restano distinti.
