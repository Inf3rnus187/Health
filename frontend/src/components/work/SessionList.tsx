import { useState } from 'react';

import type { Place, WorkSession } from '../../api/work';
import { type Selection, useSelection } from '../../hooks/useSelection';
import { useAddSession, useWorkSessions } from '../../hooks/useWork';
import { useRange } from '../../utils/range';
import { useStored } from '../../utils/stored';
import { BulkBar } from '../Bulk';
import { DateRange } from '../DateRange';
import { usePaging } from '../Paging';
import { SessionRow } from './SessionRow';

const SHOW: Record<string, (s: WorkSession) => boolean> = {
  Toutes: () => true,
  'Corrigées à la main': (s) => s.source === 'edited',
  'À distance': (s) => s.place === 'remote',
  Incomplètes: (s) => s.status.startsWith('missing'),
};

function Filter(props: { value: string; onChange: (v: string) => void }) {
  return (
    <select
      className="input"
      value={props.value}
      onChange={(e) => props.onChange(e.target.value)}
    >
      {Object.keys(SHOW).map((name) => (
        <option key={name}>{name}</option>
      ))}
    </select>
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

function Table(props: { rows: WorkSession[]; sel: Selection }) {
  return (
    <div className="table-wrap">
      <table className="data-table">
        <tbody>
          {props.rows.map((row) => (
            <SessionRow key={row.id} row={row} sel={props.sel} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** The sessions of a period, to check, add, fix or remove (many at once). */
export function SessionList() {
  const [range, setRange] = useRange(30, 'work.sessions');
  const [show, setShow] = useStored(
    'work.sessions.show',
    'Toutes',
    Object.keys(SHOW),
  );
  const sel = useSelection();
  const all = useWorkSessions(range).data ?? [];
  const shown = all.filter(SHOW[show] ?? (() => true));
  const { page: rows, bar } = usePaging(shown);
  const ids = shown.map((s) => s.id);
  return (
    <section className="card">
      <h2>Sessions ({shown.length})</h2>
      <AddSession />
      <DateRange value={range} onChange={setRange} />
      <Filter value={show} onChange={setShow} />
      <BulkBar what="work/sessions" noun="sessions" shown={ids} sel={sel} />
      {bar}
      <Table rows={rows} sel={sel} />
    </section>
  );
}
