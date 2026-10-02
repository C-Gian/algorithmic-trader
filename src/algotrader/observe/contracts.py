"""Observation-replay operational contracts (``algotrader.observe.v1``, PROVISIONAL).

A real-market observation replay consumes accepted evidence (a verified
``algotrader.marketdata.v1`` dataset or a finalized ``algotrader.recorder.v1``
session) as ``algotrader.feed.v1`` deliveries and advances the accepted pure
observable-state reducer, one causal feed delivery per step.

This namespace describes the *operation* of such a replay (source identity and
verification, feed identity, policies, committed deliveries, manifest and
validation). It is deliberately separate from:

* ``algotrader.semantic.v1`` - the frozen synthetic DEMO trader/account/order
  shell (no MarketView, decision, risk, order, fill or account records here);
* ``algotrader.feed.v1`` - causal evidence semantics (reused, never extended
  with job state).

It carries no interpretation, prediction, recommendation, sizing or P&L.

PROVISIONAL during M3: a contract change must bump ``OBSERVE_SCHEMA_REVISION``,
add an ``OBSERVE_CHANGELOG`` entry and be Director-approved.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from ..feed.contracts import AvailabilityPolicy, ChannelChange, ChannelCoverage, EventKind, Family, FreshnessPolicy

OBSERVE_SCHEMA_VERSION = "algotrader.observe.v1"
OBSERVE_CONTRACT_STATUS = "PROVISIONAL"
OBSERVE_SCHEMA_REVISION = 2
OBSERVE_CHANGELOG: tuple[tuple[int, str, str], ...] = (
    (1, "2026-09-30", "Initial provisional baseline (WP-007): observation-replay config, source verification, "
                      "feed identity, committed delivery records, manifest and validation."),
    (2, "2026-10-02", "WP-008-R1A operational lifecycle (Director-approved limited revision): durable "
                      "ObservationLaunch envelope persisted before worker-owned source preparation; manifest adds "
                      "optional fencing generation, generation-scoped immutable artifact directory, measured phase "
                      "timings and operational counters; validation adds optional outcome "
                      "(passed/failed/incomplete), validator id/version and scope. All additions are optional, so "
                      "revision-1 manifests remain readable unchanged. Replay semantics, order, digests and "
                      "validation mathematics are unchanged."),
)
VALIDATOR_ID = "observe.terminal-revalidation"
VALIDATOR_VERSION = "1"
VALIDATOR_SCOPE = ("Full pure re-execution of the committed delivery prefix from the immutable source (per-delivery "
                   "digests, order, duplicates, no-future-knowledge) plus, for completed runs, the pure cutoff "
                   "snapshot. Same reducer code as the replay: a re-derivation, not an independent implementation.")
CLOCK_POLICY = (
    "Event-driven replay clock: one step applies exactly one causal feed delivery, in the accepted feed.v1 total "
    "order; replay/information time becomes that delivery's available_time. Pacing (events/s) is operational only "
    "and never changes order, state or digests."
)
LABELS = ("REAL_MARKET_EVIDENCE", "OBSERVATION_ONLY", "NO_INTERPRETATION", "NO_TRADING")


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SourceKind(StrEnum):
    DATASET = "dataset"  # verified historical marketdata.v1 dataset (MODELED availability)
    RECORDING = "recording"  # finalized recorder.v1 session (RECORDED first-completion receipt)


class ReplayStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


TERMINAL_STATUSES = frozenset({ReplayStatus.COMPLETED, ReplayStatus.CANCELLED, ReplayStatus.FAILED})


class ReplayRuntimeState(StrEnum):
    """Compact UI summary (not a contract field). Status, phase, health and assurance stay separate."""

    QUEUED = "queued"
    PREPARING = "preparing"  # worker-owned source preparation / initialization before replay
    RUNNING = "running"
    FINISHING = "finishing"  # replay cursor complete; finalizing / validating / publishing (NOT completed)
    PAUSING = "pausing"
    PAUSED = "paused"
    STEPPING = "stepping"
    RECOVERING = "recovering"  # only while a new fenced attempt is actually restoring
    UNRESPONSIVE = "unresponsive"  # lease expired / compute lost: awaiting recovery (not yet restoring)
    SUSPENDED = "suspended"  # pre-upgrade run preserved read-only
    CANCEL_REQUESTED = "cancel_requested"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class SourceVerification(Record):
    verified: bool
    method: str  # what was checked
    problems: tuple[str, ...]
    checked_at: datetime


class SourceSummary(Record):
    kind: SourceKind
    source_id: str  # dataset_id or recorder session_id (the immutable evidence package)
    source_schema: str  # marketdata.v1 / recorder.v1
    inst_id: str
    index_id: str
    source_status: str  # dataset quality status, or recorder session status (clean / partial)
    coverage: tuple[ChannelCoverage, ...]
    warnings: tuple[str, ...]  # e.g. PARTIAL session outages
    exclusions: tuple[str, ...]  # recorded-bridge exclusions (evidence not bridged, with reason)
    notes: tuple[str, ...]  # e.g. live funding not bridged as settlements


class FeedIdentity(Record):
    schema_version: str
    contract_status: str
    schema_revision: int
    content_identity: str
    ordered_event_hash: str
    ordering_policy_id: str
    event_count: int
    event_counts: dict[str, int]


class ObservationReplayConfig(Record):
    """Everything a replay depends on; fixed at creation and re-checked by every worker claim."""

    schema_version: str
    replay_id: str
    source: SourceSummary
    verification: SourceVerification
    feed: FeedIdentity
    availability_policy: AvailabilityPolicy
    availability_label: str  # human statement of MODELED vs RECORDED meaning
    freshness_policy: FreshnessPolicy  # inspection/development policy, not a research threshold
    clock_policy: str
    code_version: str | None
    labels: tuple[str, ...]


class DeliveryRecord(Record):
    """One committed causal feed delivery (the replay journal)."""

    seq: int  # 0-based position in the feed's total order == cursor before the delivery
    event_id: str
    channel_id: str
    family: Family
    kind: EventKind
    event_time: datetime
    event_end_time: datetime | None
    available_time: datetime  # replay/information time after this delivery
    quality_reason: str | None
    snapshot_id: str
    snapshot_digest: str  # content digest of the observable snapshot after this delivery
    changes: tuple[ChannelChange, ...]  # channels whose condition/freshness/latest value changed


class ValidationCheck(Record):
    name: str
    passed: bool
    detail: str


class ValidationOutcome(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    INCOMPLETE = "incomplete"  # validation stopped (e.g. cancelled) before every check ran: not a PASS


class ReplayValidation(Record):
    passed: bool
    checks: tuple[ValidationCheck, ...]
    # revision 2 (optional; absent in revision-1 manifests)
    outcome: ValidationOutcome | None = None
    validator: str | None = None
    validator_version: str | None = None
    scope: str | None = None


class ObservationLaunch(Record):
    """Revision 2: the lightweight launch envelope persisted (<=1 s, no hashing) before any preparation.

    Source/config/feed identity and the total event count are PENDING until the worker-owned preparation
    has verified the source and built the feed; nothing here claims verification.
    """

    schema_version: str
    replay_id: str
    source_kind: SourceKind
    source_id: str
    requested_at: datetime
    speed: float
    paused: bool
    evaluation_id: str | None
    expected_manifest_sha256: str | None  # corpus binding to re-check during preparation (evaluations)
    code_version: str | None


class ArtifactFile(Record):
    name: str
    sha256: str
    bytes: int
    lines: int | None


class ObservationReplayManifest(Record):
    schema_version: str
    contract_status: str
    schema_revision: int
    replay_id: str
    status: ReplayStatus
    labels: tuple[str, ...]
    config: ObservationReplayConfig
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime
    applied_events: int
    total_events: int
    final_as_of: datetime
    final_snapshot_id: str
    final_content_digest: str
    attempts: int
    recovery_log: list[dict]
    control_log: list[dict]
    error: str | None
    validation: ReplayValidation
    source_reference: str  # where the immutable evidence lives (not duplicated here)
    artifacts: tuple[ArtifactFile, ...]
    # revision 2 (optional; absent in revision-1 manifests)
    lease_generation: int | None = None  # fencing generation that published this manifest
    artifact_dir: str | None = None  # generation-scoped immutable directory (relative to the replay directory)
    phase_timings: list[dict] | None = None  # measured operational phase spans up to publication
    operational_metrics: dict | None = None  # cheap bounded counters (events, snapshots, transactions, bytes)


PUBLIC_CONTRACTS: tuple[type[Record], ...] = (
    ObservationLaunch,
    SourceVerification,
    SourceSummary,
    FeedIdentity,
    ObservationReplayConfig,
    DeliveryRecord,
    ValidationCheck,
    ReplayValidation,
    ArtifactFile,
    ObservationReplayManifest,
)
