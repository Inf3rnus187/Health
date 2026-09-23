import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  addWorkSession,
  clockWork,
  deleteWorkSession,
  fetchWorkSessions,
  fetchWorkStats,
} from '../api/work';

/** Queries that show work hours (they refresh after a change). */
const FED = [
  'work-stats',
  'work-sessions',
  'work-health',
  'absences',
  'evidence',
  'nights',
  'summary',
  'overview',
  'trend',
  'dashboard',
];

export function useWorkRefresh() {
  const client = useQueryClient();
  return () => {
    for (const name of FED) {
      void client.invalidateQueries({ queryKey: [name] });
    }
  };
}

export const useWorkStats = (start: string, end: string, contract: number) =>
  useQuery({
    queryKey: ['work-stats', start, end, contract],
    queryFn: () => fetchWorkStats(start, end, contract),
  });

export const useWorkSessions = (start: string, end: string) =>
  useQuery({
    queryKey: ['work-sessions', start, end],
    queryFn: () => fetchWorkSessions(start, end),
  });

function useWorkAction<A>(fn: (arg: A) => Promise<unknown>) {
  const refresh = useWorkRefresh();
  return useMutation({ mutationFn: fn, onSuccess: refresh });
}

export const useClock = () => useWorkAction(clockWork);
export const useAddSession = () => useWorkAction(addWorkSession);
export const useDeleteSession = () => useWorkAction(deleteWorkSession);
