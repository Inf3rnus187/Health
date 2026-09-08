import type { Metric } from '../api/types';
import { colorForMetric } from '../theme/palette';

export function MetricRow({ metric }: { metric: Metric }) {
  return (
    <li className="metric-row">
      <span
        className="dot"
        style={{ background: colorForMetric(metric.key) }}
      />
      <span className="metric-key">{metric.key}</span>
      <span className="metric-label">{metric.label}</span>
      <span className="metric-type">{metric.data_type}</span>
    </li>
  );
}
