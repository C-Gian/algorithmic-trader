import type { ReactNode } from 'react';
import { navigate } from './router';

/** Collegamento interno: vero indirizzo #/... (nuova scheda possibile), navigazione nella cronologia. */
export function Link({ to, children, className = 'link', ariaLabel }: { to: string; children: ReactNode; className?: string; ariaLabel?: string }) {
  return (
    <a
      href={`#${to}`}
      className={className}
      aria-label={ariaLabel}
      onClick={(e) => {
        if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
        e.preventDefault();
        navigate(to);
      }}
    >
      {children}
    </a>
  );
}
