import { useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import type { FormEvent } from 'react';

import {
  importBiology,
  purgeBiology,
  type BiologyResult,
} from '../api/biology';

interface Sink {
  setBusy: (b: boolean) => void;
  setResult: (r: BiologyResult | null) => void;
  setError: (e: string | null) => void;
  refresh: () => void;
}

async function run(form: HTMLFormElement, sink: Sink): Promise<void> {
  sink.setBusy(true);
  sink.setError(null);
  try {
    sink.setResult(await importBiology(new FormData(form)));
    form.reset();
    sink.refresh();
  } catch (err) {
    sink.setError(err instanceof Error ? err.message : 'Échec de l’analyse');
  } finally {
    sink.setBusy(false);
  }
}

function Intro() {
  return (
    <p className="muted">
      Les valeurs et leurs antériorités sont extraites immédiatement et ajoutées
      aux courbes (mêmes champs que partout : marqueurs, graphiques, rapports).
      Le document est ensuite relu par l’IA (PDF scanné compris, via OCR) pour
      compléter ce qui manque — chaque valeur proposée par l’IA doit être
      imprimée dans le document pour être gardée.
    </p>
  );
}

async function purge(refresh: () => void): Promise<void> {
  if (!window.confirm('Supprimer toutes les analyses de biologie suivies ?')) {
    return;
  }
  await purgeBiology();
  refresh();
}

function PurgeButton({ refresh }: { refresh: () => void }) {
  return (
    <button
      className="btn btn-ghost"
      type="button"
      onClick={() => void purge(refresh)}
    >
      Réinitialiser la biologie
    </button>
  );
}

function Form({
  busy,
  onSubmit,
}: {
  busy: boolean;
  onSubmit: (e: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <form className="care-form" onSubmit={onSubmit}>
      <input className="input" type="file" name="file" accept=".pdf" required />
      <button className="btn" disabled={busy}>
        {busy ? 'Analyse…' : 'Analyser et suivre'}
      </button>
    </form>
  );
}

function Result({
  result,
  error,
}: {
  result: BiologyResult | null;
  error: string | null;
}) {
  return (
    <>
      {result && (
        <p className="muted">
          {result.added} valeurs importées · {result.metrics} analyses ·{' '}
          {result.dates.length} date(s).
        </p>
      )}
      {error && <p className="error">{error}</p>}
    </>
  );
}

export function BiologyImport() {
  const client = useQueryClient();
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<BiologyResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void run(event.currentTarget, {
      setBusy,
      setResult,
      setError,
      refresh: () => void client.invalidateQueries(),
    });
  };
  return (
    <section className="card">
      <h2>Analyser une prise de sang (PDF)</h2>
      <Intro />
      <Form busy={busy} onSubmit={onSubmit} />
      <Result result={result} error={error} />
      <PurgeButton refresh={() => void client.invalidateQueries()} />
    </section>
  );
}
