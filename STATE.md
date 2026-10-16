# Stato del nuovo progetto

Aggiornato: 2026-10-16. Responsabile: Director.

## Fatto

- Fondazione funzionale e tre utilità isolate, senza importazione del vecchio trader.
- Macrofase UI Figma con dati simulati autorizzata da Astra.
- DESIGN-001 conservato NON APPROVATO e NON ATTIVO.
- Figma fornito dall'Owner e letto dal Director: dashboard, otto stati, tre conferme e componenti locali.
- Contesti dei sottoalberi e screenshot verificati; mappa, stile, anteprime e correzioni in [FIGMA-REFERENCE](docs/ui/FIGMA-REFERENCE.md).
- Contratti, fixture riconciliate, interazioni, verifiche e consegna definiti nel task UI-001.
- UI-001 eseguito da Claude: accesso Figma verificato nel proprio ambiente; dashboard locale in `dashboard/` con provider simulato separato e contratto TypeScript versionato.

## Incarico corrente

**UI-001 — DELIVERED**, in attesa di review del Director e della prova d'uso dell'Owner (percorso nel task). Avvio su Windows nel [README](README.md).

## Che cosa esiste realmente

Documentazione, riferimento Figma, tre utilità Python e una dashboard React/TypeScript/Vite **solo simulata**: percorso LONG con 10 checkpoint, variante SHORT con 2, alterazioni controllate del feed, conferme operative e contabilità riconciliata con l'esempio del task. Nessun algoritmo, dato reale, backend, conto collegato o esecutore exchange. Screenshot dell'app in [docs/ui/app-screenshots](docs/ui/app-screenshots/).

Verifiche dell'esecutore: 28 test Vitest (contabilità, checkpoint, percorso Owner, duplicati, disconnessione, dialoghi), typecheck e build, prova nel browser headless. Review del Director e prova dell'Owner ancora da fare. I 14 test Python delle utilità non sono stati rieseguiti (codice non toccato).

## Decisioni ordinarie esplicitate

Correggere le etichette “Start” ereditate erroneamente dalle varianti Figma e le larghezze che ne troncano il testo; preservare stile/layout. Rendere esplicita simulazione locale e assenza connessione exchange/Telegram. Le fixture lineari LONG/SHORT del task sono esempi, non approvazione del prodotto futures o dei parametri del mockup.

## Vincoli

Banner: “SIMULAZIONE LOCALE — nessun collegamento exchange”.
Nessuna acquisizione, backtest, algoritmo decisionale, accesso Owner/exchange, ordine esterno o apertura protetta.
Vecchi studi INACTIVE; [esposizioni](docs/research/EXPOSURES.md) invariate.
[PRODUCT-CONTEXT](docs/functional/PRODUCT-CONTEXT.md) unico riferimento funzionale.
