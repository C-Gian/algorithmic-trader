# Incarico corrente — UI-002 manutenzione strumenti

**Stato: READY.** Incarico del Director entro la macrofase UI Figma autorizzata da Astra.
Esecutore: Claude Code. Review: Director.
Base: b751526476ed9dd3800ce249127ad0814ff43d07 e questa registrazione del task.
La review tecnica di UI-001/R1 è PASS, conservata nella storia di current_task.md al commit b8153351b1ad639fe1141dcbf86f34c1b7d023f1. La prova d'uso Owner rimane da svolgere; non la inventare né dichiarare chiusa la macrofase.

## 1. Obiettivo

Rimuovere gli advisory riprodotti sugli strumenti frontend/test con un aggiornamento circoscritto. Preservare dashboard, provider, scenari, contabilità, comandi e stile. Nessun nuovo algoritmo o design.

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

## Spazio dell'esecutore

Da compilare.

## Review del Director

Da effettuare dopo la consegna. Review UI-001/R1 già PASS tecnico; prova Owner e chiusura macrofase ancora pendenti.
