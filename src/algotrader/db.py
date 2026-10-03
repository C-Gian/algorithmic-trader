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

# Owner evaluation workbench (operational state only; no domain contract changes):
# local corpus bindings, durable corpus acquisition jobs and evaluation facades over observation replays.
SCHEMA_V5 = """
CREATE TABLE IF NOT EXISTS corpus_jobs (
    job_id             text PRIMARY KEY,
    chunk_id           text NOT NULL,
    plan_id            text NOT NULL,
    created_at         timestamptz NOT NULL DEFAULT now(),
    status             text NOT NULL CHECK (status IN ('queued','running','completed','cancelled','failed')),
    cancel_requested   boolean NOT NULL DEFAULT false,
    base_url           text NOT NULL,
    lease_owner        text,
    lease_expires_at   timestamptz,
    heartbeat_at       timestamptz,
    attempt            integer NOT NULL DEFAULT 0,
    max_attempts       integer NOT NULL DEFAULT 3,
    interruptions      integer NOT NULL DEFAULT 0,
    attempt_started_at timestamptz,
    recovery_log       jsonb NOT NULL DEFAULT '[]'::jsonb,
    progress           jsonb NOT NULL DEFAULT '{}'::jsonb,
    started_at         timestamptz,
    finished_at        timestamptz,
    outcome            text,
    dataset_id         text,
    result             jsonb,
    error              text
);
CREATE INDEX IF NOT EXISTS corpus_jobs_status_idx ON corpus_jobs (status, created_at);
CREATE INDEX IF NOT EXISTS corpus_jobs_chunk_idx ON corpus_jobs (chunk_id, created_at);
-- At most one active preparation per logical chunk.
CREATE UNIQUE INDEX IF NOT EXISTS corpus_jobs_one_active
    ON corpus_jobs (chunk_id) WHERE status IN ('queued','running');

CREATE TABLE IF NOT EXISTS corpus_chunks (
    chunk_id               text PRIMARY KEY,
    plan_id                text NOT NULL,
    start_time             timestamptz NOT NULL,
    end_time               timestamptz NOT NULL,
    inst_id                text NOT NULL,
    base_url               text NOT NULL,
    dataset_id             text NOT NULL,
    manifest_sha256        text NOT NULL,
    quality_status         text NOT NULL,
    verification_ok        boolean NOT NULL,
    verification_problems  jsonb NOT NULL DEFAULT '[]'::jsonb,
    verified_at            timestamptz,
    retrieved_at           timestamptz,
    bytes_on_disk          bigint NOT NULL,
    storage                jsonb NOT NULL,
    bound_at               timestamptz NOT NULL DEFAULT now(),
    bound_by_job           text,
    outcome                text NOT NULL,
    previous_dataset_id    text
);

CREATE TABLE IF NOT EXISTS evaluations (
    evaluation_id  text PRIMARY KEY,
    replay_id      text NOT NULL UNIQUE REFERENCES observation_replays(replay_id) ON DELETE CASCADE,
    run_type       text NOT NULL CHECK (run_type IN ('observation_only')),
    preset         text NOT NULL,
    plan_id        text NOT NULL,
    chunk_id       text NOT NULL,
    dataset_id     text NOT NULL,
    corpus         jsonb NOT NULL,
    created_at     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS evaluations_created_idx ON evaluations (created_at);
"""

# WP-008-R1A: observable job lifecycle (operational only; additive). Rows created before this migration
# keep lifecycle_version 1 (verified config fixed at launch) and are never relaxed: the CHECK below keeps
# config/total mandatory for them. New launches (lifecycle_version 2) persist a lightweight launch envelope
# first; the worker-owned preparation persists the verified config/total before the first causal step.
# Pre-upgrade nonterminal replays receive an additive operational suspension (their historical status,
# lease, checkpoint and deliveries are left exactly as they were) so the new workers never auto-claim them.
SCHEMA_V6 = """
ALTER TABLE observation_replays ALTER COLUMN config DROP NOT NULL;
ALTER TABLE observation_replays ALTER COLUMN total_events DROP NOT NULL;
ALTER TABLE observation_replays ADD COLUMN IF NOT EXISTS lifecycle_version integer NOT NULL DEFAULT 1;
ALTER TABLE observation_replays ADD CONSTRAINT observation_replays_legacy_config
    CHECK (lifecycle_version >= 2 OR (config IS NOT NULL AND total_events IS NOT NULL));
ALTER TABLE observation_replays ADD COLUMN IF NOT EXISTS launch jsonb;
ALTER TABLE observation_replays ADD COLUMN IF NOT EXISTS lease_generation bigint NOT NULL DEFAULT 0;
ALTER TABLE observation_replays ADD COLUMN IF NOT EXISTS phase text;
ALTER TABLE observation_replays ADD COLUMN IF NOT EXISTS phase_started_at timestamptz;
ALTER TABLE observation_replays ADD COLUMN IF NOT EXISTS phase_history jsonb NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE observation_replays ADD COLUMN IF NOT EXISTS progress jsonb NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE observation_replays ADD COLUMN IF NOT EXISTS progress_seq bigint NOT NULL DEFAULT 0;
ALTER TABLE observation_replays ADD COLUMN IF NOT EXISTS last_progress_at timestamptz;
ALTER TABLE observation_replays ADD COLUMN IF NOT EXISTS assurance jsonb;
ALTER TABLE observation_replays ADD COLUMN IF NOT EXISTS metrics jsonb NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE observation_replays ADD COLUMN IF NOT EXISTS supervisor jsonb NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE observation_replays ADD COLUMN IF NOT EXISTS diagnostic_log jsonb NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE observation_replays ADD COLUMN IF NOT EXISTS suspended_at timestamptz;
ALTER TABLE observation_replays ADD COLUMN IF NOT EXISTS suspension jsonb;
UPDATE observation_replays
   SET suspended_at = now(),
       suspension = jsonb_build_object(
         'reason', 'pre-upgrade nonterminal observation replay (lifecycle v1, WP-007/WP-008 engine) suspended at '
                   || 'the WP-008-R1A upgrade; preserved read-only, never auto-claimed or finalized by the new workers',
         'historical_status', status,
         'historical_lease_owner', lease_owner,
         'historical_lease_expires_at', lease_expires_at,
         'migration', 6)
 WHERE lifecycle_version = 1 AND status IN ('queued', 'running', 'paused') AND suspended_at IS NULL;

ALTER TABLE corpus_jobs ADD COLUMN IF NOT EXISTS lease_generation bigint NOT NULL DEFAULT 0;
ALTER TABLE corpus_jobs ADD COLUMN IF NOT EXISTS phase_history jsonb NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE corpus_jobs ADD COLUMN IF NOT EXISTS progress_seq bigint NOT NULL DEFAULT 0;
ALTER TABLE corpus_jobs ADD COLUMN IF NOT EXISTS last_progress_at timestamptz;
ALTER TABLE corpus_chunks ADD COLUMN IF NOT EXISTS bound_generation bigint;
"""

# WP-008-R1B: streaming engine storage (operational; additive). New runs (lifecycle_version 3, engine_format
# 'observe.stream.v1') persist compact committed input ranges and restorable checkpoints instead of one
# delivery row/transaction per event. Pre-R1B nonterminal R1A runs (lifecycle 2) receive the same additive
# suspension as pre-R1A runs: preserved read-only, never reclaimed under the new engine.
SCHEMA_V7 = """
ALTER TABLE observation_replays ADD COLUMN IF NOT EXISTS engine_format text;
ALTER TABLE observation_replays ADD COLUMN IF NOT EXISTS engine jsonb;

CREATE TABLE IF NOT EXISTS observation_ranges (
    replay_id          text NOT NULL REFERENCES observation_replays(replay_id) ON DELETE CASCADE,
    range_seq          integer NOT NULL CHECK (range_seq >= 0),
    generation         bigint NOT NULL,
    from_cursor        integer NOT NULL CHECK (from_cursor >= 0),
    to_cursor          integer NOT NULL,
    event_count        integer NOT NULL,
    first_order        text NOT NULL,
    last_order         text NOT NULL,
    commitment_before  text NOT NULL,
    commitment_after   text NOT NULL,
    committed_at       timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (replay_id, range_seq),
    UNIQUE (replay_id, from_cursor),
    UNIQUE (replay_id, to_cursor),
    CHECK (to_cursor > from_cursor AND event_count = to_cursor - from_cursor)
);

CREATE TABLE IF NOT EXISTS observation_restore_points (
    replay_id        text NOT NULL REFERENCES observation_replays(replay_id) ON DELETE CASCADE,
    cursor           integer NOT NULL CHECK (cursor >= 0),
    generation       bigint NOT NULL,
    state_format     text NOT NULL,
    fingerprint      text NOT NULL,
    state_blob       bytea NOT NULL,
    state_sha256     text NOT NULL,
    snapshot_id      text NOT NULL,
    snapshot_digest  text NOT NULL,
    info_time        timestamptz NOT NULL,
    commitment       text NOT NULL,
    terminal         boolean NOT NULL DEFAULT false,
    created_at       timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (replay_id, cursor)
);

UPDATE observation_replays
   SET suspended_at = now(),
       suspension = jsonb_build_object(
         'reason', 'pre-R1B nonterminal observation replay (lifecycle v2, per-event engine) suspended at the '
                   || 'WP-008-R1B upgrade; preserved read-only, never reclaimed or converted by the streaming engine',
         'historical_status', status,
         'historical_lease_owner', lease_owner,
         'historical_lease_expires_at', lease_expires_at,
         'migration', 7)
 WHERE lifecycle_version = 2 AND status IN ('queued', 'running', 'paused') AND suspended_at IS NULL;
"""

# WP-008-R1B correction: trusted feed-cache receipts. A receipt is written only after the cache directory has
# been durably published from a verified private source snapshot; it pins the cache manifest SHA-256 outside
# the (mutable) cache directory. Fresh warm launches require a matching receipt.
SCHEMA_V8 = """
CREATE TABLE IF NOT EXISTS observation_feed_caches (
    cache_id               text PRIMARY KEY,
    cache_manifest_sha256  text NOT NULL,
    cache_key              jsonb NOT NULL,
    source_kind            text NOT NULL,
    source_id              text NOT NULL,
    source_manifest_sha256 text NOT NULL,
    event_count            integer NOT NULL,
    partitions             integer NOT NULL,
    bytes_on_disk          bigint NOT NULL,
    durability             text NOT NULL,
    verification           text NOT NULL,
    created_by             jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at             timestamptz NOT NULL DEFAULT now()
);
"""

# WP-008-R1C: assurance. Committed ranges additionally record the materialized snapshot digest and the
# restorable state SHA-256 at their end cursor (comparison points for optional Deep validation; NULL for runs
# committed before this migration). Deep validations are separate durable diagnostic jobs linked to a run;
# they never modify the originating run's records.
SCHEMA_V9 = """
ALTER TABLE observation_ranges ADD COLUMN IF NOT EXISTS snapshot_digest text;
ALTER TABLE observation_ranges ADD COLUMN IF NOT EXISTS state_sha256 text;

CREATE TABLE IF NOT EXISTS observation_deep_validations (
    validation_id     text PRIMARY KEY,
    replay_id         text NOT NULL REFERENCES observation_replays(replay_id) ON DELETE CASCADE,
    created_at        timestamptz NOT NULL DEFAULT now(),
    status            text NOT NULL CHECK (status IN ('queued','running','paused','completed','cancelled','failed')),
    paused            boolean NOT NULL DEFAULT false,
    cancel_requested  boolean NOT NULL DEFAULT false,
    lease_owner       text,
    lease_generation  bigint NOT NULL DEFAULT 0,
    lease_expires_at  timestamptz,
    heartbeat_at      timestamptz,
    attempt           integer NOT NULL DEFAULT 0,
    max_attempts      integer NOT NULL DEFAULT 3,
    interruptions     integer NOT NULL DEFAULT 0,
    started_at        timestamptz,
    finished_at       timestamptz,
    phase             text,
    phase_started_at  timestamptz,
    phase_history     jsonb NOT NULL DEFAULT '[]'::jsonb,
    progress          jsonb NOT NULL DEFAULT '{}'::jsonb,
    progress_seq      bigint NOT NULL DEFAULT 0,
    last_progress_at  timestamptz,
    throughput_since  timestamptz,
    throughput_base   integer,
    metrics           jsonb NOT NULL DEFAULT '{}'::jsonb,
    supervisor        jsonb NOT NULL DEFAULT '{}'::jsonb,
    diagnostic_log    jsonb NOT NULL DEFAULT '[]'::jsonb,
    recovery_log      jsonb NOT NULL DEFAULT '[]'::jsonb,
    control_log       jsonb NOT NULL DEFAULT '[]'::jsonb,
    plan              jsonb NOT NULL,
    resume_cursor     integer NOT NULL DEFAULT 0,
    resume_commitment text,
    resume_state      bytea,
    resume_state_sha  text,
    comparisons       jsonb NOT NULL DEFAULT '{"compared": 0, "mismatches": []}'::jsonb,
    result            jsonb,
    error             text
);
CREATE INDEX IF NOT EXISTS observation_deep_validations_replay_idx ON observation_deep_validations (replay_id, created_at);
CREATE UNIQUE INDEX IF NOT EXISTS observation_deep_validations_one_active
    ON observation_deep_validations (replay_id) WHERE status IN ('queued','running','paused');
"""

# WP-008-R2: causal temporal substrate (additive). New runs (lifecycle_version 4, engine_format 'observe.stream.v2')
# store the explicit temporal restore state (algotrader.temporal-state.v1) beside the factual state in the same fenced
# checkpoint transaction, the temporal state SHA-256 and output commitments at every committed range, and a concise
# temporal inspection view at the committed checkpoint. Pre-R2 nonterminal streaming runs (lifecycle 3) receive the
# same additive suspension as earlier upgrades: preserved read-only, never reclaimed, converted or replayed.
SCHEMA_V10 = """
ALTER TABLE observation_restore_points ADD COLUMN IF NOT EXISTS temporal_format text;
ALTER TABLE observation_restore_points ADD COLUMN IF NOT EXISTS temporal_blob bytea;
ALTER TABLE observation_restore_points ADD COLUMN IF NOT EXISTS temporal_sha256 text;
ALTER TABLE observation_ranges ADD COLUMN IF NOT EXISTS temporal_sha256 text;
ALTER TABLE observation_ranges ADD COLUMN IF NOT EXISTS temporal_commitment text;
ALTER TABLE observation_ranges ADD COLUMN IF NOT EXISTS aggregate_chain text;
ALTER TABLE observation_ranges ADD COLUMN IF NOT EXISTS dispatch_seq integer;
ALTER TABLE observation_checkpoints ADD COLUMN IF NOT EXISTS temporal_view jsonb;

UPDATE observation_replays
   SET suspended_at = now(),
       suspension = jsonb_build_object(
         'reason', 'pre-R2 nonterminal observation replay (lifecycle v3, streaming engine without temporal state) '
                   || 'suspended at the WP-008-R2 upgrade; preserved read-only, never reclaimed, converted or replayed',
         'historical_status', status,
         'historical_lease_owner', lease_owner,
         'historical_lease_expires_at', lease_expires_at,
         'migration', 10)
 WHERE lifecycle_version = 3 AND status IN ('queued', 'running', 'paused') AND suspended_at IS NULL;
"""

# WP-008-R3: evaluation packs (additive). A durable parent pack job (owned by the corpus worker) coordinates bounded
# acquisitions and the composition of an immutable pack; ``corpus_packs`` is the trusted publication receipt pinning
# the pack manifest and its feed cache. Evaluations may reference a pack; observation replays accept source kind
# 'pack'. Existing chunk bindings, month evaluations and replays are unchanged.
SCHEMA_V11 = """
CREATE TABLE IF NOT EXISTS corpus_pack_jobs (
    job_id             text PRIMARY KEY,
    preset_id          text NOT NULL,
    preset             jsonb NOT NULL,
    preset_sha256      text NOT NULL,
    created_at         timestamptz NOT NULL DEFAULT now(),
    status             text NOT NULL CHECK (status IN ('queued','running','completed','cancelled','failed')),
    cancel_requested   boolean NOT NULL DEFAULT false,
    base_url           text NOT NULL,
    lease_owner        text,
    lease_expires_at   timestamptz,
    heartbeat_at       timestamptz,
    lease_generation   bigint NOT NULL DEFAULT 0,
    attempt            integer NOT NULL DEFAULT 0,
    max_attempts       integer NOT NULL DEFAULT 3,
    interruptions      integer NOT NULL DEFAULT 0,
    attempt_started_at timestamptz,
    recovery_log       jsonb NOT NULL DEFAULT '[]'::jsonb,
    diagnostic_log     jsonb NOT NULL DEFAULT '[]'::jsonb,
    progress           jsonb NOT NULL DEFAULT '{}'::jsonb,
    progress_seq       bigint NOT NULL DEFAULT 0,
    last_progress_at   timestamptz,
    phase_history      jsonb NOT NULL DEFAULT '[]'::jsonb,
    plan               jsonb,
    children           jsonb NOT NULL DEFAULT '[]'::jsonb,
    started_at         timestamptz,
    finished_at        timestamptz,
    outcome            text,
    pack_id            text,
    result             jsonb,
    error              text
);
CREATE INDEX IF NOT EXISTS corpus_pack_jobs_created_idx ON corpus_pack_jobs (created_at);
CREATE UNIQUE INDEX IF NOT EXISTS corpus_pack_jobs_one_active
    ON corpus_pack_jobs (preset_id) WHERE status IN ('queued','running');

CREATE TABLE IF NOT EXISTS corpus_packs (
    pack_id                text PRIMARY KEY,
    manifest_sha256        text NOT NULL,
    preset_id              text NOT NULL,
    preset_sha256          text NOT NULL,
    cache_id               text NOT NULL,
    cache_manifest_sha256  text NOT NULL,
    content_identity       text NOT NULL,
    event_count            integer NOT NULL,
    status                 text NOT NULL,
    created_by_job         text,
    generation             bigint,
    created_at             timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS corpus_packs_preset_idx ON corpus_packs (preset_sha256, created_at);

ALTER TABLE evaluations ADD COLUMN IF NOT EXISTS pack_id text;
ALTER TABLE evaluations ADD COLUMN IF NOT EXISTS preset_id text;
ALTER TABLE observation_replays DROP CONSTRAINT IF EXISTS observation_replays_source_kind_check;
ALTER TABLE observation_replays ADD CONSTRAINT observation_replays_source_kind_check
    CHECK (source_kind IN ('dataset', 'recording', 'pack'));
"""

MIGRATIONS: dict[int, str] = {1: SCHEMA_V1, 2: SCHEMA_V2, 3: SCHEMA_V3, 4: SCHEMA_V4, 5: SCHEMA_V5, 6: SCHEMA_V6,
                              7: SCHEMA_V7, 8: SCHEMA_V8, 9: SCHEMA_V9, 10: SCHEMA_V10, 11: SCHEMA_V11}
SCHEMA_VERSION = max(MIGRATIONS)


def database_url() -> str:
    url = os.environ.get("ALGOTRADER_DATABASE_URL")
    if not url:
        raise RuntimeError("ALGOTRADER_DATABASE_URL is not set")
    return url


def connect(url: str | None = None, **kw) -> psycopg.Connection:
    return psycopg.connect(url or database_url(), row_factory=dict_row, **kw)


@contextmanager
def connection(url: str | None = None, **kw) -> Iterator[psycopg.Connection]:
    conn = connect(url, **kw)
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
