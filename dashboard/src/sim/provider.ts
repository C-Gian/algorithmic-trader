/**
 * Provider simulato: carica uno scenario, espone snapshot e accetta intenzioni.
 * Ogni ricarica parte dal checkpoint iniziale dichiarato: nessuna persistenza.
 */
import type { CheckpointInfo, CommandPreview, CommandResult, DashboardProvider, FeedCondition, Intent, SimulationControls } from '../contract/provider';
import type { Snapshot } from '../contract/types';
import { actionStates, commandEvents, previewAction } from './commands';
import type { CheckpointDef, ScenarioDef, SimState } from './engine';
import { applyEvent, buildCheckpointState, isPendingExit, nextExecutionTick } from './engine';
import { INITIAL_CHECKPOINT_ID, SCENARIOS } from './fixtures/scenarios';
import { buildSnapshot } from './snapshot';

export interface SimulatedProviderOptions {
  /** Ritardo fra richiesta d'uscita ed eseguito simulato. 0 = completamento solo manuale (test). */
  readonly exitDelayMs?: number;
  readonly scenarios?: readonly ScenarioDef[];
  readonly initialCheckpointId?: string;
}

const FEED_SHIFT_MS: Record<Exclude<FeedCondition, 'OK'>, number> = { STALE: 2 * 60_000, DISCONNECTED: 3 * 60_000 };

export class SimulatedProvider implements DashboardProvider, SimulationControls {
  private readonly scenarios: readonly ScenarioDef[];
  private readonly initialId: string;
  private readonly exitDelayMs: number;
  private scenario!: ScenarioDef;
  private state!: SimState;
  private snapshot!: Snapshot;
  private listeners = new Set<() => void>();
  private timer: ReturnType<typeof setTimeout> | null = null;

  constructor(options: SimulatedProviderOptions = {}) {
    this.scenarios = options.scenarios ?? SCENARIOS;
    this.initialId = options.initialCheckpointId ?? INITIAL_CHECKPOINT_ID;
    this.exitDelayMs = options.exitDelayMs ?? 1200;
    this.selectCheckpoint(this.initialId);
  }

  /* ------------------------------------------------------ DashboardProvider */

  getSnapshot = (): Snapshot => this.snapshot;

  subscribe = (listener: () => void): (() => void) => {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  };

  preview(intent: Intent): CommandPreview {
    return previewAction(this.state, this.scenario.market, intent.action);
  }

  dispatch(intent: Intent, requestId: string, options: { acknowledged?: boolean } = {}): CommandResult {
    if (this.state.processedRequests.includes(requestId)) {
      return { status: 'DUPLICATE', message: 'Comando già ricevuto: nessun effetto ripetuto.' };
    }
    const status = actionStates(this.state)[intent.action];
    if (!status.enabled) return { status: 'REJECTED', message: status.reason ?? 'Azione non disponibile.' };
    const preview = this.preview(intent);
    if (preview.kind === 'CONFIRM' && preview.confirmation.acknowledgement && !options.acknowledged) {
      return { status: 'REJECTED', message: 'Serve la conferma esplicita richiesta dal dialogo.' };
    }
    let next = this.state;
    for (const ev of commandEvents(next, intent.action, requestId)) next = applyEvent(next, ev);
    next = { ...next, processedRequests: [...next.processedRequests, requestId] };
    this.commit(next);
    this.scheduleExitCompletion();
    return { status: 'APPLIED', message: 'Comando simulato applicato.' };
  }

  /**
   * Completa l'eventuale uscita richiesta con l'eseguito predeterminato. Senza feed
   * aggiornato non accade nulla: la richiesta resta in attesa di conferma.
   */
  completePendingExit(): boolean {
    this.clearTimer();
    const pending = this.state.orders.find(isPendingExit);
    if (!pending || this.state.feed.status !== 'OK') return false;
    const tick = nextExecutionTick(this.scenario.market, this.state.clock);
    this.commit(applyEvent(this.state, { kind: 'FILL', id: `fill-${pending.id}`, at: tick.at, orderId: pending.id, price: tick.price }));
    return true;
  }

  /* ----------------------------------------------------- SimulationControls */

  listCheckpoints(): readonly CheckpointInfo[] {
    return this.scenarios.flatMap((s) =>
      s.checkpoints.map((c) => ({ id: c.id, scenarioId: s.id, scenarioLabel: s.label, label: c.label, description: c.description })),
    );
  }

  initialCheckpointId(): string {
    return this.initialId;
  }

  currentCheckpointId(): string {
    return this.state.checkpointId;
  }

  selectCheckpoint(id: string): void {
    const found = this.find(id);
    this.clearTimer();
    this.scenario = found.scenario;
    this.commit(buildCheckpointState(found.scenario, found.checkpoint));
  }

  reset(): void {
    this.selectCheckpoint(this.initialId);
  }

  feedCondition(): FeedCondition {
    return this.state.feed.status;
  }

  /** Alterazione controllata del feed sul checkpoint corrente, conservando ultimo valore e orario. */
  setFeedCondition(condition: FeedCondition): void {
    const current = this.state.feed.status;
    if (condition === current) return;
    this.clearTimer();
    let next: SimState;
    if (condition === 'OK') {
      next = applyEvent(this.state, { kind: 'FEED', id: `feed-ok-${this.state.seq}`, at: this.state.clock, status: 'OK', observedAt: this.state.clock });
    } else {
      const shift = current === 'OK' ? FEED_SHIFT_MS[condition] : 60_000;
      next = applyEvent(this.state, {
        kind: 'FEED',
        id: `feed-${condition}-${this.state.seq}`,
        at: this.state.clock + shift,
        status: condition,
        observedAt: this.state.feed.observedAt,
      });
    }
    this.commit(next);
    this.scheduleExitCompletion();
  }

  /* --------------------------------------------------------------- Interni */

  private find(id: string): { scenario: ScenarioDef; checkpoint: CheckpointDef } {
    for (const scenario of this.scenarios) {
      const checkpoint = scenario.checkpoints.find((c) => c.id === id);
      if (checkpoint) return { scenario, checkpoint };
    }
    throw new Error(`Checkpoint sconosciuto: ${id}`);
  }

  private commit(next: SimState) {
    this.state = next;
    this.snapshot = buildSnapshot(this.scenario, next);
    for (const l of this.listeners) l();
  }

  private scheduleExitCompletion() {
    if (this.exitDelayMs <= 0 || this.timer) return;
    if (!this.state.orders.some(isPendingExit) || this.state.feed.status !== 'OK') return;
    this.timer = setTimeout(() => {
      this.timer = null;
      this.completePendingExit();
    }, this.exitDelayMs);
  }

  private clearTimer() {
    if (this.timer) clearTimeout(this.timer);
    this.timer = null;
  }
}
