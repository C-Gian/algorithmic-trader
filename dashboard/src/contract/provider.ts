import type { ActionId, Snapshot, Tone } from './types';

/**
 * Intenzioni inviate dai componenti. Il provider decide se e come applicarle;
 * i componenti non calcolano conseguenze, contabilità o transizioni.
 */
export type Intent = { readonly action: ActionId };

/** Testo di conferma preparato dal provider a partire dallo stato corrente. */
export interface ConfirmationPreview {
  readonly action: ActionId;
  readonly icon: 'hand' | 'bot' | 'square' | 'close' | 'partial' | 'mode';
  readonly kicker: string;
  readonly title: string;
  readonly lead: string;
  readonly summary: readonly string[];
  readonly consequences: readonly string[];
  readonly notice: { readonly tone: Tone; readonly title: string; readonly text: string } | null;
  readonly confirmLabel: string;
  readonly confirmTone: 'primary' | 'danger';
  /** Se presente, la conferma richiede una spunta esplicita con questo testo. */
  readonly acknowledgement: string | null;
  /**
   * Impronta del contesto mostrato (scenario, posizione, piano, protezioni, modalità,
   * bot, feed e testo della conferma). Il consenso vale solo per questa impronta.
   */
  readonly contextToken: string;
}

export type CommandPreview =
  | { readonly kind: 'BLOCKED'; readonly reason: string }
  | { readonly kind: 'IMMEDIATE' }
  | { readonly kind: 'CONFIRM'; readonly confirmation: ConfirmationPreview };

export type CommandResult =
  | { readonly status: 'APPLIED'; readonly message: string }
  | { readonly status: 'DUPLICATE'; readonly message: string }
  | { readonly status: 'REJECTED'; readonly message: string }
  /** Il contesto è cambiato dopo l'anteprima: nessun effetto, serve una nuova conferma. */
  | { readonly status: 'CONTEXT_CHANGED'; readonly message: string };

export interface DispatchOptions {
  readonly acknowledged?: boolean;
  readonly contextToken?: string;
}

/** Fonte dei dati della dashboard. Un'implementazione futura può sostituire quella simulata. */
export interface DashboardProvider {
  getSnapshot(): Snapshot;
  subscribe(listener: () => void): () => void;
  preview(intent: Intent): CommandPreview;
  /**
   * `requestId` rende idempotente il comando: lo stesso id applicato due volte
   * (doppio click, invio ripetuto) produce un solo effetto. Un comando che richiede
   * conferma va accompagnato dal `contextToken` dell'anteprima approvata: se il contesto
   * nel frattempo è cambiato il comando non viene applicato.
   */
  dispatch(intent: Intent, requestId: string, options?: DispatchOptions): CommandResult;
}

/** Comandi riservati al pannello di simulazione, distinti dai comandi ordinari. */
export interface SimulationControls {
  listCheckpoints(): readonly CheckpointInfo[];
  initialCheckpointId(): string;
  currentCheckpointId(): string;
  selectCheckpoint(id: string): void;
  setFeedCondition(condition: FeedCondition): void;
  feedCondition(): FeedCondition;
  reset(): void;
}

export type FeedCondition = 'OK' | 'STALE' | 'DISCONNECTED';

export interface CheckpointInfo {
  readonly id: string;
  readonly scenarioId: string;
  readonly scenarioLabel: string;
  readonly label: string;
  readonly description: string;
}
