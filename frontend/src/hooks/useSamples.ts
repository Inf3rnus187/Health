import { keepPreviousData, useQuery } from '@tanstack/react-query';

import { fetchSamples } from '../api/samples';
import type { SampleQuery } from '../api/types';

/** Fetch one filtered page of raw samples, keeping the prior page while
 *  the next loads so paging stays smooth. */
export function useSamples(query: SampleQuery) {
  return useQuery({
    queryKey: ['samples', query],
    queryFn: () => fetchSamples(query),
    placeholderData: keepPreviousData,
  });
}
