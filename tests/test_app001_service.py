"""APP-001: servizio locale, job, avanzamento, annullamento, catalogo e confini HTTP.

Dati sintetici (app001_helpers): archivi inventati, percorso reale del motore (cand001.pipeline).
Nessuna pausa artificiale nel percorso produttivo: i test bloccano o annullano tramite runner/eventi
iniettati nei punti di controllo reali.
"""

import http.client
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from trading_primitives.file_lock import FileLock

from app001.catalog import Catalog
from app001.jobs import JobManager, StartRefused, write_json_atomic
from app001.server import App, make_server
from cand001.pipeline import Cancelled, Events, execute

from app001_helpers import CAND, PROFILE, PROFILES, clean, make_data_dir

ORIGIN = "http://127.0.0.1:5173"


def wait_terminal(manager, job_id, timeout=30.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        job = manager.get(job_id)
        if job["state"] in ("COMPLETED", "INCOMPLETE", "CANCELLED", "INTERRUPTED", "FAILED"):
            return job
        time.sleep(0.02)
    raise AssertionError(f"job {job_id} non concluso: {manager.get(job_id)['state']}")


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(clean, self.tmp)

    def manager(self, root, runner=execute, **kw):
        m = JobManager(CAND, PROFILES, root, runner=runner, **kw)
        self.addCleanup(m.shutdown, 2.0)
        return m


class Blocking:
    """Runner che resta attivo finché il test non lo rilascia (per concorrenza e arresto)."""

    def __init__(self):
        self.release = threading.Event()
        self.entered = threading.Event()

    def __call__(self, cand, data_dir, profile, events, **kw):
        self.entered.set()
        while not self.release.wait(0.01):
            events.tick("save", step="attesa di test")  # punto di controllo reale: annullamento e arresto
        raise RuntimeError("runner di test rilasciato senza risultato")


class TestStartAndIdempotency(Base):
    def test_two_simultaneous_starts_create_one_job(self):
        root = make_data_dir(self.tmp)
        run = Blocking()
        m = self.manager(root, runner=run)
        barrier = threading.Barrier(2)
        out = []

        def click(key):
            barrier.wait()
            try:
                out.append(("ok",) + m.start(PROFILE.id, key))
            except StartRefused as e:
                out.append(("refused", e.code, e.job))

        threads = [threading.Thread(target=click, args=(k,)) for k in ("tab-one-aaaa", "tab-two-bbbb")]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        created = [o for o in out if o[0] == "ok" and o[2]]
        refused = [o for o in out if o[0] == "refused"]
        self.assertEqual(len(created), 1)
        self.assertEqual(refused[0][1], "ACTIVE_JOB_EXISTS")
        self.assertEqual(refused[0][2]["jobId"], created[0][1]["jobId"])  # rimanda al job in corso
        self.assertEqual(len(list((root / "jobs").glob("job-*"))), 1)
        run.release.set()

    def test_retry_same_key_returns_same_job_even_after_end(self):
        root = make_data_dir(self.tmp)
        m = self.manager(root)
        job, created = m.start(PROFILE.id, "click-1234567")
        self.assertTrue(created)
        again, created2 = m.start(PROFILE.id, "click-1234567")  # risposta persa, stesso clic
        self.assertFalse(created2)
        self.assertEqual(again["jobId"], job["jobId"])
        done = wait_terminal(m, job["jobId"])
        self.assertEqual(done["state"], "COMPLETED")
        after, created3 = m.start(PROFILE.id, "click-1234567")
        self.assertFalse(created3)
        self.assertEqual(after["jobId"], job["jobId"])
        self.assertEqual(after["state"], "COMPLETED")
        new, created4 = m.start(PROFILE.id, "click-new-99999")  # nuovo ricalcolo: nuovo avvio esplicito
        self.assertTrue(created4)
        self.assertNotEqual(new["jobId"], job["jobId"])
        wait_terminal(m, new["jobId"])
        with self.assertRaises(StartRefused) as ctx:
            m.start("OTHER", "click-1234567")
        self.assertEqual(ctx.exception.code, "PROFILE_NOT_ALLOWED")

    def test_same_bundle_two_executions_keep_own_provenance(self):
        root = make_data_dir(self.tmp)
        m = self.manager(root)
        a = wait_terminal(m, m.start(PROFILE.id, "first-run-0001")[0]["jobId"])
        b = wait_terminal(m, m.start(PROFILE.id, "second-run-0002")[0]["jobId"])
        self.assertEqual(a["result"]["resultId"], b["result"]["resultId"])
        self.assertEqual(a["result"]["bundleSha256"], b["result"]["bundleSha256"])
        self.assertFalse(a["result"]["reusedIdenticalBundle"])
        self.assertTrue(b["result"]["reusedIdenticalBundle"])
        self.assertNotEqual(a["startedAt"], b["startedAt"])
        bundle = (root / "runs" / a["result"]["resultId"] / "cand001-bundle.json").read_text(encoding="utf-8")
        for s in (a["jobId"], b["jobId"], "startedAt", "serverTime"):
            self.assertNotIn(s, bundle)  # date, job e progresso fuori dal contenuto deterministico

    def test_worker_lock_held_by_direct_command(self):
        root = make_data_dir(self.tmp)
        (root / "jobs").mkdir(exist_ok=True)
        other = FileLock(root / "jobs" / "worker.lock")  # come il comando diretto in corso
        self.assertTrue(other.acquire())
        self.addCleanup(other.release)
        m = self.manager(root)
        with self.assertRaises(StartRefused) as ctx:
            m.start(PROFILE.id, "blocked-by-cli-1")
        self.assertEqual(ctx.exception.code, "WORKER_BUSY")
        self.assertEqual(list((root / "jobs").glob("job-*")), [])

    def test_second_service_lock_refused(self):
        root = make_data_dir(self.tmp)
        (root / "jobs").mkdir(exist_ok=True)
        a, b = FileLock(root / "jobs" / "service.lock"), FileLock(root / "jobs" / "service.lock")
        self.assertTrue(a.acquire())
        self.assertFalse(b.acquire())
        a.release()
        self.assertTrue(b.acquire())
        b.release()


class Recorder(Events):
    """Inoltra al JobEvents reale e registra le fotografie del job a ogni evento."""

    def __init__(self, inner, manager, job_id, on=None):
        self.inner, self.m, self.job_id, self.on = inner, manager, job_id, on
        self.snaps = []

    def _snap(self):
        self.snaps.append(json.loads(json.dumps(self.m._jobs[self.job_id]["progress"])))

    def stage(self, name, **info):
        self.inner.stage(name, **info)
        self._snap()

    def tick(self, name, **info):
        if self.on:
            self.on(name, info)
        self.inner.tick(name, **info)
        self._snap()

    def publishing(self):
        self.inner.publishing()
        if self.on:
            self.on("published", {})

    def log(self, message):
        self.inner.log(message)


class TestProgressAndCancel(Base):
    def run_with(self, root, on=None):
        holder = {}

        def runner(cand, data_dir, profile, events, **kw):
            rec = Recorder(events, holder["m"], events.job["jobId"], on=(lambda n, i: on(holder["m"], events.job["jobId"], n, i)) if on else None)
            holder["rec"] = rec
            return execute(cand, data_dir, profile, rec, **kw)

        m = holder["m"] = self.manager(root, runner=runner)
        job = wait_terminal(m, m.start(PROFILE.id, "progress-0001")[0]["jobId"])
        return m, job, holder["rec"]

    def test_progress_from_engine_monotonic_and_not_anticipated(self):
        root = make_data_dir(self.tmp)
        m, job, rec = self.run_with(root)
        self.assertEqual(job["state"], "COMPLETED")
        snaps = rec.snaps
        first_sim = next(i for i, s in enumerate(snaps) if s["stages"]["simulate"]["closes"] is not None)
        for s in snaps[:first_sim]:
            sim = s["stages"]["simulate"]
            for k in ("closes", "requests", "tradesClosed", "t"):
                self.assertIsNone(sim[k], "conteggio mostrato prima di essere calcolato")
        sim = [s["stages"]["simulate"] for s in snaps[first_sim:]]
        for a, b in zip(sim, sim[1:]):
            for k in ("closes", "t", "requests", "tradesClosed", "episodes"):
                self.assertLessEqual(a[k], b[k])
        self.assertEqual(sim[0]["closes"], 0)
        self.assertEqual(sim[0]["tradesClosed"], 0)  # nessun totale finale anticipato
        self.assertEqual(sim[-1]["closes"], sim[-1]["closesTotal"])
        self.assertEqual(sim[-1]["tradesClosed"], job["result"]["counts"]["trades"])
        files = [s["stages"]["check"]["filesDone"] for s in snaps if s["stages"]["check"]["filesDone"] is not None]
        self.assertEqual(files, sorted(files))
        self.assertEqual(files[-1], 4)
        final = m.get(job["jobId"])["progress"]["stages"]
        self.assertTrue(all(final[s]["status"] == "DONE" for s in ("check", "init", "simulate", "save")))
        self.assertEqual(json.loads((root / "jobs" / job["jobId"] / "job.json").read_text(encoding="utf-8"))["state"], "COMPLETED")

    def cancel_at(self, stage, when=lambda info: True):
        root = make_data_dir(self.tmp)
        asked = {}

        def on(m, job_id, name, info):
            if name == stage and not asked and when(info):
                asked["at"] = time.monotonic()
                asked["outcome"] = m.cancel(job_id)[1]

        m, job, rec = self.run_with(root, on=on)
        return root, job, asked

    def test_cancel_during_check(self):
        root, job, asked = self.cancel_at("check")
        self.assertEqual(asked["outcome"], "REQUESTED")
        self.assertEqual(job["state"], "CANCELLED")
        states = [h["state"] for h in job["stateHistory"]]
        self.assertEqual(states, ["STARTING", "RUNNING", "CANCEL_REQUESTED", "CANCELLED"])
        self.assertIsNone(job["result"])
        self.assertEqual(job["progress"]["stages"]["check"]["status"], "STOPPED")
        self.assertIsNone(job["progress"]["stages"]["simulate"]["closes"])
        self.assertEqual(list((root / "runs").iterdir()), [])  # nessun risultato, nemmeno parziale
        self.assertFalse((root / "jobs" / job["jobId"] / "staging").exists())

    def test_cancel_during_simulation(self):
        root, job, asked = self.cancel_at("simulate", when=lambda info: info["closes"] >= 320)
        self.assertEqual(job["state"], "CANCELLED")
        st = job["progress"]["stages"]
        self.assertEqual(st["check"]["status"], "DONE")
        self.assertEqual(st["simulate"]["status"], "STOPPED")
        self.assertEqual(st["simulate"]["closes"], 288)  # ultimo stato del motore registrato prima dell'annullamento
        self.assertLess(st["simulate"]["closes"], st["simulate"]["closesTotal"])
        self.assertEqual(list((root / "runs").iterdir()), [])

    def test_cancel_after_publication_is_too_late_and_keeps_result(self):
        root = make_data_dir(self.tmp)
        out = {}

        def on(m, job_id, name, info):
            if name == "published":
                out["outcome"] = m.cancel(job_id)[1]

        m, job, rec = self.run_with(root, on=on)
        self.assertEqual(out["outcome"], "TOO_LATE")
        self.assertEqual(job["state"], "COMPLETED")
        self.assertEqual(job["cancel"]["outcome"], "TOO_LATE")
        self.assertTrue((root / "runs" / job["result"]["resultId"] / "run-manifest.json").exists())
        self.assertEqual(m.cancel(job["jobId"])[1], "ALREADY_FINISHED")
        self.assertEqual(m.get(job["jobId"])["state"], "COMPLETED")

    def test_error_and_data_failures_are_not_success(self):
        root = make_data_dir(self.tmp)
        m = self.manager(root, runner=lambda *a, **k: (_ for _ in ()).throw(RuntimeError("guasto di prova")))
        job = wait_terminal(m, m.start(PROFILE.id, "error-run-0001")[0]["jobId"])
        self.assertEqual((job["state"], job["error"]["kind"]), ("FAILED", "INTERNAL"))
        self.assertIsNone(job["result"])
        self.assertTrue((root / "jobs" / job["jobId"] / "error.txt").exists())

        corrupt = make_data_dir(self.tmp / "corrupt")
        (corrupt / "raw" / "trade" / "BTCUSDT-1m-2022-10.zip").write_bytes(b"non e' lo zip registrato")
        m2 = self.manager(corrupt)
        job2 = wait_terminal(m2, m2.start(PROFILE.id, "corrupt-run-001")[0]["jobId"])
        self.assertEqual((job2["state"], job2["error"]["kind"]), ("FAILED", "DATA_MISSING_OR_INVALID"))
        self.assertIn("SHA256", job2["error"]["message"])
        self.assertEqual(list((corrupt / "runs").iterdir()), [])

        badf = make_data_dir(self.tmp / "funding", bad_funding=True)
        m3 = self.manager(badf)
        job3 = wait_terminal(m3, m3.start(PROFILE.id, "funding-run-001")[0]["jobId"])
        self.assertEqual((job3["state"], job3["error"]["kind"]), ("FAILED", "DATA_NOT_CERTIFIED"))
        self.assertTrue((badf / "manifests" / f"input-{PROFILE.id}.json").exists())  # rapporto di qualità conservato
        self.assertEqual(list((badf / "runs").iterdir()), [])


class TestRestartAndShutdown(Base):
    def test_restart_marks_unfinished_job_interrupted(self):
        root = make_data_dir(self.tmp)
        folder = root / "jobs" / "job-20261017T120000Z-abcdef"
        folder.mkdir(parents=True)
        (folder / "staging").mkdir()
        (folder / "staging" / "cand001-bundle.json").write_text("{parziale", encoding="utf-8")
        write_json_atomic(folder / "job.json", {"jobId": folder.name, "requestKey": "old-key-123456", "profileId": PROFILE.id, "state": "RUNNING",
                                                "stateHistory": [{"state": "RUNNING", "at": "2026-10-17T12:00:00Z"}], "createdAt": "2026-10-17T12:00:00Z",
                                                "result": None, "error": None, "progress": {}})
        m = self.manager(root)
        job = m.get(folder.name)
        self.assertEqual(job["state"], "INTERRUPTED")
        self.assertEqual(job["error"]["kind"], "INTERRUPTED")
        self.assertIsNone(job["result"])
        self.assertFalse((folder / "staging").exists())
        self.assertEqual(m.start(PROFILE.id, "old-key-123456")[0]["jobId"], folder.name)  # nessun rilancio implicito

    def test_shutdown_interrupts_active_job(self):
        root = make_data_dir(self.tmp)
        run = Blocking()
        m = JobManager(CAND, PROFILES, root, runner=run)
        job, _ = m.start(PROFILE.id, "shutdown-0001")
        self.assertTrue(run.entered.wait(5))
        m.shutdown(5.0)
        done = m.get(job["jobId"])
        self.assertEqual(done["state"], "INTERRUPTED")
        restarted = JobManager(CAND, PROFILES, root)
        self.assertEqual(restarted.get(job["jobId"])["state"], "INTERRUPTED")
        restarted.shutdown(1.0)


class TestCatalog(Base):
    def test_partial_old_and_corrupt_results(self):
        root = make_data_dir(self.tmp)
        m = self.manager(root)
        job = wait_terminal(m, m.start(PROFILE.id, "catalog-0001")[0]["jobId"])
        cat = Catalog(CAND, PROFILES, root)
        good = cat.get(job["result"]["resultId"])
        self.assertEqual(good["status"], "OK")
        self.assertEqual(good["profile"]["id"], PROFILE.id)
        self.assertEqual(good["via"], "APP-001")
        runs = root / "runs"
        (runs / "CAND-001-partial").mkdir()
        (runs / "CAND-001-partial" / "cand001-bundle.json").write_text("{}", encoding="utf-8")  # pubblicazione interrotta
        old = runs / "CAND-001-v1.0.0-e1.0.0-DEV-old"
        old.mkdir()
        (old / "run-manifest.json").write_text(json.dumps({"kind": "CAND001_RUN", "phase": "DEV", "schema": "cand001.bundle/1"}), encoding="utf-8")
        v2 = runs / "CAND-001-v1.0.0-e1.0.2-ADDITIONAL_2025-x"
        v2.mkdir()
        body = b'{"kind":"CAND001_BUNDLE"}'
        (v2 / "cand001-bundle.json").write_bytes(body)
        (v2 / "run-manifest.json").write_text(json.dumps({"kind": "CAND001_RUN", "phase": "ADDITIONAL_2025", "schema": "cand001.bundle/2",
                                                          "outputs": {"bundle": {"file": "cand001-bundle.json", "sha256": "0" * 64, "bytes": len(body)}}}),
                                              encoding="utf-8")
        (runs / "not-a-result").mkdir()
        cat = Catalog(CAND, {**PROFILES, **__import__("cand001.profiles", fromlist=["load_profiles"]).load_profiles(CAND)}, root)
        entries = {e["resultId"]: e for e in cat.list()}
        self.assertNotIn("not-a-result", entries)
        self.assertEqual(entries["CAND-001-partial"]["status"], "NOT_OPENABLE")
        self.assertEqual(entries[old.name]["status"], "UNSUPPORTED_SCHEMA")
        inferred = entries[v2.name]
        self.assertEqual(inferred["status"], "OK")
        self.assertTrue(inferred["profile"]["inferred"])
        self.assertEqual(inferred["profile"]["id"], "ADDITIONAL_2025")
        self.assertIsNone(inferred["startedAt"])  # nessuna data inventata
        entry, content, reason = cat.bundle(v2.name)
        self.assertIsNone(content)
        self.assertIn("SHA256", reason)
        self.assertEqual(cat.bundle("../../etc")[2], "NOT_FOUND")
        entry, content, reason = cat.bundle(job["result"]["resultId"])
        self.assertIsNone(reason)
        self.assertEqual(json.loads(content)["profile"]["id"], PROFILE.id)


class TestHttp(Base):
    def serve(self, root, runner=execute):
        m = self.manager(root, runner=runner)
        app = App(CAND, PROFILES, root, m, 0, "2026-10-17T00:00:00Z")
        server = make_server(app)
        threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return app, m

    def call(self, app, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", app.port, timeout=10)
        h = {"Host": f"127.0.0.1:{app.port}", **(headers or {})}
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            h.setdefault("Content-Type", "application/json")
        conn.request(method, path, body=data, headers=h)
        r = conn.getresponse()
        raw = r.read()
        conn.close()
        try:
            return r.status, json.loads(raw), dict(r.getheaders())
        except ValueError:
            return r.status, raw, dict(r.getheaders())

    def test_boundaries_and_contract(self):
        root = make_data_dir(self.tmp)
        app, m = self.serve(root)
        post = {"Origin": ORIGIN}
        s, b, _ = self.call(app, "GET", "/api/health", headers={"Host": "evil.example:8765"})
        self.assertEqual((s, b["error"]["code"]), (403, "FORBIDDEN_HOST"))
        s, b, _ = self.call(app, "POST", "/api/jobs", {"profileId": PROFILE.id, "requestKey": "no-origin-0001"})
        self.assertEqual((s, b["error"]["code"]), (403, "FORBIDDEN_ORIGIN"))
        s, b, _ = self.call(app, "POST", "/api/jobs", {"profileId": PROFILE.id, "requestKey": "bad-origin-001"}, {"Origin": "http://evil.example"})
        self.assertEqual(s, 403)
        s, b, h = self.call(app, "OPTIONS", "/api/jobs", headers=post)
        self.assertEqual(s, 405)
        self.assertNotIn("Access-Control-Allow-Origin", h)
        s, b, _ = self.call(app, "GET", "/api/jobs/new?profileId=" + PROFILE.id)  # GET non avvia
        self.assertEqual(s, 404)
        s, b, _ = self.call(app, "POST", "/api/jobs", {"profileId": "CUSTOM", "requestKey": "custom-00001"}, post)
        self.assertEqual((s, b["error"]["code"]), (400, "PROFILE_NOT_ALLOWED"))
        s, b, _ = self.call(app, "POST", "/api/jobs", {"profileId": PROFILE.id, "requestKey": "window-00001", "end": "2026-03-01T00:00:00Z"}, post)
        self.assertEqual((s, b["error"]["code"]), (400, "INVALID_REQUEST"))
        s, b, _ = self.call(app, "POST", "/api/jobs", {"profileId": PROFILE.id, "requestKey": "form-000001"}, {**post, "Content-Type": "text/plain"})
        self.assertEqual(s, 400)
        self.assertEqual(m.list(), [])
        s, b, _ = self.call(app, "POST", "/api/jobs", {"profileId": PROFILE.id, "requestKey": "http-run-0001"}, post)
        self.assertEqual(s, 201)
        job_id = b["job"]["jobId"]
        s2, b2, _ = self.call(app, "POST", "/api/jobs", {"profileId": PROFILE.id, "requestKey": "http-run-0001"}, post)
        self.assertEqual((s2, b2["job"]["jobId"], b2["created"]), (200, job_id, False))
        done = wait_terminal(m, job_id)
        s, b, _ = self.call(app, "GET", f"/api/jobs/{job_id}")
        self.assertEqual((s, b["job"]["state"]), (200, done["state"]))
        s, b, _ = self.call(app, "GET", "/api/jobs/job-20991231T000000Z-000000")
        self.assertEqual((s, b["error"]["code"]), (404, "NOT_FOUND"))
        s, b, _ = self.call(app, "GET", "/api/results")
        rid = done["result"]["resultId"]
        self.assertIn(rid, [r["resultId"] for r in b["results"]])
        s, raw, h = self.call(app, "GET", f"/api/results/{rid}/bundle")
        self.assertEqual(s, 200)
        self.assertEqual(raw["run"]["runId"], rid)
        s, b, _ = self.call(app, "GET", "/api/results/..%2F..%2Fmanifests/bundle")
        self.assertEqual(s, 404)
        s, b, _ = self.call(app, "POST", f"/api/jobs/{job_id}/cancel", {}, post)
        self.assertEqual((s, b["outcome"], b["job"]["state"]), (200, "ALREADY_FINISHED", "COMPLETED"))

    def test_active_conflict_and_cancel_over_http(self):
        root = make_data_dir(self.tmp)
        run = Blocking()
        app, m = self.serve(root, runner=run)
        post = {"Origin": ORIGIN}
        s, b, _ = self.call(app, "POST", "/api/jobs", {"profileId": PROFILE.id, "requestKey": "tab-a-000001"}, post)
        self.assertEqual(s, 201)
        s2, b2, _ = self.call(app, "POST", "/api/jobs", {"profileId": PROFILE.id, "requestKey": "tab-b-000002"}, post)
        self.assertEqual((s2, b2["error"]["code"], b2["error"]["job"]["jobId"]), (409, "ACTIVE_JOB_EXISTS", b["job"]["jobId"]))
        s, c, _ = self.call(app, "POST", f"/api/jobs/{b['job']['jobId']}/cancel", {}, post)
        self.assertEqual((s, c["outcome"]), (202, "REQUESTED"))
        self.assertEqual(c["job"]["state"], "CANCEL_REQUESTED")  # prima la richiesta, poi l'esito effettivo
        done = wait_terminal(m, b["job"]["jobId"])
        self.assertEqual(done["state"], "CANCELLED")

    def test_missing_data_refused_without_download(self):
        root = make_data_dir(self.tmp, missing="trade/2022-10")
        app, m = self.serve(root)
        with mock.patch("obs001.acquire.http_get") as net, mock.patch("cand001.data.http_get") as net2:
            s, b, _ = self.call(app, "GET", "/api/profiles")
            prof = b["profiles"][0]
            self.assertFalse(prof["availability"]["available"])
            self.assertEqual(prof["availability"]["missing"][0]["month"], "2022-10")
            s, b, _ = self.call(app, "POST", "/api/jobs", {"profileId": PROFILE.id, "requestKey": "missing-00001"}, {"Origin": ORIGIN})
            self.assertEqual((s, b["error"]["code"]), (422, "DATA_MISSING"))
            net.assert_not_called()
            net2.assert_not_called()
        self.assertEqual(m.list(), [])


class TestInstrumentationDoesNotChangeResults(unittest.TestCase):
    """Eventi di avanzamento/annullamento attivi o assenti: stessi risultati con prefissi e futuri diversi."""

    def test_same_results_with_and_without_ticks(self):
        from cand001.backtest import observe_store, run_window
        from cand001.fixture import synthetic_store
        from cand001.metrics import summarize

        from cand001_helpers import DAY, T0

        for days_before, days_after, seed in ((10, 15, 3), (40, 15, 3), (10, 30, 5)):
            start, end = T0 - days_before * DAY, T0 + days_after * DAY
            calls = []
            plain = run_window(CAND, synthetic_store(start, end, seed), (T0, end), [], {})
            store = synthetic_store(start, end, seed)
            obs = observe_store(store, tick=lambda *a: calls.append(a))
            ticked = run_window(CAND, store, (T0, end), [], {}, obs=obs, tick=lambda s: calls.append(s))
            self.assertTrue(calls)
            a, b = summarize(plain, CAND, "DEV"), summarize(ticked, CAND, "DEV")
            self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))
            self.assertEqual(json.dumps(plain["ledger"].trades), json.dumps(ticked["ledger"].trades))
            self.assertEqual(len(plain["engine"].decisions), len(ticked["engine"].decisions))

    def test_cancel_raised_by_tick_stops_simulation(self):
        from cand001.backtest import run_window
        from cand001.fixture import synthetic_store

        from cand001_helpers import DAY, T0

        seen = []

        def tick(state):
            seen.append(state["closes"])
            if state["closes"] >= 64:
                raise Cancelled()

        with self.assertRaises(Cancelled):
            run_window(CAND, synthetic_store(T0 - 5 * DAY, T0 + 10 * DAY, 3), (T0, T0 + 10 * DAY), [], {}, tick=tick)
        self.assertEqual(seen, [0, 32, 64])


if __name__ == "__main__":
    unittest.main()
