# Algorithmic Trader

Nuovo progetto BTC di Gian: analisi continua, opportunità motivate e futura gestione automatica, inizialmente in demo.

**Stato attuale:**
- fondazione documentale e tre utilità Python isolate;
- una dashboard locale con tre ambienti: la **simulazione locale** (UI-001/UI-002), lo **studio storico** OBS-001 su prezzi reali BTCUSDT perpetual di Binance Vision e il **Backtest** del primo candidato CAND-001, che Gian avvia, segue e riapre direttamente dall'app (APP-001: servizio Python locale su 127.0.0.1, un backtest alla volta, solo dati già scaricati).

Non ci sono collegamenti exchange né ordini reali. Il candidato CAND-001 è uno studio di sviluppo, non una strategia validata. Nessuna operatività reale autorizzata.

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

Aprire http://127.0.0.1:5173 nel browser. Fermare con Ctrl+C. Da APP-001 `npm run dev` avvia anche il servizio locale dei backtest (vedi sotto); `npm run dev:ui` avvia solo la pagina. Altri comandi, sempre dalla cartella `dashboard`: `npm test` (test mirati), `npm run build` (typecheck + build), `npm run preview` (build servita su http://127.0.0.1:4173).

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

## Studio storico OBS-001 (dati reali, solo osservazione)

Pipeline Python a sola libreria standard in [`src/obs001`](src/obs001), con convenzioni congelate in [`config/OBS-001-v1.json`](config/OBS-001-v1.json). Lavora così:
1. legge sette ZIP mensili pubblici di Binance Vision (BTCUSDT perpetual USDⓈ-M, klines 1m, da giugno a dicembre 2025);
2. calcola osservazioni causali a 45m e 1D;
3. calcola il seguito a 24h in un modulo separato;
4. scrive un bundle JSON che la dashboard apre da file.

Risultati e lettura sono in [docs/research/OBS-001-results.md](docs/research/OBS-001-results.md).

**Prerequisiti.** Python 3.11 o successivo, senza pacchetti esterni. Su questo PC `python` non è nel PATH, ma `uv` ha già installato `python3.12` (verificato con 3.12.14; il motore passa i test anche con 3.11.16). Il primo passo richiede connessione internet, gli altri no.

**Comandi** (PowerShell, dalla radice del repository):

```powershell
cd C:\Projects\algorithmic-trader
$env:PYTHONPATH = "src"
python3.12 -m obs001 all          # acquisisce, controlla ed elabora (circa 25 secondi)
# oppure i passi separati:
python3.12 -m obs001 acquire      # scarica i 7 ZIP, verifica i checksum, salva metadati e termini
python3.12 -m obs001 check        # controlla hash, schema e copertura dei minuti
python3.12 -m obs001 process      # elaborazione offline: osservazioni, esiti, tabelle, bundle
python3.12 -m obs001 summarize    # rigenera summary.md dall'ultimo bundle
```

**Ripetizione offline.** Dopo il primo `acquire`, `check` e `process` funzionano senza rete. Un nuovo `acquire` riusa gli ZIP locali se il checksum coincide. A parità di input, convenzioni e motore il bundle esce identico byte per byte e non viene sovrascritto. I test sintetici del motore si eseguono con:

```powershell
python3.12 -m unittest discover -s tests -p "test_obs001_*.py"
```

**Dove finiscono i file** (fuori da Git, cartella accanto al repository; si può cambiare con `--data-dir`):

| Cartella | Contenuto |
|---|---|
| `C:\Projects\algorithmic-trader-data\OBS-001\raw\` | ZIP e `.CHECKSUM` |
| `...\meta\` | metadati dello strumento e copia dei termini |
| `...\manifests\` | manifest di acquisizione e degli input, con copie datate |
| `...\runs\OBS-001-v1-e1.0.1-40a13e10ac-3c4eb884d0\` | `obs001-bundle.json`, `run-manifest.json`, `summary.md` |

**Aprire lo studio nella dashboard.** Avviare la dashboard come sopra. Nella barra in alto scegliere **«Studio storico»**, premere **«Apri studio storico»** e selezionare `obs001-bundle.json` dalla cartella del run. Il banner diventa **STORICO REALE — studio osservativo locale — nessun collegamento exchange**.

Che cosa trovi nello storico:
- **Cutoff.** Si sceglie una chiusura 45m (giorno e ora in UTC, frecce o slider). Grafico, osservazioni, livelli, pivot e revisioni mostrano solo ciò che era noto a quel momento.
- **Seguito a 24 ore.** «Mostra seguito retrospettivo 24h» lo rivela, marcato come a posteriori; «Solo informazioni al momento» lo nasconde.
- **Riepilogo.** Le tabelle mensili e totali sono nella voce **«Studio osservativo»**. Gli esempi si aprono nella vista causale.
- **Cosa non c'è.** Posizione, conto, ordini e comandi non esistono in questo ambiente.

Senza bundle l'ambiente chiede di aprirne uno e non mostra prezzi. **«Simulazione locale»** riporta alla demo con un provider nuovo.

Funziona davvero: acquisizione, controlli, osservazioni ed esiti su dati reali. È simulato soltanto l'ambiente demo. Non esistono strategia, segnali operativi, valutazione economica, dati successivi al 2025 o collegamenti live.

## Backtest dall'app (APP-001)

**Un comando** (PowerShell; servono Node.js 24, Python 3.12 e i dati già presenti in `C:\Projects\algorithmic-trader-data\CAND-001`):

```powershell
cd C:\Projects\algorithmic-trader\dashboard
npm run dev
```

Il comando avvia insieme il servizio locale (127.0.0.1:8765) e la pagina web (127.0.0.1:5173). Aprire **http://127.0.0.1:5173/#/backtest**. Il terminale può restare aperto; Ctrl+C chiude solo i due processi avviati da questo comando (un backtest in corso risulterà «interrotto»). Se Python non viene trovato: `$env:APP001_PYTHON = "<percorso di python3.12.exe>"; npm run dev`. Cartella dati diversa: `$env:APP001_DATA_DIR = "<cartella CAND-001>"` oppure `npm run dev -- --data-dir <cartella>`. Porta occupata, dati mancanti o un secondo servizio sulla stessa cartella producono un messaggio e nessuna chiusura di altri programmi. Nessun download: l'app usa solo file già verificati.

**Percorso in pochi clic.**
1. In alto scegli **Backtest** → **Nuovo backtest**.
2. Sulla scheda **«Prova di gennaio 2025»** premi **Avvia**. Il periodo con operazioni è il gennaio 2025; la storia dal 1 ottobre 2022 serve solo a osservare.
3. Segui la progressione reale: controllo dei file, preparazione, simulazione chiusura per chiusura, salvataggio (circa 15 secondi). **«Annulla backtest»** ferma il calcolo; chiudere o ricaricare la pagina non lo ferma e non ne avvia un altro.
4. Al termine premi **Apri risultati**: «Risultato dopo i costi» e da dove viene (movimento dei prezzi, prezzo di esecuzione, commissioni, pagamento periodico).
5. **«Tutte le operazioni (3)»** → clic su una riga → dettaglio: che cosa ha riconosciuto il bot, il tentativo, se è entrato, perché ha chiuso; **«Mostra cosa è successo dopo»** per i costi.
6. **«← Torna alle operazioni»** (o il tasto Indietro del browser), poi **Risultati salvati**: tutti i risultati, anche quelli calcolati prima dell'app, si riaprono senza ricalcolare.

Le icone «i» spiegano i termini al passaggio del mouse, al clic o con il tasto Tab. Ogni vista ha un indirizzo proprio (`#/backtest/...`, `#/historical/...`, `#/simulation/...`): Indietro/Avanti e ricaricamento funzionano anche negli altri ambienti. Un file aperto da «Apri file esterno» (in Risultati salvati) o uno studio storico restano solo in memoria: dopo un ricaricamento l'app chiede di riaprirli e torna alla stessa vista.

**Profili fissi** ([config/APP-001-profiles.json](config/APP-001-profiles.json), separato dalla configurazione del candidato): Prova di gennaio 2025 (collaudo del prodotto, non un nuovo studio), Sviluppo 2023–2024, Confronto 2025 (già esposto). Nessun editor di strategia, date o costi. Le esecuzioni dell'app sono in `...\CAND-001\jobs\<job>\job.json` (stato, avanzamento, provenienza); i risultati restano in `...\CAND-001\runs\`. Stesso calcolo da terminale: `python3.12 -m cand001 run --phase app-check-2025-01` (con `$env:PYTHONPATH = "src"` dalla radice). Collaudo e confronto UI/diretto in [docs/research/APP-001-delivery.md](docs/research/APP-001-delivery.md).

## Backtest di sviluppo CAND-001 (primo candidato, esecuzioni modellate)

Primo candidato completo «movimento → reazione → tentativo di ripresa». Specifica in [docs/research/CAND-001-v1.md](docs/research/CAND-001-v1.md), configurazione congelata in [config/CAND-001-v1.json](config/CAND-001-v1.json), risultati e diagnosi in [docs/research/CAND-001-results.md](docs/research/CAND-001-results.md).

Sono operazioni ipotetiche su prezzi storici, ciascuna da 1.000 USDT di nozionale: non sono un conto, né un'autorizzazione a operare. Due risultati separati, entrambi negativi:
- **sviluppo 2023–2024** (DEV): 78 operazioni, netto modellato −210,59 USDT;
- **confronto aggiuntivo 2025**: 29 operazioni, netto −109,08 USDT. Il 2025 era già stato esaminato in studi precedenti: non è una validazione indipendente.

**Comandi** (PowerShell, dalla radice del repository; serve la connessione solo la prima volta):

```powershell
cd C:\Projects\algorithmic-trader
$env:PYTHONPATH = "src"
python3.12 -m cand001 all      # scarica i dati mancanti (verifica checksum) ed esegue il backtest 2023–2024
python3.12 -m cand001 run      # rifà il backtest offline con i dati già scaricati (circa 25 secondi)
python3.12 -m cand001 all --phase additional2025   # 2025: acquisisce solo i file mancanti e lo elabora
python3.12 -m cand001 run --phase additional2025   # rifà il 2025 offline (circa 25 secondi, bundle identico)
python3.12 -m unittest discover -s tests -p "test_cand001_*.py"   # test sintetici del candidato
```

I dati restano fuori Git, in `C:\Projects\algorithmic-trader-data\CAND-001\` (il 2025 rilegge anche gli archivi già verificati di `...\OBS-001\raw`, senza modificarli). I file per l'app sono:

- 2025: `C:\Projects\algorithmic-trader-data\CAND-001\runs\CAND-001-v1.0.0-e1.0.2-ADDITIONAL_2025-9324c5d179-aed2c4ef62\cand001-bundle.json`
- 2023–2024: `C:\Projects\algorithmic-trader-data\CAND-001\runs\CAND-001-v1.0.0-e1.0.1-DEV-adaa94c502-aed2c4ef62\cand001-bundle.json`

Il run DEV più vecchio `…-e1.0.0-…` resta nella stessa cartella `runs`, ma usa lo schema vecchio e l'app non lo apre più.

**Nell'app.** I risultati 2023–2024 e 2025 compaiono in **Backtest → Risultati salvati** (profilo dedotto dalla fase: sono stati calcolati prima dell'app) e si aprono senza scegliere file. Gli «Esempi dal registro» (prima operazione, primo caso negativo, prima astensione…) sono scorciatoie cronologiche; tutte le operazioni sono in «Tutte le operazioni».

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
