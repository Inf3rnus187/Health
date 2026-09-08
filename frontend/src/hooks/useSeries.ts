import { useQuery } from '@tanstack/react-query';

import { fetchSeries } from '../api/measurements';
import type { SeriesSpec } from '../api/types';

export function useSeries(spec: SeriesSpec) {
  return useQuery({
    queryKey: ['series', spec.metricKey, spec.agg, spec.window],
    queryFn: () => fetchSeries(spec.metricKey, spec.agg, spec.window),
  });
}
