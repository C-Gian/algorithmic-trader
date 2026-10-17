# CAND-001/D1 — Diagnosi della politica v1 e ciclo metodologico

**Stato: READY.** Director, 17 ottobre 2026. Esecutore: Claude Code. Base main **63f2e429f0496ddc1f26c3de0cf486ca21d573aa** più il commit di questo incarico; sincronizzazione del checkout a cura di Gian. Leggere AGENTS, STATE, PRODUCT-CONTEXT §31, specifica CAND-001-v1.md e questo task. Nessun pull/fetch, anche dry-run.

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
Da compilare durante esecuzione/consegna. Nessun lavoro D1 ancora dichiarato svolto.
