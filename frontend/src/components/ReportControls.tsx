import { type Range, useRange } from '../utils/range';
import { useStored } from '../utils/stored';
import { DateRange } from './DateRange';

const TYPES = [
  {
    value: 'synthesis',
    label:
      'Synthèse clinique IA + PDF clinique (modèle médical, quelques minutes)',
  },
  { value: 'clinical_pdf', label: 'PDF clinique' },
  { value: 'work', label: 'Heures travaillées (PDF)' },
  { value: 'work_health', label: 'Dossier travail ↔ santé (PDF)' },
  { value: 'csv', label: 'CSV' },
  { value: 'json', label: 'JSON' },
  { value: 'xlsx', label: 'Excel (XLSX)' },
  { value: 'fhir', label: 'FHIR' },
];

interface ReportControlsProps {
  onCreate: (type: string, range: Range) => void;
  busy: boolean;
}

function TypeSelect(props: { value: string; onChange: (v: string) => void }) {
  return (
    <select
      className="input"
      value={props.value}
      onChange={(event) => props.onChange(event.target.value)}
    >
      {TYPES.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  );
}

/** A report type and its period ("Tout" by default), then "Générer". */
export function ReportControls({ onCreate, busy }: ReportControlsProps) {
  const [type, setType] = useStored(
    'reports.type',
    'synthesis',
    TYPES.map((t) => t.value),
  );
  const [range, setRange] = useRange(null, 'reports');
  return (
    <>
      <DateRange value={range} onChange={setRange} />
      <div className="quick">
        <TypeSelect value={type} onChange={setType} />
        <button
          className="btn"
          disabled={busy}
          onClick={() => onCreate(type, range)}
        >
          Générer
        </button>
      </div>
    </>
  );
}
