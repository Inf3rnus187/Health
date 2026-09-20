import { api } from './client';
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
