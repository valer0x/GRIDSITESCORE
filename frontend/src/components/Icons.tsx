// Minimal inline SVG icon set (lucide-style). Zero dependency.

type IconProps = { size?: number; className?: string };

const base = (size = 16, className = "") =>
  ({
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.75,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    className,
  });

export function IconZap({ size, className }: IconProps) {
  return (
    <svg {...base(size, className)}>
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
    </svg>
  );
}

export function IconBolt({ size, className }: IconProps) {
  return (
    <svg {...base(size, className)}>
      <path d="m13 2-3 7h4l-3 13 10-14h-5l3-6z" />
    </svg>
  );
}

export function IconServer({ size, className }: IconProps) {
  return (
    <svg {...base(size, className)}>
      <rect x="3" y="4" width="18" height="6" rx="1.5" />
      <rect x="3" y="14" width="18" height="6" rx="1.5" />
      <line x1="7" y1="7" x2="7" y2="7" />
      <line x1="7" y1="17" x2="7" y2="17" />
    </svg>
  );
}

export function IconShield({ size, className }: IconProps) {
  return (
    <svg {...base(size, className)}>
      <path d="M12 2.5 4 5v6c0 5 3.5 8.5 8 10.5 4.5-2 8-5.5 8-10.5V5l-8-2.5z" />
    </svg>
  );
}

export function IconPin({ size, className }: IconProps) {
  return (
    <svg {...base(size, className)}>
      <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 1 1 16 0z" />
      <circle cx="12" cy="10" r="3" />
    </svg>
  );
}

export function IconDownload({ size, className }: IconProps) {
  return (
    <svg {...base(size, className)}>
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="7 10 12 15 17 10" />
      <line x1="12" y1="15" x2="12" y2="3" />
    </svg>
  );
}

export function IconSparkles({ size, className }: IconProps) {
  return (
    <svg {...base(size, className)}>
      <path d="M12 3 13.8 8.2 19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3z" />
      <path d="M19 17l.9 2.1L22 20l-2.1.9L19 23l-.9-2.1L16 20l2.1-.9L19 17z" />
    </svg>
  );
}

export function IconInfo({ size, className }: IconProps) {
  return (
    <svg {...base(size, className)}>
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="16" x2="12" y2="12" />
      <line x1="12" y1="8" x2="12.01" y2="8" />
    </svg>
  );
}

export function IconLogo({ size = 22, className }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      className={className}
      aria-hidden
    >
      <defs>
        <linearGradient id="gss-grad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#06b6d4" />
          <stop offset="1" stopColor="#8b5cf6" />
        </linearGradient>
      </defs>
      <path
        d="M12 2 3 7v10l9 5 9-5V7l-9-5z"
        stroke="url(#gss-grad)"
        strokeWidth="1.75"
        strokeLinejoin="round"
        fill="rgba(6,182,212,0.08)"
      />
      <path
        d="M12 7v10M8 9.5l4 2.5 4-2.5M8 14.5l4-2.5 4 2.5"
        stroke="url(#gss-grad)"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  );
}

export const CategoryIcon: Record<string, (p?: IconProps) => JSX.Element> = {
  grid_access: (p = {}) => <IconZap {...p} />,
  energy: (p = {}) => <IconBolt {...p} />,
  digital: (p = {}) => <IconServer {...p} />,
  resilience: (p = {}) => <IconShield {...p} />,
};
