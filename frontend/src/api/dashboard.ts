import { api } from './client';
import type { Dashboard } from './types';

export function fetchDashboard(domain: string, window = 7): Promise<Dashboard> {
  const query = new URLSearchParams({ window: String(window) });
  return api<Dashboard>(`/dashboard/${domain}?${query.toString()}`);
}
