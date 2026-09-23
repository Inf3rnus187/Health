import { useState } from 'react';

import { createWorkReport } from '../../api/work';
import { DownloadButton } from '../DownloadButton';

const LEVELS: Record<string, string> = {
  days: 'Par jour',
  weeks: 'Par semaine',
  months: 'Par mois',
  sessions: 'Chaque session',
};
const FORMATS: Record<string, string> = {
  csv: 'CSV',
  xlsx: 'Excel',
  json: 'JSON',
};

interface Props {
  start: string;
  end: string;
  contract: number;
}

function Choice(props: {
  options: Record<string, string>;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <select
      className="input"
      value={props.value}
      onChange={(e) => props.onChange(e.target.value)}
    >
      {Object.entries(props.options).map(([value, label]) => (
        <option key={value} value={value}>
          {label}
        </option>
      ))}
    </select>
  );
}

function ReportButton(props: Props) {
  const [done, setDone] = useState('');
  const make = () =>
    createWorkReport(props.start, props.end, props.contract).then(
      () => setDone('Rapport créé : voir la page Rapports.'),
      (error: Error) => setDone(error.message),
    );
  return (
    <>
      <button className="btn ghost" onClick={() => void make()}>
        Rapport PDF
      </button>
      {done && <span className="muted">{done}</span>}
    </>
  );
}

/** Export the period (CSV / Excel / JSON) or make its PDF report. */
export function WorkExport(props: Props) {
  const [level, setLevel] = useState('days');
  const [format, setFormat] = useState('csv');
  const span = `start=${props.start}&end=${props.end}`;
  const query = `${span}&level=${level}&format=${format}`;
  const path = `/work/export?${query}&contract_hours=${props.contract}`;
  const name = `heures-${level}-${props.start}-${props.end}.${format}`;
  return (
    <div className="quick">
      <Choice options={LEVELS} value={level} onChange={setLevel} />
      <Choice options={FORMATS} value={format} onChange={setFormat} />
      <DownloadButton path={path} filename={name} label="Exporter" />
      <ReportButton {...props} />
    </div>
  );
}
