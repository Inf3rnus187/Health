import { api } from './client';
import type { Metric } from './types';

export function fetchMetrics(): Promise<Metric[]> {
  return api<Metric[]>('/metrics');
}
