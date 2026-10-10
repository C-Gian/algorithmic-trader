# A v0.6 operational evaluation — Decision on the statistical conventions and the candidate build (authoritative)

Registered 10 October 2026 on base `e52f23738f9f5160c6abc314a89e2bbb34d9e7cc`. The section below is the authoritative decision **verbatim**, as relayed by the Owner. Only this header and the chronology are editorial.

**Linked documents (unchanged).**
- [Design](A-V06-OPERATIONAL-EVALUATION-DESIGN.md) and [orchestrator decision](A-V06-OPERATIONAL-EVALUATION-CLOSURE.md).
- [Decision on the study references](HDP-001-A-V06-REFERENCES-DECISION.md).
- Operational references: [A v0.6 references](A-V06-OPERATIONAL-EVALUATION-REFERENCES.md) §8–§9.

**Identities named by the decision.**
- Behaviour reference `b47b997ee93513c7a358b49e961020705e4fbb85`.
- Designated executive build candidate `be44370f958a9b60f4b02e036102a23247f361d8`.

The statistical tool identities are listed in the references §9.1.

## Chronology

| Date (2026) | Commit | Step |
|---|---|---|
| 10 Oct | `be44370` | Study path technical preparation (candidate build) |
| 10 Oct | `21619c3` / `b2ebf20` | Ledger attestation correction |
| 10 Oct | `e52f237` | Offline bootstrap and ledger v2 protections, delivered while the decision text was still missing |
| 10 Oct | this commit | This decision registered |

## Authoritative text (verbatim)

```text
Approvo le due convenzioni e accetto be44370 come build esecutiva candidata designata, con riferimento comportamentale b47b997. L’accettazione riguarda la preparazione dello studio nei limiti documentati; non certifica equivalenza generale, CI verde o prontezza all’esecuzione reale.

1. Bootstrap

Ratifico un solo random.Random(0), estrazioni uniformi tramite randrange(N-L+1), ordine ricampionamento → blocco, troncamento finale e statistica pari alla somma dei valori orari ricampionati.

Restano invariati griglia completa, blocchi di 168 ore, 10.000 ricampionamenti e percentili registrati. Gli zeri rappresentano assenza di contributo economico attestata, mai dati mancanti o risultati irrisolti. L’intervallo conserva il ruolo interpretativo già deciso: non produce automaticamente un verdetto di efficacia.

2. Percorsi irrisolti

Ratifico la proposta: un percorso PRIMARY incluso con risultato indeterminabile impedisce saldo completo e bootstrap primario. Un eventuale subtotal dei risultati determinati deve essere chiaramente parziale e non sostenere conclusioni sul saldo complessivo.

Questa possibilità va distinta dal fallimento dei controlli d’identità o completezza: se non sappiamo quali record compongano correttamente la popolazione, non possiamo presentare il subtotal come risultato riconciliato dello studio. Resta valida la protezione introdotta nel registro.

3. Build e limiti residui

Il confronto sintetico comune e la verifica separata dell’estensione temporale sono evidenze pertinenti, con la portata dichiarata. Prendo atto della tua review e dei test dell’executor; non li presento come mie verifiche indipendenti.

La completezza non attestabile del journal owner rimane un limite della rendicontazione degli episodi. Non invalida automaticamente il primario economico se la completezza delle call incluse e dei relativi percorsi è attestata separatamente; impedisce però di dichiarare esaustiva la diagnosi delle mancate conferme o emissioni.

Direttore, completa nello stesso step:

- registrazione autoritativa delle due convenzioni, senza riscrivere la cronologia;
- SHA completi e identità di build candidata, riferimento e strumenti statistici;
- implementazione o allineamento del bootstrap offline, se ancora necessario, con sole prove sintetiche e risultati elementari verificabili indipendentemente.

Puoi gestire e chiudere autonomamente questi completamenti. Se modificano soltanto gli strumenti statistici, distinguine l’identità dalla build del prodotto; una modifica alle parti che determinano decisioni o esiti richiede invece di riesaminare l’accettazione della candidata.

Il termine del disegno non viene prorogato. Restano da soddisfare i controlli pre-esecuzione, inclusa la CI esatta riportata dall’Owner, oltre a dati, provenienza e autorizzazione separata. La durata reale resta non misurata.

Non serve un’altra proposta metodologica. Entrambi gli studi restano INACTIVE; v0.6 congelato. Nessuna acquisizione, dato Owner, prova economica o interrogazione CI è autorizzata da questa decisione.
```
