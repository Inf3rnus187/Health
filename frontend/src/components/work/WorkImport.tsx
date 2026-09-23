import { useState } from 'react';

import { importWork, type WorkImport as Result } from '../../api/work';
import { useWorkRefresh } from '../../hooks/useWork';

function Skipped({ result }: { result: Result }) {
  if (result.skipped_count === 0) {
    return null;
  }
  const examples = result.skipped
    .slice(0, 5)
    .map((s) => `${s.text ?? s.at ?? ''} (${s.reason})`)
    .join(' ; ');
  return (
    <p className="muted">
      {result.skipped_count} lignes ou heures ignorées, par exemple : {examples}
    </p>
  );
}

function Summary({ result }: { result: Result }) {
  const verb = result.dry_run ? 'trouvées' : 'importées';
  const count = result.dry_run ? result.sessions : result.stored;
  const span = `${result.first_day ?? '—'} → ${result.last_day ?? '—'}`;
  return (
    <div>
      <p>
        {count} sessions {verb} sur {result.days} jours ({span}),{' '}
        {result.total_hours} h.
      </p>
      <ul className="muted">
        {result.preview.map((p) => (
          <li key={`${p.day}${p.start}`}>
            {p.day} : {p.start} → {p.end}
          </li>
        ))}
      </ul>
      <Skipped result={result} />
    </div>
  );
}

function useImport() {
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState('');
  const refresh = useWorkRefresh();
  const run = (file: File, dryRun: boolean) => {
    setError('');
    importWork(file, dryRun).then(
      (found) => {
        setResult(found);
        if (!dryRun) refresh();
      },
      (e: Error) => setError(e.message),
    );
  };
  return { result, error, run, reset: () => setResult(null) };
}

function Actions(props: {
  file: File | null;
  ready: boolean;
  run: (file: File, dryRun: boolean) => void;
}) {
  const { file } = props;
  return (
    <>
      <button
        className="btn ghost"
        disabled={!file}
        onClick={() => file && props.run(file, true)}
      >
        Lire le fichier
      </button>
      <button
        className="btn"
        disabled={!file || !props.ready}
        onClick={() => file && props.run(file, false)}
      >
        Importer
      </button>
    </>
  );
}

function Picker({ onPick }: { onPick: (file: File | null) => void }) {
  return (
    <input
      type="file"
      accept=".txt,.csv,.json,text/*,application/json"
      onChange={(e) => onPick(e.target.files?.[0] ?? null)}
    />
  );
}

/** Read a past log (txt / csv / json), check it, then import it. */
export function WorkImport() {
  const [file, setFile] = useState<File | null>(null);
  const { result, error, run, reset } = useImport();
  const ready = Boolean(result?.dry_run && result.sessions > 0);
  const pick = (picked: File | null) => {
    setFile(picked);
    reset();
  };
  return (
    <section className="card">
      <h2>Importer d’anciens pointages</h2>
      <p className="muted">
        Fichier txt, csv ou json (dates, heures d’embauche et de débauche). Il
        est d’abord lu : rien n’est enregistré avant « Importer ».
      </p>
      <div className="quick">
        <Picker onPick={pick} />
        <Actions file={file} ready={ready} run={run} />
      </div>
      {error && <p className="error">{error}</p>}
      {result && <Summary result={result} />}
    </section>
  );
}
