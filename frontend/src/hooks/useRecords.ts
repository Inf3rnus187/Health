import { useQuery } from '@tanstack/react-query';

import { fetchEcg, fetchRoutes, fetchWorkouts } from '../api/records';

export function useWorkouts(limit = 500) {
  return useQuery({
    queryKey: ['workouts', limit],
    queryFn: () => fetchWorkouts(limit),
  });
}

export function useEcg() {
  return useQuery({ queryKey: ['ecg'], queryFn: fetchEcg });
}

export function useRoutes() {
  return useQuery({ queryKey: ['routes'], queryFn: fetchRoutes });
}
