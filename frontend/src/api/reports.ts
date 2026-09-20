import { api } from './client';
import type { Report } from './types';

export function fetchReports(): Promise<Report[]> {
  return api<Report[]>('/reports');
}

export function createReport(type: string): Promise<Report> {
  return api<Report>('/reports', {
    method: 'POST',
    body: JSON.stringify({ type }),
  });
}
