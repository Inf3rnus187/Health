import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  deleteDose,
  fetchAdherence,
  fetchTodayDoses,
  takeDose,
} from '../api/medications';
import type { Range } from '../utils/range';

/** What a new dose changes (the pages refresh). */
const FED = ['doses-today', 'adherence', 'journal-days'];

function useDoseAction<A>(fn: (arg: A) => Promise<unknown>) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      for (const key of FED) {
        void client.invalidateQueries({ queryKey: [key] });
      }
    },
  });
}

export const useTodayDoses = () =>
  useQuery({ queryKey: ['doses-today'], queryFn: fetchTodayDoses });
export const useAdherence = (range: Range) =>
  useQuery({
    queryKey: ['adherence', range],
    queryFn: () => fetchAdherence(range),
  });
export const useTakeDose = () => useDoseAction(takeDose);
export const useDeleteDose = () => useDoseAction(deleteDose);
