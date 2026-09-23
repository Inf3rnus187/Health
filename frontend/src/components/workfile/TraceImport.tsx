import { useState } from 'react';

import { postForm, TRACE_KINDS } from '../../api/workfile';
import { useWorkRefresh } from '../../hooks/useWork';
import { Choice } from './fields';

interface Picked {
  file: File;
  kind: string;
}

interface FileReport {
  name: string;
  label: string;
  traces: number;
  new: number;
  merged: number;
  duplicates: number;
  total: number;
  skipped_count: number;
  columns: Record<string, string | string[]>;
}

interface Report {
  dry_run: boolean;
  meals: number;
  files: FileReport[];
}

const GUESS: [string[], string][] = [
  [['eats', 'deliveroo', 'livraison', 'commande'], 'livraison'],
  [['trip', 'uber', 'taxi', 'g7', 'vtc', 'bolt', 'heetch'], 'taxi'],
  [['navigo', 'metro', 'ratp', 'transport', 'sncf', 'train'], 'transport'],
  [['parking', 'indigo', 'onepark', 'zenpark', 'paybyphone'], 'parking'],
  [['hotel', 'booking', 'airbnb'], 'hotel'],
];

/** Kinds to choose from: guessed (a type column, a receipt) or one. */
const KINDS: Record<string, string> = {
  auto: 'Deviner (colonne type, reçu)',
  ...TRACE_KINDS,
};

function guess(name: string): string {
  const plain = name.toLowerCase();
  if (/\.(pdf|png|jpe?g)$/.test(plain)) return 'auto';
  const hit = GUESS.find(([words]) => words.some((w) => plain.includes(w)));
  return hit ? hit[1] : 'auto';
}

const FIELD: Record<string, string> = {
  start: 'début',
  end: 'fin',
  date: 'date',
  time: 'heure',
  amount: 'montant',
  currency: 'devise',
  place: 'lieu',
  what: 'détail',
  status: 'statut',
  order: 'commande',
  vendor: 'société',
  kind: 'type',
  extras: 'autres',
  document: 'document',
};

function line(f: FileReport): string {
  const found =
    Object.entries(f.columns)
      .map(([key, title]) => `${FIELD[key] ?? key} : « ${String(title)} »`)
      .join(', ') || 'aucune';
  return (
    `${f.name} (${f.label}) : ${f.traces} traces, ${f.new} nouvelles, ` +
    `${f.merged} rapprochées d’une trace déjà là (reçu ↔ note de frais), ` +
    `${f.duplicates} déjà là, ${f.total} €, ${f.skipped_count} lignes ` +
    `ignorées — colonnes lues : ${found}.`
  );
}

function Outcome({ report }: { report: Report }) {
  return (
    <div className="muted">
      {report.files.map((f) => (
        <p key={f.name}>{line(f)}</p>
      ))}
      {!report.dry_run && <p>{report.meals} repas ajoutés au Journal.</p>}
    </div>
  );
}

function useTraceImport(picked: Picked[], meals: boolean) {
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState('');
  const refresh = useWorkRefresh();
  const run = (dryRun: boolean) => {
    const form = new FormData();
    picked.forEach((p) => form.append('files', p.file));
    picked.forEach((p) => form.append('kinds', p.kind));
    const query = `dry_run=${dryRun}&meals=${meals}`;
    setError('');
    postForm<Report>(`/traces/import?${query}`, form).then(
      (r) => {
        setReport(r);
        if (!dryRun) refresh();
      },
      (e: Error) => setError(e.message),
    );
  };
  return { report, error, run, reset: () => setReport(null) };
}

function Files(props: {
  picked: Picked[];
  onKind: (i: number, kind: string) => void;
}) {
  return (
    <ul className="care-list">
      {props.picked.map((p, i) => (
        <li key={p.file.name}>
          {p.file.name}{' '}
          <Choice
            options={KINDS}
            value={p.kind}
            onChange={(k) => props.onKind(i, k)}
          />
        </li>
      ))}
    </ul>
  );
}

function Buttons(props: {
  ready: boolean;
  read: boolean;
  run: (d: boolean) => void;
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

const INTRO =
  'Exports CSV, Excel ou JSON (Uber, Uber Eats, Navigo, parking, notes ' +
  'de frais, relevé bancaire) et reçus ou factures en PDF ou photo. Les ' +
  'colonnes sont reconnues par leur titre ; un reçu et la ligne de note ' +
  'de frais du même trajet (même jour, même montant) ne font qu’une ' +
  'trace : le reçu apporte l’heure et le fichier.';

function MealsBox(props: { on: boolean; set: (on: boolean) => void }) {
  return (
    <label className="muted">
      <input
        type="checkbox"
        checked={props.on}
        onChange={(e) => props.set(e.target.checked)}
      />{' '}
      Ajouter les repas livrés au Journal (prix, analyse IA)
    </label>
  );
}

function pickers(
  picked: Picked[],
  setPicked: (p: Picked[]) => void,
  reset: () => void,
) {
  const pick = (list: FileList | null) => {
    const files = Array.from(list ?? []);
    setPicked(files.map((file) => ({ file, kind: guess(file.name) })));
    reset();
  };
  const setKind = (i: number, kind: string) =>
    setPicked(picked.map((p, j) => (j === i ? { ...p, kind } : p)));
  return { pick, setKind };
}

/** Import app exports as traces (and deliveries as priced meals). */
export function TraceImport() {
  const [meals, setMeals] = useState(true);
  const [picked, setPicked] = useState<Picked[]>([]);
  const { report, error, run, reset } = useTraceImport(picked, meals);
  const { pick, setKind } = pickers(picked, setPicked, reset);
  return (
    <section className="card">
      <h2>Importer des traces (Uber, Uber Eats, Navigo, parking, frais)</h2>
      <p className="muted">{INTRO}</p>
      <input type="file" multiple onChange={(e) => pick(e.target.files)} />
      <Files picked={picked} onKind={setKind} />
      <MealsBox on={meals} set={setMeals} />
      <Buttons
        ready={picked.length > 0}
        read={Boolean(report?.dry_run)}
        run={run}
      />
      {error && <p className="error">{error}</p>}
      {report && <Outcome report={report} />}
    </section>
  );
}
