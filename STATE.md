# Stato del nuovo progetto

Aggiornato: 2026-10-16. Responsabile: Director.

## Fatto

- Fondazione funzionale e tre utilità isolate, senza importazione del vecchio trader.
- Macrofase UI Figma con dati simulati autorizzata da Astra.
- DESIGN-001 conservato NON APPROVATO e NON ATTIVO.
- Figma fornito dall'Owner e letto dal Director: dashboard, otto stati, tre conferme e componenti locali.
- Contesti dei sottoalberi e screenshot verificati; mappa, stile, anteprime e correzioni in [FIGMA-REFERENCE](docs/ui/FIGMA-REFERENCE.md).
- Contratti, fixture riconciliate, interazioni, verifiche e consegna definiti nel task UI-001.

## Incarico corrente

**UI-001 — READY.** Claude deve prima verificare accesso effettivo al progetto Figma nel proprio ambiente. L'accesso del Director è verificato; quello dell'esecutore ancora no. Se il gate riesce, procede direttamente con implementazione/review di consegna; se non riesce segnala BLOCKED con motivo preciso, senza ricostruire arbitrariamente la UI.

Frontend React/TypeScript/Vite con provider simulato separato. Nessun backend/DB/auth/connettore. Commit/push pertinenti dell'esecutore autorizzati nel task; Gian sincronizza il checkout prima dell'incarico.

## Che cosa esiste realmente

Documentazione, riferimento Figma e tre utilità Python. Nessuna dashboard implementata, nuovo algoritmo, conto collegato o esecutore exchange. Le anteprime sono Figma, non screenshot di un'app realizzata. Nessuna verifica applicativa o prova Owner ancora effettuata.

I 14 test delle utilità appartengono alla migrazione, non sono stati rieseguiti per documentazione/design. Review visiva dell'app ancora da fare.

## Decisioni ordinarie esplicitate

Correggere le etichette “Start” ereditate erroneamente dalle varianti Figma e le larghezze che ne troncano il testo; preservare stile/layout. Rendere esplicita simulazione locale e assenza connessione exchange/Telegram. Le fixture lineari LONG/SHORT del task sono esempi, non approvazione del prodotto futures o dei parametri del mockup.

## Vincoli

Banner: “SIMULAZIONE LOCALE — nessun collegamento exchange”.
Nessuna acquisizione, backtest, algoritmo decisionale, accesso Owner/exchange, ordine esterno o apertura protetta.
Vecchi studi INACTIVE; [esposizioni](docs/research/EXPOSURES.md) invariate.
[PRODUCT-CONTEXT](docs/functional/PRODUCT-CONTEXT.md) unico riferimento funzionale.
