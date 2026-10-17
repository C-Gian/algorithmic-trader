# CAND-001/v1 — backtest di sviluppo 2023–2024 (fase DEV)

**Licenza di questo file e delle immagini in `docs/research/CAND-001-screens/`:** derivati aggregati di dati Binance Vision. Solo per questi derivati si applica **CC BY-NC-SA 4.0** (https://creativecommons.org/licenses/by-nc-sa/4.0/).
- Attribuzione: **Fonte: Binance Vision** (https://data.binance.vision).
- Termini: https://github.com/binance/binance-public-data/blob/master/TERMS_AND_CONDITIONS.md (copia locale del 16 ottobre 2026, SHA256 `99c4921d…`, riusata da OBS-001).
- Uso personale di ricerca non produttiva; nessuna associazione commerciale.
- La licenza del codice non cambia. Dati grezzi e bundle non sono redistribuiti.

Che cosa è questo documento. Sono risultati di **operazioni ipotetiche modellate** su prezzi storici, con nozionale normalizzato fisso di 1.000 USDT per operazione, senza leva né reinvestimento. Non è il rendimento di un conto, non è una strategia validata e non autorizza denaro reale. I dati 2023–2024 sono destinati alle iterazioni di sviluppo, non sono dati mai visti. **Il 2025 non è stato elaborato economicamente:** il checkpoint spetta al Director.

## Provenienza

| Voce | Valore |
|---|---|
| Specifica | `docs/research/CAND-001-v1.md`, commit `0d4882848d014f8137153848171243674759370d` (17 ottobre 2026) |
| Configurazione | `config/CAND-001-v1.json`, candidato 1.0.0, SHA256 canonico `aed2c4ef627617d73972778097bbab5fb702ab5064ce9e6eb68ded2170ce4edf`. Preregistrata e pubblicata con motore e 28 test sintetici nel commit `8146336` prima di qualunque download o backtest |
| Osservazioni | OBS-001/v1 invariate (`3c4eb884…2387`), stesso osservatore con input da ottobre 2022 |
| Motore | `cand001` 1.0.0, schema `cand001.bundle/1` |
| Run | `CAND-001-v1.0.0-e1.0.0-DEV-adaa94c502-aed2c4ef62`; input hash `adaa94c502…`; bundle 9,1 MB, SHA256 `53d5fdcfbfe1c4ef…` |
| Riproducibilità | Il run è stato rieseguito dal commit `c597a5e` con bundle identico byte per byte |
| Prestazioni | 22,3 s in tutto: controllo input 18,4 s, osservatore + decisioni + ledger 1,9 s. Picco di memoria 532 MB (Python 3.12.14, Windows 10) |

## Dati effettivi (acquisiti il 17 ottobre 2026, 07:29–07:31 UTC)

| Tipo | File | Copertura | Note |
|---|---|---|---|
| Klines negoziate 1m | 27 ZIP, da ottobre 2022 a dicembre 2024, tutti nuovi | 1.185.120 minuti validi su 1.185.120 (inizializzazione 132.480) | Nessun mancante, invalido, duplicato o fuori ordine. I 7 ZIP verificati di OBS-001 sono del 2025: non servono a DEV e non sono stati letti |
| fundingRate | 24 ZIP, 2023–2024 | 2.193 eventi (731 giorni × 3), intervallo sempre 8 h, jitter massimo 29 ms | Nessuna anomalia di ordine o intervallo. Il checksum di gennaio 2023 coincide con quello del Director (`05e3df32…`) |
| markPriceKlines 1m | 24 ZIP, 2023–2024 | Serve 1 punto per evento: 2.189 disponibili su 2.193 | Manca un giorno intero di mark nel febbraio 2023 (funding del 24 febbraio alle 08:00 e 16:00 e del 25 alle 00:00) e 2 minuti nell'agosto 2024. Il punto del 1° gennaio 2023 alle 00:00 richiederebbe il mark di dicembre 2022, non acquisito: non serve, perché la finestra parte senza posizioni. **Nessuna operazione è toccata dai punti mancanti.** Checksum di gennaio 2023 uguale a quello del Director (`18abe5d6…`) |

Identità dello strumento (BTCUSDT, PERPETUAL, BTC/USDT, margine USDT) e termini sono riusati dalla verifica OBS-001 del 16 ottobre, con provenienza registrata nel manifest. Sono metadati correnti, non certificano condizioni storiche.

**Assunzioni economiche** (dalla sezione 9 del protocollo, non verificate su un conto):
- **Baseline.** Fee 5 bp per lato e slippage 3 bp avverso per ogni eseguito; tutte le uscite modellate taker.
- **Funding.** Storico, valorizzato con il close mark 1m del minuto precedente.
- **Stress.** 10 + 10 bp sullo stesso ledger: è una rivalutazione, non un secondo percorso.

## Riscontro indipendente (script separato dal motore)

Dai minuti grezzi riletti dai CSV, per tutte le 87 call:
- A0;
- ampiezza della gamba ≥ 3A0;
- profondità della reazione tra 1/4 e 3/4;
- condizione di trigger;
- S0.

Per tutte le 78 operazioni:
- ingresso a open+60s;
- percorso minuto per minuto con le precedenze (gap, uscite dovute, attivazione dello stop, contatti intraminuto stop-first);
- motivo e prezzo d'uscita;
- netto con fee e funding.

**Zero differenze.**


## Diagnosi DEV (classi del protocollo)

Le regole della v1 sono rimaste invariate. Le scomposizioni qui sotto sono descrittive, calcolate sul ledger e sui minuti, e non selezionano operazioni o parametri.

**Bug — nessuno trovato.** Il riscontro indipendente coincide su tutte le call e le operazioni. Durante lo sviluppo i test hanno segnalato solo errori nei miei casi di test, non nel motore: profondità 1/4 e 3/4 sono ammesse ai bordi, e un 1D indisponibile non è un 1D contrario.

**Decisione non fedele al disegno — nessuna individuata.** Due interpretazioni tecniche mie, da confermare:
- le contraddizioni della reazione sono valutate anche alla chiusura di creazione t0, dove il trigger è comunque vietato. Non cambia gli ingressi, anticipa al massimo di una barra la conclusione di un episodio già perso;
- un'operazione che si chiude esattamente su una chiusura 45m rende «occupata» quella chiusura per nuove gambe.

**Scelta coerente ma poco utile — principale.** Il risultato è negativo già ai prezzi di riferimento, prima dei costi: −85,44 USDT su 78 operazioni.
- Il target (ritorno a P1) viene raggiunto in 17 operazioni su 78 (22%). Con il rapporto spazio/rischio mediano all'ingresso di 2,05 (P10 1,59, P90 3,39), un percorso fatto solo di target e stop richiederebbe circa il 33% per il pareggio lordo.
- Le 56 uscite in stop si erano mosse a favore di appena 0,38R (mediana dell'escursione favorevole massima, R = rischio geometrico iniziale). Solo il 25% aveva toccato almeno 1R prima dello stop.
- La ripresa (chiusura oltre il massimo o minimo precedente) non è stata seguita, in media, da un ritorno all'estremo prima dell'invalidazione.
- Le uscite per struttura opposta (4) e per 24 ore (1) sono rare.
- Le protezioni aggiornate (31 su 23 operazioni) non cambiano il quadro: il netto di quelle operazioni è −21,65.

**Costo/assunzione sensibile — rilevante.**
- Lo stop è vicino: il rischio iniziale mediano è lo 0,57% del nozionale. Fee e slippage di un giro valgono così circa il 28% di R (mediana; P10 14%, P90 49%).
- Dei −210,59 di netto, −124,81 sono fee e slippage assunti. Lo stress porta il netto a −397,80.
- Anche a costi zero il risultato resterebbe negativo (−85,44).
- Funding trascurabile (−0,34), nessuna ambiguità ai confini e nessun funding mancante nelle operazioni.
- Nessun contatto stop+target nello stesso minuto e nessuna uscita in gap: il risultato non dipende dall'ordine intrabar.

**Informazione insufficiente — da tenere presente.**
- Le operazioni sono 78 in 24 mesi (circa 3 al mese), con 2,0% del tempo in posizione.
- I mesi negativi sono 15, quelli positivi 8, uno senza operazioni.
- La perdita non dipende da pochi casi: i 5 trade maggiori pesano il 14,7% della somma dei |netti|.
- LONG e SHORT sono entrambi negativi: 30 operazioni a −92,24 e 48 a −118,35.
- 2023 e 2024 hanno un profilo simile (−115,87 e −94,72).
- Il campione resta piccolo per conclusioni forti in un senso o nell'altro.

**Dove si perde la selezione.** Su 5.832 gambe considerate:
- 3.549 sono escluse perché la struttura 45m non è nel verso;
- 995 per ampiezza insufficiente;
- 473 perché il candidato era occupato;
- 814 sono riconosciute.

Delle 814:
- 271 si astengono per rapporto spazio/rischio sotto 1,5 (mediana 0,68: la ripresa avviene spesso già vicino a P1);
- 266 per reazione oltre 3/4 o oltre P0;
- 161 perché P1 era già stato ritoccato;
- 15 per scadenza e 14 per struttura opposta;
- 9 richieste sono rifiutate al prezzo d'ingresso.

**Non è una raccomandazione di revisione.** La scelta fra mantenere la v1 e una sola revisione motivata spetta al Director. Le osservazioni qui sopra non sono una griglia di soglie da provare.

## Casi contrari ed esempi

Gli esempi sono stati scelti con la regola cronologica registrata (sezione 12 del protocollo). Il primo episodio SHORT del 1° gennaio 2023 è insieme prima call, prima operazione, primo caso negativo e prima protezione aggiornata: −2,69 USDT, uscita in stop dopo aver alzato la protezione. Nell'app i cinque pulsanti aprono direttamente questi episodi. Nella tabella in fondo ci sono anche il primo positivo e le prime astensioni per verso. Le categorie vuote (astensione per dato mancante) sono dichiarate.

## Limiti

- Esecuzione modellata: nessun order book, nessuna coda, impatto o profondità; nessun margine, leva o liquidazione.
- Fee e slippage sono assunzioni di studio. Il funding usa un proxy mark 1m.
- Le risoluzioni sono 1m: i contatti dentro il minuto seguono la regola stop-first, che qui non è mai servita.
- Il drawdown è calcolato sulle chiusure 1m, non tick per tick.
- 2023–2024 sono dati di sviluppo già usati per questa diagnosi.

## Tabelle generate dal motore

Mesi assegnati per ingresso; cashflow per data effettiva. Arrotondamento solo in visualizzazione.

### Popolazione, opportunità e operazioni

| Voce | 2023 | 2024 | DEV |
|---|---:|---:|---:|
| Chiusure 45m (valide) | 11680 (11680) | 11712 (11712) | 23392 (23392) |
| Gambe considerate | 2926 | 2906 | 5832 |
| Episodi riconosciuti | 372 | 442 | 814 |
| Call (LONG/SHORT) | 45 (21/24) | 42 (11/31) | 87 (32/55) |
| Ingressi eseguiti / rifiutati prezzo / senza quotazione | 41 / 4 / 0 | 37 / 5 / 0 | 78 / 9 / 0 |
| Operazioni (LONG/SHORT) | 41 (19/22) | 37 (11/26) | 78 (30/48) |
| Uscite STOP / TARGET / STRUTTURA / 24h / FINE | 30 / 9 / 1 / 1 / 0 | 26 / 8 / 3 / 0 / 0 | 56 / 17 / 4 / 1 / 0 |
| Protezioni aggiornate (operazioni) | 17 (12) | 14 (11) | 31 (23) |
| Stop e target nello stesso minuto | 0 | 0 | 0 |
| Uscite in gap all'apertura | 0 | 0 | 0 |

### Risultato modellato (USDT per operazioni da N0 = 1.000 USDT; somme, non rendimento composto)

| Voce | 2023 | 2024 | DEV |
|---|---:|---:|---:|
| PnL prezzi ai riferimenti | -49,79 | -35,65 | -85,44 |
| Slippage attribuito | -24,57 | -22,23 | -46,80 |
| Fee | -40,95 | -37,06 | -78,01 |
| Funding | -0,57 | 0,23 | -0,34 |
| **Netto modellato** | **-115,87** | **-94,72** | **-210,59** |
| Netto in punti base di N0 | -1.159 | -947 | -2.106 |
| Intervallo ambiguità funding | 0,000 / +0,000 | 0,000 / +0,000 | 0,000 / +0,000 |
| Sensibilità target-first (stesso minuto) | 0,00 | 0,00 | 0,00 |
| Netto stress (fee 10 bp, slippage 10 bp) | -214,15 | -183,65 | -397,80 |
| Quota operazioni nette positive | 24,4% | 24,3% | 24,4% |
| Payoff medio (vincita/perdita) | 1,29 | 1,67 | 1,48 |
| Profit factor | 0,42 | 0,54 | 0,48 |
| Netto per operazione: mediana (P25 / P75) | -5,45 (-6,78 / -1,69) | -5,95 (-7,96 / -0,93) | -5,76 (-7,06 / -1,12) |
| Netto per operazione: P10 / P90 | -8,80 / 8,77 | -11,65 / 11,13 | -9,62 / 10,12 |
| Durata mediana (minuti) | 220 | 254 | 227 |
| Rischio iniziale q·R0 / N0, mediana | 0,5% | 0,6% | 0,6% |
| Netto / rischio iniziale, mediana | -1,16 | -1,11 | -1,13 |
| Sequenza massima di perdite | 12 | 10 | 12 |
| Drawdown massimo (chiusure 1m) | -136,90 | -103,50 | -216,79 |
| Esposizione (quota del tempo in posizione) | 2,1% | 1,8% | 2,0% |
| Concentrazione top5 |netto| | 23,7% | 25,8% | 14,7% |
| Migliori 5 / somma positivi | 71,0% | 68,5% | 42,5% |
| Peggiori 5 / somma negativi | 27,0% | 31,3% | 16,7% |
| Operazioni con funding ambiguo / mancante | 0 / 0 | 0 / 0 | 0 / 0 |

### Mesi (operazioni per mese d'ingresso; cashflow per data effettiva)

| Mese | Chiusure valide | Episodi | Call | Operazioni | Netto per ingresso | Cashflow netto per data | Uscite S/T/Str/24h/Fine |
|---|---:|---:|---:|---:|---:|---:|---|
| 2023-01 | 992/992 | 34 | 6 | 5 | -28,80 | -28,80 | 4/1/0/0/0 |
| 2023-02 | 896/896 | 31 | 3 | 3 | 4,90 | 4,90 | 1/2/0/0/0 |
| 2023-03 | 992/992 | 31 | 2 | 2 | 16,85 | 16,85 | 0/2/0/0/0 |
| 2023-04 | 960/960 | 42 | 5 | 4 | 0,63 | 0,63 | 2/2/0/0/0 |
| 2023-05 | 992/992 | 30 | 5 | 4 | -22,67 | -22,67 | 4/0/0/0/0 |
| 2023-06 | 960/960 | 24 | 4 | 4 | -31,42 | -31,42 | 4/0/0/0/0 |
| 2023-07 | 992/992 | 26 | 1 | 1 | -5,45 | -5,45 | 1/0/0/0/0 |
| 2023-08 | 992/992 | 36 | 5 | 5 | -0,99 | -0,99 | 3/0/1/1/0 |
| 2023-09 | 960/960 | 28 | 4 | 4 | -26,82 | -26,82 | 4/0/0/0/0 |
| 2023-10 | 992/992 | 25 | 1 | 1 | 12,36 | 12,36 | 0/1/0/0/0 |
| 2023-11 | 960/960 | 35 | 7 | 6 | -39,57 | -39,57 | 6/0/0/0/0 |
| 2023-12 | 992/992 | 30 | 2 | 2 | 5,12 | 5,12 | 1/1/0/0/0 |
| 2024-01 | 992/992 | 37 | 5 | 5 | -18,27 | -18,27 | 4/1/0/0/0 |
| 2024-02 | 928/928 | 40 | 1 | 0 | 0,00 | 0,00 | 0/0/0/0/0 |
| 2024-03 | 992/992 | 32 | 1 | 1 | 22,62 | 22,62 | 0/1/0/0/0 |
| 2024-04 | 960/960 | 42 | 3 | 3 | -37,06 | -37,06 | 3/0/0/0/0 |
| 2024-05 | 992/992 | 35 | 7 | 6 | -0,45 | -0,45 | 3/3/0/0/0 |
| 2024-06 | 960/960 | 35 | 2 | 2 | -13,12 | -13,12 | 2/0/0/0/0 |
| 2024-07 | 992/992 | 51 | 3 | 2 | 10,79 | 10,79 | 1/1/0/0/0 |
| 2024-08 | 992/992 | 36 | 4 | 4 | -14,41 | -14,41 | 3/0/1/0/0 |
| 2024-09 | 960/960 | 29 | 5 | 4 | 14,90 | 14,90 | 1/2/1/0/0 |
| 2024-10 | 992/992 | 37 | 4 | 3 | -15,08 | -15,08 | 2/0/1/0/0 |
| 2024-11 | 960/960 | 35 | 3 | 3 | -15,59 | -15,59 | 3/0/0/0/0 |
| 2024-12 | 992/992 | 33 | 4 | 4 | -29,04 | -29,04 | 4/0/0/0/0 |

### Motivi delle gambe e degli episodi (totale)

| Esito della gamba | Numero |
|---|---:|
| ABSTAIN_STRUCTURE | 3549 |
| ABSTAIN_AMPLITUDE | 995 |
| RECOGNIZED | 814 |
| SKIPPED_BUSY | 473 |
| ABSTAIN_DURATION | 1 |

| Conclusione dell'episodio | Numero |
|---|---:|
| ABSTAIN_REWARD_RISK | 271 |
| INVALIDATED_DEPTH | 266 |
| INVALIDATED_TARGET_REACHED | 161 |
| CLOSED | 78 |
| EXPIRED | 15 |
| INVALIDATED_STRUCTURE | 14 |
| REJECTED_PRICE | 9 |

### Esempi (regola cronologica registrata prima degli esiti)

| Verso | Categoria | Riferimento | Momento UTC |
|---|---|---|---|
| LONG | FIRST_CALL | EP:LONG:1672793100000:1672803900000 | 2023-01-04T06:45:00Z |
| LONG | FIRST_TRADE | TR:LONG:1672793100000:1672803900000 | 2023-01-04T06:46:00Z |
| LONG | FIRST_NEGATIVE_TRADE | TR:LONG:1673651700000:1673654400000 | 2023-01-14T06:46:00Z |
| LONG | FIRST_POSITIVE_TRADE | TR:LONG:1672793100000:1672803900000 | 2023-01-04T06:46:00Z |
| LONG | FIRST_PROTECTION_UPDATE | TR:LONG:1682610300000:1682621100000 | 2023-04-28T04:31:00Z |
| LONG | FIRST_ABSTAIN_REACTION_INVALIDATED | EP:LONG:1672555500000:1672574400000 | 2023-01-01T16:30:00Z |
| LONG | FIRST_ABSTAIN_REWARD_RISK | EP:LONG:1672585200000:1672604100000 | 2023-01-01T23:15:00Z |
| LONG | FIRST_ABSTAIN_MISSING_DATA | categoria vuota | — |
| SHORT | FIRST_CALL | EP:SHORT:1672496100000:1672525800000 | 2023-01-01T03:45:00Z |
| SHORT | FIRST_TRADE | TR:SHORT:1672496100000:1672525800000 | 2023-01-01T03:46:00Z |
| SHORT | FIRST_NEGATIVE_TRADE | TR:SHORT:1672496100000:1672525800000 | 2023-01-01T03:46:00Z |
| SHORT | FIRST_POSITIVE_TRADE | TR:SHORT:1675593000000:1675622700000 | 2023-02-06T02:16:00Z |
| SHORT | FIRST_PROTECTION_UPDATE | TR:SHORT:1672496100000:1672525800000 | 2023-01-01T03:46:00Z |
| SHORT | FIRST_ABSTAIN_REACTION_INVALIDATED | EP:SHORT:1672965900000:1672984800000 | 2023-01-06T09:45:00Z |
| SHORT | FIRST_ABSTAIN_REWARD_RISK | EP:SHORT:1675050300000:1675080000000 | 2023-01-30T15:45:00Z |
| SHORT | FIRST_ABSTAIN_MISSING_DATA | categoria vuota | — |
