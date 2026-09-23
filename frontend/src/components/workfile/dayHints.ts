import type { IncompleteDay } from '../../api/workfile';
import { localStamp } from '../../utils/datetime';

/** A time to pick for a day to complete (``at`` empty: time unknown). */
export interface Hint {
  key: string;
  label: string;
  title: string;
  at: string;
}

/** The date key ``days`` after ``day``. */
function shiftDay(day: string, days: number): string {
  const [y, m, d] = day.split('-').map(Number);
  const at = new Date(Date.UTC(y ?? 0, (m ?? 1) - 1, (d ?? 1) + days));
  return at.toISOString().slice(0, 10);
}

/** ``HH:MM`` put on the right side of the known half (after midnight…). */
export function placeClock(row: IncompleteDay, clock: string): string {
  const stamp = `${row.date_key}T${clock}`;
  if (row.context.missing === 'end' && row.start_at) {
    const after = stamp > localStamp(row.start_at);
    return after ? stamp : `${shiftDay(row.date_key, 1)}T${clock}`;
  }
  if (row.end_at) {
    const before = stamp < localStamp(row.end_at);
    return before ? stamp : `${shiftDay(row.date_key, -1)}T${clock}`;
  }
  return stamp;
}

/** Clock times from the body and from habit, for the missing half. */
export function clockHints(row: IncompleteDay): Hint[] {
  const c = row.context;
  const start = c.missing === 'start';
  const found: [string, string | null][] = start
    ? [
        ['Réveil', c.wake_time],
        ['Premiers pas', c.activity.first],
      ]
    : [
        ['Derniers pas', c.activity.last],
        ['Coucher', c.bedtime],
      ];
  found.push(
    [`Habituel le ${c.usual.weekday}`, c.usual.that_weekday],
    ['Habituel (tous les jours)', c.usual.overall],
  );
  return found
    .filter((f): f is [string, string] => f[1] !== null)
    .map(([what, clock]) => ({
      key: what,
      label: `${what} ${clock}`,
      title: what,
      at: placeClock(row, clock),
    }));
}
