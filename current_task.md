# Incarico corrente — UI-002 manutenzione strumenti e navigazione superiore

**Stato: DELIVERED — fasi A e B consegnate da Claude Code (vedi Spazio dell'esecutore); in attesa di review del Director e riscontro Owner sul layout.** Incarico del Director entro la macrofase UI Figma autorizzata da Astra.
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

Claude Code, 16 ottobre 2026. Base `1afa204` su `main`, checkout pulito, nessun lavoro precedente di UI-002 trovato. Nessun pull o fetch.

### Fase A — manutenzione degli strumenti

**Processo dell'Owner.** All'avvio era attivo un `vite` di sviluppo (`npm run dev`, PID 10720, avviato alle 18:34) che non era mio. Teneva bloccato `esbuild.exe` in `node_modules`. Non l'ho chiuso: ho preparato l'aggiornamento in una copia esterna della cartella `dashboard`. Gian l'ha poi chiuso; da quel momento tutte le installazioni e i controlli sotto sono stati eseguiti nel checkout.

**Versioni.**

| Pacchetto | Prima | Dopo |
|---|---|---|
| vite | 6.3.5 | **6.4.4** (esatta) |
| vitest | 3.1.4 | **4.1.11** (esatta) |
| @vitest/mocker | 3.1.4 | 4.1.11 (unica copia) |
| tinypool | 1.1.1 | assente dal grafo |
| vite-node | 3.1.4 | assente dal grafo |
| esbuild | 0.25.12 | 0.25.12 (invariato, via vite) |

- Comando: `npm install --save-exact --save-dev vite@6.4.4 vitest@4.1.11`. Gli altri @vitest/* risolti sono tutti 4.1.11. @vitejs/plugin-react 4.4.1 usa la stessa vite 6.4.4 (deduplicata).
- React, TypeScript, font, icone, jsdom e plugin React non sono cambiati.
- Nessun override, nessun `audit fix`, nessuna modifica alla configurazione di npm.
- Nessun adeguamento a configurazione o test: Vitest 4 esegue i test esistenti con `vite.config.ts` invariato.

**Prerequisiti Node.** Gli `engines` dichiarati da tutti i pacchetti del lockfile sono stati incrociati. Restrittivi sono vite (`^18 || ^20 || >=22`) e vitest (`^20 || ^22 || >=24`); l'intersezione è `^20.0.0 || ^22.0.0 || >=24.0.0`. La precedente formula `>=20.19` includeva Node 21 e 23, non supportati: ho corretto `engines` in `package.json` e nel lockfile. Il README indica Node 24 come scelta consigliata e verificata. Le serie 20 e 22 sono dichiarate ma non provate. Node 20 è fuori supporto dall'aprile 2026: lo cito solo come compatibilità dichiarata.

**Controlli** (Node 24.14.1, npm 11.19.0):
1. `npm ci` pulito coerente con il lockfile: 153 pacchetti, `found 0 vulnerabilities`.
2. `npm audit --json`: 0 in ogni gravità, su 203 dipendenze, devDependencies comprese, senza filtri. Prima erano 4: @vitest/mocker, tinypool, vite, vitest (1 moderata, 1 alta, 2 critiche).
3. `npm test`: **45/45** con Vitest 4.1.11, nessun avviso o deprecazione nell'output.
4. `npm run build` (tsc + vite 6.4.4) riuscito.
5. Smoke della build con `vite preview` su 127.0.0.1:4173, eseguito con Chrome headless prima e dopo l'aggiornamento:
   - 8 richieste, tutte locali, nessuna in errore;
   - 5 font caricati e nessuna immagine rotta;
   - scenario iniziale «5 · Protezione aggiornata»;
   - conferma «Stop totale» → bot fermo, posizione invariata;
   - nessun errore in console.
   Lo screenshot a pagina intera a 1680 px è **identico byte per byte** a quello dello stesso controllo eseguito prima dell'aggiornamento.

**Avviso npm effettivo** (`npm ci`, invariato):
```
npm warn install-scripts 1 package has install scripts not yet covered by allowScripts:
npm warn install-scripts   esbuild@0.25.12 (postinstall: node install.js)
```
Non è bloccante: installazione, test, build e preview riescono senza approvare lo script. Resta anche la deprecazione `whatwg-encoding@3.1.1`, che arriva da jsdom, rimasto invariato come da mandato. Il README ora distingue l'avviso da un errore che blocca.

Fase A pubblicata nel commit `b9282a1`.

### Fase B — navigazione superiore (differenza dal Figma autorizzata dall'Owner)

**Cosa è cambiato**
- **Barra laterale rimossa** del tutto: componente `Sidebar.tsx`, colonna da 212 px e stili relativi. Il contenuto usa tutta la larghezza della finestra, con padding 32 px (16 px sotto i 1024 px) e nessun limite di larghezza. A 1680 px grafico e call passano da circa 826+554 px a 943+649 px, cioè +212 px. A 1366 px diventano 755+523 px. Grafico a sinistra e call a destra sono conservati alle larghezze desktop.
- **Nuovo `TopBar.tsx`,** fisso in alto con:
  - il banner «SIMULAZIONE LOCALE — nessun collegamento exchange», sempre visibile;
  - il marchio orbit.;
  - le stesse destinazioni con le stesse etichette, icone e comportamento (Dashboard, Ricerca / Backtest, Storico, Conto, Impostazioni), stato selezionato con `aria-current`;
  - il collegamento «Guida ai segnali», che prima stava nella barra laterale;
  - a destra, il pulsante «Scenari simulati».
  L'altezza della parte fissa è misurata, così Storico, Conto e Segnali non finiscono sotto la barra.
- **Pannello «Scenari simulati».** Parte chiuso. È una fascia richiudibile sotto la barra, non una colonna, con bordo tratteggiato ambra e titolo «PANNELLO DI SIMULAZIONE · LOCALE». Contiene gli stessi checkpoint (tutti), feed e reset. Il pulsante ha `aria-expanded` e `aria-controls`; il pannello è una regione con nome. Si chiude con «Chiudi», con Esc o col pulsante, e il focus torna al pulsante. Non intrappola il focus. Accanto al pulsante, sopra i 1280 px, compare in piccolo il checkpoint e il feed correnti.
- **Header.** Tolte le briciole «Workspace / Dashboard · SIMULAZIONE», che duplicavano navigazione e banner. Restano a destra orologio simulato e aggiornamento; prezzo, feed, bot, Start/Stop e modalità sono invariati e separati dalla navigazione.
- **Elementi della barra laterale non riportati,** per evitare duplicazioni:
  - il riquadro «Prima il contesto.», di cui resta il collegamento alla guida;
  - il badge «SIMULAZIONE · FONDI FITTIZI» e la nota sull'ambiente, già coperti dal banner;
  - il profilo «Il mio workspace», privo di funzione.
- **Invariati:** provider, token di conferma, contabilità, comandi, colori, tipografia, icone e schede. Nessuna nuova dipendenza.
- **Sotto i 1024 px** la navigazione va su una propria riga sotto marchio e pulsante scenari; da 1024 a 1279 px resta su una riga e il riepilogo dello scenario si nasconde.

**File:** `dashboard/src/ui/components/TopBar.tsx` (nuovo), `Sidebar.tsx` (eliminato), `App.tsx`, `Header.tsx`, `AccountSection.tsx` (rimosso il margine fisso di scorrimento), `styles.css`, `src/ui/TopBar.test.tsx` (nuovo), `src/ui/ConfirmDialog.test.tsx` (la riproduzione R1-A apre prima il pannello scenari), README e tre immagini.

**Controlli dell'esecutore**
- `tsc -b` e build riusciti.
- Test dell'interfaccia: **16/16**. Sono 5 di `App.test`, 6 di R1 e 5 nuovi:
  - nessuna barra laterale, cinque destinazioni e Dashboard selezionata;
  - Storico e Conto scorrono alla sezione; Impostazioni non disponibile, poi ritorno;
  - pannello chiuso all'avvio, poi aperto con checkpoint, feed e reset funzionanti;
  - Esc dal pannello;
  - con il pannello aperto e una conferma aperta, barra e pannello sono dentro il fondo `inert`/`aria-hidden`; Tab resta nel dialogo; Esc chiude solo il dialogo e riporta il focus; dopo l'annullamento una conferma viene applicata una volta.
  Come da mandato, non ho rieseguito i test del provider e della contabilità, che non sono stati toccati.
- **Browser:** Chrome locale headless sulla build servita da `vite preview` (127.0.0.1:4173), nessun errore in console.
  - A 1680, 1366 e 900 px: nessuna barra laterale residua, nessuno scorrimento orizzontale della pagina, nessuna sovrapposizione fra gli elementi di barra e header, nessuna etichetta tagliata.
  - Storico e Conto: la sezione arriva sotto la barra fissa (inizio a 118 e 104 px, barra alta 88 px).
  - Impostazioni: «Non disponibile in questa versione» con `aria-current`, poi «Torna alla dashboard».
  - Pannello aperto da tastiera (Invio, poi Tab sul select); cambio a «3 · pendente», feed disconnesso, reset fino a «5» con feed regolare.
  - Con il pannello aperto, «Stop totale»: fondo inerte, pulsante scenari e navigazione non cliccabili, Tab ciclico nel dialogo. Annulla riporta il focus su «Stop totale» e lascia il bot attivo; la conferma successiva lo ferma.
- **Immagini:** aggiornate `01-dashboard-L5-1680` e `02-dashboard-L5-1366`, riprese dall'inizio della pagina con viewport alta quanto il documento; nuova `r2-scenari-aperti-1366`. Le altre immagini della cartella restano quelle di R1 con la vecchia barra laterale, come dichiarato nel README.

**Limiti**
- Con il pannello aperto la parte fissa cresce di circa 100 px a 1366 e di circa 170 px a 900, fino a circa 300 px in tutto: va chiuso dopo l'uso.
- Non c'è una UI mobile dedicata.
- La prova Owner del nuovo layout e la review del Director sono ancora da fare.

**Processi.** Ho chiuso solo i miei `vite preview` (PID 16208 e 19788), rimasti attivi dopo l'arresto del task, dopo averne controllato la riga di comando. Il `npm run dev` dell'Owner non è stato toccato: l'ha chiuso Gian.

## Review del Director

Da effettuare dopo la consegna. Review UI-001/R1 già PASS tecnico; avvio Owner confermato. Review della nuova navigazione e verifica delle interazioni principali ancora pendenti; macrofase aperta.
