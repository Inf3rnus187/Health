import { useState } from 'react';
import type { FormEvent } from 'react';

import { useUploadDoc } from '../hooks/useMedical';
import { KIND_OPTIONS } from '../medical/kinds';

type Mutate = (form: FormData) => Promise<unknown>;

async function submitForm(
  mutate: Mutate,
  event: FormEvent<HTMLFormElement>,
  setError: (msg: string | null) => void,
): Promise<void> {
  event.preventDefault();
  const form = event.currentTarget;
  setError(null);
  try {
    await mutate(new FormData(form));
    form.reset();
  } catch (err) {
    setError(err instanceof Error ? err.message : 'Échec du téléversement');
  }
}

function Fields() {
  return (
    <>
      <input className="input" type="file" name="file" required />
      <select className="input" name="kind" defaultValue="ordonnance">
        {KIND_OPTIONS.map(([value, label]) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </select>
      <input className="input" name="title" placeholder="Titre du document" />
      <input className="input" type="date" name="doc_date" />
      <textarea
        className="input"
        name="notes"
        placeholder="Notes (optionnel)"
      />
    </>
  );
}

export function MedicalUpload() {
  const upload = useUploadDoc();
  const [error, setError] = useState<string | null>(null);
  return (
    <section className="card">
      <h2>Ajouter un document médical</h2>
      <form
        className="med-form"
        onSubmit={(e) => void submitForm(upload.mutateAsync, e, setError)}
      >
        <Fields />
        <button className="btn" disabled={upload.isPending}>
          Téléverser
        </button>
      </form>
      {error && <p className="error">{error}</p>}
    </section>
  );
}
