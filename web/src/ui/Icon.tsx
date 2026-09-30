// Small hand-drawn stroke icon set (24px grid, currentColor). Decorative unless labelled.

const PATHS = {
  market: "M3 20h18M5 16l4-5 4 3 6-8M15 6h4v4",
  replay: "M4 12a8 8 0 1 0 2.3-5.6M4 4v4h4M10 9v6l5-3z",
  data: "M4 6c0-1.7 3.6-3 8-3s8 1.3 8 3-3.6 3-8 3-8-1.3-8-3zM4 6v6c0 1.7 3.6 3 8 3s8-1.3 8-3V6M4 12v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6",
  recorder: "M12 12m-3 0a3 3 0 1 0 6 0a3 3 0 1 0-6 0M5.6 5.6a9 9 0 0 0 0 12.8M18.4 5.6a9 9 0 0 1 0 12.8M8.5 8.5a5 5 0 0 0 0 7M15.5 8.5a5 5 0 0 1 0 7",
  check: "M5 12.5l4.5 4.5L19 7",
  alert: "M12 4l9 16H3zM12 10v4M12 17.5v.5",
  x: "M6 6l12 12M18 6L6 18",
  clock: "M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0-18 0M12 7v5l3 2",
  lock: "M6 11h12v9H6zM8.5 11V8a3.5 3.5 0 0 1 7 0v3",
  flask: "M9 3h6M10 3v6L4.5 18.5A1.7 1.7 0 0 0 6 21h12a1.7 1.7 0 0 0 1.5-2.5L14 9V3M7 15h10",
  file: "M6 3h8l4 4v14H6zM14 3v4h4M9 12h6M9 16h6",
  link: "M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1",
  pulse: "M3 12h4l2.5-6 5 12 2.5-6h4",
  layers: "M12 3l9 5-9 5-9-5zM3 13l9 5 9-5",
  shield: "M12 3l8 3v6c0 4.5-3.4 8-8 9-4.6-1-8-4.5-8-9V6z",
  compass: "M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0-18 0M15.5 8.5l-2 5-5 2 2-5z",
  target: "M12 12m-8 0a8 8 0 1 0 16 0a8 8 0 1 0-16 0M12 12m-4 0a4 4 0 1 0 8 0a4 4 0 1 0-8 0M12 12h.01",
  scale: "M12 4v16M5 20h14M6 8h12M6 8l-3 6a3 3 0 0 0 6 0zM18 8l-3 6a3 3 0 0 0 6 0z",
  branch: "M6 4v10M6 14a4 4 0 0 0 4 4h4M6 14c0-3 2-5 6-5h2M16 9m-2 0a2 2 0 1 0 4 0a2 2 0 1 0-4 0M16 18m-2 0a2 2 0 1 0 4 0a2 2 0 1 0-4 0",
  eye: "M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12zM12 12m-3 0a3 3 0 1 0 6 0a3 3 0 1 0-6 0",
  play: "M7 5l12 7-12 7z",
  pause: "M8 5v14M16 5v14",
  step: "M6 5l9 7-9 7zM18 5v14",
  stop: "M6 6h12v12H6z",
  chevron: "M9 6l6 6-6 6",
  cpu: "M7 7h10v10H7zM10 3v4M14 3v4M10 17v4M14 17v4M3 10h4M3 14h4M17 10h4M17 14h4",
  gauge: "M4 18a8 8 0 1 1 16 0M12 18l4-6M7 13.5h.01M12 10v.01M17 13.5h.01M4 21h16",
  copy: "M9 9h11v11H9zM5 15H4V4h11v1",
  download: "M12 4v11M7.5 10.5 12 15l4.5-4.5M5 20h14",
  refresh: "M20 11a8 8 0 0 0-14.3-4.3L4 8.5M4 4v4.5h4.5M4 13a8 8 0 0 0 14.3 4.3l1.7-1.8M20 20v-4.5h-4.5",
};

export type IconName = keyof typeof PATHS;

export function Icon({ name, size = 16, label, className }: { name: IconName; size?: number; label?: string; className?: string }) {
  return (
    <svg
      className={`icon ${className ?? ""}`}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.6}
      strokeLinecap="round"
      strokeLinejoin="round"
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
    >
      <path d={PATHS[name]} />
    </svg>
  );
}
