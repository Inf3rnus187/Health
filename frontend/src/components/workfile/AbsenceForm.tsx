import { useState } from 'react';

import {
  ABSENCE_KINDS,
  type Absence,
  type AbsenceBody,
} from '../../api/workfile';
import { useSaveAbsence, useUpdateAbsence } from '../../hooks/useWorkFile';
import { Choice, Input, Text } from './fields';

const EMPTY: AbsenceBody = {
  start_date: '',
  end_date: '',
  start_half: 'am',
  end_half: 'pm',
  kind: 'arret_maladie',
  cause: '',
  note: '',
};
const FROM = { am: 'dès le matin', pm: 'à partir de l’après-midi' };
const UNTIL = { pm: 'jusqu’au soir', am: 'jusqu’à midi (matin seul)' };

interface FieldsProps {
  form: AbsenceBody;
  set: (patch: Partial<AbsenceBody>) => void;
}

function Day(props: {
  label: string;
  date: string;
  half: 'am' | 'pm';
  halves: Record<string, string>;
  set: (date: string, half: 'am' | 'pm') => void;
}) {
  return (
    <>
      <Input
        label={props.label}
        type="date"
        value={props.date}
        onChange={(v) => props.set(v, props.half)}
      />
      <Choice
        options={props.halves}
        value={props.half}
        onChange={(v) => props.set(props.date, v as 'am' | 'pm')}
      />
    </>
  );
}

function Dates({ form, set }: FieldsProps) {
  const first = (start_date: string, start_half: 'am' | 'pm') =>
    set({ start_date, start_half, end_date: form.end_date || start_date });
  const last = (end_date: string, end_half: 'am' | 'pm') =>
    set({ end_date, end_half });
  return (
    <div className="quick">
      <Day
        label="Du"
        date={form.start_date}
        half={form.start_half}
        halves={FROM}
        set={first}
      />
      <Day
        label="Au"
        date={form.end_date}
        half={form.end_half}
        halves={UNTIL}
        set={last}
      />
    </div>
  );
}

function Fields({ form, set }: FieldsProps) {
  return (
    <>
      <Dates form={form} set={set} />
      <Choice
        options={ABSENCE_KINDS}
        value={form.kind}
        onChange={(v) => set({ kind: v })}
      />
      <Text
        label="Cause (fièvre, épuisement…)"
        value={form.cause}
        onChange={(v) => set({ cause: v })}
      />
      <Text
        label="Notes"
        value={form.note}
        onChange={(v) => set({ note: v })}
      />
    </>
  );
}

function bodyOf(a: Absence | null): AbsenceBody {
  if (!a) return EMPTY;
  const keys = Object.keys(EMPTY) as (keyof AbsenceBody)[];
  return Object.fromEntries(keys.map((k) => [k, a[k]])) as AbsenceBody;
}

function useAbsenceSave(editing: Absence | null, done: () => void) {
  const add = useSaveAbsence();
  const update = useUpdateAbsence();
  const save = (body: AbsenceBody) =>
    editing
      ? update.mutate({ id: editing.id, body }, { onSuccess: done })
      : add.mutate(body, { onSuccess: done });
  return { save, error: add.error ?? update.error };
}

function Buttons(props: {
  ready: boolean;
  editing: boolean;
  save: () => void;
  cancel: () => void;
}) {
  return (
    <div className="quick">
      <button className="btn" disabled={!props.ready} onClick={props.save}>
        {props.editing ? 'Enregistrer la modification' : 'Ajouter l’absence'}
      </button>
      {props.editing && (
        <button className="btn ghost" onClick={props.cancel}>
          Annuler
        </button>
      )}
    </div>
  );
}

/** Add an absence, or fix one (half days: from the afternoon, until noon). */
export function AbsenceForm(props: {
  editing: Absence | null;
  done: () => void;
}) {
  const [form, setForm] = useState(() => bodyOf(props.editing));
  const reset = () => {
    setForm(EMPTY);
    props.done();
  };
  const { save, error } = useAbsenceSave(props.editing, reset);
  return (
    <div className="care-form">
      <Fields form={form} set={(patch) => setForm({ ...form, ...patch })} />
      <Buttons
        ready={Boolean(form.start_date && form.end_date)}
        editing={props.editing !== null}
        save={() => save(form)}
        cancel={reset}
      />
      {error && <p className="error">{error.message}</p>}
    </div>
  );
}
