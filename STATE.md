# Stato del nuovo progetto

Aggiornato: 2026-10-16. Responsabile: Director.

## Fatto

Dashboard locale simulata UI-001 consegnata a 939c866 e corretta a b751526476ed9dd3800ce249127ad0814ff43d07. Director: review tecnica R1-A/B/C PASS; 40 test pertinenti e build rieseguiti con successo, tre immagini aggiornate esaminate. La contabilità non è cambiata; i suoi cinque test erano passati nella review precedente. I 45 test completi e la prova Chrome sono evidenze dell'esecutore, non prove browser indipendenti del Director.

## Incarico e prossimi passi

UI-001 resta DELIVERED nel complesso: R1 tecnicamente accettato, prova Owner ancora da svolgere. Decisione Director: manutenzione circoscritta degli strumenti Vite/Vitest, senza cambi alla UI/strategia. Incarico successivo da registrare nel task unico.

Prova Owner già possibile con build locale e preview su 127.0.0.1:4173. Nessun algoritmo, dato reale o collegamento exchange.

## Dipendenze

npm audit riprodotto dal Director: quattro pacchetti segnalati; target verificati vite 6.4.4 e vitest 4.1.11. Avviso esbuild allowScripts distinto dagli advisory: nessuna approvazione globale di script richiesta per una build che funziona. Dettagli e fonti nella review del task.

## Vincoli

DESIGN-001 NON APPROVATO e NON ATTIVO. Vecchi studi INACTIVE. Nessuna acquisizione, backtest, algoritmo, accesso Owner/exchange, ordine esterno o apertura protetta. PRODUCT-CONTEXT unico riferimento funzionale. Macro fase UI non ancora chiusa.
