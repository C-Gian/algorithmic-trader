# MP-003 — Astra design closure
Date: 2026-10-06. Reviewed commit: eb091648cc60df66e6c89b0740ba18e608af28fe.
Owner-relayed Astra response follows verbatim.

**CHIUDIBILE** — MP-003 v0.2 al commit `eb091648cc60df66e6c89b0740ba18e608af28fe`.

Il §4 e le tre nuove fixture risolvono il precedente blocco:

- **Prima del primo arm:** restano spend e withdrawal ereditati; il semplice contatto con B non introduce un terminale.
- **Dal primo arm effettivamente pubblicato:** tempo e cursore fissano l’origine del controllo della destinazione. Source bar e contatti già ammessi non valgono retroattivamente; gli intervalli a cavallo della pubblicazione hanno una gestione esplicita dell’ambiguità.
- **Dopo la perdita dell’anchor:** il controllo resta attivo in WATCH con `ever_armed=true`. Sostituzioni e supersessioni non ne spostano l’origine.

La precisazione è coerente con le precedenze: un terminale strutturale o di destinazione impedisce la sostituzione; una sostituzione ammessa opera prospetticamente e non può ricevere conferme retroattive. Resta inoltre intatta l’immutabilità dopo la prima conferma, inclusi WAIT e call.

**Nessun finding bloccante residuo o nuovo introdotto dalla correzione.** La chiusura riguarda il design; non attiva il piano v0.4 né ne certifica l’efficacia economica.

Quindi **questa revisione è approvata: non vedo altri blocchi nel design**. Puoi passare il mio esito al Director.

Ora tocca a lui:

1. Registrare la chiusura di MP-003 v0.2.
2. Preparare il lavoro circoscritto per far implementare a Claude il metodo v0.4, con le fixture concordate.
3. Dopo implementazione e verifiche, autorizzare i backtest che lancerai tu dall’app.

In pratica: **abbiamo chiarito quando uno scenario può sopravvivere e attendere un nuovo ingresso, senza tenerlo artificialmente vivo né modificarlo dopo la conferma**. Ora possiamo costruire questa logica; se produrrà opportunità valide lo dovranno mostrare i test, non questa approvazione.
