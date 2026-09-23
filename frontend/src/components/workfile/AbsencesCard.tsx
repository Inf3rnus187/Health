import { useState } from 'react';

import { ABSENCE_KINDS, type Absence } from '../../api/workfile';
import { type Selection, useSelection } from '../../hooks/useSelection';
import { useAbsences, useDeleteAbsence } from '../../hooks/useWorkFile';
import { frNumber, shortDate } from '../../utils/format';
import { BulkBar, PickBox } from '../Bulk';
import { AbsenceForm } from './AbsenceForm';

/** « du 07/05/2026 après-midi au 08/05/2026 midi (1 j) ». */
function span(a: Absence): string {
  const from = a.start_half === 'pm' ? ' après-midi' : '';
  const until = a.end_half === 'am' ? ' midi' : '';
  const days = `${frNumber(a.days)} j`;
  if (a.start_date === a.end_date) {
    const half = a.start_half === 'pm' ? ' (après-midi)' : until && ' (matin)';
    return `le ${shortDate(a.start_date)}${half} (${days})`;
  }
  return (
    `du ${shortDate(a.start_date)}${from} au ` +
    `${shortDate(a.end_date)}${until} (${days})`
  );
}

function Item(props: { absence: Absence; edit: () => void; sel: Selection }) {
  const del = useDeleteAbsence();
  const a = props.absence;
  const drop = () =>
    window.confirm('Supprimer cette absence ?') && del.mutate(a.id);
  return (
    <li>
      <PickBox sel={props.sel} id={a.id} />{' '}
      <strong>{ABSENCE_KINDS[a.kind] ?? a.kind}</strong> {span(a)}
      {a.cause && ` — ${a.cause}`}{' '}
      <button className="btn ghost" onClick={props.edit}>
        Modifier
      </button>
      <button className="btn ghost" onClick={drop}>
        Supprimer
      </button>
    </li>
  );
}

function List(props: {
  list: Absence[];
  edit: (a: Absence) => void;
  sel: Selection;
}) {
  const ids = props.list.map((a) => a.id);
  return (
    <>
      <BulkBar what="absences" noun="absences" shown={ids} sel={props.sel} />
      <ul className="care-list">
        {props.list.map((a) => (
          <Item
            key={a.id}
            absence={a}
            edit={() => props.edit(a)}
            sel={props.sel}
          />
        ))}
      </ul>
    </>
  );
}

/** Sick leave and other absences, with their cause; half days too. */
export function AbsencesCard() {
  const list = useAbsences().data ?? [];
  const [editing, setEditing] = useState<Absence | null>(null);
  const sel = useSelection();
  return (
    <section className="card">
      <h2>Arrêts et absences</h2>
      {editing && <h3>Modifier l’absence</h3>}
      <AbsenceForm
        key={editing?.id ?? 'new'}
        editing={editing}
        done={() => setEditing(null)}
      />
      <List list={list} edit={setEditing} sel={sel} />
    </section>
  );
}
