// One metric at a glance: the same numbers on every page.
import { api } from './client';

export interface OverviewLatest {
  value: number;
  at: string | null;
  source: string;
  /** False when only the day is known (lab value, dated entry). */
  timed?: boolean;
}

export interface MetricOverview {
  key: string;
  label: string;
  unit: string | null;
  domain: string;
  aggregation: string;
  /** "Total du jour", "Moyenne du jour"… per the metric's aggregation. */
  day_label: string;
  latest: OverviewLatest | null;
  day: { date: string; value: number } | null;
  avg7?: number | null;
  avg30?: number | null;
  min30?: number | null;
  max30?: number | null;
  days_count?: number;
  first_day?: string;
  sources?: { source: string; count: number }[];
  series: { date: string; value: number }[];
}

export function fetchOverview(
  key: string,
  days = 365,
): Promise<MetricOverview> {
  // /catalog, not /metrics: tracker blockers drop /api/v1/metrics.
  return api<MetricOverview>(
    `/catalog/${encodeURIComponent(key)}/overview?days=${days}`,
  );
}
