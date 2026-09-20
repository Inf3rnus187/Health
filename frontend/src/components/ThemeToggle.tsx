import { useTheme } from '../hooks/useTheme';

export function ThemeToggle() {
  const { mode, toggle } = useTheme();
  const label = mode === 'dark' ? '☀️ Clair' : '🌙 Sombre';
  return (
    <button className="btn ghost" onClick={toggle} aria-label="Thème">
      {label}
    </button>
  );
}
