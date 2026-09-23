import { useState } from 'react';

import { localToday } from './format';

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

/** A period state, starting on the last ``days`` days (null: all). */
export function useRange(days: number | null): [Range, (r: Range) => void] {
  return useState<Range>(() => lastDays(days));
}

/** ``start=…&end=…`` for an API query (no start: from the beginning). */
export function rangeQuery(range: Range): string {
  const start = range.start ? `start=${range.start}&` : '';
  return `${start}end=${range.end}`;
}
