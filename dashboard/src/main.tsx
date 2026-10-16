import '@fontsource/inter/400.css';
import '@fontsource/inter/500.css';
import '@fontsource/inter/600.css';
import '@fontsource/ibm-plex-mono/400.css';
import '@fontsource/ibm-plex-mono/500.css';
import './ui/styles.css';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { SimulatedProvider } from './sim/provider';
import { App } from './ui/App';

// Ambiente iniziale dichiarato: simulazione locale. Lo studio storico si apre da file locale
// («Apri studio storico»); nessuna rete e nessun aggiornamento automatico dello storico.
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App createSimulation={() => new SimulatedProvider()} />
  </StrictMode>,
);
