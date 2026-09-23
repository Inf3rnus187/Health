import { useMutation, useQuery } from '@tanstack/react-query';

import {
  addNight,
  deleteAbsence,
  deleteEvidence,
  fetchAbsences,
  fetchEvidence,
  fetchNights,
  fetchWorkHealth,
  saveAbsence,
  updateSession,
} from '../api/workfile';
import { useWorkRefresh } from './useWork';

export const useAbsences = () =>
  useQuery({ queryKey: ['absences'], queryFn: fetchAbsences });

export const useEvidence = () =>
  useQuery({ queryKey: ['evidence'], queryFn: fetchEvidence });

export const useNights = (start: string, end: string) =>
  useQuery({
    queryKey: ['nights', start, end],
    queryFn: () => fetchNights(start, end),
  });

export const useWorkHealth = (start: string, end: string) =>
  useQuery({
    queryKey: ['work-health', start, end],
    queryFn: () => fetchWorkHealth(start, end),
  });

/** A write that refreshes every work / file view. */
export function useFileAction<A>(fn: (arg: A) => Promise<unknown>) {
  const refresh = useWorkRefresh();
  return useMutation({ mutationFn: fn, onSuccess: refresh });
}

export const useSaveAbsence = () => useFileAction(saveAbsence);
export const useDeleteAbsence = () => useFileAction(deleteAbsence);
export const useDeleteEvidence = () => useFileAction(deleteEvidence);
export const useAddNight = () => useFileAction(addNight);
export const useCompleteSession = () =>
  useFileAction((a: { id: string; body: Record<string, string> }) =>
    updateSession(a.id, a.body),
  );
