# WP-015 — MP-005 v0.6 candidate implementation (initial incompatibility of the RETURN reference)
Date: 2026-10-09. Status: ACTIVE BOUNDED IMPLEMENTATION; DIRECTOR ENGINEERING REVIEW REQUIRED. No Owner economic run activated or prepared.

Authority:
- the [MP-005 specification](MP-005-V06-INITIAL-RESPONSE-INCOMPATIBILITY.md) and the [Director methodological closure](MP-005-DIRECTOR-CLOSURE.md), registered as two separate documents from the authoritative text the Owner relayed on 9 October 2026 (specification first, closure after the separator, with no other change);
- the executive authorization below, which is a separate act: the closure alone did not activate any work.

Semantic base: v0.5 (MP-004) at `3c6af11355dc7f2ce0bc15e8da5fc58b6e5febb9`.

The authorization arrived first; the specification text was not attached to that message and came in a second Owner message. The second message is recorded here: "Ecco il testo integrale autoritativo MP-005, inclusa la chiusura metodologica del Director. Registralo separando specifica e chiusura, come richiesto. L'autorizzazione esecutiva è quella dell'incarico WP-015 già ricevuto. Procedi con quell'incarico."

## Executive authorization (verbatim)

> Attiva WP-015: implementazione MP-005 / candidato v0.6.
>
> AUTORIZZAZIONE DEL DIRECTOR
> La specifica allegata MP-005 è chiusa metodologicamente.
> Questo incarico autorizza ora implementazione e verifiche
> ingegneristiche sintetiche. Non autorizza run economiche.
>
> 1. Registrazione
> - Registra il testo MP-005 allegato senza modifiche silenziose,
>   separando specifica e chiusura del Director.
> - Registra questa autorizzazione esecutiva separatamente dalla
>   chiusura metodologica, che da sola non attivava il lavoro.
> - Predisponi task, registro e identità v0.6.
> - Conserva tutti i valori numerici ereditati; evidenzia i soli
>   nuovi elementi categoriali.
> - Preserva specifiche, identità, output e checkpoint delle
>   versioni v0.2–v0.5.
>
> 2. Implementazione circoscritta
> Aggiungi soltanto il controllo MP-005 dopo la preparazione
> valida dell’unico riferimento RETURN:
> - storico: intersezione F/corridoio/regione economica;
> - live: soltanto intersezione F/corridoio, indipendente dai costi;
> - intersezione con un solo tick ammesso = non vuota;
> - protezioni ereditate prioritarie;
> - INITIAL_RESPONSE_INCOMPATIBLE termina il child, non lo scenario;
> - P e X nella stessa dispatch, senza C/R/N/I/A;
> - nessun rinnovo, riapertura o classificazione locale successiva.
>
> Riusa le formule e i predicati economici esistenti.
> Non introdurre tolleranze, costi minimi live, soglie o
> interpretazioni nuove per rendere compatibili i riferimenti.
>
> 3. Integrazione
> - v0.6 selezionabile nel Workbench e nel live.
> - Identità e stato persistito distinti, con restore di produzione.
> - JSON, Markdown, Copy report ed export mostrano il nuovo motivo,
>   le basi diagnostiche e le identità dei conteggi.
> - Il nuovo conteggio è un sottoinsieme di X, denominatore P:
>   non sommarlo una seconda volta.
> - Mantieni le coorti WAIT-open e spiega la perdita delle
>   classificazioni C/R rispetto a v0.5.
> - Nessuna soglia dei 20 RETURN applicata a v0.6.
> - UI: tentativo d’ingresso terminato distinto da scenario invalidato.
> - Adegua assurance/reconciliation e Deep solo dove necessario
>   a riconoscere e verificare i nuovi record.
>
> 4. Verifiche
> Implementa tutte le fixture MP-005 LONG/SHORT.
> Aggiungi copertura sintetica diretta del terminale CORRIDOR live,
> con riferimento preparabile secondo MP-004.
>
> Verifica inoltre:
> - tick unico, bordi e arrotondamenti;
> - precedenza delle protezioni;
> - preparazione e terminale nella stessa dispatch;
> - checkpoint/restore, crash e ripresa senza riapertura o duplicati;
> - restrizione temporanea dei costi live;
> - parità con v0.5 fuori dal nuovo terminale;
> - preservazione dei pin e output delle versioni precedenti;
> - report complessivo/mensile e testo copiabile;
> - percorso browser minimo di selezione e reporting v0.6.
>
> Usa tape sintetici minimi e un database isolato.
> Esegui le suite pertinenti, typecheck/build e controlli schemi.
> Non ripetere suite già verdi senza nuovi cambi o problemi.
> La suite completa e Compose possono essere demandati alla CI
> se consentito dalle istruzioni del repository: dichiaralo.
>
> Se una fixture contraddice i predicati effettivi, segnala il
> controesempio; non correggere silenziosamente la specifica
> o il risultato atteso.
>
> 5. Limiti
> Nessuna acquisizione, estrazione Owner, replay su dati reali,
> backtest economico o confronto economico.
> Non preparare un nuovo lancio Owner automatico: questo delta
> richiede anzitutto accettazione tecnica.
> Nessuna modifica allo stack Owner.
>
> 6. Consegna
> Evidenza compatta: fixture→atteso→effettivo, compatibilità,
> identità, verifiche eseguite e limiti.
> Aggiorna STATE e task, commit e push normali.
> Non interrogare la CI; nessun processo di attesa residuo.
>
> Consegna:
> READY FOR DIRECTOR REVIEW — WP-015 ONLY
> con SHA base/finale e CI PENDING / NOT CHECKED.

## Index of deliverables

1. **Registration.**
   - Specification and closure are registered byte-for-byte as separate documents, with packaged copies.
   - This authorization is recorded separately.
   - Executor-derived register `MP-005-PARAMETERS.json`: every MP-004 value is kept, and only `mp005_policy` is added. Its new categorical elements are the reason, the two bases, the CORRIDOR primacy and the response outcome.
2. **Kernel delta.** `adviser.core.v6` adds only the MP-005 check after the MP-004 preparation of the single reference:
   - historical: F ∩ C0 ∩ A0;
   - live: F ∩ C0 only, cost-independent;
   - a single tick counts as non-empty;
   - inherited protections keep their precedence;
   - the child ends in the preparation dispatch (P and X) and the scenario does not.
3. **Integration.**
   - Own state, runtime, engine, report, reconciliation and Deep identities, with production restore.
   - The subset of X, by base and month, with the declared loss of C/R classifications.
   - v0.6 selectable in the Workbench and live.
   - The UI shows an ended attempt distinctly from an invalidated scenario.
   - A read-only v0.5/v0.6 comparison.
4. **Evidence.** See [WP-015 engineering evidence](evidence/WP-015-ENGINEERING-EVIDENCE.md).

Boundaries:
- Synthetic bounded data only, on an isolated database.
- No acquisition, Owner extraction, real-data replay, economic run or comparison.
- No Owner launch is prepared.
- The Owner stack is never touched.
