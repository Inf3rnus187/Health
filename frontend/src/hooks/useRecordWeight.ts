import { useMutation, useQueryClient } from '@tanstack/react-query';

import { recordMeasurements } from '../api/measurements';
import { localToday } from '../utils/format';

// Everything that shows the weight must refresh after an entry.
const REFRESHED = [
  ['summary'],
  ['trend'],
  ['daily-values'],
  ['inventory'],
  ['evolution-trend'],
  ['evolution-markers'],
];

export function useRecordWeight() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (kg: number) =>
      recordMeasurements([
        { metric_key: 'body.weight', date_key: localToday(), value: kg },
      ]),
    onSuccess: () => {
      for (const queryKey of REFRESHED) {
        void client.invalidateQueries({ queryKey });
      }
    },
  });
}
