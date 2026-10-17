"""APP-001: servizio locale personale che avvia, segue e ritrova i backtest CAND-001 dall'app.

Un solo processo su 127.0.0.1 con un solo worker di calcolo (thread dedicato); stato delle
esecuzioni su file in <cartella dati>/jobs, risultati deterministici nei runs/ esistenti. Il
servizio chiama lo stesso percorso del comando diretto (cand001.pipeline) e non scarica nulla.
"""

SERVICE_VERSION = "1.0.1"  # R1: completezza economica distinta, progresso dopo interruzione
DEFAULT_PORT = 8765
FRONTEND_ORIGINS = ("http://127.0.0.1:5173", "http://localhost:5173")
