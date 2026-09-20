import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { listAppointments, listConditions, listTreatments } from '../api/care';

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
    onSuccess: () => void client.invalidateQueries({ queryKey: [key] }),
  });
}
