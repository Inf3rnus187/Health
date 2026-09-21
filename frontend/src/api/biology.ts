import { getAccessToken } from './client';

export interface BiologyResult {
  added: number;
  metrics: number;
  dates: string[];
}

export interface PurgeResult {
  values: number;
  metrics: number;
}

function authHeaders(): Record<string, string> | undefined {
  const token = getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : undefined;
}

export async function importBiology(form: FormData): Promise<BiologyResult> {
  const res = await fetch('/api/v1/biology/import', {
    method: 'POST',
    headers: authHeaders(),
    body: form,
  });
  if (!res.ok) {
    throw new Error(`Erreur ${res.status}`);
  }
  return (await res.json()) as BiologyResult;
}

export async function purgeBiology(): Promise<PurgeResult> {
  const res = await fetch('/api/v1/biology/values', {
    method: 'DELETE',
    headers: authHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Erreur ${res.status}`);
  }
  return (await res.json()) as PurgeResult;
}
