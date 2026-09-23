import { useTheme } from '../hooks/useTheme';

export function ThemeToggle() {
  const { mode, toggle } = useTheme();
  const dark = mode === 'dark';
  return (
    <button className="btn ghost" onClick={toggle} aria-label="Thème">
      {dark ? '☀️' : '🌙'}
      <span className="wide-only"> {dark ? 'Clair' : 'Sombre'}</span>
    </button>
  );
}
