# Stato del nuovo progetto

Aggiornato: 17 ottobre 2026. Responsabile: Director.

## Chiuso
UI simulata conclusa con prova positiva Owner. OBS-001 ACCEPTED TECNICAMENTE a bf3280e; calcoli/tabelle verificati nella review precedente. Rimane il limite di comprensione Owner, nessuna accettazione d'uso inventata o nuova macrofase UI.

## Attivo
**CAND-001/R1 DELIVERED** (Claude Code, 17 ottobre; in attesa di review, non ACCEPTED): motore 1.0.1, candidato e config invariati. Le tre correzioni sono riprodotte prima e coperte da test dopo. Run DEV offline e1.0.1 (`b1411502…`): decisioni, richieste e 78 trade identici a e1.0.0, netto −210,59 invariato. Report con sezione «Correzioni R1». Dettagli nella consegna di current_task.md.

Review DEV su ee7282f conclusa con tre correzioni circoscritte, non ACCEPTED.
Director ha rieseguito 28 test Python CAND, 8 test UI backtest e typecheck/build: passati. Ulteriori riproduzioni mostrano:
- funding vuoto certificato e buco segnalato ma ignorato nel calcolo, con costo mancante trattato come zero;
- trade interrotto da lacuna escluso dai totali; apertura episodio irrisolto in errore;
- prezzo giornaliero precedente presentato come corrente nella nuova vista.
Questi difetti non dimostrano un errore nei numeri DEV consegnati. R1 verifica l'impatto offline, senza nuovi dati.

## Metodo e evidenza
Decisione Director: mantenere candidato1.0.0 e config aed2c4ef627617d73972778097bbab5fb702ab5064ce9e6eb68ded2170ce4edf, nessuna revisione metodologica in questa macrofase. Congelate regole/soglie, implementazione ancora da correggere. Diagnosi negativa non identifica una modifica unica sufficientemente motivata.

Esiti riportati dall'esecutore: 78 operazioni ipotetiche 2023–2024, N0=1000USDT fisso, netto −210,59 (2023−115,87;2024−94,72), PnL reference−85,44, stress−397,80. Dati:27trade+24funding+24mark, manifest esterni. Il Director non ha ricalcolato autonomamente i75archivi/78trade reali in questa review. Il33% ricavato dal rapporto mediano non è il pareggio effettivo del ledger; report da precisare.

## Seguito e confini
Macrofase Astra già autorizzata: dopo accettazione R1, registrare base tecnica congelata e completare confronto2025 già esposto, non validazione indipendente; nessuna iterazione sui suoi esiti. Il prefisso osservativo parte dal2022-10-01 anche nella finestra2025, che riparte FLAT. In R1 nessun download o elaborazione2025, nessuno sblocco CLI.

2026protetto, vecchi studiINACTIVE, niente conto/chiavi/ordini esterni/stackOwner, leva/reinvestimento, nuova famiglia, ricerca parametri, piattaforma o restyling. DESIGN-001 approvato solo nelle definizioni osservative; modello economico CAND registrato separatamente. Macrofase aperta; prova concreta Gian ancora da svolgere, poi raccomandazione adAstra anche negativa.
