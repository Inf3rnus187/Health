import { useQuery } from '@tanstack/react-query';

import { fetchMetrics } from '../api/metrics';
import type { Metric } from '../api/types';

/** Map metric id -> definition, reusing the cached catalogue query. */
export function useMetricIndex(): Map<string, Metric> {
  const { data } = useQuery({ queryKey: ['metrics'], queryFn: fetchMetrics });
  const index = new Map<string, Metric>();
  for (const metric of data ?? []) {
    index.set(metric.id, metric);
  }
  return index;
}
