import { useId, useState, type ReactNode } from 'react';

/**
 * Icona «i» con spiegazione in italiano semplice: compare al passaggio del mouse, al focus da
 * tastiera e al clic (che la fissa). Esc, un secondo clic o l'uscita dal focus la chiudono senza
 * spostare la pagina. Il testo resta un complemento: i valori tecnici non vengono sostituiti.
 */
export function Info({ label, children }: { label: string; children: ReactNode }) {
  const [pinned, setPinned] = useState(false);
  const [hover, setHover] = useState(false);
  const id = useId();
  const shown = pinned || hover;
  return (
    <span className="info" onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}>
      <button
        type="button"
        className="info-btn"
        aria-label={`Spiegazione: ${label}`}
        aria-expanded={shown}
        aria-describedby={shown ? id : undefined}
        onClick={() => setPinned((p) => !p)}
        onFocus={() => setHover(true)}
        onBlur={() => {
          setHover(false);
          setPinned(false);
        }}
        onKeyDown={(e) => {
          if (e.key === 'Escape') {
            e.stopPropagation();
            setHover(false);
            setPinned(false);
          }
        }}
      >
        i
      </button>
      {shown && (
        <span role="tooltip" id={id} className="info-pop">
          {children}
        </span>
      )}
    </span>
  );
}
