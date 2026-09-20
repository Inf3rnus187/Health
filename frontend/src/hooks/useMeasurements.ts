import { useQuery } from '@tanstack/react-query';

import { fetchMeasurements } from '../api/measurements';

export function useMeasurements() {
  return useQuery({
    queryKey: ['measurements'],
    queryFn: fetchMeasurements,
  });
}
