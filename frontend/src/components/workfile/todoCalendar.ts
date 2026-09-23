import type { WorkDayLine } from '../../api/work';
import type { IncompleteDay } from '../../api/workfile';
import { localToday } from '../../utils/format';

/** A month shown: "2026-05". */
export type Month = string;

const pad = (n: number) => String(n).padStart(2, '0');

/** The month ``by`` months after ``month`` (negative: before). */
export function shiftMonth(month: Month, by: number): Month {
  const [y, m] = month.split('-').map(Number);
  const at = new Date(Date.UTC(y ?? 0, (m ?? 1) - 1 + by, 1));
  return `${at.getUTCFullYear()}-${pad(at.getUTCMonth() + 1)}`;
}

/** The 12 months ending with ``last``, oldest first. */
export function yearTo(last: Month): Month[] {
  return Array.from({ length: 12 }, (_, i) => shiftMonth(last, i - 11));
}

export const thisMonth = (): Month => localToday().slice(0, 7);

/** The month's last day: "2026-02-28". */
export function monthEnd(month: Month): string {
  const [y, m] = month.split('-').map(Number);
  const last = new Date(Date.UTC(y ?? 0, m ?? 1, 0)).getUTCDate();
  return `${month}-${pad(last)}`;
}

/** The month's days (null: blanks before the 1st; weeks start Monday). */
export function monthDays(month: Month): (string | null)[] {
  const [y, m] = month.split('-').map(Number);
  const first = new Date(Date.UTC(y ?? 0, (m ?? 1) - 1, 1));
  const count = new Date(Date.UTC(y ?? 0, m ?? 1, 0)).getUTCDate();
  const blanks = (first.getUTCDay() + 6) % 7;
  const days = Array.from(
    { length: count },
    (_, i) => `${month}-${pad(i + 1)}`,
  );
  return [...Array<null>(blanks).fill(null), ...days];
}

/** « mai 2026 ». */
export function monthName(month: Month): string {
  const [y, m] = month.split('-').map(Number);
  return new Date(Date.UTC(y ?? 0, (m ?? 1) - 1, 15)).toLocaleDateString(
    'fr-FR',
    { month: 'long', year: 'numeric', timeZone: 'UTC' },
  );
}

/** What a day's pastille says. */
export type Mark = 'todo-none' | 'todo-proof' | 'done' | 'off' | '';

/** Each day's mark: to complete (with / without proof), worked, off. */
export function marks(
  todo: IncompleteDay[],
  days: WorkDayLine[],
): Map<string, Mark> {
  const out = new Map<string, Mark>();
  for (const d of days) {
    if (d.absence) out.set(d.date, 'off');
    else if (d.state === 'complet') out.set(d.date, 'done');
  }
  for (const row of todo) {
    const proof = out.get(row.date_key) === 'todo-proof';
    out.set(
      row.date_key,
      proof || row.context.has_proof ? 'todo-proof' : 'todo-none',
    );
  }
  return out;
}

/** The days to complete, in order (for « précédent / suivant »). */
export function todoDays(todo: IncompleteDay[]): string[] {
  return [...new Set(todo.map((r) => r.date_key))].sort();
}
