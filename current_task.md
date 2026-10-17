# OBS-002/R1 — Cronologia causale, esiti importati e lettura dei contatti

**Stato: ACCEPTED** (Director,17ottobre2026,su024938e12af41b45974b0c32a9e1cb7821706f1b). Macrofase OBS-002 conclusa; review/decisione in OBS-002-results.md §12. Esecutore:Claude Code.

Review originaria su c8ac744, superata dalla chiusura in fondo: sono richieste le tre correzioni circoscritte sotto. La macrofase rimane interamente autorizzata; nessuna nuova autorizzazione ordinaria o passaggio ad Astra ora. Nessuna ipotesi operativa scelta o implementata.

## 1. Review della consegna e scelte confermate
Review indipendente Director in copia isolata: lettura popolazione, snapshot, esiti, tabelle, timeline e lettore; **15 test Python OBS-002 e 24 UI storici passati**, typecheck/build riusciti. Letta immagine dell'esecutore obs002-02-caso-seguito-1366. Nessun nuovo download, elaborazione reale DEV, ricalcolo dei6.582 esiti, né browser autonomo Windows. Conteggi reali, hash, cross-check con OBS-001 e riproducibilità integrale restano riscontri dell'esecutore.

Le sette scelte del report §7 sono accettate nel disegno, senza modificare convenzioni:
1. Un evento non ammissibile non è un nuovo movimento valido: non ritira la versione valida attiva. Le esclusioni sono registrate.
2. Le condizioni di arretramento e riarmo sono suffissi della stessa sequenza: valutare il suffisso da max(P1,ultimo tentativo) è coerente, inclusa la prima differenza col close della candela P1.
3. Uso di avg.dist/avg.slope già normalizzate con i loro missing; A zero rende indisponibili quelle misure, come previsto dall'osservatore.
4. Livello più vicino scelto sulla distanza grezza direzionale, identità nota anche quando la distanza normalizzata manca; con A positiva l'ordine coincide. Parità kind/id confermata.
5. Coincidenza delle ancore sulle candidateOpen è sufficiente nell'attuale osservatore con pivot immutabili e verso noto; non è selezione di nuove ancore.
6. Continuità dei contatori dall'inizializzazione confermata. I numeri osservati sul solo gruppo al confine restano evidenza dell'esecutore.
7. Pacchetti con righe OBS-001 delle sole origini selezionabili, blocco OBS-002 del caso e summary null sono coerenti con il riuso autorizzato del lettore.

Il circa40% di prime origini con profondità>1 è **effetto esplicito del disegno del Director**, non bug dell'esecutore. Si mantengono tutti i casi, profili e pesi registrati. Questo limite restringe l'interpretazione della parola «ripresa»; non autorizza a escluderli dopo gli esiti o a ricalcolare altri gruppi. Nessun nuovo orizzonte/riferimento numerico.

## 2. R1-A — timeline «knownAtT» conserva un'identità futura
Difetto riprodotto indipendentemente in src/obs002/cli.py, funzione timeline:
- versione iniziale con tentativo a1664649900000, poi REPLACE dello stesso gruppo a1664671500000 (costruttore sintetico long_case(90), P1 nuovo alla barra30 disponibile alla32);
- la timeline del primo tentativo filtra versioni per t0<=t e azzera retiredAt/retireReason se il ritiro è futuro;
- ma v.as_dict() include retire_facts e la riscrittura conserva **replacedBy=VER:LONG:1664609400000:1664663400000:1664671500000** e sameGroup=True;
- entrambi compaiono in knownAtT.groupVersionsSoFar nonostante la sostituzione futura non fosse nota. Cambiando il REPLACE futuro cambia l'informazione etichettata nota allora.

Correggere la proiezione temporale completa dei metadati di versione. Prima del ritiro, nessun replacedBy/sameGroup o altro fatto del ritiro deve apparire come noto. Dopo il ritiro, i fatti già disponibili si conservano; non eliminare globalmente la storia. Anche l'elenco tentativi della versione va limitato al momento, come già fatto. Verificare tutti i campi proiettati, non solo i due timestamp.

Questo rilievo riguarda la timeline derivata degli esempi, **non dimostra contaminazione della popolazione o dei6.582 esiti**: i tentativi/snapshot sono costruiti causalmente e i metadati di ritiro sono proiettati male successivamente.

Test mirato: stesso prefisso, due futuri con sostituzioni diverse (anche ritiro a fine studio versus REPLACE) → knownAtT completamente identico fino al cutoff, con successivi dati del ritiro esposti solo quando effettivi. Test deve fallire sulla consegna c8ac744. Conservare il test esistente sulle popolazioni; non sostituirlo.

**Artefatto reale:** correggere anche examples.json già consegnato, non soltanto il generatore. Rigenerare la sola proiezione causale delle timeline a partire dagli artefatti locali già registrati; nessuna necessità di rileggere prezzi, ricalcolare osservazioni/popolazione/esiti o selezionare nuovi esempi. Conservare l'originale e identificare il derivato corretto con hash, versione tecnica/provenienza e riferimento all'originale; può stare in una sottocartella R1. Un piccolo script di migrazione derivata o una funzione del comando è sufficiente, niente sistema generale. I pacchetti del lettore sono già costruiti da attempt/snapshot, senza quei metadati: non rigenerarli se non toccati.

## 3. R1-B — validatore OBS002_CASE accetta esiti contraddittori
Riproduzioni indipendenti sulla fixture sintetica valida synthetic-obs002-case.json, parseBundle:
1. complete resta true, ma outcome.favourable=null → accettato, come fosse un esito completo con una componente ignota;
2. complete=true, class=F_BEFORE_A, final=0, contactF=null e contactA=null → accettato. La vista dice «prima F, poi A» e nello stesso blocco «F non toccato · A non toccato».
Due test Director che richiedono rifiuto falliscono entrambi sulla consegna attuale. I test esistenti verificano class=null ma non queste contraddizioni.

Correggere il controllo **dei campi OBS-002 usati dal nuovo blocco** e delle loro relazioni, senza riaprire una revisione generale di tutti i formati:
- esito completo: final/favourable/adverse finiti e non null, escursioni non negative, classe valida e flags coerenti;
- esito incompleto: nessuna classe o misura completa inventata, motivi riconosciuti e tipizzati; mantenere il prefisso parziale come tale senza obbligarne la visualizzazione;
- esistenza/assenza dei contatti coerente con la classe, ordine coerente con minute/atOpen; contatti e intervalli tipizzati nell'H24 del caso, non timestamp fuori finestra;
- C/A/markers usati nella vista validi o mancanti secondo lo stato; orizzonte coerente con t+24h e identità del caso, flag di censura coerente con il confine autorizzato;
- non ricostruire il percorso di mercato nel browser e non trasformare queste verifiche in un motore analitico. Si tratta della coerenza del pacchetto già calcolato.

File invalido: rifiuto comprensibile dal selettore, studio già aperto conservato e nessun blocco retrospettivo falso. Vecchi bundle OBS-001 e pacchetti OBS-002 validi/incompleti continuano ad aprirsi. Pochi test discriminanti tramite selettore per i due casi riprodotti, più controlli unitari pertinenti per contatti/flags/markers e regressione valida/censurata. Nessuna suite generale o restyling.

## 4. R1-C — «quasi sempre entrambi» non è sostenuto dai conteggi
Dalle righe LONG/SHORT ALL della tabella principale:
- esiti completi4368;
- entrambi i riferimenti:614+624+3+617+571+1=**2430 (55,63%)**;
- uno solo:528+436+428+508=**1900 (43,50%)**;
- nessuno:22+16=**38 (0,87%)**;
- almeno uno:4330 (99,13%).

Quindi è quasi universale **almeno un contatto**, non entrambi. Correggere report §§4/8 e sintesi/consegna che lo ripetono. Le classi contengono informazione sia su uno/entrambi/nessuno, sia sull'ordine quando entrambi sono raggiunti; non dichiarare il riferimento ±A praticamente saturato in entrambe le direzioni. Sono conteggi aritmetici sui risultati già conservati, non nuova analisi. Non cambiare soglia/orizzonte/classi. Aggiungere una piccola riconciliazione aritmetica/test di riepilogo se necessario per evitare confusione any/both, senza nuova estrazione reale.

## 5. Verifiche, pubblicazione e prosecuzione
Prima riprodurre i difetti, poi correggere. Test mirati timeline/validatore/UI e regressioni pertinenti; typecheck/build per il lettore. Non rieseguire suite generale, OBS-001 intero, CAND o CI. Nessuna nuova acquisizione, lettura2025/2026, elaborazione popolazione/esiti reali o ricerca di combinazioni.

Verificare hash invariati di config, population.json, outcomes.json, summary numerico, lista degli esempi e pacchetti non toccati. Per examples.json cambia soltanto la proiezione dei metadati futuri nella sezione knownAtT; elenco/categorie/afterT e snapshot identici. Non aggiornare gli hash storici in modo da nascondere la correzione: nuovo derivato e provenienza. Ripetizione del solo passaggio di correzione → risultato deterministico. Report conserva cronologia e limiti.

Aggiornare OBS-002-results.md con R1, impatto e prove effettive, STATE e spazio consegna; passare DELIVERED, mai ACCEPTED. Commit/push pertinenti autorizzati, niente forcepush/pull/fetch. Nessuna nuova immagine dei casi validi se non cambia la vista; eventuale immagine di errore solo sintetica e pertinente. Non chiudere processi Owner.

Dopo la correzione il Director completerà la review e la lettura congiunta per l'unica conclusione prevista dal mandato. Non chiedere ad Astra un permesso ordinario e non implementare una ipotesi o v2. La macrofase resta aperta fino a questa conclusione.

## Spazio dell'esecutore
**Consegna OBS-002/R1 — Claude Code, 17 ottobre 2026.** Checkout verificato su `ccf2b3f`, senza pull/fetch. Commit `bc92a6d` (codice e test) più il commit di questa consegna (report §11, stato). Difetti riprodotti prima: la regressione R1-A e 20 dei 22 test R1-B falliscono sul codice consegnato.

- **R1-A.** Proiezione per elenco consentito in `src/obs002/timelines.py`: i fatti del ritiro compaiono solo se avvenuti entro t.
  - Test: tre futuri diversi danno `knownAtT` identico; i fatti restano dopo il ritiro effettivo; la migrazione è idempotente e coerente col generatore.
  - Derivato reale `R1/examples.json` `92b7b150…e785` dall'originale conservato `507c2bf3…d60b`, con `R1/manifest.json` e provenienza a `bc92a6d`.
  - Impatto: 20 campi (`replacedBy` e `sameGroup` dei 10 casi), nient'altro; due esecuzioni identiche.
- **R1-B.** Validatore OBS002_CASE per completezza, flag, A/riferimenti, orizzonte, censura e coerenza contatti/classe.
  - 22 test, inclusi i due casi dal selettore con studio conservato; fixture sintetica censurata nuova.
  - I bundle OBS-001, i pacchetti validi e i 10 reali si aprono ancora.
- **R1-C.** Report §§4/8 corretti con il testo originale citato: entrambi 2.430 (55,6%), uno solo 1.900 (43,5%), nessuno 38 (0,9%), almeno uno 4.330 (99,1%).
  - `contact_breakdown` con test; `R1/contacts-breakdown.json` `cf5812a5…bb1c`.
- **Invariati e verificati:** config, `population.json`, `outcomes.json`, `summary.json`, `examples.json` originale, `outputs.json`, i 10 pacchetti.
- **Verifiche:** 21 test Python OBS-002, 46 test del lettore, typecheck e build. Nessuna nuova elaborazione reale, nessuna suite generale, CAND o CI. Nessuna ipotesi operativa.


## Review e chiusura Director — 17 ottobre 2026
R1 accettato su024938e, codicebc92a6d. Lettura patch/provenienza/report e21test Python+46UI storici indipendenti passati,typecheck/build riusciti. Derivazione realeR1,hash immutati ed estrazione originale degli esiti restano evidenza dell'esecutore; nessuna nuova elaborazione reale Director.

OBS-002 concluso con **nessuna distinzione abbastanza interpretabile**, non una ipotesi automatica o una nuova regola. Interpretazione nel report§12: profili/coordinate ed esiti prefissati non forniscono un collegamento operativo motivato; le altre famiglie non sono escluse dalle mediane o dai controesempi. Il disegno mantiene movimenti oltreP0(1728/4372prime origini)e mescola fasi diverse: responsabilitàDirector,non bugClaude. Nessuna esclusione retrospettiva, soglia o orizzonte modificati.

Registro e casi conservati; pacchetti03/07/01 consultabili nel lettore esistente,nessun run o verifica manuale aGian. Passaggio conclusivo adAstra per l'eventuale seguito; nessun ulteriore incaricoClaude o nuovo studio. CAND immutato,2025escluso,2026protetto.
