import { useState } from 'react';
import { BundleError, parseBundle } from '../../historical/loadBundle';
import { HistoricalStudy } from '../../historical/study';
import { Notice } from '../components/primitives';

function readText(file: File): Promise<string> {
  if (typeof file.text === 'function') return file.text();
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error ?? new Error('lettura del file non riuscita'));
    reader.readAsText(file);
  });
}

export const BUNDLE_PATH_HINT = 'C:\\Projects\\algorithmic-trader-data\\OBS-001\\runs\\<ID del run>\\obs001-bundle.json';

/** Selettore del file locale: nessun server dati e nessun prezzo mostrato senza bundle valido. */
export function StudyFilePicker({ onOpen, label = 'Apri studio storico' }: { onOpen: (s: HistoricalStudy) => void; label?: string }) {
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = async (file: File | undefined) => {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const study = new HistoricalStudy(parseBundle(await readText(file)));
      onOpen(study);
    } catch (e) {
      setError(e instanceof BundleError ? e.message : `Lettura non riuscita: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="file-pick">
      <label className={`btn btn-primary${busy ? ' is-busy' : ''}`}>
        {busy ? 'Lettura del bundle…' : label}
        <input type="file" accept=".json,application/json" className="sr-only" aria-label={label} onChange={(e) => load(e.target.files?.[0])} />
      </label>
      {error && (
        <Notice tone="negative" title="Bundle non valido">
          {error}
        </Notice>
      )}
    </div>
  );
}

export function OpenStudy({ onOpen }: { onOpen: (s: HistoricalStudy) => void }) {
  return (
    <main className="content" id="main-content" tabIndex={-1}>
      <section className="card unavailable" aria-label="Apri studio storico">
        <p className="section-title">Studio storico · nessun bundle aperto</p>
        <p className="t-2">
          Questo ambiente mostra prezzi storici reali BTCUSDT perpetual (Binance Vision) e le osservazioni calcolate dallo studio OBS-001.
          Nessun dato è precaricato: apri il bundle prodotto localmente dal comando <span className="mono">process</span>.
        </p>
        <p className="t-3" style={{ fontSize: 12 }}>
          Percorso del file: <span className="mono">{BUNDLE_PATH_HINT}</span>
        </p>
        <StudyFilePicker onOpen={onOpen} />
      </section>
    </main>
  );
}
