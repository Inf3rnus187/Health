import type { Range } from '../utils/range';
import { api, authFetch, toError } from './client';
import type { Report } from './types';

export function fetchReports(): Promise<Report[]> {
  return api<Report[]>('/reports');
}

/** Options of a report: before / after a day, weekly contract hours. */
export interface ReportParams {
  compare_from?: string;
  contract_hours?: number;
}

export function createReport(
  type: string,
  range: Range,
  params: ReportParams = {},
): Promise<Report> {
  return api<Report>('/reports', {
    method: 'POST',
    body: JSON.stringify({
      type,
      period_start: range.start || null,
      period_end: range.end,
      params,
    }),
  });
}

export interface Verdict {
  sha256: string;
  authentic: boolean;
  report: Report | null;
}

/** Is this file one of my reports, unchanged? */
export async function verifyReport(file: File): Promise<Verdict> {
  const form = new FormData();
  form.set('file', file);
  const res = await authFetch('/reports/verify', {
    method: 'POST',
    body: form,
  });
  if (!res.ok) throw await toError(res);
  return (await res.json()) as Verdict;
}
