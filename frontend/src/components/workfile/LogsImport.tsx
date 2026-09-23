import { useState } from 'react';

import { postForm } from '../../api/workfile';
import { useWorkRefresh } from '../../hooks/useWork';
import { keyFor, LOG_KEYS } from './keys';

interface Picked {
  file: File;
  key: string;
}

type Report = Record<string, unknown> & {
  dry_run: boolean;
  files: { name: string; key: string | null; events: number; days: number }[];
  work?: Record<string, number>;
};

function KeySelect(props: { value: string; onChange: (k: string) => void }) {
  return (
    <select
      className="input"
      value={props.value}
      onChange={(e) => props.onChange(e.target.value)}
    >
      <option value="">— type ? —</option>
      {Object.entries(LOG_KEYS).map(([key, label]) => (
        <option key={key} value={key}>
          {label}
        </option>
      ))}
    </select>
  );
}

function Files(props: {
  picked: Picked[];
  onKey: (i: number, k: string) => void;
}) {
  return (
    <ul className="care-list">
      {props.picked.map((p, i) => (
        <li key={p.file.name}>
          {p.file.name}{' '}
          <KeySelect value={p.key} onChange={(k) => props.onKey(i, k)} />
        </li>
      ))}
    </ul>
  );
}

function workLine(work: Record<string, number>): string {
  return (
    `Travail : ${work.sessions} sessions (${work.complete} complètes, ` +
    `${work.missing_start} sans embauche, ${work.missing_end} sans ` +
    `débauche), ${work.total_hours} h comptées.`
  );
}

function Outcome({ report }: { report: Report }) {
  const work = report.work;
  const verb = report.dry_run ? 'lus' : 'importés';
  return (
    <div className="muted">
      {report.files.map((f) => (
        <p key={f.name}>
          {f.name} : {f.events} pointages {verb} sur {f.days} jours.
        </p>
      ))}
      {work && <p>{workLine(work)}</p>}
    </div>
  );
}

function useLogImport(picked: Picked[]) {
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState('');
  const refresh = useWorkRefresh();
  const run = (dryRun: boolean) => {
    const form = new FormData();
    picked.forEach((p) => form.append('files', p.file));
    picked.forEach((p) => form.append('keys', p.key));
    setError('');
    postForm<Report>(`/logs/import?dry_run=${dryRun}`, form).then(
      (r) => {
        setReport(r);
        if (!dryRun) refresh();
      },
      (e: Error) => setError(e.message),
    );
  };
  return { report, error, run, reset: () => setReport(null) };
}

function Buttons(props: {
  picked: Picked[];
  report: Report | null;
  run: (dryRun: boolean) => void;
}) {
  return (
    <div className="quick">
      <button
        className="btn ghost"
        disabled={!props.picked.length}
        onClick={() => props.run(true)}
      >
        Lire
      </button>
      <button
        className="btn"
        disabled={!props.report?.dry_run}
        onClick={() => props.run(false)}
      >
        Importer
      </button>
    </div>
  );
}

const INTRO =
  'Un fichier par type (Embauche, Débauche, Cigarettes, Café, Eau…), ' +
  'une date et une heure par ligne. Choisissez-les tous ensemble : les ' +
  'embauches et débauches sont appariées. Rien n’est effacé.';

/** Import iPhone Shortcut histories: one file per kind, keys guessed. */
export function LogsImport() {
  const [picked, setPicked] = useState<Picked[]>([]);
  const { report, error, run, reset } = useLogImport(picked);
  const pick = (list: FileList | null) => {
    const files = Array.from(list ?? []);
    setPicked(files.map((file) => ({ file, key: keyFor(file.name) })));
    reset();
  };
  const setKey = (i: number, key: string) =>
    setPicked(picked.map((p, j) => (j === i ? { ...p, key } : p)));
  return (
    <section className="card">
      <h2>Importer les historiques de Raccourcis</h2>
      <p className="muted">{INTRO}</p>
      <input type="file" multiple onChange={(e) => pick(e.target.files)} />
      <Files picked={picked} onKey={setKey} />
      <Buttons picked={picked} report={report} run={run} />
      {error && <p className="error">{error}</p>}
      {report && <Outcome report={report} />}
    </section>
  );
}
