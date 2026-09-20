import { api } from './client';
import type { Metric } from './types';

export function fetchMetrics(): Promise<Metric[]> {
  // Use the /catalog alias: some tracking/ad blockers drop requests whose
  // path contains "metrics". The backend serves both.
  return api<Metric[]>('/catalog');
}
