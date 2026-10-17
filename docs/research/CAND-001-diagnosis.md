# CAND-001/D1 — diagnosi della politica v1 sul DEV 2023–2024

**Stato del documento: piano ed elenco degli esempi pubblicati prima dell'estrazione dei percorsi.** Le sezioni con i risultati saranno aggiunte nella consegna D1.

**Licenza di questo file:** derivati aggregati di dati Binance Vision, **CC BY-NC-SA 4.0** (https://creativecommons.org/licenses/by-nc-sa/4.0/). Fonte: Binance Vision (https://data.binance.vision). Dati grezzi e bundle non sono redistribuiti.

## 1. Piano

Perimetro e passi seguono `current_task.md` (CAND-001/D1, commit dell'incarico `12c195b`).

1. **Identità degli input.** Bundle DEV accettato `CAND-001-v1.0.0-e1.0.1-DEV-adaa94c502-aed2c4ef62`, SHA256 `b141150237e94a807817adea2d9fb6810f6eabc220d7db5ea3602d8b79b4944a`, inputHash `adaa94c50261a9650b3e908c28824db2dd91d3adecd46d1e6174b7cda93871a2`, config v1 `aed2c4ef627617d73972778097bbab5fb702ab5064ce9e6eb68ded2170ce4edf`. Il bundle preferito è presente: non si usa un altro run. Esiste anche un run DEV del motore 1.0.3, non usato per la regola di preferenza del task e non per il suo contenuto.
2. **Selezione degli esempi** (questo documento, sezione 2): solo dal bundle, con la regola cronologica del task. Pubblicata prima di leggere i percorsi minuto per minuto.
3. **Estrazione.** Un record per ciascuna delle 78 operazioni, dal bundle e dai soli minuti negoziati DEV già verificati (2022-10 … 2024-12; il prefisso serve solo alle osservazioni delle timeline). Nessun 2025, nessun download, nessun ricalcolo di decisioni: motore decisionale e ledger non vengono eseguiti.
4. **Riconciliazione** di 78 operazioni, 87 richieste, 814 episodi e netto non arrotondato con il bundle; identità dei costi su ogni record; hash degli input prima e dopo.
5. **Riepilogo** descrittivo e classi del protocollo, senza proporre revisioni, soglie o varianti.

Output estesi fuori Git in `algorithmic-trader-data/CAND-001/diagnosis/D1/`.

## 2. Esempi selezionati (regola fissata prima dei percorsi)

Regola del task, sezione 2: per ciascun verso il primo trade con netto positivo, il primo con netto negativo, il primo con stop aggiornato, la prima astensione `ABSTAIN_REWARD_RISK`, la prima `INVALIDATED_DEPTH` e la prima richiesta `REJECTED_PRICE`; in più il primo `EXIT_STRUCTURE` e il primo `TIME_EXIT` complessivi. Ordine: tempo pertinente, poi ID. Il caso è l'episodio; un caso scelto da più categorie compare una volta con tutte le categorie. Massimo 14 casi.

Tempo pertinente per categoria:
- netto positivo o negativo: ingresso modellato;
- stop aggiornato: prima attivazione di un nuovo stop (almeno un aggiornamento effettivamente attivato);
- astensioni: conclusione dell'episodio;
- `REJECTED_PRICE`: istante del tentativo;
- `EXIT_STRUCTURE` e `TIME_EXIT`: uscita contabile.

Netto positivo o negativo e motivo d'uscita sono **categorie a posteriori**; la scelta all'interno di ogni categoria è solo cronologica.

**Esito: 13 casi, nessuna categoria vuota.** Il primo trade SHORT negativo è anche il primo SHORT con stop aggiornato.

| # | Episodio | Operazione | Verso | Categorie | Tempo pertinente | t0 (gamba riconosciuta) | Call | Ingresso / tentativo | Fine episodio (UTC) |
|---:|---|---|---|---|---|---|---|---|---|
| 1 | `EP:SHORT:1672496100000:1672525800000` | `TR:SHORT:1672496100000:1672525800000` | SHORT | primo negativo; primo stop aggiornato | 2023-01-01 03:46 | 2023-01-01 00:45 | 2023-01-01 03:45 | 2023-01-01 03:46 | 2023-01-01 11:58 |
| 2 | `EP:LONG:1672585200000:1672604100000` | — | LONG | prima `ABSTAIN_REWARD_RISK` | 2023-01-01 23:15 | 2023-01-01 22:30 | — | — | 2023-01-01 23:15 |
| 3 | `EP:LONG:1672793100000:1672803900000` | `TR:LONG:1672793100000:1672803900000` | LONG | primo positivo | 2023-01-04 06:46 | 2023-01-04 06:00 | 2023-01-04 06:45 | 2023-01-04 06:46 | 2023-01-04 08:23 |
| 4 | `EP:SHORT:1672992900000:1673011800000` | — | SHORT | prima `INVALIDATED_DEPTH` | 2023-01-06 15:45 | 2023-01-06 15:45 | — | — | 2023-01-06 15:45 |
| 5 | `EP:LONG:1673271000000:1673287200000` | — | LONG | prima `INVALIDATED_DEPTH` | 2023-01-09 20:15 | 2023-01-09 20:15 | — | — | 2023-01-09 20:15 |
| 6 | `EP:LONG:1673651700000:1673654400000` | `TR:LONG:1673651700000:1673654400000` | LONG | primo negativo | 2023-01-14 06:46 | 2023-01-14 02:15 | 2023-01-14 06:45 | 2023-01-14 06:46 | 2023-01-14 09:18 |
| 7 | `EP:SHORT:1674329400000:1674353700000` | — | SHORT | prima `REJECTED_PRICE` | 2023-01-22 08:16 | 2023-01-22 04:30 | 2023-01-22 08:15 | 2023-01-22 08:16 (rifiutata) | 2023-01-22 08:16 |
| 8 | `EP:SHORT:1675050300000:1675080000000` | — | SHORT | prima `ABSTAIN_REWARD_RISK` | 2023-01-30 15:45 | 2023-01-30 14:15 | — | — | 2023-01-30 15:45 |
| 9 | `EP:SHORT:1675593000000:1675622700000` | `TR:SHORT:1675593000000:1675622700000` | SHORT | primo positivo | 2023-02-06 02:16 | 2023-02-05 21:00 | 2023-02-06 02:15 | 2023-02-06 02:16 | 2023-02-06 05:28 |
| 10 | `EP:LONG:1680485400000:1680517800000` | — | LONG | prima `REJECTED_PRICE` | 2023-04-03 14:16 | 2023-04-03 12:45 | 2023-04-03 14:15 | 2023-04-03 14:16 (rifiutata) | 2023-04-03 14:16 |
| 11 | `EP:LONG:1682610300000:1682621100000` | `TR:LONG:1682610300000:1682621100000` | LONG | primo stop aggiornato | 2023-04-28 08:16 | 2023-04-27 21:00 | 2023-04-28 04:30 | 2023-04-28 04:31 | 2023-04-28 08:18 |
| 12 | `EP:SHORT:1691155800000:1691180100000` | `TR:SHORT:1691155800000:1691180100000` | SHORT | primo `EXIT_STRUCTURE` (complessivo) | 2023-08-05 06:46 | 2023-08-04 22:30 | 2023-08-05 01:30 | 2023-08-05 01:31 | 2023-08-05 06:46 |
| 13 | `EP:SHORT:1692243900000:1692306000000` | `TR:SHORT:1692243900000:1692306000000` | SHORT | primo `TIME_EXIT` (complessivo) | 2023-08-19 03:01 | 2023-08-17 23:15 | 2023-08-18 03:00 | 2023-08-18 03:01 | 2023-08-19 03:01 |

Gli ID degli episodi contengono gli istanti di apertura delle candele di P0 e P1 (ms UTC). L'elenco completo, con tempi in ms, è in `diagnosis/D1/examples-selection.json`, `listSha256` `7caade6984943a7e333660dc4ef702e6ed87022b58ec7c386e70ecd308a8c3be` (hash canonico della lista e delle categorie vuote). Comando: `$env:PYTHONPATH = "src"; python3.12 -m cand001.diagnosis select`.

**Dichiarazione.** Prima della selezione ho stampato, per capire la struttura del bundle, il record completo della prima operazione del ledger (caso 1: stati, piano ed economia del bundle, nessun minuto). Nessun altro percorso individuale è stato letto prima di questa pubblicazione. L'elenco non dipende da quella lettura: deriva solo dalla regola qui sopra.
