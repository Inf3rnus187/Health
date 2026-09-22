import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import type { Measurement } from '../../api/types';
import { useDailyValues } from '../../hooks/useData';
import { shortDate } from '../../utils/format';
import { MetricPanel } from '../metric/MetricPanel';
import { MetricSelect } from '../MetricSelect';
import { sourceLabel } from './sources';

const SHOWN = 120;

function display(value: unknown): string {
  if (typeof value === 'number') {
    return value.toLocaleString('fr-FR', { maximumFractionDigits: 2 });
  }
  return value == null ? '—' : String(value);
}

function ValueRow({ row }: { row: Measurement }) {
  return (
    <tr>
      <td>{shortDate(row.date_key)}</td>
      <td>{display(row.value)}</td>
      <td>{sourceLabel(row.source)}</td>
    </tr>
  );
}

function Values({ rows }: { rows: Measurement[] }) {
  const recent = [...rows]
    .sort((a, b) => b.date_key.localeCompare(a.date_key))
    .slice(0, SHOWN);
  if (recent.length === 0) {
    return <p className="muted">Aucune valeur pour cette mesure.</p>;
  }
  return (
    <table className="inv-table">
      <thead>
        <tr>
          <th>Jour</th>
          <th>Valeur</th>
          <th>Source</th>
        </tr>
      </thead>
      <tbody>
        {recent.map((row) => (
          <ValueRow key={row.id} row={row} />
        ))}
      </tbody>
    </table>
  );
}

export function DailyValuesCard() {
  const [params] = useSearchParams();
  const [key, setKey] = useState(params.get('metric') ?? '');
  const { data, isLoading } = useDailyValues(key);
  return (
    <section className="card">
      <h2>Une mesure en détail (toutes sources)</h2>
      <p className="muted">
        Ce que lisent les graphiques, l’accueil et les rapports : saisies,
        prises de sang, documents, raccourcis et Apple Santé confondus.
      </p>
      <MetricSelect value={key} onChange={setKey} />
      {key && <MetricPanel metricKey={key} />}
      {key && isLoading && <p className="muted">Chargement…</p>}
      {key && data && <Values rows={data} />}
    </section>
  );
}
