import { useState } from 'react';

import type { WorkSession } from '../../api/work';
import { type Selection, useSelection } from '../../hooks/useSelection';
import { useWorkSessions } from '../../hooks/useWork';
import { useRange } from '../../utils/range';
import { useStored } from '../../utils/stored';
import { BulkBar } from '../Bulk';
import { DateRange } from '../DateRange';
import { usePaging } from '../Paging';
import { AddSession } from './AddSession';
import { SessionRow } from './SessionRow';

const SHOW: Record<string, (s: WorkSession) => boolean> = {
  Toutes: () => true,
  'Corrigées à la main': (s) => s.source === 'edited',
  'À distance': (s) => s.place === 'remote',
  Incomplètes: (s) => s.status.startsWith('missing'),
};

const FILTERS = Object.keys(SHOW);

function Filter(props: { value: string; onChange: (v: string) => void }) {
  return (
    <select
      className="input"
      aria-label="Filtrer les sessions"
      value={props.value}
      onChange={(e) => props.onChange(e.target.value)}
    >
      {Object.keys(SHOW).map((name) => (
        <option key={name}>{name}</option>
      ))}
    </select>
  );
}

const HEADS = [
  '',
  'Jour',
  'Embauche',
  'Débauche',
  'Durée',
  'Lieu',
  'Origine',
  '',
];

function Table(props: { rows: WorkSession[]; sel: Selection }) {
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            {HEADS.map((h, i) => (
              <th key={i}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {props.rows.map((row) => (
            <SessionRow key={row.id} row={row} sel={props.sel} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Head(props: { count: number; adding: boolean; add: () => void }) {
  return (
    <div className="card-head">
      <h2>Sessions ({props.count})</h2>
      {!props.adding && (
        <button className="btn" onClick={props.add}>
          + Ajouter une session
        </button>
      )}
    </div>
  );
}

/** The title, « + Ajouter une session » and its framed form. */
function Adding({ count }: { count: number }) {
  const [adding, setAdding] = useState(false);
  return (
    <>
      <Head count={count} adding={adding} add={() => setAdding(true)} />
      {adding && <AddSession done={() => setAdding(false)} />}
    </>
  );
}

/** The sessions of a period, to check, add, fix or remove (many at once). */
export function SessionList() {
  const [range, setRange] = useRange(30, 'work.sessions');
  const [show, setShow] = useStored('work.sessions.show', 'Toutes', FILTERS);
  const sel = useSelection();
  const all = useWorkSessions(range).data ?? [];
  const shown = all.filter(SHOW[show] ?? (() => true));
  const ids = shown.map((s) => s.id);
  const { page: rows, bar } = usePaging(shown);
  return (
    <section className="card">
      <Adding count={shown.length} />
      <div className="toolbar">
        <DateRange value={range} onChange={setRange} />
        <Filter value={show} onChange={setShow} />
      </div>
      <BulkBar what="work/sessions" noun="sessions" shown={ids} sel={sel} />
      {bar}
      <Table rows={rows} sel={sel} />
    </section>
  );
}
