"""Shared fixtures.

Database tests need ``ALGOTRADER_TEST_DATABASE_URL`` pointing at a PostgreSQL
server where the user may CREATE DATABASE (e.g. the maintenance ``postgres``
database). Each test gets a fresh, uniquely named database. If
``ALGOTRADER_REQUIRE_DB=1`` (set in CI) a missing URL is an error, not a skip.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from psycopg import sql

from algotrader import db
from algotrader.engine import Engine, trace_hash
from algotrader.synthetic import build_fixture


def _admin_url() -> str:
    url = os.environ.get("ALGOTRADER_TEST_DATABASE_URL")
    if not url:
        if os.environ.get("ALGOTRADER_REQUIRE_DB") == "1":
            pytest.fail("ALGOTRADER_TEST_DATABASE_URL is required (ALGOTRADER_REQUIRE_DB=1)")
        pytest.skip("ALGOTRADER_TEST_DATABASE_URL not set")
    return url


def _with_dbname(url: str, name: str) -> str:
    info = psycopg.conninfo.conninfo_to_dict(url)
    info["dbname"] = name
    return psycopg.conninfo.make_conninfo(**info)


@pytest.fixture
def database_url() -> Iterator[str]:
    admin = _admin_url()
    name = f"algotrader_test_{uuid.uuid4().hex[:10]}"
    with psycopg.connect(admin, autocommit=True) as c:
        c.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    url = _with_dbname(admin, name)
    db.migrate(url)
    try:
        yield url
    finally:
        with psycopg.connect(admin, autocommit=True) as c:
            c.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name)))


@pytest.fixture
def artifact_root(tmp_path: Path) -> Path:
    return tmp_path / "artifacts"


@pytest.fixture(scope="session")
def reference_trace() -> tuple[str, int]:
    """Semantic trace of the pinned fixture computed purely in-process."""
    _, events = Engine(build_fixture()).run_all()
    return trace_hash([e.semantic() for e in events]), len(events)
