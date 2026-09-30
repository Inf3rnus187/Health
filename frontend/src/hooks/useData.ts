import {
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
} from '@tanstack/react-query';

import { fetchDailyValues, fetchInventory, reconcileData } from '../api/data';
import { hub, ms } from '../settings';

const REFRESHED = [
  ['inventory'],
  ['daily-values'],
  ['summary'],
  ['trend'],
  ['evolution-trend'],
  ['evolution-markers'],
];

function refreshStaggered(client: QueryClient): void {
  // ~3 minutes by default: a full history takes a while
  const { reconcile_refresh_s: every, reconcile_refresh_steps: steps } = hub();
  for (let step = 1; step <= steps; step += 1) {
    setTimeout(
      () => {
        for (const queryKey of REFRESHED) {
          void client.invalidateQueries({ queryKey });
        }
      },
      step * ms(every),
    );
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
