import type { QueryClient } from '@tanstack/react-query';
import { useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import type { FormEvent } from 'react';

import { importCda } from '../api/clinical';

function submit(
  form: HTMLFormElement,
  client: QueryClient,
  setMsg: (m: string | null) => void,
): void {
  importCda(new FormData(form))
    .then((res) => {
      setMsg(`${res.observations} observations importées.`);
      form.reset();
      void client.invalidateQueries();
    })
    .catch((err: unknown) =>
      setMsg(err instanceof Error ? err.message : 'Échec de l’import'),
    );
}

function Form({
  onSubmit,
}: {
  onSubmit: (e: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <form className="care-form" onSubmit={onSubmit}>
      <input
        className="input"
        type="file"
        name="file"
        accept=".xml,.cda"
        required
      />
      <button className="btn">Importer</button>
    </form>
  );
}

export function CdaImport() {
  const client = useQueryClient();
  const [msg, setMsg] = useState<string | null>(null);
  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    submit(event.currentTarget, client, setMsg);
  };
  return (
    <section className="card">
      <h2>Importer un dossier CDA (médecin)</h2>
      <p className="muted">
        Fichier CDA français (CI-SIS / HL7 CDA) remis par un soignant. Les
        résultats apparaissent dans Santé → Observations cliniques.
      </p>
      <Form onSubmit={onSubmit} />
      {msg && <p className="muted">{msg}</p>}
    </section>
  );
}
