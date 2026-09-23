import { useState } from 'react';

import type { WorkSession } from '../../api/work';
import { useDeleteSession } from '../../hooks/useWork';
import { shortDate } from '../../utils/format';
import { clockTime, hm } from './format';
import { SessionEditor } from './SessionEditor';

const SOURCE: Record<string, string> = {
  tap: 'Raccourci',
  manual: 'Saisie',
  import: 'Import',
  edited: 'Corrigée à la main',
};

function end(row: WorkSession): string {
  if (row.end_at) return clockTime(row.end_at);
  return row.status === 'open' ? 'en cours' : '? à compléter';
}

function Buttons(props: { row: WorkSession; edit: () => void }) {
  const del = useDeleteSession();
  const drop = () =>
    window.confirm('Supprimer cette session ?') && del.mutate(props.row.id);
  return (
    <td className="quick">
      <button className="btn ghost" onClick={props.edit}>
        Modifier
      </button>
      <button className="btn ghost" title="Supprimer" onClick={drop}>
        ×
      </button>
    </td>
  );
}

function Editing(props: { row: WorkSession; done: () => void }) {
  return (
    <tr>
      <td colSpan={7}>
        <SessionEditor row={props.row} onDone={props.done} />
      </td>
    </tr>
  );
}

/** One session; « Modifier » opens its editor in place. */
export function SessionRow({ row }: { row: WorkSession }) {
  const [editing, setEditing] = useState(false);
  if (editing) return <Editing row={row} done={() => setEditing(false)} />;
  return (
    <tr>
      <td>{shortDate(row.date_key)}</td>
      <td>{row.start_at ? clockTime(row.start_at) : '? à compléter'}</td>
      <td>{end(row)}</td>
      <td>{hm(row.hours)}</td>
      <td>
        {row.place === 'remote' && <span className="badge">à distance</span>}
      </td>
      <td className="muted" title={row.note}>
        {SOURCE[row.source] ?? row.source}
      </td>
      <Buttons row={row} edit={() => setEditing(true)} />
    </tr>
  );
}
