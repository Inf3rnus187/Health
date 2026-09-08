import { type FormEvent, useState } from 'react';

import { useRecordWeight } from '../hooks/useRecordWeight';
import { Field } from './Field';

export function QuickWeight() {
  const [value, setValue] = useState('');
  const mutation = useRecordWeight();
  const submit = (event: FormEvent) => {
    event.preventDefault();
    const kg = Number(value);
    if (kg > 0) {
      mutation.mutate(kg);
    }
  };
  return (
    <form className="quick" onSubmit={submit}>
      <Field
        id="weight"
        label="Poids du matin (kg)"
        value={value}
        onChange={setValue}
      />
      <button className="btn" type="submit" disabled={mutation.isPending}>
        Enregistrer
      </button>
    </form>
  );
}
