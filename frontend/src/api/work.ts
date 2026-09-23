import { api, getAccessToken } from './client';

export interface WorkSession {
  id: string;
  date_key: string;
  start_at: string | null;
  end_at: string | null;
  hours: number | null;
  /** complete, open, missing_start or missing_end. */
  status: string;
  source: string;
  note: string;
}

export interface WorkWeek {
  week: string;
  monday: string;
  hours: number;
  days: number;
  overtime: number;
  over_48h: boolean;
}

export interface WorkPeriod {
  label: string;
  days: number;
  total_hours: number;
  days_worked: number;
  week_average: number;
  overtime_hours: number;
}

export interface WorkStats {
  start: string;
  end: string;
  contract_hours: number;
  open: WorkSession | null;
  total_hours: number;
  days_worked: number;
  avg_day_hours: number | null;
  avg_week_hours: number | null;
  avg_start: string | null;
  avg_end: string | null;
  longest_day: { date: string; hours: number } | null;
  days_over_10h: number;
  weeks_over_48h: number;
  overtime_hours: number;
  weeks: WorkWeek[];
  periods: WorkPeriod[];
}

export interface WorkImport {
  dry_run: boolean;
  sessions: number;
  stored: number;
  days: number;
  first_day: string | null;
  last_day: string | null;
  total_hours: number;
  preview: { day: string; start: string; end: string }[];
  skipped_count: number;
  skipped: { line?: number; text?: string; at?: string; reason: string }[];
}

export interface SessionBody {
  start_at: string;
  end_at: string | null;
  note?: string;
}

const json = (method: string, body?: unknown): RequestInit => ({
  method,
  body: body === undefined ? undefined : JSON.stringify(body),
});

export const fetchWorkStats = (start: string, end: string, contract: number) =>
  api<WorkStats>(
    `/work/stats?start=${start}&end=${end}&contract_hours=${contract}`,
  );
export const fetchWorkSessions = (start: string, end: string) =>
  api<WorkSession[]>(`/work/sessions?start=${start}&end=${end}`);
export const clockWork = (kind: 'in' | 'out') =>
  api<WorkSession>('/work/clock', json('POST', { kind }));
export const addWorkSession = (body: SessionBody) =>
  api<WorkSession>('/work/sessions', json('POST', body));
export const deleteWorkSession = (id: string) =>
  api<{ detail: string }>(`/work/sessions/${id}`, json('DELETE'));

/** Read (dry run) or import a past clock-in / clock-out log. */
export async function importWork(
  file: File,
  dryRun: boolean,
): Promise<WorkImport> {
  const form = new FormData();
  form.append('file', file);
  const token = getAccessToken();
  const res = await fetch(`/api/v1/work/import?dry_run=${dryRun}`, {
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
  return (await res.json()) as WorkImport;
}

/** Queue the work-hours PDF report of a period (see Rapports). */
export const createWorkReport = (
  start: string,
  end: string,
  contract: number,
) =>
  api<{ id: string; status: string }>(
    '/reports',
    json('POST', {
      type: 'work',
      period_start: start,
      period_end: end,
      params: { contract_hours: contract },
    }),
  );
