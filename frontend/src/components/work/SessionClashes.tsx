import type { WorkSession } from '../../api/work';
import { useWorkSessions } from '../../hooks/useWork';
import { useMergeSession } from '../../hooks/useWorkFile';
import { localStamp } from '../../utils/datetime';

/** A session as local "YYYY-MM-DDTHH:MM" bounds (a lone time: a point). */
type Span = [string, string];

function spanOf(start: string | null, end: string | null): Span | null {
  const a = start || end;
  const b = end || start;
  return a && b ? [a, b] : null;
}

function stored(s: WorkSession): Span | null {
  const at = (iso: string | null) => (iso ? localStamp(iso) : null);
  return spanOf(at(s.start_at), at(s.end_at));
}

function overlaps(a: Span, b: Span): boolean {
  return (a[0] < b[1] && b[0] < a[1]) || (a[0] === b[0] && a[1] === b[1]);
}

function show(stamp: string): string {
  return `${stamp.slice(8, 10)}/${stamp.slice(5, 7)} ${stamp.slice(11, 16)}`;
}

function shift(day: string, days: number): string {
  const [y, m, d] = day.split('-').map(Number);
  const at = new Date(Date.UTC(y ?? 0, (m ?? 1) - 1, (d ?? 1) + days));
  return at.toISOString().slice(0, 10);
}

interface Typed {
  row: WorkSession;
  start: string;
  end: string;
  onDone: () => void;
}

function bounds(list: (string | null)[]): string[] {
  return list.filter((x): x is string => Boolean(x)).sort();
}

/** The one session both would make: first clock-in → last clock-out. */
function union(t: Typed, other: WorkSession): string | null {
  const at = (iso: string | null) => (iso ? localStamp(iso) : null);
  const first = bounds([t.start || null, at(other.start_at)])[0];
  const last = bounds([t.end || null, at(other.end_at)]).pop();
  return first && last && first < last
    ? `${show(first)} → ${show(last)}`
    : null;
}

function Said({ other }: { other: WorkSession }) {
  const span = stored(other);
  return (
    <span className="error">
      Chevauche la session du{' '}
      {span ? `${show(span[0])} → ${show(span[1])}` : ''}
      {other.place === 'remote' ? ' (à distance)' : ''}
      {other.note && ` — ${other.note}`}
    </span>
  );
}

function Clash(props: { t: Typed; other: WorkSession }) {
  const merge = useMergeSession();
  const { t, other } = props;
  const merged = other.place === t.row.place ? union(t, other) : null;
  const typed = { start_at: t.start || null, end_at: t.end || null };
  const run = () =>
    window.confirm(`Réunir en une seule session ${merged} ?`) &&
    merge.mutate(
      { id: t.row.id, other: other.id, ...typed },
      { onSuccess: t.onDone },
    );
  return (
    <li className="quick">
      <Said other={other} />
      {merged && (
        <button className="btn" onClick={run}>
          Réunir : {merged}
        </button>
      )}
      {merge.error && <span className="error">{merge.error.message}</span>}
    </li>
  );
}

/** Sessions the typed times overlap, live; same place: « Réunir ». */
export function SessionClashes(props: Typed) {
  const day = props.row.date_key;
  const range = { start: shift(day, -3), end: shift(day, 3) };
  const all = useWorkSessions(range).data ?? [];
  const mine = spanOf(props.start || null, props.end || null);
  const clashes = all.filter((s) => {
    const theirs = s.id !== props.row.id ? stored(s) : null;
    return mine && theirs && overlaps(mine, theirs);
  });
  if (clashes.length === 0) return null;
  return (
    <ul className="care-list">
      {clashes.map((other) => (
        <Clash key={other.id} t={props} other={other} />
      ))}
    </ul>
  );
}
