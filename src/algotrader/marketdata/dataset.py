"""Bounded, immutable, hash-verifiable OKX BTC-USDT-SWAP datasets.

Layout under ``<data_root>/datasets/<dataset_id>/``::

    manifest.json              DatasetManifest (hashes of every other file)
    quality.json               QualityReport
    instrument.json            normalized InstrumentSnapshot
    request_log.jsonl          one RawPageRef per source response, in request order
    raw/<family>/<nnnn>.json   exact source response bytes
    <family>.parquet           normalized records, chronological, unique keys

Identity: ``dataset_id`` is derived from the logical request, the market-data
schema version, the availability policy and the SHA-256 of every raw source
response in order. Re-fetching identical source bytes yields the same ID
(idempotent; the existing dataset is kept untouched). Any change in source
bytes yields a new ID; earlier versions for the same logical request are
listed in ``prior_versions``. A dataset directory is never overwritten.

Acquisition is bounded (``MAX_SPAN``) and streams: candles are fetched in
ascending windows of ``page_limit`` minutes and appended to Parquet per
window, so memory does not grow with the interval beyond key bookkeeping.
Nothing is repaired or forward-filled: gaps, duplicates, incomplete bars and
invalid rows are reported in the quality report.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from .contracts import (
    AVAILABILITY_POLICY_ID,
    AVAILABILITY_POLICY_TEXT,
    CANDLE_FAMILIES,
    HISTORICAL_FAMILIES,
    MARKETDATA_SCHEMA_VERSION,
    DatasetManifest,
    DatasetRequest,
    Family,
    FamilyQuality,
    FamilySummary,
    FileRef,
    FundingRateEvent,
    Gap,
    IndexCandle1m,
    InstrumentSnapshot,
    MarkCandle1m,
    QualityFinding,
    QualityReport,
    QualityStatus,
    RawPageRef,
    Record,
    RowQuality,
    Severity,
    TradeCandle1m,
)
from .okx import (
    BAR_MS,
    ENDPOINTS,
    MalformedResponse,
    OkxPublicClient,
    ParsedRow,
    RawResponse,
    dt_to_ms,
    ms_to_dt,
    parse_candle,
    parse_funding,
    parse_instrument,
    source_id_for,
)

MAX_SPAN = timedelta(days=31)  # bounded acquisition; not a backfill service
MAX_GAPS_LISTED = 500
LABELS = ("REAL_MARKET_DATA", "PUBLIC_SOURCE", "NOT_A_TRADING_RESULT")
SCOPE_NOTE = (
    "Quality evidence covers only the requested interval of this dataset. It is not a claim "
    "that the source's full history is complete."
)

RECORD_TYPES: dict[Family, type[Record]] = {
    Family.TRADE_CANDLES: TradeCandle1m,
    Family.MARK_CANDLES: MarkCandle1m,
    Family.INDEX_CANDLES: IndexCandle1m,
    Family.FUNDING: FundingRateEvent,
}


class DatasetError(Exception):
    pass


def datasets_dir(root: Path) -> Path:
    return root / "datasets"


def canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------


def parse_utc(text: str) -> datetime:
    dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise DatasetError(f"{text!r}: timestamps must carry an explicit UTC offset (e.g. 2026-09-29T08:00Z)")
    return dt.astimezone(UTC)


def validate_request(req: DatasetRequest, now: datetime) -> None:
    for name, t in (("start", req.start), ("end", req.end)):
        if t.tzinfo is None or t.utcoffset() != timedelta(0):
            raise DatasetError(f"{name} must be UTC")
        if t.second or t.microsecond:
            raise DatasetError(f"{name} must be aligned to a whole minute")
    if req.end <= req.start:
        raise DatasetError("end must be after start")
    if req.end - req.start > MAX_SPAN:
        raise DatasetError(f"interval exceeds the bounded maximum of {MAX_SPAN.days} days")
    if req.end > now:
        raise DatasetError("end is in the future; only past intervals can be acquired")
    if set(req.families) != set(HISTORICAL_FAMILIES):
        raise DatasetError("a dataset must request all four historical families")


def logical_request_key(req: DatasetRequest) -> str:
    return hashlib.sha256(canonical(req.model_dump(mode="json"))).hexdigest()[:24]


def compute_dataset_id(req: DatasetRequest, page_hashes: list[str]) -> str:
    basis = {
        "schema_version": MARKETDATA_SCHEMA_VERSION,
        "availability_policy": AVAILABILITY_POLICY_ID,
        "request": req.model_dump(mode="json"),
        "raw_pages_sha256": page_hashes,
    }
    digest = hashlib.sha256(canonical(basis)).hexdigest()
    return f"okx-{req.inst_id.lower()}-1m-{req.start:%Y%m%dT%H%M}-{req.end:%Y%m%dT%H%M}-{digest[:12]}"


class DatasetIdStream:
    """Incremental ``compute_dataset_id``: identical bytes hashed without holding the page-hash list.

    ``canonical(basis)`` sorts keys (availability_policy, raw_pages_sha256, request, schema_version), so the
    canonical JSON can be produced as a stream with page hashes appended one at a time.
    """

    def __init__(self, req: DatasetRequest) -> None:
        self.req = req
        self.h = hashlib.sha256()
        self.h.update(b'{"availability_policy":' + canonical(AVAILABILITY_POLICY_ID) + b',"raw_pages_sha256":[')
        self.n = 0

    def add(self, page_sha256: str) -> None:
        self.h.update((b"," if self.n else b"") + canonical(page_sha256))
        self.n += 1

    def dataset_id(self) -> str:
        h = self.h.copy()
        h.update(b'],"request":' + canonical(self.req.model_dump(mode="json")) + b',"schema_version":'
                 + canonical(MARKETDATA_SCHEMA_VERSION) + b"}")
        r = self.req
        return f"okx-{r.inst_id.lower()}-1m-{r.start:%Y%m%dT%H%M}-{r.end:%Y%m%dT%H%M}-{h.hexdigest()[:12]}"


IDENTITY_BASIS = (
    "sha256(schema_version, availability_policy, logical request, ordered raw page sha256s); "
    "identical source bytes -> same dataset_id, changed bytes -> new dataset_id"
)


# ---------------------------------------------------------------------------
# Parquet
# ---------------------------------------------------------------------------


def _arrow_type(annotation: Any) -> pa.DataType:
    text = str(annotation)
    if "Decimal" in text:
        return pa.string()  # exact source decimal text
    if "datetime" in text:
        return pa.timestamp("us", tz="UTC")
    if "tuple" in text:
        return pa.list_(pa.string())
    if annotation is bool:
        return pa.bool_()
    return pa.string()


def arrow_schema(model: type[Record]) -> pa.Schema:
    return pa.schema([pa.field(name, _arrow_type(f.annotation)) for name, f in model.model_fields.items()])


def _cell(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return [_cell(v) for v in value]
    return value


def _row(rec: Record) -> dict[str, Any]:
    return {name: _cell(getattr(rec, name)) for name in type(rec).model_fields}


# ---------------------------------------------------------------------------
# Family accumulation and quality
# ---------------------------------------------------------------------------


@dataclass
class FamilyState:
    family: Family
    writer: pq.ParquetWriter
    rows: int = 0
    pages: int = 0
    first: datetime | None = None
    last: datetime | None = None
    rejected_incomplete: int = 0
    outside_interval: int = 0
    out_of_order: int = 0
    dup_identical: int = 0
    dup_conflicting: int = 0
    invalid_flags: dict[str, int] = field(default_factory=dict)
    gaps: list[tuple[int, int]] = field(default_factory=list)  # (first_missing_ms, last_missing_ms)
    missing: int = 0
    last_key: int | None = None
    examples: dict[str, list[str]] = field(default_factory=dict)

    def example(self, check: str, text: str) -> None:
        ex = self.examples.setdefault(check, [])
        if len(ex) < 5:
            ex.append(text)


def _iso(ms: int) -> str:
    return ms_to_dt(ms).isoformat().replace("+00:00", "Z")


class _Acquisition:
    def __init__(self, client: OkxPublicClient, req: DatasetRequest, work: Path) -> None:
        self.client = client
        self.req = req
        self.work = work
        self.pages: list[RawPageRef] = []
        self.counters: dict[Family, int] = {}
        # Optional operational progress (see AcquireProgress); never affects the dataset.
        self.progress: ProgressHook | None = None
        self.phase = ""
        self.windows_done = 0
        self.windows_total = 0
        self.bytes = 0

    def report(self) -> None:
        if self.progress is not None:
            self.progress(AcquireProgress(self.phase, self.windows_done, self.windows_total, len(self.pages),
                                          self.bytes, self.work.name))

    def save_page(self, family: Family, resp: RawResponse) -> str:
        n = self.counters.get(family, 0)
        self.counters[family] = n + 1
        page_id = f"{family.value}/{n:04d}"
        rel = f"raw/{page_id}.json"
        path = self.work / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(resp.body)
        self.pages.append(
            RawPageRef(
                page_id=page_id,
                family=family,
                base_url=resp.base_url,
                path=resp.path,
                params=resp.params,
                retrieved_at=resp.retrieved_at,
                http_status=resp.http_status,
                source_code=resp.code,
                rows=len(resp.data),
                sha256=resp.sha256,
                bytes=len(resp.body),
                file=rel,
            )
        )
        self.bytes += len(resp.body)
        self.report()
        return page_id

    def fetch_window(
        self, family: Family, inst: InstrumentSnapshot, lo_ms: int, hi_ms: int, st: FamilyState
    ) -> list[ParsedRow]:
        """All source rows with lo_ms <= t < hi_ms, paging with the exclusive `after` cursor."""
        rows: list[ParsedRow] = []
        cursor = hi_ms
        src = source_id_for(family, inst)
        while True:
            resp = self.client.history_page(family, src, after_ms=cursor, before_ms=lo_ms - 1, limit=self.req.page_limit)
            page_id = self.save_page(family, resp)
            st.pages += 1
            if not resp.data:
                break
            parsed = [
                parse_funding(r, inst, resp.retrieved_at, page_id)
                if family == Family.FUNDING
                else parse_candle(family, r, inst, resp.retrieved_at, page_id)
                for r in resp.data
            ]
            keys = [p.key_ms for p in parsed]
            if any(a <= b for a, b in zip(keys, keys[1:])):  # source promises strictly newest first
                st.out_of_order += sum(1 for a, b in zip(keys, keys[1:]) if a <= b)
                st.example("source_out_of_order", f"page {page_id}")
            rows.extend(parsed)
            oldest = min(keys)
            if len(resp.data) < self.req.page_limit or oldest <= lo_ms:
                break
            if oldest >= cursor:
                raise MalformedResponse(f"{family}: pagination did not advance past {cursor}")
            cursor = oldest
        return rows

    def process(self, family: Family, rows: list[ParsedRow], lo_ms: int, hi_ms: int, st: FamilyState) -> None:
        """Filter, de-duplicate (never merge conflicting values), sort and append one window."""
        by_key: dict[int, list[ParsedRow]] = {}
        for p in rows:
            if not lo_ms <= p.key_ms < hi_ms:
                st.outside_interval += 1
                continue
            if not p.confirmed:
                st.rejected_incomplete += 1
                st.example("incomplete_candle_rejected", _iso(p.key_ms))
                continue
            by_key.setdefault(p.key_ms, []).append(p)
        accepted = []
        for key in sorted(by_key):
            group = by_key[key]
            if len(group) > 1:
                if len({json.dumps(g.raw, sort_keys=True) for g in group}) == 1:
                    st.dup_identical += len(group) - 1
                    st.example("duplicate_identical", _iso(key))
                else:  # conflicting source values: keep none, report
                    st.dup_conflicting += len(group)
                    st.example("duplicate_conflicting", _iso(key))
                    continue
            accepted.append(group[0])
        records = [p.record for p in accepted]
        for rec in records:
            for flag in getattr(rec, "quality_flags", ()):
                st.invalid_flags[flag] = st.invalid_flags.get(flag, 0) + 1
                st.example(flag, _iso(dt_to_ms(rec.open_time)))
        if family in CANDLE_FAMILIES:
            self._track_gaps(st, [p.key_ms for p in accepted], lo_ms, hi_ms)
        if records:
            st.writer.write_table(
                pa.Table.from_pylist([_row(r) for r in records], schema=st.writer.schema)
            )
            st.rows += len(records)
            t0, t1 = (ms_to_dt(accepted[0].key_ms), ms_to_dt(accepted[-1].key_ms))
            st.first = st.first or t0
            st.last = t1

    @staticmethod
    def _track_gaps(st: FamilyState, keys: list[int], lo_ms: int, hi_ms: int) -> None:
        expected = lo_ms
        for k in [*keys, hi_ms]:
            if k > expected:
                first, last = expected, k - BAR_MS
                st.missing += (last - first) // BAR_MS + 1
                if st.gaps and st.gaps[-1][1] == first - BAR_MS:
                    st.gaps[-1] = (st.gaps[-1][0], last)  # contiguous with the previous window
                else:
                    st.gaps.append((first, last))
            expected = max(expected, k + BAR_MS)


def _family_quality(family: Family, st: FamilyState, req: DatasetRequest) -> tuple[FamilyQuality, list[QualityFinding]]:
    f: list[QualityFinding] = []

    def add(check: str, severity: Severity, count: int, detail: str) -> None:
        if count:
            f.append(QualityFinding(family=family, check=check, severity=severity, count=count, detail=detail,
                                    examples=tuple(st.examples.get(check, ()))))

    add("duplicate_conflicting", Severity.INVALID, st.dup_conflicting,
        "rows with the same key but different source values; none kept (not merged)")
    for flag, n in sorted(st.invalid_flags.items()):
        add(flag, Severity.INVALID, n, "row kept for evidence with quality=INVALID")
    add("missing_intervals", Severity.DEGRADED, st.missing if family in CANDLE_FAMILIES else 0,
        f"{len(st.gaps)} gap(s); missing 1m bars are not filled")
    add("duplicate_identical", Severity.WARNING, st.dup_identical, "identical repeated rows; one kept")
    add("source_out_of_order", Severity.WARNING, st.out_of_order,
        "source page not strictly newest-first; normalized output is sorted")
    add("incomplete_candle_rejected", Severity.WARNING, st.rejected_incomplete,
        "confirm=0 candles are never normalized as completed bars")
    add("outside_requested_interval", Severity.INFO, st.outside_interval,
        "source rows outside the requested window; kept in raw pages only")
    if family == Family.FUNDING:
        f.append(QualityFinding(family=family, check="funding_events", severity=Severity.INFO, count=st.rows,
                                detail="funding events recorded (not applied to any account)"))
    worst = max((_RANK[x.severity] for x in f), default=0)
    expected = int((req.end - req.start) / timedelta(minutes=1)) if family in CANDLE_FAMILIES else None
    fq = FamilyQuality(
        family=family,
        status=_STATUS[worst],
        rows=st.rows,
        expected_rows=expected,
        missing_rows=st.missing if family in CANDLE_FAMILIES else None,
        first_time=st.first,
        last_time=st.last,
        gaps=tuple(
            Gap(first_missing_open_time=ms_to_dt(a), last_missing_open_time=ms_to_dt(b), missing_bars=(b - a) // BAR_MS + 1)
            for a, b in st.gaps[:MAX_GAPS_LISTED]
        ),
    )
    return fq, f


_RANK = {Severity.INFO: 0, Severity.WARNING: 1, Severity.DEGRADED: 2, Severity.INVALID: 3}
_STATUS = {0: QualityStatus.CLEAN, 1: QualityStatus.WARNING, 2: QualityStatus.DEGRADED, 3: QualityStatus.INVALID}
_STATUS_RANK = {v: k for k, v in _STATUS.items()}


def _instrument_findings(inst: InstrumentSnapshot) -> list[QualityFinding]:
    out = [
        QualityFinding(
            family=Family.INSTRUMENT, check="instrument_validated", severity=Severity.INFO, count=1,
            detail=(f"{inst.inst_id}: {inst.inst_type} {inst.ct_type}, 1 contract = {inst.ct_val} {inst.ct_val_ccy}, "
                    f"settled in {inst.settle_ccy}, index {inst.index_id}"),
        )
    ]
    if inst.state != "live":
        out.append(QualityFinding(family=Family.INSTRUMENT, check="instrument_not_live", severity=Severity.WARNING,
                                  count=1, detail=f"instrument state at retrieval: {inst.state}"))
    return out


# ---------------------------------------------------------------------------
# Acquire / verify / catalog
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AcquireResult:
    manifest: DatasetManifest
    path: Path
    reused: bool  # identical source content was already present


@dataclass(frozen=True)
class AcquireProgress:
    """Operational progress of one acquisition (never part of the dataset or its identity).

    ``windows_total`` is exact: candle families are fetched in fixed windows of ``page_limit``
    minutes and funding in one window. ``pages``/``bytes`` count source responses saved so far.
    """

    phase: str  # "instrument" | a family value | "finalizing"
    windows_done: int
    windows_total: int
    pages: int
    bytes: int
    work_dir: str  # name of the temporary directory under datasets/ (removed on any exit)


ProgressHook = Callable[[AcquireProgress], None]


def window_count(req: DatasetRequest) -> int:
    lo, hi = dt_to_ms(req.start), dt_to_ms(req.end)
    step = req.page_limit * BAR_MS
    return len(CANDLE_FAMILIES) * -(-(hi - lo) // step) + 1


def acquire(
    client: OkxPublicClient,
    root: Path,
    start: datetime,
    end: datetime,
    inst_id: str = "BTC-USDT-SWAP",
    page_limit: int = 100,
    progress: ProgressHook | None = None,
) -> AcquireResult:
    """Acquire one bounded dataset.

    ``progress`` (optional) is called after every saved source page and completed window, and
    before finalization. It may raise to abort the acquisition at that page boundary: the
    temporary directory is removed and nothing is published. Without it, behavior is unchanged.
    """
    req = DatasetRequest(
        base_url=client.base_url, inst_id=inst_id, start=start, end=end,
        families=HISTORICAL_FAMILIES, page_limit=page_limit,
    )
    started = client.clock()
    validate_request(req, started)
    base = datasets_dir(root)
    base.mkdir(parents=True, exist_ok=True)
    work = base / f".tmp-{uuid.uuid4().hex}"
    work.mkdir()
    try:
        return _acquire_into(client, req, base, work, started, progress)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _acquire_into(
    client: OkxPublicClient, req: DatasetRequest, base: Path, work: Path, started: datetime,
    progress: ProgressHook | None = None,
) -> AcquireResult:
    acq = _Acquisition(client, req, work)
    if progress is not None:
        acq.progress = progress
        acq.windows_total = window_count(req)
    acq.phase = "instrument"
    inst_resp = client.instrument(req.inst_id)
    inst_page = acq.save_page(Family.INSTRUMENT, inst_resp)
    inst = parse_instrument(inst_resp, req.inst_id, inst_page)

    lo, hi = dt_to_ms(req.start), dt_to_ms(req.end)
    states: dict[Family, FamilyState] = {}
    try:
        for family in HISTORICAL_FAMILIES:
            acq.phase = family.value
            st = states[family] = FamilyState(
                family, pq.ParquetWriter(work / f"{family.value}.parquet", arrow_schema(RECORD_TYPES[family]))
            )
            # candles: ascending windows of page_limit minutes; funding: one window
            step = req.page_limit * BAR_MS if family in CANDLE_FAMILIES else hi - lo
            for w_lo in range(lo, hi, step):
                w_hi = min(w_lo + step, hi)
                acq.process(family, acq.fetch_window(family, inst, w_lo, w_hi, st), w_lo, w_hi, st)
                acq.windows_done += 1
                acq.report()
    finally:
        for st in states.values():
            st.writer.close()
    acq.phase = "finalizing"
    acq.report()
    finished = client.clock()

    dataset_id = compute_dataset_id(req, [p.sha256 for p in acq.pages])
    final = base / dataset_id
    if final.exists():
        problems = verify(final)
        if problems:
            raise DatasetError(f"{dataset_id} exists but fails verification (not overwritten): {problems}")
        return AcquireResult(load_manifest(final), final, reused=True)

    families_q, findings = [], _instrument_findings(inst)
    for family in HISTORICAL_FAMILIES:
        fq, ff = _family_quality(family, states[family], req)
        families_q.append(fq)
        findings += ff
    status = _STATUS[max(_STATUS_RANK[fq.status] for fq in families_q)]
    if any(x.severity == Severity.WARNING for x in findings) and status == QualityStatus.CLEAN:
        status = QualityStatus.WARNING
    report = QualityReport(
        schema_version=MARKETDATA_SCHEMA_VERSION, dataset_id=dataset_id, status=status,
        scope_note=SCOPE_NOTE, families=tuple(families_q), findings=tuple(findings),
    )
    (work / "quality.json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
    (work / "instrument.json").write_text(inst.model_dump_json(indent=2), encoding="utf-8")
    with (work / "request_log.jsonl").open("w", encoding="utf-8") as f:
        for p in acq.pages:
            f.write(p.model_dump_json() + "\n")

    files = []
    for path in sorted(p for p in work.rglob("*") if p.is_file()):
        name = path.relative_to(work).as_posix()
        rows = pq.ParquetFile(path).metadata.num_rows if name.endswith(".parquet") else None
        media = "application/vnd.apache.parquet" if rows is not None else (
            "application/x-ndjson" if name.endswith(".jsonl") else "application/json")
        files.append(FileRef(name=name, sha256=sha256_file(path), bytes=path.stat().st_size, rows=rows, media_type=media))

    key = logical_request_key(req)
    prior = tuple(
        m.dataset_id for m in list_manifests(base.parent) if m.logical_request_key == key and m.dataset_id != dataset_id
    )
    manifest = DatasetManifest(
        schema_version=MARKETDATA_SCHEMA_VERSION,
        dataset_id=dataset_id,
        logical_request_key=key,
        labels=LABELS,
        request=req,
        instrument=inst,
        availability_policy=AVAILABILITY_POLICY_ID,
        availability_policy_text=AVAILABILITY_POLICY_TEXT,
        retrieval_started_at=started,
        retrieval_finished_at=finished,
        code_version=_code_version(),
        families=tuple(
            FamilySummary(
                family=fam, endpoint=ENDPOINTS[fam], rows=states[fam].rows, pages=states[fam].pages,
                first_time=states[fam].first, last_time=states[fam].last,
                rejected_incomplete=states[fam].rejected_incomplete, outside_interval=states[fam].outside_interval,
            )
            for fam in HISTORICAL_FAMILIES
        ),
        quality_status=status,
        raw_page_count=len(acq.pages),
        identity_basis=IDENTITY_BASIS,
        prior_versions=prior,
        files=tuple(files),
    )
    (work / "manifest.json").write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    os.replace(work, final)  # atomic publish; `final` did not exist
    return AcquireResult(manifest, final, reused=False)


def load_manifest(path: Path) -> DatasetManifest:
    return DatasetManifest.model_validate_json((path / "manifest.json").read_text(encoding="utf-8"))


def load_quality(path: Path) -> QualityReport:
    return QualityReport.model_validate_json((path / "quality.json").read_text(encoding="utf-8"))


def verify(path: Path, progress: Callable[[str, int, int | None, str], None] | None = None) -> list[str]:
    """Re-check every recorded hash, row count and the dataset identity. Empty list = OK.

    ``progress(stage, done, total, unit)`` is an optional cooperative hook called between bounded units
    (one file / one raw page). It may raise to cancel; it never changes what is checked.
    """
    hook = progress or (lambda *_: None)
    problems: list[str] = []
    try:
        m = load_manifest(path)
    except (OSError, ValueError) as exc:
        return [f"manifest unreadable: {exc}"]
    if m.schema_version != MARKETDATA_SCHEMA_VERSION:
        problems.append(f"schema_version {m.schema_version} is not {MARKETDATA_SCHEMA_VERSION}")
    if path.name != m.dataset_id:
        problems.append(f"directory {path.name} does not match dataset_id {m.dataset_id}")
    for i, ref in enumerate(m.files):
        hook("hash dataset files", i, len(m.files), "files")
        p = path / ref.name
        if not p.is_file():
            problems.append(f"missing file {ref.name}")
            continue
        if sha256_file(p) != ref.sha256 or p.stat().st_size != ref.bytes:
            problems.append(f"hash/size mismatch for {ref.name}")
        if ref.rows is not None and pq.ParquetFile(p).metadata.num_rows != ref.rows:
            problems.append(f"row count mismatch for {ref.name}")
    hook("hash dataset files", len(m.files), len(m.files), "files")
    # request log streamed line by line (never materialized); identity hashed incrementally (same bytes)
    ident = DatasetIdStream(m.request)
    total = m.raw_page_count
    try:
        with (path / "request_log.jsonl").open(encoding="utf-8") as f:
            for i, line in enumerate(f):
                if not line.strip():
                    continue
                page = RawPageRef.model_validate_json(line)
                hook("check raw source pages", i, total, "pages")
                p = path / page.file
                if not p.is_file() or sha256_file(p) != page.sha256:
                    problems.append(f"raw page {page.page_id} missing or altered")
                ident.add(page.sha256)
    except (OSError, ValueError) as exc:
        return [*problems, f"request log unreadable: {exc}"]
    hook("check raw source pages", total, total, "pages")
    if ident.dataset_id() != m.dataset_id:
        problems.append("dataset_id does not match the raw source content")
    for fam in m.families:
        ref = next((r for r in m.files if r.name == f"{fam.family.value}.parquet"), None)
        if ref is None or ref.rows != fam.rows:
            problems.append(f"family {fam.family.value} row count not reflected in files")
    return problems


def list_manifests(root: Path) -> list[DatasetManifest]:
    base = datasets_dir(root)
    if not base.is_dir():
        return []
    out = []
    for d in sorted(base.iterdir()):
        if d.is_dir() and not d.name.startswith(".") and (d / "manifest.json").is_file():
            try:
                out.append(load_manifest(d))
            except ValueError:
                continue
    return sorted(out, key=lambda m: m.retrieval_started_at, reverse=True)


def dataset_path(root: Path, dataset_id: str) -> Path | None:
    p = datasets_dir(root) / dataset_id
    if p.parent != datasets_dir(root) or dataset_id.startswith(".") or not (p / "manifest.json").is_file():
        return None
    return p


def default_data_root() -> Path:
    return Path(os.environ.get("ALGOTRADER_DATA_ROOT", "var/data")).resolve()


def _code_version() -> str | None:
    # Imported lazily so readers of market data (e.g. the causal feed core) do not load the
    # DEMO engine/trader/account modules that live next to ``artifacts``.
    from ..artifacts import code_version

    return code_version()
