import { api } from './client';
import type { Metric } from './types';

export function fetchMetrics(): Promise<Metric[]> {
  // Use the /catalog alias: some tracking/ad blockers drop requests whose
  // path contains "metrics". The backend serves both.
  return api<Metric[]>('/catalog');
}

/** French name of every metric domain (one list shared with the backend). */
export function fetchDomainLabels(): Promise<Record<string, string>> {
  return api<Record<string, string>>('/catalog/domains');
}
