import { api, getAccessToken } from './client';

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
  const token = getAccessToken();
  const headers = token ? { Authorization: `Bearer ${token}` } : undefined;
  const res = await fetch(`/api/v1/photos/${id}/file`, { headers });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  return URL.createObjectURL(await res.blob());
}
