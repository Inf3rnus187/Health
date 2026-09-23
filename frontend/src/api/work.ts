import { type Range, rangeQuery } from '../utils/range';
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
  /** site (on site) or remote. */
  place: Place;
}

export type Place = 'site' | 'remote';

export interface WorkWeek {
  week: string;
  monday: string;
  hours: number;
  /** The part worked remote. */
  remote: number;
  days: number;
  overtime: number;
  over_48h: boolean;
  /** Weekdays off (absences, public holidays) and the main reason. */
  absent_days: number;
  absence: string | null;
  /** The contract less the weekdays off. */
  target: number;
  beyond_target: number;
}

export interface WorkPeriod {
  label: string;
  days: number;
  total_hours: number;
  days_worked: number;
  remote_hours: number;
  absent_days: number;
  /** Per week present (weekdays off left out); null if all off. */
  week_average: number | null;
  overtime_hours: number;
}

export interface WorkOff {
  kind: string;
  label: string;
  days: number;
  workdays: number;
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
  /** Full weeks worked (no day off): the base of avg_week_hours. */
  full_weeks: number;
  remote_hours: number;
  remote_days: number;
  /** Days worked remote on top of a day on site. */
  remote_after_site: string[];
  beyond_target_hours: number;
  absences: WorkOff[];
  worked_while_off: { date: string; kind: string; hours: number }[];
  weeks: WorkWeek[];
  periods: WorkPeriod[];
}

/** One day of the journal: the night before, the work, the evening. */
export interface WorkDayLine {
  date: string;
  weekday: number;
  sleep_min: number | null;
  awakenings: number | null;
  wake_time: string | null;
  bedtime: string | null;
  start: string | null;
  end: string | null;
  hours: number | null;
  remote: number;
  sessions: number;
  /** complet, a_completer, en_cours (null: no work). */
  state: string | null;
  /** arret, conge, repos, autre, ferie. */
  absence: string | null;
  absence_share: number;
  proofs: {
    id: string;
    kind: string;
    label: string;
    time: string | null;
    title: string;
    amount: number | null;
    file_name: string | null;
  }[];
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
  place?: Place;
}

const json = (method: string, body?: unknown): RequestInit => ({
  method,
  body: body === undefined ? undefined : JSON.stringify(body),
});

export const fetchWorkStats = (range: Range, contract: number) =>
  api<WorkStats>(`/work/stats?${rangeQuery(range)}&contract_hours=${contract}`);
/** Sessions of a period ("from the beginning": since 2000). */
export const fetchWorkSessions = (range: Range) =>
  api<WorkSession[]>(
    `/work/sessions?start=${range.start || '2000-01-01'}&end=${range.end}`,
  );
export const fetchWorkDays = (range: Range) =>
  api<WorkDayLine[]>(`/work/days?${rangeQuery(range)}`);
export const clockWork = (a: { kind: 'in' | 'out'; place?: Place }) =>
  api<WorkSession>('/work/clock', json('POST', a));
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
export const createWorkReport = (range: Range, contract: number) =>
  api<{ id: string; status: string }>(
    '/reports',
    json('POST', {
      type: 'work',
      period_start: range.start || null,
      period_end: range.end,
      params: { contract_hours: contract },
    }),
  );
