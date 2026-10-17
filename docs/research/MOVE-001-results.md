# MOVE-001 — applicazione descrittiva del ciclo di vita del movimento (DEV 2023–2024)

**Stato: consegna dell'esecutore (DELIVERED, in attesa di review del Director; non ACCEPTED).** Rappresentazione sperimentale: nessuna strategia, operazione, esito 24h o valutazione economica. Il Director conclude se la rappresentazione permette una prossima domanda decisionale.

**Licenza di questo file e delle immagini in `docs/research/MOVE-001-screens/`:** derivati aggregati di dati Binance Vision, **CC BY-NC-SA 4.0** (https://creativecommons.org/licenses/by-nc-sa/4.0/). Fonte: Binance Vision (https://data.binance.vision). Dati grezzi, ledger e pacchetti non sono redistribuiti.

## 1. Identità, gate e riproducibilità

| Voce | Valore |
|---|---|
| Contratto | `docs/research/MOVE-001.md` §§1–12, versione 1.0.1 (commit `9b536a2`) |
| Config | `config/MOVE-001-v1.json`, SHA256 canonico `30e67d8fe230ed48d56744dd7f8e89103dd6d5d7513486ef6c15b58f6e39e0a7` (file `91b075c7…7c6c`) |
| **Gate prima dei dati** | commit **`fd09d35a08d11a583520d61a494f4cfb23f622e3`**: config, modulo `src/move001/` e 18 test sintetici pubblicati **prima** di leggere qualsiasi dato reale per MOVE-001 |
| Commit successivi | `ad971af`: riscontro degli invarianti, nessun cambio di output; `a0f2b12`: adattatore del lettore, fixture, test e schermate; più il commit di questa consegna (report, stato) |
| Osservatore | OBS-001/v1 invariato `3c4eb884…2387` |
| Input | 27 ZIP trade 1m BTCUSDT perpetual 2022-10…2024-12 già conservati, mesi elencati esplicitamente, SHA256 verificati su manifest e checksum del fornitore; inputHash `3b768886424b4907ef3fb794d9c1e3f565d2f7d28f023e3658763b297db24a5e`; 1.185.120 minuti validi su 1.185.120. Nessun download, nessun dato 2025/2026 |
| Comando | `$env:PYTHONPATH = "src"; python3.12 -m move001 run` (circa 13 s); riscontro `python3.12 -m move001 verify` |
| Run | `C:\Projects\algorithmic-trader-data\MOVE-001\runs\MOVE-001-v1.0.1-e1.0.0-3b76888642-30e67d8fe2\`, eseguito dal checkout pulito `fd09d35` |
| Ripetizione | seconda esecuzione identica byte per byte: `outputs.json` `10dd7fc600d757ae5832dc18aea75202736b608087b4ca7f839831b8f87c03d4` (hash di ogni file al suo interno) |
| Hash principali | `ledger.json` `e31f5795…6c8f`, `references.json` `967a8d48…7dfb`, `structures.json` `90ee9d7f…037b`, `summary.json` `2b06187e…f1a2`, `examples.json` `cc6f7015…ff80` (lista `81350bc3…1717`) |
| Riscontro invarianti | `verify.json`: 701 riferimenti (70 del prefisso e 631 DEV) e 26.336 chiusure, **0 violazioni**; ledger e riferimenti ricalcolati identici a quelli registrati. Eseguito dal checkout pulito `a0f2b12` |

Provenienza, commit e orari sono in `provenance.json` e `verify.json`, separati dagli output numerici.

## 2. Che cosa è stato implementato

Modulo isolato `src/move001/`, che riusa minuti, aggregazione e osservatore OBS-001 senza modifiche. CAND-001, OBS-002 e i loro output non sono toccati.

- `cycle.py`: a ogni chiusura 45m segue l'ordine del §11.3.
  1. Continuità.
  2. Eventi disponibili, cioè la sequenza alternata accettata ricostruita dagli eventi APPEND/REPLACE dell'osservatore, ed eventuale P1.
  3. Riferimento esistente: perdita, test, completamento, struttura opposta, primo passaggio a UTILIZZABILE.
  4. Tripla corrente, primo attraversamento e adozione o rifiuto.
  5. Struttura opposta alla nascita.

  Il ledger è append-only.
- `summary.py`: conteggi per DEV, anni, mesi, verso e prefisso, con stock, condizioni di occupazione e strutture riconciliati. Durate con disponibili, censurate e non raggiunte separate.
- `examples.py`: casi del §12.3. `consult.py`: un pacchetto `MOVE001_CASE` per caso. `verify.py`: riscontro indipendente dalle barre.
- Lettore (dashboard): validatore `MOVE001_CASE` e scheda «Movimento di riferimento», che ricostruisce giudizio e ancore dai soli fatti con istante ≤ momento scelto.
  - Ancore B/P0/P1 sul grafico, solo da quando sono note.
  - Avviso «Rappresentazione sperimentale del movimento — nessuna decisione operativa».
  - Comando del seguito 24h nascosto, voce «Studio osservativo» con spiegazione.
  - I pacchetti OBS-001 e OBS-002 si aprono come prima.

### Scelte tecniche non metodologiche (da confermare dal Director se necessario)

1. **Sequenza e identità.** La sequenza alternata (ultimi tre pivot) è ricostruita dagli eventi FIB_SEQUENCE: APPEND aggiunge, REPLACE sostituisce l'ultimo, KEEP è ignorato, ed è azzerata dalle barre incomplete. Identità del pivot = tipo + candela; versione = numero di versione Fibonacci dell'evento che lo ha inserito. La tripla è identificata da segmento e (id, versione) di Q, B, P0.
2. **Periodo di un evento** = periodo della barra la cui chiusura lo rende disponibile (barra aperta a t − 45m). Così le 23.392 chiusure DEV sono esattamente le barre 2023–2024.
3. **Freschezza.** «P0 strettamente successivo alla barra di test/conflitto» è tradotto come candela di P0 con apertura maggiore dell'apertura di quella barra; dopo un completamento, candela di P0 successiva a quella del vecchio P0. Il vincolo resta finché non nasce un nuovo principale.
4. **Fatti successivi da sospeso** (non ricontano la nascita):
   - nuovo test e P1 toccato: uno per **barra**;
   - struttura opposta: solo ai passaggi.

   Sono conteggi di barre, non di riferimenti.
5. **Condizione di occupazione** misurata alla fine del trattamento di ogni chiusura completa: la chiusura di nascita conta per il neonato, quella di archiviazione per il principale successivo o come assente.
6. **Triple non qualificate.** Contate a parte, per tripla corrente con availableAt nel DEV: geometria, base testata prima di un attraversamento, nessun attraversamento finché corrente. Non sono strutture bloccate dal posto.
7. **Esempi.**
   - Solo eventi con istante nel DEV.
   - Per i rifiuti il caso è il riferimento occupante; per la sostituzione è il riferimento sostituito.
   - «Test dell'origine» = primo test registrato, sia che sospenda sia che sia un fatto successivo.
8. **Pacchetti.** Origini dalle 4 chiusure prima della nascita alle 8 dopo l'ultimo fatto; 35 giorni di osservazioni, calcolate sull'intero prefisso e poi ritagliate.
9. **Lettore.** Nel contratto TypeScript `case` resta tipizzato come caso OBS-002, per non toccare i lettori e i test esistenti; il caso MOVE-001 si legge solo tramite `HistoricalStudy.moveCase`, discriminato da `kind`.

## 3. Verifiche eseguite (dell'esecutore)

**Test sintetici** (`tests/test_move001.py`, 19). I 18 originali sono stati pubblicati al gate; il diciannovesimo riguarda il riscontro. Coprono:
- nascita, formazione, UTILIZZABILE e completamento;
- specchio LONG/SHORT;
- candela di P1 e barra di pubblicazione che non completano;
- perdita in chiusura e recupero che non ripristina;
- perdita in formazione con P1 mancante;
- doppio test con ordine ignoto, e sospensione non riattivata da P1 toccato;
- struttura opposta alla nascita, successiva e MIXED (che non sospende); completamento prima della struttura nella stessa barra;
- base testata nella barra di nascita; rottura avvenuta prima della disponibilità della tripla;
- P1 fissato contro un REPLACE successivo; KEEP non accettato;
- formazione che occupa (stesso verso e verso opposto), utilizzabile che occupa, completamento che libera il posto nella stessa chiusura;
- freschezza e sostituzione dopo sospensione; candidato rifiutato mai recuperato;
- lacuna (archiviazione e nessuna ripartenza con vecchie ancore); fine copertura amministrativa;
- stesso prefisso con futuri diversi, con l'osservatore reale;
- conteggi riconciliati, categorie vuote, durate censurate;
- riscontro che passa sui cicli validi e fallisce su riferimenti manomessi.

**Lettore** (`Move001Case.test.tsx`, 14 test, più i 46 storici esistenti: 60 passati); typecheck e build riusciti. Le tracce d'errore in console vengono dal test esistente `R1.test.tsx`, che corrompe apposta un bundle. I 6 pacchetti reali passano il validatore.

**Prova visiva** su due pacchetti reali (1366 px, Chrome headless); schermate in `docs/research/MOVE-001-screens/`. Durante la prova ho corretto la griglia della scheda, che a tutta larghezza schiacciava la terza colonna; nessun altro cambio di stile.

Nessuna suite generale, OBS-001 intero, CAND o CI. Queste verifiche sono dell'esecutore; la review indipendente spetta al Director.

## 4. Conteggi (eventi per periodo della barra; stock riconciliati)

Prefisso, DEV e anni:

| Voce | Prefisso (ott–dic 2022) | DEV | 2023 | 2024 |
|---|---:|---:|---:|---:|
| Chiusure previste / complete / incomplete | 2.944 / 2.944 / 0 | 23.392 / 23.392 / 0 | 11.680 / 11.680 / 0 | 11.712 / 11.712 / 0 |
| Chiusure: principale assente | 1.624 | 13.104 | 6.214 | 6.890 |
| Chiusure: in formazione, non sospeso | 241 | 2.265 | 976 | 1.289 |
| Chiusure: sospeso con P1 | 664 | 4.426 | 2.756 | 1.670 |
| Chiusure: sospeso senza P1 | 13 | 166 | 115 | 51 |
| Chiusure: utilizzabile | 402 | 3.431 | 1.619 | 1.812 |
| Strutture qualificate | 82 | 743 | 345 | 398 |
| — adottate | 70 | 631 | 290 | 341 |
| — rifiutate: occupato in formazione | 1 | 5 | 2 | 3 |
| — rifiutate: occupato utilizzabile | 2 | 57 | 28 | 29 |
| — rifiutate: freschezza | 9 | 50 | 25 | 25 |
| — di cui freschezza con posto libero | 4 | 35 | 19 | 16 |
| Nascite (LONG / SHORT) | 70 (35 / 35) | 631 (348 / 283) | 290 (156 / 134) | 341 (192 / 149) |
| — con predecessore (sostituzione) | 12 | 122 | 71 | 51 |
| P1 disponibile (in formazione / da sospeso) | 68 (64 / 4) | 600 (551 / 49) | 274 (245 / 29) | 326 (306 / 20) |
| Primo passaggio a UTILIZZABILE | 59 | 526 | 235 | 291 |
| Sospensioni iniziali: test dell'origine | 22 | 128 | 69 | 59 |
| Sospensioni iniziali: struttura opposta successiva | 9 | 104 | 55 | 49 |
| Sospensioni iniziali: struttura opposta alla nascita | 2 | 27 | 16 | 11 |
| — di cui senza P1 noto | 5 | 58 | 35 | 23 |
| — con doppio test, ordine ignoto | 0 | 3 | 2 | 1 |
| Fatti successivi da sospeso: barre con nuovo test | 40 | 178 | 81 | 97 |
| Fatti successivi da sospeso: barre con P1 toccato | 187 | 1.265 | 944 | 321 |
| Fatti successivi da sospeso: passaggi a struttura opposta | 27 | 159 | 104 | 55 |
| Archiviazioni: perdita della base | 28 | 234 | 109 | 125 |
| Archiviazioni: completamento geometrico | 30 | 275 | 109 | 166 |
| Archiviazioni: sostituzione | 12 | 122 | 71 | 51 |
| Archiviazioni: continuità interrotta | 0 | 0 | 0 | 0 |
| Perdite per stato prima (form. / sosp. con P1 / sosp. senza P1 / utilizz.) | 1 / 20 / 1 / 6 | 22 / 129 / 8 / 75 | 9 / 64 / 5 / 31 | 13 / 65 / 3 / 44 |
| — perdite con P1 toccato nella stessa barra | 0 | 2 | 2 | 0 |
| Stock: iniziale + nascite − archiviazioni = finale | 0 + 70 − 70 = 0 | 0 + 631 − 631 = 0 | 0 + 290 − 289 = 1 | 1 + 341 − 342 = 0 |

DEV per verso del riferimento:

| Verso | Nascite | P1 disponibile | Primo UTILIZZABILE | Sosp. test | Sosp. struttura successiva | Sosp. struttura alla nascita | Perdite | Completamenti | Sostituzioni |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| LONG | 348 | 330 | 286 | 70 | 57 | 14 | 106 | 161 | 81 |
| SHORT | 283 | 270 | 240 | 58 | 47 | 13 | 128 | 114 | 41 |

Mesi DEV (nascite, passaggi, archiviazioni, stock finale):

| Mese | Nascite | P1 | Utilizzabile | Sospensioni | Perdite | Completamenti | Sostituzioni | Stock finale | Chiusure con principale |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2023-01 | 30 | 28 | 25 | 10 | 10 | 15 | 5 | 0 | 412/992 |
| 2023-02 | 19 | 17 | 14 | 9 | 10 | 7 | 2 | 0 | 354/896 |
| 2023-03 | 23 | 23 | 19 | 13 | 9 | 8 | 5 | 1 | 504/992 |
| 2023-04 | 26 | 26 | 21 | 16 | 9 | 7 | 11 | 0 | 482/960 |
| 2023-05 | 23 | 22 | 19 | 11 | 10 | 7 | 6 | 0 | 498/992 |
| 2023-06 | 20 | 20 | 17 | 5 | 3 | 14 | 2 | 1 | 425/960 |
| 2023-07 | 19 | 18 | 16 | 12 | 11 | 3 | 5 | 1 | 419/992 |
| 2023-08 | 24 | 22 | 21 | 12 | 9 | 8 | 7 | 1 | 513/992 |
| 2023-09 | 20 | 19 | 15 | 11 | 8 | 7 | 5 | 1 | 414/960 |
| 2023-10 | 26 | 25 | 20 | 15 | 8 | 10 | 9 | 0 | 568/992 |
| 2023-11 | 29 | 28 | 24 | 11 | 13 | 12 | 4 | 0 | 367/960 |
| 2023-12 | 31 | 26 | 24 | 15 | 9 | 11 | 10 | 1 | 510/992 |
| 2024-01 | 28 | 27 | 25 | 13 | 11 | 14 | 4 | 0 | 463/992 |
| 2024-02 | 24 | 24 | 21 | 14 | 10 | 7 | 7 | 0 | 379/928 |
| 2024-03 | 30 | 29 | 25 | 11 | 6 | 18 | 6 | 0 | 372/992 |
| 2024-04 | 23 | 22 | 20 | 7 | 10 | 9 | 4 | 0 | 422/960 |
| 2024-05 | 27 | 26 | 22 | 11 | 10 | 12 | 5 | 0 | 456/992 |
| 2024-06 | 29 | 24 | 20 | 7 | 10 | 13 | 5 | 1 | 302/960 |
| 2024-07 | 33 | 31 | 30 | 8 | 8 | 22 | 3 | 1 | 377/992 |
| 2024-08 | 29 | 28 | 25 | 9 | 12 | 14 | 4 | 0 | 479/992 |
| 2024-09 | 29 | 27 | 25 | 10 | 11 | 15 | 2 | 1 | 385/960 |
| 2024-10 | 26 | 27 | 23 | 11 | 12 | 11 | 4 | 0 | 439/992 |
| 2024-11 | 36 | 35 | 32 | 12 | 14 | 17 | 5 | 0 | 400/960 |
| 2024-12 | 27 | 26 | 23 | 6 | 11 | 14 | 2 | 0 | 348/992 |

Durate (barre 45m e ore; quantile lineare h=(n−1)q):

| Durata (riferimenti nati in DEV) | Disponibili | Min | P50 | P90 | Max | Censurate | Non raggiunte |
|---|---:|---:|---:|---:|---:|---:|---:|
| nascita → P1 | 600 | 2 | 3 (2,2 h) | 7 (5,2 h) | 26 (19,5 h) | 0 | 31 |
| nascita → UTILIZZABILE | 526 | 2 | 3 (2,2 h) | 7 (5,2 h) | 26 (19,5 h) | 0 | 105 |
| nascita → archiviazione | 631 | 1 | 10 (7,5 h) | 37 (27,8 h) | 199 (149,2 h) | 0 | 0 |
| permanenza in formazione | 604 | 1 | 3 (2,2 h) | 7 (5,2 h) | 26 (19,5 h) | 0 | 0 |
| permanenza sospeso con P1 | 244 | 1 | 11 (8,2 h) | 40 (30 h) | 197 (147,8 h) | 0 | 0 |
| permanenza sospeso senza P1 | 58 | 1 | 2 (1,5 h) | 6 (4,5 h) | 10 (7,5 h) | 0 | 0 |
| permanenza utilizzabile | 526 | 1 | 5 (3,8 h) | 15 (11,2 h) | 52 (39 h) | 0 | 0 |

**Triple correnti nel DEV, contate a parte** (non sono strutture bloccate dal posto): 2.666 con geometria non qualificante, 729 con base testata prima di un attraversamento, 1.694 senza attraversamento finché correnti, 743 qualificate.

**Concentrazione e lunghe occupazioni** (descrittive, nessuna soglia):
- mesi con più nascite: 2024-11 (36), 2024-07 (33), 2023-12 (31), 2023-01 e 2024-03 (30);
- le cinque occupazioni più lunghe durano 199, 114, 107, 98 e 96 barre; finiscono tutte per sostituzione, dopo una lunga sospensione.

Nessun riferimento è aperto a fine copertura e nessuna lacuna nel DEV: la categoria «continuità interrotta» è verificata solo sui test sintetici.

## 5. Casi preregistrati

Regola del §12.3. **6 riferimenti coprono 11 categorie**. Categorie vuote, non sostituite:
- `CONTINUITY_INTERRUPTED`: nessuna lacuna nei dati DEV;
- `OPEN_AT_END_FIRST_BORN`: nessun riferimento aperto al 2025-01-01.

Orari UTC.

1. **`MOV:LONG:1672574400000:1672585200000:1672596000000`**: prima nascita LONG, primo passaggio a UTILIZZABILE, prima struttura opposta successiva, prima sostituzione dopo sospensione.
   - Tripla Q 16.488,0 → B 16.565,9 → P0 16.524,6; nasce il 1° gennaio 2023 alle 18:00 (chiusura 16.561,8 → 16.573,1).
   - P1 16.618,8 è pubblicato alle 22:30: diventa UTILIZZABILE.
   - Alle 03:00 del 2 gennaio la struttura 45m diventa opposta: sospensione. Poi per 15 chiusure il prezzo tocca o supera P1, registrato come fatto da sospeso, ma la lettura **non** viene riattivata.
   - Alle 15:00 è sostituito da una nuova struttura SHORT.
2. **`MOV:SHORT:1672658100000:1672660800000:1672671600000`**: prima nascita SHORT, prima perdita della base.
   - Nasce alle 15:00 del 2 gennaio come successore del caso 1 (rompe B 16.696,0).
   - Alla chiusura successiva (16.737,4) chiude oltre P0 16.736,1: NON_SOSTIENE_PIU_LA_TESI, senza P1.
3. **`MOV:LONG:1672820100000:1672844400000:1672857900000`**: prima struttura non adottata per riferimento utilizzabile, primo test dell'origine.
   - UTILIZZABILE dal 4 gennaio alle 21:00.
   - Il 5 gennaio alle 07:30 una struttura SHORT qualificata è rifiutata perché il posto è occupato.
   - Sospeso per struttura opposta alle 09:00, poi tre test della base come fatti successivi.
   - Perde la base il 6 gennaio alle 11:15.
4. **`MOV:LONG:1673241300000:1673246700000:1673260200000`**: primo completamento geometrico. Nasce il 9 gennaio alle 10:30, P1 17.277,7 alle 12:45, ritorno a P1 alle 14:15.
5. **`MOV:LONG:1674367200000:1674388800000:1674399600000`**: prima struttura opposta alla nascita. Nasce il 22 gennaio alle 15:00 già sospeso; due test della base, poi la perde alle 20:15 senza P1.
6. **`MOV:LONG:1699469100000:1699477200000:1699490700000`**: prima struttura non adottata per formazione occupante. Nato il 9 novembre 2023 alle 00:45; alle 03:00 una tripla LONG qualificata è rifiutata perché il principale è ancora in formazione; P1 alle 04:30, completamento alle 10:30.

## 6. Rappresentabilità: risposta descrittiva

La domanda del §12.4: il ciclo rappresenta sequenze concretamente consultabili, oppure resta prevalentemente in formazione, sospensione o blocco? I fatti osservati nel DEV, senza alcuna attribuzione di efficacia:

- **Il ciclo produce sequenze complete e consultabili:**
  - 631 nascite in 24 mesi, da 19 a 36 al mese;
  - 600 arrivano a conoscere P1 (95%), mediana 3 barre dopo la nascita;
  - 526 passano a UTILIZZABILE (83%);
  - tutte si concludono entro il DEV: completamento geometrico 275 (44%), perdita della base 234 (37%), sostituzione 122 (19%).
- **Durata.** Le letture sono brevi: nascita → archiviazione mediana 10 barre (7,5 h), P90 37 (27,8 h).
- **Principale presente.** È assente nel 56% delle chiusure. Nelle 10.288 chiusure con principale la ripartizione è:

  | Condizione | Chiusure | Quota |
  |---|---:|---:|
  | In formazione | 2.265 | 22% |
  | Utilizzabile | 3.431 | 33% |
  | Sospeso con P1 | 4.426 | 43% |
  | Sospeso senza P1 | 166 | 2% |

  **La sospensione è la condizione occupata più frequente** ed è anche la più lunga: permanenza mediana sospeso con P1 11 barre, P90 40, massimo 197.
- **Sospensioni iniziali:** 259 su 631 riferimenti: 128 per test dell'origine, 104 per struttura opposta successiva, 27 alla nascita.
- **Durante la sospensione il metodo registra ma non usa** (scelta conservativa del contratto):
  - 1.265 barre con P1 toccato da sospeso;
  - 178 barre con nuovo test;
  - 159 passaggi a struttura opposta.

  Delle 234 perdite, 137 avvengono da sospeso e 75 da utilizzabile.
- **Strutture qualificate non adottate:** 112 su 743 (15%), cioè 57 per utilizzabile occupante, 50 per freschezza (35 delle quali con posto libero) e 5 per formazione occupante. La formazione blocca raramente, perché dura poco (mediana 3 barre).

In sintesi descrittiva: la rappresentazione è consultabile e si risolve quasi sempre in poche ore. Una parte rilevante del tempo con principale passa però in sospensione persistente, e lì il prezzo spesso torna a P1 senza che la lettura venga riattivata. È in questo punto che la rappresentazione perde informazione in modo esplicito. Non ne deriva una conclusione su utilità o inefficacia: la decisione sulla prossima domanda spetta al Director.

## 7. Come consultare un caso (per Gian)

1. Dalla cartella `dashboard`: `npm run dev`, quindi apri l'indirizzo mostrato.
2. **Studio storico** → **Apri studio storico** → scegli un file in `C:\Projects\algorithmic-trader-data\MOVE-001\runs\MOVE-001-v1.0.1-e1.0.0-3b76888642-30e67d8fe2\cases\`. I nomi seguono l'ordine della sezione 5.
3. Il lettore si apre alla nascita del riferimento. Con «Chiusura successiva» vedi cambiare il giudizio solo quando un fatto diventa noto; la scheda elenca i fatti fino a quel momento. «Vai alla nascita» riporta all'inizio.

Non c'è un seguito 24h né alcuna operazione. Non devi controllare formule.

## 8. Limiti

- Rappresentazione sperimentale su DEV già esposto: nessuna efficacia, regola operativa o promozione.
- Scelte conservative del contratto: scala 45m, ritardo dei pivot 2+2, sospensione non reversibile, nessuna scadenza. Possono perdere continuazioni reali (vedi caso 1).
- I fatti successivi da sospeso sono contati per barra, quindi non sono numeri di riferimenti.
- Nessuna lacuna nel DEV: la gestione delle interruzioni è verificata solo su dati sintetici.
- Nessun riferimento aperto a fine copertura, quindi nessuna durata censurata nel DEV.
- Gli esempi sono 6 riferimenti per 11 categorie, tutti nel 2023 tranne uno, per effetto della regola «primo cronologico».
- Verifiche e riscontro sono dello stesso esecutore: non sono una review indipendente.

## 9. Review del Director — 17 ottobre 2026, base 1235e64

**Esito: correzioni R1 richieste prima della chiusura; nessuna modifica metodologica richiesta.**

Lettura diretta di config, modulo MOVE-001, test, adattatore e diff rispetto a 9b536a2. Nella copia isolata del Director: **19/19 test Python MOVE-001 e 60/60 test del lettore storico superati; typecheck e build superati**. Nessun dato reale DEV disponibile nella copia: non ricalcolati i 701 riferimenti, non verificati indipendentemente hash/output locali, conteggi o screenshot reali dell'esecutore. Le prove seguenti sono sintetiche e sono del Director.

### 9.1 Difetti riprodotti

**R1-A — validazione incompleta del nuovo ledger.** In `dashboard/src/historical/loadBundle.ts:250–279`, i fatti MOVE-001 ricevono controlli generici ma non tutti quelli necessari a `MoveCard` e al suo stato:
1. Partire dalla fixture sintetica MOVE-001 consegnata; eliminare `case.ledger[0].B`. `parseBundle` accetta; renderizzare la scheda alla nascita provoca `Cannot read properties of undefined (reading 'price')` in `MoveCard.tsx:46`.
2. Eliminare `candidateOpen` dal P1 del fatto `P1_PUBLISHED`: importazione accettata benché il timestamp sia usato nella descrizione.
3. Aggiungere `USABLE` dopo la conclusione, allo stesso timestamp: importazione accettata; il riduttore può sovrascrivere il giudizio conservando l'archiviazione. Non è un ledger coerente con una lettura conclusa.

Tre nuove asserzioni di rifiuto falliscono sulla consegna; un controllo aggiuntivo conferma l'errore di rendering del primo caso. Il contenimento `ViewGuard` limita il danno, ma non conserva lo studio precedente come farebbe il rifiuto preventivo. Occorre validazione dei campi effettivamente letti per ogni evento e coerenza minima delle transizioni, non ricalcolo dei prezzi.

**R1-B — ultima chiusura esclusa dalla consultazione.** `src/move001/consult.py:28` limita le origini a `study.end - bar`; il validatore comune vieta `origin >= periods.end`. Se il riferimento è aperto alla fine, l'evento `OPEN_AT_END` esiste a `study.end` ma non è raggiungibile dal cursore. Riguarda anche una conclusione di mercato esattamente sull'ultima chiusura disponibile.

Riproduzione senza dati reali: usare la stessa catena sintetica di `move001.fixture.build`, scegliere l'ultimo riferimento invece del primo, poi `package`. L'ultimo riferimento è aperto; fine copertura **1665446400000**, ultima origine selezionabile **1665443700000**: manca una barra45m. Il pacchetto viene accettato; `HistoricalStudy.snapshot(end)` trova già l'ultima candela completa e `moveFactsAt(end)` contiene l'evento, ma `end` non è selezionabile. Il test che richiede l'ultima chiusura fallisce. Non serve alcun prezzo successivo al confine per mostrarla. I sei casi reali non risultano dimostrati affetti: nessuna riapertura del DEV per cercarne uno.

### 9.2 Nove scelte dichiarate e portata dei risultati

Le scelte §2 sono compatibili col contratto nei limiti seguenti: identità/versioni e freschezza seguono i fatti causali; assegnazione al mese della barra aperta, occupazione misurata dopo il trattamento della chiusura, fatti ulteriori per barra/passaggio e finestre di consultazione restano convenzioni di rendicontazione esplicite. La consultazione deve però comprendere l'ultima chiusura (R1-B). La doppia tipizzazione di `case` è debito tecnico locale accettabile se il discriminante e la validazione runtime proteggono le viste (R1-A); nessuna riscrittura generale del lettore richiesta.

`verify.py` è un controllo aggiuntivo scritto dall'autore che verifica alcuni invarianti partendo dai riferimenti del ciclo, non una seconda ricostruzione indipendente di tutta la popolazione e delle decisioni. Non certifica la completezza dei candidati né ricalcola autonomamente la conferma dei pivot. La ripetizione deterministica della stessa catena verifica riproducibilità, non assenza di ogni errore. Correggere la parola «indipendente» dove usata senza questa qualificazione.

Lettura provvisoria sui numeri riportati, non ricalcolati dal Director: la candidata produce sequenze consultabili e non resta soltanto in formazione. Assenza del principale nel56% delle chiusure non è automaticamente un difetto: è una popolazione specifica. Dei112 rifiuti,62 sono per posto occupato in formazione/utilizzabile e50 per freschezza (35 con posto già libero): non attribuire tutti112 al solo vincolo del posto. Le1265 barre di contatto da sospeso non sono1265 riferimenti né continuazioni riuscite; i doppi test della stessa barra sono rappresentati separatamente dai flag. I fatti non scompaiono dal ledger: la scelta conservativa rinuncia a riutilizzarli nella vecchia lettura. Nessuna prova di efficacia di P0/P1 e nessuna riattivazione o strategia autorizzata.

### 9.3 Incarico R1

Registrato in current_task.md: correggere soltanto importazione/coerenza del ledger e accessibilità dell'ultima chiusura; verifiche mirate e aggiornamento di questa consegna. Semantica, config, dati, popolazione, ledger e riepiloghi reali restano invariati. Nessuna nuova applicazione DEV o download. Chiusura e giudizio finale Director dopo la verifica delle correzioni.
