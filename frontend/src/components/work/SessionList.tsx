import { useState } from 'react';

import type { WorkSession } from '../../api/work';
import {
  useAddSession,
  useDeleteSession,
  useWorkSessions,
} from '../../hooks/useWork';
import { localToday, shortDate } from '../../utils/format';
import { clockTime, daysAgo, hm } from './format';

const SOURCE: Record<string, string> = {
  tap: 'Raccourci',
  manual: 'Saisie',
  import: 'Import',
};

function Row({ row }: { row: WorkSession }) {
  const del = useDeleteSession();
  return (
    <tr>
      <td>{shortDate(row.date_key)}</td>
      <td>{clockTime(row.start_at)}</td>
      <td>{row.end_at ? clockTime(row.end_at) : 'en cours'}</td>
      <td>{hm(row.hours)}</td>
      <td className="muted">{SOURCE[row.source] ?? row.source}</td>
      <td>
        <button
          className="btn ghost"
          title="Supprimer"
          onClick={() => del.mutate(row.id)}
        >
          ×
        </button>
      </td>
    </tr>
  );
}

function When(props: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <input
      className="input"
      type="datetime-local"
      aria-label={props.label}
      title={props.label}
      value={props.value}
      onChange={(e) => props.onChange(e.target.value)}
    />
  );
}

function AddSession() {
  const add = useAddSession();
  const [start, setStart] = useState('');
  const [end, setEnd] = useState('');
  const save = () =>
    add.mutate(
      { start_at: start, end_at: end || null },
      { onSuccess: () => setEnd('') },
    );
  return (
    <div className="quick">
      <When label="Embauche" value={start} onChange={setStart} />
      <When label="Débauche" value={end} onChange={setEnd} />
      <button className="btn" disabled={!start} onClick={save}>
        Ajouter la session
      </button>
      {add.error && <span className="error">{add.error.message}</span>}
    </div>
  );
}

/** The last 30 days of sessions, to check, add or remove. */
export function SessionList() {
  const rows = useWorkSessions(daysAgo(29), localToday()).data ?? [];
  return (
    <section className="card">
      <h2>Sessions (30 derniers jours)</h2>
      <AddSession />
      <div className="table-wrap">
        <table className="data-table">
          <tbody>
            {rows.map((row) => (
              <Row key={row.id} row={row} />
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
