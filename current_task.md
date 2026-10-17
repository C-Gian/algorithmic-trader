# MOVE-001 — Implementazione isolata e applicazione descrittiva DEV

**Stato: IN_PROGRESS** (Claude Code, 17 ottobre 2026; incarico READY del Director, 17 ottobre 2026). Base: 03510afed13732c2fc46b5bb4e95626986c95ca0 più il commit che pubblica questo incarico. Astra approva la candidata semantica e autorizza l'intera macrofase. Esecutore: Claude Code nel checkout preparato dall'Owner.

## Obiettivo e autorità
Implementare il ciclo causale e verificare se rappresenta concretamente movimento–reazione, senza strategia o valutazione economica. Contratto completo: **docs/research/MOVE-001.md §§1–12, versione1.0.1**; §§11–12 completano le precedenze. Leggere AGENTS, STATE, contesto funzionale e EXPOSURES; usare osservatore e acquisizione locale esistenti, senza rileggere l'intero archivio.

Il Director ha fissato semantica, conteggi ed esempi. Claude sceglie l'organizzazione tecnica, non soglie, popolazioni o conclusioni metodologiche. Nessuna ulteriore autorizzazione ordinaria fra test, applicazione reale, adattatore e consegna. Blocco solo preciso/conflitto sostanziale, non domanda generica sul seguito.

## Comportamento vincolante
- Nuova popolazione specifica Q/B/P0 + nuova rottura nota, non correzione retrospettiva OBS-002.
- Formazione occupa il principale; strutture qualificate ignorate registrate e consumate, senza adozione ritardata. Suspense per test/struttura sostituibili soltanto con nuova evidenza/freschezza; recupero non riattiva.
- Opposizione strutturale già alla nascita: nascita conservata, sospensione immediata distinta; non confondere attesa P1 con sospensione metodologica.
- Eventi disponibili alla chiusura già valutabili. Nessun retouch automatico di P1 tramite la propria candela candidata. P1 fissato causalmente; revisioni future non riscrivono.
- Gap: archiviazione indeterminata, niente fatto inventato nel tratto ignoto; nuovo segmento e nuove ancore. Fine copertura amministrativa, non conclusione di mercato.
- Precedenze e identificazione del candidato esattamente §11; conteggi riconciliati e durate censurate §12.

## Esecuzione autorizzata, in ordine
1. Verificare repository/branch/base e modifiche locali senza sovrascrivere. Niente pull/fetch/reset/stash: sincronizzazione a cura Gian.
2. Implementare modulo separato MOVE-001 e CLI proporzionata, riusando OBS-001 invariato. Registrare config/MOVE-001-v1.json: versione1.0.1, formule/convenzioni, finestre, schema dei conteggi, selezione casi e quantile lineare. Test sintetici mirati §12.4. **Commit e push di contratto/config/codice/test prima di leggere i dati reali per MOVE-001.** Registrare SHA del gate nel report.
3. Un'applicazione descrittiva: soltanto i 27 file trade1m già verificati [2022-10-01,2025-01-01), prefisso prima2023 e DEV2023–2024. Riutilizzare controlli hash/provenienza/copertura locali; nessun download. Continuità del ciclo dal prefisso. Conservare output/versioni/provenienza fuori Git, sotto C:\Projects\algorithmic-trader-data\MOVE-001. Ripetizione ammessa per identità byte dei risultati, non nuova variante.
4. Produrre ledger causale, riepiloghi totale/anno/mese/verso, rifiuti del posto, durate e stock riconciliati, casi cronologici preregistrati. Nessun esito24h o rendimento.
5. Adattare minimamente il lettore esistente per MOVE001_CASE, grafico/ancore/timeline noto-allora e messaggio non operativo. Nessun nuovo esploratore. Controlli del contratto e prova visiva su pochi casi reali; non rieseguire storia per testi/layout.
6. Report docs/research/MOVE-001-results.md: comandi, versioni/hash, gate prima dei dati, conteggi/durate, casi vuoti, limiti, eventuali bug e impatto. Annotare le scelte tecniche non metodologiche. Distinguere verifiche proprie da quelle del Director. Spiegare a Gian in poche righe come consultare un caso, senza chiedergli di controllare formule.
7. Commit/push pertinenti senza force, aggiornare questo task e STATE a DELIVERED, non ACCEPTED. Non tornare ad Astra direttamente: attende review/conclusione Director.

## Verifiche e consegna
Test discriminanti per simmetria, disponibilità/versioni pivot, precedenze, formazione, sospensione, collisioni, nuova identità, candidati bloccati, gap e invarianza al futuro. Controlli del lettore solo se toccato, typecheck/build e prova integrata pertinente. Niente suite generali, polling CI o processi Owner chiusi. Raw/output e dipendenze fuori Git. Il report deve rispondere alla domanda di rappresentabilità anche se i casi sono pochi o la candidata resta spesso sospesa; nessun ritocco automatico.

## Esclusioni
CAND-001/config/costi e OBS-002/output precedenti invariati. Nessun download, lettura2025 o2026, simulazione di operazioni, PnL, nuovo segnale, ottimizzazione, strategia, API exchange, conto, ordine reale, nuovo frontend o restyling. Questa è una rappresentazione sperimentale, non una promozione operativa.

## Avanzamento e consegna dell'esecutore
**Avanzamento 1 — gate prima dei dati.** Checkout verificato su `9b536a2`, senza pull/fetch. Pubblicati prima di leggere dati reali per MOVE-001:
- `config/MOVE-001-v1.json` (versione 1.0.1, schema dei conteggi, durate, selezione dei casi, quantile lineare);
- modulo isolato `src/move001/` (ciclo, conteggi, casi, pacchetti, CLI);
- 18 test sintetici in `tests/test_move001.py`.

Nessun dato reale MOVE-001 ancora elaborato.
