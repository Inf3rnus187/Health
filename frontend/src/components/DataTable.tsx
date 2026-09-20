import type { Measurement, Metric } from '../api/types';
import { DataRow } from './DataRow';

interface DataTableProps {
  rows: Measurement[];
  metrics: Map<string, Metric>;
  selected: Set<string>;
  onToggle: (id: string) => void;
}

export function DataTable({
  rows,
  metrics,
  selected,
  onToggle,
}: DataTableProps) {
  if (rows.length === 0) {
    return <p className="muted">Aucune donnée. Ajoute des mesures.</p>;
  }
  return (
    <table className="data-table">
      <tbody>
        {rows.map((row) => (
          <DataRow
            key={row.id}
            row={row}
            metricKey={metrics.get(row.metric_id)?.key ?? row.metric_id}
            checked={selected.has(row.id)}
            onToggle={onToggle}
          />
        ))}
      </tbody>
    </table>
  );
}
