import type { Measurement, Metric } from '../api/types';
import { DataTable } from './DataTable';
import { DataToolbar } from './DataToolbar';

interface DataPanelProps {
  rows: Measurement[];
  metrics: Map<string, Metric>;
  selected: Set<string>;
  onToggle: (id: string) => void;
  onDelete: () => void;
}

export function DataPanel({
  rows,
  metrics,
  selected,
  onToggle,
  onDelete,
}: DataPanelProps) {
  return (
    <section className="card">
      <DataToolbar
        total={rows.length}
        selected={selected.size}
        onDelete={onDelete}
      />
      <DataTable
        rows={rows}
        metrics={metrics}
        selected={selected}
        onToggle={onToggle}
      />
    </section>
  );
}
