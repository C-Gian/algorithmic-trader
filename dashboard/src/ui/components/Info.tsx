import { useEffect, useId, useLayoutEffect, useRef, useState, type CSSProperties, type ReactNode } from 'react';

const WIDTH = 340;

/**
 * Icona «i» con spiegazione in italiano semplice: compare al passaggio del mouse, al focus da
 * tastiera e al clic (che la fissa). Esc, un secondo clic o l'uscita dal focus la chiudono senza
 * spostare la pagina. Il riquadro è posizionato rispetto alla finestra, così una tabella scorrevole
 * non lo taglia. Il testo resta un complemento: i valori tecnici non vengono sostituiti.
 */
export function Info({ label, children }: { label: string; children: ReactNode }) {
  const [pinned, setPinned] = useState(false);
  const [hover, setHover] = useState(false);
  const [pos, setPos] = useState<CSSProperties>({});
  const btn = useRef<HTMLButtonElement>(null);
  const id = useId();
  const shown = pinned || hover;

  const place = () => {
    const r = btn.current?.getBoundingClientRect();
    if (!r) return;
    const vw = typeof window === 'undefined' ? 1366 : window.innerWidth;
    setPos({ position: 'fixed', top: r.bottom + 6, left: Math.max(8, Math.min(r.left - 8, vw - WIDTH - 16)) });
  };
  useLayoutEffect(() => {
    if (shown) place();
  }, [shown]);
  useEffect(() => {
    if (!shown) return;
    window.addEventListener('scroll', place, true);
    window.addEventListener('resize', place);
    return () => {
      window.removeEventListener('scroll', place, true);
      window.removeEventListener('resize', place);
    };
  }, [shown]);

  return (
    <span className="info" onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}>
      <button
        ref={btn}
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
        <span role="tooltip" id={id} className="info-pop" style={pos}>
          {children}
        </span>
      )}
    </span>
  );
}
