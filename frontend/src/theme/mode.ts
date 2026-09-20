// Light/dark theme, persisted per browser and applied on <html>.

export type ThemeMode = 'light' | 'dark';

const KEY = 'phoenix-theme';

function stored(): ThemeMode | null {
  try {
    const value = localStorage.getItem(KEY);
    return value === 'dark' || value === 'light' ? value : null;
  } catch {
    return null;
  }
}

function preferred(): ThemeMode {
  const dark = window.matchMedia?.('(prefers-color-scheme: dark)').matches;
  return dark ? 'dark' : 'light';
}

export function initialTheme(): ThemeMode {
  return stored() ?? preferred();
}

export function applyTheme(mode: ThemeMode): void {
  document.documentElement.dataset.theme = mode;
  try {
    localStorage.setItem(KEY, mode);
  } catch {
    /* ignore private-mode storage errors */
  }
}
