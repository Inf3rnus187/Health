import { useQuery } from '@tanstack/react-query';

import { fetchEcgSeries, fetchRouteTrack } from '../api/records';

export function useEcgSeries(id: string | null) {
  return useQuery({
    queryKey: ['ecg-series', id],
    queryFn: () => fetchEcgSeries(id ?? ''),
    enabled: id !== null,
  });
}

export function useRouteTrack(id: string | null) {
  return useQuery({
    queryKey: ['route-track', id],
    queryFn: () => fetchRouteTrack(id ?? ''),
    enabled: id !== null,
  });
}
