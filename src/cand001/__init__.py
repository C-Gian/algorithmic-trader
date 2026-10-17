"""CAND-001: primo candidato movimento -> reazione -> tentativo di ripresa e backtest di sviluppo.

Riusa parsing, aggregazione e osservatore OBS-001 (stesse definizioni, nuovi confini). Il motore
decisionale (decision.py) e il ledger di esecuzione/costi (execution.py) sono moduli separati:
le decisioni non ricevono esiti economici, funding o minuti futuri.
"""

# 1.0.1 (review CAND-001/R1): funding non certificato blocca il run economico; percorsi irrisolti
# conservano i fatti noti e rendono mancanti i risultati completi. Candidato e config invariati.
# 1.0.2 (supporto ADDITIONAL_2025): prefisso osservativo intero dal 2022-10-01 in ogni fase, riuso
# verificato degli archivi OBS-001, acquisizione dei soli mancanti. Decisioni, ledger e config invariati.
# 1.0.3 (APP-001): profili applicativi con finestra propria (prova di gennaio 2025), eventi facoltativi
# di avanzamento/annullamento nei loop, percorso comune CLI/servizio con pubblicazione atomica.
# Schema /3 = /2 più l'identità del profilo. Decisioni, ledger, costi e config invariati.
ENGINE_VERSION = "1.0.3"
BUNDLE_SCHEMA = "cand001.bundle/3"
