import { api, getAccessToken } from './client';
import type {
  EcgRow,
  EcgSeries,
  RouteRow,
  RouteTrack,
  WorkoutRow,
} from './types';

export function fetchWorkouts(limit: number): Promise<WorkoutRow[]> {
  return api<WorkoutRow[]>(`/workouts?limit=${limit}`);
}

export function fetchEcg(): Promise<EcgRow[]> {
  return api<EcgRow[]>('/ecg');
}

export function fetchRoutes(): Promise<RouteRow[]> {
  return api<RouteRow[]>('/routes');
}

export function fetchEcgSeries(id: string): Promise<EcgSeries> {
  return api<EcgSeries>(`/ecg/${id}/series`);
}

export function fetchRouteTrack(id: string): Promise<RouteTrack> {
  return api<RouteTrack>(`/routes/${id}/track`);
}

export async function downloadRecord(
  path: string,
  filename: string,
): Promise<void> {
  const token = getAccessToken();
  const headers = token ? { Authorization: `Bearer ${token}` } : undefined;
  const res = await fetch(`/api/v1${path}`, { headers });
  if (!res.ok) {
    throw new Error(`Erreur ${res.status}`);
  }
  _save(await res.blob(), filename);
}

function _save(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
