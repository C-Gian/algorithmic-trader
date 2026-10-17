# MOVE-001/R1 — Robustezza del lettore e ultima chiusura

**Stato: DELIVERED** (Claude Code, 17 ottobre 2026; in attesa di review del Director, non accettato). Incarico READY del Director, 17 ottobre 2026. Base da contenere nel checkout: 1235e64f03026b4b728c4c1ddc0422d0e5ea982a più il commit di questo incarico. Pubblicazione commit/push pertinenti autorizzata; sincronizzazione del PC a cura Gian, nessun pull/fetch/force.

## Esito della review
Consegna MOVE-001 non ancora accettata. Report originale e review Director in docs/research/MOVE-001-results.md §§1–9. Il Director ha rieseguito19 test Python,60 del lettore e build nella copia isolata, poi riprodotto due difetti sintetici. Nessun ricalcolo reale indipendente. Le nove scelte dichiarate sono ammesse con le qualificazioni §9.2; non cambiare semantica/convenzioni in funzione dei conteggi.

## R1-A — Importazione MOVE-001 prima della sostituzione dello studio
Riprodurre sul codice consegnato:
- cancellare case.ledger[0].B dalla fixture: parseBundle accetta, MoveCard fallisce leggendo price;
- cancellare candidateOpen dal P1 del fatto P1_PUBLISHED: accettato, timestamp necessario alla vista;
- aggiungere USABLE dopo ARCHIVE allo stesso timestamp: accettato, giudizio può diventare incoerente.

Correggere validateMoveCase sul contratto effettivamente letto: campi delle ancore e prezzi/timestamp finiti, campi richiesti per ogni tipo di fatto, identità/verso coerenti col caso, ancore BIRTH coerenti con quelle del caso. P1 completo, verso/disponibilità compatibili; motivi/giudizi/conclusioni riconosciuti; nessun evento dopo la conclusione, anche allo stesso timestamp; nessun USABLE senza P1 o dopo sospensione, nessuna seconda nascita/pubblicazione/conclusione. Rispettare l'ordine valido degli eventi concorrenti del motore, per esempio nascita+sospensione e P1+perdita alla stessa chiusura. Non ricalcolare pivot/prezzi nel browser e non richiedere nuovi dati.

Un file scorretto va rifiutato dal selettore con errore preciso, lasciando studio precedente e momento intatti. ViewGuard resta difesa aggiuntiva; non sostituisce l'importazione corretta. Non limitarsi alle tre mutazioni: verificare tutti i campi usati da descrizione/stato della nuova scheda, con pochi test parametrizzati pertinenti. OBS-001/OBS-002 validi restano leggibili.

## R1-B — Consultare l'ultima chiusura disponibile
Riprodurre con la catena di move001.fixture.build: scegliere l'ultimo riferimento (aperto a fine dei10giorni), ricreare package con lo stesso ledger. OPEN_AT_END a1665446400000 non è selezionabile: origins termina a1665443700000, pur avendo già la candela completa che termina a end.

Per MOVE001_CASE rendere selezionabile anche il cutoff uguale al confine finale quando rappresenta l'ultima barra disponibile: i minuti restano [inputStart,end), nessun dato dopo end. Aggiornare in modo coordinato generatore, validatore e navigazione dove necessario. Non estendere indiscriminatamente le origini OBS-001/OBS-002, che hanno altri contratti. Verificare apertura, selezione/avanzamento fino all'ultima chiusura, stato OPEN_AT_END, ricaricamento/ritorno già previsti dove toccati. Coprire anche ARCHIVE esattamente sull'ultima chiusura e nessun completamento/perdita inventati. Nessun nuovo controllo/prodotto UI oltre alla correzione del cursore.

## Dati, output e versioni
Semantica1.0.1, config, selezione categorie, osservatore, CAND e output numerici reali immutati. Nessuna applicazione reale del ciclo, ricalcolo DEV, nuova lettura di prezzi o download;2025 fuori,2026 protetto.
La correzione del generatore di consultazione richiede versione tecnica coerente dichiarata, senza fingere un nuovo calcolo semantico. I pacchetti vecchi validi devono restare apribili. Verificare sinteticamente il generatore; sui6 pacchetti reali già registrati basta controllo di compatibilità del nuovo lettore, senza rigenerarli. Se servisse modificarne uno, dichiarare il caso preciso invece di sovrascriverlo silenziosamente.

## Verifiche e documentazione
Prima riproduzioni fallenti sul codice consegnato, poi test discriminanti per le due correzioni. Lettore e consultazione mirati, typecheck/build, prova integrata sul caso sintetico di fine copertura e un pacchetto reale già disponibile. Non rieseguire tutte le suite, CI o storia per abitudine. Non toccare processi Owner.

Aggiornare MOVE-001-results.md con correzioni, versioni, prove effettive e impatto; qualificare verify.py come controllo aggiuntivo di invarianti dell'autore, non seconda ricostruzione indipendente completa. Non cambiare i numeri del report o dedurre risultati nuovi. Non trasformare le1265 barre in numero di movimenti/occasioni né i112 rifiuti in soli blocchi del posto.

Consegna a Director, stato DELIVERED/non ACCEPTED; STATE breve. Nessuna nuova ipotesi o strategia. Non chiedere un'altra autorizzazione ordinaria.

## Consegna dell'esecutore — MOVE-001/R1, Claude Code, 17 ottobre 2026
Checkout su `e3c77f8`, senza pull/fetch. Codice e test nel commit `fix(MOVE-001/R1)`; report §10 e stato nel commit di consegna. Difetti riprodotti prima: 24 rifiuti R1-A, la prova dal selettore e i test dell'ultima chiusura falliscono su `1235e64`.

- **R1-A.** `validateMoveCase` controlla ancore e campi per tipo di fatto, identità e verso, ancore della nascita uguali al caso, P1 completo e qualificato, motivi e giudizi riconosciuti, transizioni ammesse, nessun fatto dopo la conclusione. Restano accettati gli ordini concorrenti del motore. Il file scorretto è rifiutato dal selettore con studio e momento intatti.
- **R1-B.** Generatore `move001.consult/2`: ultima origine fino alla fine copertura inclusa. Solo per MOVE001_CASE l'origine può coincidere con `periods.end`; minuti [inputStart, end). OBS-001 e OBS-002 invariati.
- **Impatto.** Semantica 1.0.1, config, ciclo e output reali invariati (`outputs.json` `10dd7fc6…03d4`). I 6 pacchetti reali MOVE-001 e i 10 OBS-002 sono compatibili e non rigenerati; nessun caso reale è toccato da R1-B.
- **Verifiche.** 22 test Python MOVE-001, 90 test del lettore, typecheck e build; prova integrata nel browser sul caso sintetico di fine copertura, su un pacchetto reale e sul rifiuto dal selettore. `verify.py` qualificato come controllo aggiuntivo dell'autore.
