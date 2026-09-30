import type { ButtonHTMLAttributes, CSSProperties, ReactNode } from "react";
import { Icon, IconName } from "./Icon";

// Internal design system. Three surface materials carry product truth:
//   real      – solid surface: operational state/evidence that exists today;
//   synthetic – violet hatching: DEMO scaffolding, never market evidence;
//   pending   – dashed blueprint: reserved for capabilities not yet built.

export type Tone = "pos" | "neg" | "warn" | "info" | "neutral" | "brand" | "synthetic" | "pending";
export type Material = "real" | "synthetic" | "pending";

export function cx(...c: (string | false | null | undefined)[]): string {
  return c.filter(Boolean).join(" ");
}

/** Status pill: always text + (optional) shape, never color alone. */
export function Badge({ tone = "neutral", children, dot, icon, testid, title, className }: {
  tone?: Tone; children: ReactNode; dot?: boolean; icon?: IconName; testid?: string; title?: string; className?: string;
}) {
  return (
    <span className={cx("badge", `tone-${tone}`, className)} data-testid={testid} title={title}>
      {dot && <span className="badge-dot" aria-hidden />}
      {icon && <Icon name={icon} size={12} />}
      {children}
    </span>
  );
}

export function Card({ material = "real", title, eyebrow, icon, actions, children, testid, className, style, id, state }: {
  material?: Material; title?: ReactNode; eyebrow?: ReactNode; icon?: IconName; actions?: ReactNode;
  children?: ReactNode; testid?: string; className?: string; style?: CSSProperties; id?: string; state?: string;
}) {
  return (
    <section className={cx("card", `m-${material}`, className)} data-testid={testid} style={style} id={id} data-state={state}>
      {(title || eyebrow || actions) && (
        <header className="card-head">
          <div className="card-titles">
            {eyebrow && <div className="eyebrow">{eyebrow}</div>}
            {title && (
              <h3 className="card-title">
                {icon && <Icon name={icon} size={16} />}
                {title}
              </h3>
            )}
          </div>
          {actions && <div className="card-actions">{actions}</div>}
        </header>
      )}
      {children}
    </section>
  );
}

export function PageHeader({ eyebrow, title, lede, meta, actions }: {
  eyebrow?: ReactNode; title: ReactNode; lede?: ReactNode; meta?: ReactNode; actions?: ReactNode;
}) {
  return (
    <header className="page-head">
      <div className="page-head-main">
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h1 className="page-title">{title}</h1>
        {lede && <p className="page-lede">{lede}</p>}
      </div>
      {(meta || actions) && (
        <div className="page-head-side">
          {meta}
          {actions}
        </div>
      )}
    </header>
  );
}

export function SectionHeader({ title, hint, actions }: { title: ReactNode; hint?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="section-head">
      <h2 className="section-title">{title}</h2>
      {hint && <span className="section-hint">{hint}</span>}
      {actions && <div className="section-actions">{actions}</div>}
    </div>
  );
}

export function Metric({ label, value, hint, testid, tone, mono = true, title }: {
  label: ReactNode; value: ReactNode; hint?: ReactNode; testid?: string; tone?: Tone; mono?: boolean; title?: string;
}) {
  return (
    <div className="metric">
      <div className="metric-label">{label}</div>
      <div className={cx("metric-value", mono && "mono", tone && `text-${tone}`)} data-testid={testid} title={title}>{value}</div>
      {hint && <div className="metric-hint">{hint}</div>}
    </div>
  );
}

export function Notice({ tone = "info", icon, title, children, testid, className }: {
  tone?: Tone; icon?: IconName; title?: ReactNode; children?: ReactNode; testid?: string; className?: string;
}) {
  const fallback: IconName = tone === "neg" ? "x" : tone === "warn" ? "alert" : tone === "pos" ? "check" : "eye";
  return (
    <div className={cx("notice", `tone-${tone}`, className)} role={tone === "neg" ? "alert" : undefined} data-testid={testid}>
      <Icon name={icon ?? fallback} size={16} />
      <div className="notice-body">
        {title && <div className="notice-title">{title}</div>}
        {children && <div className="notice-text">{children}</div>}
      </div>
    </div>
  );
}

export function EmptyState({ icon = "layers", title, children, testid, action }: {
  icon?: IconName; title: ReactNode; children?: ReactNode; testid?: string; action?: ReactNode;
}) {
  return (
    <div className="empty" data-testid={testid}>
      <div className="empty-icon"><Icon name={icon} size={20} /></div>
      <div className="empty-title">{title}</div>
      {children && <div className="empty-text">{children}</div>}
      {action}
    </div>
  );
}

export function Button({ variant = "primary", icon, children, className, ...rest }: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger"; icon?: IconName;
}) {
  return (
    <button type="button" className={cx("btn", `btn-${variant}`, className)} {...rest}>
      {icon && <Icon name={icon} size={15} />}
      <span>{children}</span>
    </button>
  );
}

export function Field({ label, children, hint }: { label: ReactNode; children: ReactNode; hint?: ReactNode }) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      {children}
      {hint && <span className="field-hint">{hint}</span>}
    </label>
  );
}

export function Skeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="skeleton" aria-busy="true" aria-label="Loading">
      {Array.from({ length: lines }, (_, i) => <div key={i} className="skeleton-line" style={{ width: `${90 - i * 17}%` }} />)}
    </div>
  );
}

export function Mono({ children, title, className }: { children: ReactNode; title?: string; className?: string }) {
  return <span className={cx("mono", className)} title={title}>{children}</span>;
}

/** Map backend status strings to semantic tones (text is always shown alongside). */
export function statusTone(status: string | null | undefined): Tone {
  switch ((status ?? "").toLowerCase()) {
    case "completed": case "clean": case "ok": case "info": case "connected": case "subscribed":
      return "pos";
    case "running": case "stepping": case "queued":
      return "info";
    case "paused": case "pausing": case "warning": case "degraded": case "partial": case "cancel_requested": case "connecting":
      return "warn";
    case "failed": case "invalid": case "recovering": case "error": case "disconnected":
      return "neg";
    default:
      return "neutral";
  }
}
