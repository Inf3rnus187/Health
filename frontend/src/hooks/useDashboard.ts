import { useQuery } from '@tanstack/react-query';

import { fetchDashboard } from '../api/dashboard';

export function useDashboard(domain: string) {
  return useQuery({
    queryKey: ['dashboard', domain],
    queryFn: () => fetchDashboard(domain),
  });
}
