# Stato del nuovo progetto

Aggiornato: 2026-10-16. Responsabile: Director.

## Fatto

UI-001 e R1-A/B/C approvati tecnicamente. UI-002 fasi A e B consegnate a b9282a1 e 9c5f315ca84b4700a4dea1b7de618306331723a5, ora **ACCEPTED tecnicamente dal Director**.

Strumenti: Vite 6.4.4, Vitest/mocker 4.1.11, tinypool rimosso. Navigazione superiore al posto della sidebar, contenuto più largo e pannello scenari richiudibile. Differenza dal Figma richiesta e autorizzata da Gian. Provider, contratti, contabilità e semantica dei comandi invariati.

Review indipendente UI-002: installazione pulita, 16 test UI e typecheck/build riusciti; audit senza filtri a zero su 203 dipendenze; versioni risolte controllate; lettura codice e due immagini dell'esecutore. I 45 test fase A e le prove Chrome a 1680/1366/900 sono evidenze di Claude, non prove browser del Director. Review completa in current_task.md.

## Mancante e prossimo passo

Gian ha confermato l'avvio della versione precedente tramite npm ci / npm run dev. Atteso il suo riscontro sulla nuova navigazione e sui controlli principali. **Macrofase UI ancora aperta.** Nessun nuovo incarico esecutivo; niente ulteriori rifiniture automatiche.

Avvio nuovo layout: dashboard/, npm ci, npm run dev, http://127.0.0.1:5173. Provare Storico/Conto, apertura/chiusura Scenari simulati e Stop totale senza chiudere la posizione.

## Limiti

Tutto è simulato e locale. Pannello aperto aumenta l'altezza della barra fissa; richiudibile. Nessuna UI telefono dedicata. Screenshot 01/02/r2 attuali, altri storici con sidebar dichiarati nel README.
Avviso allowScripts esbuild distinto dagli advisory: prove Windows dell'esecutore funzionanti senza approvare lo script, nessuna modifica globale npm. Browser indipendente Director non eseguito per limite Chromium già dichiarato.

## Vincoli

Banner permanente di simulazione locale. Nessun dato reale, algoritmo, acquisizione, backtest, accesso Owner/exchange, ordine esterno o apertura protetta. DESIGN-001 NON APPROVATO/INATTIVO; studi precedenti INACTIVE. PRODUCT-CONTEXT unico riferimento funzionale.
