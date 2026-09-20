import { MetricSelect } from './MetricSelect';

export interface SampleFilters {
  metricKey: string;
  start: string;
  end: string;
}

interface SamplesFiltersProps {
  filters: SampleFilters;
  onChange: (patch: Partial<SampleFilters>) => void;
}

export function SamplesFilters({ filters, onChange }: SamplesFiltersProps) {
  return (
    <div className="filters">
      <MetricSelect
        value={filters.metricKey}
        onChange={(metricKey) => onChange({ metricKey })}
      />
      <input
        className="input"
        type="date"
        value={filters.start}
        onChange={(event) => onChange({ start: event.target.value })}
      />
      <input
        className="input"
        type="date"
        value={filters.end}
        onChange={(event) => onChange({ end: event.target.value })}
      />
    </div>
  );
}
