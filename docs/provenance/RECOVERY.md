# Provenienza del piccolo recupero tecnico

Questo documento registra una migrazione, non definisce strategia o architettura applicativa.

Origine: `C-Gian/algorithmic-trader`, SHA `b8f8e2d4b9eb531dcab4e609a037c02024087414`. Dopo la rinomina dell'Owner il riferimento è [algorithmic-trader-archive](https://github.com/C-Gian/algorithmic-trader-archive/tree/b8f8e2d4b9eb531dcab4e609a037c02024087414).

| Nuovo file | Provenienza | Variazione |
|---|---|---|
| `.gitattributes` | File omonimo | Identico; solo conservazione byte delle fixture |
| `src/trading_primitives/file_hashes.py` | `src/algotrader/observe/feedcache.py`, `sha256_file` | Funzione identica, modulo estratto |
| `src/trading_primitives/time_intervals.py` | `src/algotrader/temporal/calendar.py` | Solo aritmetica UTC; input origine/durata obbligatori, nessuna policy del vecchio motore |
| `src/trading_primitives/decimal_steps.py` | `src/algotrader/adviser/measures.py`, arrotondamento al tick | Nessun indicatore; passi espliciti, validazione input, aritmetica indipendente dalla precisione Decimal |
| `tests/test_*` relativi alle tre primitive | Nuovi | 14 test isolati, senza DB o progetto precedente |

Nessun metodo, parametro, profilo di costo, corpus di mercato, stato di conto, ordine o collegamento exchange viene importato. Non esiste una nuova “v0.8” implicita. I periodi dei vecchi studi restano distinti dalla nuova ricerca.

I moduli richiedono solo la libreria standard Python (sintassi/API compatibili da 3.11; prova effettiva su 3.12.14). Non importare vecchi lockfile o configurazioni per eseguirli. Esecuzione locale dalla radice, su shell POSIX:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

Su PowerShell:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

È un controllo di poche funzioni, non una suite applicativa né un backtest. L'integrazione nel prodotto nuovo verrà fatta con il suo incarico. Nessun test riuscito qui certifica una futura esecuzione su exchange.
