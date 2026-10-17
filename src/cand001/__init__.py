"""CAND-001: primo candidato movimento -> reazione -> tentativo di ripresa e backtest di sviluppo.

Riusa parsing, aggregazione e osservatore OBS-001 (stesse definizioni, nuovi confini). Il motore
decisionale (decision.py) e il ledger di esecuzione/costi (execution.py) sono moduli separati:
le decisioni non ricevono esiti economici, funding o minuti futuri.
"""

ENGINE_VERSION = "1.0.0"
BUNDLE_SCHEMA = "cand001.bundle/1"
