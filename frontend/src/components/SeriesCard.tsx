import type { DashboardSeries } from '../api/types';
import { TrendChart } from './TrendChart';

export function SeriesCard({ series }: { series: DashboardSeries }) {
  const title = series.unit ? `${series.label} (${series.unit})` : series.label;
  return (
    <div className="dash-card">
      <h3 className="dash-title">{title}</h3>
      <TrendChart metricKey={series.metric_key} label={series.label} />
    </div>
  );
}
