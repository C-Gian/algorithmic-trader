"""Immutable evaluation pack contracts (``algotrader.corpus-pack.v1``, revision 2, PROVISIONAL).

A pack composes verified ``marketdata.v1`` source slices (reused local datasets and/or newly acquired boundary
slices) into ONE canonical feed over the full requested interval (warmup + evaluation + tail) of a registered
preset. Its manifest is deterministic (no machine paths, preparation timestamps or probes in its identity) and is
pinned by a publication receipt in PostgreSQL. Separate from the frozen marketdata/feed/semantic/recorder
contracts, which it reuses unchanged; it carries no adviser rule, call, outcome or trading metric.

PROVISIONAL: any change bumps ``PACK_SCHEMA_REVISION`` with a ``PACK_CHANGELOG`` entry and Director approval.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

PACK_SCHEMA_VERSION = "algotrader.corpus-pack.v1"
PACK_CONTRACT_STATUS = "PROVISIONAL"
PACK_SCHEMA_REVISION = 2
PACK_CHANGELOG: tuple[tuple[int, str, str], ...] = (
    (1, "2026-10-03", "Initial provisional baseline (WP-008-R3): preset/profile/register identities, windows and "
                      "boundary policies, pinned instrument definition, ordered source slices, composed feed "
                      "identities, per-family/window coverage, overlap accounting, capability facts and status."),
    (2, "2026-10-07", "WP-013 (additive, compatible): optional Preset.initialization = "
                      "REGISTERED_EXPLICIT_INITIALIZATION for an explicitly registered unscored initialization window "
                      "(at least the fine warmup, ending at the evaluation start) and the matching optional "
                      "windows.initialization fact. Absent for every earlier preset/pack, whose documents, identities "
                      "and validity are unchanged (their manifests keep schema_revision 1, so a rebuild keeps its pack "
                      "id); the file-level fine warmup is not modified."),
)
COMPOSITION_POLICY = "corpus.compose.slot-dedup-no-merge.v1"
COMPOSITION_POLICY_TEXT = (
    "Overlap identity is (channel, market slot) - for funding the settlement time. Identical normalized semantic "
    "content collapses once (every contributor kept in provenance); conflicting OHLC/volume/status/settlement "
    "payloads fail composition (never first/last wins); an explicit MISSING placeholder plus valid evidence from a "
    "compatible contributor admits the valid evidence once and keeps the gap provenance; rejected evidence versus "
    "valid evidence, or two different quality reasons, fail. The primary SourceRef of a collapsed slot is chosen "
    "deterministically by (source manifest SHA-256, dataset id, artifact, row index). The composed events are "
    "ordered once by the accepted feed.v1 ordering over the full requested interval.")
SLICE_POLICY = "corpus.slice.bound-first-then-longest-covering.v1"
METADATA_POLICY = "PINNED_RETRIEVAL_SNAPSHOT_ASSUMED_FOR_WINDOW"
DEFINITION_FIELDS = ("inst_id", "inst_type", "ct_type", "underlying", "inst_family", "index_id", "base_ccy",
                     "quote_ccy", "ct_val", "ct_val_ccy", "ct_mult", "settle_ccy", "tick_sz", "lot_sz", "min_sz")


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SourceSlice(Record):
    dataset_id: str
    source_manifest_sha256: str
    request_start: datetime  # the source package's own logical request
    request_end: datetime
    start: datetime  # the slice actually used (UTC half-open)
    end: datetime
    cache_id: str  # receipt-pinned per-source canonical feed cache the slice was read from
    cache_manifest_sha256: str
    # (whether a package was downloaded by this or an earlier preparation is operational history, kept in the job's
    # children records - never part of the pack identity)


class InstrumentPin(Record):
    policy: str  # METADATA_POLICY
    definition: dict[str, str]  # DEFINITION_FIELDS of the pinned snapshot (all contributors must agree)
    definition_sha256: str
    snapshot_dataset_id: str
    snapshot_retrieved_at: datetime
    snapshot_raw_sha256: str
    note: str


class WindowCounts(Record):
    family: str
    window: Literal["warmup", "evaluation", "tail"]
    expected_slots: int | None  # bar families: whole minutes of the window; funding: None (no schedule assumed)
    valid: int
    missing: int
    rejected: int
    reasons: dict[str, int]


class OverlapSummary(Record):
    overlapping_slots: int
    identical_collapsed: int  # extra identical copies removed
    gap_replaced_by_valid: int  # MISSING placeholders superseded by valid evidence from another contributor
    conflicts: int  # always 0 in a published pack (a conflict fails composition)
    provenance_file: str | None
    provenance_sha256: str | None


class CapabilityFact(Record):
    capability: str
    status: str
    detail: str


class FeedRef(Record):
    cache_id: str
    cache_manifest_sha256: str
    content_identity: str  # packaging-independent normalized content identity (feed.v1 meaning unchanged)
    ordered_event_hash: str  # provenance-sensitive (includes SourceRef); NOT equal across packagings
    ordering_policy_id: str
    availability_policy_id: str
    event_count: int
    event_counts: dict[str, int]


class PackManifest(Record):
    schema_version: Literal["algotrader.corpus-pack.v1"]
    contract_status: str
    schema_revision: int
    pack_id: str  # "pack-" + SHA-256 prefix of the canonical manifest body without this field
    preset: dict
    preset_sha256: str
    presets_schema: str
    presets_version: int
    method: str
    rules_version: str
    register_sha256: str  # input-requirement identity of the MP-001 register (not an implementation)
    capability_profile: dict[str, str]
    capability_profile_sha256: str
    windows: dict
    boundaries: dict[str, str]
    evidence_classes: dict
    requested_start: datetime
    requested_end: datetime
    tail_end: datetime  # coverage end of the outcome tail
    clock_end: datetime  # engine finite clock end = full coverage end + declared modeled closure allowance
    instrument: InstrumentPin
    sources: tuple[SourceSlice, ...]
    slice_policy: str
    composition_policy: str
    feed: FeedRef
    coverage: tuple[WindowCounts, ...]
    overlap: OverlapSummary
    capabilities: tuple[CapabilityFact, ...]
    input_readiness_preview: dict
    status: Literal["READY", "READY_WITH_LIMITATIONS"]
    limitations: tuple[str, ...]
    storage: dict
    labels: tuple[str, ...]


PUBLIC_CONTRACTS: tuple[type[Record], ...] = (SourceSlice, InstrumentPin, WindowCounts, OverlapSummary,
                                              CapabilityFact, FeedRef, PackManifest)
