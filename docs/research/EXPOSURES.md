# Memoria dei dati già incontrati

Nota di provenienza del 15 ottobre 2026: non è un nuovo protocollo, non seleziona finestre e non autorizza acquisizioni. I dati stessi non sono inclusi nel recupero.

Fonte documentale: [registro storico](https://github.com/C-Gian/algorithmic-trader-archive/blob/b8f8e2d4b9eb531dcab4e609a037c02024087414/delivery/STUDY-EXPOSURE-REGISTER.md). Le dichiarazioni riportate sono quelle del progetto precedente, non una nuova verifica delle elaborazioni o dei dataset.

| Periodo UTC | Che cosa sappiamo |
|---|---|
| Gennaio–aprile 2025 | Esposto a replica direzionale e studio economico v0.7; input storici dichiarati dal 27 novembre 2024 al 1 maggio 2025 06:05. Non trattarlo come verifica mai vista. |
| Settembre–dicembre 2025 | Ripetutamente esposto a sviluppo, diagnosi e confronti; input continui dichiarati dal 28 luglio 2025 al 1 gennaio 2026 06:05. |
| 25–30 settembre 2026 | Materiale della precedente ricerca RP-001 consultato. |
| 8–12 ottobre 2026 | Inizializzazione e sessione live v0.6 documentate; altre esposizioni live non sono consolidate completamente. |
| Gennaio–agosto 2026 | Resta protetto, salvo il tail già autorizzato del 1 gennaio fino alle 06:05. “Protetto” non equivale a certificato mai esaminato da chiunque. |
| 2 novembre 2026 → 25 gennaio 2027 | Finestra HDP-001 registrata, studio INACTIVE. Nessuna attività attivata dal nuovo progetto. |
| 25 gennaio → 26 luglio 2027 | Finestra A v0.6 registrata, studio INACTIVE; warmup dal 21 dicembre 2026 e tail secondo il vecchio disegno. Nessuna attività attivata qui. |

Una repository nuova non cancella conoscenza o esposizioni pregresse. Non qualificare altri anni come “mai visti” solo perché non compaiono in questa tabella: il registro storico dichiara lacune. Anche i dati di letteratura hanno un'esposizione distinta dai dati esaminati dal progetto. Le scelte della nuova ricerca verranno definite separatamente.

## Mandato corrente OBS-001 — 16 ottobre 2026

Astra autorizza ora, per questo solo studio osservativo descrittivo, acquisizione pubblica e lettura Binance Vision BTCUSDT perpetual USDⓈ-M, klines negoziate1m: inizializzazione [2025-06-01,2025-09-01), studio [2025-09-01,2026-01-01) UTC. Perimetro input totale giugno–dicembre2025, senza tail nel2026. Fonte diversa non rende settembre–dicembre nuovo o indipendente dalle esposizioni già registrate.

Questa è registrazione di autorizzazione, **non prova di acquisizione o copertura effettiva**: l'esecutore aggiungerà data/run/manifest alla consegna dopo i controlli. Nessun accesso al vecchio stack o riuso dei suoi dataset. Gennaio–agosto2026 rimane protetto; il precedente tail del1gennaio non è utilizzabile in OBS-001. HDP-001 e A restano INACTIVE. Nessuna estensione implicita ad altre date, simboli, fonti o studio economico.

## Mandato CAND-001 — 17 ottobre 2026

Astra autorizza l'ampliamento pubblico gratuito della medesima fonte/strumento: Binance Vision BTCUSDT perpetual USDⓈ-M, input negoziato1m [2022-10-01,2026-01-01) UTC; inizializzazione [2022-10-01,2023-01-01), sviluppo [2023-01-01,2026-01-01). Consentiti funding storico e mark strettamente necessari alla valutazione entro gli stessi confini; raw/bundle fuori Git, nessun accesso Owner/vecchio stack. Riutilizzare file già verificati e acquisire solo mancanti.

2023–2024 destinati alle iterazioni iniziali; non certificati mai esposti.2025 confronto aggiuntivo **già esposto**, non validazione indipendente: la preregistrazione non cancella OBS-001 né precedenti studi. CAND-001 valuta primaDEV2023–2024; eventuale unica revisione e congelamento prima degli esiti2025, nessuna iterazione metodologica su2025 in questa macrofase.

Autorizzazione non equivale a dato già acquisito: l'esecutore registrerà manifest/copertura/esposizione effettiva. Il Director ha verificato solo fattibilità/campi del fundinggennaio2023 e checksum markgennaio2023, nessun esito economico del candidato. Nessuna lettura nel2026, neppure il vecchio tail1gennaio. HDP-001 eA restanoINACTIVE. Eventuali nuovi dati fuori da questi confini richiedono mandato specifico.


## Esposizione effettiva CAND-001 DEV — consegna ee7282f, review 17 ottobre 2026

Dichiarazione dell'esecutore: acquisiti il17ottobre2026,07:29–07:31UTC,27archivi trade ottobre2022–dicembre2024,24funding e24mark2023–2024; checksum verificati,1.185.120minuti negoziati validi. Elaborati DEV2023–2024:78trade/87call, risultati e diagnosi esaminati. I sette archivi OBS2025 non letti in DEV; nessun nuovo download o esito economico2025 in questa fase.

Director: lettura report/codice, test sintetici e UI indipendenti; non ricalcolo autonomo dei75archivi o del ledger reale in questa review. Risultati negativi DEV ormai esposti e usati per la decisione di mantenerev1 senza revisione metodologica. R1 corregge qualità funding, percorsi irrisolti e prezzo visualizzato; non cambia soglie. Copertura dichiarata e limiti nel report CAND-001-results.md; raw/manifest/bundle restano locali fuoriGit.

## Esposizione effettiva CAND-001 ADDITIONAL_2025 — consegna esecutore, 17 ottobre 2026

Dichiarazione dell'esecutore (Claude Code), da rivedere dal Director.
- Acquisiti il 17 ottobre 2026, 08:35–08:36 UTC, solo i 29 archivi mancanti: trade gennaio–maggio 2025, funding e mark 2025. Checksum del fornitore verificati.
- Riusati senza nuove richieste i 27 trade CAND ottobre 2022–dicembre 2024 e, letti dove sono, i 7 trade OBS-001 giugno–dicembre 2025, con SHA256 uguale ai manifest.
- Input osservativo letto [2022-10-01, 2026-01-01): 1.710.720 minuti validi su 1.710.720. Funding 2025: 1.095 eventi, certificato. Mark: 1.094 punti su 1.095.
- Nessuna lettura o richiesta di dati 2026, nessun tail.

Elaborato con motore 1.0.2 (commit pre-esiti `078d9ed`), candidato 1.0.0 invariato: confronto aggiuntivo [2025-01-01, 2026-01-01) da FLAT. Esiti 2025 ora esposti: 29 operazioni modellate e 31 call, netto −109,08 USDT su N0 = 1.000 USDT; dettagli in `CAND-001-results.md`. Nessuna iterazione metodologica dopo la lettura. Il 2025 resta un periodo già esposto e non è utilizzabile come validazione indipendente per candidati futuri. Raw, manifest e bundle sono locali, fuori Git.


## Nuovo mandato diagnostico/metodologico CAND-001 — 17 ottobre 2026

Dopo APP-001 Astra autorizza diagnosi della politica v1 ed eventuale unica revisione/confronto sul DEV [2023-01-01,2025-01-01), con prefisso osservativo dal 2022-10-01 e file già conservati. Nessuna nuova acquisizione. Le precedenti esposizioni DEV e 2025 non si cancellano: non è una prova indipendente. Nel nuovo ciclo non leggere/ricalcolare il 2025 né usarne gli esiti per scegliere la revisione; nessun 2026. Primo incarico D1: estrazione/riconciliazione e casi cronologici, senza strategia alternativa. È autorizzazione, non dichiarazione di esecuzione già svolta.


## Mandato OBS-002 — 17 ottobre 2026

Astra autorizza una sola analisi esplorativa movimento–arretramento–ripresa, popolazione più ampia dei trade CAND-001, input esistenti [2022-10-01,2025-01-01), origini DEV [2023-01-01,2025-01-01). Nessun nuovo download, lettura2025 o2026. Osservazioni OBS-001 già definite, non nuovi indicatori. Prima dell'estrazione fissate popolazione, contesti congiunti ed esiti24h in current_task.md e config/OBS-002-v1.json. Esplorazione su dati già esposti, non validazione indipendente; nessuna modifica CAND o implementazione automatica di un'ipotesi. Questo paragrafo registra autorizzazione, non esecuzione già avvenuta.


## Mandato MOVE-001 — 17 ottobre 2026
Astra approva la candidata semantica sperimentale e autorizza una applicazione descrittiva sui soli input già disponibili [2022-10-01,2025-01-01), DEV [2023-01-01,2025-01-01). Popolazione nuova e specifica, non riclassificazione OBS-002. Nessun nuovo download, lettura2025/2026, trade o rendimento. Prima dell'applicazione pubblicare codice/config/test con regole e conteggi fissi in MOVE-001.md §§11–12; esempi cronologici predeterminati. Le esposizioni precedenti DEV restano tali: nessuna validazione indipendente. Questo registra autorizzazione, non applicazione già eseguita o risultato favorevole.
