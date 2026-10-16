# Stato del nuovo progetto

Aggiornato: 2026-10-16. Responsabile: Director.

## Fatto

**Macrofase UI simulata CONCLUSA.** UI-001, R1 e UI-002 accettati; Gian conferma il nuovo layout e la prova d'uso con “si controllato e sembra tutto ok!” il 16 ottobre. Non è una verifica esaustiva di ogni transizione né una validazione finanziaria.

Codice consegnato: 9c5f315ca84b4700a4dea1b7de618306331723a5. Dashboard locale React/TypeScript, provider simulato separato, scenari deterministici, contratti di presentazione, call/ordini/posizione distinti, conferme vincolate al contesto e gestione feed non corrente. Navigazione superiore approvata dall'Owner; pannello scenari richiudibile.

UI-002 verificato indipendentemente: installazione pulita, 16 test UI, typecheck/build e audit senza filtri a zero; codice e due immagini esaminati. Test completi fase A e prove Chrome a tre larghezze sono evidenze di Claude; nessuna prova browser indipendente del Director. Review e consegne in current_task.md e storia Git.

## Prossimo passo

Gian vuole iniziare l'algoritmo. **Attesa disposizione Astra per la nuova macrofase**, come previsto a chiusura UI. Nessun incarico esecutivo nuovo. Il Director ha gli obiettivi funzionali, ma DESIGN-001 resta NON APPROVATO/INATTIVO e non autorizza l'implementazione.

Il passaggio deve definire obiettivo e risultato concreto del primo incremento algoritmico, perimetro di studio/implementazione e criteri di chiusura. Il Director tradurrà il mandato nel task unico prima di Claude.

## Limiti e vincoli

UI alimentata esclusivamente da dati fittizi locali; nessun algoritmo decisionale o collegamento exchange. Parametri/prodotto/importi di esempio non sono decisioni di trading.
Nessuna acquisizione, backtest, accesso Owner/exchange, operazione esterna o apertura protetta autorizzata. Studi precedenti INACTIVE.
README documenta avvio, simulazioni, differenze Figma e immagini storiche. PRODUCT-CONTEXT unico riferimento funzionale.
