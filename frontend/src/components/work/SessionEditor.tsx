import { useState } from 'react';

import type { Place, WorkSession } from '../../api/work';
import { useCompleteSession } from '../../hooks/useWorkFile';
import { localStamp } from '../../utils/datetime';
import { DayProofs } from '../workfile/DayProofs';

function When(props: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="muted">
      {props.label}{' '}
      <input
        className="input"
        type="datetime-local"
        value={props.value}
        onChange={(e) => props.onChange(e.target.value)}
      />
    </label>
  );
}

function usePlan(row: WorkSession) {
  const [start, setStart] = useState(
    row.start_at ? localStamp(row.start_at) : '',
  );
  const [end, setEnd] = useState(row.end_at ? localStamp(row.end_at) : '');
  const [place, setPlace] = useState<Place>(row.place);
  const [note, setNote] = useState(row.note);
  const body = { start_at: start || null, end_at: end || null, place, note };
  return { start, setStart, end, setEnd, place, setPlace, note, setNote, body };
}

type Plan = ReturnType<typeof usePlan>;

function Fields({ plan }: { plan: Plan }) {
  return (
    <>
      <When label="Embauche" value={plan.start} onChange={plan.setStart} />
      <When label="Débauche" value={plan.end} onChange={plan.setEnd} />
      <select
        className="input"
        value={plan.place}
        onChange={(e) => plan.setPlace(e.target.value as Place)}
      >
        <option value="site">Sur place</option>
        <option value="remote">À distance</option>
      </select>
      <input
        className="input"
        placeholder="Note (d’où vient l’heure)"
        value={plan.note}
        onChange={(e) => plan.setNote(e.target.value)}
      />
    </>
  );
}

/** Fix a session: its times (empty: unknown, to complete), place, note. */
export function SessionEditor(props: { row: WorkSession; onDone: () => void }) {
  const save = useCompleteSession();
  const plan = usePlan(props.row);
  const store = () =>
    save.mutate(
      { id: props.row.id, body: plan.body },
      { onSuccess: props.onDone },
    );
  return (
    <div>
      <div className="quick">
        <Fields plan={plan} />
        <Buttons
          plan={plan}
          store={store}
          done={props.onDone}
          busy={save.isPending}
        />
      </div>
      {save.error && <p className="error">{save.error.message}</p>}
      <Proofs row={props.row} plan={plan} />
    </div>
  );
}

function Proofs(props: { row: WorkSession; plan: Plan }) {
  const { plan } = props;
  return (
    <>
      <p className="muted">Preuves et traces du jour et du lendemain matin :</p>
      <DayProofs
        day={props.row.date_key}
        pick={(field, at) =>
          (field === 'start' ? plan.setStart : plan.setEnd)(at)
        }
      />
    </>
  );
}

function Buttons(props: {
  plan: Plan;
  store: () => void;
  done: () => void;
  busy: boolean;
}) {
  return (
    <>
      <button
        className="btn"
        disabled={!(props.plan.start || props.plan.end) || props.busy}
        onClick={props.store}
      >
        Enregistrer
      </button>
      <button className="btn ghost" onClick={props.done}>
        Annuler
      </button>
    </>
  );
}
