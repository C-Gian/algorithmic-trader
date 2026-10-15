"""Streaming SHA-256 of existing files, not a proof of data quality or provenance.

Recovered from algotrader/observe/feedcache.py: sha256_file, unchanged body.
No feed-cache formats, database access or acquisition are imported.
The caller must provide a stable file: concurrent modifications are not detected.
"""

import hashlib
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
