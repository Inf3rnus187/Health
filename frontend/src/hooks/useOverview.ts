import { useQuery } from '@tanstack/react-query';

import { fetchOverview } from '../api/overview';

export function useOverview(key: string) {
  return useQuery({
    queryKey: ['overview', key],
    queryFn: () => fetchOverview(key),
    enabled: key !== '',
  });
}
