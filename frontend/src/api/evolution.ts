// Longitudinal photo tracking ("méthode v2"): per-angle trends, validated
// clinical markers and the profile inputs they need.
import { api } from './client';

export type TrendStatus = 'insufficient' | 'stable' | 'improving' | 'worsening';

export type MarkerLevel = 'ok' | 'warn' | 'high' | 'missing' | 'info';

export interface DatedPhoto {
  photo_id: string;
  date: string;
  /** Weight that day (photo form, else the closest weigh-in ±3 days). */
  weight?: number | null;
}

export interface DatedValue {
  value: number;
  date: string;
}

export type WeightStatus = 'insufficient' | 'stable' | 'losing' | 'gaining';

export interface WeightChange {
  label: string;
  delta: number | null;
  percent: number | null;
}

export interface WeightMilestone {
  percent: number;
  label: string;
  reached: boolean;
}

export interface WeightTrend {
  latest: DatedValue;
  first: DatedValue;
  /** 7-day rolling median, kg. */
  current: number;
  points: TrendPoint[];
  smoothed: TrendPoint[];
  n: number;
  span_days: number;
  slope_30d: number | null;
  status: WeightStatus;
  changes: WeightChange[];
  peak: DatedValue;
  loss_from_peak_pct: number;
  milestones: WeightMilestone[];
}

export interface TrendPoint {
  date: string;
  value: number;
}

export interface TrendCriterion {
  key: string;
  label: string;
  points: TrendPoint[];
  smoothed: TrendPoint[];
  n: number;
  span_days: number;
  slope_30d: number | null;
  baseline_delta: number | null;
  status: TrendStatus;
}

export interface AngleTrend {
  angle: string;
  baseline: DatedPhoto | null;
  latest: DatedPhoto | null;
  photos_total: number;
  photos_valid: number;
  criteria: TrendCriterion[];
}

export interface EvolutionTrend {
  method_version: string;
  weight: WeightTrend | null;
  angles: AngleTrend[];
}

export interface Marker {
  key: string;
  label: string;
  value: number | null;
  unit: string;
  level: MarkerLevel;
  interpretation: string;
  reference: string;
  date: string | null;
  missing: string[];
  /** Values actually used by the formula (label, value, unit, date). */
  inputs?: MarkerInput[];
}

export interface MarkerInput {
  label: string;
  value: number;
  unit: string;
  date: string | null;
}

export interface MarkerProfile {
  waist_cm: number | null;
  waist_date: string | null;
  height_cm: number | null;
  weight_kg: number | null;
  birth_year: number | null;
}

export interface MarkersResponse {
  markers: Marker[];
  profile: MarkerProfile;
}

export interface ProfileInput {
  waist_cm?: number;
  height_cm?: number;
  birth_year?: number;
  date_key?: string;
}

export function fetchTrend(): Promise<EvolutionTrend> {
  return api<EvolutionTrend>('/evolution/trend');
}

export function fetchMarkers(): Promise<MarkersResponse> {
  return api<MarkersResponse>('/evolution/markers');
}

export function saveProfile(body: ProfileInput): Promise<MarkersResponse> {
  return api<MarkersResponse>('/evolution/profile', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export function reanalyzeAll(): Promise<{ queued: number }> {
  return api<{ queued: number }>('/evolution/reanalyze-all', {
    method: 'POST',
  });
}
