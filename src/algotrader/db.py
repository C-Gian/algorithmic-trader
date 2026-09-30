"""PostgreSQL persistence for runs, checkpoints and the append-only event journal."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version integer PRIMARY KEY,
    applied_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS runs (
    run_id            text PRIMARY KEY,
    created_at        timestamptz NOT NULL DEFAULT now(),
    status            text NOT NULL CHECK (status IN ('queued','running','completed','cancelled','failed')),
    config            jsonb NOT NULL,
    total_steps       integer NOT NULL,
    started_at        timestamptz,
    finished_at       timestamptz,
    cancel_requested  boolean NOT NULL DEFAULT false,
    lease_owner       text,
    lease_expires_at  timestamptz,
    heartbeat_at      timestamptz,
    attempt           integer NOT NULL DEFAULT 0,
    max_attempts      integer NOT NULL DEFAULT 3,
    recovery_log      jsonb NOT NULL DEFAULT '[]'::jsonb,
    error             text,
    manifest          jsonb
);
CREATE INDEX IF NOT EXISTS runs_status_idx ON runs (status, created_at);

-- One row per run: the engine state after the last committed step.
CREATE TABLE IF NOT EXISTS run_checkpoints (
    run_id      text PRIMARY KEY REFERENCES runs(run_id) ON DELETE CASCADE,
    next_step   integer NOT NULL,
    next_seq    integer NOT NULL,
    state       jsonb NOT NULL,
    sim_time    timestamptz,
    updated_at  timestamptz NOT NULL DEFAULT now()
);

-- Append-only semantic journal. (run_id, seq) is the idempotency key.
CREATE TABLE IF NOT EXISTS run_events (
    run_id    text NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    seq       integer NOT NULL,
    step      integer NOT NULL,
    kind      text NOT NULL,
    sim_time  timestamptz NOT NULL,
    payload   jsonb NOT NULL,
    PRIMARY KEY (run_id, seq)
);
CREATE INDEX IF NOT EXISTS run_events_kind_idx ON run_events (run_id, kind, seq);
-- An accounting fill can never be journaled twice for a run.
CREATE UNIQUE INDEX IF NOT EXISTS run_events_fill_uniq
    ON run_events (run_id, (payload->>'fill_id')) WHERE kind = 'fill';
"""

# Durable replay control, restart-safe interruption counting and worker health.
SCHEMA_V2 = """
ALTER TABLE runs ADD COLUMN IF NOT EXISTS paused boolean NOT NULL DEFAULT false;
ALTER TABLE runs ADD COLUMN IF NOT EXISTS step_budget integer NOT NULL DEFAULT 0 CHECK (step_budget >= 0);
ALTER TABLE runs ADD COLUMN IF NOT EXISTS speed double precision NOT NULL DEFAULT 4
    CHECK (speed >= 0 AND speed <= 1000);
-- Consecutive lease-expiry reclaims without a committed step (crash-loop guard).
ALTER TABLE runs ADD COLUMN IF NOT EXISTS interruptions integer NOT NULL DEFAULT 0;
-- Operational control commands; never part of the semantic journal.
ALTER TABLE runs ADD COLUMN IF NOT EXISTS control_log jsonb NOT NULL DEFAULT '[]'::jsonb;
-- Start of the current observed-throughput window (for ETA).
ALTER TABLE runs ADD COLUMN IF NOT EXISTS throughput_since timestamptz;
ALTER TABLE runs ADD COLUMN IF NOT EXISTS throughput_base_step integer;

-- Speed used to live in the run config; it is operational pacing only.
UPDATE runs SET speed = (config->>'speed')::double precision, config = config - 'speed'
WHERE config ? 'speed';

ALTER TABLE runs DROP CONSTRAINT IF EXISTS runs_status_check;
ALTER TABLE runs ADD CONSTRAINT runs_status_check
    CHECK (status IN ('queued','running','paused','completed','cancelled','failed'));

CREATE TABLE IF NOT EXISTS workers (
    worker_id     text PRIMARY KEY,
    host          text NOT NULL,
    pid           integer NOT NULL,
    started_at    timestamptz NOT NULL DEFAULT now(),
    heartbeat_at  timestamptz NOT NULL DEFAULT now(),
    current_run   text
);
"""

# Public market recorder sessions (operational state; distinct from semantic trader runs).
SCHEMA_V3 = """
CREATE TABLE IF NOT EXISTS recorder_sessions (
    session_id        text PRIMARY KEY,
    created_at        timestamptz NOT NULL DEFAULT now(),
    status            text NOT NULL CHECK (status IN
                        ('queued','running','clean','partial','failed','cancelled')),
    config            jsonb NOT NULL,
    stop_requested    boolean NOT NULL DEFAULT false,
    lease_owner       text,
    lease_expires_at  timestamptz,
    heartbeat_at      timestamptz,
    started_at        timestamptz,
    finished_at       timestamptz,
    stats             jsonb NOT NULL DEFAULT '{}'::jsonb,
    error             text,
    manifest          jsonb
);
CREATE INDEX IF NOT EXISTS recorder_sessions_status_idx ON recorder_sessions (status, created_at);
"""

# Real-market observation replay (algotrader.observe.v1): a separate operational path.
# No semantic.v1 run/event rows are ever written for it.
SCHEMA_V4 = """
CREATE TABLE IF NOT EXISTS observation_replays (
    replay_id          text PRIMARY KEY,
    created_at         timestamptz NOT NULL DEFAULT now(),
    status             text NOT NULL CHECK (status IN
                         ('queued','running','paused','completed','cancelled','failed')),
    source_kind        text NOT NULL CHECK (source_kind IN ('dataset','recording')),
    source_id          text NOT NULL,
    config             jsonb NOT NULL,
    total_events       integer NOT NULL CHECK (total_events >= 0),
    paused             boolean NOT NULL DEFAULT false,
    step_budget        integer NOT NULL DEFAULT 0 CHECK (step_budget >= 0),
    speed              double precision NOT NULL DEFAULT 20 CHECK (speed >= 0 AND speed <= 10000),
    cancel_requested   boolean NOT NULL DEFAULT false,
    lease_owner        text,
    lease_expires_at   timestamptz,
    heartbeat_at       timestamptz,
    attempt            integer NOT NULL DEFAULT 0,
    max_attempts       integer NOT NULL DEFAULT 3,
    interruptions      integer NOT NULL DEFAULT 0,
    recovery_log       jsonb NOT NULL DEFAULT '[]'::jsonb,
    control_log        jsonb NOT NULL DEFAULT '[]'::jsonb,
    throughput_since   timestamptz,
    throughput_base    integer,
    started_at         timestamptz,
    finished_at        timestamptz,
    error              text,
    manifest           jsonb
);
CREATE INDEX IF NOT EXISTS observation_replays_status_idx ON observation_replays (status, created_at);

-- One row per replay: the committed feed cursor and the snapshot it produced.
CREATE TABLE IF NOT EXISTS observation_checkpoints (
    replay_id        text PRIMARY KEY REFERENCES observation_replays(replay_id) ON DELETE CASCADE,
    cursor           integer NOT NULL CHECK (cursor >= 0),
    info_time        timestamptz NOT NULL,
    last_event_id    text,
    snapshot_id      text NOT NULL,
    snapshot_digest  text NOT NULL,
    snapshot_view    jsonb NOT NULL,
    updated_at       timestamptz NOT NULL DEFAULT now()
);

-- Append-only committed deliveries. (replay_id, seq) and (replay_id, event_id) are idempotency keys.
CREATE TABLE IF NOT EXISTS observation_deliveries (
    replay_id        text NOT NULL REFERENCES observation_replays(replay_id) ON DELETE CASCADE,
    seq              integer NOT NULL CHECK (seq >= 0),
    event_id         text NOT NULL,
    family           text NOT NULL,
    kind             text NOT NULL,
    available_time   timestamptz NOT NULL,
    record           jsonb NOT NULL,
    payload          jsonb,  -- normalized feed payload (values only for valid observations)
    committed_at     timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (replay_id, seq),
    UNIQUE (replay_id, event_id)
);
CREATE INDEX IF NOT EXISTS observation_deliveries_family_idx ON observation_deliveries (replay_id, family, seq);
"""

MIGRATIONS: dict[int, str] = {1: SCHEMA_V1, 2: SCHEMA_V2, 3: SCHEMA_V3, 4: SCHEMA_V4}
SCHEMA_VERSION = max(MIGRATIONS)


def database_url() -> str:
    url = os.environ.get("ALGOTRADER_DATABASE_URL")
    if not url:
        raise RuntimeError("ALGOTRADER_DATABASE_URL is not set")
    return url


def connect(url: str | None = None, **kw) -> psycopg.Connection:
    return psycopg.connect(url or database_url(), row_factory=dict_row, **kw)


@contextmanager
def connection(url: str | None = None) -> Iterator[psycopg.Connection]:
    conn = connect(url)
    try:
        yield conn
    finally:
        conn.close()


def migrate(url: str | None = None, target: int = SCHEMA_VERSION) -> None:
    """Apply pending migrations in order, in one transaction (idempotent)."""
    with connection(url) as conn, conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(4242001)")
        conn.execute(MIGRATIONS[1])  # creates schema_migrations on a fresh database
        applied = {r["version"] for r in conn.execute("SELECT version FROM schema_migrations")}
        for version in sorted(v for v in MIGRATIONS if v <= target):
            if version not in applied:
                conn.execute(MIGRATIONS[version])
                conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (version,))
