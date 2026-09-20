import { keepPreviousData, useQuery } from '@tanstack/react-query';

import { fetchTrend } from '../api/trends';
import type { Bucket } from '../api/types';

/** Fetch a metric's calendar-bucketed trend, keeping the previous
 *  bucket's data while the next loads. */
export function useTrend(metricKey: string, bucket: Bucket) {
  return useQuery({
    queryKey: ['trend', metricKey, bucket],
    queryFn: () => fetchTrend(metricKey, bucket),
    placeholderData: keepPreviousData,
  });
}
