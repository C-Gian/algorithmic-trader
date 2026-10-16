# Stato del nuovo progetto

Aggiornato: 2026-10-16. Responsabile: Director.

## Fatto

Macrofase UI simulata CONCLUSA e approvata dall'Owner; chiusura a baa1e762703f7dfd01f870061dba2a1c691326ce. Dashboard React/TypeScript esistente, provider simulato separato, navbar superiore e conferme revisionate.

Astra ha autorizzato la macrofase completa “osservazioni calcolate e primo studio storico nell'app”. **DESIGN-001 approvato solo per definizioni osservative §§5–6**, con warmup per singola misura corretto nel task; resto non attivato.

## Incarico corrente

**OBS-001 — DELIVERED da Claude, in attesa di review del Director e prova di Gian.** Consegna completa nel task. Sintesi:
- **Motore Python** a sola libreria standard (`src/obs001`). Convenzioni congelate in `config/OBS-001-v1.json` (hash `3c4eb884…2387`), registrate e pubblicate prima di dati ed esiti.
- **Dati reali.** Sette ZIP Binance Vision, BTCUSDT perpetual klines 1m da giugno a dicembre 2025. Checksum e identità dello strumento verificati; 308.160/308.160 minuti validi, nessuna anomalia. File fuori Git in `C:\Projects\algorithmic-trader-data\OBS-001`.
- **Run.** `OBS-001-v1-e1.0.1-40a13e10ac-3c4eb884d0`: 3.904 origini, 31 censurate, partizioni riconciliate, bundle riproducibile.
- **Dashboard.** Ambiente «Studio storico» distinto dalla simulazione:
  - vista causale al cutoff t;
  - sei famiglie a 45m e 1D;
  - revisioni per available_at;
  - seguito 24h solo su comando;
  - riepilogo sotto «Studio osservativo».
  Nessun conto, call o ordine nello storico.
- **Risultati.** Nel report `docs/research/OBS-001-results.md`. Entro lo stesso verso 45m, le differenze fra 1D concorde, contraria e mista sono piccole rispetto alla dispersione e cambiano segno fra i mesi; alcune celle sono scarse. Nessuna conclusione causale.

Verifiche dichiarate dall'esecutore, non ancora riesaminate:
- 30 test sintetici del motore;
- riscontro indipendente sul bundle reale;
- 61 test frontend, typecheck e build;
- prova in Chrome headless sul bundle reale.

## Studio e chiusura

Tutte le chiusure45m: confronto entro stessa struttura45m UP/DOWN fra giornaliero concorde/contrario/misto/assente; riepilogo sola45m, mesi e distribuzioni final/up/down24h in A45m all'origine. Popolazione completa e censure, nessuna indipendenza delle righe presunta.

Chiusura richiede storico reale/observe nell'app, riproducibilità/causalità, confronto previsto e prova Gian con review Director. Risultati contrari o insufficienti sono validi.

## Vincoli

Nessuna strategia di ingresso, ordine exchange, valutazione economica, capitale/leva, acquisizione fuori mandato, apertura2026protetto o riattivazione vecchi studi. Nello storico niente call/posizioni/saldi fittizi. Simulazione locale separata. PRODUCT-CONTEXT aggiornato al mandato.
