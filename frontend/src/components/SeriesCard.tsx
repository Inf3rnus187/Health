import type { DashboardSeries } from '../api/types';
import { colorForMetric } from '../theme/palette';
import { Chart } from './Chart';

export function SeriesCard({ series }: { series: DashboardSeries }) {
  const title = series.unit ? `${series.label} (${series.unit})` : series.label;
  return (
    <div className="dash-card">
      <h3 className="dash-title">{title}</h3>
      <Chart
        points={series.points}
        label={series.label}
        color={colorForMetric(series.metric_key)}
      />
    </div>
  );
}
