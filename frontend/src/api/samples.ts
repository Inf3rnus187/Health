import { api } from './client';
import type { SamplePage, SampleQuery } from './types';

export function fetchSamples(query: SampleQuery): Promise<SamplePage> {
  const params = new URLSearchParams();
  params.set('limit', String(query.limit));
  params.set('offset', String(query.offset));
  if (query.metricKey) {
    params.set('metric_key', query.metricKey);
  }
  if (query.start) {
    params.set('start', query.start);
  }
  if (query.end) {
    params.set('end', query.end);
  }
  return api<SamplePage>(`/samples?${params.toString()}`);
}
