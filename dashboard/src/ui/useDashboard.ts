import { createContext, useCallback, useContext, useEffect, useRef, useState, useSyncExternalStore } from 'react';
import type { ConfirmationPreview, DashboardProvider } from '../contract/provider';
import type { ActionId, Snapshot } from '../contract/types';

export interface PendingConfirmation {
  readonly preview: ConfirmationPreview;
  /** Generato all'apertura: un doppio click sulla conferma non duplica il comando. */
  readonly requestId: string;
}

export interface DashboardApi {
  readonly snapshot: Snapshot;
  readonly request: (action: ActionId) => void;
  readonly confirmation: PendingConfirmation | null;
  readonly confirm: (acknowledged: boolean) => void;
  readonly cancel: () => void;
  readonly toast: string | null;
}

const CONTEXT_CHANGED =
  'Conferma annullata: lo stato simulato è cambiato mentre il dialogo era aperto. Nessun comando eseguito; riapri il comando per vedere la nuova anteprima.';

let counter = 0;
const newRequestId = () => `ui-${Date.now().toString(36)}-${(++counter).toString(36)}`;

export function useDashboardState(provider: DashboardProvider): DashboardApi {
  const snapshot = useSyncExternalStore(provider.subscribe, provider.getSnapshot);
  const [confirmation, setConfirmationState] = useState<PendingConfirmation | null>(null);
  // Copia sincrona: evita di trattare come «cambio di contesto» l'effetto della propria conferma.
  const openConfirmation = useRef<PendingConfirmation | null>(null);
  const setConfirmation = useCallback((next: PendingConfirmation | null) => {
    openConfirmation.current = next;
    setConfirmationState(next);
  }, []);
  const [toast, setToast] = useState<string | null>(null);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const notify = useCallback((message: string) => {
    setToast(message);
    if (toastTimer.current) clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(null), 6000);
  }, []);

  // Un aggiornamento del provider (cambio checkpoint, reset, feed, eseguito, ...) che modifica
  // le conseguenze mostrate invalida la conferma aperta prima di qualsiasi esecuzione.
  useEffect(() => {
    const open = openConfirmation.current;
    if (!open) return;
    const current = provider.preview({ action: open.preview.action });
    if (current.kind === 'CONFIRM' && current.confirmation.contextToken === open.preview.contextToken) return;
    setConfirmation(null);
    notify(CONTEXT_CHANGED);
  }, [snapshot, provider, notify, setConfirmation]);

  const request = useCallback(
    (action: ActionId) => {
      const preview = provider.preview({ action });
      if (preview.kind === 'BLOCKED') return notify(preview.reason);
      if (preview.kind === 'CONFIRM') return setConfirmation({ preview: preview.confirmation, requestId: newRequestId() });
      const result = provider.dispatch({ action }, newRequestId());
      if (result.status !== 'APPLIED') notify(result.message);
    },
    [provider, notify, setConfirmation],
  );

  const confirm = useCallback(
    (acknowledged: boolean) => {
      const open = openConfirmation.current;
      if (!open || open !== confirmation) return;
      setConfirmation(null);
      const result = provider.dispatch({ action: open.preview.action }, open.requestId, {
        acknowledged,
        contextToken: open.preview.contextToken,
      });
      if (result.status === 'CONTEXT_CHANGED') notify(CONTEXT_CHANGED);
      else if (result.status === 'REJECTED') notify(result.message);
    },
    [confirmation, provider, notify, setConfirmation],
  );

  const cancel = useCallback(() => setConfirmation(null), [setConfirmation]);

  return { snapshot, request, confirmation, confirm, cancel, toast };
}

export const DashboardContext = createContext<DashboardApi | null>(null);

export function useDashboard(): DashboardApi {
  const ctx = useContext(DashboardContext);
  if (!ctx) throw new Error('DashboardContext mancante');
  return ctx;
}
