# A v0.6 — Disegno della valutazione operativa

Stato: disegno approvato; esecuzione INACTIVE.

## 1. Domanda e oggetto

Domanda primaria:

Applicando integralmente A v0.6 nella politica ordinaria del sistema, le opportunità effettivamente emesse producono un risultato modellato favorevole rispetto all’astensione, al netto dei costi inclusi e nei limiti dichiarati?

Il riferimento è l’astensione, con risultato operativo zero.

Si valuta la combinazione di lettura, conferma, ingresso e gestione. Non si identifica il contributo dei singoli segnali, non si misura il valore della MarketView senza call e non si confronta A con altre strategie.

## 2. Congelamento

Riferimento tecnico:
b47b997ee93513c7a358b49e961020705e4fbb85.

Sono congelati:
- MP-001 e i delta/disposizioni MP-002–005, con le rispettive chiusure;
- MP-005-PARAMETERS.json;
- btc.context-action.v0.6;
- adviser.core.v6;
- adviser.evaluator.v3;
- profilo storico base, percorso PRIMARY con ritardo 60 secondi;
- gestione, normalizzazione e regole ordinarie esistenti;
- questo disegno, finestra e regole di inclusione.

Prima dell’inizio devono essere registrate le identità complete del metodo, dell’implementazione e del profilo applicabile, coerenti con il riferimento tecnico. La CI non è dichiarata verificata da questo documento.

Gli hash del pack futuro saranno registrati quando il pack esisterà, insieme a provenienza e controlli d’integrità. Non sono una condizione già soddisfatta prima della raccolta.

A non viene eseguita artificialmente in isolamento. B/C, conflitti, priorità, slot e protezioni conservano il funzionamento ordinario. Le call B/C sono rendicontate separatamente e non entrano nel risultato economico primario A.

## 3. Popolazione primaria e registro diagnostico

La popolazione economica primaria comprende tutte le call A effettivamente emesse nella finestra, secondo le regole esistenti di inizializzazione e ammissibilità.

Per ciascuna call inclusa si segue l’intero percorso previsto, anche oltre la fine della finestra.

Non si esclude una call altrimenti ammissibile perché il suo owner è nato prima dell’inizio. Non si recuperano conferme del warmup che le regole esistenti rendono non ammissibili. Le emissioni successive alla fine non entrano nel primario.

Il registro degli owner è una contabilità diagnostica distinta:
- owner già presenti all’inizio, con stato e ammissibilità;
- owner nati nella finestra;
- conferme, emissioni e terminali;
- owner ancora aperti alla fine.

Mancata conferma e mancata emissione conservano ragioni distinte. Revisioni, sostituzioni dell’anchor e aggiornamenti dello stesso owner non diventano episodi indipendenti.

Nessuna call significa astensione, non successo economico o predittivo. NO_ENTRY comporta nessuna operazione modellata. Un percorso entrato ma irrisolto, ambiguo o censurato non viene imputato a zero né eliminato per ottenere un risultato.

## 4. Esito operativo

Si usa esclusivamente il percorso PRIMARY esistente:
primo ingresso ammissibile, open modellato, geometria congelata, protezioni, gestione e terminali del valutatore.

Misura primaria:
somma dei risultati normalizzati delle call A incluse, al netto dei costi effettivamente coperti, confrontata con zero dell’astensione.

La somma non è rendimento del capitale dell’Owner, non simula reinvestimento e non certifica esecuzione reale.

Fee e allowance del profilo base sono assunzioni registrate. Non coprono automaticamente impatto della quantità o costi effettivi dell’account.

Lo stress già disponibile resta un controllo secondario di sensibilità. Non si sceglie dopo il risultato il profilo più favorevole.

Il funding entra soltanto con copertura e attribuzione temporale certificate. Altrimenti il risultato è PRICE_NET_ONLY, al netto dei soli costi inclusi, e non consente una conclusione sul netto completo.

L’insufficienza d’integrità o la presenza di percorsi entrati senza risultato determinabile impediscono una conclusione primaria completa. Si rendicontano comunque quantità e ragioni dei limiti, senza inventare un trattamento economico.

## 5. Finestra e separazione temporale

Finestra approvata:
[2027-01-25T00:00Z, 2027-07-26T00:00Z).

Durata: 26 settimane. È una convenzione preventiva, non un calcolo di potenza o una quota di call.

Il congelamento deve essere completato prima dell’inizio. Se non avviene in tempo, la finestra decade: nessun recupero retrospettivo o spostamento automatico.

I periodi già esposti servono soltanto per preparare e controllare il disegno.

Inizializzazione: 35 giorni precedenti l’inizio, non valutati. La sovrapposizione temporale con HDP-001 è dichiarata. Non autorizza consultazioni intermedie e non rende i due studi statisticamente indipendenti.

Il tail serve esclusivamente a completare i percorsi inclusi. La sua estensione deriva dai limiti temporali e dalle regole del valutatore già registrati; non aggiunge opportunità e non termina quando il risultato diventa conveniente.

Nessuna consultazione intermedia dei risultati per modificare il disegno, nessun arresto opportunistico, adattamento o prolungamento automatico. Le esposizioni rilevanti per le decisioni di ricerca devono essere dichiarate.

Gennaio–agosto 2026 resta protetto. HDP-001 resta invariato.

## 6. Rappresentazione dell’incertezza

Unica procedura:
bootstrap a blocchi mobili di 168 ore sulla griglia completa della finestra.

- Risultato completo di ogni call A attribuito alla sua ora di emissione, anche quando termina nel tail.
- Ore senza call A: zero.
- Ingresso e uscita della stessa call non vengono ricampionati separatamente.
- 10.000 ricampionamenti.
- Generatore random.Random(0).
- Partenze uniformi fra tutti i blocchi interamente interni alla finestra.
- Nessuna circolarità; ultimo blocco troncato alla lunghezza richiesta.
- Intervallo percentile al 95%, Hyndman–Fan tipo 7.

L’intervallo rappresenta incertezza condizionata alla storia osservata. Non ricrea nuove sequenze di selezione, non aggiunge esiti non osservati e non garantisce protezione da dipendenze più lunghe o cambiamenti di regime.

Si riportano numero di ingressi e distribuzione settimanale, rendendo visibile la concentrazione dell’attività. Non esiste un requisito di due settimane operative o un’altra soglia numerica di sufficienza.

## 7. Interpretazione e decisione

Si mantengono separate:
- saldo osservato: positivo, nullo o negativo nel modello;
- intervallo bootstrap: sopra zero, comprendente zero o sotto zero;
- portata della conclusione: quantità e concentrazione dell’attività, dipendenza, copertura e limiti del modello.

Nessun intervallo da solo determina un verdetto sufficiente o autorizza promozione operativa.

Un saldo favorevole può motivare ulteriore valutazione.
Un saldo sfavorevole pesa contro la promozione operativa.
Attività scarsa o informazione insufficiente lasciano aperta la domanda.

Assenza di operazioni non è prova di efficacia. Nessun esito autorizza automaticamente nuove regole, filtri, timeframe, estensioni o ricerca di parametri.

## 8. Strumenti e autorizzazioni successive

Workbench, valutatore e record esistenti sono la base prevista. Il report aggregato da solo non basta per il bootstrap: occorreranno risultati per call con identità e tempi, tramite un accesso successivamente autorizzato.

Disponibilità dei dati futuri, copertura e sufficienza degli artefatti saranno verificate senza costruire automaticamente nuova infrastruttura.

Acquisizione, accessi ed esecuzione richiedono un incarico separato. Questa registrazione non li autorizza.
