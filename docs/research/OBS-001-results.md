# OBS-001 — risultati descrittivi (convenzioni OBS-001/v1)

**Licenza di questo file e delle immagini in `docs/research/OBS-001-screens/`:** sono derivati aggregati di dati Binance Vision. Si applica **CC BY-NC-SA 4.0** (https://creativecommons.org/licenses/by-nc-sa/4.0/) solo a questi derivati. Attribuzione: **Fonte: Binance Vision** (https://data.binance.vision). Termini della fonte: https://github.com/binance/binance-public-data/blob/master/TERMS_AND_CONDITIONS.md (copia locale salvata il 16 ottobre 2026, SHA256 `99c4921dbe023cd68c1a447775707d621453cc78aec6ac0bfe2e6c06a5114ee0`). Uso personale di ricerca non produttiva. Nessuna associazione commerciale con Binance. La licenza del codice del repository non cambia. La licenza MIT del repository `binance-public-data` riguarda quel codice, non il dataset. I dati grezzi e il bundle non sono redistribuiti.

Studio osservativo e descrittivo. **Non** è una strategia, un backtest, una valutazione economica o un'autorizzazione operativa. Un risultato nullo, contrario o insufficiente è una consegna valida.

## Run e provenienza

| Voce | Valore |
|---|---|
| Convenzioni | `config/OBS-001-v1.json`, id OBS-001/v1, SHA256 canonico `3c4eb884d0b6752bfb31e7d9ae159a1414d75cadc90f9abcc9379d5825002387`, scritte dal task al commit `413c6d076077412b09b85760101658ab07f76dfd` |
| Motore | `obs001` 1.0.1, schema bundle `obs001.bundle/1`. Calcoli identici al run 1.0.0 del commit `09fd3ac`: osservazioni, eventi, esiti e riepiloghi sono uguali sezione per sezione |
| Run | `OBS-001-v1-e1.0.1-40a13e10ac-3c4eb884d0`, commit software `c51ddace4ce72b555fa8587e28b44468744594d7` (checkout pulito), Python 3.12.14, Windows 10 |
| Input | Binance Vision `futures/um/monthly/klines/BTCUSDT/1m`, da giugno a dicembre 2025, 7 ZIP scaricati il 16 ottobre 2026 alle 17:22 UTC. Tutti coincidono col `.CHECKSUM` del fornitore; settembre `c296ba45…30dc` è uguale al valore registrato dal Director. Input hash `40a13e10acaa4b8de14ac9cbaef23aabdfe085c4fe6c260aa718939ef1bc351f` |
| Strumento | `fapi/v1/exchangeInfo` pubblico, letto il 16 ottobre 2026: BTCUSDT, PERPETUAL, base BTC, quote e margine USDT, stato TRADING. Sono metadati correnti: non certificano condizioni storiche |
| Bundle | 27,4 MB, SHA256 `71b18a2f5801c1582469ef80497f63fe314385cb08e2839076f5563687cf02a8`. Conservato in locale, fuori Git |
| Tempi | controllo input 2,6 s, catena osservazioni ed esiti 1,1 s, totale 4,3 s. Acquisizione 19,5 s |

**Qualità dell'input:**
- 308.160 minuti attesi, 308.160 validi: 132.480 di inizializzazione e 175.680 di studio.
- Nessun minuto mancante o invalido, nessun duplicato, nessuna riga fuori ordine, fuori mese o corrotta.
- Ogni file ha l'intestazione riconosciuta per nome; tempi in millisecondi, `close_time = open_time + 59.999`.
- Barre: 6.848 da 45m e 214 da 1D, tutte complete.

**Controlli di popolazione:**
- 3.904 origini, nessuna eliminata.
- 31 censurate a destra (31 dicembre, dalle 00:45 alle 23:15), coerente con il controllo teorico.
- Nessuna lacuna, quindi 3.873 origini con le tre misure disponibili.
- Partizioni riconciliate: s45, matrice s45×s1d, relazioni e mesi.

**Riscontro indipendente.** Uno script separato ricalcola dalle colonne delle barre del bundle:
- A, SMA20, SMA50, distanza e volume relativo su 592 record campione;
- tutti i pivot confermati;
- 300 esiti.

Zero differenze. Massimi e minimi dei minuti futuri coincidono con quelli delle 32 barre 45m per ogni origine completa (asserzione del motore).

## Lettura dei risultati

Unità: A45m all'origine. `final` è firmato nel verso del prezzo, anche per s45 DOWN. `up` e `down` sono ampiezze non negative, non profitti o perdite. Il confronto principale è **entro lo stesso verso s45**, fra le relazioni con la struttura 1D.

1. **La struttura 1D era sempre disponibile.** Lo stato «1D non disponibile» è vuoto in tutti i mesi, per entrambi i versi. La struttura 45m non è mai risultata indisponibile. Il gruppo più numeroso è s45 MIXED: 1.728 origini su 3.904.

2. **s45 UP.** Le mediane di `final` sul totale sono vicine a zero e la dispersione è ampia: P25 e P75 cadono fra circa −2 e +2,6 in ogni relazione.

   | Relazione 1D | Mediana | P25 / P75 |
   |---|---:|---:|
   | Concorde | −0,17 | −2,07 / +1,46 |
   | Contraria | +0,44 | −1,90 / +2,60 |
   | Mista | +0,04 | −2,39 / +2,33 |

   I mesi non concordano. Per il concorde:

   | Mese | n | Mediana di `final` |
   |---|---:|---:|
   | Settembre | 94 | −0,72 |
   | Ottobre | 12 | +0,26 |
   | Novembre | 6 | +1,25 |
   | Dicembre | 147 | +0,02 |

   Contraria: positiva in settembre, ottobre e dicembre (+0,77, +1,79, +0,91), negativa in novembre (−0,19, n=148). Mista: −1,90 in novembre, positiva negli altri mesi.

   `up` e `down` mediani stanno fra circa 2,1 e 2,6 A in tutti i gruppi. Il gruppo concorde ha la coda superiore di `up` più lunga (P90 10,2 contro 6,9 e 6,5). Le escursioni sono grandi rispetto agli spostamenti finali tipici.

3. **s45 DOWN.**

   | Relazione 1D | Mediana | P25 / P75 |
   |---|---:|---:|
   | Concorde | +0,45 | −1,34 / +2,57 |
   | Contraria | −0,41 | −3,81 / +1,22 |
   | Mista | +0,11 | −3,21 / +2,80 |

   Con struttura 45m decrescente e 1D concorde, nel totale il prezzo dopo 24 ore era più spesso salito che sceso: il contrario di un'estrapolazione del verso. I mesi però si contraddicono. Il concorde va da +1,44 in settembre (n=140) a −1,63 in ottobre (n=27), 0,00 in novembre (n=177) e +0,86 in dicembre (n=93). Il contrario ha `down` mediano più ampio (3,46 contro 2,63 e 2,61) e coda di `down` più lunga (P90 9,7).

4. **Celle scarse.**

   | Cella | n |
   |---|---:|
   | UP · concorde, ottobre | 12 |
   | UP · concorde, novembre | 6 |
   | DOWN · contraria, ottobre | 17 |
   | DOWN · contraria, novembre | 12 |
   | UP · mista, settembre | 36 |
   | DOWN · mista, settembre | 34 |

   Dentro un mese queste celle coprono pochi giorni consecutivi. Con finestre 24h sovrapposte, poche decine di origini equivalgono a pochissimi episodi indipendenti. Le loro mediane, anche estreme, non vanno generalizzate.

5. **Sola s45, senza giornaliero.** Le mediane totali di `final` sono UP +0,13, DOWN +0,18 e MIXED −0,04. Le medie mensili cambiano segno da un mese all'altro per tutti e tre gli stati: per esempio UP vale −1,72 in novembre e +0,97 in dicembre.

6. **Esempi.** Le origini sono state scelte con il criterio retrospettivo dichiarato; ognuna è apribile nell'app.

   | Verso | Esempio | Origine | Gruppo | final | up | down |
   |---|---|---|---|---:|---:|---:|
   | UP | prima origine | 2025-09-01 12:45 UTC | 1D contraria | −0,34 | 3,08 | 2,58 |
   | UP | caso più contrario | 2025-11-30 15:45 UTC | 1D contraria | −24,93 | 1,44 | 25,17 |
   | DOWN | prima origine | 2025-09-01 02:15 UTC | 1D concorde | +4,03 | 5,71 | 2,14 |
   | DOWN | caso più contrario | 2025-09-28 14:15 UTC | 1D contraria | +23,21 | 23,35 | 0,00 |

   I casi estremi valgono oltre 20 A in 24 ore e cadono nei gruppi «contrari». Un singolo episodio di questo tipo pesa sulle medie: per questo vanno lette insieme a mediane e quantili.

**In sintesi:**
- Entro lo stesso verso, le differenze di mediana fra le relazioni giornaliere sono piccole rispetto alla dispersione, che spesso supera ±2 A fra P25 e P75.
- Il loro segno cambia da un mese all'altro.
- In questi quattro mesi non emerge un comportamento coerente che distingua concorde, contraria e mista.

Questo non attribuisce né esclude un ruolo della scala 1D. Le differenze possono riflettere altri fattori: regime, volatilità, singoli episodi. I quattro mesi sono già stati esposti a sviluppi precedenti e non sono un campione nuovo. Non ci sono soglie, significatività o classifiche.

## Limiti

- **Righe non indipendenti.** Origini adiacenti hanno finestre 24h quasi coincidenti.
- **Parametri.** Sono iniziali e non ottimizzati: 20/50/4 per le medie, 2+2 per i pivot, 20 TR. Lo studio non li valida.
- **Volume relativo.** Non è corretto per la stagionalità intraday. Non entra nella domanda principale.
- **Disponibilità logica.** Il clock la assume alla chiusura delle barre; non prova una latenza zero dal vivo.
- **Metadati dello strumento.** Sono correnti, non storici.
- **Lacune.** Non ce ne sono in questo input. Il trattamento delle lacune (barre INCOMPLETE, azzeramenti, GAP) è verificato solo sui test sintetici.
- **Interpretazione tecnica dell'esecutore.** Dopo una barra incompleta, anche i livelli «ultimo pivot» della scala ripartono con il segmento, come le sequenze di pivot e ancore. Sui dati reali non ha effetto, perché non ci sono lacune.

Tabelle generate dal motore (`summary.md` del run), con arrotondamento solo in visualizzazione.

### Copertura e disponibilità

| Periodo | Origini | Origine valida | A45m valida | Futuro completo | Censurate a destra | Con lacuna | Misure disponibili | Misure mancanti |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Settembre 2025 | 960 | 960 | 960 | 960 | 0 | 0 | 960 | 0 |
| Ottobre 2025 | 992 | 992 | 992 | 992 | 0 | 0 | 992 | 0 |
| Novembre 2025 | 960 | 960 | 960 | 960 | 0 | 0 | 960 | 0 |
| Dicembre 2025 | 992 | 992 | 992 | 961 | 31 | 0 | 961 | 31 |
| Totale | 3904 | 3904 | 3904 | 3873 | 31 | 0 | 3873 | 31 |

### Matrice dei conteggi s45 × s1d

**Settembre 2025**

| s45 \ s1d | UP | DOWN | MIXED | UNAVAILABLE | Totale |
|---|---:|---:|---:|---:|---:|
| UP | 94 | 105 | 36 | 0 | 235 |
| DOWN | 120 | 140 | 34 | 0 | 294 |
| MIXED | 138 | 203 | 90 | 0 | 431 |
| UNAVAILABLE | 0 | 0 | 0 | 0 | 0 |

**Ottobre 2025**

| s45 \ s1d | UP | DOWN | MIXED | UNAVAILABLE | Totale |
|---|---:|---:|---:|---:|---:|
| UP | 12 | 43 | 265 | 0 | 320 |
| DOWN | 17 | 27 | 194 | 0 | 238 |
| MIXED | 35 | 58 | 341 | 0 | 434 |
| UNAVAILABLE | 0 | 0 | 0 | 0 | 0 |

**Novembre 2025**

| s45 \ s1d | UP | DOWN | MIXED | UNAVAILABLE | Totale |
|---|---:|---:|---:|---:|---:|
| UP | 6 | 148 | 94 | 0 | 248 |
| DOWN | 12 | 177 | 102 | 0 | 291 |
| MIXED | 14 | 219 | 188 | 0 | 421 |
| UNAVAILABLE | 0 | 0 | 0 | 0 | 0 |

**Dicembre 2025**

| s45 \ s1d | UP | DOWN | MIXED | UNAVAILABLE | Totale |
|---|---:|---:|---:|---:|---:|
| UP | 147 | 63 | 86 | 0 | 296 |
| DOWN | 87 | 93 | 74 | 0 | 254 |
| MIXED | 214 | 100 | 128 | 0 | 442 |
| UNAVAILABLE | 0 | 0 | 0 | 0 | 0 |

**Totale**

| s45 \ s1d | UP | DOWN | MIXED | UNAVAILABLE | Totale |
|---|---:|---:|---:|---:|---:|
| UP | 259 | 359 | 481 | 0 | 1099 |
| DOWN | 236 | 437 | 404 | 0 | 1077 |
| MIXED | 401 | 580 | 747 | 0 | 1728 |
| UNAVAILABLE | 0 | 0 | 0 | 0 | 0 |

### Sola struttura 45m (unità: A45m all'origine)

**Settembre 2025**

| s45 | Origini | Origine valida | A valida | Futuro completo | Misure disponibili | Mancanti |
|---|---:|---:|---:|---:|---:|---:|
| UP | 235 | 235 | 235 | 235 | 235 | 0 |
| DOWN | 294 | 294 | 294 | 294 | 294 | 0 |
| MIXED | 431 | 431 | 431 | 431 | 431 | 0 |
| UNAVAILABLE | 0 | 0 | 0 | 0 | 0 | 0 |

| Gruppo | Misura | n | Media | Min | P10 | P25 | Mediana | P75 | P90 | Max |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| UP | final | 235 | -0,155 | -22,465 | -4,894 | -2,285 | -0,024 | 1,902 | 3,723 | 17,842 |
| UP | up | 235 | 3,257 | 0,000 | 0,467 | 0,924 | 2,247 | 4,569 | 7,162 | 19,617 |
| UP | down | 235 | 3,362 | 0,000 | 0,634 | 1,231 | 2,639 | 4,137 | 6,069 | 28,169 |
| DOWN | final | 294 | 0,859 | -21,208 | -3,900 | -1,227 | 0,340 | 3,207 | 5,806 | 23,209 |
| DOWN | up | 294 | 3,865 | 0,003 | 0,483 | 1,159 | 2,509 | 5,706 | 7,493 | 23,348 |
| DOWN | down | 294 | 3,271 | 0,000 | 0,341 | 0,867 | 2,299 | 3,904 | 5,774 | 28,760 |
| MIXED | final | 431 | 0,880 | -22,993 | -3,956 | -1,054 | 0,995 | 3,271 | 6,486 | 18,021 |
| MIXED | up | 431 | 3,889 | 0,000 | 0,675 | 1,348 | 2,978 | 5,172 | 7,682 | 20,035 |
| MIXED | down | 431 | 3,401 | 0,000 | 0,502 | 1,047 | 2,116 | 3,951 | 6,091 | 32,221 |
| UNAVAILABLE | final | 0 | — | — | — | — | — | — | — | — |
| UNAVAILABLE | up | 0 | — | — | — | — | — | — | — | — |
| UNAVAILABLE | down | 0 | — | — | — | — | — | — | — | — |

**Ottobre 2025**

| s45 | Origini | Origine valida | A valida | Futuro completo | Misure disponibili | Mancanti |
|---|---:|---:|---:|---:|---:|---:|
| UP | 320 | 320 | 320 | 320 | 320 | 0 |
| DOWN | 238 | 238 | 238 | 238 | 238 | 0 |
| MIXED | 434 | 434 | 434 | 434 | 434 | 0 |
| UNAVAILABLE | 0 | 0 | 0 | 0 | 0 | 0 |

| Gruppo | Misura | n | Media | Min | P10 | P25 | Mediana | P75 | P90 | Max |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| UP | final | 320 | 0,304 | -22,116 | -4,823 | -2,046 | 0,534 | 3,024 | 5,418 | 17,552 |
| UP | up | 320 | 3,149 | 0,010 | 0,329 | 0,827 | 2,081 | 4,702 | 6,799 | 17,879 |
| UP | down | 320 | 3,637 | 0,000 | 0,396 | 1,027 | 1,955 | 3,678 | 7,325 | 47,371 |
| DOWN | final | 238 | -0,400 | -22,469 | -4,876 | -3,092 | -0,507 | 1,952 | 5,370 | 11,987 |
| DOWN | up | 238 | 3,731 | 0,000 | 0,639 | 1,305 | 3,123 | 4,870 | 8,479 | 16,646 |
| DOWN | down | 238 | 4,112 | 0,000 | 0,397 | 1,250 | 3,364 | 5,346 | 7,554 | 45,882 |
| MIXED | final | 434 | 0,430 | -22,709 | -5,158 | -1,997 | 0,579 | 3,123 | 5,166 | 20,056 |
| MIXED | up | 434 | 4,315 | 0,000 | 0,499 | 1,252 | 2,887 | 6,055 | 10,294 | 22,694 |
| MIXED | down | 434 | 3,803 | 0,000 | 0,281 | 0,730 | 1,892 | 4,499 | 6,894 | 46,619 |
| UNAVAILABLE | final | 0 | — | — | — | — | — | — | — | — |
| UNAVAILABLE | up | 0 | — | — | — | — | — | — | — | — |
| UNAVAILABLE | down | 0 | — | — | — | — | — | — | — | — |

**Novembre 2025**

| s45 | Origini | Origine valida | A valida | Futuro completo | Misure disponibili | Mancanti |
|---|---:|---:|---:|---:|---:|---:|
| UP | 248 | 248 | 248 | 248 | 248 | 0 |
| DOWN | 291 | 291 | 291 | 291 | 291 | 0 |
| MIXED | 421 | 421 | 421 | 421 | 421 | 0 |
| UNAVAILABLE | 0 | 0 | 0 | 0 | 0 | 0 |

| Gruppo | Misura | n | Media | Min | P10 | P25 | Mediana | P75 | P90 | Max |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| UP | final | 248 | -1,723 | -24,927 | -8,380 | -3,517 | -0,684 | 1,530 | 3,304 | 10,973 |
| UP | up | 248 | 2,568 | 0,028 | 0,460 | 0,882 | 2,020 | 3,793 | 5,623 | 12,393 |
| UP | down | 248 | 4,627 | 0,015 | 0,633 | 1,276 | 2,791 | 5,627 | 10,383 | 25,873 |
| DOWN | final | 291 | -0,522 | -18,193 | -5,374 | -2,315 | -0,060 | 1,320 | 3,987 | 12,217 |
| DOWN | up | 291 | 2,618 | 0,000 | 0,293 | 0,882 | 1,925 | 3,573 | 5,245 | 13,251 |
| DOWN | down | 291 | 3,726 | 0,020 | 0,486 | 1,238 | 2,584 | 5,255 | 7,483 | 23,407 |
| MIXED | final | 421 | -1,857 | -20,642 | -7,946 | -3,950 | -1,199 | 0,686 | 2,978 | 13,035 |
| MIXED | up | 421 | 2,581 | 0,000 | 0,339 | 0,771 | 2,252 | 3,659 | 4,805 | 14,655 |
| MIXED | down | 421 | 4,509 | 0,022 | 0,842 | 1,658 | 3,371 | 5,683 | 9,325 | 23,690 |
| UNAVAILABLE | final | 0 | — | — | — | — | — | — | — | — |
| UNAVAILABLE | up | 0 | — | — | — | — | — | — | — | — |
| UNAVAILABLE | down | 0 | — | — | — | — | — | — | — | — |

**Dicembre 2025**

| s45 | Origini | Origine valida | A valida | Futuro completo | Misure disponibili | Mancanti |
|---|---:|---:|---:|---:|---:|---:|
| UP | 296 | 296 | 296 | 283 | 283 | 13 |
| DOWN | 254 | 254 | 254 | 249 | 249 | 5 |
| MIXED | 442 | 442 | 442 | 429 | 429 | 13 |
| UNAVAILABLE | 0 | 0 | 0 | 0 | 0 | 0 |

| Gruppo | Misura | n | Media | Min | P10 | P25 | Mediana | P75 | P90 | Max |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| UP | final | 283 | 0,970 | -9,171 | -3,136 | -1,308 | 0,377 | 2,709 | 6,366 | 15,900 |
| UP | up | 283 | 4,419 | 0,000 | 0,671 | 1,582 | 3,434 | 6,346 | 8,485 | 17,590 |
| UP | down | 283 | 2,967 | 0,000 | 0,557 | 1,255 | 2,149 | 4,085 | 6,623 | 12,054 |
| DOWN | final | 249 | 0,059 | -10,757 | -5,366 | -2,834 | 0,352 | 2,491 | 5,396 | 10,724 |
| DOWN | up | 249 | 3,585 | 0,000 | 0,464 | 1,080 | 2,806 | 4,508 | 9,074 | 11,463 |
| DOWN | down | 249 | 3,788 | 0,024 | 0,506 | 1,131 | 3,148 | 5,987 | 7,837 | 17,178 |
| MIXED | final | 429 | -0,331 | -8,918 | -4,704 | -2,722 | -0,384 | 1,383 | 3,900 | 11,659 |
| MIXED | up | 429 | 3,614 | 0,000 | 0,425 | 0,986 | 2,558 | 4,744 | 8,581 | 16,946 |
| MIXED | down | 429 | 3,483 | 0,000 | 0,443 | 1,126 | 2,846 | 4,660 | 7,397 | 15,055 |
| UNAVAILABLE | final | 0 | — | — | — | — | — | — | — | — |
| UNAVAILABLE | up | 0 | — | — | — | — | — | — | — | — |
| UNAVAILABLE | down | 0 | — | — | — | — | — | — | — | — |

**Totale**

| s45 | Origini | Origine valida | A valida | Futuro completo | Misure disponibili | Mancanti |
|---|---:|---:|---:|---:|---:|---:|
| UP | 1099 | 1099 | 1099 | 1086 | 1086 | 13 |
| DOWN | 1077 | 1077 | 1077 | 1072 | 1072 | 5 |
| MIXED | 1728 | 1728 | 1728 | 1715 | 1715 | 13 |
| UNAVAILABLE | 0 | 0 | 0 | 0 | 0 | 0 |

| Gruppo | Misura | n | Media | Min | P10 | P25 | Mediana | P75 | P90 | Max |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| UP | final | 1086 | -0,085 | -24,927 | -4,831 | -2,155 | 0,130 | 2,379 | 4,845 | 17,842 |
| UP | up | 1086 | 3,370 | 0,000 | 0,465 | 0,965 | 2,297 | 4,883 | 7,165 | 19,617 |
| UP | down | 1086 | 3,629 | 0,000 | 0,550 | 1,188 | 2,299 | 4,410 | 7,406 | 47,371 |
| DOWN | final | 1072 | 0,019 | -22,469 | -5,200 | -2,235 | 0,183 | 2,341 | 5,450 | 23,209 |
| DOWN | up | 1072 | 3,432 | 0,000 | 0,433 | 1,092 | 2,518 | 4,490 | 7,831 | 23,348 |
| DOWN | down | 1072 | 3,701 | 0,000 | 0,411 | 1,112 | 2,678 | 5,025 | 7,511 | 45,882 |
| MIXED | final | 1715 | -0,208 | -22,993 | -5,511 | -2,495 | -0,040 | 2,454 | 4,695 | 20,056 |
| MIXED | up | 1715 | 3,607 | 0,000 | 0,464 | 1,110 | 2,617 | 4,709 | 8,042 | 22,694 |
| MIXED | down | 1715 | 3,795 | 0,000 | 0,464 | 1,130 | 2,525 | 4,828 | 7,434 | 46,619 |
| UNAVAILABLE | final | 0 | — | — | — | — | — | — | — | — |
| UNAVAILABLE | up | 0 | — | — | — | — | — | — | — | — |
| UNAVAILABLE | down | 0 | — | — | — | — | — | — | — | — |

### Struttura 45m UP e DOWN per relazione con la struttura 1D

Confronto entro lo stesso verso s45, mai fra versi diversi. final è firmato nel verso del prezzo anche per DOWN; up/down sono ampiezze non negative, non profitti o perdite.

**Settembre 2025**

| s45 | Relazione 1D | Origini | Origine valida | A valida | Futuro completo | Misure disponibili | Mancanti | Flag mancanti |
|---|---|---:|---:|---:|---:|---:|---:|---|
| UP | CONCORDANT | 94 | 94 | 94 | 94 | 94 | 0 | — |
| UP | OPPOSITE | 105 | 105 | 105 | 105 | 105 | 0 | — |
| UP | MIXED | 36 | 36 | 36 | 36 | 36 | 0 | — |
| UP | UNAVAILABLE | 0 | 0 | 0 | 0 | 0 | 0 | — |
| DOWN | CONCORDANT | 140 | 140 | 140 | 140 | 140 | 0 | — |
| DOWN | OPPOSITE | 120 | 120 | 120 | 120 | 120 | 0 | — |
| DOWN | MIXED | 34 | 34 | 34 | 34 | 34 | 0 | — |
| DOWN | UNAVAILABLE | 0 | 0 | 0 | 0 | 0 | 0 | — |

| Gruppo | Misura | n | Media | Min | P10 | P25 | Mediana | P75 | P90 | Max |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| UP · CONCORDANT | final | 94 | -1,221 | -22,465 | -10,082 | -4,262 | -0,724 | 0,390 | 1,930 | 17,842 |
| UP · CONCORDANT | up | 94 | 2,782 | 0,000 | 0,339 | 0,601 | 1,306 | 2,301 | 4,234 | 19,617 |
| UP · CONCORDANT | down | 94 | 4,316 | 0,227 | 0,560 | 1,191 | 2,721 | 5,461 | 11,678 | 28,169 |
| UP · OPPOSITE | final | 105 | 0,349 | -5,620 | -3,887 | -2,314 | 0,765 | 2,664 | 4,041 | 6,252 |
| UP · OPPOSITE | up | 105 | 3,715 | 0,021 | 0,573 | 1,766 | 3,103 | 5,712 | 7,248 | 8,481 |
| UP · OPPOSITE | down | 105 | 2,547 | 0,000 | 0,634 | 1,161 | 2,091 | 3,657 | 5,254 | 7,800 |
| UP · MIXED | final | 36 | 1,159 | -2,149 | -1,361 | -0,647 | 0,511 | 2,684 | 3,390 | 8,834 |
| UP · MIXED | up | 36 | 3,159 | 0,316 | 0,929 | 1,686 | 2,456 | 3,996 | 5,668 | 9,445 |
| UP · MIXED | down | 36 | 3,245 | 0,158 | 2,175 | 2,857 | 3,234 | 3,930 | 4,339 | 6,092 |
| UP · UNAVAILABLE | final | 0 | — | — | — | — | — | — | — | — |
| UP · UNAVAILABLE | up | 0 | — | — | — | — | — | — | — | — |
| UP · UNAVAILABLE | down | 0 | — | — | — | — | — | — | — | — |
| DOWN · CONCORDANT | final | 140 | 1,782 | -3,315 | -1,621 | -0,592 | 1,438 | 4,123 | 5,705 | 7,580 |
| DOWN · CONCORDANT | up | 140 | 4,209 | 0,018 | 1,073 | 2,169 | 4,270 | 6,248 | 7,213 | 9,278 |
| DOWN · CONCORDANT | down | 140 | 2,346 | 0,073 | 0,336 | 0,986 | 2,299 | 3,413 | 4,492 | 6,313 |
| DOWN · OPPOSITE | final | 120 | -0,986 | -21,208 | -8,480 | -3,854 | -0,716 | 0,457 | 5,586 | 23,209 |
| DOWN · OPPOSITE | up | 120 | 3,058 | 0,003 | 0,288 | 0,644 | 1,370 | 2,147 | 6,817 | 23,348 |
| DOWN · OPPOSITE | down | 120 | 4,909 | 0,001 | 0,527 | 1,202 | 2,643 | 5,361 | 11,264 | 28,760 |
| DOWN · MIXED | final | 34 | 3,571 | -3,168 | -0,084 | 1,582 | 2,867 | 5,242 | 8,351 | 12,638 |
| DOWN · MIXED | up | 34 | 5,291 | 1,882 | 2,520 | 3,017 | 3,904 | 6,347 | 10,569 | 13,357 |
| DOWN · MIXED | down | 34 | 1,298 | 0,000 | 0,185 | 0,492 | 0,797 | 2,067 | 2,904 | 4,743 |
| DOWN · UNAVAILABLE | final | 0 | — | — | — | — | — | — | — | — |
| DOWN · UNAVAILABLE | up | 0 | — | — | — | — | — | — | — | — |
| DOWN · UNAVAILABLE | down | 0 | — | — | — | — | — | — | — | — |

**Ottobre 2025**

| s45 | Relazione 1D | Origini | Origine valida | A valida | Futuro completo | Misure disponibili | Mancanti | Flag mancanti |
|---|---|---:|---:|---:|---:|---:|---:|---|
| UP | CONCORDANT | 12 | 12 | 12 | 12 | 12 | 0 | — |
| UP | OPPOSITE | 43 | 43 | 43 | 43 | 43 | 0 | — |
| UP | MIXED | 265 | 265 | 265 | 265 | 265 | 0 | — |
| UP | UNAVAILABLE | 0 | 0 | 0 | 0 | 0 | 0 | — |
| DOWN | CONCORDANT | 27 | 27 | 27 | 27 | 27 | 0 | — |
| DOWN | OPPOSITE | 17 | 17 | 17 | 17 | 17 | 0 | — |
| DOWN | MIXED | 194 | 194 | 194 | 194 | 194 | 0 | — |
| DOWN | UNAVAILABLE | 0 | 0 | 0 | 0 | 0 | 0 | — |

| Gruppo | Misura | n | Media | Min | P10 | P25 | Mediana | P75 | P90 | Max |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| UP · CONCORDANT | final | 12 | 0,261 | -1,116 | -0,415 | -0,044 | 0,258 | 0,652 | 0,969 | 1,387 |
| UP · CONCORDANT | up | 12 | 2,015 | 0,619 | 1,350 | 1,787 | 2,050 | 2,356 | 2,640 | 3,027 |
| UP · CONCORDANT | down | 12 | 1,798 | 0,842 | 1,243 | 1,478 | 1,814 | 1,987 | 2,640 | 2,758 |
| UP · OPPOSITE | final | 43 | 1,792 | -2,605 | -0,445 | 0,339 | 1,790 | 3,155 | 4,822 | 5,944 |
| UP · OPPOSITE | up | 43 | 3,269 | 0,092 | 0,702 | 1,191 | 2,914 | 4,772 | 6,613 | 8,602 |
| UP · OPPOSITE | down | 43 | 2,209 | 0,063 | 0,377 | 1,103 | 2,033 | 2,996 | 3,630 | 6,182 |
| UP · MIXED | final | 265 | 0,065 | -22,116 | -5,264 | -2,468 | 0,255 | 3,176 | 5,559 | 17,552 |
| UP · MIXED | up | 265 | 3,181 | 0,010 | 0,296 | 0,771 | 1,941 | 4,747 | 6,904 | 17,879 |
| UP · MIXED | down | 265 | 3,952 | 0,000 | 0,387 | 1,015 | 1,962 | 4,564 | 7,743 | 47,371 |
| UP · UNAVAILABLE | final | 0 | — | — | — | — | — | — | — | — |
| UP · UNAVAILABLE | up | 0 | — | — | — | — | — | — | — | — |
| UP · UNAVAILABLE | down | 0 | — | — | — | — | — | — | — | — |
| DOWN · CONCORDANT | final | 27 | -0,341 | -10,114 | -8,660 | -5,637 | -1,626 | 5,249 | 6,740 | 11,739 |
| DOWN · CONCORDANT | up | 27 | 3,511 | 0,163 | 0,556 | 0,726 | 1,458 | 6,948 | 8,223 | 12,008 |
| DOWN · CONCORDANT | down | 27 | 5,201 | 0,064 | 1,022 | 2,594 | 4,663 | 7,605 | 10,988 | 11,754 |
| DOWN · OPPOSITE | final | 17 | -0,528 | -2,499 | -2,142 | -1,816 | -0,640 | 0,767 | 1,305 | 1,720 |
| DOWN · OPPOSITE | up | 17 | 1,534 | 0,112 | 0,474 | 1,053 | 1,304 | 1,950 | 3,115 | 3,343 |
| DOWN · OPPOSITE | down | 17 | 3,199 | 0,186 | 0,273 | 0,322 | 4,312 | 4,928 | 5,230 | 5,599 |
| DOWN · MIXED | final | 194 | -0,397 | -22,469 | -4,697 | -3,122 | -0,433 | 2,099 | 5,120 | 11,987 |
| DOWN · MIXED | up | 194 | 3,954 | 0,000 | 0,864 | 1,551 | 3,512 | 4,915 | 8,912 | 16,646 |
| DOWN · MIXED | down | 194 | 4,040 | 0,000 | 0,435 | 1,188 | 3,108 | 5,311 | 7,297 | 45,882 |
| DOWN · UNAVAILABLE | final | 0 | — | — | — | — | — | — | — | — |
| DOWN · UNAVAILABLE | up | 0 | — | — | — | — | — | — | — | — |
| DOWN · UNAVAILABLE | down | 0 | — | — | — | — | — | — | — | — |

**Novembre 2025**

| s45 | Relazione 1D | Origini | Origine valida | A valida | Futuro completo | Misure disponibili | Mancanti | Flag mancanti |
|---|---|---:|---:|---:|---:|---:|---:|---|
| UP | CONCORDANT | 6 | 6 | 6 | 6 | 6 | 0 | — |
| UP | OPPOSITE | 148 | 148 | 148 | 148 | 148 | 0 | — |
| UP | MIXED | 94 | 94 | 94 | 94 | 94 | 0 | — |
| UP | UNAVAILABLE | 0 | 0 | 0 | 0 | 0 | 0 | — |
| DOWN | CONCORDANT | 177 | 177 | 177 | 177 | 177 | 0 | — |
| DOWN | OPPOSITE | 12 | 12 | 12 | 12 | 12 | 0 | — |
| DOWN | MIXED | 102 | 102 | 102 | 102 | 102 | 0 | — |
| DOWN | UNAVAILABLE | 0 | 0 | 0 | 0 | 0 | 0 | — |

| Gruppo | Misura | n | Media | Min | P10 | P25 | Mediana | P75 | P90 | Max |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| UP · CONCORDANT | final | 6 | 1,159 | 0,634 | 0,637 | 0,738 | 1,247 | 1,487 | 1,593 | 1,692 |
| UP · CONCORDANT | up | 6 | 1,828 | 1,248 | 1,289 | 1,411 | 1,800 | 1,977 | 2,395 | 2,803 |
| UP · CONCORDANT | down | 6 | 0,904 | 0,508 | 0,634 | 0,769 | 0,877 | 1,030 | 1,201 | 1,348 |
| UP · OPPOSITE | final | 148 | -1,433 | -24,927 | -6,391 | -2,735 | -0,189 | 2,088 | 4,347 | 7,542 |
| UP · OPPOSITE | up | 148 | 2,498 | 0,028 | 0,364 | 0,753 | 1,835 | 3,927 | 5,684 | 8,303 |
| UP · OPPOSITE | down | 148 | 4,513 | 0,015 | 0,587 | 1,063 | 2,607 | 5,363 | 9,419 | 25,873 |
| UP · MIXED | final | 94 | -2,364 | -12,190 | -10,032 | -4,071 | -1,901 | 0,454 | 2,255 | 10,973 |
| UP · MIXED | up | 94 | 2,725 | 0,038 | 0,562 | 1,010 | 2,069 | 3,632 | 5,473 | 12,393 |
| UP · MIXED | down | 94 | 5,046 | 0,346 | 1,061 | 1,985 | 4,062 | 7,579 | 11,844 | 14,521 |
| UP · UNAVAILABLE | final | 0 | — | — | — | — | — | — | — | — |
| UP · UNAVAILABLE | up | 0 | — | — | — | — | — | — | — | — |
| UP · UNAVAILABLE | down | 0 | — | — | — | — | — | — | — | — |
| DOWN · CONCORDANT | final | 177 | -0,732 | -18,193 | -3,816 | -2,058 | 0,003 | 0,948 | 2,907 | 8,641 |
| DOWN · CONCORDANT | up | 177 | 2,238 | 0,000 | 0,275 | 0,897 | 1,773 | 3,098 | 4,252 | 11,056 |
| DOWN · CONCORDANT | down | 177 | 3,700 | 0,020 | 0,590 | 1,299 | 2,584 | 4,585 | 6,846 | 23,407 |
| DOWN · OPPOSITE | final | 12 | 1,007 | -0,424 | -0,335 | 0,143 | 0,642 | 1,756 | 2,396 | 3,359 |
| DOWN · OPPOSITE | up | 12 | 3,165 | 0,877 | 1,302 | 2,548 | 3,536 | 3,905 | 4,358 | 5,021 |
| DOWN · OPPOSITE | down | 12 | 0,947 | 0,056 | 0,205 | 0,264 | 0,873 | 1,514 | 1,665 | 2,094 |
| DOWN · MIXED | final | 102 | -0,337 | -9,458 | -6,966 | -4,781 | -0,687 | 3,350 | 6,068 | 12,217 |
| DOWN · MIXED | up | 102 | 3,212 | 0,000 | 0,353 | 0,844 | 2,096 | 4,393 | 7,792 | 13,251 |
| DOWN · MIXED | down | 102 | 4,098 | 0,072 | 0,472 | 1,316 | 3,622 | 6,037 | 8,952 | 12,721 |
| DOWN · UNAVAILABLE | final | 0 | — | — | — | — | — | — | — | — |
| DOWN · UNAVAILABLE | up | 0 | — | — | — | — | — | — | — | — |
| DOWN · UNAVAILABLE | down | 0 | — | — | — | — | — | — | — | — |

**Dicembre 2025**

| s45 | Relazione 1D | Origini | Origine valida | A valida | Futuro completo | Misure disponibili | Mancanti | Flag mancanti |
|---|---|---:|---:|---:|---:|---:|---:|---|
| UP | CONCORDANT | 147 | 147 | 147 | 147 | 147 | 0 | — |
| UP | OPPOSITE | 63 | 63 | 63 | 63 | 63 | 0 | — |
| UP | MIXED | 86 | 86 | 86 | 73 | 73 | 13 | RIGHT_CENSORED 13 |
| UP | UNAVAILABLE | 0 | 0 | 0 | 0 | 0 | 0 | — |
| DOWN | CONCORDANT | 93 | 93 | 93 | 93 | 93 | 0 | — |
| DOWN | OPPOSITE | 87 | 87 | 87 | 87 | 87 | 0 | — |
| DOWN | MIXED | 74 | 74 | 74 | 69 | 69 | 5 | RIGHT_CENSORED 5 |
| DOWN | UNAVAILABLE | 0 | 0 | 0 | 0 | 0 | 0 | — |

| Gruppo | Misura | n | Media | Min | P10 | P25 | Mediana | P75 | P90 | Max |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| UP · CONCORDANT | final | 147 | 0,967 | -9,171 | -3,265 | -1,872 | 0,024 | 3,419 | 6,754 | 15,900 |
| UP · CONCORDANT | up | 147 | 5,079 | 0,000 | 0,646 | 1,460 | 3,926 | 7,454 | 14,453 | 17,590 |
| UP · CONCORDANT | down | 147 | 3,210 | 0,196 | 0,946 | 1,375 | 2,155 | 3,958 | 7,238 | 12,054 |
| UP · OPPOSITE | final | 63 | 1,687 | -6,184 | -4,329 | -0,285 | 0,911 | 3,602 | 7,295 | 11,365 |
| UP · OPPOSITE | up | 63 | 3,895 | 0,000 | 0,695 | 1,376 | 2,895 | 6,274 | 8,251 | 13,312 |
| UP · OPPOSITE | down | 63 | 2,238 | 0,000 | 0,385 | 0,762 | 1,800 | 2,611 | 5,918 | 6,757 |
| UP · MIXED | final | 73 | 0,356 | -4,118 | -1,980 | -1,223 | 0,413 | 1,758 | 2,686 | 4,053 |
| UP · MIXED | up | 73 | 3,542 | 0,189 | 0,846 | 1,903 | 3,952 | 5,085 | 6,029 | 7,917 |
| UP · MIXED | down | 73 | 3,107 | 0,043 | 0,342 | 1,478 | 2,755 | 4,542 | 6,608 | 7,983 |
| UP · UNAVAILABLE | final | 0 | — | — | — | — | — | — | — | — |
| UP · UNAVAILABLE | up | 0 | — | — | — | — | — | — | — | — |
| UP · UNAVAILABLE | down | 0 | — | — | — | — | — | — | — | — |
| DOWN · CONCORDANT | final | 93 | 1,382 | -10,723 | -1,709 | -0,923 | 0,864 | 2,149 | 6,894 | 10,313 |
| DOWN · CONCORDANT | up | 93 | 3,803 | 0,072 | 0,523 | 1,567 | 2,515 | 4,611 | 9,708 | 10,721 |
| DOWN · CONCORDANT | down | 93 | 2,770 | 0,024 | 0,508 | 1,297 | 2,746 | 3,547 | 4,502 | 17,178 |
| DOWN · OPPOSITE | final | 87 | -0,910 | -10,757 | -7,008 | -5,079 | -0,388 | 2,815 | 5,267 | 10,724 |
| DOWN · OPPOSITE | up | 87 | 4,055 | 0,035 | 0,657 | 1,651 | 3,491 | 5,535 | 8,601 | 11,463 |
| DOWN · OPPOSITE | down | 87 | 5,166 | 0,241 | 0,859 | 1,270 | 5,678 | 7,452 | 8,978 | 14,317 |
| DOWN · MIXED | final | 69 | -0,503 | -6,858 | -4,928 | -4,123 | 0,112 | 1,862 | 3,083 | 6,766 |
| DOWN · MIXED | up | 69 | 2,699 | 0,000 | 0,309 | 0,632 | 1,610 | 3,996 | 4,792 | 10,444 |
| DOWN · MIXED | down | 69 | 3,422 | 0,033 | 0,381 | 0,755 | 2,061 | 6,359 | 7,616 | 8,917 |
| DOWN · UNAVAILABLE | final | 0 | — | — | — | — | — | — | — | — |
| DOWN · UNAVAILABLE | up | 0 | — | — | — | — | — | — | — | — |
| DOWN · UNAVAILABLE | down | 0 | — | — | — | — | — | — | — | — |

**Totale**

| s45 | Relazione 1D | Origini | Origine valida | A valida | Futuro completo | Misure disponibili | Mancanti | Flag mancanti |
|---|---|---:|---:|---:|---:|---:|---:|---|
| UP | CONCORDANT | 259 | 259 | 259 | 259 | 259 | 0 | — |
| UP | OPPOSITE | 359 | 359 | 359 | 359 | 359 | 0 | — |
| UP | MIXED | 481 | 481 | 481 | 468 | 468 | 13 | RIGHT_CENSORED 13 |
| UP | UNAVAILABLE | 0 | 0 | 0 | 0 | 0 | 0 | — |
| DOWN | CONCORDANT | 437 | 437 | 437 | 437 | 437 | 0 | — |
| DOWN | OPPOSITE | 236 | 236 | 236 | 236 | 236 | 0 | — |
| DOWN | MIXED | 404 | 404 | 404 | 399 | 399 | 5 | RIGHT_CENSORED 5 |
| DOWN | UNAVAILABLE | 0 | 0 | 0 | 0 | 0 | 0 | — |

| Gruppo | Misura | n | Media | Min | P10 | P25 | Mediana | P75 | P90 | Max |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| UP · CONCORDANT | final | 259 | 0,145 | -22,465 | -5,532 | -2,073 | -0,172 | 1,461 | 6,353 | 17,842 |
| UP · CONCORDANT | up | 259 | 4,028 | 0,000 | 0,508 | 0,920 | 2,084 | 5,107 | 10,166 | 19,617 |
| UP · CONCORDANT | down | 259 | 3,493 | 0,196 | 0,775 | 1,284 | 2,081 | 4,140 | 7,310 | 28,169 |
| UP · OPPOSITE | final | 359 | 0,022 | -24,927 | -4,388 | -1,903 | 0,437 | 2,596 | 5,047 | 11,365 |
| UP · OPPOSITE | up | 359 | 3,191 | 0,000 | 0,473 | 1,025 | 2,576 | 5,036 | 6,934 | 13,312 |
| UP · OPPOSITE | down | 359 | 3,263 | 0,000 | 0,511 | 1,048 | 2,074 | 3,877 | 6,161 | 25,873 |
| UP · MIXED | final | 468 | -0,293 | -22,116 | -5,097 | -2,388 | 0,042 | 2,330 | 4,715 | 17,552 |
| UP · MIXED | up | 468 | 3,144 | 0,010 | 0,452 | 0,948 | 2,209 | 4,711 | 6,512 | 17,879 |
| UP · MIXED | down | 468 | 3,986 | 0,000 | 0,489 | 1,263 | 2,619 | 4,925 | 8,005 | 47,371 |
| UP · UNAVAILABLE | final | 0 | — | — | — | — | — | — | — | — |
| UP · UNAVAILABLE | up | 0 | — | — | — | — | — | — | — | — |
| UP · UNAVAILABLE | down | 0 | — | — | — | — | — | — | — | — |
| DOWN · CONCORDANT | final | 437 | 0,548 | -18,193 | -2,652 | -1,337 | 0,452 | 2,573 | 5,499 | 11,739 |
| DOWN · CONCORDANT | up | 437 | 3,281 | 0,000 | 0,435 | 1,144 | 2,494 | 4,567 | 7,316 | 12,008 |
| DOWN · CONCORDANT | down | 437 | 3,161 | 0,020 | 0,483 | 1,228 | 2,632 | 3,921 | 5,841 | 23,407 |
| DOWN · OPPOSITE | final | 236 | -0,824 | -21,208 | -7,410 | -3,813 | -0,406 | 1,225 | 4,762 | 23,209 |
| DOWN · OPPOSITE | up | 236 | 3,321 | 0,003 | 0,373 | 0,840 | 1,817 | 3,617 | 8,094 | 23,348 |
| DOWN · OPPOSITE | down | 236 | 4,679 | 0,001 | 0,465 | 1,200 | 3,463 | 6,164 | 9,736 | 28,760 |
| DOWN · MIXED | final | 399 | -0,062 | -22,469 | -5,323 | -3,206 | 0,112 | 2,801 | 5,486 | 12,638 |
| DOWN · MIXED | up | 399 | 3,661 | 0,000 | 0,498 | 1,203 | 2,957 | 4,721 | 8,440 | 16,646 |
| DOWN · MIXED | down | 399 | 3,714 | 0,000 | 0,381 | 0,991 | 2,608 | 5,460 | 7,569 | 45,882 |
| DOWN · UNAVAILABLE | final | 0 | — | — | — | — | — | — | — | — |
| DOWN · UNAVAILABLE | up | 0 | — | — | — | — | — | — | — | — |
| DOWN · UNAVAILABLE | down | 0 | — | — | — | — | — | — | — | — |

### Esempi (criterio retrospettivo dichiarato)

- s45 UP: prima origine disponibile 2025-09-01T12:45:00Z; final più opposto al verso 2025-11-30T15:45:00Z.
- s45 DOWN: prima origine disponibile 2025-09-01T02:15:00Z; final più opposto al verso 2025-09-28T14:15:00Z.
