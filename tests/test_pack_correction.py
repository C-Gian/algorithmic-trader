"""WP-008-R3 correction evidence (Director review findings 1-3), through real pack preparation/publication.

1. Contributor facts come only from manifest bytes bound to the verified manifest SHA-256: cold, warm and pinned
   rebuild mutations after source verification fail visibly; tampered facts are never published as verified.
2. Publication re-hashes ACTUAL staged and published bytes against their pins under the publication boundary, persists
   the staging and final directory entries (fsync order spied) before the receipt; altered bytes never receive a
   trusted publication.
3. Staging is owned by one job attempt (``packs/.staging/<job>/g<generation>``); concurrent jobs/workers and reclaim
   never delete another live attempt's staging; only positively abandoned staging is removed.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import timedelta
from pathlib import Path

import pytest
from pack_fixtures import EV_END, EV_START, acquire, connect, corpus_worker, drain, fake, presets_doc

from algotrader.corpus import pack as pk
from algotrader.corpus import pack_job as pj
from algotrader.corpus import presets as ps
from algotrader.marketdata import dataset as md
from algotrader.observe import control
from algotrader.observe import feedcache as fc
from algotrader.observe import sources as obs_sources
from algotrader.observe.contracts import SourceKind
from algotrader.observe.job import SimulatedCrash
from algotrader.observe.worker import ObservationWorker

ISO = lambda t: t.isoformat().replace("+00:00", "Z")  # noqa: E731


def presets_with_second(tmp_path: Path, monkeypatch) -> Path:
    """Default tiny preset plus a second one (same start, evaluation one hour shorter) for concurrent jobs."""
    ev2 = EV_END - timedelta(hours=1)
    second = {"preset_id": "tiny-short-v1", "label": "Tiny short", "default": False,
              "warmup": {"start": ISO(EV_START - timedelta(hours=2)), "end": ISO(EV_START)},
              "evaluation": {"start": ISO(EV_START), "end": ISO(ev2)},
              "tail": {"start": ISO(ev2), "end": ISO(ev2 + timedelta(minutes=30))},
              "evidence_class": "DEVELOPMENT", "adviser_implemented": False, "automatic_prepare": False}
    p = tmp_path / "presets.json"
    p.write_text(json.dumps(presets_doc(extra=[second])), encoding="utf-8")
    monkeypatch.setenv("ALGOTRADER_CORPUS_PRESETS", str(p))
    return p


def create(database_url, preset_id: str | None = None) -> str:
    with connect(database_url) as c:
        f = ps.load_presets()
        return pj.create_pack_job(c, f, f.preset(preset_id) if preset_id else f.default)


def job(database_url, jid):
    with connect(database_url) as c:
        return c.execute("SELECT * FROM corpus_pack_jobs WHERE job_id = %s", (jid,)).fetchone()


def n_receipts(database_url) -> int:
    with connect(database_url) as c:
        return c.execute("SELECT count(*) AS n FROM corpus_packs").fetchone()["n"]


def published_dirs(root: Path) -> list[str]:
    r = pk.packs_root(root)
    return sorted(p.name for p in r.iterdir() if not p.name.startswith(".")) if r.is_dir() else []


def mutate_manifest(path: Path, what: str) -> None:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if what == "tick":
        doc["instrument"]["tick_sz"] = "0.5"
    elif what == "request":
        doc["request"]["page_limit"] = 99
    else:
        doc["files"][0]["bytes"] += 1
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")


def mutate_after_verification(monkeypatch, root: Path, what: str, only: set | None = None, seen: list | None = None):
    """Mutate the ORIGINAL source manifest right after the accepted source boundary returned (cold or warm)."""
    real = obs_sources.prepare_stream_source

    def wrapper(data_root, kind, source_id, **kw):
        prep = real(data_root, kind, source_id, **kw)
        if seen is not None:
            seen.append((source_id, prep.warm))
        if only is None or source_id in only:
            mutate_manifest(md.dataset_path(root, source_id) / "manifest.json", what)
        return prep

    monkeypatch.setattr(obs_sources, "prepare_stream_source", wrapper)


# ---------------------------------------------------------------------------
# Finding 1 - verified ownership of contributor facts
# ---------------------------------------------------------------------------


@pytest.mark.db
@pytest.mark.parametrize("what", ["tick", "request", "files"])
def test_cold_post_verification_manifest_mutation_is_rejected_never_published(database_url, tmp_path, monkeypatch,
                                                                               what):
    presets_with_second(tmp_path, monkeypatch)
    root = tmp_path / "data"
    f = fake()
    local = acquire(root, f, EV_START, EV_END)
    seen: list = []
    mutate_after_verification(monkeypatch, root, what, only={local}, seen=seen)
    jid = create(database_url)
    drain(corpus_worker(database_url, root, f))
    row = job(database_url, jid)
    assert ("local" if False else local, False) in seen  # cold: the cache was built from a verified snapshot
    assert row["status"] == "failed" and "changed after verification" in row["error"], row["error"]
    assert n_receipts(database_url) == 0 and published_dirs(root) == []


@pytest.mark.db
def test_warm_reuse_mutation_fails_and_unchanged_sources_reproduce_the_same_pack(database_url, tmp_path,
                                                                                 monkeypatch):
    presets_with_second(tmp_path, monkeypatch)
    root = tmp_path / "data"
    f = fake()
    local = acquire(root, f, EV_START, EV_END)
    jid = create(database_url)
    drain(corpus_worker(database_url, root, f))
    first = job(database_url, jid)
    assert first["status"] == "completed"
    doc = pk.open_pack(root, first["pack_id"], pk.pack_receipt(connect(database_url), first["pack_id"]))
    tick = doc["instrument"]["definition"]["tick_sz"]
    # force recomposition over WARM receipt-pinned source caches
    with connect(database_url) as c:
        c.execute("DELETE FROM corpus_packs")
    shutil.rmtree(pk.packs_root(root) / first["pack_id"])
    mpath = md.dataset_path(root, local) / "manifest.json"
    original = mpath.read_bytes()
    seen: list = []
    mutate_after_verification(monkeypatch, root, "tick", only={local}, seen=seen)
    jid2 = create(database_url)
    drain(corpus_worker(database_url, root, f))
    second = job(database_url, jid2)
    assert (local, True) in seen  # warm path really exercised
    assert second["status"] == "failed" and "changed after verification" in second["error"]
    assert n_receipts(database_url) == 0 and published_dirs(root) == []
    # unchanged source: success with the original verified facts and the identical pack id
    monkeypatch.undo()
    presets_with_second(tmp_path, monkeypatch)
    mpath.write_bytes(original)
    jid3 = create(database_url)
    drain(corpus_worker(database_url, root, f))
    third = job(database_url, jid3)
    assert third["status"] == "completed" and third["pack_id"] == first["pack_id"]
    doc3 = pk.open_pack(root, third["pack_id"], pk.pack_receipt(connect(database_url), third["pack_id"]))
    assert doc3["instrument"]["definition"]["tick_sz"] == tick


@pytest.mark.db
def test_pinned_rebuild_rejects_a_post_verification_mutation(database_url, tmp_path, monkeypatch):
    presets_with_second(tmp_path, monkeypatch)
    root = tmp_path / "data"
    f = fake()
    local = acquire(root, f, EV_START, EV_END)
    jid = create(database_url)
    drain(corpus_worker(database_url, root, f))
    pack_id = job(database_url, jid)["pack_id"]
    doc = pk.open_pack(root, pack_id, pk.pack_receipt(connect(database_url), pack_id))
    shutil.rmtree(fc.cache_root(root) / doc["feed"]["cache_id"])  # lost pack cache -> pinned rebuild
    mutate_after_verification(monkeypatch, root, "tick", only={local})
    with connect(database_url) as c:
        rid = control.create_replay(c, root, SourceKind.PACK, pack_id, 0, False,
                                    expected_manifest_sha256=pk.pack_receipt(c, pack_id)["manifest_sha256"])
    w = ObservationWorker(database_url, root, tmp_path / "art", worker_id="observe:rb", isolate=False,
                          sleep=lambda s: None, lease_seconds=5, poll_interval=0.01)
    while w.run_once():
        pass
    with connect(database_url) as c:
        r = c.execute("SELECT status, error FROM observation_replays WHERE replay_id = %s", (rid,)).fetchone()
    assert r["status"] == "failed" and "could not be rebuilt" in r["error"] and "after verification" in r["error"]


# ---------------------------------------------------------------------------
# Finding 2 - actual-byte validation and directory durability before the receipt
# ---------------------------------------------------------------------------


def _staged(root: Path) -> list[Path]:
    s = pk.staging_root(root)
    return sorted(s.glob("*/g*/*")) if s.is_dir() else []


@pytest.mark.db
@pytest.mark.parametrize("stage", ["before_publish_lock", "renamed_before_check"])
def test_altered_staged_or_published_manifest_never_gets_a_trusted_publication(database_url, tmp_path, monkeypatch,
                                                                                stage):
    presets_with_second(tmp_path, monkeypatch)
    root = tmp_path / "data"
    f = fake()

    def fault(s):
        if s != stage:
            return
        target = _staged(root)[0] if stage == "before_publish_lock" else \
            pk.packs_root(root) / published_dirs(root)[0]
        m = target / "manifest.json"
        m.write_bytes(m.read_bytes().replace(b'"status"', b'"status" ', 1))  # same JSON, other bytes

    jid = create(database_url)
    drain(corpus_worker(database_url, root, f, pack_fault=fault))
    row = job(database_url, jid)
    assert row["status"] == "failed" and ("changed before publication" in row["error"]
                                          or "differ from their pins after the rename" in row["error"]), row["error"]
    assert n_receipts(database_url) == 0 and published_dirs(root) == [] and _staged(root) == []
    if stage == "renamed_before_check":  # the bad published bytes were moved aside as evidence, never deleted
        assert list(pk.packs_root(root).glob(".invalid-pack-*"))
    jid2 = create(database_url)  # a later Prepare publishes the verified pack
    drain(corpus_worker(database_url, root, f))
    ok = job(database_url, jid2)
    assert ok["status"] == "completed" and n_receipts(database_url) == 1
    pk.open_pack(root, ok["pack_id"], pk.pack_receipt(connect(database_url), ok["pack_id"]))


def test_provenance_bytes_are_checked_at_staging_publication_and_convergence(tmp_path):
    root = tmp_path / "data"
    prov = tmp_path / "prov.jsonl"
    prov.write_text('{"slot": "x"}\n', encoding="utf-8")
    psha = hashlib.sha256(prov.read_bytes()).hexdigest()
    body = {"overlap": {"provenance_file": "provenance.jsonl", "provenance_sha256": psha}, "x": 1}
    doc = {**body, "pack_id": pk.pack_id_for(body)}
    st = pk.stage_pack(root, doc, prov, "job-a", 1)
    (st / "provenance.jsonl").write_text('{"slot": "y"}\n', encoding="utf-8")
    with pytest.raises(pk.PackError, match="changed before publication"):
        pk.publish_staged(root, doc, st)
    assert not (pk.packs_root(root) / doc["pack_id"]).exists() and not st.exists()

    def after_rename(stage):
        (pk.packs_root(root) / doc["pack_id"] / "provenance.jsonl").write_text("{}\n", encoding="utf-8")

    st = pk.stage_pack(root, doc, prov, "job-a", 1)
    with pytest.raises(pk.PackError, match="after the rename"):
        pk.publish_staged(root, doc, st, fault=after_rename)
    assert not (pk.packs_root(root) / doc["pack_id"]).exists()
    assert list(pk.packs_root(root).glob(f".invalid-{doc['pack_id']}-*"))
    st = pk.stage_pack(root, doc, prov, "job-a", 1)
    assert pk.publish_staged(root, doc, st) == "published"
    st = pk.stage_pack(root, doc, prov, "job-b", 1)  # identical verified bytes converge
    assert pk.publish_staged(root, doc, st) == "converged" and not st.exists()
    (pk.packs_root(root) / doc["pack_id"] / "provenance.jsonl").write_text("{}\n", encoding="utf-8")
    st = pk.stage_pack(root, doc, prov, "job-c", 1)  # an altered destination is quarantined, never trusted
    assert pk.publish_staged(root, doc, st) == "published_after_quarantine"
    assert pk.check_files(pk.packs_root(root) / doc["pack_id"], pk.expected_files(doc)) == []


@pytest.mark.db
def test_fsync_order_files_then_staging_dir_then_final_and_parent_before_the_receipt(database_url, tmp_path,
                                                                                     monkeypatch):
    presets_with_second(tmp_path, monkeypatch)
    root = tmp_path / "data"
    f = fake()
    events: list[tuple[str, str]] = []
    real_file, real_dir = fc._fsync_file, fc._fsync_dir
    monkeypatch.setattr(fc, "_fsync_file", lambda p: (events.append(("file", str(p))), real_file(p))[1])
    monkeypatch.setattr(fc, "_fsync_dir", lambda p: (events.append(("dir", str(p))), real_dir(p))[1])

    def fault(s):
        if s == "after_rename":
            events.append(("receipt_next", ""))

    jid = create(database_url)
    drain(corpus_worker(database_url, root, f, pack_fault=fault))
    row = job(database_url, jid)
    assert row["status"] == "completed"
    pid = row["pack_id"]
    final, parent = str(pk.packs_root(root) / pid), str(pk.packs_root(root))
    idx = {k: i for i, k in enumerate(events)}
    staged_manifest = next(i for i, (k, p) in enumerate(events) if k == "file" and p.endswith("manifest.json")
                           and ".staging" in p)
    staged_dir = next(i for i, (k, p) in enumerate(events) if k == "dir" and ".staging" in p and p.endswith(
        Path(events[staged_manifest][1]).parent.name))
    final_dir = next(i for i, (k, p) in enumerate(events) if k == "dir" and p == final)
    parent_dir = next(i for i, (k, p) in enumerate(events) if k == "dir" and p == parent and i > final_dir)
    receipt = idx[("receipt_next", "")]
    assert staged_manifest < staged_dir < final_dir < parent_dir < receipt


# ---------------------------------------------------------------------------
# Finding 3 - staging ownership under concurrency and reclaim
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_concurrent_jobs_and_cancellation_never_delete_another_live_staging(database_url, tmp_path, monkeypatch):
    presets_with_second(tmp_path, monkeypatch)
    root = tmp_path / "data"
    f = fake()
    a = create(database_url)
    b = create(database_url, "tiny-short-v1")
    seen = {}

    def fault_a(stage):  # worker A has staged; worker B now runs job B entirely (startup cleanup included)
        if stage == "before_publish_lock" and "b" not in seen:
            seen["a_staged"] = [str(p) for p in _staged(root)]
            seen["b"] = True
            drain(corpus_worker(database_url, root, f, worker_id="corpus:B"))
            seen["a_after_b"] = all(Path(p).exists() for p in seen["a_staged"])

    w_a = corpus_worker(database_url, root, f, worker_id="corpus:A", pack_fault=fault_a)
    w_a.run_once()  # claims job A (oldest)
    drain(w_a)
    assert seen["a_staged"] and seen["a_after_b"], seen
    ra, rb = job(database_url, a), job(database_url, b)
    assert ra["status"] == rb["status"] == "completed" and ra["pack_id"] != rb["pack_id"]
    assert n_receipts(database_url) == 2 and _staged(root) == []
    # a cancellation removes only its own unpublished staging while another job's staging is live
    with connect(database_url) as c:
        c.execute("DELETE FROM corpus_packs")
    for d in published_dirs(root):
        shutil.rmtree(pk.packs_root(root) / d)
    c2, d2 = create(database_url), create(database_url, "tiny-short-v1")
    state = {}

    def fault_c(stage):
        if stage == "before_publish_lock" and "inner" not in state:
            state["inner"] = True
            state["c_staged"] = [str(p) for p in _staged(root)]

            def fault_d(s):  # job D cancels at its publication boundary while job C's staging exists
                if s == "before_publish_lock":
                    with connect(database_url) as c:
                        c.execute("UPDATE corpus_pack_jobs SET cancel_requested = true WHERE job_id = %s", (d2,))
            drain(corpus_worker(database_url, root, f, worker_id="corpus:D", pack_fault=fault_d))
            state["c_alive"] = all(Path(p).exists() for p in state["c_staged"])
            state["after_cancel"] = [str(p) for p in _staged(root)]

    drain(corpus_worker(database_url, root, f, worker_id="corpus:C", pack_fault=fault_c))
    assert job(database_url, d2)["status"] == "cancelled" and job(database_url, c2)["status"] == "completed"
    assert state["c_alive"] and state["after_cancel"] == state["c_staged"]


@pytest.mark.db
def test_reclaim_removes_only_its_own_fenced_out_staging_and_terminal_leftovers(database_url, tmp_path, monkeypatch):
    presets_with_second(tmp_path, monkeypatch)
    root = tmp_path / "data"
    f = fake()
    a = create(database_url)

    def crash(stage):
        if stage == "before_publish_lock":
            raise SimulatedCrash(stage)

    with pytest.raises(SimulatedCrash):
        corpus_worker(database_url, root, f, worker_id="corpus:A1", pack_fault=crash).run_once()
    a_g1 = pk.staging_dir(root, a, 1)
    assert a_g1.is_dir() and any(a_g1.iterdir())  # the dead attempt's staging is still there
    # leftovers of a job that is already terminal are positively abandoned
    dead = pk.staging_dir(root, "pack-job-terminal-x", 3)
    dead.mkdir(parents=True)
    (dead / "manifest.json").write_text("{}", encoding="utf-8")
    with connect(database_url) as c:
        c.execute("""INSERT INTO corpus_pack_jobs (job_id, preset_id, preset, preset_sha256, status, base_url)
                     VALUES ('pack-job-terminal-x', 'x', '{}'::jsonb, 'x', 'failed', 'https://www.okx.com')""")
    # another live job runs meanwhile: it must not remove job A's generation-1 staging (A's row is still running)
    b = create(database_url, "tiny-short-v1")
    drain(corpus_worker(database_url, root, f, worker_id="corpus:B"))
    assert job(database_url, b)["status"] == "completed"
    assert a_g1.is_dir() and any(a_g1.iterdir()) and not dead.exists()
    with connect(database_url) as c:
        c.execute("UPDATE corpus_pack_jobs SET lease_expires_at = now() - interval '1 second' WHERE job_id = %s", (a,))
    drain(corpus_worker(database_url, root, f, worker_id="corpus:A2"))
    ra = job(database_url, a)
    assert ra["status"] == "completed" and ra["lease_generation"] == 2
    assert not a_g1.exists()  # removed by its own newer generation (fenced out, positively abandoned)
    assert {"event": "abandoned_staging_removed", "detail": f"{a}/g1"} in ra["diagnostic_log"]
    assert _staged(root) == []
