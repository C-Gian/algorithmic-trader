import { useCallback, useEffect, useState } from "react";
import { dataApi, DatasetDetail, DatasetSummary } from "./api";
import { RecorderPanel } from "./RecorderPanel";

// Read-only inspection of acquired market-data datasets (manifests + quality reports).

function t(iso: string | null | undefined): string {
  if (!iso) return "—";
  return iso.replace("T", " ").replace(/(\.\d+)?(Z|\+00:00)$/, " UTC");
}

function selectedFromHash(): string | null {
  const m = window.location.hash.match(/^#data=([\w.-]+)/);
  return m ? m[1] : null;
}

function QualityBadge({ status }: { status: string }) {
  return <span className={`badge q-${status}`} data-testid="dataset-quality">{status.toUpperCase()}</span>;
}

function Detail({ id }: { id: string }) {
  const [d, setD] = useState<DatasetDetail | null>(null);
  const [verified, setVerified] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setD(null);
    setVerified(null);
    dataApi.detail(id).then(setD).catch((e) => setError((e as Error).message));
  }, [id]);

  const runVerify = async () => {
    setVerified("verifying…");
    const r = await dataApi.verify(id);
    setVerified(r.ok ? "OK — all hashes, row counts and the dataset identity match" : `FAILED: ${r.problems.join("; ")}`);
  };

  if (error) return <div className="error">{error}</div>;
  if (!d) return <div className="panel muted">loading…</div>;
  const s = d.summary;
  const m = d.manifest;
  const inst = m.instrument;
  const files = `/api/datasets/${id}/files`;
  return (
    <>
      <section className="panel" data-testid="dataset-detail">
        <div className="row">
          <h2 data-testid="dataset-id">{s.dataset_id}</h2>
          <QualityBadge status={s.quality_status} />
        </div>
        <div className="grid4">
          <div><label>Source</label><span data-testid="dataset-source">{s.source.toUpperCase()} · {s.base_url}</span></div>
          <div><label>Instrument</label><span data-testid="dataset-instrument">{s.inst_id}</span></div>
          <div><label>Contract</label><span>{inst.inst_type} {inst.ct_type} · 1 contract = {inst.ct_val} {inst.ct_val_ccy} · settle {inst.settle_ccy}</span></div>
          <div><label>Index</label><span>{inst.index_id}</span></div>
          <div><label>Requested (UTC, end exclusive)</label><span data-testid="dataset-requested">{t(s.requested.start)} → {t(s.requested.end)}</span></div>
          <div><label>Retrieved</label><span data-testid="dataset-retrieved">{t(m.retrieval_started_at)}</span></div>
          <div><label>Schema</label><span data-testid="dataset-schema">{s.schema_version}</span></div>
          <div><label>Raw source pages</label><span>{m.raw_page_count}</span></div>
          <div><label>Code version</label><span>{m.code_version ?? "—"}</span></div>
        </div>
        <p className="muted small">
          Availability policy <code>{m.availability_policy}</code>: {m.availability_policy_text}
        </p>
        <p className="muted small">Exchange-advertised leverage ({inst.advertised_max_leverage ?? "—"}x) is venue metadata only; the project's 1x exposure cap is unchanged.</p>
      </section>

      <section className="panel">
        <h3>Coverage by family</h3>
        <table className="history" data-testid="dataset-families">
          <thead><tr><th>Family</th><th>Rows</th><th>Expected</th><th>Missing</th><th>Gaps</th><th>First</th><th>Last</th><th>Status</th></tr></thead>
          <tbody>
            {s.families.map((f) => (
              <tr key={f.family}>
                <td>{f.family}</td>
                <td>{f.rows}</td>
                <td>{f.expected_rows ?? "n/a"}</td>
                <td>{f.missing_rows ?? "n/a"}</td>
                <td>{f.gaps}</td>
                <td>{t(f.first_time)}</td>
                <td>{t(f.last_time)}</td>
                <td><span className={`badge q-${f.status}`}>{f.status}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="panel" data-testid="dataset-findings">
        <h3>Quality findings</h3>
        <p className="muted small">{d.quality.scope_note}</p>
        {d.quality.findings.length === 0 ? <p>No findings.</p> : (
          <ul className="findings">
            {d.quality.findings.map((f, i) => (
              <li key={i}>
                <span className={`badge q-${f.severity}`}>{f.severity}</span> <b>{f.family}</b> · {f.check} ×{f.count} — {f.detail}
                {f.examples.length > 0 && <span className="muted"> (e.g. {f.examples.join(", ")})</span>}
              </li>
            ))}
          </ul>
        )}
        {d.quality.families.flatMap((f) => f.gaps.map((g) => ({ family: f.family, ...g }))).slice(0, 20).map((g, i) => (
          <div key={i} className="muted small">gap · {g.family}: {t(g.first_missing_open_time)} → {t(g.last_missing_open_time)} ({g.missing_bars} bars, not filled)</div>
        ))}
      </section>

      <section className="panel" data-testid="dataset-provenance">
        <h3>Provenance and hashes</h3>
        <p>
          <a href={`${files}/manifest.json`} target="_blank" rel="noreferrer">manifest.json</a> ·{" "}
          <a href={`${files}/quality.json`} target="_blank" rel="noreferrer">quality.json</a> ·{" "}
          <a href={`${files}/request_log.jsonl`} target="_blank" rel="noreferrer">request_log.jsonl</a> ·{" "}
          <a href={`${files}/instrument.json`} target="_blank" rel="noreferrer">instrument.json</a>
          {" · "}<button className="inline-btn" onClick={runVerify} data-testid="dataset-verify">Verify hashes</button>
          {verified && <span data-testid="dataset-verify-result"> {verified}</span>}
        </p>
        <p className="muted small">Identity: {m.identity_basis}</p>
        {s.prior_versions.length > 0 && (
          <p className="warn">Earlier versions of this request with different source content: {s.prior_versions.join(", ")}</p>
        )}
        <table className="history">
          <thead><tr><th>File</th><th>Rows</th><th>Bytes</th><th>SHA-256</th></tr></thead>
          <tbody>
            {m.files.filter((f) => !f.name.startsWith("raw/")).map((f) => (
              <tr key={f.name}>
                <td><a href={`${files}/${f.name}`}>{f.name}</a></td>
                <td>{f.rows ?? ""}</td>
                <td>{f.bytes}</td>
                <td><code>{f.sha256}</code></td>
              </tr>
            ))}
            <tr><td colSpan={4} className="muted">+ {m.files.filter((f) => f.name.startsWith("raw/")).length} raw source responses (exact bytes, hashed; see manifest)</td></tr>
          </tbody>
        </table>
      </section>
    </>
  );
}

export function DataView() {
  const [datasets, setDatasets] = useState<DatasetSummary[] | null>(null);
  const [root, setRoot] = useState("");
  const [selected, setSelected] = useState<string | null>(selectedFromHash());
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const r = await dataApi.list();
      setDatasets(r.datasets);
      setRoot(r.data_root);
      setSelected((cur) => cur ?? r.datasets[0]?.dataset_id ?? null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (selected) window.location.hash = `data=${selected}`;
  }, [selected]);

  return (
    <div className="layout">
      <aside className="panel runs">
        <h2>Datasets</h2>
        <p className="muted small">Read-only view of <code>{root}</code>. Create datasets with <code>algotrader data fetch-okx</code>.</p>
        {error && <div className="error">{error}</div>}
        <ul className="run-list" data-testid="dataset-list">
          {(datasets ?? []).map((d) => (
            <li key={d.dataset_id} className={d.dataset_id === selected ? "selected" : ""} onClick={() => setSelected(d.dataset_id)}>
              <div className="run-id">{d.dataset_id}</div>
              <div className="run-meta">
                <QualityBadge status={d.quality_status} /> {d.inst_id} · {t(d.requested.start)}
              </div>
            </li>
          ))}
          {datasets !== null && datasets.length === 0 && <li className="muted" data-testid="no-datasets">No datasets yet.</li>}
        </ul>
      </aside>
      <main className="home">
        <RecorderPanel />
        {selected ? <Detail id={selected} /> : <div className="panel muted">Select a dataset.</div>}
      </main>
    </div>
  );
}
