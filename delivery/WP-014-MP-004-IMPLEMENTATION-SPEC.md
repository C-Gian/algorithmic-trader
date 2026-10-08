# WP-014 — MP-004 v0.5 candidate implementation (A RETURN followed by local recovery)
Date: 2026-10-08. Status: ACTIVE BOUNDED IMPLEMENTATION; DIRECTOR ENGINEERING REVIEW REQUIRED. No Owner economic run activated.

Authority: [MP-004 specification](MP-004-V05-RETURN-RESPONSE.md) and its [Director closure](MP-004-DIRECTOR-CLOSURE.md) (both §8 joints accepted). Semantic base v0.4 at `776752e`. The Owner-relayed activation below is recorded verbatim; the English summary that follows is an index, not a reinterpretation.

## Activation (verbatim)

> Attivo WP-014 — implementazione del candidato v0.5 secondo MP-004-V05-RETURN-RESPONSE allegata, chiusa metodologicamente dal Director.
>
> La chiusura approva la semantica candidata, non efficacia economica. Sono accettati entrambi i raccordi del §8:
> - contatto locale a cavallo della pubblicazione → UNASSESSABLE, senza rinnovo;
> - prima ripresa osservata tardivamente e non più corrente → valutazione non emettibile, senza cercare una barra successiva.
>
> Prima registra la specifica autorevole, la chiusura e il task nel repository secondo le convenzioni esistenti. Rispetta AGENTS.md.
>
> Implementa v0.5 selezionabile accanto alle versioni precedenti:
> - Solo A RETURN cambia: prima prepara il riferimento, poi richiede il recupero locale definito dalla specifica.
> - Un riferimento, nessuna sostituzione, tutte le barre intermedie controllate, prima ripresa consumata una sola volta.
> - Rispetta pubblicazione, cursore, domini temporali, precedenze, dati mancanti e distinzione fra close storico e prezzo side live.
> - IMMEDIATE, B/C, geometria, costi, scadenze e comportamento dopo emissione restano invariati.
> - Nessuna interpretazione metodologica aggiuntiva: segnala eventuali conflitti prima di introdurre una soluzione.
>
> Preserva identità e output delle versioni precedenti. Assegna al candidato identità proprie e rendi durevole il nuovo stato: restore, pausa/STEP, crash e fencing non devono perdere il riferimento, ripetere valutazioni o riaprire child consumati. Estendi riconciliazione e Deep attraverso i percorsi già esistenti, senza nuova infrastruttura generale.
>
> Nell’app:
> - metodo v0.5 riconoscibile prima di Start;
> - attesa della risposta distinta da ingresso disponibile;
> - risultati sempre associati al metodo effettivo;
> - conteggi e identità del §7 in JSON e Copy report for chat, complessivi e mensili per la prova continua;
> - confronto in sola lettura v0.4/v0.5 sullo stesso pack.
>
> Verifiche:
> - fixture del §6 LONG/SHORT, comprese collisioni, uguaglianze, violazioni intermedie e i due raccordi temporali;
> - restore durevole prima/dopo preparazione, contraddizione, prima ripresa ed emissione;
> - riconciliazione dei conteggi, report parziali e confini mensili;
> - parità delle versioni precedenti con fixture fisse;
> - percorso E2E essenziale, typecheck/build e schemi.
>
> Esegui i controlli pertinenti senza ripetizioni inutili. La suite completa e Compose possono essere coperti dalla CI finale se consentito dalle istruzioni del repository; documenta esattamente cosa hai eseguito localmente. Non attendere né interrogare la CI.
>
> Solo dati sintetici limitati per le verifiche ingegneristiche. Nessuna acquisizione, estrazione Owner o valutazione economica. Non toccare lo stack dell’Owner.
>
> Prepara, ma lascia INACTIVE, il futuro confronto continuo v0.4/v0.5 sul pack già disponibile settembre–dicembre con inizializzazione di 35 giorni. La baseline v0.4 può essere riusata solo dopo controllo di compatibilità dei pin. Il candidato sarà lanciato esclusivamente dall’Owner dall’app, dopo accettazione tecnica e CI verde.
>
> Consegna commit finale, evidenze, limiti e decisioni eventualmente aperte. Termina i processi di verifica e rimuovi le risorse usa-e-getta; nessun ciclo di attesa residuo.
>
> READY FOR DIRECTOR REVIEW — WP-014 ONLY.

## Index of deliverables

1. **Kernel delta.** A selectable `btc.context-action.v0.5` / `mp004.rules.v0.5` release beside v0.2/v0.3/v0.4. Only the A RETURN child changes (MP-004 §§1–5): WAIT_RETURN → prepared reference → WAIT_RESPONSE → first decisive recovery evaluated once → ISSUED or RESPONSE_NOT_ISSUABLE; local contradiction, straddling contact and every inherited terminal keep their precedence. IMMEDIATE, B/C, scenario/anchor geometry (v0.4), costs, deadlines, the evaluator and post-issue behaviour are inherited unchanged.
2. **Identity and durability.** Own core/state/runtime/engine/report/reconciliation/Deep identities; rules manifest over the MP-004 delta and every inherited authoritative text; durable reference state through restore, pause/STEP, crash and fencing; old releases' identities and outputs preserved with fixed fixtures.
3. **Assurance.** Reconciliation and Deep extended through their existing per-method paths; no new general infrastructure.
4. **App.** v0.5 recognisable before Start (Workbench and live); waiting for the response distinct from entry available; results always labelled with the pinned method; MP-004 §7 counts and identities in JSON and Copy report for chat, total and monthly for the continuous run; read-only v0.4/v0.5 comparison on the same pack.
5. **Evidence.** §6 fixtures LONG/SHORT (collisions, equalities, intermediate violations, both §8 joints); durable restore before/after preparation, contradiction, first recovery and issue; count reconciliation, partial reports and month boundaries; previous-version parity; essential E2E; typecheck/build/schemas. Local checks are reported exactly; the full suite and Compose smoke are left to the final exact-SHA CI (Owner-operated).
6. **Inactive Owner plan.** Continuous v0.4/v0.5 comparison on the available Sep–Dec 2025 pack with 35-day initialization, reusing the accepted v0.4 baseline only after a pin-compatibility check; launched by the Owner from the app after technical acceptance and green CI.

Boundaries: synthetic bounded data only; no acquisition, Owner-DB extraction, economic evaluation, protected-period access, parameter search or next-package activation; the Owner stack is never touched.
