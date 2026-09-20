import { api, getAccessToken } from './client';
import type { Appointment, Condition, Treatment } from './types';

type Body = Record<string, unknown>;
const del = (path: string) =>
  api<{ detail: string }>(path, { method: 'DELETE' });
const post = <T>(path: string, body: Body) =>
  api<T>(path, { method: 'POST', body: JSON.stringify(body) });

export const listConditions = () => api<Condition[]>('/conditions');
export const createCondition = (b: Body) => post<Condition>('/conditions', b);
export const deleteCondition = (id: string) => del(`/conditions/${id}`);

export const listTreatments = () => api<Treatment[]>('/treatments');
export const createTreatment = (b: Body) => post<Treatment>('/treatments', b);
export const updateTreatment = (id: string, b: Body) =>
  api<Treatment>(`/treatments/${id}`, {
    method: 'PUT',
    body: JSON.stringify(b),
  });
export const deleteTreatment = (id: string) => del(`/treatments/${id}`);

export const listAppointments = () => api<Appointment[]>('/appointments');
export const createAppointment = (b: Body) =>
  post<Appointment>('/appointments', b);
export const deleteAppointment = (id: string) => del(`/appointments/${id}`);

export async function importAppointments(
  form: FormData,
): Promise<{ added: number }> {
  const token = getAccessToken();
  const headers = token ? { Authorization: `Bearer ${token}` } : undefined;
  const res = await fetch('/api/v1/appointments/import', {
    method: 'POST',
    headers,
    body: form,
  });
  if (!res.ok) {
    throw new Error(`Erreur ${res.status}`);
  }
  return (await res.json()) as { added: number };
}
