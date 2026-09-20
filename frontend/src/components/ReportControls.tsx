import { useState } from 'react';

const TYPES = [
  { value: 'clinical_pdf', label: 'PDF clinique' },
  { value: 'csv', label: 'CSV' },
  { value: 'json', label: 'JSON' },
  { value: 'xlsx', label: 'Excel (XLSX)' },
  { value: 'fhir', label: 'FHIR' },
];

interface ReportControlsProps {
  onCreate: (type: string) => void;
  busy: boolean;
}

export function ReportControls({ onCreate, busy }: ReportControlsProps) {
  const [type, setType] = useState('clinical_pdf');
  return (
    <div className="quick">
      <select
        className="input"
        value={type}
        onChange={(event) => setType(event.target.value)}
      >
        {TYPES.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      <button className="btn" disabled={busy} onClick={() => onCreate(type)}>
        Générer
      </button>
    </div>
  );
}
