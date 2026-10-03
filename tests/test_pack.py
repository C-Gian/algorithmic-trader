"""WP-008-R3 evidence: presets/windows, local reuse with a network spy, trust/fault handling, the composition oracle,
continuity across source/month boundaries and capability scope. Tiny offline fixtures only (no real month, no
network, no economic outcome)."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg
import pytest
from okx_fake import client
from okx_synth import synthetic_fake
from pack_fixtures import (
    EV_END,
    EV_START,
    FAKE_END,
    FAKE_START,
    REQ_END,
    REQ_START,
    acquire,
    connect,
    corpus_worker,
    drain,
    fake,
    write_presets,
)

from algotrader.corpus import pack as pk
from algotrader.corpus import pack_job as pj
from algotrader.corpus import presets as ps
from algotrader.feed.ordering import canonical
from algotrader.marketdata import dataset as md
from algotrader.marketdata.contracts import Family as MdFamily
from algotrader.observe import control, deep
from algotrader.observe import feedcache as fc
from algotrader.observe.contracts import SourceKind
from algotrader.observe.job import SimulatedCrash
from algotrader.observe.sources import ReceiptStore, SourceRejected
from algotrader.observe.worker import ObservationWorker
from algotrader.temporal import engine as te

ROOT = Path(__file__).resolve().parents[1]
UTC0 = timedelta(0)


def T(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


# ---------------------------------------------------------------------------
# A. Presets and window arithmetic (pure)
# ---------------------------------------------------------------------------


def test_registered_presets_are_the_director_file_with_exact_windows():
    assert (ROOT / "src/algotrader/corpus/presets.json").read_text(encoding="utf-8") == \
        (ROOT / "delivery/WP-008-R3-PRESETS.json").read_text(encoding="utf-8")
    f = ps.load_presets(ps.PRESETS_FILE)
    assert (f.fine_warmup_hours, f.outcome_tail_minutes, f.fixture) == (96, 365, False)
    d = f.default
    assert d.preset_id == "btc-september-development-v1" and sum(p.default for p in f.presets) == 1
    assert (d.warmup.start, d.warmup.end) == (T("2025-08-28T00:00Z"), T("2025-09-01T00:00Z"))
    assert d.warmup.minutes == 96 * 60
    assert (d.evaluation.start, d.evaluation.end) == (T("2025-09-01T00:00Z"), T("2025-10-01T00:00Z"))
    assert (d.tail.start, d.tail.end, d.tail.minutes) == (T("2025-10-01T00:00Z"), T("2025-10-01T06:05Z"), 365)
    so = f.preset("btc-september-october-continuity-v1")
    assert so.evaluation.end == T("2025-11-01T00:00Z") and so.tail.end == T("2025-11-01T06:05Z")
    assert all(not p.adviser_implemented and not p.automatic_prepare for p in f.presets)
    reg = json.loads((ROOT / "delivery/MP-001-PARAMETERS.json").read_text(encoding="utf-8"))
    assert hashlib.sha256(canonical(reg)).hexdigest() == ps.MP001_REGISTER_SHA256
    w = ps.windows_doc(d)
    assert (w["warmup"]["scored"], w["evaluation"]["scored"], w["tail"]["scored"]) == (False, True, False)
    # the builder reproduces the registered default exactly (only id/label/class differ)
    b = ps.months_preset(f, ["2025-09"])
    assert (b.warmup, b.evaluation, b.tail) == (d.warmup, d.evaluation, d.tail)
    assert ps.preset_sha256(f, d) == ps.preset_sha256(ps.load_presets(ps.PRESETS_FILE), d)  # deterministic identity


def test_month_builder_calendar_months_protected_split_and_rejections():
    f = ps.load_presets(ps.PRESETS_FILE)
    feb = ps.months_preset(f, ["2026-02"])
    assert feb.evaluation.minutes == 28 * 1440 and feb.warmup.start == T("2026-01-28T00:00Z")
    leap = f.model_copy(update={"target": ps.Window(start=T("2024-01-01T00:00Z"), end=T("2027-01-01T00:00Z"))})
    assert ps.months_preset(leap, ["2024-02"]).evaluation.minutes == 29 * 1440
    dec_jan = ps.months_preset(f, ["2025-12", "2026-01"])
    assert dec_jan.tail.end == T("2026-02-01T06:05Z")
    cls = ps.classify(f, dec_jan)
    assert cls["label"] == "MIXED_DEVELOPMENT_AND_PROTECTED" and len(cls["portions"]) == 2
    assert cls["certified_uncontaminated"] is False
    assert cls["portions"][1]["contamination"].startswith("UNKNOWN")
    prot = ps.classify(f, ps.months_preset(f, ["2026-03"]))
    assert prot["label"] == "PROTECTED_PROVISIONAL" and prot["certified_uncontaminated"] is False
    for bad in (["2025-09", "2025-11"], ["2025-10", "2025-09"], ["2025-09", "2025-09"], ["2026-09"], ["2025-9x"], []):
        with pytest.raises(ps.PresetError):
            ps.months_preset(f, bad)
    with pytest.raises(ValueError):  # registered files require exact windows over whole calendar months
        ps.PresetsFile.model_validate({**json.loads(ps.PRESETS_FILE.read_text(encoding="utf-8")), "presets": [
            {**json.loads(ps.PRESETS_FILE.read_text(encoding="utf-8"))["presets"][0],
             "evaluation": {"start": "2025-09-02T00:00:00Z", "end": "2025-10-01T00:00:00Z"}}]})


def test_acquisition_requests_split_at_months_and_the_span_bound():
    s = pk.split_requests(T("2025-08-28T00:00Z"), T("2025-10-01T06:05Z"))
    assert s == [(T("2025-08-28T00:00Z"), T("2025-09-01T00:00Z")), (T("2025-09-01T00:00Z"), T("2025-10-01T00:00Z")),
                 (T("2025-10-01T00:00Z"), T("2025-10-01T06:05Z"))]
    assert all(b - a <= timedelta(days=31) for a, b in s)
    s10 = pk.split_requests(T("2025-09-01T00:00Z"), T("2025-10-01T00:00Z"), max_days=10)
    assert [b - a for a, b in s10] == [timedelta(days=10)] * 3


# ---------------------------------------------------------------------------
# B. Local reuse, slicing and the network spy
# ---------------------------------------------------------------------------


def _job(c, job_id):
    return c.execute("SELECT * FROM corpus_pack_jobs WHERE job_id = %s", (job_id,)).fetchone()


def _prepare(database_url, root, f, preset=None):
    with connect(database_url) as c:
        P = ps.load_presets()
        jid = pj.create_pack_job(c, P, preset or P.default)
    drain(corpus_worker(database_url, root, f))
    with connect(database_url) as c:
        return _job(c, jid)


@pytest.mark.db
def test_local_month_reused_only_boundary_slices_downloaded_then_warm_reuse_is_offline(
        database_url, tmp_path, monkeypatch):
    write_presets(tmp_path, monkeypatch)
    root = tmp_path / "data"
    f = fake()
    local = acquire(root, f, EV_START, EV_END)
    manifest_before = hashlib.sha256((md.dataset_path(root, local) / "manifest.json").read_bytes()).hexdigest()
    f.calls.clear()
    job = _prepare(database_url, root, f)
    assert job["status"] == "completed" and job["outcome"] == "prepared", job["error"]
    kids = job["children"]
    assert [(T(x["start"]), T(x["end"])) for x in kids] == [(REQ_START, EV_START), (EV_END, REQ_END)]
    assert all(x["status"] == "completed" for x in kids)
    # no request ever asked for the locally present evaluation interval (zero duplicate downloads)
    asked = [(int(p.get("before", -1)), int(p.get("after", 2**62))) for path, p, _ in f.calls if "after" in p]
    ev_lo, ev_hi = int(EV_START.timestamp() * 1000), int(EV_END.timestamp() * 1000)
    assert not any(lo < ev_lo + 60_000 and hi > ev_hi - 60_000 for lo, hi in asked)
    doc = pk.open_pack(root, job["pack_id"], pk.pack_receipt(connect(database_url), job["pack_id"]))
    assert [s["dataset_id"] for s in doc["sources"]] == [kids[0]["dataset_id"], local, kids[1]["dataset_id"]]
    assert hashlib.sha256((md.dataset_path(root, local) / "manifest.json").read_bytes()).hexdigest() == manifest_before
    f.calls.clear()
    again = _prepare(database_url, root, f)
    assert again["outcome"] == "reused_pack" and again["pack_id"] == job["pack_id"] and f.calls == []


@pytest.mark.db
def test_larger_covering_package_is_sliced_without_any_request(database_url, tmp_path, monkeypatch):
    write_presets(tmp_path, monkeypatch)
    root = tmp_path / "data"
    f = fake()
    big = acquire(root, f, REQ_START - timedelta(hours=1), REQ_END + timedelta(hours=1))
    f.calls.clear()
    job = _prepare(database_url, root, f)
    assert job["status"] == "completed" and f.calls == [] and job["children"] == []
    doc = pk.open_pack(root, job["pack_id"], pk.pack_receipt(connect(database_url), job["pack_id"]))
    assert [(s["dataset_id"], T(s["start"]), T(s["end"])) for s in doc["sources"]] == [(big, REQ_START, REQ_END)]
    assert T(doc["clock_end"]) == REQ_END and T(doc["tail_end"]) == REQ_END


@pytest.mark.db
def test_completed_children_survive_cancellation_and_a_worker_crash(database_url, tmp_path, monkeypatch):
    write_presets(tmp_path, monkeypatch)
    root = tmp_path / "data"
    f = fake()
    acquire(root, f, EV_START, EV_END)
    orig_check = pj.PackJobRunner._check

    def cancel_after_first_child(self, hb):  # a cancellation observed right after a child completed
        with connect(database_url) as c:
            row = c.execute("SELECT children FROM corpus_pack_jobs ORDER BY created_at DESC LIMIT 1").fetchone()
        if any(x["status"] == "completed" for x in row["children"]):
            from algotrader.corpus.job import AcquisitionCancelled

            raise AcquisitionCancelled()
        return orig_check(self, hb)

    monkeypatch.setattr(pj.PackJobRunner, "_check", cancel_after_first_child)
    job = _prepare(database_url, root, f)
    monkeypatch.setattr(pj.PackJobRunner, "_check", orig_check)
    assert job["status"] == "cancelled" and job["pack_id"] is None
    done = [x for x in job["children"] if x["status"] == "completed"]
    assert len(done) == 1 and md.dataset_path(root, done[0]["dataset_id"]) is not None
    assert md.verify(md.dataset_path(root, done[0]["dataset_id"])) == []
    with connect(database_url) as c:
        assert c.execute("SELECT count(*) AS n FROM corpus_packs").fetchone()["n"] == 0
    f.calls.clear()
    # restart with a crash in the middle of the remaining child, then reclaim by a new generation
    real = md.acquire
    crashed = {"n": 0}

    def crash_once(*a, **kw):
        if not crashed["n"]:
            crashed["n"] += 1
            raise SimulatedCrash("worker died mid-child")
        return real(*a, **kw)

    monkeypatch.setattr(md, "acquire", crash_once)
    with connect(database_url) as c:
        jid = pj.create_pack_job(c, ps.load_presets(), ps.load_presets().default)
    with pytest.raises(SimulatedCrash):
        corpus_worker(database_url, root, f, worker_id="corpus:a").run_once()
    with connect(database_url) as c:
        c.execute("UPDATE corpus_pack_jobs SET lease_expires_at = now() - interval '1 second' WHERE job_id = %s",
                  (jid,))
    drain(corpus_worker(database_url, root, f, worker_id="corpus:b"))
    with connect(database_url) as c:
        row = _job(c, jid)
    assert row["status"] == "completed" and row["lease_generation"] == 2
    assert [x["event"] for x in row["recovery_log"]] == ["lease_expired_reclaimed"]
    # only the child that was never completed is acquired: the cancelled job's child is reused locally
    assert [(T(x["start"]), T(x["end"])) for x in row["children"]] == [(EV_END, REQ_END)]


@pytest.mark.db
def test_source_api_error_is_a_failed_child_never_a_trusted_empty_package(database_url, tmp_path, monkeypatch):
    write_presets(tmp_path, monkeypatch)
    root = tmp_path / "data"
    f = fake()
    acquire(root, f, EV_START, EV_END)
    before = sorted(p.name for p in md.datasets_dir(root).iterdir())
    f.queued = [(200, json.dumps({"code": "50001", "msg": "service temporarily unavailable", "data": []}).encode())] * 8
    job = _prepare(database_url, root, f)
    assert job["status"] == "failed" and "required acquisition" in job["error"]
    assert job["children"][0]["status"] == "failed" and job["pack_id"] is None
    assert sorted(p.name for p in md.datasets_dir(root).iterdir()) == before  # nothing finalized, no fake empty data
    with connect(database_url) as c:
        assert c.execute("SELECT count(*) AS n FROM corpus_packs").fetchone()["n"] == 0


# ---------------------------------------------------------------------------
# C. Trust and publication faults
# ---------------------------------------------------------------------------


@pytest.mark.db
@pytest.mark.parametrize("stage", ["before_publish_lock", "after_rename", "before_commit"])
def test_crash_around_publication_converges_to_one_trusted_pack(database_url, tmp_path, monkeypatch, stage):
    write_presets(tmp_path, monkeypatch)
    root = tmp_path / "data"
    f = fake()

    def fault(s):
        if s == stage:
            raise SimulatedCrash(s)

    with connect(database_url) as c:
        jid = pj.create_pack_job(c, ps.load_presets(), ps.load_presets().default)
    with pytest.raises(SimulatedCrash):
        corpus_worker(database_url, root, f, worker_id="corpus:a", pack_fault=fault).run_once()
    with connect(database_url) as c:
        assert c.execute("SELECT count(*) AS n FROM corpus_packs").fetchone()["n"] == 0  # nothing trusted yet
        c.execute("UPDATE corpus_pack_jobs SET lease_expires_at = now() - interval '1 second' WHERE job_id = %s",
                  (jid,))
    f.calls.clear()
    drain(corpus_worker(database_url, root, f, worker_id="corpus:b"))
    with connect(database_url) as c:
        row = _job(c, jid)
        recs = c.execute("SELECT * FROM corpus_packs").fetchall()
    assert row["status"] == "completed" and len(recs) == 1 and f.calls == []  # children reused after the crash
    assert row["outcome"] == ("prepared_converged" if stage != "before_publish_lock" else "prepared")
    pk.open_pack(root, recs[0]["pack_id"], recs[0])


@pytest.mark.db
def test_cancel_or_stale_generation_at_the_publication_boundary_publishes_nothing(database_url, tmp_path,
                                                                                  monkeypatch):
    write_presets(tmp_path, monkeypatch)
    root = tmp_path / "data"
    f = fake()
    for column in ("cancel_requested = true", "lease_generation = lease_generation + 1"):
        def fault(s, column=column):
            if s == "before_publish_lock":
                with connect(database_url) as c:
                    c.execute(f"UPDATE corpus_pack_jobs SET {column} WHERE status = 'running'")

        with connect(database_url) as c:
            jid = pj.create_pack_job(c, ps.load_presets(), ps.load_presets().default)
        corpus_worker(database_url, root, f, pack_fault=fault).run_once()
        with connect(database_url) as c:
            row = _job(c, jid)
            assert c.execute("SELECT count(*) AS n FROM corpus_packs").fetchone()["n"] == 0
        if column.startswith("cancel"):
            assert row["status"] == "cancelled"
        else:  # fenced: the stale attempt wrote nothing and left the row to its newer owner
            assert row["status"] == "running" and row["pack_id"] is None
            with connect(database_url) as c:
                c.execute("UPDATE corpus_pack_jobs SET status = 'failed' WHERE job_id = %s", (jid,))
        assert not [p for p in pk.packs_root(root).iterdir() if not p.name.startswith(".")]


def _published(database_url, tmp_path, monkeypatch, f=None):
    write_presets(tmp_path, monkeypatch)
    root = tmp_path / "data"
    f = f or fake()
    job = _prepare(database_url, root, f)
    assert job["status"] == "completed", job["error"]
    return root, job["pack_id"], f


def _replay(database_url, root, pack_id, **kw):
    with connect(database_url) as c:
        rec = pk.pack_receipt(c, pack_id)
        rid = control.create_replay(c, root, SourceKind.PACK, pack_id, 0, False,
                                    expected_manifest_sha256=rec["manifest_sha256"] if rec else None)
    kw.setdefault("checkpoint_events", 97)
    w = ObservationWorker(database_url, root, root.parent / "art", worker_id=kw.pop("worker_id", "observe:pack"),
                          isolate=False, sleep=lambda s: None, lease_seconds=5, poll_interval=0.01, **kw)
    while w.run_once():
        pass
    with connect(database_url) as c:
        return c.execute("SELECT * FROM observation_replays WHERE replay_id = %s", (rid,)).fetchone()


@pytest.mark.db
def test_replaced_manifest_or_missing_receipt_is_never_trusted_and_prepare_recovers(database_url, tmp_path,
                                                                                     monkeypatch):
    root, pack_id, f = _published(database_url, tmp_path, monkeypatch)
    mf = pk.packs_root(root) / pack_id / "manifest.json"
    good = mf.read_bytes()
    doc = json.loads(good)
    doc["rules_version"] = "mp001.rules.v0.3"  # a plausible replacement keeping the SAME id
    mf.write_bytes(pk.render_manifest(doc))
    with connect(database_url) as c:
        with pytest.raises(pk.PackError, match="does not match its receipt"):
            pk.open_pack(root, pack_id, pk.pack_receipt(c, pack_id))
    r = _replay(database_url, root, pack_id)
    assert r["status"] == "failed" and "does not match its receipt" in r["error"]
    job = _prepare(database_url, root, f)  # rebuild: the tampered directory is quarantined, never overwritten
    assert job["status"] == "completed" and job["pack_id"] == pack_id and mf.read_bytes() == good
    assert [p for p in pk.packs_root(root).iterdir() if p.name.startswith(f".invalid-{pack_id}")]
    with connect(database_url) as c:
        c.execute("DELETE FROM corpus_packs WHERE pack_id = %s", (pack_id,))
        with pytest.raises(pk.PackError, match="no trusted publication receipt"):
            pk.open_pack(root, pack_id, pk.pack_receipt(c, pack_id))
    job = _prepare(database_url, root, f)
    assert job["status"] == "completed" and job["outcome"] == "prepared_converged"


@pytest.mark.db
def test_pack_cache_partition_or_manifest_tamper_is_rebuilt_only_from_pinned_sources(database_url, tmp_path,
                                                                                    monkeypatch):
    root, pack_id, f = _published(database_url, tmp_path, monkeypatch)
    ok = _replay(database_url, root, pack_id)
    assert ok["status"] == "completed" and ok["manifest"]["validation"]["validator_version"] == "4"
    doc = json.loads((pk.packs_root(root) / pack_id / "manifest.json").read_text())
    cdir = fc.cache_root(root) / doc["feed"]["cache_id"]
    cm = cdir / "manifest.json"
    cm.write_bytes(cm.read_bytes() + b" ")  # a compatible-looking manifest edit (same JSON, other bytes)
    rebuilt_m = _replay(database_url, root, pack_id)
    assert rebuilt_m["status"] == "completed", rebuilt_m["error"]  # quarantined and rebuilt to its receipt
    assert list(fc.cache_root(root).glob(f".invalid-{doc['feed']['cache_id']}*"))
    part = sorted(cdir.glob("part-*"))[0]
    blob = bytearray(part.read_bytes())
    blob[-5] ^= 0xFF
    part.write_bytes(bytes(blob))
    bad = _replay(database_url, root, pack_id)
    assert bad["status"] == "failed" and "feed cache" in bad["error"]
    rebuilt = _replay(database_url, root, pack_id)  # quarantined cache rebuilt from the pinned source slices
    assert rebuilt["status"] == "completed" and rebuilt["engine"]["cache_manifest_sha256"] == \
        doc["feed"]["cache_manifest_sha256"]
    # a pinned source that changed cannot rebuild the pack cache: visible failure, never a different pack
    shutil.rmtree(cdir)
    src = md.dataset_path(root, doc["sources"][0]["dataset_id"]) / "manifest.json"
    src.write_bytes(src.read_bytes().replace(b'"page_limit"', b'"page_limit" '))
    failed = _replay(database_url, root, pack_id)
    assert failed["status"] == "failed" and "could not be rebuilt" in failed["error"]


# ---------------------------------------------------------------------------
# D. Composition oracle
# ---------------------------------------------------------------------------


def _contribs(conn, root, slices):
    rs = ReceiptStore(conn)
    return pk.prepare_contributors(root, rs, slices)


def _preset(f):
    return ps.load_presets().default


def _compose(conn, root, slices, tmp):
    contribs = _contribs(conn, root, slices)
    cache, stats = pk.build_pack_cache(root, contribs, _preset(None), tmp / f"w{len(list(tmp.iterdir()))}",
                                       provenance=tmp / "prov.jsonl")
    return cache, stats


def _events(cache):
    return [fc.decode(line) for _s, line in fc.CacheReader(cache).iter_from(0)]


def _temporal_chain(cache):
    eng = te.for_feed(cache.feed_manifest, te.profile_for_feed(cache.feed_manifest))
    for i, e in enumerate(_events(cache)):
        eng.on_event(e, i)
    eng.finish()
    return eng.aggregate_chain


@pytest.mark.db
def test_equivalent_packagings_compose_identical_semantics(database_url, tmp_path, monkeypatch):
    write_presets(tmp_path, monkeypatch)
    root = tmp_path / "data"
    f = fake(gap_every=41)
    one = acquire(root, f, REQ_START, REQ_END)
    a = acquire(root, f, REQ_START, EV_START + timedelta(hours=1))
    b = acquire(root, f, EV_START + timedelta(hours=1), REQ_END)
    o1 = acquire(root, f, REQ_START, EV_START + timedelta(hours=2))  # overlapping packages
    o2 = acquire(root, f, EV_START + timedelta(hours=1), REQ_END)
    tmp = tmp_path / "w"
    tmp.mkdir()
    with connect(database_url) as c:
        single, s1 = _compose(c, root, [(one, REQ_START, REQ_END, "local")], tmp)
        split, s2 = _compose(c, root, [(a, REQ_START, EV_START + timedelta(hours=1), "local"),
                                       (b, EV_START + timedelta(hours=1), REQ_END, "local")], tmp)
        over, s3 = _compose(c, root, [(o1, REQ_START, EV_START + timedelta(hours=2), "local"),
                                      (o2, EV_START + timedelta(hours=1), REQ_END, "local")], tmp)
    fm = [x.feed_manifest for x in (single, split, over)]
    assert len({m.content_identity for m in fm}) == 1 and len({m.event_count for m in fm}) == 1
    assert fm[0].ordered_event_hash != fm[1].ordered_event_hash  # provenance-sensitive commitment (SourceRef)
    assert s3.overlapping_slots > 0 and s3.identical_collapsed == s3.overlapping_slots and s3.gap_replaced == 0
    assert (tmp / "prov.jsonl").read_text().count("\n") == s3.provenance_lines == s3.overlapping_slots
    assert pk.coverage_counts(s1) == pk.coverage_counts(s2) == pk.coverage_counts(s3)
    assert len({_temporal_chain(x) for x in (single, split, over)}) == 1
    # canonical order across families/sources: order keys strictly increasing (ties sorted together)
    keys = [fc.order_sort_key(e) for e in _events(over)]
    assert keys == sorted(keys) and len(set(keys)) == len(keys)
    # primary SourceRef of a collapsed slot is chosen deterministically, independent of slice order
    over2, _ = _compose(connect(database_url), root, [(o2, EV_START + timedelta(hours=1), REQ_END, "local"),
                                                       (o1, REQ_START, EV_START + timedelta(hours=2), "local")], tmp)
    assert over2.feed_manifest.ordered_event_hash == over.feed_manifest.ordered_event_hash


@pytest.mark.db
def test_conflicts_fail_and_gap_placeholders_yield_to_valid_evidence(database_url, tmp_path, monkeypatch):
    write_presets(tmp_path, monkeypatch)
    root = tmp_path / "data"
    good = fake()
    gappy = fake(gaps=((EV_START, EV_START + timedelta(minutes=20)),))
    shifted = synthetic_fake(FAKE_START + timedelta(minutes=7), FAKE_END, gap_every=None)  # different values
    g = acquire(root, good, REQ_START, REQ_END)
    gp = acquire(root, gappy, REQ_START, REQ_END)
    sh = acquire(root, shifted, REQ_START, REQ_END)
    tmp = tmp_path / "w"
    tmp.mkdir()
    with connect(database_url) as c:
        cache, st = _compose(c, root, [(gp, REQ_START, REQ_END, "local"), (g, EV_START, EV_END, "local")], tmp)
        assert st.gap_replaced == 20 * 3 and st.counts[("trade_bar_1m", "evaluation")]["missing"] == 0
        with pytest.raises(pk.CompositionConflict, match="different OHLC"):
            _compose(c, root, [(g, REQ_START, REQ_END, "local"), (sh, EV_START, EV_END, "local")], tmp)
    # rejected evidence versus valid evidence is a conflict, not a silent choice
    bad = fake()
    ms = int((EV_START + timedelta(minutes=5)).timestamp() * 1000)
    bad.mutate(MdFamily.TRADE_CANDLES, lambda rows: [[*r[:2], str(float(r[3]) - 50), *r[3:]] if int(r[0]) == ms
                                                     else r for r in rows])
    b = acquire(root, bad, REQ_START, REQ_END)
    with connect(database_url) as c:
        cache_b, st_b = _compose(c, root, [(b, REQ_START, REQ_END, "local")], tmp)
        assert st_b.counts[("trade_bar_1m", "evaluation")]["reasons"] == {"INVALID_ROW": 1}
        with pytest.raises(pk.CompositionConflict, match="rejected"):
            _compose(c, root, [(b, REQ_START, REQ_END, "local"), (g, EV_START, EV_END, "local")], tmp)
    # sparse funding: identical settlements collapse, no schedule is synthesized
    assert sum(1 for e in _events(cache) if e.channel.family.value == "funding_settlement") == \
        sum(1 for e in _events(cache_b) if e.channel.family.value == "funding_settlement") == 1


@pytest.mark.db
def test_source_boundary_cutoff_perturbation_leaves_the_earlier_feed_unchanged(database_url, tmp_path, monkeypatch):
    write_presets(tmp_path, monkeypatch)
    root = tmp_path / "data"
    f1, f2 = fake(), synthetic_fake(FAKE_START + timedelta(minutes=3), FAKE_END, gap_every=None)
    cut = EV_START + timedelta(hours=2)
    a = acquire(root, f1, REQ_START, cut)
    b1 = acquire(root, f1, cut, REQ_END)
    b2 = acquire(root, f2, cut, REQ_END)  # different evidence strictly after the cut
    tmp = tmp_path / "w"
    tmp.mkdir()
    with connect(database_url) as c:
        x, _ = _compose(c, root, [(a, REQ_START, cut, "local"), (b1, cut, REQ_END, "local")], tmp)
        y, _ = _compose(c, root, [(a, REQ_START, cut, "local"), (b2, cut, REQ_END, "local")], tmp)
    ex, ey = _events(x), _events(y)
    k = max(i for i, e in enumerate(ex) if e.available_time <= cut) + 1
    assert [canonical(e.model_dump(mode="json")) for e in ex[:k]] == [canonical(e.model_dump(mode="json"))
                                                                       for e in ey[:k]]
    tx, ty = (te.for_feed(z.feed_manifest, te.profile_for_feed(z.feed_manifest)) for z in (x, y))
    for i in range(k):
        tx.on_event(ex[i], i)
        ty.on_event(ey[i], i)
    # identical sealed aggregates/known-at/barriers before the cut (identities that embed the whole feed's content
    # fingerprint legitimately differ and are excluded)
    assert tx.aggregate_chain == ty.aggregate_chain and tx.counters == ty.counters and tx.cursor == ty.cursor


# ---------------------------------------------------------------------------
# E. Continuity, controls, restore, Deep terminal
# ---------------------------------------------------------------------------


def crash_once_after(rid, at):
    fired = {"done": False}

    def hook(replay_id, cursor):
        if replay_id == rid and cursor >= at and not fired["done"]:
            fired["done"] = True
            raise SimulatedCrash()
    return hook


@pytest.mark.db
def test_continuous_pack_replay_equals_the_single_source_and_survives_step_crash_and_fallback(
        database_url, tmp_path, monkeypatch):
    write_presets(tmp_path, monkeypatch)
    root = tmp_path / "data"
    f = fake()
    month_cut = datetime(2026, 9, 1, tzinfo=UTC)  # local sources split exactly at the UTC month boundary
    acquire(root, f, EV_START, month_cut)
    acquire(root, f, month_cut, EV_END)
    job = _prepare(database_url, root, f)
    pack_id = job["pack_id"]
    doc = pk.open_pack(root, pack_id, pk.pack_receipt(connect(database_url), pack_id))
    assert [T(s["end"]) for s in doc["sources"]][:3] == [EV_START, month_cut, EV_END]
    single = acquire(root, f, REQ_START, REQ_END)
    with connect(database_url) as c:
        srid = control.create_replay(c, root, SourceKind.DATASET, single, 0, False)
    w = ObservationWorker(database_url, root, tmp_path / "art", worker_id="observe:s", isolate=False,
                          sleep=lambda s: None, lease_seconds=5, poll_interval=0.01, checkpoint_events=500)
    while w.run_once():
        pass
    with connect(database_url) as c:
        s = c.execute("SELECT * FROM observation_replays WHERE replay_id = %s", (srid,)).fetchone()
        last_s = c.execute("SELECT aggregate_chain FROM observation_ranges WHERE replay_id = %s ORDER BY to_cursor "
                           "DESC LIMIT 1", (srid,)).fetchone()
    assert s["config"]["feed"]["content_identity"] == doc["feed"]["content_identity"]
    base = _replay(database_url, root, pack_id)
    assert base["status"] == "completed", base["error"]
    with connect(database_url) as c:
        last_p = c.execute("SELECT aggregate_chain FROM observation_ranges WHERE replay_id = %s ORDER BY to_cursor "
                           "DESC LIMIT 1", (base["replay_id"],)).fetchone()
    # same temporal records as one uninterrupted single-source feed: no intermediate finish/reset at the boundaries
    assert last_p["aggregate_chain"] == last_s["aggregate_chain"]
    assert base["manifest"]["temporal"]["aggregate_chain"] == s["manifest"]["temporal"]["aggregate_chain"]
    # STEP across the cross-source tie at the month boundary, then pause/resume; crash after a commit + fallback
    with connect(database_url) as c:
        rid = control.create_replay(c, root, SourceKind.PACK, pack_id, 0, True,
                                    expected_manifest_sha256=doc["_receipt"]["manifest_sha256"]
                                    if "_receipt" in doc else pk.pack_receipt(c, pack_id)["manifest_sha256"])
    w2 = ObservationWorker(database_url, root, tmp_path / "art", worker_id="observe:x", isolate=False,
                           sleep=lambda s: None, lease_seconds=5, poll_interval=0.01, checkpoint_events=7,
                           after_commit=crash_once_after(rid, 700))
    while w2.run_once():
        pass
    with connect(database_url) as c:
        for _ in range(5):
            control.step(c, rid)
            while w2.run_once():
                pass
        c.execute("UPDATE observation_restore_points SET temporal_blob = 'x'::bytea WHERE replay_id = %s AND cursor = "
                  "(SELECT max(cursor) FROM observation_restore_points WHERE replay_id = %s)", (rid, rid))
        control.resume(c, rid)
    with pytest.raises(SimulatedCrash):
        while w2.run_once():
            pass
    with connect(database_url) as c:
        c.execute("UPDATE observation_replays SET lease_expires_at = now() - interval '1 second' WHERE replay_id = %s",
                  (rid,))
    w3 = ObservationWorker(database_url, root, tmp_path / "art", worker_id="observe:y", isolate=False,
                           sleep=lambda s: None, lease_seconds=5, poll_interval=0.01, checkpoint_events=50)
    while w3.run_once():
        pass
    with connect(database_url) as c:
        r = c.execute("SELECT * FROM observation_replays WHERE replay_id = %s", (rid,)).fetchone()
    assert r["status"] == "completed", r["error"]
    assert r["manifest"]["temporal"]["aggregate_chain"] == base["manifest"]["temporal"]["aggregate_chain"]
    assert r["manifest"]["final_content_digest"] == base["manifest"]["final_content_digest"]
    assert any(e["event"] == "restore_point_rejected" for e in r["diagnostic_log"])  # fallback was exercised
    # paced execution (pacing sleeps are no-ops here) commits the same outputs as max speed
    with connect(database_url) as c:
        prid = control.create_replay(c, root, SourceKind.PACK, pack_id, 400, False,
                                     expected_manifest_sha256=pk.pack_receipt(c, pack_id)["manifest_sha256"])
    w4 = ObservationWorker(database_url, root, tmp_path / "art", worker_id="observe:paced", isolate=False,
                           sleep=lambda s: None, lease_seconds=5, poll_interval=0.01, checkpoint_events=13)
    while w4.run_once():
        pass
    with connect(database_url) as c:
        pr = c.execute("SELECT * FROM observation_replays WHERE replay_id = %s", (prid,)).fetchone()
    assert pr["status"] == "completed" and pr["manifest"]["final_content_digest"] == base["manifest"]["final_content_digest"]
    assert pr["manifest"]["temporal"]["dispatch_commitment"] == base["manifest"]["temporal"]["dispatch_commitment"]
    # Deep v3 on the pack run includes the final clock-end finish; tampering only the finished output is detected
    with connect(database_url) as c:
        vid = deep.create_deep_validation(c, base["replay_id"])
    while w3.run_once():
        pass
    with connect(database_url) as c:
        d = c.execute("SELECT * FROM observation_deep_validations WHERE validation_id = %s", (vid,)).fetchone()
    assert d["result"]["outcome"] == "match" and d["result"]["temporal"]["terminal"]["compared"], d["result"]


# ---------------------------------------------------------------------------
# F. Scope: never certifying absent evidence
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_capability_scope_is_honest_about_metadata_funding_calendar_and_gaps(database_url, tmp_path, monkeypatch):
    f = fake(gap_every=None, gaps=((EV_START + timedelta(minutes=30), EV_START + timedelta(minutes=33)),))
    f.rows[MdFamily.FUNDING] = []  # an empty funding response is not proof of zero settlements
    root, pack_id, _ = _published(database_url, tmp_path, monkeypatch, f)
    with connect(database_url) as c:
        doc = pk.open_pack(root, pack_id, pk.pack_receipt(c, pack_id))
    caps = {x["capability"]: x for x in doc["capabilities"]}
    assert caps["funding_settlements"]["status"] == "EMPTY_UNKNOWN"
    assert caps["instrument_metadata"]["status"] == "PINNED_RETRIEVAL_SNAPSHOT_ASSUMED_FOR_WINDOW"
    assert "not historical effective-date proof" in caps["instrument_metadata"]["detail"]
    assert caps["event_calendar"]["status"] == "NONE_UNKNOWN" and caps["incident_tape"]["status"] == "NOT_COVERED"
    assert caps["trade_1m"]["status"] == "OBSERVED_WITH_GAPS" and caps["source_capability_probes"]["status"] == \
        "NOT_PROBED"
    assert doc["status"] == "READY_WITH_LIMITATIONS"
    assert any("WITH GAPS, not complete market coverage" in x for x in doc["limitations"])
    assert any("PRICE_NET_ONLY" in x for x in doc["limitations"])
    assert doc["evidence_classes"]["certified_uncontaminated"] is False
    assert doc["instrument"]["policy"] == "PINNED_RETRIEVAL_SNAPSHOT_ASSUMED_FOR_WINDOW"
    ev = [x for x in doc["coverage"] if x["family"] == "trade_bar_1m" and x["window"] == "evaluation"][0]
    assert (ev["missing"], ev["valid"] + ev["missing"] + ev["rejected"]) == (3, ev["expected_slots"])
    # optional reference gaps never veto the trade core
    f2 = fake()
    f2.mutate(MdFamily.MARK_CANDLES, lambda rows: [r for r in rows if not
                                                   int(EV_START.timestamp() * 1000) <= int(r[0]) <
                                                   int((EV_START + timedelta(minutes=10)).timestamp() * 1000)])
    tmp2 = tmp_path / "b"
    tmp2.mkdir()
    with connect(database_url) as c:
        c.execute("DELETE FROM corpus_packs")
    write_presets(tmp2, monkeypatch)
    job = _prepare(database_url, tmp2 / "data", f2)
    with connect(database_url) as c:
        d2 = pk.open_pack(tmp2 / "data", job["pack_id"], pk.pack_receipt(c, job["pack_id"]))
    caps2 = {x["capability"]: x for x in d2["capabilities"]}
    assert caps2["trade_1m"]["status"] == "OBSERVED_COMPLETE"
    assert caps2["mark_1m"]["status"].endswith("OBSERVED_WITH_GAPS") and "never a veto" in caps2["mark_1m"]["detail"]
    assert d2["input_readiness_preview"]["trade_15m_contiguous_complete"] == 8  # 2 h warmup / 15 m, unaffected


@pytest.mark.db
def test_pack_evaluation_requires_acknowledgement_for_gaps_and_reports_no_adviser_metric(database_url, tmp_path,
                                                                                       monkeypatch):
    from fastapi.testclient import TestClient

    from algotrader.api import create_app

    f = fake(gap_every=None, gaps=((EV_START, EV_START + timedelta(minutes=2)),))
    root, pack_id, _ = _published(database_url, tmp_path, monkeypatch, f)
    monkeypatch.setenv("ALGOTRADER_DATA_ROOT", str(root))
    app = create_app(database_url, tmp_path / "art", web_dist=tmp_path / "no-ui", data_root=root)
    with TestClient(app) as api:
        r = api.post("/api/evaluations", json={"pack_id": pack_id, "speed": 0})
        assert r.status_code == 409 and "acknowledge" in r.text
        r = api.post("/api/evaluations", json={"pack_id": pack_id, "speed": 0, "acknowledge_limitations": True})
        assert r.status_code == 201, r.text
        ev = r.json()
        assert ev["corpus"]["pack"]["acknowledged_limitations"] is True
        presets = api.get("/api/corpus/presets").json()
        assert presets["presets"][0]["published"]["pack_id"] == pack_id and presets["note"].startswith("Opening")
        assert api.get("/api/corpus/selection", params={"months": "2026-09,2026-08"}).status_code == 422
    w = ObservationWorker(database_url, root, tmp_path / "art", worker_id="observe:e", isolate=False,
                          sleep=lambda s: None, lease_seconds=5, poll_interval=0.01)
    while w.run_once():
        pass
    with TestClient(app) as api:
        rep = api.get(f"/api/evaluations/{ev['evaluation_id']}/report.json").json()
        md_text = api.get(f"/api/evaluations/{ev['evaluation_id']}/report.md").text
    assert rep["pack"]["feed_consumed"] == "entirely" and rep["pack"]["source_coverage"]["missing_or_rejected"] == 6
    assert all(v["value"] is None and v["status"] == "UNAVAILABLE" for k, v in rep["capabilities"].items()
               if k != "professional_adviser")
    assert "## Evaluation pack (observation only; no adviser)" in md_text and "129600" not in md_text
    assert "warmup and tail are never scored" in md_text
