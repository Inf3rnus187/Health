import { useMutation, useQueryClient } from '@tanstack/react-query';

import { resetImported } from '../api/imports';

const AFFECTED = ['samples', 'import-jobs', 'dashboard', 'series', 'metrics'];

/** Wipe imported data and refresh every view that depends on it. */
export function useResetImported() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: resetImported,
    onSuccess: () => {
      for (const key of AFFECTED) {
        void client.invalidateQueries({ queryKey: [key] });
      }
    },
  });
}
