import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { createReport, fetchReports, type ReportParams } from '../api/reports';
import type { Range } from '../utils/range';
import type { Report } from '../api/types';

function interval(reports: Report[] | undefined): number | false {
  const pending = (reports ?? []).some((r) => r.status === 'pending');
  return pending ? 2000 : false;
}

export function useReports() {
  return useQuery({
    queryKey: ['reports'],
    queryFn: fetchReports,
    refetchInterval: (query) => interval(query.state.data),
  });
}

export function useCreateReport() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (a: { type: string; range: Range; params?: ReportParams }) =>
      createReport(a.type, a.range, a.params),
    onSuccess: () => void client.invalidateQueries({ queryKey: ['reports'] }),
  });
}
