import { useState } from 'react';

import { ABSENCE_KINDS, type Absence } from '../../api/workfile';
import { useAbsences, useDeleteAbsence } from '../../hooks/useWorkFile';
import { frNumber, shortDate } from '../../utils/format';
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

function Item(props: { absence: Absence; edit: () => void }) {
  const del = useDeleteAbsence();
  const a = props.absence;
  const drop = () =>
    window.confirm('Supprimer cette absence ?') && del.mutate(a.id);
  return (
    <li>
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

/** Sick leave and other absences, with their cause; half days too. */
export function AbsencesCard() {
  const list = useAbsences().data ?? [];
  const [editing, setEditing] = useState<Absence | null>(null);
  return (
    <section className="card">
      <h2>Arrêts et absences</h2>
      {editing && <h3>Modifier l’absence</h3>}
      <AbsenceForm
        key={editing?.id ?? 'new'}
        editing={editing}
        done={() => setEditing(null)}
      />
      <ul className="care-list">
        {list.map((a) => (
          <Item key={a.id} absence={a} edit={() => setEditing(a)} />
        ))}
      </ul>
    </section>
  );
}
