# Stato del nuovo progetto

Aggiornato: 2026-10-16. Responsabile: Director.

## Fatto

Dashboard locale UI-001 consegnata a 939c866 e corretta a b751526476ed9dd3800ce249127ad0814ff43d07. **R1-A/B/C: review tecnica Director PASS.** Rieseguiti 40 test pertinenti e build; esaminate tre immagini aggiornate. I cinque test della contabilità immutata erano passati nella review precedente; 45 test completi e prova Chrome sono evidenze dell'esecutore.

Review R1 completa conservata nella storia di current_task.md al commit b8153351b1ad639fe1141dcbf86f34c1b7d023f1.

## Incarico corrente

**UI-002 — READY:** aggiornamento circoscritto Vite/Vitest per gli advisory confermati. Target vite 6.4.4 e vitest 4.1.11; nessun cambio di strategia, UI o contabilità. Mandato, verifiche e pubblicazione in current_task.md.

Nessuna ulteriore implementazione funzionale richiesta per R1. Prova d'uso Owner ancora mancante; macrofase UI non chiusa. L'Owner può provare già la build b751526 in preview locale su 127.0.0.1:4173, mentre procede la manutenzione.

## Dipendenze e limiti

npm audit riprodotto dal Director: quattro pacchetti segnalati (@vitest/mocker, tinypool, vite, vitest). Fonti primarie e versioni registry consultate. Non liquidare i rilievi come innocui perché devDependencies.

Avviso npm allowScripts di esbuild distinto dalle vulnerabilità. Nessuna approvazione globale di script necessaria se build/test funzionano; in caso di errore serve diagnosi specifica.

La prova browser del Director non è stata completata per mancanza Chromium. Il confronto visivo usa immagini dell'esecutore. Nessuna validazione finanziaria.

## Vincoli

Banner permanente di simulazione locale. Nessun dato reale, algoritmo, acquisizione, backtest, accesso Owner/exchange, ordine esterno o apertura protetta.
DESIGN-001 NON APPROVATO/INATTIVO; vecchi studi INACTIVE. PRODUCT-CONTEXT unico riferimento funzionale.
