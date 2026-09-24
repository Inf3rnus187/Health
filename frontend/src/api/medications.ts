// Medication doses: taken (or not) now or at a time, and the adherence.
import type { Range } from '../utils/range';
import { api } from './client';

/** An active treatment and today's doses. */
export interface TodayDoses {
  treatment_id: string;
  name: string;
  dose: string | null;
  doses_per_day: number | null;
  taken: number;
  skipped: number;
  last_at: string | null;
  /** The last dose entered today (to take it back). */
  last_id: string | null;
}

export interface Intake {
  id: string;
  treatment_id: string | null;
  name: string;
  dose: string;
  taken_at: string;
  date_key: string;
  status: 'taken' | 'skipped';
  /** web, raccourci, mcp. */
  source: string;
  note: string;
  created_at: string;
}

export interface Adherence {
  treatment_id: string;
  name: string;
  doses_per_day: number | null;
  days: number;
  planned: number | null;
  taken: number;
  skipped: number;
  rate: number | null;
  days_complete: number | null;
  days_without_record: number;
  longest_gap_days: number;
  usual_time: string | null;
  entered_late: number;
}

export interface Dose {
  taken_at?: string;
  status?: 'taken' | 'skipped';
}

const json = (method: string, body?: unknown): RequestInit => ({
  method,
  body: body === undefined ? undefined : JSON.stringify(body),
});

export const fetchTodayDoses = () => api<TodayDoses[]>('/medications/today');
export const takeDose = (a: { id: string; dose: Dose }) =>
  api<Intake>(`/treatments/${a.id}/intakes`, json('POST', a.dose));
export const deleteDose = (id: string) =>
  api<{ detail: string }>(`/medications/intakes/${id}`, json('DELETE'));
export const fetchAdherence = (range: Range) =>
  api<{ items: Adherence[] }>(
    `/medications/adherence?start=${range.start}&end=${range.end}`,
  );
