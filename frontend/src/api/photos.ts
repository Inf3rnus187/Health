import { api, authFetch } from './client';

export interface Photo {
  id: string;
  angle: string;
  date_key: string;
  taken_at: string;
  status: string;
  linked_weight: number | null;
  created_at: string;
}

export interface PhotoAnalysis {
  id: string;
  photo_id: string;
  model: string;
  prompt_version: string;
  raw_output: Record<string, unknown>;
  derived_metrics: Record<string, unknown> | null;
  comparison_ref: string | null;
  created_at: string;
}

// Method v2 `raw_output`: quality gate, blinded 0–10 scores per criterion
// and counterbalanced paired comparisons (deltas in [-2, 2], < 0 = less
// visible fat). Old v1 analyses have no `method` key.
export interface PhotoQuality {
  ok: boolean;
  brightness?: number;
  sharpness?: number;
  width?: number;
  height?: number;
  issues?: string[];
}

export interface PhotoComparison {
  horizon: string;
  label: string;
  ref_photo_id: string | null;
  ref_date: string | null;
  deltas: Record<string, number>;
  consistent?: Record<string, boolean>;
}

export interface AnalysisV2 {
  method: 'v2';
  quality?: PhotoQuality;
  scores?: Record<string, number>;
  labels?: Record<string, string>;
  confidence?: number | null;
  pose_ok?: boolean | null;
  remarks?: string | null;
  comparisons?: PhotoComparison[];
}

export function asAnalysisV2(
  raw: Record<string, unknown> | null | undefined,
): AnalysisV2 | null {
  return raw?.method === 'v2' ? (raw as unknown as AnalysisV2) : null;
}

export function listPhotos(angle?: string): Promise<Photo[]> {
  return api<Photo[]>(`/photos${angle ? `?angle=${angle}` : ''}`);
}

export function fetchAnalysis(id: string): Promise<PhotoAnalysis> {
  return api<PhotoAnalysis>(`/photos/${id}/analysis`);
}

export function reanalyzePhoto(id: string): Promise<{ status: string }> {
  return api<{ status: string }>(`/photos/${id}/analyze`, { method: 'POST' });
}

export function deletePhoto(id: string): Promise<void> {
  return api<void>(`/photos/${id}`, { method: 'DELETE' });
}

export function deleteAllPhotos(): Promise<{ deleted: number }> {
  return api<{ deleted: number }>('/photos', { method: 'DELETE' });
}

export async function fetchPhotoBlob(id: string): Promise<string> {
  const res = await authFetch(`/photos/${id}/file`);
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  return URL.createObjectURL(await res.blob());
}
