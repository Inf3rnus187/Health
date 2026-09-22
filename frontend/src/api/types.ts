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

export type Bucket = 'day' | 'week' | 'month' | 'year';

export interface TrendPoint {
  t: number;
  value: number;
}

export interface Trend {
  metric_key: string;
  bucket: Bucket;
  points: SeriesPoint[];
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

export interface ImportJob {
  id: string;
  filename: string;
  status: string;
  phase: string;
  processed: number;
  samples: number;
  workouts: number;
  ecg: number;
  routes: number;
  error: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface Sample {
  id: string;
  metric_id: string;
  start_at: string;
  end_at: string | null;
  value_num: number | null;
  value_text: string | null;
  unit: string | null;
  source: string;
}

export interface SamplePage {
  items: Sample[];
  total: number;
  limit: number;
  offset: number;
}

export interface SampleQuery {
  metricKey?: string;
  start?: string;
  end?: string;
  limit: number;
  offset: number;
}

export interface WorkoutRow {
  id: string;
  activity_type: string;
  start_at: string;
  end_at: string | null;
  duration_min: number | null;
  energy_kcal: number | null;
  distance_km: number | null;
}

export interface EcgRow {
  id: string;
  recorded_at: string | null;
  classification: string | null;
  sample_rate_hz: number | null;
  sample_count: number | null;
}

export interface RouteRow {
  id: string;
  started_at: string | null;
  point_count: number;
}

export interface EcgSeries {
  sample_rate_hz: number | null;
  values: number[];
}

export interface RouteTrack {
  points: [number, number][];
}

export interface Observation {
  id: string;
  label: string;
  value_num: number | null;
  value_text: string | null;
  unit: string | null;
  effective_at: string | null;
}

export interface ObservationPage {
  items: Observation[];
  total: number;
  limit: number;
  offset: number;
}

export interface ClinicalDoc {
  id: string;
  observation_count: number;
  created_at: string;
}

export interface SummaryTile {
  key: string;
  label: string;
  unit: string | null;
  value: number;
  date_key: string;
  at: string | null;
  delta: number | null;
  avg7: number | null;
  spark: number[];
}

export interface Condition {
  id: string;
  name: string;
  code: string | null;
  status: string;
  onset_date: string | null;
  notes: string | null;
  created_at: string;
}

export interface Treatment {
  id: string;
  name: string;
  dose: string | null;
  frequency: string | null;
  start_date: string | null;
  end_date: string | null;
  active: boolean;
  notes: string | null;
  created_at: string;
}

export interface Appointment {
  id: string;
  title: string;
  starts_at: string;
  ends_at: string | null;
  practitioner: string | null;
  location: string | null;
  notes: string | null;
  source: string;
  created_at: string;
}

export interface MedicalDoc {
  id: string;
  kind: string;
  title: string;
  doc_date: string | null;
  media_type: string;
  size_bytes: number;
  notes: string | null;
  created_at: string;
  /** AI reading: null (never), queued, done or failed. */
  analysis_status?: string | null;
  analysis?: DocAnalysis | null;
}

export interface DocValue {
  key: string;
  label: string;
  value: number;
  unit: string;
  date: string;
  /** "lecture" = exact parser, "ia" = AI value proven by the text. */
  origin: 'lecture' | 'ia';
}

export interface DocMedication {
  name: string;
  dose: string;
  frequency: string;
}

export interface DocRejected {
  key: string;
  value: string;
  unit: string;
  date: string;
  reason: string;
}

export interface DocAnalysis {
  /** Model that extracted the values (document model). */
  model?: string | null;
  /** Model that wrote the summary (text / reasoning model). */
  summary_model?: string | null;
  document_type?: string | null;
  summary?: string | null;
  findings?: string[];
  medications?: DocMedication[];
  conditions?: string[];
  scanned?: boolean;
  values?: DocValue[];
  rejected?: number;
  rejected_items?: DocRejected[];
  ai_error?: string | null;
  error?: string;
  started_at?: string;
  finished_at?: string;
  duration_s?: number;
}

export interface SynthesisItem {
  text: string;
  facts: string[];
}

export interface Synthesis {
  model: string;
  generated_at: string;
  error: string | null;
  sections: { key: string; title: string; items: SynthesisItem[] }[];
  rejected: number;
  rejected_items: { text: string; reason: string }[];
  facts: { id: string; section: string; text: string }[];
}

export interface Report {
  id: string;
  type: string;
  period_start: string | null;
  period_end: string | null;
  status: string;
  created_at: string;
  /** AI clinical synthesis of a "synthesis" report. */
  summary?: Synthesis | null;
}

export interface ApiToken {
  id: string;
  name: string;
  scopes: string[];
  last_used_at: string | null;
  expires_at: string | null;
  revoked: boolean;
  created_at: string;
}

export interface TokenCreated extends ApiToken {
  token: string;
}
