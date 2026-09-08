import type { SeriesSpec } from '../api/types';
import { useSeries } from '../hooks/useSeries';
import { colorForMetric } from '../theme/palette';
import { Chart } from './Chart';

export function MetricChart({ spec }: { spec: SeriesSpec }) {
  const { data, isPending, isError } = useSeries(spec);
  if (isPending) {
    return <p className="muted">Chargement…</p>;
  }
  if (isError || !data || data.points.length === 0) {
    return <p className="muted">Aucune donnée pour le moment.</p>;
  }
  return (
    <Chart
      points={data.points}
      label={spec.label ?? spec.metricKey}
      color={colorForMetric(spec.metricKey)}
    />
  );
}
