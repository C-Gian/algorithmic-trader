# Riferimento Figma — dashboard UI-001

Rilevazione del Director: 16 ottobre 2026. File approvato fornito dall'Owner:
https://www.figma.com/design/ys2HFfjS2OdaLLTsfhPp9A/Untitled?node-id=0-1

File key: ys2HFfjS2OdaLLTsfhPp9A. Pagina: Page 1, nodo 0:1.
Il nodo della pagina non è una schermata implementabile: la prima chiamata design context alla pagina ha richiesto una selezione. Metadata e richieste ai frame successivi hanno avuto successo.

## Accesso verificato e limiti

Il Director ha ottenuto metadata, screenshot e contesto di implementazione dei frame e componenti sotto. La dashboard completa è troppo grande per un'unica risposta ad alta fedeltà: il suo context restituisce metadata sparsi. Sono stati quindi richiesti separatamente sidebar, header, grafico, call, posizione, conto e le sei schede. Sono disponibili contesti completi per questi sottoalberi e per tavola stati, conferme e componenti. Non usare la sola risposta sparsa per implementare.

L'accesso del Director NON prova che Claude disponga dello stesso collegamento. All'inizio del task Claude verifica concretamente i propri strumenti Figma sul file/nodo e registra esito e frame leggibili. Se riesce può proseguire autonomamente nel task; se non riesce consegna il limite preciso, senza ridisegnare dal solo screenshot e senza installare integrazioni autonome.

Le immagini in questa directory sono esportazioni del design come evidenza visiva, non codice, asset runtime, prototipi funzionanti o una sostituzione del file completo. La dashboard è esportata alla dimensione naturale; le altre tavole sono anteprime ridotte. Per testo fine e geometria richiedere screenshot del nodo pertinente.

## Mappa dei riferimenti

| Parte | Nodo | Dimensione originale |
|---|---|---|
| Dashboard | 2:9260 | 1680 × 2956 |
| Sidebar | 2:9261 | 212 × 2956 |
| Header mercato e controllo | 2:9302 | 1468 × 208 |
| Scheda grafico | 2:9347 | 826 × 665 |
| Scheda call | 2:9549 | 554 × 633 |
| Scheda posizione | 2:9595 | 1404 × 287 |
| Segnali di mercato | 2:9641 | 1404 × 898 |
| Struttura / trend | 3:154 | 457,33 × 404 |
| Supporti / resistenze | 3:210 | 457,33 × 404 |
| Medie mobili | 3:267 | 457,33 × 404 |
| Volumi | 3:342 | 457,33 × 404 |
| Volatilità | 3:416 | 457,33 × 404 |
| Fibonacci | 3:473 | 457,33 × 404 |
| Conto e attività | 2:9828 | 1404 × 770 |
| Tavola degli stati | 2:9953 | 1480 × 2790 |
| Conferme operative | 2:10283 | 1540 × 1170 |
| Componenti locali | 3:2 | 1536 × 1318 |

## Aspetto da rispettare

Marchio orbit.; interfaccia scura. Sidebar sinistra 212 px sul desktop di riferimento. Area principale con margini 32 px, spaziature di sezione 24 px. Header; riga mercato/grafico a sinistra e call a destra; posizione a tutta larghezza; sei schede in due righe da tre; riepilogo conto, ordini/operazioni a sinistra e timeline a destra. Pagina scorrevole: non comprimere tutto in un unico viewport.

Colori rilevati dal contesto: fondo #0e1115; sidebar/header #14181d; schede #1a1f25; superfici interne #151a20; bordi #303943; griglia #28313a. Testo #f2f5f7, secondario #a7b2be, attenuato #7f8c9a. Accento blu #8cbbff su #23354c; positivo #72dab0 su #1d3830; attenzione #edc078 su #3b3225; negativo #ff9395 su #40272c. Raggi schede 12 px, pulsanti 8 px, badge 6 px. Verificare i dettagli nel nodo specifico.

Font Inter per interfaccia e IBM Plex Mono per prezzi/numeri; pesi regular/medium/semibold secondo nodo. Servire i font localmente, con relative licenze, evitando dipendenze remote in esecuzione. Nessuna nuova variante estetica.

Riferimento di confronto principale a larghezza 1680. Rendere leggibile anche a 1366: flusso/griglie e altezza automatica, non trasformazione CSS che rimpicciolisce l'intera schermata. Desktop prioritario; mantenere ordinamento a larghezze inferiori con reflow proporzionato senza inventare una nuova app mobile.

## Corrispondenza funzionale

- Header: coppia, prezzo, aggiornamento e freschezza; badge feed simulato/bot; Start e Stop totale; Solo call / Call + esecuzione.
- Grafico: 45m e 1D, zoom, candele/volumi, overlay medie, livelli e Fibonacci, livelli di piano/posizione distinguibili.
- Call: lettura e controindicazione, piano originario/attuale, durata/validità, aggiornamento con motivo. Stato della posizione mostrato come tale, non fuso con la call.
- Posizione: quantità, ingresso, stop/target attuali, aperto lordo, realizzato e costi; gestione manuale, parziale e chiusura.
- Segnali: ciascuna scheda espone “Cosa osserva”, “Cosa significa”, valori contestuali, tempo e Dettagli. Testi e mini-serie provengono dal provider.
- Conto: saldo/equity, netto, costi e funding qualificato; formula di riconciliazione; ordini protettivi e storico; timeline con notifiche esplicitamente simulate.
- Navigazione: Dashboard; Ricerca / Backtest; Storico; Conto; Impostazioni. Storico e Conto possono portare alle sezioni già implementate; Ricerca / Backtest e configurazione non costruita mostrano messaggio “Non disponibile in questa versione”. Nessun backend sottinteso.
- “Guida ai segnali” e “Vedi segnali”: navigazione alla sezione; Dettagli apre un pannello/dialogo locale coerente con la scheda, senza un secondo grafico principale o nuove conclusioni analitiche.

Tavola stati (riferimenti visuali, non otto ulteriori pagine dell'app):
1. Attesa senza call.
2. Proposta SHORT senza ordine.
3. Ordine LONG pendente senza posizione.
4. Posizione gestita manualmente.
5. Disconnessione con ultimo stato noto.
6. Bot fermo e posizione ancora aperta.
7. Ordine rifiutato senza costi/eseguito.
8. Call conclusa e posizione chiusa.

Dialoghi: passaggio manuale 2:10298; ripresa automatica 2:10335; stop totale 2:10372. Renderizzarli come conferme della dashboard, non come tavola da tre dialoghi simultanei. Chiusura e parziale richiedono dialoghi coerenti con gli stessi componenti; nessun acquisto di design o nuovo restyling.

## Correzioni necessarie e autorizzate entro UI-001

1. **Etichette dei pulsanti:** context e screenshot mostrano etichetta di default “Start” su molte varianti. I nomi dei nodi indicano chiaramente le azioni. Usare la corretta etichetta italiana (“Stop totale”, “Solo call”, “Call + esecuzione”, “1D”, “− Zoom”, “+ Zoom”, “Gestione manuale”, “Uscita parziale”, “Chiudi posizione”, “Annulla”, ecc.). Adeguare min-width/auto-layout affinché non siano troncate. Questa è una correzione semantica, non restyling.
2. **Ambiente:** sostituire “Binance Demo · connesso” e altre diciture ingannevoli con feed simulato; banner persistente “SIMULAZIONE LOCALE — nessun collegamento exchange”. Le ricevute Telegram non sono reali; nessun invio.
3. **Prodotto e cifre:** Figma mostra un esempio Spot LONG e una proposta SHORT non eseguibile sullo spot. Il task usa un contratto lineare fittizio per illustrare entrambe le direzioni: etichetta “Contratto lineare · esempio simulato”, senza implicare una scelta Binance futures approvata. Non mantenere contemporaneamente “Spot”, SHORT eseguito e contabilità lineare. Cifre del task vincolanti per le fixture: aggiornare coerentemente testi/serie/livelli/controindicazioni del mockup. Non copiare il saldo liquido Spot del design dentro il modello lineare.
4. **Piano e protezioni:** piano originario/corrente e ordini protettivi restano distinti; durante disconnessione protezioni “ultime note”, non attuali verificate. Prima/dopo di una modifica disponibili in timeline.
5. **Frasi indicative:** “ATR14”, “EMA20/50”, percentuali, Fibonacci e ragioni delle call sono esempi statici. Non calcolarli dai prezzi o registrarli come strategia autorizzata.
6. **Storico:** se si mostrano operazioni concluse devono contribuire ai totali. È valido mostrare elenco vuoto all'inizio del percorso; non aggiungere le tre operazioni del mockup senza includerne gli eseguiti/costi nel conto.
7. **Non disponibilità:** mostrare valore assente con ragione, separando ultimo dato noto e tempo da quello attuale; niente zero segnaposto.

Queste correzioni discendono dal mandato funzionale e dalla simulazione locale già autorizzata. Nessun bisogno di riaprire la scelta estetica con l'Owner.

## Uso del contesto da parte dell'esecutore

Leggere la skill Figma design-to-code se disponibile, ottenere design context dei nodi pertinenti con screenshot. Se la risposta è sparsa suddividere, come sopra. Adattare codice generato a React/TypeScript/CSS del progetto: non installare Tailwind soltanto perché compare nell'output. Prima ispezionare repo e dipendenze esistenti; nessun vecchio frontend da importare.

Scaricare gli asset statici con la procedura data da Figma e servirli localmente, rispettando icone, slot e proporzioni. Niente URL temporanei nel codice finale e niente screenshot dell'intera UI usato come interfaccia. Le candele, mini-serie e livelli sono contenuti dinamici del provider: realizzarli come grafici dai dati, senza ricopiare i tracciati SVG dimostrativi come se fossero analisi. Nessuna omissione o sostituzione arbitraria delle icone statiche.

Verificare screenshot desktop della dashboard, attesa, pendente, manuale, dati vecchi, bot fermo, rifiuto, chiusura e dialoghi, riusando i checkpoint del task. Riportare differenze del contenuto simulato separatamente da errori di stile/layout.

## Anteprime congelate

- [Dashboard](figma/dashboard.png)
- [Stati](figma/states.png)
- [Conferme](figma/confirmations.png)
- [Componenti](figma/components.png)

Non rappresentano l'app costruita. Modifiche successive al Figma non sono automaticamente un nuovo requisito: confrontare e segnalare variazioni sostanziali prima di applicarle.
