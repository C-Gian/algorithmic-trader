# Incarico corrente — UI-002 manutenzione strumenti e navigazione superiore

**Stato: READY.** Incarico del Director entro la macrofase UI Figma autorizzata da Astra.
Esecutore: Claude Code. Review: Director.
Base: b751526476ed9dd3800ce249127ad0814ff43d07 e questa registrazione del task.
La review tecnica di UI-001/R1 è PASS, conservata nella storia di current_task.md al commit b8153351b1ad639fe1141dcbf86f34c1b7d023f1. Il 16 ottobre Gian riferisce di aver eseguito npm ci e npm run dev e che l'app sembra funzionare. È confermato l'avvio sul PC Owner; non è una dichiarazione di verifica completa di ogni transizione. Richiede esplicitamente di eliminare la barra sinistra e spostare la navigazione in alto per recuperare spazio.

## 1. Obiettivo

Rimuovere gli advisory riprodotti sugli strumenti frontend/test con un aggiornamento circoscritto. Fase A: preservare dashboard, provider, scenari, contabilità, comandi e stile durante la manutenzione. Fase B: applicare esclusivamente la modifica di layout autorizzata dall'Owner nella sezione 7. Nessun nuovo algoritmo.

npm audit --json sulla base segnala @vitest/mocker, tinypool, vite e vitest (1 moderate, 1 high, 2 critical). Il Director ha verificato le fonti dei manutentori, non solo il riepilogo npm. Le versioni correnti sono vite 6.3.5 e vitest 3.1.4.

## 2. Decisioni e target

- Aggiornare vite a **6.4.4**, rimanendo sulla major 6.
- Aggiornare vitest a **4.1.11**, con relativi pacchetti @vitest/* coerenti. La major cambia perché la correzione di mocker non è prevista sulla 3.x.
- Entrambi i target risultano pubblicati nel registry consultato dal Director. Vitest 4.1.11 dichiara peer Vite ^6/^7/^8, Node ^20/^22/>=24 e dipende da @vitest/mocker 4.1.11.
- Verificare risoluzione effettiva di @vitest/mocker e tinypool: niente copie vulnerabili residue usate dai test. Tinypool può sparire dal grafo; non aggiungerlo come dipendenza inutile.
- Versioni dirette esatte e lockfile aggiornato. Niente “audit fix --force”, override arbitrari di major transitive, disattivazione controlli o aggiornamento globale npm.
- Non aggiornare React, TypeScript, font, icone, jsdom o plugin React salvo incompatibilità specifica dimostrata. Se è necessario un piccolo adeguamento di config/import test per Vitest 4, farlo e motivarlo.
- Verificare engines/prerequisiti rispetto ai pacchetti effettivi e aggiornare README se la precedente formulazione “20.19 o successivo” include release Node non supportate. Preferenza pratica per la versione 24 già usata dall'Owner; non installare Node sul PC.

Fonti:
- https://github.com/vitejs/vite/security/advisories/GHSA-fx2h-pf6j-xcff (Windows; correzione nel ramo 6 da 6.4.3)
- https://github.com/vitejs/vite/security/advisories/GHSA-p9ff-h696-f583
- https://github.com/vitest-dev/vitest/security/advisories/GHSA-5xrq-8626-4rwp
- https://github.com/vitest-dev/vitest/security/advisories/GHSA-82fw-gwwq-j7x9 (mocker: fix 4.1.11; 3.x non mantenuta per questo fix)
- https://github.com/tinylibs/tinypool/security/advisories/GHSA-85c8-ppgw-ccpr
- https://github.com/tinylibs/tinypool/security/advisories/GHSA-5gmw-xhrv-c9v3

Non selezionare Vitest 3.2.7 solo perché suggerito da npm fixAvailable: non risolve tutti gli advisory verificati dalle fonti.

## 3. esbuild e npm

L'avviso “install scripts not yet covered by allowScripts: esbuild@0.25.12 (postinstall: node install.js)” è distinto dagli advisory. Con la policy attuale eseguire installazione, test e build; se funzionano non serve silenziarlo né approvare tutti gli script.

Non modificare configurazione npm globale/utente o impostazioni del PC Owner. Se la nuova installazione fallisce per esbuild, isolare l'errore, la versione risolta e il minimo rimedio locale prima di cambiare policy; consultare il Director se è richiesta un'autorizzazione diversa. Niente rimedi preventivi indiscriminati.

Il README deve distinguere un avviso non bloccante da un errore che impedisce build/avvio, senza dire che qualunque avviso si può ignorare.

## 4. Perimetro e verifiche

Aree: dashboard/package.json, package-lock.json; config e import test solo se richiesti dalla migrazione; README, STATE e consegna nel task. Non toccare comportamento/fixture/stile per far passare i test.

Verifiche proporzionate a un cambio del runner e bundler:
1. Installazione pulita coerente col lockfile; versioni effettivamente risolte.
2. Tutti i **45 test attuali della sola dashboard**, perché cambia il runner comune. Niente suite Python/vecchio progetto/CI.
3. Typecheck/build.
4. npm audit --json: i quattro rilievi noti devono essere risolti nel grafo effettivo. Se emergono nuove segnalazioni, riportare ID, catena e condizioni prima di allargare il lavoro; non dichiarare “zero” filtrando via tutte le devDependencies.
5. Breve smoke della build tramite preview su 127.0.0.1:4173: caricamento asset locali, scenario iniziale, una conferma e assenza errori. Un confronto visuale prima/dopo è sufficiente se non ci sono regressioni. Non rigenerare venti immagini o ripetere il gate Figma.

Niente API/UI server di Vitest, esposizione LAN o servizi aggiuntivi. Chiudere i processi di preview avviati per il task identificando quelli propri; non terminare processi dell'Owner.

## 5. Consegna

Commit/push su main autorizzati per questi file. Nessun pull/fetch (anche --dry-run), reset, stash o force push. All'inizio controllare repo/branch/base e modifiche locali senza sovrascrivere altro lavoro.

Riportare versioni prima/dopo, catene eliminate, eventuali adeguamenti e motivi, esiti dei controlli, avviso esbuild effettivo ed eventuali rilievi residui. Aggiornare STATE; READY → IN_PROGRESS/BLOCKED/DELIVERED, mai ACCEPTED. Il Director revisiona; nessuna nuova autorizzazione strategica necessaria per il lavoro specificato.

## 6. Prova Owner e limiti

La prova della UI può procedere già sulla build b751526 con:
npm ci
npm run build
npm run preview
Aprire http://127.0.0.1:4173. È una prova locale della build senza HMR o server API test, non un'autorizzazione a esporre il servizio.

Percorso breve: stato iniziale → Stop totale e conferma (la posizione rimane aperta) → Start e conferma → Gestione manuale → Riprendi automatico e spunta → Uscita parziale → Chiudi posizione; osservare saldo 10.005,793 e netto +5,793. Poi reset e, dal pannello simulazione, attesa/pendente/rifiutato/SHORT/feed disconnesso. Owner può riferire problemi con parole semplici; non deve leggere log.

Nessun dato reale, algoritmo, acquisizione, backtest, accesso exchange/stack Owner, ordine esterno o apertura protetta. DESIGN-001 resta non approvato e inattivo.


## 7. Fase B — navigazione superiore richiesta da Gian

Disposizione Owner del 16 ottobre 2026: eliminare la nav bar a sinistra e crearne una in alto, recuperando la larghezza del contenuto principale. È una modifica esplicitamente autorizzata rispetto al layout Figma; non richiede nuova approvazione né modifica del file Figma. Il resto del riferimento visivo rimane valido.

Eseguire dopo la fase A nello stesso incarico UI-002. Se il checkout contiene lavoro in corso sulla fase A, conservarlo: nessun reset o sovrascrittura. Documentare separatamente gli esiti delle due fasi.

### Layout e comportamento attesi

- Rimuovere completamente la colonna laterale e la larghezza/margine riservati. La dashboard usa tutta la larghezza utile della finestra, conservando padding e spaziatura coerenti. Mantenere grafico a sinistra e call/posizione a destra alle larghezze desktop previste; niente colonne vuote o grande limite di larghezza che annulli il guadagno.
- Inserire in alto una barra orizzontale compatta con identità del prodotto e le stesse destinazioni esistenti: Dashboard, Storico, Conto, Ricerca/Backtest, Impostazioni (usare le etichette attuali). Conservare destinazione, stato selezionato, scroll/viste e messaggi “Non disponibile in questa versione”. Non costruire nuove sezioni.
- Riorganizzare l'header esistente per evitare duplicazioni di logo, navigazione, stato e comandi. Banner “SIMULAZIONE LOCALE — nessun collegamento exchange” sempre evidente, senza coprire il contenuto. Modalità, feed, bot e comandi operativi restano comprensibili e distinti dalla navigazione.
- Trasferire i controlli della simulazione in un pannello richiudibile raggiungibile dall'alto con un pulsante esplicito “Scenari simulati”. Il pannello parte chiuso, mostra chiaramente la propria natura locale e contiene gli stessi checkpoint, feed e reset. Non mescolare questi selettori ai comandi di trading e non eliminare scenari. Evitare una seconda colonna permanente che ricrei l'ingombro rimosso.
- Su finestre più strette permettere un adattamento compatto della navigazione senza sovrapposizioni, tagli o scorrimento orizzontale dell'intera pagina. Nessun obbligo di nuova UI mobile completa.
- Conservare colori, tipografia, icone e schede del riferimento. Niente restyling generale, nuovi grafici, nuovi valori o dipendenze soltanto per questa modifica.

### Conferme e accessibilità

La correzione R1-A resta vincolante: a dialogo di conferma aperto anche la nuova navbar e il pannello scenari sono inerti; Tab resta nel dialogo, Esc/Annulla e ripristino focus funzionano. Il pannello scenari è utilizzabile da tastiera, ha nome/stato aperto accessibili e non introduce una trappola del focus. Non cambiare provider, token di conferma, contabilità o semantica dei comandi per adattarli al layout.

### Verifiche e consegna della fase B

- Typecheck/build dopo la modifica; test UI mirati a navigazione esistente, apertura/chiusura scenari e isolamento del fondo durante le conferme, comprese regressioni R1 pertinenti. Non rieseguire ulteriormente l'intera suite o i conti immutati per il solo spostamento.
- Prova browser a 1680, 1366 e 900 px: nessuna colonna sinistra residua, spazio recuperato, contenuto e comandi non sovrapposti, navigazione/scenari accessibili e conferme isolate. Verificare Storico/Conto e una destinazione non disponibile; una transizione di scenario e feed, reset, una conferma annullata e una confermata.
- Due screenshot aggiornati della dashboard da inizio pagina (1680/1366) e uno con pannello scenari aperto sono sufficienti; aggiungerne altri solo per un difetto concreto. Nessun nuovo gate Figma o rigenerazione generale.
- README: indicare dove si trovano ora navigazione e selettore scenari. Consegna: differenza autorizzata dal Figma, file, esiti reali e limiti. Nessuna prova browser dell'esecutore attribuita al Director.
- Pubblicazione e vincoli della sezione 5 valgono anche per i componenti/layout, CSS, test pertinenti e istruzioni di questa fase. Nessuna operazione esterna.

Criterio di chiusura UI-002: manutenzione verificata e navbar superiore funzionante, spazio sinistro recuperato, controlli simulati ancora disponibili, nessuna regressione delle conferme. DELIVERED alla consegna; review del Director e riscontro Owner sul nuovo layout prima della chiusura macrofase.

## Spazio dell'esecutore

Da compilare.

## Review del Director

Da effettuare dopo la consegna. Review UI-001/R1 già PASS tecnico; avvio Owner confermato. Review della nuova navigazione e verifica delle interazioni principali ancora pendenti; macrofase aperta.
