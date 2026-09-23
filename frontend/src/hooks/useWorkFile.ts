import { useMutation, useQuery } from '@tanstack/react-query';

import {
  addNight,
  deleteAbsence,
  deleteEvidence,
  fetchAbsences,
  fetchEvidence,
  fetchIncomplete,
  fetchNights,
  fetchWorkHealth,
  saveAbsence,
  updateAbsence,
  updateSession,
} from '../api/workfile';
import type { Range } from '../utils/range';
import { useWorkRefresh } from './useWork';

export const useAbsences = () =>
  useQuery({ queryKey: ['absences'], queryFn: fetchAbsences });

export const useEvidence = (range: Range) =>
  useQuery({
    queryKey: ['evidence', range],
    queryFn: () => fetchEvidence(range),
  });

export const useIncomplete = () =>
  useQuery({ queryKey: ['incomplete'], queryFn: fetchIncomplete });

export const useNights = (range: Range, missing: boolean) =>
  useQuery({
    queryKey: ['nights', range, missing],
    queryFn: () => fetchNights(range, missing),
  });

export const useWorkHealth = (range: Range) =>
  useQuery({
    queryKey: ['work-health', range],
    queryFn: () => fetchWorkHealth(range),
  });

/** A write that refreshes every work / file view. */
export function useFileAction<A>(fn: (arg: A) => Promise<unknown>) {
  const refresh = useWorkRefresh();
  return useMutation({ mutationFn: fn, onSuccess: refresh });
}

export const useSaveAbsence = () => useFileAction(saveAbsence);
export const useDeleteAbsence = () => useFileAction(deleteAbsence);
export const useUpdateAbsence = () => useFileAction(updateAbsence);
export const useDeleteEvidence = () => useFileAction(deleteEvidence);
export const useAddNight = () => useFileAction(addNight);
export const useCompleteSession = () =>
  useFileAction((a: { id: string; body: Record<string, string | null> }) =>
    updateSession(a.id, a.body),
  );
