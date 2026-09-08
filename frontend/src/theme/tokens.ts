// Central design tokens — the single source of truth consumed by the UI
// (§10.1). Layout tokens are also mirrored as CSS variables in styles.css.

export const tokens = {
  color: {
    bg: '#f7f9fc',
    surface: '#ffffff',
    border: '#e2e8f0',
    text: '#0f172a',
    muted: '#64748b',
    primary: '#2563eb',
    danger: '#dc2626',
    grid: '#eef2f7',
  },
  radius: '10px',
  font: "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
} as const;

export function space(steps: number): string {
  return `${steps * 4}px`;
}
