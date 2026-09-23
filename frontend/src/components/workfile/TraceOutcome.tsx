/** What a trace import read, file by file. */
export interface FileReport {
  name: string;
  label: string;
  traces: number;
  new: number;
  merged: number;
  duplicates: number;
  total: number;
  skipped_count: number;
  columns: Record<string, unknown>;
}

export interface TraceReport {
  dry_run: boolean;
  meals: number;
  files: FileReport[];
}

interface Person {
  name: string;
  actions: number;
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
  tickets: 'tickets',
};

function line(f: FileReport): string {
  const found =
    Object.entries(f.columns)
      .filter(([key]) => key in FIELD)
      .map(([key, title]) => `${FIELD[key] ?? key} : « ${String(title)} »`)
      .join(', ') || 'aucune';
  return (
    `${f.name} (${f.label}) : ${f.traces} traces, ${f.new} nouvelles, ` +
    `${f.merged} rapprochées d’une trace déjà là (reçu ↔ note de frais), ` +
    `${f.duplicates} déjà là, ${f.total} €, ${f.skipped_count} lignes ` +
    `ignorées — lu : ${found}.`
  );
}

/** A ticket export: whose actions to keep (the most active by default). */
function People(props: { file: FileReport; onPerson: (n: string) => void }) {
  const people = (props.file.columns.people ?? []) as Person[];
  if (people.length === 0) return null;
  return (
    <label>
      Vos actions (votre nom dans l’outil) :{' '}
      <select
        className="input"
        value={String(props.file.columns.person ?? '')}
        onChange={(e) => props.onPerson(e.target.value)}
      >
        {people.map((p) => (
          <option key={p.name} value={p.name}>
            {p.name} ({p.actions} actions)
          </option>
        ))}
      </select>
    </label>
  );
}

export function Outcome(props: {
  report: TraceReport;
  onPerson: (name: string) => void;
}) {
  const { report } = props;
  return (
    <div className="muted">
      {report.files.map((f) => (
        <div key={f.name}>
          <p>{line(f)}</p>
          <People file={f} onPerson={props.onPerson} />
        </div>
      ))}
      {!report.dry_run && <p>{report.meals} repas ajoutés au Journal.</p>}
    </div>
  );
}
