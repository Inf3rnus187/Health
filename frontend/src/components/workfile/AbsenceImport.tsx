import { useState } from 'react';

import { ABSENCE_KINDS, postForm } from '../../api/workfile';
import { useWorkRefresh } from '../../hooks/useWork';
import { shortDate } from '../../utils/format';

interface Period {
  start: string;
  end: string;
  kind: string;
  label: string;
  note: string;
}

interface FileReport {
  name: string;
  periods: number;
  days: number;
  new: number;
  duplicates: number;
  skipped_count: number;
  skipped: { line: number; reason: string }[];
  preview: Period[];
  columns: {
    person?: string;
    people?: { name: string; rows: number }[];
  };
}

interface Report {
  dry_run: boolean;
  files: FileReport[];
}

function useAbsenceImport(files: File[]) {
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState('');
  const refresh = useWorkRefresh();
  const run = (dryRun: boolean, person = '') => {
    const form = new FormData();
    files.forEach((f) => form.append('files', f));
    form.append('person', person || report?.files[0]?.columns.person || '');
    setError('');
    postForm<Report>(`/absences/import?dry_run=${dryRun}`, form).then(
      (r) => {
        setReport(r);
        if (!dryRun) refresh();
      },
      (e: Error) => setError(e.message),
    );
  };
  return { report, error, run, reset: () => setReport(null) };
}

function periodLine(p: Period): string {
  const kind = ABSENCE_KINDS[p.kind] ?? p.kind;
  const span =
    p.start === p.end
      ? `le ${shortDate(p.start)}`
      : `du ${shortDate(p.start)} au ${shortDate(p.end)}`;
  return `${span} — ${kind}${p.label ? ` (${p.label})` : ''}`;
}

function People(props: { file: FileReport; run: (who: string) => void }) {
  const people = props.file.columns.people ?? [];
  if (people.length < 2) return null;
  return (
    <select
      className="input"
      value={props.file.columns.person ?? ''}
      onChange={(e) => props.run(e.target.value)}
    >
      {people.map((p) => (
        <option key={p.name} value={p.name}>
          {p.name} ({p.rows} lignes)
        </option>
      ))}
    </select>
  );
}

function FileOutcome(props: { file: FileReport; run: (w: string) => void }) {
  const f = props.file;
  return (
    <div>
      <p>
        {`${f.name} : ${f.periods} absences (${f.days} jours), ${f.new} ` +
          `nouvelles, ${f.duplicates} déjà là, ${f.skipped_count} lignes ` +
          `ignorées` +
          (f.skipped.length
            ? ` (${f.skipped.map((s) => `l.${s.line} ${s.reason}`).join(', ')})`
            : '')}
      </p>
      <People file={f} run={props.run} />
      <ul className="care-list">
        {f.preview.map((p) => (
          <li key={`${p.start}-${p.kind}-${p.label}`}>{periodLine(p)}</li>
        ))}
      </ul>
    </div>
  );
}

const INTRO =
  'Export des absences de votre outil RH (Lucca, Figgo…) en CSV, Excel ' +
  'ou JSON : dates de début et de fin (ou un jour par ligne, regroupés), ' +
  'type (congés payés, RTT → repos, maladie → arrêt maladie…), statut ' +
  '(refusées et annulées ignorées ; télétravail et formation ne sont pas ' +
  'des absences). Rien n’est ajouté deux fois.';

function ReadButtons(props: {
  ready: boolean;
  read: boolean;
  run: (dryRun: boolean) => void;
}) {
  return (
    <div className="quick">
      <button
        className="btn ghost"
        disabled={!props.ready}
        onClick={() => props.run(true)}
      >
        Lire
      </button>
      <button
        className="btn"
        disabled={!props.read}
        onClick={() => props.run(false)}
      >
        Importer
      </button>
    </div>
  );
}

/** Import rest days, leave and sick leave from an HR export. */
export function AbsenceImport() {
  const [files, setFiles] = useState<File[]>([]);
  const { report, error, run, reset } = useAbsenceImport(files);
  const pick = (list: FileList | null) => {
    setFiles(Array.from(list ?? []));
    reset();
  };
  return (
    <section className="card">
      <h2>Importer des absences (Lucca, outil RH)</h2>
      <p className="muted">{INTRO}</p>
      <input type="file" multiple onChange={(e) => pick(e.target.files)} />
      <ReadButtons
        ready={files.length > 0}
        read={Boolean(report?.dry_run)}
        run={(dryRun) => run(dryRun)}
      />
      {error && <p className="error">{error}</p>}
      {report?.files.map((f) => (
        <FileOutcome key={f.name} file={f} run={(who) => run(true, who)} />
      ))}
    </section>
  );
}
