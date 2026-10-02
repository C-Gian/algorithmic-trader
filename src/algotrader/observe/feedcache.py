"""Immutable, reusable normalized feed cache (WP-008-R1B; internal format ``algotrader.observe-feedcache.v1``).

A cache holds the complete ``feed.v1`` event stream of ONE verified source in canonical total order,
split into bounded gzip partitions, plus the exact canonical feed identities:

* ``cache_id`` = hash of the cache key: source kind/id, the SHA-256 of the source's own manifest (content
  identity of the immutable package), adapter/ordering/availability/cache-format versions. Path or mtime
  never identify a cache.
* ``manifest.json``: the ``FeedManifest`` (content identity, canonical ordered-event hash, counts, coverage)
  exactly as ``feed.adapter`` defines them, every partition's SHA-256/size/first-last order key, the rolling
  input commitment before each partition and after the last event, and source facts needed by the run
  config (quality, exclusions, notes).
* ``part-NNNNN.jsonl.gz``: one canonical ``FeedEvent`` JSON line per event (the exact bytes hashed by
  ``ordered_event_hash``), ``PARTITION_EVENTS`` per partition.

Cold build: the caller verifies the source ONCE and passes the event stream in; events go through two
bounded external sorts (canonical order; content order for the content identity / ambiguous-slot check);
nothing materializes the whole source. The directory is written under ``.tmp-*`` and published with one
rename; a crashed build leaves only an ignored temporary directory.

Trust boundary: a run pins ``cache_id`` and the manifest SHA-256. Every partition is SHA-256-verified when
it is read (before any of its events are applied); a mismatch quarantines the cache and fails the run.
Path/mtime alone are never trusted.

The rolling consumed-prefix commitment (``observe.prefix-commitment.v1``) is a separate integrity chain:
H0 = SHA-256("algotrader.observe.prefix.v1" NUL cache_id); Hn = SHA-256(Hn-1 || line_n). It never replaces
the canonical ordered-event hash or a state/snapshot digest.
"""

from __future__ import annotations

import gzip
import hashlib
import heapq
import json
import os
import shutil
import tempfile
import uuid
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..feed.adapter import CONTENT_IDENTITY_PREFIX, Feed, content_record
from ..feed.contracts import (
    FEED_CONTRACT_STATUS,
    FEED_SCHEMA_REVISION,
    FEED_SCHEMA_VERSION,
    ORDERING_POLICY_ID,
    AvailabilityPolicy,
    ChannelCoverage,
    EventKind,
    FeedEvent,
    FeedManifest,
)
from ..feed.ordering import FeedError, canonical
from ..ops import OperationCancelled  # noqa: F401 - re-exported for callers' hooks

CACHE_FORMAT = "algotrader.observe-feedcache.v1"
COMMITMENT_FORMAT = "observe.prefix-commitment.v1"
PARTITION_EVENTS = 5000
SORT_BLOCK = 20000  # records held in memory per external-sort run
FAN_IN = 16  # spill runs open at once during a merge pass (bounded descriptors / buffers)
EXCLUSIONS_IN_CONFIG = 1000  # recorded exclusions copied into a run config; the full list stays in the cache
ADAPTER_VERSIONS = {"dataset": "feed.adapter.stream-dataset.v1", "recording": "recorder.feed_bridge.stream.v1"}

Hook = Callable[[str, int, int | None, str], None]


class CacheError(Exception):
    """The cache is missing, incompatible or corrupt; it must not be consumed."""


def _no_hook(stage: str, done: int, total: int | None, unit: str) -> None:  # noqa: ARG001
    return None


def cache_root(data_root: Path) -> Path:
    return data_root / "feedcache"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def cache_key(source_kind: str, source_id: str, source_manifest_sha256: str, availability: AvailabilityPolicy) -> dict:
    return {
        "format": CACHE_FORMAT, "source_kind": source_kind, "source_id": source_id,
        "source_manifest_sha256": source_manifest_sha256, "adapter": ADAPTER_VERSIONS[source_kind],
        "ordering_policy_id": ORDERING_POLICY_ID, "availability_policy_id": availability.policy_id,
        "feed_schema": f"{FEED_SCHEMA_VERSION}#r{FEED_SCHEMA_REVISION}", "partition_events": PARTITION_EVENTS,
    }


def cache_id_for(key: dict) -> str:
    return "fc-" + hashlib.sha256(canonical(key)).hexdigest()[:40]


def initial_commitment(cache_id: str) -> bytes:
    return hashlib.sha256(b"algotrader.observe.prefix.v1\x00" + cache_id.encode()).digest()


def extend_commitment(h: bytes, line: bytes) -> bytes:
    return hashlib.sha256(h + line).digest()


# ---------------------------------------------------------------------------
# Sort keys
# ---------------------------------------------------------------------------


def _ts(t: datetime) -> str:
    if t.utcoffset() is None or t.utcoffset().total_seconds() != 0:
        raise FeedError(f"non-UTC time {t!r} cannot be ordered by the streaming cache")
    return t.isoformat(timespec="microseconds")


def order_sort_key(e: FeedEvent) -> bytes:
    """Byte key whose order equals ``feed.ordering.sort_key`` (NUL-separated components)."""
    o = e.order
    return "\x00".join((_ts(o.available_time), f"{o.family_rank:03d}", o.series_id, _ts(o.event_time),
                        f"{o.kind_rank:03d}", o.event_id)).encode()


def content_sort_key(rec: dict) -> bytes:
    """Byte key whose order equals the content identity's sort (channel, iso event time, kind)."""
    return "\x00".join((rec["channel"], rec["event_time"], rec["kind"])).encode()


# ---------------------------------------------------------------------------
# Bounded external sort
# ---------------------------------------------------------------------------


class ExternalSorter:
    """Sort (key, line) records with at most ``block`` records in memory and at most ``fan_in`` spill runs
    open at once: runs are merged in bounded multi-pass groups until one final ``fan_in``-way merge remains.
    """

    SEP = b"\x1f"

    def __init__(self, workdir: Path, name: str, block: int | None = None, fan_in: int | None = None,
                 hook: Hook | None = None) -> None:
        self.workdir, self.name = workdir, name
        self.block = block or SORT_BLOCK
        self.fan_in = max(2, fan_in or FAN_IN)
        self.hook = hook or _no_hook
        self.buf: list[tuple[bytes, bytes]] = []
        self.runs: list[Path] = []
        self.count = 0
        self.stats = {"runs_created": 0, "merge_passes": 0, "max_open_runs": 0, "max_buffer_records": 0}
        self._seq = 0
        self._open: list = []  # run readers currently open (closed on completion, error or cancellation)

    def close(self) -> None:
        for st in self._open:
            st.close()
        self._open = []

    def add(self, key: bytes, line: bytes) -> None:
        self.buf.append((key, line))
        self.count += 1
        if len(self.buf) >= self.block:
            self._spill()

    def _new_run(self) -> Path:
        path = self.workdir / f"{self.name}-run{self._seq:06d}.bin"
        self._seq += 1
        self.stats["runs_created"] += 1
        return path

    def _spill(self) -> None:
        self.stats["max_buffer_records"] = max(self.stats["max_buffer_records"], len(self.buf))
        self.buf.sort(key=lambda r: r[0])
        path = self._new_run()
        with path.open("wb") as f:
            for k, line in self.buf:
                f.write(k + self.SEP + line + b"\n")
        self.runs.append(path)
        self.buf = []

    @staticmethod
    def _read(path: Path) -> Iterator[tuple[bytes, bytes]]:
        with path.open("rb") as f:
            for raw in f:
                k, _, line = raw.rstrip(b"\n").partition(ExternalSorter.SEP)
                yield k, line

    def _merge_group(self, group: list[Path]) -> Path:
        self.stats["max_open_runs"] = max(self.stats["max_open_runs"], len(group))
        out = self._new_run()
        streams = [self._read(p) for p in group]
        self._open = streams
        try:
            with out.open("wb") as f:
                for i, (k, line) in enumerate(heapq.merge(*streams, key=lambda r: r[0])):
                    f.write(k + self.SEP + line + b"\n")
                    if i % 5000 == 0:
                        self.hook(f"merge {self.name} sort runs", i, None, "records")  # no-yield work
        finally:
            self.close()
        for p in group:
            p.unlink()
        return out

    def merged(self) -> Iterator[tuple[bytes, bytes]]:
        if self.buf:
            self._spill()
        runs = list(self.runs)
        while len(runs) > self.fan_in:  # bounded multi-pass merge
            self.stats["merge_passes"] += 1
            runs = [self._merge_group(runs[i:i + self.fan_in]) for i in range(0, len(runs), self.fan_in)]
        self.runs = runs
        self.stats["max_open_runs"] = max(self.stats["max_open_runs"], len(runs))
        self._open = [self._read(p) for p in runs]
        return heapq.merge(*self._open, key=lambda r: r[0])


def _fsync_file(path: Path) -> None:
    with path.open("r+b") as f:
        os.fsync(f.fileno())


def _fsync_dir(path: Path) -> bool:
    """fsync a directory entry where the platform supports it (POSIX); False where it cannot be expressed."""
    if os.name == "nt":
        return False
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    return True


def durability_note(dir_synced: bool) -> str:
    return ("partition/manifest files fsynced, build directory and parent directory fsynced around the rename"
            if dir_synced else
            "partition/manifest files fsynced before the rename; directory fsync is not available on this "
            "platform (rename is journaled metadata, not proven power-loss durable)")


def cleanup_stale(data_root: Path, max_age_s: float = 86400.0) -> int:
    """Remove temporary build/snapshot directories left by crashed preparations (older than ``max_age_s``)."""
    import time as _t

    root = cache_root(data_root)
    n = 0
    if not root.is_dir():
        return 0
    for p in root.iterdir():
        if p.is_dir() and (p.name.startswith(".tmp-") or p.name.startswith(".snap-")):
            try:
                if _t.time() - p.stat().st_mtime > max_age_s:
                    shutil.rmtree(p, ignore_errors=True)
                    n += 1
            except OSError:
                pass
    return n


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FeedCache:
    cache_id: str
    path: Path
    manifest: dict
    manifest_sha256: str

    @property
    def feed_manifest(self) -> FeedManifest:
        return FeedManifest.model_validate(self.manifest["feed_manifest"])

    @property
    def feed_meta(self) -> Feed:
        """A ``Feed`` carrying only the manifest: what initial_state/snapshot need (never the event list)."""
        return Feed(self.feed_manifest, ())

    @property
    def event_count(self) -> int:
        return int(self.manifest["feed_manifest"]["event_count"])

    @property
    def partitions(self) -> list[dict]:
        return self.manifest["partitions"]


def build_cache(data_root: Path, key: dict, events: Iterable[FeedEvent], coverage_fn: Callable[[], tuple],
                policy: AvailabilityPolicy, dataset_ids: tuple[str, ...], inst_fn: Callable[[], tuple[str, str, dict]],
                source_facts_fn: Callable[[], dict], hook: Hook | None = None,
                counters: dict | None = None, exclusions: Callable[[], Iterable[str]] | None = None,
                fault: Callable[[str], None] | None = None) -> FeedCache:
    """Stream ``events`` (any order) into a durably published immutable cache.

    ``coverage_fn``/``inst_fn``/``source_facts_fn``/``exclusions`` are called after the stream is exhausted.
    The manifest is deterministic (no timestamps), so rebuilding the same source with the same versions
    reproduces byte-identical metadata - which lets a trusted receipt (stored outside the cache) pin it.
    Files are fsynced before the publication rename. ``fault(stage)`` is a test-only crash hook.
    """
    hook = hook or _no_hook
    fault = fault or (lambda _s: None)
    counters = counters if counters is not None else {}
    root = cache_root(data_root)
    root.mkdir(parents=True, exist_ok=True)
    cid = cache_id_for(key)
    final = root / cid
    tmp = root / f".tmp-{cid}-{uuid.uuid4().hex[:8]}"
    tmp.mkdir()
    sortdir = Path(tempfile.mkdtemp(prefix="sort-", dir=tmp))
    try:
        order = ExternalSorter(sortdir, "order", hook=hook)
        content = ExternalSorter(sortdir, "content", hook=hook)
        counts: dict[str, int] = {}
        seen_channels: set[str] = set()
        usable = False
        n = 0
        for e in events:
            if n % 1000 == 0:
                hook("normalize and sort events", n, None, "events")
            line = canonical(e.model_dump(mode="json"))
            order.add(order_sort_key(e), line)
            rec = content_record(e)
            content.add(content_sort_key(rec), canonical(rec))
            k = f"{e.channel.family.value}/{e.kind.value}"
            counts[k] = counts.get(k, 0) + 1
            seen_channels.add(e.channel.channel_id)
            usable = usable or e.kind in (EventKind.BAR_OBSERVATION, EventKind.FUNDING_OBSERVATION)
            n += 1
        hook("normalize and sort events", n, n, "events")
        counters["cache_build_events"] = n
        coverage: tuple[ChannelCoverage, ...] = coverage_fn()
        inst_id, index_id, instrument = inst_fn()
        covered = {c.channel.channel_id for c in coverage}
        missing = seen_channels - covered
        if missing:
            raise FeedError(f"events for channels without declared coverage: {sorted(missing)}")
        # content identity (streamed exactly as feed.adapter.content_identity serializes it)
        ch = hashlib.sha256()
        cov = sorted((c.channel.channel_id, c.covered_from.isoformat().replace("+00:00", "Z"),
                      c.covered_until.isoformat().replace("+00:00", "Z"),
                      c.expected_cadence.total_seconds() if c.expected_cadence else None) for c in coverage)
        ch.update(b'{"coverage":' + canonical(cov) + b',"events":[')
        prev_slot = None
        for i, (k, line) in enumerate(content.merged()):
            if i % 5000 == 0:
                hook("content identity", i, n, "events")
            slot = k.rsplit(b"\x00", 1)[0]  # (channel, event_time)
            if slot == prev_slot:
                raise FeedError(f"ambiguous slot {slot.decode(errors='replace')!r}: two events for one channel slot")
            prev_slot = slot
            ch.update((b"," if i else b"") + line)
        ch.update(b'],"instrument":' + canonical(instrument) + b',"schema":' + canonical(FEED_SCHEMA_VERSION) + b"}")
        content_identity = CONTENT_IDENTITY_PREFIX + ch.hexdigest()
        hook("content identity", n, n, "events")
        # canonical order -> partitions, ordered-event hash, rolling commitment
        oh = hashlib.sha256()
        commit = initial_commitment(cid)
        partitions: list[dict] = []
        buf: list[bytes] = []
        first_key = last_key = None
        written = 0

        def flush() -> None:
            nonlocal buf, first_key
            idx = len(partitions)
            name = f"part-{idx:05d}.jsonl.gz"
            data = b"".join(x + b"\n" for x in buf)
            blob = gzip.compress(data, compresslevel=1, mtime=0)
            with (tmp / name).open("wb") as pf:
                pf.write(blob)
                pf.flush()
                os.fsync(pf.fileno())
            partitions.append({"index": idx, "file": name, "first_seq": written - len(buf), "count": len(buf),
                               "sha256": hashlib.sha256(blob).hexdigest(), "bytes": len(blob),
                               "first_order": first_key, "last_order": last_key,
                               "commitment_before": part_commit_before})
            buf = []
            first_key = None

        part_commit_before = commit.hex()
        for k, line in order.merged():
            if written % 1000 == 0:
                hook("write ordered partitions", written, n, "events")
            if not buf:
                part_commit_before = commit.hex()
                first_key = k.decode()
            buf.append(line)
            last_key = k.decode()
            oh.update(line + b"\n")
            commit = extend_commitment(commit, line)
            written += 1
            if len(buf) >= PARTITION_EVENTS:
                flush()
        if buf:
            flush()
        order.close()
        content.close()
        hook("write ordered partitions", written, n, "events")
        feed_manifest = FeedManifest(
            schema_version=FEED_SCHEMA_VERSION, contract_status=FEED_CONTRACT_STATUS,
            schema_revision=FEED_SCHEMA_REVISION, dataset_ids=dataset_ids, content_identity=content_identity,
            inst_id=inst_id, index_id=index_id, ordering_policy_id=ORDERING_POLICY_ID, availability_policy=policy,
            coverage=coverage, event_count=n, event_counts=dict(sorted(counts.items())),
            ordered_event_hash=oh.hexdigest(),
        )
        counters["sort"] = {"order": order.stats, "content": content.stats, "block": order.block,
                            "fan_in": order.fan_in}
        counters["sort_spill_runs"] = order.stats["runs_created"] + content.stats["runs_created"]
        shutil.rmtree(sortdir, ignore_errors=True)
        facts = dict(source_facts_fn())
        n_excl, eh = 0, hashlib.sha256()
        with (tmp / "exclusions.jsonl").open("wb") as ef:
            for text in (exclusions() if exclusions else ()):
                line = canonical(text) + b"\n"
                ef.write(line)
                eh.update(line)
                n_excl += 1
            ef.flush()
            os.fsync(ef.fileno())
        facts["exclusions_count"] = n_excl
        facts["exclusions_sha256"] = eh.hexdigest()
        manifest = {
            "format": CACHE_FORMAT, "cache_id": cid, "key": key, "commitment_format": COMMITMENT_FORMAT,
            "feed_manifest": json.loads(feed_manifest.model_dump_json()), "usable": usable,
            "partitions": partitions, "final_commitment": commit.hex(), "partition_events": PARTITION_EVENTS,
            "source_facts": facts,
        }
        mbytes = canonical(manifest)
        with (tmp / "manifest.json").open("wb") as mf:
            mf.write(mbytes)
            mf.flush()
            os.fsync(mf.fileno())
        dir_synced = _fsync_dir(tmp)
        fault("before_publish_rename")
        try:
            os.replace(tmp, final)  # one-step publication of the fsynced immutable cache directory
            if dir_synced:
                _fsync_dir(root)
        except OSError:
            if not (final / "manifest.json").is_file():
                raise
            # a concurrent builder published first: identical deterministic bytes are the same cache
            if (final / "manifest.json").read_bytes() != mbytes:
                raise CacheError(f"feed cache {cid}: a concurrently published cache differs from this verified "
                                 "build; refusing to use either without a trusted receipt") from None
            shutil.rmtree(tmp, ignore_errors=True)
        counters["durability"] = durability_note(dir_synced)
        fault("after_publish_rename")
        return open_cache(data_root, cid, key, expected_manifest_sha256=hashlib.sha256(mbytes).hexdigest())
    except BaseException:
        # release every handle first (event generator -> its sqlite indexes / spill files; sort run readers)
        close = getattr(events, "close", None)
        if close is not None:
            close()
        for srt in (locals().get("order"), locals().get("content")):
            if srt is not None:
                srt.close()
        shutil.rmtree(tmp, ignore_errors=True)
        raise


def open_cache(data_root: Path, cid: str, key: dict | None = None, expected_manifest_sha256: str | None = None,
               check_files: bool = True) -> FeedCache:
    """Open and check a published cache (manifest format/key/pinned hash; partition presence and sizes).

    Partition contents are SHA-256-verified when read; this cheap open check never trusts path/mtime alone.
    """
    path = cache_root(data_root) / cid
    mf = path / "manifest.json"
    if not mf.is_file():
        raise CacheError(f"feed cache {cid} is not present")
    raw = mf.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    if expected_manifest_sha256 is not None and sha != expected_manifest_sha256:
        raise CacheError(f"feed cache {cid} manifest changed (sha256 {sha[:16]} != pinned "
                         f"{expected_manifest_sha256[:16]})")
    try:
        manifest = json.loads(raw)
    except ValueError as exc:
        raise CacheError(f"feed cache {cid} manifest unreadable: {exc}") from None
    if manifest.get("format") != CACHE_FORMAT:
        raise CacheError(f"feed cache {cid} has incompatible format {manifest.get('format')!r}")
    if manifest.get("cache_id") != cid or cache_id_for(manifest.get("key", {})) != cid:
        raise CacheError(f"feed cache {cid} manifest does not match its identity")
    if key is not None and manifest["key"] != key:
        raise CacheError(f"feed cache {cid} key does not match the requested source/versions")
    if check_files:
        total = 0
        for p in manifest["partitions"]:
            f = path / p["file"]
            if not f.is_file() or f.stat().st_size != p["bytes"]:
                raise CacheError(f"feed cache {cid}: partition {p['file']} missing or wrong size")
            total += p["count"]
        if total != manifest["feed_manifest"]["event_count"]:
            raise CacheError(f"feed cache {cid}: partitions hold {total} events, manifest says "
                             f"{manifest['feed_manifest']['event_count']}")
    return FeedCache(cid, path, manifest, sha)


def quarantine(cache: FeedCache, reason: str) -> Path | None:
    """Move a corrupt cache aside so the next preparation rebuilds it (never deleted silently)."""
    return quarantine_dir(cache.path, cache.cache_id, reason)


def quarantine_dir(path: Path, cid: str, reason: str) -> Path | None:
    dest = path.parent / f".invalid-{cid}-{uuid.uuid4().hex[:6]}"
    try:
        os.replace(path, dest)
        (dest / "QUARANTINED.txt").write_text(reason + "\n", encoding="utf-8")
        return dest
    except OSError:
        return None


# ---------------------------------------------------------------------------
# Verified reading
# ---------------------------------------------------------------------------


class CacheReader:
    """Reads canonical event lines by position; every partition is SHA-256-verified before use."""

    def __init__(self, cache: FeedCache, counters: dict | None = None) -> None:
        self.cache = cache
        self.counters = counters if counters is not None else {}
        self._last: tuple[int, list[bytes]] | None = None  # one decoded partition (bounded)

    def partition_lines(self, idx: int) -> list[bytes]:
        if self._last is not None and self._last[0] == idx:
            return self._last[1]
        p = self.cache.partitions[idx]
        blob = (self.cache.path / p["file"]).read_bytes()
        if hashlib.sha256(blob).hexdigest() != p["sha256"]:
            raise CacheError(f"feed cache {self.cache.cache_id}: partition {p['file']} content does not match its "
                             "pinned SHA-256 (corrupt or altered); nothing from it was applied")
        lines = gzip.decompress(blob).split(b"\n")[:-1]
        if len(lines) != p["count"]:
            raise CacheError(f"feed cache {self.cache.cache_id}: partition {p['file']} has {len(lines)} lines, "
                             f"expected {p['count']}")
        self.counters["cache_bytes_read"] = self.counters.get("cache_bytes_read", 0) + len(blob)
        self.counters["cache_partitions_read"] = self.counters.get("cache_partitions_read", 0) + 1
        self._last = (idx, lines)
        return lines

    def iter_from(self, position: int) -> Iterator[tuple[int, bytes]]:
        """(seq, canonical line) from ``position`` to the end of the feed (indexed partition seek)."""
        if position >= self.cache.event_count:
            return
        idx = position // self.cache.manifest["partition_events"]
        for i in range(idx, len(self.cache.partitions)):
            p = self.cache.partitions[i]
            lines = self.partition_lines(i)
            for j in range(max(position - p["first_seq"], 0), p["count"]):
                yield p["first_seq"] + j, lines[j]

    def lines(self, lo: int, hi: int) -> list[tuple[int, bytes]]:
        """Bounded range read [lo, hi)."""
        out = []
        for seq, line in self.iter_from(lo):
            if seq >= hi:
                break
            out.append((seq, line))
        return out

    def commitment_at(self, position: int) -> bytes:
        """Rolling commitment after ``position`` events, from the nearest partition boundary (bounded)."""
        if position == 0:
            return initial_commitment(self.cache.cache_id)
        if position == self.cache.event_count:
            return bytes.fromhex(self.cache.manifest["final_commitment"])
        idx = position // self.cache.manifest["partition_events"]
        p = self.cache.partitions[idx]
        h = bytes.fromhex(p["commitment_before"])
        for _seq, line in self.lines(p["first_seq"], position):
            h = extend_commitment(h, line)
        return h


def decode(line: bytes) -> FeedEvent:
    return FeedEvent.model_validate_json(line)


def iter_exclusions(cache: FeedCache) -> Iterator[str]:
    """The recorded exclusions: the file is hash-checked against the pinned manifest BEFORE any line is used."""
    p = cache.path / "exclusions.jsonl"
    if sha256_file(p) != cache.manifest["source_facts"].get("exclusions_sha256"):
        raise CacheError(f"feed cache {cache.cache_id}: exclusions file does not match the pinned manifest")
    with p.open("rb") as f:
        for line in f:
            yield json.loads(line)


def describe(cache: FeedCache) -> dict[str, Any]:
    return {"cache_id": cache.cache_id, "format": CACHE_FORMAT, "manifest_sha256": cache.manifest_sha256,
            "partitions": len(cache.partitions), "partition_events": cache.manifest["partition_events"],
            "event_count": cache.event_count, "bytes_on_disk": sum(p["bytes"] for p in cache.partitions),
            "commitment_format": COMMITMENT_FORMAT}
