"""Append-only, immutable recording-session storage.

Layout ``<data_root>/recordings/<session_id>/``::

    config.json               SessionConfig (written once at start)
    ACTIVE                    marker while a recorder process owns the session
    journal/raw-000001.jsonl  JournalRecord lines (raw source messages + receipt timing), segmented
    lifecycle.jsonl           LifecycleEvent lines (connections, subscriptions, errors, stops)
    clock.jsonl               ClockObservation lines
    bars_index.jsonl          (at finalize) first completed receipt per bar
    report.json               (at finalize) SessionReport
    manifest.json             (at finalize, last) SessionManifest with sha256 of every file

Durability policy: every line is written and flushed to the OS immediately (a
recorder *process* crash loses nothing already received); files are fsynced at
least every ``fsync_interval`` (an OS crash/power loss can drop at most that
interval). A crashed session is never resumed: recovery truncates only a torn
final line, logs it, and finalizes the session as PARTIAL. Records are never
rewritten, so recovery cannot duplicate a logical receipt. A finalized session
(manifest present) is never modified.
"""

from __future__ import annotations

import hashlib
import json
import os
import socket
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import IO, Any, Protocol

from .contracts import (
    CLOCK_SOURCE,
    RECEIPT_POINT,
    RECORDER_CONTRACT_STATUS,
    RECORDER_SCHEMA_REVISION,
    RECORDER_SCHEMA_VERSION,
    ClockObservation,
    FileRef,
    JournalRecord,
    LifecycleEvent,
    SessionConfig,
    SessionManifest,
    SessionReport,
    SessionStatus,
)

LABELS = ("PUBLIC_MARKET_RECORDING", "NO_TRADING", "CLIENT_RECEIPT_TIME_NOT_PUBLICATION_TIME")


class RecordingError(Exception):
    pass


class Clock(Protocol):
    def time_ns(self) -> int: ...
    def monotonic_ns(self) -> int: ...


def recordings_dir(root: Path) -> Path:
    return root / "recordings"


def ns_to_dt(ns: int) -> datetime:
    return datetime.fromtimestamp(ns // 1_000_000_000, tz=UTC).replace(microsecond=(ns // 1000) % 1_000_000)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> tuple[str, int, int]:
    h, size, lines = hashlib.sha256(), 0, 0
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
            size += len(chunk)
            lines += chunk.count(b"\n")
    return h.hexdigest(), size, lines


class SessionWriter:
    """Single-writer append-only journal for one recording session."""

    def __init__(self, root: Path, config: SessionConfig, clock: Clock) -> None:
        from .okx_live import validate_endpoints  # local: okx_live imports this module

        validate_endpoints(config.endpoints)  # no session artifact is created for a non-official OKX source
        self.dir = recordings_dir(root) / config.session_id
        if self.dir.exists():
            raise RecordingError(f"session {config.session_id} already exists; sessions are never reopened")
        (self.dir / "journal").mkdir(parents=True)
        self.config = config
        self.clock = clock
        (self.dir / "config.json").write_text(config.model_dump_json(indent=2), encoding="utf-8")
        (self.dir / "ACTIVE").write_text(
            json.dumps({"host": socket.gethostname(), "pid": os.getpid(), "started_utc_ns": clock.time_ns()}),
            encoding="utf-8",
        )
        self.seq = 0
        self.lifecycle_seq = 0
        self.segment = 0
        self._journal: IO[str] | None = None
        self._lifecycle = (self.dir / "lifecycle.jsonl").open("a", encoding="utf-8", newline="\n")
        self._clock = (self.dir / "clock.jsonl").open("a", encoding="utf-8", newline="\n")
        self._last_fsync = clock.monotonic_ns()
        self._rotate()

    # -- writing ----------------------------------------------------------------

    def _rotate(self) -> None:
        if self._journal is not None:
            self._fsync(self._journal)
            self._journal.close()
        self.segment += 1
        self._journal = (self.dir / "journal" / f"raw-{self.segment:06d}.jsonl").open("a", encoding="utf-8", newline="\n")

    @staticmethod
    def _fsync(f: IO[str]) -> None:
        f.flush()
        os.fsync(f.fileno())

    def _write(self, f: IO[str], line: str) -> None:
        f.write(line + "\n")
        f.flush()  # process crash cannot lose a written line
        now = self.clock.monotonic_ns()
        if now - self._last_fsync >= self.config.fsync_interval.total_seconds() * 1e9:
            self.sync()

    def sync(self) -> None:
        for f in (self._journal, self._lifecycle, self._clock):
            if f is not None and not f.closed:
                self._fsync(f)
        self._last_fsync = self.clock.monotonic_ns()

    def record(self, **fields: Any) -> JournalRecord:
        self.seq += 1
        rec = JournalRecord(seq=self.seq, raw_sha256=sha256_text(fields["raw"]), **fields)
        self._write(self._journal, rec.model_dump_json())
        if self._journal.tell() >= self.config.segment_max_bytes:
            self._rotate()
        return rec

    def lifecycle(self, event: str, **fields: Any) -> LifecycleEvent:
        self.lifecycle_seq += 1
        ev = LifecycleEvent(seq=self.lifecycle_seq, at_utc_ns=self.clock.time_ns(),
                            at_mono_ns=self.clock.monotonic_ns(), event=event, **fields)
        self._write(self._lifecycle, ev.model_dump_json())
        return ev

    def clock_observation(self, obs: ClockObservation) -> None:
        self._write(self._clock, obs.model_dump_json())

    def close(self) -> None:
        self.sync()
        for f in (self._journal, self._lifecycle, self._clock):
            if f is not None and not f.closed:
                f.close()


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------


def load_config(path: Path) -> SessionConfig:
    return SessionConfig.model_validate_json((path / "config.json").read_text(encoding="utf-8"))


def journal_segments(path: Path) -> list[Path]:
    return sorted((path / "journal").glob("raw-*.jsonl"))


def _lines(path: Path) -> Iterator[str]:
    if not path.is_file():
        return
    with path.open("r", encoding="utf-8", newline="\n") as f:
        for line in f:
            if line.endswith("\n"):
                yield line[:-1]


def iter_records(path: Path, until_recv_utc_ns: int | None = None) -> Iterator[JournalRecord]:
    """Journal records in seq order; optionally only those received at or before a local cutoff."""
    for seg in journal_segments(path):
        for line in _lines(seg):
            rec = JournalRecord.model_validate_json(line)
            if until_recv_utc_ns is None or rec.recv_utc_ns <= until_recv_utc_ns:
                yield rec


def iter_lifecycle(path: Path) -> Iterator[LifecycleEvent]:
    for line in _lines(path / "lifecycle.jsonl"):
        yield LifecycleEvent.model_validate_json(line)


def iter_clock(path: Path) -> Iterator[ClockObservation]:
    for line in _lines(path / "clock.jsonl"):
        yield ClockObservation.model_validate_json(line)


def is_finalized(path: Path) -> bool:
    return (path / "manifest.json").is_file()


def load_manifest(path: Path) -> SessionManifest:
    return SessionManifest.model_validate_json((path / "manifest.json").read_text(encoding="utf-8"))


def load_report(path: Path) -> SessionReport:
    return SessionReport.model_validate_json((path / "report.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Recovery, finalization, verification
# ---------------------------------------------------------------------------


def _truncate_torn_tail(path: Path) -> int:
    """Drop an incomplete/undecodable final line. Returns bytes removed."""
    if not path.is_file():
        return 0
    data = path.read_bytes()
    keep = len(data)
    if data and not data.endswith(b"\n"):
        keep = data.rfind(b"\n") + 1
    else:
        # a complete last line that is not valid JSON is also torn (partial write before newline flush)
        last_start = data.rfind(b"\n", 0, len(data) - 1) + 1
        try:
            if data:
                json.loads(data[last_start:])
        except ValueError:
            keep = last_start
    if keep < len(data):
        with path.open("r+b") as f:
            f.truncate(keep)
        return len(data) - keep
    return 0


def recover(path: Path, clock: Clock, reason: str) -> dict[str, int]:
    """Make an abandoned (crashed) session consistent: truncate torn tails only."""
    if is_finalized(path):
        raise RecordingError(f"{path.name} is finalized; nothing to recover")
    removed = {}
    for f in [*journal_segments(path), path / "lifecycle.jsonl", path / "clock.jsonl"]:
        n = _truncate_torn_tail(f)
        if n:
            removed[f.relative_to(path).as_posix()] = n
    seqs = [r.seq for r in iter_records(path)]
    if seqs != list(range(1, len(seqs) + 1)):
        raise RecordingError(f"{path.name}: journal sequence is not contiguous after recovery")
    lseq = sum(1 for _ in iter_lifecycle(path))
    ev = LifecycleEvent(seq=lseq + 1, at_utc_ns=clock.time_ns(), at_mono_ns=clock.monotonic_ns(), event="recovered",
                        detail=f"{reason}; torn tail bytes removed: {removed or 'none'}; session not resumed")
    with (path / "lifecycle.jsonl").open("a", encoding="utf-8", newline="\n") as f:
        f.write(ev.model_dump_json() + "\n")
        f.flush()
        os.fsync(f.fileno())
    return removed


def finalize(path: Path, stop_reason: str, recovered: bool, host: str, pid: int, code_version: str | None,
             started_ns: int | None = None, stopped_ns: int | None = None) -> SessionManifest:
    """Write index, report and (last, atomically) the manifest. Never overwrites a finalized session."""
    from .analysis import build_bar_index, build_report

    if is_finalized(path):
        raise RecordingError(f"{path.name} is already finalized")
    config = load_config(path)
    lifecycle = list(iter_lifecycle(path))
    records_iter = iter_records
    start_ns = started_ns or (lifecycle[0].at_utc_ns if lifecycle else 0)
    stop_ns = stopped_ns or max([e.at_utc_ns for e in lifecycle] + [start_ns])
    with (path / "bars_index.jsonl").open("w", encoding="utf-8", newline="\n") as f:
        for row in build_bar_index(records_iter(path), config):
            f.write(json.dumps(row, sort_keys=True) + "\n")
    report, summary = build_report(path, config, lifecycle, recovered, start_ns, stop_ns)
    (path / "report.json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
    files = []
    for p in sorted(x for x in path.rglob("*") if x.is_file() and x.name not in ("manifest.json", "ACTIVE")):
        digest, size, lines = _sha256_file(p)
        files.append(FileRef(name=p.relative_to(path).as_posix(), sha256=digest, bytes=size,
                             lines=lines if p.suffix == ".jsonl" else None))
    manifest = SessionManifest(
        schema_version=RECORDER_SCHEMA_VERSION,
        contract_status=RECORDER_CONTRACT_STATUS,
        schema_revision=RECORDER_SCHEMA_REVISION,
        session_id=config.session_id,
        status=report.status,
        labels=LABELS,
        source=config.source,
        inst_id=config.inst_id,
        index_id=config.index_id,
        endpoints=config.endpoints,
        config=config,
        started_at=ns_to_dt(start_ns),
        stopped_at=ns_to_dt(stop_ns),
        stop_reason=stop_reason,
        recovered_after_crash=recovered,
        code_version=code_version,
        host=host,
        pid=pid,
        clock_source=CLOCK_SOURCE,
        receipt_point=RECEIPT_POINT,
        channels_requested=tuple(c.key for c in config.channels),
        channels_subscribed=summary["subscribed"],
        connections=summary["connections"],
        reconnects=summary["reconnects"],
        errors=len(report.errors),
        record_count=summary["records"],
        lifecycle_count=len(lifecycle),
        clock_observation_count=report.clock.observations,
        fsync_policy=(f"flush every line; fsync at least every {config.fsync_interval.total_seconds()} s; "
                      "torn final line truncated on recovery"),
        files=tuple(files),
    )
    tmp = path / ".manifest.json.tmp"
    tmp.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    os.replace(tmp, path / "manifest.json")
    (path / "ACTIVE").unlink(missing_ok=True)
    return manifest


def verify(path: Path, progress: Callable[[str, int, int | None, str], None] | None = None) -> list[str]:
    """Re-check a finalized session: file hashes/sizes/lines, contiguous seq, per-record raw hashes.

    ``progress(stage, done, total, unit)`` is an optional cooperative hook between bounded units
    (one file / 1,000 journal records). It may raise to cancel; it never changes what is checked.
    """
    hook = progress or (lambda *_: None)
    if not is_finalized(path):
        return ["not finalized (no manifest.json)"]
    problems: list[str] = []
    m = load_manifest(path)
    listed = {f.name for f in m.files}
    actual = {p.relative_to(path).as_posix() for p in path.rglob("*") if p.is_file() and p.name != "manifest.json"}
    for extra in sorted(actual - listed):
        problems.append(f"unlisted file {extra}")
    for i, ref in enumerate(m.files):
        hook("hash session files", i, len(m.files), "files")
        p = path / ref.name
        if not p.is_file():
            problems.append(f"missing file {ref.name}")
            continue
        digest, size, lines = _sha256_file(p)
        if (digest, size) != (ref.sha256, ref.bytes) or (ref.lines is not None and lines != ref.lines):
            problems.append(f"hash/size mismatch for {ref.name}")
    hook("hash session files", len(m.files), len(m.files), "files")
    expected = 1
    for rec in iter_records(path):
        if expected % 1000 == 1:
            hook("check journal records", expected - 1, m.record_count, "records")
        if rec.seq != expected:
            problems.append(f"journal seq gap at {expected}")
            break
        if sha256_text(rec.raw) != rec.raw_sha256:
            problems.append(f"raw hash mismatch at seq {rec.seq}")
        expected += 1
    if expected - 1 != m.record_count:
        problems.append(f"record count {expected - 1} != manifest {m.record_count}")
    return problems


def list_sessions(root: Path) -> list[Path]:
    base = recordings_dir(root)
    return sorted((p for p in base.iterdir() if p.is_dir() and (p / "config.json").is_file()), reverse=True) \
        if base.is_dir() else []


def session_path(root: Path, session_id: str) -> Path | None:
    p = recordings_dir(root) / session_id
    if p.parent != recordings_dir(root) or session_id.startswith(".") or not (p / "config.json").is_file():
        return None
    return p
