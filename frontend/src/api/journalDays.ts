// The daily journal (one line per day) and the one-tap counters.
import type { Range } from '../utils/range';
import { api } from './client';

/** The night ended that morning. */
export interface JournalNight {
  asleep_min: number;
  awakenings: number | null;
  /** In how many goes (stretches split by an hour or more awake). */
  blocks: number | null;
  bedtime: string | null;
  wake_time: string | null;
  source: string;
}

export interface JournalDay {
  date: string;
  sleep: JournalNight | null;
  water_bottles: number | null;
  water_l: number | null;
  coffee: number | null;
  cigarettes: number | null;
  pee: number | null;
  meals: number;
  meal_kcal: number | null;
  /** Medication doses taken, and declared not taken. */
  meds_taken: number;
  meds_skipped: number;
}

export interface JournalPage {
  items: JournalDay[];
  /** Days in the period (the pager's total). */
  total: number;
}

export function fetchJournalDays(
  range: Range,
  limit: number,
  offset: number,
): Promise<JournalPage> {
  const params = new URLSearchParams({
    end: range.end,
    limit: String(limit),
    offset: String(offset),
  });
  if (range.start) params.set('start', range.start);
  return api<JournalPage>(`/journal/days?${params.toString()}`);
}

/** Add to today's counter (a negative amount takes one back). */
export const tally = (step: { metric: string; amount: number }) =>
  api<{ total: number }>('/sync/tally', {
    method: 'POST',
    body: JSON.stringify(step),
  });
