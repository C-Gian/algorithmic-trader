# HDP-001 and A v0.6 — Decision on the study references (authoritative addendum)

Registered 10 October 2026 on base `aff2a3d4747a71238c864129955a9f06fdbdb008`. The text in the section below is the authoritative decision **verbatim**, as relayed by the Owner. Only this header and the chronology are editorial.

**Pinned documents.** The decision is incorporated here and does not edit them. Their SHA-256 values are unchanged:
- HDP-001: [protocol](HDP-001-HOURLY-DIRECTIONAL-PERSISTENCE.md), [Director decision](HDP-001-DIRECTOR-CLOSURE.md), [exploration closure and freeze](HDP-001-EXPLORATION-CLOSURE.md).
- A v0.6: [design](A-V06-OPERATIONAL-EVALUATION-DESIGN.md), [orchestrator decision](A-V06-OPERATIONAL-EVALUATION-CLOSURE.md).

**Operational addenda updated by the executor** (not authoritative): [HDP-001 verification references](HDP-001-VERIFICATION-REFERENCES.md) · [A v0.6 frozen references](A-V06-OPERATIONAL-EVALUATION-REFERENCES.md) · [study exposure register](STUDY-EXPOSURE-REGISTER.md).

## Chronology

| Date (2026) | Commit | Document |
|---|---|---|
| 10 Oct | `7b5aaf2` | HDP-001 protocol and Director decision (seed 0) registered |
| 10 Oct | `3ee1278` | HDP-001 verification window proposal |
| 10 Oct | `cf18dbd` | HDP-001 exploration (accepted at this commit) |
| 10 Oct | `c8e982e` | HDP-001 exploration closure and verification freeze |
| 10 Oct | `6710474` | A v0.6 design and orchestrator decision registered |
| 10 Oct | `aff2a3d` | Executor reference addenda with open points |
| 10 Oct | this commit | This decision on those open points |

## Authoritative text (verbatim)

```text
Approvo entrambe le disposizioni, con le precisazioni sotto.
Sono chiarimenti necessari per eseguire fedelmente gli studi,
non modifiche delle ipotesi da valutare. Mi baso sul tuo
riscontro documentale; non dichiaro di aver verificato
autonomamente gli hash.

1. HDP-001: prevale la completezza prescritta dal protocollo

Nella verifica, ogni chiusura oraria utilizzata — per previsione,
riferimento o esito — deve appartenere a un’ora completa secondo
la semantica temporale esistente. Il solo close dell’ultimo
minuto non basta a certificare l’ora. Nessuna interpolazione.

L’esplorazione resta immutata. Registra la differenza fra la
costruzione esplorativa e quella richiesta nella verifica.
L’equivalenza numerica sui campioni esplorativi va attribuita
all’evidenza che la sostiene, senza estenderla ai casi con
minuti mancanti.

Confermo la distinzione proposta:
- lacuna identificata e correttamente rappresentata → UNAVAILABLE,
  griglia e maschera conservate;
- impossibilità di attestare identità, allineamento temporale,
  prezzi o maschere → risultato non valutabile.

Nessuna percentuale minima nuova. Il confronto deve usare
le stesse osservazioni valutabili per entrambi i previsori;
copertura ridotta o assenze concentrate limitano la conclusione,
anche quando il calcolo è tecnicamente corretto.
Il riferimento UP non viene ricalcolato.

2. A v0.6: congeliamo il comportamento, non l’inadeguatezza
degli strumenti

Non richiedo l’esecuzione dell’intero repository esattamente
a b47b997. Quel commit resta il riferimento autoritativo del
comportamento da valutare. Ammetto una futura build esecutiva
distinta, necessaria per preparare la finestra già approvata.

L’equivalenza deve coprire tutte le parti che possono cambiare
decisioni o esiti: costruzione e disponibilità temporale degli
input, inizializzazione, confini, selezione, gestione, costi
e valutatore. Non basta verificare i nomi di versione o il solo
modulo del metodo.

La futura verifica dovrà combinare confronto delle dipendenze
e del codice pertinente con prove sintetiche mirate.
Non chiameremo equivalenza generale il semplice passaggio di
qualche fixture. Ogni differenza capace di modificare decisioni
o risultati richiederà una decisione esplicita.

Nel presente step registra soltanto questa dipendenza,
distinguendo:
- riferimento congelato;
- identità già verificabili;
- build esecutiva e controlli di equivalenza ancora da completare;
- scadenza prevista dal disegno entro cui risolverli.

Il limite attuale del Workbench non autorizza a cambiare finestra,
dividerla in run mensili con reset o utilizzare periodi protetti.

Direttore, incorpora queste decisioni in un addendum autoritativo
collegato ai documenti pinnati, conservandone la cronologia.
Completa autonomamente i controlli documentali e delle identità
e chiudi lo step come riferimenti registrati, preparazione
esecutiva ancora incompleta, studi INACTIVE.

La predisposizione tecnica della finestra A sarà un incarico
separato; nessuna implementazione è attivata ora.
v0.6 e HDP-001 restano congelati.
```
