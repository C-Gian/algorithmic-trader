import { createContext, useCallback, useContext, useRef, useState, useSyncExternalStore } from 'react';
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

let counter = 0;
const newRequestId = () => `ui-${Date.now().toString(36)}-${(++counter).toString(36)}`;

export function useDashboardState(provider: DashboardProvider): DashboardApi {
  const snapshot = useSyncExternalStore(provider.subscribe, provider.getSnapshot);
  const [confirmation, setConfirmation] = useState<PendingConfirmation | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const notify = useCallback((message: string) => {
    setToast(message);
    if (toastTimer.current) clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(null), 4000);
  }, []);

  const request = useCallback(
    (action: ActionId) => {
      const preview = provider.preview({ action });
      if (preview.kind === 'BLOCKED') return notify(preview.reason);
      if (preview.kind === 'CONFIRM') return setConfirmation({ preview: preview.confirmation, requestId: newRequestId() });
      const result = provider.dispatch({ action }, newRequestId());
      if (result.status !== 'APPLIED') notify(result.message);
    },
    [provider, notify],
  );

  const confirm = useCallback(
    (acknowledged: boolean) => {
      if (!confirmation) return;
      const result = provider.dispatch({ action: confirmation.preview.action }, confirmation.requestId, { acknowledged });
      if (result.status === 'REJECTED') notify(result.message);
      setConfirmation(null);
    },
    [confirmation, provider, notify],
  );

  const cancel = useCallback(() => setConfirmation(null), []);

  return { snapshot, request, confirmation, confirm, cancel, toast };
}

export const DashboardContext = createContext<DashboardApi | null>(null);

export function useDashboard(): DashboardApi {
  const ctx = useContext(DashboardContext);
  if (!ctx) throw new Error('DashboardContext mancante');
  return ctx;
}
