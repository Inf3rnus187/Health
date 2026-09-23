import { useState } from 'react';

import { localToday } from './format';
import { readStored, writeStored } from './stored';

/** A period: ``start`` empty means "from the beginning". */
export interface Range {
  start: string;
  end: string;
}

/** The local day ``days`` before today. */
export function daysBefore(days: number): string {
  const [y, m, d] = localToday().split('-').map(Number);
  const day = new Date(Date.UTC(y ?? 0, (m ?? 1) - 1, (d ?? 1) - days));
  return day.toISOString().slice(0, 10);
}

/** The last ``days`` days up to today (null: from the beginning). */
export function lastDays(days: number | null): Range {
  return {
    start: days === null ? '' : daysBefore(days - 1),
    end: localToday(),
  };
}

/** The day ``days`` after ``day`` (negative: before). */
function shift(day: string, days: number): string {
  const [y, m, d] = day.split('-').map(Number);
  const at = new Date(Date.UTC(y ?? 0, (m ?? 1) - 1, (d ?? 1) + days));
  return at.toISOString().slice(0, 10);
}

function daysBetween(first: string, last: string): number {
  return Math.round((Date.parse(last) - Date.parse(first)) / 86_400_000);
}

/** A period saved with the day it was chosen on. */
interface Saved extends Range {
  on: string;
}

/** The saved period: one that ended "today" when chosen (7 j, 30 j,
 * Tout, up to today) still ends today, as long; a past one is kept. */
function restore(key: string, days: number | null): Range {
  const saved = readStored<Saved>(`range.${key}`);
  if (!saved?.end || !saved.on) return lastDays(days);
  const today = localToday();
  if (saved.end !== saved.on || saved.on === today) {
    return { start: saved.start, end: saved.end };
  }
  const moved = daysBetween(saved.on, today);
  return { start: saved.start ? shift(saved.start, moved) : '', end: today };
}

/** A period state, starting on the last ``days`` days (null: all);
 * ``key``: the period is kept across reloads (per page and card). */
export function useRange(
  days: number | null,
  key: string,
): [Range, (r: Range) => void] {
  const [range, setRange] = useState<Range>(() => restore(key, days));
  const set = (next: Range) => {
    setRange(next);
    writeStored(`range.${key}`, { ...next, on: localToday() });
  };
  return [range, set];
}

/** ``start=…&end=…`` for an API query (no start: from the beginning). */
export function rangeQuery(range: Range): string {
  const start = range.start ? `start=${range.start}&` : '';
  return `${start}end=${range.end}`;
}
