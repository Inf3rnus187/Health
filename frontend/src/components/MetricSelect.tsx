import { useMetrics } from '../hooks/useMetrics';

interface MetricSelectProps {
  value: string;
  onChange: (key: string) => void;
}

export function MetricSelect({ value, onChange }: MetricSelectProps) {
  const { data } = useMetrics();
  const metrics = [...(data ?? [])].sort((a, b) => a.key.localeCompare(b.key));
  return (
    <select
      className="input"
      value={value}
      onChange={(event) => onChange(event.target.value)}
    >
      <option value="">Toutes les métriques</option>
      {metrics.map((metric) => (
        <option key={metric.id} value={metric.key}>
          {metric.key} — {metric.label}
        </option>
      ))}
    </select>
  );
}
