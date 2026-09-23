import { authFetch } from './client';

export interface BiologyResult {
  added: number;
  metrics: number;
  dates: string[];
}

export interface PurgeResult {
  values: number;
  metrics: number;
}

export async function importBiology(form: FormData): Promise<BiologyResult> {
  const res = await authFetch('/biology/import', {
    method: 'POST',
    body: form,
  });
  if (!res.ok) {
    throw new Error(`Erreur ${res.status}`);
  }
  return (await res.json()) as BiologyResult;
}

export async function purgeBiology(): Promise<PurgeResult> {
  const res = await authFetch('/biology/values', { method: 'DELETE' });
  if (!res.ok) {
    throw new Error(`Erreur ${res.status}`);
  }
  return (await res.json()) as PurgeResult;
}
