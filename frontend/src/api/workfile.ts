import { type Range, rangeQuery } from '../utils/range';
import { api, getAccessToken } from './client';
import type { WorkSession } from './work';

export interface Absence {
  id: string;
  start_date: string;
  end_date: string;
  kind: string;
  cause: string;
  note: string;
}

export interface EvidenceItem {
  id: string;
  occurred_at: string;
  /** False when only the day is known (an expense line). */
  time_known: boolean;
  ended_at: string | null;
  kind: string;
  title: string;
  description: string;
  count: number;
  place: string;
  amount: number | null;
  meal_id: string | null;
  file_name: string | null;
  sha256: string | null;
}

export interface Night {
  wake_day: string;
  missing?: boolean;
  asleep_min?: number;
  awakenings?: number | null;
  blocks?: number | null;
  bedtime?: string | null;
  wake_time?: string | null;
  source?: string;
}

export interface Correlation {
  r: number;
  n: number;
}

export interface WorkHealth {
  start: string;
  end: string;
  sources: {
    sessions: number;
    missing_start: number;
    missing_end: number;
    nights: number;
    worked_days_without_night: number;
  };
  legal: {
    short_rests: unknown[];
    spread_over_13h: unknown[];
    long_sessions: unknown[];
    sundays: string[];
    holidays: string[];
    night_hours: number;
  };
  sleep: {
    correlations: Record<string, Correlation | null>;
    bands: {
      label: string;
      nights: number;
      sleep_hours: number | null;
      awakenings: number | null;
      blocks: number | null;
    }[];
  };
}

export const ABSENCE_KINDS: Record<string, string> = {
  arret_maladie: 'Arrêt maladie',
  accident_travail: 'Accident du travail',
  maladie_pro: 'Maladie professionnelle',
  conge: 'Congés',
  autre: 'Autre absence',
};

/** Traces: a third party saw you (with a place, an amount, an end). */
export const TRACE_KINDS: Record<string, string> = {
  transport: 'Transport (métro, Navigo, train)',
  taxi: 'Taxi / VTC',
  parking: 'Parking',
  livraison: 'Repas livré (Uber Eats…)',
  repas: 'Repas acheté',
  hotel: 'Hôtel',
  frais: 'Note de frais',
};

export const EVIDENCE_KINDS: Record<string, string> = {
  appel: 'Appel',
  sms: 'SMS / message',
  mail: 'Mail',
  capture: 'Capture d’écran',
  note: 'Note',
  document: 'Document',
  autre: 'Autre',
  ...TRACE_KINDS,
};

/** Trace kinds that are meals (logged as a meal with its price). */
export const MEAL_TRACES = ['livraison', 'repas'];

const json = (method: string, body?: unknown): RequestInit => ({
  method,
  body: body === undefined ? undefined : JSON.stringify(body),
});

export const fetchAbsences = () => api<Absence[]>('/absences');
export const saveAbsence = (body: Omit<Absence, 'id'>) =>
  api<Absence>('/absences', json('POST', body));
export const deleteAbsence = (id: string) =>
  api<{ detail: string }>(`/absences/${id}`, json('DELETE'));

export const fetchEvidence = (range: Range) =>
  api<EvidenceItem[]>(`/evidence?${rangeQuery(range)}`);

export const deleteEvidence = (id: string) =>
  api<{ detail: string }>(`/evidence/${id}`, json('DELETE'));

export const fetchNights = (range: Range, missing: boolean) =>
  api<Night[]>(`/sleep/nights?${rangeQuery(range)}&missing=${missing}`);

export const addNight = (body: {
  bedtime: string;
  wake_time: string;
  awakenings: number | null;
}) => api<{ id: string }>('/sleep/nights', json('POST', body));

export const fetchWorkHealth = (range: Range) =>
  api<WorkHealth>(`/work/health?${rangeQuery(range)}`);

export const updateSession = (id: string, body: Record<string, string>) =>
  api<WorkSession>(`/work/sessions/${id}`, json('PUT', body));
export const createFileReport = (range: Range) =>
  api<{ id: string }>(
    '/reports',
    json('POST', {
      type: 'work_health',
      period_start: range.start || null,
      period_end: range.end,
    }),
  );

/** POST a multipart form with the session token (files). */
export async function postForm<T>(path: string, form: FormData): Promise<T> {
  const token = getAccessToken();
  const res = await fetch(`/api/v1${path}`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  });
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as {
      detail?: string;
    } | null;
    throw new Error(body?.detail ?? `Erreur ${res.status}`);
  }
  return (await res.json()) as T;
}

/** What else says when a day to complete started or ended. */
export interface DayContext {
  missing: 'start' | 'end';
  has_proof: boolean;
  evidence: {
    id: string;
    label: string;
    title: string;
    trace: boolean;
    at: string | null;
    end_at: string | null;
    time: string;
  }[];
  wake_time: string | null;
  bedtime: string | null;
  activity: { first: string | null; last: string | null };
  usual: {
    weekday: string;
    that_weekday: string | null;
    overall: string | null;
  };
}

export type IncompleteDay = WorkSession & { context: DayContext };

export const fetchIncomplete = () => api<IncompleteDay[]>('/work/incomplete');
