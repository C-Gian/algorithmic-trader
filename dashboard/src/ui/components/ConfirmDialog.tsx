import { useEffect, useRef, useState } from 'react';
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

const NOTICE_ICON: Partial<Record<Tone, IconName>> = { accent: 'info17', warning: 'triangleAlert17', negative: 'circleAlert17Red' };

/** Conferma operativa (nodi Figma 2:10298, 2:10335, 2:10372): un solo dialogo alla volta. */
export function ConfirmDialog({
  preview,
  onConfirm,
  onCancel,
}: {
  preview: ConfirmationPreview;
  onConfirm: (acknowledged: boolean) => void;
  onCancel: () => void;
}) {
  const [ack, setAck] = useState(false);
  const [busy, setBusy] = useState(false);
  const cancelRef = useRef<HTMLButtonElement>(null);
  const symbol = SYMBOL[preview.icon];
  const needsAck = preview.acknowledgement !== null;

  useEffect(() => {
    cancelRef.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onCancel();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onCancel]);

  const confirm = () => {
    if (busy) return;
    setBusy(true);
    onConfirm(ack);
  };

  return (
    <div className="overlay" onClick={onCancel}>
      <div className="dialog" role="dialog" aria-modal="true" aria-labelledby="confirm-title" onClick={(e) => e.stopPropagation()}>
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
