import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import { uploadExport } from '../api/imports';

/** Upload an export with a live progress percentage. */
export function useUploadExport() {
  const client = useQueryClient();
  const [progress, setProgress] = useState(0);
  const mutation = useMutation({
    mutationFn: (file: File) => uploadExport(file, setProgress),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['import-jobs'] });
    },
  });
  return { mutation, progress, setProgress };
}
