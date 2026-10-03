"""UX pass: truthful code version, pending (not alarming) assurance while a run is in progress, build commit file.

Pure unit tests (no database): the report/endpoint wording that depends on these is covered by the evaluation and
E2E suites.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from algotrader import version
from algotrader.observe.deep_api import assurance_summary

ROOT = Path(__file__).resolve().parents[1]
SHA = "0123456789abcdef0123456789abcdef01234567"


def test_placeholder_versions_are_reported_as_unavailable_never_as_a_version(monkeypatch, tmp_path):
    for placeholder in ("unknown", "", "  ", "None"):
        monkeypatch.setenv("ALGOTRADER_CODE_VERSION", placeholder)
        monkeypatch.setattr(version, "BUILD_COMMIT_FILE", tmp_path / "absent")
        monkeypatch.setattr(version.subprocess, "run", _no_git)
        assert version.code_version() is None
    assert version.describe(None).startswith("not available")
    assert version.describe("unknown").startswith("not available") and "'unknown'" in version.describe("unknown")
    assert "unknown" not in version.describe(None)


def test_build_commit_file_is_used_and_labelled_as_image_build(monkeypatch, tmp_path):
    f = tmp_path / "BUILD_COMMIT"
    f.write_text(SHA + "\n", encoding="utf-8")
    monkeypatch.delenv("ALGOTRADER_CODE_VERSION", raising=False)
    monkeypatch.setattr(version, "BUILD_COMMIT_FILE", f)
    monkeypatch.setattr(version.subprocess, "run", _no_git)
    v = version.code_version()
    assert v == SHA + version.IMAGE_SUFFIX
    assert version.describe(v).startswith(SHA) and "cannot be detected" in version.describe(v)
    f.write_text("not-a-sha", encoding="utf-8")  # malformed content is not trusted
    assert version.code_version() is None
    monkeypatch.setenv("ALGOTRADER_CODE_VERSION", "explicit-1")  # an explicit real value wins
    assert version.code_version() == "explicit-1"
    assert version.describe(SHA + "-dirty") == f"{SHA} with uncommitted local changes"


def _no_git(*a, **k):
    raise OSError("git unavailable")


def test_build_commit_script_resolves_only_exact_commits(tmp_path):
    spec = importlib.util.spec_from_file_location("build_commit", ROOT / "scripts" / "build_commit.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    g = tmp_path / "git"
    (g / "refs" / "heads").mkdir(parents=True)
    (g / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (g / "refs" / "heads" / "main").write_text(SHA + "\n", encoding="utf-8")
    assert mod.resolve(g) == SHA
    (g / "refs" / "heads" / "main").unlink()
    (g / "packed-refs").write_text(f"# pack-refs\n{SHA} refs/heads/main\n", encoding="utf-8")
    assert mod.resolve(g) == SHA
    (g / "HEAD").write_text(SHA[::-1] + "\n", encoding="utf-8")  # detached HEAD
    assert mod.resolve(g) == SHA[::-1]
    (g / "HEAD").write_text("ref: refs/heads/other\n", encoding="utf-8")
    assert mod.resolve(g) is None
    assert mod.resolve(tmp_path / "missing") is None


class _Conn:
    def __init__(self, rows):
        self.rows = rows

    def execute(self, *a, **k):
        return self

    def fetchall(self):
        return self.rows


@pytest.mark.parametrize("state", ["not_checked", "incomplete"])
def test_unfinished_run_shows_pending_checks_not_a_warning(state):
    s = assurance_summary(_Conn([]), "obs-x", {"state": state, "detail": "reconciliation in progress"}, "running")
    assert s["warnings"] == [] and not s["headline"].startswith("ASSURANCE WARNING")
    assert s["runtime"]["pending"] is True and "pending" in s["headline"]
    # once finished, the same state is a visible warning (never silently passed)
    done = assurance_summary(_Conn([]), "obs-x", {"state": state, "detail": "x"}, "cancelled")
    assert done["warnings"] and done["headline"].startswith("ASSURANCE WARNING")
    # a FAILED runtime result is a warning even while the run status is not terminal
    failed = assurance_summary(_Conn([]), "obs-x", {"state": "failed", "detail": "x"}, "running")
    assert failed["warnings"] and "FAILED" in failed["headline"]
