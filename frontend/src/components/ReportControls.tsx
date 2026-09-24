import { useState } from 'react';

import type { ReportParams } from '../api/reports';
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
  onCreate: (type: string, range: Range, params: ReportParams) => void;
  busy: boolean;
}

const CLINICAL = ['synthesis', 'clinical_pdf'];
const WORK = ['work', 'work_health'];

type Set = (p: ReportParams) => void;

function CompareField(props: { params: ReportParams; set: Set }) {
  return (
    <label className="field">
      Comparer avant / après le (facultatif)
      <input
        className="input"
        type="date"
        value={props.params.compare_from ?? ''}
        onChange={(e) =>
          props.set({ compare_from: e.target.value || undefined })
        }
      />
    </label>
  );
}

function ContractField(props: { params: ReportParams; set: Set }) {
  return (
    <label className="field">
      Heures de contrat par semaine
      <input
        className="input"
        type="number"
        min={1}
        max={60}
        value={props.params.contract_hours ?? 35}
        onChange={(e) =>
          props.set({ contract_hours: Number(e.target.value) || 35 })
        }
      />
    </label>
  );
}

/** Before / after a day (clinical), contract hours (work). */
function Options(props: { type: string; params: ReportParams; set: Set }) {
  if (CLINICAL.includes(props.type)) return <CompareField {...props} />;
  if (WORK.includes(props.type)) return <ContractField {...props} />;
  return null;
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
  const [params, setParams] = useState<ReportParams>({});
  return (
    <>
      <DateRange value={range} onChange={setRange} />
      <div className="quick">
        <TypeSelect value={type} onChange={setType} />
        <Options type={type} params={params} set={setParams} />
        <button
          className="btn"
          disabled={busy}
          onClick={() => onCreate(type, range, params)}
        >
          Générer
        </button>
      </div>
    </>
  );
}
