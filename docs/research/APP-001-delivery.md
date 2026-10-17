# APP-001 — consegna: backtest autonomo locale dall'app

Esecutore Claude Code, 17 ottobre 2026. Incarico in `current_task.md` (commit 7f94d4e). Stato: **consegnato con correzioni R1, non accettato**.
Collaudo software, non nuovo studio né verifica della strategia: candidato CAND-001/v1 1.0.0, configurazione `aed2c4ef627617d73972778097bbab5fb702ab5064ce9e6eb68ded2170ce4edf`, regole, osservazioni e costi invariati.

## 1. Che cosa è stato costruito

| Parte | Dove | Comportamento |
|---|---|---|
| Percorso comune | `src/cand001/pipeline.py` | controllo input → aggregati/osservazioni → `run_window` → riepilogo/bundle → pubblicazione. Usato dal comando diretto e dal servizio. Scrive prima in staging fuori da `runs/`, poi `os.replace`; `run-manifest.json` per ultimo. |
| Eventi di avanzamento | `obs001/minutes.py`, `aggregate.py`, `observe.py`, `cand001/backtest.py`, `data.py` | `tick` facoltativo ogni 20.000 righe, 1.000 barre aggregate, 500 osservazioni, 32 chiusure 45m, più un tick finale. Senza tick il percorso è invariato. L'annullamento è un'eccezione sollevata dal tick. |
| Profili | `config/APP-001-profiles.json`, `cand001/profiles.py` | `APP_CHECK_2025_01` [2025-01-01, 2025-02-01), `DEV`, `ADDITIONAL_2025`. Il registro è separato dal JSON del candidato e valida id/hash del candidato, la finestra dentro la fase, i confini di mese e l'esclusione del 2026. |
| Bundle | schema `cand001.bundle/3`, motore `1.0.3` | `/2` più `profile` (id, nome, tipo, finestra, fase che lo contiene). Gennaio non si presenta come l'intero 2025. I `/2` consegnati restano apribili: profilo dedotto dalla fase e dichiarato come tale. `/1` è conservato ma non supportato. |
| Servizio | `src/app001/` (solo libreria standard) | HTTP su 127.0.0.1:8765, un worker in thread. Controlli: Host del servizio/Vite; per le POST Origin del frontend e corpo JSON; nessun CORS. Accetta solo id registrati, rifiuta campi estranei come periodo o costi. `http_get` è disattivato nel processo. |
| Job | `<dati>/CAND-001/jobs/<job>/job.json` | Stati: STARTING → RUNNING → (CANCEL_REQUESTED) → un solo esito tra COMPLETED, INCOMPLETE, CANCELLED, INTERRUPTED, FAILED. Il job è registrato prima del calcolo. Chiave d'avvio idempotente, un solo job attivo con controllo atomico. All'avvio i job non conclusi diventano INTERRUPTED. |
| Lock | `trading_primitives/file_lock.py` | `jobs/service.lock` impedisce due servizi sulla stessa cartella; `jobs/worker.lock` è condiviso dal worker e da `python -m cand001 run`. Lock del sistema operativo (msvcrt/flock), rilasciati anche dopo un crash; nessun processo viene terminato. |
| Catalogo | `app001/catalog.py` | Ricavato da `runs/*/run-manifest.json`, con cache per data e dimensione. Un risultato è apribile solo con manifest, schema supportato e dimensione corretta; lo SHA256 viene verificato all'apertura. Le righe non apribili sono spiegate. |
| Avvio | `dashboard/scripts/dev.mjs`, `npm run dev` | Cerca Python 3.12 (`APP001_PYTHON` per indicarlo), avvia il servizio, attende `/api/health`, poi avvia Vite nello stesso processo Node con proxy `/api`. Ctrl+C o la chiusura del launcher chiudono lo stdin del servizio, che si arresta in ordine. |
| Interfaccia | `dashboard/src/ui/router.ts`, `ui/backtest/*` | Indirizzi `#/...` per tutti gli ambienti, con Indietro/Avanti e memoria dello scorrimento. Pagine Nuovo backtest, Esecuzione, Risultati salvati, Risultati, Tutte le operazioni e dettaglio. Testi della §7 e icone «i» (`components/Info.tsx`). |

## 2. Confronto reale UI / comando diretto (profilo di gennaio 2025)

Sono stati usati gli stessi dati locali, senza download. L'esecuzione dall'interfaccia è un clic su «Avvia» in Chrome a 1366 px, con `npm run dev`. Il comando diretto, dalla radice del checkout, è:

```powershell
$env:PYTHONPATH = "src"; python3.12 -m cand001 run --phase app-check-2025-01
```

| | UI (job-20261017T143441Z-a2ba1e) | Diretto (14:35:17Z) |
|---|---|---|
| commit / modifiche locali | 6079b87 / no | 6079b87 / no |
| profilo, motore, schema | APP_CHECK_2025_01, 1.0.3, /3 | uguali |
| inputHash | `6929bd6ecada43960e4261861ceeb04689dbdc373ffa25af9cea1c0d5989fe06` | uguale |
| configHash | `aed2c4ef…4ce9e6eb68ded2170ce4edf` | uguale |
| bundle SHA256 (425.618 byte) | `982ad3a69f912aaa3028e867c401400b4df43ddfe9bf855afd6fcea5bd33facc` | uguale: il comando calcola lo stesso contenuto e trova il file identico, senza sovrascriverlo |
| conteggi | 3 operazioni, 3 richieste, 48 episodi, 242 gambe, 1.073 decisioni | uguali |
| tempi (controllo / calcolo / totale) | 11,44 / 2,05 / 13,69 s | 11,23 / 2,07 / 13,52 s |

Provenienza distinta: `runs/CAND-001-v1.0.0-e1.0.3-APP_CHECK_2025_01-6929bd6eca-aed2c4ef62/run-manifest-<data>.json`, con `execution.via` uguale a `APP-001` più `jobId`, oppure `DIRECT`. Il bundle non contiene date, ID di job o progresso: il controllo sul testo è stato fatto.

Risultato di gennaio 2025 (solo collaudo): 3 operazioni LONG, tutte chiuse allo stop. Risultato dopo i costi −18,68 USDT, così composto: movimento dei prezzi −13,69, prezzo di esecuzione −1,80, commissioni −2,99, funding −0,20. Con costi più alti −25,86. Controllo di coerenza in sola lettura: operazioni e richieste coincidono con quelle di gennaio nel confronto 2025 già consegnato (motore 1.0.2).

## 3. Controlli eseguiti

- **Python**:
  - `test_app001_service` (18): due POST simultanee, stessa chiave ripetuta anche a job concluso, ricalcolo identico con provenienza separata, lock condivisi;
  - progresso dal motore reale: contatori `null` prima della fase, valori monotoni, nessun totale anticipato;
  - annullamento in controllo e in simulazione; annullamento dopo la pubblicazione: il risultato completo resta;
  - errore interno, archivio corrotto e funding non certificato: FAILED senza risultato;
  - riavvio con job interrotto, arresto ordinato;
  - catalogo con run parziale, `/1`, `/2` dedotto e SHA errato;
  - confini HTTP: Host, Origin, OPTIONS senza CORS, GET che non avvia, profilo non previsto, campo `end` 2026 rifiutato, dati mancanti senza download;
  - tick attivi o assenti con prefissi e futuri diversi danno risultati identici.
  
  Rieseguiti anche `test_cand001_*` (45) e `test_obs001_*` (30) perché il diff tocca i loro moduli: tutti OK.
- **Frontend** (vitest 108, typecheck, build OK). La suite completa è stata eseguita perché router e barra superiore cambiano tutti gli ambienti. Nuovi test:
  - `BacktestApp.test.tsx`: doppio clic con una sola POST, risposta persa ripetuta con la stessa chiave, job attivo, dati mancanti, servizio spento;
  - pagina del job: fasi e conteggi, annullamento richiesto e poi esito, ricaricamento con sole GET, stato non aggiornato;
  - percorso job → risultati → operazioni → dettaglio, con Indietro/Avanti e scorrimento ritrovato (640 px);
  - ID inesistenti, righe salvate, file esterno da riaprire;
  - `router.test.tsx`: percorsi e ID non validi, Indietro nella simulazione, studio storico riaperto al momento dell'indirizzo con sostituzione del cutoff;
  - `Backtest*.test.tsx`: costi riconciliati senza doppio conteggio, «i» da hover/focus/clic/Esc, tentativo non eseguito, protezione SHORT che scende, motivi veri di chiusura, contatto dentro il minuto, R1 (n.d., parte nota, prezzo corrente) invariato.
- **Prova browser reale** (Chrome headless pilotato via DevTools, 1366×900, dati veri):
  - avvio con un clic, più un doppio clic che crea un solo job; progresso letto durante il controllo;
  - completamento, Apri risultati, Tutte le operazioni (3) e dettaglio; «← Torna alle operazioni» in alto a sinistra (top 112 px, visibile);
  - Indietro, ricaricamento sulle operazioni e sul job: nessun nuovo job;
  - spiegazione aperta con un vero tasto Tab, chiusa con Esc, riaperta con un clic del mouse; Risultati salvati.
- **Annullamento reale**:
  - gennaio, dall'interfaccia durante il controllo (5/30 file): 120 ms dalla richiesta all'esito CANCELLED, nessun risultato, la pagina non mostra «100%»;
  - DEV, durante la preparazione: 18 ms.
- **Arresto**: chiudere il launcher (anche con terminazione forzata) chiude il servizio e libera le porte 5173 e 8765.

## 4. Deviazioni e limiti dichiarati

1. **Un ricalcolo DEV completo non previsto.** Per misurare l'annullamento durante la simulazione ho avviato DEV. La simulazione DEV dura meno di 0,5 s ed è finita prima della richiesta: il job `job-20261017T143132Z-221dfa` è COMPLETED e ha pubblicato `CAND-001-v1.0.0-e1.0.3-DEV-adaa94c502-aed2c4ef62`. Il contenuto (trade, richieste, episodi, finestre, curva, qualità, riepilogo) è identico a quello del DEV 1.0.1 consegnato; cambiano solo schema, versione, identità del run e profilo. Non è una nuova evidenza sulla strategia. Su dati reali l'annullamento in simulazione resta provato solo dai test sintetici.
2. **Primo run UI con provenienza incompleta.** Nel servizio `git` ereditava lo stdin del launcher e andava in timeout due volte: run-manifest con `commit: None` e 40 s attribuiti al controllo. Lo stesso vale per il DEV del punto 1. È stato corretto in 6079b87: stdin chiuso e `dirty` sconosciuto se git non risponde. Il bundle non cambia. Le esecuzioni successive registrano il commit.
3. Con interrogazioni molto frequenti, ogni 20 ms dal mio script, il controllo DEV è salito a 59 s per contesa del GIL. L'app interroga ogni secondo: le prove a quel ritmo hanno tempi uguali al comando diretto.
4. App locale e personale: nessun exchange, conto o ordine; nessuna nuova efficacia della strategia. Non c'è una ripresa del calcolo dopo un'interruzione: serve un nuovo avvio esplicito. Un annullato conserva stato e progresso, non un bundle parziale. File esterni e studio storico restano solo in memoria e dopo un ricaricamento si riaprono. Nessuna versione mobile dedicata.
5. Le esecuzioni di prova di questa consegna sono in `jobs/`: 5 della prova di gennaio, 4 completate e 1 annullata, più 2 su DEV, 1 annullata e 1 completata. Si possono lasciare come storico o archiviare: l'app non ne dipende.

## 5. Screenshot

In [APP-001-screens](APP-001-screens/README.md).

## 6. APP-001/R1 — correzioni (Claude Code, 17 ottobre 2026)

Incarico 1eedcd4, base 11e0284; correzioni in **3dd3f66**. Candidato, configurazione `aed2c4ef…`, regole, costi, finestre, motore **1.0.3** e schema **/3** sono invariati. Nessun download e nessun ricalcolo DEV o 2025. La versione del servizio passa a 1.0.1.

Riproduzioni prima della correzione. Ogni nuovo test Python e UI è stato eseguito anche sul codice 11e0284 (worktree temporaneo, poi rimosso) e lì fallisce. Tutti i casi sono **sintetici**, con prezzi inventati, salvo dove è indicato «reale».

| Punto | Riproduzione su 11e0284 | Correzione | Verifica dopo |
|---|---|---|---|
| R1-A costo mancante | Archivi sintetici `app001_helpers`. Una scadenza funding regolare cade 5 minuti dopo l'ingresso dell'unica operazione e manca solo il minuto mark precedente: netto `None`, eppure job COMPLETED e catalogo completo. | `pipeline.economic_completeness`: un costo pertinente non valorizzabile rende il risultato INCOMPLETE con motivo. `windowComplete` resta il solo indicatore del percorso dei prezzi. Il manifest registra `economic`. Job e catalogo distinguono `priceCoverageComplete` da `complete` e indicano il motivo. Per i vecchi /2 o /3 con netto mancante il motivo risulta «causa non registrata». Le viste mostrano «Storico elaborato, ma risultato dopo i costi non calcolabile: manca…». Il bundle non cambia. | Pipeline, job, manifest e catalogo INCOMPLETE, con operazioni e componenti note conservate. Resta completo il caso valido; resta completo anche il caso con un mark mancante senza posizione aperta. Zero operazioni con netto 0 = completo. Il funding non certificato blocca ancora prima del ledger. Lato UI: job, salvati e risultati. |
| R1-B progresso dopo HALT | Esempio CAND/R1 (trend seme 7, minuto tolto 5 minuti dopo il primo ingresso). Il riepilogo dà 245 chiusure valutate e 395 non valutate, ma l'ultimo tick riporta 640/640 con `t` a fine finestra. | Lo stato esposto da `run_window` si ferma al punto valutato (`closes` = chiusure fino all'HALT, `t` = HALT) e aggiunge `notEvaluatedCloses`. Decisioni, registrazioni NOT_EVALUATED e ledger restano invariati. La pagina del job mostra «Valutazione interrotta… 245 di 640; 395 non valutate». | L'ultimo tick del motore vale 245/395 con `t` = HALT; tutti i tick restano ≤ 245; il caso completo dà ancora 640/0. Il job reale del servizio (dati sintetici con lacuna) ha progresso in memoria e su disco uguale al riepilogo. Lato UI: 245 e 395, nessun «640 di 640». |
| R1-C ritorno interno | Registro scorso a 640 px, apertura del dettaglio, poi «← Torna alle operazioni»: `scrollTo(0)`. | Il router ha una navigazione di tipo `return` (`Link back`): crea una nuova voce e ritrova la posizione registrata per quella vista, come Indietro. Con un collegamento diretto, senza provenienza, si parte dall'alto. Usata nei ritorni del dettaglio e del registro. | 640 → dettaglio → 640 con clic vero. Indietro del browser ritrova ancora la posizione (300). «Torna ai risultati» dalle scorciatoie: 900 → 900. Un link diretto riparte da 0. |
| R1-D costi iniziali | La riga «Costi» mostrava ancora «5 bp… 3 bp… 10+10 bp» e «prezzi mark» senza aiuto. | Commissione 0,05% all'apertura e alla chiusura; prezzo di esecuzione 0,03% per lato, già incluso nei prezzi; pagamenti periodici; scenario con costi più alti indicato solo come confronto. Ogni voce ha la sua «i», compresi i prezzi mark (riferimento del contratto, usato solo per i pagamenti). Esempi in USDT solo sulla dimensione di 1.000. | Nessun «bp» nella scheda; spiegazioni da clic, focus ed Esc. Prova reale nel browser con clic del mouse (immagine `app-12`). |

In più, un difetto trovato durante i controlli: `test_boundaries_and_contract` falliva in modo intermittente (WinError 10053) perché il servizio rifiutava alcune POST senza leggerne il corpo. Ora il corpo, entro 4 KB, viene letto prima di rispondere. Dopo la correzione la suite del servizio è passata 5 volte di fila.

**Impatto numerico: nessuno.** Il profilo breve di gennaio, rieseguito con comando diretto per il cambio nel percorso di pubblicazione (motivo dichiarato, solo il profilo breve, dato reale), dà lo stesso bundle `982ad3a69f912aaa3028e867c401400b4df43ddfe9bf855afd6fcea5bd33facc` e `economic.complete=true` (commit 3dd3f66). Il catalogo reale, letto in sola lettura, mostra i quattro risultati apribili ancora completi con lo stesso netto: gennaio −18,68, DEV 1.0.3 e 1.0.1 −210,59, 2025 −109,08. Il vecchio /1 resta non supportato.

**Controlli eseguiti per R1:**
- servizio `test_app001_*`: 24 test, 5 esecuzioni consecutive OK;
- `test_cand001_*` limitati a backtest e R1 (12 test), perché è cambiato solo lo stato esposto da `run_window`; OBS non è stato toccato e non è stato rieseguito;
- UI `src/ui`: 79 test, compresi i 5 nuovi di `BacktestAppR1.test.tsx`;
- typecheck e build.

Non rieseguiti: suite generale e ricalcoli DEV o 2025.

**Limiti residui:**
- le immagini R1-A e R1-B non esistono su dati reali, perché nessun risultato reale ha costi mancanti o interruzioni; la verifica è sintetica e dichiarata come tale;
- l'annullamento durante la simulazione resta provato solo sinteticamente;
- i job e i manifest già salvati non vengono riscritti: i primi run restano con la provenienza incompleta già dichiarata.

Nessuna prova dell'Owner registrata.
