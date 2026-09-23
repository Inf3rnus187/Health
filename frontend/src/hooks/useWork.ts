import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  addWorkSession,
  clockWork,
  deleteWorkSession,
  fetchWorkSessions,
  fetchWorkStats,
} from '../api/work';
import type { Range } from '../utils/range';

/** Queries that show work hours (they refresh after a change). */
const FED = [
  'work-stats',
  'work-sessions',
  'work-health',
  'absences',
  'evidence',
  'nights',
  'incomplete',
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

export const useWorkStats = (range: Range, contract: number) =>
  useQuery({
    queryKey: ['work-stats', range, contract],
    queryFn: () => fetchWorkStats(range, contract),
  });

export const useWorkSessions = (range: Range) =>
  useQuery({
    queryKey: ['work-sessions', range],
    queryFn: () => fetchWorkSessions(range),
  });

function useWorkAction<A>(fn: (arg: A) => Promise<unknown>) {
  const refresh = useWorkRefresh();
  return useMutation({ mutationFn: fn, onSuccess: refresh });
}

export const useClock = () => useWorkAction(clockWork);
export const useAddSession = () => useWorkAction(addWorkSession);
export const useDeleteSession = () => useWorkAction(deleteWorkSession);
