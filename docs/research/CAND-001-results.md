# CAND-001/v1 — sviluppo 2023–2024 (DEV) e confronto aggiuntivo 2025

**Licenza di questo file e delle immagini in `docs/research/CAND-001-screens/`:** derivati aggregati di dati Binance Vision. Solo per questi derivati si applica **CC BY-NC-SA 4.0** (https://creativecommons.org/licenses/by-nc-sa/4.0/).
- Attribuzione: **Fonte: Binance Vision** (https://data.binance.vision).
- Termini: https://github.com/binance/binance-public-data/blob/master/TERMS_AND_CONDITIONS.md (copia locale del 16 ottobre 2026, SHA256 `99c4921d…`, riusata da OBS-001).
- Uso personale di ricerca non produttiva; nessuna associazione commerciale.
- La licenza del codice non cambia. Dati grezzi e bundle non sono redistribuiti.

Che cosa è questo documento. Sono risultati di **operazioni ipotetiche modellate** su prezzi storici, con nozionale normalizzato fisso di 1.000 USDT per operazione, senza leva né reinvestimento. Non è il rendimento di un conto, non è una strategia validata e non autorizza denaro reale. I dati 2023–2024 sono destinati alle iterazioni di sviluppo, non sono dati mai visti. Il **2025** è un **confronto aggiuntivo su dati già esposti** in studi precedenti, elaborato dopo il checkpoint del Director con la stessa versione congelata: **non è una validazione indipendente** e non ha prodotto iterazioni sul metodo.

## Provenienza

| Voce | Valore |
|---|---|
| Specifica | `docs/research/CAND-001-v1.md`, commit `0d4882848d014f8137153848171243674759370d` (17 ottobre 2026) |
| Configurazione | `config/CAND-001-v1.json`, candidato 1.0.0, SHA256 canonico `aed2c4ef627617d73972778097bbab5fb702ab5064ce9e6eb68ded2170ce4edf`. Preregistrata e pubblicata con motore e 28 test sintetici nel commit `8146336` prima di qualunque download o backtest |
| Osservazioni | OBS-001/v1 invariate (`3c4eb884…2387`), stesso osservatore con input da ottobre 2022 |
| Motore | `cand001` 1.0.1, schema `cand001.bundle/2` (patch R1, sezione «Correzioni R1»). Candidato e configurazione invariati |
| Run DEV corrente | `CAND-001-v1.0.0-e1.0.1-DEV-adaa94c502-aed2c4ef62`; input hash `adaa94c502…`; bundle 9,1 MB, SHA256 `b141150237e94a807817adea2d9fb6810f6eabc220d7db5ea3602d8b79b4944a`. Eseguito offline dal commit `0a46892`, rieseguito dal commit `605544b` con bundle identico byte per byte |
| Run precedente (conservato) | `CAND-001-v1.0.0-e1.0.0-DEV-adaa94c502-aed2c4ef62`, motore 1.0.0, bundle SHA256 `53d5fdcfbfe1c4ef…`; non sovrascritto |
| Prestazioni DEV | 22,4 s in tutto: controllo input 18,3 s, osservatore + decisioni + ledger 2,0 s. Picco di memoria 533 MB (Python 3.12.14, Windows 10) |
| Motore per il 2025 | `cand001` 1.0.2: solo supporto tecnico della finestra 2025 (prefisso intero, riuso dei file verificati). Decisioni, ledger, candidato e configurazione invariati. Pubblicato nel commit `078d9ed` **prima** di qualunque esito 2025 |
| Run 2025 | `CAND-001-v1.0.0-e1.0.2-ADDITIONAL_2025-9324c5d179-aed2c4ef62`; input hash `9324c5d1795fc0a4…`; bundle 4,6 MB, SHA256 `7c6ff10e2051c2576c9fd6ee790a7952d22ee22937a3e69e8dde482abce3a721`. Eseguito offline dal commit pulito `078d9ed`, rieseguito subito dopo: bundle identico byte per byte, nessuna sovrascrittura |
| Prestazioni 2025 | 22,9 s in tutto: controllo input 18,7 s (39 mesi), osservatore + decisioni + ledger 2,8 s. Picco di memoria 709 MB |

## Dati effettivi (acquisiti il 17 ottobre 2026, 07:29–07:31 UTC)

| Tipo | File | Copertura | Note |
|---|---|---|---|
| Klines negoziate 1m | 27 ZIP, da ottobre 2022 a dicembre 2024, tutti nuovi | 1.185.120 minuti validi su 1.185.120 (inizializzazione 132.480) | Nessun mancante, invalido, duplicato o fuori ordine. I 7 ZIP verificati di OBS-001 sono del 2025: non servono a DEV e non sono stati letti |
| fundingRate | 24 ZIP, 2023–2024 | 2.193 eventi (731 giorni × 3), intervallo sempre 8 h, jitter massimo 29 ms | Nessuna anomalia di ordine o intervallo; con il motore 1.0.1 la serie risulta **certificata** (primo evento al confine iniziale, ultimo 8 h prima della fine). Il checksum di gennaio 2023 coincide con quello del Director (`05e3df32…`) |
| markPriceKlines 1m | 24 ZIP, 2023–2024 | Serve 1 punto per evento: 2.189 disponibili su 2.193 | Manca un giorno intero di mark nel febbraio 2023 (funding del 24 febbraio alle 08:00 e 16:00 e del 25 alle 00:00) e 2 minuti nell'agosto 2024. Il punto del 1° gennaio 2023 alle 00:00 richiederebbe il mark di dicembre 2022, non acquisito: non serve, perché la finestra parte senza posizioni. **Nessuna operazione è toccata dai punti mancanti.** Checksum di gennaio 2023 uguale a quello del Director (`18abe5d6…`) |

Identità dello strumento (BTCUSDT, PERPETUAL, BTC/USDT, margine USDT) e termini sono riusati dalla verifica OBS-001 del 16 ottobre, con provenienza registrata nel manifest. Sono metadati correnti, non certificano condizioni storiche.

**Assunzioni economiche** (dalla sezione 9 del protocollo, non verificate su un conto):
- **Baseline.** Fee 5 bp per lato e slippage 3 bp avverso per ogni eseguito; tutte le uscite modellate taker.
- **Funding.** Storico, valorizzato con il close mark 1m del minuto precedente.
- **Stress.** 10 + 10 bp sullo stesso ledger: è una rivalutazione, non un secondo percorso.

## Riscontro separato dell'esecutore (non è una verifica indipendente del Director)

Script scritto da me (Claude Code), separato dal motore ma dallo stesso autore. Rilegge i minuti grezzi dagli ZIP con un parser proprio e ricalcola le sole call e operazioni presenti nel bundle. **Perimetro:** non cerca call mancanti fra gli episodi che si sono astenuti, non ricalcola le osservazioni (pivot, struttura) né rilegge i file di funding: per il funding verifica il cashflow da tasso e mark registrati.

**DEV**, per tutte le 87 call:
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

Zero differenze sul DEV. **2025**: stesso script, minuti letti da cartella CAND-001 e archivi OBS-001; 31 call e 29 operazioni, **zero differenze** nel perimetro descritto.


## Correzioni R1 (motore 1.0.1)

La review CAND-001 (commit `d9cabee`) ha mantenuto il candidato 1.0.0 e la configurazione `aed2c4ef…ce4edf` e ha assegnato tre correzioni tecniche. Ogni difetto è stato prima riprodotto sul codice della consegna iniziale (identico a `ee7282f`), poi corretto e coperto da test (`tests/test_cand001_r1.py`, `dashboard/src/ui/backtest/BacktestR1.test.tsx`). Codice: commit `0a46892` e `605544b`.

| Difetto | Prima (codice `ee7282f`, riprodotto) | Dopo (motore 1.0.1) | Impatto sul run DEV |
|---|---|---|---|
| R1-A · funding non certificato | Una serie vuota risultava «certificata». Un buco interno (intervallo diverso da 8 h) era segnalato ma non bloccava: un'operazione aperta nel buco riceveva funding 0 senza risultare «mancante» | Il run economico si ferma **prima del ledger** se la serie è vuota, ha righe corrotte, duplicati o conflitti, eventi fuori mese, intervalli incongruenti o copertura ai confini non verificabile. Errore preciso e rapporto di qualità conservato nel manifest. I singoli punti mark mancanti restano MISSING per i soli cashflow interessati | Nessuno: 2.193 eventi, 0 anomalie, serie certificata |
| R1-B · operazione irrisolta | Con una lacuna a posizione aperta il run si fermava, ma l'operazione spariva dal ledger. Netto e stress del periodo valevano 0,0, senza alcun netto «mancante» | L'operazione resta nel ledger come «percorso irrisolto» con i fatti noti: ingresso, fee d'ingresso, protezioni, funding fino alla lacuna. Uscita, PnL, netto e stress sono mancanti, e così netto, stress e drawdown del periodo. La «parte nota» (sole operazioni concluse) è dichiarata parziale. Chiusure valutate e teoriche sono separate; i mesi dopo la lacuna sono «non valutati», mai zero. La riconciliazione separa la parte nota dalla completezza della finestra. L'app apre un bundle interrotto: avviso, registro, episodio | Nessuno: 1.185.120 minuti validi su 1.185.120, nessuna interruzione |
| R1-C · prezzo corrente nell'app | Nell'episodio, in 1D a un momento diverso dalla mezzanotte (o al momento d'ingresso, 60 s dopo la chiusura 45m) l'ultima candela completa era mostrata come «Prezzo corrente della scala» | Prezzo corrente solo se una candela completa della scala termina esattamente al momento consultato. Altrimenti un avviso indica l'ultimo noto della stessa scala, con orario di chiusura e dicitura «non corrente». Tratto senza candele complete: messaggio di indisponibilità | Solo visualizzazione, nessun numero |

Nella prova nel browser della fixture interrotta ho trovato e corretto un difetto introdotto dalla patch stessa: le chiusure valide erano contate anche dopo l'interruzione (639 valide su 581 valutate). Ora sono contate solo fra quelle valutate. Le finestre complete, come il DEV, non sono toccate.

**Confronto con il run precedente** (bundle e1.0.0 `53d5fdcf…` contro e1.0.1 `b1411502…`, script separato):
- candidato, convenzioni, finestra, fonte, nozionale e input hash: uguali;
- 814 episodi con stati e conclusioni, 87 richieste, 360 finestre del grafico: uguali;
- 78 operazioni: zero campi diversi, nessun campo nuovo, nessuna irrisolta;
- sintesi: tutti i valori comuni uguali. Unica differenza: tolto il vecchio flag `reconciliation.reconciled`, sostituito da `knownPartReconciled` e `windowComplete` (entrambi veri);
- campi nuovi: copertura completa, 23.392 chiusure valutate su 23.392, 0 irrisolte, parte nota uguale al netto (−210,59).

Il confronto «22% di target contro un pareggio teorico del 33%» è stato tolto: il 33% vale solo per operazioni identiche con due sole uscite e non è il pareggio effettivo di questo ledger.

## Diagnosi DEV (classi del protocollo)

Le regole della v1 sono rimaste invariate. Le scomposizioni qui sotto sono descrittive, calcolate sul ledger e sui minuti, e non selezionano operazioni o parametri.

**Bug.** La consegna iniziale (commit `ee7282f`) dichiarava «nessuno trovato», sulla base del riscontro indipendente di call e operazioni. La review del Director ha poi individuato tre difetti del programma, non delle regole:
- funding accettato senza certificazione della serie (R1-A);
- trade irrisolto trasformato in risultati a zero (R1-B);
- prezzo «corrente» mostrato nell'app senza una candela che termina al momento consultato (R1-C).

Sono corretti nel motore 1.0.1; dettagli e riproduzioni nella sezione «Correzioni R1». **Impatto verificato sul run DEV: nessuno.** I dati 2023–2024 non attivano i casi difettosi. Rieseguito offline, il run ha decisioni, richieste e 78 operazioni identiche al precedente, con gli stessi importi. Durante lo sviluppo iniziale i test avevano segnalato anche errori nei miei casi di test, non nel motore: profondità 1/4 e 3/4 sono ammesse ai bordi, e un 1D indisponibile non è un 1D contrario.

**Decisione non fedele al disegno — nessuna individuata.** Due interpretazioni tecniche mie, da confermare:
- le contraddizioni della reazione sono valutate anche alla chiusura di creazione t0, dove il trigger è comunque vietato. Non cambia gli ingressi, anticipa al massimo di una barra la conclusione di un episodio già perso;
- un'operazione che si chiude esattamente su una chiusura 45m rende «occupata» quella chiusura per nuove gambe.

**Scelta coerente ma poco utile — la classe più evidente nelle descrizioni, senza conclusione causale.** Sono descrizioni distinte dello stesso ledger:
- PnL ai prezzi di riferimento, prima di slippage, fee e funding: −85,44 USDT su 78 operazioni.
- Il target (ritorno a P1) è raggiunto in 17 operazioni su 78.
- Le 56 uscite in stop si erano mosse a favore di appena 0,38R (mediana dell'escursione favorevole massima, R = rischio geometrico iniziale). Solo il 25% aveva toccato almeno 1R prima dello stop.
- In questo campione la ripresa (chiusura oltre il massimo o minimo precedente) non è stata seguita, in media, da un ritorno all'estremo prima dell'invalidazione.
- Le uscite per struttura opposta (4) e per 24 ore (1) sono rare.
- Protezioni aggiornate: 31, su 23 operazioni; il netto di quelle operazioni è −21,65.

**Costo/assunzione sensibile — rilevante.**
- Lo stop è vicino: il rischio iniziale mediano è lo 0,57% del nozionale. Fee e slippage di un giro valgono così circa il 28% di R (mediana; P10 14%, P90 49%).
- Dei −210,59 di netto, −124,81 sono fee e slippage assunti. Lo stress porta il netto a −397,80.
- Il PnL ai prezzi di riferimento (−85,44) è già negativo prima dei costi: è una voce dello stesso ledger, non un percorso alternativo senza costi.
- Funding trascurabile (−0,34), nessuna ambiguità ai confini e nessun funding mancante nelle operazioni.
- Nessun contatto stop+target nello stesso minuto e nessuna uscita in gap: la regola stop-first sull'ordine intrabar non è mai intervenuta.

**Informazione insufficiente — da tenere presente.**
- Le operazioni sono 78 in 24 mesi (circa 3 al mese), con 2,0% del tempo in posizione.
- I mesi negativi sono 15, quelli positivi 8, uno senza operazioni.
- Concentrazione osservata: i 5 trade maggiori pesano il 14,7% della somma dei |netti|, i 5 peggiori il 16,7% della somma dei negativi. È una descrizione di questo campione, non una prova sulla famiglia di metodi.
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

**Non è una raccomandazione di revisione.** Il Director ha deciso di mantenere la v1 senza modifiche metodologiche e di conservare l'evidenza negativa. Le osservazioni qui sopra non sono una griglia di soglie da provare.

## Confronto aggiuntivo 2025 (ADDITIONAL_2025)

### Che cosa è e che cosa non è

Stessa versione 1.0.0 e stessa configurazione `aed2c4ef…ce4edf`, nessuna modifica dopo il DEV. Valutazione [2025-01-01, 2026-01-01) UTC:
- osservazioni calcolate su **tutto il prefisso** dal 2022-10-01, senza azzeramenti a gennaio 2025;
- partenza FLAT: nessun episodio, richiesta o posizione ereditati dal 2024; si attendono nuove gambe disponibili nel 2025;
- nessun dato 2026: l'ultima apertura 1m del 2025 chiude il segmento secondo il protocollo (nessuna operazione ne ha avuto bisogno).

Il 2025 era già stato esaminato in studi precedenti (vedi `EXPOSURES.md`): è un confronto descrittivo con il DEV, non una prova su dati mai visti.

### Supporto tecnico (motore 1.0.2) e controlli prima degli esiti

Il motore 1.0.1 caricava, per il 2025, solo i mesi 2025. La patch 1.0.2 separa tre insiemi:
- mesi da **osservare** (39, ottobre 2022 – dicembre 2025);
- mesi da **riusare** da OBS-001 (giugno–dicembre 2025, letti dove sono dopo la verifica dello SHA256);
- mesi da **acquisire**.

Un file già verificato non genera richieste di rete. Controlli sintetici nuovi (`tests/test_cand001_additional2025.py`, 9 test):
- piano degli input senza mesi 2026;
- acquisizione con rete simulata: esattamente 29 archivi, nessun file OBS riscaricato, seconda esecuzione senza richieste;
- store dal 2022-10-01 con una riga 2026 scartata;
- osservazioni al confine uguali a quelle della stessa serie continua;
- finestra che parte FLAT.

Sul codice precedente i test di piano, acquisizione e caricamento non passano, perché il supporto non esisteva. Il DEV ricalcolato in memoria con 1.0.2 dà un bundle uguale a e1.0.1 salvo versione del motore e ID del run.

Verifica sui dati reali, dopo il run: le osservazioni dello store 2025 e di quello DEV sono identiche su tutto il tratto comune. Sono 26.336 barre 45m, 823 giornaliere e 20.695 eventi 45m disponibili entro il 1° gennaio 2025. Alla prima barra 2025 volatilità e medie hanno già la loro storia.

### Dati 2025 (acquisiti il 17 ottobre 2026, 08:35–08:36 UTC)

| Tipo | File | Copertura | Note |
|---|---|---|---|
| Klines negoziate 1m | 39 mesi letti: 27 CAND-001 già verificati (nessuna richiesta), **5 nuovi** (gennaio–maggio 2025), **7 OBS-001 riusati** (giugno–dicembre 2025) con SHA256 uguale al manifest OBS e al checksum del fornitore | **1.710.720 minuti validi su 1.710.720** (prefisso 1.185.120); 2025: 11.680 chiusure 45m su 11.680 | Nessun mancante, invalido, duplicato o fuori ordine. File OBS non modificati (hash prima/dopo uguali). Manifest del riuso: `manifests/reuse-trade-obs.json` |
| fundingRate | 12 ZIP nuovi, 2025 | 1.095 eventi, intervallo sempre 8 h, jitter massimo 16 ms | Serie **certificata** (R1-A): primo evento al confine iniziale, ultimo 8 h prima della fine, 0 anomalie |
| markPriceKlines 1m | 12 ZIP nuovi, 2025 | 1.094 punti su 1.095 | Manca solo il punto del 1° gennaio 2025 alle 00:00, che richiederebbe il mark del 31 dicembre 2024 non caricato per il 2025. La finestra parte senza posizioni: **nessuna operazione è toccata** |

In totale **29 archivi nuovi**, come atteso; nessun trade riscaricato. Assunzioni economiche invariate: fee 5 bp per lato, slippage 3 bp, funding storico valorizzato con mark 1m, stress 10 + 10 bp.

### Esito 2025

Copertura completa, nessuna operazione irrisolta, nessun costo mancante: il netto è un risultato completo, non parziale.

**Somme di operazioni ipotetiche da 1.000 USDT, non rendimento di un conto:**
- 29 operazioni, 13 LONG e 16 SHORT;
- 31 call, 2 rifiutate al prezzo;
- netto modellato **−109,08 USDT**, di cui PnL ai prezzi di riferimento −62,54, slippage −17,41, fee −29,01 e funding −0,12;
- stress −178,71;
- drawdown massimo −113,99 sulle chiusure 1m.

**Diagnosi 2025 per classi** (descrittiva, stesse scomposizioni del DEV, nessuna nuova suddivisione):
- **Bug — nessuno trovato** nei controlli svolti (riscontro separato, osservazioni al confine, riesecuzione identica). Nessuna correzione dopo gli esiti.
- **Decisione non fedele al disegno — nessuna individuata.** Valgono le due interpretazioni già confermate dal Director.
- **Scelta coerente ma poco utile.**
  - PnL ai prezzi di riferimento −62,54 su 29 operazioni.
  - Target raggiunto in 3 operazioni su 29.
  - Le 22 uscite in stop si erano mosse a favore di 0,58R in mediana; il 32% aveva toccato almeno 1R.
  - Rapporto spazio/rischio mediano all'ingresso 2,26 (P10 1,73, P90 3,60).
  - Le 4 uscite per struttura opposta sommano −5,87.
- **Costo/assunzione sensibile.**
  - Rischio iniziale mediano 0,47% del nozionale; fee e slippage di un giro valgono circa il 34% di R (mediana; P10 18%, P90 53%).
  - Dei −109,08 di netto, −46,42 sono fee e slippage assunti.
  - Funding trascurabile, nessuna ambiguità o funding mancante; nessun contatto stop+target nello stesso minuto.
- **Informazione insufficiente.**
  - 29 operazioni in 12 mesi, 1,0% del tempo in posizione.
  - Mesi: 10 negativi, 1 positivo (marzo, +5,96), 1 senza operazioni (novembre: nessuna call, non un risultato a zero).
  - LONG −41,84 (13), SHORT −67,24 (16).
  - Concentrazione osservata: i 5 trade maggiori pesano il 31,9% dei |netti|. I 5 migliori fanno il 97,2% della somma dei positivi, perché i positivi sono solo 6.

**Dove si perde la selezione nel 2025.** Su 2.847 gambe considerate:
- 1.687 sono escluse per struttura 45m non nel verso;
- 466 per ampiezza;
- 233 perché il candidato era occupato;
- 461 sono riconosciute.

Delle 461:
- 157 si astengono per rapporto spazio/rischio (mediana 0,64);
- 138 per profondità della reazione;
- 120 per P1 già ritoccato;
- 9 per struttura opposta e 6 per scadenza;
- 2 richieste sono rifiutate al prezzo.

### Confronto descrittivo con il DEV

Solo descrizioni affiancate, senza test di significatività né conclusioni causali:

| Voce | DEV 2023–2024 | 2025 |
|---|---:|---:|
| Operazioni (al mese) | 78 (3,25) | 29 (2,42) |
| Netto per operazione, media | −2,70 | −3,76 |
| PnL ai riferimenti per operazione, media | −1,10 | −2,16 |
| Uscite al target | 17 su 78 | 3 su 29 |
| Quota operazioni nette positive | 24,4% | 20,7% |
| Rapporto spazio/rischio all'ingresso, mediana | 2,05 | 2,26 |
| Rischio iniziale, mediana (% di N0) | 0,57% | 0,47% |
| Costi di un giro in quota di R, mediana | 28% | 34% |
| Escursione favorevole delle uscite in stop, mediana | 0,38R | 0,58R |
| Call su episodi riconosciuti | 87 su 814 | 31 su 461 |
| Tempo in posizione | 2,0% | 1,0% |

In entrambi i periodi il PnL ai prezzi di riferimento è negativo prima dei costi, i costi assunti allargano la perdita e la maggior parte delle uscite è in stop. Il 2025 ha meno operazioni e meno uscite al target. I campioni sono piccoli (78 e 29 operazioni): le differenze fra periodi non vanno lette come tendenze.

### Casi contrari ed esempi 2025

Esempi con la stessa regola cronologica, primi per verso; categorie vuote dichiarate (astensione per dato mancante: nessun dato mancava).
- Prima call e prima operazione: LONG del 5 gennaio 2025 (call alle 03:00, ingresso alle 03:01), uscita in stop, −4,05 USDT. È anche il primo caso negativo.
- Prima astensione: LONG del 2 gennaio 2025 alle 00:45, reazione invalidata.
- Prima protezione aggiornata: SHORT del 5 maggio 2025.
- Casi contrari: la prima operazione SHORT (8 febbraio 2025) è positiva; marzo è l'unico mese positivo; le 3 uscite al target sommano +20,52.

Nell'app i cinque pulsanti del bundle 2025 aprono questi episodi.

## Raccomandazione (per Director e Astra)

- **Non promuovere CAND-001 v1** a qualunque uso, nemmeno simulato in tempo reale: negativo nel DEV (−210,59) e nel confronto 2025 (−109,08), già ai prezzi di riferimento prima dei costi, con costi assunti che pesano circa un terzo del rischio per operazione.
- **Conservare l'evidenza negativa** com'è, senza varianti scelte guardando il 2025: il 2025 è già esposto e non può selezionare una v2.
- **Non scartare per questo l'intera famiglia** «movimento → reazione → ripresa». L'evidenza riguarda questa specifica, con stop vicino, target al ritorno su P1 e costi assunti. Un candidato futuro della stessa famiglia richiederebbe un nuovo disegno preregistrato, motivato senza usare i risultati 2025, e dati non ancora esposti con un mandato specifico.
- La chiusura della macrofase spetta al Director, dopo la review e la prova concreta di Gian.

## Casi contrari ed esempi DEV

Gli esempi sono stati scelti con la regola cronologica registrata (sezione 12 del protocollo). Il primo episodio SHORT del 1° gennaio 2023 è insieme prima call, prima operazione, primo caso negativo e prima protezione aggiornata: −2,69 USDT, uscita in stop dopo aver alzato la protezione. Nell'app i cinque pulsanti aprono direttamente questi episodi. Nella tabella in fondo ci sono anche il primo positivo e le prime astensioni per verso. Le categorie vuote (astensione per dato mancante) sono dichiarate.

## Limiti

- Esecuzione modellata: nessun order book, nessuna coda, impatto o profondità; nessun margine, leva o liquidazione.
- Fee e slippage sono assunzioni di studio. Il funding usa un proxy mark 1m.
- Le risoluzioni sono 1m: i contatti dentro il minuto seguono la regola stop-first, che qui non è mai servita.
- Il drawdown è calcolato sulle chiusure 1m, non tick per tick.
- 2023–2024 sono dati di sviluppo già usati per questa diagnosi.
- Il comportamento con funding non certificato e con percorso irrisolto è verificato su dati sintetici: il DEV reale non contiene questi casi.
- Nell'app, a 390 px di larghezza l'intestazione dell'episodio (badge e pulsanti dei momenti) sporge di 256 px. Il difetto c'era già prima di R1 ed è fuori dal perimetro desktop di questa fase.
- Il 2025 è già esposto e non è una validazione indipendente; 29 operazioni sono un campione piccolo.
- Riscontro separato e verifiche dei dati sono dell'esecutore: il Director non ha ricalcolato autonomamente archivi, ledger o operazioni reali.
- Il bundle DEV e1.0.0 (schema /1) resta conservato ma l'app non lo apre.

## Tabelle generate dal motore

Generate con le funzioni del motore dai bundle DEV e1.0.1 e 2025 e1.0.2, affiancate senza ricopiare numeri. Mesi assegnati per ingresso; cashflow per data effettiva; tutti i mesi, anche senza operazioni. Arrotondamento solo in visualizzazione. I totali non si sommano fra DEV e 2025: sono finestre distinte, ognuna partita FLAT.

### Popolazione, opportunità e operazioni

| Voce | 2023 | 2024 | DEV | 2025 |
|---|---:|---:|---:|---:|
| Copertura | completa | completa | completa | completa |
| Chiusure 45m valutate / teoriche (dati validi) | 11680 / 11680 (11680) | 11712 / 11712 (11712) | 23392 / 23392 (23392) | 11680 / 11680 (11680) |
| Operazioni irrisolte (lacuna con posizione aperta) | 0 | 0 | 0 | 0 |
| Gambe considerate | 2926 | 2906 | 5832 | 2847 |
| Episodi riconosciuti | 372 | 442 | 814 | 461 |
| Call (LONG/SHORT) | 45 (21/24) | 42 (11/31) | 87 (32/55) | 31 (14/17) |
| Ingressi eseguiti / rifiutati prezzo / senza quotazione | 41 / 4 / 0 | 37 / 5 / 0 | 78 / 9 / 0 | 29 / 2 / 0 |
| Operazioni (LONG/SHORT) | 41 (19/22) | 37 (11/26) | 78 (30/48) | 29 (13/16) |
| Uscite STOP / TARGET / STRUTTURA / 24h / FINE | 30 / 9 / 1 / 1 / 0 | 26 / 8 / 3 / 0 / 0 | 56 / 17 / 4 / 1 / 0 | 22 / 3 / 4 / 0 / 0 |
| Protezioni aggiornate (operazioni) | 17 (12) | 14 (11) | 31 (23) | 5 (5) |
| Stop e target nello stesso minuto | 0 | 0 | 0 | 0 |
| Uscite in gap all'apertura | 0 | 0 | 0 | 0 |

### Risultato modellato (USDT per operazioni da N0 = 1.000 USDT; somme, non rendimento composto)

| Voce | 2023 | 2024 | DEV | 2025 |
|---|---:|---:|---:|---:|
| PnL prezzi ai riferimenti | -49,79 | -35,65 | -85,44 | -62,54 |
| Slippage attribuito | -24,57 | -22,23 | -46,80 | -17,41 |
| Fee | -40,95 | -37,06 | -78,01 | -29,01 |
| Funding | -0,57 | 0,23 | -0,34 | -0,12 |
| **Netto modellato** | **-115,87** | **-94,72** | **-210,59** | **-109,08** |
| Netto in punti base di N0 | -1.159 | -947 | -2.106 | -1.091 |
| Parte nota: netto delle sole operazioni concluse | -115,87 (41) | -94,72 (37) | -210,59 (78) | -109,08 (29) |
| Intervallo ambiguità funding | 0,000 / +0,000 | 0,000 / +0,000 | 0,000 / +0,000 | 0,000 / +0,000 |
| Sensibilità target-first (stesso minuto) | 0,00 | 0,00 | 0,00 | 0,00 |
| Netto stress (fee 10 bp, slippage 10 bp) | -214,15 | -183,65 | -397,80 | -178,71 |
| Quota operazioni nette positive | 24,4% | 24,3% | 24,4% | 20,7% |
| Payoff medio (vincita/perdita) | 1,29 | 1,67 | 1,48 | 0,69 |
| Profit factor | 0,42 | 0,54 | 0,48 | 0,18 |
| Netto per operazione: mediana (P25 / P75) | -5,45 (-6,78 / -1,69) | -5,95 (-7,96 / -0,93) | -5,76 (-7,06 / -1,12) | -4,69 (-6,12 / -1,46) |
| Netto per operazione: P10 / P90 | -8,80 / 8,77 | -11,65 / 11,13 | -9,62 / 10,12 | -8,38 / 2,14 |
| Durata mediana (minuti) | 220 | 254 | 227 | 129 |
| Rischio iniziale q·R0 / N0, mediana | 0,5% | 0,6% | 0,6% | 0,5% |
| Netto / rischio iniziale, mediana | -1,16 | -1,11 | -1,13 | -1,22 |
| Sequenza massima di perdite | 12 | 10 | 12 | 7 |
| Drawdown massimo (chiusure 1m) | -136,90 | -103,50 | -216,79 | -113,99 |
| Esposizione (quota del tempo in posizione) | 2,1% | 1,8% | 2,0% | 1,0% |
| Concentrazione top5 |netto| | 23,7% | 25,8% | 14,7% | 31,9% |
| Migliori 5 / somma positivi | 71,0% | 68,5% | 42,5% | 97,2% |
| Peggiori 5 / somma negativi | 27,0% | 31,3% | 16,7% | 36,7% |
| Operazioni con funding ambiguo / mancante | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |

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
| 2025-01 | 992/992 | 48 | 3 | 3 | -18,68 | -18,68 | 3/0/0/0/0 |
| 2025-02 | 896/896 | 34 | 4 | 4 | -19,64 | -19,64 | 2/0/2/0/0 |
| 2025-03 | 992/992 | 42 | 2 | 2 | 5,96 | 5,96 | 0/1/1/0/0 |
| 2025-04 | 960/960 | 41 | 4 | 4 | -26,31 | -26,31 | 3/0/1/0/0 |
| 2025-05 | 992/992 | 45 | 5 | 4 | -10,43 | -10,43 | 4/0/0/0/0 |
| 2025-06 | 960/960 | 33 | 1 | 1 | -5,30 | -5,30 | 1/0/0/0/0 |
| 2025-07 | 992/992 | 46 | 5 | 4 | -20,24 | -20,24 | 4/0/0/0/0 |
| 2025-08 | 992/992 | 33 | 3 | 3 | -4,08 | -4,08 | 2/1/0/0/0 |
| 2025-09 | 960/960 | 30 | 1 | 1 | -6,02 | -6,02 | 1/0/0/0/0 |
| 2025-10 | 992/992 | 36 | 2 | 2 | -0,36 | -0,36 | 1/1/0/0/0 |
| 2025-11 | 960/960 | 33 | 0 | 0 | 0,00 | 0,00 | 0/0/0/0/0 |
| 2025-12 | 992/992 | 40 | 1 | 1 | -3,99 | -3,99 | 1/0/0/0/0 |

### Motivi delle gambe e degli episodi (DEV e 2025)

| Esito della gamba | DEV | 2025 |
|---|---:|---:|
| ABSTAIN_STRUCTURE | 3549 | 1687 |
| ABSTAIN_AMPLITUDE | 995 | 466 |
| RECOGNIZED | 814 | 461 |
| SKIPPED_BUSY | 473 | 233 |
| ABSTAIN_DURATION | 1 | 0 |

| Conclusione dell'episodio | DEV | 2025 |
|---|---:|---:|
| ABSTAIN_REWARD_RISK | 271 | 157 |
| INVALIDATED_DEPTH | 266 | 138 |
| INVALIDATED_TARGET_REACHED | 161 | 120 |
| CLOSED | 78 | 29 |
| INVALIDATED_STRUCTURE | 14 | 9 |
| EXPIRED | 15 | 6 |
| REJECTED_PRICE | 9 | 2 |

### Esempi DEV (regola cronologica registrata prima degli esiti)

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

### Esempi 2025 (stessa regola cronologica)

| Verso | Categoria | Riferimento | Momento UTC |
|---|---|---|---|
| LONG | FIRST_CALL | EP:LONG:1736005500000:1736024400000 | 2025-01-05T03:00:00Z |
| LONG | FIRST_TRADE | TR:LONG:1736005500000:1736024400000 | 2025-01-05T03:01:00Z |
| LONG | FIRST_NEGATIVE_TRADE | TR:LONG:1736005500000:1736024400000 | 2025-01-05T03:01:00Z |
| LONG | FIRST_POSITIVE_TRADE | TR:LONG:1742752800000:1742774400000 | 2025-03-24T03:01:00Z |
| LONG | FIRST_PROTECTION_UPDATE | TR:LONG:1746565200000:1746578700000 | 2025-05-07T06:46:00Z |
| LONG | FIRST_ABSTAIN_REACTION_INVALIDATED | EP:LONG:1735751700000:1735765200000 | 2025-01-02T00:45:00Z |
| LONG | FIRST_ABSTAIN_REWARD_RISK | EP:LONG:1735776000000:1735792200000 | 2025-01-02T07:30:00Z |
| LONG | FIRST_ABSTAIN_MISSING_DATA | categoria vuota | — |
| SHORT | FIRST_CALL | EP:SHORT:1738951200000:1738959300000 | 2025-02-08T04:30:00Z |
| SHORT | FIRST_TRADE | TR:SHORT:1738951200000:1738959300000 | 2025-02-08T04:31:00Z |
| SHORT | FIRST_NEGATIVE_TRADE | TR:SHORT:1739842200000:1739866500000 | 2025-02-18T12:01:00Z |
| SHORT | FIRST_POSITIVE_TRADE | TR:SHORT:1738951200000:1738959300000 | 2025-02-08T04:31:00Z |
| SHORT | FIRST_PROTECTION_UPDATE | TR:SHORT:1746370800000:1746408600000 | 2025-05-05T07:31:00Z |
| SHORT | FIRST_ABSTAIN_REACTION_INVALIDATED | EP:SHORT:1735956900000:1735983900000 | 2025-01-04T15:45:00Z |
| SHORT | FIRST_ABSTAIN_REWARD_RISK | EP:SHORT:1735870500000:1735894800000 | 2025-01-03T13:30:00Z |
| SHORT | FIRST_ABSTAIN_MISSING_DATA | categoria vuota | — |
