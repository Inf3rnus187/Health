import {
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
} from '@tanstack/react-query';

import {
  fetchMarkers,
  fetchTrend,
  reanalyzeAll,
  saveProfile,
  type MarkersResponse,
} from '../api/evolution';
import { hub, ms } from '../settings';

const MARKERS_KEY = ['evolution-markers'];
const TREND_KEY = ['evolution-trend'];

// Re-analysing the whole history runs in the background for minutes:
// poll the affected queries every 10 s for ~2 min (by default).
const REFRESHED_KEYS = [TREND_KEY, ['photos'], ['photo-analysis']];

function refreshStaggered(client: QueryClient): void {
  const { reanalysis_refresh_s: every, reanalysis_refresh_steps: steps } =
    hub();
  for (let step = 1; step <= steps; step += 1) {
    setTimeout(
      () => {
        for (const queryKey of REFRESHED_KEYS) {
          void client.invalidateQueries({ queryKey });
        }
      },
      step * ms(every),
    );
  }
}

export function useTrend() {
  return useQuery({ queryKey: TREND_KEY, queryFn: fetchTrend });
}

export function useMarkers() {
  return useQuery({ queryKey: MARKERS_KEY, queryFn: fetchMarkers });
}

export function useSaveProfile() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: saveProfile,
    onSuccess: (data: MarkersResponse) => {
      client.setQueryData(MARKERS_KEY, data);
      void client.invalidateQueries({ queryKey: MARKERS_KEY });
    },
  });
}

export function useReanalyzeAll() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: reanalyzeAll,
    onSuccess: () => refreshStaggered(client),
  });
}
