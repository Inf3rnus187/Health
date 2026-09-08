// TypeScript mirrors of the backend Pydantic contracts.

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface User {
  id: string;
  email: string;
  display_name: string;
  role: string;
  timezone: string;
  unit_system: string;
  created_at: string;
}

export interface Metric {
  id: string;
  key: string;
  label: string;
  domain: string;
  data_type: string;
  unit: string | null;
  source: string;
  enum_options: string[] | null;
  min_value: number | null;
  max_value: number | null;
  aggregation_hint: string;
  formula: string | null;
  is_active: boolean;
  created_at: string;
}

export interface Measurement {
  id: string;
  metric_id: string;
  event_id: string | null;
  date_key: string;
  recorded_at: string;
  source: string;
  value: unknown;
}

export interface MeasurementInput {
  metric_key: string;
  date_key: string;
  value: unknown;
}

export interface SeriesPoint {
  date_key: string;
  value: number;
}

export interface Series {
  metric_key: string;
  agg: string;
  window_days: number;
  points: SeriesPoint[];
}

export interface SeriesSpec {
  metricKey: string;
  agg: string;
  window: number;
  label?: string;
}

export interface DashboardSeries {
  metric_key: string;
  label: string;
  unit: string | null;
  agg: string;
  window_days: number;
  points: SeriesPoint[];
}

export interface Dashboard {
  domain: string;
  window_days: number;
  series: DashboardSeries[];
}
