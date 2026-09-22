import type { DashboardSeries } from '../api/types';
import { MetricPanel } from './metric/MetricPanel';

export function SeriesCard({ series }: { series: DashboardSeries }) {
  return <MetricPanel metricKey={series.metric_key} compact />;
}
