import { api, authFetch } from './client';
import type { ClinicalDoc, ObservationPage } from './types';

export function fetchObservations(
  search: string,
  limit: number,
  offset: number,
): Promise<ObservationPage> {
  const params = new URLSearchParams();
  params.set('limit', String(limit));
  params.set('offset', String(offset));
  if (search) {
    params.set('search', search);
  }
  return api<ObservationPage>(`/clinical/observations?${params.toString()}`);
}

export function fetchClinicalDoc(): Promise<ClinicalDoc | null> {
  return api<ClinicalDoc | null>('/clinical/document');
}

export async function importCda(
  form: FormData,
): Promise<{ observations: number }> {
  const res = await authFetch('/clinical/import', {
    method: 'POST',
    body: form,
  });
  if (!res.ok) {
    throw new Error(`Erreur ${res.status}`);
  }
  return (await res.json()) as { observations: number };
}
