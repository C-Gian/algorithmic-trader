// Avvio normale dell'app (APP-001): `npm run dev` dalla cartella dashboard.
// Avvia il servizio Python locale (127.0.0.1:8765) come processo figlio e poi Vite (127.0.0.1:5173) dentro
// questo stesso processo, senza dipendenze nuove: chiudere il launcher chiude anche il frontend.
// Opzioni: APP001_PYTHON = percorso di Python 3.12; APP001_DATA_DIR = cartella dati CAND-001
// (oppure `npm run dev -- --data-dir <cartella>`). Ctrl+C ferma soltanto i due processi avviati qui.
import { spawn, spawnSync } from 'node:child_process';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const DASHBOARD = resolve(HERE, '..');
const REPO = resolve(DASHBOARD, '..');
const SERVICE_URL = 'http://127.0.0.1:8765/api/health';
const say = (msg) => console.log(`[avvio] ${msg}`);

const EXIT_TEXT = {
  3: 'la porta 8765 è occupata da un altro programma (vedi il messaggio sopra).',
  4: 'cartella dati non trovata: indica la cartella CAND-001 con APP001_DATA_DIR o --data-dir.',
  5: 'un altro servizio APP-001 è già attivo sulla stessa cartella dati.',
  6: 'versione di Python non adatta: serve Python 3.12 (APP001_PYTHON per indicarne il percorso).',
};

function findPython() {
  const custom = process.env.APP001_PYTHON;
  const candidates = custom ? [[custom, []]] : [['python3.12', []], ['py', ['-3.12']], ['python3', []], ['python', []]];
  for (const [cmd, pre] of candidates) {
    const r = spawnSync(cmd, [...pre, '-c', 'import sys; print(sys.version_info >= (3, 12))'], { encoding: 'utf8', windowsHide: true });
    if (r.status === 0 && r.stdout.trim() === 'True') return [cmd, pre];
  }
  return null;
}

function dataDirArg() {
  const i = process.argv.indexOf('--data-dir');
  if (i > 0 && process.argv[i + 1]) return ['--data-dir', process.argv[i + 1]];
  return process.env.APP001_DATA_DIR ? ['--data-dir', process.env.APP001_DATA_DIR] : [];
}

async function waitHealthy(child, timeoutMs) {
  const end = Date.now() + timeoutMs;
  while (Date.now() < end) {
    if (child.exitCode !== null) return false;
    try {
      const r = await fetch(SERVICE_URL);
      if (r.ok && r.headers.get('x-app001-service')) return true;
    } catch {
      // non ancora in ascolto
    }
    await new Promise((ok) => setTimeout(ok, 250));
  }
  return false;
}

const python = findPython();
if (!python) {
  say('Python 3.12 non trovato. Installalo oppure indica il percorso, per esempio:');
  say('  $env:APP001_PYTHON = "C:\\Users\\<nome>\\.local\\bin\\python3.12.exe"; npm run dev');
  process.exit(1);
}
let createServer;
try {
  ({ createServer } = await import('vite'));
} catch {
  say('Dipendenze del frontend assenti: esegui una volta `npm ci` nella cartella dashboard.');
  process.exit(1);
}

let stopping = false;
const [pyCmd, pyPre] = python;
const service = spawn(pyCmd, [...pyPre, '-m', 'app001', '--watch-stdin', ...dataDirArg()], {
  cwd: REPO,
  env: { ...process.env, PYTHONPATH: join(REPO, 'src'), PYTHONUNBUFFERED: '1' },
  stdio: ['pipe', 'inherit', 'inherit'],
  windowsHide: true,
});
let vite = null;

async function stopAll(code) {
  if (stopping) return;
  stopping = true;
  // Arresto ordinato del servizio: la chiusura dello stdin lo fa terminare segnando un eventuale backtest come interrotto.
  try {
    service.stdin.end();
  } catch {
    // già chiuso
  }
  if (vite) await vite.close().catch(() => {});
  if (service.exitCode === null && service.signalCode === null) {
    const force = setTimeout(() => service.kill(), 10_000); // solo il processo avviato qui
    await new Promise((ok) => service.once('exit', ok));
    clearTimeout(force);
  }
  process.exit(code);
}

service.once('exit', (code) => {
  if (stopping) return;
  say(`il servizio locale si è fermato (codice ${code}): ${EXIT_TEXT[code] ?? 'vedi il messaggio sopra.'}`);
  stopAll(code || 1);
});

for (const sig of ['SIGINT', 'SIGTERM', 'SIGHUP', 'SIGBREAK']) {
  process.on(sig, () => {
    say('arresto del servizio e del frontend avviati da questo comando…');
    stopAll(0);
  });
}

say(`servizio locale: ${pyCmd}${pyPre.length ? ' ' + pyPre.join(' ') : ''} -m app001`);
if (!(await waitHealthy(service, 30_000))) {
  if (!stopping) {
    say('il servizio locale non risponde su 127.0.0.1:8765 entro 30 secondi.');
    stopAll(1);
  }
} else {
  try {
    vite = await createServer({ root: DASHBOARD, configFile: join(DASHBOARD, 'vite.config.ts') });
    await vite.listen();
    vite.printUrls();
    say('app pronta: apri http://127.0.0.1:5173/#/backtest nel browser. Ctrl+C per fermare.');
  } catch (e) {
    say(`il frontend non è partito: ${e.message}. Se la porta 5173 è occupata chiudi l'altro programma; nessun processo viene terminato.`);
    vite = null;
    stopAll(1);
  }
}
