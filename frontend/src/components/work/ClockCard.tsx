import type { Place, WorkSession } from '../../api/work';
import {
  useClock,
  useDeleteSession,
  useWorkSessions,
  useWorkStats,
} from '../../hooks/useWork';
import { localToday } from '../../utils/format';
import { clockTime, hm } from './format';

const ACTIONS: {
  label: string;
  body: { kind: 'in' | 'out'; place?: Place };
  off: (open: WorkSession | null) => boolean;
  ghost?: boolean;
}[] = [
  {
    label: 'Embauche maintenant',
    body: { kind: 'in', place: 'site' },
    off: (open) => open !== null,
  },
  {
    label: 'Embauche à distance',
    body: { kind: 'in', place: 'remote' },
    off: (open) => open?.place === 'remote',
    ghost: true,
  },
  {
    label: 'Débauche maintenant',
    body: { kind: 'out' },
    off: (open) => open === null,
  },
];

/** Clock in on site or remote (remote also after the office), out. */
function Buttons({ open }: { open: WorkSession | null }) {
  const clock = useClock();
  return (
    <>
      <div className="quick">
        {ACTIONS.map((a) => (
          <button
            key={a.label}
            className={a.ghost ? 'btn ghost' : 'btn'}
            disabled={clock.isPending || a.off(open)}
            onClick={() => clock.mutate(a.body)}
          >
            {a.label}
          </button>
        ))}
      </div>
      {clock.error && <p className="error">{clock.error.message}</p>}
    </>
  );
}

function said(s: WorkSession): string {
  const start = s.start_at ? clockTime(s.start_at) : '?';
  const end = s.end_at
    ? clockTime(s.end_at)
    : s.status === 'open'
      ? 'en cours'
      : '?';
  const place = s.place === 'remote' ? 'À distance' : 'Sur place';
  return `${place} ${start} → ${end}`;
}

/** One of today's clockings, with « Supprimer » (a wrong tap, a test). */
function Today({ s }: { s: WorkSession }) {
  const del = useDeleteSession();
  const drop = () =>
    window.confirm(`Supprimer ce pointage (${said(s)}) ?`) && del.mutate(s.id);
  return (
    <li className="quick">
      <span>
        {said(s)}
        {s.hours != null && ` · ${hm(s.hours)}`}
      </span>
      <button className="btn ghost" onClick={drop}>
        Supprimer
      </button>
    </li>
  );
}

/** Today's clockings (and one still open since yesterday). */
function Clockings({ open }: { open: WorkSession | null }) {
  const today = localToday();
  const list = useWorkSessions({ start: today, end: today }).data ?? [];
  const all =
    open && !list.some((s) => s.id === open.id) ? [open, ...list] : list;
  if (all.length === 0) return null;
  return (
    <ul className="care-list">
      {all.map((s) => (
        <Today key={s.id} s={s} />
      ))}
    </ul>
  );
}

/** Clock in / out now, and where the day stands. */
export function ClockCard() {
  const today = localToday();
  const stats = useWorkStats({ start: today, end: today }, 35).data;
  const open = stats?.open ?? null;
  return (
    <section className="card">
      <h2>Travail — aujourd’hui : {hm(stats?.total_hours ?? 0)}</h2>
      <p className="muted">
        {open
          ? `Au travail depuis ${clockTime(open.start_at)}` +
            (open.place === 'remote' ? ' (à distance).' : '.')
          : 'Pas en poste.'}
      </p>
      <Buttons open={open} />
      <Clockings open={open} />
    </section>
  );
}
