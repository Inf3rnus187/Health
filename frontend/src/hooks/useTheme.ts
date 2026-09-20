import { useState } from 'react';

import { applyTheme, initialTheme } from '../theme/mode';
import type { ThemeMode } from '../theme/mode';

/** Current theme plus a toggle that persists and applies the choice. */
export function useTheme(): { mode: ThemeMode; toggle: () => void } {
  const [mode, setMode] = useState<ThemeMode>(initialTheme);
  const toggle = () => {
    const next: ThemeMode = mode === 'dark' ? 'light' : 'dark';
    applyTheme(next);
    setMode(next);
  };
  return { mode, toggle };
}
