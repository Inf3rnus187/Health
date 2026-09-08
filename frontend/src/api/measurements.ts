import { api } from './client';
import type { Measurement, MeasurementInput, Series } from './types';

export function fetchSeries(
  metricKey: string,
  agg: string,
  window: number,
): Promise<Series> {
  const query = new URLSearchParams({
    metric_key: metricKey,
    agg,
    window: String(window),
  });
  return api<Series>(`/measurements/series?${query.toString()}`);
}

export function recordMeasurements(
  items: MeasurementInput[],
): Promise<Measurement[]> {
  return api<Measurement[]>('/measurements', {
    method: 'POST',
    body: JSON.stringify({ items }),
  });
}
