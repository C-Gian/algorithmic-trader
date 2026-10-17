# OBS-002 — prosecuzione ed esaurimento del primo tentativo di ripresa (DEV 2023–2024)

**Stato: popolazione registrata prima degli esiti.** I risultati saranno aggiunti nella consegna.

**Licenza di questo file:** derivati aggregati di dati Binance Vision, **CC BY-NC-SA 4.0** (https://creativecommons.org/licenses/by-nc-sa/4.0/). Fonte: Binance Vision (https://data.binance.vision). Dati grezzi, registri e pacchetti non sono redistribuiti.

## 1. Preregistrazione e identità prima degli esiti

- Incarico: `current_task.md` al commit `6f1743d`; convenzioni `config/OBS-002-v1.json`, SHA256 canonico `b11bad4557cbe45063b7beaf2026d53d63b17cbb944ada2e226a31d6d2a2d0af`; osservatore OBS-001/v1 invariato `3c4eb884d0b6752bfb31e7d9ae159a1414d75cadc90f9abcc9379d5825002387`.
- Codice e 15 test sintetici pubblicati nel commit `36f6153`, prima di elaborare dati reali.
- Input: 27 ZIP trade 1m Binance Vision BTCUSDT perpetual, mesi elencati esplicitamente 2022-10…2024-12, già conservati nella cartella CAND-001 e verificati sul manifest e sul checksum del fornitore. inputHash `3b768886424b4907ef3fb794d9c1e3f565d2f7d28f023e3658763b297db24a5e`; 1.185.120 minuti validi su 1.185.120. Nessun download, nessun mese 2025/2026.
- **Popolazione e snapshot (senza esiti):** run `OBS-002-v1.0.0-e1.0.0-3b76888642-b11bad4557`, `population.json` SHA256 `e0be48abf1c5ea63343f16fdd271493bce716a34009e942b7ff2397521b4a278`. 6.568 versioni, 5.698 gruppi, 7.389 tentativi nell'intero input, di cui 6.582 con origine DEV. Hash dell'identità (config, osservatore, motore, input) `67edb71f5d5b55bc6e3430373b7c6f760a916fdd4ebd896265065df819447a7b`.
- Il comando degli esiti ricalcola la popolazione e si ferma se l'hash non coincide con quello qui registrato.
- Regola degli esempi: quella del task §6, applicata dal codice di `36f6153` (`src/obs002/examples.py`). L'elenco effettivo sarà pubblicato dopo l'estrazione.
