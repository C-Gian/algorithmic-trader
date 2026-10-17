# OBS-002 — prosecuzione ed esaurimento del primo tentativo di ripresa (DEV 2023–2024)

**Stato: correzioni R1 consegnate dall'esecutore (DELIVERED, in attesa di review del Director; non ACCEPTED).** Sezione 11 per R1. La sezione 1 è quella pubblicata nel commit `118f706`, prima degli esiti; il resto è stato aggiunto dopo l'estrazione. Il report descrive evidenze: non sceglie ipotesi, soglie o gruppi.

**Licenza di questo file:** derivati aggregati di dati Binance Vision, **CC BY-NC-SA 4.0** (https://creativecommons.org/licenses/by-nc-sa/4.0/). Fonte: Binance Vision (https://data.binance.vision). Dati grezzi, registri e pacchetti non sono redistribuiti.

## 1. Preregistrazione e identità prima degli esiti

- Incarico: `current_task.md` al commit `6f1743d`; convenzioni `config/OBS-002-v1.json`, SHA256 canonico `b11bad4557cbe45063b7beaf2026d53d63b17cbb944ada2e226a31d6d2a2d0af`; osservatore OBS-001/v1 invariato `3c4eb884d0b6752bfb31e7d9ae159a1414d75cadc90f9abcc9379d5825002387`.
- Codice e 15 test sintetici pubblicati nel commit `36f6153`, prima di elaborare dati reali.
- Input: 27 ZIP trade 1m Binance Vision BTCUSDT perpetual, mesi elencati esplicitamente 2022-10…2024-12, già conservati nella cartella CAND-001 e verificati sul manifest e sul checksum del fornitore. inputHash `3b768886424b4907ef3fb794d9c1e3f565d2f7d28f023e3658763b297db24a5e`; 1.185.120 minuti validi su 1.185.120. Nessun download, nessun mese 2025/2026.
- **Popolazione e snapshot (senza esiti):** run `OBS-002-v1.0.0-e1.0.0-3b76888642-b11bad4557`, `population.json` SHA256 `e0be48abf1c5ea63343f16fdd271493bce716a34009e942b7ff2397521b4a278`. 6.568 versioni, 5.698 gruppi, 7.389 tentativi nell'intero input, di cui 6.582 con origine DEV. Hash dell'identità (config, osservatore, motore, input) `67edb71f5d5b55bc6e3430373b7c6f760a916fdd4ebd896265065df819447a7b`.
- Il comando degli esiti ricalcola la popolazione e si ferma se l'hash non coincide con quello qui registrato.
- Regola degli esempi: quella del task §6, applicata dal codice di `36f6153` (`src/obs002/examples.py`). L'elenco effettivo è nella sezione 5.

## 2. Che cosa è stato implementato

Codice `src/obs002/` (pacchetto nuovo; osservatore OBS-001/v1, CAND-001 e i loro risultati non toccati né eseguiti).

**Popolazione causale** (`population.py`). A ogni chiusura 45m, in quest'ordine:
1. azzeramento di segmento, che ritira entrambi i contesti;
2. eventi FIB_SEQUENCE APPEND/REPLACE disponibili in quella chiusura, che creano una versione con ancore e disponibilità congelate e ritirano la versione precedente dello stesso verso;
3. tentativi.

Un movimento del verso opposto coesiste con quello attivo. I gruppi sono identificati da (verso, P0.candidateOpen): un REPLACE con lo stesso P0 conserva gruppo e contatore.

Il tentativo è definito così:
- arretramento: almeno una chiusura contro il verso dopo la candela di P1 e, se il gruppo ha già un tentativo, dopo quel tentativo (riarmo);
- trigger: C_k oltre l'estremo della barra precedente e oltre la propria apertura;
- barre complete nello stesso segmento;
- t ≥ disponibilità della versione, inclusa;
- nessun vincolo CAND: struttura, 3A, 32 barre, profondità, scadenza, ritocco di P1, rapporto, guard, 60 s, costi, occupazione.

Contesti e contatori sono inizializzati dal 2022-10-01; le origini dell'inizializzazione non entrano nella popolazione. Alla fine del DEV le versioni attive terminano con `END_OF_STUDY`, conclusione amministrativa.

**Snapshot** (stesso modulo). Un record per tentativo, con ogni misura come valore oppure motivo mancante:
- identità, ancore, arretramento (Rext, profondità senza limiti, barre da P1, chiusure contro) e trigger;
- struttura 45m e ultimo 1D concluso entro t;
- tutti i livelli pivot e del giorno, con distanza firmata d·(livello − C)/A e il più vicino davanti e dietro;
- SMA20/50, d·distanza, d·pendenza, d·posizione e incrocio relativo al verso;
- volume relativo con base e mediana;
- A, A/C, L/A, distanza residua a P1 e a Rext;
- Fibonacci effettivo dell'osservatore a t: versione, ancore, u, r, livelli, relazione col verso e coincidenza con il contesto.

Profilo congiunto a quattro classi (task §3), dalle misure dell'osservatore `piv.structure`, `avg.dist` e `avg.slope`.

**Seguito 24h** (`outcomes.py`, mai input della popolazione). Minuti [t, t+1440 min); final, favorevole e contrario in unità di A_t. Riferimenti C_t ± A con primo contatto a 1m e sei classi. Nello stesso minuto l'ordine vale solo se l'apertura è già sul riferimento, altrimenti `BOTH_UNORDERED`. Flag `RIGHT_CENSORED`, `GAP`, `MISSING_A`, `ZERO_A`; il prefisso parziale noto è registrato separatamente.

**Tabelle** (`summary.py`, `tables.py`): schema unico verso × profilo, periodi, mesi, riepilogo secondario dipendente, flusso e dipendenza. **Esempi** (`examples.py`): regola del §6. **Pacchetti di consultazione** (`consult.py`): un file per caso.

**Lettore** (dashboard, adattamento tecnico §6). Il validatore accetta anche `OBS002_CASE` / `obs002.case/1`:
- identità OBS-002, caso compreso fra le origini, esito coerente;
- tabulazione OBS-001 obbligatoriamente assente (`summary: null`);
- i bundle OBS-001 si aprono come prima.

Nelle viste:
- l'intestazione mostra il caso e il pulsante «Vai al caso»;
- il momento iniziale è quello del caso;
- il seguito retrospettivo esistente aggiunge, solo per l'istante del caso, il blocco OBS-002 nel verso del movimento;
- la voce «Studio osservativo» spiega che la tabulazione OBS-001 non è pertinente e rimanda a questo report.

Nessun nuovo ambiente, filtro, pagina o restyling.

## 3. Riconciliazioni, controlli e riproducibilità

**Comando unico riproducibile:**
`$env:PYTHONPATH = "src"; python3.12 -m obs002 population` poi `python3.12 -m obs002 outcomes`. Circa 16 s + 21 s. Output in `C:\Projects\algorithmic-trader-data\OBS-002\runs\OBS-002-v1.0.0-e1.0.0-3b76888642-b11bad4557\`.

**Codice dell'estrazione finale:** commit `7cad393`, checkout pulito (`provenance-outcomes.json`); `outputs.json` SHA256 `25e6e2daff8cf574efa6842ad52fcc4ce85ebe127fec8262c45b7c22d3ce458b`, identico all'esecuzione precedente al commit. La popolazione era stata calcolata dal commit pulito `36f6153`.

**Popolazione prima degli esiti:**
- registrata nel commit `118f706` (§1);
- il comando degli esiti ricalcola la popolazione e verifica hash e identità: coincidenti.

**Riconciliazioni nel comando** (si ferma alla prima discrepanza):
- primi + ripetuti = tentativi DEV (4.372 + 2.210 = 6.582);
- versi, profili, classi + incompleti e disponibilità delle coordinate ricostruiscono ogni cella;
- la somma dei mesi ricostruisce la popolazione;
- identità dei tentativi uniche.

**Riscontro fra due implementazioni sull'intera popolazione.** Per ciascuno dei 6.582 tentativi DEV, final, favorevole e contrario OBS-002 coincidono (|Δ| ≤ 1e-9, a meno del segno del verso) con il seguito 24h OBS-001 esistente (`outcome_for`) allo stesso istante, compresa la completezza.

**Determinismo:**
- due esecuzioni consecutive di `outcomes` hanno dato `outputs.json` identico byte per byte;
- dopo la prima estrazione ho aggiunto solo questo riscontro e la formattazione delle tabelle: tutti gli output sono rimasti identici, tranne `summary.json` (solo il campo del riscontro, verificato) e il nuovo `results-tables.md`.

**Hash degli output** (`outputs.json` del run):

| File | SHA256 |
|---|---|
| `population.json` | `e0be48abf1c5ea63343f16fdd271493bce716a34009e942b7ff2397521b4a278` |
| `outcomes.json` | `2604441548e0fc2ae4b98836f7f6c79d23b38b9b3254e22a28ba4f91c170a817` |
| `summary.json` | `db08662468bba2bdd6218758b396cb69ea62a245610740e58551bcf0a478813e` |
| `examples.json` (lista e timeline) | `507c2bf3a6979174bbfe5d7d18c67a88c5d5cee71072c162b8b43a34ca0ad60b`; `listSha256` `feb69ba86f2dcc15f50508a1840fcb9887ff125ed59f634bf96ce2aa2289f7f6` |
| `attempts-register.csv` (snapshot, causale) | `936e53c35f46fef38f6e2c84aa13a37b6ebcebfe623d84cf54304738037f3889` |
| `outcomes.csv` (a posteriori, separato) | `f96fa34a4e084c8668064f604029c83fd340b0f8e928834ede32f741062e5003` |
| `versions.csv` | `7fb6f689b6aaf531b4423aac11e4495458b855f602435c1031befdeb2e42bed8` |
| `results-tables.md` | `1480f9674ca30a30997b411cea2c97287c589ac8a62d7fe4bc4bbe1cb8778aa5` |

Pacchetti dei casi: hash in `outputs.json`. Provenienza, commit e orari sono in `provenance-*.json`, separati dagli output numerici.

**Test.** `tests/test_obs002.py`: 15 test sintetici, pubblicati prima degli esiti. Coprono:
- simmetria LONG/SHORT;
- tentativo ammesso a t0 ma mai prima della disponibilità;
- arretramento, continuazione e riarmo;
- REPLACE nello stesso gruppo e nuovo P0 in un nuovo gruppo;
- coesistenza dei versi e azzeramento;
- ordinal nell'inizializzazione;
- assenza dei vincoli CAND (struttura opposta, profondità > 1);
- eventi degeneri registrati;
- dati futuri alterati che non cambiano popolazione e snapshot fino al cutoff (osservatore reale);
- quattro profili;
- finestra 24h con primo e ultimo minuto inclusi e minuto successivo escluso;
- contatti nello stesso minuto con e senza apertura che ordina;
- NEITHER, censura, lacuna, A mancante e A zero;
- celle riconciliate, categorie vuote e ordine degli esempi.

Lettore: `Obs002Case.test.tsx` (4 test) più i test storici esistenti `Historical`/`R1`, 24 test passati; typecheck e build passati. Le tracce d'errore in console vengono da `R1.test.tsx`, che corrompe apposta un bundle per provare il contenimento. Nessuna suite generale, niente CI.

**Prova visiva** su due pacchetti reali (1366 px, Chrome headless), schermate in `docs/research/OBS-002-screens/`. Durante la prova ho corretto due testi fuorvianti: un caso ripetuto non è più chiamato «primo tentativo», e i riferimenti sono indicati come favorevole F / contrario A invece di «+A / −A», che per lo SHORT era ambiguo.

## 4. Che cosa mostrano le tabelle (descrizione, senza interpretazione)

Tabelle complete nella sezione 9. Sono letture descrittive su DEV già esposto: nessuna significatività, causalità o soglia.

- **Popolazione.**
  - 4.372 primi tentativi DEV (LONG 2.228, SHORT 2.144) e 2.210 tentativi ripetuti dipendenti.
  - Profili: DISCORDANT è la maggioranza (LONG 1.541, SHORT 1.454); CONCORDANT 330 / 255, OPPOSITE 357 / 435.
  - UNAVAILABLE è vuoto in DEV: le medie sono già calcolabili dall'inizializzazione e non ci sono lacune.
- **Completezza.** 4.368 esiti completi; 4 censurati a destra a fine dicembre 2024; nessuna lacuna o A mancante.
- **Dipendenza.**
  - Tutte le finestre 24h dei primi tentativi si sovrappongono ad almeno un'altra, con fino a 12 finestre contemporanee: le numerosità non sono prove indipendenti.
  - 1.596 gruppi hanno più di un tentativo DEV.
- **Classi di contatto ±A** (frase corretta in R1). Sui 4.368 esiti completi dei primi tentativi:
  - entrambi i riferimenti toccati in 2.430 casi (55,6%): F→A, A→F o F=A;
  - uno solo in 1.900 (43,5%): F o A;
  - nessuno in 38 (0,9%).

  Quasi universale è quindi **almeno un** contatto (4.330, 99,1%), non entrambi. Le classi informano sia su uno/entrambi/nessuno, sia sull'ordine quando entrambi sono raggiunti; BOTH_UNORDERED è rarissimo (4). Scomposizione per cella nella sezione 11. *Testo consegnato a `c8ac744`, errato:* «un'unità di A a 45m è quasi sempre raggiunta in 24 ore in entrambe le direzioni».
- **Esiti.**
  - Il final mediano è vicino a zero in tutte le celle (fra −0,31 e +0,18 A), con P10–P90 ampi (circa da −5 a +6 A).
  - Le escursioni mediane, favorevole e contraria, sono entrambe intorno a 2,2–2,6 A.
- **Coordinate.**
  - Distanze e pendenze SMA differiscono fra i profili **per costruzione**, perché li definiscono.
  - Nei primi tentativi OPPOSITE la profondità mediana è maggiore (LONG 1,34, SHORT 1,38, contro 0,63/0,65 in CONCORDANT) e L/A è minore (1,93/1,80 contro 3,45/3,36).
  - Volume relativo, r Fibonacci e struttura 1D hanno mediane simili fra i profili.
  - Queste sono differenze marginali: non indicano da sole una combinazione utile.
- **Conseguenza della definizione da tenere presente.**
  - Una versione resta attiva anche mentre si forma il movimento opposto (§2 del task). Per questo 853 primi tentativi LONG su 2.228 e 875 SHORT su 2.144 hanno profondità > 1: l'arretramento ha superato P0.
  - 565 LONG e 494 SHORT hanno già ritoccato P1; 372 LONG e 289 SHORT hanno l'origine già oltre P1.
  - È la popolazione preregistrata, non un difetto. La riporto perché «ripresa» qui include casi lontani dalla figura di una semplice reazione.
- **Fibonacci.** Le ancore correnti sono concordi col movimento quasi esattamente quando coincidono con quelle del contesto (LONG sempre; SHORT tranne un caso).

## 5. Esempi (regola fissata prima, elenco dopo l'estrazione)

10 casi, `listSha256` `feb69ba8…f7f6`. **Categorie vuote:** `FIRST_LONG_UNAVAILABLE` e `FIRST_SHORT_UNAVAILABLE`, perché nessun primo tentativo DEV ha profilo indisponibile; non sono state sostituite.

Valori: final, favorevole e contrario in A nel verso del movimento; d = distanza.

1. **LONG DISCORDANT, primo cronologico** (`ATT:LONG:1672477200000:1672539300000`, 2023-01-01 02:15).
   - *Noto a t:* versione 16.538,0 → 16.640,0 disponibile dal 31/12 16:30; C 16.547,0; arretramento fino a 16.461,8, profondità 1,75, cioè sotto P0 durante il movimento opposto. Struttura 45m DOWN, 1D MIXED.
   - *Dopo:* A→F; final +0,66, favorevole 2,16, contrario 1,77.
2. **SHORT DISCORDANT, primo cronologico** (`ATT:SHORT:1672496100000:1672544700000`, 2023-01-01 03:45; stesso istante del primo trade CAND v1).
   - *Noto a t:* 16.640,0 → 16.461,8, profondità 0,53; struttura DOWN, ma ordine SMA contrario e pendenza a favore.
   - *Dopo:* F→A; final −2,04, favorevole 1,22, contrario 2,63.
3. **LONG OPPOSITE, primo cronologico e primo OPPOSITE con final > 0** (`ATT:LONG:1672525800000:1672552800000`, 2023-01-01 06:00).
   - *Noto a t:* 16.461,8 → 16.557,1, profondità 0,52; struttura DOWN e medie contrarie.
   - *Dopo:* A→F; final +3,85, favorevole 5,90, contrario 1,27. **Caso contrario al profilo.**
4. **SHORT CONCORDANT, primo tentativo ripetuto** (`ATT:SHORT:1672496100000:1672558200000`, 2023-01-01 07:30, n. 2 del movimento del caso 2).
   - *Noto a t:* volume relativo 2,62; profilo diventato CONCORDANT.
   - *Dopo:* A soltanto; final −7,06, favorevole 0,63, contrario 8,37.
5. **LONG CONCORDANT, primo cronologico** (`ATT:LONG:1672585200000:1672614900000`, 2023-01-01 23:15; lo stesso momento è un'astensione per rapporto in CAND v1).
   - *Noto a t:* P1 a 0,30 A davanti, profondità 0,42.
   - *Dopo:* A→F; final +4,11, favorevole 7,82, contrario 2,94.
6. **SHORT OPPOSITE, primo cronologico** (`ATT:SHORT:1672604100000:1672620300000`, 2023-01-02 00:45).
   - *Noto a t:* L/A 1,61, profondità 0,99, P1 già ritoccato; strutture 45m e 1D UP.
   - *Dopo:* F→A; final −4,60, favorevole 1,73, contrario 8,70.
7. **Primo CONCORDANT con final ≤ 0** (`ATT:LONG:1672793100000:1672814700000`, 2023-01-04 06:45; stesso istante del primo trade CAND positivo).
   - *Noto a t:* profondità 0,28, P1 a 1,25 A.
   - *Dopo:* F→A; final −1,02, favorevole 3,19, contrario 2,25. **Caso contrario al profilo.**
8. **SHORT CONCORDANT, primo cronologico** (`ATT:SHORT:1674407700000:1674445500000`, 2023-01-23 03:45).
   - *Noto a t:* profondità 0,80, struttura 1D UP.
   - *Dopo:* A→F; final −2,04, favorevole 1,10, contrario 2,87.
9. **Primo BOTH_UNORDERED completo** (`ATT:SHORT:1683250200000:1683271800000`, 2023-05-05 07:30, profilo OPPOSITE).
   - *Noto a t:* C già oltre P1 (−0,24 A), volume relativo 2,02.
   - *Dopo:* F e A toccati entrambi nel minuto 12:30 con apertura fra i due: ordine non ricostruibile. Final −2,14, favorevole 3,39, contrario 5,29.
10. **Primo RIGHT_CENSORED** (`ATT:SHORT:1735589700000:1735608600000`, 2024-12-31 01:30, DISCORDANT).
    - Le 24 ore superano il 2025-01-01: nessun esito completo, solo il prefisso parziale nel JSON. Nessun dato 2025 letto.

Timeline complete (versioni del gruppo note a t, tentativi precedenti, barre 45m da P0 a t, snapshot, poi esito separato): usare il derivato corretto `R1/examples.json` (sezione 11). L'originale `examples.json` è conservato, ma la sua sezione «noto a t» mostrava fatti futuri sulla sostituzione delle versioni.

## 6. Come consultare gli esempi

1. Dalla cartella `dashboard`: `npm run dev` (oppure `npm run dev:ui` per la sola interfaccia), quindi apri l'indirizzo mostrato.
2. In alto scegli **Studio storico** → **Apri studio storico**.
3. Scegli un file in `C:\Projects\algorithmic-trader-data\OBS-002\runs\OBS-002-v1.0.0-e1.0.0-3b76888642-b11bad4557\cases\`. I nomi seguono l'ordine della sezione 5: `01-LONG-…` … `10-SHORT-…`.
4. Il lettore si apre al momento del caso. **Mostra seguito retrospettivo 24h** aggiunge ciò che è successo dopo, con il blocco OBS-002. «Chiusura precedente/successiva» scorre le chiusure attorno al caso; **Vai al caso** torna all'istante.

Ogni file pesa circa 4,3 MB: 35 giorni di osservazioni, calcolate su tutto il prefisso dal 2022-10-01 e poi ritagliate.

## 7. Punti tecnici da confermare (scelte mie dove il testo non entrava nel dettaglio)

1. Un evento APPEND/REPLACE escluso (L ≤ 0: 6 casi; ancore mancanti: 1, nell'inizializzazione) **non** ritira la versione attiva dello stesso verso, perché non è un nuovo movimento.
2. Arretramento e riarmo sono valutati insieme come «almeno una chiusura contro il verso dopo max(candela di P1, ultimo tentativo del gruppo)». È equivalente alle due condizioni del task, che sono suffissi della stessa serie. La prima chiusura contro può confrontarsi con la chiusura della candela di P1.
3. Profilo congiunto: dalle misure dell'osservatore `avg.dist` e `avg.slope`, normalizzate per A, quindi indisponibili se A = 0 (nessun caso in DEV).
4. Livello più vicino: scelto sulla distanza grezza d·(prezzo − C), che non dipende da A; a parità, prima `kind` e poi `id`.
5. «Ancore Fibonacci = contesto»: confronto sulle candele di P0 e P1.
6. Il contatore di un gruppo nato nell'inizializzazione prosegue: un solo gruppo con tentativi DEV è nato prima del DEV, e il suo primo tentativo cade in DEV (ordinal 1). Nessun ripetuto DEV ha tentativi nell'inizializzazione.
7. Pacchetti: righe del seguito OBS-001 per tutte le origini selezionabili (stesso calcolo della vista esistente); esito OBS-002 solo per il caso. Riepilogo OBS-001 assente per scelta del task, non ricalcolato.

## 8. Limiti

- Esplorazione su DEV 2023–2024 già esposto: nessuna efficacia, validazione o regola operativa. Gli esiti sono spostamenti di prezzo normalizzati, non profitti; nessun costo o esecuzione.
- Tentativi molto dipendenti: finestre 24h sovrapposte, più tentativi per movimento, i due versi coesistenti.
- Risoluzione 1m: l'ordine dentro il minuto non si ricostruisce (4 casi `BOTH_UNORDERED` fra i primi tentativi).
- Con riferimenti ±1 A su 24 ore quasi tutti i casi toccano almeno un riferimento (99,1%), poco più della metà li tocca entrambi (55,6%). Le classi descrivono quindi sia quale riferimento è raggiunto sia, quando lo sono entrambi, l'ordine. Vanno lette insieme a final ed escursioni, come chiede il task; nessun altro livello o orizzonte è stato provato. *Corretto in R1:* la consegna diceva che «quasi tutti i casi toccano entrambi i riferimenti».
- La popolazione include molti tentativi con arretramento oltre P0 o origine oltre P1, per la definizione preregistrata (sezione 4).
- I prefissi parziali dei 4 casi censurati sono solo nei JSON, non nelle tabelle.
- Lavoro e riscontri dello stesso esecutore; il riscontro con OBS-001 confronta due implementazioni nel repository, non una verifica indipendente del Director.

## 9. Tabelle complete (generate da `summary.json`, file `results-tables.md` del run)

#### Flusso della popolazione

| Voce | Valore |
|---|---|
| Eventi FIB_SEQUENCE (APPEND / REPLACE / KEEP), input | 5705 / 870 / 613 |
| Esito degli eventi, input | ANCHORS_MISSING 1 · L_NOT_POSITIVE 6 · NO_VERSION 613 · VERSION 6568 |
| Esito degli eventi, DEV | L_NOT_POSITIVE 6 · NO_VERSION 535 · VERSION 5826 |
| Versioni create (input / con disponibilità in DEV) | 6568 / 5826 |
| Versioni per motivo di ritiro (input) | END_OF_STUDY 2 · NEW_VERSION_SAME_DIRECTION 6566 |
| Versioni senza alcun tentativo (input / DEV) | 1102 / 972 |
| Gruppi (input) · iniziati prima del DEV | 5698 · 637 |
| Gruppi senza alcun tentativo (input) | 779 |
| Gruppi attivi in DEV · senza tentativo DEV | 5063 · 691 |
| Gruppi con tentativo DEV · di cui iniziati prima del DEV | 4372 · 1 |
| Tentativi: input / inizializzazione / DEV | 7389 / 807 / 6582 |
| Tentativi DEV: primi (ordinal 1) / ripetuti | 4372 / 2210 |
| Ripetuti DEV con tentativi precedenti nell'inizializzazione | 0 |
| Primi tentativi DEV per verso | LONG 2228 · SHORT 2144 |
| Tentativi DEV per ordinal (5 = 5 o più) | 1: 4372 · 2: 1596 · 3: 460 · 4: 119 · 5: 35 |

#### Dipendenza

- Primi tentativi DEV: 4372, di cui con finestra 24h sovrapposta ad almeno un altro: 4372; massimo di finestre contemporanee 12.
- Tutti i tentativi DEV: 6582, sovrapposti 6582, massimo contemporanee 16.
- Gruppi con tentativi DEV: 4372; tentativi per gruppo: 1: 2776 · 2: 1136 · 3: 341 · 4: 89 · 5: 27 · 6: 2 · 8: 1.

#### Tabella principale: primi tentativi DEV (ordinal 1), verso × profilo congiunto

Classi di contatto ±A: F = solo favorevole, A = solo contrario, F→A / A→F = ordine a risoluzione 1m, F=A = stesso minuto non ordinabile, nessuno = finestra completa senza contatti. final, favorevole, contrario in unità di A all'origine.

| Verso | Profilo | Tentativi | Gruppi | Completi | Censurati / lacune / A mancante / A zero | F | A | F→A | A→F | F=A | nessuno | final P50 [P10; P90] | favorevole | contrario |
|---|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---|---|---|
| LONG | Tutti | 2228 | 2228 | 2227 | 1 / 0 / 0 / 0 | 528 | 436 | 614 | 624 | 3 | 22 | 0,11 [-4,63; 5,76] | 2,56 [0,48; 8,56] | 2,39 [0,43; 7,72] |
| LONG | CONCORDANT | 330 | 330 | 330 | 0 / 0 / 0 / 0 | 72 | 62 | 96 | 99 | 0 | 1 | -0,05 [-4,34; 7,77] | 2,59 [0,48; 9,90] | 2,51 [0,44; 8,02] |
| LONG | OPPOSITE | 357 | 357 | 357 | 0 / 0 / 0 / 0 | 93 | 76 | 85 | 98 | 0 | 5 | 0,05 [-4,42; 4,39] | 2,19 [0,45; 7,24] | 2,45 [0,36; 8,19] |
| LONG | DISCORDANT | 1541 | 1541 | 1540 | 1 / 0 / 0 / 0 | 363 | 298 | 433 | 427 | 3 | 16 | 0,18 [-4,69; 5,76] | 2,62 [0,49; 8,58] | 2,36 [0,45; 7,53] |
| LONG | UNAVAILABLE | 0 | 0 | 0 | 0 / 0 / 0 / 0 | 0 | 0 | 0 | 0 | 0 | 0 | n=0 | n=0 | n=0 |
| SHORT | Tutti | 2144 | 2144 | 2141 | 3 / 0 / 0 / 0 | 428 | 508 | 617 | 571 | 1 | 16 | -0,23 [-5,65; 4,67] | 2,37 [0,42; 7,86] | 2,53 [0,50; 8,34] |
| SHORT | CONCORDANT | 255 | 255 | 255 | 0 / 0 / 0 / 0 | 43 | 70 | 80 | 61 | 0 | 1 | -0,31 [-4,78; 5,44] | 2,28 [0,38; 8,62] | 2,42 [0,78; 6,32] |
| SHORT | OPPOSITE | 435 | 435 | 433 | 2 / 0 / 0 / 0 | 93 | 96 | 122 | 120 | 1 | 1 | -0,08 [-6,29; 4,53] | 2,35 [0,40; 7,44] | 2,62 [0,41; 8,57] |
| SHORT | DISCORDANT | 1454 | 1454 | 1453 | 1 / 0 / 0 / 0 | 292 | 342 | 415 | 390 | 0 | 14 | -0,26 [-5,79; 4,64] | 2,40 [0,43; 7,84] | 2,52 [0,50; 8,66] |
| SHORT | UNAVAILABLE | 0 | 0 | 0 | 0 / 0 / 0 / 0 | 0 | 0 | 0 | 0 | 0 | 0 | n=0 | n=0 | n=0 |

#### Profilo simultaneo delle coordinate, LONG (primi tentativi DEV)

P50 [P10; P90]; categorie con conteggio e quota sulla cella. Distanze firmate d·(livello − C)/A: positive davanti nel verso del movimento.

| LONG: coordinata all'origine | Tutti (n=2228) | CONCORDANT (n=330) | OPPOSITE (n=357) | DISCORDANT (n=1541) | UNAVAILABLE (n=0) |
|---|---|---|---|---|---|
| Profondità dell'arretramento | 0,83 [0,38; 2,31] | 0,63 [0,31; 1,06] | 1,34 [0,43; 3,76] | 0,84 [0,40; 2,20] | — |
| L / A | 2,28 [1,18; 4,32] | 3,45 [1,99; 5,90] | 1,93 [1,02; 3,06] | 2,20 [1,16; 4,07] | — |
| Distanza residua a P1 / A | 0,67 [-0,25; 2,47] | 0,67 [-0,45; 2,04] | 0,80 [-0,04; 3,07] | 0,64 [-0,27; 2,48] | — |
| Distanza a Rext / A | -1,30 [-2,37; -0,69] | -1,33 [-2,29; -0,70] | -1,51 [-2,50; -0,77] | -1,26 [-2,34; -0,67] | — |
| A / C | 0,0055 [0,0027; 0,0094] | 0,0055 [0,0028; 0,0088] | 0,0058 [0,0031; 0,0098] | 0,0054 [0,0027; 0,0092] | — |
| Livello più vicino davanti / A | 0,81 [0,16; 2,64] · mancanti 89 | 0,75 [0,17; 1,88] · mancanti 32 | 0,84 [0,18; 2,99] · mancanti 1 | 0,81 [0,16; 2,78] · mancanti 56 | — |
| Livello più vicino dietro / A | -1,17 [-2,56; -0,25] · mancanti 32 | -1,26 [-3,04; -0,41] | -1,34 [-2,33; -0,18] · mancanti 13 | -1,11 [-2,53; -0,25] · mancanti 19 | — |
| d·(SMA20−SMA50)/A | 0,09 [-1,70; 2,03] | 1,12 [0,22; 2,59] | -1,02 [-2,24; -0,23] | 0,14 [-1,55; 1,99] | — |
| d·pendenza SMA20 / A | -0,04 [-0,61; 0,59] | 0,45 [0,13; 0,95] | -0,44 [-0,89; -0,13] | -0,03 [-0,52; 0,49] | — |
| d·(C−SMA20)/A | 0,30 [-0,99; 1,85] | 1,35 [0,34; 3,19] | -0,47 [-1,75; 0,41] | 0,29 [-0,90; 1,64] | — |
| Volume relativo | 1,01 [0,46; 2,88] | 1,11 [0,53; 3,49] | 1,05 [0,46; 2,57] | 0,98 [0,46; 2,88] | — |
| Fibonacci r effettivo | 0,39 [-0,05; 0,95] | 0,35 [-0,07; 0,81] | 0,36 [-0,01; 0,88] | 0,40 [-0,05; 1,02] | — |
| Struttura 1D | UP 861 (39%) · MIXED 844 (38%) · DOWN 523 (23%) | MIXED 129 (39%) · UP 125 (38%) · DOWN 76 (23%) | UP 150 (42%) · MIXED 132 (37%) · DOWN 75 (21%) | UP 586 (38%) · MIXED 583 (38%) · DOWN 372 (24%) | — |
| Tipo del livello davanti | PIVOT_HIGH 1451 (65%) · DAY_HIGH 491 (22%) · DAY_LOW 114 (5%) · NONE 89 (4%) · PIVOT_LOW 83 (4%) | PIVOT_HIGH 189 (57%) · DAY_HIGH 106 (32%) · NONE 32 (10%) · PIVOT_LOW 3 (1%) | PIVOT_HIGH 247 (69%) · DAY_LOW 60 (17%) · DAY_HIGH 39 (11%) · PIVOT_LOW 10 (3%) · NONE 1 (0%) | PIVOT_HIGH 1015 (66%) · DAY_HIGH 346 (22%) · PIVOT_LOW 70 (5%) · NONE 56 (4%) · DAY_LOW 54 (4%) | — |
| Tipo del livello dietro | PIVOT_LOW 1346 (60%) · DAY_LOW 349 (16%) · PIVOT_HIGH 345 (15%) · DAY_HIGH 156 (7%) · NONE 32 (1%) | PIVOT_LOW 211 (64%) · DAY_HIGH 74 (22%) · PIVOT_HIGH 42 (13%) · DAY_LOW 3 (1%) | PIVOT_LOW 159 (45%) · DAY_LOW 139 (39%) · PIVOT_HIGH 45 (13%) · NONE 13 (4%) · DAY_HIGH 1 (0%) | PIVOT_LOW 976 (63%) · PIVOT_HIGH 258 (17%) · DAY_LOW 207 (13%) · DAY_HIGH 81 (5%) · NONE 19 (1%) | — |
| Livello esattamente a C | NO 2227 (100%) · YES 1 (0%) | NO 330 (100%) | NO 357 (100%) | NO 1540 (100%) · YES 1 (0%) | — |
| Incrocio SMA alla barra | NONE 2171 (97%) · IN_DIRECTION 36 (2%) · AGAINST 21 (1%) | NONE 315 (95%) · IN_DIRECTION 15 (5%) | NONE 346 (97%) · AGAINST 11 (3%) | NONE 1510 (98%) · IN_DIRECTION 21 (1%) · AGAINST 10 (1%) | — |
| Ancore Fibonacci vs movimento | CONCORDANT 1232 (55%) · OPPOSITE 996 (45%) | CONCORDANT 199 (60%) · OPPOSITE 131 (40%) | CONCORDANT 199 (56%) · OPPOSITE 158 (44%) | CONCORDANT 834 (54%) · OPPOSITE 707 (46%) | — |
| Ancore Fibonacci = contesto | SAME 1232 (55%) · DIFFERENT 996 (45%) | SAME 199 (60%) · DIFFERENT 131 (40%) | SAME 199 (56%) · DIFFERENT 158 (44%) | SAME 834 (54%) · DIFFERENT 707 (46%) | — |

#### Profilo simultaneo delle coordinate, SHORT (primi tentativi DEV)

P50 [P10; P90]; categorie con conteggio e quota sulla cella. Distanze firmate d·(livello − C)/A: positive davanti nel verso del movimento.

| SHORT: coordinata all'origine | Tutti (n=2144) | CONCORDANT (n=255) | OPPOSITE (n=435) | DISCORDANT (n=1454) | UNAVAILABLE (n=0) |
|---|---|---|---|---|---|
| Profondità dell'arretramento | 0,86 [0,43; 2,48] | 0,65 [0,38; 0,96] | 1,38 [0,45; 4,62] | 0,85 [0,44; 2,14] | — |
| L / A | 2,20 [1,16; 4,26] | 3,36 [1,92; 5,88] | 1,80 [1,03; 3,10] | 2,17 [1,16; 4,16] | — |
| Distanza residua a P1 / A | 0,83 [-0,12; 2,73] | 1,03 [-0,07; 2,30] | 0,93 [-0,02; 3,49] | 0,76 [-0,17; 2,64] | — |
| Distanza a Rext / A | -1,19 [-2,28; -0,65] | -1,08 [-2,11; -0,62] | -1,40 [-2,53; -0,77] | -1,16 [-2,20; -0,63] | — |
| A / C | 0,0055 [0,0027; 0,0093] | 0,0059 [0,0032; 0,0095] | 0,0056 [0,0030; 0,0094] | 0,0054 [0,0026; 0,0091] | — |
| Livello più vicino davanti / A | 0,87 [0,19; 2,81] · mancanti 63 | 0,93 [0,17; 2,13] · mancanti 22 | 0,92 [0,24; 3,25] | 0,86 [0,18; 2,81] · mancanti 41 | — |
| Livello più vicino dietro / A | -1,12 [-2,48; -0,25] · mancanti 31 | -1,08 [-2,76; -0,36] | -1,26 [-2,36; -0,23] · mancanti 18 | -1,09 [-2,46; -0,24] · mancanti 13 | — |
| d·(SMA20−SMA50)/A | -0,18 [-2,05; 1,63] | 1,03 [0,24; 2,27] | -1,14 [-2,49; -0,24] | -0,07 [-1,94; 1,63] | — |
| d·pendenza SMA20 / A | -0,07 [-0,71; 0,49] | 0,40 [0,10; 0,85] | -0,53 [-1,03; -0,16] | -0,02 [-0,55; 0,44] | — |
| d·(C−SMA20)/A | 0,20 [-1,21; 1,61] | 1,10 [0,14; 2,76] | -0,55 [-2,13; 0,37] | 0,27 [-0,91; 1,54] | — |
| Volume relativo | 1,06 [0,47; 3,12] | 1,02 [0,46; 3,20] | 1,19 [0,49; 3,15] | 1,03 [0,46; 3,08] | — |
| Fibonacci r effettivo | 0,38 [0,01; 0,95] | 0,36 [0,05; 0,82] | 0,38 [0,01; 0,86] | 0,39 [-0,01; 1,00] | — |
| Struttura 1D | MIXED 823 (38%) · UP 819 (38%) · DOWN 502 (23%) | UP 102 (40%) · MIXED 94 (37%) · DOWN 59 (23%) | MIXED 183 (42%) · UP 154 (35%) · DOWN 98 (23%) | UP 563 (39%) · MIXED 546 (38%) · DOWN 345 (24%) | — |
| Tipo del livello davanti | PIVOT_LOW 1405 (66%) · DAY_LOW 446 (21%) · DAY_HIGH 136 (6%) · PIVOT_HIGH 94 (4%) · NONE 63 (3%) | PIVOT_LOW 129 (51%) · DAY_LOW 101 (40%) · NONE 22 (9%) · PIVOT_HIGH 3 (1%) | PIVOT_LOW 302 (69%) · DAY_HIGH 75 (17%) · DAY_LOW 38 (9%) · PIVOT_HIGH 20 (5%) | PIVOT_LOW 974 (67%) · DAY_LOW 307 (21%) · PIVOT_HIGH 71 (5%) · DAY_HIGH 61 (4%) · NONE 41 (3%) | — |
| Tipo del livello dietro | PIVOT_HIGH 1350 (63%) · DAY_HIGH 376 (18%) · PIVOT_LOW 265 (12%) · DAY_LOW 122 (6%) · NONE 31 (1%) | PIVOT_HIGH 174 (68%) · DAY_LOW 56 (22%) · PIVOT_LOW 23 (9%) · DAY_HIGH 2 (1%) | PIVOT_HIGH 209 (48%) · DAY_HIGH 164 (38%) · PIVOT_LOW 44 (10%) · NONE 18 (4%) | PIVOT_HIGH 967 (67%) · DAY_HIGH 210 (14%) · PIVOT_LOW 198 (14%) · DAY_LOW 66 (5%) · NONE 13 (1%) | — |
| Livello esattamente a C | NO 2141 (100%) · YES 3 (0%) | NO 254 (100%) · YES 1 (0%) | NO 435 (100%) | NO 1452 (100%) · YES 2 (0%) | — |
| Incrocio SMA alla barra | NONE 2102 (98%) · IN_DIRECTION 25 (1%) · AGAINST 17 (1%) | NONE 245 (96%) · IN_DIRECTION 10 (4%) | NONE 425 (98%) · AGAINST 10 (2%) | NONE 1432 (98%) · IN_DIRECTION 15 (1%) · AGAINST 7 (0%) | — |
| Ancore Fibonacci vs movimento | CONCORDANT 1171 (55%) · OPPOSITE 973 (45%) | CONCORDANT 152 (60%) · OPPOSITE 103 (40%) | CONCORDANT 218 (50%) · OPPOSITE 217 (50%) | CONCORDANT 801 (55%) · OPPOSITE 653 (45%) | — |
| Ancore Fibonacci = contesto | SAME 1170 (55%) · DIFFERENT 974 (45%) | SAME 152 (60%) · DIFFERENT 103 (40%) | SAME 218 (50%) · DIFFERENT 217 (50%) | SAME 800 (55%) · DIFFERENT 654 (45%) | — |

#### Periodi (primi tentativi)

| Periodo | Verso | Tentativi | CONC / OPP / DISC / UNAV | Completi | F | A | F→A | A→F | F=A | nessuno | final P50 [P10; P90] | favorevole P50 | contrario P50 |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|
| DEV | LONG | 2228 | 330 / 357 / 1541 / 0 | 2227 | 528 | 436 | 614 | 624 | 3 | 22 | 0,11 [-4,63; 5,76] | 2,56 | 2,39 |
| DEV | SHORT | 2144 | 255 / 435 / 1454 / 0 | 2141 | 428 | 508 | 617 | 571 | 1 | 16 | -0,23 [-5,65; 4,67] | 2,37 | 2,53 |
| 2023 | LONG | 1102 | 134 / 177 / 791 / 0 | 1102 | 253 | 210 | 323 | 306 | 2 | 8 | 0,08 [-4,19; 5,67] | 2,69 | 2,39 |
| 2023 | SHORT | 1065 | 123 / 190 / 752 / 0 | 1065 | 215 | 234 | 315 | 293 | 1 | 7 | -0,20 [-5,41; 4,29] | 2,35 | 2,53 |
| 2024 | LONG | 1126 | 196 / 180 / 750 / 0 | 1125 | 275 | 226 | 291 | 318 | 1 | 14 | 0,18 [-5,00; 5,94] | 2,46 | 2,41 |
| 2024 | SHORT | 1079 | 132 / 245 / 702 / 0 | 1076 | 213 | 274 | 302 | 278 | 0 | 9 | -0,26 [-6,02; 5,08] | 2,38 | 2,53 |

#### Mesi (primi tentativi, mese dell'origine)

| Periodo | Verso | Tentativi | CONC / OPP / DISC / UNAV | Completi | F | A | F→A | A→F | F=A | nessuno | final P50 [P10; P90] | favorevole P50 | contrario P50 |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|
| 2023-01 | LONG | 96 | 16 / 9 / 71 / 0 | 96 | 26 | 11 | 22 | 36 | 0 | 1 | 1,33 [-2,27; 11,77] | 3,60 | 1,53 |
| 2023-01 | SHORT | 86 | 3 / 20 / 63 / 0 | 86 | 8 | 26 | 27 | 23 | 0 | 2 | -1,21 [-8,47; 2,71] | 1,64 | 3,70 |
| 2023-02 | LONG | 78 | 9 / 25 / 44 / 0 | 78 | 13 | 17 | 28 | 20 | 0 | 0 | 0,00 [-4,41; 5,73] | 2,83 | 2,76 |
| 2023-02 | SHORT | 83 | 17 / 15 / 51 / 0 | 83 | 20 | 16 | 26 | 21 | 0 | 0 | 0,11 [-5,95; 4,93] | 2,63 | 1,83 |
| 2023-03 | LONG | 92 | 7 / 12 / 73 / 0 | 92 | 25 | 21 | 28 | 18 | 0 | 0 | 0,39 [-4,26; 6,21] | 2,65 | 2,06 |
| 2023-03 | SHORT | 86 | 10 / 17 / 59 / 0 | 86 | 19 | 21 | 25 | 21 | 0 | 0 | -0,47 [-8,45; 5,95] | 2,33 | 2,30 |
| 2023-04 | LONG | 85 | 13 / 18 / 54 / 0 | 85 | 16 | 22 | 23 | 24 | 0 | 0 | -0,56 [-4,65; 4,23] | 2,25 | 3,11 |
| 2023-04 | SHORT | 97 | 14 / 15 / 68 / 0 | 97 | 31 | 19 | 26 | 21 | 0 | 0 | 0,40 [-4,79; 3,88] | 2,44 | 2,16 |
| 2023-05 | LONG | 91 | 10 / 15 / 66 / 0 | 91 | 19 | 24 | 27 | 20 | 1 | 0 | -0,05 [-5,34; 4,31] | 2,61 | 2,81 |
| 2023-05 | SHORT | 87 | 12 / 11 / 64 / 0 | 87 | 22 | 18 | 29 | 17 | 1 | 0 | -0,19 [-5,44; 5,04] | 2,88 | 2,76 |
| 2023-06 | LONG | 101 | 10 / 12 / 79 / 0 | 101 | 19 | 11 | 34 | 35 | 1 | 1 | 0,59 [-3,92; 5,58] | 3,02 | 2,64 |
| 2023-06 | SHORT | 89 | 8 / 17 / 64 / 0 | 89 | 12 | 22 | 28 | 27 | 0 | 0 | -0,48 [-5,67; 5,04] | 2,19 | 2,79 |
| 2023-07 | LONG | 95 | 10 / 15 / 70 / 0 | 95 | 21 | 18 | 31 | 24 | 0 | 1 | -0,11 [-3,82; 2,77] | 2,63 | 2,77 |
| 2023-07 | SHORT | 94 | 10 / 11 / 73 / 0 | 94 | 20 | 22 | 24 | 28 | 0 | 0 | -0,28 [-2,82; 4,30] | 3,25 | 2,61 |
| 2023-08 | LONG | 89 | 6 / 16 / 67 / 0 | 89 | 12 | 17 | 30 | 30 | 0 | 0 | -0,41 [-3,55; 4,21] | 2,37 | 2,73 |
| 2023-08 | SHORT | 89 | 13 / 11 / 65 / 0 | 89 | 19 | 11 | 25 | 33 | 0 | 1 | 0,16 [-3,98; 3,91] | 2,64 | 2,59 |
| 2023-09 | LONG | 95 | 11 / 18 / 66 / 0 | 95 | 26 | 15 | 25 | 27 | 0 | 2 | 0,03 [-3,19; 3,56] | 2,17 | 2,48 |
| 2023-09 | SHORT | 92 | 10 / 11 / 71 / 0 | 92 | 16 | 19 | 29 | 27 | 0 | 1 | -0,11 [-4,31; 2,78] | 2,11 | 2,26 |
| 2023-10 | LONG | 91 | 13 / 11 / 67 / 0 | 91 | 24 | 14 | 29 | 23 | 0 | 1 | 0,50 [-3,01; 10,11] | 3,42 | 1,98 |
| 2023-10 | SHORT | 88 | 11 / 22 / 55 / 0 | 88 | 13 | 17 | 25 | 30 | 0 | 3 | -0,36 [-6,54; 2,61] | 1,88 | 2,55 |
| 2023-11 | LONG | 97 | 16 / 15 / 66 / 0 | 97 | 24 | 23 | 23 | 25 | 0 | 2 | -0,02 [-4,15; 5,41] | 2,53 | 2,22 |
| 2023-11 | SHORT | 91 | 9 / 20 / 62 / 0 | 91 | 19 | 23 | 26 | 23 | 0 | 0 | -0,41 [-4,35; 3,86] | 2,28 | 2,51 |
| 2023-12 | LONG | 92 | 13 / 11 / 68 / 0 | 92 | 28 | 17 | 23 | 24 | 0 | 0 | -0,02 [-3,74; 6,71] | 2,51 | 1,99 |
| 2023-12 | SHORT | 83 | 6 / 20 / 57 / 0 | 83 | 16 | 20 | 25 | 22 | 0 | 0 | 0,26 [-5,58; 4,50] | 2,50 | 2,23 |
| 2024-01 | LONG | 87 | 16 / 13 / 58 / 0 | 87 | 20 | 16 | 26 | 23 | 0 | 2 | -0,27 [-6,52; 7,59] | 2,58 | 2,44 |
| 2024-01 | SHORT | 83 | 13 / 16 / 54 / 0 | 83 | 16 | 21 | 21 | 22 | 0 | 3 | 0,07 [-5,21; 6,57] | 2,86 | 2,46 |
| 2024-02 | LONG | 93 | 24 / 9 / 60 / 0 | 93 | 31 | 17 | 20 | 25 | 0 | 0 | 0,88 [-1,87; 10,60] | 2,74 | 2,02 |
| 2024-02 | SHORT | 83 | 6 / 21 / 56 / 0 | 83 | 9 | 28 | 22 | 24 | 0 | 0 | -1,07 [-8,87; 1,49] | 1,69 | 2,80 |
| 2024-03 | LONG | 94 | 15 / 12 / 67 / 0 | 94 | 28 | 21 | 24 | 21 | 0 | 0 | 0,31 [-3,63; 5,29] | 2,19 | 2,57 |
| 2024-03 | SHORT | 84 | 8 / 23 / 53 / 0 | 84 | 16 | 16 | 25 | 25 | 0 | 2 | -0,46 [-6,42; 3,68] | 2,89 | 2,79 |
| 2024-04 | LONG | 91 | 14 / 22 / 55 / 0 | 91 | 16 | 23 | 26 | 26 | 0 | 0 | 0,10 [-7,07; 3,08] | 2,13 | 2,77 |
| 2024-04 | SHORT | 90 | 10 / 24 / 56 / 0 | 90 | 22 | 13 | 26 | 28 | 0 | 1 | 0,19 [-3,71; 6,36] | 2,72 | 1,99 |
| 2024-05 | LONG | 93 | 22 / 15 / 56 / 0 | 93 | 24 | 21 | 23 | 25 | 0 | 0 | 0,01 [-3,57; 7,41] | 2,43 | 2,54 |
| 2024-05 | SHORT | 84 | 11 / 23 / 50 / 0 | 84 | 15 | 25 | 22 | 21 | 0 | 1 | -0,21 [-7,13; 3,30] | 2,41 | 2,60 |
| 2024-06 | LONG | 84 | 11 / 14 / 59 / 0 | 84 | 20 | 12 | 20 | 27 | 0 | 5 | 0,09 [-5,59; 4,96] | 2,78 | 2,41 |
| 2024-06 | SHORT | 82 | 9 / 11 / 62 / 0 | 82 | 16 | 21 | 15 | 29 | 0 | 1 | 0,15 [-3,60; 7,77] | 2,61 | 2,69 |
| 2024-07 | LONG | 100 | 20 / 16 / 64 / 0 | 100 | 19 | 22 | 23 | 36 | 0 | 0 | -0,86 [-5,05; 4,53] | 2,58 | 2,83 |
| 2024-07 | SHORT | 100 | 17 / 24 / 59 / 0 | 100 | 24 | 24 | 30 | 22 | 0 | 0 | 0,55 [-5,10; 6,12] | 2,69 | 2,53 |
| 2024-08 | LONG | 93 | 10 / 20 / 63 / 0 | 93 | 17 | 18 | 30 | 24 | 0 | 4 | -0,20 [-6,00; 5,59] | 2,08 | 2,48 |
| 2024-08 | SHORT | 99 | 16 / 21 / 62 / 0 | 99 | 25 | 27 | 28 | 18 | 0 | 1 | 0,08 [-5,00; 8,51] | 2,58 | 2,08 |
| 2024-09 | LONG | 97 | 15 / 11 / 71 / 0 | 97 | 18 | 12 | 28 | 37 | 1 | 1 | 0,57 [-6,91; 4,57] | 2,33 | 2,21 |
| 2024-09 | SHORT | 92 | 8 / 18 / 66 / 0 | 92 | 14 | 23 | 36 | 19 | 0 | 0 | -0,49 [-5,63; 5,33] | 2,47 | 2,52 |
| 2024-10 | LONG | 104 | 20 / 15 / 69 / 0 | 104 | 31 | 27 | 20 | 25 | 0 | 1 | 0,29 [-4,68; 6,81] | 2,51 | 2,09 |
| 2024-10 | SHORT | 98 | 11 / 23 / 64 / 0 | 98 | 20 | 31 | 24 | 23 | 0 | 0 | -0,63 [-7,73; 4,42] | 2,02 | 2,57 |
| 2024-11 | LONG | 97 | 17 / 16 / 64 / 0 | 97 | 30 | 20 | 22 | 24 | 0 | 1 | 1,16 [-2,49; 6,19] | 2,84 | 2,09 |
| 2024-11 | SHORT | 87 | 8 / 20 / 59 / 0 | 87 | 19 | 20 | 32 | 16 | 0 | 0 | -0,76 [-6,18; 1,74] | 1,90 | 2,64 |
| 2024-12 | LONG | 93 | 12 / 17 / 64 / 0 | 92 | 21 | 17 | 29 | 25 | 0 | 0 | -0,69 [-5,12; 4,63] | 2,29 | 2,98 |
| 2024-12 | SHORT | 97 | 15 / 21 / 61 / 0 | 94 | 17 | 25 | 21 | 31 | 0 | 0 | 0,06 [-3,80; 4,06] | 2,98 | 2,56 |

#### Riepilogo secondario: tutti i tentativi DEV, collegati e dipendenti

| Verso | Profilo | Tentativi | Gruppi | Completi | Censurati / lacune / A mancante / A zero | F | A | F→A | A→F | F=A | nessuno | final P50 [P10; P90] | favorevole | contrario |
|---|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---|---|---|
| LONG | Tutti | 3401 | 2228 | 3400 | 1 / 0 / 0 / 0 | 791 | 679 | 956 | 937 | 4 | 33 | 0,11 [-4,58; 6,07] | 2,55 [0,48; 8,70] | 2,39 [0,44; 7,64] |
| LONG | CONCORDANT | 557 | 417 | 557 | 0 / 0 / 0 / 0 | 121 | 99 | 175 | 158 | 1 | 3 | 0,02 [-4,01; 7,95] | 2,56 [0,47; 9,88] | 2,49 [0,45; 6,68] |
| LONG | OPPOSITE | 497 | 403 | 497 | 0 / 0 / 0 / 0 | 130 | 105 | 118 | 135 | 0 | 9 | 0,25 [-4,42; 4,42] | 2,45 [0,46; 7,44] | 2,11 [0,37; 7,83] |
| LONG | DISCORDANT | 2347 | 1664 | 2346 | 1 / 0 / 0 / 0 | 540 | 475 | 663 | 644 | 3 | 21 | 0,09 [-4,70; 6,02] | 2,56 [0,49; 8,71] | 2,39 [0,45; 7,71] |
| LONG | UNAVAILABLE | 0 | 0 | 0 | 0 / 0 / 0 / 0 | 0 | 0 | 0 | 0 | 0 | 0 | n=0 | n=0 | n=0 |
| SHORT | Tutti | 3181 | 2144 | 3178 | 3 / 0 / 0 / 0 | 632 | 733 | 942 | 849 | 1 | 21 | -0,28 [-5,70; 4,67] | 2,39 [0,42; 7,91] | 2,60 [0,53; 8,33] |
| SHORT | CONCORDANT | 410 | 312 | 410 | 0 / 0 / 0 / 0 | 78 | 105 | 137 | 89 | 0 | 1 | -0,42 [-5,23; 6,21] | 2,40 [0,37; 9,11] | 2,54 [0,67; 7,05] |
| SHORT | OPPOSITE | 600 | 484 | 598 | 2 / 0 / 0 / 0 | 129 | 137 | 167 | 162 | 1 | 2 | -0,04 [-6,25; 4,34] | 2,34 [0,42; 7,21] | 2,63 [0,43; 8,48] |
| SHORT | DISCORDANT | 2171 | 1580 | 2170 | 1 / 0 / 0 / 0 | 425 | 491 | 638 | 598 | 0 | 18 | -0,31 [-5,77; 4,67] | 2,40 [0,44; 7,90] | 2,59 [0,53; 8,63] |
| SHORT | UNAVAILABLE | 0 | 0 | 0 | 0 / 0 / 0 / 0 | 0 | 0 | 0 | 0 | 0 | 0 | n=0 | n=0 | n=0 |

#### Esempi (regola del task §6)

| # | Tentativo | Origine UTC | Verso | Profilo | Ordinal | Categorie |
|---:|---|---|---|---|---:|---|
| 1 | `ATT:LONG:1672477200000:1672539300000` | 2023-01-01 02:15 | LONG | DISCORDANT | 1 | FIRST_LONG_DISCORDANT |
| 2 | `ATT:SHORT:1672496100000:1672544700000` | 2023-01-01 03:45 | SHORT | DISCORDANT | 1 | FIRST_SHORT_DISCORDANT |
| 3 | `ATT:LONG:1672525800000:1672552800000` | 2023-01-01 06:00 | LONG | OPPOSITE | 1 | FIRST_LONG_OPPOSITE, FIRST_OPPOSITE_FINAL_GT_0 |
| 4 | `ATT:SHORT:1672496100000:1672558200000` | 2023-01-01 07:30 | SHORT | CONCORDANT | 2 | FIRST_REPEATED_ATTEMPT |
| 5 | `ATT:LONG:1672585200000:1672614900000` | 2023-01-01 23:15 | LONG | CONCORDANT | 1 | FIRST_LONG_CONCORDANT |
| 6 | `ATT:SHORT:1672604100000:1672620300000` | 2023-01-02 00:45 | SHORT | OPPOSITE | 1 | FIRST_SHORT_OPPOSITE |
| 7 | `ATT:LONG:1672793100000:1672814700000` | 2023-01-04 06:45 | LONG | CONCORDANT | 1 | FIRST_CONCORDANT_FINAL_LE_0 |
| 8 | `ATT:SHORT:1674407700000:1674445500000` | 2023-01-23 03:45 | SHORT | CONCORDANT | 1 | FIRST_SHORT_CONCORDANT |
| 9 | `ATT:SHORT:1683250200000:1683271800000` | 2023-05-05 07:30 | SHORT | OPPOSITE | 1 | FIRST_BOTH_UNORDERED |
| 10 | `ATT:SHORT:1735589700000:1735608600000` | 2024-12-31 01:30 | SHORT | DISCORDANT | 1 | FIRST_RIGHT_CENSORED |

Categorie vuote: FIRST_LONG_UNAVAILABLE, FIRST_SHORT_UNAVAILABLE.


## 10. Review Director su c8ac744 — correzioni R1 richieste, non ACCEPTED

Review indipendente: lettura codice/report e15test Python OBS-002 +24test UI storici passati, typecheck/build riusciti; letta immagine obs002-02 dell'esecutore, nessun browser autonomo Windows o ricalcolo reale dei6.582 esiti. Cross-check completo e riproducibilità restano evidenza dell'esecutore. Sette scelte §7 confermate, con motivi nel task R1. Il40% con profondità>1 deriva dal disegno del Director, non da un errore Claude: non si modifica ora la popolazione.

R1-A riprodotto: knownAtT delle timeline oscura timestamp/motivo di ritiro futuro ma conserva replacedBy/sameGroup di quel ritiro, rivelando una sostituzione futura. Richiesta proiezione causale completa e derivato corretto di examples.json, senza ricalcolare popolazione/esiti.

R1-B riprodotto: il lettore accetta un esito completo con favourable=null e un F_BEFORE_A con entrambi i contatti null. Due regressioni aggiuntive falliscono sulla consegna. Richiesta validazione circoscritta dei campi/relazioni usati dal nuovo blocco e rifiuto comprensibile con studio aperto conservato.

R1-C: le frasi «quasi sempre entrambi» §§4/8 sono da correggere. Tabella principale:2430/4368=55,63% entrambi,1900/4368=43,50% uno solo,38/4368=0,87% nessuno. Almeno uno99,13%. Non cambiano numeri o convenzioni; cambia la loro descrizione. Nessuna conclusione su utilità o inefficacia delle sei famiglie dedotta da questa review.

Macrofase aperta, nessuna ipotesi operativa scelta. Incarico eseguibile OBS-002/R1 in current_task.md; nessuna nuova elaborazione reale richiesta.

## 11. Correzioni R1 (esecutore, 17 ottobre 2026)

**Commit:** `bc92a6d` (codice e test), più il commit di questa consegna (report, stato).

**Ordine seguito:** i difetti sono stati riprodotti prima della correzione con test che falliscono sul codice consegnato.
- R1-A: la regressione sulla timeline falliva sul codice della consegna (`replacedBy` del REPLACE futuro presente in `knownAtT`).
- R1-B: sul validatore consegnato falliscono 20 dei 22 nuovi test, fra cui i due casi riprodotti dal Director; i 2 verdi sono le regressioni sui pacchetti validi.

### R1-A — proiezione causale delle timeline

**Correzione.** `src/obs002/timelines.py` proietta i metadati di versione per elenco consentito:
- identità, ancore e disponibilità sono note dalla creazione;
- ritiro e tutti i suoi fatti (`retiredAt`, `retireReason`, `replacedBy`, `sameGroup` e qualsiasi altro campo del ritiro) compaiono solo se il ritiro è avvenuto entro t;
- i tentativi della versione sono limitati a t.

Un campo nuovo non previsto resta escluso finché il ritiro non è effettivo. Lo stesso codice serve al generatore e alla migrazione.

**Test** (`tests/test_obs002_r1.py`):
- stesso prefisso con tre futuri diversi (ritiro a fine studio, REPLACE con P1 alla barra 30, REPLACE alla barra 31): `knownAtT` identico;
- dopo un ritiro effettivo i suoi fatti restano visibili;
- la migrazione di una timeline nella forma consegnata coincide con il generatore corretto, è idempotente e rifiuta una popolazione diversa.

Il test esistente sulle popolazioni con futuri alterati è conservato invariato.

**Derivato reale corretto.** Comando `$env:PYTHONPATH = "src"; python3.12 -m obs002 r1`, eseguito da checkout pulito al commit `bc92a6d`:
- legge `examples.json` e `population.json` registrati, dopo averne verificato gli hash;
- non rilegge prezzi e non ricalcola osservazioni, popolazione o esiti;
- scrive in `…\OBS-002-v1.0.0-e1.0.0-3b76888642-b11bad4557\R1\`.

| File | SHA256 |
|---|---|
| `R1/examples.json` (timeline `obs002.timeline/2`) | `92b7b150ba8baaba67f04c7612c82e500df4bd4c7efd3e08d4fdb28d2affe785` |
| derivato da `examples.json` originale (conservato) | `507c2bf3a6979174bbfe5d7d18c67a88c5d5cee71072c162b8b43a34ca0ad60b` |
| `R1/contacts-breakdown.json` (R1-C) | `cf5812a55a58d9cbcb2acb48ab561fc8cf7b9e011b17dbe680a274131058bb1c` |
| `R1/manifest.json` | elenco campo per campo delle differenze, hash d'origine, `listSha256` invariato `feb69ba8…f7f6` |

**Impatto: 20 campi, cioè `replacedBy` e `sameGroup` della versione di ciascuno dei 10 casi.** Ogni versione viene prima o poi sostituita, quindi in tutti i casi quei fatti futuri erano presenti come «noti a t»; `retiredAt` e `retireReason` erano già nulli.

Il comando verifica che nient'altro cambi:
- elenco, categorie, `afterT`, tentativi/snapshot, barre e tentativi precedenti sono identici;
- due esecuzioni consecutive producono file identici byte per byte.

Popolazione, snapshot e 6.582 esiti non sono toccati: il difetto stava solo nella proiezione successiva delle timeline. I pacchetti dei casi non contengono quei metadati e non sono stati rigenerati.

### R1-B — coerenza dell'esito OBS-002 importato

**Correzione** (`dashboard/src/historical/loadBundle.ts`). Si controllano solo i campi e le relazioni usati dal blocco OBS-002; il percorso di mercato non viene ricostruito.

- **Esito completo:**
  - final, favorevole e contrario finiti, con escursioni non negative;
  - nessun flag, classe riconosciuta e coerente con i contatti;
  - nello stesso minuto ordina solo l'apertura;
  - prefisso parziale assente.
- **Esito incompleto:**
  - flag riconosciuti, non ripetuti e non vuoti;
  - nessuna classe, misura o contatto completo; il prefisso parziale resta separato ed etichettato, senza obbligo di mostrarlo.
- **Contatti:** all'apertura di un minuto, dentro [t, t+24h), con intervallo coerente con `atOpen`.
- **C, A e riferimenti:**
  - A positiva e riferimenti = C ± A nel verso del caso;
  - A nulla con `MISSING_A`, A = 0 con `ZERO_A`, e in entrambi i casi riferimenti assenti.
- **Orizzonte e censura:** orizzonte = t + 24h; `RIGHT_CENSORED` se e solo se l'orizzonte supera il confine dei dati del pacchetto.

**Test** (`Obs002CaseR1.test.tsx`, 22 test):
- i due casi riprodotti, anche dal selettore: errore leggibile, studio aperto conservato, nessun blocco retrospettivo falso;
- 17 rifiuti mirati su escursioni, flag, contatti, intervalli, classi, riferimenti, A, orizzonte e censura;
- pacchetti validi completi e censurati e bundle OBS-001 che si aprono ancora;
- un caso censurato consultabile senza classe inventata.

Nuova fixture sintetica censurata `synthetic-obs002-case-censored.json`; la fixture esistente rigenerata risulta identica byte per byte.

Il test esistente che attende «esito completo senza classe» non è stato modificato: il nuovo messaggio per quella situazione lo contiene ancora.

Tutti i **10 pacchetti reali** consegnati passano il validatore più severo (controllo locale con il parser), quindi non sono stati rigenerati.

### R1-C — scomposizione aritmetica dei contatti

Sezioni 4 e 8 corrette, con il testo originale citato. Nuova funzione `contact_breakdown` con test sui conteggi della tabella principale (2.430 / 1.900 / 38 / 4.330 su 4.368). Il derivato `R1/contacts-breakdown.json` è calcolato dal `summary.json` registrato, dopo verifica del suo hash.

Primi tentativi DEV, esiti completi:

| Verso | Profilo | Completi | Entrambi | Uno solo | Nessuno | Almeno uno |
|---|---|---:|---:|---:|---:|---:|
| LONG | Tutti | 2.227 | 1.241 (55,7%) | 964 (43,3%) | 22 (1,0%) | 2.205 (99,0%) |
| LONG | CONCORDANT | 330 | 195 (59,1%) | 134 (40,6%) | 1 (0,3%) | 329 (99,7%) |
| LONG | OPPOSITE | 357 | 183 (51,3%) | 169 (47,3%) | 5 (1,4%) | 352 (98,6%) |
| LONG | DISCORDANT | 1.540 | 863 (56,0%) | 661 (42,9%) | 16 (1,0%) | 1.524 (99,0%) |
| SHORT | Tutti | 2.141 | 1.189 (55,5%) | 936 (43,7%) | 16 (0,7%) | 2.125 (99,3%) |
| SHORT | CONCORDANT | 255 | 141 (55,3%) | 113 (44,3%) | 1 (0,4%) | 254 (99,6%) |
| SHORT | OPPOSITE | 433 | 243 (56,1%) | 189 (43,6%) | 1 (0,2%) | 432 (99,8%) |
| SHORT | DISCORDANT | 1.453 | 805 (55,4%) | 634 (43,6%) | 14 (1,0%) | 1.439 (99,0%) |
| Entrambi i versi | Tutti | 4.368 | 2.430 (55,6%) | 1.900 (43,5%) | 38 (0,9%) | 4.330 (99,1%) |

Conteggi aritmetici sui risultati conservati, non una nuova analisi: soglia, orizzonte e classi sono invariati. Il riepilogo secondario è nello stesso file.

### Hash invariati dopo R1

Verificati con `sha256sum` prima e dopo l'esecuzione di `r1`:
- `config/OBS-002-v1.json` `a8449033…115d` (canonico `b11bad45…d0af`);
- `population.json` `e0be48ab…a278`;
- `outcomes.json` `26044415…a817`;
- `summary.json` `db086624…813e`;
- `examples.json` originale `507c2bf3…d60b`;
- `outputs.json` `25e6e2da…58b`;
- `population-manifest.json` `49693559…4a88`;
- i 10 pacchetti dei casi.

Gli hash storici della sezione 3 non sono stati modificati: il derivato corretto ha un hash proprio.

### Verifiche eseguite

- Python: 21 test OBS-002 (15 esistenti e 6 R1).
- Lettore: 46 test (24 esistenti e 22 R1); typecheck e build riusciti.

Nessuna suite generale, OBS-001 intero, CAND o CI. Nessuna nuova elaborazione di popolazione o esiti reali, nessun download, nessun 2025/2026. Nessuna nuova immagine: le viste dei casi validi non cambiano.

### Limiti R1

- I controlli del lettore verificano la coerenza interna del pacchetto, non il percorso di mercato.
- La migrazione R1-A è verificata sui sintetici contro il generatore corretto; sui dati reali è verificata contro la popolazione registrata e con l'invarianza degli altri campi, senza ricostruire le timeline dalla catena completa.
- Riscontri dello stesso esecutore.
