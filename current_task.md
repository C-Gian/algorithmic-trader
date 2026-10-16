# Incarico corrente — OBS-001 osservazioni calcolate e primo studio nell'app

**Stato: IN_PROGRESS — motore e convenzioni registrati, acquisizione in corso (vedi Spazio dell'esecutore).** Macrofase completa autorizzata dalla disposizione Astra trasmessa da Gian il 16 ottobre 2026, dopo la chiusura UI al commit baa1e762703f7dfd01f870061dba2a1c691326ce.
Responsabile specifica e review: Director. Esecutore: Claude Code.
Questo task è la registrazione ex ante delle convenzioni **OBS-001/v1**: completare tutti i microstep, dal sintetico all'acquisizione, elaborazione reale, integrazione e prima tabulazione. Nessuna ulteriore autorizzazione ordinaria fra i microstep. Non fermarsi a un motore sintetico. La consegna UI accettata resta nella storia Git a baa1e76.

## 1. Risultato richiesto e autorità

Gian deve vedere nella dashboard esistente prezzi storici reali BTCUSDT perpetual USDⓈ-M e sei famiglie di osservazioni calcolate solo da informazioni disponibili al tempo scelto. Deve poter avanzare, cambiare 45m/1D e consultare separatamente il seguito retrospettivo a 24 ore e il confronto descrittivo mensile previsto sotto.

DESIGN-001 è approvato **solo per le definizioni osservative delle sezioni 5–6**, con chiarimenti vincolanti di questo task. Non sono attivati il resto del documento, warmup globale 54 barre, modello economico, barriere 2A, prossimità come criterio decisionale, R2/R3, orizzonti 3h/72h, coorte principale limitata alle 00:00, incroci SMA come ulteriore raggruppamento o finestre protette. Nessuna strategia, aspettativa predittiva, ingresso, ordine o conto generati.

AGENTS resta valido: un solo task; dettagli tecnici reversibili risolvibili dall'esecutore; cambi di convenzioni o gruppi al Director prima di procedere. Non riattivare vecchi studi o codice del vecchio motore.

## 2. Soluzione tecnica proporzionata e riproducibilità

Scelta Director: pipeline batch Python, preferibilmente sola libreria standard (CSV/ZIP/hash/HTTP/statistiche/JSON), in un piccolo modulo nuovo sotto src/; test mirati sotto tests/. Usare Python già presente, minimo 3.11, registrare versione effettiva; non installare runtime sul PC senza istruzione. Riusare le tre utilità locali solo se pertinenti e dopo lettura; nessuna suite pregressa generale. Nessun pandas, TA framework, DB, Docker, servizio permanente, streaming o secondo frontend necessari.

Dashboard React/TypeScript/Vite esistente: aggiungere provider storico e adattare in modo esplicito il contratto di presentazione, oggi vincolato a simulated=true e serie illustrative. Usare un discriminante reale di modalità/datasource, non cast o flag fittizi per forzare dati storici nel contratto simulato. Componenti consumano osservazioni e serie preparate: nessun calcolo del motore nel rendering, nessuna deduzione di segnali di trading.

Percorso: ZIP/CSV locali → minuti validati → aggregati → eventi/snapshot causali → bundle JSON versionato leggibile dalla stessa app; esiti e riepiloghi in sezione separata del bundle. Il caricamento locale può avvenire con file picker “Apri studio storico”; niente server dati. File system API privilegiata non necessaria. Metadati e validazione del formato in import: errori leggibili, nessun fallback silenzioso alle fixture.

Cartella dati scelta: directory sorella del checkout, es. C:\Projects\algorithmic-trader-data\OBS-001; ricavare dal percorso del checkout o permettere --data-dir. Non esplorare altre directory dell'Owner, vecchi dataset, account, processi o stack. Verificare che output/raw non entrino nel working tree; aggiungere .gitignore per incidenti plausibili. Nessuna cancellazione di file dell'Owner.

CLI con comandi espliciti per acquisire, controllare, elaborare e riepilogare; un comando orchestratore riproduce la catena autorizzata. Elaborazione offline possibile dopo acquisizione; niente aggiornamenti automatici dello storico all'avvio UI. Pubblicare codice, configurazione congelata e piccole fixture sintetiche; ZIP, CSV reali e bundle temporali restano locali fuori Git.

Ogni run conserva: versione schema, OBS-001/v1, hash della configurazione di convenzioni, commit software, versione runtime, manifest degli input, hash output, tempi e comandi. Prima di calcolare esiti creare manifest/config e registrarne hash e commit del task nella consegna. Non serve fermarsi o richiedere conferma. Timestamp di esecuzione e manifest globale del dataset sono metadati run, non devono far risultare diversi gli snapshot dello stesso prefisso in test causali.

Performance: leggere minuti una volta, calcoli incrementali/finestre limitate; niente ricalcolo dell'intero storico a ogni clic. Riportare durata e dimensioni effettive, ottimizzare solo un collo di bottiglia osservato. Un avanzamento per stadi e messaggio di errore bastano; niente infrastruttura di job.

## 3. Fonte, intervalli, autorizzazione pubblica e controlli

Unica fonte candidata autorizzata: Binance Vision, percorso
https://data.binance.vision/data/futures/um/monthly/klines/BTCUSDT/1m/BTCUSDT-1m-YYYY-MM.zip
con file gemello .zip.CHECKSUM. Scaricare **solo sette mesi: giugno–dicembre 2025**, senza dati aggiuntivi.

- Inizializzazione input: [2025-06-01T00:00:00Z, 2025-09-01T00:00:00Z).
- Studio/origini: [2025-09-01T00:00:00Z, 2026-01-01T00:00:00Z).
- Input totale: [2025-06-01, 2026-01-01) UTC; **nessun tail nel 2026**, neppure il vecchio tail 06:05.
- Consentiti metadati pubblici dello strumento e documentazione della fonte; nessun login/API key. Verificare symbol=BTCUSDT, base BTC, quote/margin USDT, contractType PERPETUAL, segmento UM e prezzo negoziato klines. Salvare risposta pubblica pertinente e data; metadati correnti non certificano condizioni storiche di esecuzione. Se l'endpoint pubblico è geobloccato o identità non verificabile, riportare errore preciso e documentazione alternativa ufficiale; nessun aggiramento o sostituto silenzioso.
- Vietati spot, continuousKlines al posto della serie dello strumento, mark/index, funding, order book e dati del vecchio stack. Nessuna scansione di simboli o download automatico di tutto il catalogo.
- Download seriali con timeout, pochi tentativi limitati su errori transitori e riuso della cache se checksum coerente; nessun loop infinito o aggiramento di rate limit. ZIP prima in file temporaneo, verifica hash prima di promuoverlo. Estrarre solo CSV atteso senza path traversal.
- Manifest per file: URL esatto, scaricato_alle UTC, dimensioni, SHA256 locale, checksum fornitore e risultato, simbolo/mercato/priceType, colonne, unità temporale, prima/ultima apertura, righe, copertura e anomalie. Se cache remota cambia, conservare la versione precedente e distinguere i run; non sovrascrivere risultati storici sotto lo stesso ID.

Il Director ha consultato il repository ufficiale e i termini il 16 ottobre:
https://github.com/binance/binance-public-data
https://github.com/binance/binance-public-data/blob/master/TERMS_AND_CONDITIONS.md
https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data
Il checksum di settembre è stato raggiunto via HTTP 200 nell'ambiente Director:
c296ba45c215934e9750ca82846c7b5d14be661649d8e4423eac834cf57330dc.
Non è un pin eterno né una verifica dei prezzi: confrontare il file realmente scaricato col checksum al momento del run e registrare eventuale variazione. Nessun ZIP reale o esito è stato elaborato dal Director prima di questo protocollo.

Termini osservati: uso personale di ricerca non produttiva, attribuzione e condizioni sui derivati distinte dalla licenza del codice. Conservare localmente copia/hash/data dei termini. Nell'app e nel report indicare “Fonte: Binance Vision”; nessuna associazione commerciale. Dati e bundle non redistribuiti. Se si pubblica il breve report aggregato o screenshot reali richiesti, applicare esplicitamente CC BY-NC-SA 4.0 a quei soli derivati con attribuzione e link fonte/termini, senza cambiare la licenza del codice. Non dichiarare che la MIT del repository Binance sia licenza del dataset. Nessun uso commerciale o operativo autorizzato.

Parsing: campi futures 12 come documentazione ufficiale, eventuale singola intestazione riconosciuta per nome, non scartare automaticamente la prima riga numerica. Timestamp verificati in millisecondi per questi file futures, openTime multiplo 60.000 e closeTime=openTime+59.999; rappresentazione interna barra [open,open+60s), available_at=open+60s. Unità anomala/schema diverso = errore diagnosticato, non euristica che faccia passare date fuori perimetro. Prezzi finiti positivi, H>=max(O,C), L<=min(O,C), H>=L; volumi non negativi, scambi interi non negativi. Conservare volume base, quote, scambi e campi taker senza inferirne flusso netto.

Verificare ordine, apertura univoca, cadenza 1m e confini file. Duplicati identici possono essere collassati soltanto contando e registrando le righe originali; duplicati discordanti rendono il minuto INVALID senza scegliere un prezzo. Righe corrotte non interpolabili: log e minuto mancante/invalidato. Buchi non riempiti. Ordinamento deterministico dichiarato, anomalie riportate. Copertura teorica: 308.160 minuti (214 giorni); 132.480 inizializzazione, 175.680 studio. Conteggi teorici non sostituiscono l'ispezione.

File assente/checksum errato/strumento errato bloccano l'acquisizione affidabile: consegnare BLOCKED preciso, non proclamare studio completo. Se file validi contengono buchi, proseguire con disponibilità/esiti mancanti espliciti: la popolazione temporale non scompare. Classificare copertura effettiva senza nascondere le anomalie.

## 4. Clock, aggregazione e contratto causale

Barre 45m ancorate a 00:00 UTC, 32 al giorno; giornaliera [00:00,00:00 successiva) UTC. OHLC primo/max/min/ultimo; volumi base/quote e scambi sommati. Requisiti: 45 minuti esatti per 45m, 1.440 per 1D, tutti validi. Una barra incompleta ha stato INCOMPLETE e motivi/counts; non produrre OHLC definitivo da una copertura parziale fingendola completa.

Snapshot alle chiusure 45m t: usa solo barre con end<=t; prezzo origine C_t è la chiusura della barra [t-45m,t). A mezzanotte calcolare entrambe le scale chiuse PRIMA dello snapshot. Il giorno in formazione è escluso dalle osservazioni e, per semplicità, dal grafico storico 1D. Non etichettare chiusure secondo il fuso locale: UTC sempre visibile. 00:00 del primo settembre è un'origine valida costruita anche con inizializzazione; t=2026-01-01 escluso dalle origini ma valido come endpoint dell'esito dell'origine 2025-12-31T00:00.

Gap: ogni scala ha propri segmenti continui. Barra INCOMPLETE azzera finestre dipendenti e sequenze pivot/ancore correnti di quella scala, conservando eventi precedenti. Ripartire da nuove barre consecutive senza ponti sul gap. Un gap 45m non azzera retroattivamente il giorno precedente valido; un giorno incompleto impedisce la continuità 1D. Livelli giornalieri validi già pubblicati conservano la storia; per “giorno precedente” usare esattamente il giorno UTC precedente, mai il più recente giorno valido lontano senza dichiararlo.

Ogni osservazione/evento ha identità stabile (strumento, scala, tempo, tipo), versione, event_time, available_at, inputRef e null+reason quando mancante (INSUFFICIENT_HISTORY, INCOMPLETE_INPUT, ZERO_DENOMINATOR, NO_CONFIRMED_PIVOTS, AMBIGUOUS_PIVOT, ecc.). Zero noto resta zero. Ragioni per singola misura, non un unico ready globale.

event_time del pivot = fine della barra candidata; available_at = fine della seconda barra destra. Conservare anche openTime della candidata per disegno sul grafico. L'app può disegnare il pivot sulla candela originaria SOLO dopo available_at, spiegando entrambi i tempi. Il presente clock assume disponibilità logica alla chiusura, non prova latenza zero dal vivo.

Snapshot immutabili; revisioni sono nuovi eventi/versioni con available_at e prima/dopo. Un evento futuro non aggiunge retroattivamente validTo o informazioni di sostituzione nello snapshot passato. Nessun ID/hash del futuro nei payload comparati per causalità. Manifest di run separato. Elaborazione sequenziale delle osservazioni; esiti calcolati da modulo distinto che non è input dell'osservatore.

## 5. Dizionario osservativo OBS-001/v1 e disponibilità per misura

Applicare indipendentemente a 45m e 1D. Prezzi e rapporti in doppia precisione, senza arrotondare prima dei confronti; parità numerica esatta dopo parsing dello stesso valore, nessuna epsilon di trading. Unità A in USDT/BTC. Mediana di 20 = media dei due valori centrali. Ogni scheda mostra parametri, formula sintetica, dato e tempo effettivo.

### 5.1 Volatilità

TR_i=max(H_i-L_i, |H_i-C_(i-1)|, |L_i-C_(i-1)|). Primo TR non calcolabile senza precedente completa contigua.
A_i=media aritmetica degli ultimi 20 TR: **21 barre contigue complete**. Non ATR di Wilder. A=0 è una volatilità nota zero; i rapporti che la usano sono null/ZERO_DENOMINATOR. A/C disponibile se C valido (può valere zero se A=0). Conservare TR singolo appena esiste il precedente; non attendere A per mostrarlo.

### 5.2 Medie

SMA20 media ultime 20 chiusure, SMA50 ultime 50: disponibili rispettivamente con **20 e 50 barre complete contigue**.
Distanza (SMA20-SMA50)/A: 50 barre e A>0.
Pendenza (SMA20_i-SMA20_(i-4))/A_i: **24 barre**, entrambe le SMA20 e A corrente>0; non serve SMA50.
Posizione (C-SMA20)/A: **21 barre**, A>0.
Incrocio sul segno della distanza: precedente<=0 e corrente>0 oppure precedente>=0 e corrente<0; zero mantenuto non è nuovo incrocio. Richiede entrambi i valori disponibili, quindi almeno **51 barre** e denominatori validi. Nessun bridge su dati assenti.
Non esiste warmup globale 54. Serie UI “SMA20 / SMA50”, non “EMA20/50” o curve illustrative delle fixture. Parametri 20/50/4 sono iniziali, non ottimizzati.

### 5.3 Pivot e struttura

Cinque barre contigue complete: pivot high candidata i se H_i strettamente maggiore dei due H a sinistra e dei due a destra; low speculare strettamente minore. Conferma a fine i+2; mai anticipata. Registrare candidati, conferme e scarti (parità/non estremo/ambiguità) con motivi, senza una macchina di pattern aggiuntiva.
Se stessa barra soddisfa high e low, registrare DUAL_AMBIGUOUS, esclusa da sequenza swing e confronti di struttura; non trasformarla in due swing ordinati arbitrariamente.
Struttura dagli ultimi **due pivot high confermati non ambigui e due pivot low confermati non ambigui** del segmento, NON solo dalla sequenza alternata Fibonacci:
- UP se ultimo high>precedente high E ultimo low>precedente low;
- DOWN se entrambi <;
- MIXED negli altri casi, incluse parità;
- UNAVAILABLE se mancano due di ciascun tipo o barra corrente invalida.
Conservare i quattro riferimenti. Non richiede A o SMA, non ha conteggio fisso di warmup. Nessun pivot artificiale alle estremità dei file o a fine studio.

### 5.4 Livelli

Ultimo pivot high/low confermato non ambiguo della scala e high/low del giorno UTC precedente completo (per entrambe le scale). Ogni livello disponibile indipendentemente; non nascondere pivot high se manca low. Per lo snapshot a mezzanotte il “giorno precedente” è quello appena terminato.
Distanza firmata (C-L)/A quando A>0; livello resta visibile anche senza distanza. Livello, origine e available_at conservati.
Fascia +/-0,25A ammessa solo come descrizione geometrica opzionale, **non classificazione dello studio o criterio decisionale**; non aggiungere badge di qualità.
Attraversamento solo contro la stessa identità di livello già disponibile nello snapshot precedente: lato cambia da Cprev<=L a C>L o da Cprev>=L a C<L; permanenza sullo zero non è attraversamento. Salvare L, A allora disponibile (anche null), tempi e ID; nuovo livello non produce un falso attraversamento alla pubblicazione. Non riattivare automaticamente vecchi livelli superati come nuovi.

### 5.5 Volume

V_i / mediana(V_(i-20)...V_(i-1)): **21 barre complete contigue**, barra corrente esclusa dal denominatore, mediana>0. V corrente=0 con mediana>0 è un rapporto noto zero; mediana zero o finestra incompleta = null. Volume base BTC, quote USDT e scambi osservabili appena chiusa barra completa. Nessun badge “acquisto” o flusso netto dedotto.
Rapporto non corretto per stagionalità intraday: dichiararlo nella scheda e nei limiti del report. Non aggiungere raggruppamenti per volume o fascia oraria alla domanda principale.

### 5.6 Fibonacci e versioni

Sequenza alternata di pivot confermati non ambigui: primo append; stesso tipo sostituisce terminale solo se estremo strettamente più esteso (high maggiore, low minore); altrimenti conservare il precedente; tipo opposto append. Ogni append/sostituzione ha nuova versione e tempo, conserva precedente. Ordine di elaborazione per available_at; non esistono due estremi ordinabili della stessa candidata ambigua.
Ancore = ultimi due opposti in ordine temporale P0,P1. u=(C-P0)/(P1-P0), r=1-u anche per gamba decrescente. Ritracciamenti r=0,382; 0,5; 0,618; 0,786: prezzo=P1-r*(P1-P0). Proiezioni u=1,272; 1,618: prezzo=P0+u*(P1-P0).
Registrare ancore/prezzi/tempi/versione, u, r continuo e distanze firmate (C-livello)/A quando A>0. Ancore assenti o uguali: null con motivo; nessuna dipendenza da SMA, A necessario solo alle distanze. 50% esplicitamente convenzione, non rapporto Fibonacci. Non limitare il dato alla vecchia coppia 61,8/38,2 delle fixture né trasformare livelli in target.
Cambi successivi non riscrivono ancore o r degli snapshot precedenti.

## 6. Domanda e convenzioni descrittive congelate prima degli esiti

Domanda unica: per TUTTE le chiusure 45m del periodo, quale seguito nelle successive 24h accompagna una struttura 45m crescente/decrescente quando quella 1D concorda, contrasta o è mista/non disponibile?

Popolazione: griglia t in [2025-09-01T00:00Z, 2026-01-01T00:00Z), passo 45m, **3.904 origini teoriche**, nessuna eliminata per indicatori assenti o futuro incompleto. Un record per origine, mese determinato da t UTC. Record includono anche struttura 45m MIXED e UNAVAILABLE. La barra con close=inizio studio può provenire dall'inizializzazione: convenzione deliberata. Non registrare le origini di inizializzazione come studio.

Campi gruppo ex ante:
- s45 e s1d ciascuno UP/DOWN/MIXED/UNAVAILABLE.
- Solo per s45 UP/DOWN: dailyRelation=CONCORDANT se stesso verso, OPPOSITE se verso opposto, MIXED se s1d MIXED, UNAVAILABLE se s1d mancante. **MIXED e UNAVAILABLE restano separati**; per s45 misto/assente dailyRelation=NOT_APPLICABLE.
- Il principale confronto è **entro ciascuno stesso verso s45**, fra i quattro stati dailyRelation, mai UP concorde contro DOWN contrario.
- Riepilogo base per sola s45, incluse MIXED e UNAVAILABLE, indipendente dal giornaliero. Matrice conteggi s45×s1d con celle zero esplicite per tutti i mesi e totale. Le altre quattro famiglie sono consultabili/registrate, non usate per screening, gruppi o combinazioni.

Prezzo p=C_t e scala a=A45m_t congelati all'origine. Orizzonte esatto 24h=32 barre 45m, minuti futuri [t,t+24h). Nessuna volatilità futura nel denominatore:
- final=(C_(t+24h)-p)/a;
- up=max(0, max(high futuri 1m)-p)/a;
- down=max(0, p-min(low futuri 1m))/a.
up e down sono ampiezze non negative, NON profitto/perdita di un trade; final resta firmato nel verso del prezzo anche per s45 DOWN. Non invertire segni tra gruppi. Un confronto manuale con massimi/minimi delle 32 barre complete deve coincidere.

p assente ⇒ misure null con motivo; A assente o <=0 ⇒ normalizzate null, non zero. Conservare separatamente status origine, volatilità e copertura futura; nessuna priorità di una ragione che nasconda gli altri problemi.
Future COMPLETE solo se tutti i 1.440 minuti validi sono presenti e t+24h<=2026-01-01T00:00Z. Se manca futuro per fine intervallo: RIGHT_CENSORED; se buco interno: GAP; se entrambi: entrambi i flag. Nessun prezzo finale portato avanti, nessuna escursione parziale presentata come completa. Mostrare durata disponibile e motivi; le tre misure principali a 24h restano null se incomplete. Nessun download nel 2026. Il close dell'ultimo minuto 2025 chiude a 2026-01-01T00:00Z ed è utilizzabile per un endpoint, non è input 2026 aggiuntivo.
Con copertura teorica integra: **31 origini right-censored**, 3.873 con orizzonte completo prima degli altri controlli. Questi sono conteggi di controllo, non risultati.

Riepiloghi fissi per settembre, ottobre, novembre, dicembre e totale:
1. copertura/pop orizzonti, indisponibilità e relativi motivi, disponibilità per singola misura/famiglia;
2. sola s45: ciascuno dei quattro stati;
3. UP e DOWN separati per i quattro dailyRelation; n totali, n origine valida, n A valida, n future completo, n misure disponibili e n mancanti con flag;
4. per final/up/down sulle righe disponibili: media, minimo, P10, P25, mediana, P75, P90, massimo. Quantili a interpolazione lineare h=(n-1)*q; se n=1 stesso valore, se n=0 null. Pesi uguali per origine; totale pooled, non media delle medie mensili. Arrotondamento solo in tabella, output numerico non arrotondato.
Nessuna soglia trade riuscito, percentuale di successo, barriera2A, significatività/p-value, intervalli d'inferenza o ranking “miglior gruppo”. Nessuna scelta ex post di orario, mese, lato o subset per migliorare risultati.

Origini adiacenti hanno finestre fortemente sovrapposte, non prove indipendenti. Riportare limite in UI/tabelle. Differenze tra gruppi giornalieri possono riflettere altri fattori: non attribuire causalità né contributo incrementale automatico alla scala 1D. Quattro mesi sono sviluppo già esposto, non holdout nuovo. Risultato nullo, contrario o insufficiente è una consegna valida.

Lettura risultati obbligatoria: riportare se mediana/media e dispersione cambiano entro stesso verso, se i mesi concordano o si contraddicono e dove i gruppi sono vuoti/scarsi; nessuna generalizzazione da un singolo caso. Mostrare esempi contrari senza scegliere solo grafici favorevoli: per ciascun verso con dati scegliere deterministically la riga con final più opposto al verso (tie: origine più antica), oltre a una prima origine disponibile del periodo. I criteri esempi sono retrospettivi dichiarati, non un nuovo test.

## 7. Integrazione nella dashboard esistente

Conservare navbar superiore e stile approvato. Aggiungere scelta distinta “Simulazione locale” / “Studio storico”; il pannello “Scenari simulati” esiste solo nel primo ambiente. Cambio ambiente smonta conferme, richieste e provider precedenti, senza trasferire bot/ordini. Default iniziale dichiarato; dopo apertura bundle valido portare allo storico. Nessun bundle importato ⇒ istruzione “Apri studio storico”, non prezzi finti sotto etichetta storico.

Banner nello storico: **STORICO REALE — studio osservativo locale — nessun collegamento exchange**. Nell'ambiente fixture conservare esattamente il banner di simulazione. “Binance Vision · BTCUSDT perpetual USDⓈ-M · prezzo negoziato · UTC”, intervallo/cutoff e qualità input sempre identificabili. Nessuno stato “connesso demo”, feed live fresco o “0 s fa” dal clock reale.

Nello storico:
- selettore data/ora UTC sulle origini dello studio, slider o elenco indicizzato, precedente/successiva chiusura 45m, 45m/1D; impostazione iniziale prima origine studio. Disabilitare oltre i confini; una lacuna resta selezionabile con motivo.
- grafico/pannelli sincronizzati sullo stesso cutoff t; grafico mostra soltanto barre terminate entro t e livelli/eventi available_at<=t. Si può usare un tratto precedente da inizializzazione; non è oggetto delle tabelle studio. Niente giorno completo futuro o serie oltre cutoff; buchi resi come buchi.
- sei famiglie consultabili alle due scale, valori effettivi, formule/parametri e motivi di indisponibilità; nessuna label EMA con dati SMA, nessuna linea di fixture. Nessuna frase predittiva precompilata “il bot pensa / call LONG”.
- riquadro call sostituito contestualmente da “Osservazioni al [t]” (struttura45m/1D, relazione e disponibilità); nessun falso WAIT che faccia credere a una decisione algoritmica. Area posizione/conto/ordini non alimentata: dichiarare “Non previsti nello studio osservativo”. Nessun saldo 10.000, fee o posizione sintetici mescolati ai prezzi reali. Start/Stop, modalità esecuzione e uscite non operativi nello storico: nascondere o spiegare chiaramente non disponibili.
- comando distinto **“Mostra seguito retrospettivo 24h”**: evidenza visiva e cutoff origine t mantenuto. Estendere lo stesso grafico fino a min(t+24h, fineinput) con futuro marcato come retrospettivo; pannelli osservativi RESTANO allo snapshot t. Separata scheda esiti final/up/down e stato orizzonte, con etichetta a posteriori. Ritorno “Solo informazioni al momento” rimuove il futuro. Non anticipare nella vista causale valori delle tabelle/esiti o titoli che li rivelano.
- riepilogo mensile/totale raggiungibile tramite la voce Ricerca / Backtest esistente, ora etichettata coerentemente “Studio osservativo” nell'ambiente storico. Niente seconda app o dashboard di ricerca separata. Mostrare tabelle principali, legenda, numerosità, casi mancanti, avviso sovrapposizione e limiti; link alla lettura del report locale. Storico temporale delle revisioni filtrato per available_at, distinto dal seguito del prezzo.
- i dati futuri possono essere nel bundle locale e leggibili nel sorgente: non si promette una modalità cieca sicura né accesso a periodi protetti.

I componenti condivisi possono essere adattati con discriminanti e proprietà pertinenti; non duplicare l'intero albero. Conservare il percorso fixture come demo isolata se semplice; non ampliarlo. Nessun nuovo restyling/gate Figma necessario: sono adattamenti funzionali al nuovo dato.

## 8. Sequenza di esecuzione autonoma e verifiche proporzionate

1. Verifica checkout/base e prerequisiti, leggi parti pertinenti; configura convenzioni v1 e relativo hash PRIMA degli esiti. Progetta contratti minimi e layout storico secondo task, senza delegare scelte di studio al codice.
2. Motore con pochi esempi sintetici discriminanti e riscontri numerici manuali: aggregation, formule, indipendenza disponibilità, pivot/ancore, gap e snapshot causali. Non produrre 70 giorni sintetici per abitudine: quella proposta DESIGN-001 non è attivata.
3. Acquisisci sette mesi autorizzati, verifica checksum/identità/copertura, registra manifest. Se accesso impossibile consegna blocco preciso; completa lavoro non dipendente ma non spacciare sintetico per conclusione macrofase.
4. Elabora osservazioni reali, poi esiti/tabelle congelati. Registra durate/counts, riesegui solo per bug identificati. Nessuna ricerca parametri o iterazione per ottenere esiti favorevoli.
5. Collega bundle all'app, verifica principali stati, prepara lettura risultati e istruzioni di prova Owner. Consegna intero percorso, non chiedere approvazione al solo punto 2.

Test mirati richiesti, con esempi calcolabili:
- 45 minuti esatti, gap e confini UTC/mezzanotte; aggregati 45m/1D coerenti dagli stessi minuti.
- A media TR20 con precedente; SMA20/50, pendenza a 24 barre, indipendenza da pivot; rapporto volume con corrente esclusa; denominatori zero noti distinti da rapporti mancanti.
- pivot rivelato esattamente i+2, parità e dual, duehigh/duelow e stato misto; stesso tipo non più esteso, sostituzione ancora versionata e gamba DOWN Fibonacci.
- stesso prefisso, due futuri diversi: snapshot fino al cutoff identici; provare anche aggiornamenti pivot, gap futuro e confine giorno. Confrontare elaborazione batch e prefisso troncato sullo stesso cutoff, non solo funzione mockata.
- esiti 24h con endpoint esatto e segni, high/low intraminuto, zeroA, gap e ultima giornata censurata; tutte le 3.904 righe della griglia conservate; somme delle partizioni riconciliate; quantili con piccolo campione noto.
- integrazione UI: import valido/errato, cutoff sincronizzato 45m/1D e avanzamento, futuro solo su toggle esplicito, ritorno causale, dati null leggibili e nessun saldo/call/ordine fittizio nello storico. Cambio ambiente invalida eventuale conferma.
- build/typecheck e test pertinenti del frontend; regressioni conferme R1 solo se toccato shell/provider. Non ripetere automaticamente i 50 test simulazione o suite generali Python, niente CI/polling.
- prova browser sul bundle reale: prima origine, mezzanotte, esempio pivot/ancora, una fine censurata, riepilogo mesi e toggle seguito. Screenshot essenziali 1366 o 1680 della vista causale, seguito distinto e tabella; non venti immagini. Chiudere solo processi propri, nessun processo Owner.

Bug: descrivere trigger, formula prima/dopo, test discriminante e impatto sulle tabelle; bump patch versione e rigenerare run. Non cambiare definizione s45/s1d, soglie o popolazione per correggere un risultato sgradito. Se specifica contraddittoria coinvolge obiettivi/metodo chiedere Director; niente nuova richiesta ordinaria ad Astra.

Esempi numerici di controllo prefissati (sintetici, non prezzi BTC): barre complete C_i=100+i, O_i=C_i, H_i=C_i+1, L_i=C_i-1 per i=1..51, V_i=i; dal secondo TR=2. A a i=20 assente, a i=21 vale 2; SMA20 a i=20 vale 110,5; a i=24 vale 114,5 e pendenza=2; SMA50 a i=50 vale 125,5, SMA20=140,5 e distanza=7,5; posizione a i=21 vale 4,75. Volume relativo a i=21 =21/mediana(1..20)=2. Queste barre non generano automaticamente struttura: dipende dai pivot, e può restare indisponibile.
Ancore 100→120: r=0,382 a 112,36 e u=1,272 a 125,44; ancore 120→100: r=0,382 a 107,64 e u=1,272 a 94,56. Esito con p=100, a=2, close24h=102, massimo futuro106 e minimo97: final=1, up=3, down=1,5. Realizzare finestre valide per il controllo esito; non inventare campi mancanti per soddisfare la formula.

## 9. Consegna, pubblicazione e prova Owner

Commit/push ordinari su main autorizzati per codice, test pertinenti, istruzioni, schema/config e report breve. Prima pubblicazione verificare assenza di raw/bundle/prezzi minuto reali in Git. Report aggregato piccolo docs/research/OBS-001-results.md: configurazione/run/inputhash, copertura, tabelle prefissate, lettura con mesi discordi e casi contrari, attribuzione/licenza dei soli derivati come sopra. File pesanti ed esempi temporali reali fuori Git; non allegare mesi di dati in markdown.

Aggiornare README con prerequisiti effettivi e comandi Windows completi: acquisizione autorizzata, generazione bundle, apertura nell'app e ripetizione offline. Documentare funzionante/simulato/assente. Specificare percorso locale esatto di input/output e sintesi per il Director senza esporre segreti.
Consegna nel task e STATE: commit e file, convenzioni/hash, fonte e qualità effettive, misure disponibili/mancanti, conteggi conciliati, tempi, test/browser realmente svolti, risultati e limiti. Passare a DELIVERED, mai ACCEPTED. Nessun pull/fetch, anche dry-run; sincronizzazione checkout a cura di Gian. Se base divergente, non sovrascrivere.

Prova Gian dopo review: avviare stessa dashboard, aprire bundle generato, selezionare una data UTC, avanzare 45m, passare 1D, consultare le sei famiglie, vedere perché un pivot diventa noto dopo, aprire seguito retrospettivo e tornare alla vista causale, consultare mese e caso contrario. Non presentare questa prova come trading validato.

Criterio di chiusura macrofase: storico reale nell'app, osservazioni causali e revisioni preservate, percorso riproducibile, confronto descrittivo previsto con casi incompleti/contrari, prova Owner e review Director. Non è richiesto un risultato favorevole. Tornare ad Astra solo a conclusione o conflitto sostanziale.

## 10. Esclusioni

Nessuna strategia di ingresso/uscita, ordine exchange, conto operativo, capitale/leva, valutazione economica, costo/fee/funding, acquisizione extra sette mesi, dati successivi al 2025, apertura del 2026 protetto o riattivazione vecchi studi. Fonte per ricerca non approva esecuzione reale né accesso Owner. Nessuna ricerca automatica di combinazioni.

## Spazio dell'esecutore

### Avanzamento — registrazione prima di acquisizione ed esiti (Claude Code, 16 ottobre 2026)

**Stato: IN_PROGRESS.**
- **Base e ambiente.** Base `413c6d0` su `main`, checkout pulito, nessun pull o fetch.
- **Python.** Nel PATH non c'è `python`: ci sono solo gli alias di Windows Store, che non funzionano. Sono già presenti interpreti gestiti da `uv`. Uso **Python 3.12.14** (`python3.12`); il motore è verificato anche su 3.11.16. Non ho installato nulla.
- **Convenzioni congelate.** `config/OBS-001-v1.json`, id `OBS-001/v1`, scritte dal task al commit `413c6d076077412b09b85760101658ab07f76dfd`.
  - Hash canonico SHA256, calcolato su JSON con chiavi ordinate e indipendente dai fine riga: `3c4eb884d0b6752bfb31e7d9ae159a1414d75cadc90f9abcc9379d5825002387`.
  - Motore `obs001` versione 1.0.0, schema bundle `obs001.bundle/1`.
- **Test sintetici.** Motore pubblicato con 30 test sintetici prima di qualunque download o esito reale. Acquisizione ed elaborazione reale avverranno dal commit che contiene questa nota.

## Review del Director

Specifica documentale ex ante, lettura di DESIGN-001, contratto UI e documenti di autorità. Fonte ufficiale consultata e checksum settembre raggiungibile; nessun download ZIP, calcolo reale o esito storico esaminato prima della registrazione. Review di codice, risultati e prova Owner da svolgere dopo consegna.
