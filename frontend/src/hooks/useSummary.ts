import { useQuery } from '@tanstack/react-query';

import { api } from '../api/client';
import type { SummaryTile } from '../api/types';

/** Latest value of each headline metric, for the home recap. */
export function useSummary() {
  return useQuery({
    queryKey: ['summary'],
    queryFn: () => api<SummaryTile[]>('/summary'),
  });
}
