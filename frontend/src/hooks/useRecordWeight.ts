import { useMutation, useQueryClient } from '@tanstack/react-query';

import { recordMeasurements } from '../api/measurements';

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export function useRecordWeight() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (kg: number) =>
      recordMeasurements([
        { metric_key: 'body.weight', date_key: today(), value: kg },
      ]),
    onSuccess: () => client.invalidateQueries({ queryKey: ['series'] }),
  });
}
