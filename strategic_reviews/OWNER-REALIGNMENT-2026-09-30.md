# Owner realignment — 30 September 2026

Status: **OWNER-DIRECTED PRODUCT REQUIREMENTS**  
Canonical direction: ../FOUNDATION.md v3.0  
Reviewed base: 38b2fb6bde52714b8875a282e852742bf13df7c0

## Per il Direttore — leggere prima di riprendere il lavoro

Gian ha chiarito direttamente il prodotto: un consulente di trading BTC con call utilizzabili, non un motore di ricerca su singoli segnali. Capitale, quantità, leva e ordini sono sempre decisioni manuali sue.

La homepage deve essere una board viva: grafico, risultati delle osservazioni che cambiano in pagina, opinione direzionale con orizzonte e, in evidenza, call attiva con ingresso ancora valido, target, stop e durata prevista. La call può restare buona dopo il primo segnale; deve restare disponibile finché condizioni e margine lo giustificano. L'opinione può essere rialzista/ribassista anche senza una call.

L'Owner avvia personalmente i backtest importanti dalla web app, guarda candele/analisi/call/esiti e copia un report comprensibile nella chat. Codex verifica il codice con controlli brevi, poi consegna READY FOR OWNER BACKTEST. Niente lunghe valutazioni nascoste in CLI.

Uso locale intermittente: avvio dopo lavoro, dati storici riutilizzati e recupero incrementale. Niente PC H24 o campagne quotidiane di decine di ore. La raccolta prospettica non può essere il blocco permanente per costruire e valutare il prodotto.

Integrare le conoscenze professionali necessarie in un processo unico. Valutare esplicitamente ciclica/timing e contesto eventi/news insieme a struttura, momentum, partecipazione, volatilità e vincoli pratici. Non significa sommare indicatori né supporre che ogni tecnica funzioni: significa non escluderle automaticamente in favore di un prototipo comodo.

## Correzione della precedente proposta Astra

La specializzazione pullback era un candidato ragionevole, ma è diventata una prescrizione troppo stretta per il prodotto richiesto. L'Owner non ha accettato che quel candidato definisca l'intero obiettivo o che ciclica/news siano escluse per principio.

Non si butta M3. Si rivede la traduzione professionale e si riporta lo sviluppo a versioni complete e valutabili dell'applicazione. RP-001 resta evidenza di un tentativo; i suoi limiti non impongono di attendere indefinitamente né autorizzano ad aggiustare le soglie sui vincitori noti.

Un prodotto che non genera mai call non passa l'accettazione. La frequenza va diagnosticata insieme alla qualità: nessuna quota artificiale di trade, ma nemmeno l'assenza sistematica di utilità spacciata per prudenza professionale. Sei casi senza call non bastano da soli a stimare la frequenza generale.

## Immediate Director handoff

Read Foundation v3.0 and replace task.md with the first bounded delivery package. Produce a concise whole-process specification and a short vertical delivery sequence covering app/data/report requirements alongside real advisory behavior. Define only the source questions actually needed to make those choices.

Do not restart an open-ended RP-001 study or ask the Owner to design the strategy. Do not freeze old numerical conventions by default. Preserve causal correctness, source limits and honest historical evaluation.

Initial delivery priorities:
1. Reusable data and an Owner-readable launch/progress/copy-report path, reusing existing replay.
2. One coherent real adviser with all its dependencies explicitly scoped, persistent calls and honest missing-context states.
3. Owner-run integrated diagnostics: coverage, rejection reasons, call frequency/duration and outcomes.
4. Bounded improvements with versioned development evidence, then protected evaluation.

No implementation or data download occurred in this documentation realignment. No new profitability claim is made.

## Repository reconciliation

| Surface | Action |
|---|---|
| FOUNDATION.md | Replaced by v3.0, the single canonical directive. |
| STATE.md | Retains M3 facts; replaces old next action and narrow research mandate. |
| task.md | Replaces RP-001 execution with the Director's immediate delivery-plan handoff. |
| AGENTS.md | Adds Owner-run evaluation boundary, authority precedence and no repeated/H24 data dependency. |
| README.md | Corrects stale milestone/integration language; distinguishes existing operation from required capabilities. |
| Prior strategic reviews/dispositions | Visible historical scope notice; original bodies retained for audit. |
| RP-001 brief and first_trader specifications/conventions | Historical scope notices; no active mandatory completion gate. |
| source_notes/, registries, frozen case data/labels/outcomes, implementation and schemas | Preserved; research directory/index notices govern historical scope. |

The preserved underlying documents may contain former prescriptions. Their notices and the canonical authority order explicitly make these historical, not competing current instructions.

## Istruzioni della chat/progetto fuori da Git

Questa modifica non può cambiare le Project Instructions private di altre chat. L'Owner deve aggiornare l'eventuale copia esterna. Testo di sostituzione:

> Per Algorithmic Trader, leggi sempre FOUNDATION.md v3.0 o successiva, STATE.md, AGENTS.md e task.md dall'ultima main. La chiarificazione diretta dell'Owner del 30 settembre prevale sui precedenti prompt/review. Costruisci un consulente BTC con analisi integrata e call persistenti; capitale, leva e ordini restano umani. I backtest importanti vengono avviati dall'Owner nella web app e producono report copiabili. Uso locale intermittente, storico fisso riutilizzato, nessun obbligo H24. Non riprendere automaticamente il mandato pullback-only/RP-001: è storico. Segui il passaggio operativo corrente in task.md e consegna versioni complete, comprensibili e valutabili; non sostituire il prodotto con ricerca infinita o NO_TRADE permanente.

Questo testo rimanda alla Foundation invece di duplicare tutte le regole e crearne un'altra versione divergente.

