import { useQuery } from '@tanstack/react-query';

import { fetchMetrics } from '../api/metrics';

/** The full metric catalogue (shared cache with the domain views). */
export function useMetrics() {
  return useQuery({ queryKey: ['metrics'], queryFn: fetchMetrics });
}
