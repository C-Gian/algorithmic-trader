# Algorithmic Trader

Nuovo progetto BTC di Gian: analisi continua, opportunità motivate e futura gestione automatica, inizialmente in demo.

**Stato attuale:** fondazione documentale e tre utilità Python isolate. Non sono ancora presenti algoritmo, applicazione o collegamento exchange. Nessuna operatività reale autorizzata.

## Da dove partire

| File | A cosa serve |
|---|---|
| [Documento funzionale completo](docs/functional/PRODUCT-CONTEXT.md) | Obiettivo, decisioni, ragioni, storia utile, requisiti e questioni aperte. Si può consegnare da solo a una nuova chat. È la foundation del progetto. |
| [STATE.md](STATE.md) | Situazione effettiva e prossima macrofase da definire |
| [current_task.md](current_task.md) | Unico incarico corrente, scritto da Astra o Director |
| [AGENTS.md](AGENTS.md) | Regole di lavoro, responsabilità e verifiche |
| [CLAUDE.md](CLAUDE.md) | Punto d'ingresso per Claude Code |

Non creare una seconda foundation o un altro file di task parallelo. Il documento funzionale è il riferimento per **che cosa** vogliamo; lo stato dice **che cosa esiste**; il task dice **che cosa fare adesso**.

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
