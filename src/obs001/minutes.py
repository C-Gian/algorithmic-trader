"""Minuti 1m validati: parsing dei CSV klines futures USDⓈ-M di Binance Vision.

Ogni minuto della griglia [inizio, fine) ha uno stato: MISSING (nessuna riga), VALID oppure
INVALID (riga corrotta o duplicati discordanti). Nessun buco viene riempito e nessun prezzo
viene scelto fra righe discordanti. Barra interna [open, open+60s), disponibile a open+60s.
"""

from __future__ import annotations

import csv
import io
import math
import zipfile
from array import array
from dataclasses import dataclass, field

from .conventions import MINUTE_MS

MISSING, VALID, INVALID = 0, 1, 2

EXPECTED_COLUMNS = [
    "open_time", "open", "high", "low", "close", "volume", "close_time",
    "quote_volume", "count", "taker_buy_volume", "taker_buy_quote_volume", "ignore",
]

# Oltre questa soglia un open_time non è in millisecondi (es. microsecondi): errore, non euristica.
_MS_UPPER = 10**13


class SchemaError(ValueError):
    """Schema o unità temporale incompatibili: il file non viene interpretato."""


@dataclass
class FileStats:
    name: str
    rows: int = 0
    header: bool = False
    first_open: int | None = None
    last_open: int | None = None
    duplicates_identical: int = 0
    duplicates_discordant_minutes: int = 0
    out_of_order: int = 0
    outside_month: int = 0
    corrupt_rows: int = 0
    anomalies: list[dict] = field(default_factory=list)

    def note(self, kind: str, **info) -> None:
        if len(self.anomalies) < 200:
            self.anomalies.append({"kind": kind, **info})

    def as_dict(self) -> dict:
        return {
            "name": self.name, "rows": self.rows, "header": self.header,
            "firstOpen": self.first_open, "lastOpen": self.last_open,
            "duplicatesIdentical": self.duplicates_identical,
            "duplicatesDiscordantMinutes": self.duplicates_discordant_minutes,
            "outOfOrder": self.out_of_order, "outsideMonth": self.outside_month,
            "corruptRows": self.corrupt_rows, "anomalies": self.anomalies,
        }


class MinuteStore:
    """Colonne per minuto sulla griglia [start, end)."""

    FIELDS = ("o", "h", "l", "c", "v", "q", "tb", "tq")

    def __init__(self, start: int, end: int):
        if start % MINUTE_MS or end % MINUTE_MS or end <= start:
            raise ValueError("griglia minuti non valida")
        self.start = start
        self.end = end
        self.n = (end - start) // MINUTE_MS
        self.status = bytearray(self.n)
        for f in self.FIELDS:
            setattr(self, f, array("d", bytes(8 * self.n)))
        self.trades = array("q", bytes(8 * self.n))
        self._raw: dict[int, tuple] = {}

    def index(self, open_ms: int) -> int:
        return (open_ms - self.start) // MINUTE_MS

    def set_minute(self, i: int, row: tuple) -> None:
        o, h, l, c, v, q, n, tb, tq = row
        self.o[i], self.h[i], self.l[i], self.c[i] = o, h, l, c
        self.v[i], self.q[i], self.trades[i], self.tb[i], self.tq[i] = v, q, n, tb, tq
        self.status[i] = VALID

    def invalidate(self, i: int) -> None:
        self.status[i] = INVALID

    def counts(self, lo: int | None = None, hi: int | None = None) -> dict:
        a = 0 if lo is None else self.index(lo)
        b = self.n if hi is None else self.index(hi)
        seg = self.status[a:b]
        return {"expected": b - a, "valid": seg.count(VALID), "missing": seg.count(MISSING), "invalid": seg.count(INVALID)}

    def truncated(self, cutoff: int) -> "MinuteStore":
        """Copia in cui i minuti con apertura >= cutoff non esistono ancora (prova di causalità)."""
        other = MinuteStore(self.start, self.end)
        k = max(0, min(self.n, self.index(cutoff)))
        other.status[:k] = self.status[:k]
        for f in self.FIELDS:
            getattr(other, f)[:k] = getattr(self, f)[:k]
        other.trades[:k] = self.trades[:k]
        return other


def _finite_positive(x: float) -> bool:
    return math.isfinite(x) and x > 0


def _finite_nonneg(x: float) -> bool:
    return math.isfinite(x) and x >= 0


def _validate_values(o, h, l, c, v, q, n, tb, tq) -> str | None:
    if not all(_finite_positive(x) for x in (o, h, l, c)):
        return "PRICE_NOT_FINITE_POSITIVE"
    if h < max(o, c) or l > min(o, c) or h < l:
        return "OHLC_INCONSISTENT"
    if not all(_finite_nonneg(x) for x in (v, q, tb, tq)):
        return "VOLUME_NEGATIVE_OR_NOT_FINITE"
    if n < 0:
        return "TRADES_NEGATIVE"
    return None


TICK_ROWS = 20_000


def parse_csv_text(text: str, store: MinuteStore, month_start: int, month_end: int, name: str, tick=None) -> FileStats:
    """Interpreta un CSV mensile e popola lo store. Errori di schema sollevano SchemaError.
    tick(rows) facoltativo ogni TICK_ROWS righe: solo avanzamento/annullamento, nessun effetto sui dati."""
    stats = FileStats(name=name)
    reader = csv.reader(io.StringIO(text))
    seen: dict[int, tuple] = {}
    discordant: set[int] = set()
    prev_open: int | None = None
    for line_no, fields in enumerate(reader, start=1):
        if tick is not None and line_no % TICK_ROWS == 0:
            tick(line_no)
        if not fields or (len(fields) == 1 and not fields[0].strip()):
            continue
        if line_no == 1 and fields and not fields[0].strip().lstrip("-").isdigit():
            names = [f.strip() for f in fields]
            if names != EXPECTED_COLUMNS:
                raise SchemaError(f"{name}: intestazione non riconosciuta {names}")
            stats.header = True
            continue
        stats.rows += 1
        if len(fields) != len(EXPECTED_COLUMNS):
            stats.corrupt_rows += 1
            stats.note("FIELD_COUNT", line=line_no, fields=len(fields))
            continue
        try:
            open_ms = int(fields[0])
            close_ms = int(fields[6])
        except ValueError:
            stats.corrupt_rows += 1
            stats.note("TIME_NOT_INTEGER", line=line_no)
            continue
        if open_ms >= _MS_UPPER or close_ms >= _MS_UPPER:
            raise SchemaError(f"{name}: riga {line_no} open_time={open_ms}: unità temporale non in millisecondi")
        if open_ms % MINUTE_MS or close_ms != open_ms + MINUTE_MS - 1:
            stats.corrupt_rows += 1
            stats.note("TIME_NOT_MINUTE_ALIGNED", line=line_no, openTime=open_ms, closeTime=close_ms)
            continue
        if not (month_start <= open_ms < month_end):
            stats.outside_month += 1
            stats.note("OUTSIDE_FILE_MONTH", line=line_no, openTime=open_ms)
            continue
        if prev_open is not None and open_ms <= prev_open:
            stats.out_of_order += 1
        prev_open = open_ms if prev_open is None else max(prev_open, open_ms)
        stats.first_open = open_ms if stats.first_open is None else min(stats.first_open, open_ms)
        stats.last_open = open_ms if stats.last_open is None else max(stats.last_open, open_ms)
        i = store.index(open_ms)
        try:
            o, h, l, c, v = (float(fields[k]) for k in range(1, 6))
            q = float(fields[7])
            n_raw = fields[8].strip()
            n = int(n_raw)
            tb, tq = float(fields[9]), float(fields[10])
        except ValueError:
            stats.corrupt_rows += 1
            stats.note("VALUE_NOT_NUMERIC", line=line_no, openTime=open_ms)
            store.invalidate(i)
            continue
        problem = _validate_values(o, h, l, c, v, q, n, tb, tq)
        if problem:
            stats.corrupt_rows += 1
            stats.note(problem, line=line_no, openTime=open_ms)
            store.invalidate(i)
            discordant.add(i)  # una riga corrotta non viene sostituita da un duplicato successivo
            continue
        row = (o, h, l, c, v, q, n, tb, tq)
        if i in seen:
            if seen[i] == row and i not in discordant:
                stats.duplicates_identical += 1
            elif i not in discordant:
                discordant.add(i)
                stats.duplicates_discordant_minutes += 1
                stats.note("DUPLICATE_DISCORDANT", openTime=open_ms)
                store.invalidate(i)
            continue
        seen[i] = row
        if i in discordant:
            continue
        store.set_minute(i, row)
    return stats


def read_month_zip(path, expected_csv: str) -> str:
    """Legge solo il CSV atteso dallo ZIP, senza estrarre su disco (niente path traversal)."""
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        if expected_csv not in names:
            raise SchemaError(f"{path}: CSV atteso {expected_csv} assente (contenuto: {names})")
        bad = [n for n in names if n != expected_csv]
        if bad:
            raise SchemaError(f"{path}: membri inattesi nello ZIP {bad}")
        with zf.open(expected_csv) as f:
            return f.read().decode("utf-8")
