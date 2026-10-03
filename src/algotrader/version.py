"""Code version of the running build, never invented.

Order: ``ALGOTRADER_CODE_VERSION`` (when set to a real value) -> ``git rev-parse`` of a checkout ->
the commit recorded at image build time from the build context's git metadata (``BUILD_COMMIT_FILE``).
When none is available the version is ``None`` and every report says so explicitly.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

BUILD_COMMIT_FILE = Path(os.environ.get("ALGOTRADER_BUILD_COMMIT_FILE", "/app/BUILD_COMMIT"))
IMAGE_SUFFIX = "+image"  # commit the image was built from; working-tree changes are not detectable there
_PLACEHOLDERS = {"", "unknown", "none", "null"}
_SHA = re.compile(r"^[0-9a-f]{40}$")


def _real(value: str | None) -> str | None:
    return None if value is None or value.strip().lower() in _PLACEHOLDERS else value.strip()


def code_version() -> str | None:
    env = _real(os.environ.get("ALGOTRADER_CODE_VERSION"))
    if env:
        return env
    try:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5,
                             check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, timeout=5).stdout
        return sha + ("-dirty" if dirty.strip() else "")
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        sha = BUILD_COMMIT_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return sha + IMAGE_SUFFIX if _SHA.match(sha) else None


def describe(version: str | None) -> str:
    """Plain-language rendering for reports and the UI; an absent version stays explicitly absent."""
    v = _real(version)
    if v is None:
        return ("not available — this build carries no commit information (recorded as "
                f"{version!r})" if version else "not available — this build carries no commit information")
    if v.endswith(IMAGE_SUFFIX):
        return (f"{v[:-len(IMAGE_SUFFIX)]} (commit the application image was built from; uncommitted local "
                "changes cannot be detected inside the image)")
    if v.endswith("-dirty"):
        return f"{v[:-len('-dirty')]} with uncommitted local changes"
    return v
