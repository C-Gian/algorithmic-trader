# Diagnosi trasversale Owner ottobre–dicembre 2025 (v0.4) — sola lettura

Data: 2026-10-07. Incarico Owner: diagnosi trasversale in sola lettura delle tre valutazioni v0.4, con le baseline v0.3 come confronto dei record. È evidenza dell'executor, **non accettazione del Director**. Nessun replay, backtest, Deep validation, run controfattuale, download, modifica di prodotto/schema/metodo/dati o azione sullo stack Owner.

**Stato dei tre mesi.** Ottobre, novembre e dicembre 2025 sono ora **sviluppo esposto**. Non vanno più usati come verifica intatta per revisioni future.

> **ERRATUM — correzione del 2026-10-07 alla consegna `091df18`** (review Astra). La versione precedente resta nella storia Git. Gli artefatti sono stati rigenerati dagli **stessi export** (snapshot sha256 `44c5dbc2…e094`), senza nuova estrazione. Correzioni:
> 1. Il confronto 7/9 contro 3/37 è ora presentato come **associazione descrittiva** fra percorsi classificati da eventi successivi alla conferma, con terminali concorrenti. Non è un effetto causale del RETURN né una prova della bontà generale degli scenari. La conclusione "un meccanismo supportato" è **ritirata**.
> 2. Il ritorno nel corridoio strutturale è distinto dall'ulteriore restrizione economica, che varia per profondità. Il controesempio del 31 ottobre è conservato.
> 3. Le esclusioni su ritardo e stop sono ritirate. Le sensibilità hanno denominatori diversi, e HORIZON_ONLY cambia l'intera politica d'uscita. Le call del 23 novembre e del 5 dicembre hanno entrambe un endpoint HORIZON_ONLY positivo.
> 4. Il re-anchoring non è più dichiarato economicamente innocuo. Il gruppo senza sostituzione può includere revisioni, e proporzioni simili non provano equivalenza.
> 5. L'esclusione del warmup per le call è ritirata. **Tutte** le call mancano dei livelli del mese precedente. I bound sui prezzi non ricostruiscono zone, pubblicazione, rottura o decisioni. La completezza della memoria dei pivot dopo `warmup_start + 168 h` non è certificata (campo rinominato `pivot_1h_lookback_starts_before_warmup`).
> 6. Destinazione B, target della call, scenario, guidance e percorso ipotetico restano distinti.
> 7. I totali sono ora calcolati a precisione piena e arrotondati solo per la presentazione. Il precedente −1,307 % era la somma delle percentuali per path già arrotondate a 3 decimali; il valore corretto è ≈ −1,308 %.
> 8. Tutte le distanze "dal close" usano ora il close come denominatore, e i campi sono rinominati `*_bps_of_close`. Prima, la distanza dal target per gli SHORT e le distanze da V e dal bordo economico per i LONG usavano l'altro prezzo come denominatore.

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
| **Totale** | **64** | **46** | **10** | **9** | somma price-net normalizzata **≈ −1,308 %** (ott +1,083; nov −0,887; dic −1,504) |

**Totale price-net.**
- Somma esatta dei 10 valori PRIMARY STORED, a precisione piena: **−0,0130817434351891232589748454948995…**. La somma esatta dei valori per famiglia dei tre report (−0,013081743435189123258974845495) coincide con questa fino alla 28ª cifra decimale. I valori dei report sono somme del builder a 28 cifre significative.
- Il valore indicato nella review, −0,01308174343518912325907484550, coincide con questa somma fino alla 21ª cifra decimale. Differisce di 1,0×10⁻²² alla 22ª: il record dà …258974…, il valore indicato …259074…. Non riesco a riprodurre quella differenza dai record (export dei report Owner non disponibile qui). La segnalo invece di forzare l'uguaglianza.
- In percentuale entrambi danno −1,308174 %.
- È una **somma di esiti ipotetici normalizzati** (unità N0 = 1), non un rendimento di conto: niente capitalizzazione, niente sizing, funding escluso.
- Origine del precedente −1,307 %: somma delle percentuali per path già arrotondate a 3 decimali (`tabulations.path_variant_sums_pct` in `091df18`). Ora quel campo è `path_variant_sums`, a precisione piena.

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

**Esiti distinti.**
- **Scenario**: esito strutturale. Contatto con la destinazione narrativa B, oppure con V, o scadenza/stallo.
- **Target della call**: `T`, il bordo vicino della zona del landmark limitante. È diverso da B: arrivare a B non coincide con raggiungere il target, e nessuno dei due coincide con un profitto.
- **Guidance**: lo stato della tesi della call (TARGET_REACHED, INVALIDATED, TIME_EXPIRED).
- **PRIMARY e sensibilità**: percorsi ipotetici normalizzati del valutatore. Nessun ordine né fill.

**Sensibilità.**
- Denominatori: PRIMARY, 0 s e HORIZON_ONLY coprono 10 path su 10; 120 s ne copre 9, più 1 NO_ENTRY (12-05).
- HORIZON_ONLY sostituisce l'**intera** politica d'uscita: niente target, niente guidance di stop, uscita all'orizzonte. Non è un controfattuale del solo stop.

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

**Confronto con v0.3 (STORED).** Per 9 call su 10 lo scenario v0.3 nato sullo stesso bordo 15m e nella stessa direzione era terminato prima della conferma per V_CONTACT, senza call. In v0.4 questi 9 owner hanno confermato su un anchor sostituito dopo un contatto (REARM), con eventuali revisioni successive. La provenienza di ogni anchor è in `anchors_STORED`: barra sorgente, pubblicazione, cursore, intervallo d'invalidazione. La call 10 (12-25, epoch 1) è identica nella baseline v0.3 di dicembre, ed è anch'essa uno stop.

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
**Ritorno nel corridoio e restrizione economica (DERIVED).**
- Ritornare nel corridoio strutturale R–K non basta. Il predicato economico a costo fisso (14 bps, rapporto 1,2) restringe la parte usabile a una quota variabile del corridoio.
- Quota economica alla conferma, sulle 46 WAIT: da 0,00 a 1,00, mediana ≈ 0,37.
- 32 WAIT su 46 hanno avuto almeno una chiusura campionata nel corridoio. Solo 9 hanno avuto una chiusura nella regione economica: sono esattamente le 9 entrate. Le altre 23 sono tornate nel corridoio senza mai chiudere nella parte economica.
- Ritracciamento richiesto dalla chiusura di conferma al bordo economico, in bps del close: da 5,2 a 70,7, mediana ≈ 23,8.
- La profondità varia anche fra le entrate:
  - quota economica 0,24–1,00;
  - ritracciamento richiesto 5,2–40,1 bps del close.
- **Controesempio 31 ottobre (call 4):** tutto il corridoio era economico (quota 1,00) e il ritracciamento richiesto era di soli 9,3 bps; il ritorno è stato poco profondo e la call ha raggiunto il target. Anche la call 1 (10-06: quota 0,56, 11,2 bps) è arrivata a target. Il ritorno non è dunque sempre "profondo verso V".

**Esito strutturale dello scenario dopo la conferma (STORED), per gruppo.** I gruppi sono definiti da eventi successivi alla conferma.

| Gruppo | Destinazione B | V_CONTACT | Scadenza dura | STALLED |
|---|---:|---:|---:|---:|
| WAIT **con** ritorno usabile (= 9 call RETURN entrate) | 2 | **7** | 0 | 0 |
| WAIT **senza** ritorno usabile (37) | **30** | 3 | 3 | 1 |
| Terminale alla conferma (17) | 11 | 6 | 0 | 0 |
| IMMEDIATE (1) | 0 | 0 | 1 | 0 |
| **Tutte le 64** | **43** | 16 | 4 | 1 |

**Come leggere questa tabella.** È un'**associazione descrittiva**, non un effetto causale.
- I gruppi "con" e "senza" ritorno usabile sono definiti da eventi successivi alla conferma, e i terminali sono concorrenti.
- Una WAIT finisce al primo fra: ritorno usabile, contatto lato target (cap o destinazione B), contatto con V, restrizione di contesto, scadenza. Un percorso che arriva prima dal lato del target **non può** entrare per costruzione nel gruppo con ritorno; per questo il gruppo senza ritorno è arricchito di destinazioni B.
- Il "43/64 a B" descrive lo scenario strutturale, non la bontà generale degli scenari né il target o il profitto di una call.

**Storia dell'anchor (STORED).**
- Due gruppi:
  - confermati dopo una sostituzione (REARM dopo contatto): B raggiunta in 29 casi su 43;
  - senza sostituzione dopo contatto, gruppo che **può includere revisioni** (REVISE senza contatto): B raggiunta in 14 casi su 21.
- Proporzioni simili non provano equivalenza né rendono innocuo il re-anchoring: il campione è piccolo e i gruppi non sono confrontabili per costruzione.
- L'instradamento differisce:
  - dopo una sostituzione: 37 WAIT e 1 IMMEDIATE su 43;
  - senza sostituzione: 9 WAIT su 21 e 12 terminali alla conferma.

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
| Pivot 1h | **168 h** | primo giorno di warmup | finestra troncata nota fino al 4 del mese (ott/nov/dic); dopo, completezza **non certificata** |
| Massimo/minimo del giorno precedente | giorno UTC completo | secondo giorno di warmup | completa |
| Massimo/minimo della settimana precedente | settimana completa | **6 ott / 10 nov / 8 dic** | assente nei primi 5–9 giorni del mese |
| Massimo/minimo del mese precedente | mese completo | **1 nov / 1 dic / 1 gen** (nel tail) | **mai disponibile** nel mese valutato |

**Conferme toccate.**
- Finestra pivot 1h che inizia prima del warmup: 1 (ott), 1 (nov), 2 (dic).
- Livelli settimanali assenti: 1, 7 e 3.
- Livelli del mese precedente assenti: **tutte e 64**.

`warmup_start + 168 h` segnala solo un troncamento **noto**. Non certifica che dopo quella data la memoria dei pivot sia completa: formazione, pubblicazione, rottura, ritiro e limite per orizzonte non sono ricostruiti qui.

**Call toccate: tutte e 10.**
- A nessuna call erano disponibili i livelli del mese precedente.
- La call 7 (12-01) aveva in più la finestra pivot 1h troncata e la settimana precedente assente; la call 8 (12-05) la settimana precedente assente.

**Bound descrittivi (DERIVED), solo per le call 7 e 8.**
- **Call 7**: nessuna delle 3.292 barre reali in [24-11 17:08, 27-11 00:00), mai ammesse nella run, ha scambiato nell'intervallo emissione–target [83825,0; 84937,9]. Quel periodo è rimasto fra 86057,4 e 90664,4.
- **Settimana precedente** [24-11, 01-12): massimo 93133,9, minimo 85217,9. Il prezzo è fuori dagli intervalli emissione–target delle call 7 e 8.
- Questi bound **non** ricostruiscono zone (semiampiezze), pubblicazione, rottura, ritiro o decisioni. Non escludono quindi un effetto del warmup: né sul target o sul cap, né su `AT_OPPOSING_AREA`, nascite o instradamento.

**Conclusione sul warmup.** Un effetto del contesto iniziale ridotto **non è escluso** per nessuna call né conferma, e resta UNAVAILABLE senza replay. Il bound pre-warmup di ottobre è UNAVAILABLE: la cache sorgente di settembre non è stata copiata.

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

## Ipotesi alternative (nessuna esclusa dai record)

**1. Debolezza dello scenario: non valutabile in generale da questi gruppi.**
- B è stata raggiunta in 43 conferme su 64 e V contattata in 16, ma è un esito strutturale, con terminali concorrenti. Non misura la bontà generale degli scenari né il target o il profitto di una call.
- Dopo un ritorno usabile, 7 scenari su 9 sono terminati su V. È coerente con una debolezza dello scenario quanto con un effetto del punto d'ingresso.

**2. Selezione del ritorno: associazione descrittiva, causalità non identificata.**
- V è stata contattata in 7 casi su 9 con ritorno usabile, contro 3 su 37 senza.
- I gruppi però sono definiti da eventi post-conferma con terminali concorrenti. Chi raggiunge prima il lato target è escluso per costruzione dal gruppo con ritorno.
- Il ritorno nel corridoio (32/46) non coincide con la restrizione economica (9/46). La profondità richiesta varia; il 31 ottobre un ritorno poco profondo ha raggiunto il target.

**3. Re-anchoring (MP-003): non dichiarabile né causa né innocuo.**
- 9 call su 10 vengono da owner confermati dopo una sostituzione, comprese le due a target. La provenienza è in `anchors_STORED`.
- Il confronto 29/43 contro 14/21 (gruppo che può includere revisioni) non prova equivalenza.
- L'unica call senza sostituzione (12-25) è uno stop anche in v0.3.

**4. Stop stretti e geometria dell'uscita: non esclusi.**
- Distanza dallo stop all'emissione: 0,28–1,35 S15, cioè 1,1–5,4 volte la mediana del range 1m dei 60 minuti precedenti. Non separa vincenti (2,5 e 5,4) da perdenti (1,1–5,3); con n = 10, non è un'esclusione.
- HORIZON_ONLY cambia **tutta** la politica d'uscita (niente target, niente stop guidance), quindi non isola lo stop.
- Sulle 7 call fermate dà in somma −2,298 % contro −2,630 % di PRIMARY, e **due** endpoint sono positivi: 23 novembre (+0,045 %) e 5 dicembre (+0,944 %).
- Su tutte e 10 le call HORIZON_ONLY dà −1,982 % contro −1,308 % di PRIMARY, soprattutto perché rinuncia ai due target.

**5. Geometria alla conferma (target vicino, regione economica ristretta).**
- È associata alla maggior parte delle **mancate call**: 26 WAIT finite lato target prima di un ritorno usabile, 17 terminali alla conferma, ritracciamento richiesto mediano ≈ 23,8 bps del close.
- Il suo ruolo negli esiti delle call entrate non è identificato.

**6. Fruibilità e ritardo: non esclusi.**
- Le prime finestre d'ingresso durano 1–9 minuti (mediana 2,5).
- Due stop arrivano entro 1 minuto dall'ingresso PRIMARY.
- Sensibilità sul ritardo:
  - 0 s: −1,295 % su 10 path;
  - 120 s: −1,200 % su **9** path (1 NO_ENTRY).
- I denominatori differiscono, e le sensibilità registrate coprono solo 0 e 120 s di ingresso. Non escludono il ritardo umano reale né altri tempi di reazione.

**7. Mancanza di analisi ciclica: non verificabile.** I cicli predittivi sono `NOT_COVERED`. Contesto 1h e fase osservati non separano vincenti e perdenti: tutte le call hanno contesto allineato.

**8. Contesto iniziale (warmup): non escluso**, vedi sopra. **Tail:** nessun contributo a decisioni o esiti esaminati; la conclusione è separata e circoscritta.

## Conclusione

**Ipotesi diagnostica sul RETURN; meccanismo causale non identificato.**

I record mostrano un'associazione descrittiva: le WAIT con un ritorno economicamente usabile sono terminate per contatto con V molto più spesso (7/9) delle WAIT senza ritorno (3/37).

| Gruppo (definito da eventi post-conferma) | Scenari terminati per V_CONTACT |
|---|---|
| WAIT con ritorno usabile | 7/9 |
| WAIT senza ritorno usabile | 3/37 |
| Terminali alla conferma | 6/17 |

Il confronto è viziato per costruzione dai terminali concorrenti. Non separa:
- l'informazione del ritorno sullo scenario;
- la vicinanza meccanica a V;
- la geometria del target e dello stop;
- il contesto iniziale ridotto;
- la sostituzione dell'anchor.

Il campione è di 9 call RETURN entrate, su tre mesi di sviluppo ora esposti, senza controfattuale autorizzato e senza funding.

**Controevidenze.**
- Due entrate RETURN hanno raggiunto il target (10-06 +0,378 %, 10-31 +0,843 %). Il 31 ottobre era un ritorno poco profondo, su un corridoio interamente economico.
- 3 WAIT senza ritorno sono finite comunque su V.
- Due stop hanno endpoint HORIZON_ONLY positivo (11-23, 12-05).
- La profondità del ritorno non separa gli esiti.

Il dossier **non autorizza** una nuova regola né un parametro, e non ne propone.

## Campi mancanti (UNAVAILABLE)

- Esiti di regole o ingressi alternativi (controfattuale).
- Ordine intrabar dentro il minuto.
- Landmark, zone e decisioni che la run avrebbe prodotto con un contesto iniziale più lungo: sono dati solo bound di prezzo descrittivi.
- Bound pre-warmup per ottobre (cache di settembre non copiata).
- Funding e total net.
- Copertura di news e calendario (`NONE_UNKNOWN`).
- Campioni di ritorno minuto per minuto STORED: sono DERIVED e validati sui cambi di blocker.
- Stato di `validation_outcome` dell'API: per la comparabilità è usato lo stato di assurance del replay.

READY FOR DIRECTOR REVIEW — WP-012 OWNER Q4 DIAGNOSIS CORRECTION ONLY
