# Stato del nuovo progetto

Aggiornato: 2026-10-16. Responsabile: Director.

## Fatto

Dashboard locale UI-001 consegnata a 939c866 e corretta a b751526476ed9dd3800ce249127ad0814ff43d07. **R1-A/B/C: review tecnica Director PASS.** Rieseguiti 40 test pertinenti e build; esaminate tre immagini aggiornate. I cinque test della contabilità immutata erano passati nella review precedente; 45 test completi e prova Chrome sono evidenze dell'esecutore.

Review R1 completa conservata nella storia di current_task.md al commit b8153351b1ad639fe1141dcbf86f34c1b7d023f1.

## Incarico corrente

**UI-002 — IN_PROGRESS (fase A consegnata da Claude: vite 6.4.4, vitest 4.1.11, npm audit 0, 45 test e build ok; fase B in corso), aggiornato su richiesta Owner:** fase A manutenzione circoscritta Vite/Vitest; fase B rimozione sidebar, navigazione superiore e pannello scenari richiudibile. Mandato unico e verifiche in current_task.md. Nessuna modifica di strategia, provider o contabilità.

R1 approvato tecnicamente. Gian conferma npm ci e npm run dev sul proprio PC: l'app sembra funzionare. Non è attestata la verifica completa delle transizioni. Richiesta esplicita di spostare la navigazione in alto per recuperare spazio: deroga autorizzata al layout Figma, resto dello stile conservato. Macrofase aperta fino a review e riscontro sul nuovo layout.

## Dipendenze e limiti

npm audit riprodotto dal Director: quattro pacchetti segnalati (@vitest/mocker, tinypool, vite, vitest). Fonti primarie e versioni registry consultate. Non liquidare i rilievi come innocui perché devDependencies.

Avviso npm allowScripts di esbuild distinto dalle vulnerabilità. Nessuna approvazione globale di script necessaria se build/test funzionano; in caso di errore serve diagnosi specifica.

La prova browser del Director non è stata completata per mancanza Chromium. Il confronto visivo usa immagini dell'esecutore. Nessuna validazione finanziaria.

## Vincoli

Banner permanente di simulazione locale. Nessun dato reale, algoritmo, acquisizione, backtest, accesso Owner/exchange, ordine esterno o apertura protetta.
DESIGN-001 NON APPROVATO/INATTIVO; vecchi studi INACTIVE. PRODUCT-CONTEXT unico riferimento funzionale.
