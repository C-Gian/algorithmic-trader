# Stato del nuovo progetto

Aggiornato: 2026-10-16. Responsabile: Director.

## Fatto

- Fondazione funzionale, tre utilità isolate; DESIGN-001 NON APPROVATO e NON ATTIVO.
- UI-001 consegnato da Claude a 939c866fb847fcc489979d99b2080e0c96bedca7: dashboard locale React/TypeScript/Vite, provider simulato separato e scenari LONG/SHORT. Nessun dato reale o collegamento exchange.
- Figma letto dal Director; accesso dell'esecutore dichiarato riuscito con nodi/metodo nella consegna. Riferimento e immagini in docs/ui.
- Review indipendente del Director: installazione pulita, 28 test originali e build riusciti; lettura del codice e confronto di quattro immagini dell'esecutore con Figma.
- Due sonde temporanee riproducono conferma obsoleta su scenario diverso e testi non qualificati delle protezioni durante disconnessione. Individuata anche icona history deformata nei riquadri aggiornamento.
- Correzioni R1-A/B/C consegnate da Claude (commit che aggiorna questo file). Conferme legate all'impronta del contesto e dialogo isolato. Con feed non regolare: ultimi noti, Start e ripresa bloccati, badge di sospensione. Icona history alla misura naturale.

## Incarico corrente

**UI-001/R1 — DELIVERED**, in attesa di review del Director. Consegna e verifiche nella sezione «Consegna R1» di current_task.md. Non ACCEPTED.

## Verifiche e limiti

Il Director ha rieseguito i test/build nella propria copia. Non ha completato la prova browser indipendente perché manca Chromium nell'ambiente; le immagini esaminate e il percorso browser completo sono evidenze di Claude. Prova d'uso Owner ancora mancante.

Verifiche R1 dichiarate da Claude, non ancora riesaminate dal Director:
- 45 test Vitest: 28 originali e 17 nuovi. I 6 nuovi test UI falliscono sul codice di 939c866.
- Typecheck e build.
- Prova in Chrome locale headless sulla build: geometria di 423 icone, isolamento del dialogo, invalidazione delle conferme, feed STALE e DISCONNECTED, percorso Owner fino a 10.005,793.

Avviso esbuild riprodotto da Claude con `npm ci` (npm 11.19.0, Node 24.14.1): `npm warn install-scripts 1 package has install scripts not yet covered by allowScripts: esbuild@0.25.12 (postinstall: node install.js)`. Senza approvare lo script, test e build riescono su questo PC Windows; il risultato non è generalizzato ad altri ambienti. Lo stesso `npm ci` riporta 4 vulnerabilità `npm audit`: vite ≤ 6.4.2, tinypool e @vitest/mocker. Nessun aggiornamento eseguito: decide il Director.

Convenzioni di uscita/medie illustrate approvate soltanto come simulazione; nessun protocollo exchange o strategia approvato. Il modello di contabilità delle fixture resta invariato.

## Vincoli

Banner: “SIMULAZIONE LOCALE — nessun collegamento exchange”.
Nessuna acquisizione, backtest, algoritmo decisionale, accesso Owner/exchange, ordine esterno o apertura protetta.
Vecchi studi INACTIVE; [esposizioni](docs/research/EXPOSURES.md) invariate.
[PRODUCT-CONTEXT](docs/functional/PRODUCT-CONTEXT.md) unico riferimento funzionale.
