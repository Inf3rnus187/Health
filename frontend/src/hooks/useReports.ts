import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { createReport, fetchReports } from '../api/reports';
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
    mutationFn: (type: string) => createReport(type),
    onSuccess: () => void client.invalidateQueries({ queryKey: ['reports'] }),
  });
}
