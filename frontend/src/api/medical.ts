import { api, authFetch } from './client';
import type { MedicalDoc } from './types';

export function listMedicalDocs(): Promise<MedicalDoc[]> {
  return api<MedicalDoc[]>('/medical/documents');
}

export async function uploadMedicalDoc(form: FormData): Promise<MedicalDoc> {
  const res = await authFetch('/medical/documents', {
    method: 'POST',
    body: form,
  });
  if (!res.ok) {
    throw new Error(`Erreur ${res.status}`);
  }
  return (await res.json()) as MedicalDoc;
}

export function deleteMedicalDoc(id: string): Promise<{ detail: string }> {
  return api<{ detail: string }>(`/medical/documents/${id}`, {
    method: 'DELETE',
  });
}

export async function viewMedicalDoc(id: string): Promise<void> {
  const res = await authFetch(`/medical/documents/${id}/file`);
  if (!res.ok) {
    throw new Error(`Erreur ${res.status}`);
  }
  const url = URL.createObjectURL(await res.blob());
  window.open(url, '_blank', 'noopener');
}

export function analyzeMedicalDoc(id: string): Promise<{ status: string }> {
  return api<{ status: string }>(`/medical/documents/${id}/analyze`, {
    method: 'POST',
  });
}

export function analyzeAllMedicalDocs(): Promise<{ queued: number }> {
  return api<{ queued: number }>('/medical/documents/analyze-all', {
    method: 'POST',
  });
}
