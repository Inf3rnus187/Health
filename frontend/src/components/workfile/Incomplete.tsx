import { useState } from 'react';

import type { WorkSession } from '../../api/work';
import { useDeleteSession, useWorkSessions } from '../../hooks/useWork';
import { TRACE_KINDS } from '../../api/workfile';
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

function Hints({ day }: { day: string }) {
  const items = useEvidence().data ?? [];
  const seen = items.filter(
    (i) => i.kind in TRACE_KINDS && i.occurred_at.slice(0, 10) === day,
  );
  if (seen.length === 0) {
    return null;
  }
  const text = seen
    .map((i) => `${i.kind} ${clockTime(i.occurred_at)}`)
    .join(', ');
  return <span className="muted"> · traces ce jour-là : {text}</span>;
}

function Fill({ row }: { row: WorkSession }) {
  const [time, setTime] = useState('');
  const field = row.start_at ? 'end_at' : 'start_at';
  const label = field === 'start_at' ? 'Embauche' : 'Débauche';
  return (
    <li>
      <Known row={row} />
      <Hints day={row.date_key} />
      <Input label={label} type="time" value={time} onChange={setTime} />
      <Actions
        row={row}
        field={field}
        at={`${row.date_key}T${time}`}
        ready={Boolean(time)}
      />
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
