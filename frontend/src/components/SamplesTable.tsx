import type { Metric, Sample } from '../api/types';
import { SampleRow } from './SampleRow';

interface SamplesTableProps {
  rows: Sample[];
  metrics: Map<string, Metric>;
}

export function SamplesTable({ rows, metrics }: SamplesTableProps) {
  if (rows.length === 0) {
    return <p className="muted">Aucun échantillon.</p>;
  }
  return (
    <div className="table-wrap">
      <table className="data-table">
        <tbody>
          {rows.map((sample) => (
            <SampleRow
              key={sample.id}
              sample={sample}
              metricKey={metrics.get(sample.metric_id)?.key ?? sample.metric_id}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}
