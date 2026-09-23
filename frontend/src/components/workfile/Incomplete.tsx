import { useState } from 'react';

import type { WorkSession } from '../../api/work';
import { useDeleteSession, useWorkSessions } from '../../hooks/useWork';
import { type EvidenceItem, TRACE_KINDS } from '../../api/workfile';
import { useCompleteSession, useEvidence } from '../../hooks/useWorkFile';
import { localToday, shortDate } from '../../utils/format';
import { clockTime } from '../work/format';
import { Input } from './fields';

function Known({ row }: { row: WorkSession }) {
  return (
    <>
      {shortDate(row.date_key)} —{' '}
      {row.start_at
        ? `embauche ${clockTime(row.start_at)}, débauche ?`
        : `embauche ?, débauche ${clockTime(row.end_at)}`}{' '}
    </>
  );
}

interface ActionProps {
  row: WorkSession;
  field: string;
  at: string;
  ready: boolean;
}

function Complete({ row, field, at, ready }: ActionProps) {
  const complete = useCompleteSession();
  const save = () => complete.mutate({ id: row.id, body: { [field]: at } });
  return (
    <>
      <button className="btn" disabled={!ready} onClick={save}>
        Compléter
      </button>
      {complete.error && (
        <span className="error">{complete.error.message}</span>
      )}
    </>
  );
}

function Actions(props: ActionProps) {
  const del = useDeleteSession();
  return (
    <>
      <Complete {...props} />
      <button className="btn ghost" onClick={() => del.mutate(props.row.id)}>
        Supprimer
      </button>
    </>
  );
}

/** An instant as a local ``YYYY-MM-DDTHH:MM`` (datetime-local value). */
function localStamp(iso: string): string {
  const at = new Date(iso);
  at.setMinutes(at.getMinutes() - at.getTimezoneOffset());
  return at.toISOString().slice(0, 16);
}

/** The next day's date key (a clock-out after midnight). */
function nextDay(day: string): string {
  const at = new Date(`${day}T12:00:00`);
  at.setDate(at.getDate() + 1);
  return at.toISOString().slice(0, 10);
}

function useHints(row: WorkSession): EvidenceItem[] {
  const items = useEvidence().data ?? [];
  const days = row.start_at ? [row.date_key, nextDay(row.date_key)] : [];
  return items.filter((i) => {
    const stamp = localStamp(i.occurred_at);
    const sameDay = stamp.startsWith(row.date_key);
    const morning = stamp.startsWith(days[1] ?? '-') && stamp < `${days[1]}T12`;
    return i.kind in TRACE_KINDS && i.time_known && (sameDay || morning);
  });
}

function Hints(props: { row: WorkSession; pick: (at: string) => void }) {
  const hints = useHints(props.row);
  if (hints.length === 0) {
    return null;
  }
  return (
    <span className="muted">
      {' '}
      · traces :{' '}
      {hints.map((i) => (
        <button
          key={i.id}
          className="chip"
          onClick={() => props.pick(localStamp(i.occurred_at))}
        >
          {i.kind} {localStamp(i.occurred_at).slice(5).replace('T', ' ')}
        </button>
      ))}
    </span>
  );
}

function Fill({ row }: { row: WorkSession }) {
  const [at, setAt] = useState('');
  const field = row.start_at ? 'end_at' : 'start_at';
  const label = field === 'start_at' ? 'Embauche' : 'Débauche';
  return (
    <li>
      <Known row={row} />
      <Hints row={row} pick={setAt} />
      <Input label={label} type="datetime-local" value={at} onChange={setAt} />
      <Actions row={row} field={field} at={at} ready={Boolean(at)} />
    </li>
  );
}

/** Every session with a missing half, to complete from your notes. */
export function Incomplete() {
  const rows = useWorkSessions('2000-01-01', localToday()).data ?? [];
  const todo = rows.filter(
    (r) => r.status === 'missing_start' || r.status === 'missing_end',
  );
  return (
    <section className="card">
      <h2>Journées à compléter ({todo.length})</h2>
      <p className="muted">
        Départ sans arrivée pointée (retour de pause, GPS muet) ou arrivée sans
        départ : ajoutez l’heure manquante d’après vos notes. La session est
        alors marquée « complétée à la main » dans le rapport.
      </p>
      <ul className="care-list">
        {todo.map((row) => (
          <Fill key={row.id} row={row} />
        ))}
      </ul>
    </section>
  );
}
