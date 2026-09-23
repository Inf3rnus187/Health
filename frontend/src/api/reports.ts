import type { Range } from '../utils/range';
import { api } from './client';
import type { Report } from './types';

export function fetchReports(): Promise<Report[]> {
  return api<Report[]>('/reports');
}

export function createReport(type: string, range: Range): Promise<Report> {
  return api<Report>('/reports', {
    method: 'POST',
    body: JSON.stringify({
      type,
      period_start: range.start || null,
      period_end: range.end,
    }),
  });
}
