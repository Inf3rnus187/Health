import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';

import { fetchJournalDays, tally } from '../api/journalDays';
import { localToday } from '../utils/format';
import type { Range } from '../utils/range';

/** Pages that show the counters (refreshed after a tap). */
const FED = ['journal-days', 'urinations', 'summary', 'overview', 'trend'];

/** A page of the journal (the previous page stays while the next loads). */
export function useJournalDays(range: Range, limit: number, offset: number) {
  return useQuery({
    queryKey: ['journal-days', range, limit, offset],
    queryFn: () => fetchJournalDays(range, limit, offset),
    placeholderData: keepPreviousData,
  });
}

/** Today's line: last night and the counters. */
export function useToday() {
  const today = localToday();
  return useJournalDays({ start: today, end: today }, 1, 0);
}

/** +1 / −1 on a counter (water, coffee, cigarette, pee). */
export function useTally() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: tally,
    onSuccess: () => {
      for (const name of FED) {
        void client.invalidateQueries({ queryKey: [name] });
      }
    },
  });
}
