# Diagnosi trasversale Owner ottobre–dicembre 2025 (v0.4) — sola lettura

Data: 2026-10-07. Incarico Owner: diagnosi trasversale in sola lettura delle tre valutazioni v0.4, con le baseline v0.3 come confronto dei record. È evidenza dell'executor, **non accettazione del Director**. Nessun replay, backtest, Deep validation, run controfattuale, download, modifica di prodotto/schema/metodo/dati o azione sullo stack Owner.

**Stato dei tre mesi.** Ottobre, novembre e dicembre 2025 sono ora **sviluppo esposto**. Non vanno più usati come verifica intatta per revisioni future.

| Mese | v0.4 (candidata) | v0.3 (baseline) | Pack / cache pinnata |
|---|---|---|---|
| Ottobre | `eval-20261007T094006-67272e` / `obs-…094006-0f9af7` | `eval-20261006T175135-9ddf6d` (build bd5d81c) | `pack-30c0661f…` / `fc-de5aa4a9…` |
| Novembre | `eval-20261007T102821-ae14be` / `obs-…102821-68ca1a` | `eval-20261007T101912-087dd1` | `pack-47ef4022…` / `fc-83bba301…` |
| Dicembre | `eval-20261007T105636-6d9276` / `obs-…105636-dba49c` | `eval-20261007T105343-eb536a` | `pack-bb3e895b…` / `fc-29ae65c9…` |

File:
- [dossier.json](dossier.json): provenienza, riconciliazione, tutte le call e conferme, tabulazioni, funnel B/C, MarketView, warmup, tail;
- [calls.csv](calls.csv): le 10 call;
- [confirmations.csv](confirmations.csv): le 64 conferme A;
- [extract_q4_diagnosis.py](extract_q4_diagnosis.py): lo script di estrazione;
- [export.sql](export.sql): la transazione di lettura.

Etichette:
- **STORED**: campo del journal o dei record di valutazione committati, oppure conteggio fatto dal builder di report del prodotto.
- **DERIVED**: aritmetica Decimal esatta su campi STORED, oppure su barre 1m trade pinnate non oltre il cutoff indicato. Per predicato e limiti economici sono state usate le funzioni pure del prodotto (`geometry`).
- **UNAVAILABLE**: non registrato, e non ricavabile senza replay o controfattuale.

## Provenienza e riconciliazione

**Lettura del DB.**
- Una sola transazione psql `REPEATABLE READ READ ONLY` nel container `db` dell'Owner, avviata con `docker exec` ([export.sql](export.sql)). Lo stack non è stato avviato, fermato né modificato.
- Parametri della transazione: `transaction_read_only=on`, snapshot `704341:704341:`.
- Righe lette, solo per le sei run: valutazione, replay, checkpoint, finish (blob escluso), pack, cache, journal completi e record di valutazione.
- L'export grezzo (sha256 `44c5dbc2…e094`) e le copie delle cache restano fuori da Git, nello scratchpad di sessione.

**Catene.** Per tutte e sei le run digest e catene sono stati ricalcolati e coincidono con il commitment di finish (journal ed evaluation records).

**Cache.** Le tre cache sono state copiate byte per byte e verificate:
- sha del manifest uguale al pin di entrambe le run del mese;
- tutte le partizioni verificate;
- trade minuti presenti: 50.765 (ott), 49.325 (nov), 50.765 (dic);
- copertura trade senza buchi in warmup, valutazione e tail.

**Run.**
- Tutte `completed`.
- Assurance `passed` 21/21: validator v7 per v0.4, v6 per v0.3.
- Le v0.4 hanno build `c525941…+image`.

**Comparabilità.** Ricalcolata con `compare.comparability` del prodotto: COMPARABLE per ciascun mese, senza differenze di pin. La baseline di ottobre ha build bd5d81c; la build non è un pin di comparabilità.

**Riproducibilità.** Due esecuzioni dello script producono file identici byte per byte.

**Conteggi.** Ricostruiti con `report4.build` e `report3.build`, selezionati come fa `evaluation/api.py`. Coincidono con quelli attesi:

| | Conferme A | WAIT | Call | RETURN entrati (PRIMARY 60 s) | PRIMARY |
|---|---:|---:|---:|---:|---|
| Ottobre | 19 | 14 | 4 (3 RETURN + 1 IMMEDIATE) | 3 | 2 target, 1 stop, 1 uscita guidance (TIME_EXPIRED) |
| Novembre | 20 | 16 | 2 RETURN | 2 | 2 stop |
| Dicembre | 25 | 16 | 4 RETURN | 4 | 4 stop |
| **Totale** | **64** | **46** | **10** | **9** | price-net somma **−1,307 %** (ott +1,084; nov −0,887; dic −1,504) |

- Il funding non è coperto: ogni path è `PRICE_NET_ONLY_TOTAL_NET_UNAVAILABLE`.
- Nel warmup di novembre compare la call del 31 ottobre 03:32 con lo stesso id della run di ottobre. Non è conteggiata due volte.

## Le 10 call

Tutte le call sono A. La fonte dei campi è indicata in testa a ciascuna colonna; il dettaglio completo è in [calls.csv](calls.csv) e in `dossier.json → calls`.

| # | Call (UTC) | Dir · modo | Epoch anchor alla conferma (perdite) | Conferma → ritorno usabile → emissione → ingresso | Rischio / guadagno all'emissione (bps) | Margine conf / emiss / ingresso (bps) | Prima finestra d'ingresso | PRIMARY | 0 s / 120 s / HORIZON_ONLY (%) | Scenario · guidance |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 10-06 18:26 | LONG RETURN | e2 (1) | 18:16 → 18:26 → 18:26 → 18:27 | 13,6 / 50,1 | −24,6 / +2,9 / +6,8 | 3 min | TARGET +0,378 % in 23 min | +0,360 / +0,365 / −0,120 | DESTINATION · TARGET_REACHED |
| 2 | 10-19 20:13 | LONG RETURN | e3 (1 + revisione) | 20:08 → 20:13 → 20:13 → 20:14 | 11,8 / 46,4 | −14,0 / +1,4 / +5,8 | 9 min (4 riaperture) | STOP −0,238 % in 58 min | −0,258 / −0,242 / −0,645 | V_CONTACT · INVALIDATED |
| 3 | 10-26 23:34 | LONG IMMEDIATE | e2 (1) | 23:34 → — → 23:34 → 23:35 | 25,3 / 99,4 | +38,2 / +38,2 / +33,7 | 2 min (4 riaperture) | GUIDANCE_TIME_EXPIRED +0,101 % in 240 min | +0,121 / +0,145 / +0,101 | TIME_EXPIRED · TIME_EXPIRED |
| 4 | 10-31 03:32 | LONG RETURN | e3 (2) | 03:08 → 03:32 → 03:32 → 03:33 | 37,6 / 98,6 | −5,8 / +22,7 / +22,1 | 3 min | TARGET +0,843 % in 67 min | +0,846 / +0,822 / +0,334 | DESTINATION · TARGET_REACHED |
| 5 | 11-17 21:44 | SHORT RETURN | e3 (1 + revisione) | 21:18 → 21:44 → 21:44 → **22:08** (23 aperture rifiutate) | 26,9 / 78,3 | −29,6 / +15,3 / +2,2 | 1 min (2 riaperture) | STOP −0,469 % in 34 min | −0,409 / −0,469 / −0,176 | V_CONTACT · INVALIDATED |
| 6 | 11-23 06:18 | LONG RETURN | e4 (3) | 05:55 → 06:18 → 06:18 → 06:19 | 32,0 / 69,8 | −11,4 / +0,6 / +9,8 | 3 min | STOP −0,418 % in 32 min | −0,460 / −0,429 / +0,045 | V_CONTACT · INVALIDATED |
| 7 | 12-01 17:08 | SHORT RETURN | e2 (1) | 16:55 → 17:08 → 17:08 → 17:09 | 61,9 / 131,0 | −88,1 / +25,9 / +20,6 | 2 min (4 riaperture) | STOP −0,784 % in 65 min | −0,760 / −0,853 / −0,661 | V_CONTACT · INVALIDATED |
| 8 | 12-05 11:07 | SHORT RETURN | e3 (1 + revisione) | 11:00 → 11:07 → 11:07 → 11:08 | 8,1 / 43,3 | −35,9 / +2,8 / +11,1 | 2 min (chiusa da terminale) | STOP −0,183 % in 0 min | −0,221 / NO_ENTRY / **+0,944** | V_CONTACT · INVALIDATED |
| 9 | 12-19 19:16 | SHORT RETURN | e2 (1) | 18:40 → 19:16 → 19:16 → 19:18 (1 apertura rifiutata) | 17,1 / 52,3 | −80,1 / +1,0 / +1,1 | 1 min | STOP −0,311 % in 1 min | −0,311 / −0,311 / −1,260 | V_CONTACT · INVALIDATED |
| 10 | 12-25 16:38 | LONG RETURN | e1 (0) | 16:27 → 16:38 → 16:38 → 16:39 | 6,3 / 44,7 | −55,0 / +6,4 / +1,2 | 3 min | STOP −0,226 % in 11 min | −0,203 / −0,229 / −0,545 | V_CONTACT · INVALIDATED |

Fonti delle colonne:
- **STORED**: epoch, timestamp, rischio/guadagno/margine all'emissione, margine alla conferma, path, scenario, guidance.
- **DERIVED**: margine all'ingresso PRIMARY (prezzo d'ingresso STORED, V e cap attivi a quel cutoff) e minuti della prima finestra.
- Il totale minuti di entry disponibile, riaperture incluse, è quello del report STORED: mediana 17 (ott), 32–35 (nov), 5 (dic).

**Anchor e provenienza (STORED, `anchors_STORED`).** Per ogni call il dossier riporta ogni ARM/REVISE/REARM/ANCHOR_LOST con:
- R/K/V e barra 15m sorgente;
- pubblicazione e cursore;
- intervallo 1m che ha invalidato l'anchor perso.

**Target e cap (STORED).**
- Le 9 call RETURN partono dal target `T_CONFIRM`, cioè il bordo vicino della zona del landmark limitante alla conferma. Landmark limitante: IMPULSE_B proprio in 4 casi (11-17, 11-23, 12-19, 12-25), pivot 15m/1h negli altri 5.
- La call 10 ha 1 revisione del cap: un nuovo pivot 15m ha portato il target da 88564,3 a 88564,0.
- La call 3 (IMMEDIATE) usa come target il bordo vicino della zona del proprio impulso B (115739,3 per B 115759,3).

**Tempo residuo (DERIVED).**
- Alla conferma: 240 min fino alla scadenza dura (conferma + 4 h); 22–93 min fino alla scadenza del setup.
- All'emissione: 204–240 min.
- I controlli di progresso della call cadono sempre dopo l'uscita, salvo la call 3, rimasta aperta fino a TIME_EXPIRED.

**Contesto ai cutoff decisivi (STORED, pubblicato al cambio).**
- Tutte e 10 le call avevano il contesto 1h allineato alla direzione: UP per i LONG, DOWN per gli SHORT.
- Fase: REACTION in 9/10 alla conferma, EXPANSION per la call 10. All'emissione alcune sono passate a TRANSITION/COMPRESSION.
- Dislocation `NORMAL/NORMAL` sempre.
- MarketView `CONDITIONAL_SCENARIO` nella direzione della call.

**Confronto con v0.3 (STORED).** Per 9 call su 10 lo scenario v0.3 nato sullo stesso bordo 15m e nella stessa direzione era terminato prima della conferma per V_CONTACT, senza call. Queste 9 call esistono solo per la sostituzione dell'anchor introdotta da MP-003. La call 10 (12-25, epoch 1) è identica nella baseline v0.3 di dicembre, ed è anch'essa uno stop.

## Le 54 conferme senza call (e le 64 complessive)

La classificazione è DERIVED dalle ragioni STORED di instradamento e fine. Vale per tutte le conferme, non per una selezione.

| Classe | Ott | Nov | Dic | Tot |
|---|---:|---:|---:|---:|
| Call | 4 | 2 | 4 | 10 |
| Cap/ostacolo durante WAIT: contatto lato target prima del ritorno (`PRE_ENTRY_TARGET_CONTACT`) | 4 | 5 | 5 | 14 |
| Terminale durante WAIT: scenario a destinazione B | 5 | 5 | 2 | 12 |
| Terminale durante WAIT: scenario V_CONTACT | 0 | 2 | 0 | 2 |
| Mancato ritorno: scadenza del setup originale | 2 | 0 | 4 | 6 |
| Restrizione di contesto (`CONTEXT_FORBIDDEN_PREISSUE`) | 0 | 2 | 1 | 3 |
| Geometria alla conferma: `NO_ECONOMIC_RETURN_REGION` | 2 | 3 | 4 | 9 |
| Cap/ostacolo alla conferma: `AT_OPPOSING_AREA` (tutti INSIDE_ZONE, esclusi da D) | 1 | 1 | 4 | 6 |
| Cap/ostacolo alla conferma: `PRE_ENTRY_TARGET_CONTACT` | 1 | 0 | 1 | 2 |
| Selezione (slot, priorità, conflitto) | 0 | 0 | 0 | **0** |
| Restrizione di esecuzione/dislocation | 0 | 0 | 0 | **0** |

**D/N (STORED).** Ottobre 18/3, novembre 19/3, dicembre 21/5.

**WAIT minuto per minuto (DERIVED, cutoff = fine di ciascuna WAIT).**
- I blocker di prezzo ricostruiti coincidono con quelli STORED in **963 su 963** minuti campionati.
- L'unico blocker non di prezzo osservato è `BLOCKED_BY_ZONE`, per 4 minuti (WAIT del 21 dicembre).
- Solo 9 WAIT su 46 hanno avuto almeno una chiusura nella regione economica: sono esattamente le 9 entrate.
- Il ritracciamento richiesto dalla chiusura di conferma al bordo della regione economica è di 5–71 bps, mediana ≈ 24.

**Esito strutturale dello scenario dopo la conferma (STORED, indipendente dall'ingresso).**

| Gruppo | Destinazione B | V_CONTACT | Scadenza dura | STALLED |
|---|---:|---:|---:|---:|
| WAIT **con** ritorno usabile (= 9 call RETURN entrate) | 2 | **7** | 0 | 0 |
| WAIT **senza** ritorno usabile (37) | **30** | 3 | 3 | 1 |
| Terminale alla conferma (17) | 11 | 6 | 0 | 0 |
| IMMEDIATE (1) | 0 | 0 | 1 | 0 |
| **Tutte le 64** | **43** | 16 | 4 | 1 |

**Storia dell'anchor (STORED).**
- Lo scenario raggiunge B con la stessa frequenza dopo una sostituzione (29/43) e sul primo anchor (14/21).
- La sostituzione cambia invece l'instradamento: dopo una sostituzione 37 WAIT + 1 IMMEDIATE su 43; sul primo anchor 9 WAIT su 21, con 12 terminali alla conferma.

## Funnel B/C e MarketView (STORED, builder di report)

**B/C.** Identici fra v0.3 e v0.4 in ciascun mese:
- conferme B/C: 5 (ott), 3 (nov), 2 (dic);
- **0 call**;
- terminali principali: WITHDRAWN (rientro prima del retest, contesto alla nascita, espansione direzionale), EXPIRED (scadenza del setup, box ritirato).

**Copertura.** 100 % dei minuti valutabili in tutti i mesi.
- Righe MarketView v0.4: NO_QUALIFIED_STRUCTURE ≈ 66–70 %, BALANCED_RANGE ≈ 20–24 %, CONDITIONAL_SCENARIO ≈ 4–6 %, WATCH_ONLY ≈ 5 %.
- Intervallo massimo senza call: 314 h (ott), 406 h (nov), 344 h (dic).

**Campioni di vista** (orari, v0.4).
- Ottobre: 39 direzionali; segno corretto 24 a 1h e 27 a 4h.
- Novembre: 30 direzionali; segno corretto 14 a 1h e 13 a 4h.
- Dicembre: 52 direzionali; segno corretto 25 a 1h e 23 a 4h.
- Tutte le altre ore sono astensioni. Sono etichette condizionali, non probabilità calibrate.

**Condizioni.**
- `NO_ARMED_SCENARIO` per ≈ 96–97 % del tempo.
- `SLOT_OCCUPIED`: 394 min (ott), 93 (nov), 86 (dic). Nessuna conferma è stata rifiutata per slot.
- Dislocation attiva 21 min (ott) e 1 min (nov).

## Limiti del contesto iniziale (warmup di 96 h)

Le dipendenze dichiarate 15m e 1h diventano READY dopo 6 h 15 e 21 h di warmup, quindi prima dell'inizio del mese. La memoria registrata dei landmark però è più lunga del warmup (STORED/DERIVED):

| Orizzonte | Memoria registrata | Primo landmark pubblicato (ott / nov / dic) | Conseguenza |
|---|---|---|---|
| Pivot 15m | 24 h | ore 05:15 del primo giorno di warmup | completa all'inizio del mese |
| Pivot 1h | **168 h** | primo giorno di warmup | memoria troncata fino al 4 del mese (ott/nov/dic) |
| Massimo/minimo del giorno precedente | giorno UTC completo | secondo giorno di warmup | completa |
| Massimo/minimo della settimana precedente | settimana completa | **6 ott / 10 nov / 8 dic** | assente nei primi 5–9 giorni del mese |
| Massimo/minimo del mese precedente | mese completo | **1 nov / 1 dic / 1 gen** (nel tail) | **mai disponibile** nel mese valutato |

**Conferme toccate.**
- Pivot 1h troncati: 1 (ott), 1 (nov), 2 (dic).
- Livelli settimanali assenti: 1, 7 e 3.
- Livelli mensili assenti: tutte e 64.

**Call toccate.** Solo la 7 (12-01: pivot 1h troncati e settimana assente) e la 8 (12-05: settimana assente). Bound DERIVED, descrittivo; la logica dei landmark non è stata rieseguita:
- **call 7**: delle 3.292 barre reali in [24-11 17:08, 27-11 00:00), mai ammesse nella run, nessuna ha scambiato nell'intervallo emissione–target [83825,0; 84937,9]. Quel periodo stava tra 86057,4 e 90664,4;
- **settimana precedente** [24-11, 01-12), completa con 10.080 barre: massimo 93133,9, minimo 85217,9. È fuori dagli intervalli emissione–target delle call 7 e 8.

Nessun pivot 1h o livello settimanale mancante poteva quindi trovarsi tra ingresso e target di queste due call. L'effetto della memoria troncata su altre decisioni, per esempio `AT_OPPOSING_AREA` o le nascite, resta UNAVAILABLE senza replay. Per ottobre il bound pre-warmup è UNAVAILABLE: la cache sorgente di settembre non è stata copiata.

## Tail del 1° gennaio 2026 (00:00–06:05 UTC)

**Dati ammessi.** Entrambe le run di dicembre (v0.4 e v0.3) hanno ammesso solo:
- 365 barre trade 1m, 365 mark e 365 index del 1° gennaio, dalla sorgente `okx-…-20260101T0000-20260101T0605-995eade7b222`;
- nessun evento di funding.

Il cursore finale corrisponde a 2026-01-01T06:05.

**Contributo agli esiti esaminati.**
- **Zero** record decisionali nel tail: nessuno scenario, tentativo d'ingresso, call, revisione o material change.
- Nessun path di una call del mese risolto nel tail.
- Nessuno scenario del mese terminato nel tail.
- Nel tail sono stati pubblicati solo landmark (compresi `PREV_1MO` di dicembre), osservazioni e MarketView. Nessuna decisione del mese li usa.
- **Unico contributo:** 3 campioni di vista (31-12 21:00/22:00/23:00) hanno l'esito a 4 h nel tail. Uno è direzionale (21:00 DOWN condizionale, esito UP); due sono astensioni. Lo stesso vale per la baseline.

**Conclusione sul tail.** Gennaio–agosto 2026 non è stato toccato oltre questa finestra di 6 h 05. Le statistiche di vista a 4 h di dicembre includono 3 campioni misurati con prezzi del 1° gennaio. Nessun esito di call o conferma qui esaminato usa dati 2026. Non c'è motivo, da questi record, di dichiarare contaminati gli otto mesi protetti; resta esposta solo la finestra del 1° gennaio 00:00–06:05.

## Ipotesi alternative

**1. Debolezza dello scenario: non supportata come spiegazione generale.**
- Le conferme A raggiungono la destinazione B in 43/64 casi.
- L'invalidazione colpisce soprattutto il sottoinsieme entrato: 7 casi su 9.

**2. Re-anchoring (MP-003): non distinguibile come causa delle perdite.**
- 9 call su 10 esistono grazie alla sostituzione, comprese entrambe le call a target.
- Il tasso strutturale di arrivo a B è uguale con e senza sostituzione (29/43 e 14/21).
- L'unica call sul primo anchor (12-25) perde anche nella baseline v0.3.
- La sostituzione aumenta il volume di WAIT, non peggiora gli scenari osservabili.

**3. Stop stretti: non supportata come meccanismo principale.**
- Distanza dallo stop all'emissione: 0,28–1,35 S15, pari a 1,1–5,4 volte la mediana del range 1m dei 60 minuti precedenti. Non separa vincenti (2,5 e 5,4 volte) da perdenti (1,1–5,3 volte).
- Sulle 7 call fermate, HORIZON_ONLY dà in somma −2,30 % contro −2,63 %, e 5 su 7 restano negative all'orizzonte. Lo stop di solito non tagliava un movimento recuperabile.
- Eccezione: la call 8 (+0,94 % all'orizzonte, stop entro il primo minuto).
- Su tutte e 10 le call HORIZON_ONLY è peggiore di PRIMARY (−1,98 % contro −1,31 %).

**4. Geometria e target vicini alla conferma.**
- Spiegano gran parte delle **mancate call**: 26 WAIT finite lato target prima del ritorno, 17 terminali alla conferma, ritracciamenti richiesti mediani ≈ 24 bps.
- Non spiegano il segno dell'esito delle call entrate.

**5. Fruibilità.**
- Le prime finestre d'ingresso durano 1–9 minuti (mediana 2,5).
- Due stop arrivano entro 1 minuto dall'ingresso PRIMARY.
- È un limite pratico reale per un umano. Non spiega le perdite: le sensibilità 0 s e 120 s danno quasi la stessa somma (−1,30 % e −1,20 %).

**6. Mancanza di analisi ciclica: non verificabile.**
- Il profilo dichiara i cicli predittivi `NOT_COVERED`.
- Nessun record consente di attribuire o escludere un effetto.
- Contesto e fase osservati non separano vincenti da perdenti: tutte le call hanno contesto 1h allineato.

**7. Warmup e tail: esclusi per le call** (vedi sopra). Restano possibili, ma non misurabili, effetti sulle conferme dei primi giorni.

## Conclusione: un meccanismo supportato

**Selezione del ritorno.**

Con target conservativo vicino e rapporto 1,2 fisso, la regione economica di una WAIT è la parte del corridoio vicina alla reazione R. L'ingresso RETURN avviene quindi solo quando, dopo la conferma, il prezzo ritraccia in profondità verso V. Nei record questo ritracciamento seleziona proprio gli scenari che poi falliscono:

| Gruppo | Scenari terminati per V_CONTACT |
|---|---|
| WAIT con ritorno usabile | **7/9** |
| WAIT senza ritorno | 3/37 |
| Terminali alla conferma | 6/17 |

Gli scenari confermati arrivano a B in 43/64 casi in generale, ma solo in 2/9 dopo un ritorno usabile. Le perdite non sono recuperate tenendo la posizione senza stop. Non dipendono dal ritardo d'esecuzione né dall'anchor sostituito.

**Limiti.**
- Il campione è di 9 call RETURN entrate, su tre mesi di sviluppo ora esposti.
- Parte dell'effetto è meccanica: un prezzo vicino a V lo tocca più facilmente. I record non separano "il ritorno segnala il fallimento" da "il ritorno avvicina il prezzo allo stop"; HORIZON_ONLY ne attenua ma non elimina il peso.
- Non è dimostrabile che un ingresso diverso, per esempio immediato, sarebbe stato redditizio: servirebbe un controfattuale, non autorizzato.
- Il funding non è coperto.

**Controevidenze.**
- 2 delle 9 entrate RETURN hanno raggiunto il target: +0,38 % e +0,84 %, che rendono ottobre positivo.
- 3 WAIT senza ritorno sono comunque finite per V_CONTACT.
- La call 8 si sarebbe ripresa all'orizzonte.
- La profondità del ritorno nel corridoio non separa vincenti e perdenti: 0,5 e 0,9 dal lato R per le vincenti, 0,15–0,85 per le perdenti.

Nessun parametro o nuova regola è proposto o implementato.

## Campi mancanti (UNAVAILABLE)

- Esiti di regole o ingressi alternativi (controfattuale).
- Ordine intrabar dentro il minuto.
- Landmark che la run avrebbe pubblicato da storia pre-warmup: è dato solo un bound di prezzo.
- Bound pre-warmup per ottobre (cache di settembre non copiata).
- Funding e total net.
- Copertura di news e calendario (`NONE_UNKNOWN`).
- Campioni di ritorno minuto per minuto STORED: sono DERIVED e validati sui cambi di blocker.
- Stato di `validation_outcome` dell'API: per la comparabilità è usato lo stato di assurance del replay.

READY FOR DIRECTOR REVIEW — WP-012 OWNER Q4 DIAGNOSIS ONLY
