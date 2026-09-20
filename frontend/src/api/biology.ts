import { getAccessToken } from './client';

export interface BiologyResult {
  added: number;
  metrics: number;
  dates: string[];
}

export async function importBiology(form: FormData): Promise<BiologyResult> {
  const token = getAccessToken();
  const headers = token ? { Authorization: `Bearer ${token}` } : undefined;
  const res = await fetch('/api/v1/biology/import', {
    method: 'POST',
    headers,
    body: form,
  });
  if (!res.ok) {
    throw new Error(`Erreur ${res.status}`);
  }
  return (await res.json()) as BiologyResult;
}
