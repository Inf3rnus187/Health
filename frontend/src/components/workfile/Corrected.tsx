import { useState } from 'react';

import type { WorkSession } from '../../api/work';
import { useWorkSessions } from '../../hooks/useWork';
import { localToday, shortDate } from '../../utils/format';
import { usePaging } from '../Paging';
import { clockTime, hm } from '../work/format';
import { SessionEditor } from '../work/SessionEditor';

function Line({ row }: { row: WorkSession }) {
  const [editing, setEditing] = useState(false);
  if (editing) {
    return (
      <li className="day-card">
        <strong>{shortDate(row.date_key)}</strong>
        <SessionEditor row={row} onDone={() => setEditing(false)} />
      </li>
    );
  }
  return (
    <li>
      <strong>{shortDate(row.date_key)}</strong>{' '}
      {`${clockTime(row.start_at)} → ${clockTime(row.end_at)}`} ({hm(row.hours)}
      ){row.place === 'remote' && ' · à distance'}
      {row.note && <span className="muted"> — {row.note}</span>}{' '}
      <button className="btn ghost" onClick={() => setEditing(true)}>
        Modifier
      </button>
    </li>
  );
}

/** Sessions completed or fixed by hand: to check, and fix again. */
export function Corrected() {
  const all = useWorkSessions({ start: '', end: localToday() }).data ?? [];
  const edited = all.filter((s) => s.source === 'edited');
  const { page, bar } = usePaging(edited);
  if (edited.length === 0) return null;
  return (
    <>
      <h3>Corrigées à la main ({edited.length})</h3>
      <p className="muted">
        Une erreur ? « Modifier » : changez l’heure, le lieu ou la note ; videz
        une heure pour remettre la journée à compléter.
      </p>
      {bar}
      <ul className="care-list">
        {page.map((row) => (
          <Line key={row.id} row={row} />
        ))}
      </ul>
    </>
  );
}
