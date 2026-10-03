"""Image build helper: record the commit of the build context, or nothing.

Usage: python build_commit.py <git-metadata-dir> <output-file>

Reads only HEAD, refs/ and packed-refs (the build context includes no other git data). Writes the 40-hex commit
when it can be resolved exactly; otherwise writes no file, so the application reports the version as unavailable
instead of guessing. Working-tree changes cannot be detected from this metadata.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SHA = re.compile(r"^[0-9a-f]{40}$")


def resolve(git: Path) -> str | None:
    try:
        head = (git / "HEAD").read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if SHA.match(head):
        return head
    if not head.startswith("ref: "):
        return None
    ref = head[5:].strip()
    try:
        value = (git / ref).read_text(encoding="utf-8").strip()
        return value if SHA.match(value) else None
    except OSError:
        pass
    try:
        for line in (git / "packed-refs").read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[1] == ref and SHA.match(parts[0]):
                return parts[0]
    except OSError:
        pass
    return None


if __name__ == "__main__":
    sha = resolve(Path(sys.argv[1]))
    if sha:
        Path(sys.argv[2]).write_text(sha + "\n", encoding="utf-8")
    print(f"build commit: {sha or 'not available'}")
