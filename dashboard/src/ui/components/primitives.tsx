import type { ReactNode } from 'react';
import type { Tone } from '../../contract/types';
import { icons, type IconName } from '../icons';

/** Le SVG Figma hanno già larghezza/altezza: non vengono ridimensionate. */
export function Icon({ name, label }: { name: IconName; label?: string }) {
  return <img className="icon" src={icons[name]} alt={label ?? ''} aria-hidden={label ? undefined : true} />;
}

/** Slot di dimensione fissa con icona centrata alla sua misura naturale. */
export function IconSlot({ name, size }: { name: IconName; size: number }) {
  return (
    <span className="icon-slot" style={{ width: size, height: size }}>
      <Icon name={name} />
    </span>
  );
}

export function Badge({ tone, icon, children, title }: { tone: Tone; icon?: IconName; children: ReactNode; title?: string }) {
  return (
    <span className={`badge tone-${tone}`} title={title}>
      {icon && <Icon name={icon} />}
      {children}
    </span>
  );
}

type ButtonVariant = 'secondary' | 'primary' | 'danger' | 'ghost';

export function Button({
  variant = 'secondary',
  icon,
  children,
  disabled,
  reason,
  onClick,
  pressed,
}: {
  variant?: ButtonVariant;
  icon?: IconName;
  children: ReactNode;
  disabled?: boolean;
  /** Spiegazione mostrata quando il pulsante è disabilitato. */
  reason?: string | null;
  onClick?: () => void;
  pressed?: boolean;
}) {
  return (
    <button
      type="button"
      className={`btn btn-${variant}`}
      disabled={disabled}
      title={disabled && reason ? reason : undefined}
      aria-pressed={pressed}
      onClick={onClick}
    >
      {icon && <Icon name={icon} />}
      {children}
    </button>
  );
}

export function Notice({ tone, icon, title, children }: { tone: Tone; icon?: IconName; title: ReactNode; children?: ReactNode }) {
  return (
    <div className={`notice tone-${tone}`} role="note">
      {icon && <Icon name={icon} />}
      <div className="notice-body">
        <p className="notice-title">{title}</p>
        {children && <p className="t-body">{children}</p>}
      </div>
    </div>
  );
}
