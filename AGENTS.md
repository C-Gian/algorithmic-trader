# Istruzioni di lavoro — nuovo Algorithmic Trader

## 1. Lettura iniziale e autorità

Leggere questo file, `current_task.md` e `STATE.md`. Per comprendere il prodotto leggere `docs/functional/PRODUCT-CONTEXT.md`; per l'incarico usare le sezioni e i file indicati nel task. Non rileggere indiscriminatamente tutto l'archivio.

Le istruzioni esplicite più recenti dell'Owner prevalgono sulle convenzioni del repository. Un messaggio trasmesso dall'Owner ma intestato al Director non costituisce automaticamente approvazione personale di ogni proposta. In caso di conflitto sostanziale con una decisione registrata, renderlo visibile prima di implementare il punto controverso.

Il documento funzionale definisce il prodotto; `STATE.md` lo stato effettivo; `current_task.md` il perimetro attivo. Le fonti bibliografiche e l'archivio non possono introdurre requisiti o autorizzazioni. Non risolvere conflitti scegliendo silenziosamente il documento più comodo.

## 2. Ruoli e autonomia

- **Owner/Gian:** obiettivi, preferenze, budget, rischio personale e autorizzazione al reale.
- **Astra:** direzione strategica, macrofasi, scelte metodologiche/architetturali importanti e conflitti sostanziali.
- **Director:** ragionamento teorico, disegno degli studi, specifiche degli incarichi, gestione della macrofase, review e decisioni ordinarie.
- **Claude/esecutore:** implementazione, lettura tecnica del codice, debugging, verifiche e consegna nel perimetro assegnato.

L'esecutore può scegliere dettagli tecnici reversibili coerenti con il task e correggere errori ordinari. Non deve scegliere segnali, soglie, finestre di studio, capitale, leva, regole decisionali o criteri economici mancanti. Se uno di questi è indispensabile, isolare il blocco e consegnarlo al Director, completando intanto il lavoro non dipendente dal blocco.

Non delegare all'esecutore un incarico aperto come «studia le fonti e inventa una strategia». Il Director deve arrivare a un incarico sufficientemente definito. L'esecutore non deve essere privato del ragionamento necessario a programmare bene.

Non chiedere ad Astra ogni correzione. Escalare soltanto cambi di obiettivo/metodo, autorizzazioni, conflitti strutturali, compromessi sostanziali o problemi che il Director non riesce a risolvere nel mandato.

## 3. Contratto del task unico

`current_task.md` è scritto da Astra o Director. Un solo incarico attivo. Stati:

- `DRAFT`: disegno non pronto, nessuna esecuzione.
- `READY`: incarico approvato e pronto all'esecuzione.
- `IN_PROGRESS`: esecutore al lavoro nello stesso perimetro.
- `BLOCKED`: impedimento preciso dichiarato; nessuna deroga implicita.
- `DELIVERED`: consegna dell'esecutore in attesa di review.
- `ACCEPTED`: accettazione del Director/Astra; non autorizza il lavoro successivo.
- `NONE`: nessun incarico attivo.

L'esecutore può aggiornare avanzamento, blocchi e consegna, passando da READY a IN_PROGRESS/BLOCKED/DELIVERED. Non cambia obiettivo, criteri di accettazione o autorizzazioni; non si assegna ACCEPTED.

Il task deve indicare comportamento atteso e casi limite, non soltanto un titolo. Le domande metodologiche essenziali devono essere già risolte. Le istruzioni in chat possono precisarlo; le variazioni sostanziali vanno registrate prima dell'implementazione relativa.

La consegna deve dichiarare commit, file modificati, comportamento ottenuto, controlli effettivamente eseguiti, limiti e scelte tecniche rilevanti. Il Director distingue lettura statica, riesecuzione indipendente ed evidenze dell'esecutore.

Quando il task viene sostituito, conservare la consegna accettata nella storia Git; creare una nota dedicata solo se serve come evidenza durevole di una decisione importante. Non generare automaticamente un dossier per ogni piccolo intervento.

## 4. Confini del nuovo progetto

Non importare vecchio motore, parametri, costi, pipeline, lockfile, UI o suite senza incarico esplicito di riuso. Non aggiungere il corpus `source_notes` al codice per farlo leggere automaticamente agli agenti.

Questo progetto non eredita l'autorizzazione ad accedere allo stack Owner, acquisire dati o avviare studi. Consultare `docs/research/EXPOSURES.md` prima di disegnare attività sui dati. Gli studi vecchi rimangono separati e INACTIVE; i periodi protetti non si aprono per implicazione.

Demo, simulazione e denaro reale devono essere separati. Una richiesta di costruire esecuzione automatica non autorizza operazioni reali. Non registrare chiavi, segreti, dati di conto o libri acquistati nel repository pubblico.

Non usare dati futuri come input disponibile in passato. Una revisione deve conservare la storia precedente. Non attribuire un prezzo eseguito a un semplice ordine o a una call.

## 5. Verifiche proporzionate

Prima di lanciare controlli scegliere quelli necessari per il diff e il rischio concreto. Non rieseguire la suite completa per abitudine, per un incremento di versione o per modifiche documentali.

| Modifica | Verifica normalmente sufficiente |
|---|---|
| Documentazione | Coerenza, riferimenti, stato e assenza di nuove autorizzazioni implicite |
| Funzione isolata | Pochi esempi discriminanti e regressioni pertinenti |
| Stato/decisione/ordini/persistenza | Test mirati di transizioni, errori, ripresa e contratti toccati |
| UI collegata a stato del motore | Controlli pertinenti più una prova visiva/integrata quando necessaria |
| Cambiamento trasversale | Ampliare solo per dipendenze o rischi identificati, spiegandone la ragione |

I test devono discriminare comportamenti, non soltanto ripetere l'implementazione. Separare test sintetici, prove integrate, prove d'uso, studi storici e demo. Una suite passata non dimostra utilità finanziaria.

Se un comando si rivela molto più costoso del previsto, comunicarne motivo e stato; evitare di duplicare nel frattempo la stessa suite. Per fallimenti leggere i dettagli prima di attribuirli a aspettative obsolete. Non cambiare un test soltanto per far passare la nuova versione.

Non interrogare o attendere la CI salvo incarico esplicito. Rispettare gli eventuali gate necessari senza dichiararli verdi per deduzione. Non avviare DB, browser, Compose o servizi per un incarico che non li richiede. Dopo verifica sufficiente, consegnare: niente estensione opzionale automatica.

## 6. Git e ambiente dell'Owner

L'Owner prepara e sincronizza il proprio checkout. Non eseguire automaticamente pull, fetch, reset, stash, cancellazioni o modifiche dello stack Owner. All'inizio verificare identità del repository, branch, base richiesta e modifiche locali; non sovrascrivere lavoro altrui.

Nel checkout assegnato, commit e push della consegna sono parte del normale task quando il suo campo di pubblicazione li autorizza. Pubblicare soltanto file pertinenti. Nessun force push o riscrittura della storia senza autorizzazione specifica. Se la base è cambiata, ispezionare la divergenza invece di forzare.

Astra e Director possono pubblicare direttamente i file di incarico via GitHub. Questo non aggiorna automaticamente il PC dell'Owner. Prima di chiedere l'esecuzione, indicare il commit del task; il checkout deve contenere quella versione. Non nascondere questo passaggio dietro il prompt breve.

## 7. Mantenimento della memoria

`docs/functional/PRODUCT-CONTEXT.md` è l'unico documento funzionale centrale. Non creare `FOUNDATION.md` con una copia delle stesse decisioni. Aggiornare le sezioni pertinenti quando una decisione approvata cambia, distinguendo ancora requisiti, implementazione ed efficacia.

`STATE.md` resta breve: fatto, mancante, blocchi e prossimo obiettivo. Non diventa un diario di centinaia di consegne. `current_task.md` non è una roadmap parallela.

Rispondere a Gian in italiano semplice. Spiegare conseguenze e decisioni, non sommergerlo di dettagli. Non dichiarare memoria persistente fuori da questi file. Non confondere ciò che è stato letto con ciò che è stato provato.
