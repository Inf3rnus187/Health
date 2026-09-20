import { keepPreviousData, useQuery } from '@tanstack/react-query';

import { fetchClinicalDoc, fetchObservations } from '../api/clinical';

export function useObservations(search: string, limit: number, offset: number) {
  return useQuery({
    queryKey: ['observations', search, limit, offset],
    queryFn: () => fetchObservations(search, limit, offset),
    placeholderData: keepPreviousData,
  });
}

export function useClinicalDoc() {
  return useQuery({ queryKey: ['clinical-doc'], queryFn: fetchClinicalDoc });
}
