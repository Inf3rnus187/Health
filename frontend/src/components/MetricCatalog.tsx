import { useQuery } from '@tanstack/react-query';

import { fetchMetrics } from '../api/metrics';
import { MetricRow } from './MetricRow';

export function MetricCatalog() {
  const { data, isPending, isError, error } = useQuery({
    queryKey: ['metrics'],
    queryFn: fetchMetrics,
  });
  if (isError) {
    return <p className="error">Erreur : {(error as Error).message}</p>;
  }
  if (isPending || !data) {
    return <p className="muted">Chargement du catalogue…</p>;
  }
  return (
    <div>
      <h2>Catalogue de métriques ({data.length})</h2>
      <ul className="metric-list">
        {data.map((metric) => (
          <MetricRow key={metric.key} metric={metric} />
        ))}
      </ul>
    </div>
  );
}
