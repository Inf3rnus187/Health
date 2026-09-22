import {
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
} from '@tanstack/react-query';

import { fetchDailyValues, fetchInventory, reconcileData } from '../api/data';

const REFRESHED = [
  ['inventory'],
  ['daily-values'],
  ['summary'],
  ['trend'],
  ['evolution-trend'],
  ['evolution-markers'],
];
const STEP_MS = 10_000;
const STEPS = 18; // ~3 minutes: a full history takes a while

function refreshStaggered(client: QueryClient): void {
  for (let step = 1; step <= STEPS; step += 1) {
    setTimeout(() => {
      for (const queryKey of REFRESHED) {
        void client.invalidateQueries({ queryKey });
      }
    }, step * STEP_MS);
  }
}

export function useInventory() {
  return useQuery({ queryKey: ['inventory'], queryFn: fetchInventory });
}

export function useReconcile() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: reconcileData,
    onSuccess: () => refreshStaggered(client),
  });
}

export function useDailyValues(metricKey: string) {
  return useQuery({
    queryKey: ['daily-values', metricKey],
    queryFn: () => fetchDailyValues(metricKey),
    enabled: metricKey !== '',
  });
}
