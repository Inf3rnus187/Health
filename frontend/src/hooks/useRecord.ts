import { useQuery } from '@tanstack/react-query';

import { fetchCareOverview, fetchRecord } from '../api/record';

/** Query keys refreshed whenever the record's inputs change. */
export const RECORD_KEYS = ['record', 'care-overview'] as const;

export const useRecord = () =>
  useQuery({ queryKey: ['record'], queryFn: fetchRecord });

export const useCareOverview = () =>
  useQuery({ queryKey: ['care-overview'], queryFn: fetchCareOverview });
