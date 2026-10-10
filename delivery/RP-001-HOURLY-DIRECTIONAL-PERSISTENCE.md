# RP-001 — Persistenza direzionale 1h → 1h

## 1. Ipotesi e popolazione

Domanda primaria:

Il segno dell’ultima ora completa anticipa il segno della
prossima ora meglio di una direzione costante scelta
esclusivamente nell’esplorazione?

L’unità è ogni cutoff orario UTC previsto nella finestra
dichiarata. La popolazione comprende tutte le ore, incluse
astensioni, indisponibilità e casi senza scenario o call.
Nessuna selezione tramite MarketView, intensità del movimento
o risultato successivo.

## 2. Prezzi, causalità e confini

Si usa il medesimo strumento e ruolo di prezzo della
tabulazione: OKX BTC-USDT-SWAP, prezzo trade, senza mescolare
mark o index.

Indicando con C_t la chiusura della barra oraria completa
che termina a t:

- informazione disponibile al cutoff: C_(t-1) e C_t,
  da barre complete contigue e causalmente disponibili;
- previsione: segno di C_t - C_(t-1);
- esito: segno di C_(t+1) - C_t.

L’endpoint deve essere quello esatto; niente sostituzione
con la prima chiusura successiva, interpolazione o
ricostruzione da barre incomplete.

Per ogni fase con intervallo [inizio, fine), sono utilizzabili
soltanto esiti con endpoint strettamente precedente a fine.
Le ore previste il cui endpoint supera o coincide con quel
confine restano nel registro come BOUNDARY_NOT_SCORED.
Non si riutilizzano endpoint della verifica nell’esplorazione.

La storia precedente all’inizio può servire a costruire la
prima previsione, purché causalmente disponibile; non
aggiunge osservazioni alla popolazione.

## 3. FLAT e dati mancanti

- Differenza positiva: UP; negativa: DOWN; esattamente zero:
  FLAT. Nessuna fascia numerica aggiuntiva.
- Previsione FLAT: astensione della persistenza, conteggiata
  nella copertura; esclusa dal confronto direzionale primario.
- Esito FLAT con previsione direzionale: mancata corrispondenza
  per entrambi i previsori, mantenuta nel denominatore appaiato.
- Input incompleto o indisponibile: PREDICTION_UNAVAILABLE.
- Endpoint incompleto o indisponibile: OUTCOME_UNAVAILABLE.

Si registrano separatamente queste condizioni, anche se
concorrenti. I dati mancanti non diventano FLAT o errori
di previsione.

## 4. Riferimento costante

Nell’esplorazione si contano gli esiti UP e DOWN di tutte
le ore con endpoint valido e interno alla fase, senza
condizionare alla previsione di persistenza.

- Più UP: riferimento sempre UP.
- Più DOWN: riferimento sempre DOWN.
- Parità: riferimento sempre UP, per convenzione
  amministrativa dichiarata.
- Nessun esito direzionale disponibile: esplorazione
  insufficiente; arresto.

Il riferimento viene congelato prima della verifica.
Non viene aggiornato mensilmente o adattato alla frequenza
osservata nella verifica. La sua prestazione esplorativa
è una misura sul campione usato per sceglierlo, non evidenza
indipendente.

## 5. Confronto e incertezza

Il confronto primario comprende le ore in cui la persistenza
è UP/DOWN e l’esito è disponibile, inclusi gli esiti FLAT.
Entrambi i previsori vengono valutati sugli stessi timestamp.

Si riportano soltanto:

- ore previste, ore con previsione direzionale e ore appaiate,
  con esclusioni riconciliate;
- tabella appaiata: entrambi corretti, solo persistenza,
  solo costante, nessuno;
- accuratezze sul medesimo denominatore e differenza:
  Delta = accuratezza persistenza - accuratezza costante.

Unica procedura d’incertezza: bootstrap a blocchi mobili
di 168 ore consecutive, 10.000 ricampionamenti, intervallo
percentile al 95% di Delta.

Si ricampiona la griglia temporale completa, conservando
le maschere di indisponibilità; non si comprimono prima
le sole ore valutabili. Blocchi interamente interni alla
fase, senza collegamento circolare fra fine e inizio;
ultimo blocco ricampionato troncato alla lunghezza richiesta.
Il riferimento resta fisso.

Una settimana è una convenzione preventiva per conservare
dipendenze intragiornaliere e settimanali, non una lunghezza
ottimizzata. Non garantisce protezione da dipendenze più
lunghe o cambiamenti di regime.

Se la durata non consente almeno due blocchi settimanali
non sovrapposti, oppure il ricampionamento produce
denominatori nulli, il risultato resta inconcludente;
non si accorciano i blocchi per ottenere un verdetto.

## 6. Lettura della verifica

- Intervallo al 95% di Delta interamente sopra zero:
  favorevole all’ipotesi, nella popolazione e nel periodo
  verificati.
- Intervallo interamente sotto zero:
  sfavorevole rispetto al riferimento.
- Intervallo che comprende o tocca zero:
  inconcludente.

Un’integrità insufficiente rende il risultato non valutabile.
L’intervallo è un’approssimazione dipendente dalle assunzioni
temporali, non una certificazione universale.

Nessuna di queste categorie implica redditività, qualità
di target o invalidazioni, oppure equivalenza al caso.

## 7. Esplorazione e verifica

L’esplorazione usa i campioni già esposti settembre–dicembre
2025, applicando il confine sopra definito. Non si calcolano
ora frequenze, riferimento o risultati.

La verifica sarà individuata solo attraverso il registro
delle esposizioni, prima di consultarne gli esiti.
Deve avere inizio e fine fissati anticipatamente, senza
arresto opportunistico quando il risultato appare favorevole.

“Non esaminato dal progetto” significa assenza documentata
di consultazione o uso di quel periodo nelle decisioni
del progetto. Non significa indipendenza dalla letteratura,
dalle conoscenze generali sul mercato o dalle scelte
di ricerca già compiute.

La scelta dell’ipotesi avviene inoltre dopo aver visto
i diagnostici esposti: questa cronologia resta dichiarata.

Nessuna finestra viene selezionata qui;
gennaio–agosto 2026 rimane protetto.

## 8. Arresto

Se l’ipotesi non è sostenuta, si registra l’esito e si
arresta questa ricerca. Nessun passaggio automatico ad
altri timeframe, inversione del segnale, filtri, sottogruppi,
soglie o prolungamenti della verifica.

Il protocollo è pronto da registrare; l’esecuzione resta
inattiva finché non vengono identificati e autorizzati
i confini della verifica. v0.6 rimane congelato.
