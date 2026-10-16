import { useEffect, useRef, useState, type KeyboardEvent as ReactKeyboardEvent, type RefObject } from 'react';
import type { ConfirmationPreview } from '../../contract/provider';
import type { Tone } from '../../contract/types';
import type { IconName } from '../icons';
import { Badge, Icon, Notice } from './primitives';

const SYMBOL: Record<ConfirmationPreview['icon'], { icon: IconName; tone: Tone }> = {
  hand: { icon: 'hand23Blue', tone: 'accent' },
  bot: { icon: 'bot23Blue', tone: 'accent' },
  square: { icon: 'square23Amber', tone: 'warning' },
  close: { icon: 'x16Red', tone: 'negative' },
  partial: { icon: 'receiptText', tone: 'neutral' },
  mode: { icon: 'eye', tone: 'neutral' },
};

const FOCUSABLE = 'button:not([disabled]), input:not([disabled]), select:not([disabled]), [href], [tabindex]:not([tabindex="-1"])';

const NOTICE_ICON: Partial<Record<Tone, IconName>> = { accent: 'info17', warning: 'triangleAlert17', negative: 'circleAlert17Red' };

/**
 * Conferma operativa (nodi Figma 2:10298, 2:10335, 2:10372): un solo dialogo alla volta.
 * Finché è aperto il resto della pagina è inerte e il focus resta nel dialogo; alla chiusura
 * torna al comando che l'ha aperto, se ancora utilizzabile.
 */
export function ConfirmDialog({
  preview,
  onConfirm,
  onCancel,
  background,
}: {
  preview: ConfirmationPreview;
  onConfirm: (acknowledged: boolean) => void;
  onCancel: () => void;
  /** Contenuto della pagina da rendere inerte durante il dialogo. */
  background: RefObject<HTMLElement>;
}) {
  const [ack, setAck] = useState(false);
  const [busy, setBusy] = useState(false);
  const cancelRef = useRef<HTMLButtonElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);
  const symbol = SYMBOL[preview.icon];
  const needsAck = preview.acknowledgement !== null;

  useEffect(() => {
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const page = background.current;
    page?.setAttribute('inert', '');
    page?.setAttribute('aria-hidden', 'true');
    cancelRef.current?.focus();
    return () => {
      page?.removeAttribute('inert');
      page?.removeAttribute('aria-hidden');
      const usable = opener && opener.isConnected && !(opener as HTMLButtonElement).disabled;
      if (usable) opener.focus();
      else page?.querySelector<HTMLElement>('#main-content')?.focus();
    };
  }, [background]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onCancel();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onCancel]);

  /** Tab e Maiusc+Tab ciclano dentro il dialogo (oltre a `inert`, utile dove non è supportato). */
  const trapTab = (e: ReactKeyboardEvent) => {
    if (e.key !== 'Tab' || !dialogRef.current) return;
    const items = [...dialogRef.current.querySelectorAll<HTMLElement>(FOCUSABLE)];
    if (items.length === 0) return;
    const first = items[0];
    const last = items[items.length - 1];
    const active = document.activeElement;
    if (e.shiftKey && (active === first || !dialogRef.current.contains(active))) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && (active === last || !dialogRef.current.contains(active))) {
      e.preventDefault();
      first.focus();
    }
  };

  const confirm = () => {
    if (busy) return;
    setBusy(true);
    onConfirm(ack);
  };

  return (
    <div className="overlay" onClick={onCancel}>
      <div
        className="dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-title"
        ref={dialogRef}
        onKeyDown={trapTab}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="dialog-identity">
          <span className={`action-symbol tone-${symbol.tone}`}>
            <Icon name={symbol.icon} />
          </span>
          <Badge tone="accent">SIMULAZIONE</Badge>
        </div>
        <div>
          <p className="dialog-kicker">{preview.kicker}</p>
          <p className="dialog-title" id="confirm-title">
            {preview.title}
          </p>
        </div>
        <p className="dialog-lead">{preview.lead}</p>
        <div className="dialog-summary">
          {preview.summary.map((line) => (
            <p key={line}>{line}</p>
          ))}
        </div>
        <div className="consequences">
          {preview.consequences.map((c) => (
            <div className="consequence" key={c}>
              <Icon name="check15" />
              <p>{c}</p>
            </div>
          ))}
        </div>
        {preview.notice && (
          <Notice tone={preview.notice.tone} icon={NOTICE_ICON[preview.notice.tone]} title={preview.notice.title}>
            {preview.notice.text}
          </Notice>
        )}
        {needsAck && (
          <label className="ack">
            <input type="checkbox" checked={ack} onChange={(e) => setAck(e.target.checked)} />
            {preview.acknowledgement}
          </label>
        )}
        <div className="sep" />
        <div className="dialog-actions">
          <button ref={cancelRef} type="button" className="btn btn-secondary" onClick={onCancel}>
            Annulla
          </button>
          <button
            type="button"
            className={`btn ${preview.confirmTone === 'danger' ? 'btn-danger' : 'btn-primary'}`}
            disabled={busy || (needsAck && !ack)}
            title={needsAck && !ack ? 'Spunta la conferma esplicita per procedere' : undefined}
            onClick={confirm}
          >
            {preview.confirmLabel}
          </button>
        </div>
        <p className="footnote">Solo simulazione. Non viene inviato alcun ordine reale.</p>
      </div>
    </div>
  );
}
