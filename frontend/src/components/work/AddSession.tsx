import { useState } from 'react';

import type { Place } from '../../api/work';
import { useAddSession } from '../../hooks/useWork';

function When(props: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="field">
      {props.label}
      <input
        className="input"
        type="datetime-local"
        value={props.value}
        onChange={(e) => props.onChange(e.target.value)}
      />
    </label>
  );
}

function Where(props: { value: Place; onChange: (p: Place) => void }) {
  return (
    <label className="field">
      Lieu
      <select
        className="input"
        value={props.value}
        onChange={(e) => props.onChange(e.target.value as Place)}
      >
        <option value="site">Sur place</option>
        <option value="remote">
          À distance (même après une journée sur place)
        </option>
      </select>
    </label>
  );
}

function useForm(done: () => void) {
  const add = useAddSession();
  const [start, setStart] = useState('');
  const [end, setEnd] = useState('');
  const [place, setPlace] = useState<Place>('site');
  const save = () =>
    add.mutate(
      { start_at: start, end_at: end || null, place },
      { onSuccess: done },
    );
  return { add, start, setStart, end, setEnd, place, setPlace, save };
}

/** A forgotten session, in a frame of its own (apart from the list). */
export function AddSession(props: { done: () => void }) {
  const f = useForm(props.done);
  return (
    <div className="form-box">
      <h3>Ajouter une session oubliée</h3>
      <div className="fields">
        <When label="Embauche" value={f.start} onChange={f.setStart} />
        <When
          label="Débauche (vide : à compléter)"
          value={f.end}
          onChange={f.setEnd}
        />
        <Where value={f.place} onChange={f.setPlace} />
      </div>
      <Actions f={f} done={props.done} />
    </div>
  );
}

function Actions(props: { f: ReturnType<typeof useForm>; done: () => void }) {
  const { f } = props;
  return (
    <div className="quick">
      <button
        className="btn"
        disabled={!f.start || f.add.isPending}
        onClick={f.save}
      >
        Ajouter
      </button>
      <button className="btn ghost" onClick={props.done}>
        Fermer
      </button>
      {f.add.error && <span className="error">{f.add.error.message}</span>}
    </div>
  );
}
