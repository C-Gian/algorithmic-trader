"""OBS-001: osservazioni causali BTCUSDT perpetual e primo studio descrittivo.

Pipeline batch a sola libreria standard: ZIP/CSV Binance Vision locali -> minuti
validati -> barre 45m/1D -> osservazioni causali per barra -> esiti 24h separati ->
bundle JSON letto dalla dashboard. Nessuna strategia, ordine o valutazione economica.
"""

ENGINE_VERSION = "1.0.0"
BUNDLE_SCHEMA = "obs001.bundle/1"
