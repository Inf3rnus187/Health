// Everything stored per metric and per source, and the reconcile job.
import { api } from './client';
import type { Measurement } from './types';

export interface SourceStat {
  source: string;
  count: number;
  first: string | null;
  last: string | null;
}

export interface InventoryRow {
  key: string;
  label: string;
  domain: string;
  unit: string | null;
  /** Raw readings (Apple export, Health Auto Export…). */
  raw: SourceStat[];
  /** One value per day, from every source. */
  daily: SourceStat[];
}

export function fetchInventory(): Promise<InventoryRow[]> {
  return api<InventoryRow[]>('/data/inventory');
}

export function reconcileData(): Promise<{ queued: boolean }> {
  return api<{ queued: boolean }>('/data/reconcile', { method: 'POST' });
}

export function fetchDailyValues(metricKey: string): Promise<Measurement[]> {
  const query = new URLSearchParams({ metric_key: metricKey });
  return api<Measurement[]>(`/measurements?${query.toString()}`);
}
