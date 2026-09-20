import { useMutation, useQueryClient } from '@tanstack/react-query';

import { deleteMeasurements } from '../api/measurements';

export function useDeleteMeasurements() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (ids: string[]) => deleteMeasurements(ids),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['measurements'] });
      void client.invalidateQueries({ queryKey: ['series'] });
      void client.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}
