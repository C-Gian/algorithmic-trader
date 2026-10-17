# CAND-001/D1 — diagnosi della politica v1 sul DEV 2023–2024

**Stato del documento: consegna D1 dell'esecutore (DELIVERED, in attesa di review del Director).** Le sezioni 1–2 sono quelle pubblicate nel commit `78f5fd8`, prima di leggere i percorsi; dalla sezione 3 in poi i risultati dell'estrazione. Questa diagnosi descrive la v1: non sceglie né propone una revisione.

**Licenza di questo file:** derivati aggregati di dati Binance Vision, **CC BY-NC-SA 4.0** (https://creativecommons.org/licenses/by-nc-sa/4.0/). Fonte: Binance Vision (https://data.binance.vision). Dati grezzi e bundle non sono redistribuiti.

## 1. Piano

Perimetro e passi seguono `current_task.md` (CAND-001/D1, commit dell'incarico `12c195b`).

1. **Identità degli input.** Bundle DEV accettato `CAND-001-v1.0.0-e1.0.1-DEV-adaa94c502-aed2c4ef62`, SHA256 `b141150237e94a807817adea2d9fb6810f6eabc220d7db5ea3602d8b79b4944a`, inputHash `adaa94c50261a9650b3e908c28824db2dd91d3adecd46d1e6174b7cda93871a2`, config v1 `aed2c4ef627617d73972778097bbab5fb702ab5064ce9e6eb68ded2170ce4edf`. Il bundle preferito è presente: non si usa un altro run. Esiste anche un run DEV del motore 1.0.3, non usato per la regola di preferenza del task e non per il suo contenuto.
2. **Selezione degli esempi** (questo documento, sezione 2): solo dal bundle, con la regola cronologica del task. Pubblicata prima di leggere i percorsi minuto per minuto.
3. **Estrazione.** Un record per ciascuna delle 78 operazioni, dal bundle e dai soli minuti negoziati DEV già verificati (2022-10 … 2024-12; il prefisso serve solo alle osservazioni delle timeline). Nessun 2025, nessun download, nessun ricalcolo di decisioni: motore decisionale e ledger non vengono eseguiti.
4. **Riconciliazione** di 78 operazioni, 87 richieste, 814 episodi e netto non arrotondato con il bundle; identità dei costi su ogni record; hash degli input prima e dopo.
5. **Riepilogo** descrittivo e classi del protocollo, senza proporre revisioni, soglie o varianti.

Output estesi fuori Git in `algorithmic-trader-data/CAND-001/diagnosis/D1/`.

## 2. Esempi selezionati (regola fissata prima dei percorsi)

Regola del task, sezione 2: per ciascun verso il primo trade con netto positivo, il primo con netto negativo, il primo con stop aggiornato, la prima astensione `ABSTAIN_REWARD_RISK`, la prima `INVALIDATED_DEPTH` e la prima richiesta `REJECTED_PRICE`; in più il primo `EXIT_STRUCTURE` e il primo `TIME_EXIT` complessivi. Ordine: tempo pertinente, poi ID. Il caso è l'episodio; un caso scelto da più categorie compare una volta con tutte le categorie. Massimo 14 casi.

Tempo pertinente per categoria:
- netto positivo o negativo: ingresso modellato;
- stop aggiornato: prima attivazione di un nuovo stop (almeno un aggiornamento effettivamente attivato);
- astensioni: conclusione dell'episodio;
- `REJECTED_PRICE`: istante del tentativo;
- `EXIT_STRUCTURE` e `TIME_EXIT`: uscita contabile.

Netto positivo o negativo e motivo d'uscita sono **categorie a posteriori**; la scelta all'interno di ogni categoria è solo cronologica.

**Esito: 13 casi, nessuna categoria vuota.** Il primo trade SHORT negativo è anche il primo SHORT con stop aggiornato.

| # | Episodio | Operazione | Verso | Categorie | Tempo pertinente | t0 (gamba riconosciuta) | Call | Ingresso / tentativo | Fine episodio (UTC) |
|---:|---|---|---|---|---|---|---|---|---|
| 1 | `EP:SHORT:1672496100000:1672525800000` | `TR:SHORT:1672496100000:1672525800000` | SHORT | primo negativo; primo stop aggiornato | 2023-01-01 03:46 | 2023-01-01 00:45 | 2023-01-01 03:45 | 2023-01-01 03:46 | 2023-01-01 11:58 |
| 2 | `EP:LONG:1672585200000:1672604100000` | — | LONG | prima `ABSTAIN_REWARD_RISK` | 2023-01-01 23:15 | 2023-01-01 22:30 | — | — | 2023-01-01 23:15 |
| 3 | `EP:LONG:1672793100000:1672803900000` | `TR:LONG:1672793100000:1672803900000` | LONG | primo positivo | 2023-01-04 06:46 | 2023-01-04 06:00 | 2023-01-04 06:45 | 2023-01-04 06:46 | 2023-01-04 08:23 |
| 4 | `EP:SHORT:1672992900000:1673011800000` | — | SHORT | prima `INVALIDATED_DEPTH` | 2023-01-06 15:45 | 2023-01-06 15:45 | — | — | 2023-01-06 15:45 |
| 5 | `EP:LONG:1673271000000:1673287200000` | — | LONG | prima `INVALIDATED_DEPTH` | 2023-01-09 20:15 | 2023-01-09 20:15 | — | — | 2023-01-09 20:15 |
| 6 | `EP:LONG:1673651700000:1673654400000` | `TR:LONG:1673651700000:1673654400000` | LONG | primo negativo | 2023-01-14 06:46 | 2023-01-14 02:15 | 2023-01-14 06:45 | 2023-01-14 06:46 | 2023-01-14 09:18 |
| 7 | `EP:SHORT:1674329400000:1674353700000` | — | SHORT | prima `REJECTED_PRICE` | 2023-01-22 08:16 | 2023-01-22 04:30 | 2023-01-22 08:15 | 2023-01-22 08:16 (rifiutata) | 2023-01-22 08:16 |
| 8 | `EP:SHORT:1675050300000:1675080000000` | — | SHORT | prima `ABSTAIN_REWARD_RISK` | 2023-01-30 15:45 | 2023-01-30 14:15 | — | — | 2023-01-30 15:45 |
| 9 | `EP:SHORT:1675593000000:1675622700000` | `TR:SHORT:1675593000000:1675622700000` | SHORT | primo positivo | 2023-02-06 02:16 | 2023-02-05 21:00 | 2023-02-06 02:15 | 2023-02-06 02:16 | 2023-02-06 05:28 |
| 10 | `EP:LONG:1680485400000:1680517800000` | — | LONG | prima `REJECTED_PRICE` | 2023-04-03 14:16 | 2023-04-03 12:45 | 2023-04-03 14:15 | 2023-04-03 14:16 (rifiutata) | 2023-04-03 14:16 |
| 11 | `EP:LONG:1682610300000:1682621100000` | `TR:LONG:1682610300000:1682621100000` | LONG | primo stop aggiornato | 2023-04-28 08:16 | 2023-04-27 21:00 | 2023-04-28 04:30 | 2023-04-28 04:31 | 2023-04-28 08:18 |
| 12 | `EP:SHORT:1691155800000:1691180100000` | `TR:SHORT:1691155800000:1691180100000` | SHORT | primo `EXIT_STRUCTURE` (complessivo) | 2023-08-05 06:46 | 2023-08-04 22:30 | 2023-08-05 01:30 | 2023-08-05 01:31 | 2023-08-05 06:46 |
| 13 | `EP:SHORT:1692243900000:1692306000000` | `TR:SHORT:1692243900000:1692306000000` | SHORT | primo `TIME_EXIT` (complessivo) | 2023-08-19 03:01 | 2023-08-17 23:15 | 2023-08-18 03:00 | 2023-08-18 03:01 | 2023-08-19 03:01 |

Gli ID degli episodi contengono gli istanti di apertura delle candele di P0 e P1 (ms UTC). L'elenco completo, con tempi in ms, è in `diagnosis/D1/examples-selection.json`, `listSha256` `7caade6984943a7e333660dc4ef702e6ed87022b58ec7c386e70ecd308a8c3be` (hash canonico della lista e delle categorie vuote). Comando: `$env:PYTHONPATH = "src"; python3.12 -m cand001.diagnosis select`.

**Dichiarazione.** Prima della selezione ho stampato, per capire la struttura del bundle, il record completo della prima operazione del ledger (caso 1: stati, piano ed economia del bundle, nessun minuto). Nessun altro percorso individuale è stato letto prima di questa pubblicazione. L'elenco non dipende da quella lettura: deriva solo dalla regola qui sopra.

All'estrazione la lista è stata riletta e il suo hash riverificato; nessun caso è stato aggiunto, tolto o sostituito.

## 3. Provenienza, riconciliazione e controlli

| Voce | Valore |
|---|---|
| Codice | `src/cand001/diagnosis.py`, commit `3c639a8b404e958d4975a8bcbdbab80f94ea8b9f` (checkout pulito al momento dell'estrazione) |
| Comandi | `$env:PYTHONPATH = "src"; python3.12 -m cand001.diagnosis select` poi `... extract` |
| Bundle | SHA256 `b141150237e94a807817adea2d9fb6810f6eabc220d7db5ea3602d8b79b4944a` prima e dopo; mai modificato |
| Config v1 | canonico `aed2c4ef627617d73972778097bbab5fb702ab5064ce9e6eb68ded2170ce4edf`, invariata |
| Minuti letti | 27 ZIP trade 1m `2022-10 … 2024-12` della cartella CAND-001, SHA256 verificati con manifest e checksum del fornitore prima della lettura, uguali a quelli registrati nel bundle, e ricontrollati dopo: invariati. Nessun mese 2025, nessun download, nessun funding/mark grezzo (il funding per operazione è quello del bundle) |
| Motore e ledger | non eseguiti: nessuna decisione ricalcolata. Nessun passaggio strumentato è stato necessario |
| Output locali | `algorithmic-trader-data/CAND-001/diagnosis/D1/`: `trades.json` `e4acc5bc…3468`, `trades.csv` `204a1033…8561`, `examples-timelines.json` `20e16c72…e92d`, `summary.json` `ccc942ef…3801`, `examples-selection.json` `85fee8ac…9e30`, `provenance.json` (hash completi e prima/dopo di ogni input) |
| Riproducibilità | prima esecuzione dal codice non ancora committato e seconda dal commit pulito: `trades.json`, `trades.csv` ed `examples-timelines.json` identici byte per byte; `summary.json` cambiato solo per i campi aggiunti fra le due esecuzioni |
| Tempo | circa 11 s, quasi tutto per leggere e verificare gli ZIP |

**Riconciliazione su tutti i record**, eseguita dal comando, che si ferma se una sola voce non torna:
- 78 operazioni, 87 richieste e 814 episodi;
- netto `−210.58825128111891`, uguale bit per bit al valore del bundle (`summary.reconciliation.net`; −210,59 visualizzato);
- motivi d'uscita 56 STOP, 17 TARGET, 4 EXIT_STRUCTURE, 1 TIME_EXIT e 0 END_OF_SEGMENT, uguali al bundle;
- identità `netto = pricePnLRef − slippage − feeEntry − feeExit + funding` su ognuna delle 78 operazioni, residuo massimo 0. Lo slippage è preso come costo positivo `pricePnLRef − pricePnL`: nel bundle `slippageCost` ha il segno opposto. È già nei prezzi fill e non viene sottratto due volte;
- nessuna sovrapposizione fra operazioni;
- per ogni minuto detenuto (fino al minuto d'uscita escluso), né lo stop attivo in quel minuto né il target sono stati toccati. Il percorso letto dai minuti grezzi è quindi coerente con le uscite registrate dal ledger, senza contatti mancati.

**Test mirati** (`tests/test_cand001_diagnosis.py`, 9 test, tutti passati; nessuna suite generale):
- selezione: ordine per tempo e poi ID, deduplicazione che conserva le categorie, categoria vuota dichiarata e non sostituita, astensioni ordinate per conclusione;
- percorso: LONG e SHORT speculari;
- uscita intraminuto senza close né estremi del minuto d'uscita, e uscita all'open senza prezzi successivi;
- prima chiusura 45m solo se la posizione è ancora aperta (chiusa prima, contatto nel minuto di chiusura, uscita all'open seguente);
- latenza dello stop: il vecchio stop resta attivo nel minuto di latenza, e un aggiornamento non attivato per uscita è distinto;
- identità dei costi con i numeri del protocollo §13, senza doppio slippage.

## 4. Quadro integrato della v1 sul DEV

Sono dimensioni descrittive della **stessa** politica e dello stesso ledger: non sono quattro backtest né trattamenti indipendenti. Nessuna variante è stata calcolata. Importi in USDT per operazioni da N0 = 1.000 USDT, somme e non rendimento di un conto.

### 4.1 Periodi

| Periodo | Operazioni | Netto | PnL ai riferimenti | Drawdown max (1m) | Top5 \|netto\| | Migliori 5 / positivi | Peggiori 5 / negativi | Netto stress |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| DEV | 78 | −210,59 | −85,44 | −216,79 | 14,7% | 42,5% | 16,7% | −397,80 |
| 2023 | 41 | −115,87 | −49,79 | −136,90 | 23,7% | 71,0% | 27,0% | −214,15 |
| 2024 | 37 | −94,72 | −35,65 | −103,50 | 25,8% | 68,5% | 31,3% | −183,65 |

Valori ripresi dal riepilogo del bundle, non ricalcolati. Drawdown sulle chiusure 1m con il non realizzato; lo stress è la rivalutazione esistente a 10 + 10 bp, nessuno scenario nuovo.

| Mese | Op. | Netto | DD max | Mese | Op. | Netto | DD max |
|---|---:|---:|---:|---|---:|---:|---:|
| 2023-01 | 5 | −28,80 | −30,23 | 2024-01 | 5 | −18,27 | −22,33 |
| 2023-02 | 3 | 4,90 | −7,83 | 2024-02 | 0 | 0,00 | 0,00 |
| 2023-03 | 2 | 16,85 | −3,14 | 2024-03 | 1 | 22,62 | −5,55 |
| 2023-04 | 4 | 0,63 | −12,63 | 2024-04 | 3 | −37,06 | −41,50 |
| 2023-05 | 4 | −22,67 | −24,36 | 2024-05 | 6 | −0,45 | −41,37 |
| 2023-06 | 4 | −31,42 | −42,39 | 2024-06 | 2 | −13,12 | −13,12 |
| 2023-07 | 1 | −5,45 | −5,45 | 2024-07 | 2 | 10,79 | −14,62 |
| 2023-08 | 5 | −0,99 | −28,43 | 2024-08 | 4 | −14,41 | −26,63 |
| 2023-09 | 4 | −26,82 | −26,83 | 2024-09 | 4 | 14,90 | −18,30 |
| 2023-10 | 1 | 12,36 | −2,43 | 2024-10 | 3 | −15,08 | −15,08 |
| 2023-11 | 6 | −39,57 | −39,57 | 2024-11 | 3 | −15,59 | −20,50 |
| 2023-12 | 2 | 5,12 | −12,62 | 2024-12 | 4 | −29,04 | −29,04 |

Netto per mese d'ingresso, drawdown del mese a risoluzione 1m. I mesi negativi sono 15, quelli positivi 8, uno senza operazioni. Con 5 operazioni o meno la quota top5 vale per costruzione 100%; nei due mesi con 6 operazioni vale 88,6% (2023-11) e 91,0% (2024-05).

### 4.2 Popolazione: gambe, episodi, richieste e astensioni

- **Gambe considerate: 5.832.** Di queste:
  - 3.549 escluse perché la struttura 45m non era nel verso;
  - 995 per ampiezza sotto 3·A0;
  - 473 perché il candidato era occupato;
  - 1 per durata;
  - 814 riconosciute come episodi.
- **Episodi: 814**, conclusi così:
  - 271 `ABSTAIN_REWARD_RISK`, con rapporto indicativo mediano 0,68 (P10 0,21, P90 1,27; in un caso lo spazio verso P1 non era positivo);
  - 266 `INVALIDATED_DEPTH`, di cui **124 già alla chiusura di riconoscimento t0**: le due barre di reazione necessarie a confermare P1 avevano già superato 3/4 della gamba;
  - 161 `INVALIDATED_TARGET_REACHED`;
  - 15 `EXPIRED` e 14 `INVALIDATED_STRUCTURE`;
  - 9 `REJECTED_PRICE`;
  - 78 `CLOSED`.
- **Richieste: 87.** 78 eseguite e 9 rifiutate al prezzo; nessuna senza quotazione o a fine finestra. Tutte le 9 rifiutate avevano alla call un rapporto indicativo fra 1,52 e 1,66. L'apertura 60 s dopo si era mossa **nel verso del trade** di 0,03–0,15·A0 e il rapporto all'ingresso scendeva sotto 1,5 (fra 1,31 e 1,49). Nessun profitto o perdita viene attribuito a queste operazioni mai aperte.

### 4.3 Ingresso: che cosa era noto alla call (78 operazioni)

| Misura | n | P10 | P50 | P90 |
|---|---:|---:|---:|---:|
| Ampiezza gamba / A0 | 78 | 3,55 | 5,10 | 7,29 |
| Profondità della reazione al trigger | 78 | 0,40 | 0,55 | 0,72 |
| Chiusure 45m d'attesa da t0 alla call | 78 | 1,7 | 4,0 | 8,0 |
| Superamento dell'estremo della barra precedente / A0 | 78 | 0,02 | 0,10 | 0,23 |
| Corpo direzionale della barra di ripresa / A0 | 78 | 0,14 | 0,36 | 0,57 |
| Rapporto spazio/rischio indicativo alla call | 78 | 1,65 | 2,00 | 3,31 |
| Rapporto G0/R0 all'ingresso | 78 | 1,59 | 2,05 | 3,39 |
| R0 / prezzo d'ingresso | 78 | 0,0032 | 0,0057 | 0,0113 |

Struttura 45m alla call: nel verso in 67 casi (23 UP per LONG, 44 DOWN per SHORT), MIXED in 11. Il trigger supera l'estremo precedente di poco: mediana 0,10·A0, e in un decimo dei casi meno di 0,02·A0.

### 4.4 Percorso dopo l'ingresso (campionato alle chiusure 1m detenute)

Definizione fissata dal task: `z(p) = d·(p − Eref)/R0`, con R0 geometrico v1 dalla fill. Origine z = 0 al riferimento d'ingresso. Le chiusure considerate sono quelle dei minuti detenuti, dall'ingresso al minuto d'uscita escluso, e il riferimento d'uscita modellato è un punto finale separato. Sono descrizioni del percorso campionato: **non** sono MFE/MAE tick, profitto catturabile o un'uscita che si poteva scegliere.

| Misura (z in unità R0) | n | P10 | P50 | P90 |
|---|---:|---:|---:|---:|
| z alla prima chiusura 45m dopo l'ingresso, se ancora aperta | 67 | −0,39 | 0,02 | 0,44 |
| Massimo favorevole campionato max(0, z) | 78 | 0,07 | 0,64 | 1,67 |
| Minimo contrario campionato min(0, z) | 78 | −0,85 | −0,62 | −0,20 |
| z al riferimento d'uscita | 78 | −0,96 | −0,88 | 1,95 |
| Restituzione: massimo campionato − z d'uscita | 78 | −0,27 | 1,04 | 2,16 |
| Distanza iniziale dal target | 78 | 1,66 | 2,12 | 3,44 |
| Minuti dall'ingresso al massimo campionato | 78 | 3 | 94 | 317 |
| Durata / 24 h | 78 | 0,02 | 0,16 | 0,38 |
| Chiusure 1m detenute | 78 | 35 | 226 | 552 |

Esclusioni e mancanze:
- prima chiusura 45m: 11 operazioni erano già chiuse prima e sono escluse da quella riga, non sostituite con un prezzo successivo;
- nessun minuto mancante nei percorsi;
- in 6 operazioni nessuna chiusura detenuta è mai stata sopra l'ingresso (massimo = origine);
- 29 operazioni su 78 hanno almeno una chiusura a z ≥ 1;
- la restituzione negativa (P10) riguarda uscite al target raggiunto dentro un minuto, sopra ogni chiusura osservata.

Massimo favorevole campionato per motivo d'uscita (P50, con P10–P90):
- STOP (56): 0,31 (0,03–1,33);
- TARGET (17): 1,64 (1,33–2,23);
- EXIT_STRUCTURE (4): 0,65;
- TIME_EXIT (1): 1,38.

La «escursione favorevole» della consegna precedente (0,38R per gli stop) usava un'altra misura: non va confrontata con questa.

Spazio e tempo: il target si trova in mediana a 2,12 R0, il massimo campionato a 0,64. Le operazioni finiscono in mediana in 3,8 h (0,16 di 24 h), e il limite di 24 h scatta una sola volta.

### 4.5 Uscite, protezioni e costi: contributi, non cause

| Motivo d'uscita | n | PnL ai riferimenti | Slippage | Fee | Funding | Netto |
|---|---:|---:|---:|---:|---:|---:|
| STOP | 56 | −308,29 | −33,62 | −56,04 | −0,36 | −398,31 |
| TARGET | 17 | 193,08 | −10,19 | −16,98 | 0,07 | 165,98 |
| EXIT_STRUCTURE | 4 | 11,34 | −2,40 | −3,99 | −0,10 | 4,85 |
| TIME_EXIT | 1 | 18,43 | −0,59 | −0,99 | 0,05 | 16,89 |
| Totale | 78 | −85,44 | −46,80 | −78,01 | −0,34 | −210,59 |

| Stop in vigore all'uscita | n | PnL ai riferimenti | Slippage | Fee | Funding | Netto |
|---|---:|---:|---:|---:|---:|---:|
| Iniziale S0 | 55 | −100,71 | −33,00 | −55,00 | −0,23 | −188,94 |
| Aggiornato | 23 | 15,27 | −13,81 | −23,01 | −0,11 | −21,65 |
| Totale | 78 | −85,44 | −46,80 | −78,01 | −0,34 | −210,59 |

**Netto delle operazioni con aggiornamento ≠ effetto dell'aggiornamento.** Le 23 operazioni con stop aggiornato sono quelle durate abbastanza da formare un nuovo pivot dopo l'ingresso, e il loro esito con lo stop iniziale non è osservabile.

Gestione (decisioni alla chiusura 45m, efficacia a +60 s):
- 31 aggiornamenti decisi in 23 operazioni, **tutti attivati esattamente a decisione + 60 s**. In nessun caso un'uscita o un gap ha preceduto l'attivazione;
- 1 proposta scartata perché non migliorativa;
- 36 pivot protettivi ignorati perché la loro candela precedeva l'ingresso, come prescrive §7.2;
- 4 richieste `EXIT_STRUCTURE`, tutte eseguite all'apertura decisione + 60 s, senza stop o target nel minuto di latenza.

Costi:
- fee e slippage assunti valgono 124,81 contro un PnL ai riferimenti di −85,44;
- per operazione valgono in mediana 0,28 del rischio iniziale (P10 0,14, P90 0,49), perché R0 è in mediana lo 0,57% del prezzo;
- funding −0,34, nessuna ambiguità ai confini né funding mancante;
- 73 uscite intraminuto e 5 all'apertura; nessun contatto stop+target nello stesso minuto e nessuna uscita in gap: la regola STOP_FIRST non è mai intervenuta.

## 5. Esempi selezionati: noto allora, decisione, seguito

Per ogni caso: che cosa era noto alla decisione (barre chiuse, pivot già confermati, struttura, piano); che cosa ha deciso la v1; che cosa è successo dopo, fino all'uscita o alla conclusione e mai oltre. Infine quale osservazione contemporanea potrebbe sostenere o contraddire una spiegazione. Il ritardo di conferma dei pivot (due barre 45m dopo la candela) è parte delle definizioni OBS-001: non è un bug e non prova che l'estremo fosse utilizzabile prima. Orari UTC.

1. **SHORT, primo negativo e primo stop aggiornato** (`EP:SHORT:1672496100000:1672525800000`).
   - *Noto alla call (2023-01-01 03:45):* gamba da HIGH 16.640,0 (candela del 31/12 14:15) a LOW 16.461,8 (22:30), confermata alle 00:45; ampiezza 5,4·A0, struttura 45m DOWN, 1D MIXED. Reazione 0,53. La barra di ripresa chiude a 16.529,4, sotto il minimo precedente (16.534,8) e sotto l'apertura. Rapporto 1,74.
   - *Decisione e seguito:* ingresso alle 03:46. Alla prima chiusura 45m z = +0,44. Alle 08:15 un pivot HIGH (candela delle 06:00, confermato alle 08:15) porta lo stop da 16.560,41 a 16.549,01, efficace e attivato alle 08:16. La struttura 45m diventa MIXED dalle 09:00. Il massimo campionato è +0,89, dopo 322 minuti. Lo stop aggiornato è toccato nel minuto 11:57 (z d'uscita −0,55). Netto −2,69: riferimenti −1,19, slippage 0,60, fee 1,00, funding +0,10.
   - *Non deducibile:* se lo stop iniziale avrebbe dato un esito diverso (servirebbe il percorso dopo l'uscita).
   - *Osservazione utile:* il passaggio a MIXED era noto mentre la posizione restava aperta; la v1 non agisce su MIXED per scelta di §7.

2. **LONG, prima `ABSTAIN_REWARD_RISK`** (`EP:LONG:1672585200000:1672604100000`).
   - *Noto alle 23:15 del 1° gennaio:* gamba 16.524,6 → 16.618,8 (4,0·A0), reazione 0,42. La barra di ripresa chiude a 16.611,6, 7,2 USDT sotto P1, con massimo 16.617,4. Spazio 2,22 contro rischio 39,87: rapporto 0,06.
   - *Decisione:* astensione, episodio consumato.
   - *Osservazione utile:* la stessa chiusura che soddisfa il trigger lascia quasi nessuno spazio verso P1. È il caso tipico delle 271 astensioni con rapporto mediano 0,68; non si attribuisce alcun esito al trade non aperto.

3. **LONG, primo positivo** (`EP:LONG:1672793100000:1672803900000`).
   - *Noto alla call (2023-01-04 06:45):* gamba 16.645,7 → 16.904,4 (5,9·A0), struttura 45m e 1D UP, reazione 0,28. La ripresa supera il massimo precedente di 0,8 USDT (0,02·A0). Rapporto 1,57.
   - *Seguito:* alla prima chiusura 45m z = −0,16. Il massimo campionato è +1,10 dopo 17 minuti; il target è raggiunto nel minuto 08:22. Netto +1,44: riferimenti +3,07, costi 1,60.
   - *Osservazione utile:* qui un trigger marginale e un primo movimento contrario non hanno impedito il target. Una spiegazione basata sul margine del trigger andrebbe controllata sull'intera popolazione, non su questo caso.

4. **SHORT, prima `INVALIDATED_DEPTH`** (`EP:SHORT:1672992900000:1673011800000`).
   - *Noto a t0 (2023-01-06 15:45):* gamba 16.805,3 → 16.664,8 (3,3·A0). Le due barre di reazione necessarie a confermare P1 arrivano a 16.830,0, oltre P0 (profondità 1,18), con chiusura 16.816,9 sopra P0.
   - *Decisione:* invalidazione al riconoscimento.
   - *Osservazione utile:* la candela di P1 aveva già un massimo (16.812,6) sopra P0, ma il suo ordine interno è ignoto e la v1 non lo legge.

5. **LONG, prima `INVALIDATED_DEPTH`** (`EP:LONG:1673271000000:1673287200000`).
   - *Noto a t0 (2023-01-09 20:15):* gamba 17.181,9 → 17.387,8 (3,8·A0). Le due barre di reazione scendono a 17.218,3 (profondità 0,82).
   - *Decisione:* invalidazione al riconoscimento. È uno dei 124 casi chiusi a t0.

6. **LONG, primo negativo** (`EP:LONG:1673651700000:1673654400000`).
   - *Noto alla call (2023-01-14 06:45):* gamba di **una sola barra** (19.725,9 → 21.544,0, 6,3·A0; la barra delle 00:00 va da 19.882,6 a 21.544,0). Struttura 45m MIXED alla call (UP a t0), 1D UP. Reazione 0,46 dopo 6 chiusure d'attesa. La ripresa supera il massimo precedente di 0,05·A0. Rapporto 2,20 (2,10 all'ingresso).
   - *Seguito:* alla prima chiusura 45m z = −0,04; massimo campionato +0,30 dopo 119 minuti. Stop iniziale nel minuto 09:17. Netto −15,02: riferimenti −12,97, costi 1,59, funding −0,46.
   - *Osservazione utile:* gamba di una barra e struttura MIXED alla call erano entrambe note. Il caso 9, positivo, entra anche lui con struttura MIXED: nessuna delle due osservazioni basta da sola.

7. **SHORT, prima `REJECTED_PRICE`** (`EP:SHORT:1674329400000:1674353700000`).
   - *Noto alla call (2023-01-22 08:15):* rapporto 1,60, vincolo E ≥ 22.832,47.
   - *Seguito:* all'apertura delle 08:16 (22.833,5) la fill modellata vale 22.826,65, sotto il vincolo; rapporto 1,41, richiesta rifiutata. L'apertura si era mossa nel verso del trade di 0,06·A0.

8. **SHORT, prima `ABSTAIN_REWARD_RISK`** (`EP:SHORT:1675050300000:1675080000000`).
   - *Noto alle 15:45 del 30 gennaio:* la ripresa chiude a 23.109,9, sotto il minimo precedente. L'estremo di reazione a 23.282,0 porta lo stop a 23.310,10: rischio 207 contro spazio 173, rapporto 0,84.
   - *Decisione:* astensione.

9. **SHORT, primo positivo** (`EP:SHORT:1675593000000:1675622700000`).
   - *Noto alla call (2023-02-06 02:15):* gamba 23.406,0 → 22.741,0 (6,2·A0). 1D UP (solo contestuale), struttura 45m MIXED dalle 23:15. Reazione 0,53 dopo 7 chiusure. La ripresa supera il minimo precedente di 0,06·A0. Rapporto 2,10 alla call e 1,74 all'ingresso, perché l'apertura si era già mossa a favore.
   - *Seguito:* alla prima chiusura 45m z = +0,79; target nel minuto 05:27. Netto +8,77: riferimenti +10,37, costi 1,59.

10. **LONG, prima `REJECTED_PRICE`** (`EP:LONG:1680485400000:1680517800000`).
    - *Noto alla call (2023-04-03 14:15):* rapporto 1,52, vincolo E ≤ 28.234,85.
    - *Seguito:* apertura alle 14:16 a 28.232,9, fill modellata 28.241,37; rapporto 1,42, richiesta rifiutata.

11. **LONG, primo stop aggiornato** (`EP:LONG:1682610300000:1682621100000`).
    - *Noto alla call (2023-04-28 04:30):* gamba 28.814,4 → 29.898,0 (3,7·A0). La call arriva 10 chiusure dopo t0, a 11 barre da P1 (la scadenza è 12). Reazione 0,61, struttura 45m MIXED dalle 03:00, 1D MIXED. Rapporto 1,67 alla call e 1,51 all'ingresso.
    - *Seguito:* alla prima chiusura 45m z = −0,01; massimo campionato +0,25 dopo 77 minuti. Alle 08:15 un pivot LOW (candela delle 06:00) porta lo stop a 29.353,33, efficace alle 08:16; lo stop aggiornato è toccato nel minuto 08:17 (z −0,44). Netto −5,82.
    - *Non deducibile:* l'esito con lo stop iniziale.

12. **SHORT, primo `EXIT_STRUCTURE`** (`EP:SHORT:1691155800000:1691180100000`).
    - *Noto alla call (2023-08-05 01:30):* gamba 29.323,8 → 28.780,0 (5,4·A0), struttura 45m e 1D DOWN, reazione 0,67. Rapporto 2,79; target a 2,89 R0.
    - *Seguito:* alla prima chiusura 45m z = −0,09. La struttura passa a MIXED dalle 03:00 e a UP alle 06:45: la richiesta d'uscita è eseguita all'apertura delle 06:46 (decisione + 60 s), a z = −0,03, dopo un massimo campionato di +0,42. Netto −1,69, quasi tutto costi (1,60).

13. **SHORT, primo `TIME_EXIT`** (`EP:SHORT:1692243900000:1692306000000`).
    - *Noto alla call (2023-08-18 03:00):* gamba 28.694,9 → 24.581,0 in 17 h 15 min (9,5·A0). Reazione 0,59 e rapporto 3,27: target a 3,30 R0.
    - *Seguito:* 5 aggiornamenti dello stop (08:15, 11:15, 13:30, 21:00, 02:15), tutti attivati a + 60 s. Massimo campionato +1,38 dopo 862 minuti. Uscita all'apertura esatta di ingresso + 24 h (19/08 03:01) a z = 0,85. Netto +16,89.

## 6. Classi del protocollo

Per ogni classe: fatto osservato, informazione disponibile allora, decisione presa dalla v1, che cosa **non** si può dedurre.

**BUG — nessuno trovato in D1.**
- *Fatto:* riconciliazione esatta. Tutti i minuti detenuti sono coerenti con lo stop attivo e con il target. Aggiornamenti e uscite discrezionali sono avvenuti esattamente a decisione + 60 s.
- *Limite:* stesso autore del motore. Il controllo copre il ledger rispetto ai minuti grezzi, non ricalcola pivot, struttura o A (presi dal bundle). Che i controlli passino non dimostra che il metodo sia l'unica causa del risultato.

**NOT_FAITHFUL_TO_DESIGN — nessuna deviazione accertata; due interpretazioni da confermare.**
- **Contraddizioni valutate già a t0.** 124 delle 266 `INVALIDATED_DEPTH` terminano alla chiusura di riconoscimento.
  - L'esito di quegli episodi non dipende da questa scelta. Una profondità oltre 3/4 non può tornare indietro, perché l'estremo di reazione può solo allargarsi. E una chiusura oltre P0 implica già profondità maggiore di 1.
  - Ciò che può cambiare è l'occupazione del candidato alla chiusura successiva, e quindi quali gambe nuove risultano `SKIPPED_BUSY`. Il bundle non conserva gli eventi di gamba per ricostruirlo: **non ricostruito**.
- **Un'uscita su una chiusura 45m rende occupata quella chiusura** per nuove gambe: interpretazione già dichiarata nella consegna precedente, non riesaminata qui.
- I 36 pivot ignorati perché precedenti all'ingresso sono fedeli a §7.2.

**COHERENT_BUT_NOT_USEFUL — la descrizione più evidente, senza conclusione causale.**
- *Fatti:*
  - PnL ai riferimenti −85,44 già prima dei costi;
  - alla prima chiusura 45m il movimento mediano è nullo (z P50 +0,02, P10 −0,39, P90 +0,44);
  - il massimo campionato mediano (0,64 R0) copre circa il 30% della distanza mediana dal target (2,12 R0);
  - 29 operazioni su 78 arrivano a z ≥ 1, 17 al target;
  - gli stop hanno un massimo campionato mediano di 0,31.
- *Noto allora:* ampiezza, profondità, margine del trigger (mediana 0,10·A0), corpo, struttura 45m/1D (MIXED alla call in 11 casi), rapporto spazio/rischio.
- *Decisione v1:* ingresso alla chiusura che supera l'estremo della barra precedente, target fisso su P1, stop sotto o sopra l'estremo di reazione.
- *Non deducibile:*
  - che un altro trigger, target o filtro avrebbe dato di più: nessuna variante è stata calcolata;
  - che il movimento favorevole restituito fosse catturabile con un'uscita disponibile allora;
  - che un ingresso seguito da un ribasso provi l'utilità di un filtro.

**COST_OR_ASSUMPTION_SENSITIVE — rilevante.**
- *Fatti:*
  - fee e slippage assunti valgono 124,81, cioè una mediana di 0,28·R per operazione, perché lo stop è vicino (R0 mediano 0,57% del prezzo);
  - lo stress porta il netto a −397,80;
  - funding trascurabile;
  - STOP_FIRST mai usato, nessuna uscita in gap.
- *Non deducibile:* le tariffe e lo slippage reali dell'Owner. Anche il PnL ai riferimenti è negativo, quindi i costi assunti non sono l'unica componente della perdita.

**INSUFFICIENT_INFORMATION — da tenere presente.**
- *Fatti:*
  - 78 operazioni in 24 mesi, con 15 mesi negativi e 8 positivi;
  - top5 al 14,7% della somma dei |netti|: la perdita è distribuita, non dovuta a pochi trade;
  - LONG 30 operazioni −92,24, SHORT 48 operazioni −118,35;
  - 2023 e 2024 simili.
- *Limiti della misura:* risoluzione 1m, nessun ordine tick dentro il minuto, nessun percorso dopo l'uscita per costruzione.
- *Non deducibile:* conclusioni forti sulla famiglia di metodi, in un senso o nell'altro.

## 7. Evidenze per la decisione del Director

Elenco di fatti, non di proposte. Nessuna soglia, regola v2 o indicatore è suggerito.

1. **Ingresso.** Dopo il trigger la v1 non mostra in mediana movimento nel verso alla prima chiusura 45m. Il superamento dell'estremo precedente è spesso piccolo rispetto ad A0. Margine, corpo, profondità e struttura alla call erano noti a t e sono registrati per ogni operazione in `trades.csv`.
2. **Destinazione e tempo.** P1 resta lontano rispetto ai movimenti campionati (2,12 contro 0,64 R0 in mediana). La durata tipica è di alcune ore e il limite di 24 h quasi non interviene.
3. **Gestione.** Gli aggiornamenti funzionano come specificato (31 su 31 a + 60 s) e l'uscita per struttura è rara (4). Il netto delle operazioni aggiornate non misura l'effetto della regola.
4. **Costi.** In rapporto a R pesano molto, per la distanza ridotta dello stop: circa 0,28·R per giro in mediana.
5. **Astensioni.**
   - La selezione esclude soprattutto per struttura (3.549 gambe) e ampiezza (995).
   - Fra gli episodi, le astensioni per spazio/rischio (271, mediana 0,68) indicano riprese che avvengono già vicino a P1.
   - Le profondità invalidate a t0 (124) indicano reazioni già troppo ampie quando P1 diventa noto.
   - I 9 rifiuti al prezzo nascono da aperture mosse nel verso del trade quando il rapporto era vicino a 1,5.

Quale di questi punti sia un problema modificabile, con informazione disponibile allora e svantaggi dichiarati, è una decisione del Director, come prevede la sezione 6 del task.

## 8. Limiti e informazioni non ricostruibili

- Non è una preregistrazione: gli aggregati DEV e la diagnosi precedente erano già noti. Prima della lista ho letto il record di bundle del caso 1 (sezione 2).
- **Non ricostruito:** l'effetto della valutazione a t0 sulle gambe `SKIPPED_BUSY` (il bundle non conserva gli eventi di gamba); l'ordine dei prezzi dentro il minuto; prezzi, fee e slippage reali; qualsiasi esito di regole alternative o di operazioni mai aperte, esclusi dal mandato.
- Per i casi 4 e 5 il bundle non ha una finestra con le osservazioni a ogni momento: struttura e fatti vengono dagli stati dell'episodio, le barre dall'aggregazione 45m dei minuti verificati. Pivot, struttura e A non sono ricalcolati: sono quelli del bundle.
- Funding per operazione dal bundle: i file grezzi di funding e mark non sono stati riletti.
- `z` e gli estremi campionati usano le chiusure 1m e sono più conservativi di massimi e minimi dentro il minuto. Non coincidono con la misura di escursione usata nella consegna precedente.
- Riscontro dello stesso esecutore: non è una verifica indipendente del Director.
