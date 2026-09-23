import { useState } from 'react';

import { ABSENCE_KINDS, type Absence } from '../../api/workfile';
import {
  useAbsences,
  useDeleteAbsence,
  useSaveAbsence,
} from '../../hooks/useWorkFile';
import { shortDate } from '../../utils/format';
import { Choice, Input, Text } from './fields';

const EMPTY = {
  start_date: '',
  end_date: '',
  kind: 'arret_maladie',
  cause: '',
  note: '',
};

type Form = typeof EMPTY;

const DATES: [keyof Form, string][] = [
  ['start_date', 'Du'],
  ['end_date', 'Au'],
];
const TEXTS: [keyof Form, string][] = [
  ['cause', 'Cause (fièvre, épuisement…)'],
  ['note', 'Notes'],
];

interface FieldsProps {
  form: Form;
  set: (k: keyof Form, v: string) => void;
}

function Dates({ form, set }: FieldsProps) {
  return (
    <>
      {DATES.map(([key, label]) => (
        <Input
          key={key}
          label={label}
          type="date"
          value={form[key]}
          onChange={(v) => set(key, v)}
        />
      ))}
    </>
  );
}

function Fields({ form, set }: FieldsProps) {
  return (
    <>
      <Dates form={form} set={set} />
      <Choice
        options={ABSENCE_KINDS}
        value={form.kind}
        onChange={(v) => set('kind', v)}
      />
      {TEXTS.map(([key, label]) => (
        <Text
          key={key}
          label={label}
          value={form[key]}
          onChange={(v) => set(key, v)}
        />
      ))}
    </>
  );
}

function AbsenceForm() {
  const save = useSaveAbsence();
  const [form, setForm] = useState(EMPTY);
  const set = (key: keyof Form, value: string) =>
    setForm({ ...form, [key]: value });
  const ready = Boolean(form.start_date && form.end_date);
  return (
    <div className="care-form">
      <Fields form={form} set={set} />
      <button
        className="btn"
        disabled={!ready}
        onClick={() => save.mutate(form, { onSuccess: () => setForm(EMPTY) })}
      >
        Ajouter l’absence
      </button>
      {save.error && <p className="error">{save.error.message}</p>}
    </div>
  );
}

function Item({ absence }: { absence: Absence }) {
  const del = useDeleteAbsence();
  return (
    <li>
      <strong>{ABSENCE_KINDS[absence.kind] ?? absence.kind}</strong> du{' '}
      {shortDate(absence.start_date)} au {shortDate(absence.end_date)}
      {absence.cause && ` — ${absence.cause}`}
      <button className="btn ghost" onClick={() => del.mutate(absence.id)}>
        Supprimer
      </button>
    </li>
  );
}

/** Sick leave and other absences, with their cause. */
export function AbsencesCard() {
  const list = useAbsences().data ?? [];
  return (
    <section className="card">
      <h2>Arrêts et absences</h2>
      <AbsenceForm />
      <ul className="care-list">
        {list.map((a) => (
          <Item key={a.id} absence={a} />
        ))}
      </ul>
    </section>
  );
}
