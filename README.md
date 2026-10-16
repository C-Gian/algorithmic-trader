# Algorithmic Trader

Nuovo progetto BTC di Gian: analisi continua, opportunità motivate e futura gestione automatica, inizialmente in demo.

**Stato attuale:** fondazione documentale, tre utilità Python isolate e una dashboard locale **solo simulata** (UI-001). Non sono presenti algoritmo, collegamento exchange o ordini reali. Nessuna operatività reale autorizzata.

## Da dove partire

| File | A cosa serve |
|---|---|
| [Documento funzionale completo](docs/functional/PRODUCT-CONTEXT.md) | Obiettivo, decisioni, ragioni, storia utile, requisiti e questioni aperte. Si può consegnare da solo a una nuova chat. È la foundation del progetto. |
| [STATE.md](STATE.md) | Situazione effettiva e prossima macrofase da definire |
| [current_task.md](current_task.md) | Unico incarico corrente, scritto da Astra o Director |
| [AGENTS.md](AGENTS.md) | Regole di lavoro, responsabilità e verifiche |
| [CLAUDE.md](CLAUDE.md) | Punto d'ingresso per Claude Code |

Non creare una seconda foundation o un altro file di task parallelo. Il documento funzionale è il riferimento per **che cosa** vogliamo; lo stato dice **che cosa esiste**; il task dice **che cosa fare adesso**.

## Dashboard simulata (UI-001)

Interfaccia React/TypeScript/Vite in [`dashboard/`](dashboard/), fedele al [riferimento Figma](docs/ui/FIGMA-REFERENCE.md). Tutti i dati sono fittizi e generati localmente: nessun backend, database, rete prezzi o exchange. Banner fisso: **SIMULAZIONE LOCALE — nessun collegamento exchange**.

**Avvio su Windows.** Serve Node.js 24 (consigliato; verificato con Node 24.14.1 e npm 11.19.0). Gli strumenti dichiarano compatibili anche le serie 20 e 22, non la 21 né la 23; queste versioni non sono state provate.

```powershell
cd C:\Projects\algorithmic-trader\dashboard
npm ci
npm run dev
```

Durante `npm ci`, npm 11 mostra un **avviso** non bloccante: `npm warn install-scripts … esbuild@0.25.12 (postinstall: node install.js)`. Significa che npm non ha eseguito lo script di installazione di esbuild. Nella prova su Windows `npm ci`, test, build e avvio riescono comunque, quindi non serve approvare lo script né cambiare impostazioni di npm.

Diverso è un **errore**: `npm ci` termina con `npm error`, oppure `npm run dev` o `npm run build` si fermano (per esempio con un messaggio su esbuild). In quel caso non approvare script a caso: copia il messaggio e segnalalo.

Aprire http://127.0.0.1:5173 nel browser. Fermare con Ctrl+C. Altri comandi, sempre dalla cartella `dashboard`: `npm test` (test mirati), `npm run build` (typecheck + build), `npm run preview` (build servita su http://127.0.0.1:4173).

**Dove si trova cosa (layout UI-002).** Non c'è più la barra a sinistra: la navigazione è nella barra in alto, sotto il banner di simulazione, e resta visibile anche scorrendo. Le voci sono Dashboard, Ricerca / Backtest, Storico, Conto, Impostazioni e «Guida ai segnali». Storico e Conto portano alle rispettive sezioni della dashboard; Ricerca / Backtest e Impostazioni mostrano «Non disponibile in questa versione». A destra della barra il pulsante **«Scenari simulati»** apre e chiude il pannello di simulazione, che all'avvio è chiuso. Si chiude con «Chiudi», con Esc o ripremendo il pulsante.

Il **pannello di simulazione** sceglie il checkpoint dello scenario (LONG o variante SHORT), altera il feed simulato (regolare / non aggiornato / disconnesso) e reimposta tutto. È separato dai comandi ordinari (Stop totale, Start, Solo call / Call + esecuzione, Gestione manuale, Uscita parziale, Chiudi posizione), che chiedono conferma e producono solo esiti simulati predeterminati. Ricaricare la pagina torna al checkpoint iniziale «5 · Protezione aggiornata».

Regole della simulazione da conoscere durante la prova:
- **Una conferma vale solo per ciò che mostra.** Se lo stato cambia mentre il dialogo è aperto (checkpoint, reset, feed, un eseguito, bot o modalità), il dialogo si chiude senza eseguire nulla e va riaperto. Finché il dialogo è aperto, il resto della pagina non si può usare.
- **Con feed «Non aggiornato» o «Disconnesso»:**
  - posizione e protezioni sono **ultime note**, con il loro orario;
  - le azioni automatiche del bot sono sospese;
  - Start e ritorno alla gestione automatica restano bloccati e, quando il feed torna regolare, vanno richiesti e confermati di nuovo;
  - Stop totale, gestione manuale e richieste d'uscita restano possibili; un'uscita richiesta resta in attesa e si completa al ritorno del feed.
- **Esecuzione delle uscite:** avviene alla chiusura della candela 45m successiva dello scenario. **Oltre il segmento dello scenario il prezzo fittizio viene mantenuto** (ultima chiusura, un minuto dopo). È una convenzione sintetica, non un prezzo di mercato osservato. Screenshot in [docs/ui/app-screenshots](docs/ui/app-screenshots/): `01`, `02` e `r2-scenari-aperti-1366` mostrano il layout attuale; le altre immagini documentano gli stati con la vecchia barra laterale.

## Come lavoriamo

1. Astra definisce una macrofase con obiettivo e confini.
2. Il Director la gestisce e scrive incarichi completi in `current_task.md`.
3. Quando il task è `READY`, Gian dice a Claude: «Leggi AGENTS.md e current_task.md ed esegui l'incarico attivo».
4. Claude realizza e consegna; il Director revisiona e accetta oppure chiede correzioni.
5. Si torna ad Astra alla chiusura della macrofase o per conflitti sostanziali.

Non è necessario far decidere all'Owner ogni dettaglio tecnico, né chiedere ad Astra conferma per ogni commit.

## Che cosa abbiamo recuperato

Solo aritmetica degli intervalli, arrotondamenti a passi espliciti e hash dei file, con 14 test isolati. Nessuna regola di trading ereditata.

- [Provenienza e comandi per i test delle utilità](docs/provenance/RECOVERY.md).
- [Indice delle fonti](docs/references/SOURCES.md): i dossier rimangono nell'archivio o nella biblioteca esterna, non sono istruzioni del nuovo algoritmo.
- [Memoria dei periodi già esposti e protetti](docs/research/EXPOSURES.md).
- [Vecchio progetto archiviato](https://github.com/C-Gian/algorithmic-trader-archive).

I documenti e test del vecchio progetto non si applicano automaticamente. Nessuna suite generale o CI viene importata solo perché esisteva prima.
