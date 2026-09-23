import { useState } from 'react';

import type { Place, WorkSession } from '../../api/work';
import {
  useAddSession,
  useDeleteSession,
  useWorkSessions,
} from '../../hooks/useWork';
import { shortDate } from '../../utils/format';
import { useRange } from '../../utils/range';
import { DateRange } from '../DateRange';
import { usePaging } from '../Paging';
import { clockTime, hm } from './format';

const SOURCE: Record<string, string> = {
  tap: 'Raccourci',
  manual: 'Saisie',
  import: 'Import',
  edited: 'Corrigée',
};

function Row({ row }: { row: WorkSession }) {
  const del = useDeleteSession();
  return (
    <tr>
      <td>{shortDate(row.date_key)}</td>
      <td>{clockTime(row.start_at)}</td>
      <td>{row.end_at ? clockTime(row.end_at) : 'en cours'}</td>
      <td>{hm(row.hours)}</td>
      <td>
        {row.place === 'remote' && <span className="badge">à distance</span>}
      </td>
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

function Remote(props: { on: boolean; set: (on: boolean) => void }) {
  return (
    <label className="muted">
      <input
        type="checkbox"
        checked={props.on}
        onChange={(e) => props.set(e.target.checked)}
      />{' '}
      À distance (même après une journée sur place)
    </label>
  );
}

function AddSession() {
  const add = useAddSession();
  const [start, setStart] = useState('');
  const [end, setEnd] = useState('');
  const [remote, setRemote] = useState(false);
  const place: Place = remote ? 'remote' : 'site';
  const save = () =>
    add.mutate(
      { start_at: start, end_at: end || null, place },
      { onSuccess: () => setEnd('') },
    );
  return (
    <div className="quick">
      <When label="Embauche" value={start} onChange={setStart} />
      <When label="Débauche" value={end} onChange={setEnd} />
      <Remote on={remote} set={setRemote} />
      <button className="btn" disabled={!start} onClick={save}>
        Ajouter la session
      </button>
      {add.error && <span className="error">{add.error.message}</span>}
    </div>
  );
}

/** The sessions of a period, to check, add or remove. */
export function SessionList() {
  const [range, setRange] = useRange(30);
  const all = useWorkSessions(range).data ?? [];
  const { page: rows, bar } = usePaging(all);
  return (
    <section className="card">
      <h2>Sessions ({all.length})</h2>
      <AddSession />
      <DateRange value={range} onChange={setRange} />
      {bar}
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
