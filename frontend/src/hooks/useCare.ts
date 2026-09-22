import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { listAppointments, listConditions, listTreatments } from '../api/care';
import { RECORD_KEYS } from './useRecord';

export const useConditions = () =>
  useQuery({ queryKey: ['conditions'], queryFn: listConditions });

export const useTreatments = () =>
  useQuery({ queryKey: ['treatments'], queryFn: listTreatments });

export const useAppointments = () =>
  useQuery({ queryKey: ['appointments'], queryFn: listAppointments });

export function useCareMutation<A>(
  key: string,
  fn: (arg: A) => Promise<unknown>,
) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      for (const name of [key, ...RECORD_KEYS]) {
        void client.invalidateQueries({ queryKey: [name] });
      }
    },
  });
}
