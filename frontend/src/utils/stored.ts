import { useState } from 'react';

const PREFIX = 'phoenix.view.';

/** A value saved in this browser (null: none, or storage unavailable). */
export function readStored<T>(key: string): T | null {
  try {
    const raw = localStorage.getItem(PREFIX + key);
    return raw === null ? null : (JSON.parse(raw) as T);
  } catch {
    return null; // private mode, blocked storage, a value from before
  }
}

export function writeStored(key: string, value: unknown): void {
  try {
    localStorage.setItem(PREFIX + key, JSON.stringify(value));
  } catch {
    // storage full or blocked: the choice simply is not remembered
  }
}

/** A view choice (tab, filter, search) kept across reloads, per key.
 *
 * ``allowed``: the values it may take (a stored one no longer offered
 * falls back to ``initial``). */
export function useStored<T extends string = string>(
  key: string,
  initial: NoInfer<T>,
  allowed?: readonly string[],
): [T, (value: T) => void] {
  const [value, setValue] = useState<T>(() => {
    const saved = readStored<T>(key);
    const ok =
      typeof saved === 'string' && (!allowed || allowed.includes(saved));
    return ok ? saved : initial;
  });
  const set = (next: T) => {
    setValue(next);
    writeStored(key, next);
  };
  return [value, set];
}
