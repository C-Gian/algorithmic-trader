import type { ReactNode } from 'react';
import { navigate } from './router';

/**
 * Collegamento interno: vero indirizzo #/... (nuova scheda possibile), navigazione nella cronologia.
 * `back` segna un ritorno interno a una vista già vista: si ritrova lo scorrimento come con Indietro.
 */
export function Link({ to, children, className = 'link', ariaLabel, back = false }: { to: string; children: ReactNode; className?: string; ariaLabel?: string; back?: boolean }) {
  return (
    <a
      href={`#${to}`}
      className={className}
      aria-label={ariaLabel}
      onClick={(e) => {
        if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
        e.preventDefault();
        navigate(to, { restore: back });
      }}
    >
      {children}
    </a>
  );
}
