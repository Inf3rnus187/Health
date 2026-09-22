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

const MARKERS_KEY = ['evolution-markers'];
const TREND_KEY = ['evolution-trend'];

// Re-analysing the whole history runs in the background for minutes:
// poll the affected queries every 10 s for ~2 min.
const STAGGER_MS = 10_000;
const STAGGER_STEPS = 12;
const REFRESHED_KEYS = [TREND_KEY, ['photos'], ['photo-analysis']];

function refreshStaggered(client: QueryClient): void {
  for (let step = 1; step <= STAGGER_STEPS; step += 1) {
    setTimeout(() => {
      for (const queryKey of REFRESHED_KEYS) {
        void client.invalidateQueries({ queryKey });
      }
    }, step * STAGGER_MS);
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
