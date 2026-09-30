import { useEffect, useState } from "react";
import { dataApi, DatasetDetail, DatasetFamily, DatasetSummary } from "../api";
import { fmtBytes, fmtInt, fmtTime } from "../lib/format";
import { datasetFromHash, replaceHash } from "../lib/route";
import { usePoll } from "../lib/usePoll";
import { Icon } from "../ui/Icon";
import { Badge, Button, Card, cx, EmptyState, Metric, Notice, PageHeader, Skeleton, statusTone, Tone } from "../ui/primitives";

// Read-only evidence workspace over acquired market-data datasets (algotrader.marketdata.v1 manifests + quality).

function QualityBadge({ status, testid }: { status: string; testid?: string }) {
  return <Badge tone={statusTone(status)} dot testid={testid}>{status.toUpperCase()}</Badge>;
}

function Coverage({ f }: { f: DatasetFamily }) {
  if (!f.expected_rows) return <span className="muted small-text">no completeness schedule</span>;
  const pct = Math.min(100, (f.rows / f.expected_rows) * 100);
  const tone: Tone = pct >= 100 ? "pos" : pct >= 95 ? "warn" : "neg";
  return (
    <span className="coverage" title={`${f.rows} of ${f.expected_rows} expected rows`}>
      <span className="coverage-bar"><span className={`coverage-fill tone-${tone}`} style={{ width: `${pct}%` }} /></span>
      <span className="mono">{pct.toFixed(pct === 100 ? 0 : 1)}%</span>
    </span>
  );
}

type VerifyState = { state: "idle" } | { state: "running" } | { state: "ok"; text: string } | { state: "fail"; text: string };

function Detail({ id }: { id: string }) {
  const [d, setD] = useState<DatasetDetail | null>(null);
  const [verify, setVerify] = useState<VerifyState>({ state: "idle" });
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setD(null);
    setError(null);
    setVerify({ state: "idle" });
    dataApi.detail(id).then(setD).catch((e) => setError((e as Error).message));
  }, [id]);

  const runVerify = async () => {
    setVerify({ state: "running" });
    try {
      const r = await dataApi.verify(id);
      setVerify(r.ok
        ? { state: "ok", text: "OK — all hashes, row counts and the dataset identity match" }
        : { state: "fail", text: `FAILED: ${r.problems.join("; ")}` });
    } catch (e) {
      setVerify({ state: "fail", text: `FAILED: ${(e as Error).message}` });
    }
  };

  if (error) return <Notice tone="neg" title="Could not load dataset">{error}</Notice>;
  if (!d) return <Card><Skeleton lines={6} /></Card>;
  const s = d.summary;
  const m = d.manifest;
  const inst = m.instrument;
  const files = `/api/datasets/${id}/files`;
  const rawCount = m.files.filter((f) => f.name.startsWith("raw/")).length;
  const gaps = d.quality.families.flatMap((f) => f.gaps.map((g) => ({ family: f.family, ...g })));

  return (
    <div className="detail-stack">
      <Card className="dataset-hero" testid="dataset-detail">
        <div className="dataset-hero-head">
          <div className="min-0">
            <div className="eyebrow">Historical dataset · immutable</div>
            <h2 className="dataset-title mono" data-testid="dataset-id">{s.dataset_id}</h2>
          </div>
          <div className="dataset-hero-actions">
            <QualityBadge status={s.quality_status} testid="dataset-quality" />
            <Button variant="secondary" icon="shield" onClick={runVerify} disabled={verify.state === "running"} data-testid="dataset-verify">
              {verify.state === "running" ? "Verifying…" : "Verify hashes"}
            </Button>
          </div>
        </div>
        {verify.state !== "idle" && (
          <div className={cx("verify-result", verify.state === "ok" && "tone-pos", verify.state === "fail" && "tone-neg")}
               data-testid="dataset-verify-result" role="status">
            <Icon name={verify.state === "ok" ? "check" : verify.state === "fail" ? "x" : "refresh"} size={14} />
            {verify.state === "running" ? "verifying…" : verify.text}
          </div>
        )}
        <div className="metric-grid">
          <Metric label="Source" value={<span data-testid="dataset-source">{s.source.toUpperCase()} · {s.base_url}</span>} />
          <Metric label="Instrument" value={s.inst_id} testid="dataset-instrument" />
          <Metric label="Contract" mono={false}
                  value={`${inst.inst_type ?? "—"} ${inst.ct_type ?? ""}`}
                  hint={`1 contract = ${inst.ct_val ?? "—"} ${inst.ct_val_ccy ?? ""} · settle ${inst.settle_ccy ?? "—"}`} />
          <Metric label="Index" value={inst.index_id ?? "—"} />
          <Metric label="Requested (UTC, end exclusive)" value={<span data-testid="dataset-requested">{fmtTime(s.requested.start)} → {fmtTime(s.requested.end)}</span>} />
          <Metric label="Retrieved" value={<span data-testid="dataset-retrieved">{fmtTime(m.retrieval_started_at)}</span>} />
          <Metric label="Schema" value={s.schema_version} testid="dataset-schema" />
          <Metric label="Raw source pages" value={fmtInt(m.raw_page_count)} />
          <Metric label="Code version" value={m.code_version ?? "—"} />
        </div>
        <div className="notes">
          <p><Icon name="clock" size={14} /> <span>Availability policy <code>{m.availability_policy}</code>: {m.availability_policy_text}</span></p>
          <p><Icon name="lock" size={14} /> <span>Exchange-advertised maximum leverage ({inst.advertised_max_leverage ?? "—"}×) is venue metadata only. Leverage and position size are the Owner's decisions; the product does not choose them.</span></p>
        </div>
      </Card>

      <Card title="Coverage by family" icon="layers" eyebrow="Rows received versus the expected 1-minute schedule">
        <div className="table-wrap">
          <table className="table" data-testid="dataset-families">
            <thead>
              <tr><th>Family</th><th className="num">Rows</th><th className="num">Expected</th><th className="num">Missing</th><th className="num">Gaps</th><th>Coverage</th><th>First → last (UTC)</th><th>Status</th></tr>
            </thead>
            <tbody>
              {s.families.map((f) => (
                <tr key={f.family}>
                  <td className="mono strong">{f.family}</td>
                  <td className="num mono">{fmtInt(f.rows)}</td>
                  <td className="num mono">{f.expected_rows ?? "n/a"}</td>
                  <td className={cx("num mono", (f.missing_rows ?? 0) > 0 && "text-warn")}>{f.missing_rows ?? "n/a"}</td>
                  <td className={cx("num mono", f.gaps > 0 && "text-warn")}>{f.gaps}</td>
                  <td><Coverage f={f} /></td>
                  <td className="mono span-cell"><span>{fmtTime(f.first_time)}</span><span className="muted">→ {fmtTime(f.last_time)}</span></td>
                  <td><QualityBadge status={f.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card title="Quality findings" icon="alert" testid="dataset-findings"
            actions={<span className="count-chip mono">{d.quality.findings.length}</span>}>
        <p className="muted small-text">{d.quality.scope_note}</p>
        {d.quality.findings.length === 0 ? (
          <div className="inline-ok"><Icon name="check" size={14} /> No findings.</div>
        ) : (
          <ul className="findings">
            {d.quality.findings.map((f, i) => (
              <li key={i} className="finding">
                <Badge tone={statusTone(f.severity)}>{f.severity}</Badge>
                <div className="finding-body">
                  <div><span className="mono strong">{f.family}</span> · <span className="mono">{f.check}</span> <span className="muted">×{f.count}</span></div>
                  <div className="finding-detail">{f.detail}</div>
                  {f.examples.length > 0 && <div className="muted small-text mono">e.g. {f.examples.join(", ")}</div>}
                </div>
              </li>
            ))}
          </ul>
        )}
        {gaps.length > 0 && (
          <div className="gaps">
            <div className="log-title">Gaps — shown, never filled</div>
            <ul className="gap-list">
              {gaps.slice(0, 20).map((g, i) => (
                <li key={i}>
                  <span className="mono strong">{g.family}</span>
                  <span className="mono">{fmtTime(g.first_missing_open_time)} → {fmtTime(g.last_missing_open_time)}</span>
                  <Badge tone="warn">{g.missing_bars} bars</Badge>
                </li>
              ))}
            </ul>
            {gaps.length > 20 && <p className="muted small-text">+ {gaps.length - 20} more in quality.json</p>}
          </div>
        )}
      </Card>

      <Card title="Provenance and hashes" icon="shield" testid="dataset-provenance">
        <div className="file-links">
          {["manifest.json", "quality.json", "request_log.jsonl", "instrument.json"].map((n) => (
            <a key={n} className="file-link" href={`${files}/${n}`} target="_blank" rel="noreferrer">
              <Icon name="file" size={14} /><span className="mono">{n}</span>
            </a>
          ))}
        </div>
        <p className="muted small-text">Identity: {m.identity_basis}</p>
        {s.prior_versions.length > 0 && (
          <Notice tone="warn" title="Earlier versions exist">
            Earlier versions of this request with different source content: <span className="mono">{s.prior_versions.join(", ")}</span>
          </Notice>
        )}
        <div className="table-wrap">
          <table className="table table-compact">
            <thead><tr><th>File</th><th className="num">Rows</th><th className="num">Size</th><th>SHA-256</th></tr></thead>
            <tbody>
              {m.files.filter((f) => !f.name.startsWith("raw/")).map((f) => (
                <tr key={f.name}>
                  <td><a className="mono" href={`${files}/${f.name}`}>{f.name}</a></td>
                  <td className="num mono">{f.rows ?? ""}</td>
                  <td className="num mono nowrap" title={`${f.bytes} bytes`}>{fmtBytes(f.bytes)}</td>
                  <td><code className="hash">{f.sha256}</code></td>
                </tr>
              ))}
              <tr><td colSpan={4} className="muted">+ {rawCount} raw source responses (exact bytes, hashed; see manifest)</td></tr>
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

function DatasetList({ datasets, selected, onSelect }: { datasets: DatasetSummary[]; selected: string | null; onSelect: (id: string) => void }) {
  return (
    <ul className="list" data-testid="dataset-list" aria-label="Datasets">
      {datasets.map((d) => (
        <li key={d.dataset_id}>
          <button type="button" className={cx("list-item", d.dataset_id === selected && "is-selected")}
                  aria-current={d.dataset_id === selected ? "true" : undefined} onClick={() => onSelect(d.dataset_id)}>
            <span className="list-item-title mono">{d.dataset_id}</span>
            <span className="list-item-meta">
              <QualityBadge status={d.quality_status} />
              <span className="mono muted">{d.inst_id}</span>
            </span>
            <span className="list-item-sub mono">{fmtTime(d.requested.start)} → {fmtTime(d.requested.end)}</span>
          </button>
        </li>
      ))}
    </ul>
  );
}

export function DataWorkspace() {
  const list = usePoll(dataApi.list, 15000);
  const datasets = list.data?.datasets ?? null;
  const [selected, setSelected] = useState<string | null>(datasetFromHash());

  useEffect(() => {
    if (!selected && datasets?.length) setSelected(datasets[0].dataset_id);
  }, [datasets, selected]);

  useEffect(() => {
    if (selected) replaceHash(`data=${selected}`);
  }, [selected]);

  // Follow dataset deep links while the workspace stays mounted.
  useEffect(() => {
    const on = () => {
      const id = datasetFromHash();
      if (id) setSelected((cur) => (cur === id ? cur : id));
    };
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);

  const counts = (datasets ?? []).reduce<Record<string, number>>((acc, d) => ({ ...acc, [d.quality_status]: (acc[d.quality_status] ?? 0) + 1 }), {});

  return (
    <div className="page page-data" data-testid="page-data">
      <PageHeader
        eyebrow="Workbench · market evidence"
        title="Data"
        lede="Immutable historical datasets from the official OKX public API: coverage, quality, gaps and provenance. Read-only — nothing is repaired or filled."
        meta={
          <div className="head-stats">
            <Metric label="Datasets" value={datasets ? datasets.length : "—"} />
            {Object.entries(counts).map(([k, v]) => <Metric key={k} label={k} value={v} tone={statusTone(k)} />)}
          </div>
        }
      />

      <div className="split">
        <Card title="Datasets" icon="data" className="split-rail"
              actions={datasets && <span className="count-chip mono">{datasets.length}</span>}>
          <p className="muted small-text rail-note">Read-only view of <code className="path" title={list.data?.data_root}>{list.data?.data_root ?? "…"}</code><br />Create datasets with <code>algotrader data fetch-okx</code>.</p>
          {list.error && <Notice tone="neg" title="Datasets unavailable">{list.error}</Notice>}
          {list.loading && !datasets && <Skeleton lines={4} />}
          {datasets && datasets.length === 0 && (
            <EmptyState icon="data" title="No datasets yet" testid="no-datasets">
              Fetch a window of public OKX history with <code>algotrader data fetch-okx --start … --end …</code>.
            </EmptyState>
          )}
          {datasets && datasets.length > 0 && <DatasetList datasets={datasets} selected={selected} onSelect={setSelected} />}
        </Card>

        <div className="split-main">
          {selected ? <Detail id={selected} /> : (
            datasets && datasets.length === 0 ? (
              <Card>
                <EmptyState icon="layers" title="Evidence appears here">
                  Each dataset shows its source, instrument snapshot, coverage per family, quality findings and every file hash.
                </EmptyState>
              </Card>
            ) : <Card><Skeleton lines={6} /></Card>
          )}
        </div>
      </div>
    </div>
  );
}
