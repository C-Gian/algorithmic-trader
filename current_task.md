# CAND-001/D1 — Diagnosi della politica v1 e ciclo metodologico

**Stato: ACCEPTED** (Director, 17 ottobre 2026, su 3b27b5d). Macrofase conclusa senza revisione giustificata; decisione in docs/research/CAND-001-diagnosis.md §9. Esecutore: Claude Code.

## Mandato e responsabilità
Astra accetta la chiusura APP-001 e autorizza l'intero ciclo: diagnosi v1 DEV, al massimo una revisione motivata nella stessa famiglia, confronto sull'intero DEV e consultazione nella stessa app. Nessun altro lavoro preparatorio UI. Chiusura possibile anche con nessuna revisione giustificata, indicando precisamente quale decisione non è sostenibile e quale informazione manca.

Il Director sceglie il problema e specifica l'eventuale nuova decisione. Claude estrae e riconcilia le evidenze, documenta fatti e limiti; non propone implementazioni strategiche autonome, filtri o soglie. Questo incarico eseguibile riguarda la diagnosi D1. La sua review e l'eventuale specifica v2 sono microstep della macrofase già autorizzata, non nuove richieste ad Astra/Owner. Non implementare v2 sulla sola diagnosi di Claude.

## 1. Confini e identità prima dell'analisi
Solo DEV [2023-01-01,2025-01-01) UTC, con prefisso osservativo dal 2022-10-01 dove realmente necessario. Binance Vision BTCUSDT perpetual USDⓈ-M già conservato. Nessun download, accesso rete per dati, 2025 (neppure gennaio di collaudo), 2026, stack Owner o vecchi studi. Non aprire i run ADDITIONAL_2025 per completare confronti. Eventuali dati oltre fine DEV restano esclusi, anche per completare un percorso.

Riutilizzare il bundle DEV accettato e i relativi manifest/input già verificati. Preferire il DEV e1.0.1, schema /2, inputHash adaa94c502… e bundle SHA256 b141150237e94a807817adea2d9fb6810f6eabc220d7db5ea3602d8b79b4944a, se presente; altrimenti un DEV compatibile con uguaglianza verificata di decisioni, richieste, trade e risultati. Registrare identificatori e hash completi effettivi. Non scegliere il run sulla base del risultato. Riconciliare 78 operazioni, 87 richieste, 814 episodi e netto non arrotondato (−210,59 alla visualizzazione). Config v1 SHA256 aed2c4ef627617d73972778097bbab5fb702ab5064ce9e6eb68ded2170ce4edf invariata.

La diagnosi precedente e gli esiti aggregati DEV sono già noti: questa non è preregistrazione dell'ipotesi originaria né analisi su dati nuovi. Prima di leggere nuovi percorsi individuali, pubblicare il presente piano e un piccolo elenco deterministico degli esempi selezionati con ID/tempi/categorie, senza commenti sul seguito. Conservare lista/hash anche negli output locali. Se una categoria è vuota, dichiararlo; non sostituirla con un caso scelto a vista.

## 2. Popolazione completa e selezione degli esempi
Un'unica diagnosi, con tutti i 78 trade e tutte le richieste/astensioni nel conteggio. Niente gruppi per SMA, volume, giornaliero o Fibonacci e nessuna ricerca di sottogruppi favorevoli.

Esempi dettagliati, su DEV intero, separati LONG/SHORT:
- primo trade con netto positivo, primo negativo, primo con stop aggiornato;
- prima astensione ABSTAIN_REWARD_RISK, prima INVALIDATED_DEPTH, prima richiesta REJECTED_PRICE.
Aggiungere il primo EXIT_STRUCTURE e il primo TIME_EXIT complessivi, se non già presenti. Ordinamento: tempo pertinente poi ID; deduplicare conservando tutte le categorie. Categorie di risultato a posteriori dichiarate, selezione cronologica non discrezionale. Massimo 14 casi, senza sostituzioni per rendere la storia convincente.

Per le astensioni ricostruire le ragioni e i dati noti fino alla conclusione dell'episodio. Non attribuire un profitto o una perdita a un'operazione mai aperta e non simularne qui un ingresso alternativo. I conteggi completi mostrano anche gli altri motivi di astensione, senza aprire altre analisi.

## 3. Un record diagnostico per trade
Generare fuori Git una tabella leggibile CSV/JSON con un record per ciascuna operazione e riferimenti ai fatti sorgente. Nessuna modifica al bundle originale.

Identità e decisione: ID episodio/richiesta/trade, verso, t0/call/ingresso, P0/P1/A0, ampiezza e durata gamba, profondità al trigger, numero di barre d'attesa, condizione effettiva di ripresa, struttura allora disponibile, stop iniziale, target, R0/G0 e rapporto, prezzo indicativo/riferimento/fill. Missing distinto da zero.

Percorso e tempo:
- istante/motivo/riferimento/fill d'uscita, durata, stop attivo all'uscita e provenienza (iniziale oppure aggiornato), decisioni e attivazioni degli aggiornamenti;
- prezzo e movimento direzionale alla prima chiusura 45m strettamente dopo l'ingresso, solo se la posizione è ancora aperta dopo il processo di esecuzione di quel momento; altrimenti «chiusa prima», non una quotazione successiva spacciata per osservazione durante il trade;
- massimo e minimo movimento direzionale osservato alle chiusure 1m effettivamente detenute, con tempi. Per una uscita intraminuto escludere il close e gli estremi del minuto d'uscita: il contatto non identifica l'ordine degli altri prezzi. Aggiungere come punto finale solo il riferimento d'uscita modellato, distinguendolo da una chiusura osservata. Se uscita a open, nessun prezzo successivo; includere il riferimento d'ingresso come origine zero;
- definizione fissata: z(p)=d*(p−entryReference)/R0, R0 geometrico della v1 basato sulla fill. Riportare max(0,z), min(0,z), z al riferimento d'uscita e differenza fra massimo osservato e z d'uscita. Sono descrizioni del percorso campionato, non MFE/MAE tick esatte, profitto catturabile o suggerimenti di vendere al massimo;
- tempo al massimo favorevole campionato, distanza iniziale dal target in R0, durata effettiva rispetto alle 24h con conteggi delle ragioni d'uscita. Nessun percorso dopo l'uscita per costruire un nuovo target o orizzonte.

Economia: pricePnLRef, effetto dei prezzi d'esecuzione, fee ingresso/uscita, funding, netto e rischio monetario iniziale. Identità da riconciliare: netto = pricePnLRef − slippageCost − feeEntry − feeExit + funding. Lo slippage è già nei prezzi fill, non sottrarlo una seconda volta. Riprendere stress e drawdown esistenti, non creare scenari di costi ulteriori.

Nelle timeline degli esempi distinguere sempre informazione disponibile a t (barre chiuse, conferma pivot, struttura, piano, decisione) da ciò che accade dopo. Per ogni aggiornamento/uscita discrezionale riportare t di decisione ed efficacia +60s, inclusi casi in cui un evento di esecuzione lo precede. Non trattare il ritardo di conferma del pivot come un bug o una prova che l'estremo fosse utilizzabile prima.

## 4. Riepilogo e interpretazione richiesta
Un report sintetico docs/research/CAND-001-diagnosis.md, con un solo quadro integrato:
- riconciliazione della popolazione e dei risultati con gli artefatti;
- DEV, 2023, 2024, mesi già disponibili: netto, numero, drawdown alla risoluzione esistente e concentrazione top5, senza riscrivere tutta la consegna precedente;
- sul totale: descrizioni (n e quantili P10/P50/P90) di primo movimento 45m quando disponibile, estremi campionati favorevole/contrario, restituzione del movimento favorevole, spazio iniziale/tempo; esclusioni e mancanze contate;
- ragioni d'uscita e stop iniziali/aggiornati: numero e contributi pricePnLRef/costi/netto, non attribuzione causale. Netto delle operazioni con aggiornamento non equivale all'effetto dell'aggiornamento;
- conteggi di episodi/richieste/astensioni e spiegazione semplice dei casi selezionati.

Queste sono dimensioni descrittive della stessa politica, non quattro backtest o trattamenti indipendenti. Non eseguire varianti «senza stop», «senza filtro», «target diverso», «uscita al massimo», né un benchmark sullo stesso futuro per suggerire la regola migliore. Non usare il 2025 nella motivazione, anche se risultati storici sono già pubblici.

Per ciascuna spiegazione plausibile distinguere: fatto osservato; informazione disponibile allora; decisione che v1 ha preso; cosa non possiamo dedurre. Classi: BUG, NOT_FAITHFUL_TO_DESIGN, COHERENT_BUT_NOT_USEFUL, COST_OR_ASSUMPTION_SENSITIVE, INSUFFICIENT_INFORMATION. Non dichiarare che il metodo è l'unica causa perché il codice passa i test. Un ingresso seguito da ribasso non prova un filtro corretto; movimento favorevole restituito non prova un'uscita anticipata disponibile.

Concludere con evidenze utili alla decisione del Director, anche se nessuna modifica è supportata. Non scegliere una soglia, una v2 o un nuovo indicatore. Per gli esempi indicare quale osservazione contemporanea potrebbe sostenere o contraddire una spiegazione, senza stimare il saldo di regole alternative.

## 5. Implementazione e verifiche proporzionate
Un piccolo comando diagnostico offline riutilizzando parser/contratti esistenti, separato dal motore decisionale: legge artefatti e soli file autorizzati necessari. Niente dipendenze, servizio, database o nuova pagina. CSV/JSON/lista/output estesi fuori Git nella cartella dati CAND-001; script, test, report aggregato e metadati pertinenti in Git. Provenienza e istruzione unica riproducibile; input immutabili, hash prima/dopo.

Se il bundle non conserva un'informazione, non inventarla: ricavarla dagli input autorizzati e dalle definizioni già fissate. Solo se indispensabile e motivato per iscritto prima: ammesso un passaggio diagnostico strumentato con v1 invariata su DEV, usando gli stessi dati e confrontando richieste/trade/risultati con il riferimento. Non pubblicare un nuovo backtest come evidenza strategica e non sovrascrivere i run. Se il fatto resta non ricostruibile, dichiarare il limite preciso.

Pochi controlli discriminanti: LONG/SHORT speculari, uscita a open/intraminuto senza prezzi posteriori, trade prima del primo close45m, latenza stop, identità costi, categoria vuota e deduplicazione/ordine. Un controllo di riconciliazione su tutti i record, nessun ricalcolo completo per ogni correzione di testo. Niente suite generale, suite UI/OBS non toccate o polling CI.

Non modificare la UI in D1. I casi già apribili si consultano coi meccanismi esistenti; riportare ID e momenti. Gli adattamenti strettamente necessari per distinguere v1/eventuale v2 e mostrare le decisioni cambiate si faranno nel relativo incarico dopo la scelta Director, senza restyling.

## 6. Consegna e prosecuzione della macrofase
Pubblicazione commit/push main autorizzata dei soli lavori pertinenti, senza force push o operazioni di sincronizzazione. Prima lista deterministica degli esempi, poi estrazione/analisi; conservare il legame tra commit e artefatti. Aggiornare questo spazio consegna e STATE; passare DELIVERED, mai ACCEPTED. Riportare comando, hash input/output, coperture/mancanze, controlli effettivi, limiti, percorso dei file locali. Non incollare migliaia di righe in chat.

Il Director farà review delle evidenze e deciderà al massimo un problema modificabile. Prima di qualsiasi esito v2 registrerà problema, nuova decisione causale, motivazione, svantaggi/controesempi e risultato che indebolirebbe la spiegazione. Confronto eventuale su tutto DEV a dati/costi/dimensionamento/esecuzione invariati, includendo operazioni aggiunte/eliminate/spostate e concentrazione/drawdown. Nessuna iterazione su 2025; 2026 protetto. Una revisione al massimo, nessuna ricerca combinatoria. Se non giustificata, chiusura motivata senza implementarla. Nessuna nuova autorizzazione ordinaria richiesta a Gian/Astra tra questi microstep; escalation solo per cambi sostanziali indicati dal mandato.

## Spazio dell'esecutore
**Avanzamento 1 — piano ed esempi pubblicati prima dei percorsi.** Checkout verificato su `12c195b` senza pull/fetch. Bundle DEV preferito presente e verificato (run `CAND-001-v1.0.0-e1.0.1-DEV-adaa94c502-aed2c4ef62`, SHA256 `b141150237e94a807817adea2d9fb6810f6eabc220d7db5ea3602d8b79b4944a`), config v1 `aed2c4ef…ce4edf`. Piano e 13 casi deterministici (nessuna categoria vuota) in `docs/research/CAND-001-diagnosis.md` §§1–2; lista locale `diagnosis/D1/examples-selection.json`, `listSha256` `7caade6984943a7e333660dc4ef702e6ed87022b58ec7c386e70ecd308a8c3be`. Comando `python3.12 -m cand001.diagnosis select` (solo bundle). Estrazione dei percorsi non ancora eseguita.

**Consegna D1 — Claude Code, 17 ottobre 2026.** Commit:
- `78f5fd8`: piano e lista degli esempi, prima dei percorsi;
- `3c639a8`: codice e test dell'estrazione;
- commit di questa consegna: report e stato.

File modificati: `src/cand001/diagnosis.py` (nuovo), `tests/test_cand001_diagnosis.py` (nuovo), `docs/research/CAND-001-diagnosis.md` (nuovo), questo file, `STATE.md`. Nessuna modifica a motore, ledger, config, bundle o UI.

Comportamento ottenuto:
- comando offline `python3.12 -m cand001.diagnosis select|extract`, separato dal motore decisionale; legge il bundle DEV accettato e i soli 27 ZIP trade 1m 2022-10…2024-12 verificati;
- un record per ciascuna delle 78 operazioni (decisione, percorso campionato in R0, gestione con decisioni e attivazioni, costi) in `algorithmic-trader-data/CAND-001/diagnosis/D1/trades.json` e `trades.csv`;
- timeline dei 13 esempi, riepilogo e provenienza con hash prima/dopo di ogni input;
- report integrato in `docs/research/CAND-001-diagnosis.md` §§3–8.

Controlli effettivamente eseguiti:
- riconciliazione nel comando su tutti i record: 78/87/814; netto `−210.58825128111891` uguale bit per bit al bundle; identità dei costi con residuo 0 su 78; motivi d'uscita; nessuna sovrapposizione; nessun contatto stop/target mancato nei minuti detenuti;
- input invariati: bundle `b1411502…`, config, lista e 27 ZIP;
- seconda esecuzione da commit pulito con `trades.json`, `trades.csv` e timeline identici byte per byte;
- 9 test mirati in `tests/test_cand001_diagnosis.py`, passati. Nessuna suite generale, UI o CI.

Esiti principali (descrittivi):
- nessun bug trovato;
- nessuna deviazione dal disegno accertata. Da confermare l'interpretazione delle contraddizioni valutate a t0 (124 `INVALIDATED_DEPTH`), il cui effetto su `SKIPPED_BUSY` non è ricostruibile dal bundle;
- PnL ai riferimenti −85,44 prima dei costi;
- movimento mediano nullo alla prima chiusura 45m;
- massimo campionato mediano 0,64 R0 contro target a 2,12 R0;
- costi assunti circa 0,28·R per operazione;
- tutti i 31 aggiornamenti e le 4 uscite per struttura avvenuti a decisione + 60 s.

Limiti: elenco in report §8. In particolare: non è una preregistrazione; prima della pubblicazione della lista ho letto il record di bundle del caso 1; si usano chiusure 1m e non tick; pivot e struttura vengono dal bundle e non sono ricalcolati; il riscontro è dello stesso esecutore. Nessuna revisione, soglia o v2 proposta.


## Review e chiusura Director — 17 ottobre 2026
Consegna 3b27b5d7f498c838643d43274a535b5d50c11877 accettata con limiti e decisione in docs/research/CAND-001-diagnosis.md §9. Lettura report/codice/spec e 9 test mirati indipendenti passati; nessun ricalcolo reale o suite generale. Estrazione sui 27 ZIP e riconciliazione integrale restano evidenza dell'esecutore; deviazione sulla lettura anticipata del caso 1 conservata.

**Esito: nessuna revisione giustificata.** Manca una condizione contemporanea motivata che identifichi quale ingresso, mantenimento o uscita cambiare; non soltanto un campione piccolo. Mediane del percorso, massimo favorevole e saldo dei trade aggiornati non identificano regole alternative. Nessuna v2 o confronto fittizio, nessuna ricerca di valori. Precisazioni sulle misure e interpretazioni t0/occupazione nel report §9, senza cambiare convenzioni o richiedere rielaborazioni.

Casi consultabili nel DEV salvato da registro/dettaglio esistenti; nessun nuovo lavoro UI, run o verifica di formule a Gian. Passaggio conclusivo ad Astra. Nessun nuovo incarico a Claude; v1 invariata e non promossa, 2025 escluso dal ciclo, 2026 protetto.
