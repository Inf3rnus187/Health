import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  addMealPhoto,
  analyzeMeal,
  createMeal,
  dropMealPhoto,
  type MealChange,
  updateMeal,
  deleteMeal,
  deleteUrination,
  fetchMeals,
  fetchUrinations,
  logUrination,
  type Meal,
} from '../api/journal';
import type { Range } from '../utils/range';

const POLL_MS = 5000;
/** Metrics the journal feeds (their pages refresh after a change). */
const FED = [
  'journal-days',
  'summary',
  'overview',
  'trend',
  'dashboard',
  'care-overview',
  'record',
];

function pending(meals: Meal[] | undefined): boolean {
  return (meals ?? []).some(
    (m) => m.analysis_status === 'queued' || m.analysis_status === 'running',
  );
}

function useRefresh(key: string) {
  const client = useQueryClient();
  return () => {
    for (const name of [key, ...FED]) {
      void client.invalidateQueries({ queryKey: [name] });
    }
  };
}

export const useUrinations = (day: string) =>
  useQuery({
    queryKey: ['urinations', day],
    queryFn: () => fetchUrinations(day),
  });

export function useUrinationAction<A>(fn: (arg: A) => Promise<unknown>) {
  const refresh = useRefresh('urinations');
  return useMutation({ mutationFn: fn, onSuccess: refresh });
}

export const useLogUrination = () => useUrinationAction(logUrination);
export const useDeleteUrination = () => useUrinationAction(deleteUrination);

/** Meals of a period; polls while an AI reading is queued or running. */
export function useMeals(range: Range) {
  return useQuery({
    queryKey: ['meals', range],
    queryFn: () => fetchMeals(range),
    refetchInterval: (query) => (pending(query.state.data) ? POLL_MS : false),
  });
}

export function useMealAction<A>(fn: (arg: A) => Promise<unknown>) {
  const refresh = useRefresh('meals');
  return useMutation({ mutationFn: fn, onSuccess: refresh });
}

export const useCreateMeal = () => useMealAction(createMeal);
export const useAnalyzeMeal = () => useMealAction(analyzeMeal);
export const useDeleteMeal = () => useMealAction(deleteMeal);

/** A meal's edit: photos dropped, photos added, then the fields (the
 * last step reads the meal again, once). */
export interface MealEdit {
  id: string;
  change: MealChange;
  dropPlate: boolean;
  dropIds: string[];
  add: File[];
}

async function saveEdit(edit: MealEdit) {
  if (edit.dropPlate) await dropMealPhoto(edit.id, null);
  for (const photoId of edit.dropIds) await dropMealPhoto(edit.id, photoId);
  for (const file of edit.add) await addMealPhoto(edit.id, file);
  return updateMeal(edit.id, edit.change);
}

export const useEditMeal = () => useMealAction(saveEdit);
