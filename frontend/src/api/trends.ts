import { api } from './client';
import type { Bucket, Trend } from './types';

export function fetchTrend(metricKey: string, bucket: Bucket): Promise<Trend> {
  const params = new URLSearchParams({ metric_key: metricKey, bucket });
  return api<Trend>(`/trends?${params.toString()}`);
}
