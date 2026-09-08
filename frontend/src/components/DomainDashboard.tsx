import type { DashboardSeries } from '../api/types';
import { useDashboard } from '../hooks/useDashboard';
import { SeriesCard } from './SeriesCard';

function hasData(series: DashboardSeries): boolean {
  return series.points.length > 0;
}

export function DomainDashboard({ domain }: { domain: string }) {
  const { data, isPending } = useDashboard(domain);
  if (isPending || !data) {
    return <p className="muted">Chargement…</p>;
  }
  const series = data.series.filter(hasData);
  if (series.length === 0) {
    return <p className="muted">Aucune donnée pour ce domaine.</p>;
  }
  return (
    <div className="dash-grid">
      {series.map((entry) => (
        <SeriesCard key={entry.metric_key} series={entry} />
      ))}
    </div>
  );
}
